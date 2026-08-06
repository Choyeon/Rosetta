"""
Hero 轮播 API

提供公开接口获取当前活跃 Hero 幻灯片，以及管理员接口管理 CRUD。

路由设计：
- 公开接口: GET /api/hero/slides
- 管理接口: /api/admin/hero/slides (GET/POST/PUT/DELETE/toggle)
"""

from datetime import datetime

from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import select

from backend.core.auth import DB, CurrentStaff
from backend.models.hero import HeroSlide
from backend.schemas import BaseResponse
from backend.schemas.hero import (
    HeroSlideCreate,
    HeroSlideResponse,
    HeroSlideUpdate,
)
from backend.utils.compat import UTC

router = APIRouter(tags=["Hero轮播"])


# ==================== 公开接口 ====================


@router.get(
    "/hero/slides",
    response_model=list[HeroSlideResponse],
    summary="获取当前活跃 Hero 幻灯片",
    description="获取当前时间范围内处于激活状态的 Hero 幻灯片列表，按 sort_order 升序排列。",
)
async def list_active_hero_slides(db: DB):
    """获取当前生效的 Hero 幻灯片（公开接口）"""
    now = datetime.now(UTC)

    query = (
        select(HeroSlide)
        .where(HeroSlide.is_active.is_(True))
        .where((HeroSlide.start_time.is_(None)) | (HeroSlide.start_time <= now))
        .where((HeroSlide.end_time.is_(None)) | (HeroSlide.end_time >= now))
        .order_by(HeroSlide.sort_order.asc(), HeroSlide.created_at.desc())
    )

    result = await db.execute(query)
    return result.scalars().all()


# ==================== 管理接口 ====================


@router.get(
    "/admin/hero/slides",
    response_model=list[HeroSlideResponse],
    summary="管理员获取所有 Hero 幻灯片",
    description="管理员获取所有 Hero 幻灯片列表，支持按激活状态过滤。",
)
async def admin_list_hero_slides(
    db: DB,
    current_user: CurrentStaff,
    is_active: bool | None = Query(None, description="按激活状态过滤"),
):
    """管理员获取所有 Hero 幻灯片"""
    query = select(HeroSlide).order_by(HeroSlide.sort_order.asc(), HeroSlide.created_at.desc())

    if is_active is not None:
        query = query.where(HeroSlide.is_active == is_active)

    result = await db.execute(query)
    return result.scalars().all()


@router.post(
    "/admin/hero/slides",
    response_model=HeroSlideResponse,
    status_code=status.HTTP_201_CREATED,
    summary="创建 Hero 幻灯片",
    description="管理员创建新 Hero 幻灯片。",
)
async def create_hero_slide(
    data: HeroSlideCreate,
    db: DB,
    current_user: CurrentStaff,
):
    """创建 Hero 幻灯片"""
    slide = HeroSlide(
        title=data.title,
        subtitle=data.subtitle,
        media_type=data.media_type,
        media_url=data.media_url,
        poster_url=data.poster_url,
        overlay_opacity=data.overlay_opacity,
        overlay_color=data.overlay_color,
        cta_text=data.cta_text,
        cta_url=data.cta_url,
        cta_secondary_text=data.cta_secondary_text,
        cta_secondary_url=data.cta_secondary_url,
        text_align=data.text_align,
        text_color=data.text_color,
        is_active=data.is_active,
        sort_order=data.sort_order,
        start_time=data.start_time,
        end_time=data.end_time,
    )
    db.add(slide)
    await db.flush()
    await db.refresh(slide)

    return HeroSlideResponse.model_validate(slide)


@router.put(
    "/admin/hero/slides/{slide_id}",
    response_model=HeroSlideResponse,
    summary="更新 Hero 幻灯片",
    description="管理员更新指定 Hero 幻灯片。",
)
async def update_hero_slide(
    slide_id: int,
    data: HeroSlideUpdate,
    db: DB,
    current_user: CurrentStaff,
):
    """更新 Hero 幻灯片"""
    result = await db.execute(select(HeroSlide).where(HeroSlide.id == slide_id))
    slide = result.scalar_one_or_none()

    if not slide:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Hero 幻灯片不存在",
        )

    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(slide, field, value)

    await db.flush()
    await db.refresh(slide)
    return HeroSlideResponse.model_validate(slide)


@router.delete(
    "/admin/hero/slides/{slide_id}",
    response_model=BaseResponse,
    summary="删除 Hero 幻灯片",
    description="管理员删除指定 Hero 幻灯片。",
)
async def delete_hero_slide(
    slide_id: int,
    db: DB,
    current_user: CurrentStaff,
):
    """删除 Hero 幻灯片"""
    result = await db.execute(select(HeroSlide).where(HeroSlide.id == slide_id))
    slide = result.scalar_one_or_none()

    if not slide:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Hero 幻灯片不存在",
        )

    await db.delete(slide)
    return BaseResponse(message="Hero 幻灯片已删除")


@router.put(
    "/admin/hero/slides/{slide_id}/toggle",
    response_model=HeroSlideResponse,
    summary="切换 Hero 幻灯片激活状态",
    description="管理员切换 Hero 幻灯片的激活状态。",
)
async def toggle_hero_slide(
    slide_id: int,
    db: DB,
    current_user: CurrentStaff,
):
    """切换 Hero 幻灯片激活状态"""
    result = await db.execute(select(HeroSlide).where(HeroSlide.id == slide_id))
    slide = result.scalar_one_or_none()

    if not slide:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Hero 幻灯片不存在",
        )

    slide.is_active = not slide.is_active
    await db.flush()
    await db.refresh(slide)
    return HeroSlideResponse.model_validate(slide)
