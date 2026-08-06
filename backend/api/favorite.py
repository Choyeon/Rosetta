"""
收藏系统 API

支持文章收藏、收藏夹管理等功能。
"""

import math
from datetime import datetime

from fastapi import APIRouter, Body, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, func, select
from sqlalchemy.orm import Mapped, mapped_column, relationship, selectinload

from backend.core.auth import DB, CurrentUser
from backend.core.concurrency import concurrent_query
from backend.core.database import Base
from backend.utils.compat import UTC


class FavoriteFolder(Base):
    """收藏夹"""

    __tablename__ = "favorite_folders"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_public: Mapped[bool] = mapped_column(Boolean, default=False)
    order: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC)
    )

    user: Mapped["User"] = relationship("User", backref="favorite_folders")


class Favorite(Base):
    """收藏记录"""

    __tablename__ = "favorites"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    post_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("posts.id", ondelete="CASCADE"), nullable=False, index=True
    )
    folder_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("favorite_folders.id", ondelete="SET NULL"), nullable=True
    )
    note: Mapped[str | None] = mapped_column(Text, nullable=True)  # 收藏备注
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(UTC), index=True
    )

    user: Mapped["User"] = relationship("User")
    post: Mapped["Post"] = relationship("Post")
    folder: Mapped["FavoriteFolder | None"] = relationship("FavoriteFolder", backref="favorites")


router = APIRouter(tags=["收藏"])


class FolderCreate(BaseModel):
    """创建收藏夹"""

    name: str
    description: str | None = None
    is_public: bool = False


class FolderUpdate(BaseModel):
    """更新收藏夹"""

    name: str | None = None
    description: str | None = None
    is_public: bool | None = None


# ==================== 收藏夹 API ====================


@router.get(
    "/folders",
    summary="我的收藏夹列表",
    description="获取当前用户的收藏夹列表。",
)
async def list_favorite_folders(
    db: DB,
    current_user: CurrentUser,
):
    """获取收藏夹列表"""
    result = await db.execute(
        select(FavoriteFolder)
        .where(FavoriteFolder.user_id == current_user.id)
        .order_by(FavoriteFolder.order, FavoriteFolder.created_at.desc())
    )
    folders = result.scalars().all()

    # 获取每个收藏夹的文章数
    items = []
    for folder in folders:
        count = (
            await db.scalar(
                select(func.count()).select_from(Favorite).where(Favorite.folder_id == folder.id)
            )
            or 0
        )
        items.append(
            {
                "id": folder.id,
                "name": folder.name,
                "description": folder.description,
                "is_public": folder.is_public,
                "count": count,
                "created_at": folder.created_at.isoformat() if folder.created_at else None,
            }
        )

    return {"items": items, "total": len(items)}


@router.post(
    "/folders",
    summary="创建收藏夹",
    description="创建新的收藏夹。",
)
async def create_favorite_folder(
    db: DB,
    current_user: CurrentUser,
    data: FolderCreate = Body(...),
):
    """创建收藏夹"""
    folder = FavoriteFolder(
        user_id=current_user.id,
        name=data.name,
        description=data.description,
        is_public=data.is_public,
    )
    db.add(folder)
    await db.flush()
    await db.refresh(folder)

    return {
        "success": True,
        "message": "收藏夹创建成功",
        "folder": {
            "id": folder.id,
            "name": folder.name,
            "description": folder.description,
            "is_public": folder.is_public,
        },
    }


@router.put(
    "/folders/{folder_id}",
    summary="更新收藏夹",
    description="更新收藏夹信息。",
)
async def update_favorite_folder(
    folder_id: int,
    db: DB,
    current_user: CurrentUser,
    data: FolderUpdate = Body(...),
):
    """更新收藏夹"""
    folder = await db.get(FavoriteFolder, folder_id)
    if not folder or folder.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="收藏夹不存在",
        )

    if data.name is not None:
        folder.name = data.name
    if data.description is not None:
        folder.description = data.description
    if data.is_public is not None:
        folder.is_public = data.is_public

    await db.flush()

    return {"success": True, "message": "收藏夹更新成功"}


@router.delete(
    "/folders/{folder_id}",
    summary="删除收藏夹",
    description="删除收藏夹（收藏的文章会移到默认收藏）。",
)
async def delete_favorite_folder(
    folder_id: int,
    db: DB,
    current_user: CurrentUser,
):
    """删除收藏夹"""
    folder = await db.get(FavoriteFolder, folder_id)
    if not folder or folder.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="收藏夹不存在",
        )

    # 将收藏移到默认（folder_id = None）
    await db.execute(select(Favorite).where(Favorite.folder_id == folder_id))

    await db.delete(folder)
    await db.flush()

    return {"success": True, "message": "收藏夹已删除"}


# ==================== 收藏 API ====================


@router.get(
    "",
    summary="我的收藏列表",
    description="获取当前用户的收藏列表。",
)
async def list_favorites(
    db: DB,
    current_user: CurrentUser,
    folder_id: int | None = Query(None, description="收藏夹 ID"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    """获取收藏列表"""
    from backend.models.blog import Post

    query = (
        select(Favorite)
        .where(Favorite.user_id == current_user.id)
        .options(selectinload(Favorite.post).selectinload(Post.category))
    )

    if folder_id:
        query = query.where(Favorite.folder_id == folder_id)

    query = query.order_by(Favorite.created_at.desc())

    # 并发查询
    count_query = select(func.count()).select_from(
        select(Favorite).where(Favorite.user_id == current_user.id).subquery()
    )

    total, result = await concurrent_query(
        db.scalar(count_query),
        db.execute(query.offset((page - 1) * page_size).limit(page_size)),
    )

    favorites = result.scalars().all()
    total = total or 0

    items = []
    for fav in favorites:
        post = fav.post
        items.append(
            {
                "id": fav.id,
                "note": fav.note,
                "folder_id": fav.folder_id,
                "created_at": fav.created_at.isoformat() if fav.created_at else None,
                "post": {
                    "id": post.id,
                    "title": post.title,
                    "slug": post.slug,
                    "cover_image": post.cover_image,
                    "views": post.views,
                    "category": {
                        "id": post.category.id,
                        "name": post.category.name,
                        "color": post.category.color,
                    }
                    if post.category
                    else None,
                    "published_at": post.published_at.isoformat() if post.published_at else None,
                }
                if post
                else None,
            }
        )

    return {
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": math.ceil(total / page_size) if total > 0 else 0,
    }


@router.post(
    "",
    summary="收藏文章",
    description="收藏一篇文章。",
)
async def add_favorite(
    db: DB,
    current_user: CurrentUser,
    post_id: int = Body(..., embed=True),
    folder_id: int | None = Body(None, embed=True),
    note: str | None = Body(None, embed=True),
):
    """收藏文章"""
    from backend.models.blog import Post

    # 检查文章是否存在
    post = await db.get(Post, post_id)
    if not post:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="文章不存在",
        )

    # 检查是否已收藏
    existing = await db.execute(
        select(Favorite).where(
            Favorite.user_id == current_user.id,
            Favorite.post_id == post_id,
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="已收藏此文章",
        )

    # 检查收藏夹
    if folder_id:
        folder = await db.get(FavoriteFolder, folder_id)
        if not folder or folder.user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="收藏夹不存在",
            )

    favorite = Favorite(
        user_id=current_user.id,
        post_id=post_id,
        folder_id=folder_id,
        note=note,
    )
    db.add(favorite)
    await db.flush()

    return {"success": True, "message": "收藏成功"}


@router.put(
    "/{favorite_id}",
    summary="更新收藏",
    description="更新收藏信息（移动收藏夹、添加备注）。",
)
async def update_favorite(
    favorite_id: int,
    db: DB,
    current_user: CurrentUser,
    folder_id: int | None = Body(None, embed=True),
    note: str | None = Body(None, embed=True),
):
    """更新收藏"""
    favorite = await db.get(Favorite, favorite_id)
    if not favorite or favorite.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="收藏不存在",
        )

    if folder_id is not None:
        if folder_id:
            folder = await db.get(FavoriteFolder, folder_id)
            if not folder or folder.user_id != current_user.id:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="收藏夹不存在",
                )
        favorite.folder_id = folder_id if folder_id else None

    if note is not None:
        favorite.note = note

    await db.flush()

    return {"success": True, "message": "收藏更新成功"}


@router.delete(
    "/{favorite_id}",
    summary="取消收藏",
    description="取消收藏文章。",
)
async def remove_favorite(
    favorite_id: int,
    db: DB,
    current_user: CurrentUser,
):
    """取消收藏"""
    favorite = await db.get(Favorite, favorite_id)
    if not favorite or favorite.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="收藏不存在",
        )

    await db.delete(favorite)
    await db.flush()

    return {"success": True, "message": "已取消收藏"}


@router.delete(
    "/post/{post_id}",
    summary="按文章ID取消收藏",
    description="根据文章ID取消收藏。",
)
async def remove_favorite_by_post(
    post_id: int,
    db: DB,
    current_user: CurrentUser,
):
    """按文章ID取消收藏"""
    result = await db.execute(
        select(Favorite).where(
            Favorite.user_id == current_user.id,
            Favorite.post_id == post_id,
        )
    )
    favorite = result.scalar_one_or_none()
    if not favorite:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="收藏不存在",
        )

    await db.delete(favorite)
    await db.flush()

    return {"success": True, "message": "已取消收藏"}


@router.patch(
    "/post/{post_id}/folder",
    summary="按文章ID移动收藏夹",
    description="根据文章ID移动收藏到指定收藏夹。",
)
async def move_favorite_by_post(
    post_id: int,
    db: DB,
    current_user: CurrentUser,
    folder_id: int | None = Body(None, embed=True),
):
    """按文章ID移动收藏夹"""
    result = await db.execute(
        select(Favorite).where(
            Favorite.user_id == current_user.id,
            Favorite.post_id == post_id,
        )
    )
    favorite = result.scalar_one_or_none()
    if not favorite:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="收藏不存在",
        )

    if folder_id:
        folder = await db.get(FavoriteFolder, folder_id)
        if not folder or folder.user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="收藏夹不存在",
            )
    favorite.folder_id = folder_id

    await db.flush()

    return favorite


@router.patch(
    "/post/{post_id}/note",
    summary="按文章ID更新备注",
    description="根据文章ID更新收藏备注。",
)
async def update_favorite_note_by_post(
    post_id: int,
    db: DB,
    current_user: CurrentUser,
    note: str | None = Body(None, embed=True),
):
    """按文章ID更新备注"""
    result = await db.execute(
        select(Favorite).where(
            Favorite.user_id == current_user.id,
            Favorite.post_id == post_id,
        )
    )
    favorite = result.scalar_one_or_none()
    if not favorite:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="收藏不存在",
        )

    favorite.note = note
    await db.flush()

    return favorite


@router.post(
    "/check",
    summary="检查收藏状态",
    description="检查多篇文章是否已收藏。",
)
async def check_favorites(
    db: DB,
    current_user: CurrentUser,
    post_ids: list[int] = Body(..., embed=True),
):
    """检查收藏状态"""
    result = await db.execute(
        select(Favorite.post_id, Favorite.id).where(
            Favorite.user_id == current_user.id,
            Favorite.post_id.in_(post_ids),
        )
    )
    favorites = {row.post_id: row.id for row in result.all()}

    return {
        "favorites": {
            str(post_id): {
                "is_favorited": post_id in favorites,
                "favorite_id": favorites.get(post_id),
            }
            for post_id in post_ids
        }
    }
