"""
Webhook 系统

支持事件推送和外部集成。
"""

import hashlib
import hmac
import json
from datetime import datetime

from fastapi import APIRouter, Body, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, func, select
from sqlalchemy.orm import Mapped, mapped_column

from backend.core.auth import DB, CurrentStaff, CurrentUser
from backend.core.database import Base
from backend.utils.compat import UTC


class WebhookEndpoint(Base):
    """Webhook 端点"""

    __tablename__ = "webhook_endpoints"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    url: Mapped[str] = mapped_column(String(500), nullable=False)
    secret: Mapped[str | None] = mapped_column(String(100), nullable=True)
    events: Mapped[str] = mapped_column(Text, nullable=False, default="[]")  # JSON 数组
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_by_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC)
    )


class WebhookDelivery(Base):
    """Webhook 投递记录"""

    __tablename__ = "webhook_deliveries"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    endpoint_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("webhook_endpoints.id"), nullable=False
    )
    event_type: Mapped[str] = mapped_column(String(50), nullable=False)
    payload: Mapped[str] = mapped_column(Text, nullable=False)
    status_code: Mapped[int | None] = mapped_column(Integer, nullable=True)
    response_body: Mapped[str | None] = mapped_column(Text, nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    delivered_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC))


router = APIRouter(tags=["Webhook"])


# 支持的事件类型
WEBHOOK_EVENTS = {
    "post.created": "文章创建",
    "post.updated": "文章更新",
    "post.published": "文章发布",
    "post.deleted": "文章删除",
    "comment.created": "评论创建",
    "comment.deleted": "评论删除",
    "user.registered": "用户注册",
    "media.uploaded": "媒体上传",
}


class WebhookCreate(BaseModel):
    """创建 Webhook"""

    name: str
    url: str
    secret: str | None = None
    events: list[str]


class WebhookResponse(BaseModel):
    """Webhook 响应"""

    id: int
    name: str
    url: str
    events: list[str]
    is_active: bool
    created_at: str

    model_config = {"from_attributes": True}


@router.get(
    "",
    summary="Webhook 列表",
    description="获取所有 Webhook 端点列表。",
)
async def list_webhooks(
    db: DB,
    current_user: CurrentStaff,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    """获取 Webhook 列表"""
    query = select(WebhookEndpoint).order_by(WebhookEndpoint.created_at.desc())

    total = await db.scalar(select(func.count()).select_from(query.subquery())) or 0
    result = await db.execute(query.offset((page - 1) * page_size).limit(page_size))
    webhooks = result.scalars().all()

    items = []
    for wh in webhooks:
        items.append(
            {
                "id": wh.id,
                "name": wh.name,
                "url": wh.url,
                "events": json.loads(wh.events) if isinstance(wh.events, str) else wh.events,
                "is_active": wh.is_active,
                "created_at": wh.created_at.isoformat() if wh.created_at else None,
            }
        )

    return {
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
    }


@router.get(
    "/events",
    summary="支持的事件类型",
    description="获取所有支持的 Webhook 事件类型。",
)
async def list_webhook_events():
    """获取支持的事件类型"""
    return {"events": [{"type": k, "description": v} for k, v in WEBHOOK_EVENTS.items()]}


@router.post(
    "",
    summary="创建 Webhook",
    description="创建新的 Webhook 端点。",
)
async def create_webhook(
    db: DB,
    current_user: CurrentStaff,
    data: WebhookCreate = Body(...),
):
    """创建 Webhook"""
    # 验证事件类型
    for event in data.events:
        if event not in WEBHOOK_EVENTS:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"不支持的事件类型: {event}",
            )

    webhook = WebhookEndpoint(
        name=data.name,
        url=data.url,
        secret=data.secret,
        events=json.dumps(data.events),
        created_by_id=current_user.id,
    )
    db.add(webhook)
    await db.flush()
    await db.refresh(webhook)

    return {
        "success": True,
        "message": "Webhook 创建成功",
        "webhook": {
            "id": webhook.id,
            "name": webhook.name,
            "url": webhook.url,
            "events": data.events,
        },
    }


@router.put(
    "/{webhook_id}",
    summary="更新 Webhook",
    description="更新 Webhook 端点配置。",
)
async def update_webhook(
    webhook_id: int,
    db: DB,
    current_user: CurrentStaff,
    name: str | None = Body(None),
    url: str | None = Body(None),
    secret: str | None = Body(None),
    events: list[str] | None = Body(None),
    is_active: bool | None = Body(None),
):
    """更新 Webhook"""
    webhook = await db.get(WebhookEndpoint, webhook_id)
    if not webhook:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Webhook 不存在",
        )

    if name is not None:
        webhook.name = name
    if url is not None:
        webhook.url = url
    if secret is not None:
        webhook.secret = secret
    if events is not None:
        for event in events:
            if event not in WEBHOOK_EVENTS:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"不支持的事件类型: {event}",
                )
        webhook.events = json.dumps(events)
    if is_active is not None:
        webhook.is_active = is_active

    await db.flush()

    return {"success": True, "message": "Webhook 更新成功"}


@router.delete(
    "/{webhook_id}",
    summary="删除 Webhook",
    description="删除 Webhook 端点。",
)
async def delete_webhook(
    webhook_id: int,
    db: DB,
    current_user: CurrentStaff,
):
    """删除 Webhook"""
    webhook = await db.get(WebhookEndpoint, webhook_id)
    if not webhook:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Webhook 不存在",
        )

    await db.delete(webhook)
    await db.flush()

    return {"success": True, "message": "Webhook 已删除"}


@router.get(
    "/{webhook_id}/deliveries",
    summary="投递记录",
    description="获取 Webhook 的投递记录。",
)
async def list_webhook_deliveries(
    webhook_id: int,
    db: DB,
    current_user: CurrentStaff,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    """获取投递记录"""
    webhook = await db.get(WebhookEndpoint, webhook_id)
    if not webhook:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Webhook 不存在",
        )

    query = (
        select(WebhookDelivery)
        .where(WebhookDelivery.endpoint_id == webhook_id)
        .order_by(WebhookDelivery.created_at.desc())
    )

    total = await db.scalar(select(func.count()).select_from(query.subquery())) or 0
    result = await db.execute(query.offset((page - 1) * page_size).limit(page_size))
    deliveries = result.scalars().all()

    items = []
    for d in deliveries:
        items.append(
            {
                "id": d.id,
                "event_type": d.event_type,
                "status_code": d.status_code,
                "error": d.error,
                "delivered_at": d.delivered_at.isoformat() if d.delivered_at else None,
                "created_at": d.created_at.isoformat() if d.created_at else None,
            }
        )

    return {
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
    }


async def trigger_webhook(event_type: str, payload: dict, db):
    """
    触发 Webhook

    内部函数，用于在事件发生时触发 Webhook。
    """

    # 查找订阅此事件的 Webhook
    result = await db.execute(select(WebhookEndpoint).where(WebhookEndpoint.is_active.is_(True)))
    webhooks = result.scalars().all()

    for webhook in webhooks:
        events = json.loads(webhook.events) if isinstance(webhook.events, str) else webhook.events
        if event_type not in events:
            continue

        # 构建请求体
        request_body = {
            "event": event_type,
            "timestamp": datetime.now(UTC).isoformat(),
            "data": payload,
        }

        # 生成签名
        if webhook.secret:
            payload_str = json.dumps(request_body, separators=(",", ":"))
            hmac.new(
                webhook.secret.encode(),
                payload_str.encode(),
                hashlib.sha256,
            ).hexdigest()

        # 创建投递记录
        delivery = WebhookDelivery(
            endpoint_id=webhook.id,
            event_type=event_type,
            payload=json.dumps(request_body),
        )
        db.add(delivery)
        await db.flush()


@router.post(
    "/{webhook_id}/test",
    summary="测试 Webhook",
    description="发送测试请求到 Webhook URL。",
)
async def test_webhook(
    webhook_id: int,
    db: DB,
    current_user: CurrentUser,
):
    """测试 Webhook 端点"""
    webhook = await db.get(WebhookEndpoint, webhook_id)
    if not webhook or webhook.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Webhook 不存在",
        )

    import httpx

    test_payload = {
        "event": "test",
        "timestamp": datetime.now(UTC).isoformat(),
        "data": {"message": "This is a test webhook"},
    }

    signature = None
    if webhook.secret:
        payload_str = json.dumps(test_payload, separators=(",", ":"))
        signature = hmac.new(
            webhook.secret.encode(),
            payload_str.encode(),
            hashlib.sha256,
        ).hexdigest()

    try:
        headers = {
            "Content-Type": "application/json",
            "X-Webhook-Event": "test",
        }
        if signature:
            headers["X-Webhook-Signature"] = f"sha256={signature}"

        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(
                webhook.url,
                json=test_payload,
                headers=headers,
            )

        return {
            "success": True,
            "message": "测试成功",
            "status_code": response.status_code,
        }

    except Exception as e:
        return {
            "success": False,
            "message": f"测试失败: {str(e)}",
        }


@router.post(
    "/{webhook_id}/regenerate-secret",
    summary="重新生成密钥",
    description="重新生成 Webhook 密钥。",
)
async def regenerate_webhook_secret(
    webhook_id: int,
    db: DB,
    current_user: CurrentUser,
):
    """重新生成 Webhook 密钥"""
    webhook = await db.get(WebhookEndpoint, webhook_id)
    if not webhook or webhook.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Webhook 不存在",
        )

    import secrets

    webhook.secret = secrets.token_hex(32)
    await db.flush()

    return {"secret": webhook.secret}


@router.post(
    "/deliveries/{delivery_id}/retry",
    summary="重试投递",
    description="重新发送失败的 Webhook 投递。",
)
async def retry_webhook_delivery(
    delivery_id: int,
    db: DB,
    current_user: CurrentUser,
):
    """重试 Webhook 投递"""
    delivery = await db.get(WebhookDelivery, delivery_id)
    if not delivery:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="投递记录不存在",
        )

    webhook = await db.get(WebhookEndpoint, delivery.endpoint_id)
    if not webhook or webhook.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Webhook 不存在",
        )

    import httpx

    payload = json.loads(delivery.payload)
    signature = None
    if webhook.secret:
        payload_str = json.dumps(payload, separators=(",", ":"))
        signature = hmac.new(
            webhook.secret.encode(),
            payload_str.encode(),
            hashlib.sha256,
        ).hexdigest()

    try:
        headers = {
            "Content-Type": "application/json",
            "X-Webhook-Event": delivery.event_type,
        }
        if signature:
            headers["X-Webhook-Signature"] = f"sha256={signature}"

        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(
                webhook.url,
                json=payload,
                headers=headers,
            )

        delivery.status_code = response.status_code
        delivery.response_body = response.text[:1000]
        delivery.delivered_at = datetime.now(UTC)
        delivery.error = None

        await db.flush()

        return {"success": True, "message": "重试成功"}

    except Exception as e:
        delivery.error = str(e)
        await db.flush()
        return {"success": False, "message": f"重试失败: {str(e)}"}

        # 发送请求
        try:
            headers = {
                "Content-Type": "application/json",
                "X-Webhook-Event": event_type,
            }
            if signature:
                headers["X-Webhook-Signature"] = f"sha256={signature}"

            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(
                    webhook.url,
                    json=request_body,
                    headers=headers,
                )

                delivery.status_code = response.status_code
                delivery.response_body = response.text[:1000]
                delivery.delivered_at = datetime.now(UTC)

        except Exception as e:
            delivery.error = str(e)

        await db.flush()
