"""
文章可读性判定的单一来源。

文章详情端点（`backend/api/blog.py::get_post`）历史上把这套规则**内联**在自己函数体里，
而派生资源（评论、回复、留言引用）各自另写一份或干脆不写——表现就是"正文已按状态/密码
收口，但同一篇文章的评论口匿名直读"。本模块把那两条判据抽出来，供派生资源复用：

1. ``post_is_publicly_visible``：非 published 与"定时发布未到"的文章只有作者本人与
   staff/超管可读；对其他人**按不存在处理**（404，不是 403——承认存在即可枚举草稿 id）。
2. ``post_content_unlocked``：设了密码的文章，未带正确密码时对任何人都不放行
   （作者/staff 短路）。

与文章详情端点的差异是刻意的：详情口对加密文章返回 200 并置
``is_password_protected=true``、正文留空，由客户端出解锁界面；派生资源没有"部分可见"
这种形态，只能整体给或不给。
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from backend.models.blog import Post
    from backend.models.user import User


def _ensure_aware(value: datetime | None) -> datetime | None:
    """无时区的时间一律按 UTC 解释（与 blog.py 同口径，避免 naive/aware 比较 TypeError）。"""
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value


def _is_privileged(post: Post, current_user: User | None) -> bool:
    if current_user is None:
        return False
    return bool(
        current_user.id == post.author_id
        or getattr(current_user, "is_staff", False)
        or getattr(current_user, "is_superuser", False)
    )


def post_is_publicly_visible(post: Post, current_user: User | None) -> bool:
    """这篇文章对当前观看者是否"存在"。草稿/待审/未来定时 → 仅作者与 staff。"""
    if _is_privileged(post, current_user):
        return True
    if post.status != "published":
        return False
    published_at = _ensure_aware(getattr(post, "published_at", None))
    if published_at and published_at > datetime.now(timezone.utc):
        return False
    return True


async def post_content_unlocked(
    post: Post,
    current_user: User | None,
    provided_password: str | None = None,
) -> bool:
    """加密文章的密码闸门；未设密码恒 True。"""
    password_hash: Any = getattr(post, "password", None)
    if not password_hash:
        return True
    if _is_privileged(post, current_user):
        return True
    if not provided_password:
        return False
    from backend.core.auth import averify_password

    return await averify_password(provided_password, password_hash)
