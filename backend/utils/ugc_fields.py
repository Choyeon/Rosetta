"""UGC 写入口共用的字段清洗工具（评论 / 留言板）。

这两个 service 以前各存一份逐字节相同的 `mask_ip` / `gravatar_avatar` /
`truncate_ua`，改一处忘另一处的表现是"留言板的 IP 脱敏口径和评论不一样"。
真源在此，两个 service 只做 re-export。
"""

from __future__ import annotations

import hashlib
import re

from backend.core.config import settings

# 访客身份字段的**唯一**形态定义。写入口（`CommentCreate` / `GuestbookEntryCreate`）与头像
# 解析器必须吃同一份：解析器过去自带正则、写入侧不设限，于是 `github="<img src=x>"` 这种值
# 能进库——它不会 XSS（渲染侧是文本插值），但会被公开评论口当显示名原样发出去，而解析器只是
# 静默把它判成"没有头像"。口径见 AGENTS.md §12.8（会渲染到访客页面上的短字符串字段，写入侧
# 必须用 pattern 拒掉标记语言）。
GITHUB_USERNAME_PATTERN = r"^[a-zA-Z0-9](?:-?[a-zA-Z0-9]){0,38}$"
QQ_PATTERN = r"^\d{5,11}$"
GITHUB_USERNAME_RE = re.compile(GITHUB_USERNAME_PATTERN)
QQ_RE = re.compile(QQ_PATTERN)


def gravatar_base() -> str:
    raw = (settings.gravatar_cdn_base or "https://cravatar.cn/avatar").rstrip("/ ")
    return raw or "https://cravatar.cn/avatar"


# 头像 URL 在调用期取 gravatar_base()，改环境变量后无需重启；这个常量只是给
# 调用方/测试直接 import 的快照（改造前两个 service 各有一份同名常量）。
GRAVATAR_BASE: str = gravatar_base()

AUTO_REJECT_ON_SENSITIVE_DEFAULT = True


def mask_ip(ip: str | None) -> str | None:
    """对 IP 地址脱敏：IPv4 保留前两段；IPv6 保留前 4 段"""
    if not ip:
        return None
    ip = ip.strip()
    if not ip:
        return None
    if ":" in ip:
        parts = ip.split(":")
        head = parts[:4]
        while len(head) < 4:
            head.append("0")
        return ":".join(head) + "::"
    if "." in ip:
        parts = ip.split(".")
        if len(parts) == 4:
            return f"{parts[0]}.{parts[1]}.x.x"
        return ip
    return ip


def gravatar_avatar(email: str | None, author_name: str | None) -> str:
    """生成 Gravatar 头像 URL（默认国内镜像），绝不暴露 email 明文"""
    source = ""
    if email:
        source = email.strip().lower()
    if not source:
        source = (author_name or "guest").strip().lower()
    h = hashlib.md5(source.encode("utf-8")).hexdigest()
    # 每次调用重取镜像基址，与改造前一致
    return f"{gravatar_base()}/{h}?d=mp&s=64"


def truncate_ua(ua: str | None, max_len: int = 200) -> str | None:
    if not ua:
        return None
    return ua[:max_len] if len(ua) > max_len else ua
