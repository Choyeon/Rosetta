"""
操作日志管理 API

GET    /api/admin/logs                  分页查询
DELETE /api/admin/logs/retention        清理 N 天前日志
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timedelta
from typing import Any

from fastapi import APIRouter, HTTPException, Query, Request, status
from pydantic import BaseModel
from sqlalchemy import func, select

from backend.core.auth import DB, CurrentStaff
from backend.core.logging_middleware import log_operation
from backend.models.log import OperationLog
from backend.models.user import User
from backend.utils.compat import UTC

logger = logging.getLogger(__name__)

router = APIRouter(prefix="", tags=["操作日志"])


def _parse_date(s: str | None) -> datetime | None:
    if not s:
        return None
    try:
        d = datetime.fromisoformat(s.replace("Z", "+00:00"))
        if d.tzinfo is None:
            d = d.replace(tzinfo=UTC)
        return d
    except Exception:
        return None


def _row_to_dict(row: OperationLog, user_map: dict[int, User] | None = None) -> dict[str, Any]:
    user_name = None
    user_avatar = None
    if row.user_id and user_map and row.user_id in user_map:
        u = user_map[row.user_id]
        user_name = getattr(u, "nickname", None) or getattr(u, "username", None)
        user_avatar = getattr(u, "avatar", None)
    details: Any = None
    if row.detail:
        try:
            details = json.loads(row.detail)
        except Exception:
            details = row.detail
    return {
        "id": row.id,
        "user_id": row.user_id,
        "user_name": user_name,
        "user_avatar": user_avatar,
        "action": row.action,
        "target_type": row.resource_type,  # alias target_type
        "target_id": row.resource_id,  # alias target_id
        "details": details,
        "ip": row.ip_address,
        "user_agent": row.user_agent,
        "request_path": row.request_path,
        "request_method": row.request_method,
        "status": row.status,
        "error_code": row.error_code,
        "created_at": row.created_at.isoformat() if row.created_at else None,
    }


# 说明：GET /api/admin/logs 的统一实现位于 backend/api/advanced.py（其 APIRouter 内部
# prefix="/admin"，随主应用挂载于 /api，与本模块曾注册的路由同路径；该实现返回 total_pages 与
# 嵌套 user，且注册顺序在前、运行时优先生效）。此处不再重复注册，以消除同路径同方法的重复路由
# 与 OpenAPI operationId 冲突；保留下方 DELETE /logs/retention 清理接口。
class _RetentionResponse(BaseModel):
    deleted_count: int
    before: str


@router.delete(
    "/logs/retention",
    summary="清理旧日志",
    description="按保留天数删除早于 N 天的操作日志记录。",
)
async def cleanup_old_logs(
    request: Request,
    db: DB,
    current_user: CurrentStaff,
    days: int = Query(7, ge=1, le=3650, description="保留天数，删除早于 N 天的记录"),
):
    if not (current_user.is_superuser or current_user.is_staff):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "需要管理员权限")

    cutoff = datetime.now(UTC) - timedelta(days=days)
    from sqlalchemy import delete

    sub = select(OperationLog.id).where(OperationLog.created_at < cutoff)
    count_q = select(func.count()).select_from(sub)
    to_delete = await db.scalar(count_q) or 0

    if to_delete:
        await db.execute(delete(OperationLog).where(OperationLog.created_at < cutoff))

    await log_operation(
        db,
        request,
        user_id=current_user.id,
        action="delete",
        target_type="logs",
        target_id=None,
        details={"days": days, "deleted_count": int(to_delete), "cutoff": cutoff.isoformat()},
        status="success",
    )
    await db.commit()

    return _RetentionResponse(deleted_count=int(to_delete), before=cutoff.isoformat())
