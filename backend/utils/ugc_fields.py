"""UGC 写入口共用的字段清洗工具（评论 / 留言板）。

这两个 service 以前各存一份逐字节相同的 `mask_ip` / `gravatar_avatar` /
`truncate_ua`，改一处忘另一处的表现是"留言板的 IP 脱敏口径和评论不一样"。
真源在此，两个 service 只做 re-export。
"""

from __future__ import annotations

import hashlib

from backend.core.config import settings


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
