"""Hello Rosetta 示例插件。

覆盖三类扩展点：
1. Action 钩子 ``post.rendered`` — 在文章详情页 HTML 尾部插入签名。
2. Filter 钩子 ``post.title`` — 给文章标题统一追加后缀 ``· hello``。
3. Shortcode ``[hello to="World"]`` — 输出问候语 HTML。

两种注册模式兼容：
- ``async def register(ctx)``  —— 新 ctx 风格（计划 D 描述）；
- ``def register(app, bus)`` —— 现有的 plugin_loader 同步风格。
"""

from __future__ import annotations

import html as _html
import logging
from typing import Any

logger = logging.getLogger("hello_rosetta")

PLUGIN_SLUG = "hello-rosetta"

# ── 新风格 ctx 注册 (async) ─────────────────────────────────────────────────


async def register_via_ctx(ctx: Any) -> None:
    """使用新的 PluginContext（extensions.py 内提供）注册。

    ctx 具备：add_action / add_filter / register_shortcode / manifest / settings 等。
    """
    # 1) Action：post.rendered — 在文章内容末尾插入签名
    def _append_signature(post: Any = None, **_kw: Any) -> None:
        if post is None:
            return
        signature = (
            '<hr class="my-4" style="border-color:hsl(var(--border)/0.6)"/>'
            '<p class="text-sm text-muted-foreground">'
            "— Hello from <b>hello-rosetta</b> 示例插件 —"
            "</p>"
        )
        existing = getattr(post, "content_html", "") or ""
        if signature not in existing:
            try:
                post.content_html = existing + signature
            except Exception:
                pass

    ctx_add_action = getattr(ctx, "add_action", None)
    if callable(ctx_add_action):
        ctx_add_action("post.rendered", _append_signature)
    else:  # 兼容旧 ctx 没有 add_action —— 走全局 hooks.py
        from backend.core.hooks import register_action

        register_action("post.rendered", plugin=PLUGIN_SLUG)(_append_signature)

    # 2) Filter：post.title — 追加后缀
    def _title_suffix(title: str, _post: Any = None, **_kw: Any) -> str:
        suffix = "  · hello"
        if not isinstance(title, str):
            return title
        if title.endswith(suffix):
            return title
        return title + suffix

    ctx_add_filter = getattr(ctx, "add_filter", None)
    if callable(ctx_add_filter):
        ctx_add_filter("post.title", _title_suffix)
    else:
        from backend.core.hooks import register_filter

        register_filter("post.title", plugin=PLUGIN_SLUG)(_title_suffix)

    # 3) Shortcode：[hello to="World"/] —— <p>Hello, <b>World</b>!</p>
    def _shortcode_hello(to: str = "World", **_kw: Any) -> str:
        safe_to = _html.escape(str(to))
        return f'<p class="hello-rosetta-greeting">Hello, <b>{safe_to}</b>!</p>'

    ctx_register_sc = getattr(ctx, "register_shortcode", None)
    if callable(ctx_register_sc):
        ctx_register_sc("hello", _shortcode_hello)
    else:  # 回退：走 core.shortcodes 直接注册
        try:
            from backend.core.shortcodes import register_shortcode

            register_shortcode("hello", _shortcode_hello, plugin=PLUGIN_SLUG)
        except Exception as exc:  # pragma: no cover - 防御性
            logger.warning("hello-rosetta: shortcode 注册失败: %s", exc)


# ── 旧风格 (app, bus) 注册 —— 当前 plugin_loader 实际使用 ──────────────────


def register_via_bus(app: Any = None, bus: Any = None) -> None:
    """与 plugin_loader 的 ``register(app, bus)`` 签名兼容。"""
    from backend.core.hooks import register_action, register_filter

    # Action
    @register_action("post.rendered", plugin=PLUGIN_SLUG)
    def _append(post: Any = None, **_kw: Any) -> None:
        if post is None:
            return
        signature = (
            '<hr class="my-4" style="border-color:hsl(var(--border)/0.6)"/>'
            '<p class="text-sm text-muted-foreground">'
            "— Hello from <b>hello-rosetta</b> 示例插件 —"
            "</p>"
        )
        existing = getattr(post, "content_html", "") or ""
        if signature not in existing:
            try:
                post.content_html = existing + signature
            except Exception:
                pass

    # Filter
    @register_filter("post.title", plugin=PLUGIN_SLUG)
    def _suffix(title: str, **_kw: Any) -> str:
        suffix = "  · hello"
        if not isinstance(title, str):
            return title
        if title.endswith(suffix):
            return title
        return title + suffix

    # Shortcode — 直接注册到 core.shortcodes
    try:
        from backend.core.shortcodes import register_shortcode

        def _hello(to: str = "World", **_kw: Any) -> str:
            safe_to = _html.escape(str(to))
            return f'<p class="hello-rosetta-greeting">Hello, <b>{safe_to}</b>!</p>'

        register_shortcode("hello", _hello, plugin=PLUGIN_SLUG)
    except Exception as exc:  # pragma: no cover
        logger.warning("hello-rosetta: shortcode 注册失败: %s", exc)

    # 同时注册到 bus (plugin_loader 传过来的那个)
    if bus is not None and hasattr(bus, "add_filter"):
        def _bus_suffix(title: str, **_kw: Any) -> str:
            suffix = "  · hello"
            if not isinstance(title, str) or title.endswith(suffix):
                return title
            return title + suffix
        try:
            bus.add_filter("post.title", _bus_suffix)
        except Exception:
            pass

    logger.info("hello-rosetta plugin registered (app=%s bus=%s)",
                app is not None, bus is not None)


# 暴露给 plugin_loader 的入口：优先识别是否以 ctx 调用
def register(*args: Any, **kwargs: Any) -> Any:
    """统一入口（同步/异步双路径，返回值匹配调用方）。

    - 新风格：``await register(ctx)``  → 返回 awaitable（coroutine），由
      PluginManager / PluginLoader 的 ``await register(...)`` 执行。
    - 旧风格：``register(app, bus)`` → 直接返回 None，同步完成。

    注意：**不** 主动包 asyncio.Task，避免调用方做
    ``if hasattr(result, '__await__'): await result`` 时出现
    "a coroutine was expected, got <Task …>" 类型错误。
    """

    # —— 旧风格：register(app, bus)，显式关键字或 2 个位置参数 ——
    if "app" in kwargs or "bus" in kwargs or len(args) >= 2:
        app = kwargs.get("app") or (args[0] if len(args) >= 1 else None)
        bus = kwargs.get("bus") or (args[1] if len(args) >= 2 else None)
        return register_via_bus(app, bus)

    # —— 新风格：register(ctx)（1 个位置参数 / ctx 关键字） ——
    ctx_like: Any | None = kwargs.get("ctx")
    if ctx_like is None and args:
        ctx_like = args[0]

    if ctx_like is not None:
        # 返回原生 coroutine：调用方 await 即可。
        return register_via_ctx(ctx_like)

    # 兜底：无参数 → 退化为旧风格空参数调用（同步）。
    return register_via_bus(None, None)
