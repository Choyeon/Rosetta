"""
文章系列数据模型

用于将多篇相关文章组织为一个系列，支持多语言标题和描述。
Post 模型通过 series_id 外键关联到本表。
"""

from datetime import datetime

from sqlalchemy import JSON, Boolean, DateTime, Integer, String, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.core.config import settings
from backend.core.database import Base

JSON_TYPE = JSONB if settings.is_postgresql else JSON


class PostSeries(Base):
    """
    文章系列

    用于将多篇相关文章组织为一个系列（如教程连载、专题合集）。
    支持多语言标题和描述，独立的 slug 用于 URL。

    Attributes:
        title: 多语言系列标题
        description: 多语言系列描述
        slug: 唯一标识，用于 URL
        cover_image: 系列封面图 URL
        is_active: 是否启用（启用的系列才会在前台展示）
        sort_order: 排序权重，越小越靠前
        posts: 该系列下的文章列表（通过 Post.series_id 关联）
    """

    __tablename__ = "post_series"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    title: Mapped[dict] = mapped_column(JSON_TYPE, nullable=False)
    description: Mapped[dict | None] = mapped_column(JSON_TYPE, nullable=True)
    slug: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    cover_image: Mapped[str | None] = mapped_column(String(500), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    posts: Mapped[list["Post"]] = relationship(
        "Post",
        backref="series",
        order_by="Post.series_order",
    )

    def __repr__(self) -> str:
        title = self.title.get("zh", "Untitled") if self.title else "Untitled"
        return f"<PostSeries(id={self.id}, title='{title}')>"
