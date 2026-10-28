"""
网站动态相关 Pydantic Schemas

定义活动/说说相关的请求和响应数据模型。
"""

from datetime import datetime
from typing import TYPE_CHECKING, Literal

from pydantic import BaseModel, Field, field_validator

from backend.schemas._i18n_dict import I18nDict

if TYPE_CHECKING:
    from backend.schemas import PublicUserResponse


ActivityType = Literal["say", "article", "update", "notice", "link"]

# 每种语言正文的字符上限。这是动态唯一的长度闸门：模型侧的 ``content`` 是 JSON 列，
# 没有列宽限制，而 ``POST /activities`` 对任何登录用户开放——没有上限时，一个脚本就能把
# 动态表与按语言分键的响应缓存（每页 4 个键）无上限地撑大。
MAX_ACTIVITY_CONTENT_CHARS = 1000


def _bound_activity_content(value: dict[str, str] | None) -> dict[str, str] | None:
    if value is None:
        return None
    too_long = [
        code
        for code, text in value.items()
        if isinstance(text, str) and len(text) > MAX_ACTIVITY_CONTENT_CHARS
    ]
    if too_long:
        codes = ", ".join(sorted(too_long))
        raise ValueError(f"动态内容过长（每种语言最多 {MAX_ACTIVITY_CONTENT_CHARS} 字）：{codes}")
    return value


class ActivityBase(BaseModel):
    """活动基础模型"""

    content: dict[str, str] = Field(
        ...,
        description="多语言内容，如 {'zh': '内容', 'en': 'Content', 'ja': 'コンテンツ', 'zh_Hant': '內容'}",
    )
    type: ActivityType = Field(default="say", description="动态类型")
    is_published: bool = Field(default=True, description="是否已发布")

    @field_validator("content")
    @classmethod
    def _content_within_limit(cls, value: dict[str, str]) -> dict[str, str]:
        return _bound_activity_content(value)


class ActivityCreate(ActivityBase):
    """活动创建模型"""

    pass


class ActivityUpdate(BaseModel):
    """活动更新模型"""

    content: dict[str, str] | None = None
    type: ActivityType | None = None
    is_published: bool | None = None

    @field_validator("content")
    @classmethod
    def _content_within_limit(cls, value: dict[str, str] | None) -> dict[str, str] | None:
        return _bound_activity_content(value)


class ActivityResponse(BaseModel):
    """活动响应模型"""

    id: int
    content: I18nDict
    type: ActivityType
    author: "PublicUserResponse"
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
    author: "PublicUserResponse"
    is_published: bool
    likes_count: int = 0
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_activity(cls, activity, lang: str = "zh") -> "ActivityLocalizedResponse":
        """从活动模型创建本地化响应"""
        from backend.api._user_response_helper import build_public_user_response
        from backend.core.i18n import get_i18n_value

        return cls(
            id=activity.id,
            content=get_i18n_value(activity.content, lang),
            type=activity.type,
            author=build_public_user_response(activity.author),
            is_published=activity.is_published,
            # 漏传这一行时前台永远显示 0 赞：模型默认值是 0，序列化不会报错，
            # 只有真点一次赞再读公开列表才暴露（回归见 tests/test_admin_activity_crud.py）
            likes_count=activity.likes_count,
            created_at=activity.created_at,
            updated_at=activity.updated_at,
        )


from backend.schemas.strict_config import apply_strict_extra_forbid

apply_strict_extra_forbid(globals(), __name__)
