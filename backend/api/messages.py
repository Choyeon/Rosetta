"""私信 API"""

from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import and_, case, desc, func, or_, select, update

from backend.core.auth import DB, CurrentUser
from backend.models.message import PrivateMessage
from backend.models.user import User

router = APIRouter(prefix="/messages", tags=["私信"])


# ==================== 响应体文档模型 ====================
# 仅用于 OpenAPI responses 声明（$ref 文档化），刻意不挂 response_model=，
# 避免 Pydantic 序列化过滤抹掉运行时字段。


class MessagePeerUserOut(BaseModel):
    """会话对端用户的公开资料"""

    id: int = Field(..., description="对端用户 ID")
    username: str = Field(..., description="用户名")
    nickname: str | None = Field(None, description="昵称，未设置时为 null")
    avatar: str | None = Field(None, description="头像 URL，未设置时为 null")


class MessageLastMessageOut(BaseModel):
    """会话里的最近一条消息摘要"""

    content: str = Field(..., description="消息内容；超过 100 字时截断并追加省略号")
    created_at: str = Field(..., description="发送时间（ISO 8601 字符串）")
    is_mine: bool = Field(..., description="该条消息是否由当前用户发出")


class MessageConversationItemOut(BaseModel):
    """会话列表中的一行（每个对端一行）"""

    user: MessagePeerUserOut = Field(..., description="对端用户")
    last_message: MessageLastMessageOut = Field(..., description="与该对端之间的最近一条消息")
    unread_count: int = Field(
        ..., description="「对方发给我且未读」的消息条数，不含当前用户自己发出的未读消息"
    )


class MessageConversationListOut(BaseModel):
    """私信会话分页列表"""

    items: list[MessageConversationItemOut] = Field(
        ..., description="本页会话列表，按最近消息时间倒序"
    )
    total: int = Field(..., description="会话总数（对端数量，非本页条数）")
    page: int = Field(..., description="当前页码，从 1 开始")
    page_size: int = Field(..., description="每页条数")
    total_pages: int = Field(..., description="总页数，至少为 1")


class MessageUnreadCountOut(BaseModel):
    """未读私信总数"""

    count: int = Field(..., description="当前用户收到的全部未读私信条数")


class MessageDetailItemOut(BaseModel):
    """会话中的一条私信原文"""

    id: int = Field(..., description="消息 ID")
    content: str = Field(..., description="消息内容（不截断）")
    is_mine: bool = Field(..., description="该条消息是否由当前用户发出")
    is_read: bool = Field(..., description="接收方是否已读；本接口读取后即把自己收到的消息置为已读")
    created_at: str = Field(..., description="发送时间（ISO 8601 字符串）")


class MessageConversationDetailOut(BaseModel):
    """与指定用户的私信记录分页"""

    items: list[MessageDetailItemOut] = Field(..., description="本页消息列表，按时间正序")
    other_user: MessagePeerUserOut = Field(..., description="对端用户资料")
    total: int = Field(..., description="双方消息总数（非本页条数）")
    page: int = Field(..., description="当前页码，从 1 开始")
    page_size: int = Field(..., description="每页条数")
    total_pages: int = Field(..., description="总页数")


class MessageSendOut(BaseModel):
    """发送私信成功后的消息回显"""

    id: int = Field(..., description="新建消息 ID")
    content: str = Field(..., description="消息内容")
    recipient_id: int = Field(..., description="接收者用户 ID")
    created_at: str = Field(..., description="发送时间（ISO 8601 字符串）")


class MessageSuccessOut(BaseModel):
    """已读标记类操作结果"""

    success: bool = Field(True, description="操作是否成功")


@router.get(
    "/conversations",
    summary="获取会话列表",
    description=(
        "当前用户的私信会话，按最近消息时间倒序，**每个对端一行**。"
        "返回 ``{items, total, page, page_size, total_pages}``；``total`` 是会话总数"
        "（非本页条数），``items[].unread_count`` 只统计「对方发给我且未读」的消息。"
    ),
    response_model=None,
    responses={200: {"model": MessageConversationListOut, "description": "会话分页列表"}},
)
async def get_conversations(
    db: DB,
    current_user: CurrentUser,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    """获取对话列表：每个对端一行，按最近消息时间倒序分页。"""
    # 「对端用户 id」表达式：我发出的 ⇒ 对端是 recipient，收到的 ⇒ 对端是 sender。
    # 必须是顶层 ``case(...)``：``func.case`` 构造的是名为 case 的普通 SQL 函数，
    # 既不接受 ``else_`` 关键字（TypeError → 500），也带不动裸列 GROUP BY（PG 非法）。
    other_id_expr = case(
        (PrivateMessage.sender_id == current_user.id, PrivateMessage.recipient_id),
        else_=PrivateMessage.sender_id,
    )
    between_us = or_(
        PrivateMessage.sender_id == current_user.id,
        PrivateMessage.recipient_id == current_user.id,
    )

    peer_latest = (
        select(
            other_id_expr.label("other_id"),
            func.max(PrivateMessage.created_at).label("last_message_time"),
        )
        .where(between_us)
        .group_by(other_id_expr)
        .subquery()
    )

    total = await db.scalar(select(func.count()).select_from(peer_latest)) or 0

    latest_messages = (
        select(PrivateMessage)
        .join(
            peer_latest,
            and_(
                other_id_expr == peer_latest.c.other_id,
                PrivateMessage.created_at == peer_latest.c.last_message_time,
            ),
        )
        .order_by(desc(PrivateMessage.created_at))
        .offset((page - 1) * page_size)
        .limit(page_size)
    )

    result = await db.execute(latest_messages)
    messages = result.scalars().all()

    conversations = []
    user_ids = set()
    for msg in messages:
        other_id = msg.recipient_id if msg.sender_id == current_user.id else msg.sender_id
        user_ids.add(other_id)

    if user_ids:
        users_result = await db.execute(select(User).where(User.id.in_(user_ids)))
        users = {u.id: u for u in users_result.scalars().all()}

        # 未读数按发件人一次 GROUP BY 取回：原先每个会话补一条 COUNT，
        # 列表页查询数随会话数线性增长。
        unread_rows = await db.execute(
            select(PrivateMessage.sender_id, func.count(PrivateMessage.id))
            .where(
                PrivateMessage.recipient_id == current_user.id,
                PrivateMessage.sender_id.in_(user_ids),
                PrivateMessage.is_read.is_(False),
            )
            .group_by(PrivateMessage.sender_id)
        )
        unread_map = {int(sender_id): int(count) for sender_id, count in unread_rows.all()}

        for msg in messages:
            other_id = msg.recipient_id if msg.sender_id == current_user.id else msg.sender_id
            other_user = users.get(other_id)
            if other_user:
                unread_count = unread_map.get(other_id, 0)

                conversations.append(
                    {
                        "user": {
                            "id": other_user.id,
                            "username": other_user.username,
                            "nickname": other_user.nickname,
                            "avatar": other_user.avatar,
                        },
                        "last_message": {
                            "content": msg.content[:100] + "..."
                            if len(msg.content) > 100
                            else msg.content,
                            "created_at": msg.created_at.isoformat(),
                            "is_mine": msg.sender_id == current_user.id,
                        },
                        "unread_count": unread_count,
                    }
                )

    return {
        "items": conversations,
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": max(1, (total + page_size - 1) // page_size),
    }


@router.get(
    "/unread/count",
    summary="获取未读消息数",
    description="返回当前用户所有未读私信的总数（需登录，用于角标轮询）。",
    response_model=None,
    responses={200: {"model": MessageUnreadCountOut, "description": "未读私信总数"}},
)
async def get_unread_count(
    db: DB,
    current_user: CurrentUser,
):
    """获取未读消息数量"""
    result = await db.execute(
        select(func.count())
        .select_from(PrivateMessage)
        .where(
            PrivateMessage.recipient_id == current_user.id,
            PrivateMessage.is_read.is_(False),
        )
    )
    count = result.scalar() or 0
    return {"count": count}


@router.get(
    "/{user_id}",
    summary="获取与某用户的会话",
    description="获取当前用户与指定用户之间的私信记录，支持分页（需登录）。"
    "**副作用**：读取时会把该用户发给当前用户的未读消息全部标记为已读。",
    response_model=None,
    responses={200: {"model": MessageConversationDetailOut, "description": "私信记录分页"}},
)
async def get_conversation(
    db: DB,
    current_user: CurrentUser,
    user_id: int,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
):
    """获取与某用户的对话历史"""
    other_user = await db.get(User, user_id)
    if not other_user:
        raise HTTPException(status_code=404, detail="用户不存在")

    query = (
        select(PrivateMessage)
        .where(
            or_(
                and_(
                    PrivateMessage.sender_id == current_user.id,
                    PrivateMessage.recipient_id == user_id,
                ),
                and_(
                    PrivateMessage.sender_id == user_id,
                    PrivateMessage.recipient_id == current_user.id,
                ),
            )
        )
        .order_by(desc(PrivateMessage.created_at))
    )

    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    messages_query = query.offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(messages_query)
    messages = result.scalars().all()

    await db.execute(
        update(PrivateMessage)
        .where(
            PrivateMessage.sender_id == user_id,
            PrivateMessage.recipient_id == current_user.id,
            PrivateMessage.is_read.is_(False),
        )
        .values(is_read=True)
    )
    await db.commit()

    return {
        "items": [
            {
                "id": msg.id,
                "content": msg.content,
                "is_mine": msg.sender_id == current_user.id,
                "is_read": msg.is_read,
                "created_at": msg.created_at.isoformat(),
            }
            for msg in reversed(messages)
        ],
        "other_user": {
            "id": other_user.id,
            "username": other_user.username,
            "nickname": other_user.nickname,
            "avatar": other_user.avatar,
        },
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": (total + page_size - 1) // page_size,
    }


@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    summary="发送私信",
    description="向指定用户发送一条私信消息（需登录）。给自己发送时 400；接收者不存在时 404。",
    response_model=None,
    responses={201: {"model": MessageSendOut, "description": "新建消息回显"}},
)
async def send_message(
    db: DB,
    current_user: CurrentUser,
    recipient_id: int = Query(..., description="接收者ID"),
    content: str = Query(..., min_length=1, max_length=5000, description="消息内容"),
):
    """发送私信"""
    if recipient_id == current_user.id:
        raise HTTPException(status_code=400, detail="不能给自己发送私信")

    recipient = await db.get(User, recipient_id)
    if not recipient:
        raise HTTPException(status_code=404, detail="用户不存在")

    message = PrivateMessage(
        sender_id=current_user.id,
        recipient_id=recipient_id,
        content=content,
    )
    db.add(message)
    await db.commit()
    await db.refresh(message)

    return {
        "id": message.id,
        "content": message.content,
        "recipient_id": message.recipient_id,
        "created_at": message.created_at.isoformat(),
    }


@router.put(
    "/{message_id}/read",
    summary="标记单条消息已读",
    description="将指定私信标记为已读（需登录）。消息不存在时 404；"
    "当前用户不是接收者时 403。成功后该会话/全局未读数相应减少。",
    response_model=None,
    responses={200: {"model": MessageSuccessOut, "description": "操作结果"}},
)
async def mark_as_read(
    db: DB,
    current_user: CurrentUser,
    message_id: int,
):
    """标记消息为已读"""
    message = await db.get(PrivateMessage, message_id)
    if not message:
        raise HTTPException(status_code=404, detail="消息不存在")

    if message.recipient_id != current_user.id:
        raise HTTPException(status_code=403, detail="无权操作此消息")

    message.is_read = True
    await db.commit()

    return {"success": True}


@router.put(
    "/read-all/{user_id}",
    summary="标记某会话全部已读",
    description="将与指定用户的所有私信标记为已读（需登录，仅标记对方发给当前用户的未读消息）。",
    response_model=None,
    responses={200: {"model": MessageSuccessOut, "description": "操作结果"}},
)
async def mark_all_as_read(
    db: DB,
    current_user: CurrentUser,
    user_id: int,
):
    """标记与某用户的所有消息为已读"""
    await db.execute(
        update(PrivateMessage)
        .where(
            PrivateMessage.sender_id == user_id,
            PrivateMessage.recipient_id == current_user.id,
            PrivateMessage.is_read.is_(False),
        )
        .values(is_read=True)
    )
    await db.commit()

    return {"success": True}
