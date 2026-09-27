"""
文章仓储层

提供文章相关的数据库操作，包括：
- 文章 CRUD 操作
- 按 slug、分类、标签查询
- 并行获取文章详情数据
- 点赞和评论统计
"""

from datetime import datetime
from typing import Any

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload, selectinload

from backend.core.concurrency import concurrent_query
from backend.models.blog import Category, Comment, Post, Tag, post_likes
from backend.repositories.base import BaseRepository, PaginationResult


class PostRepository(BaseRepository[Post]):
    """
    文章仓储类

    提供文章相关的数据库操作方法。

    Attributes:
        session: 异步数据库会话

    Example:
        >>> async with get_db_context() as session:
        ...     repo = PostRepository(session)
        ...     post = await repo.get_by_slug("my-first-post")
    """

    def __init__(self, session: AsyncSession):
        """
        初始化文章仓储

        Args:
            session: 异步数据库会话
        """
        super().__init__(Post, session)

    async def get_by_slug(self, slug: str) -> Post | None:
        """
        根据 slug 获取文章

        Args:
            slug: 文章 URL 别名

        Returns:
            文章实例，不存在则返回 None
        """
        result = await self.session.execute(select(Post).where(Post.slug == slug))
        return result.scalar_one_or_none()

    async def get_by_slug_with_relations(self, slug: str) -> Post | None:
        """
        根据 slug 获取文章（包含关联数据）

        Args:
            slug: 文章 URL 别名

        Returns:
            文章实例（包含作者、分类、标签），不存在则返回 None
        """
        result = await self.session.execute(
            select(Post)
            .where(Post.slug == slug)
            .options(
                joinedload(Post.author),
                joinedload(Post.category),
                selectinload(Post.tags),
            )
        )
        return result.scalar_one_or_none()

    async def get_published_posts(
        self,
        skip: int = 0,
        limit: int = 20,
        order_by: str = "published_at",
        descending: bool = True,
    ) -> list[Post]:
        """
        获取已发布的文章列表

        Args:
            skip: 跳过的记录数
            limit: 返回的最大记录数
            order_by: 排序字段
            descending: 是否降序

        Returns:
            文章列表
        """
        # 排序白名单：只允许真实列名（防 getattr 命中方法/敏感列导致 500 或信息侧信道）
        _SORTABLE = {
            "id": Post.id,
            "created_at": Post.created_at,
            "updated_at": Post.updated_at,
            "published_at": Post.published_at,
            "views": Post.views,
            "title": Post.title,
            "slug": Post.slug,
        }
        order_column = _SORTABLE.get(order_by, Post.published_at)
        query = (
            select(Post)
            .where(Post.status == "published")
            .order_by(order_column.desc() if descending else order_column)
            .offset(skip)
            .limit(limit)
        )
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def get_posts_by_category(
        self,
        category_id: int,
        skip: int = 0,
        limit: int = 20,
    ) -> list[Post]:
        """
        获取指定分类的文章

        Args:
            category_id: 分类 ID
            skip: 跳过的记录数
            limit: 返回的最大记录数

        Returns:
            文章列表
        """
        query = (
            select(Post)
            .where(Post.category_id == category_id, Post.status == "published")
            .order_by(Post.published_at.desc())
            .offset(skip)
            .limit(limit)
        )
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def get_posts_by_category_slug(
        self,
        category_slug: str,
        skip: int = 0,
        limit: int = 20,
    ) -> list[Post]:
        """
        根据分类 slug 获取文章

        Args:
            category_slug: 分类 slug
            skip: 跳过的记录数
            limit: 返回的最大记录数

        Returns:
            文章列表
        """
        query = (
            select(Post)
            .join(Category)
            .where(Category.slug == category_slug, Post.status == "published")
            .order_by(Post.published_at.desc())
            .offset(skip)
            .limit(limit)
        )
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def get_posts_by_tag(
        self,
        tag_id: int,
        skip: int = 0,
        limit: int = 20,
    ) -> list[Post]:
        """
        获取指定标签的文章

        Args:
            tag_id: 标签 ID
            skip: 跳过的记录数
            limit: 返回的最大记录数

        Returns:
            文章列表
        """
        query = (
            select(Post)
            .join(Post.tags)
            .where(Tag.id == tag_id, Post.status == "published")
            .order_by(Post.published_at.desc())
            .offset(skip)
            .limit(limit)
        )
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def get_posts_by_tag_slug(
        self,
        tag_slug: str,
        skip: int = 0,
        limit: int = 20,
    ) -> list[Post]:
        """
        根据标签 slug 获取文章

        Args:
            tag_slug: 标签 slug
            skip: 跳过的记录数
            limit: 返回的最大记录数

        Returns:
            文章列表
        """
        query = (
            select(Post)
            .join(Post.tags)
            .where(Tag.slug == tag_slug, Post.status == "published")
            .order_by(Post.published_at.desc())
            .offset(skip)
            .limit(limit)
        )
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def get_posts_by_author(
        self,
        author_id: int,
        skip: int = 0,
        limit: int = 20,
        include_unpublished: bool = False,
    ) -> list[Post]:
        """
        获取指定作者的文章

        Args:
            author_id: 作者 ID
            skip: 跳过的记录数
            limit: 返回的最大记录数
            include_unpublished: 是否包含未发布的文章

        Returns:
            文章列表
        """
        query = select(Post).where(Post.author_id == author_id)
        if not include_unpublished:
            query = query.where(Post.status == "published")
        query = query.order_by(Post.created_at.desc()).offset(skip).limit(limit)
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def get_pinned_posts(self, limit: int = 5) -> list[Post]:
        """
        获取置顶文章

        Args:
            limit: 返回的最大记录数

        Returns:
            置顶文章列表
        """
        query = (
            select(Post)
            .where(Post.status == "published", Post.is_pinned.is_(True))
            .order_by(Post.published_at.desc())
            .limit(limit)
        )
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def get_post_detail(self, post_id: int) -> dict[str, Any]:
        """
        获取文章详情数据

        预加载 author/category/tags 关系；两条 count 顺序执行（AsyncSession 不能并发）。

        Args:
            post_id: 文章 ID

        Returns:
            包含文章详情的字典
        """
        result = await self.session.execute(
            select(Post)
            .where(Post.id == post_id)
            .options(
                selectinload(Post.author),
                selectinload(Post.category),
                selectinload(Post.tags),
            )
        )
        post = result.scalar_one_or_none()
        if post is None:
            return {}

        # 仅真实需要访问 DB 的 count 查询保留为协程
        async def get_comment_count():
            r = await self.session.execute(
                select(func.count())
                .select_from(Comment)
                .where(Comment.post_id == post_id, Comment.active.is_(True))
            )
            return r.scalar_one()

        async def get_like_count():
            r = await self.session.execute(
                select(func.count()).select_from(post_likes).where(post_likes.c.post_id == post_id)
            )
            return r.scalar_one()

        comment_count, like_count = await concurrent_query(
            get_comment_count(),
            get_like_count(),
        )

        return {
            "post": post,
            "author": post.author,
            "category": post.category,
            "tags": list(post.tags),
            "comment_count": comment_count,
            "like_count": like_count,
        }

    async def increment_views(self, post_id: int) -> bool:
        """
        增加文章浏览量

        原子 UPDATE ... SET views = views + 1：旧的读-改-写在并发访问下会互相覆盖丢计数。

        Args:
            post_id: 文章 ID

        Returns:
            成功返回 True
        """
        result = await self.session.execute(
            update(Post).where(Post.id == post_id).values(views=Post.views + 1)
        )
        return result.rowcount > 0

    async def toggle_like(self, post_id: int, user_id: int) -> tuple[bool, bool]:
        """
        切换文章点赞状态

        Args:
            post_id: 文章 ID
            user_id: 用户 ID

        Returns:
            (是否点赞, 操作是否成功) 元组
        """
        result = await self.session.execute(
            select(post_likes).where(
                post_likes.c.post_id == post_id, post_likes.c.user_id == user_id
            )
        )
        existing_like = result.first()

        if existing_like:
            await self.session.execute(
                post_likes.delete().where(
                    post_likes.c.post_id == post_id, post_likes.c.user_id == user_id
                )
            )
            await self.session.flush()
            return False, True
        else:
            await self.session.execute(post_likes.insert().values(post_id=post_id, user_id=user_id))
            await self.session.flush()
            return True, True

    async def is_liked_by_user(self, post_id: int, user_id: int) -> bool:
        """
        检查用户是否已点赞文章

        Args:
            post_id: 文章 ID
            user_id: 用户 ID

        Returns:
            已点赞返回 True
        """
        result = await self.session.execute(
            select(func.count())
            .select_from(post_likes)
            .where(post_likes.c.post_id == post_id, post_likes.c.user_id == user_id)
        )
        return result.scalar_one() > 0

    async def get_like_count(self, post_id: int) -> int:
        """
        获取文章点赞数

        Args:
            post_id: 文章 ID

        Returns:
            点赞数
        """
        result = await self.session.execute(
            select(func.count()).select_from(post_likes).where(post_likes.c.post_id == post_id)
        )
        return result.scalar_one()

    async def get_comment_count(self, post_id: int) -> int:
        """
        获取文章评论数

        Args:
            post_id: 文章 ID

        Returns:
            评论数
        """
        result = await self.session.execute(
            select(func.count())
            .select_from(Comment)
            .where(Comment.post_id == post_id, Comment.active.is_(True))
        )
        return result.scalar_one()

    async def get_post_stats(self, post_id: int) -> dict[str, int]:
        """
        获取文章统计数据

        Args:
            post_id: 文章 ID

        Returns:
            包含浏览量、点赞数、评论数的字典
        """
        post = await self.get_by_id(post_id)
        if post is None:
            return {"views": 0, "likes": 0, "comments": 0}

        likes, comments = await concurrent_query(
            self.get_like_count(post_id),
            self.get_comment_count(post_id),
        )

        return {
            "views": post.views,
            "likes": likes,
            "comments": comments,
        }

    async def search_posts(
        self,
        keyword: str,
        skip: int = 0,
        limit: int = 20,
        status: str = "published",
    ) -> list[Post]:
        """
        搜索文章

        在标题、内容、摘要中搜索关键词。

        Args:
            keyword: 搜索关键词
            skip: 跳过的记录数
            limit: 返回的最大记录数
            status: 文章状态

        Returns:
            文章列表
        """
        from sqlalchemy import or_

        search_pattern = f"%{keyword}%"

        query = (
            select(Post)
            .where(
                Post.status == status,
                or_(
                    Post.title["zh"].astext.ilike(search_pattern),
                    Post.title["en"].astext.ilike(search_pattern),
                    Post.content["zh"].astext.ilike(search_pattern),
                    Post.content["en"].astext.ilike(search_pattern),
                    Post.excerpt["zh"].astext.ilike(search_pattern),
                    Post.excerpt["en"].astext.ilike(search_pattern),
                ),
            )
            .order_by(Post.published_at.desc())
            .offset(skip)
            .limit(limit)
        )

        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def count_posts_by_status(self, status: str) -> int:
        """
        统计指定状态的文章数

        Args:
            status: 文章状态

        Returns:
            文章数
        """
        result = await self.session.execute(
            select(func.count()).select_from(Post).where(Post.status == status)
        )
        return result.scalar_one()

    async def count_posts_by_category(self, category_id: int) -> int:
        """
        统计指定分类的文章数

        Args:
            category_id: 分类 ID

        Returns:
            文章数
        """
        result = await self.session.execute(
            select(func.count())
            .select_from(Post)
            .where(Post.category_id == category_id, Post.status == "published")
        )
        return result.scalar_one()

    async def count_posts_by_tag(self, tag_id: int) -> int:
        """
        统计指定标签的文章数

        Args:
            tag_id: 标签 ID

        Returns:
            文章数
        """
        result = await self.session.execute(
            select(func.count())
            .select_from(Post)
            .join(Post.tags)
            .where(Tag.id == tag_id, Post.status == "published")
        )
        return result.scalar_one()

    async def get_recent_posts(self, days: int = 7, limit: int = 10) -> list[Post]:
        """
        获取最近发布的文章

        Args:
            days: 最近天数
            limit: 返回的最大记录数

        Returns:
            文章列表
        """
        from datetime import UTC, timedelta

        cutoff_date = datetime.now(UTC) - timedelta(days=days)

        query = (
            select(Post)
            .where(Post.status == "published", Post.published_at >= cutoff_date)
            .order_by(Post.published_at.desc())
            .limit(limit)
        )
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def get_popular_posts(self, limit: int = 10) -> list[Post]:
        """
        获取热门文章（按浏览量排序）

        Args:
            limit: 返回的最大记录数

        Returns:
            热门文章列表
        """
        query = (
            select(Post).where(Post.status == "published").order_by(Post.views.desc()).limit(limit)
        )
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def get_related_posts(
        self,
        post_id: int,
        limit: int = 5,
    ) -> list[Post]:
        """
        获取相关文章

        基于相同分类和标签推荐相关文章。

        Args:
            post_id: 当前文章 ID
            limit: 返回的最大记录数

        Returns:
            相关文章列表
        """
        post = await self.get_by_id(post_id)
        if post is None:
            return []

        query = (
            select(Post)
            .where(
                Post.id != post_id,
                Post.status == "published",
            )
            .order_by(Post.views.desc())
            .limit(limit)
        )

        if post.category_id:
            query = query.where(Post.category_id == post.category_id)

        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def paginate_posts(
        self,
        page: int = 1,
        page_size: int = 20,
        status: str | None = None,
        category_id: int | None = None,
        tag_id: int | None = None,
        author_id: int | None = None,
        is_pinned: bool | None = None,
        order_by: str = "published_at",
        descending: bool = True,
    ) -> PaginationResult[Post]:
        """
        分页查询文章

        支持多条件过滤和排序。

        Args:
            page: 页码
            page_size: 每页记录数
            status: 文章状态
            category_id: 分类 ID
            tag_id: 标签 ID
            author_id: 作者 ID
            is_pinned: 是否置顶
            order_by: 排序字段
            descending: 是否降序

        Returns:
            分页结果
        """
        query = select(Post)

        if status is not None:
            query = query.where(Post.status == status)
        if category_id is not None:
            query = query.where(Post.category_id == category_id)
        if author_id is not None:
            query = query.where(Post.author_id == author_id)
        if is_pinned is not None:
            query = query.where(Post.is_pinned == is_pinned)
        if tag_id is not None:
            query = query.join(Post.tags).where(Tag.id == tag_id)

        count_query = select(func.count()).select_from(query.subquery())
        total_result = await self.session.execute(count_query)
        total = total_result.scalar_one()

        # 排序白名单：只允许真实列名（防 getattr 命中方法/敏感列导致 500 或信息侧信道）
        _SORTABLE = {
            "id": Post.id,
            "created_at": Post.created_at,
            "updated_at": Post.updated_at,
            "published_at": Post.published_at,
            "views": Post.views,
            "title": Post.title,
            "slug": Post.slug,
        }
        order_column = _SORTABLE.get(order_by, Post.published_at)
        query = query.order_by(order_column.desc() if descending else order_column)

        skip = (page - 1) * page_size
        query = query.offset(skip).limit(page_size)

        result = await self.session.execute(query)
        items = list(result.scalars().all())

        return PaginationResult(
            items=items,
            total=total,
            page=page,
            page_size=page_size,
        )

    async def get_archive_data(
        self,
        lang: str = "zh",
        limit_per_month: int = 50,
    ) -> list[dict]:
        """
        获取归档数据

        按年月分组返回已发布文章的归档数据。

        Args:
            lang: 语言代码
            limit_per_month: 每月最多返回的文章数

        Returns:
            归档数据列表，按年月分组
        """

        # 只投影归档真正要展示的列：原先 `select(Post)` 会把每篇文章的 JSON `content`
        # 正文整列读进内存并实例化 ORM 对象，文章数上千时归档页的内存与耗时都失控。
        query = (
            select(
                Post.id,
                Post.title,
                Post.slug,
                Post.created_at,
                Post.published_at,
                Post.views,
                Category.id,
                Category.name,
                Category.color,
            )
            .outerjoin(Category, Post.category_id == Category.id)
            .where(Post.status == "published")
            .order_by(Post.published_at.desc())
        )

        result = await self.session.execute(query)
        rows = result.all()

        # 按年月分组
        archive_map: dict[tuple[int, int], list[dict]] = {}

        for (
            post_id,
            post_title,
            slug,
            created_at,
            published_at,
            views,
            category_id,
            category_name_i18n,
            category_color,
        ) in rows:
            date_field = published_at or created_at
            if not date_field:
                continue

            year = date_field.year
            month = date_field.month
            key = (year, month)

            if key not in archive_map:
                archive_map[key] = []

            if len(archive_map[key]) < limit_per_month:
                # 获取标题
                title = post_title.get(lang, post_title.get("zh", "")) if post_title else ""

                # 获取分类信息
                category_data = None
                if category_id is not None:
                    category_name = (
                        category_name_i18n.get(lang, category_name_i18n.get("zh", ""))
                        if category_name_i18n
                        else ""
                    )
                    category_data = {
                        "id": category_id,
                        "name": category_name,
                        "color": category_color,
                    }

                archive_map[key].append(
                    {
                        "id": post_id,
                        "title": title,
                        "slug": slug,
                        "created_at": created_at.isoformat() if created_at else None,
                # 分组按 published_at（回退 created_at），显示必须用同一个字段，
                # 否则「2026-08」标题下会列出创建日在 7 月的文章。
                "published_at": (published_at or created_at).isoformat(),
                        "category": category_data,
                        "views": views,
                    }
                )

        # 转换为列表格式
        archive_list = []
        for (year, month), posts_list in sorted(
            archive_map.items(), key=lambda x: (x[0][0], x[0][1]), reverse=True
        ):
            archive_list.append(
                {
                    "year": year,
                    "month": month,
                    "count": len(posts_list),
                    "posts": posts_list,
                }
            )

        return archive_list

    async def get_archive_stats(self) -> dict:
        """
        获取归档统计信息

        Returns:
            包含总文章数、总年份数等统计信息
        """
        from sqlalchemy import extract

        # 使用coalesce处理published_at为null的情况，fallback到created_at
        date_expr = func.coalesce(Post.published_at, Post.created_at)
        year_expr = extract("year", date_expr)

        # 统计总数
        total_result = await self.session.execute(
            select(func.count()).select_from(Post).where(Post.status == "published")
        )
        total_posts = total_result.scalar_one()

        # 一次 GROUP BY 拿到"每年文章数"：原先先 DISTINCT 年份、再对每个年份单发一条
        # COUNT，跨年归档统计的查询数随年份数线性增长（归档页每次命中都要跑一遍）。
        # GROUP BY 用与 SELECT 完全相同的表达式，PG 才不会判"裸列分组"。
        stats_result = await self.session.execute(
            select(year_expr, func.count()).where(Post.status == "published").group_by(year_expr)
        )
        year_stats = {int(y): cnt for y, cnt in stats_result.fetchall() if y is not None}
        years = sorted(year_stats, reverse=True)

        return {
            "total_posts": total_posts,
            "total_years": len(years),
            "years": years,
            "year_stats": year_stats,
        }
