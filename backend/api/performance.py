"""
性能监控 API

提供管理员接口查看 API 性能统计，包括平均响应时间、P95/P99、错误率、热门慢接口等。

路由设计：
- GET /api/admin/performance/summary：最近 24 小时 / 7 天性能摘要
- GET /api/admin/performance/slow：最慢的 20 个请求
- GET /api/admin/performance/storage：存储占用估算
- DELETE /api/admin/performance/cleanup：清理指定天数前的旧数据
"""

from datetime import datetime, timedelta
from typing import Any

from fastapi import APIRouter, Query
from pydantic import BaseModel, Field
from sqlalchemy import delete, desc, func, select

from backend.core.auth import DB, CurrentStaff
from backend.models.performance_metric import PerformanceMetric
from backend.utils.compat import UTC

router = APIRouter(tags=["性能监控"])


# ═══════════════════════════════════════════════════════════════════════════
# 响应体文档模型（仅供 OpenAPI `responses={200: {"model": ...}}` 声明使用，
# 运行时不做序列化过滤——实际响应以 handler 返回字面量为准）
# ═══════════════════════════════════════════════════════════════════════════


class PerformanceSlowEndpointDoc(BaseModel):
    """热门慢接口榜单的单条（按平均响应时间倒序 top 5）。"""

    endpoint: str = Field(..., description="接口路径（performance_metrics 表登记的原始 path）")
    method: str = Field(..., description="HTTP 方法（GET/POST/…）")
    avg_response_time_ms: float = Field(..., description="窗口内平均响应时间毫秒（保留 2 位小数）")
    request_count: int = Field(..., description="窗口内该 (endpoint, method) 的请求条数")


class PerformancePeriodStatsDoc(BaseModel):
    """单个时间窗口（24h / 7d）的性能统计块，由 ``_stats_for_period`` 产出。"""

    total_requests: int = Field(..., description="窗口内记录的请求总数")
    avg_response_time_ms: float = Field(..., description="平均响应时间毫秒（保留 2 位小数）")
    max_response_time_ms: int = Field(..., description="最慢一次请求的响应时间毫秒")
    p95_response_time_ms: int = Field(
        ..., description="P95 响应时间毫秒（升序取整索引，无数据时为 0）"
    )
    p99_response_time_ms: int = Field(..., description="P99 响应时间毫秒（同上，无数据时为 0）")
    error_count: int = Field(..., description="状态码 >= 400 的请求数")
    error_rate: float = Field(
        ..., description="错误率百分比（error_count/total_requests*100，保留 2 位小数；零请求为 0）"
    )
    slow_endpoints: list[PerformanceSlowEndpointDoc] = Field(
        default_factory=list, description="平均耗时最高的 5 个接口"
    )


class PerformanceSummaryResponseDoc(BaseModel):
    """``GET /api/admin/performance/summary`` 的响应体（裸 dict，无信封）。需 CurrentStaff。"""

    last_24h: PerformancePeriodStatsDoc = Field(..., description="最近 24 小时窗口统计")
    last_7d: PerformancePeriodStatsDoc = Field(..., description="最近 7 天窗口统计")
    timestamp: str = Field(
        ..., description="统计基准时刻（当前 UTC 时间的 isoformat 字符串，两窗口共用）"
    )


class StorageStatusBucketDoc(BaseModel):
    """按 HTTP 状态码分组的行数。"""

    status_code: int = Field(..., description="HTTP 状态码")
    count: int = Field(..., description="该状态码的记录的条数（全表，不限窗口）")


class StorageDailyBucketDoc(BaseModel):
    """最近 7 天按日期分组的统计（Python 侧分组以兼容 SQLite/PG 方言差异）。"""

    date: str = Field(..., description="日期键 YYYY-MM-DD，升序排列")
    count: int = Field(
        ..., description="当日记录条数（含 response_time 为 null 的行，它们不进均值计算）"
    )
    avg_response_time_ms: float = Field(
        ..., description="当日平均响应时间毫秒（保留 2 位小数），无有效耗时样本时为 0"
    )


class PerformanceStorageResponseDoc(BaseModel):
    """``GET /api/admin/performance/storage`` 的响应体（裸 dict，无信封）。需 CurrentStaff。"""

    total_count: int = Field(..., description="performance_metrics 全表行数")
    earliest_record: str | None = Field(
        None, description="最早记录的 created_at ISO 8601 字符串，空表时为 null"
    )
    latest_record: str | None = Field(
        None, description="最晚记录的 created_at ISO 8601 字符串，空表时为 null"
    )
    status_breakdown: list[StorageStatusBucketDoc] = Field(
        default_factory=list, description="按状态码分组计数，状态码升序"
    )
    daily_breakdown: list[StorageDailyBucketDoc] = Field(
        default_factory=list, description="最近 7 天的逐日统计，日期升序"
    )
    queried_at: str = Field(
        ..., description="查询时刻（handler 在返回前再取一次当前 UTC 时间的 isoformat 字符串）"
    )


class SlowRequestItemDoc(BaseModel):
    """``GET /api/admin/performance/slow`` 数组里的单条最慢请求记录。"""

    id: int = Field(..., description="performance_metrics 主键")
    endpoint: str = Field(..., description="请求路径（原始登记的 path）")
    method: str = Field(..., description="HTTP 方法（GET/POST/…）")
    status_code: int = Field(..., description="响应状态码")
    response_time_ms: int = Field(..., description="响应耗时毫秒；数组整体按此字段降序")
    user_agent: str | None = Field(None, description="原始 User-Agent，缺失为 null")
    ip: str | None = Field(None, description="客户端 IP，缺失为 null")
    created_at: str | None = Field(
        None, description="记录时刻 ISO 8601 字符串；行内时间为空时为 null"
    )


async def _stats_for_period(db: DB, since: datetime) -> dict[str, Any]:
    """计算指定时间点之后的性能统计"""
    # 基础统计
    result = await db.execute(
        select(
            func.count().label("total_requests"),
            func.avg(PerformanceMetric.response_time_ms).label("avg_response_time"),
            func.max(PerformanceMetric.response_time_ms).label("max_response_time"),
        ).where(PerformanceMetric.created_at >= since)
    )
    row = result.one()
    total_requests = int(row.total_requests or 0)
    avg_response_time = float(row.avg_response_time or 0)
    max_response_time = int(row.max_response_time or 0)

    # 错误率：状态码 >= 400
    error_result = await db.execute(
        select(func.count())
        .select_from(PerformanceMetric)
        .where(
            PerformanceMetric.created_at >= since,
            PerformanceMetric.status_code >= 400,
        )
    )
    error_count = int(error_result.scalar() or 0)
    error_rate = (error_count / total_requests * 100) if total_requests > 0 else 0

    # P95 / P99：按响应时间升序取分位数
    times_result = await db.execute(
        select(PerformanceMetric.response_time_ms)
        .where(PerformanceMetric.created_at >= since)
        .order_by(PerformanceMetric.response_time_ms.asc())
    )
    times = [t[0] for t in times_result.all()]
    if times:
        p95_idx = min(int(len(times) * 0.95), len(times) - 1)
        p99_idx = min(int(len(times) * 0.99), len(times) - 1)
        p95 = int(times[p95_idx])
        p99 = int(times[p99_idx])
    else:
        p95 = 0
        p99 = 0

    # 热门慢接口（按平均响应时间倒序 top 5）
    slow_result = await db.execute(
        select(
            PerformanceMetric.endpoint,
            PerformanceMetric.method,
            func.avg(PerformanceMetric.response_time_ms).label("avg_time"),
            func.count().label("cnt"),
        )
        .where(PerformanceMetric.created_at >= since)
        .group_by(PerformanceMetric.endpoint, PerformanceMetric.method)
        .order_by(desc("avg_time"))
        .limit(5)
    )
    slow_endpoints = [
        {
            "endpoint": r.endpoint,
            "method": r.method,
            "avg_response_time_ms": round(float(r.avg_time or 0), 2),
            "request_count": int(r.cnt or 0),
        }
        for r in slow_result.all()
    ]

    return {
        "total_requests": total_requests,
        "avg_response_time_ms": round(avg_response_time, 2),
        "max_response_time_ms": max_response_time,
        "p95_response_time_ms": p95,
        "p99_response_time_ms": p99,
        "error_count": error_count,
        "error_rate": round(error_rate, 2),
        "slow_endpoints": slow_endpoints,
    }


@router.get(
    "/performance/summary",
    summary="性能统计摘要",
    description=(
        "返回最近 24 小时和 7 天的性能统计：平均响应时间、P95/P99、错误率、热门慢接口。"
        "需 CurrentStaff。响应为裸 dict（last_24h/last_7d/timestamp，无信封），"
        "两个窗口由同一段统计逻辑分别计算，结构完全一致。"
    ),
    responses={200: {"model": PerformanceSummaryResponseDoc}},
)
async def get_performance_summary(
    db: DB,
    current_user: CurrentStaff,
):
    """获取性能统计摘要"""
    now = datetime.now(UTC)
    last_24h = now - timedelta(hours=24)
    last_7d = now - timedelta(days=7)

    return {
        "last_24h": await _stats_for_period(db, last_24h),
        "last_7d": await _stats_for_period(db, last_7d),
        "timestamp": now.isoformat(),
    }


@router.get(
    "/performance/slow",
    summary="最慢的请求",
    description="返回最近 7 天内最慢的 20 个请求记录。",
    responses={200: {"model": list[SlowRequestItemDoc]}},
)
async def get_slow_requests(
    db: DB,
    current_user: CurrentStaff,
    limit: int = Query(20, ge=1, le=100, description="返回数量"),
):
    """获取最慢的请求"""
    since = datetime.now(UTC) - timedelta(days=7)
    result = await db.execute(
        select(PerformanceMetric)
        .where(PerformanceMetric.created_at >= since)
        .order_by(PerformanceMetric.response_time_ms.desc())
        .limit(limit)
    )
    items = result.scalars().all()
    return [
        {
            "id": m.id,
            "endpoint": m.endpoint,
            "method": m.method,
            "status_code": m.status_code,
            "response_time_ms": m.response_time_ms,
            "user_agent": m.user_agent,
            "ip": m.ip,
            "created_at": m.created_at.isoformat() if m.created_at else None,
        }
        for m in items
    ]


@router.get(
    "/performance/storage",
    summary="性能数据存储统计",
    description=(
        "返回性能监控表的数据量、时间范围及按状态码分组的统计，便于评估是否需要清理。"
        "需 CurrentStaff。响应为裸 dict（total_count/earliest_record/latest_record/"
        "status_breakdown/daily_breakdown/queried_at，无信封）；空表时两条时间边界为 null。"
    ),
    responses={200: {"model": PerformanceStorageResponseDoc}},
)
async def get_performance_storage(
    db: DB,
    current_user: CurrentStaff,
):
    """获取性能监控数据存储统计"""
    # 总条数
    total_result = await db.execute(select(func.count()).select_from(PerformanceMetric))
    total_count = int(total_result.scalar() or 0)

    # 时间范围
    range_result = await db.execute(
        select(
            func.min(PerformanceMetric.created_at).label("earliest"),
            func.max(PerformanceMetric.created_at).label("latest"),
        )
    )
    row = range_result.one()
    earliest = row.earliest
    latest = row.latest

    # 按状态码分组
    status_result = await db.execute(
        select(
            PerformanceMetric.status_code,
            func.count().label("cnt"),
        )
        .group_by(PerformanceMetric.status_code)
        .order_by(PerformanceMetric.status_code)
    )
    status_breakdown = [
        {"status_code": r.status_code, "count": int(r.cnt or 0)} for r in status_result.all()
    ]

    # 按日期分组（最近 7 天）- 兼容 PostgreSQL 和 SQLite
    seven_days_ago = datetime.now(UTC) - timedelta(days=7)
    all_recent_result = await db.execute(
        select(
            PerformanceMetric.created_at,
            PerformanceMetric.response_time_ms,
        ).where(PerformanceMetric.created_at >= seven_days_ago)
    )
    # 在 Python 侧按日期分组，避免数据库方言差异
    daily_map: dict[str, list[int]] = {}
    for created_at, response_time in all_recent_result.all():
        if created_at is None:
            continue
        day_key = created_at.strftime("%Y-%m-%d")
        if day_key not in daily_map:
            daily_map[day_key] = []
        if response_time is not None:
            daily_map[day_key].append(int(response_time))

    daily_breakdown = []
    for day_key in sorted(daily_map.keys()):
        times = daily_map[day_key]
        avg_time = sum(times) / len(times) if times else 0
        daily_breakdown.append(
            {
                "date": day_key,
                "count": len(times),
                "avg_response_time_ms": round(avg_time, 2),
            }
        )

    return {
        "total_count": total_count,
        "earliest_record": earliest.isoformat() if earliest else None,
        "latest_record": latest.isoformat() if latest else None,
        "status_breakdown": status_breakdown,
        "daily_breakdown": daily_breakdown,
        "queried_at": datetime.now(UTC).isoformat(),
    }


class CleanupResult(BaseModel):
    """清理结果"""

    success: bool
    deleted_count: int
    cutoff_date: str
    remaining_count: int


@router.delete(
    "/performance/cleanup",
    response_model=CleanupResult,
    summary="清理性能监控旧数据",
    description="删除指定天数之前的性能监控记录，避免表无限增长。",
)
async def cleanup_performance_data(
    db: DB,
    current_user: CurrentStaff,
    days: int = Query(30, ge=1, le=365, description="保留最近 N 天的数据，更早的将被删除"),
) -> CleanupResult:
    """清理性能监控旧数据"""
    cutoff = datetime.now(UTC) - timedelta(days=days)

    # 先统计将被删除的数量
    count_result = await db.execute(
        select(func.count())
        .select_from(PerformanceMetric)
        .where(PerformanceMetric.created_at < cutoff)
    )
    to_delete = int(count_result.scalar() or 0)

    # 执行删除
    if to_delete > 0:
        await db.execute(delete(PerformanceMetric).where(PerformanceMetric.created_at < cutoff))
        await db.flush()

    # 统计剩余数量
    remaining_result = await db.execute(select(func.count()).select_from(PerformanceMetric))
    remaining = int(remaining_result.scalar() or 0)

    return CleanupResult(
        success=True,
        deleted_count=to_delete,
        cutoff_date=cutoff.isoformat(),
        remaining_count=remaining,
    )
