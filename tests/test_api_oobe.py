"""
OOBE (Out-of-Box Experience) API 测试

包含：
- test_oobe_flow_clean_env: 完整安装流程 + 幂等 409 验证
- test_oobe_required_before_install: 安装前访问受保护 API 返回 503 + OOBE_REQUIRED
- test_oobe_reset_and_retrigger: 完成后 reset，再重新安装成功
- test_oobe_admin_weak_password: 密码<8位返回 422
"""

from collections.abc import AsyncGenerator
from pathlib import Path

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

import sys

import backend.api.oobe as _oobe
import backend.core.deps as _deps
import backend.core.paths as _paths
from backend.core.setup_config import ConfigService
from backend.main import create_application

BASE_DIR = Path(__file__).resolve().parent.parent
ROSETTA_JSON = BASE_DIR / "rosetta.json"
OOBE_COMPLETE = BASE_DIR / ".oobe_complete"
OOBE_STATE = BASE_DIR / ".oobe_state.json"
ENV_FILE = BASE_DIR / ".env"

DEFAULT_INSTALL_PAYLOAD = {
    "database_type": "sqlite",
    "db_path": "rosetta_oobe_test.db",
    "db_host": "localhost",
    "db_port": 5432,
    "db_name": "rosetta",
    "db_user": "",
    "db_password": "",
    "redis_enabled": False,
    "redis_host": "localhost",
    "redis_port": 6379,
    "redis_password": "",
    "admin_username": "oobeadmin",
    "admin_email": "oobeadmin@example.com",
    "admin_password": "Str0ngP@ss",
    "admin_nickname": "OOBE管理员",
    "site_name": "Rosetta Test Site",
    "site_description": "Rosetta OOBE Test",
    "site_url": "http://localhost:4321",
    "site_keywords": "blog, rosetta, test",
    "site_author": "OOBE Author",
    "site_email": "hello@example.com",
    "enable_comments": False,
    "enable_registration": False,
    "enable_rss": False,
    "enable_bing_wallpaper": False,
    "enable_pagefind_search": False,
    "enable_encrypted_posts": False,
    "enable_music_player": False,
    "environment": "development",
}


def _safe_unlink(p: Path):
    try:
        if p.exists():
            p.unlink()
    except Exception:
        pass


@pytest_asyncio.fixture(scope="function")
async def oobe_client(monkeypatch, tmp_path) -> AsyncGenerator[AsyncClient, None]:
    """OOBE 专用测试客户端。

    将 OOBE 状态文件重定向到 tmp_path，原因有二：
    1. 仓库目录下的删除会被 safe-delete 拦截（windows 回收站不可用 → fail-closed），
       导致 fixture 无法清理标记文件、测试间状态泄漏；
    2. tmp 路径在 safe-delete 白名单内走原生删除，天然隔离且不污染仓库。
    """
    tmp_cfg = tmp_path / "rosetta.json"
    tmp_lock = tmp_path / "oobe_complete"
    tmp_state = tmp_path / ".oobe_state.json"
    tmp_env = tmp_path / ".env"
    tmp_db = tmp_path / "rosetta_oobe_test.db"

    for name, val in [
        ("CONFIG_FILE", tmp_cfg),
        ("OOBE_LOCK_FILE", tmp_lock),
        ("STATE_FILE", tmp_state),
        ("ENV_FILE", tmp_env),
    ]:
        monkeypatch.setattr(_paths, name, val)
    # oobe_middleware 通过 deps.is_oobe_complete 读取这两个模块级常量
    monkeypatch.setattr(_deps, "CONFIG_FILE", tmp_cfg)
    monkeypatch.setattr(_deps, "OOBE_LOCK_FILE", tmp_lock)
    # oobe.py 模块级导入的常量与 config_service 实例
    monkeypatch.setattr(_oobe, "CONFIG_FILE", tmp_cfg)
    monkeypatch.setattr(_oobe, "OOBE_LOCK_FILE", tmp_lock)
    monkeypatch.setattr(_oobe, "STATE_FILE", tmp_state)
    monkeypatch.setattr(_oobe, "ENV_FILE", tmp_env)
    monkeypatch.setattr(_oobe, "config_service", ConfigService())
    # 安装用的数据库也落在 tmp，避免仓库内残留
    monkeypatch.setitem(DEFAULT_INSTALL_PAYLOAD, "db_path", str(tmp_db))

    # 测试断言使用的全局常量同步重定向到 tmp
    self_mod = sys.modules[__name__]
    monkeypatch.setattr(self_mod, "ROSETTA_JSON", tmp_cfg)
    monkeypatch.setattr(self_mod, "OOBE_COMPLETE", tmp_lock)
    monkeypatch.setattr(self_mod, "OOBE_STATE", tmp_state)
    monkeypatch.setattr(self_mod, "ENV_FILE", tmp_env)

    for p in (tmp_cfg, tmp_lock, tmp_state, tmp_env, tmp_db):
        _safe_unlink(p)

    app = create_application()

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as ac:
        yield ac

    try:
        await ac.aclose()
    except Exception:
        pass
    for p in (tmp_cfg, tmp_lock, tmp_state, tmp_env, tmp_db):
        _safe_unlink(p)


@pytest.mark.asyncio
async def test_oobe_flow_clean_env(oobe_client: AsyncClient):
    """完整安装流程：reset → check → install 成功 → GET posts 有 Hello World → 管理员登录成功 → 再次 install 409"""
    r = await oobe_client.post("/api/oobe/reset")
    assert r.status_code == 200, r.text
    assert r.json()["success"] is True

    r = await oobe_client.get("/api/oobe/check")
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["success"] is True
    assert "python_version" in data
    assert "uv_installed" in data
    assert "node_version" in data
    assert "pnpm_version" in data
    assert "database_connectivity" in data
    assert "redis_connectivity" in data
    assert "disk_free_gb" in data
    assert "memory_free_mb" in data
    assert isinstance(data["python_version"], dict)
    assert "ok" in data["python_version"]
    assert isinstance(data["uv_installed"], dict)
    assert "ok" in data["uv_installed"]

    r = await oobe_client.post("/api/oobe/install", json=DEFAULT_INSTALL_PAYLOAD)
    assert r.status_code == 200, r.text
    j = r.json()
    assert j["success"] is True
    assert "frontend_url" in j
    assert "admin_url" in j

    assert OOBE_COMPLETE.exists()
    assert ROSETTA_JSON.exists()

    r = await oobe_client.get("/api/blog/posts")
    assert r.status_code == 200, r.text
    posts = r.json()
    items = posts.get("items") or posts.get("data") or (posts if isinstance(posts, list) else [])
    if isinstance(posts, dict) and "items" in posts:
        items = posts["items"]
    elif isinstance(posts, dict) and "data" in posts:
        items = posts["data"]
    else:
        items = posts if isinstance(posts, list) else []
    assert len(items) >= 1, f"至少应有 1 篇种子文章，实际 {len(items)}"
    slugs = [p.get("slug") for p in items if isinstance(p, dict)]
    # 兼容两种 OOBE 造数方式：老版本生成 Hello World，新版本随机 AI 造名 → 只要 slug 数量 ok 就通过
    # 同时要求至少 1 篇 slug 非空
    assert any(s for s in slugs), f"种子文章 slug 全为空，实际={slugs}"

    r = await oobe_client.post(
        "/api/users/login",
        json={
            "username": DEFAULT_INSTALL_PAYLOAD["admin_username"],
            "password": DEFAULT_INSTALL_PAYLOAD["admin_password"],
        },
    )
    assert r.status_code == 200, r.text
    login = r.json()
    assert login.get("success") is True or ("access_token" in login)
    token = login.get("access_token")
    assert token, f"未返回 access_token: {login}"

    me_headers = {"Authorization": f"Bearer {token}"}
    r = await oobe_client.get("/api/users/me", headers=me_headers)
    assert r.status_code == 200, r.text

    r = await oobe_client.post("/api/oobe/install", json=DEFAULT_INSTALL_PAYLOAD)
    assert r.status_code == 409, f"重复调用 install 应返回 409，实际 {r.status_code}: {r.text}"
    j = r.json()
    assert j.get("error_code") == "OOBE_ALREADY_COMPLETED", (
        f"error_code 应为 OOBE_ALREADY_COMPLETED，实际 {j}"
    )


@pytest.mark.asyncio
async def test_oobe_required_before_install(oobe_client: AsyncClient):
    """安装前直接访问受保护的 /api/users/me 期望 503 + error_code OOBE_REQUIRED"""
    r = await oobe_client.post("/api/oobe/reset")
    assert r.status_code == 200

    r = await oobe_client.get("/api/users/me")
    assert r.status_code == 503, (
        f"安装前访问 /api/users/me 应返回 503，实际 {r.status_code}: {r.text}"
    )
    j = r.json()
    assert j.get("error_code") == "OOBE_REQUIRED", f"error_code 应为 OOBE_REQUIRED，实际 {j}"

    r = await oobe_client.get("/api/oobe/status")
    assert r.status_code == 200, f"/api/oobe/status 应始终放行，实际 {r.status_code}"

    r = await oobe_client.get("/api/captcha/image")
    assert r.status_code != 503, f"/api/captcha/* 应放行，实际 {r.status_code}"


@pytest.mark.asyncio
async def test_oobe_reset_and_retrigger(oobe_client: AsyncClient):
    """完成后 reset，再 POST install 能重新成功（幂等回退）"""
    r = await oobe_client.post("/api/oobe/install", json=DEFAULT_INSTALL_PAYLOAD)
    assert r.status_code == 200, r.text
    assert OOBE_COMPLETE.exists()

    r = await oobe_client.post("/api/oobe/install", json=DEFAULT_INSTALL_PAYLOAD)
    assert r.status_code == 409, r.text

    r = await oobe_client.post("/api/oobe/reset")
    assert r.status_code == 200, r.text
    assert not OOBE_COMPLETE.exists()
    assert not ROSETTA_JSON.exists()

    r = await oobe_client.post("/api/oobe/install", json=DEFAULT_INSTALL_PAYLOAD)
    assert r.status_code == 200, f"reset 后重新 install 应成功，实际 {r.status_code}: {r.text}"
    j = r.json()
    assert j["success"] is True
    assert OOBE_COMPLETE.exists()

    r = await oobe_client.get("/api/blog/posts")
    assert r.status_code == 200, r.text


@pytest.mark.asyncio
async def test_oobe_admin_weak_password(oobe_client: AsyncClient):
    """POST install 用 admin_password='123456'，期望 422 (验证失败)"""
    await oobe_client.post("/api/oobe/reset")

    weak_payload = {**DEFAULT_INSTALL_PAYLOAD, "admin_password": "123456"}
    r = await oobe_client.post("/api/oobe/install", json=weak_payload)
    assert r.status_code == 422, f"弱密码应返回 422，实际 {r.status_code}: {r.text}"
    assert not OOBE_COMPLETE.exists(), "弱密码时不应写入 OOBE 完成标记"
