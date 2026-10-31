"""评论审核写口的「前台页面缓存」闸门（批次 #133）。

2026-10-31 起，文章页 SSR 的载荷里带着评论首屏（`pages/posts/[slug].vue` 的
`PostDetailPayload.comments`）——评论正文从此真的烘进了公开 HTML。于是审核动作必须
同时清两层缓存，只清其中一层的表现是：接口与后台列表已经更新，而访客与爬虫在整个
Nitro SWR 窗口（文章页 600s）里仍读到被拒绝/被删/被改前的那一条。

四条写口逐一钉一次（都断言「文章响应缓存失效 + 前台页面清除」两件事都发生）：
- POST /api/admin/comments/{id}/approve
- POST /api/admin/comments/{id}/reject
- POST /api/admin/comments/{id}/spam
- PATCH /api/admin/comments/{id}（前台审核 UI 真正走的那条，status/active 双向同步）

另设一条反证：评论不存在 → 404 且一个缓存都不清（把 404 也当成"集合变了"会让垃圾
请求变成整站清缓存的放大器）。批量口与单删/作者删的同类断言已在
`tests/test_comment_author_delete.py`，本文件不重复。
"""

import pytest
from httpx import AsyncClient
from sqlalchemy import select

from backend.models.blog import Comment

ADMIN_COMMENTS = "/api/admin/comments"


async def _mk_comment(db, *, post_id: int, content: str, status: str = "pending") -> Comment:
    comment = Comment(
        post_id=post_id,
        user_id=None,
        author_name="Guest",
        content=content,
        status=status,
        active=status == "approved",
        likes_count=0,
    )
    db.add(comment)
    await db.commit()
    await db.refresh(comment)
    return comment


def _spy(monkeypatch, module: str):
    """把两条清缓存的动作记下来（模块内名，不是服务层函数）。"""
    invalidated: list[list[int]] = []
    purged: list[str] = []

    async def fake_invalidate(_db, post_ids):
        invalidated.append(list(post_ids))

    def fake_purge(reason: str = "", *args, **kwargs):
        purged.append(reason)

    monkeypatch.setattr(f"{module}.invalidate_post_caches_by_ids", fake_invalidate)
    monkeypatch.setattr(f"{module}.purge_frontend_page_cache", fake_purge)
    return invalidated, purged


class TestModerationPurgesFrontendPageCache:
    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        ("action", "module", "expect_status"),
        [
            ("approve", "backend.api.comments", "approved"),
            ("reject", "backend.api.comments", "rejected"),
            ("spam", "backend.api.comments", "spam"),
        ],
    )
    async def test_legacy_sub_actions_purge(
        self,
        client: AsyncClient,
        db_session,
        test_post,
        staff_headers: dict,
        monkeypatch,
        action: str,
        module: str,
        expect_status: str,
    ):
        invalidated, purged = _spy(monkeypatch, module)
        comment = await _mk_comment(db_session, post_id=test_post.id, content=f"待审:{action}")

        resp = await client.post(
            f"{ADMIN_COMMENTS}/{comment.id}/{action}",
            headers=staff_headers,
        )
        assert resp.status_code == 200, resp.text

        assert invalidated == [[test_post.id]], f"{action} 未失效文章响应缓存"
        assert len(purged) == 1, f"{action} 未清前台页面缓存（访客面 TTL 内仍是旧线程）"

        row = (
            await db_session.execute(select(Comment).where(Comment.id == comment.id))
        ).scalar_one()
        assert row.status == expect_status

    @pytest.mark.asyncio
    async def test_admin_patch_status_purges(
        self,
        client: AsyncClient,
        db_session,
        test_post,
        staff_headers: dict,
        monkeypatch,
    ):
        """PATCH /admin/comments/{id} 是前台审核 UI 真正调用的那条口。

        审核弹窗的"下架"走 status=rejected；此前它只清后端缓存，于是"后台说已处理、
        访客页面上的骂人评论还在"，最长挂整个 SWR 窗口。
        """
        invalidated, purged = _spy(monkeypatch, "backend.api.admin")
        comment = await _mk_comment(
            db_session, post_id=test_post.id, content="已批准的评论", status="approved"
        )

        resp = await client.patch(
            f"{ADMIN_COMMENTS}/{comment.id}",
            headers=staff_headers,
            json={"status": "rejected"},
        )
        assert resp.status_code == 200, resp.text
        assert invalidated == [[test_post.id]], "PATCH 未失效文章响应缓存"
        assert len(purged) == 1, "PATCH 未清前台页面缓存"

    @pytest.mark.asyncio
    async def test_patch_content_edit_purges(
        self,
        client: AsyncClient,
        db_session,
        test_post,
        staff_headers: dict,
        monkeypatch,
    ):
        """改正文同样是"访客看到的评论变了"，不能只清接口层。"""
        _inv, purged = _spy(monkeypatch, "backend.api.admin")
        comment = await _mk_comment(db_session, post_id=test_post.id, content="原始正文")

        resp = await client.patch(
            f"{ADMIN_COMMENTS}/{comment.id}",
            headers=staff_headers,
            json={"content": "编辑后的正文"},
        )
        assert resp.status_code == 200, resp.text
        assert len(purged) == 1, "改正文未清前台页面缓存"

    @pytest.mark.asyncio
    async def test_missing_comment_clears_nothing(
        self,
        client: AsyncClient,
        staff_headers: dict,
        monkeypatch,
    ):
        """404 不是"可见集合变了"：不应当成为整站清缓存的放大器。"""
        _inv, purged = _spy(monkeypatch, "backend.api.comments")
        resp = await client.post(f"{ADMIN_COMMENTS}/99999999/reject", headers=staff_headers)
        assert resp.status_code == 404, resp.text
        assert purged == []
