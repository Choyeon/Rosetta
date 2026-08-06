"""
多级缓存模块

提供高性能的多级缓存系统，支持：
- 一级缓存：本地内存缓存（LRU 算法，快速访问）
- 二级缓存：Redis 缓存（分布式共享）
- 缓存穿透保护（空值缓存）
- 缓存击穿保护（分布式锁）
- 统一的缓存键生成器
"""

import asyncio
import hashlib
import json
import logging
import threading
import time
from collections import OrderedDict
from collections.abc import Callable
from dataclasses import dataclass, field
from functools import wraps
from typing import Any, ParamSpec, TypeVar

from backend.core.config import settings
from backend.core.distributed_lock import distributed_lock

logger = logging.getLogger(__name__)

P = ParamSpec("P")
T = TypeVar("T")

NULL_MARKER = "__NULL__"


@dataclass
class CacheEntry:
    """缓存条目"""

    value: Any
    expires_at: float | None = None
    created_at: float = field(default_factory=time.time)

    def is_expired(self) -> bool:
        """检查是否过期"""
        if self.expires_at is None:
            return False
        return time.time() > self.expires_at


class LocalCache:
    """
    本地内存缓存

    基于 LRU 算法的本地内存缓存，支持：
    - TTL 过期
    - 线程安全
    - 最大容量限制
    - LRU 淘汰策略
    """

    def __init__(
        self,
        max_size: int = 1000,
        default_ttl: int = 300,
    ):
        """
        初始化本地缓存

        Args:
            max_size: 最大缓存条目数
            default_ttl: 默认过期时间（秒）
        """
        self._cache: OrderedDict[str, CacheEntry] = OrderedDict()
        self._lock = threading.RLock()
        self._max_size = max_size
        self._default_ttl = default_ttl
        self._hits = 0
        self._misses = 0

    def get(self, key: str) -> Any | None:
        """
        获取缓存值

        Args:
            key: 缓存键

        Returns:
            缓存值，不存在或过期返回 None
        """
        with self._lock:
            if key not in self._cache:
                self._misses += 1
                return None

            entry = self._cache[key]

            if entry.is_expired():
                del self._cache[key]
                self._misses += 1
                return None

            self._cache.move_to_end(key)
            self._hits += 1
            return entry.value

    def set(self, key: str, value: Any, ttl: int | None = None) -> bool:
        """
        设置缓存值

        Args:
            key: 缓存键
            value: 缓存值
            ttl: 过期时间（秒），None 使用默认值

        Returns:
            是否设置成功
        """
        with self._lock:
            if key in self._cache:
                del self._cache[key]

            if len(self._cache) >= self._max_size:
                self._cache.popitem(last=False)

            effective_ttl = ttl if ttl is not None else self._default_ttl
            expires_at = time.time() + effective_ttl if effective_ttl > 0 else None

            self._cache[key] = CacheEntry(value=value, expires_at=expires_at)
            return True

    def delete(self, key: str) -> bool:
        """
        删除缓存

        Args:
            key: 缓存键

        Returns:
            是否删除成功
        """
        with self._lock:
            if key in self._cache:
                del self._cache[key]
                return True
            return False

    def delete_pattern(self, pattern: str) -> int:
        """
        删除匹配模式的所有缓存

        Args:
            pattern: 匹配模式（支持前缀匹配 *）

        Returns:
            删除的条目数
        """
        prefix = pattern.rstrip("*")
        with self._lock:
            keys_to_delete = [k for k in self._cache if k.startswith(prefix)]
            for key in keys_to_delete:
                del self._cache[key]
            return len(keys_to_delete)

    def exists(self, key: str) -> bool:
        """
        检查缓存是否存在

        Args:
            key: 缓存键

        Returns:
            是否存在
        """
        with self._lock:
            if key not in self._cache:
                return False
            entry = self._cache[key]
            if entry.is_expired():
                del self._cache[key]
                return False
            return True

    def clear(self) -> bool:
        """
        清空所有缓存

        Returns:
            是否清空成功
        """
        with self._lock:
            self._cache.clear()
            self._hits = 0
            self._misses = 0
            return True

    def get_stats(self) -> dict[str, Any]:
        """
        获取缓存统计信息

        Returns:
            统计信息字典
        """
        with self._lock:
            total = self._hits + self._misses
            hit_rate = self._hits / total * 100 if total > 0 else 0
            return {
                "size": len(self._cache),
                "max_size": self._max_size,
                "hits": self._hits,
                "misses": self._misses,
                "hit_rate": f"{hit_rate:.2f}%",
            }

    def cleanup_expired(self) -> int:
        """
        清理过期条目

        Returns:
            清理的条目数
        """
        with self._lock:
            expired_keys = [k for k, v in self._cache.items() if v.is_expired()]
            for key in expired_keys:
                del self._cache[key]
            return len(expired_keys)


class CacheKeyBuilder:
    """
    缓存键生成器

    提供统一的缓存键生成，支持：
    - 命名空间
    - 版本控制
    - 参数序列化
    """

    DEFAULT_NAMESPACE = "rosetta"
    DEFAULT_VERSION = "v1"

    def __init__(
        self,
        namespace: str = DEFAULT_NAMESPACE,
        version: str = DEFAULT_VERSION,
    ):
        """
        初始化缓存键生成器

        Args:
            namespace: 命名空间
            version: 版本号
        """
        self._namespace = namespace
        self._version = version

    def build(self, *parts: str | int, suffix: str | None = None) -> str:
        """
        构建缓存键

        Args:
            *parts: 键的各个部分
            suffix: 可选的后缀

        Returns:
            完整的缓存键
        """
        key_parts = [self._namespace, self._version] + [str(p) for p in parts]
        if suffix:
            key_parts.append(suffix)
        return ":".join(key_parts)

    def build_with_hash(
        self,
        prefix: str,
        *args: Any,
        **kwargs: Any,
    ) -> str:
        """
        基于参数哈希构建缓存键

        Args:
            prefix: 键前缀
            *args: 位置参数
            **kwargs: 关键字参数

        Returns:
            完整的缓存键
        """
        params_str = json.dumps({"args": args, "kwargs": sorted(kwargs.items())}, default=str)
        params_hash = hashlib.md5(params_str.encode()).hexdigest()[:8]
        return self.build(prefix, params_hash)

    def build_pattern(self, *parts: str | int) -> str:
        """
        构建缓存键模式（用于批量删除）

        Args:
            *parts: 键的各个部分

        Returns:
            缓存键模式
        """
        return self.build(*parts) + "*"

    @staticmethod
    def sanitize(value: str) -> str:
        """
        清理键值中的特殊字符

        Args:
            value: 原始值

        Returns:
            清理后的值
        """
        return value.replace(":", "_").replace(" ", "_").replace("\n", "_")

    def with_namespace(self, namespace: str) -> "CacheKeyBuilder":
        """
        创建新的命名空间生成器

        Args:
            namespace: 新的命名空间

        Returns:
            新的缓存键生成器
        """
        return CacheKeyBuilder(namespace=namespace, version=self._version)

    def with_version(self, version: str) -> "CacheKeyBuilder":
        """
        创建新版本的生成器

        Args:
            version: 新的版本号

        Returns:
            新的缓存键生成器
        """
        return CacheKeyBuilder(namespace=self._namespace, version=version)


class TwoLevelCache:
    """
    二级缓存系统

    实现多级缓存架构：
    - 一级缓存：本地内存（快速访问）
    - 二级缓存：Redis（分布式共享）

    支持 Cache-Aside 模式，自动同步两级缓存。
    """

    def __init__(
        self,
        local_cache: LocalCache | None = None,
        local_ttl_ratio: float = 0.3,
        enable_local_cache: bool = True,
    ):
        """
        初始化二级缓存

        Args:
            local_cache: 本地缓存实例，None 则自动创建
            local_ttl_ratio: 本地缓存 TTL 占 Redis TTL 的比例
            enable_local_cache: 是否启用本地缓存
        """
        self._local_cache = local_cache or LocalCache()
        self._local_ttl_ratio = local_ttl_ratio
        self._enable_local_cache = enable_local_cache
        self._redis_client = None
        self._redis_connected = False

    async def _get_redis_client(self):
        """获取 Redis 客户端"""
        if self._redis_client is None:
            if not settings.redis_enabled:
                logger.debug("Redis 未启用，仅使用本地缓存")
                return None
            try:
                import redis.asyncio as redis

                self._redis_client = redis.from_url(
                    settings.redis_url,
                    encoding="utf-8",
                    decode_responses=True,
                )
                await self._redis_client.ping()
                self._redis_connected = True
                logger.info("二级缓存 Redis 连接成功")
            except Exception as e:
                logger.warning(f"二级缓存 Redis 连接失败: {e}")
                self._redis_connected = False
        return self._redis_client

    async def get(self, key: str) -> Any | None:
        """
        获取缓存值（先查本地，再查 Redis）

        Args:
            key: 缓存键

        Returns:
            缓存值
        """
        if self._enable_local_cache:
            local_value = self._local_cache.get(key)
            if local_value is not None:
                if local_value == NULL_MARKER:
                    return None
                logger.debug(f"本地缓存命中: {key}")
                return local_value

        redis_client = await self._get_redis_client()
        if redis_client and self._redis_connected:
            try:
                redis_value = await redis_client.get(key)
                if redis_value is not None:
                    try:
                        value = json.loads(redis_value)
                    except json.JSONDecodeError:
                        value = redis_value

                    if value == NULL_MARKER:
                        return None

                    if self._enable_local_cache:
                        local_ttl = await self._get_local_ttl(key, redis_client)
                        self._local_cache.set(key, value, ttl=local_ttl)

                    logger.debug(f"Redis 缓存命中: {key}")
                    return value
            except Exception as e:
                logger.error(f"Redis get 错误: {e}")

        logger.debug(f"缓存未命中: {key}")
        return None

    async def set(
        self,
        key: str,
        value: Any,
        ttl: int = 300,
        skip_local: bool = False,
    ) -> bool:
        """
        设置缓存值（同时设置本地和 Redis）

        Args:
            key: 缓存键
            value: 缓存值
            ttl: 过期时间（秒）
            skip_local: 是否跳过本地缓存

        Returns:
            是否设置成功
        """
        success = True

        if self._enable_local_cache and not skip_local:
            local_ttl = int(ttl * self._local_ttl_ratio)
            self._local_cache.set(key, value, ttl=local_ttl)

        redis_client = await self._get_redis_client()
        if redis_client and self._redis_connected:
            try:
                if isinstance(value, (dict, list)):
                    redis_value = json.dumps(value, ensure_ascii=False)
                elif not isinstance(value, str):
                    redis_value = str(value)
                else:
                    redis_value = value

                await redis_client.setex(key, ttl, redis_value)
                logger.debug(f"Redis 缓存设置成功: {key}, TTL: {ttl}s")
            except Exception as e:
                logger.error(f"Redis set 错误: {e}")
                success = False

        return success

    async def set_null(self, key: str, ttl: int = 60) -> bool:
        """
        设置空值缓存（防止缓存穿透）

        Args:
            key: 缓存键
            ttl: 空值缓存时间

        Returns:
            是否设置成功
        """
        if self._enable_local_cache:
            self._local_cache.set(key, NULL_MARKER, ttl=ttl)

        redis_client = await self._get_redis_client()
        if redis_client and self._redis_connected:
            try:
                await redis_client.setex(key, ttl, json.dumps(NULL_MARKER))
                return True
            except Exception as e:
                logger.error(f"Redis set_null 错误: {e}")

        return False

    async def delete(self, key: str) -> bool:
        """
        删除缓存（同时删除本地和 Redis）

        Args:
            key: 缓存键

        Returns:
            是否删除成功
        """
        if self._enable_local_cache:
            self._local_cache.delete(key)

        redis_client = await self._get_redis_client()
        if redis_client and self._redis_connected:
            try:
                await redis_client.delete(key)
                return True
            except Exception as e:
                logger.error(f"Redis delete 错误: {e}")

        return False

    async def delete_pattern(self, pattern: str) -> int:
        """
        删除匹配模式的所有缓存

        Args:
            pattern: 匹配模式

        Returns:
            删除的条目数
        """
        local_deleted = 0
        if self._enable_local_cache:
            local_deleted = self._local_cache.delete_pattern(pattern)

        redis_deleted = 0
        redis_client = await self._get_redis_client()
        if redis_client and self._redis_connected:
            try:
                keys = []
                async for key in redis_client.scan_iter(match=pattern):
                    keys.append(key)
                if keys:
                    redis_deleted = await redis_client.delete(*keys)
            except Exception as e:
                logger.error(f"Redis delete_pattern 错误: {e}")

        return max(local_deleted, redis_deleted)

    async def invalidate(self, key: str) -> bool:
        """
        使缓存失效（删除本地和 Redis）

        Args:
            key: 缓存键

        Returns:
            是否成功
        """
        return await self.delete(key)

    async def invalidate_pattern(self, pattern: str) -> int:
        """
        使匹配模式的缓存失效

        Args:
            pattern: 匹配模式

        Returns:
            删除的条目数
        """
        return await self.delete_pattern(pattern)

    async def get_or_set(
        self,
        key: str,
        fetch_func: Callable[[], Any],
        ttl: int = 300,
        null_ttl: int = 60,
        lock_timeout: int = 10,
    ) -> Any | None:
        """
        获取或设置缓存（支持穿透和击穿保护）

        Args:
            key: 缓存键
            fetch_func: 获取数据的函数
            ttl: 正常数据的缓存时间
            null_ttl: 空值的缓存时间（防止穿透）
            lock_timeout: 分布式锁超时时间（防止击穿）

        Returns:
            缓存的数据
        """
        cached = await self.get(key)
        if cached is not None:
            return cached

        if settings.redis_enabled:
            async with distributed_lock(f"cache:{key}", timeout=lock_timeout):
                cached = await self.get(key)
                if cached is not None:
                    return cached

                result = await self._execute_fetch(fetch_func)

                if result is None:
                    await self.set_null(key, ttl=null_ttl)
                    return None

                await self.set(key, result, ttl=ttl)
                return result
        else:
            result = await self._execute_fetch(fetch_func)

            if result is None:
                await self.set_null(key, ttl=null_ttl)
                return None

            await self.set(key, result, ttl=ttl)
            return result

    async def _execute_fetch(self, fetch_func: Callable[[], Any]) -> Any:
        """执行数据获取函数"""
        if asyncio.iscoroutinefunction(fetch_func):
            return await fetch_func()
        return fetch_func()

    async def _get_local_ttl(self, key: str, redis_client) -> int:
        """获取本地缓存的 TTL"""
        try:
            redis_ttl = await redis_client.ttl(key)
            if redis_ttl > 0:
                return int(redis_ttl * self._local_ttl_ratio)
        except Exception:
            pass
        return int(300 * self._local_ttl_ratio)

    def get_local_stats(self) -> dict[str, Any]:
        """获取本地缓存统计信息"""
        return self._local_cache.get_stats()

    async def close(self):
        """关闭 Redis 连接"""
        if self._redis_client:
            await self._redis_client.close()
            self._redis_client = None


def cached(
    key_prefix: str,
    ttl: int = 300,
    null_ttl: int = 60,
    lock_timeout: int = 10,
    key_builder: Callable[..., str] | None = None,
    cache_instance: TwoLevelCache | None = None,
    skip_local: bool = False,
):
    """
    增强版缓存装饰器

    支持多级缓存、穿透保护、击穿保护。

    Args:
        key_prefix: 缓存键前缀
        ttl: 正常数据的缓存时间
        null_ttl: 空值的缓存时间（防止穿透）
        lock_timeout: 分布式锁超时时间（防止击穿）
        key_builder: 自定义键生成函数
        cache_instance: 缓存实例，None 则使用全局实例
        skip_local: 是否跳过本地缓存

    Returns:
        装饰器函数

    Example:
        @cached("posts", ttl=600)
        async def get_post(slug: str) -> Post:
            ...

        @cached("user", key_builder=lambda args, kwargs: f"user:{kwargs['user_id']}")
        async def get_user(user_id: int) -> User:
            ...
    """
    _cache = cache_instance

    def decorator(func: Callable[P, T]) -> Callable[P, T]:
        @wraps(func)
        async def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
            nonlocal _cache
            if _cache is None:
                _cache = two_level_cache

            if key_builder:
                cache_key = key_builder(args, kwargs)
            else:
                cache_key = CacheKeyBuilder().build_with_hash(key_prefix, *args, **kwargs)

            async def fetch():
                return (
                    await func(*args, **kwargs)
                    if asyncio.iscoroutinefunction(func)
                    else func(*args, **kwargs)
                )

            if skip_local:
                cached_value = await _cache.get(cache_key)
                if cached_value is not None:
                    return cached_value

                result = await fetch()

                if result is not None:
                    await _cache.set(cache_key, result, ttl=ttl, skip_local=True)

                return result

            return await _cache.get_or_set(
                cache_key,
                fetch,
                ttl=ttl,
                null_ttl=null_ttl,
                lock_timeout=lock_timeout,
            )

        return wrapper

    return decorator


def cached_simple(
    key_prefix: str,
    ttl: int = 300,
):
    """
    简单缓存装饰器（无穿透/击穿保护）

    适用于对穿透和击穿不敏感的场景。

    Args:
        key_prefix: 缓存键前缀
        ttl: 缓存时间

    Returns:
        装饰器函数
    """

    def decorator(func: Callable[P, T]) -> Callable[P, T]:
        @wraps(func)
        async def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
            cache_key = CacheKeyBuilder().build_with_hash(key_prefix, *args, **kwargs)

            cached_value = await two_level_cache.get(cache_key)
            if cached_value is not None:
                return cached_value

            if asyncio.iscoroutinefunction(func):
                result = await func(*args, **kwargs)
            else:
                result = func(*args, **kwargs)

            if result is not None:
                await two_level_cache.set(cache_key, result, ttl=ttl)

            return result

        return wrapper

    return decorator


two_level_cache = TwoLevelCache()

cache_key_builder = CacheKeyBuilder()
