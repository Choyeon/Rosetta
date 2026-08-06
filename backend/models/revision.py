"""
文章修订版本模型

支持文章编辑历史追踪和版本回滚。
"""

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.core.database import Base


class PostRevision(Base):
    """
    文章修订版本

    保存文章的每次编辑历史，支持版本对比和回滚。
    """

    __tablename__ = "post_revisions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # 关联文章
    post_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("posts.id", ondelete="CASCADE"), nullable=False, index=True
    )

    # 版本号（自动递增）
    revision_number: Mapped[int] = mapped_column(Integer, nullable=False)

    # 快照数据
    title: Mapped[dict] = mapped_column(Text, nullable=False)  # JSON 多语言标题
    content: Mapped[dict] = mapped_column(Text, nullable=False)  # JSON 多语言内容
    excerpt: Mapped[dict | None] = mapped_column(Text, nullable=True)  # JSON 多语言摘要

    # 编辑信息
    author_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    author: Mapped["User | None"] = relationship("User")

    # 变更说明
    change_summary: Mapped[str | None] = mapped_column(String(500), nullable=True)

    # 时间戳
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    def __repr__(self) -> str:
        return f"<PostRevision(id={self.id}, post_id={self.post_id}, rev={self.revision_number})>"
