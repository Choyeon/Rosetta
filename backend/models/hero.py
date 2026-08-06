"""
首页 Hero 轮播数据模型

支持图片/视频背景的首页 Hero 区，可配置多条幻灯片轮播。
媒体类型支持：image（静态图片）、video（自动播放视频）、youtube（YouTube嵌入）。
"""

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from backend.core.database import Base


class HeroSlide(Base):
    """
    首页 Hero 幻灯片

    Attributes:
        title: 主标题（支持多语言 JSON，如 {"zh": "标题", "en": "Title"}）
        subtitle: 副标题（同上）
        media_type: 媒体类型，image / video / youtube
        media_url: 媒体地址（图片URL/视频URL/YouTube视频ID）
        poster_url: 视频封面图（视频加载前显示）
        overlay_opacity: 遮罩透明度 0-100
        overlay_color: 遮罩颜色（CSS颜色值，默认 #000000）
        cta_text: 主按钮文案（多语言 JSON）
        cta_url: 主按钮链接
        cta_secondary_text: 次按钮文案（多语言 JSON）
        cta_secondary_url: 次按钮链接
        text_align: 文字对齐 left/center/right
        text_color: 文字颜色（亮色 light / 暗色 dark）
        is_active: 是否启用
        sort_order: 排序权重，越小越靠前
        start_time: 生效开始时间
        end_time: 生效结束时间
    """

    __tablename__ = "hero_slides"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    title: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON 多语言
    subtitle: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON 多语言
    media_type: Mapped[str] = mapped_column(String(20), default="image", nullable=False)
    media_url: Mapped[str] = mapped_column(String(500), nullable=False)
    poster_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    overlay_opacity: Mapped[int] = mapped_column(Integer, default=40, nullable=False)
    overlay_color: Mapped[str] = mapped_column(String(20), default="#000000", nullable=False)
    cta_text: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON 多语言
    cta_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    cta_secondary_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    cta_secondary_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    text_align: Mapped[str] = mapped_column(String(10), default="center", nullable=False)
    text_color: Mapped[str] = mapped_column(String(10), default="light", nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    start_time: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    end_time: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
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
        return f"<HeroSlide(id={self.id}, media_type='{self.media_type}')>"
