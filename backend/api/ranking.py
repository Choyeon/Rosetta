"""
热门文章排行 API

根据浏览量、点赞数、评论数综合排序，提供日榜、周榜、月榜和总榜。

- period=all：直接按总浏览量 views 排序
- period=day/week/month：通过 PostViewHistory 表限制时间范围，
  以近期浏览量为主，结合点赞数、评论数计算综合分数排序
"""

from datetime import datetime, timedelta
from typing import Any, Literal

from fastapi import APIRouter, Query
from sqlalchemy import func, select

from backend.core.auth import DB
from backend.models.blog import Comment, Post, PostViewHistory, post_likes
from backend.utils.compat import UTC

router = APIRouter(tags=["热门排行"])

Period = Literal["day", "week", "month", "all"]


@router.get(
    "/ranking/posts",
    summary="热门文章排行榜",
    description="根据浏览量、点赞数、评论数综合排序的热门文章排行榜。支持按时间周期过滤。",
)
async def get_hot_posts(
    db: DB,
    period: Period = Query("week", description="统计周期：day/week/month/all"),
    limit: int = Query(10, ge=1, le=50, description="返回数量"),
) -> dict[str, Any]:
    """获取热门文章排行榜"""
    now = datetime.now(UTC)

    # period=all 直接按总浏览量排序
    if period == "all":
        query = (
            select(Post)
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

    return {"period": period, "items": items}
