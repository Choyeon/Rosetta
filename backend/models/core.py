"""
核心功能数据模型

包含页面、导航、友链、媒体、通知、站点配置等模型。
支持多语言字段。
"""

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.core.database import Base

if TYPE_CHECKING:
    from backend.models.user import User


class Page(Base):
    """
    独立页面

    用于创建关于、友链等独立页面，支持 Markdown 格式。
    支持多语言标题和内容。
    """

    __tablename__ = "pages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    title: Mapped[dict] = mapped_column(JSON, nullable=False)  # 多语言页面标题
    slug: Mapped[str] = mapped_column(
        String(200), unique=True, nullable=False, index=True
    )  # URL 别名
    content: Mapped[dict] = mapped_column(JSON, nullable=False)  # 多语言页面内容
    status: Mapped[str] = mapped_column(
        String(10), default="published", nullable=False
    )  # draft/published

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    def __repr__(self) -> str:
        title = self.title.get("zh", "Untitled") if self.title else "Untitled"
        return f"<Page(id={self.id}, title='{title}')>"


class Navigation(Base):
    """
    导航菜单

    网站顶部/底部/侧边栏的导航链接。
    支持多语言标题、图标、多级菜单。
    """

    __tablename__ = "navigations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    title: Mapped[dict] = mapped_column(JSON, nullable=False)  # 多语言显示文本
    url: Mapped[str] = mapped_column(String(200), nullable=False)  # 链接地址
    icon: Mapped[str | None] = mapped_column(String(100), nullable=True)  # 图标名称
    parent_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("navigations.id", ondelete="CASCADE"), nullable=True
    )  # 父导航ID
    parent: Mapped["Navigation | None"] = relationship(
        "Navigation", remote_side=[id], backref="children"
    )
    location: Mapped[str] = mapped_column(
        String(20), default="header", nullable=False
    )  # 位置：header/footer/sidebar
    order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)  # 排序权重
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)  # 是否启用
    target_blank: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)  # 新窗口打开

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    def __repr__(self) -> str:
        title = self.title.get("zh", "Untitled") if self.title else "Untitled"
        return f"<Navigation(id={self.id}, title='{title}')>"


class FriendLink(Base):
    """
    友情链接

    网站底部的友链列表。
    支持多语言名称和描述。
    """

    __tablename__ = "friend_links"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[dict] = mapped_column(JSON, nullable=False)  # 多语言网站名称
    url: Mapped[str] = mapped_column(String(500), nullable=False)  # 网站地址
    description: Mapped[dict | None] = mapped_column(JSON, nullable=True)  # 多语言网站描述
    logo: Mapped[str | None] = mapped_column(String(500), nullable=True)  # 网站 Logo
    order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)  # 排序权重
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)  # 是否启用
    target_blank: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)  # 新窗口打开

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    def __repr__(self) -> str:
        name = self.name.get("zh", "Unnamed") if self.name else "Unnamed"
        return f"<FriendLink(id={self.id}, name='{name}')>"


class SearchPlaceholder(Base):
    """
    搜索框占位符

    搜索框显示的随机提示文本。
    支持多语言文本。
    """

    __tablename__ = "search_placeholders"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    text: Mapped[dict] = mapped_column(JSON, nullable=False)  # 多语言占位符文本
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)  # 是否启用
    order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)  # 排序权重

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    def __repr__(self) -> str:
        text = self.text.get("zh", "Untitled") if self.text else "Untitled"
        return f"<SearchPlaceholder(id={self.id}, text='{text}')>"


class Media(Base):
    """
    媒体文件

    上传的图片、视频等媒体资源。
    """

    __tablename__ = "media"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    file: Mapped[str] = mapped_column(String(500), nullable=False)  # 文件路径
    filename: Mapped[str | None] = mapped_column(String(255), nullable=True)  # 原始文件名
    file_type: Mapped[str] = mapped_column(
        String(20), default="other", nullable=False
    )  # 文件类型：image/video/audio/other
    file_size: Mapped[int] = mapped_column(Integer, default=0, nullable=False)  # 文件大小（字节）

    # 元信息
    title: Mapped[str | None] = mapped_column(String(255), nullable=True)  # 标题
    alt_text: Mapped[str | None] = mapped_column(String(255), nullable=True)  # 替代文本
    description: Mapped[str | None] = mapped_column(Text, nullable=True)  # 描述

    # 上传者
    uploaded_by_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    uploaded_by: Mapped["User | None"] = relationship("User")

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    def __repr__(self) -> str:
        return f"<Media(id={self.id}, filename='{self.filename}')>"


class Notification(Base):
    """
    通知消息

    系统通知、评论回复提醒等。
    支持多语言标题和内容。
    """

    __tablename__ = "notifications"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # 接收者
    recipient_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    recipient: Mapped["User"] = relationship(
        "User", back_populates="notifications", foreign_keys=[recipient_id]
    )

    # 触发者
    actor_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    actor: Mapped["User"] = relationship(
        "User", back_populates="triggered_notifications", foreign_keys=[actor_id]
    )

    # 动作类型
    verb: Mapped[str] = mapped_column(String(255), nullable=False)  # 动作描述

    # 关联对象
    content_type: Mapped[str | None] = mapped_column(String(100), nullable=True)  # 对象类型
    object_id: Mapped[int | None] = mapped_column(Integer, nullable=True)  # 对象 ID

    # 通知内容（多语言）
    title: Mapped[dict] = mapped_column(JSON, nullable=False)  # 多语言通知标题
    message: Mapped[dict] = mapped_column(JSON, nullable=False)  # 多语言通知内容
    level: Mapped[str] = mapped_column(
        String(20), default="info", nullable=False
    )  # 级别：info/success/warning/error
    link: Mapped[str | None] = mapped_column(String(255), nullable=True)  # 跳转链接
    is_read: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)  # 是否已读

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, index=True
    )

    def __repr__(self) -> str:
        title = self.title.get("zh", "Untitled") if self.title else "Untitled"
        return f"<Notification(id={self.id}, title='{title}')>"


class SiteConfig(Base):
    """
    站点配置

    存储网站的全局配置，以键值对形式保存。
    """

    __tablename__ = "site_configs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    key: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)  # 配置键
    value: Mapped[str] = mapped_column(Text, nullable=False)  # 配置值
    description: Mapped[str | None] = mapped_column(String(255), nullable=True)  # 配置说明

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    def __repr__(self) -> str:
        return f"<SiteConfig(key='{self.key}')>"
