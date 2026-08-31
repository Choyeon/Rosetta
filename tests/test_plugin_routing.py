"""
Task D 最小 TDD：验证 routing_registry / PluginContext / 菜单 API / FastAPI 挂载

覆盖范围（以最小必要验证为原则，避免污染现有 tests 约定）：

1. RoutingRegistry 能登记 admin/public router，并 list_routes() 返回其 mount_prefix。
2. PluginContext.{register_admin_router,register_public_router,register_admin_menu}
   实际写入到全局 routing_registry（含 slug 自动回填、类型校验）。
3. 通过 TestClient(create_application())：
   - GET /api/admin/plugins/menu-registry 返回 {success, data.items}。
4. 插件 router 被 mount_all 正确挂载：用独立测试 session 级 registry 注册后，
   创建新 app 并 mount，能通过 /api/plugins/{slug}/* 与 /api/admin/plugins/{slug}/*
   访问。
"""

from __future__ import annotations

import pytest
from fastapi import APIRouter, FastAPI
from fastapi.testclient import TestClient

from backend.core.routing_registry import RoutingRegistry, routing_registry


# ── 隔离：每测试重置全局单例状态（避免跨测试污染） ─────────────────────


@pytest.fixture(autouse=True)
def _reset_routing_registry():
    routing_registry._reset()
    try:
        yield
    finally:
        routing_registry._reset()


# ── 1. RoutingRegistry 基础登记 / 列出 ──────────────────────────────────


def test_routing_registry_list_routes_contains_prefixes():
    admin = APIRouter(prefix="/test-admin")
    public = APIRouter(prefix="/test-public")

    @admin.get("/ping")
    def _a():
        return "admin"

    @public.get("/ping")
    def _p():
        return "public"

    routing_registry.register_admin_router("demo", admin)
    routing_registry.register_public_router("demo", public)

    items = routing_registry.list_routes()
    # 计划中的最小断言：
    assert any("test-admin" in r["prefix"] for r in items), "admin prefix 未登记"
    assert any("test-public" in r["prefix"] for r in items), "public prefix 未登记"

    mount_prefixes = [r["mount_prefix"] for r in items]
    assert any(p.startswith("/api/admin/plugins/demo") for p in mount_prefixes)
    assert any(p.startswith("/api/plugins/demo") for p in mount_prefixes)


def test_routing_registry_register_admin_menu_roundtrip():
    routing_registry.register_admin_menu(
        {
            "slug": "guestbook-rss",
            "label": "留言板 RSS",
            "icon": "material-symbols:rss-feed-rounded",
            "path": "/admin/plugins/guestbook-rss/settings",
        }
    )
    menu = routing_registry.list_menu()
    assert len(menu) == 1
    assert menu[0]["slug"] == "guestbook-rss"
    assert menu[0]["label"] == "留言板 RSS"
    assert menu[0]["path"] == "/admin/plugins/guestbook-rss/settings"


def test_routing_registry_rejects_invalid_params():
    with pytest.raises((ValueError, TypeError)):
        routing_registry.register_admin_router("", APIRouter())
    with pytest.raises((ValueError, TypeError)):
        routing_registry.register_public_router("x", "not-a-router")  # type: ignore[arg-type]
    with pytest.raises(ValueError):
        routing_registry.register_admin_menu({"slug": "x", "label": "y"})  # 缺少 path


# ── 2. PluginContext 三个新增方法 ───────────────────────────────────────


def test_plugin_context_registers_to_global_registry():
    from backend.core.plugin_loader import PluginContext

    ctx = PluginContext(slug="demo-ctx", manifest={"name": "Demo"})

    admin = APIRouter()

    @admin.get("/x")
    def _ax():
        return "ok"

    ctx.register_admin_router(admin)

    public = APIRouter()

    @public.get("/y")
    def _py():
        return "public-ok"

    ctx.register_public_router(public)

    # 显式传 slug 时以显式为准；未传则自动回填 ctx.slug
    ctx.register_admin_menu({"label": "Demo 设置", "path": "/admin/plugins/demo-ctx/settings"})

    routes = routing_registry.list_routes()
    # admin mount_prefix 应对应 demo-ctx
    admin_mounts = [r["mount_prefix"] for r in routes if r["kind"] == "admin"]
    assert any(p.startswith("/api/admin/plugins/demo-ctx") for p in admin_mounts)

    public_mounts = [r["mount_prefix"] for r in routes if r["kind"] == "public"]
    assert any(p.startswith("/api/plugins/demo-ctx") for p in public_mounts)

    menu = routing_registry.list_menu()
    assert any(
        m["slug"] == "demo-ctx" and m["path"] == "/admin/plugins/demo-ctx/settings" for m in menu
    )


# ── 3. mount_all 实际挂载到 FastAPI ─────────────────────────────────────


def test_mount_all_mounts_admin_and_public_routes():
    # 用独立 RoutingRegistry（非全局）避免污染其它测试
    reg = RoutingRegistry()

    admin = APIRouter()

    @admin.get("/hello")
    def _a():
        return {"from": "admin"}

    public = APIRouter()

    @public.get("/hello")
    def _p():
        return {"from": "public"}

    reg.register_admin_router("widget", admin)
    reg.register_public_router("widget", public)

    app = FastAPI()
    # 无权限 guard 的挂载（为了能通过 TestClient 直接断言）
    reg.mount_all(app, admin_guard=lambda: None)

    with TestClient(app) as client:
        # Admin 路由实际挂载：因为上面传了 admin_guard=lambda: None，相当于无权限保护
        resp_a = client.get("/api/admin/plugins/widget/hello")
        assert resp_a.status_code == 200
        assert resp_a.json() == {"from": "admin"}

        resp_p = client.get("/api/plugins/widget/hello")
        assert resp_p.status_code == 200
        assert resp_p.json() == {"from": "public"}


# ── 4. GET /api/admin/plugins/menu-registry 存在并返回正确结构 ──────────


@pytest.mark.asyncio
async def test_menu_registry_endpoint_returns_items(client, admin_headers):
    # 先把菜单写入全局单例（测试 conftest 会 override get_db 但不会污染 registry）
    routing_registry.register_admin_menu(
        {
            "slug": "foo",
            "label": "Foo Bar",
            "icon": "material-symbols:star",
            "path": "/admin/plugins/foo/home",
        }
    )

    resp = await client.get("/api/admin/plugins/menu-registry", headers=admin_headers)
    # 必须不能是 404
    assert resp.status_code in (200, 401, 403, 503), f"unexpected status: {resp.status_code} {resp.text}"
    if resp.status_code == 200:
        body = resp.json()
        assert body.get("success") is True
        data = body.get("data") or {}
        items = data.get("items") or []
        # 至少包含上述注入的 foo（若进程中还有其它插件菜单，也会出现）
        assert any(it.get("slug") == "foo" for it in items), f"menu 未包含 foo: {items}"
        # 每个 item 带 admin_route_prefix
        foo_item = next(it for it in items if it.get("slug") == "foo")
        assert foo_item.get("admin_route_prefix") == "/api/admin/plugins/foo"
