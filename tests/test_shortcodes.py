"""
Shortcode 引擎测试
==================

覆盖：
- 基础注册与渲染（自闭合 / 成对闭合）
- 属性解析：key=value、key="value"、key='value'
- 成对短代码：body 传递、嵌套同名短代码（栈深度处理）
- 未注册短代码：原样保留不丢失内容
- 安全：输出经过 HTML allowlist 清洗（剔除 <script>、onxxx= 等）
- 全局 do_shortcode() 函数接口
- register_shortcode / unregister_shortcode 与插件绑定
"""
from __future__ import annotations

import pytest

from backend.core.shortcodes import (
    ShortcodeManager,
    do_shortcode,
    shortcode_manager,
    register_shortcode,
    unregister_shortcode,
)


class TestShortcodeBasic:
    """基础注册与自闭合渲染"""

    def test_register_and_render_self_closing(self):
        sm = ShortcodeManager()

        def greet(name="world", **_):
            return f"<b>Hello {name}!</b>"

        sm.register("greet", greet, plugin="demo")
        rendered = sm.render("Say [greet name=Rosetta /] end")
        assert rendered.endswith("end")
        assert "Hello Rosetta!" in rendered

    def test_render_preserves_surrounding_text(self):
        sm = ShortcodeManager()
        sm.register("ping", lambda **_: "<i>PONG</i>", plugin="demo")
        result = sm.render("AAA [ping/] BBB [ping/] CCC")
        assert result.startswith("AAA ")
        assert result.endswith(" CCC")
        assert result.count("PONG") == 2

    def test_default_attribute_values(self):
        sm = ShortcodeManager()

        def greet(name="stranger", **_):
            return f"Hi, {name}"

        sm.register("greet", greet, plugin="demo")
        # 不带属性
        assert "Hi, stranger" in sm.render("[greet /]")
        # 带属性覆盖
        assert "Hi, Alice" in sm.render("[greet name=Alice /]")


class TestShortcodeAttributes:
    """属性解析：多种引号风格"""

    def test_double_quoted_attrs(self):
        sm = ShortcodeManager()

        def banner(title="", **_):
            return f"<div>{title}</div>"

        sm.register("banner", banner, plugin="demo")
        result = sm.render('[banner title="Hello World" /]')
        assert "Hello World" in result

    def test_single_quoted_attrs(self):
        sm = ShortcodeManager()

        def banner(title="", **_):
            return f"<div>{title}</div>"

        sm.register("banner", banner, plugin="demo")
        result = sm.render("[banner title='Single Quoted' /]")
        assert "Single Quoted" in result

    def test_unquoted_attrs(self):
        sm = ShortcodeManager()

        def gallery(ids="", **_):
            return f"gallery-{ids}"

        sm.register("gallery", gallery, plugin="demo")
        result = sm.render("[gallery ids=1,2,3 /]")
        assert "gallery-1,2,3" in result

    def test_mixed_attrs(self):
        sm = ShortcodeManager()

        def link(text="", url="", **_):
            return f"{text}:{url}"

        sm.register("link", link, plugin="demo")
        result = sm.render('[link url="http://x" text=Visit /]')
        assert "Visit:http://x" in result

    def test_body_passed_to_handler(self):
        sm = ShortcodeManager()

        def box(content="", cls="info", **_):
            # 使用 blockquote（allowlist 内标签），属性用双引号（sanitize 会归一化）
            return f'<blockquote class="{cls}">{content}</blockquote>'

        sm.register("box", box, plugin="demo")
        result = sm.render('[box cls="warning"]Be careful[/box]')
        # sanitize_html 将属性归一化为双引号
        assert '<blockquote class="warning">Be careful</blockquote>' in result


class TestShortcodePaired:
    """成对短代码与 body 捕获"""

    def test_pair_simple_body(self):
        sm = ShortcodeManager()

        def bold(content="", **_):
            return f"<b>{content}</b>"

        sm.register("b", bold, plugin="demo")
        result = sm.render("Start [b]Important[/b] End")
        assert "<b>Important</b>" in result

    def test_pair_contains_nested_unregistered(self):
        """未注册的内部短代码作为 body 文本原样传递（不丢）"""
        sm = ShortcodeManager()

        def wrap(content="", **_):
            # span 在短代码 allowlist 扩展中
            return f"<span>{content}</span>"

        sm.register("wrap", wrap, plugin="demo")
        # [unknown] 未注册 → 保留在 body 中
        result = sm.render("[wrap]hello [unknown x=1] there[/wrap]")
        # 外层被渲染（span），内部保留原样
        assert result.startswith("<span>")
        assert "[unknown x=1]" in result

    def test_pair_no_match_leaves_alone(self):
        """有起始无结束的标签：视为未闭合，原样保留 + 后续短码仍正常"""
        sm = ShortcodeManager()

        def wrap(content="", **_):
            return f"<wrap>{content}</wrap>"

        sm.register("wrap", wrap, plugin="demo")
        sm.register("ping", lambda **_: "PONG", plugin="demo")
        result = sm.render("[wrap]no close [ping/] after")
        # [ping/] 应被正常解析
        assert "PONG" in result
        # 未闭合的 [wrap] 原样保留
        assert "[wrap]" in result


class TestShortcodeStack:
    """同名嵌套短代码的栈匹配"""

    def test_same_name_nested_stack(self):
        sm = ShortcodeManager()
        captured = []

        def box(content="", level="0", **_):
            captured.append((level, content))
            return f"[box-{level}:{content}]"

        sm.register("box", box, plugin="demo")
        # 两级同名嵌套：内部先解析
        result = sm.render('[box level=1]outer [box level=2]inner[/box] tail[/box]')
        # 内层：level=2 content="inner" → 被内层函数先捕获
        # 外层：level=1 content="outer [box-2:inner] tail"
        #   (因为内层先渲染，结果替换回字符串)
        assert "[box-2:inner]" in result
        # 最终应包含最外层的展开
        assert result.startswith("[box-1:outer")
        # captured 顺序：先内层后外层
        levels = [lv for lv, _ in captured]
        assert levels[-1] == "1"
        assert "2" in levels


class TestShortcodeUnregistered:
    """未注册短代码：原样保留，防内容丢失"""

    def test_unregistered_self_closing_kept(self):
        sm = ShortcodeManager()
        result = sm.render("Hello [unknown foo=bar /] world")
        assert "[unknown foo=bar /]" in result

    def test_unregistered_pair_kept(self):
        sm = ShortcodeManager()
        result = sm.render("A [notreal x=1]body[/notreal] B")
        assert "[notreal x=1]body[/notreal]" in result

    def test_mixed_registered_and_unregistered(self):
        sm = ShortcodeManager()
        # <b> 是 allowlist 标签
        sm.register("ok", lambda **_: "<b>OK</b>", plugin="demo")
        result = sm.render("[ok/] [nope/] [ok/]")
        assert result.count("<b>OK</b>") == 2
        assert "[nope/]" in result


class TestShortcodeSanitize:
    """安全：短码输出经过 HTML allowlist 二次清洗"""

    def test_script_tag_stripped(self):
        sm = ShortcodeManager()
        # 恶意 handler 想注入 script
        def evil(**_):
            return '<script>alert(1)</script><b>safe</b>'

        sm.register("evil", evil, plugin="demo")
        result = sm.render("[evil /]")
        # <script> 不应原样出现（被移除 或 转义为实体），浏览器不执行
        assert "<script>" not in result
        assert "alert(1)" not in result  # payload 已消除
        # 允许的 <b> 仍保留
        assert "<b>safe</b>" in result

    def test_onerror_event_attribute_stripped(self):
        sm = ShortcodeManager()

        def img(**_):
            # /x.png 是短代码允许的站内相对路径（sanitize 白名单含 "/" 前缀）
            return '<img src="/x.png" onerror="alert(1)" alt="pic">'

        sm.register("img", img, plugin="demo")
        result = sm.render("[img /]")
        # onerror 属性不应以可执行形式存在（应被转义为实体）
        assert "onerror" not in result or "&#" in result
        # 允许的 src + alt 仍保留
        assert 'src="/x.png"' in result
        assert 'alt="pic"' in result

    def test_javascript_protocol_href_stripped(self):
        sm = ShortcodeManager()

        def link(**_):
            return '<a href="javascript:alert(1)">click</a>'

        sm.register("link", link, plugin="demo")
        result = sm.render("[link /]")
        # javascript: 应被禁用/转义为 #javascript:
        assert 'href="javascript:' not in result
        assert "click" in result

    def test_allowed_tags_preserved(self):
        """计划列出的白名单标签均允许通过"""
        sm = ShortcodeManager()

        def rich(**_):
            return (
                "<p>Para</p>"
                "<ul><li>Item</li></ul>"
                "<pre>code</pre>"
                "<blockquote>quote</blockquote>"
                "<br><i>i</i><em>em</em><strong>s</strong><code>c</code>"
                '<a href="https://example.com">ex</a>'
                '<img src="https://i/a.png" alt="a">'
            )

        sm.register("rich", rich, plugin="demo")
        result = sm.render("[rich /]")
        for tag in (
            "<p>Para</p>",
            "<ul>",
            "<li>Item</li>",
            "<pre>code</pre>",
            "<blockquote>quote</blockquote>",
            "<i>i</i>",
            "<em>em</em>",
            "<strong>s</strong>",
            "<code>c</code>",
            "href=\"https://example.com\"",
            "src=\"https://i/a.png\"",
        ):
            assert tag in result, f"Missing expected tag: {tag}"


class TestGlobalFunctions:
    """全局 do_shortcode / register_shortcode / unregister_shortcode 接口"""

    def setup_method(self):
        """每个测试清理全局 shortcode manager"""
        shortcode_manager._registry.clear()

    def teardown_method(self):
        shortcode_manager._registry.clear()

    def test_do_shortcode_function(self):
        def hi(name="", **_):
            return f"Hi {name}"

        register_shortcode("hi", hi, plugin="t")
        assert "Hi Bob" in do_shortcode("[hi name=Bob /]")

    def test_unregister_shortcode(self):
        def hi(**_):
            return "HI"

        register_shortcode("hi", hi, plugin="t")
        assert "HI" in do_shortcode("[hi /]")

        unregister_shortcode("hi")
        # 注销后未注册 → 原样保留
        result = do_shortcode("[hi /]")
        assert "HI" not in result
        assert "[hi /]" in result

    def test_plugin_binding_removal(self):
        def a(**_): return "A"
        def b(**_): return "B"

        register_shortcode("a", a, plugin="p1")
        register_shortcode("b", b, plugin="p1")
        register_shortcode("c", lambda **_: "C", plugin="p2")

        # 移除 p1 的所有短码
        removed = shortcode_manager.remove_for_plugin("p1")
        assert removed == 2

        # "a" 和 "b" 应不再渲染，但 "c" 仍工作
        assert "[a /]" in do_shortcode("[a /]")
        assert "[b /]" in do_shortcode("[b /]")
        assert "C" in do_shortcode("[c /]")


class TestEdgeCases:
    """边角场景"""

    def test_empty_string(self):
        sm = ShortcodeManager()
        assert sm.render("") == ""
        assert sm.render(None) == ""  # type: ignore[arg-type]

    def test_no_shortcodes_passthrough(self):
        sm = ShortcodeManager()
        text = "Hello World. No short codes here. 123."
        assert sm.render(text) == text

    def test_content_with_square_brackets_not_shortcodes(self):
        """普通括号文本不被误判"""
        sm = ShortcodeManager()
        sm.register("x", lambda **_: "X", plugin="demo")
        result = sm.render("a [x=1] b [invalid] c [x/] d")
        # [x=1] 不符合命名规则（开头是字母/数字），应保留
        assert "[x=1]" in result
        # [invalid] 未注册
        assert "[invalid]" in result
        # [x/] 应被正常渲染
        assert "X" in result
