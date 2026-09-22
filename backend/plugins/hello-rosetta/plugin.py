"""Hello Rosetta —— Rosetta 示例插件（规范版）。

演示插件平台四类扩展点，全部遵循 WordPress 风格的
**「接收一个值 → 返回一个值」纯函数约定**（不依赖 ORM、不修改传入对象）：

1. Filter ``the_title``   —— 给文章标题幂等追加后缀 ``· hello``；
2. Filter ``the_content`` —— 在正文末尾幂等插入插件署名；
3. Action ``post.rendered`` —— 渲染完成后的通知型钩子（此处仅记日志，演示副作用）；
4. Shortcode ``[hello to="World"]`` —— 在正文里输出问候语 HTML。

注册入口：

- ``register(ctx)``       —— 新 PluginContext 风格；
- ``register(app, bus)``  —— 历史 (app, bus) 风格。

两种调用等价。所有钩子都在 ``register()`` 内以命令式 API 注册，并做
「先按引用移除再注册」，因此：

- 重复调用（双加载路径 / 测试 reset 后重注册）幂等，不会叠加重复回调；
- 插件被停用时由 hooks 引擎按 ``plugin=slug`` 整体摘除。
"""

from __future__ import annotations

import html as _html
import logging
from typing import Any

logger = logging.getLogger("hello_rosetta")

PLUGIN_SLUG = "hello-rosetta"

# 标题后缀；回调据此判断是否已追加（幂等）。
TITLE_SUFFIX = "  · hello"

# 署名块的唯一锚点，用于判重。
SIGNATURE_ANCHOR = "Hello from <b>hello-rosetta</b>"


def _signature_html() -> str:
    """构造正文末尾的插件署名 HTML（仅使用设计变量，不注入自定义样式体系）。"""
    return (
        '<hr class="my-4" style="border-color:hsl(var(--border)/0.6)"/>'
        '<p class="text-sm text-muted-foreground">'
        "— Hello from <b>hello-rosetta</b> 示例插件 —"
        "</p>"
    )


# ── Filter / Action 处理器（模块级单例函数，便于按引用幂等注册） ───────────


def hello_title_filter(title: Any, post: Any = None, context: Any = None, **_kw: Any) -> Any:
    """``the_title``：标题幂等追加后缀。"""
    if not isinstance(title, str) or title.endswith(TITLE_SUFFIX):
        return title
    return title + TITLE_SUFFIX


def hello_content_filter(content: Any, post: Any = None, context: Any = None, **_kw: Any) -> Any:
    """``the_content``：正文末尾幂等插入署名。"""
    if not isinstance(content, str):
        return content
    if SIGNATURE_ANCHOR in content:
        return content
    return content + _signature_html()


def hello_rendered_action(
    post: Any = None,
    title: Any = None,
    content: Any = None,
    **_kw: Any,
) -> None:
    """``post.rendered``：通知型 action，演示渲染完成后的副作用（此处仅 debug 日志）。"""
    logger.debug(
        "hello-rosetta: 一篇内容已完成渲染 slug=%s title=%r",
        getattr(post, "slug", None),
        title,
    )


def hello_shortcode(to: Any = "World", **_kw: Any) -> str:
    """``[hello]`` 短代码：输出问候语；对参数做 HTML 转义防 XSS。"""
    safe_to = _html.escape(str(to))
    return f'<p class="hello-rosetta-greeting">Hello, <b>{safe_to}</b>!</p>'


# ── 注册入口 ────────────────────────────────────────────────────────────────


def register(*args: Any, **kwargs: Any) -> None:
    """统一注册入口：兼容 ``register(ctx)`` 与 ``register(app, bus)``。

    本插件不直接需要 app / bus —— 钩子通过全局 hooks / shortcodes 引擎注册，
    因此忽略传入参数。注册采用「先移除再添加」，保证任意调用次数下每个钩子
    都只有一个处理器。
    """
    from backend.core.hooks import add_action, add_filter, remove_action, remove_filter
    from backend.core.shortcodes import register_shortcode

    # Filter：the_title（默认优先级）/ the_content（靠后，让其它转换先完成）
    remove_filter("the_title", hello_title_filter)
    add_filter("the_title", hello_title_filter, priority=10, plugin=PLUGIN_SLUG)

    remove_filter("the_content", hello_content_filter)
    add_filter("the_content", hello_content_filter, priority=20, plugin=PLUGIN_SLUG)

    # Action：post.rendered（通知）
    remove_action("post.rendered", hello_rendered_action)
    add_action("post.rendered", hello_rendered_action, priority=10, plugin=PLUGIN_SLUG)

    # Shortcode：[hello]（dict 覆盖，天然幂等）
    register_shortcode("hello", hello_shortcode, plugin=PLUGIN_SLUG)

    logger.debug("hello-rosetta 已注册扩展点（args=%d）", len(args))
