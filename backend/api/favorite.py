"""
收藏系统 API

支持文章收藏、收藏夹管理等功能。
"""

from __future__ import annotations

import math
from datetime import datetime
from typing import TYPE_CHECKING

from fastapi import APIRouter, Body, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, func, select, update
from sqlalchemy.orm import Mapped, mapped_column, relationship, selectinload

from backend.core.auth import DB, CurrentUser
from backend.core.concurrency import concurrent_query
from backend.core.database import Base
from backend.utils.compat import UTC

if TYPE_CHECKING:
    from backend.models.blog import Post
    from backend.models.user import User


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

    user: Mapped[User] = relationship("User", backref="favorite_folders")


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
        Integer,
        ForeignKey("favorite_folders.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    note: Mapped[str | None] = mapped_column(Text, nullable=True)  # 收藏备注
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(UTC), index=True
    )

    user: Mapped[User] = relationship("User")
    post: Mapped[Post] = relationship("Post")
    folder: Mapped[FavoriteFolder | None] = relationship("FavoriteFolder", backref="favorites")


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


# ==================== 响应体文档模型 ====================
# 仅用于 OpenAPI responses 声明（$ref 文档化），刻意不挂 response_model= 实体模型，
# 避免 Pydantic 序列化过滤抹掉运行时字段。


class FavoriteFolderItemOut(BaseModel):
    """收藏夹条目（含收藏数）"""

    id: int = Field(..., description="收藏夹 ID")
    name: str = Field(..., description="收藏夹名称")
    description: str | None = Field(None, description="收藏夹描述，未填写时为 null")
    is_public: bool = Field(..., description="是否公开（公开收藏夹可被他人浏览）")
    count: int = Field(..., description="该收藏夹内的收藏文章数量")
    created_at: str | None = Field(None, description="创建时间（ISO 8601 字符串）")


class FavoriteFolderListOut(BaseModel):
    """我的收藏夹列表"""

    items: list[FavoriteFolderItemOut] = Field(
        ..., description="收藏夹列表，按 order 升序、创建时间倒序"
    )
    total: int = Field(..., description="收藏夹总数")


class FavoriteFolderBriefOut(BaseModel):
    """创建收藏夹后回显的收藏夹摘要"""

    id: int = Field(..., description="新建收藏夹 ID")
    name: str = Field(..., description="收藏夹名称")
    description: str | None = Field(None, description="收藏夹描述，未填写时为 null")
    is_public: bool = Field(..., description="是否公开")


class FavoriteFolderCreateOut(BaseModel):
    """创建收藏夹响应"""

    success: bool = Field(True, description="操作是否成功")
    message: str = Field(..., description="人类可读操作结果提示")
    folder: FavoriteFolderBriefOut = Field(..., description="新建的收藏夹摘要")


class FavoriteActionResultOut(BaseModel):
    """收藏 CRUD 操作的统一结果"""

    success: bool = Field(True, description="操作是否成功")
    message: str = Field(..., description="人类可读操作结果提示（如「收藏成功」）")


class FavoritePostCategoryOut(BaseModel):
    """收藏列表中文章所属分类的摘要"""

    id: int = Field(..., description="分类 ID")
    name: dict[str, str] = Field(..., description="多语言分类名称 {zh,en,ja,zh_Hant}")
    color: str = Field(..., description="分类展示颜色（主题色令牌或十六进制色值）")


class FavoritePostOut(BaseModel):
    """收藏记录关联的文章摘要"""

    id: int = Field(..., description="文章 ID")
    title: dict[str, str] = Field(..., description="多语言文章标题 {zh,en,ja,zh_Hant}")
    slug: str = Field(..., description="文章 slug，用于 URL")
    cover_image: str | None = Field(None, description="封面图 URL，无封面时为 null")
    views: int = Field(..., description="浏览量")
    category: FavoritePostCategoryOut | None = Field(None, description="所属分类，未归类时为 null")
    published_at: str | None = Field(
        None, description="发布时间（ISO 8601 字符串），未发布（草稿）时为 null"
    )


class FavoriteItemOut(BaseModel):
    """单条收藏记录"""

    id: int = Field(..., description="收藏记录 ID")
    note: str | None = Field(None, description="收藏备注，未填写时为 null")
    folder_id: int | None = Field(None, description="所属收藏夹 ID，默认收藏（未归类）时为 null")
    created_at: str | None = Field(None, description="收藏时间（ISO 8601 字符串）")
    post: FavoritePostOut | None = Field(
        None, description="关联文章摘要；文章记录已被级联清理时为 null"
    )


class FavoriteListOut(BaseModel):
    """收藏分页列表"""

    items: list[FavoriteItemOut] = Field(..., description="本页收藏列表，按收藏时间倒序")
    total: int = Field(..., description="符合当前筛选（含 folder_id）的收藏总数")
    page: int = Field(..., description="当前页码，从 1 开始")
    page_size: int = Field(..., description="每页条数")
    total_pages: int = Field(..., description="总页数；total 为 0 时是 0")


class FavoriteRecordOut(BaseModel):
    """收藏记录原始行（移动收藏夹 / 更新备注成功后直接回显）"""

    id: int = Field(..., description="收藏记录 ID")
    user_id: int = Field(..., description="所属用户 ID")
    post_id: int = Field(..., description="被收藏的文章 ID")
    folder_id: int | None = Field(None, description="移动后的收藏夹 ID，移回默认收藏时为 null")
    note: str | None = Field(None, description="收藏备注，清空后为 null")
    created_at: str | None = Field(None, description="收藏时间（ISO 8601 字符串）")


class FavoriteCheckItemOut(BaseModel):
    """单篇文章的收藏状态"""

    is_favorited: bool = Field(..., description="当前用户是否已收藏该文章")
    favorite_id: int | None = Field(None, description="收藏记录 ID，未收藏时为 null")


class FavoriteCheckResultOut(BaseModel):
    """批量检查收藏状态响应"""

    favorites: dict[str, FavoriteCheckItemOut] = Field(
        ..., description="以文章 ID 字符串为键的收藏状态映射，覆盖请求中的全部 post_ids"
    )


# ==================== 收藏夹 API ====================


@router.get(
    "/folders",
    summary="我的收藏夹列表",
    description="获取当前用户的收藏夹列表（需登录），每项含该收藏夹内的收藏文章数量。",
    response_model=None,
    responses={200: {"model": FavoriteFolderListOut, "description": "收藏夹列表"}},
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

    # 每个收藏夹的文章数：一次 GROUP BY 取回。
    # 原先循环内逐条 COUNT，收藏夹越多首屏越慢（查询数线性增长）。
    folder_ids = [folder.id for folder in folders]
    count_map: dict[int, int] = {}
    if folder_ids:
        count_rows = await db.execute(
            select(Favorite.folder_id, func.count(Favorite.id))
            .where(Favorite.folder_id.in_(folder_ids))
            .group_by(Favorite.folder_id)
        )
        count_map = {int(folder_id): int(count) for folder_id, count in count_rows.all()}

    items = []
    for folder in folders:
        items.append(
            {
                "id": folder.id,
                "name": folder.name,
                "description": folder.description,
                "is_public": folder.is_public,
                "count": count_map.get(folder.id, 0),
                "created_at": folder.created_at.isoformat() if folder.created_at else None,
            }
        )

    return {"items": items, "total": len(items)}


@router.post(
    "/folders",
    summary="创建收藏夹",
    description="创建新的收藏夹（需登录）。成功后回显新收藏夹的 ID 与基本信息。",
    response_model=None,
    responses={200: {"model": FavoriteFolderCreateOut, "description": "创建结果与收藏夹摘要"}},
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
    description="更新收藏夹信息（需登录）。仅更新传入的字段；收藏夹不存在或不属于当前用户时 404。",
    response_model=None,
    responses={200: {"model": FavoriteActionResultOut, "description": "操作结果"}},
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
    description="删除收藏夹（需登录），收藏夹内的文章会移到默认收藏（folder_id 置空）而不被删除。",
    response_model=None,
    responses={200: {"model": FavoriteActionResultOut, "description": "操作结果"}},
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

    # 将收藏移到默认（folder_id = None）。显式 UPDATE 而不是依赖 FK 的
    # ON DELETE SET NULL：原先这里是一条结果被丢弃的 SELECT（空操作），
    # 行为全靠数据库 DDL 兜住，换成未建该约束的库就会级联删掉用户的收藏。
    await db.execute(update(Favorite).where(Favorite.folder_id == folder_id).values(folder_id=None))

    await db.delete(folder)
    await db.flush()

    return {"success": True, "message": "收藏夹已删除"}


# ==================== 收藏 API ====================


@router.get(
    "",
    summary="我的收藏列表",
    description="获取当前用户的收藏列表（需登录）。可按收藏夹筛选并分页；"
    "``total`` / ``total_pages`` 与该筛选同口径。",
    response_model=None,
    responses={200: {"model": FavoriteListOut, "description": "收藏分页列表"}},
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

    conditions = [Favorite.user_id == current_user.id]
    if folder_id:
        conditions.append(Favorite.folder_id == folder_id)

    query = (
        select(Favorite)
        .where(*conditions)
        .options(selectinload(Favorite.post).selectinload(Post.category))
        .order_by(Favorite.created_at.desc())
    )

    # 顺序查询（同一会话不能并发）。计数必须与列表同一套 WHERE：
    # 用未筛选的总数算 total_pages 时，按收藏夹过滤会宣称还有下一页、
    # 拉过去却是空的——分页契约（FavoriteListOut）本身就承诺 total 随筛选走。
    count_query = select(func.count()).select_from(Favorite).where(*conditions)

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
    description="收藏一篇文章（需登录）。文章不存在时 404；重复收藏时 400；"
    "指定 folder_id 时收藏夹必须属于当前用户，否则 404。",
    response_model=None,
    responses={200: {"model": FavoriteActionResultOut, "description": "操作结果"}},
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
    description="更新收藏信息（移动收藏夹、添加备注）。需登录；"
    "收藏不存在或不属于当前用户时 404，目标收藏夹非法时 404。",
    response_model=None,
    responses={200: {"model": FavoriteActionResultOut, "description": "操作结果"}},
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
    description="按收藏记录 ID 取消收藏（需登录）。收藏不存在或不属于当前用户时 404。",
    response_model=None,
    responses={200: {"model": FavoriteActionResultOut, "description": "操作结果"}},
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
    description="根据文章 ID 取消收藏（需登录）。该文章未被当前用户收藏时 404。",
    response_model=None,
    responses={200: {"model": FavoriteActionResultOut, "description": "操作结果"}},
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
    description="根据文章 ID 移动收藏到指定收藏夹（需登录，folder_id 传 null 表示移回默认收藏）。"
    "成功后直接回显更新后的收藏记录行；收藏或目标收藏夹不存在时 404。",
    response_model=None,
    responses={200: {"model": FavoriteRecordOut, "description": "更新后的收藏记录"}},
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
    await db.refresh(favorite)

    return favorite


@router.patch(
    "/post/{post_id}/note",
    summary="按文章ID更新备注",
    description="根据文章 ID 更新收藏备注（需登录，note 传 null 表示清空备注）。"
    "成功后直接回显更新后的收藏记录行；收藏不存在时 404。",
    response_model=None,
    responses={200: {"model": FavoriteRecordOut, "description": "更新后的收藏记录"}},
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
    await db.refresh(favorite)

    return favorite


@router.post(
    "/check",
    summary="检查收藏状态",
    description="批量检查多篇文章是否已被当前用户收藏（需登录）。"
    "响应以文章 ID 字符串为键，未收藏的文章 favorite_id 为 null。",
    response_model=None,
    responses={200: {"model": FavoriteCheckResultOut, "description": "按文章 ID 索引的收藏状态"}},
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
