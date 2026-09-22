"""SEO Toolkit — Rosetta 内建插件。

以 WordPress 风格注册以下扩展点：

- action ``post.published`` —— 文章发布时记录搜索引擎 ping 占位；
- filter ``the_content``（priority=5，先于正文类插件执行）—— 正文末尾追加
  JSON-LD 占位注释；
- action ``plugin.activated`` —— 自身被激活时输出一条日志，便于验证钩子链路。

注册约定（与 hello-rosetta 一致）：

所有钩子**只在** :func:`register` 被调用时通过命令式 API 注册，而非模块导入时
靠装饰器注册 —— 这样「已停用」插件即使被任何路径意外 import，也不会偷偷挂载
处理器。注册采用「先移除再添加」，任意调用次数下每个钩子都只有一个处理器。
``register()`` 同时兼容 ``register(ctx)`` 与 ``register(app, bus)`` 两种签名。
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger("seo_toolkit")

PLUGIN_SLUG = "seo-toolkit"


# ── Hook 处理器（纯函数，导入无副作用） ────────────────────────────────────


def on_post_published_ping(post_id: int, **kwargs: Any) -> None:
    """(示例) 文章发布后通知搜索引擎。"""
    logger.info("SEO Toolkit: post %s published — ping stub.", post_id)


def inject_jsonld_comment_marker(
    html_content: str,
    context: dict | None = None,
    **kwargs: Any,
) -> str:
    """(示例) 在内容末尾追加 JSON-LD 占位符注释（幂等）。"""
    marker = "<!-- seo-toolkit:article-jsonld-placeholder -->"
    if marker in (html_content or ""):
        return html_content
    return (html_content or "") + "\n" + marker


def on_self_activated(slug: str, **kwargs: Any) -> None:
    """插件自己被激活时打印一条日志，便于验证钩子链路。"""
    if slug == PLUGIN_SLUG:
        logger.info("SEO Toolkit 已激活 ✅ plugin.activated 钩子触发成功")


# ── 统一注册入口 ────────────────────────────────────────────────────────────


def register(*args: Any, **kwargs: Any) -> None:
    """Rosetta 插件入口（兼容 ``register(ctx)`` 与 ``register(app, bus)``）。

    本插件不需要直接使用 app / bus / ctx —— 钩子统一汇入全局 hooks 引擎，
    因此忽略传入参数。
    """
    from backend.core.hooks import add_action, add_filter, remove_action, remove_filter

    # Action：post.published（默认优先级）
    remove_action("post.published", on_post_published_ping)
    add_action("post.published", on_post_published_ping, priority=10, plugin=PLUGIN_SLUG)

    # Filter：the_content（priority=5，先于默认 10 的正文转换执行）
    remove_filter("the_content", inject_jsonld_comment_marker)
    add_filter(
        "the_content",
        inject_jsonld_comment_marker,
        priority=5,
        plugin=PLUGIN_SLUG,
    )

    # Action：plugin.activated（自身激活通知）
    remove_action("plugin.activated", on_self_activated)
    add_action("plugin.activated", on_self_activated, priority=10, plugin=PLUGIN_SLUG)

    logger.debug("seo-toolkit 已注册扩展点（args=%d）", len(args))
