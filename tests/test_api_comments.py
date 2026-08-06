"""
Rosetta 评论系统 API 测试（Task 5 要求的 5 条核心用例 + 若干辅助断言）
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from httpx import AsyncClient
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.config import settings
from backend.models.blog import Comment, Post

BASE_DIR = Path(__file__).resolve().parent.parent
OOBE_LOCK_FILE = BASE_DIR / ".oobe_complete"
CONFIG_FILE = BASE_DIR / "rosetta.json"


def extract_error_code(body: dict | list) -> str | None:
    """从响应 body 中提取字符串 error_code，兼容多种统一封装风格：
    - 标准 FastAPI：{"detail": {..., "error_code": "X"}}
    - 自定义 envelope v1：{"success": False, "message": {..., "error_code": "X"}, "error_code": 422}
    - 自定义 envelope v2：{"success": False, "error_code": "X"}
    """
    if not isinstance(body, dict):
        return None
    # case: direct error_code string
    direct = body.get("error_code")
    if isinstance(direct, str):
        return direct
    # case: detail dict
    dtl = body.get("detail")
    if isinstance(dtl, dict):
        dc = dtl.get("error_code")
        if isinstance(dc, str):
            return dc
    # case: message dict (double envelope)
    msg = body.get("message")
    if isinstance(msg, dict):
        mc = msg.get("error_code")
        if isinstance(mc, str):
            return mc
        # inner nested again: fallback look detail inside message
        mdtl = msg.get("detail")
        if isinstance(mdtl, dict):
            mc2 = mdtl.get("error_code")
            if isinstance(mc2, str):
                return mc2
    return None


@pytest.fixture(scope="module", autouse=True)
def _ensure_oobe_marked():
    """评论端点要求 OOBE 完成。为了让本模块可以独立运行，临时写入标记文件。"""
    existed_lock = OOBE_LOCK_FILE.exists()
    existed_cfg = CONFIG_FILE.exists()
    if not existed_lock:
        OOBE_LOCK_FILE.write_text("1", encoding="utf-8")
    if not existed_cfg:
        sample = {
            "app_name": "Rosetta",
            "database_url": "sqlite+aiosqlite:///./rosetta.db",
            "admin_initialized": True,
        }
        CONFIG_FILE.write_text(json.dumps(sample, ensure_ascii=False, indent=2), encoding="utf-8")
    yield
    # cleanup
    if not existed_lock and OOBE_LOCK_FILE.exists():
        try:
            OOBE_LOCK_FILE.unlink()
        except Exception:
            pass
    if not existed_cfg and CONFIG_FILE.exists():
        try:
            CONFIG_FILE.unlink()
        except Exception:
            pass


@pytest.mark.asyncio(loop_scope="function")
async def test_post_comment_creates_pending_when_approval_required(
    client: AsyncClient,
    db_session: AsyncSession,
    test_post: Post,
):
    """游客发评论 → 默认 require_approval=True → 状态应为 pending，DB 计数 +1"""
    settings.comment_require_approval = True
    before_r = await db_session.execute(
        select(func.count(Comment.id)).where(Comment.post_id == test_post.id)
    )
    before = int(before_r.scalar_one() or 0)

    payload = {
        "author_name": "游客李四",
        "author_email": None,
        "content": "这是我的第一条评论，感谢博主分享！",
    }
    headers = {"X-Forwarded-For": "10.10.10.1"}
    r = await client.post(f"/api/posts/{test_post.id}/comments", json=payload, headers=headers)
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["status"] == "pending"
    assert body["author_name"] == "游客李四"
    assert body["author_avatar"].startswith("https://www.gravatar.com/avatar/")
    # 计数
    after_r = await db_session.execute(
        select(func.count(Comment.id)).where(Comment.post_id == test_post.id)
    )
    after = int(after_r.scalar_one() or 0)
    assert after == before + 1


@pytest.mark.asyncio(loop_scope="function")
async def test_nested_reply_rejects_grandchild(
    client: AsyncClient,
    db_session: AsyncSession,
    test_post: Post,
):
    """
    构造：根评论 A（approved） → 回复 B（parent=A） → 对 B 发回复（parent=B）
    期望：422 error_code=NESTED_REPLY_TOO_DEEP
    """
    # 手动造 A、B 两条（用 DB session，避免重复被频控卡）
    root = Comment(
        post_id=test_post.id,
        parent_id=None,
        author_name="根评论 A",
        author_email=None,
        content="我是 A（根）",
        status="approved",
        active=True,
        likes_count=0,
        is_pinned=False,
        author_ip="10.20.1.x.x",
    )
    db_session.add(root)
    await db_session.flush()

    reply_b = Comment(
        post_id=test_post.id,
        parent_id=root.id,
        author_name="回复 B",
        author_email=None,
        content="我是 B（回复 A）",
        status="approved",
        active=True,
        likes_count=0,
        is_pinned=False,
        author_ip="10.20.2.x.x",
    )
    db_session.add(reply_b)
    await db_session.commit()
    await db_session.refresh(reply_b)

    # 现在尝试 POST 一条 parent=reply_b.id 的评论（也就是孙子层）
    payload = {
        "author_name": "孙子评论",
        "parent_id": reply_b.id,
        "content": "试图在孙子层回复",
    }
    headers = {"X-Forwarded-For": "10.20.3.4"}
    r = await client.post(f"/api/posts/{test_post.id}/comments", json=payload, headers=headers)
    assert r.status_code == 422, f"期望 422 但得到 {r.status_code}: {r.text}"
    body = r.json()
    err_code = extract_error_code(body)
    assert err_code == "NESTED_REPLY_TOO_DEEP", (
        f"期望 NESTED_REPLY_TOO_DEEP 实际 err_code={err_code!r} body={body}"
    )


@pytest.mark.asyncio(loop_scope="function")
async def test_sensitive_word_auto_rejects(
    client: AsyncClient,
    db_session: AsyncSession,
    test_post: Post,
):
    """content 包含黑名单敏感词 → status=rejected（前端会提示被系统拦截）"""
    payload = {
        "author_name": "敏感词测试员",
        "content": "大家加微群领资料哦，还有更多福利等你来~",
    }
    headers = {"X-Forwarded-For": "10.30.1.1"}
    r = await client.post(f"/api/posts/{test_post.id}/comments", json=payload, headers=headers)
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["status"] == "rejected"
    # DB 中真实 status 也是 rejected
    cid = int(body["id"])
    row_r = await db_session.execute(select(Comment).where(Comment.id == cid))
    row = row_r.scalars().first()
    assert row is not None
    assert row.status == "rejected"
    assert row.active is False


@pytest.mark.asyncio(loop_scope="function")
async def test_admin_approve_reject_pipeline(
    client: AsyncClient,
    db_session: AsyncSession,
    test_post: Post,
    admin_user,
    admin_headers: dict,
):
    """
    - 先造一条 pending 评论（作者=guest）
    - 未 approve 时：公开 GET include_unapproved=false 看不到它
    - admin 取 pending 列表 → 包含它
    - admin approve → 200
    - 再公开 GET include_unapproved=false → 出现
    """
    settings.comment_require_approval = True

    pending = Comment(
        post_id=test_post.id,
        parent_id=None,
        author_name="待审核访客",
        author_email=None,
        content="这是一条待审核的评论，审核通过后才会公开。",
        status="pending",
        active=False,
        likes_count=0,
        is_pinned=False,
        author_ip="10.40.1.x.x",
    )
    db_session.add(pending)
    await db_session.commit()
    await db_session.refresh(pending)

    # 公开：include_unapproved=false
    public1 = await client.get(f"/api/posts/{test_post.slug}/comments?include_unapproved=false")
    assert public1.status_code == 200
    public1_ids = [c["id"] for c in public1.json()["items"]]
    assert pending.id not in public1_ids

    # admin 列表 pending
    admin_list = await client.get(
        "/api/admin/comments?status=pending&page=1&page_size=20", headers=admin_headers
    )
    assert admin_list.status_code == 200, admin_list.text
    items = admin_list.json()["items"]
    ids = [c["id"] for c in items]
    assert pending.id in ids

    # admin approve
    approve_r = await client.post(
        f"/api/admin/comments/{pending.id}/approve", headers=admin_headers
    )
    assert approve_r.status_code == 200
    assert approve_r.json()["status"] == "approved"

    # 公开 GET 再次
    public2 = await client.get(f"/api/posts/{test_post.slug}/comments?include_unapproved=false")
    assert public2.status_code == 200
    public2_ids = [c["id"] for c in public2.json()["items"]]
    assert pending.id in public2_ids


@pytest.mark.asyncio(loop_scope="function")
async def test_guest_ip_rate_limit_30s_window(
    client: AsyncClient,
    db_session: AsyncSession,
    test_post: Post,
):
    """
    同一个 IP（X-Forwarded-For）同 post 连续 2 条 comment →
    第二条返回 429 error_code=TOO_FREQUENT_COMMENT（30s 同 post 防重）
    """
    # 使用独立 IP，避免和其他测试频控互相影响
    shared_ip = "10.99.88.77"
    headers = {"X-Forwarded-For": shared_ip}
    payload1 = {"author_name": "频控测试者 1号", "content": "这是我的第一条正常评论（会成功）"}
    r1 = await client.post(f"/api/posts/{test_post.id}/comments", json=payload1, headers=headers)
    # 期望 201（可能被频控拦截，如果之前的其他测试用了这个 IP；所以先断言 201/或 201 pending 都行）
    assert r1.status_code == 201, f"第一条评论失败：{r1.status_code} {r1.text}"

    payload2 = {"author_name": "频控测试者 2号", "content": "这是 30s 内的第二条，会被拦截。"}
    r2 = await client.post(f"/api/posts/{test_post.id}/comments", json=payload2, headers=headers)
    # 第二次：期望 429 + error_code=TOO_FREQUENT_COMMENT
    assert r2.status_code == 429, f"第二条应该返回 429，实际：{r2.status_code} {r2.text}"
    body2 = r2.json()
    err = extract_error_code(body2)
    assert err == "TOO_FREQUENT_COMMENT", f"期望 TOO_FREQUENT_COMMENT 实际 err={err!r} body={body2}"
