"""
热门文章排行 API

根据浏览量、点赞数、评论数综合排序，提供日榜、周榜、月榜和总榜。

- period=all：直接按总浏览量 views 排序
- period=day/week/month：通过 PostViewHistory 表限制时间范围，
  以近期浏览量为主，结合点赞数、评论数计算综合分数排序
"""

from datetime import datetime, timedelta
from typing import Literal

from fastapi import APIRouter, Query
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.orm import defer

from backend.core.auth import DB
from backend.core.cache import cache, make_cache_key
from backend.models.blog import Comment, Post, PostViewHistory, post_likes
from backend.utils.compat import UTC

router = APIRouter(tags=["热门排行"])

Period = Literal["day", "week", "month", "all"]


# ═══════════════════════════════════════════════════════════════════════════
# 响应体文档模型（仅供 OpenAPI `responses={200: {"model": ...}}` 声明使用，
# 运行时不做序列化过滤——实际响应以 handler 返回字面量为准）
# ═══════════════════════════════════════════════════════════════════════════


class HotPostItemDoc(BaseModel):
    """榜单中的单篇文章条目（缓存命中路径回放的是同构 dict，两路径字段集合一致）。"""

    id: int = Field(..., description="文章 ID")
    title: dict[str, str] = Field(
        ..., description="多语言标题 dict（JSON 列原样返回，未做请求语言解析）"
    )
    slug: str = Field(..., description="文章 slug")
    cover_image: str | None = Field(None, description="封面图 URL，未设置时为 null")
    views: int = Field(..., description="累计浏览量（Post.views 列）")
    recent_views: int | None = Field(
        None,
        description="统计窗口内的近期浏览量（源自 post_view_histories）；period=all 时恒为 null",
    )
    likes_count: int = Field(..., description="点赞总数（post_likes 关联表计数）")
    comments_count: int = Field(..., description="已过审评论数（active=True 的评论计数）")
    score: int = Field(
        ...,
        description="排序综合分：period=all 时等于总浏览量；周期榜为 近期浏览 + 点赞*5 + 评论*3",
    )
    published_at: str | None = Field(
        None, description="发布时间 ISO 8601 字符串（handler isoformat()），未发布为 null"
    )
    created_at: str | None = Field(
        None, description="创建时间 ISO 8601 字符串（handler isoformat()），缺失为 null"
    )


class HotPostsRankingResponseDoc(BaseModel):
    """``GET /api/ranking/posts`` 的响应体（裸 dict，无 success/data 信封）。"""

    period: str = Field(
        ..., description="回显统计周期：day / week / month / all（month 实际窗口为 30 天）"
    )
    items: list[HotPostItemDoc] = Field(
        default_factory=list,
        description=(
            "榜单条目：all 榜按总浏览量倒序直接截断；周期榜按综合分重排后截断 limit 条；"
            "窗口内无任何候选文章时是空数组"
        ),
    )


@router.get(
    "/ranking/posts",
    summary="热门文章排行榜",
    description=(
        "根据浏览量、点赞数、评论数综合排序的热门文章排行榜。支持按时间周期过滤。"
        "公开接口、无需鉴权；结果带 60s 响应缓存（命中缓存与实时计算的响应体同构）。"
        "响应为裸 dict（period + items，无信封），items 的 title 是未解析的多语言 dict。"
    ),
    responses={200: {"model": HotPostsRankingResponseDoc}},
)
async def get_hot_posts(
    db: DB,
    period: Period = Query("week", description="统计周期：day/week/month/all"),
    limit: int = Query(10, ge=1, le=50, description="返回数量"),
):
    """获取热门文章排行榜"""
    # 榜单是首页/侧栏级别的公开读流量，每次都要跑 1 次候选查询 + 2 个 GROUP BY。
    # 键挂在 "posts:" 前缀下，文章增删改的 invalidate_cache("posts") 会顺带清掉；
    # TTL 取 60s，与首页 /posts/hot 的 SWR 口径一致，不让"今日热榜"比页面缓存更陈旧。
    cache_key = make_cache_key("posts", "ranking", period, str(limit))
    cached = await cache.get(cache_key)
    if isinstance(cached, dict):
        return cached

    now = datetime.now(UTC)

    # 榜单只用到 id/title/slug/cover_image/views/时间戳，正文与 meta 大字段全部 defer：
    # 候选集是 limit*5（最大 250 行）整行 Post，带上 content/content_html/JSON meta
    # 等于每次排行都从 DB 拖几 MB 过来再扔掉。
    list_defer = (
        defer(Post.content),
        defer(Post.encrypted_content),
        defer(Post.meta_fields),
        defer(Post.meta_title),
        defer(Post.meta_description),
        defer(Post.meta_keywords),
    )

    # period=all 直接按总浏览量排序
    if period == "all":
        query = (
            select(Post)
            .options(*list_defer)
            .where(Post.status == "published")
            .order_by(Post.views.desc(), Post.created_at.desc())
            .limit(limit)
        )
        result = await db.execute(query)
        posts = result.scalars().all()
        recent_views_map: dict[int, int] = {}
    else:
        # 计算时间范围
        if period == "day":
            delta = timedelta(days=1)
        elif period == "week":
            delta = timedelta(weeks=1)
        else:  # month
            delta = timedelta(days=30)
        since = now - delta

        # 子查询：统计该时间段内每个 post 的浏览次数
        view_counts_subq = (
            select(
                PostViewHistory.post_id.label("pid"),
                func.count().label("recent_views"),
            )
            .where(PostViewHistory.viewed_at >= since)
            .group_by(PostViewHistory.post_id)
            .subquery()
        )

        # 取候选集（按近期浏览数倒序，取 limit*5 以便后续用综合分数重排）
        candidate_query = (
            select(
                Post,
                func.coalesce(view_counts_subq.c.recent_views, 0).label("recent_views"),
            )
            .outerjoin(view_counts_subq, view_counts_subq.c.pid == Post.id)
            .options(*list_defer)
            .where(Post.status == "published")
            .order_by(
                func.coalesce(view_counts_subq.c.recent_views, 0).desc(),
                Post.views.desc(),
            )
            .limit(limit * 5)
        )
        result = await db.execute(candidate_query)
        rows = result.all()
        posts = [row[0] for row in rows]
        recent_views_map = {row[0].id: int(row[1] or 0) for row in rows}

    if not posts:
        return {"period": period, "items": []}

    post_ids = [p.id for p in posts]

    # 批量获取点赞数（通过 post_likes 关联表）
    likes_result = await db.execute(
        select(post_likes.c.post_id, func.count().label("cnt"))
        .where(post_likes.c.post_id.in_(post_ids))
        .group_by(post_likes.c.post_id)
    )
    likes_counts = {row[0]: int(row[1]) for row in likes_result.all()}

    # 批量获取评论数
    comments_result = await db.execute(
        select(Comment.post_id, func.count().label("cnt"))
        .where(Comment.post_id.in_(post_ids), Comment.active.is_(True))
        .group_by(Comment.post_id)
    )
    comments_counts = {row[0]: int(row[1]) for row in comments_result.all()}

    # 构造条目并计算综合分数
    items = []
    for p in posts:
        recent_views = recent_views_map.get(p.id, 0)
        likes_count = likes_counts.get(p.id, 0)
        comments_count = comments_counts.get(p.id, 0)

        if period == "all":
            # 总榜：分数 = 总浏览量
            score = p.views
        else:
            # 周期榜：分数 = 近期浏览量 + 点赞数 * 5 + 评论数 * 3
            score = recent_views + likes_count * 5 + comments_count * 3

        items.append(
            {
                "id": p.id,
                "title": p.title,
                "slug": p.slug,
                "cover_image": p.cover_image,
                "views": p.views,
                "recent_views": recent_views if period != "all" else None,
                "likes_count": likes_count,
                "comments_count": comments_count,
                "score": score,
                "published_at": p.published_at.isoformat() if p.published_at else None,
                "created_at": p.created_at.isoformat() if p.created_at else None,
            }
        )

    # 非 all 周期：按综合分数重新排序后截断
    if period != "all":
        items.sort(key=lambda x: x["score"], reverse=True)
        items = items[:limit]

    result = {"period": period, "items": items}
    await cache.set(cache_key, result, 60)
    return result
