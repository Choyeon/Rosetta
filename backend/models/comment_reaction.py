"""
评论表情反应数据模型

允许用户对评论添加表情反应（如 👍❤️🎉😄😢😡），
同一用户对同一评论的同一表情只能反应一次。
"""

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from backend.core.database import Base


class CommentReaction(Base):
    """
    评论表情反应

    Attributes:
        comment_id: 关联的评论 ID
        user_id: 反应用户 ID
        emoji: 表情符号（如 👍❤️🎉😄😢😡）
        created_at: 反应时间
    """

    __tablename__ = "comment_reactions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    comment_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("comments.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    emoji: Mapped[str] = mapped_column(String(20), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    __table_args__ = (
        Index(
            "ix_comment_reactions_unique",
            "comment_id",
            "user_id",
            "emoji",
            unique=True,
        ),
    )

    def __repr__(self) -> str:
        return (
            f"<CommentReaction(id={self.id}, comment_id={self.comment_id}, emoji='{self.emoji}')>"
        )
