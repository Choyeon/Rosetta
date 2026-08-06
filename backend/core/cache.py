"""
缓存服务层

提供统一的缓存接口，支持：
- 生产环境：Redis 缓存
- 开发环境：内存缓存

自动根据配置切换缓存后端，对业务代码透明。
"""

import json
import logging
from abc import ABC, abstractmethod
from collections.abc import Callable
from typing import Any, ParamSpec, TypeVar

from backend.core.config import settings

logger = logging.getLogger(__name__)

P = ParamSpec("P")
T = TypeVar("T")


class CacheBackend(ABC):
    """缓存后端抽象基类"""

    @abstractmethod
    async def get(self, key: str) -> Any | None:
        """获取缓存值"""
        pass

    @abstractmethod
    async def set(self, key: str, value: Any, ttl: int | None = None) -> bool:
        """设置缓存值"""
        pass

    @abstractmethod
    async def delete(self, key: str) -> bool:
        """删除缓存"""
        pass

    @abstractmethod
    async def delete_pattern(self, pattern: str) -> int:
        """删除匹配模式的所有缓存"""
        pass

    @abstractmethod
    async def exists(self, key: str) -> bool:
        """检查缓存是否存在"""
        pass

    @abstractmethod
    async def clear(self) -> bool:
        """清空所有缓存"""
        pass

    @abstractmethod
    async def incr(self, key: str, amount: int = 1) -> int:
        """递增计数器"""
        pass

    @abstractmethod
    async def decr(self, key: str, amount: int = 1) -> int:
        """递减计数器"""
        pass


class MemoryCacheBackend(CacheBackend):
    """
    内存缓存后端

    用于开发环境，使用 Python 字典存储缓存。
    支持简单的 TTL 过期检查。
    """

    def __init__(self):
        self._store: dict[str, tuple[Any, float | None]] = {}
        self._counters: dict[str, int] = {}
        import time

        self._time = time.time

    def _is_expired(self, expires_at: float | None) -> bool:
        """检查是否过期"""
        if expires_at is None:
            return False
        return self._time() > expires_at

    async def get(self, key: str) -> Any | None:
        value, expires_at = self._store.get(key, (None, None))
        if self._is_expired(expires_at):
            del self._store[key]
            return None
        return value

    async def set(self, key: str, value: Any, ttl: int | None = None) -> bool:
        expires_at = None
        if ttl:
            expires_at = self._time() + ttl
        self._store[key] = (value, expires_at)
        return True

    async def delete(self, key: str) -> bool:
        if key in self._store:
            del self._store[key]
            return True
        return False

    async def delete_pattern(self, pattern: str) -> int:
        """删除匹配模式的缓存（简单前缀匹配）"""
        prefix = pattern.rstrip("*")
        keys_to_delete = [k for k in self._store if k.startswith(prefix)]
        for key in keys_to_delete:
            del self._store[key]
        return len(keys_to_delete)

    async def exists(self, key: str) -> bool:
        value, expires_at = self._store.get(key, (None, None))
        if self._is_expired(expires_at):
            if key in self._store:
                del self._store[key]
            return False
        return key in self._store

    async def clear(self) -> bool:
        self._store.clear()
        self._counters.clear()
        return True

    async def incr(self, key: str, amount: int = 1) -> int:
        if key not in self._counters:
            self._counters[key] = 0
        self._counters[key] += amount
        return self._counters[key]

    async def decr(self, key: str, amount: int = 1) -> int:
        if key not in self._counters:
            self._counters[key] = 0
        self._counters[key] -= amount
        return self._counters[key]


class RedisCacheBackend(CacheBackend):
    """
    Redis 缓存后端

    用于生产环境，提供高性能分布式缓存。
    """

    def __init__(self):
        self._client = None
        self._connected = False

    async def _get_client(self):
        """获取 Redis 客户端"""
        if self._client is None:
            try:
                import redis.asyncio as redis

                self._client = redis.from_url(
                    settings.redis_url,
                    encoding="utf-8",
                    decode_responses=True,
                )
                await self._client.ping()
                self._connected = True
                logger.info("Redis 连接成功")
            except Exception as e:
                logger.warning(f"Redis 连接失败，回退到内存缓存: {e}")
                self._connected = False
        return self._client

    async def get(self, key: str) -> Any | None:
        try:
            client = await self._get_client()
            if not self._connected:
                return None
            value = await client.get(key)
            if value is None:
                return None
            try:
                return json.loads(value)
            except json.JSONDecodeError:
                return value
        except Exception as e:
            logger.error(f"Redis get 错误: {e}")
            return None

    async def set(self, key: str, value: Any, ttl: int | None = None) -> bool:
        try:
            client = await self._get_client()
            if not self._connected:
                return False
            if isinstance(value, (dict, list)):
                value = json.dumps(value, ensure_ascii=False)
            elif not isinstance(value, str):
                value = str(value)
            if ttl:
                await client.setex(key, ttl, value)
            else:
                await client.set(key, value)
            return True
        except Exception as e:
            logger.error(f"Redis set 错误: {e}")
            return False

    async def delete(self, key: str) -> bool:
        try:
            client = await self._get_client()
            if not self._connected:
                return False
            await client.delete(key)
            return True
        except Exception as e:
            logger.error(f"Redis delete 错误: {e}")
            return False

    async def delete_pattern(self, pattern: str) -> int:
        try:
            client = await self._get_client()
            if not self._connected:
                return 0
            keys = []
            async for key in client.scan_iter(match=pattern):
                keys.append(key)
            if keys:
                await client.delete(*keys)
            return len(keys)
        except Exception as e:
            logger.error(f"Redis delete_pattern 错误: {e}")
            return 0

    async def exists(self, key: str) -> bool:
        try:
            client = await self._get_client()
            if not self._connected:
                return False
            return await client.exists(key) > 0
        except Exception as e:
            logger.error(f"Redis exists 错误: {e}")
            return False

    async def clear(self) -> bool:
        try:
            client = await self._get_client()
            if not self._connected:
                return False
            await client.flushdb()
            return True
        except Exception as e:
            logger.error(f"Redis clear 错误: {e}")
            return False

    async def incr(self, key: str, amount: int = 1) -> int:
        try:
            client = await self._get_client()
            if not self._connected:
                return 0
            return await client.incrby(key, amount)
        except Exception as e:
            logger.error(f"Redis incr 错误: {e}")
            return 0

    async def decr(self, key: str, amount: int = 1) -> int:
        try:
            client = await self._get_client()
            if not self._connected:
                return 0
            return await client.decrby(key, amount)
        except Exception as e:
            logger.error(f"Redis decr 错误: {e}")
            return 0

    async def close(self):
        """关闭 Redis 连接"""
        if self._client:
            await self._client.close()


class CacheService:
    """
    缓存服务

    根据配置自动选择缓存后端：
    - 生产环境启用 Redis 时使用 Redis
    - 其他情况使用内存缓存
    """

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._initialized = True

        if settings.redis_enabled:
            self._backend = RedisCacheBackend()
            logger.info("使用 Redis 缓存后端")
        else:
            self._backend = MemoryCacheBackend()
            logger.info("使用内存缓存后端")

    @property
    def backend(self) -> CacheBackend:
        return self._backend

    async def get(self, key: str) -> Any | None:
        return await self._backend.get(key)

    async def set(self, key: str, value: Any, ttl: int | None = None) -> bool:
        return await self._backend.set(key, value, ttl)

    async def delete(self, key: str) -> bool:
        return await self._backend.delete(key)

    async def delete_pattern(self, pattern: str) -> int:
        return await self._backend.delete_pattern(pattern)

    async def exists(self, key: str) -> bool:
        return await self._backend.exists(key)

    async def clear(self) -> bool:
        return await self._backend.clear()

    async def incr(self, key: str, amount: int = 1) -> int:
        return await self._backend.incr(key, amount)

    async def decr(self, key: str, amount: int = 1) -> int:
        return await self._backend.decr(key, amount)

    def cached(
        self,
        key_prefix: str,
        ttl: int = 300,
        key_builder: Callable[..., str] | None = None,
    ):
        """
        缓存装饰器

        用法:
            @cache.cached("posts", ttl=600)
            async def get_post(slug: str) -> Post:
                ...
        """

        def decorator(func: Callable[P, T]) -> Callable[P, T]:
            async def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
                if key_builder:
                    cache_key = key_builder(*args, **kwargs)
                else:
                    key_parts = [key_prefix, str(args), str(sorted(kwargs.items()))]
                    cache_key = ":".join(key_parts)

                cached_value = await self.get(cache_key)
                if cached_value is not None:
                    return cached_value

                result = await func(*args, **kwargs)

                if result is not None:
                    await self.set(cache_key, result, ttl)

                return result

            return wrapper

        return decorator


cache = CacheService()


CACHE_TTL = {
    "site_config": 3600,
    "navigations": 3600,
    "friend_links": 1800,
    "categories": 600,
    "tags": 600,
    "post_list": 300,
    "post_detail": 600,
    "user_profile": 300,
    "search_results": 60,
}

NULL_MARKER = "__NULL__"

import random


def get_cache_ttl(key: str) -> int:
    """获取缓存 TTL，添加随机偏移防止雪崩"""
    base_ttl = CACHE_TTL.get(key, 300)
    jitter = int(base_ttl * 0.1)
    return base_ttl + random.randint(-jitter, jitter)


def make_cache_key(*parts: str) -> str:
    """生成缓存键"""
    return ":".join(str(p) for p in parts)


async def invalidate_cache(pattern: str) -> int:
    """使缓存失效"""
    return await cache.delete_pattern(f"{pattern}*")


async def get_or_set_with_null(
    key: str,
    fetch_func: Callable[[], Any],
    ttl: int = 300,
    null_ttl: int = 60,
) -> Any | None:
    """获取或设置缓存，支持空值缓存防止穿透

    Args:
        key: 缓存键
        fetch_func: 获取数据的函数
        ttl: 正常数据的缓存时间
        null_ttl: 空值的缓存时间（防止穿透）

    Returns:
        缓存的数据或 None
    """
    cached = await cache.get(key)
    if cached == NULL_MARKER:
        return None
    if cached is not None:
        return cached

    result = await fetch_func()

    if result is None:
        await cache.set(key, NULL_MARKER, null_ttl)
        return None

    await cache.set(key, result, ttl)
    return result
