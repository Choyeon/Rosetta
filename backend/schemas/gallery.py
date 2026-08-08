"""
相册（Gallery）相关 Pydantic Schemas

定义 Album/Photo 的创建、更新、响应模型。
"""

from datetime import datetime

from pydantic import BaseModel, Field

# ================= Album =================


class AlbumBase(BaseModel):
    """相册基础字段"""

    title: str = Field(..., min_length=1, max_length=200, description="相册标题")
    description: str | None = Field(None, max_length=2000, description="相册描述")
    cover: str | None = Field(None, max_length=500, description="封面 URL")
    sort_order: int = Field(0, ge=0, description="排序权重（越小越靠前）")
    is_published: bool = Field(True, description="是否公开")


class AlbumCreate(AlbumBase):
    """创建相册请求"""

    pass


class AlbumUpdate(BaseModel):
    """更新相册请求（所有字段可选）"""

    title: str | None = Field(None, min_length=1, max_length=200)
    description: str | None = Field(None, max_length=2000)
    cover: str | None = Field(None, max_length=500)
    sort_order: int | None = Field(None, ge=0)
    is_published: bool | None = None


class AlbumResponse(AlbumBase):
    """相册响应（含 id/时间/数量 等）"""

    id: int
    photo_count: int = 0
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class AlbumDetailResponse(AlbumResponse):
    """相册详情响应（包含照片列表）"""

    photos: list["PhotoResponse"] = []


# ================= Photo =================


class PhotoBase(BaseModel):
    """照片基础字段"""

    title: str | None = Field(None, max_length=200, description="照片标题")
    description: str | None = Field(None, max_length=2000, description="照片描述")
    url: str = Field(..., min_length=1, max_length=500, description="照片 URL")
    sort_order: int = Field(0, ge=0, description="排序权重")


class PhotoCreate(PhotoBase):
    """创建照片请求"""

    album_id: int = Field(..., ge=1, description="所属相册 ID")


class PhotoUpdate(BaseModel):
    """更新照片请求（所有字段可选）"""

    title: str | None = Field(None, max_length=200)
    description: str | None = Field(None, max_length=2000)
    url: str | None = Field(None, min_length=1, max_length=500)
    sort_order: int | None = Field(None, ge=0)
    album_id: int | None = Field(None, ge=1)


class PhotoResponse(PhotoBase):
    """照片响应"""

    id: int
    album_id: int
    created_at: datetime

    model_config = {"from_attributes": True}


# 解决前向引用
AlbumDetailResponse.model_rebuild()


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
