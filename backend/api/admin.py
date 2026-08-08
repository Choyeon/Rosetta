"""
后台管理 API

提供仪表盘统计、系统管理、用户管理等功能。

性能优化：
- 使用并发查询优化统计和列表
- 使用服务层封装业务逻辑
- 使用仓储层进行数据访问
- 使用 selectinload 预加载关联数据
"""

import math
from datetime import datetime

from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy import func, or_, select
from sqlalchemy.orm import joinedload, selectinload

from backend.api._user_response_helper import build_user_detail_response, build_user_response
from backend.core.auth import DB, CurrentStaff, CurrentSuperUser
from backend.core.concurrency import concurrent_query
from backend.models.blog import Category, Comment, Post
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
from backend.services.user_service import get_user_service

router = APIRouter(tags=["后台管理"])


class AdminUserUpdate(BaseModel):
    is_staff: bool | None = None
    is_active: bool | None = None
    is_banned: bool | None = None


class CommentResponse(BaseModel):
    id: int
    post_id: int
    user: dict | None = None
    parent_id: int | None = None
    content: str
    active: bool = True
    created_at: datetime
    replies: list = []


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

    性能优化：
    - 使用并发查询获取总数和列表
    - 使用 selectinload 预加载关联数据
    """
    query = select(User).options(selectinload(User.title))

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

    # 并发执行计数和列表查询
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
        from backend.models.blog import Comment as _Comment
        from backend.models.blog import Post as _Post

        post_counts_q = (
            select(_Post.author_id, func.count(_Post.id).label("c"))
            .where(_Post.author_id.in_(user_ids))
            .group_by(_Post.author_id)
        )
        comment_counts_q = (
            select(_Comment.user_id, func.count(_Comment.id).label("c"))
            .where(_Comment.user_id.in_(user_ids))
            .group_by(_Comment.user_id)
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
    await db.flush()

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

    from backend.models.blog import Comment as _Comment
    from backend.models.blog import Post as _Post

    pc, cc = await concurrent_query(
        db.scalar(select(func.count(_Post.id)).where(_Post.author_id == user_id)) or 0,
        db.scalar(select(func.count(_Comment.id)).where(_Comment.user_id == user_id)) or 0,
    )
    d = build_user_detail_response(user)
    d.posts_count = int(pc or 0)
    d.comments_count = int(cc or 0)
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

    if user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="不能修改超级管理员",
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
    for field, value in update_data.items():
        setattr(user, field, value)

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
    description="管理员删除用户（软删除）。",
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
    from sqlalchemy import update as _sa_update

    from backend.models.blog import Comment as BlogComment

    await db.execute(
        _sa_update(BlogComment)
        .where(BlogComment.user_id == user_id)
        .values(user_id=None)
    )

    # 同目录同层：清理 Guestbook / Post.author_id 等外键引用
    try:
        from backend.models.guestbook import GuestbookEntry  # type: ignore

        await db.execute(
            _sa_update(GuestbookEntry).where(GuestbookEntry.user_id == user_id).values(user_id=None)
        )
    except Exception:
        pass
    try:
        from backend.models.blog import Post as BlogPost

        await db.execute(
            _sa_update(BlogPost).where(BlogPost.author_id == user_id).values(author_id=None)
        )
    except Exception:
        pass

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


@router.patch("/users/{user_id}")
async def admin_update_user(
    user_id: int,
    data: AdminUserUpdate,
    current_user: CurrentSuperUser,
    db: DB,
):
    """管理员更新用户状态"""
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
    updated_user = await service.update_profile(user_id, update_dict)

    return {
        "id": updated_user.id,
        "username": updated_user.username,
        "email": updated_user.email,
        "nickname": updated_user.nickname,
        "avatar": updated_user.avatar,
        "is_active": updated_user.is_active,
        "is_staff": updated_user.is_staff,
        "is_superuser": updated_user.is_superuser,
        "is_banned": updated_user.is_banned,
    }


@router.get("/comments")
async def admin_list_comments(
    db: DB,
    current_user: CurrentStaff,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: str | None = Query(None, description="pending/approved/rejected/spam"),
    keyword: str | None = Query(None, description="关键词：内容/昵称/邮箱/IP"),
):
    """管理员获取所有评论"""
    from backend.api._user_response_helper import build_user_response
    from backend.services._avatar_helpers import resolved_for_comment

    base_q = select(Comment).options(
        joinedload(Comment.user),
        joinedload(Comment.post),
        joinedload(Comment.parent),
    )

    # 状态过滤：旧 active 字段 → approved=active=True；pending/rejected/spam 由 status 字段决定
    if status:
        if status == "approved":
            base_q = base_q.where(Comment.active == True)  # noqa: E712
        elif status == "pending":
            base_q = base_q.where(Comment.status == "pending")
        elif status == "rejected":
            base_q = base_q.where(Comment.status == "rejected")
        elif status == "spam":
            base_q = base_q.where(Comment.status == "spam")

    if keyword:
        kw = f"%{keyword}%"
        base_q = base_q.where(
            or_(
                Comment.content.ilike(kw),
                (Comment.author_name or "").ilike(kw),
                (Comment.author_email or "").ilike(kw),
                (Comment.author_ip or "").ilike(kw),
                (Comment.qq or "").ilike(kw),
                (Comment.github or "").ilike(kw),
            )
        )

    count_q = select(func.count()).select_from(base_q.subquery())
    offset = (page - 1) * page_size

    total, result = await concurrent_query(
        db.scalar(count_q),
        db.execute(
            base_q.order_by(Comment.created_at.desc())
            .offset(offset)
            .limit(page_size)
        ),
    )
    total = total or 0
    comments = result.scalars().all()

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
        items_dicts.append(
            {
                "id": c.id,
                "post_id": c.post_id,
                "user_id": c.user_id,
                "parent_id": c.parent_id,
                "author_name": c.author_name or (c.user.nickname if c.user else "匿名用户"),
                "author_avatar": (getattr(c, "avatar", None) or (c.user.avatar if c.user else "") or ""),
                "author_email": getattr(c, "author_email", None),
                "author_url": getattr(c, "author_url", None),
                "author_website": c.author_website or (c.user.website if c.user else None),
                "qq": getattr(c, "qq", None),
                "github": getattr(c, "github", None),
                "avatar_source": getattr(c, "avatar_source", None) or getattr(c, "author_avatar_source", None),
                "resolved_avatar_url": resolved,
                "content": c.content,
                # 11-Bug#1：直接取 c.status 的真实值，不再基于 active 坍缩
                "status": c.status or ("approved" if c.active else "rejected"),
                "active": bool(c.active),
                "is_pinned": bool(getattr(c, "is_pinned", False)),
                "likes_count": int(getattr(c, "likes_count", 0)),
                "reply_total": int(getattr(c, "reply_total", 0)),
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


@router.patch("/comments/{comment_id}")
async def admin_update_comment(
    comment_id: int,
    data: dict,
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
            selectinload(Comment.parent),
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
    new_status = data.get("status")
    new_active = data.get("active")
    new_content = data.get("content")

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
            "title": (
                p.title.get("zh")
                if isinstance(p.title, dict)
                else str(p.title or "")
            ),
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

    # PATCH 返回也用普通 dict：避免 CommentResponse from_attributes 造成字段缺失/变形
    return {
        "id": comment.id,
        "post_id": comment.post_id,
        "user_id": comment.user_id,
        "parent_id": comment.parent_id,
        "author_name": comment.author_name or (comment.user.nickname if comment.user else "匿名用户"),
        "author_avatar": (
            getattr(comment, "avatar", None) or (comment.user.avatar if comment.user else "") or ""
        ),
        "author_email": getattr(comment, "author_email", None),
        "author_url": getattr(comment, "author_url", None),
        "author_website": comment.author_website or (comment.user.website if comment.user else None),
        "qq": getattr(comment, "qq", None),
        "github": getattr(comment, "github", None),
        "avatar_source": getattr(comment, "avatar_source", None) or getattr(comment, "author_avatar_source", None),
        "resolved_avatar_url": resolved,
        "content": comment.content,
        "status": comment.status or ("approved" if comment.active else "rejected"),
        "active": bool(comment.active),
        "is_pinned": bool(getattr(comment, "is_pinned", False)),
        "likes_count": int(getattr(comment, "likes_count", 0)),
        "reply_total": int(getattr(comment, "reply_total", 0)),
        "created_at": comment.created_at.isoformat() if comment.created_at else None,
        "updated_at": comment.updated_at.isoformat() if getattr(comment, "updated_at", None) else None,
        "replies": [],
        "post_ref": post_ref,
        "parent_ref": parent_ref,
        "user_ref": user_data,
    }


@router.delete("/comments/{comment_id}")
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

    await db.delete(comment)
    return BaseResponse(message="评论已删除")


# ==================== 系统工具 API ====================


class MockDataRequest(BaseModel):
    posts_count: int = 20
    categories_count: int = 5
    tags_count: int = 10
    users_count: int = 5
    comments_count: int = 50
    reset: bool = False


@router.post("/tools/mock-data")
async def generate_mock_data(
    request: MockDataRequest,
    current_user: CurrentStaff,
    db: DB,
):
    """生成模拟数据"""
    from backend.scripts.mock_data import generate_all_mock_data

    result = await generate_all_mock_data(
        db=db,
        posts_count=request.posts_count,
        categories_count=request.categories_count,
        tags_count=request.tags_count,
        users_count=request.users_count,
        comments_count=request.comments_count,
        reset=request.reset,
    )

    return {
        "success": True,
        "message": "模拟数据生成成功",
        "data": result,
    }


@router.get("/tools/unused-images")
async def list_unused_images(
    current_user: CurrentStaff,
    db: DB,
):
    """扫描并列出未使用的图片"""
    from pathlib import Path

    media_dir = Path("media")
    if not media_dir.exists():
        return {"images": [], "total_size": 0}

    result = await db.execute(select(Post.cover_image, Post.content))
    posts = result.all()

    content_refs = set()
    for post in posts:
        if post.cover_image:
            content_refs.add(post.cover_image)
        if post.content:
            import re

            if isinstance(post.content, dict):
                for v in post.content.values():
                    if v:
                        content_refs.update(re.findall(r'/media/[^\s"\')]+', str(v)))
            else:
                content_refs.update(re.findall(r'/media/[^\s"\')]+', str(post.content)))

    from backend.models.user import User as UserModel

    result2 = await db.execute(select(UserModel.avatar))
    avatars = result2.all()
    for a in avatars:
        if a.avatar:
            content_refs.add(a.avatar)

    image_extensions = {".jpg", ".jpeg", ".png", ".gif", ".webp", ".svg", ".bmp"}
    unused_images = []
    total_size = 0

    for f in media_dir.rglob("*"):
        if f.is_file() and f.suffix.lower() in image_extensions:
            file_url = f"/{f.as_posix()}"
            rel_path = f.relative_to(Path.cwd()).as_posix()
            if file_url not in content_refs and f"/{rel_path}" not in content_refs:
                size = f.stat().st_size
                total_size += size
                unused_images.append(
                    {
                        "path": rel_path,
                        "url": file_url,
                        "name": f.name,
                        "size": size,
                        "size_human": f"{size / 1024:.1f} KB"
                        if size < 1024 * 1024
                        else f"{size / 1024 / 1024:.2f} MB",
                    }
                )

    unused_images.sort(key=lambda x: x["size"], reverse=True)
    return {
        "images": unused_images,
        "total_size": total_size,
        "total_size_human": f"{total_size / 1024 / 1024:.2f} MB",
    }


@router.post("/tools/clean-unused-images")
async def clean_unused_images(
    current_user: CurrentStaff,
    db: DB,
):
    """清理未使用的图片"""
    result_data = await list_unused_images(current_user, db)
    images = result_data["images"]

    deleted = []
    errors = []
    for img in images:
        try:
            p = Path(img["path"])
            if p.exists():
                p.unlink()
                deleted.append(img["path"])
        except Exception as e:
            errors.append({"path": img["path"], "error": str(e)})

    return {
        "success": True,
        "deleted_count": len(deleted),
        "freed_size": result_data["total_size"],
        "freed_size_human": result_data["total_size_human"],
        "deleted": deleted,
        "errors": errors,
    }


@router.get("/tools/search-stats")
async def get_search_optimization_stats(
    current_user: CurrentStaff,
    db: DB,
):
    """获取检索优化统计"""
    total_posts = await db.scalar(select(func.count()).select_from(Post)) or 0

    result = await db.execute(
        select(
            func.coalesce(func.sum(func.char_length(Post.slug)), 0).label("total_slug_len"),
            func.coalesce(func.sum(func.char_length(func.coalesce(Post.excerpt, ""))), 0).label(
                "total_excerpt_len"
            ),
        )
    )
    row = result.first()

    posts_without_excerpt = (
        await db.scalar(
            select(func.count())
            .select_from(Post)
            .where((Post.excerpt == "") | (Post.excerpt.is_(None)))
        )
        or 0
    )

    posts_without_tags = (
        await db.scalar(select(func.count()).select_from(Post).where(~Post.tags.any())) or 0
    )

    total_categories = await db.scalar(select(func.count()).select_from(Category)) or 0

    return {
        "total_posts": total_posts,
        "total_categories": total_categories,
        "posts_without_excerpt": posts_without_excerpt,
        "posts_without_tags": posts_without_tags,
        "avg_slug_length": round(row.total_slug_len / total_posts, 2) if total_posts > 0 else 0,
        "avg_excerpt_length": round(row.total_excerpt_len / total_posts, 2)
        if total_posts > 0
        else 0,
        "recommendations": [
            {
                "type": "excerpt",
                "count": posts_without_excerpt,
                "message": f"有 {posts_without_excerpt} 篇文章缺少摘要",
            },
            {
                "type": "tags",
                "count": posts_without_tags,
                "message": f"有 {posts_without_tags} 篇文章未设置标签",
            },
        ],
    }


@router.post("/tools/optimize-search")
async def optimize_search(
    current_user: CurrentStaff,
    db: DB,
):
    """执行检索优化（自动补全摘要、生成slug等）"""
    import re

    def _slugify(text: str) -> str:
        slug = text.lower()
        slug = re.sub(r"[^\w\s-]", "", slug)
        slug = re.sub(r"[\s_-]+", "-", slug)
        slug = slug.strip("-")
        return slug or f"post-{id(text)}"

    result = await db.execute(
        select(Post).where(
            (Post.slug == "")
            | (Post.slug.is_(None))
            | (Post.excerpt == "")
            | (Post.excerpt.is_(None))
        )
    )
    posts = result.scalars().all()

    optimized = 0
    for post in posts:
        changed = False
        if not post.slug and post.title:
            title_text = post.title.get("zh") or post.title.get("en") or ""
            if title_text:
                post.slug = _slugify(title_text)[:100]
                changed = True
        if not post.excerpt and post.content:
            content_text = post.content.get("zh") or post.content.get("en") or ""
            if content_text:
                import re

                plain = re.sub(r"[#*`>\[\]()!_\-]", "", content_text)
                plain = plain.replace("\n", " ").strip()
                post.excerpt = {"zh": plain[:200], "en": plain[:200]}
                changed = True
        if changed:
            optimized += 1

    return {
        "success": True,
        "optimized_count": optimized,
        "message": f"已优化 {optimized} 篇文章的检索信息",
    }
