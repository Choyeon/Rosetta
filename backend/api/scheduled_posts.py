"""
定时发布 API

提供管理员对文章定时发布的管理能力，以及将到期文章自动转为已发布的工具函数。

路由设计：
- 管理接口:
    GET    /api/admin/posts/scheduled           获取待发布的定时文章列表
    PUT    /api/admin/posts/{post_id}/schedule  设置/更新定时发布
    DELETE /api/admin/posts/{post_id}/schedule  取消定时发布

定时发布模型：
- ``status`` 为 ``scheduled``（本模块 PUT 口写的等待态）或 ``published``（历史数据），
  且 ``scheduled_at`` 为未来时间，表示"定时等待"。
  对匿名方是否可见由 ``services/post_access.py::post_is_publicly_visible`` 单独判定
  （看的是 published_at 未到 + 状态不是 published），所以这里的状态字段只决定"谁来推进它"。
- publish_due_posts(db) 把 scheduled_at <= now 的文章真正发布：status=published、
  写入 published_at 并清空 scheduled_at。main.py 的 60s 扫描循环复用同一个函数。
"""

from datetime import datetime

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select

from backend.core.auth import DB, CurrentStaff
from backend.core.cache import invalidate_cache, invalidate_post_detail_cache
from backend.models.blog import Post
from backend.schemas import BaseResponse
from backend.services.post_cache import (
    invalidate_post_aggregate_caches,
    invalidate_series_chapter_caches,
)
from backend.utils.compat import UTC, to_utc_instant

router = APIRouter(tags=["定时发布"])


class ScheduleRequest(BaseModel):
    """设置定时发布请求"""

    scheduled_at: datetime = Field(..., description="计划发布时间（UTC）")
    status: str | None = Field(
        None,
        pattern="^(draft|published|scheduled)$",
        description="目标状态，缺省 scheduled（等待发布）；传 published 表示立即发布；"
        "draft 不支持定时发布（400）。计划时间已过去时一律立即发布。",
    )


async def publish_due_posts(db) -> int:
    """
    发布到期的定时文章

    查询 ``status`` 为 ``scheduled``（本接口写入的等待状态）或 ``published``（历史数据），
    且 ``scheduled_at <= now`` 的文章，把状态定为 published、写入 published_at 并清空
    scheduled_at。

    两条状态都要捞：只捞 published 的话，本文件 PUT 口写进去的 scheduled 行永远不会被这个
    函数推进——`GET /admin/posts/scheduled` 却对外承诺"查询前会先触发到期文章的发布，
    列表里不会再包含已到点的文章"，于是待发布队列会一直挂着早就到点的文章，
    直到 main.py 的 60s 扫描循环（或该循环没起来时，永远）。

    Args:
        db: 数据库会话

    Returns:
        int: 本次实际发布的文章数量
    """
    now = datetime.now(UTC)
    query = select(Post).where(
        Post.status.in_(("scheduled", "published")),
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
        post.status = "published"
        post.scheduled_at = None
        count += 1

    if count:
        await db.flush()
        # 到点的定时文章此前对匿名访客是 404，列表缓存里也不存在；不立刻失效的话，
        # posts:* 最长 300s 仍按"未发布"返回，首页/分类会在到点后几分钟内继续查不到它。
        await invalidate_cache("posts")
        # 到点即入公开章节目录：同系列其它章节的 position / prev / next 与 post_count 都要重算
        await invalidate_series_chapter_caches(db, {post.series_id for post in posts})
        # 聚合缓存 + 前端 swr 页面同属读侧：定时发布首次让文章对匿名方可见，
        # 归档计数、首页统计、推荐位、Nitro 页面缓存全部失真。
        await invalidate_post_aggregate_caches()

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
    description=(
        "为文章设置定时发布时间。status 缺省为 scheduled（进入发布扫描器的等待状态），"
        "传 published 表示立即可见；draft 会被 400 拒绝（草稿不参与定时发布）。"
        "计划时间已过去时一律立即发布并清空 scheduled_at。"
    ),
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

    # 落库前折算成 UTC 瞬时（朴素按 UTC 解释、带偏移的换算），口径见 compat.to_utc_instant
    scheduled_at = to_utc_instant(data.scheduled_at)

    # 状态缺省值必须是 "scheduled"（唯一被发布扫描器认的"等待中"状态）。
    # 原先缺省是 None → 草稿仍是草稿，而 publish_due_posts / main.py 的定时循环
    # 只捞 scheduled / published，于是接口回"定时发布已设置"、文章永远不会发布，
    # 还会一直留在 GET /admin/posts/scheduled 列表里（scheduled_at 已过期）。
    target_status = data.status or "scheduled"
    if target_status == "draft":
        # 草稿不参与定时发布：要么现在就让它等待发布（scheduled），要么就别排期。
        # 静默接受 draft 只会再造一个"说了会发、其实不发"的死状态。
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="草稿不支持定时发布：请改用 scheduled（等待发布）或 published（立即发布）",
        )

    now = datetime.now(UTC)

    if scheduled_at <= now:
        # 计划时间已到（或已过去）：立即发布，别让作者等到下一个扫描周期
        post.status = "published"
        if post.published_at is None:
            post.published_at = scheduled_at
        post.scheduled_at = None
        message = "文章已立即发布"
        just_published = True
    else:
        post.status = target_status
        post.scheduled_at = scheduled_at
        message = "定时发布已设置"
        just_published = False

    await db.flush()

    await invalidate_cache("posts")
    await invalidate_post_detail_cache(post.slug)
    # 立即发布 = 文章首次对匿名方可见。归档计数 / 首页统计 / 推荐位 / Nitro 600s swr
    # 页面都会失真（前台表现："定时已到但首页仍看不到新文章"）。
    if just_published:
        await invalidate_post_aggregate_caches()
        # 立即发布 = 这篇此刻进入公开章节目录，同系列其它章节的序号与上下章要重算
        await invalidate_series_chapter_caches(db, {post.series_id})

    return BaseResponse(message=message)


@router.delete(
    "/admin/posts/{post_id}/schedule",
    response_model=BaseResponse,
    summary="取消定时发布",
    description=(
        "清空文章的 scheduled_at。状态为 scheduled 的行会同时回到 draft——"
        "只清时间不改状态会造出「定时等待但没有计划时间」的死状态：扫描循环只捞 "
        "scheduled_at 非空的行，这种文章既不会被发布，也不再出现在待发布队列里。"
    ),
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

    was_scheduled = post.status == "scheduled"
    post.scheduled_at = None
    if was_scheduled:
        # 回到草稿：既不会被扫描器发布，也不会以"等待中"的形态卡在列表/编辑页里。
        post.status = "draft"
    await db.flush()

    if not was_scheduled:
        # 原本就是 published（历史数据 / 立即发布后残留的计划时间）：取消计划时间等于
        # 这篇对匿名方从"未到点"变成"可见"，读侧三份缓存必须一起清，否则 TTL 内
        # 首页/列表/详情页仍按不可见返回（与 PUT 口立即发布的分支同口径）。
        await invalidate_cache("posts")
        await invalidate_post_detail_cache(post.slug)
        await invalidate_post_aggregate_caches()
        # 取消计划让这篇重新对匿名方可见 = 回到公开章节目录，同系列序号要重算
        await invalidate_series_chapter_caches(db, {post.series_id})

    return BaseResponse(
        message="定时发布已取消，文章已回到草稿" if was_scheduled else "定时发布已取消"
    )
