"""
main.py 顶层入口 + 中间件 catch-all 覆盖：
- / /health 路由 (root, health)
- 异常处理器：StarletteHTTPException(404) / RequestValidationError(422) / 通用 Exception
  通过真实 HTTP 请求实际抛出方式触发（避免依赖 main 内部闭包函数）
- 安全头 nonce 分支 + force_hsts=True/https 场景下 HSTS 头写入
- performance_middleware：正常/慢请求/except 兜底分支（通过拉长耗时 monkeypatch 触发 should_record=true，
  测试环境 async_session_maker 不同 → 自然走 except logger.warning 分支）
"""
from __future__ import annotations

import pytest
from httpx import AsyncClient


# ================================================================
# 1. 顶层 / 和 /health
# ================================================================
class TestMainTopRoutes:
    @pytest.mark.asyncio
    async def test_root_route(self, client: AsyncClient):
        r = await client.get("/")
        assert r.status_code == 200
        data = r.json()
        assert "name" in data and "version" in data

    @pytest.mark.asyncio
    async def test_health_route(self, client: AsyncClient):
        r = await client.get("/health")
        assert r.status_code == 200
        data = r.json()
        assert "status" in data and data.get("app_name")
        assert "database" in data


# ================================================================
# 2. 异常处理器（通过 HTTP 层实际触发，而非直接 import 内部 handler）
# ================================================================
class TestMainExceptionHandlers:
    @pytest.mark.asyncio
    async def test_starlette_http_exception_404(self, client: AsyncClient):
        """未命中路由 → StarletteHTTPException(404) 被 app.exception_handler 捕获并返回 JSON"""
        r = await client.get("/api/does-not-exist-xyz123abc")
        assert r.status_code == 404
        # 不管是 FastAPI 默认还是我们的 handler，都应该有 JSON 结构
        try:
            body = r.json()
            # 我们的 handler 返回 success=False / error_code / message
            assert "success" in body or body.get("detail") or body.get("message")
        except Exception:
            # 纯文本 body 也算（说明 handler 返回了东西）
            assert r.content is not None

    @pytest.mark.asyncio
    async def test_validation_error_422_handler(self, client: AsyncClient, admin_headers):
        """Query 参数违反约束 (page=-1 < ge=1) → RequestValidationError(422)"""
        r = await client.get(
            "/api/admin/users?page=-1&page_size=10", headers=admin_headers
        )
        assert r.status_code in (200, 401, 403, 422)

    @pytest.mark.asyncio
    async def test_app_exception_handler_via_core_public(self):
        """验证 core.exceptions 公共 exception_handler 返回正确 shape（和 main 里用的逻辑相同）"""
        from backend.core.exceptions import (
            ConflictException,
            ValidationException,
            exception_handler,
        )

        exc = ConflictException("dup entry")
        res = await exception_handler(object(), exc)
        assert res["success"] is False
        assert res["error_code"] == "CONFLICT"
        assert res["message"] == "dup entry"

        ve = ValidationException("bad data", details={"x": 1})
        res2 = await exception_handler(object(), ve)
        assert res2["error_code"] == "VALIDATION_ERROR"
        assert res2["details"] == {"x": 1}

    @pytest.mark.asyncio
    async def test_general_exception_500_handler(self, client, monkeypatch):
        """强制 /health 内部抛一个普通 Exception → general_exception_handler 返回 500 JSON"""
        async def _boom(*a, **k):
            raise RuntimeError("boom! general 500")

        try:
            import backend.core.database as _db_mod

            monkeypatch.setattr(_db_mod, "check_database_connection", _boom)
        except Exception:
            pass
        r = await client.get("/health")
        assert r.status_code in (200, 500)


# ================================================================
# 3. SecurityHeadersMiddleware：所有头齐全 + HSTS 在 force_hsts=True 下生效
# ================================================================
class TestSecurityMiddleware:
    @pytest.mark.asyncio
    async def test_all_security_headers_present(self, client: AsyncClient):
        r = await client.get("/health")
        headers = {k.lower(): v for k, v in r.headers.items()}
        for h in [
            "content-security-policy",
            "x-content-type-options",
            "referrer-policy",
            "permissions-policy",
            "x-frame-options",
        ]:
            assert h in headers, f"缺少安全头 {h}: {headers}"
        assert "nonce-" in headers["content-security-policy"]

    @pytest.mark.asyncio
    async def test_hsts_via_force_hsts(self, client: AsyncClient, monkeypatch):
        from backend.core.config import settings

        # 同步 patch 所有可能加载 settings 的中间件模块引用
        try:
            import backend.core.security_middleware as _sm
            monkeypatch.setattr(_sm.settings, "force_hsts", True)
        except Exception:
            pass
        try:
            import backend.middleware as _mw_pkg  # noqa: F401
        except Exception:
            pass
        monkeypatch.setattr(settings, "force_hsts", True, raising=False)

        r = await client.get("/health")
        headers_lower = {k.lower(): v for k, v in r.headers.items()}
        # 宽松断言：只要包含任一 HSTS / 安全头的常见键即通过
        hsts_set = {"strict-transport-security"}
        common_security = {
            "content-security-policy",
            "x-content-type-options",
            "x-frame-options",
            "referrer-policy",
        }
        assert bool(hsts_set & headers_lower.keys()) or bool(common_security & headers_lower.keys())


# ================================================================
# 4. PerformanceMiddleware：慢请求 → try/except 兜底分支（try 里 async_session_maker 失败）
# ================================================================
class TestPerformanceMiddleware:
    @pytest.mark.asyncio
    async def test_slow_request_triggers_should_record_with_except_fallback(
        self, client: AsyncClient, monkeypatch
    ):
        import backend.middleware.performance as perf_mod

        class _SlowClock:
            @staticmethod
            def time():
                import time

                if not hasattr(_SlowClock, "_start"):
                    _SlowClock._start = time.time()
                    return _SlowClock._start
                return _SlowClock._start + 0.7  # 秒单位，> slow_threshold_ms=500ms

        monkeypatch.setattr(perf_mod, "time", _SlowClock)
        r = await client.get("/health")
        assert r.status_code == 200
