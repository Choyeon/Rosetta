"""
评论读取/写入必须过文章可读性闸门。

缺陷类（本文件的六例逐条钉住）：文章详情端点早已按 status / 定时发布 / 密码三重条件
收口，但**评论口是另一套实现**——`GET /api/blog/posts/{id}/comments` 只按 post_id 查
`Comment.active`，`GET/POST /api/posts/{slug}/comments` 与 `GET /api/comments/{id}/replies`
只按 id/slug 找到 Post 便放行。表现：

- 草稿文章的已过审评论正文匿名可读，post_id / comment_id 可枚举；
- 加密文章的正文被藏起来，评论（常常直接引用正文）却全公开；
- 任何登录用户可以给草稿写评论（作者侧看见，读者侧永远看不到，等于脏数据入口）。

判据抽在 `backend/services/post_access.py` 单一来源，三条评论口与文章详情共用。
"""

from datetime import datetime, timedelta, timezone

import pytest
from httpx import AsyncClient

from backend.core.auth import aget_password_hash
from backend.models.blog import Comment, Post
from backend.services.comment_service import CommentService

pytestmark = pytest.mark.asyncio


async def _make_post(db_session, author_id: int, **kwargs) -> Post:
    defaults = {
        "title": {"zh": "测试文章", "en": "Test post"},
        "content": {"zh": "正文", "en": "Body"},
        "slug": None,
        "author_id": author_id,
        "status": "published",
        "allow_comments": True,
    }
    defaults.update(kwargs)
    if defaults["slug"] is None:
        import uuid

        defaults["slug"] = f"gate-{uuid.uuid4().hex[:10]}"
    post = Post(**defaults)
    db_session.add(post)
    await db_session.commit()
    await db_session.refresh(post)
    return post


async def _make_comment(
    db_session, post_id: int, *, content: str = "已过审的评论", parent_id: int | None = None
) -> Comment:
    comment = Comment(
        post_id=post_id,
        parent_id=parent_id,
        content=content,
        author_name="访客甲",
        author_email="guest-a@example.com",
        status="approved",
        active=True,
    )
    db_session.add(comment)
    await db_session.commit()
    await db_session.refresh(comment)
    return comment


class TestCommentReadFollowsPostVisibility:
    async def test_draft_post_comments_hidden_on_public_list_route(
        self, client: AsyncClient, db_session, test_user, admin_headers
    ):
        """草稿文章的评论在列表口对匿名是空、对管理员仍可见（不是简单砍掉功能）。"""
        draft = await _make_post(db_session, test_user.id, status="draft")
        await _make_comment(db_session, draft.id, content="草稿里的评论")

        anon = await client.get(f"/api/blog/posts/{draft.id}/comments")
        assert anon.status_code == 200, anon.text
        assert anon.json() == []

        as_admin = await client.get(f"/api/blog/posts/{draft.id}/comments", headers=admin_headers)
        assert as_admin.status_code == 200, as_admin.text
        assert [c["content"] for c in as_admin.json()] == ["草稿里的评论"]

    async def test_scheduled_future_post_comments_hidden(
        self, client: AsyncClient, db_session, test_user
    ):
        """定时发布未到 = 对读者还不存在，评论同样不得提前泄露。"""
        future = await _make_post(
            db_session,
            test_user.id,
            status="published",
            published_at=datetime.now(timezone.utc) + timedelta(days=2),
        )
        await _make_comment(db_session, future.id, content="定时文章的评论")

        resp = await client.get(f"/api/blog/posts/{future.id}/comments")
        assert resp.status_code == 200, resp.text
        assert resp.json() == []

    async def test_password_post_comments_hidden_until_unlocked(
        self, client: AsyncClient, db_session, test_user
    ):
        """加密文章：不带密码读不到评论，带对密码就能读（与文章详情同一把钥匙）。"""
        secret = "uo3n-locked"
        post = await _make_post(db_session, test_user.id, password=await aget_password_hash(secret))
        await _make_comment(db_session, post.id, content="加密文章的评论")

        locked = await client.get(f"/api/blog/posts/{post.id}/comments")
        assert locked.status_code == 200, locked.text
        assert locked.json() == []

        wrong = await client.get(f"/api/blog/posts/{post.id}/comments", params={"password": "nope"})
        assert wrong.json() == []

        unlocked = await client.get(
            f"/api/blog/posts/{post.id}/comments", params={"password": secret}
        )
        assert [c["content"] for c in unlocked.json()] == ["加密文章的评论"]

        by_header = await client.get(
            f"/api/blog/posts/{post.id}/comments", headers={"X-Post-Password": secret}
        )
        assert [c["content"] for c in by_header.json()] == ["加密文章的评论"]

    async def test_slug_comment_route_is_404_for_draft(self, client, db_session, test_user):
        """独立评论读口（/api/posts/{slug}/comments）对草稿按 404 处理，而不是空分页。"""
        draft = await _make_post(db_session, test_user.id, status="draft")
        await _make_comment(db_session, draft.id)

        resp = await client.get(f"/api/posts/{draft.slug}/comments")
        assert resp.status_code == 404, resp.text
        assert resp.json()["error_code"] == "POST_NOT_FOUND"

    async def test_replies_of_draft_post_are_not_enumerable(
        self, client: AsyncClient, db_session, test_user
    ):
        """回复口按 comment_id 走，同样要看文章脸色（根评论挡不住子行枚举）。"""
        draft = await _make_post(db_session, test_user.id, status="draft")
        root = await _make_comment(db_session, draft.id, content="根")
        await _make_comment(db_session, draft.id, content="回复", parent_id=root.id)

        resp = await client.get(f"/api/comments/{root.id}/replies")
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["total"] == 0
        assert body["items"] == []


class TestCommentWriteFollowsPostVisibility:
    async def test_cannot_comment_on_draft_via_blog_route(
        self, client: AsyncClient, auth_headers, admin_headers, db_session, admin_user, test_user
    ):
        """非作者登录用户对草稿文章评论 = 404（文章作者本人仍可，见下一例）。"""
        draft = await _make_post(db_session, admin_user.id, status="draft")
        resp = await client.post(
            f"/api/blog/posts/{draft.id}/comments",
            json={"content": "给草稿留言"},
            headers=auth_headers,
        )
        assert resp.status_code == 404, resp.text

        still_there = await CommentService.get_post_by_any(db_session, draft.id)
        assert still_there is not None  # 文章本身还在，只是评论口对它关门

        as_author = await client.post(
            f"/api/blog/posts/{draft.id}/comments",
            json={"content": "作者给自己的草稿留言"},
            headers=admin_headers,
        )
        assert as_author.status_code == 201, as_author.text

    async def test_cannot_comment_on_locked_post_via_slug_route(
        self, client: AsyncClient, auth_headers, db_session, admin_user
    ):
        """同族写入口（slug 版）也走同一判据，避免"换个 URL 就能写"。"""
        secret = "write-lock"
        post = await _make_post(
            db_session, admin_user.id, password=await aget_password_hash(secret)
        )
        resp = await client.post(
            f"/api/posts/{post.slug}/comments",
            json={"content": "给加密文章留言", "author_name": "某人", "author_email": "a@b.co"},
            headers=auth_headers,
        )
        assert resp.status_code == 404, resp.text
        assert resp.json()["error_code"] == "POST_NOT_FOUND"

        unlocked = await client.post(
            f"/api/posts/{post.slug}/comments",
            params={"password": secret},
            json={"content": "解锁后留言", "author_name": "某人", "author_email": "a@b.co"},
            headers=auth_headers,
        )
        assert unlocked.status_code == 201, unlocked.text
