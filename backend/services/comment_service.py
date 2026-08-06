"""
Rosetta 评论服务模块

封装评论 CRUD、审核、点赞、敏感词、频控校验、通知与邮件异步发送等业务逻辑。
"""

from __future__ import annotations

import asyncio
import hashlib
import logging
import re
from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import and_, desc, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from backend.core.config import settings
from backend.core.moderation import moderate_text
from backend.core.xss_filter import sanitize_html
from backend.models.blog import Comment, Post
from backend.models.core import Notification
from backend.models.user import User
from backend.schemas import CommentCreate, CommentResponse
from backend.services._avatar_helpers import resolved_for_comment

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)

HTTP_URL_RE = re.compile(r"^https?://", re.IGNORECASE)
GRAVATAR_BASE = "https://www.gravatar.com/avatar"
AUTO_REJECT_ON_SENSITIVE_DEFAULT = True


# ================= 静态辅助工具 =================


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


def _status_to_active(status: str) -> bool:
    return status == "approved"


def _comment_to_response(
    c: Comment, replies: list[Comment] | None = None, reply_total: int | None = None
) -> CommentResponse:
    """把 ORM Comment 转成对外响应（填充 author_avatar、replies、reply_total）"""
    email = c.author_email
    avatar = gravatar_avatar(email, c.author_name)
    return CommentResponse(
        id=c.id,
        post_id=c.post_id,
        user_id=c.user_id,
        parent_id=c.parent_id,
        author_name=c.author_name,
        author_avatar=avatar,
        author_website=c.author_website if HTTP_URL_RE.match(c.author_website or "") else None,
        content=c.content,
        status=c.status,
        is_pinned=c.is_pinned,
        likes_count=c.likes_count,
        reply_total=reply_total if reply_total is not None else 0,
        created_at=c.created_at,
        replies=[_comment_to_response(r) for r in (replies or [])],
        qq=getattr(c, "qq", None),
        github=getattr(c, "github", None),
        avatar_source=getattr(c, "avatar_source", None),
        resolved_avatar_url=resolved_for_comment(c),
    )


# ================= 业务服务类 =================


class CommentService:
    """评论业务服务。所有方法为 AsyncSession 内操作，无状态。"""

    # ---------- 公开查询 ----------

    @staticmethod
    async def get_post_by_any(db: AsyncSession, post_id_or_slug: str | int) -> Post | None:
        """接受 id（str纯数字）或 slug 两种形式查询 Post"""
        sid = str(post_id_or_slug)
        if sid.isdigit():
            stmt = select(Post).where(Post.id == int(sid))
        else:
            stmt = select(Post).where(Post.slug == sid)
        r = await db.execute(stmt)
        return r.scalars().first()

    @staticmethod
    async def list_root_comments(
        db: AsyncSession,
        post: Post,
        page: int = 1,
        page_size: int = 10,
        include_unapproved: bool = False,
        current_user: User | None = None,
    ) -> tuple[list[CommentResponse], int]:
        """
        分页取某文章的根评论（parent_id is null）。
        - 每条根评论预取前 3 条最新回复并计算 reply_total。
        - include_unapproved=True：仅作者/管理员可见"自己提交"的 pending/rejected，其他用户不可见他人的非 approved。
        """
        post_id = post.id
        post_author_id = post.author_id

        base_where = [Comment.post_id == post_id, Comment.parent_id.is_(None)]

        if not include_unapproved:
            base_where.append(Comment.status == "approved")
        else:
            allowed_extra: list[Any] = [Comment.status == "approved"]
            if current_user is not None:
                is_staff = bool(
                    getattr(current_user, "is_staff", False)
                    or getattr(current_user, "is_superuser", False)
                )
                if is_staff or (post_author_id is not None and current_user.id == post_author_id):
                    pass
                else:
                    allowed_extra.append(
                        and_(
                            Comment.user_id == current_user.id,
                            Comment.status.in_(["pending", "rejected"]),
                        )
                    )
            # 非 staff/作者 的 include_unapproved=true：其实仅能看到 approved 或本人 pending
            if not (
                current_user
                and (
                    bool(
                        getattr(current_user, "is_staff", False)
                        or getattr(current_user, "is_superuser", False)
                    )
                    or (post_author_id is not None and current_user.id == post_author_id)
                )
            ):
                base_where.append(or_(*allowed_extra))

        where_stmt = and_(*base_where)

        count_stmt = select(func.count(Comment.id)).select_from(Comment).where(where_stmt)
        total_res = await db.execute(count_stmt)
        total = int(total_res.scalar_one() or 0)

        offset = max(0, (page - 1) * page_size)
        list_stmt = (
            select(Comment)
            .options(
                joinedload(Comment.user),
                joinedload(Comment.post),
                joinedload(Comment.parent),
            )
            .where(where_stmt)
            .order_by(desc(Comment.is_pinned), desc(Comment.created_at))
            .limit(page_size)
            .offset(offset)
        )
        list_res = await db.execute(list_stmt)
        roots: list[Comment] = list(list_res.scalars().all())

        # 批量求 reply_total + 取前 3 条最新回复（一次性批查询以减少 round-trip）
        response_items: list[CommentResponse] = []
        if roots:
            root_ids = [r.id for r in roots]

            total_subq = (
                select(Comment.parent_id, func.count(Comment.id).label("c"))
                .where(Comment.parent_id.in_(root_ids))
                .group_by(Comment.parent_id)
            )
            total_res2 = await db.execute(total_subq)
            totals_map: dict[int, int] = {pid: int(c) for pid, c in total_res2.all()}

            # 取每个根评论前 3 条最新回复：用窗口函数 row_number 因 SQLite/PG 都支持
            from sqlalchemy import func as sa_func

            rn = (
                sa_func.row_number()
                .over(partition_by=Comment.parent_id, order_by=Comment.created_at.asc())
                .label("rn")
            )
            replies_stmt = (
                select(Comment, rn)
                .options(
                    joinedload(Comment.user),
                    joinedload(Comment.post),
                    joinedload(Comment.parent),
                )
                .where(Comment.parent_id.in_(root_ids))
            )
            # 兼容：无窗口函数时退化为每个根查 3 条
            try:
                rr = await db.execute(replies_stmt)
                flat: list[tuple[Comment, int]] = list(rr.all())
                replies_by_root: dict[int, list[Comment]] = {rid: [] for rid in root_ids}
                for c, rnum in flat:
                    if rnum <= 3:
                        replies_by_root.setdefault(c.parent_id, []).append(c)
            except Exception:
                replies_by_root = {rid: [] for rid in root_ids}
                for rid in root_ids:
                    per = await db.execute(
                        select(Comment)
                        .options(
                            joinedload(Comment.user),
                            joinedload(Comment.post),
                            joinedload(Comment.parent),
                        )
                        .where(Comment.parent_id == rid)
                        .order_by(Comment.created_at.asc())
                        .limit(3)
                    )
                    replies_by_root[rid] = list(per.scalars().all())

            # 非 approved 回复的可见性过滤（和根一样规则）
            def reply_visible(reply: Comment) -> bool:
                if reply.status == "approved":
                    return True
                if not include_unapproved:
                    return False
                if current_user is None:
                    return False
                staff = bool(
                    getattr(current_user, "is_staff", False)
                    or getattr(current_user, "is_superuser", False)
                )
                if staff or (post_author_id is not None and current_user.id == post_author_id):
                    return True
                return bool(reply.user_id == current_user.id)

            for r in roots:
                reply_total = totals_map.get(r.id, 0)
                raw_replies = [rep for rep in replies_by_root.get(r.id, []) if reply_visible(rep)]
                response_items.append(_comment_to_response(r, raw_replies, reply_total))

        return response_items, total

    @staticmethod
    async def get_replies(
        db: AsyncSession,
        comment_id: int,
        page: int = 1,
        page_size: int = 10,
        current_user: User | None = None,
    ) -> tuple[list[CommentResponse], int, Post | None]:
        """分页取某根评论的全部回复（按 created_at asc）。返回 (items, total, post_ref)"""
        root_stmt = (
            select(Comment)
            .options(
                joinedload(Comment.user),
                joinedload(Comment.post),
                joinedload(Comment.parent),
            )
            .where(Comment.id == int(comment_id))
        )
        r = await db.execute(root_stmt)
        root: Comment | None = r.scalars().first()
        if root is None:
            return [], 0, None
        # 必须是根：根 parent_id 为 null
        if root.parent_id is not None:
            # 查询的不是根评论，也仍按其 parent_id 查回复
            pass

        post_stmt = select(Post).where(Post.id == root.post_id)
        pres = await db.execute(post_stmt)
        post: Post | None = pres.scalars().first()
        post_author_id = post.author_id if post else None

        base_where = [Comment.parent_id == root.id]
        # 可见性（同根的回复可见性）
        is_staff = bool(
            current_user
            and (
                getattr(current_user, "is_staff", False)
                or getattr(current_user, "is_superuser", False)
            )
        )
        is_post_author = bool(
            current_user and post_author_id is not None and current_user.id == post_author_id
        )
        if not (is_staff or is_post_author):
            if current_user is None:
                base_where.append(Comment.status == "approved")
            else:
                base_where.append(
                    or_(
                        Comment.status == "approved",
                        and_(
                            Comment.user_id == current_user.id,
                            Comment.status.in_(["pending", "rejected"]),
                        ),
                    )
                )

        where_and = and_(*base_where)
        cnt_stmt = select(func.count(Comment.id)).select_from(Comment).where(where_and)
        cnt = await db.execute(cnt_stmt)
        total = int(cnt.scalar_one() or 0)

        offset = max(0, (page - 1) * page_size)
        q = (
            select(Comment)
            .options(
                joinedload(Comment.user),
                joinedload(Comment.post),
                joinedload(Comment.parent),
            )
            .where(where_and)
            .order_by(Comment.created_at.asc())
            .limit(page_size)
            .offset(offset)
        )
        res = await db.execute(q)
        items = [_comment_to_response(c) for c in res.scalars().all()]
        return items, total, post

    # ---------- 创建评论 ----------

    @staticmethod
    async def validate_parent_depth(db: AsyncSession, parent_id: int | None, post_id: int) -> None:
        """若 parent_id 非空：确保 parent 是同 post 下的根评论，否则抛 ValueError(code)"""
        if parent_id is None:
            return
        stmt = select(Comment).where(Comment.id == int(parent_id))
        r = await db.execute(stmt)
        parent: Comment | None = r.scalars().first()
        if parent is None:
            raise ValueError("COMMENT_PARENT_NOT_FOUND")
        if parent.post_id != post_id:
            raise ValueError("COMMENT_PARENT_WRONG_POST")
        if parent.parent_id is not None:
            raise ValueError("NESTED_REPLY_TOO_DEEP")

    @staticmethod
    async def check_same_post_ip_duplicate(
        db: AsyncSession, post_id: int, masked_ip: str | None, window_sec: int = 30
    ) -> bool:
        """同 post + 同 IP 30s 内已存在评论 → 返回 True（表示命中重复频控）

        注意：SQLite / PG 的 created_at 使用 SQL 的 CURRENT_TIMESTAMP/func.now() 存储的是 UTC；
        因此这里必须使用 datetime.utcnow() 进行窗口比对，否则 Python 默认的本地时区（如 UTC+8）
        会造成 8 小时的偏差，导致时间窗口判断永远 false。
        """
        if not masked_ip:
            return False
        try:
            from datetime import timedelta

            since = datetime.utcnow() - timedelta(seconds=window_sec)
            alt_stmt = select(func.count(Comment.id)).where(
                and_(
                    Comment.post_id == int(post_id),
                    Comment.author_ip == masked_ip,
                    Comment.created_at >= since,
                )
            )
            r = await db.execute(alt_stmt)
            return int(r.scalar_one() or 0) > 0
        except Exception:
            return False

    @staticmethod
    async def create_comment(
        db: AsyncSession,
        post: Post,
        data: CommentCreate,
        client_ip: str | None,
        user_agent: str | None,
        current_user: User | None,
    ) -> CommentResponse:
        """创建一条评论（游客或登录用户均可）。内部处理：敏感词、status 决策、嵌套深度校验。"""
        # 1. 基本字段校验：游客必填 author_name；登录用户可从 user 派生但冗余存 author_name
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

        if current_user is not None and data.author_email is None:
            author_email = getattr(current_user, "email", None)
        else:
            author_email = data.author_email

        author_website = data.author_website

        # 2. 嵌套深度
        await CommentService.validate_parent_depth(db, data.parent_id, post.id)

        # 3. 同 post 同 IP 30s 防重（在事务里做近似判断即可，误判率极低）
        masked = mask_ip(client_ip)
        dup = await CommentService.check_same_post_ip_duplicate(db, post.id, masked, 30)
        if dup:
            raise ValueError("TOO_FREQUENT_COMMENT")

        # 4. 敏感词 + XSS 策略（CMS 标准模式）：
        #    - 原文 `data.content` 直接入库（保留完整审计与回显依据）
        #    - 敏感词分析在 sanitize_html 清洗后的副本上进行（避免 script 标签干扰关键词）
        #    - XSS 防御由前端模板 escape + 详情页 HTML 渲染器 allowlist 共同承担
        safe_content_for_analysis = sanitize_html(data.content)
        mod = moderate_text(safe_content_for_analysis)
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

        # 5. 构建 ORM 对象 — 注意 content 存储原始输入，不做改写
        obj = Comment(
            post_id=post.id,
            user_id=current_user.id if current_user is not None else None,
            parent_id=data.parent_id,
            author_name=author_name,
            author_email=author_email,
            author_website=author_website,
            author_ip=masked,
            author_user_agent=truncate_ua(user_agent, 200),
            qq=(data.qq.strip() if getattr(data, "qq", None) and data.qq.strip() else None),
            github=(data.github.strip() if getattr(data, "github", None) and data.github.strip() else None),
            avatar_source=(getattr(data, "avatar_source", "auto") or "auto"),
            content=data.content,  # 存原文，不在 storage 层做 destructive 清洗
            status=status,
            active=_status_to_active(status),
            likes_count=0,
            is_pinned=False,
        )
        db.add(obj)
        await db.flush()
        await db.refresh(obj)

        # 6. 异步触发通知（不等待，不抛出异常）
        try:
            asyncio.create_task(
                CommentService._fire_notifications_and_email(
                    CommentService._db_session_get_bind_key(db),
                    comment_id=obj.id,
                    post_id=post.id,
                    parent_id=obj.parent_id,
                    actor_user_id=current_user.id if current_user is not None else None,
                    actor_display_name=author_name,
                    post_author_id=post.author_id,
                    content_preview=(data.content[:80] + ("…" if len(data.content) > 80 else "")),
                    post_title_preview=(
                        post.title.get("zh")
                        if isinstance(post.title, dict)
                        else str(post.title or "")
                    )[:80],
                    comment_status=status,
                )
            )
        except Exception:
            logger.exception("schedule comment notification task failed")

        return _comment_to_response(obj)

    @staticmethod
    def _db_session_get_bind_key(_db: AsyncSession) -> str:
        return "default"

    # ---------- 通知 & 邮件（异步 fire-and-forget）----------

    @staticmethod
    async def _fire_notifications_and_email(
        _bind_key: str,
        *,
        comment_id: int,
        post_id: int,
        parent_id: int | None,
        actor_user_id: int | None,
        actor_display_name: str,
        post_author_id: int | None,
        content_preview: str,
        post_title_preview: str,
        comment_status: str,
    ) -> None:
        """
        - 新根评论 → 通知帖子作者（若有 user）
        - 新回复 → 通知 parent 作者（若有 user）
        - 若目标用户 notify_by_email=True 且 SMTP 配置有效，异步发送邮件
        所有异常静默吞噬。
        """
        try:
            from backend.core.database import async_session_maker  # 延迟 import 避免循环
            from backend.services.email_service import get_email_service  # type: ignore

            async with async_session_maker() as adb:
                recipients: list[tuple[int, str, str]] = []  # (recipient_id, verb, message_zh)
                parent_author_user_id: int | None = None
                if parent_id is not None:
                    pres = await adb.execute(select(Comment).where(Comment.id == int(parent_id)))
                    pcom = pres.scalars().first()
                    if pcom is not None and pcom.user_id is not None:
                        parent_author_user_id = pcom.user_id
                        verb = "comment_reply_received"
                        msg_zh = f"{actor_display_name} 回复了你的评论：{content_preview}"
                        if not (actor_user_id is not None and actor_user_id == pcom.user_id):
                            recipients.append((pcom.user_id, verb, msg_zh))

                if post_author_id is not None and (
                    actor_user_id is None or actor_user_id != post_author_id
                ):
                    if post_author_id != parent_author_user_id:  # 避免重复通知
                        verb = "post_comment_received"
                        msg_zh = f"你的文章《{post_title_preview}》收到 {actor_display_name} 的新评论：{content_preview}"
                        recipients.append((post_author_id, verb, msg_zh))

                # actor_id fallback：游客评论没有 actor_user_id 时，用站点管理员 ID=1 兜底
                resolved_actor = actor_user_id or 1
                written_notif_ids: list[int] = []
                for rid, verb, msg_zh in recipients:
                    try:
                        notif = Notification(
                            recipient_id=rid,
                            actor_id=resolved_actor,
                            verb=verb,
                            content_type="Comment",
                            object_id=comment_id,
                            title={"zh": "评论通知", "en": "Comment"},
                            message={"zh": msg_zh, "en": msg_zh},
                            level="info",
                        )
                        adb.add(notif)
                        await adb.flush()
                        written_notif_ids.append(notif.id)
                    except Exception:
                        logger.exception("write notification failed, rid=%s", rid)

                if written_notif_ids:
                    try:
                        await adb.commit()
                    except Exception:
                        logger.exception("commit notifications failed")
                        await adb.rollback()

                # 邮件发送
                try:
                    smtp_ready = bool(
                        getattr(settings, "smtp_host", "")
                        and getattr(settings, "smtp_user", "")
                        and getattr(settings, "smtp_password", "")
                        and getattr(settings, "smtp_from_email", "")
                    )
                    if smtp_ready and recipients:
                        es = get_email_service()
                        email_recips: set[str] = set()
                        for rid, _verb, _msg in recipients:
                            user_q = await adb.execute(select(User).where(User.id == rid))
                            u = user_q.scalars().first()
                            if u is None:
                                continue
                            if not getattr(u, "notify_by_email", True):
                                continue
                            em = getattr(u, "email", None)
                            if em and "@" in em:
                                email_recips.add(em)
                        for em in email_recips:
                            try:
                                await es.send_email(
                                    to=em,
                                    subject=f"[Rosetta] 评论通知 - {post_title_preview}",
                                    body=f"你在 Rosetta 站点收到新的评论交互：\n{content_preview}\n\n状态：{comment_status}",
                                )
                            except Exception:
                                logger.exception("send notification email failed to=%s", em)
                except Exception:
                    logger.exception("email stage failed (non-fatal)")
        except Exception:
            logger.exception("comment _fire_notifications_and_email failed (non-fatal)")

    # ---------- 点赞 ----------

    @staticmethod
    async def like(db: AsyncSession, comment_id: int) -> int:
        stmt = select(Comment).where(Comment.id == int(comment_id)).with_for_update()
        r = await db.execute(stmt)
        c: Comment | None = r.scalars().first()
        if c is None:
            raise ValueError("COMMENT_NOT_FOUND")
        c.likes_count = int(c.likes_count or 0) + 1
        await db.flush()
        return c.likes_count

    # ---------- 管理员 ----------

    @staticmethod
    async def admin_list(
        db: AsyncSession,
        *,
        status: str | None = None,
        keyword: str | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[CommentResponse], int]:
        wh: list[Any] = []
        if status:
            wh.append(Comment.status == status)
        if keyword:
            like = f"%{keyword}%"
            wh.append(
                or_(
                    Comment.content.like(like),
                    Comment.author_name.like(like),
                    Comment.author_email.like(like),
                )
            )
        where_and = and_(*wh) if wh else True

        cnt_stmt = select(func.count(Comment.id)).select_from(Comment).where(where_and)
        cnt = await db.execute(cnt_stmt)
        total = int(cnt.scalar_one() or 0)

        offset = max(0, (page - 1) * page_size)
        stmt = (
            select(Comment)
            .options(
                joinedload(Comment.user),
                joinedload(Comment.post),
                joinedload(Comment.parent),
            )
            .where(where_and)
            .order_by(desc(Comment.created_at))
            .limit(page_size)
            .offset(offset)
        )
        res = await db.execute(stmt)
        items = [_comment_to_response(c) for c in res.scalars().all()]
        return items, total

    @staticmethod
    async def _set_status(db: AsyncSession, comment_id: int, new_status: str) -> CommentResponse:
        stmt = (
            select(Comment)
            .options(
                joinedload(Comment.user),
                joinedload(Comment.post),
                joinedload(Comment.parent),
            )
            .where(Comment.id == int(comment_id))
        )
        r = await db.execute(stmt)
        c: Comment | None = r.scalars().first()
        if c is None:
            raise ValueError("COMMENT_NOT_FOUND")
        c.status = new_status
        c.active = _status_to_active(new_status)
        await db.flush()
        await db.refresh(c)
        return _comment_to_response(c)

    @staticmethod
    async def admin_approve(db: AsyncSession, comment_id: int) -> CommentResponse:
        return await CommentService._set_status(db, comment_id, "approved")

    @staticmethod
    async def admin_reject(db: AsyncSession, comment_id: int) -> CommentResponse:
        return await CommentService._set_status(db, comment_id, "rejected")

    @staticmethod
    async def admin_spam(db: AsyncSession, comment_id: int) -> CommentResponse:
        return await CommentService._set_status(db, comment_id, "spam")

    @staticmethod
    async def admin_delete(db: AsyncSession, comment_id: int) -> None:
        stmt = select(Comment).where(Comment.id == int(comment_id))
        r = await db.execute(stmt)
        c: Comment | None = r.scalars().first()
        if c is None:
            return
        await db.delete(c)
        await db.flush()

    @staticmethod
    async def admin_batch(db: AsyncSession, ids: list[int], action: str) -> dict[str, int]:
        if not ids:
            return {"processed": 0}
        stmt = select(Comment).where(Comment.id.in_([int(i) for i in ids]))
        r = await db.execute(stmt)
        cs = list(r.scalars().all())
        n = 0
        for c in cs:
            if action == "approve":
                c.status = "approved"
                c.active = True
            elif action == "reject":
                c.status = "rejected"
                c.active = False
            elif action == "spam":
                c.status = "spam"
                c.active = False
            elif action == "delete":
                await db.delete(c)
            else:
                raise ValueError("INVALID_ACTION")
            n += 1
        await db.flush()
        return {"processed": n}
