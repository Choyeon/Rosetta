"""私信 API"""

from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import and_, desc, func, or_, select, update

from backend.core.auth import DB, CurrentUser
from backend.models.message import PrivateMessage
from backend.models.user import User

router = APIRouter(prefix="/messages", tags=["私信"])


@router.get("/conversations")
async def get_conversations(
    db: DB,
    current_user: CurrentUser,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    """获取对话列表"""
    subquery = (
        select(
            PrivateMessage.sender_id,
            PrivateMessage.recipient_id,
            func.max(PrivateMessage.created_at).label("last_message_time"),
        )
        .where(
            or_(
                PrivateMessage.sender_id == current_user.id,
                PrivateMessage.recipient_id == current_user.id,
            )
        )
        .group_by(
            func.case(
                (PrivateMessage.sender_id == current_user.id, PrivateMessage.recipient_id),
                else_=PrivateMessage.sender_id,
            )
        )
        .subquery()
    )

    latest_messages = (
        select(PrivateMessage)
        .where(
            or_(
                and_(
                    PrivateMessage.sender_id == current_user.id,
                    PrivateMessage.recipient_id == subquery.c.recipient_id,
                ),
                and_(
                    PrivateMessage.recipient_id == current_user.id,
                    PrivateMessage.sender_id == subquery.c.sender_id,
                ),
            ),
            PrivateMessage.created_at == subquery.c.last_message_time,
        )
        .order_by(desc(PrivateMessage.created_at))
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

        for msg in messages:
            other_id = msg.recipient_id if msg.sender_id == current_user.id else msg.sender_id
            other_user = users.get(other_id)
            if other_user:
                unread_count_result = await db.execute(
                    select(func.count())
                    .select_from(PrivateMessage)
                    .where(
                        PrivateMessage.sender_id == other_id,
                        PrivateMessage.recipient_id == current_user.id,
                        not PrivateMessage.is_read,
                    )
                )
                unread_count = unread_count_result.scalar() or 0

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
        "total": len(conversations),
        "page": page,
        "page_size": page_size,
        "total_pages": 1,
    }


@router.get("/unread/count")
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
            not PrivateMessage.is_read,
        )
    )
    count = result.scalar() or 0
    return {"count": count}


@router.get("/{user_id}")
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
            not PrivateMessage.is_read,
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


@router.post("", status_code=status.HTTP_201_CREATED)
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


@router.put("/{message_id}/read")
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


@router.put("/read-all/{user_id}")
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
            not PrivateMessage.is_read,
        )
        .values(is_read=True)
    )
    await db.commit()

    return {"success": True}
