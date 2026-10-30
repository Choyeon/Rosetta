"""
自定义内容类型（Content Type）模型。

Rosetta 的文章（Post）除内置标题、正文、slug 等通用字段外，还可通过
「自定义内容类型」扩展元数据字段。例如：

- 书籍（book）：作者 / 出版社 / 出版年份 / ISBN
- 视频（video）：时长 / B站链接 / 封面图

约定：
- ``ContentTypeDefinition`` 是 ORM 模型，存在 ``content_types`` 表；
- 字段定义通过 ``fields`` JSON 列存储为 ``list[ContentField]``；
- 定义管理与「文章写入口按定义校验 ``meta_fields``」的实现在
  ``backend/services/content_type_service.py``（写口校验）与
  ``backend/api/content_type.py``（定义 CRUD）；本模型只承担数据契约。
- **读侧比写侧宽**：定义可以在有文章之后被改字段（改标签/删字段/改可选性），
  历史行里因此可能留着今日定义之外的键。公开详情照原样下发 ``meta_fields``，
  渲染侧只展示"定义里存在且值非空"的键——不得在读侧按定义重新校验，否则
  一次定义调整会让一批文章详情整条 500（与 hero 响应模型同一类事故）。
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, model_validator
from pydantic import Field as PDField
from sqlalchemy import JSON, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from backend.core.database import Base
from backend.core.tenant import TenantMixin

FIELD_TYPES: tuple[str, ...] = (
    "text",
    "textarea",
    "number",
    "boolean",
    "select",
    "date",
    "datetime",
    "image",
    "url",
    "markdown",
)


class ContentField(BaseModel):
    """自定义字段定义（非 ORM，作为 ContentTypeDefinition.fields 的元素）。

    ``key`` 是写进 ``Post.meta_fields`` 的 JSON 键，一旦有文章用了就不能改名
    （改名等于让旧值变成"未知字段"，见 content_type_service 的校验）。
    ``default`` 只在编辑器里预填，**不会**在写入时替作者补值：必填字段缺值必须
    显式报 422，静默补默认值会让"我以为没填就不该保存"变成看不见的写入。
    """

    key: str = PDField(
        ...,
        min_length=1,
        max_length=64,
        pattern=r"^[a-z][a-z0-9_]{0,63}$",
        description="字段英文键（小写字母开头，仅小写字母/数字/下划线），用作 meta key",
    )
    label: str = PDField(..., min_length=1, max_length=128, description="后台与前台展示名")
    field_type: str = PDField(
        "text",
        pattern=r"^(" + "|".join(FIELD_TYPES) + r")$",
        description="字段类型",
    )
    required: bool = PDField(False, description="是否必填")
    default: Any = PDField(None, description="编辑器预填的默认值（写入时不自动补）")
    description: str | None = PDField(None, max_length=512, description="字段说明/帮助文本")
    options: list[str] | None = PDField(
        None, max_length=100, description="select 类型的候选项（其它类型必须为空）"
    )

    model_config = {"extra": "forbid"}

    @model_validator(mode="after")
    def _validate_shape(self) -> ContentField:
        options = [opt.strip() for opt in (self.options or [])]
        if any(not opt for opt in options):
            raise ValueError("候选项不能为空串")
        if len(set(options)) != len(options):
            raise ValueError("候选项不能重复")
        if self.field_type == "select":
            if not options:
                raise ValueError("select 类型至少需要一个候选项")
        elif options:
            raise ValueError("只有 select 类型可以声明候选项")
        self.options = options or None
        return self


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
    description: Mapped[str | None] = mapped_column(Text, nullable=True, comment="内容类型用途描述")
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

    def __repr__(self) -> str:  # pragma: no cover - debug helper
        return f"<ContentTypeDefinition key={self.key!r} name={self.name!r}>"
