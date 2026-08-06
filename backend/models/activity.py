"""
网站动态（说说/活动）数据模型

支持说说、文章发布、更新、通知等多种动态类型。
支持多语言内容（zh/en/ja/zh_Hant）。
"""

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import JSON, Boolean, DateTime, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.core.database import Base

if TYPE_CHECKING:
    from backend.models.user import User


class Activity(Base):
    """
    网站动态

    Attributes:
        content: 多语言内容，如 {"zh": "内容", "en": "Content", "ja": "コンテンツ", "zh_Hant": "內容"}
        type: 动态类型：say（说说）/article（文章发布）/update（更新）/notice（通知）
        author_id: 作者ID
        author: 作者对象
        is_published: 是否已发布
        created_at: 创建时间
        updated_at: 更新时间
    """

    __tablename__ = "activities"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    content: Mapped[dict] = mapped_column(JSON, nullable=False)
    type: Mapped[str] = mapped_column(String(20), default="say", nullable=False, index=True)
    author_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    author: Mapped["User"] = relationship("User", foreign_keys=[author_id])
    is_published: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False, index=True)
    likes_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, index=True
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    def __repr__(self) -> str:
        content = self.content.get("zh", "Untitled") if self.content else "Untitled"
        return f"<Activity(id={self.id}, type='{self.type}', content='{content[:30]}...')>"
