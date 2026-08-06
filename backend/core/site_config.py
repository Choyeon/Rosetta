"""
站点配置工具函数

提供便捷的站点配置访问接口，支持缓存优化。
"""

from sqlalchemy import select

from backend.core.cache import CACHE_TTL, cache, make_cache_key
from backend.core.database import async_session_maker
from backend.models.core import SiteConfig


async def get_site_config_value(key: str) -> str | None:
    """
    获取站点配置值

    从数据库 SiteConfig 表获取指定 key 的配置值，使用缓存优化性能。

    Args:
        key: 配置键名，如 "SITE_NAME"、"SITE_DESCRIPTION" 等

    Returns:
        配置值字符串，如果不存在则返回 None

    缓存策略：
    - 缓存时间：1 小时
    - 空值缓存：60 秒（防止缓存穿透）
    """
    cache_key = make_cache_key("site_config_value", key)

    cached = await cache.get(cache_key)
    if cached is not None:
        if cached == "__NULL__":
            return None
        return cached

    async with async_session_maker() as db:
        result = await db.execute(select(SiteConfig).where(SiteConfig.key == key))
        config = result.scalar_one_or_none()

        if config is None:
            await cache.set(cache_key, "__NULL__", 60)
            return None

        await cache.set(cache_key, config.value, CACHE_TTL["site_config"])
        return config.value
