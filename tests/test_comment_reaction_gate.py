"""
评论表情反应的读口/添加口必须过文章可读性闸门。

缺陷类：`backend/api/comment_reactions.py` 的三个口只按 `Comment.id` 查评论存在与否，
从不看它挂在哪个 post 上、那个 post 对当前观看者存不存在。而评论正文那几条口早已走
``services/post_access`` 的判据。表现：草稿文章与加密文章的评论即使正文读不到，它的
**表情计数**仍能用 ``GET /api/comments/{id}/reactions`` 按 comment_id 枚举出来——
匿名回 200 + 空数组本身就是在承认"这条评论存在"，同时任何登录用户都能给看不见的评论
写反应（脏数据入口）。

取消反应（``DELETE /comments/{id}/reactions/{emoji}``）刻意不接闸门：它只删调用者自己
的行，存在与不存在都回同样的 404，问不出信息，而接了闸门会让"文章转草稿后取消不掉已有
反应"这种真实场景无从解释。
"""

from __future__ import annotations

import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy import select

from backend.core.auth import aget_password_hash
from backend.models.blog import Comment, Post
from backend.models.comment_reaction import CommentReaction

pytestmark = pytest.mark.asyncio


async def _make_post(db_session, author_id: int, **kwargs) -> Post:
    defaults = {
        "title": {"zh": "测试文章", "en": "Test post"},
        "content": {"zh": "正文", "en": "Body"},
        "slug": f"rx-{uuid.uuid4().hex[:10]}",
        "author_id": author_id,
        "status": "published",
        "allow_comments": True,
    }
    defaults.update(kwargs)
    post = Post(**defaults)
    db_session.add(post)
    await db_session.commit()
    await db_session.refresh(post)
    return post


async def _make_comment(db_session, post_id: int) -> Comment:
    comment = Comment(
        post_id=post_id,
        parent_id=None,
        content="已过审的评论",
        author_name="访客甲",
        author_email="guest-a@example.com",
        status="approved",
        active=True,
    )
    db_session.add(comment)
    await db_session.commit()
    await db_session.refresh(comment)
    return comment


class TestReactionReadGate:
    async def test_published_post_comment_is_publicly_readable(
        self, client: AsyncClient, db_session, test_user
    ):
        """正向基线：闸门不能把公开评论的统计一起挡掉。"""
        post = await _make_post(db_session, test_user.id)
        comment = await _make_comment(db_session, post.id)
        resp = await client.get(f"/api/comments/{comment.id}/reactions")
        assert resp.status_code == 200, resp.text
        assert resp.json() == {"comment_id": comment.id, "reactions": [], "total": 0}

    async def test_draft_post_comment_reactions_are_404(
        self, client: AsyncClient, db_session, test_user
    ):
        """草稿：空数组也是信息（承认评论存在），必须按 404。"""
        draft = await _make_post(db_session, test_user.id, status="draft")
        comment = await _make_comment(db_session, draft.id)
        resp = await client.get(f"/api/comments/{comment.id}/reactions")
        assert resp.status_code == 404, resp.text

    async def test_locked_post_comment_reactions_are_404(
        self, client: AsyncClient, db_session, test_user
    ):
        """加密文章：与评论列表口同判据——解不开正文就读不到它的衍生计数。"""
        secret = "rx-locked"
        post = await _make_post(db_session, test_user.id, password=await aget_password_hash(secret))
        comment = await _make_comment(db_session, post.id)
        resp = await client.get(f"/api/comments/{comment.id}/reactions")
        assert resp.status_code == 404, resp.text

    async def test_missing_comment_is_404(self, client: AsyncClient):
        resp = await client.get("/api/comments/999999/reactions")
        assert resp.status_code == 404, resp.text


class TestReactionWriteGate:
    async def test_cannot_react_on_hidden_comment(
        self, client: AsyncClient, auth_headers, db_session, admin_user
    ):
        """挡不住写口等于让任何登录用户往看不见的评论上堆计数。

        文章作者本人要留给 admin_user：`post_is_publicly_visible` 对作者放行自己的草稿，
        用 test_user 当作者就等于测另一条正向路径。
        """
        draft = await _make_post(db_session, admin_user.id, status="draft")
        comment = await _make_comment(db_session, draft.id)
        resp = await client.post(
            f"/api/comments/{comment.id}/reactions",
            json={"emoji": "👍"},
            headers=auth_headers,
        )
        assert resp.status_code == 404, resp.text
        rows = (
            (
                await db_session.execute(
                    select(CommentReaction).where(CommentReaction.comment_id == comment.id)
                )
            )
            .scalars()
            .all()
        )
        assert list(rows) == []

    async def test_public_comment_still_accepts_reaction(
        self, client: AsyncClient, auth_headers, db_session, test_user
    ):
        post = await _make_post(db_session, test_user.id)
        comment = await _make_comment(db_session, post.id)
        resp = await client.post(
            f"/api/comments/{comment.id}/reactions",
            json={"emoji": "🎉"},
            headers=auth_headers,
        )
        assert resp.status_code == 201, resp.text
        # reacted 只对登录用户有意义：同一 token 再读统计必须点亮
        listed = await client.get(f"/api/comments/{comment.id}/reactions", headers=auth_headers)
        assert listed.json()["reactions"] == [{"emoji": "🎉", "count": 1, "reacted": True}]
