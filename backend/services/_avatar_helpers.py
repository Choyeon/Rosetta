"""Avatar 工具：解析 + 包装代理 URL（给 comment/guestbook/user 三个 service 复用）。"""
from __future__ import annotations

import base64

from backend.services.avatar_resolver import AvatarInput
from backend.services.avatar_resolver import resolve as _resolve_avatar

_PROXY_PREFIX = "/api/media/avatar?src="

def wrap_proxy(original_url: str | None) -> str | None:
    if not original_url:
        return None
    b64 = base64.urlsafe_b64encode(original_url.encode("utf-8")).rstrip(b"=").decode("ascii")
    return _PROXY_PREFIX + b64

def resolved_for_user(user) -> str | None:
    """User ORM instance → 包装代理后的 resolved_avatar_url。user=None 也安全返回 None。"""
    if user is None:
        return None
    inp = AvatarInput(
        avatar_source=getattr(user, "avatar_source", "auto") or "auto",
        avatar=getattr(user, "avatar", None),
        github=getattr(user, "github", None),
        qq=getattr(user, "qq", None),
        email=getattr(user, "email", None),
    )
    return wrap_proxy(_resolve_avatar(inp))

def resolved_for_comment(comment) -> str | None:
    """Comment ORM：优先 user 表解析；否则用游客列。"""
    if getattr(comment, "user", None) is not None:
        return resolved_for_user(comment.user)
    inp = AvatarInput(
        avatar_source=getattr(comment, "avatar_source", "auto") or "auto",
        github=getattr(comment, "github", None),
        qq=getattr(comment, "qq", None),
        email=getattr(comment, "author_email", None),
    )
    return wrap_proxy(_resolve_avatar(inp))

def resolved_for_guestbook(entry) -> str | None:
    """GuestbookEntry ORM：优先 user；否则游客列。逻辑同 comment。"""
    if getattr(entry, "user", None) is not None:
        return resolved_for_user(entry.user)
    inp = AvatarInput(
        avatar_source=getattr(entry, "avatar_source", "auto") or "auto",
        github=getattr(entry, "github", None),
        qq=getattr(entry, "qq", None),
        email=getattr(entry, "author_email", None),
    )
    return wrap_proxy(_resolve_avatar(inp))
