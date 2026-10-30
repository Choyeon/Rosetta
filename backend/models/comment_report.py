"""
评论举报数据模型

前台访客或登录用户对一条评论发起举报，后台在「评论 → 举报」页按状态处理。

口径（与 ``Comment.reported_at`` 的分工）：
- 本表是**举报明细**：谁、什么理由、什么时候、处理结果；
- ``Comment.reported_at`` 是**待处理标记**：只要这条评论还有一条 open 的举报就非空，
  最后一条被处理后清回 NULL。后台「仅看被举报」列表查的是这个标记（单表单列，
  不用 EXISTS 子查询），明细页查本表。
"""

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from backend.core.database import Base


class CommentReport(Base):
    """一条评论举报

    Attributes:
        comment_id: 被举报的评论
        post_id: 冗余的文章外键：后台列表要按文章跳转且举报行数远小于评论数，
            存下来就不必每次 JOIN 两跳（评论删除时整行级联消失）
        reporter_user_id: 举报人是登录用户时记 user_id，游客为 NULL
        reporter_ip: 举报时的客户端 IP（游客去重与滥用排查用；不对外展示）
        reason: spam / abuse / offtopic / other
        detail: 补充说明（可选，≤500 字）
        status: open / handled / dismissed
        handled_by_id: 处理人（staff），未处理为 NULL
        handled_at: 处理时间，未处理为 NULL
    """

    __tablename__ = "comment_reports"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    comment_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("comments.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    post_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("posts.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    reporter_user_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    reporter_ip: Mapped[str | None] = mapped_column(String(64), nullable=True)
    reason: Mapped[str] = mapped_column(String(16), nullable=False)
    detail: Mapped[str | None] = mapped_column(String(500), nullable=True)
    status: Mapped[str] = mapped_column(
        String(16), nullable=False, default="open", server_default="open", index=True
    )
    handled_by_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    handled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, index=True
    )

    __table_args__ = (
        Index("ix_comment_reports_comment_status", "comment_id", "status"),
        {"comment": "评论举报明细（Comment.reported_at 是它的待处理标记）"},
    )

    def __repr__(self) -> str:
        return (
            f"<CommentReport(id={self.id}, comment_id={self.comment_id}, "
            f"reason='{self.reason}', status='{self.status}')>"
        )
