"""
监控数据模型
"""

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from backend.core.database import Base


class VisitLog(Base):
    """访问日志"""

    __tablename__ = "visit_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    path: Mapped[str] = mapped_column(String(500), nullable=False, index=True)
    method: Mapped[str] = mapped_column(String(10), nullable=False)
    ip: Mapped[str | None] = mapped_column(String(50), nullable=True)
    user_agent: Mapped[str | None] = mapped_column(String(500), nullable=True)
    referer: Mapped[str | None] = mapped_column(String(500), nullable=True)
    user_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    status_code: Mapped[int] = mapped_column(Integer, nullable=False, default=200)
    response_time_ms: Mapped[float] = mapped_column(Integer, nullable=False, default=0)
    # 只有 cookie 的**名字**列表（`rosetta_lang; cf_clearance`），永远不存值。
    # 值是会话凭证（JWT / 会话 token），落进只增的遥测表等于把凭据写进日志 —— 见 AGENTS.md §12.5。
    cookie_names: Mapped[str | None] = mapped_column(String(255), nullable=True)
    accept_language: Mapped[str | None] = mapped_column(String(100), nullable=True)
    # 存布尔而不存系统/浏览器标签：这一列要在 SQL 里筛（60 万行分页），
    # 而"UA 里有没有 bot 标记"是稳定判据；os/浏览器/设备那三档给人看的标签
    # 一律读取时现算（规则改了历史行会跟着变），不写进表里固化一次误判。
    # 可为空：本列上线前的历史行是 NULL，页面按"未判定"显示，不硬猜成机器人。
    is_bot: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, index=True
    )
