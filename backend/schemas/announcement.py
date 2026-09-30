"""
公告相关 Pydantic Schema
"""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, field_validator, model_validator

from backend.utils.compat import UTC

AnnouncementType = Literal["info", "warning", "success", "error"]

# 公告正文上限。横幅是「站点顶部一行」，不是正文渲染位（渲染侧见
# composables/useAnnouncementBar.ts::stripInlineMarkdown，只做 Markdown 降级不做完整排版）；
# 不加上限时管理员可以把整篇文章粘进来，SSR 首屏与公开接口响应体一起膨胀，
# 而访客实际看到的只有前几个字。
ANNOUNCEMENT_CONTENT_MAX_LENGTH = 2000


def ensure_utc(value: datetime | None) -> datetime | None:
    """朴素时间一律按 UTC 补齐 tzinfo（与 utils/compat.parse_utc_date 同口径）。

    start_time / end_time 列是 `DateTime(timezone=True)`。若让朴素值直接入库，
    SQLite 存成朴素串、PG 存成瞬时，而过滤时用的是 `datetime.now(UTC)`（带 tz），
    跨库比对结果不一致；更糟的是"一端朴素一端带 tz"直接撞 TypeError → 500。
    这里统一补 UTC，让比较永远有定义。
    """
    if value is None or value.tzinfo is not None:
        return value
    return value.replace(tzinfo=UTC)


class AnnouncementBase(BaseModel):
    """公告基础模型"""

    title: str = Field(..., min_length=1, max_length=200, description="公告标题")
    content: str = Field(
        ...,
        min_length=1,
        max_length=ANNOUNCEMENT_CONTENT_MAX_LENGTH,
        description="公告正文",
    )
    type: AnnouncementType = Field(default="info", description="公告类型")
    is_active: bool = Field(default=True, description="是否启用")
    is_dismissible: bool = Field(default=True, description="是否允许用户关闭")
    start_time: datetime | None = Field(default=None, description="生效开始时间")
    end_time: datetime | None = Field(default=None, description="生效结束时间")
    sort_order: int = Field(default=0, ge=0, description="排序权重，越小越靠前")

    @field_validator("start_time", "end_time", mode="after")
    @classmethod
    def _normalize_timezone(cls, value: datetime | None) -> datetime | None:
        return ensure_utc(value)

    @model_validator(mode="after")
    def _check_time_window(self):
        """结束时间必须晚于开始时间。

        倒挂的窗口不会报错：公开接口的过滤条件是 `start<=now AND end>=now`，
        永远不成立，于是公告被存下来、接口返回 201、前台却一条都不显示，
        管理员没有任何反馈可查。这里在写入前就拦成 422。
        """
        if self.start_time and self.end_time and self.end_time <= self.start_time:
            raise ValueError("结束时间必须晚于开始时间")
        return self


class AnnouncementCreate(AnnouncementBase):
    """公告创建模型"""

    pass


class AnnouncementUpdate(BaseModel):
    """公告更新模型"""

    title: str | None = Field(None, min_length=1, max_length=200)
    content: str | None = Field(None, min_length=1, max_length=ANNOUNCEMENT_CONTENT_MAX_LENGTH)
    type: AnnouncementType | None = None
    is_active: bool | None = None
    is_dismissible: bool | None = None
    start_time: datetime | None = None
    end_time: datetime | None = None
    sort_order: int | None = Field(None, ge=0)

    @field_validator("start_time", "end_time", mode="after")
    @classmethod
    def _normalize_timezone(cls, value: datetime | None) -> datetime | None:
        return ensure_utc(value)

    @model_validator(mode="after")
    def _check_time_window(self):
        """两边都显式给到时才能在这里判（局部更新看不到库里的旧值）。

        只给了其中一边的情形必须由 API 层 `validate_window` 拿现有行合并后再判——
        否则"把 end_time 改到 start_time 之前"这种最常见的误操作会从这里漏过去。
        """
        if self.start_time and self.end_time and self.end_time <= self.start_time:
            raise ValueError("结束时间必须晚于开始时间")
        return self


class AnnouncementResponse(AnnouncementBase):
    """公告响应模型"""

    id: int
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


from backend.schemas.strict_config import apply_strict_extra_forbid

apply_strict_extra_forbid(globals(), __name__)
