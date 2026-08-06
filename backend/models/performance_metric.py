"""
性能监控指标数据模型

记录 API 请求的响应时间、状态码等信息，用于性能分析。
"""

from datetime import datetime

from sqlalchemy import DateTime, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from backend.core.database import Base


class PerformanceMetric(Base):
    """
    API 性能指标

    Attributes:
        endpoint: 请求路径
        method: HTTP 方法
        status_code: HTTP 状态码
        response_time_ms: 响应时间（毫秒）
        user_agent: 用户代理（可空）
        ip: 客户端 IP（可空）
        created_at: 记录时间（索引）
    """

    __tablename__ = "performance_metrics"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    endpoint: Mapped[str] = mapped_column(String(500), nullable=False)
    method: Mapped[str] = mapped_column(String(10), nullable=False)
    status_code: Mapped[int] = mapped_column(Integer, nullable=False)
    response_time_ms: Mapped[int] = mapped_column(Integer, nullable=False)
    user_agent: Mapped[str | None] = mapped_column(String(500), nullable=True)
    ip: Mapped[str | None] = mapped_column(String(50), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        index=True,
    )

    def __repr__(self) -> str:
        return (
            f"<PerformanceMetric(id={self.id}, {self.method} {self.endpoint}, "
            f"{self.status_code}, {self.response_time_ms}ms)>"
        )
