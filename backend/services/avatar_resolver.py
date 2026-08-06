"""
头像解析器（纯函数，无 DB/HTTP IO）。

Avatar 选择优先级（当 avatar_source == "auto" 时，从高到低）：
  1) custom 且 avatar URL 非空 → 直接用 avatar
  2) github 非空 → "https://github.com/{github}.png?size=160"
  3) qq 非空 → "https://q1.qlogo.cn/g?b=qq&nk={qq}&s=160"
  4) email 非空 → Gravatar MD5 + d=mp + s=160
  5) 否则 → None（由前端 fallback 到首字母色块 / rosetta-256.png）

当 avatar_source 强制指定（qq/github/gravatar/custom）时，直接走对应分支，若失败返回 None。
"""
from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from typing import Literal

AvatarSource = Literal["auto", "custom", "github", "qq", "gravatar"]

GITHUB_USERNAME_RE = re.compile(r"^[a-zA-Z0-9](?:-?[a-zA-Z0-9]){0,38}$")
QQ_RE = re.compile(r"^\d{5,11}$")
WEBSITE_URL_RE = re.compile(r"^https?://[^\s]+$", re.IGNORECASE)
EMAIL_RE = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")


@dataclass(frozen=True)
class AvatarInput:
    avatar_source: AvatarSource = "auto"
    avatar: str | None = None          # custom 模式下使用（User.avatar）
    github: str | None = None
    qq: str | None = None
    email: str | None = None


def _normalize_github(raw: str | None) -> str | None:
    if not raw:
        return None
    # 支持 "https://github.com/xxx" / "@xxx" / "xxx"
    s = raw.strip().rstrip("/")
    if s.startswith(("http://github.com/", "https://github.com/", "//github.com/")):
        s = s.split("github.com/", 1)[1]
    if s.startswith("@"):
        s = s[1:]
    s = s.strip("/")
    return s if GITHUB_USERNAME_RE.match(s) else None


def _normalize_qq(raw: str | None) -> str | None:
    if not raw:
        return None
    s = raw.strip()
    return s if QQ_RE.match(s) else None


def _gravatar_url(email: str | None, size: int = 160) -> str | None:
    if not email:
        return None
    m = EMAIL_RE.match(email.strip())
    if not m:
        return None
    digest = hashlib.md5(email.strip().lower().encode("utf-8")).hexdigest()
    # 直接返回 gravatar 原始 URL；是否加代理由外层 Response 包装器决定
    return f"https://www.gravatar.com/avatar/{digest}?s={size}&d=mp&r=g"


def validate_input(inp: AvatarInput) -> dict[str, str | None]:
    """返回标准化后的字段字典（不抛异常，非法自动变 None）"""
    return {
        "github": _normalize_github(inp.github),
        "qq": _normalize_qq(inp.qq),
        "email": inp.email if (inp.email and EMAIL_RE.match(inp.email.strip())) else None,
        "avatar": inp.avatar
        if (inp.avatar and WEBSITE_URL_RE.match(inp.avatar.strip()))
        else None,
    }


def resolve(inp: AvatarInput, size: int = 160) -> str | None:
    """返回解析后的「原始头像 URL」；代理包装在外层调用。"""
    std = validate_input(inp)
    src: AvatarSource = inp.avatar_source or "auto"

    # 1. 强制 custom
    if src == "custom":
        return std["avatar"]

    # 2. 强制 github
    if src == "github":
        gh = std["github"]
        return f"https://github.com/{gh}.png?size={size}" if gh else None

    # 3. 强制 qq
    if src == "qq":
        q = std["qq"]
        return f"https://q1.qlogo.cn/g?b=qq&nk={q}&s={size}" if q else None

    # 4. 强制 gravatar
    if src == "gravatar":
        return _gravatar_url(std["email"], size=size)

    # 5. auto：高→低优先级
    if std["avatar"]:
        return std["avatar"]
    gh = std["github"]
    if gh:
        return f"https://github.com/{gh}.png?size={size}"
    q = std["qq"]
    if q:
        return f"https://q1.qlogo.cn/g?b=qq&nk={q}&s={size}"
    g = _gravatar_url(std["email"], size=size)
    if g:
        return g
    return None
