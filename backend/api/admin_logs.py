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
from sqlalchemy import and_, desc, func, or_, select

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


@router.get("/logs")
async def list_operation_logs(
    db: DB,
    current_user: CurrentStaff,
    user_id: int | None = Query(None, description="用户 id 过滤"),
    action: str | None = Query(None, description="动作过滤"),
    target_type: str | None = Query(None, description="对象类型过滤（等价 resource_type）"),
    from_date: str | None = Query(None, alias="from", description="开始日期 ISO"),
    to_date: str | None = Query(None, alias="to", description="结束日期 ISO"),
    q: str | None = Query(None, description="关键词搜索(details/error_code/ip)"),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
):
    from_dt = _parse_date(from_date)
    to_dt = _parse_date(to_date)

    conditions = []
    if user_id is not None:
        conditions.append(OperationLog.user_id == user_id)
    if action:
        conditions.append(OperationLog.action == action)
    if target_type:
        conditions.append(OperationLog.resource_type == target_type)
    if from_dt:
        conditions.append(OperationLog.created_at >= from_dt)
    if to_dt:
        conditions.append(OperationLog.created_at <= to_dt)
    if q:
        like = f"%{q}%"
        conditions.append(
            or_(
                OperationLog.detail.like(like),
                OperationLog.error_code.like(like),
                OperationLog.ip_address.like(like),
                OperationLog.request_path.like(like),
            )
        )

    where = and_(*conditions) if conditions else True

    total = await db.scalar(select(func.count()).select_from(OperationLog).where(where)) or 0

    stmt = (
        select(OperationLog)
        .where(where)
        .order_by(desc(OperationLog.created_at))
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    rows = (await db.execute(stmt)).scalars().all()

    user_ids: list[int] = [r.user_id for r in rows if r.user_id is not None]
    user_map: dict[int, User] = {}
    if user_ids:
        urows = (await db.execute(select(User).where(User.id.in_(user_ids)))).scalars().all()
        user_map = {u.id: u for u in urows}

    items = [_row_to_dict(r, user_map) for r in rows]

    return {
        "items": items,
        "total": int(total),
        "page": page,
        "page_size": page_size,
        "pages": (int(total) + page_size - 1) // page_size if page_size else 0,
    }


class _RetentionResponse(BaseModel):
    deleted_count: int
    before: str


@router.delete("/logs/retention")
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
