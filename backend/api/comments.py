"""
Rosetta 评论 API 路由（独立 comments 模块）

公开端点：
- GET  /api/posts/{post_id_or_slug}/comments          取文章根评论分页（含前3回复 + reply_total）
- GET  /api/comments/{comment_id}/replies             取某根评论的回复分页
- POST /api/posts/{post_id_or_slug}/comments          发表评论（游客或 OptionalCurrentUser）
- POST /api/comments/{comment_id}/like                点赞
- DELETE /api/comments/{comment_id}                   作者本人删除自己的评论（进回收站）

管理员端点：
- GET    /api/admin/comments                          列表（status/pagination/keyword）
- POST   /api/admin/comments/{id}/approve|reject|spam 单条审核
- POST   /api/admin/comments/batch                    批量 approve/reject/spam/delete

单条 PATCH / 管理员单条 DELETE 由 admin.py 统一提供（本模块只留 legacy 子动作）；
作者本人删自己那条评论走本模块的 DELETE /api/comments/{comment_id}（归属判据进 WHERE，
与管理员单删同构：回收站快照 + comment.deleted 钩子 + 文章缓存失效）。

文章可读性闸门：本模块所有口（含 `/api/comments/{id}/replies`）的可见性判据都走
:mod:`backend.services.post_access`，与文章详情端点同源——草稿、定时未到、加密未解锁
的文章，它的评论树对无权观看者一律不存在（404 / 空）。加新评论口时**不要**再自己
`select(Post)`，那道判据漏一处就是正文藏住而评论全公开。

缓存口径：文章的 ``comments_count`` 会嵌进列表缓存（``posts*``，读侧不重算）与
文章详情响应体，所以本模块所有"改变可见评论集合"的写操作都要走
:func:`backend.services.post_cache.invalidate_post_caches_by_ids`。
（详情键的读侧 ``GET /posts/{slug}`` 本来就会当场重算 likes/comments 计数，
顺带失效它是为了让快照与列表口径一致，而不是为了纠正计数。）
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request
from pydantic import BaseModel, Field
from sqlalchemy import select

from backend.core.csrf import require_csrf
from backend.core.deps import (
    DB,
    CurrentStaff,
    CurrentUser,
    CurrentUserOptional,
    PaginationParams,
    get_pagination,
)
from backend.core.plugin_bus import bus
from backend.core.rate_limit import (
    RateLimitRule,
    RateLimitStrategy,
    build_depends_rate_limit,
    get_client_ip,
    rate_limit_sensitive,
    rate_limit_write,
)
from backend.models.blog import Comment
from backend.schemas import (
    BaseResponse,
    CommentBatchAction,
    CommentCreate,
    CommentPagedResponse,
    CommentResponse,
)
from backend.services.comment_service import CommentService
from backend.services.frontend_cache_purge import purge_frontend_page_cache
from backend.services.post_cache import invalidate_post_caches_by_ids
from backend.services.trash import comment_trash_payload, snapshot_to_trash

logger = logging.getLogger(__name__)

router = APIRouter(tags=["评论"])


# ═══════════════════════════════════════════════════════════════════════════
# 响应体文档模型（仅供 OpenAPI `responses={200: {"model": ...}}` 声明使用，
# 运行时不做序列化过滤——实际响应以 handler 返回字面量为准）
# ═══════════════════════════════════════════════════════════════════════════


class CommentLikeResponse(BaseModel):
    """评论点赞端点的响应体（裸 dict，无 success/data 信封）。"""

    success: bool = Field(True, description="固定为 true：评论不存在时本接口返回 404 而非 false")
    likes_count: int = Field(
        0, description="自增之后该评论的最新点赞总数（不是本次请求的增量，非幂等）"
    )


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
        # 以下四条来自后台「评论」分组（site_configs.key="comments"）：
        # 403 是站点策略（关评论 / 关访客评论），不是凭证失效——用 401 会让前端
        # apiFetch 把这次操作判成"登录过期"并清登录态（AGENTS §7.2 红线）。
        "COMMENTS_DISABLED": (403, "站点已关闭评论功能"),
        "COMMENT_POST_CLOSED": (403, "该文章已关闭评论"),
        "COMMENT_GUEST_NOT_ALLOWED": (403, "本站评论需要登录，请先登录"),
        "COMMENT_NESTING_DISABLED": (422, "本站已关闭嵌套回复，请直接发表评论"),
        "COMMENT_TOO_LONG": (422, "评论内容超出本站允许的最大长度"),
        # 图形验证码（后台「功能开关 → 图形验证码」打开后，匿名提交必须带）：
        # 400 而不是 401——验证码错不等于登录凭证失效（AGENTS §7.2）。
        "CAPTCHA_REQUIRED": (400, "请填写验证码"),
        "CAPTCHA_EXPIRED": (400, "验证码已过期，请重新获取"),
        "CAPTCHA_INVALID": (400, "验证码错误，请重试"),
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
    description=(
        "公开接口。post_id_or_slug 同时接受数字 ID 或文章 slug；文章不存在返回 404"
        "（业务码 POST_NOT_FOUND）。每条根评论附带前 3 条最新回复与 reply_total，"
        "完整回复走 GET /api/comments/{comment_id}/replies。"
        "include_unapproved=true 仅对作者本人/管理员生效，匿名访客始终只见过审评论。"
        "评论树的可读性判定与文章详情同源：草稿/待审/定时未到的文章、以及设了密码但"
        "本次未带正确密码（``password`` 查询参数或 ``X-Post-Password`` 头，作者与 staff 免验）"
        "的文章，对无权观看者一律 404 POST_NOT_FOUND，而不是把正文藏起来却把评论全给你。"
    ),
)
async def list_root_comments(
    post_id_or_slug: str,
    db: DB,
    pagination: PaginationParams = Depends(get_pagination),
    include_unapproved: bool = Query(
        False, description="是否包含待审核/已拒绝（仅作者/管理员可见本人或全部）"
    ),
    password: str | None = Query(None, description="加密文章访问密码（与文章详情同名）"),
    x_post_password: str | None = Header(None, alias="X-Post-Password"),
    current_user: CurrentUserOptional = None,
):
    post = await CommentService.get_readable_post(
        db, post_id_or_slug, current_user, x_post_password or password
    )
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
    description=(
        "公开接口，按时间正序分页返回该根评论下的全部回复（回复只有一层，"
        "嵌套超过 1 层的回复在发表时即被拒绝）。评论不存在返回 404（业务码 COMMENT_NOT_FOUND）。"
    ),
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
    description=(
        "公开写入接口，支持对根评论的一层回复（parent_id 指向的评论必须属于同一篇文章）。"
        "携带 Bearer Token（登录用户发帖）时走 `core/csrf.py::require_csrf`（per-route 依赖，"
        "不是全局中间件）：带 `Origin` 头时必须命中白名单，否则 403（CSRF_CHECK_FAILED）；"
        "不带 Origin（curl / 服务端调用）不拦。另有一条 Cookie csrf_token 与 X-CSRF-Token "
        "的比对分支，**只在两个值同时存在时**才执行——本站从不发 cookie（登录态只在请求头里），"
        "所以现在没有浏览器会带上它们，这条分支不触发；`X-CSRF-Token` 因此**不是本接口的必需请求头**。"
        "匿名请求不带 Authorization 时整个校验跳过。"
        "文章不存在返回 404（POST_NOT_FOUND）。"
        "与读取口同口径：草稿/待审/定时未到的文章与未解锁的加密文章一律按 404 处理，"
        "不给草稿或加密文章写评论。"
        "文章级「允许评论」（编辑器 allow_comments）关闭时返回 403（COMMENT_POST_CLOSED），"
        "对游客与登录用户一致生效；站点级评论开关关闭时 403（COMMENTS_DISABLED）优先。"
        "常见失败：403 COMMENTS_DISABLED / COMMENT_POST_CLOSED / COMMENT_GUEST_NOT_ALLOWED；"
        "422 AUTHOR_NAME_REQUIRED / AUTHOR_NAME_TOO_SHORT / COMMENT_PARENT_WRONG_POST /"
        " NESTED_REPLY_TOO_DEEP / COMMENT_TOO_LONG；404 COMMENT_PARENT_NOT_FOUND；"
        "429 TOO_FREQUENT_COMMENT（Retry-After: 30，同文章同 IP 频控）。"
        "成功后触发插件钩子 comment.created。非幂等。"
    ),
    dependencies=[Depends(rate_limit_sensitive("post_comment")), Depends(require_csrf)],
)
async def create_comment(
    post_id_or_slug: str,
    data: CommentCreate,
    request: Request,
    db: DB,
    password: str | None = Query(None, description="加密文章访问密码"),
    x_post_password: str | None = Header(None, alias="X-Post-Password"),
    current_user: CurrentUserOptional = None,
):
    post = await CommentService.get_readable_post(
        db, post_id_or_slug, current_user, x_post_password or password
    )
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
        await bus.do_action("comment.created", resp, db=db)
        # 直接可见（免审核）的新评论会改变文章的 comments_count，而列表缓存读侧
        # 不重算该计数；待审核评论不影响公开计数，不必白清缓存。
        if resp.status == "approved":
            await invalidate_post_caches_by_ids(db, [resp.post_id])
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
    description=(
        "公开接口，无需登录。对评论 likes_count 简单自增，不按用户去重，非幂等。"
        "按 IP 限流 30 次/分钟（滑动窗口）。评论不存在返回 404（业务码 COMMENT_NOT_FOUND）。"
        "响应为裸 dict（success + 自增后的 likes_count 累计总数），无 data 信封。"
    ),
    dependencies=[Depends(_rate_limit_comment_like("comment_like"))],
    responses={200: {"model": CommentLikeResponse}},
)
async def like_comment(comment_id: int, db: DB):
    try:
        likes = await CommentService.like(db, comment_id)
        await db.commit()
    except ValueError as e:
        await db.rollback()
        raise _service_err_to_http(e) from e
    return {"success": True, "likes_count": likes}


@router.delete(
    "/comments/{comment_id}",
    response_model=BaseResponse,
    summary="删除自己的评论（作者本人，软删除进回收站）",
    description=(
        "需登录 + CSRF。只允许删自己那条：归属判据直接进 SELECT 的 WHERE"
        "（id 与 user_id 同一条谓词），所以「评论不存在」与「是别人的评论」回同一个 404"
        "（COMMENT_NOT_FOUND）——回 403 等于用连续自增的主键替旁人数「这条存在」，"
        "即可枚举全站评论 id。游客评论的 user_id 为 NULL，任何登录账号都匹配不上，"
        "因此游客内容只有管理员能删。与管理员单删（DELETE /api/admin/comments/{id}）同构："
        "先写回收站快照（30 天内可在「回收站」恢复，原文章已删除时不可恢复）再删原行，"
        "子回复由外键 ON DELETE SET NULL 提升为根评论、正文不丢。"
        "删除改变文章的可见评论集合，因此失效该文章的详情/列表缓存并通知前台清页面缓存"
        "（评论树由客户端拉取，但首页与列表页 SSR 的 HTML 里烘着评论计数，"
        "只清后端响应缓存在 Nitro 的 swr 窗口内访客仍看到旧数字）。"
        "成功后触发插件钩子 comment.deleted。"
    ),
    dependencies=[Depends(rate_limit_write("comment_delete")), Depends(require_csrf)],
)
async def delete_own_comment(
    comment_id: int,
    current_user: CurrentUser,
    db: DB,
):
    """作者本人删除自己的评论（先落回收站快照，与管理员单删同构）。"""
    comment = (
        await db.execute(
            select(Comment).where(
                Comment.id == comment_id,
                Comment.user_id == current_user.id,
            )
        )
    ).scalar_one_or_none()

    if comment is None:
        raise HTTPException(
            status_code=404,
            detail={
                "success": False,
                "message": "评论不存在",
                "error_code": "COMMENT_NOT_FOUND",
            },
        )

    # post_id 必须在 delete 之前取：对象一旦被删，属性访问会走已失效的行。
    affected_post_id = comment.post_id

    await snapshot_to_trash(
        db,
        resource_type="comment",
        resource_id=comment.id,
        data=comment_trash_payload(comment),
        deleted_by_id=current_user.id,
    )
    await db.delete(comment)
    await db.flush()
    await bus.do_action("comment.deleted", comment, current_user=current_user, db=db)
    await invalidate_post_caches_by_ids(db, [affected_post_id])
    purge_frontend_page_cache("作者删除评论")
    return BaseResponse(message="评论已移入回收站")


# ================= 管理员端点 =================
# 注意：评论列表(GET)、单条更新(PATCH)、单条删除(DELETE) 已统一由 admin.py 提供，
# 此处仅保留 Phase 3 已上线且仍被 React Admin 前端调用的 legacy 子动作：
#   POST /api/admin/comments/{id}/approve | reject | spam
#   POST /api/admin/comments/batch


@router.post(
    "/admin/comments/{comment_id}/approve",
    response_model=CommentResponse,
    summary="【管理员】批准评论（legacy 子动作，建议统一使用 PATCH /api/admin/comments/{id} status=approved）",
    description=(
        "需 CurrentStaff。将评论置为 approved 并公开展示；成功后触发插件钩子 comment.approved。"
        "评论不存在返回 404（业务码 COMMENT_NOT_FOUND）。保留原因：React Admin 前端仍在调用。"
        "审核会改变文章 comments_count，故顺带失效该文章的详情/列表缓存。"
    ),
)
async def admin_approve(_staff: CurrentStaff, comment_id: int, db: DB):
    try:
        r = await CommentService.admin_approve(db, comment_id)
        await db.commit()
        await bus.do_action("comment.approved", r, db=db)
        await invalidate_post_caches_by_ids(db, [r.post_id])
        # 评论正文现在烘在文章页 SSR HTML 里：只清后端响应缓存，前台 SWR 窗口内访客仍看不到这条。
        purge_frontend_page_cache("评论批准")
    except ValueError as e:
        await db.rollback()
        raise _service_err_to_http(e) from e
    return r


@router.post(
    "/admin/comments/{comment_id}/reject",
    response_model=CommentResponse,
    summary="【管理员】拒绝评论（legacy 子动作）",
    description=(
        "需 CurrentStaff。将评论置为 rejected，前台不再展示。"
        "评论不存在返回 404（业务码 COMMENT_NOT_FOUND）。"
        "下架会改变文章 comments_count，故顺带失效该文章的详情/列表缓存。"
    ),
)
async def admin_reject(_staff: CurrentStaff, comment_id: int, db: DB):
    try:
        r = await CommentService.admin_reject(db, comment_id)
        await db.commit()
        await invalidate_post_caches_by_ids(db, [r.post_id])
        # 下架后前台 HTML 里仍带着这条正文 = 审核动作在最坏窗口内不生效。
        purge_frontend_page_cache("评论拒绝")
    except ValueError as e:
        await db.rollback()
        raise _service_err_to_http(e) from e
    return r


@router.post(
    "/admin/comments/{comment_id}/spam",
    response_model=CommentResponse,
    summary="【管理员】标记为垃圾评论（legacy 子动作）",
    description=(
        "需 CurrentStaff。将评论置为 spam，前台不再展示；成功后触发插件钩子 comment.spam。"
        "评论不存在返回 404（业务码 COMMENT_NOT_FOUND）。"
        "判垃圾会改变文章 comments_count，故顺带失效该文章的详情/列表缓存。"
    ),
)
async def admin_spam(_staff: CurrentStaff, comment_id: int, db: DB):
    try:
        r = await CommentService.admin_spam(db, comment_id)
        await db.commit()
        await bus.do_action("comment.spam", r, db=db)
        await invalidate_post_caches_by_ids(db, [r.post_id])
        purge_frontend_page_cache("评论标记垃圾")
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
    description=(
        "需 CurrentStaff。请求体 {ids: [评论ID...], action: approve|reject|spam|delete}，"
        "逐条执行并返回处理计数；action 不在枚举内返回 422（业务码 INVALID_ACTION）。"
        "四种动作都会改变文章的可见评论集合，处理完顺带失效受影响文章的详情/列表缓存与前台页面缓存。"
        "delete 与单删同构：先进回收站（30 天可恢复），不是物理删除。"
    ),
)
async def admin_batch(staff: CurrentStaff, body: CommentBatchAction, db: DB):
    try:
        result = await CommentService.admin_batch(db, body.ids, body.action, deleted_by_id=staff.id)
        await db.commit()
    except ValueError as e:
        await db.rollback()
        raise _service_err_to_http(e) from e
    await invalidate_post_caches_by_ids(db, result.get("post_ids") or [])
    # 首页/列表页 SSR 的 HTML 里烘着评论计数，四个动作都会改变访客看到的可见评论集合。
    purge_frontend_page_cache("评论批量操作")
    return BaseResponse(success=True, message=f"已处理 {result.get('processed', 0)} 条")
