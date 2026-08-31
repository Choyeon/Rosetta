"""Guestbook RSS — Rosetta 示例插件。

覆盖以下扩展点：
1. **独立前台路由** ``GET /api/plugins/guestbook-rss/feed.xml`` ——
   输出留言板条目作为 RSS 2.0 feed。
2. **独立后台页** ``GET /admin/plugins/guestbook-rss/settings`` 与
   ``PUT /admin/plugins/guestbook-rss/settings`` —— 读写插件 KV 设置。
3. **admin_menu 声明** —— 在 rosetta-plugin.json 中声明菜单，并通过
   ``register_admin_menu`` 注入到路由注册表供前端 sidebar 消费。

两种注册模式均兼容（详见 ``register()`` 总入口）。
"""

from __future__ import annotations

import html as _html
import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

logger = logging.getLogger("guestbook_rss")

PLUGIN_SLUG = "guestbook-rss"

# 读取 manifest（用于 admin_menu 等元信息；失败时回退到默认值）
_MANIFEST: dict = {}
try:
    _MANIFEST_PATH = Path(__file__).resolve().parent / "rosetta-plugin.json"
    _MANIFEST = json.loads(_MANIFEST_PATH.read_text(encoding="utf-8"))
except Exception as exc:  # pragma: no cover
    logger.warning("guestbook-rss: 无法读取 manifest: %s", exc)

# 内存里维护一份 settings，便于 smoke test 不走 DB 也能断言读写
_MEM_SETTINGS: dict = {}


def _default_settings() -> dict:
    sch = _MANIFEST.get("settings_schema", {}).get("properties", {}) or {}
    return {k: v.get("default") for k, v in sch.items()} if sch else {
        "feed_title": "Rosetta 留言板 RSS",
        "feed_description": "最近 50 条公开留言",
        "max_items": 50,
        "include_author_email": False,
        "language": "zh-CN",
    }


def _get_settings(ctx_settings: Any = None) -> dict:
    """读取 settings：优先 ctx.settings，其次内存，再其次默认值。"""
    if isinstance(ctx_settings, dict) and ctx_settings:
        return {**_default_settings(), **ctx_settings}
    if _MEM_SETTINGS:
        return {**_default_settings(), **_MEM_SETTINGS}
    return _default_settings()


# ── RSS XML 生成器 ──────────────────────────────────────────────────────────


def _rss_xml(entries: list[Any], settings: dict | None = None) -> str:
    """生成 RSS 2.0 feed XML。

    :param entries: 任意 iterable 对象，只要有 ``id / author_name / content /
        created_at`` 属性即可；缺失字段用默认值兜底。
    :param settings: feed_title / feed_description / language / max_items /
        include_author_email。
    """
    s = settings or _default_settings()
    title = _html.escape(str(s.get("feed_title") or "Rosetta 留言板 RSS"))
    desc = _html.escape(str(s.get("feed_description") or "最近公开留言"))
    lang = _html.escape(str(s.get("language") or "zh-CN"))
    max_items = int(s.get("max_items") or 50)
    include_email = bool(s.get("include_author_email", False))
    now = datetime.now(timezone.utc).strftime("%a, %d %b %Y %H:%M:%S GMT")
    link = "https://example.com/guestbook"  # 不依赖 SiteConfig，默认占位；后台可覆盖

    lines: list[str] = []
    lines.append('<?xml version="1.0" encoding="UTF-8"?>')
    lines.append('<rss version="2.0" xmlns:atom="http://www.w3.org/2005/Atom">')
    lines.append("  <channel>")
    lines.append(f"    <title>{title}</title>")
    lines.append(f"    <link>{link}</link>")
    lines.append(f"    <description>{desc}</description>")
    lines.append(f"    <language>{lang}</language>")
    lines.append(f"    <lastBuildDate>{now}</lastBuildDate>")
    lines.append(
        '    <atom:link href="https://example.com/api/plugins/guestbook-rss/feed.xml"'
        ' rel="self" type="application/rss+xml"/>'
    )

    items: list[Any] = list(entries or [])[:max_items]
    for e in items:
        eid = getattr(e, "id", 0) or 0
        author = getattr(e, "author_name", "Anonymous") or "Anonymous"
        email = getattr(e, "author_email", None) or ""
        content = getattr(e, "content", "") or ""
        created = getattr(e, "created_at", None)
        website = getattr(e, "author_website", None) or None
        try:
            pub_date = (
                created.astimezone(timezone.utc).strftime("%a, %d %b %Y %H:%M:%S GMT")
                if hasattr(created, "astimezone")
                else now
            )
        except Exception:
            pub_date = now

        safe_author = _html.escape(str(author))
        safe_content = _html.escape(str(content))
        safe_link = f"{link}#entry-{eid}"
        guid = f"guestbook-entry-{eid}@rosetta.dev"

        lines.append("    <item>")
        lines.append(f"      <title><![CDATA[{safe_author} 留言]]></title>")
        lines.append(f"      <link>{safe_link}</link>")
        lines.append(f"      <guid isPermaLink=\"false\">{guid}</guid>")
        lines.append(f"      <pubDate>{pub_date}</pubDate>")
        if include_email and email:
            safe_email = _html.escape(str(email))
            lines.append(f"      <author>{safe_email} ({safe_author})</author>")
        else:
            lines.append(f"      <dc:creator>{safe_author}</dc:creator>")
        if website:
            safe_w = _html.escape(str(website))
            lines.append(f"      <comments>{safe_w}</comments>")
        lines.append(f"      <description><![CDATA[{safe_content}]]></description>")
        lines.append("    </item>")

    lines.append("  </channel>")
    lines.append("</rss>")
    return "\n".join(lines) + "\n"


# ── 新 ctx 风格注册 (async) ─────────────────────────────────────────────────


async def register_via_ctx(ctx: Any) -> None:
    """使用 PluginContext 注册前台路由、后台路由、后台菜单。"""
    manifest = getattr(ctx, "manifest", None) or _MANIFEST
    admin_menu_decl = manifest.get("admin_menu") if isinstance(manifest, dict) else None

    # ── 前台路由：/feed.xml ──────────────────────────────────────────────
    try:
        from fastapi import APIRouter
        from fastapi.responses import Response
        from sqlalchemy import select
    except Exception as exc:  # pragma: no cover
        logger.warning("guestbook-rss: FastAPI/SQLAlchemy 不可用: %s", exc)
        return

    public = APIRouter(tags=["Guestbook RSS"])

    @public.get("/feed.xml")
    async def rss_feed() -> Response:
        # 实际查询 DB；失败时回退空 items（保证输出结构对）
        rows: list[Any] = []
        try:
            from backend.core.database import async_session_maker
            from backend.models.guestbook import GuestbookEntry

            async with async_session_maker() as db:
                stmt = (
                    select(GuestbookEntry)
                    .where(GuestbookEntry.status == "approved")
                    .order_by(GuestbookEntry.created_at.desc())
                    .limit(max(1, min(int(_get_settings(getattr(ctx, "settings", None)).get("max_items") or 50), 200)))
                )
                res = await db.execute(stmt)
                rows = list(res.scalars().all())
        except Exception:
            rows = []
        body = _rss_xml(rows, _get_settings(getattr(ctx, "settings", None)))
        return Response(body, media_type="application/rss+xml; charset=utf-8")

    reg_pub = getattr(ctx, "register_public_router", None)
    if callable(reg_pub):
        reg_pub(public)
    else:  # 回退 → 全局路由注册表
        try:
            from backend.core.routing_registry import routing_registry

            routing_registry.register_public_router(PLUGIN_SLUG, public)
        except Exception as exc:
            logger.warning("guestbook-rss: 注册前台路由失败: %s", exc)

    # ── 后台路由：GET/PUT /settings ─────────────────────────────────────
    admin = APIRouter(tags=["Guestbook RSS Admin"])

    @admin.get("/settings")
    async def get_admin_settings() -> dict:
        settings = _get_settings(getattr(ctx, "settings", None))
        return {"success": True, "data": settings}

    @admin.put("/settings")
    async def put_admin_settings(payload: dict) -> dict:
        # 写入 ctx.set_settings（如果存在）；并同步更新内存副本
        if not isinstance(payload, dict):
            return {"success": False, "error": "payload 必须是 object"}
        merged = {**_get_settings(getattr(ctx, "settings", None)), **payload}
        set_fn = getattr(ctx, "set_settings", None)
        if callable(set_fn):
            try:
                maybe = set_fn(merged)
                if hasattr(maybe, "__await__"):
                    await maybe
            except Exception as exc:
                logger.warning("guestbook-rss: ctx.set_settings 失败: %s", exc)
        _MEM_SETTINGS.update(merged)
        return {"success": True, "data": merged}

    reg_admin = getattr(ctx, "register_admin_router", None)
    if callable(reg_admin):
        reg_admin(admin)
    else:
        try:
            from backend.core.routing_registry import routing_registry

            routing_registry.register_admin_router(PLUGIN_SLUG, admin)
        except Exception as exc:
            logger.warning("guestbook-rss: 注册后台路由失败: %s", exc)

    # ── 后台菜单注册 ────────────────────────────────────────────────────
    menu_reg = getattr(ctx, "register_admin_menu", None)
    if callable(menu_reg) and admin_menu_decl:
        try:
            menu_reg(admin_menu_decl)
        except Exception as exc:
            logger.warning("guestbook-rss: ctx.register_admin_menu 失败: %s", exc)
    elif admin_menu_decl:
        try:
            from backend.core.routing_registry import routing_registry

            routing_registry.register_admin_menu(admin_menu_decl)
        except Exception as exc:
            logger.warning("guestbook-rss: 注册菜单失败: %s", exc)


# ── 旧风格 register(app, bus) —— 当前 plugin_loader 使用 ───────────────────


def register_via_bus(app: Any = None, bus: Any = None) -> None:
    """旧签名版本：把路由/菜单直接注册到全局 routing_registry，app 不为空时直接挂载。"""
    try:
        from fastapi import APIRouter, Depends, Response
    except Exception as exc:  # pragma: no cover
        logger.warning("guestbook-rss: FastAPI 不可用，跳过路由注册: %s", exc)
        return

    # ── 前台路由 ────────────────────────────────────────────────────────
    public = APIRouter(tags=["Guestbook RSS"])

    @public.get("/feed.xml")
    async def rss_feed() -> Response:
        rows: list[Any] = []
        try:
            from backend.core.database import async_session_maker
            from backend.models.guestbook import GuestbookEntry
            from sqlalchemy import select

            async with async_session_maker() as db:
                stmt = (
                    select(GuestbookEntry)
                    .where(GuestbookEntry.status == "approved")
                    .order_by(GuestbookEntry.created_at.desc())
                    .limit(max(1, min(int(_get_settings().get("max_items") or 50), 200)))
                )
                res = await db.execute(stmt)
                rows = list(res.scalars().all())
        except Exception:
            rows = []
        body = _rss_xml(rows, _get_settings())
        return Response(body, media_type="application/rss+xml; charset=utf-8")

    try:
        from backend.core.routing_registry import routing_registry

        routing_registry.register_public_router(PLUGIN_SLUG, public)
        if app is not None and hasattr(app, "include_router"):
            app.include_router(public, prefix=f"/api/plugins/{PLUGIN_SLUG}", tags=["Plugin-Public: guestbook-rss"])
    except Exception as exc:
        logger.warning("guestbook-rss: 前台路由挂载失败: %s", exc)

    # ── 后台路由 ────────────────────────────────────────────────────────
    admin = APIRouter(tags=["Guestbook RSS Admin"])

    @admin.get("/settings")
    async def get_settings() -> dict:
        return {"success": True, "data": _get_settings()}

    @admin.put("/settings")
    async def put_settings(payload: dict) -> dict:
        if not isinstance(payload, dict):
            return {"success": False, "error": "payload 必须是 object"}
        merged = {**_get_settings(), **payload}
        _MEM_SETTINGS.update(merged)
        return {"success": True, "data": merged}

    try:
        from backend.core.routing_registry import routing_registry as _rr

        _rr.register_admin_router(PLUGIN_SLUG, admin)
        # 如果 app 非空，也尝试挂载（不加 Depends，便于 smoke 测试用 TestClient 直接请求）
        if app is not None and hasattr(app, "include_router"):
            try:
                app.include_router(
                    admin,
                    prefix=f"/api/admin/plugins/{PLUGIN_SLUG}",
                    tags=["Plugin: guestbook-rss"],
                )
            except Exception:
                pass
    except Exception as exc:
        logger.warning("guestbook-rss: 后台路由挂载失败: %s", exc)

    # ── 后台菜单声明 ────────────────────────────────────────────────────
    menu_decl = _MANIFEST.get("admin_menu") if isinstance(_MANIFEST, dict) else None
    if menu_decl:
        try:
            from backend.core.routing_registry import routing_registry as _rr2

            _rr2.register_admin_menu(menu_decl)
        except Exception as exc:
            logger.warning("guestbook-rss: 菜单注册失败: %s", exc)

    logger.info("guestbook-rss plugin registered (app=%s bus=%s)",
                app is not None, bus is not None)


# ── 总入口（双模式分发） ────────────────────────────────────────────────────


def register(*args: Any, **kwargs: Any) -> Any:
    """统一入口（同步/异步双路径，返回值匹配调用方）。

    - 新风格：``await register(ctx)``  → 返回原生 coroutine。
    - 旧风格：``register(app, bus)`` → 同步返回 None。

    不主动包 asyncio.Task，避免调用方 await result 时抛出：
    ``TypeError: a coroutine was expected, got <Task pending …>``。
    """

    # 旧风格：register(app, bus)
    if "app" in kwargs or "bus" in kwargs or len(args) >= 2:
        app = kwargs.get("app") or (args[0] if len(args) >= 1 else None)
        bus = kwargs.get("bus") or (args[1] if len(args) >= 2 else None)
        return register_via_bus(app, bus)

    # 新风格：register(ctx)
    ctx_like: Any | None = kwargs.get("ctx")
    if ctx_like is None and args:
        ctx_like = args[0]

    if ctx_like is not None:
        return register_via_ctx(ctx_like)

    return register_via_bus(None, None)
