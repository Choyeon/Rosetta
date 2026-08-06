"""
推荐算法服务

实现类似 X/Twitter 的文章推荐算法，综合考虑：
- 浏览量 (30%)
- 点赞数 (20%)
- 评论数 (15%)
- 时间衰减 (25%)
- 标签匹配 (10%)
"""

import logging
import math
from collections import Counter
from datetime import datetime
from typing import Any

from fastapi import Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from backend.core.database import get_db
from backend.models.blog import Comment, Post, PostViewHistory, post_likes, post_tags
from backend.services.cache_service import CacheService, get_cache_service
from backend.utils.compat import UTC

logger = logging.getLogger(__name__)

# 缓存配置
RECOMMENDATION_TTL = 300  # 推荐列表缓存 5 分钟
SIMILAR_POSTS_TTL = 1800  # 相似文章缓存 30 分钟

# 权重配置
WEIGHT_VIEWS = 0.30  # 浏览量权重
WEIGHT_LIKES = 0.20  # 点赞数权重
WEIGHT_COMMENTS = 0.15  # 评论数权重
WEIGHT_TIME_DECAY = 0.25  # 时间衰减权重
WEIGHT_TAG_MATCH = 0.10  # 标签匹配权重

# 时间衰减参数
DECAY_LAMBDA = 0.1  # 衰减系数，10 天后衰减至约 36.8%


class RecommendationService:
    """
    推荐算法服务类

    实现文章推荐算法，支持：
    - 获取推荐文章列表
    - 获取相似文章
    - 计算文章得分
    """

    def __init__(
        self,
        db: AsyncSession,
        cache: CacheService | None = None,
    ):
        """
        初始化推荐服务

        Args:
            db: 数据库会话
            cache: 缓存服务实例
        """
        self._db = db
        self._cache = cache or CacheService()

    def _calculate_time_decay(self, published_at: datetime | None) -> float:
        """
        计算时间衰减因子

        使用指数衰减公式: score = exp(-λ * days_old)
        λ = 0.1 时，10 天后衰减至约 36.8%，30 天后衰减至约 5%

        Args:
            published_at: 发布时间

        Returns:
            衰减因子 (0-1)
        """
        if not published_at:
            return 0.5  # 默认中等权重

        now = datetime.now(UTC)
        # 确保 published_at 有时区信息
        if published_at.tzinfo is None:
            from datetime import timezone

            published_at = published_at.replace(tzinfo=timezone.utc)

        days_old = (now - published_at).days
        return math.exp(-DECAY_LAMBDA * max(0, days_old))

    def _calculate_score(
        self,
        views: int,
        likes_count: int,
        comments_count: int,
        published_at: datetime | None,
        tag_match_score: float = 0.0,
    ) -> float:
        """
        计算文章综合得分

        Args:
            views: 浏览量
            likes_count: 点赞数
            comments_count: 评论数
            published_at: 发布时间
            tag_match_score: 标签匹配得分 (0-1)

        Returns:
            综合得分
        """
        # 使用对数函数平滑浏览量和互动数据
        views_score = math.log(views + 1)
        likes_score = math.log(likes_count + 1)
        comments_score = math.log(comments_count + 1)

        # 时间衰减
        time_score = self._calculate_time_decay(published_at)

        # 加权计算
        total_score = (
            WEIGHT_VIEWS * views_score
            + WEIGHT_LIKES * likes_score
            + WEIGHT_COMMENTS * comments_score
            + WEIGHT_TIME_DECAY * time_score * 10  # 放大时间因子
            + WEIGHT_TAG_MATCH * tag_match_score * 10  # 放大标签匹配因子
        )

        return total_score

    async def _get_user_tag_preferences(
        self,
        user_id: int | None,
        days: int = 30,
    ) -> Counter:
        """
        获取用户标签偏好

        统计用户最近 N 天浏览的文章标签频次

        Args:
            user_id: 用户 ID，None 则返回空
            days: 统计天数

        Returns:
            标签 ID 频次计数器
        """
        if not user_id:
            return Counter()

        from datetime import timedelta

        cutoff_date = datetime.now(UTC) - timedelta(days=days)

        # 查询用户浏览历史中的标签
        query = (
            select(post_tags.c.tag_id)
            .select_from(PostViewHistory)
            .join(Post, PostViewHistory.post_id == Post.id)
            .join(post_tags, Post.id == post_tags.c.post_id)
            .where(
                PostViewHistory.user_id == user_id,
                PostViewHistory.viewed_at >= cutoff_date,
            )
        )

        result = await self._db.execute(query)
        tag_ids = [row[0] for row in result.fetchall()]

        return Counter(tag_ids)

    async def get_recommended_posts(
        self,
        user_id: int | None = None,
        page: int = 1,
        page_size: int = 20,
        exclude_post_ids: list[int] | None = None,
    ) -> dict[str, Any]:
        """
        获取推荐文章列表

        Args:
            user_id: 当前用户 ID（用于个性化推荐）
            page: 页码
            page_size: 每页数量
            exclude_post_ids: 需要排除的文章 ID 列表

        Returns:
            包含推荐文章和分页信息的字典
        """
        cache_key = self._cache.build_key_with_hash(
            "recommended_posts",
            user_id=user_id or "anonymous",
            page=page,
            page_size=page_size,
        )

        # 尝试从缓存获取
        cached = await self._cache.get(cache_key)
        if cached:
            return cached

        exclude_ids = exclude_post_ids or []

        # 获取用户标签偏好
        user_tag_prefs = await self._get_user_tag_preferences(user_id)

        # 查询所有已发布文章的统计数据
        stats_query = (
            select(
                Post.id,
                Post.views,
                Post.published_at,
                func.count(func.distinct(post_likes.c.user_id)).label("likes_count"),
                func.count(func.distinct(Comment.id)).label("comments_count"),
            )
            .outerjoin(post_likes, Post.id == post_likes.c.post_id)
            .outerjoin(
                Comment,
                (Post.id == Comment.post_id) & (Comment.active == True),  # noqa: E712
            )
            .where(
                Post.status == "published",
                Post.id.notin_(exclude_ids) if exclude_ids else True,
            )
            .group_by(Post.id)
        )

        stats_result = await self._db.execute(stats_query)
        post_stats = {
            row.id: {
                "views": row.views,
                "likes_count": row.likes_count,
                "comments_count": row.comments_count,
                "published_at": row.published_at,
            }
            for row in stats_result.fetchall()
        }

        # 获取每篇文章的标签
        tags_query = select(post_tags.c.post_id, post_tags.c.tag_id).where(
            post_tags.c.post_id.in_(list(post_stats.keys()))
        )
        tags_result = await self._db.execute(tags_query)
        post_tag_map: dict[int, list[int]] = {}
        for row in tags_result.fetchall():
            if row.post_id not in post_tag_map:
                post_tag_map[row.post_id] = []
            post_tag_map[row.post_id].append(row.tag_id)

        # 计算每篇文章的得分
        scored_posts: list[tuple[int, float]] = []
        for post_id, stats in post_stats.items():
            # 计算标签匹配得分
            tag_match_score = 0.0
            if user_tag_prefs and post_id in post_tag_map:
                post_tag_ids = post_tag_map[post_id]
                matched_count = sum(
                    user_tag_prefs[tid] for tid in post_tag_ids if tid in user_tag_prefs
                )
                if matched_count > 0:
                    tag_match_score = min(1.0, matched_count / sum(user_tag_prefs.values()))

            score = self._calculate_score(
                views=stats["views"],
                likes_count=stats["likes_count"],
                comments_count=stats["comments_count"],
                published_at=stats["published_at"],
                tag_match_score=tag_match_score,
            )
            scored_posts.append((post_id, score))

        # 按得分排序
        scored_posts.sort(key=lambda x: x[1], reverse=True)

        # 分页
        total = len(scored_posts)
        start = (page - 1) * page_size
        end = start + page_size
        page_post_ids = [pid for pid, _ in scored_posts[start:end]]

        # 获取完整的文章数据
        if page_post_ids:
            posts_query = (
                select(Post)
                .options(
                    selectinload(Post.author),
                    selectinload(Post.category),
                    selectinload(Post.tags),
                )
                .where(Post.id.in_(page_post_ids))
            )
            posts_result = await self._db.execute(posts_query)
            posts_map = {post.id: post for post in posts_result.scalars().all()}
            # 按得分顺序排列
            posts = [posts_map[pid] for pid in page_post_ids if pid in posts_map]
        else:
            posts = []

        result = {
            "items": posts,
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": math.ceil(total / page_size) if total > 0 else 1,
        }

        # 缓存结果
        await self._cache.set(cache_key, result, ttl=RECOMMENDATION_TTL)

        return result

    async def get_similar_posts(
        self,
        post_id: int,
        limit: int = 5,
    ) -> list[Post]:
        """
        获取相似文章（基于标签匹配）

        Args:
            post_id: 当前文章 ID
            limit: 返回数量

        Returns:
            相似文章列表
        """
        cache_key = f"similar_posts:{post_id}:{limit}"

        # 尝试从缓存获取
        cached = await self._cache.get(cache_key)
        if cached:
            return cached

        # 获取当前文章的标签和分类
        post_query = select(Post).options(selectinload(Post.tags)).where(Post.id == post_id)
        post_result = await self._db.execute(post_query)
        current_post = post_result.scalar_one_or_none()

        if not current_post:
            return []

        tag_ids = [tag.id for tag in current_post.tags]
        category_id = current_post.category_id

        # 查询具有相同标签或分类的文章
        similar_query = (
            select(
                Post,
                func.count(post_tags.c.tag_id).label("tag_match_count"),
            )
            .outerjoin(post_tags, Post.id == post_tags.c.post_id)
            .options(
                selectinload(Post.author),
                selectinload(Post.category),
                selectinload(Post.tags),
            )
            .where(
                Post.id != post_id,
                Post.status == "published",
            )
        )

        # 如果有标签，按标签匹配
        if tag_ids:
            similar_query = similar_query.where(post_tags.c.tag_id.in_(tag_ids))
        # 如果没有标签，按分类匹配
        elif category_id:
            similar_query = similar_query.where(Post.category_id == category_id)

        similar_query = (
            similar_query.group_by(Post.id)
            .order_by(func.count(post_tags.c.tag_id).desc(), Post.views.desc())
            .limit(limit)
        )

        result = await self._db.execute(similar_query)
        posts = [row.Post for row in result.fetchall()]

        # 如果结果不足，补充热门文章
        if len(posts) < limit:
            existing_ids = [p.id for p in posts] + [post_id]
            supplement_query = (
                select(Post)
                .options(
                    selectinload(Post.author),
                    selectinload(Post.category),
                    selectinload(Post.tags),
                )
                .where(
                    Post.id.notin_(existing_ids),
                    Post.status == "published",
                )
                .order_by(Post.views.desc())
                .limit(limit - len(posts))
            )
            supplement_result = await self._db.execute(supplement_query)
            posts.extend(supplement_result.scalars().all())

        # 缓存结果
        await self._cache.set(cache_key, posts, ttl=SIMILAR_POSTS_TTL)

        return posts


async def get_recommendation_service(
    db: AsyncSession = Depends(get_db),
    cache: CacheService = Depends(get_cache_service),
) -> RecommendationService:
    """获取推荐服务实例（依赖注入）"""
    return RecommendationService(db, cache)
