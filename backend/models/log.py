"""
操作日志模型

记录系统中的重要操作，用于审计和问题追踪。
"""

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.core.database import Base


class OperationLog(Base):
    """
    操作日志

    记录用户的操作行为，支持审计追踪。
    """

    __tablename__ = "operation_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # 操作用户
    user_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    user: Mapped["User | None"] = relationship("User")

    # 操作类型
    action: Mapped[str] = mapped_column(
        String(50), nullable=False, index=True
    )  # create/update/delete/publish/etc

    # 操作对象
    resource_type: Mapped[str] = mapped_column(String(50), nullable=False)  # post/user/comment/etc
    resource_id: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # 操作详情
    detail: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON 格式的详情

    # 请求信息
    ip_address: Mapped[str | None] = mapped_column(String(45), nullable=True)
    user_agent: Mapped[str | None] = mapped_column(String(500), nullable=True)
    request_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    request_method: Mapped[str | None] = mapped_column(String(10), nullable=True)

    # 状态
    status: Mapped[str] = mapped_column(String(20), default="success")  # success/failed
    error_code: Mapped[str | None] = mapped_column(String(100), nullable=True)

    # 时间戳
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, index=True
    )

    def __repr__(self) -> str:
        return f"<OperationLog(id={self.id}, action={self.action}, resource={self.resource_type})>"


class TrashItem(Base):
    """
    回收站项目

    软删除的内容暂存，支持恢复或永久删除。
    """

    __tablename__ = "trash_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # 原始数据
    resource_type: Mapped[str] = mapped_column(
        String(50), nullable=False, index=True
    )  # post/comment/page
    resource_id: Mapped[int] = mapped_column(Integer, nullable=False)
    resource_data: Mapped[str] = mapped_column(Text, nullable=False)  # JSON 格式的完整数据

    # 删除信息
    deleted_by_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    deleted_by: Mapped["User | None"] = relationship("User")

    # 自动清理时间
    auto_delete_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # 时间戳
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    def __repr__(self) -> str:
        return (
            f"<TrashItem(id={self.id}, type={self.resource_type}, resource_id={self.resource_id})>"
        )
