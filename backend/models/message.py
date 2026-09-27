"""私信模型"""

from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Integer, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.core.database import Base


class PrivateMessage(Base):
    """私信模型"""

    __tablename__ = "private_messages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    sender_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="发送者ID",
    )
    recipient_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="接收者ID",
    )
    content: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        comment="消息内容",
    )
    is_read: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        comment="是否已读",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        comment="创建时间",
    )

    __table_args__ = (
        # 未读角标与会话列表的 COUNT 都是 `WHERE recipient_id = ? AND is_read = false`
        # （messages.py 未读数 / 按对端分组）；recipient_id 单列索引要把已读行一起捞出来。
        Index("ix_private_messages_recipient_read", "recipient_id", "is_read"),
    )

    sender = relationship("User", foreign_keys=[sender_id], backref="sent_messages")
    recipient = relationship("User", foreign_keys=[recipient_id], backref="received_messages")

    def __repr__(self) -> str:
        return f"<PrivateMessage(id={self.id}, sender_id={self.sender_id}, recipient_id={self.recipient_id})>"
