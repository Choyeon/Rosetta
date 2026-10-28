"""
文章系列相关 Pydantic Schema
"""

from datetime import datetime

from pydantic import BaseModel, Field

from backend.schemas._i18n_dict import I18nDict
from backend.schemas._slug import CONTENT_SLUG_PATTERN


class PostSeriesBase(BaseModel):
    """文章系列基础模型"""

    # `PostSeriesResponse` 直接继承这两个字段，所以归一类型写在 Base 上：匿名列表口
    # `GET /api/series` 用 `model_validate`/构造时，库里躺裸字符串的旧行会让整口 500。
    # 副作用是创建口也接受裸串并折成 `{zh: 原文}` 落库——比 422 更不像 bug。
    title: I18nDict = Field(..., description="多语言系列标题，如 {'zh': '...', 'en': '...'}")
    description: I18nDict | None = Field(None, description="多语言系列描述")
    slug: str = Field(
        ...,
        min_length=1,
        max_length=100,
        pattern=CONTENT_SLUG_PATTERN,
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
    slug: str | None = Field(None, min_length=1, max_length=100, pattern=CONTENT_SLUG_PATTERN)
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


from backend.schemas.strict_config import apply_strict_extra_forbid

apply_strict_extra_forbid(globals(), __name__)
