"""
Rosetta 多站点 Site 模型（骨架）。

当前单站点形态下数据库中恒定只有一条 id=DEFAULT_SITE_ID=1 的记录；
多站点启用后会由配置写入多条记录，tenant_middleware 会解析 domain/slug。
"""

from __future__ import annotations

from sqlalchemy import Boolean, Column, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, validates

from backend.core.database import Base
from backend.core.tenant import DEFAULT_SITE_ID, TenantMixin


class Site(Base, TenantMixin):
    __tablename__ = "sites"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    slug: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        unique=True,
        index=True,
        comment="站点短标识，用于 /s/{slug} 路由",
    )
    name: Mapped[str] = mapped_column(String(128), nullable=False, comment="站点名称")
    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="站点简介（tagline/subtitle）",
    )
    domain: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        index=True,
        comment="绑定的域名（多站点启用时按 Host 匹配）",
    )
    is_default: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default="false",
        comment="是否为默认站点（Host 匹配失败时回退）",
    )
    locale: Mapped[str] = mapped_column(
        String(16),
        nullable=False,
        default="zh",
        server_default="zh",
        comment="站点默认语言：zh/en/ja/zh_Hant",
    )
    timezone: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        default="Asia/Shanghai",
        server_default="Asia/Shanghai",
        comment="站点时区（IANA）",
    )

    __table_args__ = (
        UniqueConstraint("site_id", "slug", name="uq_sites_site_slug"),
        {"comment": "多站点：站点元数据表（单站点时仅含 1 条 id=1 默认行）"},
    )

    @validates("site_id")
    def _site_id_default(self, key, value):  # noqa: ARG002 - signature convention
        return value if value is not None else DEFAULT_SITE_ID

    def __repr__(self) -> str:  # pragma: no cover - debug helper
        return f"<Site id={self.id} slug={self.slug!r} name={self.name!r}>"
