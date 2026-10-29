"""
Hero 轮播相关 Pydantic Schema
"""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, field_validator

from backend.schemas._url_policy import reject_pseudo_url_scheme as _reject_pseudo_url_scheme
from backend.utils.compat import to_utc_instant

MediaType = Literal["image", "video", "youtube"]
TextAlign = Literal["left", "center", "right"]
TextColor = Literal["light", "dark"]


class HeroSlideBase(BaseModel):
    """Hero 幻灯片基础模型"""

    title: str | None = Field(None, description="主标题（多语言 JSON）")
    subtitle: str | None = Field(None, description="副标题（多语言 JSON）")
    media_type: MediaType = Field(default="image", description="媒体类型")
    media_url: str = Field(..., min_length=1, max_length=500, description="媒体地址")
    poster_url: str | None = Field(None, max_length=500, description="视频封面图")
    overlay_opacity: int = Field(default=40, ge=0, le=100, description="遮罩透明度 0-100")
    overlay_color: str = Field(default="#000000", max_length=20, description="遮罩颜色")
    cta_text: str | None = Field(None, description="主按钮文案（多语言 JSON）")
    cta_url: str | None = Field(None, max_length=500, description="主按钮链接")
    cta_secondary_text: str | None = Field(None, description="次按钮文案（多语言 JSON）")
    cta_secondary_url: str | None = Field(None, max_length=500, description="次按钮链接")
    text_align: TextAlign = Field(default="center", description="文字对齐")
    text_color: TextColor = Field(default="light", description="文字颜色主题")
    is_active: bool = Field(default=True, description="是否启用")
    sort_order: int = Field(default=0, ge=0, description="排序权重")
    start_time: datetime | None = Field(default=None, description="生效开始时间")
    end_time: datetime | None = Field(default=None, description="生效结束时间")


class HeroSlideCreate(HeroSlideBase):
    """创建 Hero 幻灯片"""

    # 只挂在写口，不挂 HeroSlideBase：HeroSlideResponse 继承 Base，挂在 Base 会让
    # `model_validate(ORM 行)` 也跑一遍——库里躺着历史脏值时公开口就从"渲染一条坏链接"
    # 变成整站 500。读侧的防线是前端 safeHeroHref 回落缺省，不是拒绝响应。
    @field_validator("cta_url", "cta_secondary_url")
    @classmethod
    def _reject_pseudo_scheme(cls, v: str | None) -> str | None:
        return _reject_pseudo_url_scheme(v)

    @field_validator("start_time", "end_time")
    @classmethod
    def _fold_to_utc_instant(cls, v: datetime | None) -> datetime | None:
        """朴素值直接进 `DateTime(timezone=True)` 会被 PG 按会话时区解释（实测偏 8 小时）。

        口径与理由见 `backend/utils/compat.py::to_utc_instant`。
        """
        return to_utc_instant(v)


class HeroSlideUpdate(BaseModel):
    """更新 Hero 幻灯片"""

    title: str | None = None
    subtitle: str | None = None
    media_type: MediaType | None = None
    media_url: str | None = Field(None, min_length=1, max_length=500)
    poster_url: str | None = Field(None, max_length=500)
    overlay_opacity: int | None = Field(None, ge=0, le=100)
    overlay_color: str | None = Field(None, max_length=20)
    cta_text: str | None = None
    cta_url: str | None = Field(None, max_length=500)
    cta_secondary_text: str | None = None
    cta_secondary_url: str | None = Field(None, max_length=500)
    text_align: TextAlign | None = None
    text_color: TextColor | None = None
    is_active: bool | None = None
    sort_order: int | None = Field(None, ge=0)
    start_time: datetime | None = None
    end_time: datetime | None = None

    # 与 HeroSlideCreate 同口径：PUT 也必须挡伪协议，否则"创建时拦住、改一下就有"。
    @field_validator("cta_url", "cta_secondary_url")
    @classmethod
    def _reject_pseudo_scheme(cls, v: str | None) -> str | None:
        return _reject_pseudo_url_scheme(v)

    # PUT 是这条守卫唯一会漏的第二个写口：只改一侧时另一侧走 exclude_unset 不进模型，
    # 但提交的那一侧仍必须是折算过的瞬时。
    @field_validator("start_time", "end_time")
    @classmethod
    def _fold_to_utc_instant(cls, v: datetime | None) -> datetime | None:
        return to_utc_instant(v)


class HeroSlideResponse(HeroSlideBase):
    """Hero 幻灯片响应模型"""

    id: int
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


from backend.schemas.strict_config import apply_strict_extra_forbid

apply_strict_extra_forbid(globals(), __name__)
