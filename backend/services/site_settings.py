"""站点设置分组（13 组）的服务层读取口。

背景：设置页保存的是 site_configs 表里 ``key=分组名`` 的整段 JSON，但此前只有
``/api/config`` 与 ``/settings/public`` 两条读口会把它们叠进返回值。真正的**执行点**
（评论审核、上传大小、robots 正文）读的是环境变量或硬编码常量，于是出现
"后台改了、前台不生效"——设置项存进库却没有任何代码分支去判断它。

本模块给执行点一个统一入口：优先复用请求会话（无会话的调用点自行开一条），
带 TTL 缓存，``PATCH /api/settings/{group}`` 保存时同键失效（见 api/settings_groups.py）。

**返回库内存值，不合并默认值**：调用点各自决定"这一项没配过时的既有行为"
（环境变量 / 硬编码常量）。若在这里合并 ``_default_*``，未保存过分组的站点会被
默认值静默改写既有行为（例：``comments.require_approval`` 分组默认 False，
而环境变量默认 True → 一次读取就把所有站点的评论改成免审）。

失败即空 dict：分组行不存在、JSON 损坏、DB 异常都按"没配过"处理，
配置坏掉不该让评论、上传、robots 这些主流程 500。
"""

from __future__ import annotations

import json
import logging

from sqlalchemy import select

logger = logging.getLogger(__name__)

GROUP_CACHE_TTL = 300


async def read_group(name: str, db=None) -> dict:
    """读取某分组**已保存**的键值；未保存过（或数据损坏）返回 ``{}``。

    ``db``：在请求处理链里调用时**必须**传入请求会话。测试环境的 SQLite 用
    StaticPool（全局共享一条连接），请求会话还开着事务时再开第二个会话会和它
    抢同一条连接，把请求侧已加载的 ORM 对象顶成过期状态，后续属性读取即在
    greenlet 之外触发隐式 IO（``MissingGreenlet`` → 500）。
    无请求会话的调用点（Nitro 之外的独立端点）可以不传，自行开带缓存的读取。
    """
    # 延迟导入：service 层在模块加载期不应依赖 api 层与 DB 引擎
    from backend.api.settings_groups import SETTING_GROUPS
    from backend.core.cache import cache, make_cache_key
    from backend.core.database import async_session_maker
    from backend.models.core import SiteConfig

    if name not in SETTING_GROUPS:  # pragma: no cover - 调用方写错分组名
        return {}

    cache_key = make_cache_key("settings_group", name)
    try:
        cached = await cache.get(cache_key)
        if isinstance(cached, dict):
            return cached
    except Exception:  # 缓存后端异常不影响配置读取
        logger.debug("settings_group cache get failed: %s", name, exc_info=True)

    value: str | None = None
    try:
        if db is not None:
            value = await db.scalar(select(SiteConfig.value).where(SiteConfig.key == name))
        else:
            async with async_session_maker() as session:
                value = await session.scalar(
                    select(SiteConfig.value).where(SiteConfig.key == name)
                )
    except Exception:
        logger.warning("settings_group db read failed: %s", name, exc_info=True)
        return {}

    parsed: dict = {}
    if value:
        try:
            loaded = json.loads(value)
            if isinstance(loaded, dict):
                parsed = loaded
        except (json.JSONDecodeError, TypeError):
            logger.warning("[site_settings] 分组 %s 的库内值不是合法 JSON，按未配置处理", name)

    try:
        await cache.set(cache_key, parsed, GROUP_CACHE_TTL)
    except Exception:
        logger.debug("settings_group cache set failed: %s", name, exc_info=True)

    return parsed


def bool_of(cfg: dict, key: str, default: bool) -> bool:
    """把配置值当布尔用：历史手写数据里可能是 "true"/1/"0"。"""
    val = cfg.get(key)
    if val is None:
        return default
    if isinstance(val, bool):
        return val
    if isinstance(val, str):
        return val.strip().lower() in {"1", "true", "yes", "on"}
    return bool(val)


def int_of(cfg: dict, key: str, default: int) -> int:
    """同上取整数；坏值退回默认而不是抛异常。"""
    val = cfg.get(key)
    if val is None:
        return default
    try:
        return int(val)
    except (TypeError, ValueError):
        return default
