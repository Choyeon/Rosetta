"""
插件路由与后台菜单注册表。

插件通过 ``PluginContext`` 将自己的 ``APIRouter`` / 菜单项提交到这里集中暂存，
待 ``main.py`` 完成所有核心路由挂载后，再统一调用 :func:`RoutingRegistry.mount_all`
把插件路由挂到 FastAPI 应用上。

典型用法::

    from backend.core.routing_registry import routing_registry

    admin = APIRouter()
    @admin.get("/ping")
    def _ping(): return "ok"

    routing_registry.register_admin_router("demo", admin)
    routing_registry.register_admin_menu({
        "slug": "demo",
        "label": "演示插件",
        "icon": "material-symbols:widgets",
        "path": "/admin/plugins/demo/index",
    })

    # 在 main.py 末尾：
    routing_registry.mount_all(app)
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from fastapi import APIRouter, Depends

if TYPE_CHECKING:  # pragma: no cover
    from fastapi import FastAPI

logger = logging.getLogger("rosetta.routing_registry")


@dataclass
class AdminMenuEntry:
    """单个插件声明的后台菜单项。"""

    slug: str
    label: str
    path: str
    icon: str = "material-symbols:extension"
    badge: str | int | None = None
    extras: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        data = {
            "slug": self.slug,
            "label": self.label,
            "path": self.path,
            "icon": self.icon,
        }
        if self.badge is not None:
            data["badge"] = self.badge
        if self.extras:
            data["extras"] = self.extras
        return data


class RoutingRegistry:
    """集中暂存插件声明的 admin/public 路由与后台菜单。"""

    def __init__(self) -> None:
        # (slug, router)；保持注册顺序，便于调试
        self._admin_routes: list[tuple[str, APIRouter]] = []
        self._public_routes: list[tuple[str, APIRouter]] = []
        self._menu_items: list[AdminMenuEntry] = []
        self._mounted = False

    # ── 注册 API（供插件 ctx / 手动调用） ──────────────────────────────

    def register_admin_router(self, slug: str, router: APIRouter) -> None:
        """注册一个插件后台 APIRouter，最终挂载在 ``/api/admin/plugins/{slug}``。"""
        if not isinstance(slug, str) or not slug:
            raise ValueError("register_admin_router: slug 必须是非空字符串")
        if not isinstance(router, APIRouter):
            raise TypeError("register_admin_router: router 必须是 fastapi.APIRouter 实例")
        if self._mounted:
            logger.warning(
                "[routing_registry] %s 在路由统一挂载之后再注册 admin router，可能不生效",
                slug,
            )
        self._admin_routes.append((slug, router))
        logger.info("[routing_registry] admin router 注册完成: plugin=%s", slug)

    def register_public_router(self, slug: str, router: APIRouter) -> None:
        """注册一个插件前台 APIRouter，最终挂载在 ``/api/plugins/{slug}``。"""
        if not isinstance(slug, str) or not slug:
            raise ValueError("register_public_router: slug 必须是非空字符串")
        if not isinstance(router, APIRouter):
            raise TypeError("register_public_router: router 必须是 fastapi.APIRouter 实例")
        if self._mounted:
            logger.warning(
                "[routing_registry] %s 在路由统一挂载之后再注册 public router，可能不生效",
                slug,
            )
        self._public_routes.append((slug, router))
        logger.info("[routing_registry] public router 注册完成: plugin=%s", slug)

    def register_admin_menu(self, item: dict[str, Any] | AdminMenuEntry) -> None:
        """注册一个后台菜单项，供 Sidebar / AppHeader 动态渲染。

        允许传入 ``dict``（最常见插件写法）或 :class:`AdminMenuEntry` 实例。
        dict 中必须包含 ``slug`` / ``label`` / ``path``，其余字段可选。
        """
        if isinstance(item, AdminMenuEntry):
            entry = item
        elif isinstance(item, dict):
            slug = str(item.get("slug") or "").strip()
            label = str(item.get("label") or "").strip()
            path = str(item.get("path") or "").strip()
            if not slug or not label or not path:
                raise ValueError(
                    "register_admin_menu: dict 必须包含 slug / label / path 三个字段"
                )
            entry = AdminMenuEntry(
                slug=slug,
                label=label,
                path=path,
                icon=str(item.get("icon") or "material-symbols:extension"),
                badge=item.get("badge"),
                extras={k: v for k, v in item.items() if k not in {"slug", "label", "path", "icon", "badge"}},
            )
        else:
            raise TypeError("register_admin_menu: 参数必须是 dict 或 AdminMenuEntry")
        self._menu_items.append(entry)
        logger.info("[routing_registry] admin menu 注册完成: plugin=%s path=%s", entry.slug, entry.path)

    # ── 查询 API（供列表 / 菜单接口调用） ──────────────────────────────

    def list_routes(self) -> list[dict[str, Any]]:
        """返回已注册路由的描述列表（主要用于单测与自检）。"""
        items: list[dict[str, Any]] = []
        for slug, r in self._admin_routes:
            prefix = getattr(r, "prefix", "") or ""
            items.append(
                {
                    "kind": "admin",
                    "slug": slug,
                    "prefix": prefix,
                    "mount_prefix": f"/api/admin/plugins/{slug}{prefix}",
                    "routes": [getattr(route, "path", None) for route in getattr(r, "routes", [])],
                }
            )
        for slug, r in self._public_routes:
            prefix = getattr(r, "prefix", "") or ""
            items.append(
                {
                    "kind": "public",
                    "slug": slug,
                    "prefix": prefix,
                    "mount_prefix": f"/api/plugins/{slug}{prefix}",
                    "routes": [getattr(route, "path", None) for route in getattr(r, "routes", [])],
                }
            )
        return items

    def list_menu(self) -> list[dict[str, Any]]:
        """以 dict 列表形式返回菜单，给 REST API 直接返回用。"""
        return [e.to_dict() for e in self._menu_items]

    # ── 统一挂载 ────────────────────────────────────────────────────────

    def mount_all(self, app: "FastAPI", *, admin_guard: Any = None) -> None:
        """把 registry 中暂存的 admin/public 路由统一挂到 ``app`` 上。

        Args:
            app: FastAPI 应用实例。
            admin_guard: 后台路由的全局依赖；默认 ``backend.core.auth.get_current_staff``
                （即与现有 /api/admin/* 接口一致的 CurrentStaff 权限）。
        """
        if self._mounted:
            logger.warning("[routing_registry] mount_all() 已经调用过，本次跳过（避免重复挂载）")
            return

        if admin_guard is None:
            # 延迟导入，避免本模块在 imports 顶层就需要 sqlalchemy/fastapi/auth 全部构造完
            from backend.core.auth import get_current_staff

            admin_guard = get_current_staff

        # 1) Admin 路由：统一加 admin 权限依赖
        for slug, router in self._admin_routes:
            prefix = f"/api/admin/plugins/{slug}"
            try:
                app.include_router(
                    router,
                    prefix=prefix,
                    dependencies=[Depends(admin_guard)],
                    tags=[f"Plugin: {slug}"],
                )
                logger.info(
                    "[routing_registry] admin router 已挂载: plugin=%s prefix=%s",
                    slug,
                    prefix,
                )
            except Exception:  # noqa: BLE001
                logger.exception("[routing_registry] admin router 挂载失败: plugin=%s", slug)

        # 2) Public 路由：无权限依赖，走插件自己的 guard
        for slug, router in self._public_routes:
            prefix = f"/api/plugins/{slug}"
            try:
                app.include_router(
                    router,
                    prefix=prefix,
                    tags=[f"Plugin-Public: {slug}"],
                )
                logger.info(
                    "[routing_registry] public router 已挂载: plugin=%s prefix=%s",
                    slug,
                    prefix,
                )
            except Exception:  # noqa: BLE001
                logger.exception("[routing_registry] public router 挂载失败: plugin=%s", slug)

        self._mounted = True
        logger.info(
            "[routing_registry] 统一挂载完成：admin=%d public=%d menu=%d",
            len(self._admin_routes),
            len(self._public_routes),
            len(self._menu_items),
        )

    # ── 测试辅助：清理状态（仅 tests 内部使用） ───────────────────────

    def _reset(self) -> None:
        self._admin_routes.clear()
        self._public_routes.clear()
        self._menu_items.clear()
        self._mounted = False


# 全局单例
routing_registry = RoutingRegistry()


def _reset_routing_registry() -> None:
    """清空路由注册表（仅测试隔离使用）。"""
    routing_registry._reset()  # noqa: SLF001


__all__ = [
    "RoutingRegistry",
    "AdminMenuEntry",
    "routing_registry",
    "_reset_routing_registry",
]
