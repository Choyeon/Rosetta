"""
Rosetta 评论 API 路由（独立 comments 模块）

公开端点：
- GET  /api/posts/{post_id_or_slug}/comments          取文章根评论分页（含前3回复 + reply_total）
- GET  /api/comments/{comment_id}/replies             取某根评论的回复分页
- POST /api/posts/{post_id_or_slug}/comments          发表评论（游客或 OptionalCurrentUser）
- POST /api/comments/{comment_id}/like                点赞

管理员端点：
- GET    /api/admin/comments                          列表（status/pagination/keyword）
- POST   /api/admin/comments/{id}/approve|reject|spam 单条审核
- POST   /api/admin/comments/batch                    批量 approve/reject/spam/delete
- DELETE /api/admin/comments/{id}                     删除
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, Query, Request

from backend.core.deps import (
    DB,
    CurrentStaff,
    CurrentUserOptional,
    PaginationParams,
    get_pagination,
    require_csrf,
)
from backend.core.rate_limit import (
    RateLimitRule,
    RateLimitStrategy,
    build_depends_rate_limit,
    get_client_ip,
    rate_limit_sensitive,
)
from backend.schemas import (
    BaseResponse,
    CommentBatchAction,
    CommentCreate,
    CommentPagedResponse,
    CommentResponse,
)
from backend.services.comment_service import CommentService

logger = logging.getLogger(__name__)

router = APIRouter(tags=["评论"])


# ================= 自定义 RateLimit 依赖 =================

_like_rule = RateLimitRule(
    requests=30,
    window_seconds=60,
    strategy=RateLimitStrategy.SLIDING_WINDOW,
    key_prefix="comment_like",
)


def _rate_limit_comment_like(endpoint_name: str):
    return build_depends_rate_limit(_like_rule, endpoint_name, use_user_id=False)


# ================= 工具 =================


def _service_err_to_http(exc: ValueError) -> HTTPException:
    """把 CommentService 抛出的 ValueError(CODE) 转成合适的 HTTPException"""
    code = str(exc)
    mapping: dict[str, tuple[int, str]] = {
        "AUTHOR_NAME_REQUIRED": (422, "评论需要填写昵称"),
        "AUTHOR_NAME_TOO_SHORT": (422, "昵称至少 2 个字符"),
        "COMMENT_PARENT_NOT_FOUND": (404, "回复的目标评论不存在"),
        "COMMENT_PARENT_WRONG_POST": (422, "回复的目标评论不属于这篇文章"),
        "NESTED_REPLY_TOO_DEEP": (422, "嵌套回复不能超过 1 层，请直接回复根评论"),
        "TOO_FREQUENT_COMMENT": (429, "你在这篇文章发表评论太频繁了，请稍后再试"),
        "COMMENT_NOT_FOUND": (404, "评论不存在"),
        "INVALID_ACTION": (422, "未知批量操作类型"),
    }
    status, msg = mapping.get(code, (400, f"Bad Request: {code}"))
    detail = {"success": False, "message": msg, "error_code": code}
    if status == 429:
        headers = {"Retry-After": "30"}
        return HTTPException(status_code=status, detail=detail, headers=headers)
    return HTTPException(status_code=status, detail=detail)


def _pagination_to_response(
    items: list[CommentResponse], total: int, page: int, page_size: int
) -> CommentPagedResponse:
    total_pages = (total + page_size - 1) // page_size if page_size else 0
    return CommentPagedResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


# ================= 公开端点 =================


@router.get(
    "/posts/{post_id_or_slug}/comments",
    response_model=CommentPagedResponse,
    summary="获取某文章根评论分页（含前 3 条最新回复与 reply_total）",
)
async def list_root_comments(
    post_id_or_slug: str,
    db: DB,
    pagination: PaginationParams = Depends(get_pagination),
    include_unapproved: bool = Query(
        False, description="是否包含待审核/已拒绝（仅作者/管理员可见本人或全部）"
    ),
    current_user: CurrentUserOptional = None,
):
    post = await CommentService.get_post_by_any(db, post_id_or_slug)
    if post is None:
        raise HTTPException(
            status_code=404,
            detail={"success": False, "message": "文章不存在", "error_code": "POST_NOT_FOUND"},
        )
    try:
        items, total = await CommentService.list_root_comments(
            db,
            post=post,
            page=pagination.page,
            page_size=pagination.page_size,
            include_unapproved=bool(include_unapproved),
            current_user=current_user,
        )
    except ValueError as e:
        raise _service_err_to_http(e) from e
    return _pagination_to_response(items, total, pagination.page, pagination.page_size)


@router.get(
    "/comments/{comment_id}/replies",
    response_model=CommentPagedResponse,
    summary="获取某根评论的全部回复分页",
)
async def list_replies(
    comment_id: int,
    db: DB,
    pagination: PaginationParams = Depends(get_pagination),
    current_user: CurrentUserOptional = None,
):
    try:
        items, total, _post = await CommentService.get_replies(
            db,
            comment_id=comment_id,
            page=pagination.page,
            page_size=pagination.page_size,
            current_user=current_user,
        )
    except ValueError as e:
        raise _service_err_to_http(e) from e
    return _pagination_to_response(items, total, pagination.page, pagination.page_size)


@router.post(
    "/posts/{post_id_or_slug}/comments",
    response_model=CommentResponse,
    status_code=201,
    summary="发表评论（游客或登录用户均可）",
    dependencies=[Depends(rate_limit_sensitive("post_comment")), Depends(require_csrf)],
)
async def create_comment(
    post_id_or_slug: str,
    data: CommentCreate,
    request: Request,
    db: DB,
    current_user: CurrentUserOptional = None,
):
    post = await CommentService.get_post_by_any(db, post_id_or_slug)
    if post is None:
        raise HTTPException(
            status_code=404,
            detail={"success": False, "message": "文章不存在", "error_code": "POST_NOT_FOUND"},
        )
    try:
        client_ip = get_client_ip(request)
        ua = request.headers.get("User-Agent")
        resp = await CommentService.create_comment(
            db,
            post=post,
            data=data,
            client_ip=client_ip,
            user_agent=ua,
            current_user=current_user,
        )
        await db.commit()
    except ValueError as e:
        await db.rollback()
        raise _service_err_to_http(e) from e
    except HTTPException:
        await db.rollback()
        raise
    except Exception as e:
        await db.rollback()
        logger.exception("create_comment unexpected error")
        raise HTTPException(
            status_code=500,
            detail={"success": False, "message": "服务器错误", "error_code": "INTERNAL"},
        ) from e
    return resp


@router.post(
    "/comments/{comment_id}/like",
    summary="给评论点赞（简单计数，允许匿名）",
    dependencies=[Depends(_rate_limit_comment_like("comment_like"))],
)
async def like_comment(comment_id: int, db: DB):
    try:
        likes = await CommentService.like(db, comment_id)
        await db.commit()
    except ValueError as e:
        await db.rollback()
        raise _service_err_to_http(e) from e
    return {"success": True, "likes_count": likes}


# ================= 管理员端点 =================
# 注意：评论列表(GET)、单条更新(PATCH)、单条删除(DELETE) 已统一由 admin.py 提供，
# 此处仅保留 Phase 3 已上线且仍被 React Admin 前端调用的 legacy 子动作：
#   POST /api/admin/comments/{id}/approve | reject | spam
#   POST /api/admin/comments/batch


@router.post(
    "/admin/comments/{comment_id}/approve",
    response_model=CommentResponse,
    summary="【管理员】批准评论（legacy 子动作，建议统一使用 PATCH /api/admin/comments/{id} status=approved）",
)
async def admin_approve(_staff: CurrentStaff, comment_id: int, db: DB):
    try:
        r = await CommentService.admin_approve(db, comment_id)
        await db.commit()
    except ValueError as e:
        await db.rollback()
        raise _service_err_to_http(e) from e
    return r


@router.post(
    "/admin/comments/{comment_id}/reject",
    response_model=CommentResponse,
    summary="【管理员】拒绝评论（legacy 子动作）",
)
async def admin_reject(_staff: CurrentStaff, comment_id: int, db: DB):
    try:
        r = await CommentService.admin_reject(db, comment_id)
        await db.commit()
    except ValueError as e:
        await db.rollback()
        raise _service_err_to_http(e) from e
    return r


@router.post(
    "/admin/comments/{comment_id}/spam",
    response_model=CommentResponse,
    summary="【管理员】标记为垃圾评论（legacy 子动作）",
)
async def admin_spam(_staff: CurrentStaff, comment_id: int, db: DB):
    try:
        r = await CommentService.admin_spam(db, comment_id)
        await db.commit()
    except ValueError as e:
        await db.rollback()
        raise _service_err_to_http(e) from e
    return r


# /admin/comments/{id} DELETE：移除（已由 admin.py@router.delete("/comments/{comment_id}") 统一提供）
# /admin/comments      GET：移除（已由 admin.py@router.get("/comments") 统一提供，带 status/qq/github/parent_ref 等扩展）


@router.post(
    "/admin/comments/batch",
    response_model=BaseResponse,
    summary="【管理员】批量操作评论（approve/reject/spam/delete）",
)
async def admin_batch(_staff: CurrentStaff, body: CommentBatchAction, db: DB):
    try:
        result = await CommentService.admin_batch(db, body.ids, body.action)
        await db.commit()
    except ValueError as e:
        await db.rollback()
        raise _service_err_to_http(e) from e
    return BaseResponse(success=True, message=f"已处理 {result.get('processed', 0)} 条")
