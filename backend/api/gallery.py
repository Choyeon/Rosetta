"""
相册（Gallery）API 路由

公开接口（所有人可见，仅 is_published=True）：
  GET  /api/gallery/albums          相册列表
  GET  /api/gallery/albums/{id}     相册详情（含照片）

管理接口（CurrentStaff 鉴权）：
  POST   /api/admin/gallery/albums          创建相册
  PUT    /api/admin/gallery/albums/{id}     更新相册
  DELETE /api/admin/gallery/albums/{id}     删除相册
  POST   /api/admin/gallery/photos          上传照片（URL 方式）
  PUT    /api/admin/gallery/photos/{id}     更新照片
  DELETE /api/admin/gallery/photos/{id}     删除照片
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.orm import selectinload

from backend.core.auth import CurrentStaff
from backend.core.cache import cache, make_cache_key
from backend.core.deps import DB, PaginationParams, get_pagination
from backend.models.gallery import Album, Photo
from backend.schemas import BaseResponse, PaginatedResponse
from backend.schemas.gallery import (
    AlbumCreate,
    AlbumDetailResponse,
    AlbumResponse,
    AlbumUpdate,
    PhotoCreate,
    PhotoResponse,
    PhotoUpdate,
)

logger = logging.getLogger(__name__)

public_router = APIRouter(prefix="/gallery", tags=["相册"])
admin_router = APIRouter(prefix="/admin/gallery", tags=["相册管理"])


# ==================== 工具 ====================


async def _refresh_photo_count(db: DB, album_id: int) -> None:
    """刷新相册 photo_count 字段"""
    count = await db.scalar(
        select(func.count()).select_from(Photo).where(Photo.album_id == album_id)
    )
    album = await db.get(Album, album_id)
    if album:
        album.photo_count = count or 0
        await db.flush()


# ==================== 公开接口 ====================


@public_router.get(
    "/albums",
    response_model=PaginatedResponse[AlbumResponse],
    summary="获取公开相册列表",
)
async def list_albums(
    db: DB,
    pagination: PaginationParams = Depends(get_pagination),
):
    """公开相册列表（分页）"""
    cache_key = make_cache_key("gallery", "albums", f"p{pagination.page}", f"ps{pagination.page_size}")
    cached = await cache.get(cache_key)
    if cached:
        return cached

    query = (
        select(Album)
        .where(Album.is_published.is_(True))
        .order_by(Album.sort_order.asc(), Album.created_at.desc())
    )
    total = await db.scalar(select(func.count()).select_from(query.subquery())) or 0
    query = query.offset(pagination.offset).limit(pagination.limit)
    items = (await db.execute(query)).scalars().all()
    resp = PaginatedResponse(
        items=[AlbumResponse.model_validate(a) for a in items],
        total=total,
        page=pagination.page,
        page_size=pagination.page_size,
        total_pages=(total + pagination.page_size - 1) // pagination.page_size if total else 0,
    )
    await cache.set(cache_key, resp, ttl=600)
    return resp


@public_router.get(
    "/albums/{album_id}",
    response_model=AlbumDetailResponse,
    summary="获取相册详情及照片",
)
async def get_album(album_id: int, db: DB):
    """获取指定相册详情（包含照片列表，仅公开相册）"""
    cache_key = make_cache_key("gallery", "album_detail", str(album_id))
    cached = await cache.get(cache_key)
    if cached:
        return cached

    result = await db.execute(
        select(Album)
        .options(selectinload(Album.photos))
        .where(Album.id == album_id, Album.is_published.is_(True))
    )
    album = result.scalar_one_or_none()
    if not album:
        raise HTTPException(status_code=404, detail="相册不存在或未公开")

    resp = AlbumDetailResponse(
        **AlbumResponse.model_validate(album).model_dump(),
        photos=[PhotoResponse.model_validate(p) for p in album.photos],
    )
    await cache.set(cache_key, resp, ttl=600)
    return resp


# ==================== 管理接口 - 相册 ====================


@admin_router.get(
    "/albums",
    response_model=PaginatedResponse[AlbumResponse],
    summary="【管理员】获取所有相册",
)
async def admin_list_albums(
    _staff: CurrentStaff,
    db: DB,
    pagination: PaginationParams = Depends(get_pagination),
    is_published: bool | None = Query(None, description="按发布状态过滤"),
):
    query = select(Album).order_by(Album.sort_order.asc(), Album.created_at.desc())
    if is_published is not None:
        query = query.where(Album.is_published == is_published)
    total = await db.scalar(select(func.count()).select_from(query.subquery())) or 0
    query = query.offset(pagination.offset).limit(pagination.limit)
    items = (await db.execute(query)).scalars().all()
    return PaginatedResponse(
        items=[AlbumResponse.model_validate(a) for a in items],
        total=total,
        page=pagination.page,
        page_size=pagination.page_size,
        total_pages=(total + pagination.page_size - 1) // pagination.page_size if total else 0,
    )


@admin_router.post(
    "/albums",
    response_model=AlbumResponse,
    status_code=status.HTTP_201_CREATED,
    summary="【管理员】创建相册",
)
async def admin_create_album(
    data: AlbumCreate,
    db: DB,
    current_user: CurrentStaff,
):
    album = Album(
        title=data.title,
        description=data.description,
        cover=data.cover,
        sort_order=data.sort_order,
        is_published=data.is_published,
        author_id=current_user.id,
    )
    db.add(album)
    await db.flush()
    await db.refresh(album)
    await cache.delete_pattern(make_cache_key("gallery", "*"))
    return AlbumResponse.model_validate(album)


@admin_router.put(
    "/albums/{album_id}",
    response_model=AlbumResponse,
    summary="【管理员】更新相册",
)
async def admin_update_album(
    album_id: int,
    data: AlbumUpdate,
    db: DB,
    _staff: CurrentStaff,
):
    album = await db.get(Album, album_id)
    if not album:
        raise HTTPException(status_code=404, detail="相册不存在")
    update_data = data.model_dump(exclude_unset=True)
    for k, v in update_data.items():
        setattr(album, k, v)
    await db.flush()
    await db.refresh(album)
    await cache.delete_pattern(make_cache_key("gallery", "*"))
    return AlbumResponse.model_validate(album)


@admin_router.delete(
    "/albums/{album_id}",
    response_model=BaseResponse,
    summary="【管理员】删除相册",
)
async def admin_delete_album(
    album_id: int,
    db: DB,
    _staff: CurrentStaff,
):
    album = await db.get(Album, album_id)
    if not album:
        raise HTTPException(status_code=404, detail="相册不存在")
    await db.delete(album)
    await cache.delete_pattern(make_cache_key("gallery", "*"))
    return BaseResponse(message="相册已删除")


# ==================== 管理接口 - 照片 ====================


@admin_router.get(
    "/albums/{album_id}/photos",
    response_model=PaginatedResponse[PhotoResponse],
    summary="【管理员】获取相册照片列表",
)
async def admin_list_photos(
    album_id: int,
    _staff: CurrentStaff,
    db: DB,
    pagination: PaginationParams = Depends(get_pagination),
):
    album = await db.get(Album, album_id)
    if not album:
        raise HTTPException(status_code=404, detail="相册不存在")
    query = (
        select(Photo)
        .where(Photo.album_id == album_id)
        .order_by(Photo.sort_order.asc(), Photo.created_at.asc())
    )
    total = await db.scalar(select(func.count()).select_from(query.subquery())) or 0
    query = query.offset(pagination.offset).limit(pagination.limit)
    items = (await db.execute(query)).scalars().all()
    return PaginatedResponse(
        items=[PhotoResponse.model_validate(p) for p in items],
        total=total,
        page=pagination.page,
        page_size=pagination.page_size,
        total_pages=(total + pagination.page_size - 1) // pagination.page_size if total else 0,
    )


@admin_router.post(
    "/photos",
    response_model=PhotoResponse,
    status_code=status.HTTP_201_CREATED,
    summary="【管理员】添加照片到相册",
)
async def admin_create_photo(
    data: PhotoCreate,
    db: DB,
    _staff: CurrentStaff,
):
    album = await db.get(Album, data.album_id)
    if not album:
        raise HTTPException(status_code=404, detail="相册不存在")
    photo = Photo(
        album_id=data.album_id,
        title=data.title,
        description=data.description,
        url=data.url,
        sort_order=data.sort_order,
    )
    db.add(photo)
    await db.flush()
    await db.refresh(photo)
    await _refresh_photo_count(db, data.album_id)
    await cache.delete_pattern(make_cache_key("gallery", "*"))
    return PhotoResponse.model_validate(photo)


@admin_router.put(
    "/photos/{photo_id}",
    response_model=PhotoResponse,
    summary="【管理员】更新照片",
)
async def admin_update_photo(
    photo_id: int,
    data: PhotoUpdate,
    db: DB,
    _staff: CurrentStaff,
):
    photo = await db.get(Photo, photo_id)
    if not photo:
        raise HTTPException(status_code=404, detail="照片不存在")
    old_album_id = photo.album_id
    update_data = data.model_dump(exclude_unset=True)
    for k, v in update_data.items():
        setattr(photo, k, v)
    await db.flush()
    await db.refresh(photo)
    if data.album_id is not None and data.album_id != old_album_id:
        await _refresh_photo_count(db, old_album_id)
        await _refresh_photo_count(db, photo.album_id)
    else:
        await _refresh_photo_count(db, photo.album_id)
    await cache.delete_pattern(make_cache_key("gallery", "*"))
    return PhotoResponse.model_validate(photo)


@admin_router.delete(
    "/photos/{photo_id}",
    response_model=BaseResponse,
    summary="【管理员】删除照片",
)
async def admin_delete_photo(
    photo_id: int,
    db: DB,
    _staff: CurrentStaff,
):
    photo = await db.get(Photo, photo_id)
    if not photo:
        raise HTTPException(status_code=404, detail="照片不存在")
    album_id = photo.album_id
    await db.delete(photo)
    await _refresh_photo_count(db, album_id)
    await cache.delete_pattern(make_cache_key("gallery", "*"))
    return BaseResponse(message="照片已删除")
