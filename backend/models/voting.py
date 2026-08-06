"""
投票相关数据模型

包含投票、选项、投票记录等模型。

PostgreSQL 优化：
- 添加复合索引优化投票统计查询
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
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.core.database import Base

if TYPE_CHECKING:
    from backend.models.user import User


class Poll(Base):
    """
    投票主题

    支持单选和多选投票，可控制是否显示结果。

    PostgreSQL 优化：添加索引优化查询
    """

    __tablename__ = "polls"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False, index=True)
    allow_multiple: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    show_results: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, index=True
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    choices: Mapped[list["Choice"]] = relationship(
        "Choice", back_populates="poll", cascade="all, delete-orphan"
    )
    votes: Mapped[list["Vote"]] = relationship(
        "Vote", back_populates="poll", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Poll(id={self.id}, title='{self.title}')>"


class Choice(Base):
    """
    投票选项

    每个投票可以有多个选项。

    PostgreSQL 优化：添加索引优化查询
    """

    __tablename__ = "choices"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    poll_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("polls.id", ondelete="CASCADE"), nullable=False, index=True
    )
    poll: Mapped["Poll"] = relationship("Poll", back_populates="choices")

    text: Mapped[str] = mapped_column(String(200), nullable=False)
    order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    votes: Mapped[list["Vote"]] = relationship(
        "Vote", back_populates="choice", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Choice(id={self.id}, text='{self.text}')>"


class Vote(Base):
    """
    投票记录

    记录每次投票，支持匿名投票。

    PostgreSQL 优化：添加复合索引优化统计查询
    """

    __tablename__ = "votes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    poll_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("polls.id", ondelete="CASCADE"), nullable=False, index=True
    )
    poll: Mapped["Poll"] = relationship("Poll", back_populates="votes")

    choice_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("choices.id", ondelete="CASCADE"), nullable=False, index=True
    )
    choice: Mapped["Choice"] = relationship("Choice", back_populates="votes")

    user_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    user: Mapped["User | None"] = relationship("User")

    ip_address: Mapped[str | None] = mapped_column(String(45), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    __table_args__ = (
        Index("ix_votes_poll_choice", "poll_id", "choice_id"),
        Index("ix_votes_user_poll", "user_id", "poll_id"),
    )

    def __repr__(self) -> str:
        return f"<Vote(id={self.id}, poll_id={self.poll_id})>"
