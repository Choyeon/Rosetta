"""文章行写操作 → 聚合计数缓存（归档 / 站点统计 / sitemap）失效守卫。

背景：``archive:*``、``archive_stats``、``site_stats`` 三份缓存嵌的是"文章行数量"，
``seo:sitemap`` / ``sitemap:*`` / ``blog:sitemap*`` 嵌的是"文章 slug 清单"。
旧实现里发文/改文/删文只走 ``invalidate_cache("posts")``，这些聚合键完全不动：
发布一篇新文章后，归档页月份计数、首页统计卡与 sitemap 最长 600s（sitemap 3600s）
仍然少一篇——对搜索引擎来说就是"新文章不在 sitemap 里"。

反方向同样要守住：评论、点赞这类高频写改的不是文章行集合，若顺手抹掉聚合键，
``site_stats`` 的全量统计会在每次互动后重新回源，等于用正确性换回一次缓存雪崩。
"""

from __future__ import annotations

import pytest
from httpx import AsyncClient

from backend.core.cache import cache, make_cache_key
from backend.models.blog import Post
from backend.services.post_cache import invalidate_post_aggregate_caches

# 读侧真实键位（含历史遗留的三种 sitemap 形态），逐个塞值才能证明前缀匹配没漏
_AGGREGATE_KEYS = (
    "archive:zh:limit_5",
    "archive:2026:zh",
    "archive_stats",
    "site_stats",
    "sitemap:zh",
    "blog:sitemap:1",
    "seo:sitemap",
)


async def _seed_aggregates() -> None:
    for key in _AGGREGATE_KEYS:
        await cache.set(key, {"stale": True}, ttl=600)
    for key in _AGGREGATE_KEYS:
        assert await cache.get(key) is not None, f"聚合键 {key} 未能写入，测试本身失效"


async def _assert_cleared(why: str) -> None:
    for key in _AGGREGATE_KEYS:
        assert await cache.get(key) is None, f"{why}：聚合键 {key} 仍是旧值"


@pytest.mark.asyncio
async def test_service_clears_every_aggregate_key() -> None:
    """失效入口本身要覆盖全部键位（新增读侧键时这条会先失败）。"""
    await _seed_aggregates()
    await invalidate_post_aggregate_caches()
    await _assert_cleared("直接调用失效入口")


@pytest.mark.asyncio
async def test_delete_post_clears_aggregates(
    client: AsyncClient,
    admin_headers: dict,
    test_post: Post,
) -> None:
    await _seed_aggregates()

    r = await client.delete(f"/api/blog/posts/{test_post.id}", headers=admin_headers)
    assert r.status_code == 200, r.text

    await _assert_cleared("删除文章后归档计数与 sitemap 仍含该文")


@pytest.mark.asyncio
async def test_like_toggle_keeps_aggregates_warm(
    client: AsyncClient,
    auth_headers: dict,
    test_post: Post,
) -> None:
    """点赞改的是计数不是文章集合：清聚合键会让统计卡无谓回源。"""
    await _seed_aggregates()

    r = await client.post(f"/api/blog/posts/{test_post.id}/like", headers=auth_headers)
    assert r.status_code == 200, r.text

    assert await cache.get(make_cache_key("site_stats")) is not None, (
        "点赞顺手抹掉了站点统计，属于缓存雪崩"
    )
    assert await cache.get(make_cache_key("archive_stats")) is not None
