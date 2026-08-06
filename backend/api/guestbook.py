"""
Rosetta 留言板 API 路由（Task 6 新版）

公开端点：
- GET  /api/guestbook                       留言板列表分页（按置顶/精华/时间倒序）
- POST /api/guestbook                       发表留言（游客或登录用户）
- POST /api/guestbook/{id}/like             点赞

管理员端点：
- GET    /api/admin/guestbook               列表（status/pagination/keyword，支持 status=trashed 查回收站）
- POST   /api/admin/guestbook/{id}/pin      切换置顶
- POST   /api/admin/guestbook/{id}/feature  切换精华
- POST   /api/admin/guestbook/{id}/approve | reject | spam   单条审核
- POST   /api/admin/guestbook/batch         批量 approve/reject/spam/pin/feature/trash/restore/delete
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
    GuestbookBatchAction,
    GuestbookEntryCreate,
    GuestbookEntryPagedResponse,
    GuestbookEntryResponse,
)
from backend.services.guestbook_service import GuestbookService

logger = logging.getLogger(__name__)

router = APIRouter(tags=["留言板"])


_like_rule = RateLimitRule(
    requests=30,
    window_seconds=60,
    strategy=RateLimitStrategy.SLIDING_WINDOW,
    key_prefix="guestbook_like",
)


def _rate_limit_guestbook_like(endpoint_name: str):
    return build_depends_rate_limit(_like_rule, endpoint_name, use_user_id=False)


def _service_err_to_http(exc: ValueError) -> HTTPException:
    """把 GuestbookService 抛出的 ValueError(CODE) 转成合适的 HTTPException"""
    code = str(exc)
    mapping: dict[str, tuple[int, str]] = {
        "AUTHOR_NAME_REQUIRED": (422, "留言需要填写昵称"),
        "AUTHOR_NAME_TOO_SHORT": (422, "昵称至少 2 个字符"),
        "CONTENT_TOO_SHORT": (422, "留言内容至少 2 个字符"),
        "CONTENT_TOO_LONG": (422, "留言内容不能超过 3000 字符"),
        "TOO_FREQUENT_GUESTBOOK": (429, "你在留言板发表留言太频繁了，请稍后再试"),
        "GUESTBOOK_ENTRY_NOT_FOUND": (404, "留言不存在"),
        "INVALID_ACTION": (422, "未知批量操作类型"),
    }
    status, msg = mapping.get(code, (400, f"Bad Request: {code}"))
    detail = {"success": False, "message": msg, "error_code": code}
    if status == 429:
        headers = {"Retry-After": "30"}
        return HTTPException(status_code=status, detail=detail, headers=headers)
    return HTTPException(status_code=status, detail=detail)


def _pagination_to_response(
    items: list[GuestbookEntryResponse], total: int, page: int, page_size: int
) -> GuestbookEntryPagedResponse:
    total_pages = (total + page_size - 1) // page_size if page_size else 0
    return GuestbookEntryPagedResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


# ================= 公开端点 =================


@router.get(
    "/guestbook",
    response_model=GuestbookEntryPagedResponse,
    summary="获取留言板分页列表",
)
async def list_guestbook_entries(
    db: DB,
    pagination: PaginationParams = Depends(get_pagination),
    status: str | None = Query(
        "approved", description="approved|pending|rejected|spam|all|trashed"
    ),
    include: str | None = Query(None, description="trashed=包含回收站（管理员）"),
    current_user: CurrentUserOptional = None,
):
    try:
        include_trashed = include == "trashed"
        items, total = await GuestbookService.list_entries(
            db,
            page=pagination.page,
            page_size=pagination.page_size,
            status=status,
            include_trashed=include_trashed,
            current_user=current_user,
        )
    except ValueError as e:
        raise _service_err_to_http(e) from e
    return _pagination_to_response(items, total, pagination.page, pagination.page_size)


@router.post(
    "/guestbook",
    response_model=GuestbookEntryResponse,
    status_code=201,
    summary="发表留言（游客或登录用户均可）",
    dependencies=[Depends(rate_limit_sensitive("post_guestbook"))],
)
async def create_guestbook_entry(
    data: GuestbookEntryCreate,
    request: Request,
    db: DB,
    current_user: CurrentUserOptional = None,
):
    try:
        client_ip = get_client_ip(request)
        ua = request.headers.get("User-Agent")
        resp = await GuestbookService.create_entry(
            db,
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
        logger.exception("create_guestbook_entry unexpected error")
        raise HTTPException(
            status_code=500,
            detail={"success": False, "message": "服务器错误", "error_code": "INTERNAL"},
        ) from e
    return resp


@router.post(
    "/guestbook/{entry_id}/like",
    summary="给留言点赞（简单计数，允许匿名）",
    dependencies=[Depends(_rate_limit_guestbook_like("guestbook_like"))],
)
async def like_guestbook_entry(entry_id: int, db: DB):
    try:
        likes = await GuestbookService.like(db, entry_id)
        await db.commit()
    except ValueError as e:
        await db.rollback()
        raise _service_err_to_http(e) from e
    return {"success": True, "likes_count": likes}


# ================= 管理员端点 =================


@router.get(
    "/admin/guestbook",
    response_model=GuestbookEntryPagedResponse,
    summary="【管理员】留言板列表（含审核状态过滤/回收站/搜索）",
)
async def admin_list_guestbook(
    _staff: CurrentStaff,
    db: DB,
    pagination: PaginationParams = Depends(get_pagination),
    status: str | None = Query(None, description="pending|approved|rejected|spam|trashed|all"),
    keyword: str | None = Query(None, description="关键词搜索内容/昵称/邮箱"),
):
    try:
        items, total = await GuestbookService.admin_list(
            db,
            status=status,
            keyword=keyword,
            page=pagination.page,
            page_size=pagination.page_size,
        )
    except ValueError as e:
        raise _service_err_to_http(e) from e
    return _pagination_to_response(items, total, pagination.page, pagination.page_size)


@router.post(
    "/admin/guestbook/{entry_id}/pin",
    response_model=GuestbookEntryResponse,
    summary="【管理员】切换留言置顶",
)
async def admin_toggle_pin(_staff: CurrentStaff, entry_id: int, db: DB):
    try:
        r = await GuestbookService.admin_toggle_pin(db, entry_id)
        await db.commit()
    except ValueError as e:
        await db.rollback()
        raise _service_err_to_http(e) from e
    return r


@router.post(
    "/admin/guestbook/{entry_id}/feature",
    response_model=GuestbookEntryResponse,
    summary="【管理员】切换留言精华",
)
async def admin_toggle_feature(_staff: CurrentStaff, entry_id: int, db: DB):
    try:
        r = await GuestbookService.admin_toggle_feature(db, entry_id)
        await db.commit()
    except ValueError as e:
        await db.rollback()
        raise _service_err_to_http(e) from e
    return r


@router.post(
    "/admin/guestbook/{entry_id}/approve",
    response_model=GuestbookEntryResponse,
    summary="【管理员】批准留言",
)
async def admin_approve(_staff: CurrentStaff, entry_id: int, db: DB):
    try:
        r = await GuestbookService.admin_approve(db, entry_id)
        await db.commit()
    except ValueError as e:
        await db.rollback()
        raise _service_err_to_http(e) from e
    return r


@router.post(
    "/admin/guestbook/{entry_id}/reject",
    response_model=GuestbookEntryResponse,
    summary="【管理员】拒绝留言",
)
async def admin_reject(_staff: CurrentStaff, entry_id: int, db: DB):
    try:
        r = await GuestbookService.admin_reject(db, entry_id)
        await db.commit()
    except ValueError as e:
        await db.rollback()
        raise _service_err_to_http(e) from e
    return r


@router.post(
    "/admin/guestbook/{entry_id}/spam",
    response_model=GuestbookEntryResponse,
    summary="【管理员】标记为垃圾留言",
)
async def admin_spam(_staff: CurrentStaff, entry_id: int, db: DB):
    try:
        r = await GuestbookService.admin_spam(db, entry_id)
        await db.commit()
    except ValueError as e:
        await db.rollback()
        raise _service_err_to_http(e) from e
    return r


@router.post(
    "/admin/guestbook/batch",
    response_model=BaseResponse,
    summary="【管理员】批量操作留言（approve/reject/spam/pin/feature/trash/restore/delete）",
)
async def admin_batch(_staff: CurrentStaff, body: GuestbookBatchAction, db: DB):
    try:
        result = await GuestbookService.admin_batch(db, body.ids, body.action)
        await db.commit()
    except ValueError as e:
        await db.rollback()
        raise _service_err_to_http(e) from e
    return BaseResponse(success=True, message=f"已处理 {result.get('processed', 0)} 条")
