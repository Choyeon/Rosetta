"""
文章服务层

封装文章相关的业务逻辑，包括：
- 文章列表查询
- 文章详情获取
- 文章创建、更新、删除
- 点赞功能
- 缓存集成
"""

import logging
from datetime import datetime
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.concurrency import concurrent_query
from backend.models.blog import Post
from backend.repositories.post import PostRepository
from backend.services.cache_service import CacheService
from backend.utils.compat import UTC

logger = logging.getLogger(__name__)

POST_LIST_TTL = 300
POST_DETAIL_TTL = 600
POST_STATS_TTL = 60


class PostService:
    """
    文章服务类

    封装文章相关的业务逻辑，使用 PostRepository 进行数据访问，
    集成缓存提高性能。

    Attributes:
        db: 数据库会话
        repo: 文章仓储实例
        cache: 缓存服务实例

    Example:
        >>> async with get_db_context() as db:
        ...     service = PostService(db)
        ...     posts = await service.get_post_list(page=1, page_size=20)
    """

    def __init__(
        self,
        db: AsyncSession,
        cache: CacheService | None = None,
    ):
        """
        初始化文章服务

        Args:
            db: 数据库会话
            cache: 缓存服务实例，None 则创建新实例
        """
        self._db = db
        self._repo = PostRepository(db)
        self._cache = cache or CacheService()

    async def get_post_list(
        self,
        page: int = 1,
        page_size: int = 20,
        status: str | None = "published",
        category_id: int | None = None,
        tag_id: int | None = None,
        author_id: int | None = None,
        is_pinned: bool | None = None,
        order_by: str = "published_at",
        descending: bool = True,
        use_cache: bool = True,
    ) -> dict[str, Any]:
        """
        获取文章列表

        Args:
            page: 页码
            page_size: 每页数量
            status: 文章状态
            category_id: 分类 ID
            tag_id: 标签 ID
            author_id: 作者 ID
            is_pinned: 是否置顶
            order_by: 排序字段
            descending: 是否降序
            use_cache: 是否使用缓存

        Returns:
            分页结果字典
        """
        cache_key = self._cache.build_key_with_hash(
            "post_list",
            page=page,
            page_size=page_size,
            status=status,
            category_id=category_id,
            tag_id=tag_id,
            author_id=author_id,
            is_pinned=is_pinned,
            order_by=order_by,
            descending=descending,
        )

        async def fetch():
            result = await self._repo.paginate_posts(
                page=page,
                page_size=page_size,
                status=status,
                category_id=category_id,
                tag_id=tag_id,
                author_id=author_id,
                is_pinned=is_pinned,
                order_by=order_by,
                descending=descending,
            )
            return result.to_dict()

        if use_cache:
            return await self._cache.get_or_set(
                cache_key,
                fetch,
                ttl=POST_LIST_TTL,
            )

        return await fetch()

    async def get_post_detail(
        self,
        post_id: int | None = None,
        slug: str | None = None,
        user_id: int | None = None,
        use_cache: bool = True,
    ) -> dict[str, Any] | None:
        """
        获取文章详情

        并行获取文章基本信息、统计数据、用户点赞状态等。

        Args:
            post_id: 文章 ID
            slug: 文章 slug
            user_id: 当前用户 ID（用于判断是否已点赞）
            use_cache: 是否使用缓存

        Returns:
            文章详情字典，不存在返回 None
        """
        if post_id is None and slug is None:
            return None

        cache_key = self._cache.build_key(
            "post_detail",
            post_id or slug,
            suffix=str(user_id) if user_id else "anonymous",
        )

        async def fetch():
            if slug:
                post = await self._repo.get_by_slug_with_relations(slug)
            else:
                post = await self._repo.get_by_id(post_id)

            if post is None:
                return None

            async def get_stats():
                return await self._repo.get_post_stats(post.id)

            async def get_is_liked():
                if user_id is None:
                    return False
                return await self._repo.is_liked_by_user(post.id, user_id)

            stats, is_liked = await concurrent_query(
                get_stats(),
                get_is_liked(),
            )

            return {
                "post": post,
                "author": post.author,
                "category": post.category,
                "tags": list(post.tags),
                "stats": stats,
                "is_liked": is_liked,
            }

        if use_cache:
            return await self._cache.get_or_set(
                cache_key,
                fetch,
                ttl=POST_DETAIL_TTL,
            )

        return await fetch()

    async def create_post(
        self,
        data: dict[str, Any],
        author_id: int,
    ) -> Post:
        """
        创建文章

        Args:
            data: 文章数据
            author_id: 作者 ID

        Returns:
            创建的文章实例
        """
        post_data = {**data, "author_id": author_id}

        if data.get("status") == "published" and not data.get("published_at"):
            post_data["published_at"] = datetime.now(UTC)

        post = await self._repo.create(post_data)

        await self._cache.invalidate_post_cache()

        logger.info(f"文章创建成功: id={post.id}, slug={post.slug}")

        return post

    async def update_post(
        self,
        post_id: int,
        data: dict[str, Any],
        user_id: int,
    ) -> Post | None:
        """
        更新文章

        Args:
            post_id: 文章 ID
            data: 更新数据
            user_id: 当前用户 ID

        Returns:
            更新后的文章实例，不存在返回 None
        """
        post = await self._repo.get_by_id(post_id)
        if post is None:
            return None

        if data.get("status") == "published" and post.status != "published":
            if not data.get("published_at"):
                data["published_at"] = datetime.now(UTC)

        updated_post = await self._repo.update(post, data)

        await self._cache.invalidate_post_cache(post_id)

        logger.info(f"文章更新成功: id={post_id}")

        return updated_post

    async def delete_post(
        self,
        post_id: int,
        user_id: int,
    ) -> bool:
        """
        删除文章

        Args:
            post_id: 文章 ID
            user_id: 当前用户 ID

        Returns:
            删除成功返回 True
        """
        post = await self._repo.get_by_id(post_id)
        if post is None:
            return False

        await self._repo.delete(post)

        await self._cache.invalidate_post_cache(post_id)

        logger.info(f"文章删除成功: id={post_id}")

        return True

    async def toggle_like(
        self,
        post_id: int,
        user_id: int,
    ) -> dict[str, Any]:
        """
        切换文章点赞状态

        Args:
            post_id: 文章 ID
            user_id: 用户 ID

        Returns:
            包含点赞状态和点赞数的字典
        """
        is_liked, success = await self._repo.toggle_like(post_id, user_id)

        if success:
            await self._cache.invalidate_post_cache(post_id)

        like_count = await self._repo.get_like_count(post_id)

        logger.info(f"文章点赞切换: post_id={post_id}, user_id={user_id}, is_liked={is_liked}")

        return {
            "is_liked": is_liked,
            "like_count": like_count,
            "success": success,
        }

    async def increment_views(
        self,
        post_id: int,
    ) -> bool:
        """
        增加文章浏览量

        Args:
            post_id: 文章 ID

        Returns:
            成功返回 True
        """
        return await self._repo.increment_views(post_id)

    async def get_posts_by_category(
        self,
        category_slug: str,
        page: int = 1,
        page_size: int = 20,
        use_cache: bool = True,
    ) -> dict[str, Any]:
        """
        获取指定分类的文章

        Args:
            category_slug: 分类 slug
            page: 页码
            page_size: 每页数量
            use_cache: 是否使用缓存

        Returns:
            分页结果字典
        """
        cache_key = self._cache.build_key_with_hash(
            "posts_by_category",
            category_slug,
            page=page,
            page_size=page_size,
        )

        async def fetch():
            skip = (page - 1) * page_size
            posts = await self._repo.get_posts_by_category_slug(
                category_slug,
                skip=skip,
                limit=page_size,
            )
            return {
                "items": posts,
                "page": page,
                "page_size": page_size,
            }

        if use_cache:
            return await self._cache.get_or_set(
                cache_key,
                fetch,
                ttl=POST_LIST_TTL,
            )

        return await fetch()

    async def get_posts_by_tag(
        self,
        tag_slug: str,
        page: int = 1,
        page_size: int = 20,
        use_cache: bool = True,
    ) -> dict[str, Any]:
        """
        获取指定标签的文章

        Args:
            tag_slug: 标签 slug
            page: 页码
            page_size: 每页数量
            use_cache: 是否使用缓存

        Returns:
            分页结果字典
        """
        cache_key = self._cache.build_key_with_hash(
            "posts_by_tag",
            tag_slug,
            page=page,
            page_size=page_size,
        )

        async def fetch():
            skip = (page - 1) * page_size
            posts = await self._repo.get_posts_by_tag_slug(
                tag_slug,
                skip=skip,
                limit=page_size,
            )
            return {
                "items": posts,
                "page": page,
                "page_size": page_size,
            }

        if use_cache:
            return await self._cache.get_or_set(
                cache_key,
                fetch,
                ttl=POST_LIST_TTL,
            )

        return await fetch()

    async def get_posts_by_author(
        self,
        author_id: int,
        page: int = 1,
        page_size: int = 20,
        include_unpublished: bool = False,
        use_cache: bool = True,
    ) -> dict[str, Any]:
        """
        获取指定作者的文章

        Args:
            author_id: 作者 ID
            page: 页码
            page_size: 每页数量
            include_unpublished: 是否包含未发布的文章
            use_cache: 是否使用缓存

        Returns:
            分页结果字典
        """
        cache_key = self._cache.build_key_with_hash(
            "posts_by_author",
            author_id,
            page=page,
            page_size=page_size,
            include_unpublished=include_unpublished,
        )

        async def fetch():
            skip = (page - 1) * page_size
            posts = await self._repo.get_posts_by_author(
                author_id,
                skip=skip,
                limit=page_size,
                include_unpublished=include_unpublished,
            )
            return {
                "items": posts,
                "page": page,
                "page_size": page_size,
            }

        if use_cache:
            return await self._cache.get_or_set(
                cache_key,
                fetch,
                ttl=POST_LIST_TTL,
            )

        return await fetch()

    async def get_pinned_posts(
        self,
        limit: int = 5,
        use_cache: bool = True,
    ) -> list[Post]:
        """
        获取置顶文章

        Args:
            limit: 最大数量
            use_cache: 是否使用缓存

        Returns:
            置顶文章列表
        """
        cache_key = self._cache.build_key("pinned_posts", limit)

        async def fetch():
            return await self._repo.get_pinned_posts(limit)

        if use_cache:
            return await self._cache.get_or_set(
                cache_key,
                fetch,
                ttl=POST_LIST_TTL,
            )

        return await fetch()

    async def get_popular_posts(
        self,
        limit: int = 10,
        use_cache: bool = True,
    ) -> list[Post]:
        """
        获取热门文章

        Args:
            limit: 最大数量
            use_cache: 是否使用缓存

        Returns:
            热门文章列表
        """
        cache_key = self._cache.build_key("popular_posts", limit)

        async def fetch():
            return await self._repo.get_popular_posts(limit)

        if use_cache:
            return await self._cache.get_or_set(
                cache_key,
                fetch,
                ttl=POST_LIST_TTL,
            )

        return await fetch()

    async def get_related_posts(
        self,
        post_id: int,
        limit: int = 5,
        use_cache: bool = True,
    ) -> list[Post]:
        """
        获取相关文章

        Args:
            post_id: 文章 ID
            limit: 最大数量
            use_cache: 是否使用缓存

        Returns:
            相关文章列表
        """
        cache_key = self._cache.build_key("related_posts", post_id, limit)

        async def fetch():
            return await self._repo.get_related_posts(post_id, limit)

        if use_cache:
            return await self._cache.get_or_set(
                cache_key,
                fetch,
                ttl=POST_LIST_TTL,
            )

        return await fetch()

    async def search_posts(
        self,
        keyword: str,
        page: int = 1,
        page_size: int = 20,
        status: str = "published",
    ) -> dict[str, Any]:
        """
        搜索文章

        Args:
            keyword: 搜索关键词
            page: 页码
            page_size: 每页数量
            status: 文章状态

        Returns:
            搜索结果字典
        """
        skip = (page - 1) * page_size
        posts = await self._repo.search_posts(
            keyword=keyword,
            skip=skip,
            limit=page_size,
            status=status,
        )

        return {
            "items": posts,
            "page": page,
            "page_size": page_size,
            "keyword": keyword,
        }

    async def get_post_stats(
        self,
        post_id: int,
        use_cache: bool = True,
    ) -> dict[str, int]:
        """
        获取文章统计数据

        Args:
            post_id: 文章 ID
            use_cache: 是否使用缓存

        Returns:
            统计数据字典
        """
        cache_key = self._cache.build_key("post_stats", post_id)

        async def fetch():
            return await self._repo.get_post_stats(post_id)

        if use_cache:
            return await self._cache.get_or_set(
                cache_key,
                fetch,
                ttl=POST_STATS_TTL,
            )

        return await fetch()


async def get_post_service(
    db: AsyncSession,
    cache: CacheService | None = None,
) -> PostService:
    """
    获取文章服务实例（依赖注入）

    Args:
        db: 数据库会话
        cache: 缓存服务实例

    Returns:
        PostService 实例
    """
    return PostService(db, cache)
