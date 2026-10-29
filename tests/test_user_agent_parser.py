"""UA 派生标签的解析表（访客记录页的"什么系统 / 什么浏览器 / 是不是爬虫"）

这些标签是给人做判断用的，读错一档的表现是"iPad 被当桌面、Googlebot 混进真人 UV"。
所以每条规则都用真实 UA 字符串钉住，并且专门有一组"顺序陷阱"用例：
Chrome 的 UA 里同时含 Safari 与 Macintosh，Edge 的 UA 里同时含 Chrome 与 Safari ——
判定顺序错一位，整列表就全是"桌面 Safari"。
"""

import pytest

from backend.utils.user_agent import describe_user_agent, parse_user_agent

_UA_WINDOWS_CHROME = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/129.0.0.0 Safari/537.36"
)
_UA_WINDOWS_EDGE = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/129.0.0.0 Safari/537.36 Edg/129.0.0.0"
)
_UA_MAC_SAFARI = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 "
    "(KHTML, like Gecko) Version/17.4 Safari/605.1.15"
)
_UA_IPHONE_SAFARI = (
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_5 like Mac OS X) AppleWebKit/605.1.15 "
    "(KHTML, like Gecko) Version/17.5 Mobile/15E148 Safari/604.1"
)
_UA_IPAD = (
    "Mozilla/5.0 (iPad; CPU OS 17_5 like Mac OS X) AppleWebKit/605.1.15 "
    "(KHTML, like Gecko) Version/17.5 Mobile/15E148 Safari/604.1"
)
_UA_ANDROID_CHROME = (
    "Mozilla/5.0 (Linux; Android 14; Pixel 8) AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/128.0.0.0 Mobile Safari/537.36"
)
_UA_ANDROID_TABLET = (
    "Mozilla/5.0 (Linux; Android 13; SM-X700) AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/120.0.0.0 Safari/537.36"
)
_UA_FIREFOX_LINUX = "Mozilla/5.0 (X11; Linux x86_64; rv:130.0) Gecko/20100101 Firefox/130.0"
_UA_UBUNTU_FIREFOX = (
    "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:126.0) Gecko/20100101 Firefox/126.0"
)
_UA_WECHAT_ANDROID = (
    "Mozilla/5.0 (Linux; Android 13; M2012K11AC Build/TK1Q.221007.002; wv) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/110.0.5481.154 "
    "Mobile Safari/537.36 MicroMessenger/8.0.44"
)
_UA_SAMSUNG = (
    "Mozilla/5.0 (Linux; Android 13; SAMSUNG SM-S918B) AppleWebKit/537.36 "
    "(KHTML, like Gecko) SamsungBrowser/23.0 Chrome/115.0.0.0 Mobile Safari/537.36"
)
_UA_OLDCYWINE = "Mozilla/5.0 (Windows NT 6.1; WOW64; rv:52.0) Gecko/20100101 Firefox/52.0"


@pytest.mark.parametrize(
    ("ua", "os_name", "browser", "device"),
    [
        (_UA_WINDOWS_CHROME, "Windows", "Chrome", "desktop"),
        (_UA_WINDOWS_EDGE, "Windows", "Edge", "desktop"),
        (_UA_MAC_SAFARI, "macOS", "Safari", "desktop"),
        (_UA_IPHONE_SAFARI, "iOS", "Safari", "mobile"),
        (_UA_IPAD, "iPadOS", "Safari", "tablet"),
        (_UA_ANDROID_CHROME, "Android", "Chrome", "mobile"),
        (_UA_ANDROID_TABLET, "Android", "Chrome", "tablet"),
        (_UA_FIREFOX_LINUX, "Linux", "Firefox", "desktop"),
        (_UA_UBUNTU_FIREFOX, "Linux (Ubuntu)", "Firefox", "desktop"),
        (_UA_WECHAT_ANDROID, "Android", "微信", "mobile"),
        (_UA_SAMSUNG, "Android", "Samsung Internet", "mobile"),
        (_UA_OLDCYWINE, "Windows", "Firefox", "desktop"),
    ],
)
def test_common_real_world_ua_labels(ua, os_name, browser, device):
    info = parse_user_agent(ua)
    assert info.os == os_name, f"{ua[:40]}... -> {info.os}"
    assert info.browser == browser, f"{ua[:40]}... -> {info.browser}"
    assert info.device == device, f"{ua[:40]}... -> {info.device}"
    assert info.is_bot is False


def test_windows_nt_version_is_mapped_not_raw():
    """`Windows NT 10.0` 是版本号常量而不是"10.0 版"，直接回显会把所有人写成同一档。"""
    assert parse_user_agent(_UA_WINDOWS_CHROME).os_version == "10 / 11"
    assert parse_user_agent(_UA_OLDCYWINE).os_version == "7"


def test_browser_and_os_versions_are_captured():
    info = parse_user_agent(_UA_MAC_SAFARI)
    assert info.os_version == "10.15.7"
    assert info.browser_version == "17.4"


@pytest.mark.parametrize(
    ("ua", "name"),
    [
        ("Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)", "Googlebot"),
        ("Mozilla/5.0 (compatible; bingbot/2.0; +http://www.bing.com/bingbot.htm)", "Bingbot"),
        (
            "Mozilla/5.0 (compatible; Baiduspider/2.0; +http://www.baidu.com/search/spider.html)",
            "Baiduspider",
        ),
        ("facebookexternalhit/1.1 (+http://www.facebook.com/externalhit_uatext.php)", "Facebook"),
        ("curl/8.5.0", "curl"),
        ("python-requests/2.32.3", "python-requests"),
        ("Go-http-client/2.0", "Go http-client"),
        ("Mozilla/5.0 (compatible; NewSpiderBot/1.0)", "NewSpiderBot"),
    ],
)
def test_bots_are_flagged_with_a_name(ua, name):
    info = parse_user_agent(ua)
    assert info.is_bot is True, f"{ua} 必须判成机器流量"
    assert info.bot_name == name
    assert info.device == "bot"


def test_empty_and_bare_ua_are_bots_not_desktops():
    """没有产品标记的 UA（裸扫工具常这么干）按机器处理，否则每个端口扫描都算一个独立访客。"""
    assert parse_user_agent("").is_bot is True
    assert parse_user_agent(None).is_bot is True
    assert parse_user_agent(None).os == "未知"
    assert parse_user_agent("scanner").is_bot is True


def test_human_ua_without_bot_word_is_not_a_bot():
    assert parse_user_agent(_UA_WINDOWS_CHROME).is_bot is False
    assert parse_user_agent(_UA_WINDOWS_CHROME).bot_name == ""


def test_describe_shape_is_a_flat_dict_for_the_api():
    body = describe_user_agent(_UA_WINDOWS_EDGE)
    assert set(body) == {
        "os",
        "os_version",
        "browser",
        "browser_version",
        "device",
        "is_bot",
        "bot_name",
    }
    assert body["browser"] == "Edge"
