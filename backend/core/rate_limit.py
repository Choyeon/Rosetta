"""
限流服务层

提供统一的限流接口，支持：
- 滑动窗口限流算法
- Redis 存储（生产环境）
- 内存存储（开发环境）
- 多种限流策略
- FastAPI Depends 风格端点限流
"""

import asyncio
import hashlib
import logging
import time
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from enum import Enum
from functools import wraps
from typing import ParamSpec, TypeVar

from fastapi import HTTPException, Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from backend.core.cache import cache
from backend.core.config import settings

logger = logging.getLogger(__name__)

P = ParamSpec("P")
T = TypeVar("T")


class RateLimitStrategy(Enum):
    """限流策略枚举"""

    FIXED_WINDOW = "fixed_window"
    SLIDING_WINDOW = "sliding_window"
    TOKEN_BUCKET = "token_bucket"


@dataclass
class RateLimitRule:
    """限流规则"""

    requests: int
    window_seconds: int
    strategy: RateLimitStrategy = RateLimitStrategy.SLIDING_WINDOW
    key_prefix: str = "rate_limit"

    @property
    def requests_per_second(self) -> float:
        """每秒请求数"""
        return self.requests / self.window_seconds


@dataclass
class RateLimitResult:
    """限流检查结果"""

    allowed: bool
    remaining: int
    reset_at: float
    retry_after: int | None = None

    def to_headers(self) -> dict[str, str]:
        """转换为响应头"""
        headers = {
            "X-RateLimit-Limit": str(self.remaining + (0 if self.allowed else 0)),
            "X-RateLimit-Remaining": str(max(0, self.remaining)),
            "X-RateLimit-Reset": str(int(self.reset_at)),
        }
        if self.retry_after:
            headers["Retry-After"] = str(self.retry_after)
        return headers


@dataclass
class LoginAttempt:
    """登录尝试记录"""

    username: str
    ip_address: str
    attempt_count: int = 0
    first_attempt_at: float = field(default_factory=time.time)
    last_attempt_at: float = field(default_factory=time.time)
    locked_until: float | None = None


class RateLimiter:
    """
    限流器

    实现滑动窗口限流算法，支持 Redis 和内存存储。
    """

    def __init__(self):
        self._memory_store: dict[str, list[float]] = {}
        self._lock = asyncio.Lock()

    def _get_redis_client(self):
        """获取 Redis 客户端（如果可用）"""
        if hasattr(cache.backend, "_get_client"):
            return cache.backend
        return None

    async def _get_sliding_window_data(self, key: str) -> list[float]:
        """获取滑动窗口数据"""
        redis_backend = self._get_redis_client()

        if redis_backend and settings.redis_enabled:
            try:
                import json

                client = await redis_backend._get_client()
                if redis_backend._connected:
                    data = await client.get(key)
                    if data:
                        return json.loads(data)
                return []
            except Exception as e:
                logger.error(f"Redis 获取滑动窗口数据失败: {e}")
                return []
        else:
            async with self._lock:
                return self._memory_store.get(key, []).copy()

    async def _set_sliding_window_data(self, key: str, data: list[float], ttl: int) -> bool:
        """设置滑动窗口数据"""
        redis_backend = self._get_redis_client()

        if redis_backend and settings.redis_enabled:
            try:
                import json

                client = await redis_backend._get_client()
                if redis_backend._connected:
                    await client.setex(key, ttl, json.dumps(data))
                    return True
            except Exception as e:
                logger.error(f"Redis 设置滑动窗口数据失败: {e}")
        else:
            async with self._lock:
                self._memory_store[key] = data

        return True

    async def check_rate_limit(
        self,
        key: str,
        rule: RateLimitRule,
    ) -> RateLimitResult:
        """
        检查是否超过限流

        Args:
            key: 限流键
            rule: 限流规则

        Returns:
            RateLimitResult: 限流检查结果
        """
        current_time = time.time()
        window_start = current_time - rule.window_seconds

        if rule.strategy == RateLimitStrategy.SLIDING_WINDOW:
            return await self._check_sliding_window(key, rule, current_time, window_start)
        else:
            return await self._check_fixed_window(key, rule, current_time)

    async def _check_sliding_window(
        self,
        key: str,
        rule: RateLimitRule,
        current_time: float,
        window_start: float,
    ) -> RateLimitResult:
        """滑动窗口限流检查"""
        cache_key = f"{rule.key_prefix}:{key}"

        timestamps = await self._get_sliding_window_data(cache_key)

        valid_timestamps = [ts for ts in timestamps if ts > window_start]

        if len(valid_timestamps) >= rule.requests:
            oldest = min(valid_timestamps) if valid_timestamps else current_time
            reset_at = oldest + rule.window_seconds
            retry_after = int(reset_at - current_time)

            return RateLimitResult(
                allowed=False,
                remaining=0,
                reset_at=reset_at,
                retry_after=retry_after,
            )

        valid_timestamps.append(current_time)
        await self._set_sliding_window_data(cache_key, valid_timestamps, rule.window_seconds + 1)

        remaining = rule.requests - len(valid_timestamps)
        reset_at = current_time + rule.window_seconds

        return RateLimitResult(
            allowed=True,
            remaining=remaining,
            reset_at=reset_at,
        )

    async def _check_fixed_window(
        self,
        key: str,
        rule: RateLimitRule,
        current_time: float,
    ) -> RateLimitResult:
        """固定窗口限流检查"""
        window_start = int(current_time / rule.window_seconds) * rule.window_seconds
        cache_key = f"{rule.key_prefix}:{key}:{window_start}"

        count = await cache.incr(cache_key)

        if count == 1:
            await cache.set(cache_key, count, ttl=rule.window_seconds)

        remaining = max(0, rule.requests - count)
        reset_at = window_start + rule.window_seconds

        if count > rule.requests:
            retry_after = int(reset_at - current_time)
            return RateLimitResult(
                allowed=False,
                remaining=0,
                reset_at=reset_at,
                retry_after=retry_after,
            )

        return RateLimitResult(
            allowed=True,
            remaining=remaining,
            reset_at=reset_at,
        )

    async def reset(self, key: str, prefix: str = "rate_limit") -> bool:
        """重置限流计数"""
        cache_key = f"{prefix}:{key}"

        redis_backend = self._get_redis_client()
        if redis_backend and settings.redis_enabled:
            try:
                client = await redis_backend._get_client()
                if redis_backend._connected:
                    await client.delete(cache_key)
            except Exception as e:
                logger.error(f"Redis 重置限流失败: {e}")
        else:
            async with self._lock:
                self._memory_store.pop(cache_key, None)

        return True

    async def get_remaining(
        self,
        key: str,
        rule: RateLimitRule,
    ) -> int:
        """获取剩余请求数"""
        current_time = time.time()
        window_start = current_time - rule.window_seconds
        cache_key = f"{rule.key_prefix}:{key}"

        timestamps = await self._get_sliding_window_data(cache_key)
        valid_timestamps = [ts for ts in timestamps if ts > window_start]

        return max(0, rule.requests - len(valid_timestamps))


rate_limiter = RateLimiter()


class LoginRateLimiter:
    """
    登录限流器

    专门用于登录场景的限流，支持：
    - 基于用户名的限流
    - 基于IP的限流
    - 账户锁定机制
    """

    DEFAULT_MAX_ATTEMPTS = 5
    DEFAULT_WINDOW_SECONDS = 900
    DEFAULT_LOCKOUT_SECONDS = 1800

    def __init__(
        self,
        max_attempts: int = DEFAULT_MAX_ATTEMPTS,
        window_seconds: int = DEFAULT_WINDOW_SECONDS,
        lockout_seconds: int = DEFAULT_LOCKOUT_SECONDS,
    ):
        self.max_attempts = max_attempts
        self.window_seconds = window_seconds
        self.lockout_seconds = lockout_seconds
        self._memory_store: dict[str, LoginAttempt] = {}
        self._lock = asyncio.Lock()

    def _get_cache_key(self, username: str, ip_address: str) -> str:
        """生成缓存键"""
        return f"login_attempt:{username}:{ip_address}"

    def _get_lockout_key(self, username: str) -> str:
        """生成锁定键"""
        return f"login_lockout:{username}"

    async def _get_attempt(self, key: str) -> LoginAttempt | None:
        """获取登录尝试记录"""
        redis_backend = rate_limiter._get_redis_client()

        if redis_backend and settings.redis_enabled:
            try:
                import json

                client = await redis_backend._get_client()
                if redis_backend._connected:
                    data = await client.get(key)
                    if data:
                        attempt_data = json.loads(data)
                        return LoginAttempt(**attempt_data)
            except Exception as e:
                logger.error(f"Redis 获取登录尝试记录失败: {e}")

        return None

    async def _set_attempt(self, key: str, attempt: LoginAttempt, ttl: int) -> bool:
        """设置登录尝试记录"""
        redis_backend = rate_limiter._get_redis_client()

        if redis_backend and settings.redis_enabled:
            try:
                import json

                client = await redis_backend._get_client()
                if redis_backend._connected:
                    data = {
                        "username": attempt.username,
                        "ip_address": attempt.ip_address,
                        "attempt_count": attempt.attempt_count,
                        "first_attempt_at": attempt.first_attempt_at,
                        "last_attempt_at": attempt.last_attempt_at,
                        "locked_until": attempt.locked_until,
                    }
                    await client.setex(key, ttl, json.dumps(data))
                    return True
            except Exception as e:
                logger.error(f"Redis 设置登录尝试记录失败: {e}")
        else:
            async with self._lock:
                self._memory_store[key] = attempt

        return True

    async def is_locked(self, username: str) -> tuple[bool, int | None]:
        """
        检查账户是否被锁定

        Args:
            username: 用户名

        Returns:
            tuple[bool, int | None]: (是否锁定, 剩余锁定时间秒数)
        """
        lockout_key = self._get_lockout_key(username)

        redis_backend = rate_limiter._get_redis_client()

        if redis_backend and settings.redis_enabled:
            try:
                client = await redis_backend._get_client()
                if redis_backend._connected:
                    ttl = await client.ttl(lockout_key)
                    if ttl > 0:
                        return True, ttl
            except Exception as e:
                logger.error(f"Redis 检查锁定状态失败: {e}")

        return False, None

    async def record_attempt(
        self,
        username: str,
        ip_address: str,
        success: bool = False,
    ) -> tuple[int, bool]:
        """
        记录登录尝试

        Args:
            username: 用户名
            ip_address: IP地址
            success: 是否登录成功

        Returns:
            tuple[int, bool]: (当前尝试次数, 是否被锁定)
        """
        current_time = time.time()
        cache_key = self._get_cache_key(username, ip_address)

        if success:
            await self.reset_attempts(username, ip_address)
            return 0, False

        attempt = await self._get_attempt(cache_key)

        if attempt is None:
            attempt = LoginAttempt(
                username=username,
                ip_address=ip_address,
                attempt_count=1,
                first_attempt_at=current_time,
                last_attempt_at=current_time,
            )
        else:
            window_start = current_time - self.window_seconds
            if attempt.first_attempt_at < window_start:
                attempt.attempt_count = 1
                attempt.first_attempt_at = current_time
            else:
                attempt.attempt_count += 1
            attempt.last_attempt_at = current_time

        await self._set_attempt(cache_key, attempt, self.window_seconds + 1)

        if attempt.attempt_count >= self.max_attempts:
            await self._lock_account(username)
            return attempt.attempt_count, True

        return attempt.attempt_count, False

    async def _lock_account(self, username: str) -> bool:
        """锁定账户"""
        lockout_key = self._get_lockout_key(username)

        redis_backend = rate_limiter._get_redis_client()

        if redis_backend and settings.redis_enabled:
            try:
                client = await redis_backend._get_client()
                if redis_backend._connected:
                    await client.setex(lockout_key, self.lockout_seconds, "1")
                    logger.warning(f"账户 {username} 已锁定 {self.lockout_seconds} 秒")
                    return True
            except Exception as e:
                logger.error(f"Redis 锁定账户失败: {e}")

        return True

    async def reset_attempts(self, username: str, ip_address: str) -> bool:
        """重置登录尝试计数"""
        cache_key = self._get_cache_key(username, ip_address)
        lockout_key = self._get_lockout_key(username)

        redis_backend = rate_limiter._get_redis_client()

        if redis_backend and settings.redis_enabled:
            try:
                client = await redis_backend._get_client()
                if redis_backend._connected:
                    await client.delete(cache_key)
                    await client.delete(lockout_key)
            except Exception as e:
                logger.error(f"Redis 重置登录尝试失败: {e}")
        else:
            async with self._lock:
                self._memory_store.pop(cache_key, None)

        return True

    async def get_remaining_attempts(self, username: str, ip_address: str) -> int:
        """获取剩余尝试次数"""
        cache_key = self._get_cache_key(username, ip_address)
        attempt = await self._get_attempt(cache_key)

        if attempt is None:
            return self.max_attempts

        return max(0, self.max_attempts - attempt.attempt_count)


login_rate_limiter = LoginRateLimiter()


def get_client_ip(request: Request) -> str:
    """获取客户端真实IP"""
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()

    real_ip = request.headers.get("X-Real-IP")
    if real_ip:
        return real_ip

    if request.client:
        return request.client.host

    return "unknown"


def generate_rate_limit_key(request: Request, identifier: str | None = None) -> str:
    """生成限流键"""
    if identifier:
        return hashlib.sha256(identifier.encode()).hexdigest()[:16]

    ip = get_client_ip(request)
    path = request.url.path

    return hashlib.sha256(f"{ip}:{path}".encode()).hexdigest()[:16]


def rate_limit(
    rule: RateLimitRule | None = None,
    key_func: Callable[[Request], str] | None = None,
    identifier: str | None = None,
):
    """
    限流装饰器

    用于单个路由的限流控制。

    用法:
        @rate_limit(RateLimitRule(requests=10, window_seconds=60))
        async def my_endpoint(request: Request):
            ...

        @rate_limit(identifier="login")
        async def login_endpoint(request: Request):
            ...
    """
    if rule is None:
        rule = RateLimitRule(requests=60, window_seconds=60)

    def decorator(func: Callable[P, Awaitable[T]]) -> Callable[P, Awaitable[T]]:
        @wraps(func)
        async def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
            request: Request | None = None

            for arg in args:
                if isinstance(arg, Request):
                    request = arg
                    break

            if request is None:
                request = kwargs.get("request")

            if request is None:
                return await func(*args, **kwargs)

            if key_func:
                key = key_func(request)
            elif identifier:
                key = generate_rate_limit_key(request, identifier)
            else:
                key = generate_rate_limit_key(request)

            result = await rate_limiter.check_rate_limit(key, rule)

            if not result.allowed:
                raise HTTPException(
                    status_code=429,
                    detail={
                        "message": "请求过于频繁，请稍后再试",
                        "retry_after": result.retry_after,
                    },
                    headers=result.to_headers(),
                )

            response = await func(*args, **kwargs)

            if isinstance(response, Response):
                for header, value in result.to_headers().items():
                    response.headers[header] = value

            return response

        return wrapper

    return decorator


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    限流中间件

    支持基于IP和用户的限流，可配置白名单路径。
    """

    def __init__(
        self,
        app: ASGIApp,
        default_rule: RateLimitRule | None = None,
        whitelist_paths: list[str] | None = None,
        path_rules: dict[str, RateLimitRule] | None = None,
    ):
        super().__init__(app)
        self.default_rule = default_rule or RateLimitRule(requests=100, window_seconds=60)
        self.whitelist_paths = whitelist_paths or [
            "/health",
            "/metrics",
            "/favicon.ico",
            "/static",
            "/_nuxt",
        ]
        self.path_rules = path_rules or {}

    def _is_whitelisted(self, path: str) -> bool:
        """检查路径是否在白名单中"""
        for whitelist_path in self.whitelist_paths:
            if path.startswith(whitelist_path):
                return True
        return False

    def _get_rule_for_path(self, path: str) -> RateLimitRule:
        """获取路径对应的限流规则"""
        for pattern, rule in self.path_rules.items():
            if path.startswith(pattern):
                return rule
        return self.default_rule

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """处理请求"""
        path = request.url.path

        if self._is_whitelisted(path):
            return await call_next(request)

        rule = self._get_rule_for_path(path)

        user_id = None
        if hasattr(request.state, "user") and request.state.user:
            user_id = getattr(request.state.user, "id", None)

        if user_id:
            key = f"user:{user_id}"
        else:
            key = f"ip:{get_client_ip(request)}"

        key = f"{key}:{path}"

        result = await rate_limiter.check_rate_limit(key, rule)

        if not result.allowed:
            return JSONResponse(
                status_code=429,
                content={
                    "detail": {
                        "message": "请求过于频繁，请稍后再试",
                        "retry_after": result.retry_after,
                    }
                },
                headers=result.to_headers(),
            )

        response = await call_next(request)

        for header, value in result.to_headers().items():
            response.headers[header] = value

        return response


DEFAULT_RATE_LIMIT_RULES = {
    "/api/users/login": RateLimitRule(
        requests=5,
        window_seconds=900,
        key_prefix="login",
    ),
    "/api/users/register": RateLimitRule(
        requests=3,
        window_seconds=3600,
        key_prefix="register",
    ),
    "/api/users/password-reset": RateLimitRule(
        requests=3,
        window_seconds=3600,
        key_prefix="password_reset",
    ),
    "/api/media/upload": RateLimitRule(
        requests=10,
        window_seconds=60,
        key_prefix="upload",
    ),
    "/api": RateLimitRule(
        requests=100,
        window_seconds=60,
        key_prefix="api",
    ),
}


def setup_rate_limit_middleware(app) -> None:
    """
    配置限流中间件

    Args:
        app: FastAPI 应用实例
    """
    app.add_middleware(
        RateLimitMiddleware,
        default_rule=RateLimitRule(requests=100, window_seconds=60),
        whitelist_paths=[
            "/health",
            "/metrics",
            "/favicon.ico",
            "/static",
            "/_nuxt",
            "/api/docs",
            "/api/openapi.json",
        ],
        path_rules=DEFAULT_RATE_LIMIT_RULES,
    )

    logger.info("限流中间件已配置")


SENSITIVE_ENDPOINT_RULE = RateLimitRule(
    requests=settings.rate_limit_sensitive_requests,
    window_seconds=settings.rate_limit_sensitive_window,
    strategy=RateLimitStrategy.SLIDING_WINDOW,
    key_prefix="sensitive",
)

WRITE_ENDPOINT_RULE = RateLimitRule(
    requests=settings.rate_limit_write_requests,
    window_seconds=settings.rate_limit_write_window,
    strategy=RateLimitStrategy.SLIDING_WINDOW,
    key_prefix="write",
)


def build_depends_rate_limit(
    rule: RateLimitRule,
    endpoint_name: str,
    use_user_id: bool = False,
    *,
    requests_attr: str | None = None,
    window_attr: str | None = None,
):
    """
    生成基于 Depends 的限流依赖函数

    Args:
        rule: 默认限流规则（当 settings 属性不可用时回退）
        endpoint_name: 端点名称，用于生成 key
        use_user_id: True 时优先使用已登录 user_id，否则用 client_ip
        requests_attr: 若指定，每请求从 settings 动态读取该属性覆盖 rule.requests
        window_attr: 若指定，每请求从 settings 动态读取该属性覆盖 rule.window_seconds

    Returns:
        Callable 可直接用于 Depends(...)
    """

    async def _dep(request: Request) -> None:
        identifier: str | None = None
        if use_user_id:
            try:
                from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

                security = HTTPBearer(auto_error=False)
                creds: HTTPAuthorizationCredentials | None = await security(request)
                if creds is not None:
                    from backend.core.auth import decode_token

                    payload = decode_token(creds.credentials)
                    if payload and payload.get("type") == "access":
                        uid = payload.get("sub")
                        if uid:
                            identifier = f"user:{uid}"
            except Exception:
                identifier = None

        if identifier is None:
            identifier = f"ip:{get_client_ip(request)}"

        # 每请求动态从 settings 读取阈值，方便测试 / 运行时调整
        eff_requests = rule.requests
        eff_window = rule.window_seconds
        try:
            if requests_attr is not None and hasattr(settings, requests_attr):
                eff_requests = int(getattr(settings, requests_attr))
            if window_attr is not None and hasattr(settings, window_attr):
                eff_window = int(getattr(settings, window_attr))
        except Exception:
            pass

        effective_rule = RateLimitRule(
            requests=max(1, eff_requests),
            window_seconds=max(1, eff_window),
            strategy=rule.strategy,
            key_prefix=rule.key_prefix,
        )

        key = f"{endpoint_name}:{identifier}"
        result = await rate_limiter.check_rate_limit(key, effective_rule)

        if not result.allowed:
            headers = result.to_headers()
            raise HTTPException(
                status_code=429,
                detail={
                    "message": "请求过于频繁，请稍后再试",
                    "error_code": "RATE_LIMITED",
                    "retry_after": result.retry_after,
                },
                headers=headers,
            )

    return _dep


def rate_limit_sensitive(endpoint_name: str):
    """
    敏感接口（登录/注册/刷新/重置密码）限流：默认 1 分钟 10 次，基于 IP

    每请求动态读取 settings.rate_limit_sensitive_requests / rate_limit_sensitive_window。
    """
    return build_depends_rate_limit(
        SENSITIVE_ENDPOINT_RULE,
        endpoint_name=endpoint_name,
        use_user_id=False,
        requests_attr="rate_limit_sensitive_requests",
        window_attr="rate_limit_sensitive_window",
    )


def rate_limit_write(endpoint_name: str):
    """
    普通写接口限流：默认 1 分钟 60 次，优先按 user_id，匿名按 IP

    每请求动态读取 settings.rate_limit_write_requests / rate_limit_write_window。
    """
    return build_depends_rate_limit(
        WRITE_ENDPOINT_RULE,
        endpoint_name=endpoint_name,
        use_user_id=True,
        requests_attr="rate_limit_write_requests",
        window_attr="rate_limit_write_window",
    )
