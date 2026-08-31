"""SEO Toolkit — Rosetta 示例插件。

以 WordPress 风格注册：
- action ``post.published`` — 文章发布时 ping 搜索引擎占位
- filter ``the_content`` — 正文末尾插入 JSON-LD 占位注释

启动入口：使用 `register(app, bus)` 协议；插件管理器会在激活时导入模块
并优先调用 ``register()``。
"""
from __future__ import annotations

import logging
from typing import Any

try:
    from backend.core.hooks import register_action, register_filter
except Exception:  # pragma: no cover - 导入失败的最小兼容
    def register_action(*a: Any, **kw: Any):  # type: ignore[no-redef]
        def deco(fn: Any) -> Any:
            return fn
        return deco

    def register_filter(*a: Any, **kw: Any):  # type: ignore[no-redef]
        def deco(fn: Any) -> Any:
            return fn
        return deco

logger = logging.getLogger("seo_toolkit")


@register_action("post.published", plugin="seo-toolkit")
def on_post_published_ping(post_id: int, **kwargs: Any) -> None:
    """(示例) 文章发布后通知搜索引擎。"""
    logger.info("SEO Toolkit: post %s published — ping stub.", post_id)


@register_filter("the_content", priority=5, plugin="seo-toolkit")
def inject_jsonld_comment_marker(
    html_content: str,
    context: dict | None = None,
    **kwargs: Any,
) -> str:
    """(示例) 在内容末尾追加 JSON-LD 占位符注释。"""
    marker = "<!-- seo-toolkit:article-jsonld-placeholder -->"
    if marker in (html_content or ""):
        return html_content
    return (html_content or "") + "\n" + marker


@register_action("plugin.activated", plugin="seo-toolkit")
def on_self_activated(slug: str, **kwargs: Any) -> None:
    """插件自己被激活时打印一条日志，便于验证钩子链路。"""
    if slug == "seo-toolkit":
        logger.info("SEO Toolkit 已激活 ✅ plugin.activated 钩子触发成功")


def register(app: Any | None = None, bus: Any | None = None, **_: Any) -> None:
    """Rosetta 插件入口函数（可选项，便于未来传 app/event-bus）。

    本插件所有钩子通过装饰器在模块导入时完成注册，这里仅做显式标记与
    可选的初始化动作（例如向 FastAPI app 额外挂 route）。
    """
    logger.info(
        "SEO Toolkit register() 被调用 (app=%s, bus=%s)",
        app is not None,
        bus is not None,
    )
