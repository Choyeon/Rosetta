"""
Rosetta 插件加载器。

约定（详见 ``backend/plugins/announce_bar/__init__.py`` 中的注释）：

- 每个插件是目录 ``backend/plugins/<plugin_id>/``，必须包含 ``__init__.py``。
- ``__init__.py`` 内可选定义：
  * ``PLUGIN_META: dict`` —— 元数据（id/name/version/description/requires_cap...）
  * ``def register(app, bus) -> None`` —— 注册入口（必填）
  * ``def activate(app, bus) -> None`` —— 激活（加载后立即调用，可选）
  * ``def deactivate(app, bus) -> None`` —— 停用（卸载前调用，可选）

加载流程：
1. ``discover_plugin_ids`` 扫描 ``backend/plugins/*/__init__.py`` 得到插件 id；
2. ``load_plugins(app)`` 对每个未加载、且 DB 记录为 active（或尚无记录）的插件：
   ``register`` → ``activate`` → 预取 settings 快照，并把 id 追加到
   ``bus.loaded_plugins``；重复调用不会重复注册。
3. ``unload_plugins(app)`` 调用所有 ``deactivate``，清空已加载标记，并卸载
   路由上由插件注册的前缀（尽力而为，FastAPI 没有标准卸载路由 API）。
"""

from __future__ import annotations

import importlib
import logging
import pkgutil
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any

from fastapi import APIRouter

from backend.core.plugin_bus import bus

if TYPE_CHECKING:  # pragma: no cover
    from fastapi import FastAPI

logger = logging.getLogger(__name__)


# ──────────────────────────────────────────────────────────────────────────
# 插件 settings 进程内快照（同步安全读 + 异步失效）
# ──────────────────────────────────────────────────────────────────────────
# WHY: 插件的 register()/钩子处理器多为同步调用路径，而事件循环已在运行，
# 同步桥接读 DB（run_until_complete）必然 RuntimeError。旧实现把该异常吞成
# 空 dict，导致插件永远读不到自身配置。现在改为：加载/激活成功后异步预取
# 一份快照进进程；一切写入路径（平台 API / ctx.set_settings / 插件自带
# 持久化）提交成功后刷新快照；停用/删除时失效。


_SETTINGS_SNAPSHOTS: dict[str, dict[str, Any]] = {}


def get_settings_snapshot(slug: str) -> dict[str, Any]:
    """读取插件 settings 快照（纯 dict 查找，不触 DB、不碰事件循环）。"""
    return _SETTINGS_SNAPSHOTS.get(slug, {})


def set_settings_snapshot(slug: str, value: Any) -> None:
    """由写入方在 DB 事务 commit 成功后回灌快照，保证运行中的插件立即可见。"""
    if isinstance(value, dict):
        _SETTINGS_SNAPSHOTS[slug] = dict(value)


def invalidate_settings_snapshot(slug: str) -> None:
    _SETTINGS_SNAPSHOTS.pop(slug, None)


async def prime_settings_snapshot(slug: str) -> dict[str, Any]:
    """从 DB 预取 settings 并写入快照。

    失败时**抛出**异常（由调用方记录日志），不再静默回退空 dict——
    静默空快照正是本模块修复的原始缺陷。
    """
    from backend.core.database import async_session_maker
    from backend.core.extensions import plugin_manager

    if async_session_maker is None:
        raise RuntimeError("prime_settings_snapshot: 数据库尚未就绪")
    async with async_session_maker() as db:  # type: ignore[misc]
        value = await plugin_manager.get_settings(db, slug)
    _SETTINGS_SNAPSHOTS[slug] = value
    return value


# ──────────────────────────────────────────────────────────────────────────
# PluginContext：插件 register(ctx) 的统一上下文
# ──────────────────────────────────────────────────────────────────────────


@dataclass
class PluginContext:
    """插件 register(ctx) 入口的上下文对象。

    插件通过 ``ctx`` 完成扩展点注册，Rosetta 保证以下字段在进程生命周期中
    均可用（``settings`` 为同步快照，实时值请用 ``await ctx.get_settings()``）。

    Attributes:
        slug: 插件 slug。
        manifest: 插件 manifest 字典（来自 rosetta-plugin.json）。
        app: FastAPI 应用（只读访问）。
        bus: 事件总线实例（向后兼容）。
    """

    slug: str
    manifest: dict[str, Any] = field(default_factory=dict)
    app: Any = None
    bus: Any = None

    # ── 路由/菜单注册（Task D 新增） ──────────────────────────────

    def register_admin_router(self, router: APIRouter) -> None:
        """注册插件后台 APIRouter，最终挂载到 ``/api/admin/plugins/{slug}``。"""
        from backend.core.routing_registry import routing_registry

        routing_registry.register_admin_router(self.slug, router)

    def register_public_router(self, router: APIRouter) -> None:
        """注册插件前台 APIRouter，最终挂载到 ``/api/plugins/{slug}``。"""
        from backend.core.routing_registry import routing_registry

        routing_registry.register_public_router(self.slug, router)

    def register_admin_menu(self, item: dict[str, Any]) -> None:
        """注册插件后台菜单项（Sidebar「插件」分组下显示）。

        ``item`` 必须包含 ``label`` / ``path``；``icon`` 与 ``badge`` 可选。
        若 ``slug`` 未显式声明则回落到 ``self.slug``。
        """
        from backend.core.routing_registry import routing_registry

        if not isinstance(item, dict):
            raise TypeError("register_admin_menu: 参数必须是 dict")
        normalized = dict(item)
        normalized.setdefault("slug", self.slug)
        routing_registry.register_admin_menu(normalized)

    # ── Hook 注册（保持与 hooks.py / Task C register_shortcode 一致语义） ──

    def add_action(
        self,
        hook_name: str,
        fn: Callable[..., Any],
        *,
        priority: int = 10,
    ) -> None:
        """注册 action handler。"""
        from backend.core.hooks import add_action as _add

        _add(hook_name, fn, priority=priority, plugin=self.slug)

    def add_filter(
        self,
        hook_name: str,
        fn: Callable[..., Any],
        *,
        priority: int = 10,
    ) -> None:
        """注册 filter handler。"""
        from backend.core.hooks import add_filter as _add

        _add(hook_name, fn, priority=priority, plugin=self.slug)

    # ── Shortcode（Task C 中将正式提供；这里做安全桩，不抛错） ───────

    def register_shortcode(self, name: str, fn: Callable[..., Any]) -> None:
        """注册短代码（引擎侧 ``core/shortcodes.py``）。"""
        try:
            from backend.core.shortcodes import register_shortcode as _reg

            _reg(name, fn, plugin=self.slug)
        except Exception:  # noqa: BLE001 - 单插件注册失败不应打断其他插件
            # 至少要是 warning：debug 级在生产日志级别下不可见，插件作者会认为
            # "register() 没报错就是注册成功了"，而实际短代码从未进入注册表，
            # 前台表现为"[tag] 原样出现在文章里"且无人知道为什么。
            logger.warning(
                "[PluginContext] shortcode 注册失败: plugin=%s shortcode=%s",
                self.slug,
                name,
                exc_info=True,
            )

    # ── Settings（同步快照读 + 异步实时读，两条路径都不触事件循环桥接） ──

    @property
    def settings(self) -> dict[str, Any]:
        """settings 同步安全快照。

        快照在插件加载/激活成功时预取，任何设置写入提交后即时刷新，
        纯内存查找、可在同步上下文安全调用。需要**权威实时值**时用
        ``await ctx.get_settings()``。
        """
        return get_settings_snapshot(self.slug)

    async def get_settings(self) -> dict[str, Any]:
        """异步读取 DB 权威值并刷新快照。失败时抛异常，不静默返回空 dict。"""
        return await prime_settings_snapshot(self.slug)

    async def set_settings(self, payload: dict[str, Any]) -> dict[str, Any]:
        """异步写入 settings，commit 成功后同步刷新进程内快照。"""
        from backend.core.database import async_session_maker
        from backend.core.extensions import plugin_manager

        if async_session_maker is None:
            raise RuntimeError("set_settings: 数据库尚未就绪")
        async with async_session_maker() as db:  # type: ignore[misc]
            result = await plugin_manager.set_settings(db, self.slug, payload)
            await db.commit()
        set_settings_snapshot(self.slug, result)
        return result

    # ── Forward action / filter 触发（便利 API） ─────────────────────

    async def do_action(self, hook_name: str, *args: Any, **kwargs: Any) -> None:
        from backend.core.hooks import do_action as _do

        await _do(hook_name, *args, plugin=self.slug, **kwargs)

    async def apply_filters(self, hook_name: str, value: Any, *args: Any, **kwargs: Any) -> Any:
        from backend.core.hooks import apply_filters as _apply

        return await _apply(hook_name, value, *args, plugin=self.slug, **kwargs)


_PLUGINS_PKG = "backend.plugins"


def discover_plugin_ids() -> list[str]:
    """扫描 backend.plugins 包返回插件 id 列表（仅识别带 __init__.py 的目录）。"""
    ids: list[str] = []
    try:
        pkg = importlib.import_module(_PLUGINS_PKG)
    except Exception as exc:  # pragma: no cover
        logger.warning(f"[plugin-loader] 无法导入插件根包: {exc}")
        return ids
    pkg_paths = []
    for p in getattr(pkg, "__path__", []):
        pkg_paths.append(p)
    if not pkg_paths:
        # 回退：按项目相对路径查
        candidate = Path(__file__).resolve().parent.parent / "plugins"
        if candidate.exists():
            pkg_paths.append(str(candidate))
    for finder, name, ispkg in pkgutil.iter_modules(pkg_paths):
        if not ispkg:
            continue
        # 只保留真正有 __init__.py 的
        base = getattr(finder, "path", None)
        if base:
            init_file = Path(base) / name / "__init__.py"
            if not init_file.exists():
                continue
        ids.append(name)
    # 稳定顺序，便于测试去重
    return sorted(set(ids))


async def _plugin_db_status() -> dict[str, str]:
    """返回 DB 中 ``slug -> status`` 映射。

    DB 未就绪 / 查询失败时返回空字典（退化为旧的「全部可加载」行为），
    保证启动早期或异常情况下不会因为读取状态失败而阻断启动；失败会记录
    日志而非静默。
    """
    try:
        from sqlalchemy import select as _select

        from backend.core.database import async_session_maker
        from backend.models.extensions import Plugin as PluginModel

        if async_session_maker is None:
            return {}
        async with async_session_maker() as db:  # type: ignore[misc]
            rows = (await db.execute(_select(PluginModel.slug, PluginModel.status))).all()
        return {r[0]: r[1] for r in rows}
    except Exception:  # noqa: BLE001
        logger.warning("[plugin-loader] 读取插件状态表失败，按全部可加载处理", exc_info=True)
        return {}


async def load_plugins(app: FastAPI) -> list[str]:
    """加载所有尚未加载且在 DB 中处于激活状态的插件，返回本次新加载 id 列表。

    - 仅加载 DB 记录为 ``active`` 的插件，或**尚无 DB 记录**的插件（首次启动、
      bootstrap 扫描前的兼容路径）；``installed`` / ``inactive`` / ``error``
      一律跳过——否则「已安装未启用」的插件钩子会在运行时偷偷生效，
      与后台开关状态漂移。
    - 加载成功后异步预取该插件的 settings 快照，保证同步上下文里
      ``ctx.settings`` 可用（预取失败记日志，不阻断加载）。
    - 幂等：两次调用 ``bus.loaded_plugins`` 不重复。
    """
    status_map = await _plugin_db_status()
    newly_loaded: list[str] = []
    for pid in discover_plugin_ids():
        if pid in bus.loaded_plugins:
            continue  # 已经加载过，幂等
        db_status = status_map.get(pid)
        if db_status is not None and db_status != "active":
            logger.info("[plugin-loader] 插件 id=%s DB 状态=%s（未激活），跳过加载", pid, db_status)
            continue
        try:
            module = importlib.import_module(f"{_PLUGINS_PKG}.{pid}")
        except Exception as exc:
            logger.exception(f"[plugin-loader] 导入插件失败 id={pid}: {exc}")
            continue

        register = getattr(module, "register", None)
        if register is None:
            logger.warning(f"[plugin-loader] 插件 {pid} 缺少 register(app,bus)，跳过")
            continue

        try:
            # register 可以是 sync 或 async（按需兼容）
            result = register(app, bus)
            if hasattr(result, "__await__") or _iscoro(result):
                await result
        except Exception as exc:
            logger.exception(f"[plugin-loader] 插件 {pid}.register 抛异常: {exc}")
            continue

        activate = getattr(module, "activate", None)
        if callable(activate):
            try:
                result = activate(app, bus)
                if hasattr(result, "__await__") or _iscoro(result):
                    await result
            except Exception as exc:
                logger.warning(f"[plugin-loader] 插件 {pid}.activate 抛异常(继续加载): {exc}")

        bus.loaded_plugins.append(pid)
        newly_loaded.append(pid)
        try:
            await prime_settings_snapshot(pid)
        except Exception:  # noqa: BLE001 - 快照预取失败不应阻断插件加载，但必须留痕
            logger.warning(
                "[plugin-loader] 插件 %s settings 快照预取失败（ctx.settings 将暂为空快照）",
                pid,
                exc_info=True,
            )
        logger.info(f"[plugin-loader] 插件 id={pid} 加载完成")
    return newly_loaded


async def unload_plugins(app: FastAPI) -> None:
    """卸载所有已加载插件：调用 deactivate，摘除其 hooks/shortcodes，清空 loaded_plugins。

    钩子注册表已统一收归 :mod:`backend.core.hooks`，``PluginBus`` 门面不再自持
    ``_actions/_filters``，因此这里按插件 slug 精确摘除（与运行时 deactivate 路径
    :meth:`PluginManager.deactivate` 完全一致），避免误删其它来源的处理器。

    注：路由卸载仍为「尽力而为」：FastAPI 未暴露公开的 ``remove_router`` API，
    本函数不修改路由表；进程级生命周期下这种简化是可接受的。
    """
    if not bus.loaded_plugins:
        return
    from backend.core.hooks import remove_hooks_for_plugin
    from backend.core.shortcodes import shortcode_manager

    for pid in list(bus.loaded_plugins):
        try:
            module = importlib.import_module(f"{_PLUGINS_PKG}.{pid}")
        except Exception:
            module = None
        if module is not None:
            deactivate = getattr(module, "deactivate", None)
            if callable(deactivate):
                try:
                    result = deactivate(app, bus)
                    if hasattr(result, "__await__") or _iscoro(result):
                        await result
                except Exception as exc:
                    logger.warning(f"[plugin-loader] 插件 {pid}.deactivate 抛异常: {exc}")
        # 精确摘除该插件注册的全部 action/filter 与 shortcode（deactivate 未做时的兜底）
        removed_hooks = remove_hooks_for_plugin(pid)
        removed_codes = shortcode_manager.remove_for_plugin(pid)
        invalidate_settings_snapshot(pid)
        if removed_hooks or removed_codes:
            logger.info(
                "[plugin-loader] 插件 %s 摘除 hooks=%d shortcodes=%d",
                pid,
                removed_hooks,
                removed_codes,
            )
    bus.loaded_plugins.clear()
    logger.info("[plugin-loader] 所有插件已卸载，loaded_plugins 已清空")


async def reconcile_loaded_with_db() -> list[str]:
    """把「已被 legacy loader 加载、但 DB 状态并非 active」的插件运行期注册摘除。

    背景：首次启动时 bootstrap 扫描前 DB 还没有插件记录，legacy loader 会按
    目录全量加载；随后 scan 把这些插件登记为 ``installed``（未启用）。不摘除
    就会出现"后台显示未启用、前台钩子仍在生效"的状态漂移。

    注：插件路由受 FastAPI 无公开卸载 API 限制无法在本进程内移除（既有约定，
    见 :func:`unload_plugins` 文档），本函数只回收 hooks / shortcodes / 快照。
    """
    if not bus.loaded_plugins:
        return []
    from backend.core.hooks import remove_hooks_for_plugin
    from backend.core.shortcodes import shortcode_manager

    status_map = await _plugin_db_status()
    pruned: list[str] = []
    for pid in list(bus.loaded_plugins):
        db_status = status_map.get(pid)
        # 无记录（异常路径）或确为 active 的插件保持现状
        if db_status is None or db_status == "active":
            continue
        removed_hooks = remove_hooks_for_plugin(pid)
        removed_codes = shortcode_manager.remove_for_plugin(pid)
        invalidate_settings_snapshot(pid)
        bus.loaded_plugins.remove(pid)
        pruned.append(pid)
        logger.info(
            "[plugin-loader] 插件 %s DB 状态=%s 但运行期已注册，已摘除 hooks=%d shortcodes=%d",
            pid,
            db_status,
            removed_hooks,
            removed_codes,
        )
    return pruned


def _iscoro(obj: object) -> bool:
    import asyncio

    return asyncio.iscoroutine(obj)
