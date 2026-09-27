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
  DELETE /api/admin/gallery/photos/batch    批量删除照片
  DELETE /api/admin/gallery/photos/{id}     删除照片
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, Body, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import delete, func, select
from sqlalchemy.orm import selectinload

from backend.core.auth import CurrentStaff
from backend.core.cache import cache, make_cache_key
from backend.core.deps import DB, PaginationParams, get_pagination
from backend.core.partial_update import apply_partial_update
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


# ═══════════════════════════════════════════════════════════════════════════
# 响应体文档模型（仅供 OpenAPI `responses={200: {"model": ...}}` 声明使用，
# 运行时不做序列化过滤——实际响应以 handler 返回字面量为准）
# ═══════════════════════════════════════════════════════════════════════════


class PhotoBatchDeleteResponse(BaseModel):
    """``DELETE /api/admin/gallery/photos/batch`` 的响应体（裸 dict，无 data 信封）。"""

    success: bool = Field(
        True,
        description="固定为 true：一条都不存在时本接口返回 404 而非 false；部分缺失仍为 true",
    )
    message: str = Field(
        ..., description="人类可读汇总，如「已删除 3 张照片，2 个 ID 不存在」（后半段仅缺失时出现）"
    )
    deleted_count: int = Field(..., description="本次实际删除的行数（请求 ID 中与库内交集的大小）")
    missing_ids: list[int] = Field(
        default_factory=list,
        description="请求里不存在的 ID 列表，升序去重；调用方不得只看 success 判定全部删除完成",
    )


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


async def _fallback_cover_map(db: DB, albums: list[Album]) -> dict[int, str]:
    """为缺封面的相册批量算出兜底封面：``{album_id: 排序最前的照片 URL}``。

    两点刻意之为：
    1. 一次查询拿整页（旧实现在列表循环里逐个 ``SELECT photos ... LIMIT 1``，即 1 + page_size 次往返）；
    2. **只返回映射，绝不写 ``album.cover``**。相册对象还挂在 session 的 identity map 里，
       一旦赋值就成了脏对象，请求结束 commit 时 autoflush 会把"首张照片 URL"真的写进 DB——
       管理员下次进后台会发现封面被自动改掉，且再也回不到原来的空值。展示层的东西必须止步于展示层。
    """
    missing = [album for album in albums if not album.cover]
    if not missing:
        return {}

    rows = await db.execute(
        select(Photo.album_id, Photo.url)
        .where(Photo.album_id.in_([album.id for album in missing]))
        .order_by(Photo.album_id.asc(), Photo.sort_order.asc(), Photo.id.asc())
    )
    first_url: dict[int, str] = {}
    for album_id, url in rows.all():
        first_url.setdefault(album_id, url)
    return first_url


def _album_response(album: Album, fallback_cover: str | None = None) -> AlbumResponse:
    """相册序列化；``fallback_cover`` 只覆写响应对象，不回写 ORM。"""
    response = AlbumResponse.model_validate(album)
    if not response.cover and fallback_cover:
        response.cover = fallback_cover
    return response


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
    cache_key = make_cache_key(
        "gallery", "albums", f"p{pagination.page}", f"ps{pagination.page_size}"
    )
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
    covers = await _fallback_cover_map(db, list(items))
    resp = PaginatedResponse(
        items=[_album_response(a, covers.get(a.id)) for a in items],
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
        # 封面兜底：未设封面则用首张照片。写响应对象而非 album.cover——后者会把
        # 兜底值 flush 进数据库，覆盖掉用户真实的"空封面"状态。
        **_album_response(album, album.photos[0].url if album.photos else None).model_dump(),
        photos=[PhotoResponse.model_validate(p) for p in album.photos],
    )
    await cache.set(cache_key, resp, ttl=600)
    return resp


# ==================== 管理接口 - 相册 ====================


@admin_router.get(
    "/albums",
    response_model=PaginatedResponse[AlbumResponse],
    summary="【管理员】获取所有相册",
    description=(
        "需 CurrentStaff。按 sort_order 升序 + 创建时间倒序分页返回全部相册（含未发布项），"
        "可用 is_published 按发布状态过滤。封面为空时自动填充兜底图（仅展示层，不回写 DB）。"
    ),
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
    covers = await _fallback_cover_map(db, list(items))
    return PaginatedResponse(
        items=[_album_response(a, covers.get(a.id)) for a in items],
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
    description=(
        "需 CurrentStaff。创建后作者记为当前管理员，并立即失效相册公开缓存（gallery:*）。"
        "非幂等，重复提交会产生同名多相册。"
    ),
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
    description=(
        "需 CurrentStaff。PATCH 风格局部更新：仅写入请求体中出现的字段（exclude_unset）。"
        "相册不存在返回 404。保存后失效相册公开缓存。"
    ),
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
    apply_partial_update(album, update_data)
    await db.flush()
    await db.refresh(album)
    await cache.delete_pattern(make_cache_key("gallery", "*"))
    return AlbumResponse.model_validate(album)


@admin_router.delete(
    "/albums/{album_id}",
    response_model=BaseResponse,
    summary="【管理员】删除相册",
    description=(
        "需 CurrentStaff。物理删除相册（级联行为由 ORM relationship 定义），不存在返回 404。"
        "删除后失效相册公开缓存。不可恢复。"
    ),
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
    description=(
        "需 CurrentStaff。按 sort_order 升序 + 创建时间正序分页返回该相册全部照片（含未发布语义）。"
        "相册不存在返回 404。"
    ),
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
    description=(
        "需 CurrentStaff。photo.url 应指向 /api/media 上传后的媒体地址（本接口不接收文件本身）。"
        "写入后同步刷新所属相册 photo_count 并失效相册公开缓存；album_id 对应相册不存在返回 404。"
    ),
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
    description=(
        "需 CurrentStaff。局部更新（exclude_unset）；若传入新的 album_id 则执行跨相册移动，"
        "新旧相册的 photo_count 都会重算。照片不存在返回 404。保存后失效相册公开缓存。"
    ),
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
    apply_partial_update(photo, update_data)
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
    "/photos/batch",
    summary="【管理员】批量删除照片",
    description=(
        "需 CurrentStaff。一次请求删除多张照片：`DELETE /photos/{photo_id}` 的批量版，"
        "前端逐张调用会把 N 张照片变成 N 次请求 + N 次全量相册缓存失效。"
        "受影响的相册各重算一次 `photo_count`。"
        "响应含 `deleted_count` 与 `missing_ids`（请求里不存在的 ID），"
        "调用方不得只看 `success` 判定全部删除完成。"
        "只删 DB 记录，媒体文件不自动清理，不可恢复。"
    ),
    responses={200: {"model": PhotoBatchDeleteResponse}},
)
async def admin_delete_photos_batch(
    db: DB,
    _staff: CurrentStaff,
    ids: list[int] = Body(..., embed=True, description="照片 ID 列表"),
):
    """批量删除照片，并按相册各重算一次 photo_count。"""
    if not ids:
        raise HTTPException(status_code=400, detail="请提供要删除的照片 ID")

    # 只取删除与重算计数所需的列，避免把整行（含 description）载入内存
    rows = (await db.execute(select(Photo.id, Photo.album_id).where(Photo.id.in_(ids)))).all()
    if not rows:
        raise HTTPException(status_code=404, detail="照片不存在")

    found_ids = [row.id for row in rows]
    album_ids = {row.album_id for row in rows}
    await db.execute(delete(Photo).where(Photo.id.in_(found_ids)))
    for album_id in album_ids:
        await _refresh_photo_count(db, album_id)
    await db.flush()
    await cache.delete_pattern(make_cache_key("gallery", "*"))

    missing = sorted(set(ids) - set(found_ids))
    message = f"已删除 {len(found_ids)} 张照片"
    if missing:
        message += f"，{len(missing)} 个 ID 不存在"

    return {
        "success": True,
        "message": message,
        "deleted_count": len(found_ids),
        "missing_ids": missing,
    }


@admin_router.delete(
    "/photos/{photo_id}",
    response_model=BaseResponse,
    summary="【管理员】删除照片",
    description=(
        "需 CurrentStaff。物理删除照片并重算所属相册 photo_count，不存在返回 404。"
        "删除后失效相册公开缓存。不可恢复（仅删 DB 记录，媒体文件不自动清理）。"
    ),
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
