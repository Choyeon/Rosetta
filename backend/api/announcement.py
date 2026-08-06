"""
公告 API

提供公开接口获取当前活跃公告，以及管理员接口管理公告 CRUD。

路由设计：
- 公开接口: GET /api/announcements
- 管理接口: /api/admin/announcements (GET/POST/PUT/DELETE/toggle)
"""

from datetime import datetime

from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import select

from backend.core.auth import DB, CurrentStaff
from backend.models.announcement import Announcement
from backend.schemas import BaseResponse
from backend.schemas.announcement import (
    AnnouncementCreate,
    AnnouncementResponse,
    AnnouncementUpdate,
)
from backend.utils.compat import UTC

router = APIRouter(tags=["公告"])


# ==================== 公开接口 ====================


@router.get(
    "/announcements",
    response_model=list[AnnouncementResponse],
    summary="获取当前活跃公告",
    description="获取当前时间范围内处于激活状态的公告列表，按 sort_order 升序排列。",
)
async def list_active_announcements(db: DB):
    """获取当前生效的公告（公开接口）"""
    now = datetime.now(UTC)

    query = (
        select(Announcement)
        .where(Announcement.is_active.is_(True))
        .where((Announcement.start_time.is_(None)) | (Announcement.start_time <= now))
        .where((Announcement.end_time.is_(None)) | (Announcement.end_time >= now))
        .order_by(Announcement.sort_order.asc(), Announcement.created_at.desc())
    )

    result = await db.execute(query)
    return result.scalars().all()


# ==================== 管理接口 ====================


@router.get(
    "/admin/announcements",
    response_model=list[AnnouncementResponse],
    summary="管理员获取所有公告",
    description="管理员获取所有公告列表，支持按激活状态过滤。",
)
async def admin_list_announcements(
    db: DB,
    current_user: CurrentStaff,
    is_active: bool | None = Query(None, description="按激活状态过滤"),
):
    """管理员获取所有公告"""
    query = select(Announcement).order_by(
        Announcement.sort_order.asc(), Announcement.created_at.desc()
    )

    if is_active is not None:
        query = query.where(Announcement.is_active == is_active)

    result = await db.execute(query)
    return result.scalars().all()


@router.post(
    "/admin/announcements",
    response_model=AnnouncementResponse,
    status_code=status.HTTP_201_CREATED,
    summary="创建公告",
    description="管理员创建新公告。",
)
async def create_announcement(
    data: AnnouncementCreate,
    db: DB,
    current_user: CurrentStaff,
):
    """创建公告"""
    announcement = Announcement(
        title=data.title,
        content=data.content,
        type=data.type,
        is_active=data.is_active,
        is_dismissible=data.is_dismissible,
        start_time=data.start_time,
        end_time=data.end_time,
        sort_order=data.sort_order,
    )
    db.add(announcement)
    await db.flush()
    await db.refresh(announcement)

    return AnnouncementResponse.model_validate(announcement)


@router.put(
    "/admin/announcements/{announcement_id}",
    response_model=AnnouncementResponse,
    summary="更新公告",
    description="管理员更新指定公告。",
)
async def update_announcement(
    announcement_id: int,
    data: AnnouncementUpdate,
    db: DB,
    current_user: CurrentStaff,
):
    """更新公告"""
    result = await db.execute(select(Announcement).where(Announcement.id == announcement_id))
    announcement = result.scalar_one_or_none()

    if not announcement:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="公告不存在",
        )

    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(announcement, field, value)

    await db.flush()
    await db.refresh(announcement)
    return AnnouncementResponse.model_validate(announcement)


@router.delete(
    "/admin/announcements/{announcement_id}",
    response_model=BaseResponse,
    summary="删除公告",
    description="管理员删除指定公告。",
)
async def delete_announcement(
    announcement_id: int,
    db: DB,
    current_user: CurrentStaff,
):
    """删除公告"""
    result = await db.execute(select(Announcement).where(Announcement.id == announcement_id))
    announcement = result.scalar_one_or_none()

    if not announcement:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="公告不存在",
        )

    await db.delete(announcement)
    return BaseResponse(message="公告已删除")


@router.put(
    "/admin/announcements/{announcement_id}/toggle",
    response_model=AnnouncementResponse,
    summary="切换公告激活状态",
    description="管理员切换公告的激活状态。",
)
async def toggle_announcement(
    announcement_id: int,
    db: DB,
    current_user: CurrentStaff,
):
    """切换公告激活状态"""
    result = await db.execute(select(Announcement).where(Announcement.id == announcement_id))
    announcement = result.scalar_one_or_none()

    if not announcement:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="公告不存在",
        )

    announcement.is_active = not announcement.is_active
    await db.flush()
    await db.refresh(announcement)
    return AnnouncementResponse.model_validate(announcement)
