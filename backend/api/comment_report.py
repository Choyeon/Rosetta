"""
评论举报 API

两段式：访客/登录用户标记 → 管理员裁决。

- POST /api/comments/{comment_id}/report   公开写口（匿名可用，按 IP 限流）
- GET  /api/admin/comments/reports         【staff】举报列表 + 各状态计数
- PATCH /api/admin/comments/reports/{id}   【staff】裁决（handled / dismissed）

四条口径（都是"错了看不出来"的那一类，写在这里以免下一个人重新发明）：

1. **可读性闸门**：与表情反应同源（``services.comment_access.readable_comment_or_404``）。
   没有它，草稿 / 定时未到 / 加密未解锁的文章的评论仍能被匿名按 comment_id 举报——
   写口本身就是一次「这条评论存在」的确认，比读口更值得守。
2. **``Comment.reported_at`` 是"还有未处理举报"的标记，不是历史**：新建举报时若为空则立起，
   裁决后若该评论已无 open 举报则清回 NULL。后台评论列表的「待处理」筛选读的就是它
   （``GET /api/admin/comments?reported_only=true``），所以清标记必须与裁决同事务完成，
   否则会出现"举报都处理完了，评论列表里还挂着红点"。
3. **重复举报回成功而不是报错**：同一登录用户对同一条评论只保留一条 open 举报；
   匿名按 IP + 24 小时去重。``duplicate=true`` 让前端能说"你已经举报过了"，
   而不用为 409 单独写一套分支。
4. **举报不改公开面**：它不改变评论的可见性、不进公开展示、不动任何缓存
   （reported_at 只服务后台）。真正的下架仍走管理员对评论本身的 approve/reject/删除。
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, status
from sqlalchemy import func, select
from sqlalchemy.orm import aliased

from backend.core.auth import DB, CurrentStaff, CurrentUserOptional
from backend.core.csrf import require_csrf
from backend.core.i18n import get_i18n_value
from backend.core.rate_limit import (
    RateLimitRule,
    RateLimitStrategy,
    build_depends_rate_limit,
    get_client_ip,
)
from backend.models.blog import Comment, Post
from backend.models.comment_report import CommentReport
from backend.models.user import User
from backend.schemas.comment_report import (
    AdminCommentReportItem,
    AdminCommentReportListResponse,
    AdminCommentReportUpdate,
    AdminCommentReportUpdated,
    CommentReportCreate,
    CommentReportReceipt,
)
from backend.services.comment_access import readable_comment_or_404

router = APIRouter(tags=["评论举报"])

_report_rule = RateLimitRule(
    requests=10,
    window_seconds=60,
    strategy=RateLimitStrategy.SLIDING_WINDOW,
    key_prefix="comment_report",
)


def _rate_limit_comment_report(endpoint_name: str):
    return build_depends_rate_limit(_report_rule, endpoint_name, use_user_id=False)


_ANON_DEDUPE_WINDOW = timedelta(hours=24)
_EXCERPT_LIMIT = 120


def _iso(value: datetime | None) -> str | None:
    return value.isoformat() if value else None


def _display_name(nickname: str | None, username: str | None) -> str | None:
    return nickname or username or None


def _report_columns():
    """举报 + 评论摘要 + 文章摘要 + 举报人/裁决人的列投影（不实例化 ORM 对象）。

    刻意不走 ``select(CommentReport, Comment, Post)``：``Post`` 带着正文、加密正文与
    meta 三列，实例化就会把它们一起拉进内存（评论列表端点同型，那里是 ``defer`` 兜的）。
    这里只要标题/slug，按列取最省事，也不会在异步会话上触发懒加载。
    """
    handler = aliased(User)
    return (
        select(
            CommentReport,
            Comment.content,
            Comment.author_name,
            Comment.status,
            Post.slug,
            Post.title,
            User.nickname,
            User.username,
            handler.nickname,
            handler.username,
        )
        .join(Comment, Comment.id == CommentReport.comment_id)
        .outerjoin(Post, Post.id == CommentReport.post_id)
        .outerjoin(User, User.id == CommentReport.reporter_user_id)
        .outerjoin(handler, handler.id == CommentReport.handled_by_id)
    )


def _to_item(row) -> AdminCommentReportItem:
    (
        report,
        comment_content,
        comment_author,
        comment_status,
        post_slug,
        post_title,
        reporter_nickname,
        reporter_username,
        handler_nickname,
        handler_username,
    ) = row
    content = (comment_content or "").strip().replace("\r", "")
    excerpt = content[:_EXCERPT_LIMIT] + ("…" if len(content) > _EXCERPT_LIMIT else "")
    return AdminCommentReportItem(
        id=report.id,
        comment_id=report.comment_id,
        post_id=report.post_id,
        reason=report.reason,
        detail=report.detail,
        status=report.status,
        reporter_user_id=report.reporter_user_id,
        reporter_name=_display_name(reporter_nickname, reporter_username),
        reporter_ip=report.reporter_ip,
        comment_excerpt=excerpt,
        comment_author=comment_author or "匿名用户",
        comment_status=comment_status or "approved",
        post_slug=post_slug,
        post_title=get_i18n_value(post_title, "zh") if post_title else None,
        created_at=_iso(report.created_at),
        handled_at=_iso(report.handled_at),
        handled_by=_display_name(handler_nickname, handler_username),
    )


async def _counts(db: DB) -> dict[str, int]:
    rows = (
        await db.execute(
            select(CommentReport.status, func.count(CommentReport.id)).group_by(
                CommentReport.status
            )
        )
    ).all()
    mapped = {str(status): int(count) for status, count in rows}
    open_count = mapped.get("open", 0)
    handled = mapped.get("handled", 0)
    dismissed = mapped.get("dismissed", 0)
    return {
        "open": open_count,
        "handled": handled,
        "dismissed": dismissed,
        "total": open_count + handled + dismissed,
    }


async def _has_open_report(db: DB, comment_id: int) -> bool:
    return bool(
        await db.scalar(
            select(func.count(CommentReport.id)).where(
                CommentReport.comment_id == comment_id,
                CommentReport.status == "open",
            )
        )
    )


@router.post(
    "/comments/{comment_id}/report",
    response_model=CommentReportReceipt,
    status_code=status.HTTP_201_CREATED,
    summary="举报评论（匿名或登录用户）",
    description=(
        "公开写口，匿名可用；按 IP 限流 10 次/分钟（滑动窗口）。"
        "评论不存在、所属文章不可见或加密未解锁一律 404（COMMENT_NOT_FOUND），"
        "与读口同源闸门（services.comment_access）。"
        "登录用户举报自己的评论返回 400（SELF_REPORT）；游客评论的 user_id 为空，任何账号都可举报。"
        "同一登录用户对同一条评论只保留一条待处理举报，匿名按 IP + 24 小时去重——"
        "重复时**不新建行**，返回 200 且 `duplicate=true`（不是错误）。"
        "携带 Bearer Token 时走 per-route CSRF 依赖（带 Origin 必须命中白名单）；匿名请求跳过。"
        "成功后置起 `comments.reported_at` 供后台「待处理」筛选使用。"
    ),
    responses={
        200: {
            "model": CommentReportReceipt,
            "description": "重复举报：未新建行，返回已存在的那条（duplicate=true）",
        }
    },
    dependencies=[
        Depends(_rate_limit_comment_report("comment_report")),
        Depends(require_csrf),
    ],
)
async def report_comment(
    comment_id: int,
    data: CommentReportCreate,
    request: Request,
    response: Response,
    db: DB,
    current_user: CurrentUserOptional = None,
):
    """标记一条评论：落举报行 + 立起评论的待处理标记。"""
    comment = await readable_comment_or_404(db, comment_id, current_user)

    if current_user is not None and comment.user_id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "success": False,
                "message": "不能举报自己的评论",
                "error_code": "SELF_REPORT",
            },
        )

    client_ip = get_client_ip(request)

    # 去重：登录用户按 user_id，匿名按 IP + 24h。只对 open 状态去重——
    # 管理员驳回后再报是正常诉求，不该被历史记录挡住。
    existing: CommentReport | None = None
    if current_user is not None:
        existing = (
            await db.execute(
                select(CommentReport)
                .where(
                    CommentReport.comment_id == comment_id,
                    CommentReport.status == "open",
                    CommentReport.reporter_user_id == current_user.id,
                )
                .order_by(CommentReport.id.desc())
                .limit(1)
            )
        ).scalar_one_or_none()
    elif client_ip:
        existing = (
            await db.execute(
                select(CommentReport)
                .where(
                    CommentReport.comment_id == comment_id,
                    CommentReport.status == "open",
                    CommentReport.reporter_user_id.is_(None),
                    CommentReport.reporter_ip == client_ip,
                    CommentReport.created_at >= datetime.now(timezone.utc) - _ANON_DEDUPE_WINDOW,
                )
                .order_by(CommentReport.id.desc())
                .limit(1)
            )
        ).scalar_one_or_none()

    if existing is not None:
        response.status_code = status.HTTP_200_OK
        return CommentReportReceipt(
            id=existing.id,
            comment_id=comment_id,
            status=existing.status,
            duplicate=True,
            message="你已经举报过这条评论，管理员会尽快处理",
        )

    report = CommentReport(
        comment_id=comment_id,
        post_id=comment.post_id,
        reporter_user_id=current_user.id if current_user is not None else None,
        reporter_ip=client_ip or None,
        reason=data.reason,
        detail=(data.detail or "").strip() or None,
        status="open",
    )
    db.add(report)
    if comment.reported_at is None:
        comment.reported_at = datetime.now(timezone.utc)
    await db.flush()
    await db.commit()
    await db.refresh(report)
    return CommentReportReceipt(
        id=report.id,
        comment_id=comment_id,
        status=report.status,
        duplicate=False,
        message="举报已提交，感谢你的反馈",
    )


@router.get(
    "/admin/comments/reports",
    summary="评论举报列表（管理员）",
    description=(
        "按状态筛选 + 分页返回举报明细，附带每个状态的总数（不受筛选影响，用于页签角标）。"
        "响应为裸分页 dict（items/total/page/page_size/total_pages/counts），无 success/data 信封。"
        "单条含被举报评论正文前 120 字、评论审核状态、文章 slug/标题与举报人摘要；"
        "`reporter_ip` 属 PII，与评论列表同口径只对 staff 开放，不要再放宽闸门。"
    ),
    responses={200: {"model": AdminCommentReportListResponse}},
)
async def list_comment_reports(
    db: DB,
    current_user: CurrentStaff,
    status_filter: str = Query(
        "open",
        alias="status",
        pattern="^(open|handled|dismissed|all)$",
        description="open（默认，只看待处理）/ handled / dismissed / all",
    ),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    """管理员：举报队列。"""
    conditions = []
    if status_filter != "all":
        conditions.append(CommentReport.status == status_filter)

    count_q = select(func.count(CommentReport.id))
    if conditions:
        count_q = count_q.where(*conditions)
    total = (await db.scalar(count_q)) or 0

    stmt = _report_columns()
    if conditions:
        stmt = stmt.where(*conditions)
    stmt = (
        stmt.order_by(CommentReport.created_at.desc(), CommentReport.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    rows = (await db.execute(stmt)).all()
    counts = await _counts(db)

    return {
        "items": [_to_item(row).model_dump() for row in rows],
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": (total + page_size - 1) // page_size if total else 0,
        "counts": counts,
    }


@router.patch(
    "/admin/comments/reports/{report_id}",
    summary="裁决评论举报（管理员）",
    description=(
        "把一条举报置为 handled（确认违规并已处置）或 dismissed（误报驳回），"
        "并记录裁决人与时间。重复裁决按最后一次为准（不做状态机拦截）。"
        "裁决后若该评论已无其它待处理举报，清空 `comments.reported_at`；"
        "响应额外带 `comment_reported` 标识评论是否仍挂着待处理举报。"
        "注意：本端点只改举报状态，**不会**下架评论——下架仍走 "
        "PATCH /api/admin/comments/{comment_id} 的 status 字段。"
    ),
    responses={200: {"model": AdminCommentReportUpdated}},
)
async def update_comment_report(
    report_id: int,
    data: AdminCommentReportUpdate,
    db: DB,
    current_user: CurrentStaff,
):
    """管理员：裁决一条举报。"""
    report = await db.scalar(select(CommentReport).where(CommentReport.id == report_id))
    if report is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "success": False,
                "message": "举报记录不存在",
                "error_code": "REPORT_NOT_FOUND",
            },
        )

    report.status = data.status
    report.handled_by_id = current_user.id
    report.handled_at = datetime.now(timezone.utc)
    # 先落这一行再数 open：自动刷新虽会替我们做，但依赖 autoflush 的时序太脆——
    # 计数一旦读到"改之前"的状态，reported_at 就永远清不掉。
    await db.flush()

    comment = await db.scalar(select(Comment).where(Comment.id == report.comment_id))
    still_open = await _has_open_report(db, report.comment_id)
    if comment is not None and not still_open:
        comment.reported_at = None

    await db.commit()

    row = (await db.execute(_report_columns().where(CommentReport.id == report_id))).first()
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "success": False,
                "message": "举报记录不存在",
                "error_code": "REPORT_NOT_FOUND",
            },
        )
    item = _to_item(row)
    return AdminCommentReportUpdated(
        **item.model_dump(),
        comment_reported=still_open,
    )
