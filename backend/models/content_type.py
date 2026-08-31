"""
自定义内容类型（Content Type）模型。

Rosetta 的文章（Post）除内置标题、正文、slug 等通用字段外，还可通过
「自定义内容类型」扩展元数据字段。例如：

- 书籍（book）：作者 / 出版社 / 出版年份 / ISBN
- 视频（video）：时长 / B站链接 / 封面图

约定：
- ``ContentTypeDefinition`` 是 ORM 模型，存在 ``content_types`` 表；
- 字段定义通过 ``fields`` JSON 列存储为 ``list[ContentField]``；
- 业务层使用 ``services.content_type_service`` 做：
    * 动态生成 Pydantic schema
    * 校验 & 打包 meta_fields（JSON blob 存入 Post.meta_fields）
    * 读取 meta_fields 中的单字段值
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field as PDField
from sqlalchemy import JSON, Column, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from backend.core.database import Base
from backend.core.tenant import DEFAULT_SITE_ID, TenantMixin


class ContentField(BaseModel):
    """自定义字段定义（非 ORM，作为 ContentTypeDefinition.fields 的元素）。"""

    key: str = PDField(..., min_length=1, max_length=64, description="字段英文键，用作 meta key")
    label: str = PDField(..., min_length=1, max_length=128, description="中文显示名")
    field_type: str = PDField(
        "text",
        pattern=r"^(text|textarea|number|boolean|select|date|datetime|image|url|markdown)$",
        description="字段类型",
    )
    required: bool = PDField(False, description="是否必填")
    default: Any = PDField(None, description="默认值")
    description: str | None = PDField(None, max_length=512, description="字段说明/帮助文本")
    options: list[str] | None = PDField(
        None, description="select 类型的候选项（text 等类型忽略）"
    )

    model_config = {"extra": "forbid"}


class ContentTypeDefinition(Base, TenantMixin):
    """自定义内容类型 ORM 模型。"""

    __tablename__ = "content_types"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    key: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        index=True,
        comment="内容类型唯一键，例：book / video / portfolio",
    )
    name: Mapped[str] = mapped_column(
        String(128), nullable=False, comment="中文显示名，例：书籍 / 视频"
    )
    icon: Mapped[str | None] = mapped_column(
        String(64), nullable=True, comment="Lucide / 自定义图标名称"
    )
    description: Mapped[str | None] = mapped_column(
        Text, nullable=True, comment="内容类型用途描述"
    )
    fields: Mapped[list[dict]] = mapped_column(
        JSON,
        nullable=False,
        default=list,
        comment="自定义字段定义 JSON：list[ContentField.dict()]",
    )

    __table_args__ = (
        UniqueConstraint("site_id", "key", name="uq_content_types_site_key"),
        {"comment": "自定义内容类型定义（给 Post.post_type 做扩展字段）"},
    )

    @property
    def parsed_fields(self) -> list[ContentField]:
        """返回解析后的 ContentField 列表（懒解析 + 兼容异常值）。"""
        if not self.fields:
            return []
        parsed: list[ContentField] = []
        for raw in self.fields:
            if isinstance(raw, ContentField):
                parsed.append(raw)
            elif isinstance(raw, dict):
                try:
                    parsed.append(ContentField.model_validate(raw))
                except Exception:
                    # 脏数据跳过，避免整体 schema 加载失败
                    continue
        return parsed

    # 为列显式声明 SQLAlchemy 字段（mapped_column(JSON) + site_id TenantMixin）
    # 保证 Column 级反射/迁移识别
    _ = Column("site_id_fallback_placeholder", Integer, comment="占位，不影响建表") if False else None

    def __repr__(self) -> str:  # pragma: no cover - debug helper
        return f"<ContentTypeDefinition key={self.key!r} name={self.name!r}>"
