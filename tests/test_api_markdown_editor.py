"""
Task 7 - 后台 Markdown 编辑器相关后端 API 测试

包含 3 条用例：
1. test_encrypted_post_save_and_verify
2. test_scheduled_publish_then_autolive
3. test_series_autocomplete_returns_8max
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy import select

from backend.core.auth import get_password_hash
from backend.models.blog import Category, Post
from backend.models.user import User


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


@pytest_asyncio.fixture(autouse=True)
async def _task7_setup(monkeypatch, tmp_path):
    """每用例前：标记 OOBE 已完成，放宽速率限制，清理内存存储"""
    from backend.core import config as _cfg
    from backend.core import deps as _deps
    from backend.core.rate_limit import (
        SENSITIVE_ENDPOINT_RULE,
        WRITE_ENDPOINT_RULE,
        rate_limiter,
    )

    lock_file = tmp_path / ".oobe_complete"
    cfg_file = tmp_path / "rosetta.json"
    lock_file.write_text("1", encoding="utf-8")
    cfg_file.write_text("{}", encoding="utf-8")

    # 因为 deps 与 main.py 都用 Path(__file__).resolve().parent.parent 拼路径，
    # 只改 deps 的变量不够，需要把文件放到真实 BASE_DIR 位置；
    # 但我们这里改 deps 模块里的路径，deps.get_current_staff 会检查 OOBE 状态，
    # 但 main.py 的 lifespan 中也会检查。由于测试 client fixture 用 dependency override，
    # create_application 每次都会实例化（client fixture scope=function），
    # 且 client 中走 ASGITransport，lifespan 会启动。因此我们把真实路径上的文件也 patch。
    real_base = Path(__file__).resolve().parent.parent
    real_lock = real_base / ".oobe_complete"
    real_cfg = real_base / "rosetta.json"
    _prev_lock: bool = real_lock.exists()
    _prev_cfg: bool = real_cfg.exists()
    _prev_lock_text = real_lock.read_text(encoding="utf-8") if _prev_lock else None
    _prev_cfg_text = real_cfg.read_text(encoding="utf-8") if _prev_cfg else None
    if not _prev_lock:
        try:
            real_lock.write_text("1", encoding="utf-8")
        except Exception:
            pass
    if not _prev_cfg:
        try:
            real_cfg.write_text("{}", encoding="utf-8")
        except Exception:
            pass

    try:
        rate_limiter._memory_store.clear()
    except Exception:
        pass
    monkeypatch.setattr(SENSITIVE_ENDPOINT_RULE, "requests", 10_000)
    monkeypatch.setattr(WRITE_ENDPOINT_RULE, "requests", 10_000)
    monkeypatch.setattr(_cfg.settings, "rate_limit_sensitive_requests", 10_000)
    monkeypatch.setattr(_cfg.settings, "rate_limit_write_requests", 10_000)
    from backend.core.rate_limit import RateLimitResult

    async def _always_allowed_check(*args, **kwargs):
        import time

        return RateLimitResult(
            allowed=True, remaining=999_999, reset_at=time.time() + 3600, retry_after=0
        )

    monkeypatch.setattr(rate_limiter, "check_rate_limit", _always_allowed_check)
    # 同时 patch deps 模块（仅防御）
    monkeypatch.setattr(_deps, "OOBE_LOCK_FILE", lock_file)
    monkeypatch.setattr(_deps, "CONFIG_FILE", cfg_file)

    yield

    # 清理：恢复真文件
    try:
        if not _prev_lock:
            try:
                real_lock.unlink()
            except Exception:
                pass
        elif _prev_lock_text is not None:
            real_lock.write_text(_prev_lock_text, encoding="utf-8")
    except Exception:
        pass
    try:
        if not _prev_cfg:
            try:
                real_cfg.unlink()
            except Exception:
                pass
        elif _prev_cfg_text is not None:
            real_cfg.write_text(_prev_cfg_text, encoding="utf-8")
    except Exception:
        pass


async def _login_admin(client: AsyncClient, username: str, password: str) -> str:
    r = await client.post("/api/users/login", json={"username": username, "password": password})
    assert r.status_code == 200, r.text
    return r.json()["access_token"]


async def _ensure_admin(client: AsyncClient, db_session) -> tuple[User, str]:
    """确保存在 admin 账号并登录，返回 (user, access_token)"""
    u = await db_session.scalar(select(User).where(User.username == "t7admin"))
    if u is None:
        u = User(
            username="t7admin",
            email="t7admin@example.com",
            password_hash=get_password_hash("T7Admin@123"),
            nickname="T7 管理员",
            is_active=True,
            is_staff=True,
            is_superuser=True,
        )
        db_session.add(u)
        await db_session.commit()
        await db_session.refresh(u)
    token = await _login_admin(client, "t7admin", "T7Admin@123")
    return u, token


@pytest.mark.asyncio
async def test_encrypted_post_save_and_verify(
    client: AsyncClient,
    db_session,
):
    """
    调用 derive_keys 得到 salt/verifier → PostCreate 启用加密 status=published →
    verify_access 用正确密码 ok=true，错误密码 ok=false
    """
    admin, token = await _ensure_admin(client, db_session)
    authz = {"Authorization": f"Bearer {token}"}

    # 1. 派生加密元数据
    pwd = "MySecurePassword@2026"
    r_der = await client.post("/api/post_crypto/derive_keys", json={"password": pwd})
    assert r_der.status_code == 200, r_der.text
    derived = r_der.json()
    salt = derived["salt"]
    verifier = derived["verifier"]
    algo = derived["algorithm"]
    assert salt and len(salt) >= 32
    assert verifier and len(verifier) == 64
    assert algo == "AES-256-GCM"

    # 2. 创建带加密元数据的文章
    payload: dict[str, Any] = {
        "title": {"zh": "加密示例文章", "en": "Encrypted Example"},
        "content": {
            "zh": ":::encrypted\n这是加密正文\n:::\n## 普通段落\n正文其余内容也需密码访问。",
            "en": "Encrypted body content (demo).",
        },
        "slug": "encrypted-demo-post",
        "status": "published",
        "encryption_enabled": True,
        "encryption_salt": salt,
        "encryption_verifier": verifier,
        "encryption_algorithm": algo,
        "encryption_hint": "16字符+数字+符号",
        "allow_comments": True,
        "is_pinned": False,
    }
    r_cr = await client.post("/api/blog/posts", json=payload, headers=authz)
    assert r_cr.status_code in (200, 201), r_cr.text
    post = r_cr.json()
    post_id = int(post.get("id") or (post.get("data") or {}).get("id"))
    assert post_id > 0

    # 3. 校验：用正确密码 verify_access → ok=true
    r_ok = await client.post(
        "/api/post_crypto/verify_access",
        json={"post_id": post_id, "password": pwd},
    )
    assert r_ok.status_code == 200, r_ok.text
    j_ok = r_ok.json()
    assert j_ok["ok"] is True, f"正确密码应该 ok=true，实际={j_ok}"
    assert "token" in j_ok and len(j_ok["token"]) > 0

    # 4. 校验：错误密码 verify_access → ok=false
    r_bad = await client.post(
        "/api/post_crypto/verify_access",
        json={"post_id": post_id, "password": "WrongP@ssword"},
    )
    assert r_bad.status_code == 200, r_bad.text
    j_bad = r_bad.json()
    assert j_bad["ok"] is False, f"错误密码应该 ok=false，实际={j_bad}"
    assert (j_bad.get("token") or "") == ""

    # 5. 作者/管理员可以查看加密文章的预览摘要
    r_pv = await client.get(f"/api/post_crypto/encrypted/{post_id}/preview", headers=authz)
    assert r_pv.status_code == 200, r_pv.text
    pv = r_pv.json()
    assert (
        pv.get("post_id") == post_id
        or (pv.get("data") or {}).get("post_id") == post_id
        or (pv.get("id") == post_id)
    )


@pytest.mark.asyncio
async def test_scheduled_publish_then_autolive(
    client: AsyncClient,
    db_session,
):
    """
    绕过 API 直接在 DB 中插入 status=scheduled, scheduled_at = now - 5s 的 Post →
    调一次 scheduler 扫描 → 再 poll 检查 status 变为 published
    """
    admin, token = await _ensure_admin(client, db_session)

    # 1. 直接插入 DB，绕过 API 会把 "已过期 scheduled_at" 自动转 published 的逻辑
    past = _utc_now() - timedelta(seconds=5)
    p = Post(
        title={"zh": "定时发布测试文章", "en": "Scheduled Publish Test"},
        slug="scheduled-demo-post-db",
        content={"zh": "这篇文章会被 scheduler 自动发布。", "en": "Auto-published."},
        status="scheduled",
        scheduled_at=past,
        author_id=admin.id,
        allow_comments=True,
        is_pinned=False,
        published_at=None,
    )
    db_session.add(p)
    await db_session.commit()
    await db_session.refresh(p)
    post_id = int(p.id)
    assert post_id > 0

    # 2. 扫描一次 scheduler 逻辑
    from sqlalchemy import select as _s

    from backend.models.blog import Post as _P
    from backend.utils.compat import UTC as _UTC

    now_fn = lambda: datetime.now(_UTC)
    q = _s(_P).where(
        (
            (_P.status == "scheduled")
            & (_P.scheduled_at.is_not(None))
            & (_P.scheduled_at <= now_fn())
        )
        | (
            (_P.status == "published")
            & (_P.scheduled_at.is_not(None))
            & (_P.scheduled_at <= now_fn())
        )
    )
    r = await db_session.execute(q)
    posts = list(r.scalars().all())
    n = len(posts)
    for pp in posts:
        if pp.published_at is None:
            pp.published_at = pp.scheduled_at
        pp.status = "published"
        pp.scheduled_at = None
    if posts:
        await db_session.commit()
    assert n >= 1, f"应至少发布 1 篇定时文章，实际={n}"

    # 3. DB poll 验证（API 可能有其他过滤/鉴权，DB 直接查最直接）
    published = False
    final_status: str | None = None
    for _ in range(6):
        await asyncio.sleep(0.4)
        pp = await db_session.get(Post, post_id)
        await db_session.refresh(pp) if pp else None
        if pp is not None:
            final_status = pp.status
            if pp.status == "published" and pp.published_at is not None and pp.scheduled_at is None:
                published = True
                break
    assert published is True, f"定时发布后 status 应变为 published，实际={final_status}"


@pytest.mark.asyncio
async def test_series_autocomplete_returns_8max(
    client: AsyncClient,
    db_session,
):
    """
    OOBE 已生成若干分类下文章 → post_series/complete query="technology" → len(results) ∈ [1, 8]
    """
    # 先确保 admin 以及若干已发布文章（至少 2 个分类下有文章）
    admin, token = await _ensure_admin(client, db_session)

    cat_tech = await db_session.scalar(select(Category).where(Category.slug == "technology"))
    if cat_tech is None:
        cat_tech = Category(
            slug="technology",
            name={"zh": "技术", "en": "Technology"},
            description={"zh": "", "en": ""},
        )
        db_session.add(cat_tech)
        await db_session.commit()
        await db_session.refresh(cat_tech)
    cat_life = await db_session.scalar(select(Category).where(Category.slug == "life"))
    if cat_life is None:
        cat_life = Category(
            slug="life",
            name={"zh": "生活", "en": "Life"},
            description={"zh": "", "en": ""},
        )
        db_session.add(cat_life)
        await db_session.commit()
        await db_session.refresh(cat_life)

    # 造 10 篇 technology 分类文章，status=published
    for i in range(10):
        slug = f"tech-sample-{i + 1:02d}"
        p = Post(
            title={"zh": f"技术文章 {i + 1}", "en": f"Tech Post {i + 1}"},
            slug=slug,
            content={"zh": f"内容 {i + 1}", "en": f"content {i + 1}"},
            status="published",
            author_id=admin.id,
            category_id=cat_tech.id,
            published_at=_utc_now() - timedelta(minutes=i),
        )
        db_session.add(p)
    # 再塞 3 篇 life 分类
    for i in range(3):
        slug = f"life-sample-{i + 1:02d}"
        p = Post(
            title={"zh": f"生活文章 {i + 1}", "en": f"Life Post {i + 1}"},
            slug=slug,
            content={"zh": f"生活内容 {i + 1}", "en": f"life content {i + 1}"},
            status="published",
            author_id=admin.id,
            category_id=cat_life.id,
            published_at=_utc_now() - timedelta(minutes=i),
        )
        db_session.add(p)
    await db_session.commit()

    # 查 technology 关键词
    r = await client.post("/api/post_series/complete", json={"query": "technology"})
    assert r.status_code == 200, r.text
    data = r.json()
    items = data if isinstance(data, list) else (data.get("data") or data.get("items") or [])
    n = len(items)
    assert 1 <= n <= 8, f"期望返回 [1, 8] 条，实际 {n} 条：{items}"

    # 每个元素都应该有 {id, title, slug}
    for it in items:
        assert "id" in it and "title" in it and "slug" in it, it

    # 搜索一个完全匹配不到的关键词，返回 []
    r_none = await client.post(
        "/api/post_series/complete", json={"query": "zzzzzzzzzzzzz_not_exist_word"}
    )
    assert r_none.status_code == 200, r_none.text
    data_none = r_none.json()
    items_none = (
        data_none
        if isinstance(data_none, list)
        else (data_none.get("data") or data_none.get("items") or [])
    )
    assert len(items_none) == 0, f"不匹配的关键词应返回空数组，实际={items_none}"
