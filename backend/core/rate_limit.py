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
import uuid
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
from backend.core.exceptions import RATE_LIMIT_EXCEEDED

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
    limit: int
    remaining: int
    reset_at: float
    retry_after: int | None = None

    def to_headers(self) -> dict[str, str]:
        """转换为响应头

        `X-RateLimit-Limit` 必须是规则阈值而不是剩余量：此前它直接抄了
        `remaining`，两个头永远相等，客户端据此画的进度条/退避逻辑都是错的。
        """
        headers = {
            "X-RateLimit-Limit": str(self.limit),
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


# 滑动窗口原子化 Lua（ZSET）：裁剪过期成员、计数、判断、写入在同一脚本内完成，
# 消除 GET→改→SETEX 在并发下放行超过限额的竞态。
_SLIDING_WINDOW_LUA = """
redis.call("ZREMRANGEBYSCORE", KEYS[1], "-inf", ARGV[1])
local count = redis.call("ZCARD", KEYS[1])
if count >= tonumber(ARGV[2]) then
    local oldest = redis.call("ZRANGE", KEYS[1], 0, 0, "WITHSCORES")
    if #oldest == 2 then
        return {0, oldest[2]}
    end
    return {0, ARGV[3]}
end
redis.call("ZADD", KEYS[1], ARGV[3], ARGV[4])
redis.call("PEXPIRE", KEYS[1], ARGV[5])
return {1, count + 1}
"""

_SLIDING_COUNT_LUA = """
redis.call("ZREMRANGEBYSCORE", KEYS[1], "-inf", ARGV[1])
return redis.call("ZCARD", KEYS[1])
"""

# 固定窗口 INCR + 首次 EXPIRE 原子化：避免计数键永不过期
_FIXED_WINDOW_LUA = """
local count = redis.call("INCR", KEYS[1])
if count == 1 then
    redis.call("EXPIRE", KEYS[1], ARGV[1])
end
return count
"""

# 内存存储条目超过该数量时触发一次惰性过期清理
_MEMORY_PRUNE_THRESHOLD = 2048


class RateLimiter:
    """
    限流器

    实现滑动/固定窗口限流算法，支持 Redis（Lua 原子操作）和内存存储。
    """

    def __init__(self):
        # key -> (expires_at, timestamps)；expires_at 供惰性清理
        self._memory_store: dict[str, tuple[float, list[float]]] = {}
        # 固定窗口计数：key -> (count, expires_at)
        self._memory_counters: dict[str, tuple[int, float]] = {}
        self._lock = asyncio.Lock()

    def _get_redis_client(self):
        """获取 Redis 客户端（仅当已实际连上时返回，否则回退内存存储）"""
        backend = getattr(cache, "backend", None)
        if backend is None:
            return None
        # 必须同时满足：声明启用 + 拥有客户端方法 + 真正建立连接
        if (
            settings.redis_enabled
            and hasattr(backend, "_get_client")
            and getattr(backend, "_connected", False)
        ):
            return backend
        return None

    def _prune_memory_locked(self, now: float) -> None:
        """惰性清理过期内存条目，防止 key 无界增长"""
        if len(self._memory_store) > _MEMORY_PRUNE_THRESHOLD:
            for k in [k for k, (exp, _) in self._memory_store.items() if exp <= now]:
                del self._memory_store[k]
        if len(self._memory_counters) > _MEMORY_PRUNE_THRESHOLD:
            for k in [k for k, (_, exp) in self._memory_counters.items() if exp <= now]:
                del self._memory_counters[k]

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
        """滑动窗口限流检查（Redis Lua 原子；内存路径整个临界区持锁且无 await）"""
        cache_key = f"{rule.key_prefix}:{key}"

        result = await self._sliding_window_redis(cache_key, rule, current_time, window_start)
        if result is not None:
            return result

        async with self._lock:
            self._prune_memory_locked(current_time)
            stored = self._memory_store.get(cache_key)
            if stored is None or stored[0] <= current_time:
                timestamps: list[float] = []
            else:
                timestamps = [ts for ts in stored[1] if ts > window_start]

            expires_at = current_time + rule.window_seconds + 1
            if len(timestamps) >= rule.requests:
                oldest = min(timestamps)
                reset_at = oldest + rule.window_seconds
                self._memory_store[cache_key] = (expires_at, timestamps)
                return RateLimitResult(
                    allowed=False,
                    limit=rule.requests,
                    remaining=0,
                    reset_at=reset_at,
                    retry_after=max(1, int(reset_at - current_time)),
                )

            timestamps.append(current_time)
            self._memory_store[cache_key] = (expires_at, timestamps)
            return RateLimitResult(
                allowed=True,
                limit=rule.requests,
                remaining=rule.requests - len(timestamps),
                reset_at=current_time + rule.window_seconds,
            )

    async def _sliding_window_redis(
        self,
        cache_key: str,
        rule: RateLimitRule,
        current_time: float,
        window_start: float,
    ) -> RateLimitResult | None:
        """Redis 原子滑动窗口；返回 None 表示不可用/失败，调用方回退内存"""
        redis_backend = self._get_redis_client()
        if redis_backend is None:
            return None
        try:
            client = await redis_backend._get_client()
            allowed, payload = await client.eval(
                _SLIDING_WINDOW_LUA,
                1,
                cache_key,
                str(window_start),
                str(rule.requests),
                str(current_time),
                uuid.uuid4().hex,
                str((rule.window_seconds + 1) * 1000),
            )
        except Exception as e:
            logger.error(f"Redis 滑动窗口执行失败，回退内存: {e}")
            return None

        if allowed:
            used = int(payload)
            return RateLimitResult(
                allowed=True,
                limit=rule.requests,
                remaining=max(0, rule.requests - used),
                reset_at=current_time + rule.window_seconds,
            )
        oldest = float(payload)
        reset_at = oldest + rule.window_seconds
        return RateLimitResult(
            allowed=False,
            limit=rule.requests,
            remaining=0,
            reset_at=reset_at,
            retry_after=max(1, int(reset_at - current_time)),
        )

    async def _check_fixed_window(
        self,
        key: str,
        rule: RateLimitRule,
        current_time: float,
    ) -> RateLimitResult:
        """固定窗口限流检查（计数带 TTL，不再依赖 cache.set 与 incr 双写不同 store）"""
        window_start = int(current_time / rule.window_seconds) * rule.window_seconds
        cache_key = f"{rule.key_prefix}:{key}:{window_start}"

        count = await self._incr_fixed_window(cache_key, rule.window_seconds, current_time)

        remaining = max(0, rule.requests - count)
        reset_at = window_start + rule.window_seconds

        if count > rule.requests:
            retry_after = int(reset_at - current_time)
            return RateLimitResult(
                allowed=False,
                limit=rule.requests,
                remaining=0,
                reset_at=reset_at,
                retry_after=retry_after,
            )

        return RateLimitResult(
            allowed=True,
            limit=rule.requests,
            remaining=remaining,
            reset_at=reset_at,
        )

    async def _incr_fixed_window(
        self,
        cache_key: str,
        window_seconds: int,
        current_time: float,
    ) -> int:
        """固定窗口计数自增（Redis Lua 原子 INCR+EXPIRE；内存带过期时间）"""
        redis_backend = self._get_redis_client()
        if redis_backend is not None:
            try:
                client = await redis_backend._get_client()
                return int(await client.eval(_FIXED_WINDOW_LUA, 1, cache_key, str(window_seconds)))
            except Exception as e:
                logger.error(f"Redis 固定窗口计数失败，回退内存: {e}")

        async with self._lock:
            self._prune_memory_locked(current_time)
            count, expires_at = self._memory_counters.get(cache_key, (0, 0.0))
            if expires_at <= current_time:
                count = 0
            count += 1
            self._memory_counters[cache_key] = (count, current_time + window_seconds)
            return count

    async def reset(self, key: str, prefix: str = "rate_limit") -> bool:
        """重置限流计数"""
        cache_key = f"{prefix}:{key}"

        redis_backend = self._get_redis_client()
        if redis_backend is not None:
            try:
                client = await redis_backend._get_client()
                await client.delete(cache_key)
            except Exception as e:
                logger.error(f"Redis 重置限流失败: {e}")
        async with self._lock:
            self._memory_store.pop(cache_key, None)
            # 固定窗口键带 window_start 后缀，无法精确还原；按前缀清理
            for k in [k for k in self._memory_counters if k.startswith(cache_key)]:
                del self._memory_counters[k]

        return True

    async def get_remaining(
        self,
        key: str,
        rule: RateLimitRule,
    ) -> int:
        """获取剩余请求数（滑动窗口口径）"""
        current_time = time.time()
        window_start = current_time - rule.window_seconds
        cache_key = f"{rule.key_prefix}:{key}"

        used: int | None = None
        redis_backend = self._get_redis_client()
        if redis_backend is not None:
            try:
                client = await redis_backend._get_client()
                used = int(await client.eval(_SLIDING_COUNT_LUA, 1, cache_key, str(window_start)))
            except Exception as e:
                logger.error(f"Redis 读取滑动窗口计数失败: {e}")
                used = None

        if used is None:
            async with self._lock:
                stored = self._memory_store.get(cache_key)
                if stored is None or stored[0] <= current_time:
                    timestamps: list[float] = []
                else:
                    timestamps = [ts for ts in stored[1] if ts > window_start]
                used = len(timestamps)

        return max(0, rule.requests - used)


rate_limiter = RateLimiter()


class LoginRateLimiter:
    """
    登录限流器（纯内存最小实现）

    生产登录锁定由 users.py 的 DB 字段（failed_login_attempts / locked_until）实现，
    本类无业务调用方；测试夹具（conftest 等）直接引用 is_locked / record_attempt /
    _memory_store，故保留这份最小可用形态而非删除。
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

    async def is_locked(self, username: str) -> tuple[bool, int | None]:
        """
        检查账户是否被锁定

        Args:
            username: 用户名

        Returns:
            tuple[bool, int | None]: (是否锁定, 剩余锁定时间秒数)
        """
        now = time.time()
        async with self._lock:
            lock = self._memory_store.get(self._get_lockout_key(username))
        if lock and lock.locked_until and lock.locked_until > now:
            return True, int(lock.locked_until - now)
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
        if success:
            await self.reset_attempts(username, ip_address)
            return 0, False

        now = time.time()
        cache_key = self._get_cache_key(username, ip_address)
        async with self._lock:
            attempt = self._memory_store.get(cache_key)
            if attempt is None or attempt.first_attempt_at < now - self.window_seconds:
                attempt = LoginAttempt(
                    username=username,
                    ip_address=ip_address,
                    attempt_count=1,
                    first_attempt_at=now,
                    last_attempt_at=now,
                )
            else:
                attempt.attempt_count += 1
                attempt.last_attempt_at = now
            self._memory_store[cache_key] = attempt

            locked = attempt.attempt_count >= self.max_attempts
            if locked:
                self._memory_store[self._get_lockout_key(username)] = LoginAttempt(
                    username=username,
                    ip_address="",
                    attempt_count=attempt.attempt_count,
                    first_attempt_at=now,
                    last_attempt_at=now,
                    locked_until=now + self.lockout_seconds,
                )
                logger.warning(f"账户 {username} 已锁定 {self.lockout_seconds} 秒")

        return attempt.attempt_count, locked

    async def reset_attempts(self, username: str, ip_address: str) -> bool:
        """重置登录尝试计数"""
        async with self._lock:
            self._memory_store.pop(self._get_cache_key(username, ip_address), None)
            self._memory_store.pop(self._get_lockout_key(username), None)
        return True

    async def get_remaining_attempts(self, username: str, ip_address: str) -> int:
        """获取剩余尝试次数"""
        now = time.time()
        async with self._lock:
            attempt = self._memory_store.get(self._get_cache_key(username, ip_address))
        if attempt is None or attempt.first_attempt_at < now - self.window_seconds:
            return self.max_attempts
        return max(0, self.max_attempts - attempt.attempt_count)


login_rate_limiter = LoginRateLimiter()


_TRUSTED_PROXY_CACHE: tuple[list[str], frozenset[str]] | None = None


def _trusted_proxies() -> frozenset[str]:
    """解析受信反代 IP 集合（缓存于模块级，settings 变更后进程内生效）"""
    global _TRUSTED_PROXY_CACHE
    raw = [str(x) for x in (getattr(settings, "trusted_proxy_ips", None) or [])]
    cached = _TRUSTED_PROXY_CACHE
    if cached is not None and cached[0] == raw:
        return cached[1]
    result = frozenset(x.strip() for x in raw if x.strip())
    _TRUSTED_PROXY_CACHE = (raw, result)
    return result


def get_client_ip(request: Request) -> str:
    """获取客户端真实 IP

    安全策略：仅当直连对端（socket 层 IP）属于 settings.trusted_proxy_ips 时，
    才采信 X-Forwarded-For / X-Real-IP 头；否则一律使用 socket IP。
    XFF 取「最右侧非受信跳」——最左值可被客户端伪造，最右值由离我们最近的
    受信反代追加，最为可信。

    若部署在 Nginx 等反代之后，需配置 TRUSTED_PROXY_IPS（如 127.0.0.1），
    否则所有请求都会被记录为反代 IP。
    """
    peer = request.client.host if request.client else None
    proxies = _trusted_proxies()

    if peer and peer in proxies:
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            candidates = [c.strip() for c in forwarded.split(",") if c.strip()]
            if candidates:
                for cand in reversed(candidates):
                    if cand not in proxies:
                        return cand
                return candidates[-1]

        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip.strip()

    if peer:
        return peer

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
                        "error_code": RATE_LIMIT_EXCEEDED,
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
            # 包络形状与 AGENTS.md §7.2 一致（success/error_code/message）。
            # 原先直接返回 {"detail": {...}}：FastAPI 的 exception handler 不参与
            # 中间件构造的响应，于是 429 成为全站唯一的非包络错误体，
            # 前端 extractApiErrorMessage 取不到 message，用户只看到"请求失败"。
            return JSONResponse(
                status_code=429,
                content={
                    "success": False,
                    "error_code": RATE_LIMIT_EXCEEDED,
                    "message": "请求过于频繁，请稍后再试",
                    "retry_after": result.retry_after,
                },
                headers=result.to_headers(),
            )

        response = await call_next(request)

        for header, value in result.to_headers().items():
            response.headers[header] = value

        return response


DEFAULT_RATE_LIMIT_RULES = {
    "/api/users/login": RateLimitRule(
        requests=5 if settings.is_production else 30,
        window_seconds=900 if settings.is_production else 60,
        key_prefix="login",
    ),
    "/api/users/register": RateLimitRule(
        requests=3 if settings.is_production else 20,
        window_seconds=3600 if settings.is_production else 60,
        key_prefix="register",
    ),
    "/api/users/password-reset": RateLimitRule(
        requests=3 if settings.is_production else 20,
        window_seconds=3600 if settings.is_production else 60,
        key_prefix="password_reset",
    ),
    "/api/media/upload": RateLimitRule(
        requests=10,
        window_seconds=60,
        key_prefix="upload",
    ),
    # 未鉴权 + 纯 CPU（正则扫描并逐层重扫正文），单请求成本远高于一次普通读接口。
    # 必须排在 "/api" 之前：_get_rule_for_path 按插入顺序 startswith 命中即返回，
    # 放在通配项之后这条规则永远命中不了。
    "/api/shortcodes/render": RateLimitRule(
        requests=20,
        window_seconds=60,
        key_prefix="shortcode_render",
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
            # 不套 try：`HTTPBearer(auto_error=False)` 无头时返回 None，
            # `decode_token` 内部已把 JWTError 转成 None（见 core/auth.py）。
            # 这里原本 `except Exception: identifier = None` 只会吞掉真实缺陷
            # （改名、导入路径变动等），让"按用户限流"静默退化成"按 IP 限流"。
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
        except (TypeError, ValueError) as exc:
            # 只可能是配置值不是整数（env 写错、测试 patch 成对象）。回落到规则自带阈值
            # 是安全的，但**必须留痕**：原先静默回落，运维把限流调大/调小后发现没生效，
            # 只能靠猜。其余异常（AttributeError 等）是真实缺陷，照样抛出。
            logger.warning(
                "限流阈值配置无法解析（requests_attr=%s window_attr=%s），回落到规则默认值：%s",
                requests_attr,
                window_attr,
                exc,
            )

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
                    "error_code": RATE_LIMIT_EXCEEDED,
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
