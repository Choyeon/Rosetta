"""限流契约回归：`X-RateLimit-*` 头 + 429 错误包络 + 全站唯一 429 错误码。

修复前的三处真实缺陷：
1. ``to_headers`` 把 ``X-RateLimit-Limit`` 写成了 ``remaining``
   （``str(self.remaining + (0 if self.allowed else 0))``，那个加法恒等于 0），
   于是 Limit 与 Remaining 两个头永远相等，客户端拿不到阈值；
2. ``RateLimitMiddleware`` 命中限流时直接返回 ``{"detail": {...}}``，
   绕过了 main.py 的错误包络（中间件自造响应不走 exception handler），
   429 成为全站唯一的非 ``success/error_code/message`` 错误体，
   而前端 ``extractApiErrorMessage`` 只认 ``detail`` 为**字符串**，
   用户看到的是兜底文案而不是"请求过于频繁"；
3. 三个触发点各写各的 ``error_code``（中间件无、装饰器走状态码回退成
   ``TOO_MANY_REQUESTS``、依赖式写死 ``RATE_LIMITED``），
   而 ``backend/docs/error_codes.md`` 声称的是 ``RATE_LIMIT_EXCEEDED``。

本文件不打数据库，全部走内存计数器。
"""

import time
from collections.abc import Iterator

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from backend.core.exceptions import RATE_LIMIT_EXCEEDED
from backend.core.rate_limit import (
    RateLimitMiddleware,
    RateLimitResult,
    RateLimitRule,
    RateLimitStrategy,
    rate_limiter,
)


@pytest.fixture(autouse=True)
def _isolated_memory_counters() -> Iterator[None]:
    """清计数 + 断掉 Redis 分支，保证两次调用之间不互相污染。"""
    rate_limiter._memory_store.clear()
    rate_limiter._memory_counters.clear()
    original = rate_limiter._get_redis_client
    rate_limiter._get_redis_client = lambda: None  # type: ignore[method-assign]
    yield
    rate_limiter._memory_store.clear()
    rate_limiter._memory_counters.clear()
    rate_limiter._get_redis_client = original  # type: ignore[method-assign]


class TestRateLimitHeaders:
    def test_limit_header_is_threshold_not_remaining(self):
        """Limit 必须是规则阈值；修复前它等于 remaining。"""
        headers = RateLimitResult(
            allowed=True, limit=5, remaining=4, reset_at=time.time() + 60
        ).to_headers()
        assert headers["X-RateLimit-Limit"] == "5"
        assert headers["X-RateLimit-Remaining"] == "4"
        assert "Retry-After" not in headers

    def test_blocked_result_carries_retry_after(self):
        headers = RateLimitResult(
            allowed=False, limit=1, remaining=0, reset_at=time.time() + 30, retry_after=29
        ).to_headers()
        assert headers["X-RateLimit-Limit"] == "1"
        assert headers["X-RateLimit-Remaining"] == "0"
        assert headers["Retry-After"] == "29"

    @pytest.mark.asyncio
    @pytest.mark.parametrize("strategy", list(RateLimitStrategy))
    async def test_both_algorithms_report_same_limit(self, strategy: RateLimitStrategy):
        """固定窗口与滑动窗口的头口径必须一致（同一 rule.requests）。"""
        rule = RateLimitRule(
            requests=2, window_seconds=60, strategy=strategy, key_prefix=strategy.value
        )
        first = await rate_limiter.check_rate_limit("k1", rule)
        second = await rate_limiter.check_rate_limit("k1", rule)
        third = await rate_limiter.check_rate_limit("k1", rule)

        assert [first.allowed, second.allowed, third.allowed] == [True, True, False]
        for result in (first, second, third):
            assert result.to_headers()["X-RateLimit-Limit"] == "2"
        assert first.remaining == 1
        assert second.remaining == 0
        assert third.retry_after is not None and third.retry_after >= 1


class TestMiddlewareEnvelope:
    @staticmethod
    def _app(rule: RateLimitRule) -> FastAPI:
        app = FastAPI()
        app.add_middleware(RateLimitMiddleware, default_rule=rule, path_rules={})
        seen: list[int] = []

        @app.get("/probe/limited")
        async def _probe():
            seen.append(1)
            return {"ok": True}

        app.state.seen = seen
        return app

    @pytest.mark.asyncio
    async def test_429_body_is_unified_envelope(self):
        """命中限流必须返回 success/error_code/message，而不是 {"detail": {...}}。"""
        app = self._app(RateLimitRule(requests=1, window_seconds=60, key_prefix="mw-env"))
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            ok = await ac.get("/probe/limited")
            blocked = await ac.get("/probe/limited")

        assert ok.status_code == 200
        assert blocked.status_code == 429
        body = blocked.json()
        assert "detail" not in body, "非包络形状会让前端取不到 message"
        assert body["success"] is False
        assert body["error_code"] == RATE_LIMIT_EXCEEDED
        assert isinstance(body["message"], str) and body["message"]
        assert blocked.headers["X-RateLimit-Limit"] == "1"
        assert blocked.headers["X-RateLimit-Remaining"] == "0"
        assert int(blocked.headers["Retry-After"]) >= 1

    @pytest.mark.asyncio
    async def test_allowed_response_carries_threshold_header(self):
        app = self._app(RateLimitRule(requests=3, window_seconds=60, key_prefix="mw-ok"))
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
            ok = await ac.get("/probe/limited")
        assert ok.status_code == 200
        assert ok.headers["X-RateLimit-Limit"] == "3"
        assert ok.headers["X-RateLimit-Remaining"] == "2"


class TestErrorCodeSingleSource:
    def test_exception_class_uses_canonical_code(self):
        from backend.core.exceptions import RateLimitException

        assert RateLimitException().error_code == RATE_LIMIT_EXCEEDED

    def test_no_legacy_429_codes_left_in_source(self):
        """历史上有 `TOO_MANY_REQUESTS`（状态码回退表）与 `RATE_LIMITED`（依赖式限流）
        两个 429 码；两者都必须收敛到 `RATE_LIMIT_EXCEEDED`，不得回潮。"""
        from backend.core.paths import BASE_DIR

        sources = {
            "main.py": BASE_DIR / "backend" / "main.py",
            "rate_limit.py": BASE_DIR / "backend" / "core" / "rate_limit.py",
        }
        for name, path in sources.items():
            text = path.read_text(encoding="utf-8")
            assert "TOO_MANY_REQUESTS" not in text, f"{name} 仍在产 429 的旧错误码"
            assert '"RATE_LIMITED"' not in text, f"{name} 仍在产 429 的旧错误码"
