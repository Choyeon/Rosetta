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
2. ``load_plugins(app)`` 对每个未加载的插件：``register`` → ``activate``，
   并把 id 追加到 ``bus.loaded_plugins``；重复调用不会重复注册。
3. ``unload_plugins(app)`` 调用所有 ``deactivate``，清空已加载标记，并卸载
   路由上由插件注册的前缀（尽力而为，FastAPI 没有标准卸载路由 API）。
"""

from __future__ import annotations

import importlib
import logging
import pkgutil
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any, Callable

from fastapi import APIRouter

from backend.core.plugin_bus import bus

if TYPE_CHECKING:  # pragma: no cover
    from fastapi import FastAPI

logger = logging.getLogger(__name__)


# ──────────────────────────────────────────────────────────────────────────
# PluginContext：插件 register(ctx) 的统一上下文
# ──────────────────────────────────────────────────────────────────────────


@dataclass
class PluginContext:
    """插件 register(ctx) 入口的上下文对象。

    插件通过 ``ctx`` 完成扩展点注册，Rosetta 保证以下字段在进程生命周期中
    均可用（settings/set_settings 在插件未激活时使用会报错，属于正常边界）。

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
        from backend.core.hooks import register_action as _reg_action

        _reg_action(hook_name, priority=priority, plugin=self.slug)(fn)

    def add_filter(
        self,
        hook_name: str,
        fn: Callable[..., Any],
        *,
        priority: int = 10,
    ) -> None:
        """注册 filter handler。"""
        from backend.core.hooks import register_filter as _reg_filter

        _reg_filter(hook_name, priority=priority, plugin=self.slug)(fn)

    # ── Shortcode（Task C 中将正式提供；这里做安全桩，不抛错） ───────

    def register_shortcode(self, name: str, fn: Callable[..., Any]) -> None:
        """注册短代码（Task C 正式接入 shortcodes.py 后覆盖实现）。"""
        try:
            from backend.core.shortcodes import register_shortcode as _reg  # type: ignore

            _reg(name, fn, plugin=self.slug)
        except Exception:  # noqa: BLE001 - Task C 尚未创建时静默忽略
            logger.debug(
                "[PluginContext] shortcode engine 尚未就绪，占位忽略: plugin=%s shortcode=%s",
                self.slug,
                name,
            )

    # ── Settings（调用时动态解析，避免本模块依赖 db session） ───────

    @property
    def settings(self) -> dict[str, Any]:
        """插件设置快照。注意：该属性仅在有活跃 DB session 且插件已持久化后可用。"""
        try:
            import asyncio as _aio

            from backend.core.database import async_session_maker
            from backend.core.extensions import plugin_manager

            async def _get() -> dict[str, Any]:
                if async_session_maker is None:
                    return {}
                async with async_session_maker() as db:  # type: ignore[misc]
                    return await plugin_manager.get_settings(db, self.slug)

            return _aio.get_event_loop().run_until_complete(_get())
        except Exception:  # noqa: BLE001
            return {}

    async def set_settings(self, payload: dict[str, Any]) -> dict[str, Any]:
        """异步写入 settings。供 Task E 示例插件调用。"""
        from backend.core.database import async_session_maker
        from backend.core.extensions import plugin_manager

        if async_session_maker is None:
            raise RuntimeError("set_settings: 数据库尚未就绪")
        async with async_session_maker() as db:  # type: ignore[misc]
            result = await plugin_manager.set_settings(db, self.slug, payload)
            await db.commit()
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


async def load_plugins(app: "FastAPI") -> list[str]:
    """加载所有尚未加载的插件，返回本次新加载的 id 列表。

    幂等：两次调用返回的 loaded 列表相同，bus.loaded_plugins 不重复。
    """
    newly_loaded: list[str] = []
    for pid in discover_plugin_ids():
        if pid in bus.loaded_plugins:
            continue  # 已经加载过，幂等
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
        logger.info(f"[plugin-loader] 插件 id={pid} 加载完成")
    return newly_loaded


async def unload_plugins(app: "FastAPI") -> None:
    """卸载所有已加载插件：调用 deactivate，并清空 bus.loaded_plugins。

    注：当前对路由的卸载做「尽力而为」：因为 FastAPI 未暴露公开的
    ``remove_router`` API，我们只做 hook 清理和 deactivate 通知，不修改
    路由表；进程级生命周期下这种简化是可接受的。
    """
    if not bus.loaded_plugins:
        return
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
    # 清空钩子（保证下次加载是干净状态），避免 bus 对象常驻导致重复订阅
    bus._actions.clear()
    bus._filters.clear()
    bus.loaded_plugins.clear()
    logger.info("[plugin-loader] 所有插件已卸载，钩子已清空")


def _iscoro(obj: object) -> bool:
    import asyncio
    return asyncio.iscoroutine(obj)
