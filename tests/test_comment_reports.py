"""
评论举报（comment_reports）的四段接线：写口 → 存储 → 读口投影 → 后台消费。

缺陷类：``Comment.reported_at`` 在模型与迁移里躺了很久，没有任何读写方，
``comment_reports`` 表也不存在——「用户标记一条评论 → 管理员裁决」整条链路缺失。
本文件钉住：

1. 公开写口必须过文章可读性闸门（与表情反应同源，见 ``services/comment_access``）：
   草稿 / 加密文章 / 不存在的评论一律 404，写不进去任何行。
2. 登录用户不能举报自己的评论（400 SELF_REPORT）；游客评论任何账号都可举报。
3. 去重：同一登录用户对同一条评论只留一条 open；匿名按 IP + 24h。
   重复时回 200 + ``duplicate=true``，**不新建行**。
4. ``Comment.reported_at`` 是"还有 open 举报"的待处理标记：首次举报立起，
   最后一条被裁决后清回 NULL；只裁决其中一条时保持非空。后台
   ``GET /api/admin/comments?reported_only=true`` 查的就是它。
5. 管理端两个口只对 staff 开放（429/403 之外的身份面不做暴露）。
"""

from __future__ import annotations

import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy import select

from backend.core.auth import aget_password_hash
from backend.models.blog import Comment, Post
from backend.models.comment_report import CommentReport

pytestmark = pytest.mark.asyncio


async def _make_post(db_session, author_id: int, **kwargs) -> Post:
    defaults = {
        "title": {"zh": "举报测试文章", "en": "Report test"},
        "content": {"zh": "正文", "en": "Body"},
        "slug": f"rp-{uuid.uuid4().hex[:10]}",
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


async def _make_comment(db_session, post_id: int, *, user_id: int | None = None) -> Comment:
    comment = Comment(
        post_id=post_id,
        parent_id=None,
        user_id=user_id,
        content="这条评论会被举报：包含不当言论示例。",
        author_name="访客乙",
        author_email="guest-b@example.com",
        status="approved",
        active=True,
    )
    db_session.add(comment)
    await db_session.commit()
    await db_session.refresh(comment)
    return comment


async def _report_rows(db_session, comment_id: int) -> list[CommentReport]:
    return list(
        (
            await db_session.execute(
                select(CommentReport).where(CommentReport.comment_id == comment_id)
            )
        )
        .scalars()
        .all()
    )


async def _reload_comment(db_session, comment_id: int) -> Comment:
    db_session.expire_all()
    return await db_session.scalar(select(Comment).where(Comment.id == comment_id))


class TestReportWriteGate:
    async def test_anonymous_report_creates_row_and_flag(
        self, client: AsyncClient, db_session, test_user
    ):
        post = await _make_post(db_session, test_user.id)
        comment = await _make_comment(db_session, post.id)

        resp = await client.post(
            f"/api/comments/{comment.id}/report",
            json={"reason": "abuse", "detail": "人身攻击"},
        )
        assert resp.status_code == 201, resp.text
        body = resp.json()
        assert body["duplicate"] is False
        assert body["status"] == "open"

        rows = await _report_rows(db_session, comment.id)
        assert len(rows) == 1
        assert rows[0].reason == "abuse"
        assert rows[0].post_id == post.id
        assert rows[0].reporter_user_id is None

        reloaded = await _reload_comment(db_session, comment.id)
        assert reloaded.reported_at is not None

    async def test_duplicate_anonymous_report_is_200_without_new_row(
        self, client: AsyncClient, db_session, test_user
    ):
        post = await _make_post(db_session, test_user.id)
        comment = await _make_comment(db_session, post.id)

        first = await client.post(f"/api/comments/{comment.id}/report", json={"reason": "spam"})
        second = await client.post(f"/api/comments/{comment.id}/report", json={"reason": "other"})
        assert first.status_code == 201, first.text
        assert second.status_code == 200, second.text
        assert second.json()["duplicate"] is True
        assert second.json()["id"] == first.json()["id"]
        assert len(await _report_rows(db_session, comment.id)) == 1

    async def test_self_report_is_400(
        self, client: AsyncClient, auth_headers, db_session, test_user
    ):
        post = await _make_post(db_session, test_user.id)
        comment = await _make_comment(db_session, post.id, user_id=test_user.id)

        resp = await client.post(
            f"/api/comments/{comment.id}/report",
            json={"reason": "other"},
            headers=auth_headers,
        )
        assert resp.status_code == 400, resp.text
        # 全局异常处理器把 detail dict 摊平到顶层（信封 §7.2）
        assert resp.json()["error_code"] == "SELF_REPORT"
        assert await _report_rows(db_session, comment.id) == []

    async def test_guest_comment_can_be_reported_by_logged_in_user(
        self, client: AsyncClient, auth_headers, db_session, test_user
    ):
        post = await _make_post(db_session, test_user.id)
        comment = await _make_comment(db_session, post.id)

        resp = await client.post(
            f"/api/comments/{comment.id}/report",
            json={"reason": "offtopic"},
            headers=auth_headers,
        )
        assert resp.status_code == 201, resp.text
        rows = await _report_rows(db_session, comment.id)
        assert len(rows) == 1
        assert rows[0].reporter_user_id == test_user.id

    async def test_draft_post_comment_is_404(self, client: AsyncClient, db_session, admin_user):
        """写口比读口更该守：一次成功的举报就是「这条评论存在」的确认。"""
        draft = await _make_post(db_session, admin_user.id, status="draft")
        comment = await _make_comment(db_session, draft.id)

        resp = await client.post(f"/api/comments/{comment.id}/report", json={"reason": "spam"})
        assert resp.status_code == 404, resp.text
        assert await _report_rows(db_session, comment.id) == []

    async def test_locked_post_comment_is_404(self, client: AsyncClient, db_session, test_user):
        post = await _make_post(
            db_session, test_user.id, password=await aget_password_hash("rp-locked")
        )
        comment = await _make_comment(db_session, post.id)

        resp = await client.post(f"/api/comments/{comment.id}/report", json={"reason": "spam"})
        assert resp.status_code == 404, resp.text
        assert await _report_rows(db_session, comment.id) == []

    async def test_missing_comment_is_404(self, client: AsyncClient):
        resp = await client.post("/api/comments/999999/report", json={"reason": "spam"})
        assert resp.status_code == 404, resp.text

    async def test_unknown_reason_is_422(self, client: AsyncClient, db_session, test_user):
        post = await _make_post(db_session, test_user.id)
        comment = await _make_comment(db_session, post.id)

        resp = await client.post(
            f"/api/comments/{comment.id}/report", json={"reason": "not-a-reason"}
        )
        assert resp.status_code == 422, resp.text


class TestAdminReportQueue:
    async def test_list_requires_staff(self, client: AsyncClient):
        resp = await client.get("/api/admin/comments/reports")
        assert resp.status_code in (401, 403), resp.text

    async def test_list_projects_comment_and_post_context(
        self, client: AsyncClient, admin_headers, db_session, test_user
    ):
        post = await _make_post(db_session, test_user.id)
        comment = await _make_comment(db_session, post.id)
        created = await client.post(
            f"/api/comments/{comment.id}/report",
            json={"reason": "abuse", "detail": "骂人"},
        )
        assert created.status_code == 201, created.text

        resp = await client.get("/api/admin/comments/reports", headers=admin_headers)
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["counts"]["open"] >= 1
        item = next(i for i in body["items"] if i["id"] == created.json()["id"])
        assert item["comment_id"] == comment.id
        assert item["post_id"] == post.id
        assert item["post_slug"] == post.slug
        assert item["post_title"] == "举报测试文章"
        assert item["comment_excerpt"].startswith("这条评论会被举报")
        assert item["comment_author"] == "访客乙"
        assert item["detail"] == "骂人"
        assert item["handled_at"] is None

    async def test_handle_clears_flag_only_after_last_open_report(
        self, client: AsyncClient, admin_headers, auth_headers, db_session, test_user
    ):
        post = await _make_post(db_session, test_user.id)
        comment = await _make_comment(db_session, post.id)

        anon = await client.post(f"/api/comments/{comment.id}/report", json={"reason": "spam"})
        # 登录用户的去重键是 user_id，与匿名那条并存
        logged = await client.post(
            f"/api/comments/{comment.id}/report",
            json={"reason": "abuse"},
            headers=auth_headers,
        )
        assert anon.status_code == 201 and logged.status_code == 201

        first = await client.patch(
            f"/api/admin/comments/reports/{anon.json()['id']}",
            json={"status": "handled"},
            headers=admin_headers,
        )
        assert first.status_code == 200, first.text
        assert first.json()["status"] == "handled"
        assert first.json()["comment_reported"] is True
        assert (await _reload_comment(db_session, comment.id)).reported_at is not None

        second = await client.patch(
            f"/api/admin/comments/reports/{logged.json()['id']}",
            json={"status": "dismissed"},
            headers=admin_headers,
        )
        assert second.status_code == 200, second.text
        assert second.json()["comment_reported"] is False
        assert (await _reload_comment(db_session, comment.id)).reported_at is None

        # 后端「仅看被举报」筛选读的是同一个标记，清干净之后必须查不到
        listed = await client.get(
            "/api/admin/comments", params={"reported_only": "true"}, headers=admin_headers
        )
        assert listed.status_code == 200, listed.text
        assert all(i["id"] != comment.id for i in listed.json()["items"])

    async def test_reported_only_filter_lists_flagged_comment(
        self, client: AsyncClient, admin_headers, db_session, test_user
    ):
        post = await _make_post(db_session, test_user.id)
        flagged = await _make_comment(db_session, post.id)
        clean = await _make_comment(db_session, post.id)

        created = await client.post(f"/api/comments/{flagged.id}/report", json={"reason": "spam"})
        assert created.status_code == 201, created.text

        listed = await client.get(
            "/api/admin/comments", params={"reported_only": "true"}, headers=admin_headers
        )
        assert listed.status_code == 200, listed.text
        ids = [i["id"] for i in listed.json()["items"]]
        assert flagged.id in ids
        assert clean.id not in ids
        flagged_item = next(i for i in listed.json()["items"] if i["id"] == flagged.id)
        assert flagged_item["reported_at"]

    async def test_status_filter_and_counts(
        self, client: AsyncClient, admin_headers, db_session, test_user
    ):
        post = await _make_post(db_session, test_user.id)
        comment = await _make_comment(db_session, post.id)
        created = await client.post(f"/api/comments/{comment.id}/report", json={"reason": "spam"})
        report_id = created.json()["id"]
        handled = await client.patch(
            f"/api/admin/comments/reports/{report_id}",
            json={"status": "handled"},
            headers=admin_headers,
        )
        assert handled.status_code == 200, handled.text

        open_list = await client.get(
            "/api/admin/comments/reports", params={"status": "open"}, headers=admin_headers
        )
        handled_list = await client.get(
            "/api/admin/comments/reports", params={"status": "handled"}, headers=admin_headers
        )
        assert open_list.status_code == 200 and handled_list.status_code == 200
        open_ids = [i["id"] for i in open_list.json()["items"]]
        handled_ids = [i["id"] for i in handled_list.json()["items"]]
        assert report_id not in open_ids
        assert report_id in handled_ids
        counts = handled_list.json()["counts"]
        assert counts["handled"] >= 1
        assert counts["total"] == counts["open"] + counts["handled"] + counts["dismissed"]

    async def test_update_missing_report_is_404(self, client: AsyncClient, admin_headers):
        resp = await client.patch(
            "/api/admin/comments/reports/999999",
            json={"status": "handled"},
            headers=admin_headers,
        )
        assert resp.status_code == 404, resp.text
