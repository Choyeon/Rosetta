"""
插件与主题数据模型

提供 WordPress 风格的插件和主题元数据存储，
支持多租户隔离、版本管理、状态管理。
"""

from datetime import datetime

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from backend.core.config import settings
from backend.core.database import Base
from backend.core.tenant import TenantMixin

JSON_TYPE = JSONB if settings.is_postgresql else JSON


class Plugin(Base, TenantMixin):
    """
    插件元数据

    存储已安装插件的版本、状态、设置 Schema 等信息。
    每个站点（site_id）下的插件 slug 唯一。
    """

    __tablename__ = "plugins"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    slug: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    version: Mapped[str] = mapped_column(String(32), nullable=False)
    author: Mapped[str | None] = mapped_column(String(200))
    description: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(
        String(16),
        nullable=False,
        default="inactive",
        server_default="inactive",
        index=True,
        comment="inactive|active|error|installed",
    )
    manifest_version: Mapped[str] = mapped_column(
        String(8), nullable=False, default="1.0", server_default="1.0"
    )
    requires_rosetta: Mapped[str | None] = mapped_column(String(16))
    plugin_uri: Mapped[str | None] = mapped_column(String(500))
    author_uri: Mapped[str | None] = mapped_column(String(500))
    textdomain: Mapped[str | None] = mapped_column(String(64))
    folder: Mapped[str] = mapped_column(
        String(300), nullable=False, comment="relative folder under backend/plugins/"
    )
    settings_schema: Mapped[dict | None] = mapped_column(JSON_TYPE, nullable=True, default=None)
    install_path: Mapped[str | None] = mapped_column(String(500))
    installed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    activated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    __table_args__ = (
        UniqueConstraint("site_id", "slug", name="uq_plugins_site_slug"),
        {"comment": "Plugins installed metadata"},
    )

    def __repr__(self) -> str:
        return f"<Plugin(id={self.id}, slug='{self.slug}', status='{self.status}')>"


class Theme(Base, TenantMixin):
    """
    主题元数据

    存储已安装主题的版本、状态、Mods Schema 等信息。
    每个站点（site_id）下的主题 slug 唯一。
    支持子主题（parent_theme）机制。
    """

    __tablename__ = "themes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    slug: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    version: Mapped[str] = mapped_column(String(32), nullable=False)
    author: Mapped[str | None] = mapped_column(String(200))
    description: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(
        String(16),
        nullable=False,
        default="installed",
        server_default="installed",
        index=True,
        comment="installed|active|error",
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="false", index=True
    )
    manifest_version: Mapped[str] = mapped_column(
        String(8), nullable=False, default="1.0", server_default="1.0"
    )
    requires_rosetta: Mapped[str | None] = mapped_column(String(16))
    theme_uri: Mapped[str | None] = mapped_column(String(500))
    author_uri: Mapped[str | None] = mapped_column(String(500))
    textdomain: Mapped[str | None] = mapped_column(String(64))
    folder: Mapped[str] = mapped_column(
        String(300), nullable=False, comment="relative folder under frontend/themes/"
    )
    mods_schema: Mapped[dict | None] = mapped_column(JSON_TYPE, nullable=True)
    parent_theme: Mapped[str | None] = mapped_column(String(100), nullable=True)
    screenshot_urls: Mapped[list | None] = mapped_column(JSON_TYPE, nullable=True, default=lambda: [])
    tags: Mapped[list | None] = mapped_column(JSON_TYPE, nullable=True, default=lambda: [])
    install_path: Mapped[str | None] = mapped_column(String(500))
    installed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    activated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    __table_args__ = (
        UniqueConstraint("site_id", "slug", name="uq_themes_site_slug"),
        {"comment": "Themes installed metadata"},
    )

    def __repr__(self) -> str:
        return f"<Theme(id={self.id}, slug='{self.slug}', is_active={self.is_active})>"
