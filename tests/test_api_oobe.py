"""
OOBE (Out-of-Box Experience) API 测试

包含：
- test_oobe_flow_clean_env: 完整安装流程 + 幂等 409 验证
- test_oobe_required_before_install: 安装前访问受保护 API 返回 503 + OOBE_REQUIRED
- test_oobe_reset_and_retrigger: 完成后 reset，再重新安装成功
- test_oobe_admin_weak_password: 密码<8位返回 422
"""

import sys
from collections.abc import AsyncGenerator
from pathlib import Path

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

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

    # 快照全局 settings 与数据库引擎：
    # install 流程会通过 _refresh_settings_inplace() 原地改写全局 settings，
    # 并通过 reset_engine() 原地改写 async_session_maker 的 bind。
    # 若不在 teardown 还原，这些泄漏会污染后续所有测试文件（曾导致
    # test_password_reset_flow 的 debug 回传断言失败）。
    import backend.core.config as _config_mod
    import backend.core.database as _db_mod

    _settings_snapshot = dict(_config_mod.settings.__dict__)
    _engine_snapshot = _db_mod.async_session_maker.kw.get("bind")

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

    # --- 还原全局状态（顺序：先 settings 再缓存清理） ---
    try:
        _config_mod.settings.__dict__.clear()
        _config_mod.settings.__dict__.update(_settings_snapshot)
    except Exception:
        pass
    try:
        if hasattr(_config_mod.get_settings, "cache_clear"):
            _config_mod.get_settings.cache_clear()
    except Exception:
        pass
    try:
        _db_mod.async_session_maker.kw["bind"] = _engine_snapshot
        _db_mod.engine = _engine_snapshot
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

    # OOBE 向导页背景壁纸依赖 /api/bing/*（服务端 Bing 中继，无凭据、域名白名单）。
    # 不放行则向导只能直连 bing.com 被 CORS 拦死。该端点离线时也返回 200 占位。
    r = await oobe_client.get("/api/bing/wallpapers", params={"n": 1, "market": "zh-CN"})
    assert r.status_code == 200, (
        f"安装前 /api/bing/wallpapers 应放行，实际 {r.status_code}: {r.text}"
    )


@pytest.mark.asyncio
async def test_oobe_reset_and_retrigger(oobe_client: AsyncClient):
    """完成后 reset，再 POST install 能重新成功（幂等回退）"""
    r = await oobe_client.post("/api/oobe/install", json=DEFAULT_INSTALL_PAYLOAD)
    assert r.status_code == 200, r.text
    assert OOBE_COMPLETE.exists()

    r = await oobe_client.post("/api/oobe/install", json=DEFAULT_INSTALL_PAYLOAD)
    assert r.status_code == 409, r.text

    # 安装完成后 reset 属高危操作：匿名请求应被拒绝（403）
    r = await oobe_client.post("/api/oobe/reset")
    assert r.status_code == 403, f"匿名 reset 已安装站点应 403，实际 {r.status_code}"

    # 用安装时创建的超管登录后 reset 应成功
    r_login = await oobe_client.post(
        "/api/users/login",
        json={
            "username": DEFAULT_INSTALL_PAYLOAD["admin_username"],
            "password": DEFAULT_INSTALL_PAYLOAD["admin_password"],
        },
    )
    assert r_login.status_code == 200, r_login.text
    token = r_login.json().get("access_token")
    assert token

    r = await oobe_client.post("/api/oobe/reset", headers={"Authorization": f"Bearer {token}"})
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


@pytest.mark.asyncio
async def test_oobe_legacy_complete_endpoint_removed(oobe_client: AsyncClient):
    """旧分步式 `POST /api/oobe/complete` 已下线：向导只认 `POST /api/oobe/install`。

    该端点自标注 deprecated 且前后端零调用，保留等于留一份和真安装流程
    并行的第二套初始化实现（两者行为早已漂移）。钉住 404 防止被"顺手恢复"。
    """
    await oobe_client.post("/api/oobe/reset")

    r = await oobe_client.post("/api/oobe/complete")
    assert r.status_code == 404, f"/oobe/complete 应已下线，实际 {r.status_code}: {r.text}"
    assert not OOBE_COMPLETE.exists(), "下线的端点不应产生任何安装副作用"


def test_reset_oobe_reports_undeletable_files(tmp_path, monkeypatch):
    """`reset_oobe` 必须逐个删除并回报失败项，而不是整体 `except: pass` 后假装成功。

    半完成态是这里最坏的结果：安装锁已删而带 SECRET_KEY/DB 连接串的 .env 还在，
    调用方却收到"成功"。同时验证单项失败不会中断其余文件的删除。
    """
    svc = ConfigService()
    paths = {
        "lock": tmp_path / ".oobe_complete",
        "env": tmp_path / ".env",
        "config": tmp_path / "rosetta.json",
        "state": tmp_path / "oobe_state.json",
    }
    for p in paths.values():
        p.write_text("placeholder", encoding="utf-8")
    monkeypatch.setattr(svc, "lock_file", paths["lock"])
    monkeypatch.setattr(svc, "env_file", paths["env"])
    monkeypatch.setattr(svc, "config_file", paths["config"])
    monkeypatch.setattr(svc, "state_file", paths["state"])

    real_unlink = Path.unlink

    def flaky_unlink(self, *args, **kwargs):
        if self.name == ".env":
            raise PermissionError("simulated read-only .env")
        return real_unlink(self, *args, **kwargs)

    monkeypatch.setattr(Path, "unlink", flaky_unlink)

    failed = svc.reset_oobe()

    assert failed == ["env"], f"只应回报无法删除的 env，实际={failed}"
    assert not paths["lock"].exists(), "单项失败不得中断其余文件删除（锁必须被删）"
    assert not paths["config"].exists() and not paths["state"].exists()
    assert paths["env"].exists(), ".env 仍应存在，供调用方上报"


@pytest.mark.asyncio
async def test_oobe_reset_fails_closed_on_leftover(oobe_client: AsyncClient, monkeypatch):
    """重置未清干净时 `POST /oobe/reset` 必须回 5xx，不能回 200 让前端以为可重跑向导"""
    monkeypatch.setattr(_oobe.config_service, "reset_oobe", lambda: ["env"])

    r = await oobe_client.post("/api/oobe/reset")

    assert r.status_code == 500, f"残留文件应显式失败，实际 {r.status_code}: {r.text}"
    assert "env" in r.text


# ============================= 安装请求默认值红线 =============================

# 这些字符串是本项目作者的真实个人信息，曾经作为 CombinedInstallRequest 的默认值存在。
# OOBE 安装端点是**匿名**可调用的，默认值会进 OpenAPI schema（/docs、/openapi.json 可读），
# 等于把作者的个人联系方式随每个发行版一起公开，并且会被写进每一个用默认参数装出来的站点。
_PERSONAL_DATA_MARKERS = ("952223950", "rosetta.choyeon.cc", "Choyeon")


def test_install_request_has_no_personal_data_defaults():
    """CombinedInstallRequest 的默认值里不得出现作者个人信息。"""
    from backend.api.oobe import CombinedInstallRequest

    for name, field in CombinedInstallRequest.model_fields.items():
        if field.is_required():
            continue
        blob = repr(field.default)
        for marker in _PERSONAL_DATA_MARKERS:
            assert marker not in blob, (
                f"CombinedInstallRequest.{name} 的默认值含个人信息 {marker!r}：{blob}"
            )


def test_site_url_is_required():
    """site_url 必填：省略时会指向别人的域名，且 RSS/sitemap 的绝对地址全错。"""
    from pydantic import ValidationError

    from backend.api.oobe import CombinedInstallRequest

    base = {
        "admin_username": "admin",
        "admin_email": "admin@example.com",
        "admin_password": "StrongPass123",
    }
    with pytest.raises(ValidationError):
        CombinedInstallRequest(**base)

    ok = CombinedInstallRequest(**base, site_url="https://example.com")
    assert ok.site_url == "https://example.com"


def test_admin_optional_profile_defaults_to_empty():
    """管理员扩展资料默认空串，由安装者决定填什么。"""
    from backend.api.oobe import CombinedInstallRequest

    req = CombinedInstallRequest(
        admin_username="admin",
        admin_email="admin@example.com",
        admin_password="StrongPass123",
        site_url="https://example.com",
    )
    assert req.admin_nickname == ""
    assert req.admin_bio == ""
    assert req.admin_qq == ""
    assert req.admin_github == ""
    assert req.admin_website == ""


# ============================= 安装请求强校验（与 /oobe/preflight 同口径） =============================
# 背景：同一批字段曾经有两套规则 —— `GET /oobe/check-username` 校验字符集，
# 但 `POST /oobe/install` 只判断 `len(password) >= 8`，用户名/邮箱/站点地址一律放行。
# 后果是向导本地校验说"通过"、提交后被 422 弹回，用户不知道是哪一格错了。


@pytest.mark.parametrize(
    "bad_username",
    ["ab", "a b", "管理员", "admin@x", "x" * 21, "admin;drop"],
)
@pytest.mark.asyncio
async def test_install_rejects_bad_username_charset(oobe_client: AsyncClient, bad_username: str):
    """用户名字符集/长度不合法 → 422，且不产生任何安装副作用。"""
    payload = {**DEFAULT_INSTALL_PAYLOAD, "admin_username": bad_username}
    r = await oobe_client.post("/api/oobe/install", json=payload)
    assert r.status_code == 422, f"{bad_username!r} 应被拒，实际 {r.status_code}: {r.text}"
    assert not OOBE_COMPLETE.exists(), "校验失败时不得落安装锁"


@pytest.mark.asyncio
async def test_install_rejects_bad_email(oobe_client: AsyncClient):
    payload = {**DEFAULT_INSTALL_PAYLOAD, "admin_email": "not-an-email"}
    r = await oobe_client.post("/api/oobe/install", json=payload)
    assert r.status_code == 422, r.text
    assert not OOBE_COMPLETE.exists()


@pytest.mark.parametrize("bad_url", ["example.com", "ftp://example.com", "//example.com", ""])
@pytest.mark.asyncio
async def test_install_rejects_bad_site_url(oobe_client: AsyncClient, bad_url: str):
    """站点地址必须带 http(s):// —— 它会被写进 SiteConfig 用于拼 RSS / sitemap 绝对地址。"""
    payload = {**DEFAULT_INSTALL_PAYLOAD, "site_url": bad_url}
    r = await oobe_client.post("/api/oobe/install", json=payload)
    assert r.status_code == 422, f"{bad_url!r} 应被拒，实际 {r.status_code}: {r.text}"


@pytest.mark.asyncio
async def test_install_uses_same_password_policy_as_registration(oobe_client: AsyncClient):
    """安装与注册必须共用一套口令策略。

    '12345678' 长度达标但缺大小写字母：注册路径会拒，安装路径以前只查 `len >= 8` 直接放行，
    等于给超管发了一个策略不允许的口令。
    """
    payload = {**DEFAULT_INSTALL_PAYLOAD, "admin_password": "12345678"}
    r = await oobe_client.post("/api/oobe/install", json=payload)
    assert r.status_code == 422, f"缺大小写的口令应被拒，实际 {r.status_code}: {r.text}"
    assert r.json().get("error_code") == "WEAK_PASSWORD", r.text
    assert not OOBE_COMPLETE.exists()


@pytest.mark.asyncio
async def test_install_strips_trailing_slash_from_site_url(oobe_client: AsyncClient):
    """site_url 末尾斜杠要被剥掉，否则拼出来是 https://x.com//admin。"""
    payload = {**DEFAULT_INSTALL_PAYLOAD, "site_url": "https://example.com/"}
    r = await oobe_client.post("/api/oobe/install", json=payload)
    assert r.status_code == 200, r.text
    j = r.json()
    assert j["admin_url"] == "https://example.com/admin", j
    assert j["frontend_url"] == "https://example.com", j


# ============================= POST /oobe/preflight（安装前干跑） =============================


@pytest.mark.asyncio
async def test_preflight_flags_every_bad_field(oobe_client: AsyncClient):
    """一次把四格错误全报出来，而不是让用户四轮试错。"""
    r = await oobe_client.post(
        "/api/oobe/preflight",
        json={
            "admin_username": "a b",
            "admin_email": "not-an-email",
            "admin_password": "12345678",
            "site_name": "   ",
            "site_url": "example.com",
            "database_type": "sqlite",
        },
    )
    assert r.status_code == 200, r.text
    j = r.json()
    assert j["ok"] is False
    codes = {i["code"] for i in j["issues"]}
    assert {"USERNAME_INVALID", "EMAIL_INVALID", "SITE_URL_INVALID", "SITE_NAME_EMPTY"} <= codes
    assert "PASSWORD_WEAK" in codes, f"缺大小写的口令应报 PASSWORD_WEAK，实际 {codes}"
    # 每条 error 都必须带 field，前端要靠它跳回对应步骤
    for issue in j["issues"]:
        assert issue["field"], issue
        assert issue["level"] in ("error", "warn"), issue


@pytest.mark.asyncio
async def test_preflight_all_green_returns_empty_issues(oobe_client: AsyncClient):
    r = await oobe_client.post(
        "/api/oobe/preflight",
        json={
            "admin_username": "oobeadmin",
            "admin_email": "admin@example.com",
            "admin_password": "Str0ngP@ss",
            "site_name": "Rosetta",
            "site_url": "https://example.com",
            "database_type": "sqlite",
            "db_path": "rosetta.db",
        },
    )
    assert r.status_code == 200, r.text
    j = r.json()
    assert j["ok"] is True, j
    assert j["issues"] == [], j


@pytest.mark.asyncio
async def test_preflight_is_read_only(oobe_client: AsyncClient):
    """预检必须零副作用：不落锁、不写配置、不建库、不建账号。

    前端会在离开 Step3 和点安装前各调一次，若它有写副作用，等于把安装入口
    变成一个可被匿名反复触发的写操作。
    """
    await oobe_client.post(
        "/api/oobe/preflight",
        json={
            "admin_username": "oobeadmin",
            "admin_email": "admin@example.com",
            "admin_password": "Str0ngP@ss",
            "site_name": "Rosetta",
            "site_url": "https://example.com",
            "database_type": "sqlite",
        },
    )
    assert not OOBE_COMPLETE.exists(), "预检不得落安装锁"
    assert not ROSETTA_JSON.exists(), "预检不得写站点配置"
    assert not ENV_FILE.exists(), "预检不得写 .env"


@pytest.mark.asyncio
async def test_preflight_http_url_warns_without_blocking(oobe_client: AsyncClient):
    """明文 HTTP 站点地址是风险提示，不是硬错误 —— 本地开发就是 http。"""
    r = await oobe_client.post(
        "/api/oobe/preflight",
        json={"site_url": "http://localhost:3000", "database_type": "sqlite"},
    )
    assert r.status_code == 200, r.text
    j = r.json()
    assert j["ok"] is True, "warn 不应阻断安装"
    assert any(i["code"] == "SITE_URL_INSECURE" and i["level"] == "warn" for i in j["issues"]), j


@pytest.mark.asyncio
async def test_preflight_postgresql_requires_credentials(oobe_client: AsyncClient):
    r = await oobe_client.post(
        "/api/oobe/preflight",
        json={"database_type": "postgresql", "check_database": True, "db_user": "", "db_name": ""},
    )
    assert r.status_code == 200, r.text
    j = r.json()
    assert j["ok"] is False
    codes = {i["code"] for i in j["issues"]}
    assert {"DB_USER_EMPTY", "DB_NAME_EMPTY"} <= codes, j


# ============================= POST /oobe/test-database（密码不进 query string） =============================


@pytest.mark.asyncio
async def test_test_database_post_sqlite_always_ok(oobe_client: AsyncClient):
    r = await oobe_client.post("/api/oobe/test-database", json={"db_type": "sqlite", "db_path": "x.db"})
    assert r.status_code == 200, r.text
    j = r.json()
    assert j["success"] is True
    assert j["code"] == "DB_OK"
    assert "code" in j and "hint" in j, "新响应体必须带结构化 code/hint"


@pytest.mark.asyncio
async def test_test_database_post_returns_structured_code_and_never_echoes_password(
    oobe_client: AsyncClient,
):
    """连不上时也要回 200 + 结构化错误码；口令绝不能出现在响应里。

    同路径的 GET 版本把 db_password 放在 query string —— 会被 Nginx/uvicorn/APM
    原样写进访问日志。这里钉钉 POST 的响应体同样不含口令。
    """
    r = await oobe_client.post(
        "/api/oobe/test-database",
        json={
            "db_type": "postgresql",
            "db_host": "127.0.0.1",
            "db_port": 1,
            "db_user": "probe_user",
            "db_password": "SUPERSECRET123",
            "db_name": "nope",
        },
    )
    assert r.status_code == 200, r.text
    j = r.json()
    assert "SUPERSECRET123" not in r.text, "响应体不得回显数据库口令"
    assert j["success"] is False
    assert j["code"].startswith("DB_"), j
    assert j["code"] != "DB_OK"


# ============================= 凭据脱敏与错误分类（纯函数） =============================


def test_scrub_database_url_masks_password_but_keeps_host():
    """脱敏要够用：口令抹掉，主机/库名保留（排查时需要知道连的是哪台机器）。"""
    from backend.core.setup_database import scrub_database_url

    s = scrub_database_url(
        "could not connect: postgresql+asyncpg://rosetta:S3cr3t@db.internal:5432/rosetta"
    )
    assert "S3cr3t" not in s
    assert "rosetta:***@db.internal:5432/rosetta" in s, s
    assert scrub_database_url(None) == ""
    assert scrub_database_url("plain text without url") == "plain text without url"


@pytest.mark.parametrize(
    ("raw", "expected_code"),
    [
        ("connection refused", "DB_UNREACHABLE"),
        ("[Errno 111] Connect call failed ('127.0.0.1', 5432)", "DB_UNREACHABLE"),
        ('password authentication failed for user "rosetta"', "DB_AUTH_FAILED"),
        ('role "rosetta" does not exist', "DB_AUTH_FAILED"),
        ('database "rosetta" does not exist', "DB_NOT_EXIST"),
        ("No module named 'asyncpg'", "DB_DRIVER_MISSING"),
        ("connection timed out", "DB_TIMEOUT"),
        ("something utterly unexpected", "DB_UNKNOWN"),
    ],
)
def test_classify_db_error_maps_known_failures(raw: str, expected_code: str):
    from backend.core.setup_database import classify_db_error

    code, message, hint = classify_db_error(raw)
    assert code == expected_code, f"{raw!r} → {code}（期望 {expected_code}）"
    assert message and hint, "每条分类都必须给人读的结论 + 可操作的下一步"


def test_classify_db_error_never_leaks_credentials():
    """asyncpg 的原始异常里会夹着完整 DSN（含口令），分类后必须已脱敏。"""
    from backend.core.setup_database import classify_db_error

    code, message, hint = classify_db_error(
        'password authentication failed for user "rosetta" '
        "(postgresql+asyncpg://rosetta:S3cr3t@db.internal:5432/rosetta)"
    )
    assert "S3cr3t" not in (code + message + hint)
