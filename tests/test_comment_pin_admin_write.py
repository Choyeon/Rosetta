"""
评论置顶（``Comment.is_pinned``）的四段接线补齐。

后端原本有三段：模型列、``CommentResponse.is_pinned`` 投影，以及公开线程
``order_by(desc(Comment.is_pinned), desc(Comment.created_at))`` 那条排序判据。
缺的是**写口**：``PATCH /api/admin/comments/{id}`` 的 ``CommentAdminUpdate``
只收 status / active / content，后台的「置顶」菜单因此是留言专属，
评论那一族没有任何入口。于是「置顶」对评论来说是一个访客会被它影响、
却没人能设置的状态；而即便有人能设，公开线程也从不解释为什么某条评论在最上面
（消费方缺位，批次 #146 的前端那半）。

本文件钉住：

1. PATCH 显式写 ``is_pinned=true/false`` 真的落库，响应体回吐新值；
2. **省略键 = 不动它**（``exclude_unset`` 语义下的 None 分支）：改状态不能把置顶抹掉；
3. 公开列表口把置顶那条顶到最前（徽标解释的正是这个顺序）；
4. 公开投影带 ``is_pinned``（前端接的不是空气）；
5. 非 staff 调这个口不获授权。
"""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta

import pytest
from httpx import AsyncClient
from sqlalchemy import select

from backend.models.blog import Comment, Post

pytestmark = pytest.mark.asyncio

# 显式时间戳的锚点（SQLite 的 created_at 只到秒，同秒并列会让排序断言翻面）
BASE = datetime(2026, 4, 1, 12, 0, 0)


async def _make_post(db_session, author_id: int) -> Post:
    post = Post(
        title={"zh": "置顶测试文章", "en": "Pin test"},
        content={"zh": "正文", "en": "Body"},
        slug=f"pin-{uuid.uuid4().hex[:10]}",
        author_id=author_id,
        status="published",
        allow_comments=True,
    )
    db_session.add(post)
    await db_session.commit()
    await db_session.refresh(post)
    return post


async def _make_comment(db_session, post_id: int, *, content: str, created_at: datetime) -> Comment:
    """created_at 必须显式给：SQLite 只到秒，两条同秒的行按 desc(created_at) 排会并列，
    "未置顶时较新的在前"那条断言就会随机翻面（假绿/假红都 possible）。naive 值即可。"""
    comment = Comment(
        post_id=post_id,
        parent_id=None,
        user_id=None,
        content=content,
        author_name="访客甲",
        status="approved",
        active=True,
        is_pinned=False,
        created_at=created_at,
    )
    db_session.add(comment)
    await db_session.commit()
    await db_session.refresh(comment)
    return comment


class TestAdminPinWritePath:
    async def test_patch_sets_and_clears_is_pinned(
        self, client: AsyncClient, admin_headers, db_session, test_user
    ):
        post = await _make_post(db_session, test_user.id)
        comment = await _make_comment(db_session, post.id, content="第一条", created_at=BASE)

        resp = await client.patch(
            f"/api/admin/comments/{comment.id}",
            json={"is_pinned": True},
            headers=admin_headers,
        )
        assert resp.status_code == 200, resp.text
        assert resp.json()["is_pinned"] is True
        stored = await db_session.scalar(select(Comment).where(Comment.id == comment.id))
        await db_session.refresh(stored)
        assert stored.is_pinned is True

        off = await client.patch(
            f"/api/admin/comments/{comment.id}",
            json={"is_pinned": False},
            headers=admin_headers,
        )
        assert off.status_code == 200, off.text
        assert off.json()["is_pinned"] is False
        await db_session.refresh(stored)
        assert stored.is_pinned is False

    async def test_omitting_the_key_does_not_clear_a_pin(
        self, client: AsyncClient, admin_headers, db_session, test_user
    ):
        """PATCH 是增量语义：只改审核状态不能顺手把置顶抹了（表现是"保存成功但置顶没了"）。"""
        post = await _make_post(db_session, test_user.id)
        comment = await _make_comment(db_session, post.id, content="置顶稿", created_at=BASE)
        first = await client.patch(
            f"/api/admin/comments/{comment.id}",
            json={"is_pinned": True},
            headers=admin_headers,
        )
        assert first.status_code == 200, first.text

        second = await client.patch(
            f"/api/admin/comments/{comment.id}",
            json={"status": "approved"},
            headers=admin_headers,
        )
        assert second.status_code == 200, second.text
        assert second.json()["is_pinned"] is True
        stored = await db_session.scalar(select(Comment).where(Comment.id == comment.id))
        await db_session.refresh(stored)
        assert stored.is_pinned is True

    async def test_missing_comment_is_404(self, client: AsyncClient, admin_headers):
        resp = await client.patch(
            "/api/admin/comments/999999", json={"is_pinned": True}, headers=admin_headers
        )
        assert resp.status_code == 404

    async def test_requires_staff(self, client: AsyncClient, db_session, test_user):
        post = await _make_post(db_session, test_user.id)
        comment = await _make_comment(db_session, post.id, content="别人的", created_at=BASE)
        resp = await client.patch(f"/api/admin/comments/{comment.id}", json={"is_pinned": True})
        assert resp.status_code in (401, 403)


class TestPublicReadPath:
    @staticmethod
    def _rows(body) -> list[dict]:
        """该口直接回评论数组（无 ``{success,data}`` 信封），断言按实际形态取。"""
        if isinstance(body, list):
            return list(body)
        data = body.get("data", body)
        if isinstance(data, dict):
            return list(data.get("items") or data.get("comments") or [])
        return list(data or [])

    async def test_pinned_comment_is_first_and_projected(
        self, client: AsyncClient, admin_headers, db_session, test_user
    ):
        post = await _make_post(db_session, test_user.id)
        older = await _make_comment(db_session, post.id, content="较早的一条", created_at=BASE)
        newer = await _make_comment(
            db_session, post.id, content="较新的一条", created_at=BASE + timedelta(hours=1)
        )

        # 未置顶时：倒序，newer 在前
        before = await client.get(f"/api/blog/posts/{post.id}/comments")
        assert before.status_code == 200, before.text
        rows = self._rows(before.json())
        assert [r["id"] for r in rows] == [newer.id, older.id]
        assert all(r["is_pinned"] is False for r in rows)

        pin = await client.patch(
            f"/api/admin/comments/{older.id}",
            json={"is_pinned": True},
            headers=admin_headers,
        )
        assert pin.status_code == 200, pin.text

        after = await client.get(f"/api/blog/posts/{post.id}/comments")
        assert after.status_code == 200, after.text
        rows2 = self._rows(after.json())
        assert [r["id"] for r in rows2] == [older.id, newer.id]
        by_id = {r["id"]: r for r in rows2}
        assert by_id[older.id]["is_pinned"] is True
        assert by_id[newer.id]["is_pinned"] is False
