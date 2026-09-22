"""Guestbook RSS — Rosetta 内建插件。

覆盖三类扩展点：

1. **独立前台路由** ``GET /api/plugins/guestbook-rss/feed.xml`` ——
   输出留言板公开条目作为 RSS 2.0 feed（含 Atom 自链接、Dublin Core 作者）。
2. **独立后台路由** ``GET/PUT /api/admin/plugins/guestbook-rss/settings`` ——
   读写插件设置；PUT 经 ``PluginManager`` 持久化到站点 KV。
3. **admin_menu 声明** —— manifest 中声明菜单，注册到路由注册表供前端 sidebar 消费。

注册入口 :func:`register` 同时兼容 ``register(ctx)`` 与 ``register(app, bus)`` 两种
签名：内部只有一份路由构造逻辑，通过 :mod:`backend.core.routing_registry` 完成挂载，
全路径幂等（重复调用不会重复注册或重复挂载）。
"""

from __future__ import annotations

import html as _html
import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# 模块级导入：嵌套路由函数注解里的 Response 需在模块全局可解析，否则
# /openapi.json 生成时 get_type_hints 退化为 ForwardRef 会导致 500。
from fastapi import Request, Response

logger = logging.getLogger("guestbook_rss")

PLUGIN_SLUG = "guestbook-rss"

# 读取 manifest（失败时回退空 dict，设置仍有硬编码默认值）
_MANIFEST: dict = {}
try:
    _MANIFEST = json.loads(
        (Path(__file__).resolve().parent / "rosetta-plugin.json").read_text(encoding="utf-8")
    )
except Exception as exc:  # pragma: no cover
    logger.warning("guestbook-rss: 无法读取 manifest: %s", exc)

# 内存设置副本：DB 不可用时的兜底，也便于 smoke test 不走 DB 断言读写
_MEM_SETTINGS: dict = {}


def _default_settings() -> dict:
    sch = _MANIFEST.get("settings_schema", {}).get("properties", {}) or {}
    return (
        {k: v.get("default") for k, v in sch.items()}
        if sch
        else {
            "feed_title": "Rosetta 留言板 RSS",
            "feed_description": "最近 50 条公开留言",
            "max_items": 50,
            "include_author_email": False,
            "language": "zh-CN",
        }
    )


async def _load_settings() -> dict:
    """读取设置：优先 DB 持久化值，其次内存副本，最后默认值。任何异常安全回退。"""
    try:
        from backend.core.database import async_session_maker
        from backend.core.extensions import plugin_manager

        if async_session_maker is not None:
            async with async_session_maker() as db:  # type: ignore[misc]
                persisted = await plugin_manager.get_settings(db, PLUGIN_SLUG)
            if isinstance(persisted, dict) and persisted:
                return persisted
    except Exception:  # noqa: BLE001
        logger.debug("guestbook-rss: DB 设置读取失败，使用内存/默认值", exc_info=True)
    if _MEM_SETTINGS:
        return {**_default_settings(), **_MEM_SETTINGS}
    return _default_settings()


async def _persist_settings(merged: dict) -> bool:
    """经 PluginManager 持久化设置；同步更新内存副本。返回是否落库成功。"""
    _MEM_SETTINGS.update(merged)
    try:
        from backend.core.database import async_session_maker
        from backend.core.extensions import plugin_manager

        if async_session_maker is None:
            return False
        async with async_session_maker() as db:  # type: ignore[misc]
            await plugin_manager.set_settings(db, PLUGIN_SLUG, merged)
            await db.commit()
        return True
    except Exception:  # noqa: BLE001
        logger.debug("guestbook-rss: 设置持久化失败，仅保留内存副本", exc_info=True)
        return False


# ── RSS XML 生成器 ──────────────────────────────────────────────────────────


def _rss_xml(
    entries: list[Any],
    settings: dict | None,
    *,
    self_url: str,
    guestbook_url: str,
) -> str:
    """生成 RSS 2.0 feed XML。

    :param entries: 任意对象列表，需有 ``id / author_name / content / created_at``
        属性，缺失字段用默认值兜底。
    :param settings: feed_title / feed_description / language / max_items /
        include_author_email。
    :param self_url: 本 feed 的完整 URL（写入 ``atom:link rel="self"``）。
    :param guestbook_url: 留言板页面完整 URL（channel link 与条目 link）。
    """
    s = settings or _default_settings()
    title = _html.escape(str(s.get("feed_title") or "Rosetta 留言板 RSS"))
    desc = _html.escape(str(s.get("feed_description") or "最近公开留言"))
    lang = _html.escape(str(s.get("language") or "zh-CN"))
    max_items = max(1, min(int(s.get("max_items") or 50), 200))
    include_email = bool(s.get("include_author_email", False))
    now = datetime.now(timezone.utc).strftime("%a, %d %b %Y %H:%M:%S GMT")

    safe_self = _html.escape(self_url, quote=True)
    safe_guestbook = _html.escape(guestbook_url, quote=True)

    lines: list[str] = []
    lines.append('<?xml version="1.0" encoding="UTF-8"?>')
    lines.append(
        '<rss version="2.0" xmlns:atom="http://www.w3.org/2005/Atom"'
        ' xmlns:dc="http://purl.org/dc/elements/1.1/">'
    )
    lines.append("  <channel>")
    lines.append(f"    <title>{title}</title>")
    lines.append(f"    <link>{safe_guestbook}</link>")
    lines.append(f"    <description>{desc}</description>")
    lines.append(f"    <language>{lang}</language>")
    lines.append(f"    <lastBuildDate>{now}</lastBuildDate>")
    lines.append(
        f'    <atom:link href="{safe_self}" rel="self" type="application/rss+xml"/>'
    )

    for e in list(entries or [])[:max_items]:
        eid = getattr(e, "id", 0) or 0
        author = getattr(e, "author_name", "Anonymous") or "Anonymous"
        email = getattr(e, "author_email", None) or ""
        content = getattr(e, "content", "") or ""
        created = getattr(e, "created_at", None)
        try:
            pub_date = (
                created.astimezone(timezone.utc).strftime("%a, %d %b %Y %H:%M:%S GMT")
                if hasattr(created, "astimezone")
                else now
            )
        except Exception:  # noqa: BLE001
            pub_date = now

        safe_author = _html.escape(str(author))
        safe_content = _html.escape(str(content))
        entry_link = f"{guestbook_url}#entry-{eid}"

        lines.append("    <item>")
        lines.append(f"      <title><![CDATA[{safe_author} 留言]]></title>")
        lines.append(f"      <link>{_html.escape(entry_link, quote=True)}</link>")
        lines.append(
            f'      <guid isPermaLink="false">guestbook-entry-{eid}@rosetta.dev</guid>'
        )
        lines.append(f"      <pubDate>{pub_date}</pubDate>")
        if include_email and email:
            lines.append(f"      <author>{_html.escape(str(email), quote=True)} ({safe_author})</author>")
        else:
            lines.append(f"      <dc:creator>{safe_author}</dc:creator>")
        lines.append(f"      <description><![CDATA[{safe_content}]]></description>")
        lines.append("    </item>")

    lines.append("  </channel>")
    lines.append("</rss>")
    return "\n".join(lines) + "\n"


# ── 路由构造（两种 register 签名共用的唯一实现） ───────────────────────────


def _build_routers() -> tuple[Any, Any]:
    """构造前台 feed 路由与后台 settings 路由（各一次）。"""
    from fastapi import APIRouter

    public = APIRouter(tags=["Guestbook RSS"])

    @public.get("/feed.xml")
    async def rss_feed(request: Request) -> Response:
        settings = await _load_settings()
        rows: list[Any] = []
        try:
            from sqlalchemy import select

            from backend.core.database import async_session_maker
            from backend.models.guestbook import GuestbookEntry

            async with async_session_maker() as db:  # type: ignore[misc]
                stmt = (
                    select(GuestbookEntry)
                    .where(GuestbookEntry.status == "approved")
                    .order_by(GuestbookEntry.created_at.desc())
                    .limit(max(1, min(int(settings.get("max_items") or 50), 200)))
                )
                rows = list((await db.execute(stmt)).scalars().all())
        except Exception:  # noqa: BLE001 - DB 异常时输出空 channel，结构仍然合法
            rows = []

        self_url = str(request.url)
        base = f"{request.url.scheme}://{request.url.netloc}"
        body = _rss_xml(rows, settings, self_url=self_url, guestbook_url=f"{base}/guestbook")
        return Response(body, media_type="application/rss+xml; charset=utf-8")

    admin = APIRouter(tags=["Guestbook RSS Admin"])

    @admin.get("/settings")
    async def get_settings() -> dict:
        return {"success": True, "data": await _load_settings()}

    @admin.put("/settings")
    async def put_settings(payload: dict) -> dict:
        if not isinstance(payload, dict):
            return {"success": False, "error_code": "VALIDATION_FAILED", "message": "payload 必须是 object"}
        current = await _load_settings()
        merged = {**current, **payload}
        await _persist_settings(merged)
        return {"success": True, "data": merged}

    return public, admin


# ── 统一注册入口 ────────────────────────────────────────────────────────────


def register(*args: Any, **kwargs: Any) -> Any:
    """插件注册总入口（同步/异步双路径，返回值匹配调用方）。

    - ``await register(ctx)``：新风格，使用 ctx 的注册方法（内部仍汇入
      routing_registry）；
    - ``register(app, bus)``：旧风格，直接登记到 routing_registry。

    两种路径共用 :func:`_build_routers` 的同一份构造结果；routing_registry
    按 slug 去重，因此任意调用次数都安全幂等。
    """
    from backend.core.routing_registry import routing_registry

    # 识别 ctx：PluginContext 带 register_public_router；FastAPI app 不会有
    ctx: Any = None
    if args and hasattr(args[0], "register_public_router"):
        ctx = args[0]
    ctx = kwargs.get("ctx", ctx)

    if ctx is not None:
        return _register_via_ctx(ctx, routing_registry)
    return _register_sync(routing_registry)


async def _register_via_ctx(ctx: Any, routing_registry: Any) -> None:
    """新风格：通过 ctx 注册路由与菜单。"""
    public, admin = _build_routers()
    ctx.register_public_router(public)
    ctx.register_admin_router(admin)

    menu_decl = _MANIFEST.get("admin_menu")
    if isinstance(menu_decl, dict) and menu_decl.get("label") and menu_decl.get("path"):
        # 菜单去重：沙箱导入器可能已预注册过一次
        exists = any(
            m.get("slug") == PLUGIN_SLUG and m.get("path") == menu_decl.get("path")
            for m in routing_registry.list_menu()
        )
        if not exists:
            try:
                ctx.register_admin_menu(menu_decl)
            except Exception as exc:  # noqa: BLE001
                logger.warning("guestbook-rss: ctx.register_admin_menu 失败: %s", exc)


def _register_sync(routing_registry: Any) -> None:
    """旧风格：直接登记到 routing_registry（已注册则整体跳过）。"""
    if routing_registry.has_slug(PLUGIN_SLUG):
        logger.debug("guestbook-rss: 路由已注册，跳过（幂等）")
    else:
        public, admin = _build_routers()
        routing_registry.register_public_router(PLUGIN_SLUG, public)
        routing_registry.register_admin_router(PLUGIN_SLUG, admin)

    menu_decl = _MANIFEST.get("admin_menu")
    if isinstance(menu_decl, dict) and menu_decl.get("label") and menu_decl.get("path"):
        # 菜单幂等：已存在相同 slug+path 则不重复登记
        exists = any(
            m.get("slug") == PLUGIN_SLUG and m.get("path") == menu_decl.get("path")
            for m in routing_registry.list_menu()
        )
        if not exists:
            routing_registry.register_admin_menu(menu_decl)
