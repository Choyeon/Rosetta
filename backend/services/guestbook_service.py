"""
Rosetta 留言板服务模块

封装留言板 CRUD、审核、置顶/精华切换、点赞、敏感词、频控校验、通知等业务逻辑。
与 comment_service.py 保持字段风格一致，避免耦合回归风险。
"""

from __future__ import annotations

import asyncio
import hashlib
import logging
import re
from datetime import datetime
from typing import Any

from sqlalchemy import and_, desc, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.config import settings
from backend.core.moderation import moderate_text
from backend.models.core import Notification
from backend.models.guestbook import GuestbookEntry
from backend.models.user import User
from backend.schemas import GuestbookEntryCreate, GuestbookEntryResponse
from backend.services._avatar_helpers import resolved_for_guestbook

logger = logging.getLogger(__name__)

HTTP_URL_RE = re.compile(r"^https?://", re.IGNORECASE)
GRAVATAR_BASE = "https://www.gravatar.com/avatar"
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
    """生成 Gravatar 头像 URL，绝不暴露 email 明文"""
    source = ""
    if email:
        source = email.strip().lower()
    if not source:
        source = (author_name or "guest").strip().lower()
    h = hashlib.md5(source.encode("utf-8")).hexdigest()
    return f"{GRAVATAR_BASE}/{h}?d=mp&s=64"


def truncate_ua(ua: str | None, max_len: int = 200) -> str | None:
    if not ua:
        return None
    return ua[:max_len] if len(ua) > max_len else ua


def _entry_to_response(e: GuestbookEntry) -> GuestbookEntryResponse:
    """把 ORM GuestbookEntry 转成对外响应（填充 author_avatar）"""
    email = e.author_email
    avatar = gravatar_avatar(email, e.author_name)
    return GuestbookEntryResponse(
        id=e.id,
        user_id=e.user_id,
        author_name=e.author_name,
        author_avatar=avatar,
        author_website=e.author_website if HTTP_URL_RE.match(e.author_website or "") else None,
        content=e.content,
        status=e.status,
        is_pinned=e.is_pinned,
        is_featured=e.is_featured,
        likes_count=e.likes_count,
        created_at=e.created_at,
        qq=getattr(e, "qq", None),
        github=getattr(e, "github", None),
        avatar_source=getattr(e, "avatar_source", None),
        resolved_avatar_url=resolved_for_guestbook(e),
    )


class GuestbookService:
    """留言板业务服务。所有方法为 AsyncSession 内操作，无状态。"""

    # ---------- 公开查询 ----------

    @staticmethod
    async def list_entries(
        db: AsyncSession,
        *,
        page: int = 1,
        page_size: int = 10,
        status: str | None = "approved",
        include_trashed: bool = False,
        current_user: User | None = None,
    ) -> tuple[list[GuestbookEntryResponse], int]:
        """
        分页取留言板列表（扁平结构，无嵌套）。

        排序：is_pinned DESC > is_featured DESC > created_at DESC
        可见性：
          - 普通用户：仅 approved（deleted_at IS NULL）
          - 作者本人：可见自己的 pending/rejected
          - 管理员：可见所有（可 include_trashed=True 看回收站）
        """
        is_staff = bool(
            current_user
            and (
                getattr(current_user, "is_staff", False)
                or getattr(current_user, "is_superuser", False)
            )
        )

        wh: list[Any] = []

        if include_trashed and is_staff:
            pass
        elif status == "trashed" and is_staff:
            wh.append(GuestbookEntry.deleted_at.is_not(None))
        else:
            wh.append(GuestbookEntry.deleted_at.is_(None))

            if is_staff:
                if status and status != "all":
                    wh.append(GuestbookEntry.status == status)
            else:
                allowed: list[Any] = [GuestbookEntry.status == "approved"]
                if current_user is not None:
                    allowed.append(
                        and_(
                            GuestbookEntry.user_id == current_user.id,
                            GuestbookEntry.status.in_(["pending", "rejected"]),
                        )
                    )
                wh.append(or_(*allowed))

        where_stmt = and_(*wh) if wh else True

        count_stmt = (
            select(func.count(GuestbookEntry.id)).select_from(GuestbookEntry).where(where_stmt)
        )
        total_res = await db.execute(count_stmt)
        total = int(total_res.scalar_one() or 0)

        offset = max(0, (page - 1) * page_size)
        list_stmt = (
            select(GuestbookEntry)
            .where(where_stmt)
            .order_by(
                desc(GuestbookEntry.is_pinned),
                desc(GuestbookEntry.is_featured),
                desc(GuestbookEntry.created_at),
            )
            .limit(page_size)
            .offset(offset)
        )
        list_res = await db.execute(list_stmt)
        items: list[GuestbookEntry] = list(list_res.scalars().all())

        return [_entry_to_response(e) for e in items], total

    # ---------- 创建留言 ----------

    @staticmethod
    async def check_same_ip_duplicate(
        db: AsyncSession, masked_ip: str | None, window_sec: int = 30
    ) -> bool:
        """同 IP 30s 内已存在留言 → 返回 True（命中重复频控）"""
        if not masked_ip:
            return False
        try:
            from datetime import timedelta

            since = datetime.utcnow() - timedelta(seconds=window_sec)
            stmt = select(func.count(GuestbookEntry.id)).where(
                and_(
                    GuestbookEntry.author_ip == masked_ip,
                    GuestbookEntry.created_at >= since,
                )
            )
            r = await db.execute(stmt)
            return int(r.scalar_one() or 0) > 0
        except Exception:
            return False

    @staticmethod
    async def create_entry(
        db: AsyncSession,
        data: GuestbookEntryCreate,
        client_ip: str | None,
        user_agent: str | None,
        current_user: User | None,
    ) -> GuestbookEntryResponse:
        """创建一条留言（游客或登录用户均可）。内部处理：敏感词、status 决策、频控。"""
        author_name = (data.author_name or "").strip()
        if not author_name:
            if current_user is None:
                raise ValueError("AUTHOR_NAME_REQUIRED")
            author_name = (
                getattr(current_user, "nickname", None)
                or getattr(current_user, "username", None)
                or "Member"
            )
        author_name = author_name[:30]
        if len(author_name) < 2:
            raise ValueError("AUTHOR_NAME_TOO_SHORT")

        if len(data.content) < 2:
            raise ValueError("CONTENT_TOO_SHORT")
        if len(data.content) > 3000:
            raise ValueError("CONTENT_TOO_LONG")

        if current_user is not None and data.author_email is None:
            author_email = getattr(current_user, "email", None)
        else:
            author_email = data.author_email

        author_website = data.author_website

        masked = mask_ip(client_ip)
        dup = await GuestbookService.check_same_ip_duplicate(db, masked, 30)
        if dup:
            raise ValueError("TOO_FREQUENT_GUESTBOOK")

        mod = moderate_text(data.content)
        require_approval = bool(getattr(settings, "comment_require_approval", True))
        auto_reject = AUTO_REJECT_ON_SENSITIVE_DEFAULT
        status: str
        if mod.level == "black" and auto_reject:
            status = "rejected"
        elif mod.level == "gray":
            status = "pending"
        elif require_approval:
            status = "pending"
        else:
            status = "approved"

        obj = GuestbookEntry(
            user_id=current_user.id if current_user is not None else None,
            author_name=author_name,
            author_email=author_email,
            author_website=author_website,
            author_ip=masked,
            author_user_agent=truncate_ua(user_agent, 200),
            qq=(data.qq.strip() if getattr(data, "qq", None) and data.qq.strip() else None),
            github=(data.github.strip() if getattr(data, "github", None) and data.github.strip() else None),
            avatar_source=(getattr(data, "author_avatar_source", "auto") or "auto"),
            content=data.content,
            status=status,
            is_pinned=False,
            is_featured=False,
            likes_count=0,
            deleted_at=None,
        )
        db.add(obj)
        await db.flush()
        await db.refresh(obj)

        try:
            asyncio.create_task(
                GuestbookService._fire_notifications(
                    entry_id=obj.id,
                    actor_user_id=current_user.id if current_user is not None else None,
                    actor_display_name=author_name,
                    content_preview=(data.content[:80] + ("…" if len(data.content) > 80 else "")),
                    entry_status=status,
                )
            )
        except Exception:
            logger.exception("schedule guestbook notification task failed")

        return _entry_to_response(obj)

    @staticmethod
    async def _fire_notifications(
        *,
        entry_id: int,
        actor_user_id: int | None,
        actor_display_name: str,
        content_preview: str,
        entry_status: str,
    ) -> None:
        """留言板收到新留言 → 通知所有管理员（role=admin/staff）。所有异常静默吞噬。"""
        try:
            from backend.core.database import async_session_maker

            async with async_session_maker() as adb:
                admin_q = await adb.execute(
                    select(User).where(or_(User.is_staff.is_(True), User.is_superuser.is_(True)))
                )
                admins = list(admin_q.scalars().all())
                if not admins:
                    return

                resolved_actor = actor_user_id or 1

                for admin in admins:
                    try:
                        notif = Notification(
                            recipient_id=admin.id,
                            actor_id=resolved_actor,
                            verb="guestbook_entry_received",
                            content_type="GuestbookEntry",
                            object_id=entry_id,
                            title={"zh": "留言板通知", "en": "Guestbook"},
                            message={
                                "zh": f"留言板收到 {actor_display_name} 的新留言：{content_preview}",
                                "en": f"Guestbook received new message from {actor_display_name}: {content_preview}",
                            },
                            level="info",
                        )
                        adb.add(notif)
                    except Exception:
                        logger.exception("write guestbook notification failed, rid=%s", admin.id)

                try:
                    await adb.commit()
                except Exception:
                    logger.exception("commit guestbook notifications failed")
                    await adb.rollback()
        except Exception:
            logger.exception("_fire_notifications failed (non-fatal)")

    # ---------- 点赞 ----------

    @staticmethod
    async def like(db: AsyncSession, entry_id: int) -> int:
        stmt = (
            select(GuestbookEntry)
            .where(GuestbookEntry.id == int(entry_id), GuestbookEntry.deleted_at.is_(None))
            .with_for_update()
        )
        r = await db.execute(stmt)
        e: GuestbookEntry | None = r.scalars().first()
        if e is None:
            raise ValueError("GUESTBOOK_ENTRY_NOT_FOUND")
        e.likes_count = int(e.likes_count or 0) + 1
        await db.flush()
        return e.likes_count

    # ---------- 管理员 ----------

    @staticmethod
    async def admin_list(
        db: AsyncSession,
        *,
        status: str | None = None,
        keyword: str | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[GuestbookEntryResponse], int]:
        wh: list[Any] = []

        if status == "trashed":
            wh.append(GuestbookEntry.deleted_at.is_not(None))
        elif status and status != "all":
            wh.append(GuestbookEntry.status == status)
            wh.append(GuestbookEntry.deleted_at.is_(None))
        else:
            wh.append(GuestbookEntry.deleted_at.is_(None))

        if keyword:
            like = f"%{keyword}%"
            wh.append(
                or_(
                    GuestbookEntry.content.like(like),
                    GuestbookEntry.author_name.like(like),
                    GuestbookEntry.author_email.like(like),
                )
            )

        where_and = and_(*wh) if wh else True

        cnt_stmt = (
            select(func.count(GuestbookEntry.id)).select_from(GuestbookEntry).where(where_and)
        )
        cnt = await db.execute(cnt_stmt)
        total = int(cnt.scalar_one() or 0)

        offset = max(0, (page - 1) * page_size)
        stmt = (
            select(GuestbookEntry)
            .where(where_and)
            .order_by(
                desc(GuestbookEntry.is_pinned),
                desc(GuestbookEntry.is_featured),
                desc(GuestbookEntry.created_at),
            )
            .limit(page_size)
            .offset(offset)
        )
        res = await db.execute(stmt)
        items = [_entry_to_response(c) for c in res.scalars().all()]
        return items, total

    @staticmethod
    async def _set_status(
        db: AsyncSession, entry_id: int, new_status: str
    ) -> GuestbookEntryResponse:
        stmt = select(GuestbookEntry).where(GuestbookEntry.id == int(entry_id))
        r = await db.execute(stmt)
        e: GuestbookEntry | None = r.scalars().first()
        if e is None:
            raise ValueError("GUESTBOOK_ENTRY_NOT_FOUND")
        e.status = new_status
        await db.flush()
        await db.refresh(e)
        return _entry_to_response(e)

    @staticmethod
    async def admin_toggle_pin(db: AsyncSession, entry_id: int) -> GuestbookEntryResponse:
        stmt = select(GuestbookEntry).where(GuestbookEntry.id == int(entry_id))
        r = await db.execute(stmt)
        e: GuestbookEntry | None = r.scalars().first()
        if e is None:
            raise ValueError("GUESTBOOK_ENTRY_NOT_FOUND")
        e.is_pinned = not e.is_pinned
        await db.flush()
        await db.refresh(e)
        return _entry_to_response(e)

    @staticmethod
    async def admin_toggle_feature(db: AsyncSession, entry_id: int) -> GuestbookEntryResponse:
        stmt = select(GuestbookEntry).where(GuestbookEntry.id == int(entry_id))
        r = await db.execute(stmt)
        e: GuestbookEntry | None = r.scalars().first()
        if e is None:
            raise ValueError("GUESTBOOK_ENTRY_NOT_FOUND")
        e.is_featured = not e.is_featured
        await db.flush()
        await db.refresh(e)
        return _entry_to_response(e)

    @staticmethod
    async def admin_approve(db: AsyncSession, entry_id: int) -> GuestbookEntryResponse:
        return await GuestbookService._set_status(db, entry_id, "approved")

    @staticmethod
    async def admin_reject(db: AsyncSession, entry_id: int) -> GuestbookEntryResponse:
        return await GuestbookService._set_status(db, entry_id, "rejected")

    @staticmethod
    async def admin_spam(db: AsyncSession, entry_id: int) -> GuestbookEntryResponse:
        return await GuestbookService._set_status(db, entry_id, "spam")

    @staticmethod
    async def admin_batch(db: AsyncSession, ids: list[int], action: str) -> dict[str, int]:
        if not ids:
            return {"processed": 0}
        stmt = select(GuestbookEntry).where(GuestbookEntry.id.in_([int(i) for i in ids]))
        r = await db.execute(stmt)
        entries = list(r.scalars().all())
        n = 0
        for e in entries:
            if action == "approve":
                e.status = "approved"
            elif action == "reject":
                e.status = "rejected"
            elif action == "spam":
                e.status = "spam"
            elif action == "pin":
                e.is_pinned = True
            elif action == "feature":
                e.is_featured = True
            elif action == "trash":
                e.deleted_at = datetime.utcnow()
            elif action == "restore":
                e.deleted_at = None
            elif action == "delete":
                await db.delete(e)
            else:
                raise ValueError("INVALID_ACTION")
            n += 1
        await db.flush()
        return {"processed": n}
