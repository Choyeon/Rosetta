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


from backend.schemas.strict_config import apply_strict_extra_forbid

apply_strict_extra_forbid(globals(), __name__)
