"""
Hero 轮播相关 Pydantic Schema
"""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

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

    pass


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


class HeroSlideResponse(HeroSlideBase):
    """Hero 幻灯片响应模型"""

    id: int
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


import sys as _sys  # noqa: E402

_STRICT_EXTRA_FORBID = {"strict": True, "extra": "forbid"}
for _name in list(globals().keys()):
    _obj = globals()[_name]
    if (
        isinstance(_obj, type)
        and issubclass(_obj, BaseModel)
        and _obj is not BaseModel
        and _obj.__module__ == _sys.modules[__name__].__name__
    ):
        _existing = _obj.model_config if isinstance(_obj.model_config, dict) else {}
        _merged = {**_existing, **_STRICT_EXTRA_FORBID}
        try:
            _obj.model_config = _merged
        except Exception:
            pass
    del _name, _obj
