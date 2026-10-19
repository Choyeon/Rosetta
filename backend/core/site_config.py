"""
站点配置工具函数

提供便捷的站点配置访问接口，支持缓存优化。
"""

from sqlalchemy import select

from backend.core.cache import CACHE_TTL, cache, invalidate_cache, make_cache_key
from backend.core.database import async_session_maker
from backend.models.core import SiteConfig


async def invalidate_site_config_caches() -> int:
    """删净 SiteConfig 的两族读缓存，返回删除条数。

    同一个 `site_configs` 表有两个读面、键形不同：
    - ``site_config`` —— 聚合值（/api/config、RSS channel、sitemap 读它，分组 JSON 会叠进去）；
    - ``site_config_value:<key>`` —— 本模块 ``get_site_config_value`` 的逐键缓存，
      robots.txt 与 OG 的站点名/简介走这条口（TTL 同为 ``CACHE_TTL["site_config"]``＝3600s）。

    写侧曾经只 ``cache.delete(make_cache_key("site_config"))`` 精确删聚合键，表现是
    "后台改了站点名，/api/config 立刻是新的，但爬虫读的 robots.txt / sitemap 一小时内
    仍写旧站名"。两者都在 ``site_config`` 命名空间下，用同一条前缀通配一次删净；
    OOBE 装机与整站恢复已经用这个前缀，本函数是它的单源写法。
    """
    return await invalidate_cache("site_config")


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
