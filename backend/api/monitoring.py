"""
监控和性能统计 API

提供系统监控、性能指标、访问统计等功能。
"""

import time
from datetime import datetime
from typing import Any

from fastapi import APIRouter, Query, Request
from pydantic import BaseModel
from sqlalchemy import func, select

from backend.core.auth import DB, CurrentStaff
from backend.core.cache import cache
from backend.core.config import settings
from backend.core.database import engine
from backend.utils.compat import UTC, timedelta

router = APIRouter(tags=["监控"])

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


async def record_visit(request: Request, status_code: int, response_time_ms: float):
    """记录访问日志"""
    from backend.core.database import async_session_factory
    from backend.models.monitoring import VisitLog

    try:
        async with async_session_factory() as db:
            visit = VisitLog(
                path=request.url.path[:500],
                method=request.method,
                ip=request.client.host if request.client else None,
                user_agent=request.headers.get("user-agent", "")[:500]
                if request.headers.get("user-agent")
                else None,
                referer=request.headers.get("referer", "")[:500]
                if request.headers.get("referer")
                else None,
                status_code=status_code,
                response_time_ms=int(response_time_ms),
            )
            db.add(visit)
            await db.commit()
    except Exception:
        pass


@router.get(
    "/health",
    summary="健康检查",
    description="检查系统各组件的健康状态。",
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
    description="获取系统运行统计数据。",
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
    total_visits = await db.scalar(select(func.count()).select_from(VisitLog)) or 0
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

        cpu_stats["percent"] = psutil.cpu_percent(interval=0.1)
        cpu_stats["count"] = psutil.cpu_count(logical=True) or 1
    except ImportError:
        pass
    except Exception:
        pass

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
    except ImportError:
        pass
    except Exception:
        pass

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
    description="获取访问量汇总数据。",
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

    total = await db.scalar(select(func.count()).select_from(VisitLog)) or 0
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

    # 计算趋势（最近7天每天访问量）
    trend = []
    for i in range(6, -1, -1):
        date = today_start - timedelta(days=i)
        next_date = date + timedelta(days=1)
        count = (
            await db.scalar(
                select(func.count())
                .select_from(VisitLog)
                .where(
                    VisitLog.created_at >= date,
                    VisitLog.created_at < next_date,
                )
            )
            or 0
        )
        trend.append({"date": date.strftime("%m-%d"), "value": count})

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

    return {
        "total": total,
        "today": today,
        "yesterday": yesterday,
        "week": week,
        "month": month,
        "unique_ips_today": unique_ips,
        "trend": trend,
        "growth": ((today - yesterday) / max(yesterday, 1)) * 100 if yesterday > 0 else 0,
    }


@router.get(
    "/performance/summary",
    summary="性能概览",
    description="获取性能概览数据。",
)
async def get_performance_summary(
    db: DB,
    current_user: CurrentStaff,
):
    """获取性能概览"""
    import numpy as np

    from backend.models.monitoring import VisitLog

    now = datetime.now(UTC)
    h24_ago = now - timedelta(hours=24)
    d7_ago = now - timedelta(days=7)

    # 24小时性能
    h24_logs = (
        (
            await db.execute(
                select(VisitLog.response_time_ms).where(
                    VisitLog.created_at >= h24_ago,
                    VisitLog.response_time_ms > 0,
                )
            )
        )
        .scalars()
        .all()
    )

    # 7天性能
    d7_logs = (
        (
            await db.execute(
                select(VisitLog.response_time_ms).where(
                    VisitLog.created_at >= d7_ago,
                    VisitLog.response_time_ms > 0,
                )
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
        arr = np.array(logs_list)
        return {
            "avg_response_time_ms": round(float(np.mean(arr)), 2),
            "p50_response_time_ms": round(float(np.percentile(arr, 50)), 2),
            "p95_response_time_ms": round(float(np.percentile(arr, 95)), 2),
            "p99_response_time_ms": round(float(np.percentile(arr, 99)), 2),
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

    h24_stats = calc_stats(h24_logs)
    h24_stats["error_count"] = h24_errors
    h24_stats["error_rate"] = round(h24_errors / max(h24_stats["total_requests"], 1) * 100, 2)

    d7_stats = calc_stats(d7_logs)
    d7_stats["error_count"] = d7_errors
    d7_stats["error_rate"] = round(d7_errors / max(d7_stats["total_requests"], 1) * 100, 2)

    return {
        "last_24h": h24_stats,
        "last_7d": d7_stats,
    }


@router.get(
    "/performance",
    summary="性能指标",
    description="获取系统性能指标。",
)
async def get_performance_metrics(
    current_user: CurrentStaff,
    period: int = Query(60, ge=1, le=1440, description="统计周期（分钟）"),
):
    """获取性能指标"""
    import numpy as np

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

    latencies_array = np.array(filtered_latencies)

    return {
        "avg_latency": float(np.mean(latencies_array) * 1000),
        "p50_latency": float(np.percentile(latencies_array, 50) * 1000),
        "p95_latency": float(np.percentile(latencies_array, 95) * 1000),
        "p99_latency": float(np.percentile(latencies_array, 99) * 1000),
        "requests_per_minute": len(filtered_latencies) / period,
        "error_rate": 0,
        "sample_count": len(filtered_latencies),
    }


@router.get(
    "/database",
    summary="数据库监控",
    description="获取数据库连接和查询统计。",
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
    description="获取缓存命中率和使用统计。",
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
    description="获取系统指标的历史趋势。",
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

    trends = {
        "posts": [],
        "comments": [],
        "users": [],
        "visits": [],
    }

    now = datetime.now(UTC)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)

    for i in range(days - 1, -1, -1):
        date = today_start - timedelta(days=i)
        date_end = date + timedelta(days=1)

        # 文章数
        posts_count = (
            await db.scalar(
                select(func.count())
                .select_from(Post)
                .where(
                    Post.created_at >= date,
                    Post.created_at < date_end,
                )
            )
            or 0
        )

        # 评论数
        comments_count = (
            await db.scalar(
                select(func.count())
                .select_from(Comment)
                .where(
                    Comment.created_at >= date,
                    Comment.created_at < date_end,
                )
            )
            or 0
        )

        # 用户数
        users_count = (
            await db.scalar(
                select(func.count())
                .select_from(User)
                .where(
                    User.created_at >= date,
                    User.created_at < date_end,
                )
            )
            or 0
        )

        # 访问数
        visits_count = (
            await db.scalar(
                select(func.count())
                .select_from(VisitLog)
                .where(
                    VisitLog.created_at >= date,
                    VisitLog.created_at < date_end,
                )
            )
            or 0
        )

        trends["posts"].append({"date": date.strftime("%m-%d"), "count": posts_count})
        trends["comments"].append({"date": date.strftime("%m-%d"), "count": comments_count})
        trends["users"].append({"date": date.strftime("%m-%d"), "count": users_count})
        trends["visits"].append({"date": date.strftime("%m-%d"), "count": visits_count})

    return trends


# 内部函数：记录请求延迟


def record_request_latency(latency: float):
    """记录请求延迟"""
    _metrics["request_latency"].append(latency)
    _metrics_timestamps["request_latency"].append(time.time())

    # 保留最近 10000 条记录
    if len(_metrics["request_latency"]) > 10000:
        _metrics["request_latency"] = _metrics["request_latency"][-10000:]
        _metrics_timestamps["request_latency"] = _metrics_timestamps["request_latency"][-10000:]
