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
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from backend.core.auth import DB, CurrentStaff
from backend.core.cache import cache, make_cache_key
from backend.core.deps import CurrentUserOptional
from backend.core.i18n import (
    get_language_from_request,
)
from backend.core.partial_update import apply_partial_update
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


async def _reload_activity(db: AsyncSession, activity_id: int) -> Activity:
    """写操作后重新读取一条动态，并带齐 `author`（含 title）关联。

    flush 之后 `created_at` / `updated_at` 这类服务端 onupdate 列处于过期状态，
    而 `ActivityResponse.author` 是必填，所以必须回读一次。

    此前每个写接口是"一条带 selectinload 但结果丢弃的 SELECT + refresh"两连；
    refresh 本身就会连 author→user→title 一起重载，那条 SELECT 纯属多余——实测一次
    POST /admin/activities 要读 activities 表 3 遍（计数断言见
    tests/test_admin_activity_crud.py）。现在收敛为一次带预加载的重读。
    """
    result = await db.execute(
        select(Activity)
        .options(selectinload(Activity.author).selectinload(User.title))
        .where(Activity.id == activity_id)
    )
    return result.unique().scalar_one()


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

    # 计数用裸 count(*)：此前是 `select_from(list_query.subquery())`，
    # 等于把整页列表当成派生表再扫一遍，还带上了没意义的 ORDER BY。
    total = (
        await db.scalar(
            select(func.count(Activity.id)).where(Activity.is_published.is_(True)),
        )
        or 0
    )
    total_pages = math.ceil(total / page_size) if total > 0 else 0

    query = (
        select(Activity)
        .options(selectinload(Activity.author).selectinload(User.title))
        .where(Activity.is_published.is_(True))
        .order_by(Activity.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )

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
    activity = await _reload_activity(db, activity.id)
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
    description="管理员获取所有动态列表，包括未发布的，支持按发布状态与类型（type）过滤、分页。",
)
async def admin_list_activities(
    db: DB,
    current_user: CurrentStaff,
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(10, ge=1, le=100, description="每页数量"),
    is_published: bool | None = Query(None, description="按发布状态过滤"),
    type: str | None = Query(
        None,
        pattern="^(say|article|update|notice|link)$",
        description="按动态类型过滤：say（说说）/article（文章发布）/update（更新）/notice（通知）/link（友链推荐）",
    ),
):
    """管理员获取所有动态"""
    conditions = []
    if is_published is not None:
        conditions.append(Activity.is_published == is_published)
    if type is not None:
        conditions.append(Activity.type == type)

    # 同上：计数不套派生表
    count_stmt = select(func.count(Activity.id))
    if conditions:
        count_stmt = count_stmt.where(*conditions)
    total = await db.scalar(count_stmt) or 0
    total_pages = math.ceil(total / page_size) if total > 0 else 0

    query = (
        select(Activity)
        .options(selectinload(Activity.author).selectinload(User.title))
        .order_by(Activity.created_at.desc())
    )
    if conditions:
        query = query.where(*conditions)
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
    activity = await _reload_activity(db, activity.id)

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
    # 这里只需要"存在性 + 可改的列"，带关联的完整对象在写完后统一重读
    activity = await db.get(Activity, activity_id)

    if not activity:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="动态不存在",
        )

    update_data = data.model_dump(exclude_unset=True)
    apply_partial_update(activity, update_data)

    await db.flush()
    activity = await _reload_activity(db, activity_id)

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
    # 这里只需要"存在性 + 可改的列"，带关联的完整对象在写完后统一重读
    activity = await db.get(Activity, activity_id)

    if not activity:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="动态不存在",
        )

    activity.is_published = not activity.is_published
    await db.flush()
    activity = await _reload_activity(db, activity_id)

    await cache.delete_pattern(make_cache_key("activities", "*"))

    return ActivityResponse.model_validate(activity)
