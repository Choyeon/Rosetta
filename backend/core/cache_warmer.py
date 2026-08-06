"""
缓存预热模块

在应用启动时预热热点数据到缓存，减少首次访问延迟。
支持定时刷新和手动触发预热。

功能特性：
- 启动时预热热点数据
- 定时刷新缓存
- 手动触发预热
- 预热任务状态追踪
"""

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime

try:
    from enum import StrEnum
except ImportError:
    from enum import Enum

    class StrEnum(str, Enum):
        pass


from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import selectinload

from backend.core.cache import CACHE_TTL, cache, make_cache_key
from backend.core.config import settings
from backend.core.database import async_session_maker
from backend.models.blog import Category, Post, Tag, post_likes, post_tags
from backend.models.core import FriendLink, Navigation, SiteConfig

logger = logging.getLogger(__name__)


class WarmupTaskStatus(StrEnum):
    """预热任务状态"""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class WarmupTaskResult:
    """预热任务结果"""

    task_name: str
    status: WarmupTaskStatus
    start_time: datetime | None = None
    end_time: datetime | None = None
    duration_ms: float = 0.0
    items_cached: int = 0
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """转换为字典"""
        return {
            "task_name": self.task_name,
            "status": self.status.value,
            "start_time": self.start_time.isoformat() if self.start_time else None,
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "duration_ms": self.duration_ms,
            "items_cached": self.items_cached,
            "error": self.error,
        }


@dataclass
class WarmupState:
    """预热状态"""

    is_running: bool = False
    last_warmup: datetime | None = None
    last_error: str | None = None
    task_results: list[WarmupTaskResult] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """转换为字典"""
        return {
            "is_running": self.is_running,
            "last_warmup": self.last_warmup.isoformat() if self.last_warmup else None,
            "last_error": self.last_error,
            "task_results": [r.to_dict() for r in self.task_results],
        }


class CacheWarmer:
    """
    缓存预热器

    在应用启动时预热热点数据到缓存，支持：
    - 站点配置
    - 导航列表
    - 分类列表
    - 标签列表
    - 友链列表
    - 热门文章
    """

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._initialized = True
        self._state = WarmupState()
        self._lock = asyncio.Lock()

    @property
    def state(self) -> WarmupState:
        """获取预热状态"""
        return self._state

    async def warmup_all(self) -> dict[str, Any]:
        """
        预热所有缓存

        Returns:
            预热结果摘要
        """
        async with self._lock:
            if self._state.is_running:
                logger.warning("缓存预热正在进行中，跳过本次预热")
                return self._state.to_dict()

            self._state.is_running = True
            self._state.task_results = []
            self._state.last_error = None

            logger.info("开始缓存预热...")

            tasks = [
                ("site_config", self._warmup_site_config),
                ("navigations", self._warmup_navigations),
                ("categories", self._warmup_categories),
                ("tags", self._warmup_tags),
                ("friend_links", self._warmup_friend_links),
                ("hot_posts", self._warmup_hot_posts),
            ]

            results = await asyncio.gather(
                *[self._run_warmup_task(name, func) for name, func in tasks],
                return_exceptions=True,
            )

            for result in results:
                if isinstance(result, WarmupTaskResult):
                    self._state.task_results.append(result)
                elif isinstance(result, Exception):
                    logger.error(f"预热任务异常: {result}")

            self._state.is_running = False
            self._state.last_warmup = datetime.now()

            total_cached = sum(r.items_cached for r in self._state.task_results)
            failed_tasks = [
                r for r in self._state.task_results if r.status == WarmupTaskStatus.FAILED
            ]

            if failed_tasks:
                self._state.last_error = f"{len(failed_tasks)} 个预热任务失败"

            logger.info(f"缓存预热完成: {total_cached} 项已缓存, {len(failed_tasks)} 个任务失败")

            return self._state.to_dict()

    async def _run_warmup_task(
        self,
        task_name: str,
        task_func: Any,
    ) -> WarmupTaskResult:
        """
        执行单个预热任务

        Args:
            task_name: 任务名称
            task_func: 任务函数

        Returns:
            预热任务结果
        """
        result = WarmupTaskResult(task_name=task_name, status=WarmupTaskStatus.RUNNING)
        result.start_time = datetime.now()

        try:
            items_cached = await task_func()
            result.status = WarmupTaskStatus.COMPLETED
            result.items_cached = items_cached
            logger.info(f"预热任务 [{task_name}] 完成: {items_cached} 项已缓存")
        except Exception as e:
            result.status = WarmupTaskStatus.FAILED
            result.error = str(e)
            logger.error(f"预热任务 [{task_name}] 失败: {e}")
        finally:
            result.end_time = datetime.now()
            result.duration_ms = (result.end_time - result.start_time).total_seconds() * 1000

        return result

    async def _warmup_site_config(self) -> int:
        """预热站点配置"""
        async with async_session_maker() as db:
            result = await db.execute(select(SiteConfig))
            configs = {c.key: c.value for c in result.scalars().all()}

            cache_key = make_cache_key("site_config")
            config_data = {
                "site_name": configs.get("SITE_NAME", "Rosetta Blog"),
                "site_description": configs.get(
                    "SITE_DESCRIPTION",
                    "Rosetta开源博客系统",
                ),
                "site_keywords": configs.get(
                    "SITE_KEYWORDS", "Rosetta, FastAPI, Astro, Svelte, Blog"
                ),
                "site_author": configs.get("SITE_AUTHOR", "Rosetta Team"),
                "site_email": configs.get("SITE_EMAIL", "contact@rosetta.dev"),
                "site_logo": configs.get("SITE_LOGO"),
                "site_favicon": configs.get("SITE_FAVICON"),
                "footer_text": configs.get("FOOTER_TEXT", "Powered by Rosetta"),
                "footer_slogan": configs.get(
                    "FOOTER_SLOGAN", "Share knowledge, inspire creativity"
                ),
                "github_url": configs.get("GITHUB_URL"),
                "x_url": configs.get("X_URL"),
                "bilibili_url": configs.get("BILIBILI_URL"),
                "contact_email": configs.get("CONTACT_EMAIL"),
                "enable_comments": configs.get("ENABLE_COMMENTS", "true").lower() == "true",
                "enable_registration": configs.get("ENABLE_REGISTRATION", "true").lower() == "true",
                "enable_rss_feed": configs.get("ENABLE_RSS_FEED", "true").lower() == "true",
                "pagination_page_size": int(configs.get("PAGINATION_PAGE_SIZE", "12")),
                "code_theme": configs.get("CODE_THEME", "github"),
                "maintenance_mode": configs.get("MAINTENANCE_MODE", "false").lower() == "true",
                "maintenance_message": configs.get(
                    "MAINTENANCE_MESSAGE", "Site is under maintenance"
                ),
                "default_post_cover": configs.get("DEFAULT_POST_COVER"),
            }

            await cache.set(cache_key, config_data, CACHE_TTL["site_config"])
            return 1

    async def _warmup_navigations(self) -> int:
        """预热导航列表"""
        async with async_session_maker() as db:
            locations = ["header", "footer", "sidebar", None]
            total_cached = 0

            for location in locations:
                cache_key = make_cache_key("navigations", location or "all")

                query = (
                    select(Navigation)
                    .where(Navigation.is_active.is_(True))
                    .order_by(Navigation.order)
                )

                if location:
                    query = query.where(Navigation.location == location)

                result = await db.execute(query)
                navigations = result.scalars().all()

                nav_data = [
                    {
                        "id": n.id,
                        "title": n.title,
                        "url": n.url,
                        "location": n.location,
                        "order": n.order,
                        "is_active": n.is_active,
                        "target_blank": n.target_blank,
                        "created_at": n.created_at.isoformat() if n.created_at else None,
                    }
                    for n in navigations
                ]

                await cache.set(cache_key, nav_data, CACHE_TTL["navigations"])
                total_cached += 1

            return total_cached

    async def _warmup_categories(self) -> int:
        """预热分类列表"""
        async with async_session_maker() as db:
            languages = ["zh", "en", "ja", "zh_Hant"]
            total_cached = 0

            result = await db.execute(
                select(
                    Category,
                    func.count(Post.id).filter(Post.status == "published").label("post_count"),
                )
                .outerjoin(Post, Category.id == Post.category_id)
                .group_by(Category.id)
                .order_by(Category.created_at)
            )
            rows = result.all()

            for lang in languages:
                cache_key = make_cache_key("categories", lang)

                def get_i18n_value(data: dict | None, language: str) -> str:
                    if not data:
                        return ""
                    if isinstance(data, str):
                        return data
                    return data.get(language, data.get("zh", ""))

                categories_data = [
                    {
                        "id": row.Category.id,
                        "name": get_i18n_value(row.Category.name, lang),
                        "slug": row.Category.slug,
                        "description": get_i18n_value(row.Category.description, lang),
                        "icon": row.Category.icon,
                        "color": row.Category.color,
                        "cover_image": row.Category.cover_image,
                        "created_at": row.Category.created_at.isoformat(),
                        "post_count": row.post_count or 0,
                    }
                    for row in rows
                ]

                await cache.set(cache_key, categories_data, CACHE_TTL["categories"])
                total_cached += 1

            return total_cached

    async def _warmup_tags(self) -> int:
        """预热标签列表"""
        async with async_session_maker() as db:
            languages = ["zh", "en", "ja", "zh_Hant"]
            total_cached = 0

            result = await db.execute(
                select(
                    Tag,
                    func.count(post_tags.c.post_id).label("post_count"),
                )
                .outerjoin(post_tags, Tag.id == post_tags.c.tag_id)
                .where(Tag.is_active.is_(True))
                .group_by(Tag.id)
                .order_by(Tag.created_at)
            )
            rows = result.all()

            for lang in languages:
                cache_key = make_cache_key("tags", lang)

                def get_i18n_value(data: dict | None, language: str) -> str:
                    if not data:
                        return ""
                    if isinstance(data, str):
                        return data
                    return data.get(language, data.get("zh", ""))

                tags_data = [
                    {
                        "id": row.Tag.id,
                        "name": get_i18n_value(row.Tag.name, lang),
                        "slug": row.Tag.slug,
                        "color": row.Tag.color,
                        "icon": row.Tag.icon,
                        "is_active": row.Tag.is_active,
                        "created_at": row.Tag.created_at.isoformat(),
                        "post_count": row.post_count or 0,
                    }
                    for row in rows
                ]

                await cache.set(cache_key, tags_data, CACHE_TTL["tags"])
                total_cached += 1

            return total_cached

    async def _warmup_friend_links(self) -> int:
        """预热友链列表"""
        async with async_session_maker() as db:
            total_cached = 0

            for include_inactive in [False, True]:
                cache_key = make_cache_key("friend_links", "all" if include_inactive else "active")

                query = select(FriendLink).order_by(FriendLink.order)
                if not include_inactive:
                    query = query.where(FriendLink.is_active.is_(True))

                result = await db.execute(query)
                links = result.scalars().all()

                links_data = [
                    {
                        "id": f.id,
                        "name": f.name,
                        "url": f.url,
                        "description": f.description,
                        "logo": f.logo,
                        "order": f.order,
                        "is_active": f.is_active,
                        "target_blank": f.target_blank,
                        "created_at": f.created_at.isoformat() if f.created_at else None,
                    }
                    for f in links
                ]

                await cache.set(cache_key, links_data, CACHE_TTL["friend_links"])
                total_cached += 1

            return total_cached

    async def _warmup_hot_posts(self) -> int:
        """预热热门文章列表"""
        async with async_session_maker() as db:
            languages = ["zh", "en", "ja", "zh_Hant"]
            total_cached = 0

            result = await db.execute(
                select(
                    Post,
                    func.coalesce(
                        select(func.count())
                        .select_from(post_likes)
                        .where(post_likes.c.post_id == Post.id)
                        .scalar_subquery(),
                        0,
                    ).label("likes_count"),
                )
                .options(
                    selectinload(Post.author),
                    selectinload(Post.category),
                    selectinload(Post.tags),
                )
                .where(Post.status == "published")
                .order_by(Post.views.desc())
                .limit(10)
            )
            posts = result.unique().all()

            for lang in languages:
                cache_key = make_cache_key("hot_posts", lang)

                def get_i18n_value(data: dict | None, language: str) -> str:
                    if not data:
                        return ""
                    if isinstance(data, str):
                        return data
                    return data.get(language, data.get("zh", ""))

                posts_data = []
                for row in posts:
                    post = row.Post
                    posts_data.append(
                        {
                            "id": post.id,
                            "title": get_i18n_value(post.title, lang),
                            "slug": post.slug,
                            "cover_image": post.cover_image,
                            "views": post.views,
                            "likes_count": row.likes_count or 0,
                            "created_at": post.created_at.isoformat(),
                            "published_at": post.published_at.isoformat()
                            if post.published_at
                            else None,
                        }
                    )

                await cache.set(cache_key, posts_data, CACHE_TTL["post_list"])
                total_cached += 1

            return total_cached

    async def warmup_task(self, task_name: str) -> WarmupTaskResult:
        """
        执行单个预热任务

        Args:
            task_name: 任务名称

        Returns:
            预热任务结果
        """
        task_map = {
            "site_config": self._warmup_site_config,
            "navigations": self._warmup_navigations,
            "categories": self._warmup_categories,
            "tags": self._warmup_tags,
            "friend_links": self._warmup_friend_links,
            "hot_posts": self._warmup_hot_posts,
        }

        if task_name not in task_map:
            result = WarmupTaskResult(task_name=task_name, status=WarmupTaskStatus.FAILED)
            result.error = f"未知的预热任务: {task_name}"
            return result

        return await self._run_warmup_task(task_name, task_map[task_name])

    def get_status(self) -> dict[str, Any]:
        """
        获取预热状态

        Returns:
            预热状态信息
        """
        return self._state.to_dict()


cache_warmer = CacheWarmer()


async def warmup_cache() -> dict[str, Any]:
    """
    启动时调用的预热函数

    并行预热多个缓存项，错误处理和日志记录。

    Returns:
        预热结果摘要
    """
    if not settings.redis_enabled:
        logger.info("未启用 Redis，跳过缓存预热")
        return {"skipped": True, "reason": "Redis not enabled"}

    try:
        result = await cache_warmer.warmup_all()
        return result
    except Exception as e:
        logger.error(f"缓存预热失败: {e}")
        return {"error": str(e)}


class ScheduledCacheRefresher:
    """
    定时缓存刷新器

    在后台定时刷新缓存，保持数据新鲜度。
    """

    def __init__(
        self,
        refresh_interval: int = 3600,
        enabled: bool = True,
    ):
        """
        初始化定时刷新器

        Args:
            refresh_interval: 刷新间隔（秒），默认 1 小时
            enabled: 是否启用定时刷新
        """
        self.refresh_interval = refresh_interval
        self.enabled = enabled
        self._task: asyncio.Task | None = None
        self._running = False
        self._stop_event = asyncio.Event()

    async def start(self) -> None:
        """启动定时刷新任务"""
        if not self.enabled:
            logger.info("定时缓存刷新已禁用")
            return

        if self._running:
            logger.warning("定时刷新任务已在运行")
            return

        self._running = True
        self._stop_event.clear()
        self._task = asyncio.create_task(self._refresh_loop())
        logger.info(f"定时缓存刷新已启动，间隔: {self.refresh_interval} 秒")

    async def stop(self) -> None:
        """停止定时刷新任务"""
        if not self._running:
            return

        self._stop_event.set()
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None

        self._running = False
        logger.info("定时缓存刷新已停止")

    async def _refresh_loop(self) -> None:
        """刷新循环"""
        while self._running and not self._stop_event.is_set():
            try:
                await asyncio.sleep(self.refresh_interval)

                if self._stop_event.is_set():
                    break

                logger.info("开始定时缓存刷新...")
                await cache_warmer.warmup_all()
                logger.info("定时缓存刷新完成")

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"定时缓存刷新失败: {e}")
                await asyncio.sleep(60)

    @property
    def is_running(self) -> bool:
        """是否正在运行"""
        return self._running


scheduled_cache_refresher = ScheduledCacheRefresher(
    refresh_interval=getattr(settings, "cache_refresh_interval", 3600),
    enabled=settings.redis_enabled,
)
