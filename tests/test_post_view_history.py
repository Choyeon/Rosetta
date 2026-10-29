"""阅读历史写口：POST /api/blog/posts/{id}/view 是这张表的唯一插入点。

缺陷类：`post_view_histories` 一直被三处读取——周期榜 `GET /api/ranking/posts`
（day/week/month 的 `recent_views`）、`GET /api/blog/users/me/history`、
推荐服务的用户标签偏好——却没有任何写手。线上表现正是这两条读口的读数恒为空：
周期榜每个条目 `recent_views = 0`（综合分只剩点赞/评论），个人中心「阅读历史」
永远是空列表。四段（写口 → 存储 → 响应模型 → 消费方）里只有第一段缺失时，
接口不会报任何错，所以只能靠本文件钉住。

写口只服务登录用户：`user_id` 是 NOT NULL，匿名阅读本就无从归属；详情端点自己
不能兼任写手（SSR 首屏无 token、匿名读走缓存分支），前端由文章页在登录态下补记。
"""

import uuid
from datetime import datetime, timedelta, timezone

import pytest
from httpx import AsyncClient
from sqlalchemy import func, select

from backend.core.cache import invalidate_cache
from backend.models.blog import Post, PostViewHistory

pytestmark = pytest.mark.asyncio


async def _make_post(db_session, author_id: int, **kwargs) -> Post:
    defaults = {
        "title": {"zh": "阅读历史测试文章", "en": "History test post"},
        "content": {"zh": "正文", "en": "Body"},
        "author_id": author_id,
        "status": "published",
    }
    defaults.update(kwargs)
    defaults.setdefault("slug", f"hist-{uuid.uuid4().hex[:10]}")
    post = Post(**defaults)
    db_session.add(post)
    await db_session.commit()
    await db_session.refresh(post)
    return post


async def _history_rows(db_session, user_id: int, post_id: int) -> list[PostViewHistory]:
    return list(
        (
            await db_session.execute(
                select(PostViewHistory).where(
                    PostViewHistory.user_id == user_id,
                    PostViewHistory.post_id == post_id,
                )
            )
        )
        .scalars()
        .all()
    )


class TestViewHistoryWriter:
    async def test_logged_in_view_records_one_row(
        self, client: AsyncClient, db_session, test_user, auth_headers
    ):
        post = await _make_post(db_session, test_user.id)

        resp = await client.post(f"/api/blog/posts/{post.id}/view", headers=auth_headers)
        assert resp.status_code == 200, resp.text
        assert resp.json()["success"] is True

        rows = await _history_rows(db_session, test_user.id, post.id)
        assert len(rows) == 1
        assert rows[0].viewed_at is not None

    async def test_repeat_view_updates_same_row(
        self, client: AsyncClient, db_session, test_user, auth_headers
    ):
        """唯一索引 (user_id, post_id) 是口径：重复阅读只刷新时间，不堆行。"""
        post = await _make_post(db_session, test_user.id)

        first = await client.post(f"/api/blog/posts/{post.id}/view", headers=auth_headers)
        second = await client.post(f"/api/blog/posts/{post.id}/view", headers=auth_headers)
        assert first.status_code == second.status_code == 200

        rows = await _history_rows(db_session, test_user.id, post.id)
        assert len(rows) == 1, "重复阅读不得插入第二行（周期榜按行数算人数）"

    async def test_anonymous_view_is_rejected(self, client: AsyncClient, db_session, test_user):
        post = await _make_post(db_session, test_user.id)

        resp = await client.post(f"/api/blog/posts/{post.id}/view")
        assert resp.status_code == 401

        total = await db_session.scalar(select(func.count()).select_from(PostViewHistory))
        assert total == 0

    @pytest.mark.parametrize(
        "overrides",
        [
            {"status": "draft"},
            {"visibility": "private"},
            {"published_at": datetime.now(timezone.utc) + timedelta(days=1)},
        ],
        ids=["draft", "private", "future-scheduled"],
    )
    async def test_invisible_posts_are_not_recorded(
        self, client: AsyncClient, db_session, test_user, auth_headers, overrides
    ):
        """对外不存在的文章不写历史：否则作者预览会在自己的阅读历史里留下幽灵行。"""
        post = await _make_post(db_session, test_user.id, **overrides)

        resp = await client.post(f"/api/blog/posts/{post.id}/view", headers=auth_headers)
        assert resp.status_code == 404

        rows = await _history_rows(db_session, test_user.id, post.id)
        assert rows == []


class TestHistoryConsumersSeeTheWrite:
    async def test_my_history_lists_the_recorded_post(
        self, client: AsyncClient, db_session, test_user, auth_headers
    ):
        post = await _make_post(db_session, test_user.id)
        await client.post(f"/api/blog/posts/{post.id}/view", headers=auth_headers)

        resp = await client.get("/api/blog/users/me/history", headers=auth_headers)
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["total"] == 1
        assert body["items"][0]["post"]["slug"] == post.slug

    async def test_period_ranking_recent_views_becomes_nonzero(
        self, client: AsyncClient, db_session, test_user, auth_headers
    ):
        post = await _make_post(db_session, test_user.id)
        await client.post(f"/api/blog/posts/{post.id}/view", headers=auth_headers)

        # 榜单带 60s 响应缓存，且键位不含文章集合——不清会读到别的用例留下的快照。
        await invalidate_cache("posts")

        resp = await client.get("/api/ranking/posts", params={"period": "day", "limit": 50})
        assert resp.status_code == 200, resp.text
        items = {row["id"]: row for row in resp.json()["items"]}
        assert post.id in items, "刚被读过的公开文章必须进周期榜候选"
        assert items[post.id]["recent_views"] == 1
        assert items[post.id]["score"] >= 1
