"""
公告相关 Pydantic Schema
"""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

AnnouncementType = Literal["info", "warning", "success", "error"]


class AnnouncementBase(BaseModel):
    """公告基础模型"""

    title: str = Field(..., min_length=1, max_length=200, description="公告标题")
    content: str = Field(..., min_length=1, description="公告正文")
    type: AnnouncementType = Field(default="info", description="公告类型")
    is_active: bool = Field(default=True, description="是否启用")
    is_dismissible: bool = Field(default=True, description="是否允许用户关闭")
    start_time: datetime | None = Field(default=None, description="生效开始时间")
    end_time: datetime | None = Field(default=None, description="生效结束时间")
    sort_order: int = Field(default=0, ge=0, description="排序权重，越小越靠前")


class AnnouncementCreate(AnnouncementBase):
    """公告创建模型"""

    pass


class AnnouncementUpdate(BaseModel):
    """公告更新模型"""

    title: str | None = Field(None, min_length=1, max_length=200)
    content: str | None = None
    type: AnnouncementType | None = None
    is_active: bool | None = None
    is_dismissible: bool | None = None
    start_time: datetime | None = None
    end_time: datetime | None = None
    sort_order: int | None = Field(None, ge=0)


class AnnouncementResponse(AnnouncementBase):
    """公告响应模型"""

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
