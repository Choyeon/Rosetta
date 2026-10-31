"""站点设置分组（14 组）的服务层读取口。

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
                value = await session.scalar(select(SiteConfig.value).where(SiteConfig.key == name))
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


# 站内默认 OG 分享图（品牌 PNG，落在 frontend/public/ 根下，由 Nitro 直出）。
# 仓库根 static/ 目录只挂在 /favicon 下，写 /static/xxx 会是一条 404 分享图。
# 文章没有真实封面时，
# RSS / Open Graph / JSON-LD / hero 兜底一律回落到它，而不是外链占位图
# （picsum 限流或被墙即无图，且随机图与内容无关，图片搜索零收益）。
DEFAULT_OG_IMAGE_PATH = "/og-default.png"


async def default_og_image_url(db=None) -> str:
    """默认分享图的绝对 URL：seo.default_og_image（可后台改），空则内置品牌图。

    ``db``：在请求处理链里调用时**必须**传入请求会话（口径同 ``read_group``，
    SQLite StaticPool 下双会话并存会把请求侧 ORM 对象顶成过期态）。
    站点根取 ``settings.site_url``；未配置时返回相对路径（同源部署下前端可解析，
    绝不虚构绝对域名）。
    """
    cfg = await read_group("seo", db)
    path = str(cfg.get("default_og_image") or "").strip() or DEFAULT_OG_IMAGE_PATH
    if path.startswith(("http://", "https://")):
        return path
    from backend.core.config import settings

    site_url = (getattr(settings, "site_url", "") or "").rstrip("/")
    if not site_url:
        return path
    return f"{site_url}/{path.lstrip('/')}"


BING_WALLPAPER_FLAT_KEY = "ENABLE_BING_WALLPAPER"


async def bing_wallpaper_enabled(db=None) -> bool:
    """Bing 壁纸开关的**合并口径单源**（与 ``/api/config`` 的 ``enable_bing_wallpaper`` 同值）。

    两层，顺序与 ``api/core.py::get_site_config`` 一致：

    1. SiteConfig 扁平键 ``ENABLE_BING_WALLPAPER``——OOBE 向导 / ``auto_oobe`` 写的那份，
       大小写不敏感、缺省按开、值必须整串等于 ``true`` 才算开（与 ``get_bool`` 同判据）；
    2. ``features`` 分组里的同名 bool——后台「功能开关」保存后的覆盖，仅在它是真 bool 时生效。

    只读一层必然分叉，两半边都在线上发生过：只读分组 → 从没进过设置页的站点只有 OOBE
    扁平行，``/api/config`` 按它回 ``false`` 而 sitemap 仍提交 ``/wallpapers``；只读扁平键 →
    后台关掉开关后页面自己 noindex 了、页脚入口也收了，sitemap 却还在递地址。

    ``db``：口径同 ``read_group``（请求链里必须传请求会话）。读取失败按"开"处理——
    配置表坏了不该让 sitemap 少一整条 URL，且默认值本来就是开。
    """
    from sqlalchemy import func, select

    from backend.core.database import async_session_maker
    from backend.models.core import SiteConfig

    values: list = []
    try:
        stmt = select(SiteConfig.value).where(func.upper(SiteConfig.key) == BING_WALLPAPER_FLAT_KEY)
        if db is not None:
            values = list((await db.execute(stmt)).scalars().all())
        else:
            async with async_session_maker() as session:
                values = list((await session.execute(stmt)).scalars().all())
    except Exception:
        logger.warning(
            "[site_settings] %s 读取失败，按开启处理", BING_WALLPAPER_FLAT_KEY, exc_info=True
        )

    # `select(SiteConfig)` 无 ORDER BY，core.py 的大小写镜像字典是"后出现的行覆盖前面的"，
    # 这里取同名行的最后一条以保持同一判据。
    raw = values[-1] if values else "true"
    enabled = str(raw).strip().lower() == "true"

    features = await read_group("features", db)
    override = features.get("enable_bing_wallpaper")
    if isinstance(override, bool):
        return override
    return enabled
