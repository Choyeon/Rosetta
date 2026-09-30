"""文章展示缓存的统一失效入口。

缓存键陷阱（本模块存在的全部理由）：文章详情缓存是 ``post:{slug}:{lang}``，
它**不在** ``posts`` 前缀下，所以写侧只调 ``invalidate_cache("posts")`` 清不掉它；
而列表项里嵌的 ``comments_count`` / author 段 / category+tags 又确实会变。
凡是"改动了会被嵌进文章响应体的数据"的操作，都必须同时走这两个失效动作，
散落在各 API 模块里各写一遍迟早漏一处——所以收在这里。
"""

from __future__ import annotations

from collections.abc import Iterable

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.cache import invalidate_cache, invalidate_post_detail_cache
from backend.models.blog import Post
from backend.services.cache_service import CacheService

# 推荐/相似/热榜三套 key 走的是 services/cache_service.py 的二级缓存，
# 命名空间与 core/cache 的 make_cache_key 不同（后者统一带 rosetta:v1 前缀），
# 所以 invalidate_cache("posts") 之类根本匹配不到它们。漏掉失效的表现是：
# 文章删除或转草稿后，最长 30 分钟内仍会出现在公开推荐位上。
_RECOMMENDATION_PATTERNS = ("simv2:*", "hotv2:*", "rosetta:v1:recsv2:*")


async def invalidate_recommendation_caches() -> None:
    """失效相似文章 / 首页推荐 / 热榜三类推荐缓存。

    这三份缓存在 recommendation.py 里写入，但从来没有任何 purge 调用点，
    TTL 分别是 30min / 5min / 10min。文章行增删改必须连带清掉。
    """
    cache_service = CacheService()
    for pattern in _RECOMMENDATION_PATTERNS:
        await cache_service.invalidate_pattern(pattern)


async def invalidate_post_caches_by_slugs(slugs: Iterable[str]) -> None:
    """按 slug 失效文章详情缓存（全语言）+ 列表/RSS 缓存。

    没有受影响 slug 时**整段跳过**：列表缓存只能全量抹掉，无关写操作顺手抹一次
    就是全站文章列表集体回源的缓存雪崩。
    """
    unique = {slug for slug in slugs if slug}
    if not unique:
        return
    await invalidate_post_detail_cache(*unique)
    await invalidate_cache("posts")


async def invalidate_post_caches_by_ids(db: AsyncSession, post_ids: Iterable[int]) -> None:
    """按文章 ID 反查 slug 后失效展示缓存。

    删除评论这类"手里只有 post_id"的调用方走这里；注意必须在
    ``db.delete()`` 之前取到 ID——级联删除后关联行就查不回来了。
    """
    ids = {pid for pid in post_ids if pid}
    if not ids:
        return
    rows = await db.execute(select(Post.slug).where(Post.id.in_(ids)))
    await invalidate_post_caches_by_slugs(rows.scalars().all())


# 只随"文章行本身增删改"变化的聚合缓存前缀。``archive`` 同时覆盖 ``archive:*``
# 与 ``archive_stats``（前缀匹配）。sitemap 有三种历史键位，全部列出：
# ``sitemap:*`` / ``blog:sitemap*`` / ``seo:sitemap``。
_AGGREGATE_PREFIXES = ("archive", "site_stats", "sitemap", "blog:sitemap", "seo:sitemap")


async def invalidate_post_aggregate_caches() -> None:
    """失效归档计数、站点统计与 sitemap 三类聚合缓存。

    刻意**不**并进 ``invalidate_post_caches_by_slugs``：那条路径评论/分类/标签/作者
    写操作都会走（频率比发文高一个数量级），而这三份聚合只随文章行变化；
    顺手抹掉会让 ``site_stats`` 的全量统计在每次评论后重新回源。
    """
    for prefix in _AGGREGATE_PREFIXES:
        await invalidate_cache(prefix)
    # 推荐位只会引用已发布文章，文章行变化即可能让"相似/推荐/热榜"变成陈旧数据
    await invalidate_recommendation_caches()
