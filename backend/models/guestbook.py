"""
留言板数据模型

独立 GuestbookEntry 表，避免与 Comment 模型的 post_id 必填语义冲突。
支持：登录用户/游客留言、审核工作流、置顶/精华、点赞、软删除（回收站）。
"""

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    false,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.core.database import Base

if TYPE_CHECKING:
    from backend.models.user import User


class GuestbookEntry(Base):
    """
    留言板条目

    扁平结构，无嵌套回复。与评论模型字段保持一致：
    - author_name/author_email/author_website/author_ip/author_user_agent
    - 敏感词过滤后的 status: approved|pending|rejected|spam
    - is_pinned / is_featured / likes_count
    - deleted_at 软删除（NULL=未删，非空=回收站）
    """

    __tablename__ = "guestbook_entries"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    user_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    user: Mapped["User | None"] = relationship("User")

    author_name: Mapped[str] = mapped_column(String(30), nullable=False)
    author_email: Mapped[str | None] = mapped_column(String(254), nullable=True)
    author_website: Mapped[str | None] = mapped_column(String(200), nullable=True)
    author_ip: Mapped[str | None] = mapped_column(String(64), nullable=True)
    author_user_agent: Mapped[str | None] = mapped_column(String(200), nullable=True)
    qq: Mapped[str | None] = mapped_column(
        String(20), nullable=True, index=True, comment="留言者 QQ（可选，游客填）"
    )
    github: Mapped[str | None] = mapped_column(
        String(64), nullable=True, comment="留言者 GitHub 用户名（可选，游客填）"
    )
    avatar_source: Mapped[str] = mapped_column(
        String(16), nullable=False, default="auto", server_default="auto",
        comment="头像来源：auto/custom/github/qq/gravatar",
    )

    content: Mapped[str] = mapped_column(Text, nullable=False)

    status: Mapped[str] = mapped_column(
        String(16), nullable=False, default="pending", server_default="pending", index=True
    )

    is_pinned: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default=false(), index=True
    )
    is_featured: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default=false()
    )

    likes_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")

    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, index=True
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    __table_args__ = (
        Index(
            "ix_guestbook_status_deleted_pinned_created",
            "status",
            "deleted_at",
            "is_pinned",
            "created_at",
        ),
        Index("ix_guestbook_author_ip_created", "author_ip", "created_at"),
    )

    def __repr__(self) -> str:
        return f"<GuestbookEntry(id={self.id}, status={self.status}, is_pinned={self.is_pinned})>"
