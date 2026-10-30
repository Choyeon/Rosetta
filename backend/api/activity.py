"""
网站动态 API

提供公开接口获取已发布动态列表（支持分页），以及管理员接口管理动态 CRUD。

路由设计：
- 公开接口: GET /api/activities
- 管理接口: /api/admin/activities (GET/POST/PUT/DELETE)
"""

import math
from typing import get_args

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
    ActivityType,
    ActivityUpdate,
)
from backend.services.frontend_cache_purge import purge_frontend_page_cache

router = APIRouter(tags=["网站动态"])

# 公开口可筛选的类型：直接取 schemas.activity.ActivityType 这个 Literal，不再抄一份清单。
# 前端 pages/activity.vue 的 ACTIVITY_TYPES / ICONS / activity.type_* 必须与这里同集合，
# 新增类型漏补的表现是筛出来的动态全部落回「说说」图标。
ACTIVITY_TYPE_FILTERS = frozenset(get_args(ActivityType))


async def _invalidate_activity_caches(reason: str) -> None:
    """动态写侧统一失效：后端 `activities:*` 响应缓存 + 前端 swr 页面缓存。

    动态列表挂在首页右侧卡片（`LatestActivitiesCard`）与独立 `/activities` 页；
    Nitro 对 '/' 做 300s swr、'/activities' 也做 swr。管理员发布/删除/改动态后
    只清后端缓存 = 访客 TTL 内首页仍显示旧动态。
    """
    await cache.delete_pattern(make_cache_key("activities", "*"))
    purge_frontend_page_cache(f"activity change: {reason}")


async def _get_activities_cache_key(
    language: str,
    page: int,
    page_size: int,
    activity_type: str | None = None,
) -> str:
    """生成动态列表缓存键

    `activity_type` 必须进键：它是 WHERE 里真正的判别位，不进键就等于让
    `?type=say` 的响应写进「全部」那一条，TTL 内所有访客的列表被单一类型污染。
    """
    parts = [
        "activities",
        language,
        f"p{page}",
        f"ps{page_size}",
        f"t{activity_type or 'all'}",
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
    description="获取已发布的网站动态列表，支持分页与按类型（type）筛选。",
)
async def list_activities(
    request: Request,
    db: DB,
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(10, ge=1, le=100, description="每页数量"),
    lang: str | None = Query(None, description="语言代码（zh/en/ja/zh_Hant）"),
    type: str | None = Query(  # noqa: A002 - 与 admin 口与前端 query 同名
        None,
        description=f"按动态类型筛选（{'/'.join(sorted(ACTIVITY_TYPE_FILTERS))}）；其它值按「不筛选」处理",
    ),
):
    """获取已发布动态列表（公开接口，支持分页与类型筛选）"""
    language = get_language_from_request(request, lang)

    # 白名单归一：未知类型按「不筛选」处理，而不是 422 也不是空列表。
    # ①缓存键取归一后的值，垃圾参数不会各自占一条键位；②与前端图标白名单同轨
    # （pages/activity.vue 的 backendToIconKey 对未知类型同样回落），分享出去的
    # 旧链接 / 手打的错参数看到的是完整列表，而不是一个错误态。
    activity_type = type.strip() if type else None
    if activity_type not in ACTIVITY_TYPE_FILTERS:
        activity_type = None

    cache_key = await _get_activities_cache_key(language, page, page_size, activity_type)
    cached = await cache.get(cache_key)
    if cached:
        return cached

    conditions = [Activity.is_published.is_(True)]
    if activity_type is not None:
        conditions.append(Activity.type == activity_type)

    # 计数用裸 count(*)：此前是 `select_from(list_query.subquery())`，
    # 等于把整页列表当成派生表再扫一遍，还带上了没意义的 ORDER BY。
    # 计数与列表必须过同一组 conditions，否则筛选后的 total_pages 会宣称还有下一页。
    total = (
        await db.scalar(
            select(func.count(Activity.id)).where(*conditions),
        )
        or 0
    )
    total_pages = math.ceil(total / page_size) if total > 0 else 0

    query = (
        select(Activity)
        .options(selectinload(Activity.author).selectinload(User.title))
        .where(*conditions)
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
    await _invalidate_activity_caches("write")
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
    await _invalidate_activity_caches("write")
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

    await _invalidate_activity_caches("write")

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

    await _invalidate_activity_caches("write")

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

    await _invalidate_activity_caches("write")

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

    await _invalidate_activity_caches("write")

    return ActivityResponse.model_validate(activity)
