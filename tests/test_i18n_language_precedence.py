"""接口语言优先级契约：lang 参数 > Accept-Language > 默认，**cookie 不参与**。

背景：`rosetta_lang` cookie 曾排在 Accept-Language 之前，于是"访客点过一次繁体"
之后，访问简体中文裸路径 `/posts/xxx` 时所有不带 `lang` 参数的接口（导航、分类/标签
名、公告、留言板）都返回繁体——SSR 先渲简体、客户端补拉后翻回繁体。语言真相只有 URL
前缀（AGENTS §2.3.3.6），cookie 现在只服务前端 `locale-prefix.global.client.ts` 的
跨页保序。本用例把这条口径钉在后端：任何带 cookie 的请求都不得被 cookie 改写语言。
"""

from starlette.requests import Request

from backend.core.i18n import DEFAULT_LANGUAGE, get_language_from_request


def _request(headers: dict[str, str]) -> Request:
    return Request(
        {
            "type": "http",
            "method": "GET",
            "path": "/api/blog/posts",
            "headers": [(k.lower().encode(), v.encode()) for k, v in headers.items()],
            "query_string": b"",
            "client": ("127.0.0.1", 12345),
            "server": ("127.0.0.1", 8000),
            "scheme": "http",
        }
    )


class TestCookieIsIgnored:
    def test_hant_cookie_does_not_override_default(self):
        # 简体裸路径 + 浏览器英文头都不该被繁体 cookie 翻掉
        req = _request({"Cookie": "rosetta_lang=zh_Hant", "Accept-Language": "zh-CN,zh;q=0.9"})
        assert get_language_from_request(req) == "zh"

    def test_hant_cookie_does_not_override_accept_language(self):
        req = _request({"Cookie": "rosetta_lang=zh_Hant", "Accept-Language": "ja"})
        assert get_language_from_request(req) == "ja"

    def test_en_cookie_does_not_override_accept_language(self):
        req = _request({"Cookie": "rosetta_lang=en", "Accept-Language": "zh-Hant-TW"})
        assert get_language_from_request(req) == "zh_Hant"

    def test_cookie_only_request_falls_back_to_default(self):
        req = _request({"Cookie": "rosetta_lang=ja"})
        assert get_language_from_request(req) == DEFAULT_LANGUAGE


class TestPrecedence:
    def test_lang_param_beats_accept_language(self):
        req = _request({"Accept-Language": "en"})
        assert get_language_from_request(req, lang_param="ja") == "ja"

    def test_accept_language_used_when_no_param(self):
        req = _request({"Accept-Language": "en-US,en;q=0.9"})
        assert get_language_from_request(req) == "en"

    def test_no_request_and_no_param_is_default(self):
        assert get_language_from_request(None) == DEFAULT_LANGUAGE
        assert get_language_from_request(_request({})) == DEFAULT_LANGUAGE

    def test_underscore_locale_in_accept_language_is_preserved(self):
        # 前端用 URL 前缀码写头，zh_Hant 带下划线；不能因为不是标准 tag 就退回默认
        req = _request({"Accept-Language": "zh_Hant"})
        assert get_language_from_request(req) == "zh_Hant"
