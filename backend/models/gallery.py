"""
相册（Gallery）数据模型

包含相册 Album 和照片 Photo 两个核心实体。
- Album: 相册集合，支持排序、发布状态、封面
- Photo: 单张照片，属于某个相册，支持排序和描述
"""

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.core.database import Base

if TYPE_CHECKING:
    from backend.models.user import User


class Album(Base):
    """
    相册模型

    Attributes:
        title: 相册标题（多语言 dict 或纯字符串，统一存储为 JSON 兼容字符串）
        description: 相册描述
        cover: 封面图片 URL
        sort_order: 排序权重（越小越靠前）
        is_published: 是否公开
        created_at: 创建时间
        updated_at: 更新时间
        author_id: 创建者
        author: 创建者对象
        photos: 相册内照片列表
    """

    __tablename__ = "albums"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    cover: Mapped[str | None] = mapped_column(String(500), nullable=True)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    is_published: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default="true", index=True
    )
    photo_count: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0"
    )

    author_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    author: Mapped["User | None"] = relationship("User", foreign_keys=[author_id])

    photos: Mapped[list["Photo"]] = relationship(
        "Photo",
        back_populates="album",
        cascade="all, delete-orphan",
        order_by="Photo.sort_order.asc(), Photo.id.asc()",
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, index=True
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    def __repr__(self) -> str:
        return f"<Album(id={self.id}, title='{self.title[:30]}...')>"


class Photo(Base):
    """
    照片模型

    Attributes:
        album_id: 所属相册 ID
        album: 所属相册对象
        title: 照片标题
        description: 照片描述
        url: 照片 URL（必填）
        sort_order: 排序权重
        created_at: 创建时间
    """

    __tablename__ = "photos"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    album_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("albums.id", ondelete="CASCADE"), nullable=False, index=True
    )
    album: Mapped[Album] = relationship("Album", back_populates="photos")

    title: Mapped[str | None] = mapped_column(String(200), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    url: Mapped[str] = mapped_column(String(500), nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, index=True
    )

    def __repr__(self) -> str:
        return f"<Photo(id={self.id}, album_id={self.album_id}, url='{self.url[:50]}...')>"
