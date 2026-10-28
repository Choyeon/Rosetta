"""轮播按钮链接的伪协议闸门（写侧）—— 与渲染侧 `frontend/lib/hero-cta.ts` 同口径。

`cta_url` / `cta_secondary_url` 最终成为访客首页上 `<a href>` 的一部分。这两个框填的是
**站内路径**（`/posts`、`/series/xxx`），所以不能套用"必须 http(s)"的严格档；但可执行协议
必须在这里就拒掉，理由与 §12.8 一致：只守渲染侧不算守——库里躺着脏值时换一个消费点就中招。
"""

import pytest

from backend.schemas._url_policy import reject_pseudo_url_scheme as _reject_pseudo_url_scheme
from backend.schemas.hero import HeroSlideCreate, HeroSlideUpdate

BAD = [
    "javascript:alert(document.cookie)",
    "  javascript:alert(1)",
    "JaVaScRiPt:alert(1)",
    "data:text/html,<script>alert(1)</script>",
    "vbscript:msgbox(1)",
    "file:///etc/passwd",
    # 浏览器解析 URL 时会剥掉 \t \n \r 与空格，所以这三条在点击时都是可执行协议，
    # 只在串首做人眼判定挡不住。
    "javas\tcript:alert(1)",
    "java\nscript:alert(1)",
    "j a v a s c r i p t:alert(1)",
]

GOOD = [
    "/posts/hello",
    "/series/python?tab=1#top",
    "https://example.com/a",
    "http://example.com/a",
    "//cdn.example.com/x",
    "",
    None,
]


class TestHelper:
    @pytest.mark.parametrize("value", BAD)
    def test_rejects_pseudo_scheme(self, value):
        with pytest.raises(ValueError):
            _reject_pseudo_url_scheme(value)

    @pytest.mark.parametrize("value", GOOD)
    def test_passes_everything_else_through(self, value):
        """站内路径与外链是这两个框的正常用法，闸门只管协议。"""
        assert _reject_pseudo_url_scheme(value) == value


@pytest.mark.parametrize("model", [HeroSlideCreate, HeroSlideUpdate])
class TestSchemaWired:
    """字段声明了却不挂 validator ＝ 写了个没人执行的函数。"""

    def test_validators_present(self, model):
        validators = model.__pydantic_decorators__.field_validators
        for field in ("cta_url", "cta_secondary_url"):
            hooked = any(field in d.info.fields for d in validators.values())
            assert hooked, f"{model.__name__} 的 {field} 没挂 scheme 校验"

    @pytest.mark.parametrize("value", BAD)
    def test_create_and_update_reject(self, model, value):
        # media_url 是必填项：不填的话 ValidationError 会先因为"缺字段"抛出，
        # 那条断言就证不到协议闸门。补一个合法 media_url 让唯一的变量是被测字段。
        with pytest.raises(ValueError, match="可执行协议"):
            model(media_url="/a.jpg", cta_secondary_url=value)

    def test_relative_path_still_accepted(self, model):
        row = model(media_url="/a.jpg", cta_url="/posts/a", cta_secondary_url="/series/b")
        assert row.cta_url == "/posts/a"
        assert row.cta_secondary_url == "/series/b"
