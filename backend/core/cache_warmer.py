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

from backend.core.cache import (
    CACHE_KEY_CATEGORIES,
    CACHE_KEY_TAGS,
    CACHE_TTL,
    cache,
    make_cache_key,
)
from backend.core.config import settings
from backend.core.database import async_session_maker
from backend.models.blog import Category, Post, Tag, post_tags
from backend.models.core import FriendLink, Navigation
from backend.schemas import (
    CategoryResponse,
    FriendLinkResponse,
    NavigationResponse,
    TagResponse,
)

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

    def _warmup_tasks(self) -> list[tuple[str, Any]]:
        """预热任务清单——全量预热与单任务触发共用同一来源。

        此前两处各自维护一份，删任务要记得改两个地方，历史上就漏过。
        """
        return [
            ("site_config", self._warmup_site_config),
            ("navigations", self._warmup_navigations),
            ("categories", self._warmup_categories),
            ("tags", self._warmup_tags),
            ("friend_links", self._warmup_friend_links),
        ]

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

            tasks = self._warmup_tasks()

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
        """预热站点配置：委托 /api/config 端点函数本体——它是配置口径的唯一权威
        （扁平键 → 分组 JSON 覆写 → env 兜底），返回前自行写入 site_config 缓存。
        此前这里复刻了一套只认大写扁平键的手工拼装：既没有分组覆写，也读不到
        小写键行，冷启动预热反而把 "Rosetta Blog" 等默认值毒进缓存——
        此后缓存命中直接返回旧值，改站点名要等 TTL 到期或任意保存才可见。"""
        from backend.api.core import get_site_config

        async with async_session_maker() as db:
            await get_site_config(db)
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

                # 载荷必须走 NavigationResponse：读侧命中缓存是原样透传（不再过模型），
                # 此前手写 dict 漏了 icon/parent_id/updated_at，冷启动预热后
                # 菜单图标与父子关系凭空消失，要等任意一次失效才恢复。
                nav_data = [
                    NavigationResponse.model_validate(n).model_dump(mode="json")
                    for n in navigations
                ]

                await cache.set(cache_key, nav_data, CACHE_TTL["navigations"])
                total_cached += 1

            return total_cached

    async def _warmup_categories(self) -> int:
        """预热分类列表

        键与载荷形态必须和 ``GET /blog/categories`` 读侧完全一致（单键 ``raw-i18n``、
        值为 ``CategoryResponse`` 列表的 JSON 形态）。这里刻意复用同一个响应模型，
        避免"预热门面与读侧字段各自演化"——形状不一致时命中缓存反而会交出坏数据。
        """
        async with async_session_maker() as db:
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

            items = [
                CategoryResponse(
                    id=row.Category.id,
                    name=row.Category.name or {"zh": "", "en": "", "ja": "", "zh_Hant": ""},
                    slug=row.Category.slug,
                    description=row.Category.description or None,
                    icon=row.Category.icon,
                    color=row.Category.color,
                    cover_image=row.Category.cover_image,
                    created_at=row.Category.created_at,
                    post_count=row.post_count or 0,
                )
                for row in rows
            ]

            await cache.set(
                CACHE_KEY_CATEGORIES,
                [item.model_dump(mode="json") for item in items],
                CACHE_TTL["categories"],
            )
            return 1

    async def _warmup_tags(self) -> int:
        """预热标签列表（键/形态与 ``GET /blog/tags`` 读侧一致）"""
        async with async_session_maker() as db:
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

            items = [
                TagResponse(
                    id=row.Tag.id,
                    name=row.Tag.name or {"zh": "", "en": "", "ja": "", "zh_Hant": ""},
                    slug=row.Tag.slug,
                    color=row.Tag.color,
                    icon=row.Tag.icon,
                    is_active=row.Tag.is_active,
                    created_at=row.Tag.created_at,
                    post_count=row.post_count or 0,
                )
                for row in rows
            ]

            await cache.set(
                CACHE_KEY_TAGS,
                [item.model_dump(mode="json") for item in items],
                CACHE_TTL["tags"],
            )
            return 1

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

                # 同上：读侧透传缓存，载荷形态必须与 FriendLinkResponse 一致
                # （此前手写 dict 漏了必填的 status，友链审核状态在预热载荷里丢失）
                links_data = [
                    FriendLinkResponse.model_validate(f).model_dump(mode="json") for f in links
                ]

                await cache.set(cache_key, links_data, CACHE_TTL["friend_links"])
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
        task_map = dict(self._warmup_tasks())

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

    注意：这里**不看** ``redis_enabled``。内存缓存后端同样是有意义的响应缓存，
    而且进程一重启就全冷，单机部署反而更需要预热；把它当成 Redis 专属功能，
    等于让默认部署形态永远冷启动。
    """
    if not settings.cache_warmup_enabled:
        logger.info("缓存预热已由配置关闭")
        return {"skipped": True, "reason": "cache_warmup_enabled=False"}

    try:
        result = await cache_warmer.warmup_all()
        return result or {}
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
        refresh_interval: int | None = None,
        enabled: bool | None = None,
    ):
        """
        初始化定时刷新器

        Args:
            refresh_interval: 刷新间隔（秒），None 则跟随 ``settings.cache_refresh_interval``
            enabled: 是否启用定时刷新，None 则跟随 ``settings.cache_warmup_enabled``
        """
        self._refresh_interval = refresh_interval
        self._enabled = enabled
        self._task: asyncio.Task | None = None
        self._running = False
        self._stop_event = asyncio.Event()

    @property
    def refresh_interval(self) -> int:
        """间隔每次取用都重读配置，避免 import 期定值后改 settings 不生效"""
        return self._refresh_interval or settings.cache_refresh_interval

    @property
    def enabled(self) -> bool:
        return settings.cache_warmup_enabled if self._enabled is None else self._enabled

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


scheduled_cache_refresher = ScheduledCacheRefresher()
