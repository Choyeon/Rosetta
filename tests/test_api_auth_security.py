"""
认证体系安全测试 - Task 4
"""

import pytest
import pytest_asyncio
from httpx import AsyncClient

from backend.core.auth import _MEMORY_BLACKLIST_LOCK, MEMORY_REFRESH_BLACKLIST


@pytest_asyncio.fixture(autouse=True)
async def _setup(monkeypatch, tmp_path):
    """
    每轮测试前：
      1. 清空内存 refresh 黑名单
      2. 标记 OOBE 已完成（绕过安装向导）
      3. 放宽速率限制，避免暴力破解测试被 429 拦截
         - 直接修改 SENSITIVE_ENDPOINT_RULE / WRITE_ENDPOINT_RULE 对象的 requests
           因为 rule 对象是在模块 import 时基于 settings 构建一次，仅改 settings 不生效
         - 清空 rate_limiter._memory_store 确保跨测试无残留计数
    """
    async with _MEMORY_BLACKLIST_LOCK:
        MEMORY_REFRESH_BLACKLIST.clear()

    from backend.core import config as _cfg
    from backend.core import deps as _deps
    from backend.core.rate_limit import (
        SENSITIVE_ENDPOINT_RULE,
        WRITE_ENDPOINT_RULE,
        login_rate_limiter,
        rate_limiter,
    )

    # 清空限流器内存存储
    try:
        rate_limiter._memory_store.clear()
    except Exception:
        pass
    try:
        # login_rate_limiter 可能是 redis 或内存实现，尽力清
        if hasattr(login_rate_limiter, "_memory_attempts"):
            login_rate_limiter._memory_attempts.clear()  # type: ignore[attr-defined]
    except Exception:
        pass

    lock_file = tmp_path / ".oobe_complete"
    cfg_file = tmp_path / "rosetta.json"
    lock_file.write_text("1", encoding="utf-8")
    cfg_file.write_text("{}", encoding="utf-8")

    monkeypatch.setattr(_deps, "OOBE_LOCK_FILE", lock_file)
    monkeypatch.setattr(_deps, "CONFIG_FILE", cfg_file)

    # 放宽速率限制到 1000/分钟：修改 rule 对象本身的字段
    monkeypatch.setattr(SENSITIVE_ENDPOINT_RULE, "requests", 1000)
    monkeypatch.setattr(WRITE_ENDPOINT_RULE, "requests", 1000)
    # 同时同步 settings 值（代码的其他地方可能读 settings）
    monkeypatch.setattr(_cfg.settings, "rate_limit_sensitive_requests", 1000)
    monkeypatch.setattr(_cfg.settings, "rate_limit_write_requests", 1000)

    # 终极保险：让通用 rate_limiter.check_rate_limit 永远放行；暴力锁定逻辑走 login_rate_limiter（独立代码路径）
    # 这样不会因为 10+ 次的连续登录/重置密码请求而被通用 429 拦，
    # 只留下真正要测试的 login_rate_limiter 的 423 锁定。
    from backend.core.rate_limit import RateLimitResult

    async def _always_allowed_check(*args, **kwargs):
        import time

        return RateLimitResult(
            allowed=True,
            remaining=999_999,
            reset_at=time.time() + 3600,
            retry_after=0,
        )

    monkeypatch.setattr(rate_limiter, "check_rate_limit", _always_allowed_check)
    yield


def _err_code(body: dict) -> str | None:
    """从响应 body 中取出业务 error_code（适配 main.py 的全局异常包装格式）"""
    msg = body.get("message")
    if isinstance(msg, dict):
        return msg.get("error_code")
    return None


def _err_errors(body: dict) -> list[str]:
    """取出业务 errors 列表（中文）"""
    msg = body.get("message")
    if isinstance(msg, dict):
        return msg.get("errors") or []
    return []


@pytest.mark.asyncio
async def test_refresh_token_single_use(
    client: AsyncClient,
    test_user,
):
    """登录 → refresh 成功 → 再次用同一个 refresh → 401 TOKEN_REUSED"""
    r_login = await client.post(
        "/api/users/login",
        json={"username": "testuser", "password": "Testpass123"},
    )
    assert r_login.status_code == 200, r_login.text
    login_data = r_login.json()
    refresh_1 = login_data["refresh_token"]
    assert login_data.get("access_token")
    assert login_data.get("refresh_token")

    r1 = await client.post("/api/users/refresh", json={"refresh_token": refresh_1})
    assert r1.status_code == 200, r1.text
    d1 = r1.json()
    assert "access_token" in d1
    assert d1.get("refresh_token") and d1["refresh_token"] != refresh_1

    r2 = await client.post("/api/users/refresh", json={"refresh_token": refresh_1})
    assert r2.status_code == 401, r2.text
    body = r2.json()
    assert _err_code(body) == "TOKEN_REUSED", body


@pytest.mark.asyncio
async def test_password_change_invalidates_refresh(
    client: AsyncClient,
    test_user,
):
    """登录得 R1 → 修改密码 → 用 R1 refresh → 401 TOKEN_VERSION_MISMATCH"""
    r_login = await client.post(
        "/api/users/login",
        json={"username": "testuser", "password": "Testpass123"},
    )
    assert r_login.status_code == 200, r_login.text
    login_data = r_login.json()
    access = login_data["access_token"]
    refresh_1 = login_data["refresh_token"]

    r_pwd = await client.post(
        "/api/users/me/password",
        headers={"Authorization": f"Bearer {access}"},
        json={"old_password": "Testpass123", "new_password": "Newpass456"},
    )
    assert r_pwd.status_code == 200, r_pwd.text

    r_ref = await client.post("/api/users/refresh", json={"refresh_token": refresh_1})
    assert r_ref.status_code == 401, r_ref.text
    body = r_ref.json()
    assert _err_code(body) == "TOKEN_VERSION_MISMATCH", body


@pytest.mark.asyncio
async def test_login_brute_force_lockout(
    client: AsyncClient,
    test_user,
):
    """循环 10 次错误密码 → 第 11 次（无论对错）423 ACCOUNT_LOCKED"""
    for i in range(10):
        r = await client.post(
            "/api/users/login",
            json={"username": "testuser", "password": f"Wrongpass{i}"},
        )
        assert r.status_code == 401, (
            f"第 {i + 1} 次错误密码应返回 401, got {r.status_code}: {r.text}"
        )

    # 第 11 次 → 锁定
    r = await client.post(
        "/api/users/login",
        json={"username": "testuser", "password": "Testpass123"},
    )
    assert r.status_code == 423, f"第 11 次尝试应 423, got {r.status_code}: {r.text}"
    body = r.json()
    assert _err_code(body) == "ACCOUNT_LOCKED", body

    retry_after = r.headers.get("Retry-After")
    assert retry_after is not None and int(retry_after) > 0


@pytest.mark.asyncio
async def test_weak_password_rejected(
    client: AsyncClient,
):
    """
    注册密码为常见弱密码 → 422 + 中文错误

    注意：只使用长度 >= 8 的密码，避免被 pydantic min_length=8 拦截。
    弱密码可能在 Pydantic model validator 或 endpoint 层被拦截，两者都返回 422
    但格式不同；本测试主要校验：422 状态码 + 含中文错误消息。
    """
    for weak_pw in ("password", "12345678"):
        r = await client.post(
            "/api/users/register",
            json={
                "username": f"u_{weak_pw}",
                "email": f"{weak_pw}@example.com",
                "password": weak_pw,
                "nickname": weak_pw,
            },
        )
        assert r.status_code == 422, f"弱密码 {weak_pw!r} 应 422，实际 {r.status_code}: {r.text}"
        body = r.json()
        # 两种格式都接受：1) HTTPException wrapper: success=False, message={error_code,errors,...}
        #               2) pydantic validation error: success=False, message=xxx, errors=[{field,message}]
        ec = _err_code(body)
        errs = _err_errors(body)
        alt_errs = body.get("errors") or []
        if ec == "WEAK_PASSWORD":
            # endpoint 层格式：应当有中文 errors
            assert isinstance(errs, list) and len(errs) > 0, body
            has_cn = any("\u4e00" <= ch <= "\u9fff" for e in errs for ch in e)
            assert has_cn, f"应包含中文错误，errors={errs}"
        else:
            # pydantic validator 格式：alt_errs 里有 field-level message
            assert isinstance(alt_errs, list) and len(alt_errs) > 0, body
            # 任意字段 message 中必须有中文
            any_msg = [str(e.get("message", "")) for e in alt_errs if isinstance(e, dict)]
            has_cn = any("\u4e00" <= ch <= "\u9fff" for m in any_msg for ch in m)
            assert has_cn, f"应包含中文错误，errors={alt_errs}"


@pytest.mark.asyncio
async def test_password_reset_flow(
    client: AsyncClient,
    test_user,
    monkeypatch,
):
    """debug=true 调 reset-request 拿 code+token → 重置密码 → 新密码成功，旧密码失败

    由于测试环境禁用 Redis，对 backend.api.users 中的 cache 模块的 set/get 提供内存兜底。
    """
    from backend.core import config as _cfg
    # --- 内存 fake cache key-value store (用于 password_reset 存 code/token) ---
    _fake_store: dict[str, object] = {}
    import backend.api.users as _u_mod

    class _FakeCache:
        @staticmethod
        async def set(key: str, value: object, ttl: int = 0) -> None:
            _fake_store[key] = value

        @staticmethod
        async def get(key: str) -> object | None:
            return _fake_store.get(key)

    monkeypatch.setattr(_u_mod, "cache", _FakeCache())

    monkeypatch.setattr(_cfg.settings, "debug", True)

    # Step 1: password-reset-request
    r_req = await client.post(
        "/api/users/password-reset-request",
        json={"email_or_username": "testuser"},
    )
    assert r_req.status_code == 200, r_req.text
    body = r_req.json()
    debug = body.get("debug") or {}
    code = debug.get("reset_code")
    token = debug.get("reset_token")
    assert code and len(code) == 6, f"调试模式下应返回 6 位 code, body={body}"
    assert token and len(token) >= 32, f"调试模式下应返回 32+ 位 token, body={body}"

    # Step 2: 故意弱密码提交 → 拒绝 WEAK_PASSWORD
    r_weak = await client.post(
        "/api/users/password-reset",
        json={
            "token_or_email": "testuser",
            "code": code,
            "new_password": "password",
        },
    )
    assert r_weak.status_code == 422, f"弱密码重置应 422，got {r_weak.status_code}: {r_weak.text}"
    body2 = r_weak.json()
    assert _err_code(body2) == "WEAK_PASSWORD", body2

    # Step 3: 强密码重置成功
    r_reset = await client.post(
        "/api/users/password-reset",
        json={
            "token_or_email": "testuser",
            "code": code,
            "new_password": "Resetpass789",
        },
    )
    assert r_reset.status_code == 200, f"密码重置应 200，got {r_reset.status_code}: {r_reset.text}"

    # Step 4: 新密码登录成功
    r_new_login = await client.post(
        "/api/users/login",
        json={"username": "testuser", "password": "Resetpass789"},
    )
    assert r_new_login.status_code == 200, (
        f"新密码登录应成功，got {r_new_login.status_code}: {r_new_login.text}"
    )

    # Step 5: 旧密码登录失败
    r_old_login = await client.post(
        "/api/users/login",
        json={"username": "testuser", "password": "Testpass123"},
    )
    assert r_old_login.status_code == 401, (
        f"旧密码登录应失败，got {r_old_login.status_code}: {r_old_login.text}"
    )
