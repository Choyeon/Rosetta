"""
通知系统 API

支持站内通知、邮件通知等功能。
"""

import logging
import math

from fastapi import APIRouter, HTTPException, Query, WebSocket, WebSocketDisconnect, status
from pydantic import BaseModel, Field
from sqlalchemy import delete, func, select, update
from sqlalchemy.orm import selectinload

from backend.core.auth import DB, CurrentUser
from backend.core.concurrency import concurrent_query
from backend.models.core import Notification

logger = logging.getLogger(__name__)

router = APIRouter(tags=["通知"])


# ==================== 响应体文档模型 ====================
# 仅用于 OpenAPI responses 声明（$ref 文档化），刻意不挂 response_model=，
# 避免 Pydantic 序列化过滤抹掉运行时字段。


class NotificationActorOut(BaseModel):
    """通知触发者的公开资料"""

    id: int = Field(..., description="触发者用户 ID")
    username: str = Field(..., description="用户名")
    nickname: str | None = Field(None, description="昵称，未设置时为 null")
    avatar: str | None = Field(None, description="头像 URL，未设置时为 null")


class NotificationItemOut(BaseModel):
    """单条站内通知"""

    id: int = Field(..., description="通知 ID")
    level: str = Field(..., description="通知级别：info / success / warning / error")
    title: dict[str, str] | str = Field(
        ...,
        description="通知标题；系统通知为多语言字典 {zh,en,ja,zh_Hant}，"
        "留言/评论等 UGC 通知为明文字符串（不自动翻译）",
    )
    message: dict[str, str] | str = Field(..., description="通知正文，多语言口径同 title")
    verb: str = Field(..., description="动作类型标识（如评论回复、留言通过等），统计接口按此分组")
    link: str | None = Field(None, description="点击通知跳转的目标链接，可为 null")
    is_read: bool = Field(..., description="是否已读")
    actor: NotificationActorOut | None = Field(
        None, description="触发该通知的用户，系统通知时为 null"
    )
    created_at: str | None = Field(
        None, description="创建时间（ISO 8601 字符串），异常数据下可为 null"
    )


class NotificationListOut(BaseModel):
    """通知分页列表"""

    items: list[NotificationItemOut] = Field(..., description="本页通知列表，按创建时间倒序")
    total: int = Field(..., description="符合筛选条件的通知总数（非本页条数）")
    unread_count: int = Field(..., description="当前用户全部未读通知数，用于角标展示")
    page: int = Field(..., description="当前页码，从 1 开始")
    page_size: int = Field(..., description="每页条数")
    total_pages: int = Field(..., description="总页数；total 为 0 时是 0")


class NotificationUnreadCountOut(BaseModel):
    """未读通知数"""

    unread_count: int = Field(..., description="当前用户的未读通知数量")


class NotificationStatsOut(BaseModel):
    """通知统计"""

    total: int = Field(..., description="通知总数")
    unread: int = Field(..., description="未读通知数")
    read: int = Field(..., description="已读通知数（total - unread）")
    type_distribution: dict[str, int] = Field(
        ..., description="按 verb 分组的通知数量统计，键为动作类型、值为条数"
    )


class NotificationActionResultOut(BaseModel):
    """标记已读 / 删除 / 清空类操作的统一结果"""

    success: bool = Field(True, description="操作是否成功")
    message: str = Field(..., description="人类可读操作结果提示（如「已标记为已读」）")


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
        connections = self.active_connections.get(user_id)
        if not connections:
            return
        stale: list[WebSocket] = []
        for connection in list(connections):
            try:
                await connection.send_json(message)
            except (WebSocketDisconnect, RuntimeError) as exc:
                # RuntimeError 是 starlette 对「连接已关闭还继续 send」的报错。
                # 原先 `except Exception: pass` 只吞掉错误，僵尸连接永远留在
                # active_connections 里：既泄漏对象，又让每次推送重复撞上同一条死连接。
                logger.debug(f"[ws] 推送失败，摘除 user={user_id} 的连接: {exc}")
                stale.append(connection)
        for connection in stale:
            self.disconnect(connection, user_id)


manager = ConnectionManager()


# ==================== 通知 API ====================


@router.get(
    "",
    summary="通知列表",
    description="获取当前用户的通知列表（需登录）。支持按未读筛选与分页；"
    "响应中的 unread_count 始终是全量未读数，不受 unread_only 筛选影响。",
    response_model=None,
    responses={200: {"model": NotificationListOut, "description": "通知分页列表"}},
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

    # 顺序查询（同一会话不能并发）
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
    description="获取当前用户的未读通知数量（需登录，用于角标轮询）。",
    response_model=None,
    responses={200: {"model": NotificationUnreadCountOut, "description": "未读通知数"}},
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
    description="获取当前用户的通知统计信息（需登录），含按动作类型 verb 分组的数量分布。",
    response_model=None,
    responses={200: {"model": NotificationStatsOut, "description": "通知统计"}},
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
        type_distribution[row.verb] = row.count

    return {
        "total": total_count,
        "unread": unread_count,
        "read": read_count,
        "type_distribution": type_distribution,
    }


@router.post(
    "/{notification_id}/read",
    summary="标记已读",
    description="标记单条通知为已读（需登录）。会减少未读数；通知不存在或不属于当前用户时 404。",
    response_model=None,
    responses={200: {"model": NotificationActionResultOut, "description": "操作结果"}},
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
    description="标记当前用户所有通知为已读（需登录）。成功后未读数归零。",
    response_model=None,
    responses={200: {"model": NotificationActionResultOut, "description": "操作结果"}},
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
    description="删除单条通知（需登录）。通知不存在或不属于当前用户时 404。",
    response_model=None,
    responses={200: {"model": NotificationActionResultOut, "description": "操作结果"}},
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
    description="清空当前用户的所有通知，read_only=true 时只清空已读通知（需登录）。",
    response_model=None,
    responses={
        200: {"model": NotificationActionResultOut, "description": "操作结果，message 含清空条数"}
    },
)
async def clear_notifications(
    db: DB,
    current_user: CurrentUser,
    read_only: bool = Query(False, description="只清空已读通知"),
):
    """清空通知（单条批量 DELETE，不再 SELECT+N 次 db.delete）"""
    conditions = [Notification.recipient_id == current_user.id]
    if read_only:
        conditions.append(Notification.is_read.is_(True))

    result = await db.execute(delete(Notification).where(*conditions))
    await db.flush()

    # rowcount 在部分方言下可能是 -1（未知），此时回退为"已清空"不带具体条数
    count = result.rowcount or 0
    message = f"已清空 {count} 条通知" if count > 0 else "没有可清空的通知"
    return {"success": True, "message": message}


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
