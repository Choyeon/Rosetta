"""
网站动态相关 Pydantic Schemas

定义活动/说说相关的请求和响应数据模型。
"""

from datetime import datetime
from typing import TYPE_CHECKING, Literal

from pydantic import BaseModel, Field

if TYPE_CHECKING:
    from backend.schemas import UserResponse


ActivityType = Literal["say", "article", "update", "notice"]


class ActivityBase(BaseModel):
    """活动基础模型"""

    content: dict[str, str] = Field(
        ...,
        description="多语言内容，如 {'zh': '内容', 'en': 'Content', 'ja': 'コンテンツ', 'zh_Hant': '內容'}",
    )
    type: ActivityType = Field(default="say", description="动态类型")
    is_published: bool = Field(default=True, description="是否已发布")


class ActivityCreate(ActivityBase):
    """活动创建模型"""

    pass


class ActivityUpdate(BaseModel):
    """活动更新模型"""

    content: dict[str, str] | None = None
    type: ActivityType | None = None
    is_published: bool | None = None


class ActivityResponse(BaseModel):
    """活动响应模型"""

    id: int
    content: dict[str, str]
    type: ActivityType
    author: "UserResponse"
    is_published: bool
    likes_count: int = 0
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ActivityLocalizedResponse(BaseModel):
    """活动本地化响应模型"""

    id: int
    content: str
    type: ActivityType
    author: "UserResponse"
    is_published: bool
    likes_count: int = 0
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_activity(cls, activity, lang: str = "zh") -> "ActivityLocalizedResponse":
        """从活动模型创建本地化响应"""
        from backend.core.i18n import get_i18n_value
        from backend.schemas import UserResponse

        return cls(
            id=activity.id,
            content=get_i18n_value(activity.content, lang),
            type=activity.type,
            author=UserResponse.model_validate(activity.author),
            is_published=activity.is_published,
            created_at=activity.created_at,
            updated_at=activity.updated_at,
        )


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
