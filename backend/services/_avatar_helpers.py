"""Avatar 工具：解析 + 包装代理 URL（给 comment/guestbook/user 三个 service 复用）。"""

from __future__ import annotations

import base64
import re

from sqlalchemy import inspect as _sa_inspect

from backend.services.avatar_resolver import AvatarInput
from backend.services.avatar_resolver import resolve as _resolve_avatar

_PROXY_PREFIX = "/api/media/avatar?src="

# 不应该走到代理流程的「明显无效/占位」上游域名：
# - IANA 保留域 (example.com)、RFC2606 测试域
# - 回环/私有保留 IP 段（避免 SSRF+兜底时把内网 IP 暴露给前端 URL）
_BAD_HOST_RE = re.compile(
    r"(^|\.)(example\.(com|org|net)|invalid|localhost|test|example\.edu)$",
    re.I,
)


def wrap_proxy(original_url: str | None) -> str | None:
    """把「上游原始头像 URL」包装为后端代理路径。

    None / 空串 / 无效占位 URL -> 返回 None，交给前端 fallback 到 DiceBear
    或本地兜底图，避免把无效 base64 串抛给前端再绕一圈代理触发 ORB。
    """
    if not original_url:
        return None
    url = original_url.strip()
    if not url or url.lower() in {"none", "null", "undefined", "n/a"}:
        return None

    # 本站自托管头像（/media/avatars/xxx.jpg）原样返回：它本来就是我们自己发的图，
    # 包进代理只会多一次解码转发，还把 immutable 缓存头换成代理的 7 天。
    # `//host/path` 是协议相对外链，不在这一支（由 avatar_resolver 的白名单正则挡掉）。
    if url.startswith("/") and not url.startswith("//"):
        return url

    # 仅当 http(s):// 时校验 host
    if url.lower().startswith(("http://", "https://")):
        from urllib.parse import urlparse

        try:
            parsed = urlparse(url)
            host = (parsed.hostname or "").lower()
            if not host or _BAD_HOST_RE.match(host) or _BAD_HOST_RE.search("." + host):
                return None
            # 私有 IP / 回环地址：不包装（避免代理把内网请求打到自己）
            ip_like = host
            if (
                ip_like in {"127.0.0.1", "0.0.0.0", "::1"}
                or ip_like.startswith("127.")
                or ip_like.startswith("10.")
                or ip_like.startswith("192.168.")
                or re.match(r"^172\.(1[6-9]|2\d|3[01])\.", ip_like)
            ):
                return None
            path = (parsed.path or "").lower()
            # 占位文件名：/avatar.png 裸路径 + 无效域
            if path in {"", "/"} or path.endswith("/avatar.png"):
                if _BAD_HOST_RE.match(host) or _BAD_HOST_RE.search("." + host):
                    return None
        except Exception:
            return None

    b64 = base64.urlsafe_b64encode(url.encode("utf-8")).rstrip(b"=").decode("ascii")
    return _PROXY_PREFIX + b64


def resolved_for_profile(
    *,
    avatar: str | None = None,
    github: str | None = None,
    qq: str | None = None,
    email: str | None = None,
    avatar_source: str | None = "auto",
) -> str | None:
    """头像字段（不必是 ORM 对象）→ resolved_avatar_url。

    列表类接口只投影了展示列（`select(User.avatar, ...)`）时没有 ORM 实例，
    就按这一支传字段；有完整 User 对象的一律走 resolved_for_user。
    """
    inp = AvatarInput(
        avatar_source=(avatar_source or "auto"),  # type: ignore[arg-type]
        avatar=avatar,
        github=github,
        qq=qq,
        email=email,
    )
    return wrap_proxy(_resolve_avatar(inp))


def resolved_for_user(user) -> str | None:
    """User ORM instance → 包装代理后的 resolved_avatar_url。user=None 也安全返回 None。"""
    if user is None:
        return None
    return resolved_for_profile(
        avatar=getattr(user, "avatar", None),
        github=getattr(user, "github", None),
        qq=getattr(user, "qq", None),
        email=getattr(user, "email", None),
        avatar_source=getattr(user, "avatar_source", "auto"),
    )


def _user_relationship_safe(orm_obj, rel_name: str = "user"):
    """安全读取 ORM 对象的关系属性，未 eager-load 时返回 None 避免触发 async greenlet IO。"""
    insp = getattr(_sa_inspect(orm_obj), "unloaded", set()) if orm_obj is not None else set()
    if rel_name in insp:
        return None
    return getattr(orm_obj, rel_name, None)


def resolved_for_comment(comment) -> str | None:
    """Comment ORM：优先 user 表解析；否则用游客列。"""
    user = _user_relationship_safe(comment)
    if user is not None:
        return resolved_for_user(user)
    inp = AvatarInput(
        avatar_source=getattr(comment, "avatar_source", "auto") or "auto",
        github=getattr(comment, "github", None),
        qq=getattr(comment, "qq", None),
        email=getattr(comment, "author_email", None),
    )
    return wrap_proxy(_resolve_avatar(inp))


def resolved_for_guestbook(entry) -> str | None:
    """GuestbookEntry ORM：优先 user；否则游客列。逻辑同 comment。"""
    user = _user_relationship_safe(entry)
    if user is not None:
        return resolved_for_user(user)
    inp = AvatarInput(
        avatar_source=getattr(entry, "avatar_source", "auto") or "auto",
        github=getattr(entry, "github", None),
        qq=getattr(entry, "qq", None),
        email=getattr(entry, "author_email", None),
    )
    return wrap_proxy(_resolve_avatar(inp))
