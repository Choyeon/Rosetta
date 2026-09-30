"""
Webhook 系统

支持事件推送和外部集成。
"""

import asyncio
import functools
import hashlib
import hmac
import json
import logging
import secrets
from datetime import datetime
from typing import Any

import httpx
from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Integer, String, Text, func, select
from sqlalchemy.orm import Mapped, mapped_column

from backend.core import hooks as _hooks
from backend.core.auth import DB, CurrentStaff
from backend.core.config import settings
from backend.core.database import Base, async_session_maker
from backend.core.net_guard import UnsafeTargetError, assert_public_http_url
from backend.utils.compat import UTC

logger = logging.getLogger(__name__)

# webhook 投递超时（秒）
WEBHOOK_TIMEOUT = 10.0


class WebhookEndpoint(Base):
    """Webhook 端点"""

    __tablename__ = "webhook_endpoints"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    url: Mapped[str] = mapped_column(String(500), nullable=False)
    secret: Mapped[str | None] = mapped_column(String(100), nullable=True)
    events: Mapped[str] = mapped_column(Text, nullable=False, default="[]")  # JSON 数组
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    provider: Mapped[str] = mapped_column(String(20), default="generic")
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

    # webhook_deliveries 是只增表，此前整表零索引：
    # - 列表页 `WHERE endpoint_id = ?` 分页（:485）
    # - 端点列表的「最后触发时间」按行做相关子查询
    #   `SELECT max(delivered_at) FROM webhook_deliveries WHERE endpoint_id = ?`（:332）
    # 复合索引以 endpoint_id 为最左列同时覆盖两者，max() 直接取索引末位。
    __table_args__ = (
        Index(
            "ix_webhook_deliveries_endpoint_delivered",
            "endpoint_id",
            "delivered_at",
        ),
    )


router = APIRouter(tags=["Webhook"])


async def _validate_webhook_url(url: str) -> None:
    """Webhook URL 护栏：scheme 必须 http/https；默认拒绝内网/保留地址。

    服务端会主动请求该 URL（投递），属于 SSRF 攻击面；
    自托管内网自动化场景可通过 WEBHOOK_ALLOW_PRIVATE_TARGETS=true 显式放行。
    """
    if not url.startswith(("http://", "https://")):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Webhook URL 仅支持 http/https 协议",
        )
    if getattr(settings, "webhook_allow_private_targets", False):
        return
    try:
        await assert_public_http_url(url)
    except UnsafeTargetError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Webhook URL 不允许指向内网/保留地址（可在配置中显式放行）: {exc}",
        ) from exc


# 支持的事件类型
# 键必须是 hooks 总线上真实会 do_action 的名字（见 backend/core/hooks.py 与各 api 模块
# 的 bus.do_action 调用点）；前端不得再自有一套事件名，统一 GET /webhooks/events 取。
WEBHOOK_EVENTS = {
    "post.created": "文章创建",
    "post.updated": "文章更新",
    "post.published": "文章发布",
    "post.deleted": "文章删除",
    "comment.created": "评论创建",
    "comment.deleted": "评论删除",
    "user.registered": "用户注册",
    "media.uploaded": "媒体上传",
    "media.updated": "媒体更新",
    "media.deleted": "媒体删除",
    "album.created": "相册创建",
    "album.updated": "相册更新",
    "album.deleted": "相册删除",
    "photo.created": "照片创建",
    "photo.updated": "照片更新",
    "photo.deleted": "照片删除",
    "announcement.created": "公告创建",
    "announcement.updated": "公告更新",
    "announcement.deleted": "公告删除",
}

# Provider 只是「这条 URL 属于哪类接收方」的标签，用于后台分组展示；
# 投递逻辑对所有 provider 一致（同一份 JSON + HMAC 头）。
PROVIDER_PATTERN = "^(generic|github|feishu|email)$"


def _subscribes(webhook: WebhookEndpoint, event_type: str) -> bool:
    """端点是否订阅了该事件（events 列是 JSON 数组文本，也可能是已解好的 list）。"""
    raw = webhook.events
    try:
        events = json.loads(raw) if isinstance(raw, str) else raw
    except (TypeError, ValueError):
        logger.warning("Webhook %s 的 events 字段不是合法 JSON，按未订阅处理", webhook.id)
        return False
    return isinstance(events, list) and event_type in events


class WebhookCreate(BaseModel):
    """创建 Webhook。

    字段清单必须与后台表单一致：Pydantic 默认丢弃未声明的键，历史上 provider
    就是这样被静默吞掉的。事件名统一在 schema 层校验，路由不再各写一份。
    """

    name: str = Field(min_length=1, max_length=100)
    url: str = Field(min_length=8, max_length=500)
    secret: str | None = Field(default=None, max_length=100)
    events: list[str] = Field(min_length=1)
    provider: str = Field(default="generic", pattern=PROVIDER_PATTERN)
    active: bool = True

    @field_validator("events")
    @classmethod
    def _check_events(cls, value: list[str]) -> list[str]:
        unknown = [e for e in value if e not in WEBHOOK_EVENTS]
        if unknown:
            raise ValueError(f"不支持的事件类型: {', '.join(unknown)}")
        return value


class WebhookUpdate(BaseModel):
    """更新 Webhook：None = 该字段不修改。

    secret 例外——传空串表示「清除签名密钥」，传 null 表示「保持原值不变」，
    因为响应体不再回显 secret，前端无法区分"用户没填"和"用户想清空"。
    """

    name: str | None = Field(default=None, min_length=1, max_length=100)
    url: str | None = Field(default=None, min_length=8, max_length=500)
    secret: str | None = Field(default=None, max_length=100)
    events: list[str] | None = Field(default=None, min_length=1)
    provider: str | None = Field(default=None, pattern=PROVIDER_PATTERN)
    active: bool | None = None

    @field_validator("events")
    @classmethod
    def _check_events(cls, value: list[str] | None) -> list[str] | None:
        if value is None:
            return None
        unknown = [e for e in value if e not in WEBHOOK_EVENTS]
        if unknown:
            raise ValueError(f"不支持的事件类型: {', '.join(unknown)}")
        return value


class WebhookOut(BaseModel):
    """Webhook 对外表示。

    刻意不含 secret：签名密钥只用于服务端出站计算，回显等于把它塞进每一次
    列表请求的响应体与浏览器历史里。前端需要展示"是否已配置"用 has_secret。
    """

    id: int
    name: str
    url: str
    provider: str
    events: list[str]
    active: bool
    has_secret: bool
    last_triggered_at: str | None = None
    created_at: str | None = None
    updated_at: str | None = None


class WebhookListOut(BaseModel):
    items: list[WebhookOut]
    total: int
    page: int
    page_size: int


class WebhookDeliveryOut(BaseModel):
    id: int
    event_type: str
    status_code: int | None
    error: str | None
    response_body: str | None
    delivered_at: str | None
    created_at: str | None


class WebhookDeliveryListOut(BaseModel):
    items: list[WebhookDeliveryOut]
    total: int
    page: int
    page_size: int


# ==================== 响应体文档模型（补漏） ====================
# 以下模型仅用于 OpenAPI responses 声明（$ref 文档化），对应端点刻意不挂
# response_model= 实体模型，避免 Pydantic 序列化过滤抹掉运行时字段。


class WebhookEventItemOut(BaseModel):
    """单个可订阅事件"""

    type: str = Field(
        ..., description="事件名，即 hooks 总线上的 do_action 名（如 post.published）"
    )
    description: str = Field(..., description="事件的中文说明")


class WebhookEventsOut(BaseModel):
    """支持的事件类型清单"""

    events: list[WebhookEventItemOut] = Field(
        ..., description="全部可订阅事件列表，是前端订阅 UI 的唯一事件名来源"
    )


class WebhookActionResultOut(BaseModel):
    """删除 / 重试类操作结果"""

    success: bool = Field(True, description="操作是否成功")
    message: str = Field(..., description="人类可读操作结果提示")


class WebhookTestResultOut(BaseModel):
    """测试投递结果"""

    success: bool = Field(
        ..., description="测试是否通过（目标端点未返回 5xx 且未被 SSRF 护栏拦截）"
    )
    message: str = Field(..., description="测试结果说明；失败时含错误摘要")
    status_code: int | None = Field(
        None, description="目标端点返回的 HTTP 状态码；请求未发出（网络错误/被护栏拦截）时为 null"
    )


class WebhookSecretDataOut(BaseModel):
    """轮换后一次性给出的密钥数据"""

    secret: str = Field(
        ...,
        description="新生成的 HMAC-SHA256 密钥明文（64 位十六进制字符串）。"
        "仅此接口、仅此一次返回明文，此后列表/详情只回显 has_secret，旧密钥立即失效",
    )


class WebhookSecretRotateOut(BaseModel):
    """重新生成密钥结果"""

    success: bool = Field(True, description="操作是否成功")
    message: str = Field(..., description="提示需同步更新接收方配置")
    data: WebhookSecretDataOut = Field(..., description="携带一次性明文密钥")


def _iso(value: datetime | None) -> str | None:
    return value.isoformat() if value else None


def _webhook_out(webhook: WebhookEndpoint, last_triggered: datetime | None = None) -> WebhookOut:
    raw = webhook.events
    try:
        events = json.loads(raw) if isinstance(raw, str) else raw
    except (TypeError, ValueError):
        events = []
    if not isinstance(events, list):  # 历史脏数据：按空订阅处理，不让列表接口 500
        events = []
    return WebhookOut(
        id=webhook.id,
        name=webhook.name,
        url=webhook.url,
        provider=webhook.provider or "generic",
        events=[str(e) for e in events],
        active=bool(webhook.is_active),
        has_secret=bool(webhook.secret),
        last_triggered_at=_iso(last_triggered),
        created_at=_iso(webhook.created_at),
        updated_at=_iso(webhook.updated_at),
    )


async def _last_triggered(db, webhook_id: int) -> datetime | None:
    return await db.scalar(
        select(func.max(WebhookDelivery.delivered_at)).where(
            WebhookDelivery.endpoint_id == webhook_id
        )
    )


@router.get(
    "",
    summary="Webhook 列表",
    description="获取所有 Webhook 端点列表。",
    response_model=WebhookListOut,
)
async def list_webhooks(
    db: DB,
    current_user: CurrentStaff,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    """获取 Webhook 列表"""
    total = await db.scalar(select(func.count()).select_from(WebhookEndpoint)) or 0

    # 相关子查询取「最后一次成功投递时间」：避免逐行 N+1，也避免为一次
    # 列表展示去 JOIN 整张投递表。
    last_triggered = (
        select(func.max(WebhookDelivery.delivered_at))
        .where(WebhookDelivery.endpoint_id == WebhookEndpoint.id)
        .correlate(WebhookEndpoint)
        .scalar_subquery()
    )
    result = await db.execute(
        select(WebhookEndpoint, last_triggered.label("last_triggered"))
        .order_by(WebhookEndpoint.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )

    return WebhookListOut(
        items=[_webhook_out(endpoint, last_triggered) for endpoint, last_triggered in result.all()],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get(
    "/events",
    summary="支持的事件类型",
    description=(
        "获取所有可订阅的 Webhook 事件类型（无需管理员写权限即可读取）。"
        "事件名即 hooks 总线上的 do_action 名，"
        "前端订阅清单必须来自本接口，不得自有一套命名。"
    ),
    response_model=None,
    responses={200: {"model": WebhookEventsOut, "description": "可订阅事件清单"}},
)
async def list_webhook_events():
    """获取支持的事件类型"""
    return {"events": [{"type": k, "description": v} for k, v in WEBHOOK_EVENTS.items()]}


@router.post(
    "",
    summary="创建 Webhook",
    description="创建新的 Webhook 端点。",
    response_model=WebhookOut,
)
async def create_webhook(
    db: DB,
    current_user: CurrentStaff,
    data: WebhookCreate,
):
    """创建 Webhook"""
    await _validate_webhook_url(data.url)

    webhook = WebhookEndpoint(
        name=data.name,
        url=data.url,
        secret=data.secret or None,
        events=json.dumps(data.events),
        provider=data.provider,
        is_active=data.active,
        created_by_id=current_user.id,
    )
    db.add(webhook)
    await db.flush()
    await db.refresh(webhook)

    return _webhook_out(webhook)


@router.put(
    "/{webhook_id}",
    summary="更新 Webhook",
    description="更新 Webhook 端点配置。未提供的字段保持不变；secret 传空串表示清除密钥。",
    response_model=WebhookOut,
)
async def update_webhook(
    webhook_id: int,
    db: DB,
    current_user: CurrentStaff,
    data: WebhookUpdate,
):
    """更新 Webhook"""
    webhook = await db.get(WebhookEndpoint, webhook_id)
    if not webhook:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Webhook 不存在",
        )

    if data.name is not None:
        webhook.name = data.name
    if data.url is not None:
        await _validate_webhook_url(data.url)
        webhook.url = data.url
    if data.secret is not None:
        webhook.secret = data.secret or None
    if data.events is not None:
        webhook.events = json.dumps(data.events)
    if data.provider is not None:
        webhook.provider = data.provider
    if data.active is not None:
        webhook.is_active = data.active

    await db.flush()
    await db.refresh(webhook)

    return _webhook_out(webhook, await _last_triggered(db, webhook_id))


@router.delete(
    "/{webhook_id}",
    summary="删除 Webhook",
    description="删除 Webhook 端点（需管理员）。端点不存在时 404；删除后该端点不再接收任何事件投递。",
    response_model=None,
    responses={200: {"model": WebhookActionResultOut, "description": "操作结果"}},
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
    response_model=WebhookDeliveryListOut,
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

    base = select(WebhookDelivery).where(WebhookDelivery.endpoint_id == webhook_id)
    total = await db.scalar(select(func.count()).select_from(base.subquery())) or 0
    result = await db.execute(
        base.order_by(WebhookDelivery.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )

    return WebhookDeliveryListOut(
        items=[
            WebhookDeliveryOut(
                id=d.id,
                event_type=d.event_type,
                status_code=d.status_code,
                error=d.error,
                response_body=d.response_body,
                delivered_at=_iso(d.delivered_at),
                created_at=_iso(d.created_at),
            )
            for d in result.scalars().all()
        ],
        total=total,
        page=page,
        page_size=page_size,
    )


async def trigger_webhook(event_type: str, payload: dict, db) -> int:
    """向所有订阅 event_type 的活跃端点投递一次事件。返回投递条数。

    每个端点互相隔离（并发 + return_exceptions）：黑洞端点只留痕在自己的
    WebhookDelivery.error 上，既不拖慢其他端点，也不向上抛给业务代码。
    """
    body = json.dumps(
        {
            "event": event_type,
            "timestamp": datetime.now(UTC).isoformat(),
            "data": payload,
        },
        ensure_ascii=False,
    ).encode("utf-8")

    result = await db.execute(select(WebhookEndpoint).where(WebhookEndpoint.is_active.is_(True)))
    targets = [w for w in result.scalars().all() if _subscribes(w, event_type)]
    if not targets:
        return 0

    deliveries = []
    for webhook in targets:
        delivery = WebhookDelivery(
            endpoint_id=webhook.id,
            event_type=event_type,
            payload=body.decode("utf-8"),
        )
        db.add(delivery)
        deliveries.append((webhook, delivery))
    # flush 让 delivery.id 可用；HTTP 在落库之后再跑，保证失败也有记录可查
    await db.flush()

    async with httpx.AsyncClient(timeout=WEBHOOK_TIMEOUT) as client:
        outcomes = await asyncio.gather(
            *(
                _send_once(client, webhook.url, body, webhook.secret, event_type)
                for webhook, _ in deliveries
            ),
            return_exceptions=True,
        )

    for (webhook, delivery), outcome in zip(deliveries, outcomes, strict=True):
        if isinstance(outcome, BaseException):
            # _send_once 自带 except，这里只兜底 gather 的异常路径
            delivery.error = str(outcome)[:500]
            delivery.delivered_at = datetime.now(UTC)
            logger.warning(
                "Webhook 投递异常 endpoint=%s event=%s: %s", webhook.id, event_type, outcome
            )
            continue
        status_code, response_text, error = outcome
        delivery.status_code = status_code
        delivery.response_body = response_text[:2000] if response_text else None
        delivery.error = error
        delivery.delivered_at = datetime.now(UTC)

    await db.flush()
    return len(deliveries)


async def _send_once(
    client: httpx.AsyncClient,
    url: str,
    body: bytes,
    secret: str | None,
    event_type: str,
) -> tuple[int | None, str, str | None]:
    """发送单个投递请求。返回 (status_code, response_text, error)；error 非空即失败。

    签名头统一为 X-Rosetta-Signature（HMAC-SHA256，对**实际发出的字节**签名）+
    X-Rosetta-Event。历史上 test/retry 走的是 X-Webhook-* 三个入口三套头，
    接收方按任一文档校验都会失败，故这里只保留一套。
    """
    headers = {
        "Content-Type": "application/json",
        "X-Rosetta-Event": event_type,
    }
    if secret:
        digest = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
        headers["X-Rosetta-Signature"] = f"sha256={digest}"

    try:
        # 发送前复核出口地址：URL 创建时校验过，但 DNS 会重绑定、解析会变，
        # 真正发起请求的这一刻才是 SSRF 的唯一有效防线。
        # 复用 _validate_webhook_url：它同时实现了协议白名单与
        # webhook_allow_private_targets（本地调试指向 127.0.0.1 需要能放行）。
        await _validate_webhook_url(url)
        resp = await client.post(url, content=body, headers=headers)
    except HTTPException as exc:
        logger.warning("Webhook 目标被 SSRF 护栏拒绝 url=%s: %s", url, exc.detail)
        return None, "", f"blocked: {exc.detail}"
    except Exception as exc:  # noqa: BLE001 - 投递失败不得影响业务
        logger.warning("Webhook 投递失败 url=%s event=%s: %s", url, event_type, exc)
        return None, "", str(exc)[:500]

    error = None if resp.status_code < 500 else f"HTTP {resp.status_code}"
    return resp.status_code, resp.text, error


# ── 总线接线 ────────────────────────────────────────────────────────────────
#
# 本模块此前的状态是「有投递函数、无触发方」：trigger_webhook 没有任何调用点，
# 于是 /admin/system/webhooks 里配置的订阅永远不会兑现第二次请求。下面把
# WEBHOOK_EVENTS 逐个挂到 hooks 总线上，补全这条链路。

# 实体在 do_action 里的传法不统一（post.created 按位置、post.published 按关键字），
# 因此按「位置参数 + 这几个已知 kwarg」取实体，绝不扫全部 kwargs：
# 那里躺着 AsyncSession 和 User（当前操作者），全扫会把无关字段发给外部端点。
_ENTITY_KWARGS = ("post", "comment", "user", "media", "page")
# 白名单式取字段，不给 email 之类的 PII 开口子：webhook 端点是第三方地址，
# 事件里带用户邮箱等于把订阅者的隐私转发给任意一个 URL。
_ENTITY_FIELDS = ("id", "slug", "status", "post_id", "author_id", "title", "name")

_dispatch_tasks: set = set()  # 强引用：裸 create_task 的任务无引用时可能被 GC
# 事件名 -> 已注册的 partial。必须存住对象本身：functools.partial 没有 __eq__，
# 现造的 partial 传进 remove_action 永远匹配不上，钩子表会只增不减。
_listeners: dict[str, Any] = {}


def _jsonable(value: Any) -> Any:
    """把实体字段收敛成 JSON 可序列化值（i18n 标题是 dict，时间是 datetime）。"""
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, dict):
        return {str(k): _jsonable(v) for k, v in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_jsonable(v) for v in value]
    return str(value)


def _event_payload(args: tuple, kwargs: dict) -> dict:
    """从钩子参数里提取事件主体标识，构造 webhook payload 的 data 字段。

    默认只认字段白名单（防 PII 外流）。事件源若确实要带别的上下文，必须显式传
    ``webhook_payload={...}`` —— 让「对外披露哪些字段」成为一次可读的代码评审，
    而不是 getattr 扫出来的意外结果。
    """
    explicit = kwargs.get("webhook_payload")
    data: dict[str, Any] = dict(explicit) if isinstance(explicit, dict) else {}
    entities = list(args) + [kwargs[key] for key in _ENTITY_KWARGS if key in kwargs]
    for entity in entities:
        if isinstance(entity, dict):
            for key in _ENTITY_FIELDS:
                if key in entity:
                    data.setdefault(key, _jsonable(entity[key]))
            continue
        for attr in _ENTITY_FIELDS:
            value = getattr(entity, attr, None)
            if value is not None and not callable(value):
                data.setdefault(attr, _jsonable(value))
    actor = kwargs.get("current_user")
    actor_id = getattr(actor, "id", None)
    if actor_id is not None:
        data["actor_id"] = actor_id
    return data


async def _on_bus_event(event_type: str, *args: Any, **kwargs: Any) -> None:
    """总线回调：只负责排投递任务，绝不 await HTTP（写请求不能被外网端点拖住）。"""
    payload = _event_payload(args, kwargs)

    async def _run() -> None:
        try:
            # 自建 session：业务事务此刻尚未提交，投递只读事件本身携带的数据。
            async with async_session_maker() as session:
                await trigger_webhook(event_type, payload, session)
                await session.commit()
        except Exception:  # noqa: BLE001 - 后台任务异常不得冒泡成未处理错误
            logger.exception("Webhook 后台投递失败 event=%s", event_type)

    task = asyncio.create_task(_run())
    _dispatch_tasks.add(task)
    task.add_done_callback(_dispatch_tasks.discard)


def register_webhook_listeners() -> list[str]:
    """把 WEBHOOK_EVENTS 挂到 hooks 总线。幂等：重复调用只补注册缺失的事件。"""
    registered: list[str] = []
    for event_type in WEBHOOK_EVENTS:
        if event_type in _listeners:
            continue
        handler = functools.partial(_on_bus_event, event_type)
        _hooks.add_action(event_type, handler)
        _listeners[event_type] = handler
        registered.append(event_type)
    return registered


def unregister_webhook_listeners() -> list[str]:
    """注销总线回调（测试 teardown 用：全局钩子表会跨用例残留）。"""
    removed: list[str] = []
    for event_type, handler in list(_listeners.items()):
        _hooks.remove_action(event_type, handler)
        del _listeners[event_type]
        removed.append(event_type)
    return removed


@router.post(
    "/{webhook_id}/test",
    summary="测试 Webhook",
    description="发送测试请求到 Webhook URL（需管理员）。与真实投递共用同一套签名头与 SSRF 护栏，"
    "并落一条 event_type=test 的投递记录；端点不存在时 404。",
    response_model=None,
    responses={200: {"model": WebhookTestResultOut, "description": "测试结果"}},
)
async def test_webhook(
    webhook_id: int,
    db: DB,
    current_user: CurrentStaff,
):
    """测试 Webhook 端点

    与真实投递共用 _send_once：同一套签名头、同一道 SSRF 护栏，
    避免出现「测试按钮通过、线上接收方校验不过」的双实现漂移。
    测试同样落一条 WebhookDelivery：「最后触发」列必须来自真实记录，
    而不是前端本地猜的时间戳。
    """
    webhook = await db.get(WebhookEndpoint, webhook_id)
    if not webhook:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Webhook 不存在",
        )

    payload = {
        "event": "test",
        "timestamp": datetime.now(UTC).isoformat(),
        "data": {"message": "This is a test webhook"},
    }
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")

    async with httpx.AsyncClient(timeout=WEBHOOK_TIMEOUT) as client:
        code, text, error = await _send_once(client, webhook.url, body, webhook.secret, "test")

    db.add(
        WebhookDelivery(
            endpoint_id=webhook.id,
            event_type="test",
            payload=json.dumps(payload, ensure_ascii=False),
            status_code=code,
            response_body=text[:2000] if text else None,
            error=error,
            delivered_at=datetime.now(UTC),
        )
    )
    await db.flush()

    if error:
        return {"success": False, "message": f"测试失败: {error}", "status_code": code}
    return {"success": True, "message": "测试成功", "status_code": code}


@router.post(
    "/{webhook_id}/regenerate-secret",
    summary="重新生成密钥",
    description="生成新的 HMAC 密钥并返回**明文**（需管理员，仅此接口给出）；"
    "旧密钥立即失效，接收方必须同步更新，否则后续投递的签名校验全部失败。端点不存在时 404。",
    response_model=None,
    responses={
        200: {"model": WebhookSecretRotateOut, "description": "轮换结果，data.secret 为一次性明文"}
    },
)
async def regenerate_webhook_secret(
    webhook_id: int,
    db: DB,
    current_user: CurrentStaff,
):
    """重新生成 Webhook 密钥

    这是密钥的唯一「可见」出口（列表/详情不再回显），因此返回值刻意带明文。
    鉴权与其余 CRUD 一致用 CurrentStaff：端点是站点级配置，任何 staff 都能
    PUT/DELETE 它，再单独要求「仅创建者」只会在协作者点上按钮时得到一个假 404。
    """
    webhook = await db.get(WebhookEndpoint, webhook_id)
    if not webhook:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Webhook 不存在",
        )

    webhook.secret = secrets.token_hex(32)
    await db.flush()
    await db.refresh(webhook)

    # 明文密钥只在轮换这一次给出（列表/详情永不回显），接收方需同步更新配置。
    return {
        "success": True,
        "message": "密钥已重新生成，请同步更新接收方配置",
        "data": {"secret": webhook.secret},
    }


@router.post(
    "/deliveries/{delivery_id}/retry",
    summary="重试投递",
    description="重新发送失败的 Webhook 投递（需管理员）。按库内 payload 原文复发以保持签名一致性，"
    "并就地更新该投递记录的状态码/响应体/错误；投递或端点不存在时 404。",
    response_model=None,
    responses={200: {"model": WebhookActionResultOut, "description": "重试结果"}},
)
async def retry_webhook_delivery(
    delivery_id: int,
    db: DB,
    current_user: CurrentStaff,
):
    """重试 Webhook 投递

    直接复发库内 payload 原文（不重新序列化）：重新 dumps 会改变字节，
    接收方若已按签名校验就会误判。判定口径与正常投递一致
    （5xx 记 error），此前任何 2xx/4xx/5xx 都被改写为 error=None。
    """
    delivery = await db.get(WebhookDelivery, delivery_id)
    if not delivery:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="投递记录不存在",
        )

    webhook = await db.get(WebhookEndpoint, delivery.endpoint_id)
    if not webhook:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Webhook 不存在",
        )

    async with httpx.AsyncClient(timeout=WEBHOOK_TIMEOUT) as client:
        code, text, error = await _send_once(
            client,
            webhook.url,
            delivery.payload.encode("utf-8"),
            webhook.secret,
            delivery.event_type,
        )

    delivery.status_code = code
    delivery.response_body = text[:2000] if text else None
    delivery.error = error
    delivery.delivered_at = datetime.now(UTC)
    await db.flush()

    if error:
        return {"success": False, "message": f"重试失败: {error}"}
    return {"success": True, "message": "重试成功"}
