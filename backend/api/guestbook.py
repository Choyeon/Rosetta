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
from pydantic import BaseModel, Field

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


# ═══════════════════════════════════════════════════════════════════════════
# 响应体文档模型（仅供 OpenAPI `responses={200: {"model": ...}}` 声明使用，
# 运行时不做序列化过滤——实际响应以 handler 返回字面量为准）
# ═══════════════════════════════════════════════════════════════════════════


class GuestbookLikeResponse(BaseModel):
    """留言点赞端点的响应体。"""

    success: bool = Field(True, description="固定为 true：留言不存在时本接口返回 404 而非 false")
    likes_count: int = Field(
        0, description="自增之后该留言的最新点赞总数（不是本次请求的增量，恒为正整数）"
    )


# ================= 公开端点 =================


@router.get(
    "/guestbook",
    response_model=GuestbookEntryPagedResponse,
    summary="获取留言板分页列表",
    description=(
        "公开接口，无需登录。按 置顶 → 精华 → 时间 倒序分页返回留言。"
        "默认只返回 approved 条目；status 支持 approved|pending|rejected|spam|all|trashed，"
        "include=trashed 时包含回收站条目（管理员语义）。"
        "携带 Bearer Token 时登录用户可看到自己尚未过审的留言；匿名访客只看得到已过审内容。"
    ),
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
    description=(
        "公开写入接口，携带可选 Bearer Token 时自动关联登录用户身份。"
        "服务端记录客户端 IP 与 User-Agent 用于审核追溯；留言进入审核流，"
        "管理员批准后才对公众可见。"
        "受敏感接口限流与同 IP 频控保护：过于频繁返回 429（业务码 TOO_FREQUENT_GUESTBOOK，"
        "响应头带 Retry-After: 30）。字段校验失败返回 422："
        "AUTHOR_NAME_REQUIRED / AUTHOR_NAME_TOO_SHORT / CONTENT_TOO_SHORT / CONTENT_TOO_LONG。"
        "非幂等，重复提交会产生多条留言。"
    ),
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
    description=(
        "公开接口，无需登录。对指定留言的 likes_count 做简单自增，不做按用户去重，"
        "因此非幂等（重复调用会重复计数）。自增前对留言行加行锁，并发点赞不会丢计数。"
        "按 IP 限流 30 次/分钟（滑动窗口）。"
        "留言不存在或已被移入回收站时返回 404（业务码 GUESTBOOK_ENTRY_NOT_FOUND）。"
        "返回值是点赞后的累计总数，不是本次增量。"
        "响应为裸 dict（success + 自增后的 likes_count 累计总数），无 data 信封。"
    ),
    dependencies=[Depends(_rate_limit_guestbook_like("guestbook_like"))],
    responses={200: {"model": GuestbookLikeResponse}},
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
    description=(
        "需 CurrentStaff（管理员 Bearer Token）。支持 status 过滤"
        "（pending|approved|rejected|spam|trashed|all）与 keyword 对内容/昵称/邮箱的模糊搜索，"
        "分页返回含审核状态的完整条目（含未过审与回收站数据，仅管理员可见）。"
    ),
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
    description=(
        "需 CurrentStaff。Toggle 语义：当前置顶则取消、未置顶则置顶，可安全重复调用（幂等于切换）。"
        "留言不存在时返回 404（业务码 GUESTBOOK_ENTRY_NOT_FOUND）。"
    ),
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
    description=(
        "需 CurrentStaff。Toggle 语义：当前为精华则取消、反之设为精华。"
        "留言不存在时返回 404（业务码 GUESTBOOK_ENTRY_NOT_FOUND）。"
    ),
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
    description=(
        "需 CurrentStaff。将留言状态置为 approved 并立即对公众可见。"
        "幂等：对已批准条目重复调用不产生副作用。"
        "留言不存在时返回 404（业务码 GUESTBOOK_ENTRY_NOT_FOUND）。"
    ),
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
    description=(
        "需 CurrentStaff。将留言状态置为 rejected，前台不再展示（作者登录可见自己的被拒条目）。"
        "留言不存在时返回 404（业务码 GUESTBOOK_ENTRY_NOT_FOUND）。"
    ),
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
    description=(
        "需 CurrentStaff。将留言状态置为 spam，前台不再展示。"
        "留言不存在时返回 404（业务码 GUESTBOOK_ENTRY_NOT_FOUND）。"
    ),
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
    description=(
        "需 CurrentStaff。请求体 {ids: [留言ID...], action: 上述枚举之一}。"
        "逐条执行并统计处理数量；action 不在枚举内返回 422（业务码 INVALID_ACTION）。"
        "trash/restore 进/出回收站，delete 为彻底删除（回收站内条目也可删）。"
    ),
)
async def admin_batch(_staff: CurrentStaff, body: GuestbookBatchAction, db: DB):
    try:
        result = await GuestbookService.admin_batch(db, body.ids, body.action)
        await db.commit()
    except ValueError as e:
        await db.rollback()
        raise _service_err_to_http(e) from e
    return BaseResponse(success=True, message=f"已处理 {result.get('processed', 0)} 条")


@router.delete(
    "/admin/guestbook/{entry_id}",
    response_model=BaseResponse,
    summary="【管理员】单条删除留言",
    description=(
        "需 CurrentStaff。内部复用批量 delete 通道彻底删除（非软删除，不可恢复）。"
        "条目不存在或已被删除时返回 404。"
    ),
)
async def admin_delete_entry(_staff: CurrentStaff, entry_id: int, db: DB):
    try:
        result = await GuestbookService.admin_batch(db, [entry_id], "delete")
        await db.commit()
    except ValueError as e:
        await db.rollback()
        raise _service_err_to_http(e) from e
    if result.get("processed", 0) == 0:
        raise HTTPException(status_code=404, detail=f"留言 {entry_id} 不存在或已被删除")
    return BaseResponse(success=True, message="留言已删除")
