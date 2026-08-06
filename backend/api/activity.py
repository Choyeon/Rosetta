"""
网站动态 API

提供公开接口获取已发布动态列表（支持分页），以及管理员接口管理动态 CRUD。

路由设计：
- 公开接口: GET /api/activities
- 管理接口: /api/admin/activities (GET/POST/PUT/DELETE)
"""

import math

from fastapi import APIRouter, HTTPException, Query, Request, status
from sqlalchemy import func, select
from sqlalchemy.orm import selectinload

from backend.core.auth import DB, CurrentStaff
from backend.core.cache import cache, make_cache_key
from backend.core.i18n import (
    DEFAULT_LANGUAGE,
    get_language_from_request,
    normalize_language,
)
from backend.core.deps import CurrentUserOptional
from backend.models.activity import Activity
from backend.models.user import User
from backend.schemas import BaseResponse, PaginatedResponse
from backend.schemas.activity import (
    ActivityCreate,
    ActivityLocalizedResponse,
    ActivityResponse,
    ActivityUpdate,
)

router = APIRouter(tags=["网站动态"])


async def _get_activities_cache_key(
    language: str,
    page: int,
    page_size: int,
) -> str:
    """生成动态列表缓存键"""
    parts = [
        "activities",
        language,
        f"p{page}",
        f"ps{page_size}",
    ]
    return make_cache_key(*parts)


# ==================== 公开接口 ====================


@router.get(
    "/activities",
    response_model=PaginatedResponse[ActivityLocalizedResponse],
    summary="获取已发布动态列表",
    description="获取已发布的网站动态列表，支持分页。",
)
async def list_activities(
    request: Request,
    db: DB,
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(10, ge=1, le=100, description="每页数量"),
    lang: str | None = Query(None, description="语言代码（zh/en/ja/zh_Hant）"),
):
    """获取已发布动态列表（公开接口，支持分页）"""
    language = get_language_from_request(request, lang)

    cache_key = await _get_activities_cache_key(language, page, page_size)
    cached = await cache.get(cache_key)
    if cached:
        return cached

    query = (
        select(Activity)
        .options(selectinload(Activity.author).selectinload(User.title))
        .where(Activity.is_published.is_(True))
        .order_by(Activity.created_at.desc())
    )

    count_query = select(func.count()).select_from(query.subquery())
    total = await db.scalar(count_query) or 0
    total_pages = math.ceil(total / page_size) if total > 0 else 0

    query = query.offset((page - 1) * page_size).limit(page_size)

    result = await db.execute(query)
    activities = result.scalars().all()

    items = [ActivityLocalizedResponse.from_activity(a, language) for a in activities]

    response = PaginatedResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )

    await cache.set(cache_key, response, ttl=300)

    return response


@router.post(
    "/activities",
    response_model=ActivityResponse,
    status_code=status.HTTP_201_CREATED,
    summary="创建动态（登录用户可发布公开说说）",
    description="登录用户可以创建自己的动态，is_published 默认 True；如果未登录返回 401。",
)
async def create_activity_public(
    data: ActivityCreate,
    db: DB,
    current_user: CurrentUserOptional,
):
    """公开接口：登录用户创建动态（说说）"""
    if current_user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "success": False,
                "message": "请先登录后再发布动态",
                "error_code": "AUTH_REQUIRED",
            },
        )
    activity = Activity(
        content=data.content,
        type=data.type,
        author_id=current_user.id,
        is_published=data.is_published,
    )
    db.add(activity)
    await db.flush()
    await db.refresh(activity)
    # 重新加载关联 author
    await db.execute(
        select(Activity)
        .options(selectinload(Activity.author).selectinload(User.title))
        .where(Activity.id == activity.id)
    )
    await db.refresh(activity)
    await cache.delete_pattern(make_cache_key("activities", "*"))
    return ActivityResponse.model_validate(activity)


@router.post(
    "/activities/{activity_id}/like",
    response_model=BaseResponse,
    summary="给动态点赞",
    description="每次调用 likes_count +1，允许匿名。",
)
async def like_activity(activity_id: int, db: DB):
    """给动态点赞（计数 +1）"""
    result = await db.execute(select(Activity).where(Activity.id == activity_id))
    activity = result.scalar_one_or_none()
    if not activity:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="动态不存在",
        )
    activity.likes_count = (activity.likes_count or 0) + 1
    await db.flush()
    await cache.delete_pattern(make_cache_key("activities", "*"))
    return BaseResponse(message="点赞成功", success=True)


# ==================== 管理接口 ====================


@router.get(
    "/admin/activities",
    response_model=PaginatedResponse[ActivityResponse],
    summary="管理员获取所有动态",
    description="管理员获取所有动态列表，包括未发布的，支持分页。",
)
async def admin_list_activities(
    db: DB,
    current_user: CurrentStaff,
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(10, ge=1, le=100, description="每页数量"),
    is_published: bool | None = Query(None, description="按发布状态过滤"),
):
    """管理员获取所有动态"""
    query = (
        select(Activity)
        .options(selectinload(Activity.author).selectinload(User.title))
        .order_by(Activity.created_at.desc())
    )

    if is_published is not None:
        query = query.where(Activity.is_published == is_published)

    count_query = select(func.count()).select_from(query.subquery())
    total = await db.scalar(count_query) or 0
    total_pages = math.ceil(total / page_size) if total > 0 else 0

    query = query.offset((page - 1) * page_size).limit(page_size)

    result = await db.execute(query)
    activities = result.scalars().all()

    items = [ActivityResponse.model_validate(a) for a in activities]

    return PaginatedResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


@router.post(
    "/admin/activities",
    response_model=ActivityResponse,
    status_code=status.HTTP_201_CREATED,
    summary="创建动态",
    description="管理员创建新动态。",
)
async def create_activity(
    data: ActivityCreate,
    db: DB,
    current_user: CurrentStaff,
):
    """创建动态"""
    activity = Activity(
        content=data.content,
        type=data.type,
        author_id=current_user.id,
        is_published=data.is_published,
    )
    db.add(activity)
    await db.flush()
    await db.refresh(activity)

    await db.execute(
        select(Activity)
        .options(selectinload(Activity.author).selectinload(User.title))
        .where(Activity.id == activity.id)
    )
    await db.refresh(activity)

    await cache.delete_pattern(make_cache_key("activities", "*"))

    return ActivityResponse.model_validate(activity)


@router.put(
    "/admin/activities/{activity_id}",
    response_model=ActivityResponse,
    summary="更新动态",
    description="管理员更新指定动态。",
)
async def update_activity(
    activity_id: int,
    data: ActivityUpdate,
    db: DB,
    current_user: CurrentStaff,
):
    """更新动态"""
    result = await db.execute(
        select(Activity)
        .options(selectinload(Activity.author).selectinload(User.title))
        .where(Activity.id == activity_id)
    )
    activity = result.scalar_one_or_none()

    if not activity:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="动态不存在",
        )

    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(activity, field, value)

    await db.flush()
    await db.refresh(activity)

    await cache.delete_pattern(make_cache_key("activities", "*"))

    return ActivityResponse.model_validate(activity)


@router.delete(
    "/admin/activities/{activity_id}",
    response_model=BaseResponse,
    summary="删除动态",
    description="管理员删除指定动态。",
)
async def delete_activity(
    activity_id: int,
    db: DB,
    current_user: CurrentStaff,
):
    """删除动态"""
    result = await db.execute(select(Activity).where(Activity.id == activity_id))
    activity = result.scalar_one_or_none()

    if not activity:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="动态不存在",
        )

    await db.delete(activity)

    await cache.delete_pattern(make_cache_key("activities", "*"))

    return BaseResponse(message="动态已删除")


@router.put(
    "/admin/activities/{activity_id}/toggle",
    response_model=ActivityResponse,
    summary="切换动态发布状态",
    description="管理员切换动态的发布状态。",
)
async def toggle_activity(
    activity_id: int,
    db: DB,
    current_user: CurrentStaff,
):
    """切换动态发布状态"""
    result = await db.execute(
        select(Activity)
        .options(selectinload(Activity.author).selectinload(User.title))
        .where(Activity.id == activity_id)
    )
    activity = result.scalar_one_or_none()

    if not activity:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="动态不存在",
        )

    activity.is_published = not activity.is_published
    await db.flush()
    await db.refresh(activity)

    await cache.delete_pattern(make_cache_key("activities", "*"))

    return ActivityResponse.model_validate(activity)
