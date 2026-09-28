"""
监控和性能统计 API

提供系统监控、性能指标、访问统计等功能。
"""

import asyncio
import logging
import math
import time
from datetime import datetime
from typing import Any

from fastapi import APIRouter, Query, Request
from pydantic import BaseModel, Field
from sqlalchemy import desc, func, select

from backend.core.auth import DB, CurrentStaff
from backend.core.cache import cache, make_cache_key
from backend.core.config import settings
from backend.core.database import engine
from backend.core.setup_system import psutil_errors
from backend.utils.compat import UTC, timedelta

logger = logging.getLogger(__name__)

router = APIRouter(tags=["监控"])

# 分位数按"窗口内最近 N 条带耗时的请求"计算：visit_logs 是纯追加表（下方已有 64.5 万行的实测，
# 7 天窗口约 24 万行），全量拉进内存再排序既吃内存又在事件循环上跑长任务。
_PERF_SAMPLE_LIMIT = 50_000


def _percentile(values: list[float], percentile: float) -> float:
    """线性插值分位数（与 numpy 默认 ``interpolation='linear'`` 同口径）。

    刻意不引 numpy：它不在 ``pyproject.toml`` 依赖里，而旧实现是函数内 ``import numpy``，
    于是**只要窗口里有数据就 ModuleNotFoundError → 500**（空窗口走提前返回才显得正常）。
    """
    if not values:
        return 0.0
    ordered = sorted(values)
    position = (len(ordered) - 1) * percentile / 100
    lower = math.floor(position)
    upper = math.ceil(position)
    if lower == upper:
        return float(ordered[lower])
    return ordered[lower] + (ordered[upper] - ordered[lower]) * (position - lower)


# `visit_logs` 是纯追加表（开发库实测 64.5 万行），无 `WHERE` 的 `COUNT(*)` 走不到任何索引，
# 每次仪表盘轮询都要扫全表。两个只读端点都用它展示"累计访问"，60s 陈旧无关紧要，
# 因此共用这一个短 TTL 缓存键；带 `created_at` 区间的今日/本周计数保持实时。
_VISIT_TOTAL_KEY = make_cache_key("monitoring", "visit_total")
_VISIT_TOTAL_TTL = 60

# 服务启动时间
_start_time = time.time()

# 性能指标存储
_metrics: dict[str, list[float]] = {
    "request_latency": [],
    "db_query_time": [],
    "cache_hit_rate": [],
}

_metrics_timestamps: dict[str, list[float]] = {
    "request_latency": [],
    "db_query_time": [],
    "cache_hit_rate": [],
}


class SystemStats(BaseModel):
    """系统统计"""

    database: dict[str, Any]
    cache: dict[str, Any]
    requests: dict[str, Any]
    memory: dict[str, Any]


class PerformanceMetrics(BaseModel):
    """性能指标"""

    avg_latency: float
    p50_latency: float
    p95_latency: float
    p99_latency: float
    requests_per_minute: float
    error_rate: float


class HealthComponentOut(BaseModel):
    """健康检查里单个组件的探测结果。"""

    status: str = Field(..., description="组件状态：healthy / degraded / unhealthy")
    latency_ms: int | None = Field(
        default=None, description="数据库探测延迟（毫秒）；其余组件不返回"
    )
    error: str | None = Field(default=None, description="探测异常信息；正常时为 null")


class HealthCheckResponse(BaseModel):
    """GET /health 的响应体（匿名可访问，无鉴权）。"""

    status: str = Field(..., description="整体状态：全部组件 healthy 才为 healthy，否则 degraded")
    timestamp: str = Field(..., description="服务端探测完成时间（ISO 8601，UTC）")
    checks: dict[str, HealthComponentOut] = Field(
        ..., description="按组件名聚合的探测结果，当前键为 database 与 cache"
    )


class ContentCountStatsOut(BaseModel):
    """内容量统计（/stats 的 database 段）。"""

    users_count: int = Field(..., description="用户总数")
    posts_count: int = Field(..., description="文章总数（含草稿）")
    published_posts_count: int = Field(..., description="已发布文章数")
    comments_count: int = Field(..., description="评论总数")
    active_comments_count: int = Field(..., description="已通过审核的评论数")


class CacheProbeOut(BaseModel):
    """缓存后端标识（/stats 的 cache 段）。"""

    type: str = Field(..., description="缓存后端类型：redis 或 memory")
    connected: bool = Field(
        ..., description="本字段为固定占位 true，真实可用性看 /cache 与 /health"
    )


class RequestCountStatsOut(BaseModel):
    """请求量统计（/stats 的 requests 段）。"""

    total_requests: int = Field(..., description="访问日志累计条数")
    today_requests: int = Field(..., description="今日（UTC 零点起）访问条数")
    avg_latency_ms: float = Field(
        ..., description="进程内缓冲区（最近一万条）的平均响应毫秒数，冷启动时为 0"
    )


class ProcessMemoryStatsOut(BaseModel):
    """进程内存占用（/stats 的 memory 段）；psutil 不可用时全部为 0。"""

    rss_mb: float = Field(..., description="常驻内存（MB，保留两位小数）")
    vms_mb: float = Field(..., description="虚拟内存（MB，保留两位小数）")
    percent: float = Field(..., description="进程占系统内存百分比")


class CpuStatsOut(BaseModel):
    """CPU 指标（/stats 的 cpu 段）；psutil 不可用时保持默认值。"""

    percent: float = Field(..., description="瞬时 CPU 使用率百分比")
    count: int | None = Field(..., description="逻辑核心数，探测不到时为 null")


class VisitCounterOut(BaseModel):
    """访问计数（/stats 的 visits 段）。"""

    total: int = Field(..., description="访问日志累计条数")
    today: int = Field(..., description="今日（UTC 零点起）访问条数")


class SystemStatsResponse(BaseModel):
    """GET /stats 的响应体（裸对象，无 success 信封）。"""

    database: ContentCountStatsOut = Field(..., description="内容量统计")
    cache: CacheProbeOut = Field(..., description="缓存后端标识")
    requests: RequestCountStatsOut = Field(..., description="请求量与平均延迟")
    memory: ProcessMemoryStatsOut = Field(..., description="进程内存占用")
    cpu: CpuStatsOut = Field(..., description="CPU 指标")
    visits: VisitCounterOut = Field(..., description="访问计数")
    uptime_seconds: float = Field(..., description="进程启动至今的运行秒数")
    timestamp: str = Field(..., description="统计生成时间（ISO 8601，UTC）")


class VisitTrendPointOut(BaseModel):
    """访问量趋势单日采样点。"""

    date: str = Field(..., description="日期，格式 MM-DD")
    value: int = Field(..., description="当日访问条数，无数据时为 0")


class VisitsSummaryResponse(BaseModel):
    """GET /visits/summary 的响应体。"""

    total: int = Field(..., description="访问日志累计条数")
    today: int = Field(..., description="今日（UTC 零点起）访问条数")
    yesterday: int = Field(..., description="昨日全天访问条数")
    week: int = Field(..., description="最近 7 天访问条数")
    month: int = Field(..., description="最近 30 天访问条数")
    unique_ips_today: int = Field(..., description="今日去重来源 IP 数（忽略 IP 为空的记录）")
    trend: list[VisitTrendPointOut] = Field(
        ..., description="最近 7 天逐日访问曲线，固定 7 个点（含今天），缺失日补 0"
    )
    growth: float = Field(..., description="今日相对昨日的增长率百分比；昨日为 0 时回 0")
    retention_days: int = Field(
        ...,
        description=(
            "日志自动保留窗口天数（LOG_RETENTION_DAYS）。<=0 表示不清理，"
            "week/month 恒为真实窗口；>0 且小于窗口天数时，对应计数只是下界"
        ),
    )
    data_since: str | None = Field(
        None,
        description="visit_logs 现存最早一条的 UTC 时间（ISO 8601）；表为空时为 null。用于判断窗口是否被保留策略截短",
    )


class PerformanceWindowStatsOut(BaseModel):
    """某个时间窗口的响应耗时统计（/performance/summary 的两段结构）。"""

    avg_response_time_ms: float = Field(..., description="平均响应耗时（毫秒）")
    p50_response_time_ms: float = Field(..., description="中位数响应耗时（毫秒）")
    p95_response_time_ms: float = Field(..., description="P95 响应耗时（毫秒）")
    p99_response_time_ms: float = Field(..., description="P99 响应耗时（毫秒）")
    total_requests: int = Field(..., description="参与统计的请求条数（仅 response_time_ms > 0）")
    error_count: int = Field(..., description="状态码 >= 400 的请求条数（按窗口全量统计）")
    window_requests: int = Field(
        ..., description="窗口内全部访问日志条数（error_rate 的分母，与 error_count 同口径）"
    )
    error_rate: float = Field(
        ..., description="错误率百分比（error_count / window_requests），保留两位小数"
    )


class PerformanceSummaryResponse(BaseModel):
    """GET /performance/summary 的响应体。"""

    last_24h: PerformanceWindowStatsOut = Field(..., description="最近 24 小时窗口统计")
    last_7d: PerformanceWindowStatsOut = Field(..., description="最近 7 天窗口统计")


class PerformanceLatencyResponse(BaseModel):
    """GET /performance 的响应体：基于进程内内存缓冲的延迟分位数。"""

    avg_latency: float = Field(..., description="平均延迟（毫秒）")
    p50_latency: float = Field(..., description="中位延迟（毫秒）")
    p95_latency: float = Field(..., description="P95 延迟（毫秒）")
    p99_latency: float = Field(..., description="P99 延迟（毫秒）")
    requests_per_minute: float = Field(..., description="采样窗口内的每分钟平均请求数")
    error_rate: float = Field(..., description="错误率（当前实现固定回 0）")
    sample_count: int | None = Field(
        default=None, description="窗口内采样条数；无样本的快速分支不返回该键"
    )


class DbPoolStatsOut(BaseModel):
    """SQLAlchemy 连接池状态。"""

    size: int = Field(..., description="池内连接数；池类型不支持该探针时为 0")
    checked_in: int = Field(..., description="空闲（已归还）连接数")
    checked_out: int = Field(..., description="已被占用（借出）的连接数")
    overflow: int = Field(..., description="超出 size 的临时连接数")


class DatabaseMonitorResponse(BaseModel):
    """GET /database 的响应体。"""

    pool: DbPoolStatsOut = Field(..., description="连接池状态")
    table_sizes: dict[str, int] = Field(
        ..., description="按表名聚合的行数，当前键为 users 与 posts"
    )
    database_url: str | None = Field(
        default=None, description="生效的数据库连接串，凭据段已做掩码处理；无 URL 时为 null"
    )


class CacheMonitorResponse(BaseModel):
    """GET /cache 的响应体（裸对象，无 success 信封）。"""

    type: str = Field(..., description="缓存后端类型：redis 或 memory")
    connected: bool = Field(..., description="是否连通；Redis 探测失败时置 false")
    metrics: dict[str, Any] = Field(
        ...,
        description=(
            "缓存指标。memory 后端固定为 total_keys / hit_rate / miss_rate 三个占位 0；"
            "Redis 后端额外含 used_memory_human、connected_clients、total_commands_processed，"
            "hit_rate / miss_rate 为百分比"
        ),
    )
    error: str | None = Field(default=None, description="Redis 探测异常信息；正常时不返回该键")


class TrendPointOut(BaseModel):
    """业务量趋势单日采样点。"""

    date: str = Field(..., description="日期，格式 MM-DD")
    count: int = Field(..., description="当日新增条数，无数据时为 0")


class TrendsResponse(BaseModel):
    """GET /trends 的响应体：四条按天分桶的折线数据。"""

    posts: list[TrendPointOut] = Field(..., description="每日新增文章数")
    comments: list[TrendPointOut] = Field(..., description="每日新增评论数")
    users: list[TrendPointOut] = Field(..., description="每日新增用户数")
    visits: list[TrendPointOut] = Field(..., description="每日访问量")


# ── 访问日志：内存队列 + 后台批量落库 ─────────────────────────────────────
# 高并发下逐请求 INSERT 会让数据库成为吞吐瓶颈（每请求一次连接获取+事务提交），
# 改为内存队列缓冲、后台任务每 5s 批量写一次。
# 队列满时丢弃（访问日志允许有损，业务请求吞吐优先）。

_VISIT_QUEUE_MAX = 10000
_VISIT_BATCH_SIZE = 50
_VISIT_FLUSH_INTERVAL = 5.0

_visit_queue: asyncio.Queue | None = None
_visit_flusher: asyncio.Task | None = None


async def _flush_visit_queue() -> int:
    """把队列中的访问日志批量写入数据库，返回本次写入条数。"""
    from backend.core.database import async_session_maker
    from backend.models.monitoring import VisitLog

    if _visit_queue is None or _visit_queue.empty():
        return 0

    items: list[tuple] = []
    while len(items) < _VISIT_BATCH_SIZE:
        try:
            items.append(_visit_queue.get_nowait())
        except asyncio.QueueEmpty:
            break
    if not items:
        return 0

    try:
        async with async_session_maker() as db:
            db.add_all(
                VisitLog(
                    path=it[0],
                    method=it[1],
                    ip=it[2],
                    user_agent=it[3],
                    referer=it[4],
                    status_code=it[5],
                    response_time_ms=it[6],
                    created_at=it[7],
                )
                for it in items
            )
            await db.commit()
    except Exception:
        # 返回 0 而不是 len(items)：调用方 `while await _flush_visit_queue() > 0` 靠返回值
        # 判断是否继续排空。落库失败也算"有进展"的话，一次数据库抖动期间会把整个缓冲队列
        # 连续取出并全部丢弃；返回 0 让本轮停下。
        # 同时尽力把本批放回队列（放不下的部分才真丢），一次瞬时故障不必整批报废。
        restored = 0
        for it in reversed(items):
            try:
                _visit_queue.put_nowait(it)
                restored += 1
            except asyncio.QueueFull:
                break
        logger.exception(
            "[monitoring] 访问日志批量落库失败（本批 %d 条，回队 %d 条，丢弃 %d 条）",
            len(items),
            restored,
            len(items) - restored,
        )
        return 0
    return len(items)


async def _visit_flush_loop() -> None:
    """后台周期性落库任务（懒启动，进程内单例）。"""
    while True:
        await asyncio.sleep(_VISIT_FLUSH_INTERVAL)
        try:
            # 一次唤醒可能积压多批，循环清空
            while await _flush_visit_queue() > 0:
                pass
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception("[monitoring] 访问日志 flush 循环异常")


async def record_visit(request: Request, status_code: int, response_time_ms: float):
    """记录访问日志（入队，非阻塞；由后台任务批量落库）。"""
    global _visit_queue, _visit_flusher

    if _visit_queue is None:
        _visit_queue = asyncio.Queue(maxsize=_VISIT_QUEUE_MAX)
    try:
        _visit_queue.put_nowait(
            (
                request.url.path[:500],
                request.method,
                request.client.host if request.client else None,
                (request.headers.get("user-agent") or "")[:500] or None,
                (request.headers.get("referer") or "")[:500] or None,
                status_code,
                int(response_time_ms),
                datetime.now(UTC),
            )
        )
    except asyncio.QueueFull:
        return  # 高峰期丢弃访问日志，保护业务吞吐

    # 懒启动 flush 循环（进程内单例；意外退出后自动重启）
    if _visit_flusher is None or _visit_flusher.done():
        try:
            _visit_flusher = asyncio.create_task(_visit_flush_loop())
        except RuntimeError:
            pass  # 无运行中的事件循环——下次请求再启


@router.get(
    "/health",
    summary="健康检查",
    description=(
        "匿名可访问（OOBE 与负载均衡探针白名单）。对数据库与缓存各做一次真实探测，"
        "任一组件非 healthy 时整体降级为 degraded。只读、幂等，无副作用。"
    ),
    responses={200: {"model": HealthCheckResponse, "description": "组件级健康报告"}},
)
async def health_check():
    """健康检查"""
    checks = {}

    # 检查数据库
    try:
        async with engine.connect() as conn:
            await conn.execute(select(1))
        checks["database"] = {"status": "healthy", "latency_ms": 0}
    except Exception as e:
        checks["database"] = {"status": "unhealthy", "error": str(e)}

    # 检查缓存
    try:
        await cache.set("health_check", "ok", 10)
        result = await cache.get("health_check")
        checks["cache"] = {"status": "healthy" if result == "ok" else "degraded"}
    except Exception as e:
        checks["cache"] = {"status": "unhealthy", "error": str(e)}

    # 计算整体状态
    all_healthy = all(c.get("status") == "healthy" for c in checks.values())

    return {
        "status": "healthy" if all_healthy else "degraded",
        "timestamp": datetime.now(UTC).isoformat(),
        "checks": checks,
    }


@router.get(
    "/stats",
    summary="系统统计",
    description=(
        "需 CurrentStaff。聚合内容量、访问量、缓存后端、进程内存与 CPU 五类指标，"
        "供后台仪表盘首屏使用；psutil 缺失时内存/CPU 回 0 而不是报错。只读、幂等。"
    ),
    responses={200: {"model": SystemStatsResponse, "description": "系统统计聚合对象"}},
)
async def get_system_stats(
    db: DB,
    current_user: CurrentStaff,
):
    """获取系统统计"""
    from backend.models.blog import Comment, Post
    from backend.models.monitoring import VisitLog
    from backend.models.user import User

    # 数据库统计
    db_stats = {
        "users_count": await db.scalar(select(func.count()).select_from(User)) or 0,
        "posts_count": await db.scalar(select(func.count()).select_from(Post)) or 0,
        "published_posts_count": await db.scalar(
            select(func.count()).select_from(Post).where(Post.status == "published")
        )
        or 0,
        "comments_count": await db.scalar(select(func.count()).select_from(Comment)) or 0,
        "active_comments_count": await db.scalar(
            select(func.count()).select_from(Comment).where(Comment.active.is_(True))
        )
        or 0,
    }

    # 访问统计
    total_visits = await cache.get(_VISIT_TOTAL_KEY)
    if total_visits is None:
        total_visits = await db.scalar(select(func.count()).select_from(VisitLog)) or 0
        await cache.set(_VISIT_TOTAL_KEY, total_visits, ttl=_VISIT_TOTAL_TTL)
    today_start = datetime.now(UTC).replace(hour=0, minute=0, second=0, microsecond=0)
    today_visits = (
        await db.scalar(
            select(func.count()).select_from(VisitLog).where(VisitLog.created_at >= today_start)
        )
        or 0
    )

    # 缓存统计
    cache_stats = {
        "type": "redis" if settings.redis_url else "memory",
        "connected": True,
    }

    # CPU 统计
    cpu_stats = {
        "percent": 0.0,
        "count": 1,
    }
    try:
        import psutil

        # interval=0.1 是**阻塞**采样：直接调用会让事件循环停 100ms，监控页每次刷新
        # 就顺带拖慢全站请求。与 stats.py 的 _get_system_health 同口径，丢给线程池。
        def _sample_cpu() -> tuple[float, int | None]:
            return psutil.cpu_percent(interval=0.1), psutil.cpu_count(logical=True)

        percent, logical = await asyncio.to_thread(_sample_cpu)
        cpu_stats["percent"] = percent
        cpu_stats["count"] = logical or 1
    except psutil_errors() as exc:
        # psutil 缺失/调用失败时保留默认值，但留下原因：
        # 否则监控页的 "CPU 0%" 会永久伪装成一台健康的机器。
        logger.debug(f"[monitoring] CPU 指标探测失败: {exc}")

    # 运行时间
    uptime_seconds = time.time() - _start_time

    # 请求统计
    request_stats = {
        "total_requests": total_visits,
        "today_requests": today_visits,
        "avg_latency_ms": sum(_metrics.get("request_latency", []))
        / max(len(_metrics.get("request_latency", [])), 1)
        * 1000,
    }

    # 内存统计
    memory_stats = {
        "rss_mb": 0,
        "vms_mb": 0,
        "percent": 0.0,
    }
    try:
        import psutil

        process = psutil.Process()
        memory_info = process.memory_info()
        memory_stats = {
            "rss_mb": round(memory_info.rss / 1024 / 1024, 2),
            "vms_mb": round(memory_info.vms / 1024 / 1024, 2),
            "percent": round(process.memory_percent(), 2),
        }
    except psutil_errors() as exc:
        logger.debug(f"[monitoring] 内存指标探测失败: {exc}")

    return {
        "database": db_stats,
        "cache": cache_stats,
        "requests": request_stats,
        "memory": memory_stats,
        "cpu": cpu_stats,
        "visits": {
            "total": total_visits,
            "today": today_visits,
        },
        "uptime_seconds": uptime_seconds,
        "timestamp": datetime.now(UTC).isoformat(),
    }


@router.get(
    "/visits/summary",
    summary="访问量汇总",
    description=(
        "需 CurrentStaff。按今日/昨日/7 天/30 天窗口汇总访问日志条数，并给出最近 7 天逐日曲线"
        "与今日环比增长率。趋势用单条 GROUP BY 聚合，不按天循环查询。只读、幂等。"
        "响应另带 retention_days 与 data_since：日志受 LOG_RETENTION_DAYS 自动清理，"
        "保留窗口小于窗口天数时 week/month 只是下界，消费方据此标注口径。"
    ),
    responses={200: {"model": VisitsSummaryResponse, "description": "访问量汇总与 7 日趋势"}},
)
async def get_visits_summary(
    db: DB,
    current_user: CurrentStaff,
):
    """获取访问量汇总"""
    from backend.models.monitoring import VisitLog

    now = datetime.now(UTC)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    yesterday_start = today_start - timedelta(days=1)
    week_start = today_start - timedelta(days=7)
    month_start = today_start - timedelta(days=30)

    total = await cache.get(_VISIT_TOTAL_KEY)
    if total is None:
        total = await db.scalar(select(func.count()).select_from(VisitLog)) or 0
        await cache.set(_VISIT_TOTAL_KEY, total, ttl=_VISIT_TOTAL_TTL)
    today = (
        await db.scalar(
            select(func.count()).select_from(VisitLog).where(VisitLog.created_at >= today_start)
        )
        or 0
    )
    yesterday = (
        await db.scalar(
            select(func.count())
            .select_from(VisitLog)
            .where(
                VisitLog.created_at >= yesterday_start,
                VisitLog.created_at < today_start,
            )
        )
        or 0
    )
    week = (
        await db.scalar(
            select(func.count()).select_from(VisitLog).where(VisitLog.created_at >= week_start)
        )
        or 0
    )
    month = (
        await db.scalar(
            select(func.count()).select_from(VisitLog).where(VisitLog.created_at >= month_start)
        )
        or 0
    )

    # 计算趋势（最近7天每天访问量）：单次 GROUP BY 聚合（替代 7 次 COUNT）
    week_ago_start = today_start - timedelta(days=6)
    date_expr = func.date(VisitLog.created_at)
    rows = (
        await db.execute(
            select(date_expr, func.count())
            .where(
                VisitLog.created_at >= week_ago_start,
                VisitLog.created_at < today_start + timedelta(days=1),
            )
            .group_by(date_expr)
        )
    ).all()
    counts_by_day = {}
    for date_val, cnt in rows:
        if date_val is not None:
            key = datetime.strptime(str(date_val)[:10], "%Y-%m-%d").strftime("%m-%d")
            counts_by_day[key] = int(cnt or 0)
    trend = []
    for i in range(6, -1, -1):
        date = today_start - timedelta(days=i)
        trend.append(
            {"date": date.strftime("%m-%d"), "value": counts_by_day.get(date.strftime("%m-%d"), 0)}
        )

    # 独立IP数（今日）
    unique_ips = (
        await db.scalar(
            select(func.count(func.distinct(VisitLog.ip)))
            .select_from(VisitLog)
            .where(
                VisitLog.created_at >= today_start,
                VisitLog.ip.isnot(None),
            )
        )
        or 0
    )

    # 数据覆盖起点：visit_logs 会被 LOG_RETENTION_DAYS 自动清理，"最近 30 天"这类
    # 固定窗口在保留窗口更短时就只剩部分数据。MIN(created_at) 走 created_at 索引，
    # 是常数级开销；前端据此把被截短的窗口标成下界，而不是当成全量。
    earliest = await db.scalar(select(func.min(VisitLog.created_at)))
    if earliest is not None and earliest.tzinfo is None:
        # SQLite 的 CURRENT_TIMESTAMP 落的是 naive UTC；PG 才是 TIMESTAMPTZ。
        earliest = earliest.replace(tzinfo=UTC)

    return {
        "total": total,
        "today": today,
        "yesterday": yesterday,
        "week": week,
        "month": month,
        "unique_ips_today": unique_ips,
        "trend": trend,
        "growth": ((today - yesterday) / max(yesterday, 1)) * 100 if yesterday > 0 else 0,
        "retention_days": settings.log_retention_days,
        "data_since": earliest.isoformat() if earliest is not None else None,
    }


@router.get(
    "/performance/summary",
    summary="性能概览",
    description=(
        "需 CurrentStaff。基于访问日志的 response_time_ms 计算 24 小时与 7 天窗口的均值与"
        "P50/P95/P99 分位数，并按 status_code >= 400 统计错误数与错误率。"
        "只统计耗时大于 0 的请求（取窗口内最近 50000 条样本），无数据时各分位回 0。只读、幂等。"
    ),
    responses={200: {"model": PerformanceSummaryResponse, "description": "两个时间窗口的耗时统计"}},
)
async def get_performance_summary(
    db: DB,
    current_user: CurrentStaff,
):
    """获取性能概览（分位数用纯 Python 实现，不依赖 numpy）"""
    from backend.models.monitoring import VisitLog

    now = datetime.now(UTC)
    h24_ago = now - timedelta(hours=24)
    d7_ago = now - timedelta(days=7)

    # 24小时性能
    h24_logs = (
        (
            await db.execute(
                select(VisitLog.response_time_ms)
                .where(
                    VisitLog.created_at >= h24_ago,
                    VisitLog.response_time_ms > 0,
                )
                .order_by(desc(VisitLog.created_at), desc(VisitLog.id))
                .limit(_PERF_SAMPLE_LIMIT)
            )
        )
        .scalars()
        .all()
    )

    # 7天性能
    d7_logs = (
        (
            await db.execute(
                select(VisitLog.response_time_ms)
                .where(
                    VisitLog.created_at >= d7_ago,
                    VisitLog.response_time_ms > 0,
                )
                .order_by(desc(VisitLog.created_at), desc(VisitLog.id))
                .limit(_PERF_SAMPLE_LIMIT)
            )
        )
        .scalars()
        .all()
    )

    def calc_stats(logs_list):
        if not logs_list:
            return {
                "avg_response_time_ms": 0,
                "p50_response_time_ms": 0,
                "p95_response_time_ms": 0,
                "p99_response_time_ms": 0,
                "total_requests": 0,
                "error_count": 0,
                "error_rate": 0,
            }
        return {
            "avg_response_time_ms": round(sum(logs_list) / len(logs_list), 2),
            "p50_response_time_ms": round(_percentile(logs_list, 50), 2),
            "p95_response_time_ms": round(_percentile(logs_list, 95), 2),
            "p99_response_time_ms": round(_percentile(logs_list, 99), 2),
            "total_requests": len(logs_list),
        }

    # 错误统计
    h24_errors = (
        await db.scalar(
            select(func.count())
            .select_from(VisitLog)
            .where(
                VisitLog.created_at >= h24_ago,
                VisitLog.status_code >= 400,
            )
        )
        or 0
    )
    d7_errors = (
        await db.scalar(
            select(func.count())
            .select_from(VisitLog)
            .where(
                VisitLog.created_at >= d7_ago,
                VisitLog.status_code >= 400,
            )
        )
        or 0
    )

    # 分母口径：窗口内**全部**日志条数（与 error_count 同一套 WHERE）。
    h24_window_total = (
        await db.scalar(
            select(func.count()).select_from(VisitLog).where(VisitLog.created_at >= h24_ago)
        )
        or 0
    )
    d7_window_total = (
        await db.scalar(
            select(func.count()).select_from(VisitLog).where(VisitLog.created_at >= d7_ago)
        )
        or 0
    )

    h24_stats = calc_stats(h24_logs)
    h24_stats["window_requests"] = h24_window_total
    h24_stats["error_count"] = h24_errors
    # 原先分母用的是 response_time_ms>0 的样本数，而快错误（429/401 亚毫秒回 0）
    # 全在样本之外，分子却统计所有 >=400 的行——两处不同口径能把错误率顶过 100%。
    h24_stats["error_rate"] = round(h24_errors / max(h24_window_total, 1) * 100, 2)

    d7_stats = calc_stats(d7_logs)
    d7_stats["window_requests"] = d7_window_total
    d7_stats["error_count"] = d7_errors
    d7_stats["error_rate"] = round(d7_errors / max(d7_window_total, 1) * 100, 2)

    return {
        "last_24h": h24_stats,
        "last_7d": d7_stats,
    }


@router.get(
    "/performance",
    summary="性能指标",
    description=(
        "需 CurrentStaff。统计**进程内内存环形缓冲**里最近 period 分钟（默认 60，上限 1440）的"
        "请求延迟分位数；缓冲不落盘，进程重启后清零，无样本时快速返回全 0（该分支不含 sample_count 键）。"
        "只读、幂等。"
    ),
    responses={
        200: {"model": PerformanceLatencyResponse, "description": "延迟分位数与每分钟请求数"}
    },
)
async def get_performance_metrics(
    current_user: CurrentStaff,
    period: int = Query(60, ge=1, le=1440, description="统计周期（分钟）"),
):
    """获取性能指标"""
    latencies = _metrics.get("request_latency", [])
    timestamps = _metrics_timestamps.get("request_latency", [])

    # 过滤时间范围内的数据
    now = time.time()
    cutoff = now - period * 60

    filtered_latencies = [l for l, t in zip(latencies, timestamps) if t >= cutoff]

    if not filtered_latencies:
        return {
            "avg_latency": 0,
            "p50_latency": 0,
            "p95_latency": 0,
            "p99_latency": 0,
            "requests_per_minute": 0,
            "error_rate": 0,
        }

    # 环形缓冲里存的是秒，读数统一换算成毫秒
    return {
        "avg_latency": round(sum(filtered_latencies) / len(filtered_latencies) * 1000, 2),
        "p50_latency": round(_percentile(filtered_latencies, 50) * 1000, 2),
        "p95_latency": round(_percentile(filtered_latencies, 95) * 1000, 2),
        "p99_latency": round(_percentile(filtered_latencies, 99) * 1000, 2),
        "requests_per_minute": len(filtered_latencies) / period,
        "error_rate": 0,
        "sample_count": len(filtered_latencies),
    }


@router.get(
    "/database",
    summary="数据库监控",
    description=(
        "需 CurrentStaff。读取 SQLAlchemy 连接池占用与 users/posts 两张表的行数。"
        "database_url 为运行时生效的连接串且凭据段已掩码，请勿在前端公开展示。只读、幂等。"
    ),
    responses={200: {"model": DatabaseMonitorResponse, "description": "连接池与表行数"}},
)
async def get_database_stats(
    db: DB,
    current_user: CurrentStaff,
):
    """获取数据库统计"""
    from backend.models.blog import Post
    from backend.models.user import User

    # 连接池信息
    pool = engine.pool

    pool_info = {
        "size": pool.size() if hasattr(pool, "size") else 0,
        "checked_in": pool.checkedin() if hasattr(pool, "checkedin") else 0,
        "checked_out": pool.checkedout() if hasattr(pool, "checkedout") else 0,
        "overflow": pool.overflow() if hasattr(pool, "overflow") else 0,
    }

    # 表大小统计
    table_sizes = {}

    # 用户表
    user_count = await db.scalar(select(func.count()).select_from(User))
    table_sizes["users"] = user_count or 0

    # 文章表
    post_count = await db.scalar(select(func.count()).select_from(Post))
    table_sizes["posts"] = post_count or 0

    return {
        "pool": pool_info,
        "table_sizes": table_sizes,
        "database_url": str(engine.url).replace(":***@", ":****@") if engine.url else None,
    }


@router.get(
    "/cache",
    summary="缓存监控",
    description=(
        "需 CurrentStaff。Redis 配置存在时实时 INFO 一次（键总量/命中率/内存占用/客户端数），"
        "探测失败回 connected=false 并附 error 文本；memory 后端只回三项占位 0。"
        "返回裸对象（无 success 信封）。只读、幂等。"
    ),
    responses={200: {"model": CacheMonitorResponse, "description": "缓存后端指标"}},
)
async def get_cache_stats(
    current_user: CurrentStaff,
):
    """获取缓存统计"""
    stats = {
        "type": "redis" if settings.redis_url else "memory",
        "connected": True,
        "metrics": {
            "total_keys": 0,
            "hit_rate": 0,
            "miss_rate": 0,
        },
    }

    if settings.redis_url:
        try:
            import redis.asyncio as redis

            client = redis.from_url(settings.redis_url)
            info = await client.info()

            stats["metrics"] = {
                "total_keys": await client.dbsize(),
                "hit_rate": info.get("keyspace_hits", 0)
                / max(info.get("keyspace_hits", 0) + info.get("keyspace_misses", 0), 1)
                * 100,
                "miss_rate": info.get("keyspace_misses", 0)
                / max(info.get("keyspace_hits", 0) + info.get("keyspace_misses", 0), 1)
                * 100,
                "used_memory_human": info.get("used_memory_human", "0B"),
                "connected_clients": info.get("connected_clients", 0),
                "total_commands_processed": info.get("total_commands_processed", 0),
            }

            await client.close()
        except Exception as e:
            stats["error"] = str(e)
            stats["connected"] = False

    return stats


@router.get(
    "/trends",
    summary="趋势数据",
    description=(
        "需 CurrentStaff。返回文章/评论/用户/访问四条按天分桶的折线，天数 1-30（默认 7）。"
        "每张表一条 GROUP BY 查询，缺失日期补 0，数组长度恒等于 days。只读、幂等。"
    ),
    responses={200: {"model": TrendsResponse, "description": "四条日度趋势序列"}},
)
async def get_trends(
    db: DB,
    current_user: CurrentStaff,
    days: int = Query(7, ge=1, le=30, description="统计天数"),
):
    """获取趋势数据"""
    from backend.models.blog import Comment, Post
    from backend.models.monitoring import VisitLog
    from backend.models.user import User

    now = datetime.now(UTC)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    range_start = today_start - timedelta(days=days - 1)

    def _empty_slots() -> dict[str, int]:
        return {
            (today_start - timedelta(days=i)).strftime("%m-%d"): 0 for i in range(days - 1, -1, -1)
        }

    # 每张表一次 GROUP BY 聚合（替代原来的 4×days 次 COUNT 查询；
    # func.date() 在 SQLite 与 PostgreSQL 上均可按天分桶）
    async def _daily_counts(model, column) -> dict[str, int]:
        slots = _empty_slots()
        date_expr = func.date(column)
        rows = (
            await db.execute(
                select(date_expr, func.count())
                .where(column >= range_start, column < today_start + timedelta(days=1))
                .group_by(date_expr)
            )
        ).all()
        for date_val, cnt in rows:
            if date_val is None:
                continue
            # date() 输出 "YYYY-MM-DD"（两库一致）
            key = datetime.strptime(str(date_val)[:10], "%Y-%m-%d").strftime("%m-%d")
            if key in slots:
                slots[key] = int(cnt or 0)
        return slots

    posts_by_day = await _daily_counts(Post, Post.created_at)
    comments_by_day = await _daily_counts(Comment, Comment.created_at)
    users_by_day = await _daily_counts(User, User.created_at)
    visits_by_day = await _daily_counts(VisitLog, VisitLog.created_at)

    return {
        "posts": [{"date": d, "count": c} for d, c in posts_by_day.items()],
        "comments": [{"date": d, "count": c} for d, c in comments_by_day.items()],
        "users": [{"date": d, "count": c} for d, c in users_by_day.items()],
        "visits": [{"date": d, "count": c} for d, c in visits_by_day.items()],
    }


# 内部函数：记录请求延迟


def record_request_latency(latency: float):
    """记录请求延迟"""
    _metrics["request_latency"].append(latency)
    _metrics_timestamps["request_latency"].append(time.time())

    # 保留最近 10000 条记录
    if len(_metrics["request_latency"]) > 10000:
        _metrics["request_latency"] = _metrics["request_latency"][-10000:]
        _metrics_timestamps["request_latency"] = _metrics_timestamps["request_latency"][-10000:]
