"""
定时发布 API

提供管理员对文章定时发布的管理能力，以及将到期文章自动转为已发布的工具函数。

路由设计：
- 管理接口:
    GET    /api/admin/posts/scheduled           获取待发布的定时文章列表
    PUT    /api/admin/posts/{post_id}/schedule  设置/更新定时发布
    DELETE /api/admin/posts/{post_id}/schedule  取消定时发布

定时发布模型：
- Post.status == "published" 且 Post.scheduled_at 为未来时间表示处于"定时等待"状态
- publish_due_posts(db) 将 scheduled_at <= now 的文章真正发布（写入 published_at 并清空 scheduled_at）
"""

from datetime import datetime

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select

from backend.core.auth import DB, CurrentStaff
from backend.core.cache import invalidate_cache, invalidate_post_detail_cache
from backend.models.blog import Post
from backend.schemas import BaseResponse
from backend.utils.compat import UTC

router = APIRouter(tags=["定时发布"])


class ScheduleRequest(BaseModel):
    """设置定时发布请求"""

    scheduled_at: datetime = Field(..., description="计划发布时间（UTC）")
    status: str | None = Field(
        None,
        pattern="^(draft|published)$",
        description="文章状态，默认为 published（定时发布）",
    )


async def publish_due_posts(db) -> int:
    """
    发布到期的定时文章

    查询 status=published 且 scheduled_at <= now 的文章，
    将其 published_at 设置为计划时间（真正生效），并清空 scheduled_at。

    Args:
        db: 数据库会话

    Returns:
        int: 本次实际发布的文章数量
    """
    now = datetime.now(UTC)
    query = select(Post).where(
        Post.status == "published",
        Post.scheduled_at.is_not(None),
        Post.scheduled_at <= now,
    )
    result = await db.execute(query)
    posts = result.scalars().all()

    count = 0
    for post in posts:
        # 仅在尚未设置 published_at 时写入，避免覆盖已发布文章的时间
        if post.published_at is None:
            post.published_at = post.scheduled_at
        post.scheduled_at = None
        count += 1

    if count:
        await db.flush()
        # 到点的定时文章此前对匿名访客是 404，列表缓存里也不存在；不立刻失效的话，
        # posts:* 最长 300s 仍按"未发布"返回，首页/分类会在到点后几分钟内继续查不到它。
        await invalidate_cache("posts")

    return count


# ==================== 管理接口 ====================


# ═══════════════════════════════════════════════════════════════════════════
# 响应体文档模型（仅供 OpenAPI `responses={200: {"model": ...}}` 声明使用，
# 运行时不做序列化过滤——实际响应以 handler 返回字面量为准）
# ═══════════════════════════════════════════════════════════════════════════


class ScheduledPostDoc(BaseModel):
    """``GET /api/admin/posts/scheduled`` 列表中的单条定时文章投影。"""

    id: int = Field(..., description="文章 ID")
    title: dict[str, str] = Field(
        ..., description="多语言标题 dict（JSON 列原样返回，如 {'zh': ..., 'en': ...}）"
    )
    slug: str = Field(..., description="文章 slug")
    cover_image: str | None = Field(None, description="封面图 URL，未设置时为 null")
    status: str = Field(
        ..., description="文章状态（draft/published 等，定时发布请求里可携带的目标状态）"
    )
    scheduled_at: datetime | None = Field(
        ...,
        description="计划发布时间（响应序列化为 ISO 8601 字符串）。"
        "本端点先触发到期文章发布再查询，理论上恒非空；到期已发布的文章会从列表消失",
    )
    published_at: datetime | None = Field(
        None, description="实际发布时间，尚未发布（等待定时生效）时为 null"
    )
    author_id: int | None = Field(None, description="作者用户 ID，历史脏数据可能为 null")


@router.get(
    "/admin/posts/scheduled",
    summary="获取定时发布文章列表",
    description=(
        "获取所有处于定时等待状态的文章（scheduled_at 非空），按 scheduled_at 升序，"
        "响应为裸数组（无分页/信封）。需 CurrentStaff。"
        "查询前会先触发到期文章的发布，因此列表中不会再包含已到点的文章。"
    ),
    responses={200: {"model": list[ScheduledPostDoc]}},
)
async def list_scheduled_posts(
    db: DB,
    current_user: CurrentStaff,
):
    """管理员获取待发布的定时文章列表"""
    # 先将到期的文章发布，保证列表为最新的待发布状态
    await publish_due_posts(db)

    query = select(Post).where(Post.scheduled_at.is_not(None)).order_by(Post.scheduled_at.asc())
    result = await db.execute(query)
    posts = result.scalars().all()

    return [
        {
            "id": p.id,
            "title": p.title,
            "slug": p.slug,
            "cover_image": p.cover_image,
            "status": p.status,
            "scheduled_at": p.scheduled_at,
            "published_at": p.published_at,
            "author_id": p.author_id,
        }
        for p in posts
    ]


@router.put(
    "/admin/posts/{post_id}/schedule",
    response_model=BaseResponse,
    summary="设置定时发布",
    description="为文章设置定时发布时间。若计划时间已过去则立即发布。",
)
async def schedule_post(
    post_id: int,
    data: ScheduleRequest,
    db: DB,
    current_user: CurrentStaff,
):
    """设置或更新文章的定时发布"""
    result = await db.execute(select(Post).where(Post.id == post_id))
    post = result.scalar_one_or_none()

    if not post:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="文章不存在",
        )

    # 规范化时区：无时区信息时按 UTC 处理
    scheduled_at = data.scheduled_at
    if scheduled_at.tzinfo is None:
        scheduled_at = scheduled_at.replace(tzinfo=UTC)

    if data.status:
        post.status = data.status

    now = datetime.now(UTC)

    if post.status == "published" and scheduled_at <= now:
        # 计划时间已到，立即发布
        if post.published_at is None:
            post.published_at = scheduled_at
        post.scheduled_at = None
        message = "文章已立即发布"
    else:
        post.scheduled_at = scheduled_at
        message = "定时发布已设置"

    await db.flush()

    await invalidate_cache("posts")
    await invalidate_post_detail_cache(post.slug)

    return BaseResponse(message=message)


@router.delete(
    "/admin/posts/{post_id}/schedule",
    response_model=BaseResponse,
    summary="取消定时发布",
    description="取消文章的定时发布计划（清空 scheduled_at），不影响文章当前状态。",
)
async def cancel_schedule(
    post_id: int,
    db: DB,
    current_user: CurrentStaff,
):
    """取消文章的定时发布"""
    result = await db.execute(select(Post).where(Post.id == post_id))
    post = result.scalar_one_or_none()

    if not post:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="文章不存在",
        )

    post.scheduled_at = None
    await db.flush()

    return BaseResponse(message="定时发布已取消")
