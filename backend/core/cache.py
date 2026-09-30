"""
缓存服务层

提供统一的缓存接口，支持：
- 生产环境：Redis 缓存
- 开发环境：内存缓存

自动根据配置切换缓存后端，对业务代码透明。
"""

import json
import logging
import random
import time
from abc import ABC, abstractmethod
from collections.abc import Callable
from typing import Any, ParamSpec, TypeVar

from pydantic import BaseModel

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

    async def get_stats(self) -> dict[str, Any]:
        """返回后端状态快照：keys 数量、内存使用字节数（如有）、命中率。默认实现返回空字典，子类可重写。"""
        return {}


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
        self._hits: int = 0
        self._misses: int = 0

    def _is_expired(self, expires_at: float | None) -> bool:
        """检查是否过期"""
        if expires_at is None:
            return False
        return self._time() > expires_at

    async def get(self, key: str) -> Any | None:
        value, expires_at = self._store.get(key, (None, None))
        if self._is_expired(expires_at):
            if key in self._store:
                del self._store[key]
            self._misses += 1
            return None
        self._hits += 1
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

    async def get_stats(self) -> dict[str, Any]:
        # 清理一次过期键，keys 数更准确
        expired_keys = [k for k, (_, exp) in self._store.items() if self._is_expired(exp)]
        for k in expired_keys:
            del self._store[k]
        total = self._hits + self._misses
        hit_rate = (self._hits / total) if total > 0 else 0.0
        # 粗略估算内存占用：每个 entry 按 (key 长度 + pickle value 字节数) 近似
        size_bytes: int | None = None
        try:
            import sys

            size_bytes = sys.getsizeof(self._store)
            for k, (v, _) in self._store.items():
                size_bytes += sys.getsizeof(k) + sys.getsizeof(v)
        except (TypeError, ValueError, MemoryError) as e:
            # 估算失败只影响"内存占用"这一个展示字段，返回 None 让 UI 显示未知。
            logger.debug(f"[cache] 内存占用估算失败: {e}")
            size_bytes = None
        return {
            "keys": len(self._store),
            "memory_used_bytes": size_bytes,
            "hits": self._hits,
            "misses": self._misses,
            "hit_rate": hit_rate,
        }


class RedisCacheBackend(CacheBackend):
    """
    Redis 缓存后端

    用于生产环境，提供高性能分布式缓存。
    Redis 不可用时**真正**降级到内存后端继续服务，而不是把整套缓存变成 no-op。
    """

    # 连接失败后的重试间隔：太短会在 Redis 宕机时被重试风暴打满，
    # 太长则恢复后仍长时间停留在内存兜底。
    _RECONNECT_INTERVAL_SECONDS = 30.0

    def __init__(self):
        self._client = None
        self._connected = False
        self._retry_after = 0.0
        self._fallback = MemoryCacheBackend()

    async def _get_client(self):
        """获取 Redis 客户端；未连接时返回 None，由调用方走内存兜底。

        失败后必须把 ``_client`` 留成 None，否则下次调用会因为 ``_client is not None``
        直接跳过建连分支，``_connected`` 永远停在 False——Redis 恢复后缓存仍然是死的，
        只能靠重启进程解决。
        """
        if self._client is not None:
            return self._client
        now = time.monotonic()
        if now < self._retry_after:
            return None
        try:
            import redis.asyncio as redis

            client = redis.from_url(
                settings.redis_url,
                encoding="utf-8",
                decode_responses=True,
            )
            await client.ping()
            self._client = client
            self._connected = True
            self._retry_after = 0.0
            logger.info("Redis 连接成功")
        except Exception as e:
            logger.warning(f"Redis 连接失败，回退到内存缓存: {e}")
            self._client = None
            self._connected = False
            self._retry_after = now + self._RECONNECT_INTERVAL_SECONDS
        return self._client

    def _degrade(self, op: str, error: Exception) -> None:
        """标记 Redis 不可用，让本次与后续请求走内存兜底。"""
        logger.error(f"Redis {op} 错误: {error}")
        self._connected = False
        self._retry_after = time.monotonic() + self._RECONNECT_INTERVAL_SECONDS

    async def get(self, key: str) -> Any | None:
        try:
            client = await self._get_client()
            if client is None:
                return await self._fallback.get(key)
            value = await client.get(key)
            if value is None:
                return None
            try:
                return json.loads(value)
            except json.JSONDecodeError:
                return value
        except Exception as e:
            self._degrade("get", e)
            return await self._fallback.get(key)

    async def set(self, key: str, value: Any, ttl: int | None = None) -> bool:
        try:
            client = await self._get_client()
            if client is None:
                return await self._fallback.set(key, value, ttl)
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
            self._degrade("set", e)
            return await self._fallback.set(key, value, ttl)

    async def delete(self, key: str) -> bool:
        try:
            client = await self._get_client()
            # 兜底里可能有降级期间写入的同名键，无论 Redis 是否可用都要一起清，
            # 否则"降级时写脏、恢复后删不掉"。
            await self._fallback.delete(key)
            if client is None:
                return True
            await client.delete(key)
            return True
        except Exception as e:
            self._degrade("delete", e)
            return await self._fallback.delete(key)

    async def delete_pattern(self, pattern: str) -> int:
        try:
            client = await self._get_client()
            fallback_deleted = await self._fallback.delete_pattern(pattern)
            if client is None:
                return fallback_deleted
            keys = []
            async for key in client.scan_iter(match=pattern):
                keys.append(key)
            if keys:
                await client.delete(*keys)
            return len(keys)
        except Exception as e:
            self._degrade("delete_pattern", e)
            return await self._fallback.delete_pattern(pattern)

    async def exists(self, key: str) -> bool:
        try:
            client = await self._get_client()
            if client is None:
                return await self._fallback.exists(key)
            return await client.exists(key) > 0
        except Exception as e:
            self._degrade("exists", e)
            return await self._fallback.exists(key)

    async def clear(self) -> bool:
        try:
            client = await self._get_client()
            await self._fallback.clear()
            if client is None:
                return True
            await client.flushdb()
            return True
        except Exception as e:
            self._degrade("clear", e)
            return False

    async def incr(self, key: str, amount: int = 1) -> int:
        try:
            client = await self._get_client()
            if client is None:
                return await self._fallback.incr(key, amount)
            return await client.incrby(key, amount)
        except Exception as e:
            self._degrade("incr", e)
            return await self._fallback.incr(key, amount)

    async def decr(self, key: str, amount: int = 1) -> int:
        try:
            client = await self._get_client()
            if client is None:
                return await self._fallback.decr(key, amount)
            return await client.decrby(key, amount)
        except Exception as e:
            self._degrade("decr", e)
            return await self._fallback.decr(key, amount)

    async def get_stats(self) -> dict[str, Any]:
        try:
            client = await self._get_client()
            if client is None:
                stats = await self._fallback.get_stats()
                # degraded=True 让监控页能区分"Redis 里 0 个键"和"Redis 挂了正在吃内存兜底"
                stats.update({"connected": False, "degraded": True})
                return stats
            info = await client.info("stats")
            db_info = await client.info("keyspace")
            db_key = next((k for k in db_info.keys() if k.startswith("db")), None)
            total_keys: int = 0
            if db_key and isinstance(db_info[db_key], dict):
                total_keys = int(db_info[db_key].get("keys", 0) or 0)
            hits = int((info or {}).get("keyspace_hits", 0) or 0)
            misses = int((info or {}).get("keyspace_misses", 0) or 0)
            total = hits + misses
            hit_rate = (hits / total) if total > 0 else 0.0
            memory: int | None = None
            try:
                mem_info = await client.info("memory")
                memory = int((mem_info or {}).get("used_memory", 0) or 0)
            except (TypeError, ValueError) as e:
                # 连接层异常由外层统一处理；这里只兜"服务端回了非数字字段"的解析噪声。
                logger.debug(f"[cache] Redis used_memory 解析失败: {e}")
                memory = None
            return {
                "keys": total_keys,
                "memory_used_bytes": memory,
                "hits": hits,
                "misses": misses,
                "hit_rate": hit_rate,
                "connected": True,
                "degraded": False,
            }
        except Exception as e:
            logger.warning(f"Redis stats 读取失败: {e}")
            return {
                "keys": 0,
                "memory_used_bytes": None,
                "hit_rate": None,
                "connected": False,
                "degraded": True,
                "error": str(e),
            }

    async def close(self):
        """关闭 Redis 连接"""
        if self._client:
            await self._client.aclose()
        self._client = None
        self._connected = False


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
        self._backend: CacheBackend | None = None

    @property
    def backend(self) -> CacheBackend:
        """缓存后端，首次使用时才绑定。

        早先是 ``__init__`` 里直接读 ``settings.redis_enabled`` 建实例，而模块级单例
        ``cache = CacheService()`` 在 import 阶段就执行了——任何在 import 之后才改
        settings 的路径（测试 conftest 全局 patch、启动期按环境重算配置）都来不及生效，
        进程会握着连不上的 Redis 后端跑完整生命周期。延后到这里，绑定时机与
        "配置最终值"对齐。
        """
        if self._backend is None:
            if settings.redis_enabled:
                self._backend = RedisCacheBackend()
                logger.info("使用 Redis 缓存后端")
            else:
                self._backend = MemoryCacheBackend()
                logger.info("使用内存缓存后端")
        return self._backend

    async def get(self, key: str) -> Any | None:
        return await self.backend.get(key)

    async def set(self, key: str, value: Any, ttl: int | None = None) -> bool:
        return await self.backend.set(key, self._serialize(value), ttl)

    @staticmethod
    def _serialize(value: Any) -> Any:
        """写入前把 Pydantic 模型压成 JSON 友好的 dict/list。

        两个后端对"非 dict/list 且非 str"的处理并不一致：内存后端原样存对象，Redis 后端
        走 ``str(value)`` 存成 Python repr。于是 ``cache.set(key, SomeResponse)`` 这种写法
        在开发环境一切正常，生产环境读回来是一串 ``items=[AlbumResponse(id=1, ...)]``，
        response_model 校验直接 500（相册列表 / 相册详情 / 活动流都踩过这个坑）。
        在唯一入口处统一序列化，让 dev 与 prod 存到同一个字节形态，也让内存后端不再
        把可变模型对象跨请求共享出去。
        """
        if isinstance(value, BaseModel):
            return value.model_dump(mode="json")
        if isinstance(value, list):
            return [v.model_dump(mode="json") if isinstance(v, BaseModel) else v for v in value]
        return value

    async def delete(self, key: str) -> bool:
        return await self.backend.delete(key)

    async def delete_pattern(self, pattern: str) -> int:
        return await self.backend.delete_pattern(pattern)

    async def exists(self, key: str) -> bool:
        return await self.backend.exists(key)

    async def clear(self) -> bool:
        return await self.backend.clear()

    async def incr(self, key: str, amount: int = 1) -> int:
        return await self.backend.incr(key, amount)

    async def decr(self, key: str, amount: int = 1) -> int:
        return await self.backend.decr(key, amount)

    async def get_stats(self) -> dict[str, Any]:
        return await self.backend.get_stats()

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


def get_cache_ttl(key: str) -> int:
    """获取缓存 TTL，添加随机偏移防止雪崩"""
    base_ttl = CACHE_TTL.get(key, 300)
    jitter = int(base_ttl * 0.1)
    return base_ttl + random.randint(-jitter, jitter)


def make_cache_key(*parts: str) -> str:
    """生成缓存键"""
    return ":".join(str(p) for p in parts)


# 分类 / 标签列表的键位。两者返回"完整 i18n dict"、与请求语言无关，因此读侧、写侧
# 与启动预热器必须共用同一个常量。曾经预热器按语言写 ``categories:zh`` / ``tags:ja``
# 等 8 个键，而路由读的是 ``*:raw-i18n``：每次启动写入的条目永远命中不了，
# 后台"预热 N 项"是假数字，首访延迟也没有改善。
CACHE_KEY_CATEGORIES = make_cache_key("categories", "raw-i18n")
CACHE_KEY_TAGS = make_cache_key("tags", "raw-i18n")


async def invalidate_cache(pattern: str) -> int:
    """使缓存失效"""
    return await cache.delete_pattern(f"{pattern}*")


async def invalidate_post_detail_cache(*slugs: str | None) -> int:
    """按 slug 删除文章详情缓存（覆盖全部语言），返回删除条数。

    详情键形如 ``post:{slug}:{language}``，不在 ``posts`` 前缀下，因此写侧习惯性
    调用的 ``invalidate_cache("posts")`` 命中不了它。凡是让旧正文失效的操作——删除、
    改名、转草稿、加访问密码——都必须显式调用本函数，否则缓存会在 TTL 内继续把
    已下线/已删除的内容端给匿名访客。改名时把旧 slug 一起传进来。
    """
    # 延迟导入：LANGUAGE_CODES 来自 i18n，避免核心缓存反向依赖请求语言层
    from backend.core.i18n import LANGUAGE_CODES

    deleted = 0
    for slug in {s for s in slugs if s}:
        for lang_code in LANGUAGE_CODES:
            if await cache.delete(make_cache_key("post", slug, lang_code)):
                deleted += 1
    return deleted


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
