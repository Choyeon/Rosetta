"""系列变更必须失效「全部章节」的详情缓存（批次 #203）。

详情响应里嵌着 series 简报（系列的 title/slug/post_count + 本篇 position 与 prev/next，
见 ``PostSeriesBrief``），它属于整个系列而不是某一篇：系列改名 / 停用 / 删除，或者章节
增删、重排、发布状态变化，都会让**其它章节**缓存里的「第 N 章」与上下章链接失真。

缓存键是 ``post:{slug}:{lang}``（``CACHE_TTL["post_detail"] = 600s``），写侧原先只清
"被改的那一篇"：停用系列后最长十分钟里，其余章节的卡片还在链一个已经 404 的
``/series/<slug>`` —— 正是批次 #74 卡片口径要挡的形态（"把访客引向 404 比没有入口更糟"）。

每条用例都先往缓存里塞一份"陈旧详情"，再走真实写口，然后断言两件事：
1. 同系列每一篇、每一种语言的键都被清掉；
2. 与本次改动无关的文章键原样保留（失效范围不能顺手扩成全量）。
"""

from __future__ import annotations

from datetime import timedelta

import pytest
from httpx import AsyncClient

from backend.api.scheduled_posts import publish_due_posts
from backend.core.cache import cache, make_cache_key
from backend.core.i18n import LANGUAGE_CODES
from backend.models.blog import Post
from backend.models.post_series import PostSeries
from backend.utils.compat import utc_now_naive

SERIES = "/api/series"
ADMIN_SERIES = "/api/admin/series"
BLOG = "/api/blog"


def _unwrap(body):
    """详情/管理口两种形态都接：全局信封 ``{success, data}`` 与裸 dict。"""
    if isinstance(body, dict) and "data" in body:
        return body["data"]
    return body


async def _mk_series(db, slug: str, *, is_active: bool = True) -> PostSeries:
    series = PostSeries(
        title={"zh": f"系列{slug}", "en": f"Series {slug}"},
        slug=slug,
        is_active=is_active,
    )
    db.add(series)
    await db.commit()
    await db.refresh(series)
    return series


async def _mk_post(
    db,
    author_id: int,
    slug: str,
    *,
    series: PostSeries | None = None,
    order: int = 1,
    status: str = "published",
    scheduled_at=None,
) -> Post:
    post = Post(
        title={"zh": f"《{slug}》", "en": slug},
        slug=slug,
        content={"zh": "正文", "en": "body"},
        excerpt={"zh": "摘要", "en": "excerpt"},
        author_id=author_id,
        series_id=series.id if series else None,
        series_order=order,
        status=status,
        # naive：SQLite 把 aware 值存成带 +00:00 的字符串，`published_at <= now()`
        # 会按字符串比较把刚写的行判成"在未来"（AGENTS §9.1）。
        published_at=utc_now_naive() - timedelta(days=1) if status == "published" else None,
        scheduled_at=scheduled_at,
    )
    db.add(post)
    await db.commit()
    await db.refresh(post)
    return post


async def _seed_detail_caches(*slugs: str) -> list[str]:
    """给每篇的每种语言塞一份"陈旧详情"，返回键清单。"""
    keys = [make_cache_key("post", slug, lang) for slug in slugs for lang in LANGUAGE_CODES]
    for key in keys:
        await cache.set(key, {"id": 1, "stale": True}, ttl=600)
        assert await cache.get(key) is not None
    return keys


async def _assert_cleared(keys: list[str], reason: str) -> None:
    survivors = [key for key in keys if await cache.get(key) is not None]
    assert not survivors, f"{reason}，这些详情缓存没清：{survivors}"


async def _assert_kept(keys: list[str], reason: str) -> None:
    lost = [key for key in keys if await cache.get(key) is None]
    assert not lost, f"{reason}，却把这些无关缓存清了：{lost}"


class TestSeriesAdminWrites:
    """系列 admin 写口（改名 / 启停 / 删除）必须连带失效名下每篇章节。"""

    @pytest.mark.asyncio
    async def test_toggle_clears_every_chapter(
        self, client: AsyncClient, admin_headers: dict, db_session, test_post: Post
    ):
        series = await _mk_series(db_session, "cache-toggle")
        await _mk_post(db_session, test_post.author_id, "cache-toggle-1", series=series, order=1)
        await _mk_post(db_session, test_post.author_id, "cache-toggle-2", series=series, order=2)

        unrelated = await _seed_detail_caches("cache-toggle-outsider")
        chapter_keys = await _seed_detail_caches("cache-toggle-1", "cache-toggle-2")

        resp = await client.put(f"{ADMIN_SERIES}/{series.id}/toggle", headers=admin_headers)
        assert resp.status_code == 200, resp.text
        assert _unwrap(resp.json())["is_active"] is False

        # 停用后系列页是 404：卡片刻在缓存里就等于把访客引向 404（最长 600s）
        await _assert_cleared(chapter_keys, "停用系列后章节详情缓存仍在")
        await _assert_kept(unrelated, "停用系列不应清无关文章")

    @pytest.mark.asyncio
    async def test_rename_clears_every_chapter(
        self, client: AsyncClient, admin_headers: dict, db_session, test_post: Post
    ):
        series = await _mk_series(db_session, "cache-rename")
        await _mk_post(db_session, test_post.author_id, "cache-rename-1", series=series, order=1)
        await _mk_post(db_session, test_post.author_id, "cache-rename-2", series=series, order=2)

        chapter_keys = await _seed_detail_caches("cache-rename-1", "cache-rename-2")

        resp = await client.put(
            f"{ADMIN_SERIES}/{series.id}",
            headers=admin_headers,
            json={"title": {"zh": "改名后的系列", "en": "Renamed series"}},
        )
        assert resp.status_code == 200, resp.text

        await _assert_cleared(chapter_keys, "系列改名后章节卡片还会显示旧系列名")

    @pytest.mark.asyncio
    async def test_delete_clears_every_chapter(
        self, client: AsyncClient, admin_headers: dict, db_session, test_post: Post
    ):
        """删除必须在行消失之前按 series_id 取到章节 slug——晚一步就永远清不到。"""
        series = await _mk_series(db_session, "cache-delete")
        await _mk_post(db_session, test_post.author_id, "cache-delete-1", series=series, order=1)
        await _mk_post(db_session, test_post.author_id, "cache-delete-2", series=series, order=2)

        chapter_keys = await _seed_detail_caches("cache-delete-1", "cache-delete-2")

        resp = await client.delete(f"{ADMIN_SERIES}/{series.id}", headers=admin_headers)
        assert resp.status_code == 200, resp.text

        await _assert_cleared(chapter_keys, "删除系列后章节缓存里还挂着已删除的系列卡片")


class TestPostWrites:
    """章节自身的写路径（改序位 / 删除 / 批量状态 / 定时发布）同样要清整组章节。"""

    @pytest.mark.asyncio
    async def test_update_order_clears_siblings(
        self, client: AsyncClient, admin_headers: dict, db_session, test_post: Post
    ):
        series = await _mk_series(db_session, "cache-reorder")
        first = await _mk_post(
            db_session, test_post.author_id, "cache-reorder-1", series=series, order=1
        )
        await _mk_post(db_session, test_post.author_id, "cache-reorder-2", series=series, order=2)

        sibling_keys = await _seed_detail_caches("cache-reorder-2")

        resp = await client.put(
            f"{BLOG}/posts/{first.id}",
            headers=admin_headers,
            json={"series_order": 9},
        )
        assert resp.status_code == 200, resp.text

        await _assert_cleared(sibling_keys, "调序后同系列其它章节的「第 N 章」还是旧值")

    @pytest.mark.asyncio
    async def test_delete_chapter_clears_siblings(
        self, client: AsyncClient, admin_headers: dict, db_session, test_post: Post
    ):
        series = await _mk_series(db_session, "cache-drop")
        chapter = await _mk_post(
            db_session, test_post.author_id, "cache-drop-1", series=series, order=1
        )
        await _mk_post(db_session, test_post.author_id, "cache-drop-2", series=series, order=2)

        sibling_keys = await _seed_detail_caches("cache-drop-2")

        resp = await client.delete(f"{BLOG}/posts/{chapter.id}", headers=admin_headers)
        assert resp.status_code == 200, resp.text

        await _assert_cleared(sibling_keys, "删掉一章后剩余章节的 prev/next 仍指向已删文章")

    @pytest.mark.asyncio
    async def test_batch_status_clears_siblings(
        self, client: AsyncClient, admin_headers: dict, db_session, test_post: Post
    ):
        series = await _mk_series(db_session, "cache-batch")
        chapter = await _mk_post(
            db_session, test_post.author_id, "cache-batch-1", series=series, order=1
        )
        await _mk_post(db_session, test_post.author_id, "cache-batch-2", series=series, order=2)

        sibling_keys = await _seed_detail_caches("cache-batch-2")

        resp = await client.post(
            f"{BLOG}/posts/batch-status",
            headers=admin_headers,
            json={"post_ids": [chapter.id], "status": "draft"},
        )
        assert resp.status_code == 200, resp.text

        await _assert_cleared(sibling_keys, "批量转草稿后章节目录少了一章，其余章节序号没更新")

    @pytest.mark.asyncio
    async def test_advanced_batch_clears_siblings(
        self, client: AsyncClient, admin_headers: dict, db_session, test_post: Post
    ):
        series = await _mk_series(db_session, "cache-batch2")
        chapter = await _mk_post(
            db_session, test_post.author_id, "cache-batch2-1", series=series, order=1
        )
        await _mk_post(db_session, test_post.author_id, "cache-batch2-2", series=series, order=2)

        sibling_keys = await _seed_detail_caches("cache-batch2-2")

        resp = await client.post(
            "/api/admin/posts/batch",
            headers=admin_headers,
            json={"action": "draft", "post_ids": [chapter.id]},
        )
        assert resp.status_code == 200, resp.text

        await _assert_cleared(sibling_keys, "后台批量转草稿后章节序号没更新")

    @pytest.mark.asyncio
    async def test_create_chapter_clears_siblings(
        self, client: AsyncClient, admin_headers: dict, db_session, test_post: Post
    ):
        """新建并直接发布 = 目录多一章：旧章节的 post_count 与「下一篇」全变。"""
        series = await _mk_series(db_session, "cache-create")
        await _mk_post(db_session, test_post.author_id, "cache-create-1", series=series, order=1)

        sibling_keys = await _seed_detail_caches("cache-create-1")
        unrelated = await _seed_detail_caches("cache-create-outsider")

        resp = await client.post(
            f"{BLOG}/posts",
            headers=admin_headers,
            json={
                "title": {"zh": "新章节", "en": "New chapter"},
                "content": {"zh": "正文", "en": "body"},
                "slug": "cache-create-2",
                "status": "published",
                "series_id": series.id,
                "series_order": 2,
            },
        )
        assert resp.status_code == 201, resp.text

        await _assert_cleared(sibling_keys, "新建章节后同系列旧章节的章数/上下章还是旧值")
        await _assert_kept(unrelated, "新建章节不应清无关文章")

    @pytest.mark.asyncio
    async def test_publish_due_posts_clears_siblings(self, db_session, test_post: Post):
        """到点发布 = 这篇进入公开章节目录：同系列其它章节的 post_count 与 prev/next 全变。"""
        series = await _mk_series(db_session, "cache-due")
        await _mk_post(db_session, test_post.author_id, "cache-due-1", series=series, order=1)
        await _mk_post(
            db_session,
            test_post.author_id,
            "cache-due-2",
            series=series,
            order=2,
            status="scheduled",
            scheduled_at=utc_now_naive() - timedelta(minutes=5),
        )

        sibling_keys = await _seed_detail_caches("cache-due-1")

        published = await publish_due_posts(db_session)
        assert published == 1

        await _assert_cleared(sibling_keys, "定时发布到点后，同系列章节的章数/上下章还是旧值")
