"""
缓存服务层

提供统一的缓存管理接口，支持：
- 多级缓存（本地 + Redis）
- 缓存预热
- 缓存失效策略
- 缓存统计
"""

import logging
from collections.abc import Callable
from typing import Any

from backend.core.cache_v2 import (
    CacheKeyBuilder,
    TwoLevelCache,
    cache_key_builder,
    two_level_cache,
)
from backend.core.cache_warmer import CacheWarmer, cache_warmer

logger = logging.getLogger(__name__)


class CacheService:
    """
    缓存服务类

    提供统一的缓存管理接口，封装二级缓存操作。

    Attributes:
        cache: 二级缓存实例
        key_builder: 缓存键生成器
        warmer: 缓存预热器

    Example:
        >>> cache_service = CacheService()
        >>> await cache_service.set("user:1", user_data, ttl=3600)
        >>> data = await cache_service.get("user:1")
    """

    def __init__(
        self,
        cache: TwoLevelCache | None = None,
        key_builder: CacheKeyBuilder | None = None,
        warmer: CacheWarmer | None = None,
    ):
        """
        初始化缓存服务

        Args:
            cache: 二级缓存实例，None 则使用全局实例
            key_builder: 缓存键生成器，None 则使用全局实例
            warmer: 缓存预热器，None 则使用全局实例
        """
        self._cache = cache or two_level_cache
        self._key_builder = key_builder or cache_key_builder
        self._warmer = warmer or cache_warmer

    async def get(self, key: str) -> Any | None:
        """
        获取缓存值

        Args:
            key: 缓存键

        Returns:
            缓存值，不存在返回 None
        """
        return await self._cache.get(key)

    async def set(
        self,
        key: str,
        value: Any,
        ttl: int = 300,
        skip_local: bool = False,
    ) -> bool:
        """
        设置缓存值

        Args:
            key: 缓存键
            value: 缓存值
            ttl: 过期时间（秒）
            skip_local: 是否跳过本地缓存

        Returns:
            是否设置成功
        """
        return await self._cache.set(key, value, ttl=ttl, skip_local=skip_local)

    async def delete(self, key: str) -> bool:
        """
        删除缓存

        Args:
            key: 缓存键

        Returns:
            是否删除成功
        """
        return await self._cache.delete(key)

    async def invalidate_pattern(self, pattern: str) -> int:
        """
        使匹配模式的缓存失效

        Args:
            pattern: 匹配模式（支持通配符 *）

        Returns:
            删除的条目数
        """
        return await self._cache.invalidate_pattern(pattern)

    async def get_or_set(
        self,
        key: str,
        fetch_func: Callable[[], Any],
        ttl: int = 300,
        null_ttl: int = 60,
        lock_timeout: int = 10,
    ) -> Any | None:
        """
        获取或设置缓存

        如果缓存不存在，则调用 fetch_func 获取数据并缓存。

        Args:
            key: 缓存键
            fetch_func: 获取数据的函数
            ttl: 正常数据的缓存时间
            null_ttl: 空值的缓存时间（防止穿透）
            lock_timeout: 分布式锁超时时间（防止击穿）

        Returns:
            缓存的数据
        """
        return await self._cache.get_or_set(
            key,
            fetch_func,
            ttl=ttl,
            null_ttl=null_ttl,
            lock_timeout=lock_timeout,
        )

    async def warmup(self) -> dict[str, Any]:
        """
        执行缓存预热

        预热热点数据到缓存，包括站点配置、导航、分类、标签等。

        Returns:
            预热结果摘要
        """
        return await self._warmer.warmup_all()

    async def warmup_task(self, task_name: str) -> dict[str, Any]:
        """
        执行单个预热任务

        Args:
            task_name: 任务名称（site_config, navigations, categories, tags, friend_links）

        Returns:
            预热任务结果
        """
        result = await self._warmer.warmup_task(task_name)
        return result.to_dict()

    def get_warmup_status(self) -> dict[str, Any]:
        """
        获取预热状态

        Returns:
            预热状态信息
        """
        return self._warmer.get_status()

    def get_local_stats(self) -> dict[str, Any]:
        """
        获取本地缓存统计信息

        Returns:
            统计信息字典
        """
        return self._cache.get_local_stats()

    def build_key(self, *parts: str | int, suffix: str | None = None) -> str:
        """
        构建缓存键

        Args:
            *parts: 键的各个部分
            suffix: 可选的后缀

        Returns:
            完整的缓存键
        """
        return self._key_builder.build(*parts, suffix=suffix)

    def build_key_with_hash(
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
        return self._key_builder.build_with_hash(prefix, *args, **kwargs)

    def build_pattern(self, *parts: str | int) -> str:
        """
        构建缓存键模式

        Args:
            *parts: 键的各个部分

        Returns:
            缓存键模式（用于批量删除）
        """
        return self._key_builder.build_pattern(*parts)

    async def invalidate_user_cache(self, user_id: int) -> int:
        """删除该用户在二级缓存里的全部键族，返回删除条数。

        读侧其实有三族键：``user:{id}``、``user_profile:{id}``（公开资料，含
        preferences）、``user_stats:{id}``。旧实现只删 ``build_pattern("user", id)``
        → ``rosetta:v1:user:<id>*``，而 ``user_profile`` 是**另一个前缀**，压根不匹配。
        后果：用户改完隐私开关 / 头像 / 昵称后，公开资料页最长 ``USER_PROFILE_TTL``
        （300s）仍返回旧值——"关掉邮箱显示却没生效"这类反馈就出自这条路径。
        三族都是精确键名，逐个删即可，不要用前缀通配（``user:1*`` 会顺带命中
        ``user:10``、``user:11``，白打一批数据库）。
        """
        deleted = 0
        for prefix in ("user", "user_profile", "user_stats"):
            if await self.delete(self.build_key(prefix, user_id)):
                deleted += 1
        return deleted

    async def invalidate_post_cache(self, post_id: int | None = None) -> int:
        """
        使文章相关缓存失效

        Args:
            post_id: 文章 ID，None 则清除所有文章缓存

        Returns:
            删除的条目数
        """
        if post_id is not None:
            pattern = self.build_pattern("post", post_id)
        else:
            pattern = self.build_pattern("post")
        return await self.invalidate_pattern(pattern)

    async def invalidate_category_cache(self) -> int:
        """
        使分类相关缓存失效

        Returns:
            删除的条目数
        """
        pattern = self.build_pattern("categories")
        return await self.invalidate_pattern(pattern)

    async def invalidate_tag_cache(self) -> int:
        """
        使标签相关缓存失效

        Returns:
            删除的条目数
        """
        pattern = self.build_pattern("tags")
        return await self.invalidate_pattern(pattern)

    async def invalidate_site_cache(self) -> int:
        """
        使站点配置缓存失效

        Returns:
            删除的条目数
        """
        pattern = self.build_pattern("site_config")
        return await self.invalidate_pattern(pattern)

    async def invalidate_navigation_cache(self) -> int:
        """
        使导航缓存失效

        Returns:
            删除的条目数
        """
        pattern = self.build_pattern("navigations")
        return await self.invalidate_pattern(pattern)

    async def clear_all(self) -> bool:
        """
        清空所有缓存

        Returns:
            是否清空成功
        """
        try:
            await self.invalidate_pattern("rosetta:*")
            return True
        except Exception as e:
            logger.error(f"清空缓存失败: {e}")
            return False

    async def close(self) -> None:
        """关闭缓存连接"""
        await self._cache.close()


async def get_cache_service() -> CacheService:
    """
    获取缓存服务实例（依赖注入）

    Returns:
        CacheService 实例
    """
    return CacheService()
