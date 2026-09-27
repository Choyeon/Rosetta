"""
后台管理 API

提供仪表盘统计、系统管理、用户管理等功能。

实现约定：
- 列表查询显式 `defer` 掉响应不用的大字段/敏感列（正文、密码哈希）。
- 关联用 selectinload / joinedload 批量预加载，禁止在异步会话上懒加载。
- `concurrent_query` 是顺序执行工具（AsyncSession 非并发安全），只用于把多条
  查询写在一处，没有并行收益，见 backend/core/concurrency.py。
- 业务逻辑走服务层，数据访问可走仓储层。
"""

import logging
import math
import re
from datetime import datetime
from typing import Literal

from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import String, case, cast, func, or_, select, update
from sqlalchemy.orm import defer, joinedload, selectinload

from backend.api._user_response_helper import build_user_detail_response, build_user_response
from backend.core.auth import DB, CurrentStaff, CurrentSuperUser
from backend.core.concurrency import concurrent_query
from backend.core.partial_update import apply_partial_update
from backend.core.plugin_bus import bus
from backend.models.blog import Category, Comment, Post
from backend.models.guestbook import GuestbookEntry
from backend.models.user import User
from backend.schemas import (
    AdminUserCreate,
    AdminUserUpdateFull,
    BaseResponse,
    PaginatedResponse,
    PasswordReset,
    UserDetailResponse,
    UserResponse,
)
from backend.schemas.admin_reads import (
    CommentParentRefDoc,
    CommentPostRefDoc,
    CommentUserRefDoc,
    UserTitleBadgeDoc,
)
from backend.services.post_cache import invalidate_post_caches_by_ids
from backend.services.user_service import get_user_service

logger = logging.getLogger(__name__)

router = APIRouter(tags=["后台管理"])


class AdminUserUpdate(BaseModel):
    """PATCH /admin/users/{user_id} 请求体

    与 schemas.AdminUserUpdateFull（PUT 全量更新）区分：本模型只承接状态位
    与 RBAC 角色四类字段，role 必须在此显式声明，否则 Pydantic 会静默丢弃
    前端发来的角色变更。
    """

    is_staff: bool | None = None
    is_active: bool | None = None
    is_banned: bool | None = None
    role: str | None = Field(
        None,
        description="RBAC 角色：super_admin/admin/editor/author/contributor/subscriber。为空时不变更。",
    )


class CommentAdminUpdate(BaseModel):
    """管理员更新评论请求体"""

    status: Literal["approved", "pending", "rejected", "spam"] | None = None
    active: bool | None = None
    content: str | None = Field(default=None, max_length=5000)


class CommentResponse(BaseModel):
    id: int
    post_id: int
    user: dict | None = None
    parent_id: int | None = None
    content: str
    active: bool = True
    created_at: datetime
    replies: list = []


# ═══════════════════════════════════════════════════════════════════════════
# 响应体文档模型（仅供 OpenAPI `responses={200: {"model": ...}}` 声明使用，
# 运行时不做序列化过滤——实际响应以 handler 返回字面量为准）
# ═══════════════════════════════════════════════════════════════════════════


class AdminUserStatusResponse(BaseModel):
    """PATCH /admin/users/{user_id} 的响应体（状态位/角色更新后的用户摘要）。"""

    id: int = Field(..., description="用户 ID")
    username: str = Field(..., description="用户名")
    email: str = Field(..., description="邮箱（管理员视图明文回显）")
    nickname: str | None = Field(None, description="昵称，未设置时为 null")
    avatar: str | None = Field(None, description="自定义头像 URL，未设置时为 null")
    is_active: bool = Field(..., description="账号是否激活")
    is_staff: bool = Field(..., description="是否管理员（变更 role 时按 RBAC 层级反向同步）")
    is_superuser: bool = Field(..., description="是否超级管理员（仅 role==super_admin 时为 true）")
    is_banned: bool = Field(..., description="是否封禁")
    role: str | None = Field(None, description="RBAC 角色名，历史数据可能为 null")


class CommentAdminItemDoc(BaseModel):
    """管理员评论列表（GET /admin/comments）单条评论的完整投影。

    字段逐一对齐 handler 手工拼装的 dict。PATCH 端点复用本模型但**不输出**
    ``title`` 头衔字段（见 :class:`CommentAdminUpdatedDoc`）。
    """

    id: int = Field(..., description="评论 ID")
    post_id: int = Field(..., description="所属文章 ID")
    user_id: int | None = Field(None, description="登录作者的用户 ID，匿名评论为 null")
    parent_id: int | None = Field(None, description="父评论 ID，顶级评论为 null")
    author_name: str = Field(
        ...,
        description="显示名：author_name → 关联用户 nickname → 兜底字符串「匿名用户」",
    )
    author_avatar: str = Field(
        ..., description="作者头像原始 URL（模型 avatar 列），无头像时为空串"
    )
    author_email: str | None = Field(None, description="匿名评论填写的邮箱，登录作者通常为 null")
    author_url: str | None = Field(None, description="匿名评论填写的个人站点 URL")
    author_website: str | None = Field(
        None, description="作者网站：评论 author_website → 关联用户 website → null"
    )
    qq: str | None = Field(None, description="QQ 号（头像识别用），未提供为 null")
    github: str | None = Field(None, description="GitHub 用户名/主页，未提供为 null")
    avatar_source: str | None = Field(
        None, description="头像来源标识（avatar_source 或 author_avatar_source），未设置为 null"
    )
    resolved_avatar_url: str | None = Field(
        None, description="经 avatar_resolver 统一解析后的最终头像 URL"
    )
    content: str = Field(..., description="评论正文")
    title: UserTitleBadgeDoc | None = Field(
        None, description="登录作者的头衔徽章（id/name/icon/color 投影），无头衔时为 null"
    )
    status: str = Field(
        ...,
        description="审核状态：status 列真实值；为空时按 active 兜底推导 approved/rejected",
    )
    active: bool = Field(..., description="是否公开展示（旧布尔列，与 status 双向同步）")
    is_pinned: bool = Field(..., description="是否置顶")
    likes_count: int = Field(..., description="点赞数")
    reply_total: int = Field(
        ..., description="直接回复数（按 parent_id 一条 GROUP BY 聚合，非模型列）"
    )
    created_at: str | None = Field(None, description="创建时间 ISO 8601 字符串，缺失为 null")
    updated_at: str | None = Field(None, description="更新时间 ISO 8601 字符串，缺失为 null")
    replies: list = Field(
        default_factory=list,
        description="嵌套回复列表：管理员列表端点恒为空数组（回复走 reply_total）",
    )
    post_ref: CommentPostRefDoc | None = Field(None, description="关联文章摘要，文章缺失为 null")
    parent_ref: CommentParentRefDoc | None = Field(None, description="父评论摘要，顶级评论为 null")
    user_ref: CommentUserRefDoc | None = Field(
        None, description="登录作者完整用户投影（UserResponse.model_dump），匿名评论为 null"
    )


class CommentAdminUpdatedDoc(CommentAdminItemDoc):
    """PATCH /admin/comments/{comment_id} 的响应体。

    与列表条目同一套手工投影，唯一差异是该端点**不输出** ``title`` 头衔字段，
    故在此显式覆写为恒 null，保持文档与实际返回一致。
    """

    title: None = Field(None, description="该端点不输出头衔（与列表端点的唯一字段差异），恒为 null")


class CommentAdminListResponse(BaseModel):
    """GET /admin/comments 的分页响应体（裸 dict，无 success/data 信封）。"""

    items: list[CommentAdminItemDoc] = Field(
        default_factory=list, description="当前页评论列表，按创建时间倒序"
    )
    total: int = Field(..., description="符合筛选条件的评论总数（不带 JOIN 的裸 count）")
    page: int = Field(..., description="当前页码，从 1 开始")
    page_size: int = Field(..., description="每页条数（1-100）")
    total_pages: int = Field(..., description="总页数；total 为 0 时是 0")


# ==================== 用户管理 API ====================


@router.get(
    "/users",
    response_model=PaginatedResponse,
    summary="用户列表（管理员）",
    description="获取所有用户列表，支持搜索和分页。",
)
async def admin_list_users(
    db: DB,
    current_user: CurrentSuperUser,
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    search: str | None = Query(None, description="搜索关键词"),
    is_staff: bool | None = Query(None, description="筛选管理员"),
    is_active: bool | None = Query(None, description="筛选激活状态"),
    is_banned: bool | None = Query(None, description="筛选封禁状态"),
):
    """
    管理员获取用户列表

    - `defer(User.password_hash)`：列表响应（UserDetailResponse）没有该字段，
      整行加载只是白白把每页最多 100 条 argon2 哈希读进内存。
    - 头衔用 selectinload；posts_count/comments_count 用两条 GROUP BY 批量取，
      避免逐行 N+1。计数与列表的顺序执行见 `concurrent_query`。
    """
    query = select(User).options(selectinload(User.title), defer(User.password_hash))

    if search:
        query = query.where(
            User.username.ilike(f"%{search}%")
            | User.nickname.ilike(f"%{search}%")
            | User.email.ilike(f"%{search}%")
            | User.qq.ilike(f"%{search}%")
            | User.github.ilike(f"%{search}%")
        )

    if is_staff is not None:
        query = query.where(User.is_staff == is_staff)

    if is_active is not None:
        query = query.where(User.is_active == is_active)

    if is_banned is not None:
        query = query.where(User.is_banned == is_banned)

    # 计数 + 列表（顺序两条查询）
    count_query = select(func.count()).select_from(query.subquery())

    total, result = await concurrent_query(
        db.scalar(count_query),
        db.execute(
            query.offset((page - 1) * page_size).limit(page_size).order_by(User.created_at.desc())
        ),
    )

    users = result.scalars().all()
    total = total or 0

    # 批量计算 posts_count / comments_count（避免 N+1）
    user_ids = [u.id for u in users]
    if user_ids:
        post_counts_q = (
            select(Post.author_id, func.count(Post.id).label("c"))
            .where(Post.author_id.in_(user_ids))
            .group_by(Post.author_id)
        )
        comment_counts_q = (
            select(Comment.user_id, func.count(Comment.id).label("c"))
            .where(Comment.user_id.in_(user_ids))
            .group_by(Comment.user_id)
        )
        pc_res, cc_res = await concurrent_query(
            db.execute(post_counts_q), db.execute(comment_counts_q)
        )
        post_map = {r.author_id: r.c for r in pc_res.all()}
        comment_map = {r.user_id: r.c for r in cc_res.all()}
    else:
        post_map = {}
        comment_map = {}

    items: list[UserDetailResponse] = []
    for u in users:
        d = build_user_detail_response(u)
        d.posts_count = int(post_map.get(u.id, 0))
        d.comments_count = int(comment_map.get(u.id, 0))
        items.append(d)

    return PaginatedResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=math.ceil(total / page_size) if total > 0 else 0,
    )


@router.post(
    "/users",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="创建用户（管理员）",
    description="管理员创建新用户。",
)
async def admin_create_user(
    data: AdminUserCreate,
    db: DB,
    current_user: CurrentSuperUser,
):
    """管理员创建用户"""
    service = await get_user_service(db)
    try:
        result = await service.register(
            username=data.username,
            email=data.email,
            password=data.password,
            nickname=data.nickname,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )

    user = result["user"]
    user.is_staff = data.is_staff
    user.is_active = data.is_active

    # RBAC：若显式传入 role，则与旧布尔字段保持一致；否则由布尔派生
    from backend.core.rbac import (
        ALL_ROLES,
        get_role_level,
        normalize_role,
        role_from_flags,
    )

    if data.role is not None:
        role = normalize_role(data.role)
        if role not in ALL_ROLES:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"非法角色：{data.role}",
            )
        if get_role_level(current_user.role) < get_role_level(role):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="无权分配高于自身层级的角色",
            )
        user.role = role
        # 同步旧布尔字段，保持向后兼容
        user.is_superuser = role == "super_admin"
        user.is_staff = get_role_level(role) >= get_role_level("admin")
    else:
        # 未传 role 时由布尔派生，保持旧行为
        user.role = role_from_flags(user.is_staff, user.is_superuser)

    await db.flush()
    await db.refresh(user)

    return build_user_response(user)


@router.get(
    "/users/{user_id}",
    response_model=UserDetailResponse,
    summary="获取用户详情（管理员）",
    description="管理员获取用户详细信息。",
)
async def admin_get_user(
    user_id: int,
    db: DB,
    current_user: CurrentSuperUser,
):
    """管理员获取用户详情"""
    result = await db.execute(
        select(User).options(selectinload(User.title)).where(User.id == user_id)
    )
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="用户不存在",
        )

    from backend.core.cache import cache as _cache
    from backend.models.blog import Comment as _Comment
    from backend.models.blog import Post as _Post

    # —— 性能优化：文章数 / 评论数 按用户维度缓存 30 秒 ——
    # 管理员"刷一下编辑页"这类高频场景下，避免每次都跑两次 COUNT(*)。
    # 注意：COUNT(*) 在 SQLAlchemy 里返回 int | None，统一转 int 避免下游 None 比较。
    cache_key_pc = f"admin:user:{user_id}:posts_count"
    cache_key_cc = f"admin:user:{user_id}:comments_count"

    cached_pc: int | None = await _cache.get(cache_key_pc)
    cached_cc: int | None = await _cache.get(cache_key_cc)

    if cached_pc is not None and cached_cc is not None:
        pc: int = int(cached_pc)
        cc: int = int(cached_cc)
    else:
        raw_pc, raw_cc = await concurrent_query(
            db.scalar(select(func.count(_Post.id)).where(_Post.author_id == user_id)),
            db.scalar(select(func.count(_Comment.id)).where(_Comment.user_id == user_id)),
        )
        pc = int(raw_pc or 0)
        cc = int(raw_cc or 0)
        # 回填缓存：两项各自 best-effort，一项写失败不能连带跳过另一项；
        # 缓存层（Memory/Redis backend）内部已吞掉连接异常并 logger.error，
        # 这里只可能吃到 import 失败，按纯噪声收窄并留痕。
        for cache_key_item, value_item in ((cache_key_pc, pc), (cache_key_cc, cc)):
            try:
                await _cache.set(cache_key_item, value_item, ttl=30)
            except ImportError as exc:
                logger.warning(f"[admin] 用户计数缓存不可用: {exc}")

    d = build_user_detail_response(user)
    d.posts_count = pc
    d.comments_count = cc
    return d


@router.put(
    "/users/{user_id}",
    response_model=UserDetailResponse,
    summary="更新用户（管理员）",
    description="管理员更新用户信息。",
)
async def admin_update_user_full(
    user_id: int,
    data: AdminUserUpdateFull,
    current_user: CurrentSuperUser,
    db: DB,
):
    """管理员完整更新用户信息"""
    from backend.core.rbac import get_role_level

    if current_user.id == user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="不能修改自己的信息，请使用个人设置",
        )

    result = await db.execute(
        select(User)
        .where(User.id == user_id)
        .options(
            selectinload(User.title),
            selectinload(User.preferences),
        )
    )
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="用户不存在",
        )

    # 仅禁止修改「自己」；允许超级管理员修改其他用户（含其他超级管理员），
    # 以支撑单管理员/个人博客场景下正常的账号资料维护。
    if (
        user.is_superuser
        and current_user.id != user_id
        and get_role_level(current_user.role) < get_role_level("super_admin")
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="无权修改超级管理员",
        )

    if data.username and data.username != user.username:
        existing = await db.execute(
            select(User).where(User.username == data.username, User.id != user_id)
        )
        if existing.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="用户名已存在",
            )

    if data.email and data.email != user.email:
        existing = await db.execute(
            select(User).where(User.email == data.email, User.id != user_id)
        )
        if existing.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="邮箱已存在",
            )

    update_data = data.model_dump(exclude_unset=True)

    # RBAC：角色变更需单独校验（actor 层级 >= target 层级），并同步旧布尔字段
    role_value = update_data.pop("role", None)
    if role_value is not None:
        from backend.core.rbac import (
            ALL_ROLES,
            get_role_level,
            normalize_role,
        )

        new_role = normalize_role(role_value)
        if new_role not in ALL_ROLES:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"非法角色：{role_value}",
            )
        if get_role_level(current_user.role) < get_role_level(new_role):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="无权分配高于自身层级的角色",
            )
        update_data["role"] = new_role

    apply_partial_update(user, update_data)

    # 若本次设置了 role，反向同步 is_staff/is_superuser 保持向后兼容
    if role_value is not None:
        user.is_superuser = user.role == "super_admin"
        user.is_staff = get_role_level(user.role) >= get_role_level("admin")

    await db.flush()
    await db.commit()

    # 重新加载用户对象（使用 populate_existing），避免 flush 后属性 expire 导致的 MissingGreenlet
    result = await db.execute(
        select(User)
        .where(User.id == user_id)
        .options(
            selectinload(User.title),
            selectinload(User.preferences),
        )
        .execution_options(populate_existing=True)
    )
    user_refreshed = result.scalar_one()

    return build_user_detail_response(user_refreshed)


@router.post(
    "/users/{user_id}/reset-password",
    response_model=BaseResponse,
    summary="重置用户密码（管理员）",
    description="管理员重置用户密码。",
)
async def admin_reset_password(
    user_id: int,
    data: PasswordReset,
    current_user: CurrentSuperUser,
    db: DB,
):
    """管理员重置用户密码"""
    if current_user.id == user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="不能重置自己的密码，请使用修改密码功能",
        )

    service = await get_user_service(db)
    user = await service.get_user_by_id(user_id)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="用户不存在",
        )

    if user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="不能重置超级管理员的密码",
        )

    await service.update_profile(user_id, {"password": data.new_password})
    return BaseResponse(message="密码已重置")


@router.delete(
    "/users/{user_id}",
    response_model=BaseResponse,
    summary="删除用户（管理员）",
    description=(
        "需 CurrentSuperUser。软删除：只封禁 + 停用，用户行保留。"
        "副作用是把该用户的可空外键引用置空——评论与留言板变匿名；"
        "`Post.author_id` 为 NOT NULL，文章继续归属原作者（不做处理）。"
        "不能删除自己或超级管理员，均返回 4xx。"
    ),
)
async def admin_delete_user(
    user_id: int,
    current_user: CurrentSuperUser,
    db: DB,
):
    """管理员删除用户"""
    if current_user.id == user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="不能删除自己",
        )

    service = await get_user_service(db)
    user = await service.get_user_by_id(user_id)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="用户不存在",
        )

    if user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="不能删除超级管理员",
        )

    # Bug#X3：删除用户（软/硬删除）前，先把其关联的评论 user_id 置空，
    # 避免评论被 CASCADE 删除 或 仍指向已删除用户造成引用脏数据。
    await db.execute(update(Comment).where(Comment.user_id == user_id).values(user_id=None))

    # 清理留言板引用（user_id 可为空 -> 变成匿名留言）。这里不得吞异常：
    # 清理失败却照样返回"用户已删除"，脏引用只能事后人工发现。
    await db.execute(
        update(GuestbookEntry).where(GuestbookEntry.user_id == user_id).values(user_id=None)
    )
    # Post.author_id 是 NOT NULL + ondelete=CASCADE，无法置空；本接口只做
    # 封禁+停用（用户行仍在），文章继续归属原作者，因此这里不动文章。

    await service.ban_user(user_id)
    await service.deactivate_user(user_id)
    return BaseResponse(message="用户已删除")


@router.post(
    "/users/{user_id}/activate",
    response_model=BaseResponse,
    summary="激活用户（管理员）",
    description="管理员激活已禁用的用户。",
)
async def admin_activate_user(
    user_id: int,
    current_user: CurrentSuperUser,
    db: DB,
):
    """管理员激活用户"""
    service = await get_user_service(db)
    user = await service.get_user_by_id(user_id)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="用户不存在",
        )

    await service.unban_user(user_id)
    await service.activate_user(user_id)
    return BaseResponse(message="用户已激活")


@router.post(
    "/users/{user_id}/ban",
    response_model=BaseResponse,
    summary="封禁用户（管理员）",
    description="管理员封禁用户。",
)
async def admin_ban_user(
    user_id: int,
    current_user: CurrentSuperUser,
    db: DB,
):
    """管理员封禁用户"""
    if current_user.id == user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="不能封禁自己",
        )

    service = await get_user_service(db)
    user = await service.get_user_by_id(user_id)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="用户不存在",
        )

    if user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="不能封禁超级管理员",
        )

    await service.ban_user(user_id)
    return BaseResponse(message="用户已封禁")


@router.post(
    "/users/{user_id}/unban",
    response_model=BaseResponse,
    summary="解封用户（管理员）",
    description="管理员解封用户。",
)
async def admin_unban_user(
    user_id: int,
    current_user: CurrentSuperUser,
    db: DB,
):
    """管理员解封用户"""
    service = await get_user_service(db)
    user = await service.get_user_by_id(user_id)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="用户不存在",
        )

    await service.unban_user(user_id)
    return BaseResponse(message="用户已解封")


# ==================== 统计 API ====================
# （Task 8 后，仪表盘统计 API 已迁移到 backend/api/stats.py 中的 GET /stats 端点，
#  包括 timeseries / top_articles / active_commenters / system_health / summary。
#  此处删除旧的 /stats /view-trends /category-stats 避免路由冲突。）


@router.patch(
    "/users/{user_id}",
    summary="部分更新用户（管理员）",
    description=(
        "仅更新提供的字段：is_staff/is_active/is_banned 状态位与 RBAC role。"
        "需超级管理员（CurrentSuperUser）；不能改自己（400）、目标不存在（404）、"
        "不能改超级管理员（403）、角色非法（400）或高于自身层级（403）。"
        "变更 role 后会反向同步 is_superuser/is_staff 布尔位，"
        "响应回显更新后的用户状态摘要。"
    ),
    responses={200: {"model": AdminUserStatusResponse}},
)
async def admin_update_user(
    user_id: int,
    data: AdminUserUpdate,
    current_user: CurrentSuperUser,
    db: DB,
):
    """管理员更新用户状态/角色

    注意：service.update_profile 的白名单只包含资料字段，is_staff/is_active/
    is_banned/role 会被其静默过滤，因此权限类变更必须在本处直接落到模型上，
    校验逻辑与 PUT 全量更新端点（admin_update_user_full）保持一致。
    """
    from backend.core.rbac import (
        ALL_ROLES,
        get_role_level,
        normalize_role,
    )

    if current_user.id == user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="不能修改自己的状态",
        )

    service = await get_user_service(db)
    user = await service.get_user_by_id(user_id)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="用户不存在",
        )

    if user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="不能修改超级管理员",
        )

    update_dict = data.model_dump(exclude_unset=True)

    # RBAC：角色需规范化 + 层级校验（actor 层级 >= 新角色层级）
    role_value = update_dict.pop("role", None)
    if role_value is not None:
        new_role = normalize_role(role_value)
        if new_role not in ALL_ROLES:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"非法角色：{role_value}",
            )
        if get_role_level(current_user.role) < get_role_level(new_role):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="无权分配高于自身层级的角色",
            )
        update_dict["role"] = new_role

    apply_partial_update(user, update_dict)

    # 变更 role 后反向同步旧布尔字段，保持向后兼容（与 PUT 端点一致）
    if role_value is not None:
        user.is_superuser = user.role == "super_admin"
        user.is_staff = get_role_level(user.role) >= get_role_level("admin")

    await db.flush()
    await db.commit()
    await db.refresh(user)

    return {
        "id": user.id,
        "username": user.username,
        "email": user.email,
        "nickname": user.nickname,
        "avatar": user.avatar,
        "is_active": user.is_active,
        "is_staff": user.is_staff,
        "is_superuser": user.is_superuser,
        "is_banned": user.is_banned,
        "role": user.role,
    }


@router.get(
    "/comments",
    summary="评论列表（管理员）",
    description=(
        "获取所有评论，支持按状态、文章、作者筛选和分页。需 CurrentStaff。"
        "响应为裸分页 dict（items/total/page/page_size/total_pages，无 success/data 信封）；"
        "items 内每条评论是服务端手工拼装的投影：含 resolved_avatar_url、title 头衔徽章、"
        "post_ref/parent_ref/user_ref 摘要与 reply_total 聚合计数，replies 恒为空数组。"
    ),
    responses={200: {"model": CommentAdminListResponse}},
)
async def admin_list_comments(
    db: DB,
    current_user: CurrentStaff,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: str | None = Query(None, description="pending/approved/rejected/spam"),
    keyword: str | None = Query(None, description="关键词：内容/昵称/邮箱/IP"),
):
    """
    管理员获取所有评论

    查询形状说明（三处都是踩过的坑）：
    - `Comment.post` 只用来出 `post_ref`（id/slug/title），必须把正文、加密正文、
      meta 三列 `defer` 掉，否则每页最多 100 条评论会连带 JOIN 出 100 份整篇 Markdown。
    - `Comment.user` / 父评论的作者 `defer(User.password_hash)`：响应里没有该字段，
      没必要把 argon2 哈希批量搬进内存。
    - 父评论的作者也一并预加载：`parent_ref` 在父评论 `author_name` 为空时会读
      `p.user.nickname`，那一列没加载就是异步会话上的懒加载 → MissingGreenlet。
    - 计数用不带 JOIN 的裸 `count(*) FROM comments`：先前它复用列表语句的 subquery，
      等于为了数行数把三张表 JOIN 一遍。
    """
    from backend.api._user_response_helper import build_user_response
    from backend.services._avatar_helpers import resolved_for_comment

    conditions = []

    # 状态过滤：旧 active 字段 → approved=active=True；pending/rejected/spam 由 status 字段决定
    if status:
        if status == "approved":
            conditions.append(Comment.active == True)  # noqa: E712
        elif status == "pending":
            conditions.append(Comment.status == "pending")
        elif status == "rejected":
            conditions.append(Comment.status == "rejected")
        elif status == "spam":
            conditions.append(Comment.status == "spam")

    if keyword:
        kw = f"%{keyword}%"
        conditions.append(
            or_(
                Comment.content.ilike(kw),
                (Comment.author_name or "").ilike(kw),
                (Comment.author_email or "").ilike(kw),
                (Comment.author_ip or "").ilike(kw),
                (Comment.qq or "").ilike(kw),
                (Comment.github or "").ilike(kw),
            )
        )

    base_q = select(Comment).options(
        # defer 必须写在 selectinload 之前：selectinload 会把生成链的路径推进到
        # User.title，之后再 defer(User.password_hash) 会报 "does not link from" 。
        joinedload(Comment.user).defer(User.password_hash).selectinload(User.title),
        joinedload(Comment.parent).joinedload(Comment.user).defer(User.password_hash),
        joinedload(Comment.post)
        .defer(Post.content)
        .defer(Post.encrypted_content)
        .defer(Post.meta_fields)
        .defer(Post.password),
    )
    if conditions:
        base_q = base_q.where(*conditions)

    count_q = select(func.count(Comment.id))
    if conditions:
        count_q = count_q.where(*conditions)
    offset = (page - 1) * page_size

    total, result = await concurrent_query(
        db.scalar(count_q),
        db.execute(base_q.order_by(Comment.created_at.desc()).offset(offset).limit(page_size)),
    )
    total = total or 0
    comments = result.scalars().all()

    # reply_total 不是 Comment 模型列（模型只有自引用 parent_id），
    # 必须用一条聚合查询批量统计每条根评论的直接回复数，避免逐行 COUNT 的 N+1。
    comment_ids = [c.id for c in comments]
    reply_count_map: dict[int, int] = {}
    if comment_ids:
        reply_rows = await db.execute(
            select(Comment.parent_id, func.count(Comment.id))
            .where(Comment.parent_id.in_(comment_ids))
            .group_by(Comment.parent_id)
        )
        reply_count_map = {int(pid): int(total) for pid, total in reply_rows.all()}

    items_dicts = []
    for c in comments:
        user_data = None
        if c.user:
            user_data = build_user_response(c.user).model_dump()
        resolved = resolved_for_comment(c)
        # 关联文章摘要
        post_ref = None
        if getattr(c, "post", None) is not None:
            post_ref = {
                "id": c.post.id,
                "slug": getattr(c.post, "slug", None),
                "title": (
                    c.post.title.get("zh")
                    if isinstance(c.post.title, dict)
                    else str(c.post.title or "")
                ),
            }
        parent_ref = None
        if getattr(c, "parent", None) is not None:
            p = c.parent
            parent_ref = {
                "id": p.id,
                "nickname": getattr(p, "author_name", None)
                or (getattr(p.user, "nickname", None) if getattr(p, "user", None) else None),
            }
        # 直接构造成普通 dict：完全绕开 CommentResponse/PaginatedResponse 的
        # Generic[T] + from_attributes 的链式重新序列化问题
        title_data = None
        if c.user and c.user.title:
            title_data = {
                "id": c.user.title.id,
                "name": c.user.title.name,
                "icon": c.user.title.icon,
                "color": c.user.title.color,
            }
        elif c.author_name and not c.user:
            # 匿名评论用户：检查是否有上传的头衔（通常没有，但预留扩展）
            pass

        items_dicts.append(
            {
                "id": c.id,
                "post_id": c.post_id,
                "user_id": c.user_id,
                "parent_id": c.parent_id,
                "author_name": c.author_name or (c.user.nickname if c.user else "匿名用户"),
                "author_avatar": (
                    getattr(c, "avatar", None) or (c.user.avatar if c.user else "") or ""
                ),
                "author_email": getattr(c, "author_email", None),
                "author_url": getattr(c, "author_url", None),
                "author_website": c.author_website or (c.user.website if c.user else None),
                "qq": getattr(c, "qq", None),
                "github": getattr(c, "github", None),
                "avatar_source": getattr(c, "avatar_source", None)
                or getattr(c, "author_avatar_source", None),
                "resolved_avatar_url": resolved,
                "content": c.content,
                "title": title_data,
                # 11-Bug#1：直接取 c.status 的真实值，不再基于 active 坍缩
                "status": c.status or ("approved" if c.active else "rejected"),
                "active": bool(c.active),
                "is_pinned": bool(getattr(c, "is_pinned", False)),
                "likes_count": int(getattr(c, "likes_count", 0)),
                "reply_total": int(reply_count_map.get(c.id, 0)),
                "created_at": c.created_at.isoformat() if c.created_at else None,
                "updated_at": c.updated_at.isoformat() if getattr(c, "updated_at", None) else None,
                "replies": [],
                # 11-Bug#2：确保 parent_ref / post_ref / user_ref 都是可序列化的 dict
                "post_ref": post_ref,
                "parent_ref": parent_ref,
                "user_ref": user_data,
            }
        )

    # 返回普通 dict：FastAPI 会直接 JSON 序列化，不再触发 Pydantic 二次 model_validate
    return {
        "items": items_dicts,
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": math.ceil(total / page_size) if total > 0 else 0,
    }


@router.patch(
    "/comments/{comment_id}",
    summary="更新评论（管理员）",
    description=(
        "修改评论内容、状态（approved/rejected/spam）等。"
        "status/active 变更会改变文章的 comments_count，故顺带失效该文章的详情/列表缓存。"
        "响应为手工拼装、与列表端点同构的评论投影 dict（不再经 CommentResponse 二次校验），"
        "但比列表条目少一个 title 头衔字段；replies 恒为空数组，reply_total 实时统计。"
    ),
    responses={200: {"model": CommentAdminUpdatedDoc}},
)
async def admin_update_comment(
    comment_id: int,
    data: CommentAdminUpdate,
    current_user: CurrentStaff,
    db: DB,
):
    """管理员更新评论：支持 status / active / content 字段双向同步

    - status / active 任一方变更都会自动同步另一方：
      * approved → active=True
      * pending/rejected/spam → active=False
    - 返回严格对齐 CommentResponse schema（不额外输出 user/active 不存在于 schema 的字段）
    """
    from backend.api._user_response_helper import build_user_response
    from backend.services._avatar_helpers import resolved_for_comment

    result = await db.execute(
        select(Comment)
        .options(
            selectinload(Comment.user),
            selectinload(Comment.post),
            # 父评论的作者也要预加载：下面 parent_ref 会读 p.user.nickname，
            # 未加载时在异步会话上触发懒加载直接 MissingGreenlet（500）。
            selectinload(Comment.parent).selectinload(Comment.user),
        )
        .where(Comment.id == comment_id)
    )
    comment = result.scalar_one_or_none()
    if not comment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="评论不存在",
        )

    # --- 1. 应用字段更新（status ↔ active 双向同步） ---
    new_status = data.status
    new_active = data.active
    new_content = data.content

    if new_status is not None:
        comment.status = new_status
        # 以 status 为准同步 active
        comment.active = new_status == "approved"
    elif new_active is not None:
        comment.active = bool(new_active)
        # 以 active 为锚反向推导 status（仅当原 status 无意义时覆写）
        if comment.active and comment.status in ("rejected", "spam", "pending"):
            comment.status = "approved"
        elif not comment.active and comment.status == "approved":
            comment.status = "rejected"

    if new_content is not None:
        comment.content = new_content

    await db.flush()
    await db.refresh(comment)

    if comment.status == "approved":
        await bus.do_action("comment.approved", comment, current_user=current_user, db=db)

    # status/active 一改动就改变文章的可见评论数。列表缓存读侧不重算 comments_count，
    # 不清就是最长 TTL 的旧计数；详情键一并失效保持两层快照一致。
    await invalidate_post_caches_by_ids(db, [comment.post_id])

    # --- 2. 组装严格对齐 CommentResponse schema 的返回 ---
    user_data = None
    if comment.user:
        user_data = build_user_response(comment.user).model_dump()

    post_ref = None
    if getattr(comment, "post", None) is not None:
        p = comment.post
        post_ref = {
            "id": p.id,
            "slug": getattr(p, "slug", None),
            "title": (p.title.get("zh") if isinstance(p.title, dict) else str(p.title or "")),
        }

    parent_ref = None
    if getattr(comment, "parent", None) is not None:
        p = comment.parent
        parent_ref = {
            "id": p.id,
            "nickname": getattr(p, "author_name", None)
            or (getattr(p.user, "nickname", None) if getattr(p, "user", None) else None),
        }

    resolved = resolved_for_comment(comment)

    # reply_total 非模型列：按自引用 parent_id 实时统计直接回复数
    reply_total = await db.scalar(
        select(func.count(Comment.id)).where(Comment.parent_id == comment.id)
    )

    # PATCH 返回也用普通 dict：避免 CommentResponse from_attributes 造成字段缺失/变形
    return {
        "id": comment.id,
        "post_id": comment.post_id,
        "user_id": comment.user_id,
        "parent_id": comment.parent_id,
        "author_name": comment.author_name
        or (comment.user.nickname if comment.user else "匿名用户"),
        "author_avatar": (
            getattr(comment, "avatar", None) or (comment.user.avatar if comment.user else "") or ""
        ),
        "author_email": getattr(comment, "author_email", None),
        "author_url": getattr(comment, "author_url", None),
        "author_website": comment.author_website
        or (comment.user.website if comment.user else None),
        "qq": getattr(comment, "qq", None),
        "github": getattr(comment, "github", None),
        "avatar_source": getattr(comment, "avatar_source", None)
        or getattr(comment, "author_avatar_source", None),
        "resolved_avatar_url": resolved,
        "content": comment.content,
        "status": comment.status or ("approved" if comment.active else "rejected"),
        "active": bool(comment.active),
        "is_pinned": bool(getattr(comment, "is_pinned", False)),
        "likes_count": int(getattr(comment, "likes_count", 0)),
        "reply_total": int(reply_total or 0),
        "created_at": comment.created_at.isoformat() if comment.created_at else None,
        "updated_at": comment.updated_at.isoformat()
        if getattr(comment, "updated_at", None)
        else None,
        "replies": [],
        "post_ref": post_ref,
        "parent_ref": parent_ref,
        "user_ref": user_data,
    }


@router.delete(
    "/comments/{comment_id}",
    response_model=BaseResponse,
    summary="删除评论（管理员）",
    description=(
        "永久删除指定评论及其子回复。删除会改变文章的 comments_count，"
        "因此顺带失效该文章的详情/列表缓存。"
    ),
)
async def admin_delete_comment(
    comment_id: int,
    current_user: CurrentStaff,
    db: DB,
):
    """管理员删除评论"""
    result = await db.execute(select(Comment).where(Comment.id == comment_id))
    comment = result.scalar_one_or_none()

    if not comment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="评论不存在",
        )

    # post_id 必须在 delete 之前取：对象一旦被删，属性访问会走已失效的行。
    affected_post_id = comment.post_id

    await db.delete(comment)
    await db.flush()
    await bus.do_action("comment.deleted", comment, current_user=current_user, db=db)
    await invalidate_post_caches_by_ids(db, [affected_post_id])
    return BaseResponse(message="评论已删除")


# ==================== 系统工具 API ====================
#
# 这里曾挂着三个 HTTP 入口，现已移除（前端零调用，只有 smoke 测试打它们）：
# - POST /tools/mock-data：后台一键灌假数据。示例数据的正道是 CLI
#   `uv run python -m backend.scripts.mock_data`，挂在登录态 API 上等于给生产环境留了个
#   "污染真实站点"按钮，而且和仪表盘"绝不回填演示数据"的口径自相矛盾。
# - GET /tools/unused-images + POST /tools/clean-unused-images：清理"未引用"图片。
#   两者都有硬伤——引用集合只覆盖文章正文/封面 + 用户头像，站点设置里的 logo/favicon、
#   相册、主题 mods、独立页正文全没算，照着它的列表删文件会误删在用图片；
#   而且删除时把相对 media_dir 的路径当相对 cwd 的 `Path` 用，实际既删不掉目标、
#   又可能命中 cwd 下的同名文件。要恢复这个能力，请先补全引用扫描 + 绝对路径解析，
#   并改成"勾选后按显式清单删除 + 二次确认"。


_MARKDOWN_NOISE = re.compile(r"[#*`>\[\]()!_\-|]+")


def _missing_i18n_json(column):
    """JSON 多语言列的"没有内容"判定（SQL 表达式）。

    SQLAlchemy 的 JSON 默认 `none_as_null=False`：Python None 落库不是 SQL NULL，
    而是 JSON null（SQLite 存成文本 `null`，PG 存成 JSONB null），所以
    `column.is_(None)` 永远匹配不到——旧代码只用它判"缺摘要"，结果是
    search-stats 的 posts_without_excerpt 恒为 0，optimize-search 也永远扫不到
    需要补摘要的文章。这里把 SQL NULL / 空串 / JSON null 三种形态一起兜住。
    """
    return or_(column.is_(None), column == "", cast(column, String) == "null")


def _pick_localized_text(value: dict | str | None) -> str:
    """从多语言字段里挑一条作为生成源：优先 zh，其次 en，再次任意非空。"""
    if isinstance(value, str):
        return value.strip()
    if not isinstance(value, dict):
        return ""
    for lang in ("zh", "en"):
        text = value.get(lang)
        if isinstance(text, str) and text.strip():
            return text.strip()
    for text in value.values():
        if isinstance(text, str) and text.strip():
            return text.strip()
    return ""


def _plain_excerpt(markdown_text: str, max_length: int = 200) -> str:
    """把 Markdown 正文压成纯文本摘要；没有有效内容时返回空串。"""
    plain = _MARKDOWN_NOISE.sub(" ", markdown_text)
    plain = re.sub(r"\s+", " ", plain).strip()
    return plain[:max_length]


class SearchRecommendation(BaseModel):
    """体检结论里的一条建议"""

    type: Literal["excerpt", "slug", "tags"]
    count: int
    message: str


class SearchStatsResponse(BaseModel):
    """GET /admin/tools/search-stats 响应"""

    total_posts: int
    total_categories: int
    posts_without_excerpt: int
    posts_without_slug: int
    posts_without_tags: int
    avg_slug_length: float
    avg_excerpt_length: float
    recommendations: list[SearchRecommendation]


class OptimizeSearchResponse(BaseModel):
    """POST /admin/tools/optimize-search 响应

    三个计数分开给：旧实现只有一个 `optimized_count`，把"补了 slug"和"补了摘要"
    混在一起，前端/运维看不出这次到底改了什么。
    """

    success: bool = True
    scanned_count: int
    slug_filled_count: int
    excerpt_filled_count: int
    message: str


@router.get(
    "/tools/search-stats",
    response_model=SearchStatsResponse,
    summary="检索字段体检",
    description="统计缺少摘要/标签的文章数与 slug、摘要平均长度，为「补全检索字段」提供依据。",
)
async def get_search_optimization_stats(
    current_user: CurrentStaff,
    db: DB,
):
    """文章检索字段完整度统计。

    这里没有"全文索引"概念可查（SQLite/PG 都是 LIKE 检索），口径是内容侧 SEO
    完整度。5 条聚合合并成 1 条 `FILTER (WHERE ...)` 条件计数 + 1 条分类计数，
    不再为每个数字单开一次往返。
    """
    no_excerpt = _missing_i18n_json(Post.excerpt)
    no_slug = (Post.slug == "") | (Post.slug.is_(None))
    stats = (
        await db.execute(
            select(
                func.count(Post.id).label("total_posts"),
                func.coalesce(func.count(Post.id).filter(no_excerpt), 0).label(
                    "posts_without_excerpt"
                ),
                func.coalesce(func.count(Post.id).filter(no_slug), 0).label("posts_without_slug"),
                func.coalesce(func.count(Post.id).filter(~Post.tags.any()), 0).label(
                    "posts_without_tags"
                ),
                func.coalesce(func.sum(func.char_length(Post.slug)), 0).label("total_slug_len"),
                # JSON 列要先转文本再取长度（PG 的 char_length(jsonb) 直接报错）；
                # 缺摘要的行记 0，免得 JSON null 的 4 个字符混进平均值。
                func.coalesce(
                    func.sum(
                        case(
                            (no_excerpt, 0),
                            else_=func.char_length(cast(Post.excerpt, String)),
                        )
                    ),
                    0,
                ).label("total_excerpt_len"),
            )
        )
    ).one()
    total_posts = stats.total_posts
    posts_without_excerpt = stats.posts_without_excerpt
    posts_without_tags = stats.posts_without_tags

    total_categories = await db.scalar(select(func.count()).select_from(Category)) or 0

    return {
        "total_posts": total_posts,
        "total_categories": total_categories,
        "posts_without_excerpt": posts_without_excerpt,
        "posts_without_slug": stats.posts_without_slug,
        "posts_without_tags": posts_without_tags,
        "avg_slug_length": round(stats.total_slug_len / total_posts, 2) if total_posts else 0,
        "avg_excerpt_length": (
            round(stats.total_excerpt_len / total_posts, 2) if total_posts else 0
        ),
        "recommendations": [
            rec
            for rec in (
                {
                    "type": "excerpt",
                    "count": posts_without_excerpt,
                    "message": f"有 {posts_without_excerpt} 篇文章缺少摘要",
                },
                {
                    "type": "slug",
                    "count": stats.posts_without_slug,
                    "message": f"有 {stats.posts_without_slug} 篇文章缺少 slug",
                },
                {
                    "type": "tags",
                    "count": posts_without_tags,
                    "message": f"有 {posts_without_tags} 篇文章未设置标签",
                },
            )
            # 只报真实存在的缺口：全量返回三条会让前端"字段完整"空态永远不可达，
            # 且在健康站点上渲染三行 "有 0 篇文章缺少 X" 的噪声。
            if rec["count"] > 0
        ],
    }


@router.post(
    "/tools/optimize-search",
    response_model=OptimizeSearchResponse,
    summary="补全检索字段",
    description=(
        "扫描缺少 slug 或摘要的文章，按标题生成唯一 slug、按各语言正文生成摘要。"
        "有实际改动时同步失效文章详情与列表缓存，避免 TTL 内继续吐出补字段前的旧正文。"
    ),
)
async def optimize_search(
    current_user: CurrentStaff,
    db: DB,
):
    """为缺字段的文章批量补 slug / 摘要。

    slug 生成复用建文流程同一个 `generate_slug`（中文转拼音 + 长度截断 + 空结果
    uuid 兜底），避免两处口径漂移。旧实现在这里自己重写了一遍 slugify：中文标题
    原样进 URL、空结果兜底取 ``id(text)``（CPython 内存地址，跨进程不稳定还会
    泄漏进公开 URL），而且完全不查重——`Post.slug` 是 unique 列，撞上已有 slug
    时异常要等到请求结尾 commit 才抛，get_db 回滚整个事务，接口却已经返回了
    "已优化 N 篇"，实际一个字都没写进去。

    查重直接查库：SQLAlchemy 的 autoflush 会把同批次待写入的 slug 一起看见，
    所以不需要额外的记账集合。扫描条件用 `_missing_i18n_json` 判"缺摘要"——
    JSON 列的 None 落库是 JSON null 而不是 SQL NULL，旧的 `is_(None)` 一条都扫不到。
    """
    from backend.api.blog import generate_slug
    from backend.core.cache import invalidate_cache, invalidate_post_detail_cache

    result = await db.execute(
        select(Post).where(
            (Post.slug == "") | (Post.slug.is_(None)) | _missing_i18n_json(Post.excerpt)
        )
    )
    posts = list(result.scalars().all())

    slug_filled = 0
    excerpt_filled = 0
    touched_slugs: set[str] = set()

    for post in posts:
        changed = False
        if not post.slug:
            title_text = _pick_localized_text(post.title)
            if title_text:
                base = generate_slug(title_text)
                candidate = base
                n = 2
                while await db.scalar(select(Post.id).where(Post.slug == candidate)):
                    candidate = f"{base}-{n}"
                    n += 1
                post.slug = candidate
                slug_filled += 1
                changed = True

        if not post.excerpt and post.content:
            # 逐语言生成：旧实现把中文正文同时塞进 zh 和 en，等于凭空造译文。
            excerpt: dict[str, str] = {}
            for lang, text in post.content.items():
                if isinstance(text, str):
                    plain = _plain_excerpt(text)
                    if plain:
                        excerpt[lang] = plain
            if excerpt:
                post.excerpt = excerpt
                excerpt_filled += 1
                changed = True

        if changed and post.slug:
            touched_slugs.add(post.slug)

    await db.flush()

    # 补 slug / 摘要会改动文章详情与列表：详情缓存 `post:{slug}:{lang}` 不在 "posts"
    # 前缀下，只调 invalidate_cache("posts") 命中不了它，TTL 内访客仍读到无摘要的旧正文。
    # 与单篇 update_post 的写侧口径保持一致，两个都清。
    if touched_slugs:
        await invalidate_post_detail_cache(*touched_slugs)
        await invalidate_cache("posts")

    return {
        "success": True,
        "scanned_count": len(posts),
        "slug_filled_count": slug_filled,
        "excerpt_filled_count": excerpt_filled,
        "message": f"扫描 {len(posts)} 篇：补 slug {slug_filled} 篇、补摘要 {excerpt_filled} 篇",
    }
