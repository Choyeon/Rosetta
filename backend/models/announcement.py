"""
网站公告数据模型

用于在站点顶部（navbar 下方）显示可关闭的公告条。
支持多种类型（info / warning / success / error）、定时显示与排序。
"""

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from backend.core.database import Base


class Announcement(Base):
    """
    网站公告

    Attributes:
        title: 公告标题
        content: 公告正文（纯文本或简单 Markdown）
        type: 公告类型，info / warning / success / error
        is_active: 是否启用
        is_dismissible: 是否允许用户关闭
        start_time: 生效开始时间（可空表示立即生效）
        end_time: 生效结束时间（可空表示长期有效）
        sort_order: 排序权重，越小越靠前
    """

    __tablename__ = "announcements"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    type: Mapped[str] = mapped_column(String(20), default="info", nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_dismissible: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    start_time: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    end_time: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
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

    def __repr__(self) -> str:
        return f"<Announcement(id={self.id}, title='{self.title}')>"
