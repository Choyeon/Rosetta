"""
Rosetta 内容渲染管线（单一注入点）。

把 WordPress 风格的内容处理统一收敛到本模块，核心请求端点只调用这里的函数，
不在各处散落 ``do_shortcode`` / ``apply_filters``：

    短代码 do_shortcode  →  Filter 链（canonical + 历史别名）  →  Action 通知

钩子命名（同时支持 WordPress canonical 名与 Rosetta 历史别名，按序应用）：

=================  ==============================  ==============================
内容               Filter（按顺序）                 Action
=================  ==============================  ==============================
标题               ``the_title`` → ``post.title``   —
正文               ``the_content`` → ``post.content`` 渲染后 ``post.rendered``
摘要               ``the_excerpt`` → ``post.excerpt``  —
=================  ==============================  ==============================

插件只需挂到其中任一名字即可生效；推荐使用 canonical 名。

去耦合保证：
    本模块只依赖 hooks 引擎与 shortcodes 引擎，不感知 ORM，也不修改传入的
    ``post`` 对象。插件回调异常由 hooks 沙箱隔离，绝不冒泡到请求链路。
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

from backend.core.hooks import apply_filters, do_action
from backend.core.shortcodes import do_shortcode

logger = logging.getLogger("rosetta.content_renderer")

# ── 钩子名：canonical（WordPress） + Rosetta 历史别名 ─────────────────────

TITLE_FILTERS: tuple[str, ...] = ("the_title", "post.title")
CONTENT_FILTERS: tuple[str, ...] = ("the_content", "post.content")
EXCERPT_FILTERS: tuple[str, ...] = ("the_excerpt", "post.excerpt")


def build_context(post: Any, language: str | None) -> dict[str, Any]:
    """构造传给短代码 / filter 的轻量上下文字典（不暴露 DB session）。"""
    return {
        "language": language,
        "post_id": getattr(post, "id", None),
        "slug": getattr(post, "slug", None),
    }


async def render_title(
    title: str | None,
    *,
    post: Any = None,
    language: str | None = None,
) -> str | None:
    """渲染标题：依次应用标题 filter 链。"""
    if not isinstance(title, str) or not title:
        return title
    context = build_context(post, language)
    result: Any = title
    for hook_name in TITLE_FILTERS:
        result = await apply_filters(
            hook_name, result, post=post, language=language, context=context
        )
    return result if isinstance(result, str) else title


async def render_content(
    content: str | None,
    *,
    post: Any = None,
    language: str | None = None,
) -> str | None:
    """渲染正文：先执行短代码，再应用正文 filter 链。"""
    if not isinstance(content, str) or not content:
        return content
    context = build_context(post, language)
    result: Any = do_shortcode(content, context=context)
    for hook_name in CONTENT_FILTERS:
        result = await apply_filters(
            hook_name, result, post=post, language=language, context=context
        )
    return result if isinstance(result, str) else content


async def render_excerpt(
    excerpt: str | None,
    *,
    post: Any = None,
    language: str | None = None,
) -> str | None:
    """渲染摘要：先执行短代码，再应用摘要 filter 链。"""
    if not isinstance(excerpt, str) or not excerpt:
        return excerpt
    context = build_context(post, language)
    result: Any = do_shortcode(excerpt, context=context)
    for hook_name in EXCERPT_FILTERS:
        result = await apply_filters(
            hook_name, result, post=post, language=language, context=context
        )
    return result if isinstance(excerpt, str) else excerpt


async def notify_rendered(
    *,
    post: Any,
    language: str | None,
    title: str | None,
    content: str | None,
    excerpt: str | None = None,
) -> None:
    """渲染完成后触发 ``post.rendered`` action（纯通知，返回值忽略）。"""
    context = build_context(post, language)
    await do_action(
        "post.rendered",
        post=post,
        language=language,
        title=title,
        content=content,
        excerpt=excerpt,
        context=context,
    )


@dataclass
class RenderedFields:
    """文章详情一次渲染后的三类字段。"""

    title: str | None
    content: str | None
    excerpt: str | None


async def render_post_fields(
    *,
    title: str | None,
    content: str | None,
    excerpt: str | None,
    post: Any,
    language: str | None,
    render_body: bool = True,
) -> RenderedFields:
    """文章详情端点的一站式入口：渲染标题 / 正文 / 摘要并发出渲染通知。

    Args:
        render_body: 加密文章未通过密码校验时为 False —— 标题仍渲染，
            正文保留空串，摘要按基础信息返回。
    """
    rendered_title = await render_title(title, post=post, language=language)
    if render_body:
        rendered_content = await render_content(content, post=post, language=language)
        rendered_excerpt = (
            await render_excerpt(excerpt, post=post, language=language)
            if isinstance(excerpt, str) and excerpt
            else excerpt
        )
    else:
        rendered_content = ""
        rendered_excerpt = excerpt

    await notify_rendered(
        post=post,
        language=language,
        title=rendered_title,
        content=rendered_content,
        excerpt=rendered_excerpt,
    )
    return RenderedFields(
        title=rendered_title,
        content=rendered_content,
        excerpt=rendered_excerpt,
    )
