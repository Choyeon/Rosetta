"""
通知系统 API

支持站内通知、邮件通知等功能。
"""

import math

from fastapi import APIRouter, HTTPException, Query, WebSocket, WebSocketDisconnect, status
from sqlalchemy import func, select, update
from sqlalchemy.orm import selectinload

from backend.core.auth import DB, CurrentUser
from backend.core.concurrency import concurrent_query
from backend.models.core import Notification

router = APIRouter(tags=["通知"])


# WebSocket 连接管理
class ConnectionManager:
    """WebSocket 连接管理器"""

    def __init__(self):
        self.active_connections: dict[int, list[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, user_id: int):
        await websocket.accept()
        if user_id not in self.active_connections:
            self.active_connections[user_id] = []
        self.active_connections[user_id].append(websocket)

    def disconnect(self, websocket: WebSocket, user_id: int):
        if user_id in self.active_connections:
            self.active_connections[user_id].remove(websocket)
            if not self.active_connections[user_id]:
                del self.active_connections[user_id]

    async def send_to_user(self, user_id: int, message: dict):
        if user_id in self.active_connections:
            for connection in self.active_connections[user_id]:
                try:
                    await connection.send_json(message)
                except Exception:
                    pass


manager = ConnectionManager()


# ==================== 通知 API ====================


@router.get(
    "",
    summary="通知列表",
    description="获取当前用户的通知列表。",
)
async def list_notifications(
    db: DB,
    current_user: CurrentUser,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    unread_only: bool = Query(False, description="只显示未读"),
):
    """获取通知列表"""
    query = select(Notification).where(Notification.recipient_id == current_user.id)

    if unread_only:
        query = query.where(Notification.is_read.is_(False))

    query = query.options(selectinload(Notification.actor)).order_by(Notification.created_at.desc())

    # 并发查询
    count_query = select(func.count()).select_from(query.subquery())
    unread_query = select(func.count()).select_from(
        select(Notification)
        .where(Notification.recipient_id == current_user.id, Notification.is_read.is_(False))
        .subquery()
    )

    total, unread_count, result = await concurrent_query(
        db.scalar(count_query),
        db.scalar(unread_query),
        db.execute(query.offset((page - 1) * page_size).limit(page_size)),
    )

    notifications = result.scalars().all()
    total = total or 0
    unread_count = unread_count or 0

    items = []
    for n in notifications:
        items.append(
            {
                "id": n.id,
                "level": n.level,
                "title": n.title,
                "message": n.message,
                "verb": n.verb,
                "link": n.link,
                "is_read": n.is_read,
                "actor": {
                    "id": n.actor.id,
                    "username": n.actor.username,
                    "nickname": n.actor.nickname,
                    "avatar": n.actor.avatar,
                }
                if n.actor
                else None,
                "created_at": n.created_at.isoformat() if n.created_at else None,
            }
        )

    return {
        "items": items,
        "total": total,
        "unread_count": unread_count,
        "page": page,
        "page_size": page_size,
        "total_pages": math.ceil(total / page_size) if total > 0 else 0,
    }


@router.get(
    "/unread-count",
    summary="未读通知数",
    description="获取当前用户的未读通知数量。",
)
async def get_unread_count(
    db: DB,
    current_user: CurrentUser,
):
    """获取未读通知数"""
    count = (
        await db.scalar(
            select(func.count())
            .select_from(Notification)
            .where(
                Notification.recipient_id == current_user.id,
                Notification.is_read.is_(False),
            )
        )
        or 0
    )

    return {"unread_count": count}


@router.get(
    "/stats",
    summary="通知统计",
    description="获取当前用户的通知统计信息。",
)
async def get_notification_stats(
    db: DB,
    current_user: CurrentUser,
):
    """获取通知统计"""
    total_count = (
        await db.scalar(
            select(func.count())
            .select_from(Notification)
            .where(
                Notification.recipient_id == current_user.id,
            )
        )
        or 0
    )

    unread_count = (
        await db.scalar(
            select(func.count())
            .select_from(Notification)
            .where(
                Notification.recipient_id == current_user.id,
                Notification.is_read.is_(False),
            )
        )
        or 0
    )

    read_count = total_count - unread_count

    type_stats = await db.execute(
        select(
            Notification.verb,
            func.count().label("count"),
        )
        .where(Notification.recipient_id == current_user.id)
        .group_by(Notification.verb)
    )

    type_distribution = {}
    for row in type_stats:
        type_distribution[row.notification_type] = row.count

    return {
        "total": total_count,
        "unread": unread_count,
        "read": read_count,
        "type_distribution": type_distribution,
    }


@router.post(
    "/{notification_id}/read",
    summary="标记已读",
    description="标记单条通知为已读。",
)
async def mark_as_read(
    notification_id: int,
    db: DB,
    current_user: CurrentUser,
):
    """标记通知为已读"""
    notification = await db.get(Notification, notification_id)
    if not notification or notification.recipient_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="通知不存在",
        )

    notification.is_read = True
    await db.flush()

    return {"success": True, "message": "已标记为已读"}


@router.post(
    "/read-all",
    summary="全部已读",
    description="标记所有通知为已读。",
)
async def mark_all_as_read(
    db: DB,
    current_user: CurrentUser,
):
    """标记所有通知为已读"""
    await db.execute(
        update(Notification)
        .where(Notification.recipient_id == current_user.id, Notification.is_read.is_(False))
        .values(is_read=True)
    )
    await db.flush()

    return {"success": True, "message": "已全部标记为已读"}


@router.delete(
    "/{notification_id}",
    summary="删除通知",
    description="删除单条通知。",
)
async def delete_notification(
    notification_id: int,
    db: DB,
    current_user: CurrentUser,
):
    """删除通知"""
    notification = await db.get(Notification, notification_id)
    if not notification or notification.recipient_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="通知不存在",
        )

    await db.delete(notification)
    await db.flush()

    return {"success": True, "message": "通知已删除"}


@router.delete(
    "",
    summary="清空通知",
    description="清空所有通知或已读通知。",
)
async def clear_notifications(
    db: DB,
    current_user: CurrentUser,
    read_only: bool = Query(False, description="只清空已读通知"),
):
    """清空通知"""
    query = select(Notification).where(Notification.recipient_id == current_user.id)
    if read_only:
        query = query.where(Notification.is_read.is_(True))

    result = await db.execute(query)
    notifications = result.scalars().all()

    count = 0
    for n in notifications:
        await db.delete(n)
        count += 1

    await db.flush()

    return {"success": True, "message": f"已清空 {count} 条通知"}


# ==================== WebSocket ====================


@router.websocket("/ws")
async def websocket_notifications(websocket: WebSocket):
    """WebSocket 实时通知"""
    await websocket.accept()

    user_id = None

    try:
        while True:
            data = await websocket.receive_json()

            if data.get("type") == "auth":
                # 验证用户
                from backend.core.auth import decode_token

                token = data.get("token")
                if token:
                    payload = decode_token(token)
                    if payload:
                        user_id = payload.get("sub")
                        if user_id:
                            manager.connect(websocket, int(user_id))
                            await websocket.send_json({"type": "auth", "status": "success"})

            elif data.get("type") == "ping":
                await websocket.send_json({"type": "pong"})

    except WebSocketDisconnect:
        if user_id:
            manager.disconnect(websocket, int(user_id))


# ==================== 内部函数 ====================


async def create_notification(
    db,
    recipient_id: int,
    actor_id: int,
    verb: str,
    title: dict,
    message: dict,
    link: str | None = None,
    level: str = "info",
    content_type: str | None = None,
    object_id: int | None = None,
):
    """
    创建通知

    内部函数，用于创建并发送通知。
    """
    notification = Notification(
        recipient_id=recipient_id,
        actor_id=actor_id,
        verb=verb,
        title=title,
        message=message,
        link=link,
        level=level,
        content_type=content_type,
        object_id=object_id,
    )
    db.add(notification)
    await db.flush()
    await db.refresh(notification)

    # 通过 WebSocket 发送实时通知
    await manager.send_to_user(
        recipient_id,
        {
            "type": "notification",
            "id": notification.id,
            "title": title,
            "message": message,
            "link": link,
            "level": level,
            "created_at": notification.created_at.isoformat() if notification.created_at else None,
        },
    )

    return notification
