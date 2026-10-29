"""
User-Agent 派生信息：什么系统 / 什么浏览器 / 什么设备 / 是不是爬虫。

为什么在读取口现算而不落库：``visit_logs`` 是只增的遥测表，而 UA 规则会随浏览器改版。
把一次解析结果写进历史行，等于让那次误判永久固化；现算则每一行都跟着最新规则走，
也不必给只增表做回填迁移。

刻意不引 ua-parser / user-agents 之类第三方库：后台只需要"给人看的四档标签"，
不需要完整 UA 数据库。正则表可单测、可控、零依赖（也避免函数体里藏未声明依赖那类事故）。

诚实的边界：UA 嗅探本身有天花板 —— iOS 13+ 的 Safari 可以请求"桌面网站"并伪装成
Macintosh，Android 平板与手机在 UA 上并不总是可分。所以设备档位给的是"最可能"，
原始 UA 字符串始终随行返回，判断依据要能被人工复核。
"""

import re
from dataclasses import dataclass

# ── 爬虫 / 命令行客户端 ────────────────────────────────────────────────────
# 顺序即优先级：具名引擎在前，通用兜底在后。
_BOT_RULES: tuple[tuple[str, str], ...] = (
    (r"Googlebot-Image", "Googlebot-Image"),
    (r"Googlebot-Video", "Googlebot-Video"),
    (r"Googlebot|Google-Read-Aloud|Mediapartners-Google", "Googlebot"),
    (r"Bingbot|msnbot", "Bingbot"),
    (r"Baiduspider", "Baiduspider"),
    (r"Yandex(bot|Images|Video)", "Yandexbot"),
    (r"DuckDuckBot", "DuckDuckBot"),
    (r"Slurp", "Yahoo Slurp"),
    (r"facebot|facebookexternalhit", "Facebook"),
    (r"Twitterbot", "X/Twitter"),
    (r"LinkedInBot", "LinkedIn"),
    (r"Slackbot", "Slack"),
    (r"TelegramBot", "Telegram"),
    (r"WhatsApp", "WhatsApp"),
    (r"PetalBot", "PetalBot"),
    (r"Sogou (web|inst)?", "Sogou"),
    (r"360Spider", "360Spider"),
    (r"AhrefsBot", "AhrefsBot"),
    (r"SemrushBot|Semrush", "Semrush"),
    (r"MJ12bot", "Majestic"),
    (r"DotBot", "DotBot"),
    (r"DataForSeoBot", "DataForSeo"),
    (r"Pulsepoint|Turnbot|Gigabot", "广告/抓取bot"),
    (r"FeedFetcher|Google-Favicon", "Google 辅助抓取"),
    (r"curl/", "curl"),
    (r"Wget/", "wget"),
    (r"python-requests", "python-requests"),
    (r"Python-urllib", "python-urllib"),
    (r"Go-http-client", "Go http-client"),
    (r"okhttp/", "okhttp"),
    (r"node-fetch|und\.io|got/|axios/", "Node HTTP 客户端"),
    (r"libwww-perl", "libwww-perl"),
    (r"Java/", "Java HTTP 客户端"),
    (r"HTTPie/", "HTTPie"),
    (r"Zgrab|Masscan|Censys|Netcraft|ScoutJet", "扫描器"),
)

# 通用兜底：形如 `SomeThingBot/1.0` 的具名 bot（未在上表登记的长尾引擎）
_GENERIC_BOT_RE = re.compile(r"([A-Za-z0-9._-]*[Bb]ot(?:/[0-9.]+)?)")

# ── 操作系统 ───────────────────────────────────────────────────────────────
_WINDOWS_NT_MAP = {
    "10.0": "10 / 11",
    "6.3": "8.1",
    "6.2": "8",
    "6.1": "7",
    "6.0": "Vista",
    "5.2": "Server 2003",
    "5.1": "XP",
}


@dataclass
class UserAgentInfo:
    """一条 UA 的派生标签（全部为给人看的短字符串，未知时统一 "未知"）。"""

    os: str
    os_version: str
    browser: str
    browser_version: str
    device: str
    is_bot: bool
    bot_name: str


def detect_bot(ua: str) -> tuple[bool, str]:
    """是否机器流量，以及具名引擎。"""
    for pattern, name in _BOT_RULES:
        if re.search(pattern, ua, re.IGNORECASE):
            return True, name
    # 兜底认 `XxxBot/x.y`：表现是"新冒头的长尾爬虫也被归到 bot 档"，
    # 而不是混进真人访问里把 UV 抬高。
    match = _GENERIC_BOT_RE.search(ua)
    if match:
        return True, match.group(1).split("/")[0]
    # 没有任何产品标记的空/畸形 UA（裸扫工具常这么干）按机器处理
    if not ua or "/" not in ua:
        return True, "无标识客户端"
    return False, ""


def _os_info(ua: str) -> tuple[str, str]:
    if m := re.search(r"Windows NT ([\d.]+)", ua):
        return "Windows", _WINDOWS_NT_MAP.get(m.group(1), m.group(1))
    if re.search(r"Windows Phone|WPDesktop", ua):
        return "Windows Phone", ""
    # iPad 的 UA 写的是 `CPU OS x_y like Mac OS X`，与 iPhone 同形，所以 iPad 必须排在
    # 通用 iOS 分支之前——否则平板会被标成 iOS，设备档位和系统名字互相矛盾。
    if m := re.search(r"iPad;.*OS ([\d_]+)", ua):
        return "iPadOS", m.group(1).replace("_", ".")
    if m := re.search(r"iPhone OS ([\d_]+)", ua):
        return "iOS", m.group(1).replace("_", ".")
    if m := re.search(r"CPU (?:iPhone )?OS ([\d_]+)", ua):
        return "iOS", m.group(1).replace("_", ".")
    if "Android" in ua:
        m = re.search(r"Android ([\d.]+)", ua)
        return "Android", m.group(1) if m else ""
    if m := re.search(r"CrOS \S+ ([\d.]+)", ua):
        return "ChromeOS", m.group(1)
    if m := re.search(r"Mac OS X ([\d_.]+)", ua):
        return "macOS", m.group(1).replace("_", ".")
    if "Macintosh" in ua:
        return "macOS", ""
    if re.search(r"Ubuntu", ua):
        return "Linux (Ubuntu)", ""
    if re.search(r"X11|Linux", ua):
        return "Linux", ""
    if re.search(r"BlackBerry|BB10", ua):
        return "BlackBerry", ""
    return "未知", ""


def _browser_info(ua: str) -> tuple[str, str]:
    if m := re.search(r"Edg(?:e|A|iOS)?/([\d.]+)", ua):
        return "Edge", m.group(1)
    if m := re.search(r"(?:OPR|OPiOS)/([\d.]+)", ua):
        return "Opera", m.group(1)
    if m := re.search(r"\bOpera[ /]([\d.]+)", ua):
        return "Opera", m.group(1)
    if m := re.search(r"SamsungBrowser/([\d.]+)", ua):
        return "Samsung Internet", m.group(1)
    if m := re.search(r"YaBrowser/([\d.]+)", ua):
        return "Yandex", m.group(1)
    if m := re.search(r"UCBrowser/([\d.]+)", ua):
        return "UC Browser", m.group(1)
    if m := re.search(r"Vivaldi/([\d.]+)", ua):
        return "Vivaldi", m.group(1)
    if m := re.search(r"MicroMessenger/([\d.]+)", ua):
        return "微信", m.group(1)
    if m := re.search(r"\bMQQBrowser/([\d.]+)", ua):
        return "QQ 浏览器", m.group(1)
    if re.search(r"DingTalk", ua):
        return "钉钉", ""
    if re.search(r"whatsapp", ua, re.IGNORECASE):
        return "WhatsApp", ""
    # Chrome 与 Safari 的 UA 互含对方的标记，所以必须先判 Chrome/CriOS 再判 Safari。
    if m := re.search(r"(?:Chrome|CriOS)/([\d.]+)", ua):
        return "Chrome", m.group(1)
    if m := re.search(r"(?:Firefox|FxiOS)/([\d.]+)", ua):
        return "Firefox", m.group(1)
    if m := re.search(r"Version/([\d.]+).*Safari", ua):
        return "Safari", m.group(1)
    if "Safari" in ua:
        return "Safari", ""
    if m := re.search(r"^([A-Za-z][\w .-]*)/([\d.]+)", ua):
        return m.group(1).strip(), m.group(2)
    return "未知", ""


def _device_kind(ua: str, is_bot: bool) -> str:
    if is_bot:
        return "bot"
    if re.search(r"iPhone|iPad|iPod|Android|Mobile|BlackBerry|Windows Phone", ua, re.IGNORECASE):
        # 手机与平板的分界：`Mobile` 标记是手机；Android 无 Mobile 标记按平板；
        # iPad 一律平板。iOS 13+ 桌面模式伪装成 Macintosh，这里判不出来（见模块 docstring）。
        if re.search(r"iPad", ua):
            return "tablet"
        if re.search(r"\bMobile\b", ua):
            return "mobile"
        if re.search(r"Android", ua):
            return "tablet"
        return "mobile"
    return "desktop"


def parse_user_agent(ua: str | None) -> UserAgentInfo:
    """把一条 UA 字符串解析成后台展示用的标签。"""
    raw = (ua or "").strip()
    is_bot, bot_name = detect_bot(raw)
    os_name, os_version = _os_info(raw)
    browser, browser_version = _browser_info(raw)
    if not raw:
        return UserAgentInfo(
            os="未知",
            os_version="",
            browser="未知",
            browser_version="",
            device="unknown",
            is_bot=True,
            bot_name="空 UA",
        )
    return UserAgentInfo(
        os=os_name,
        os_version=os_version,
        browser=browser,
        browser_version=browser_version,
        device=_device_kind(raw, is_bot),
        is_bot=is_bot,
        bot_name=bot_name,
    )


def describe_user_agent(ua: str | None) -> dict[str, object]:
    """响应体用的扁平字典（浏览器侧直接铺表格里，不必再拼一次）。"""
    info = parse_user_agent(ua)
    return {
        "os": info.os,
        "os_version": info.os_version,
        "browser": info.browser,
        "browser_version": info.browser_version,
        "device": info.device,
        "is_bot": info.is_bot,
        "bot_name": info.bot_name,
    }
