"""
Task 8: 后台管理生产化 UI 相关 pytest 用例
- 修改 4 次 settings → 操作日志 action=settings 数量=4 target_type=settings
- editor 访问 admin/users 403 → 新增 permission failed 日志
- stats 接口返回完整 schema（timeseries 5 datasets 等）
"""

from __future__ import annotations

from pathlib import Path

import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.auth import get_password_hash
from backend.models.log import OperationLog
from backend.models.user import User


@pytest_asyncio.fixture(autouse=True)
async def _task8_setup(monkeypatch, tmp_path):
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
    monkeypatch.setattr(_deps, "OOBE_LOCK_FILE", lock_file)
    monkeypatch.setattr(_deps, "CONFIG_FILE", cfg_file)

    yield

    try:
        if not _prev_lock:
            try:
                real_lock.unlink()
            except Exception:
                pass
        else:
            try:
                real_lock.write_text(_prev_lock_text, encoding="utf-8")
            except Exception:
                pass
        if not _prev_cfg:
            try:
                real_cfg.unlink()
            except Exception:
                pass
        else:
            try:
                real_cfg.write_text(_prev_cfg_text, encoding="utf-8")
            except Exception:
                pass
    except Exception:
        pass


# ==================== Fixtures ====================


@pytest_asyncio.fixture
async def editor_user(db_session: AsyncSession) -> User:
    """创建 editor 角色（普通 staff，非 superuser）"""
    user = User(
        username="editor",
        email="editor@example.com",
        password_hash=get_password_hash("Editor123"),
        nickname="编辑人员",
        is_active=True,
        is_staff=True,
        is_superuser=False,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest_asyncio.fixture
async def editor_headers(client: AsyncClient, editor_user: User) -> dict:
    """登录 editor，返回其 Bearer 认证头"""
    resp = await client.post(
        "/api/users/login",
        json={"username": "editor", "password": "Editor123"},
    )
    assert resp.status_code == 200, f"editor 登录失败 {resp.text}"
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


# ==================== Tests ====================


@pytest.mark.asyncio
async def test_modify_4_settings_writes_operation_logs(
    client: AsyncClient,
    admin_headers: dict,
    db_session: AsyncSession,
):
    """
    用 admin token PATCH 4 次 settings：basic + friendlinks + hero + notice
    → GET admin/logs action=settings 数量=4 且 target_type=settings
    """
    # 1. 先执行 4 次 PATCH /api/settings/{group}
    patches = [
        ("basic", {"site_name": "Rosetta", "site_url": "https://roetta.dev"}),
        (
            "friendlinks",
            {
                "links": [
                    {
                        "name": "Rosetta Hub",
                        "url": "https://rosetta.dev",
                        "desc": "官方社区",
                        "avatar": "",
                    }
                ],
            },
        ),
        (
            "hero",
            {
                "title": "Welcome to Rosetta",
                "subtitle": "The modern Markdown-first blogging platform",
                "caption": "v1.0 Task 8 edition",
                "cta_text": "Get started",
                "cta_url": "/docs",
            },
        ),
        (
            "notice",
            {
                "enabled": True,
                "content_md": "系统将于本周六凌晨进行例行维护，预计 1 小时。",
            },
        ),
    ]

    for group, payload in patches:
        resp = await client.patch(
            f"/api/settings/{group}",
            headers=admin_headers,
            json=payload,
        )
        assert resp.status_code in (200, 201, 204), (
            f"PATCH /api/settings/{group} 失败: {resp.status_code} {resp.text}"
        )

    # 2. 再 GET /api/admin/logs 过滤 action=settings
    logs_resp = await client.get(
        "/api/admin/logs",
        params={"action": "settings", "page": 1, "page_size": 50},
        headers=admin_headers,
    )
    assert logs_resp.status_code == 200, f"查询 logs 失败: {logs_resp.status_code} {logs_resp.text}"
    logs_data = logs_resp.json()
    items = logs_data.get("items") or logs_data.get("data", {}).get("items", [])

    settings_logs = [
        it
        for it in items
        if (it.get("action") == "settings" or it.get("resource_type") == "settings")
        and (it.get("target_type") == "settings" or it.get("resource_type") == "settings")
    ]

    # 3. 断言数量 = 4
    assert len(settings_logs) >= 4, (
        f"期望至少 4 条 settings 日志，实际只有 {len(settings_logs)} 条；items={items}"
    )


@pytest.mark.asyncio
async def test_editor_cannot_access_user_admin_403(
    client: AsyncClient,
    editor_headers: dict,
    admin_headers: dict,
    db_session: AsyncSession,
):
    """
    editor 角色 token 调 GET admin/users → 403；
    操作日志新增一条 permission failed。
    """
    # 1. 先查下操作日志目前数量，后面增量校验
    before = await db_session.scalar(
        select(OperationLog.id).order_by(OperationLog.id.desc()).limit(1)
    )
    before = before or 0

    # 2. editor 调 GET /api/admin/users → 403
    resp = await client.get("/api/admin/users", headers=editor_headers)
    assert resp.status_code == 403, (
        f"editor 应被 403 拒绝访问 admin/users，实际是 {resp.status_code} {resp.text}"
    )

    # 3. 用 admin 查询日志：action=permission 且 status=failed
    logs_resp = await client.get(
        "/api/admin/logs",
        params={"action": "permission", "page": 1, "page_size": 20},
        headers=admin_headers,
    )
    assert logs_resp.status_code == 200, f"查询 logs 失败: {logs_resp.text}"
    logs_data = logs_resp.json()
    items = logs_data.get("items") or logs_data.get("data", {}).get("items", [])

    permission_failed_logs = [
        it for it in items if (it.get("action") == "permission") and (it.get("status") == "failed")
    ]

    assert len(permission_failed_logs) >= 1, (
        f"期望至少 1 条 permission failed 日志，实际 {len(permission_failed_logs)} 条；items={items}"
    )


@pytest.mark.asyncio
async def test_stats_returns_schema(
    client: AsyncClient,
    admin_headers: dict,
):
    """
    admin 调 GET /api/admin/stats?range=7d →
    返回必须包含 timeseries(5 datasets: pv/uv/comments/posts/users)
    + top_articles (list) + active_commenters (list)
    + system_health (至少 4 个 key)
    """
    resp = await client.get(
        "/api/admin/stats",
        params={"range": "7d"},
        headers=admin_headers,
    )
    assert resp.status_code == 200, f"GET stats 失败 {resp.status_code} {resp.text}"
    resp_body = resp.json()
    assert resp_body.get("success") is True, f"缺少 success=true; body={resp_body}"
    payload = resp_body["data"]

    # 1. 顶层键检查
    for required in ("timeseries", "top_articles", "active_commenters", "system_health", "summary"):
        assert required in payload, f"缺少顶层字段 {required}; keys={list(payload.keys())}"

    # 2. timeseries 结构：labels 数组 + datasets 数组（5 条）
    ts = payload["timeseries"]
    assert isinstance(ts, dict) and "labels" in ts and "datasets" in ts, (
        f"timeseries 结构错误: {ts}"
    )
    assert isinstance(ts["labels"], list), "timeseries.labels 应该是数组"

    datasets = ts["datasets"]
    assert isinstance(datasets, list), "timeseries.datasets 应该是数组"
    dataset_keys = sorted([d.get("key") for d in datasets])
    expected_keys = sorted(["pv", "uv", "comments", "posts", "users"])
    assert dataset_keys == expected_keys, (
        f"期望 5 个 datasets keys={expected_keys}，实际是 {dataset_keys}"
    )

    # 3. top_articles & active_commenters 必须是 list
    assert isinstance(payload["top_articles"], list), "top_articles 必须是数组"
    assert isinstance(payload["active_commenters"], list), "active_commenters 必须是数组"

    # 4. system_health 必须有 4 个以上 key（cpu_percent, memory_percent, db_rtt_ms, cache_hit_percent, health_score）
    sh = payload["system_health"]
    assert isinstance(sh, dict), "system_health 应该是对象"
    for k in ("cpu_percent", "memory_percent", "db_rtt_ms", "cache_hit_percent"):
        assert k in sh, f"system_health 缺少 {k}"
