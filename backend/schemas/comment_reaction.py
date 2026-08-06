"""
评论表情反应相关 Pydantic Schema
"""

from datetime import datetime

from pydantic import BaseModel, Field


class CommentReactionCreate(BaseModel):
    """评论表情反应创建模型"""

    emoji: str = Field(..., min_length=1, max_length=20, description="表情符号")


class CommentReactionResponse(BaseModel):
    """评论表情反应响应模型"""

    id: int
    comment_id: int
    user_id: int
    emoji: str
    created_at: datetime

    model_config = {"from_attributes": True}


class CommentReactionSummary(BaseModel):
    """评论表情反应汇总（按表情分组）"""

    emoji: str
    count: int
    reacted: bool = Field(default=False, description="当前用户是否已添加该表情")


class CommentReactionSummaryList(BaseModel):
    """评论表情反应汇总列表"""

    comment_id: int
    reactions: list[CommentReactionSummary]
    total: int


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
