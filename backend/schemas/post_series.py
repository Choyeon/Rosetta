"""
文章系列相关 Pydantic Schema
"""

from datetime import datetime

from pydantic import BaseModel, Field


class PostSeriesBase(BaseModel):
    """文章系列基础模型"""

    title: dict[str, str] = Field(..., description="多语言系列标题，如 {'zh': '...', 'en': '...'}")
    description: dict[str, str] | None = Field(None, description="多语言系列描述")
    slug: str = Field(
        ...,
        min_length=1,
        max_length=100,
        pattern=r"^[a-z0-9-]+$",
        description="唯一标识，用于 URL",
    )
    cover_image: str | None = Field(None, max_length=500, description="系列封面图 URL")
    is_active: bool = Field(default=True, description="是否启用")
    sort_order: int = Field(default=0, ge=0, description="排序权重，越小越靠前")


class PostSeriesCreate(PostSeriesBase):
    """文章系列创建模型"""

    pass


class PostSeriesUpdate(BaseModel):
    """文章系列更新模型"""

    title: dict[str, str] | None = None
    description: dict[str, str] | None = None
    slug: str | None = Field(None, min_length=1, max_length=100, pattern=r"^[a-z0-9-]+$")
    cover_image: str | None = Field(None, max_length=500)
    is_active: bool | None = None
    sort_order: int | None = Field(None, ge=0)


class PostSeriesResponse(PostSeriesBase):
    """文章系列响应模型"""

    id: int
    created_at: datetime
    updated_at: datetime
    post_count: int = 0

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
