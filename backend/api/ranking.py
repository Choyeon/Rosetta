"""
热门文章排行 API

根据文章综合热度（物化列 ``Post.hot_score``）排序，提供日榜、周榜、月榜和总榜。

- ``period`` 仅作为响应回显字段，所有周期统一按 ``hot_score`` 倒序。
- ``hot_score`` 由写入事件（浏览 / 点赞 / 评论审核）增量维护并周期重算
  （见 ``backend/services/hot_score.py``），因此本接口不再每次请求对
  ``post_view_histories`` / ``comments`` 做全表聚合——原先 day/week/month 的
  ``recent_views`` 窗口 ``GROUP BY`` 是热榜最大的读放大来源。
"""

from typing import Literal

from fastapi import APIRouter, Query
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.orm import defer

from backend.core.auth import DB
from backend.core.cache import cache, namespaced_key
from backend.models.blog import Comment, Post, post_likes
from backend.services.post_access import (
    post_access_flags,
    post_media_flags,
    publicly_listable_posts,
)

router = APIRouter(tags=["热门排行"])

Period = Literal["day", "week", "month", "all"]


# ═════════════════════════════════════════════════════════════════════════
# 响应体文档模型（仅供 OpenAPI `responses={200: {"model": ...}}` 声明使用，
# 运行时不做序列化过滤——实际响应以 handler 返回字面量为准）
# ═════════════════════════════════════════════════════════════════════════


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
        description=(
            "近期浏览量：已改为按物化 hot_score 排序，不再做窗口聚合，"
            "故此字段恒为 null（保留键位以兼容既有前端读取）"
        ),
    )
    likes_count: int = Field(..., description="点赞总数（post_likes 关联表计数）")
    comments_count: int = Field(..., description="已过审评论数（active=True 的评论计数）")
    score: int = Field(
        ...,
        description=(
            "文章综合热度 = Post.hot_score 物化列（views + likes*5 + 有效评论*3），"
            "由写入事件增量维护、周期重算；所有周期统一按此排序"
        ),
    )
    published_at: str | None = Field(
        None, description="发布时间 ISO 8601 字符串（handler isoformat()），未发布为 null"
    )
    created_at: str | None = Field(
        None, description="创建时间 ISO 8601 字符串（handler isoformat()），缺失为 null"
    )
    # 存在性三位（批次 #120 口径）：只说"有没有"，不带地址。榜单页把这些条目补齐成
    # PostCard 的形状渲染，缺这三键就是"综合榜有徽标、周期榜整排没有"。
    has_audio: bool = Field(False, description="是否带站内音频")
    has_video: bool = Field(False, description="是否带站内视频")
    has_embed: bool = Field(False, description="是否带 YouTube 嵌入")
    # 预计阅读分钟数（批次 #137）：持久化列，卡片与详情页共用同一个数。
    reading_time: int = Field(1, description="预计阅读分钟数（Post.reading_time 持久化列）")
    is_password_protected: bool = Field(False, description="是否需要访问密码（不输出密码本身）")


class HotPostsRankingResponseDoc(BaseModel):
    """``GET /api/ranking/posts`` 的响应体（裸 dict，无 success/data 信封）。"""

    period: str = Field(
        ..., description="回显统计周期：day / week / month / all（仅回显，排序均按 hot_score）"
    )
    items: list[HotPostItemDoc] = Field(
        default_factory=list,
        description=(
            "榜单条目：所有周期统一按 hot_score 倒序直接截断 limit 条；"
            "窗口内无任何候选文章时是空数组"
        ),
    )


@router.get(
    "/ranking/posts",
    summary="热门文章排行榜",
    description=(
        "根据文章综合热度（物化列 hot_score = views + likes*5 + 有效评论*3）排序的热门文章排行榜。"
        "公开接口、无需鉴权；结果带 60s 响应缓存（命中缓存与实时计算的响应体同构）。"
        "响应为裸 dict（period + items，无信封），items 的 title 是未解析的多语言 dict。"
        "period 仅作回显，所有周期均按 hot_score 排序。"
    ),
    responses={200: {"model": HotPostsRankingResponseDoc}},
)
async def get_hot_posts(
    db: DB,
    period: Period = Query("week", description="统计周期：day/week/month/all（仅回显）"),
    limit: int = Query(10, ge=1, le=50, description="返回数量"),
):
    """获取热门文章排行榜"""
    # 榜单是首页/侧栏级别的公开读流量，每次都要跑 1 次候选查询 + 2 个 GROUP BY。
    # 键挂在 "posts:" 命名空间下，文章增删改的 invalidate_cache("posts") 会撞世代（bump），
    # 旧键自然过期；TTL 取 60s，与首页 /posts/hot 的 SWR 口径一致。
    cache_key = await namespaced_key("posts", "ranking", period, str(limit))
    cached = await cache.get(cache_key)
    if isinstance(cached, dict):
        return cached

    # 榜单只用到 id/title/slug/cover_image/views/时间戳，正文与 meta 大字段全部 defer：
    # 候选集是 limit（最大 50）整行 Post，带上 content/content_html/JSON meta 等于
    # 每次排行都从 DB 拖几百 KB 过来再扔掉。
    list_defer = (
        defer(Post.content),
        defer(Post.encrypted_content),
        defer(Post.meta_fields),
        defer(Post.meta_title),
        defer(Post.meta_description),
        defer(Post.meta_keywords),
    )

    # 统一按物化 hot_score 排序：彻底消除原先 day/week/month 对 PostViewHistory 的窗口全表聚合。
    query = (
        select(Post)
        .options(*list_defer)
        .where(publicly_listable_posts())
        .order_by(Post.hot_score.desc(), Post.published_at.desc())
        .limit(limit)
    )
    result = await db.execute(query)
    posts = result.scalars().all()

    if not posts:
        return {"period": period, "items": []}

    post_ids = [p.id for p in posts]

    # 仅对 top-N 批量取点赞数（通过 post_likes 关联表）与有效评论数，用于展示卡片，不再参与排序。
    likes_result = await db.execute(
        select(post_likes.c.post_id, func.count().label("cnt"))
        .where(post_likes.c.post_id.in_(post_ids))
        .group_by(post_likes.c.post_id)
    )
    likes_counts = {row[0]: int(row[1]) for row in likes_result.all()}

    comments_result = await db.execute(
        select(Comment.post_id, func.count().label("cnt"))
        .where(Comment.post_id.in_(post_ids), Comment.active.is_(True))
        .group_by(Comment.post_id)
    )
    comments_counts = {row[0]: int(row[1]) for row in comments_result.all()}

    # 构造条目（score 直接取物化 hot_score，不再实时计算）
    items = []
    for p in posts:
        likes_count = likes_counts.get(p.id, 0)
        comments_count = comments_counts.get(p.id, 0)

        items.append(
            {
                "id": p.id,
                "title": p.title,
                "slug": p.slug,
                "cover_image": p.cover_image,
                "views": p.views,
                "recent_views": None,
                "likes_count": likes_count,
                "comments_count": comments_count,
                "score": p.hot_score,
                "published_at": p.published_at.isoformat() if p.published_at else None,
                "created_at": p.created_at.isoformat() if p.created_at else None,
                **post_media_flags(p),
                "reading_time": p.reading_time or 1,
                **post_access_flags(p),
            }
        )

    result = {"period": period, "items": items}
    await cache.set(cache_key, result, 60)
    return result
