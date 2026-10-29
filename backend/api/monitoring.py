"""
监控和性能统计 API

提供系统监控、性能指标、访问统计等功能。
"""

import asyncio
import hmac
import logging
import math
import time
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from fastapi import APIRouter, Header, HTTPException, Query, Request
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import desc, func, select

from backend.core.auth import DB, CurrentStaff, decode_token
from backend.core.cache import cache, make_cache_key
from backend.core.config import settings
from backend.core.database import engine
from backend.core.rate_limit import get_client_ip, is_internal_request
from backend.core.setup_system import psutil_errors
from backend.utils.compat import UTC, timedelta
from backend.utils.user_agent import parse_user_agent

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


class VisitRecordOut(BaseModel):
    """一条完整访客记录：原始字段 + UA 现算出来的系统/浏览器/设备标签。"""

    id: int = Field(..., description="visit_logs 主键")
    path: str = Field(..., description="请求路径")
    method: str = Field(..., description="HTTP 方法")
    ip: str | None = Field(
        None, description="真实来源 IP（仅在直连对端属于 TRUSTED_PROXY_IPS 时采信 X-Forwarded-For）"
    )
    user_agent: str | None = Field(None, description="原始 UA 字符串（派生标签的判断依据）")
    referer: str | None = Field(None, description="来源页")
    status_code: int = Field(..., description="响应状态码")
    response_time_ms: int = Field(..., description="响应耗时（毫秒）")
    created_at: str = Field(..., description="访问时间（ISO 8601，UTC）")
    user_id: int | None = Field(
        None, description="带 access token 访问时的用户 id；匿名访问为 null"
    )
    username: str | None = Field(
        None, description="对应用户名。令牌有效但用户已删时也是 null，故不等同于「有人登录」"
    )
    cookie_names: str | None = Field(
        None, description="请求携带的 Cookie **名称**列表（分号分隔）。值一律不落库——那是会话凭证"
    )
    accept_language: str | None = Field(None, description="Accept-Language 原文")
    is_bot: bool | None = Field(
        None, description="机器人判定；本列上线前的历史行是 null（未判定），不硬猜"
    )
    os: str = Field(..., description="操作系统（现算）")
    os_version: str = Field(..., description="操作系统版本片段（现算）")
    browser: str = Field(..., description="浏览器（现算）")
    browser_version: str = Field(..., description="浏览器版本（现算）")
    device: str = Field(..., description="设备档位：desktop / mobile / tablet / bot / unknown")
    bot_name: str = Field(..., description="具名抓取引擎；非机器人时为空串")


class VisitRecordsResponse(BaseModel):
    """GET /visits 的响应体（裸对象，无 success 信封，与同族只读口一致）。"""

    items: list[VisitRecordOut] = Field(..., description="当前页记录，按访问时间倒序")
    total: int = Field(..., description="命中筛选条件的总条数（用于分页）")
    page: int = Field(..., description="当前页码，从 1 开始")
    page_size: int = Field(..., description="每页条数")
    days: int = Field(..., description="查询窗口天数")
    unique_ips: int = Field(..., description="同窗口同条件（不含 kind）下的去重来源 IP 数")
    bot_total: int = Field(..., description="同窗口同条件（不含 kind）下判定为机器人的条数")
    retention_days: int = Field(
        ..., description="LOG_RETENTION_DAYS。>0 且小于 days 时本次读数只是下界"
    )
    data_since: str | None = Field(None, description="visit_logs 现存最早一条的 UTC 时间")
    window_truncated: bool = Field(
        ..., description="保留窗口是否已经把请求天数截短（前端据此标注口径，不得当全量读数）"
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

    items: list[_VisitDraft] = []
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
                    path=it.path,
                    method=it.method,
                    ip=it.ip,
                    user_agent=it.user_agent,
                    referer=it.referer,
                    status_code=it.status_code,
                    response_time_ms=it.response_time_ms,
                    created_at=it.created_at,
                    cookie_names=it.cookie_names,
                    accept_language=it.accept_language,
                    user_id=it.user_id,
                    is_bot=it.is_bot,
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


@dataclass
class _VisitDraft:
    """入队的一条访问日志草稿。

    刻意用具名字段而不是位置元组：这张表已经在加列（cookie 名 / Accept-Language /
    is_bot / user_id），按 `it[7]` 这样的下标对齐写库，加一个字段就要重数一遍下标，
    错位的表现是"耗时写进了状态码列"这种安静又难看的脏数据。
    """

    path: str
    method: str
    ip: str | None
    user_agent: str | None
    referer: str | None
    status_code: int
    response_time_ms: int
    created_at: datetime
    cookie_names: str | None = None
    accept_language: str | None = None
    user_id: int | None = None
    is_bot: bool | None = None


def _cookie_names_from_raw(raw: str | None) -> str | None:
    """从任意"分号分隔的 cookie 形态字符串"里只取**名字**。

    两个调用方共用它，所以"值不落库"这条红线只有一份实现：
    * `_cookie_names_of`：真实请求的 Cookie 头（`name=value; name2=value2`）；
    * 边缘上报的 `cookie_names`：Nitro 已经只发名字，这里再过一遍是**防御性重导**——
      即使某个客户端把值一起送过来，切出来的第一段也只剩名字，值不可能落库。

    值是会话凭证，落进只增、会被后台整页列出、还可能被日志备份带走的遥测表里，
    等于把 token 抄送一份给任何能读 visit_logs 的人（含未来的日志导出）。
    名字已经够回答"这个访客带了哪些第三方 cookie"（Cloudflare / GA / 本站语言偏好）。
    """
    if not raw:
        return None
    names: list[str] = []
    for part in raw.split(";"):
        name = part.split("=", 1)[0].strip()
        if name and name not in names:
            names.append(name)
    return ("; ".join(names))[:255] or None


def _cookie_names_of(request: Request) -> str | None:
    """真实请求 Cookie 头里的名字列表（见 `_cookie_names_from_raw`）。"""
    return _cookie_names_from_raw(request.headers.get("cookie"))


def _bearer_user_id(request: Request) -> int | None:
    """从 Authorization 头的 access token 里取用户 id（只解 JWT，不打数据库）。

    遥测路径上不做存在性/封禁校验：这一列只是给后台标注"这条是谁看的"，
    令牌失效或用户已删时最坏是一个查不到昵称的空行，不该为它多一次查询。
    """
    auth = request.headers.get("authorization") or ""
    if not auth[:7].lower() == "bearer ":
        return None
    payload = decode_token(auth[7:].strip())
    if not payload or payload.get("type") != "access":
        return None
    try:
        return int(payload.get("sub") or 0) or None
    except (TypeError, ValueError):
        return None


async def _enqueue_visit_draft(draft: _VisitDraft) -> bool:
    """入队一条访问草稿并保证 flush 循环活着；队列满时丢弃并回 False。

    单列出来是因为现在有两个采集源（后端中间件 + Nitro 边缘上报页面浏览），
    队列懒初始化与 flusher 懒启动这对动作必须在两边同构——漏一半的表现是
    "草稿进了一个没有消费者的队列"，遥测安静地全丢。
    """
    global _visit_queue, _visit_flusher

    if _visit_queue is None:
        _visit_queue = asyncio.Queue(maxsize=_VISIT_QUEUE_MAX)
    try:
        _visit_queue.put_nowait(draft)
    except asyncio.QueueFull:
        return False  # 高峰期丢弃访问日志，保护业务吞吐

    # 懒启动 flush 循环（进程内单例；意外退出后自动重启）
    if _visit_flusher is None or _visit_flusher.done():
        try:
            _visit_flusher = asyncio.create_task(_visit_flush_loop())
        except RuntimeError:
            pass  # 无运行中的事件循环——下次请求再启
    return True


async def record_visit(request: Request, status_code: int, response_time_ms: float):
    """记录访问日志（入队，非阻塞；由后台任务批量落库）。"""
    # 本机服务直连（Nitro SSR 渲染时打 127.0.0.1:8000 取设置/列表、健康探针）不是访客。
    # 它们和真实访客共用这张表时，生产实测 8.4 万条里 8.3 万条的 IP 是 127.0.0.1——
    # 后台"独立 IP"、UV、按 IP 筛人全部读成"整站只有一个本机访客"。
    # 判定要求直连对端在 TRUSTED_PROXY_IPS 内且请求不带转发头，所以未配置该列表时
    # 这里恒为 False（保持旧行为），配置后才真正生效。
    if is_internal_request(request):
        return

    # 真实来源 IP：经 nginx 进来的请求，对端要么是 nginx 递来的 X-Forwarded-For 跳，
    # 要么已被 uvicorn 的 --proxy-headers 改写回访客地址；两种形态都取到同一个 IP。
    # 不采信转发头（且 uvicorn 关闭代理头）时整张表会记成本机回环——去重 IP、UV、
    # 按 IP 筛访客全部退化成 1。get_client_ip 只在直连对端属于 TRUSTED_PROXY_IPS 时
    # 才读 X-Forwarded-For，所以客户端自己伪造 XFF 不会污染这张表。
    peer_ip = get_client_ip(request)
    ua = (request.headers.get("user-agent") or "")[:500] or None
    await _enqueue_visit_draft(
        _VisitDraft(
            path=request.url.path[:500],
            method=request.method,
            ip=None if peer_ip == "unknown" else peer_ip[:50],
            user_agent=ua,
            referer=(request.headers.get("referer") or "")[:500] or None,
            status_code=status_code,
            response_time_ms=int(response_time_ms),
            created_at=datetime.now(UTC),
            cookie_names=_cookie_names_of(request),
            accept_language=(request.headers.get("accept-language") or "")[:100] or None,
            user_id=_bearer_user_id(request),
            is_bot=parse_user_agent(ua).is_bot,
        )
    )


class PageviewReport(BaseModel):
    """Nitro 边缘节点上报的一次页面浏览（HTML 文档请求）。

    为什么必须让边缘上报而不是后端自己记：nginx 只把 `/api` 与 `/media` 转给 FastAPI，
    HTML 页面全部由 Nitro 渲染并直接回给浏览器——后端**从来没见过**这次请求。
    于是 `visit_logs` 实际只是"API 请求明细"：真实访客读一篇文章、爬虫抓一个页面，
    一条都不进表，后台的"独立访客/UV/机器人档位"数出来的只有后台自己与浏览器发出的
    那部分 XHR。批次 #53 的访客记录页要做的是"谁在浏览这个站点"，所以补这一条上报链。

    `cookie_names` 送名字而不是 Cookie 头原文：会话凭证不该为遥测多走一跳。
    后端仍会在落库前重导一次（见 `_cookie_names_from_raw`），万一有客户端把值带上，
    切第一段后也只剩名字——这条红线不依赖调用方的自觉。
    """

    model_config = ConfigDict(extra="forbid")

    path: str = Field(..., min_length=1, max_length=500, description="文档请求的路径（不含域名）")
    method: str = Field("GET", min_length=3, max_length=10, description="HTTP 方法")
    ip: str | None = Field(None, max_length=50, description="边缘看到的访客真实 IP（XFF 第一跳）")
    user_agent: str | None = Field(None, max_length=500, description="原始 User-Agent")
    referer: str | None = Field(None, max_length=500, description="来源页")
    cookie_names: str | None = Field(
        None, max_length=255, description="Cookie **名称**（分号分隔），不含值"
    )
    accept_language: str | None = Field(None, max_length=100, description="Accept-Language 原文")
    status_code: int = Field(..., ge=100, le=599, description="本次文档响应的状态码")
    response_time_ms: int = Field(
        ..., ge=0, le=3_600_000, description="本次文档响应耗时（毫秒，边缘侧量）"
    )


class PageviewReportAck(BaseModel):
    """POST /pageviews 的响应体。"""

    recorded: bool = Field(..., description="是否已进入访问日志队列（队列满时被丢弃仍回 false）")


def _internal_report_secret_ok(presented: str | None) -> bool:
    """边缘上报的共享密钥校验：没配密钥就等于禁用这条链，一律 403。

    复用 `FRONTEND_PURGE_SECRET`（后端）↔ `NUXT_PURGE_SECRET`（Nitro）这一对已经配好的密钥：
    它本来就是"本机前后端互认"的单源，再加一个变量只会多一个"两边不一样就静默失效"的面。
    刻意不给开发环境放宽——本地没配密钥时上报侧本来就会跳过（拿到空串就不发），
    放宽只会让"线上没生效"和"本地在生效"看起来一样。
    """
    expected = (settings.frontend_purge_secret or "").strip()
    if not expected or not presented:
        return False
    return hmac.compare_digest(expected, presented.strip())


@router.post(
    "/pageviews",
    summary="边缘上报页面浏览",
    description=(
        "由 Nitro 服务端在每次 HTML 文档响应后 fire-and-forget 调用（本机直连，不经 nginx）。"
        "鉴权用与页面缓存清除同一条共享密钥（`x-rosetta-purge-secret`），未配置或不匹配一律 403。"
        "写入的是访问日志队列（批量落库、队列满即丢），不触碰业务内容，也不发 webhook。"
        "IP 取边缘看到的 XFF 第一跳：nginx 之外没有人能伪造它。"
    ),
    status_code=202,
    responses={202: {"model": PageviewReportAck, "description": "入队结果"}},
)
async def report_pageview(
    payload: PageviewReport,
    x_rosetta_purge_secret: str | None = Header(default=None, alias="x-rosetta-purge-secret"),
):
    """记录一次页面浏览（visit_logs 的边缘来源写入口）。"""
    if not _internal_report_secret_ok(x_rosetta_purge_secret):
        raise HTTPException(status_code=403, detail="上报密钥无效")

    ip = (payload.ip or "").strip()
    ua = (payload.user_agent or "").strip() or None
    recorded = await _enqueue_visit_draft(
        _VisitDraft(
            path=payload.path[:500],
            method=payload.method.upper()[:10],
            ip=ip[:50] if ip and ip.lower() != "unknown" else None,
            user_agent=ua,
            referer=(payload.referer or "")[:500] or None,
            status_code=payload.status_code,
            response_time_ms=payload.response_time_ms,
            created_at=datetime.now(UTC),
            # 名称在这里重导一次：值进不来这张表，与中间件那条采集路径同一条规则。
            cookie_names=_cookie_names_from_raw(payload.cookie_names),
            accept_language=(payload.accept_language or "")[:100] or None,
            # 页面浏览的归属：这一跳只有文档请求，没有 token，留空由 API 采集那侧标注。
            user_id=None,
            is_bot=parse_user_agent(ua).is_bot,
        )
    )
    return PageviewReportAck(recorded=recorded)


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


def _contains(col, value: str):
    """LIKE 包含匹配，通配符按字面量处理。

    不转义的话，在 IP 输入框里打一个 `%` 就变成"匹配全部"，路径框里的 `_` 会匹配任意
    单字符——筛选条件悄悄失效比筛不出东西更难查（两者都回 200 + 一堆行）。
    """
    escaped = value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    return col.like(f"%{escaped}%", escape="\\")


@router.get(
    "/visits",
    summary="访客记录明细",
    description=(
        "需 CurrentStaff。分页返回 visit_logs 的完整记录：真实来源 IP、原始 UA、按 UA 现算的"
        "系统/浏览器/设备/机器人标签、来源页、Cookie 名称列表（绝不含 Cookie 值）、"
        "Accept-Language、状态码与耗时，并带上访问用户的 id/用户名（按 access token 的 claims 标注，"
        "不查库）。可按窗口、机器人档位、IP、路径、状态码筛选。只读、幂等。"
        "响应带 retention_days / data_since / window_truncated：LOG_RETENTION_DAYS 比请求窗口短时，"
        "本次读数只是下界。"
    ),
    responses={200: {"model": VisitRecordsResponse, "description": "访客记录分页与窗口口径"}},
)
async def get_visit_records(
    db: DB,
    current_user: CurrentStaff,
    days: int = Query(7, ge=1, le=365, description="回看窗口天数"),
    page: int = Query(1, ge=1, description="页码，从 1 开始"),
    page_size: int = Query(50, ge=10, le=200, description="每页条数"),
    kind: str = Query("all", pattern="^(all|human|bot)$", description="机器人档位筛选"),
    ip: str | None = Query(None, max_length=64, description="来源 IP 片段（字面量包含匹配）"),
    path: str | None = Query(None, max_length=200, description="路径片段（字面量包含匹配）"),
    status: int | None = Query(None, ge=100, le=599, description="状态码精确匹配"),
):
    """访客记录明细（UA 派生标签在读取口现算，见 backend/utils/user_agent.py）。"""
    from backend.models.monitoring import VisitLog
    from backend.models.user import User

    now = datetime.now(UTC)
    window_start = now - timedelta(days=days)

    base_filters = [VisitLog.created_at >= window_start]
    if ip:
        base_filters.append(_contains(VisitLog.ip, ip))
    if path:
        base_filters.append(_contains(VisitLog.path, path))
    if status is not None:
        base_filters.append(VisitLog.status_code == status)

    row_filters = list(base_filters)
    if kind == "bot":
        # 用 `.is_()` 而不是 Python 的 `is True`（后者在 SQLAlchemy 列上是恒假的普通比较，
        # 条件静默消失＝"机器人档位筛出全量"），也而不是 `== True`（ruff E712 之外，
        # PG/SQLite 对 `= true` 的布尔字面量支持不一致）。
        # 历史行的 NULL 两档都不该命中，所以两个分支都显式带值比较，不写 `isnot(None)`。
        row_filters.append(VisitLog.is_bot.is_(True))
    elif kind == "human":
        row_filters.append(VisitLog.is_bot.is_(False))

    total = await db.scalar(select(func.count()).select_from(VisitLog).where(*row_filters)) or 0

    rows = (
        (
            await db.execute(
                select(VisitLog)
                .where(*row_filters)
                .order_by(desc(VisitLog.created_at), desc(VisitLog.id))
                .offset((page - 1) * page_size)
                .limit(page_size)
            )
        )
        .scalars()
        .all()
    )

    # 昵称一次批量取（逐行查会在 200 行的页面上打 200 次 SELECT）
    user_ids = {row.user_id for row in rows if row.user_id}
    names: dict[int, str] = {}
    if user_ids:
        for uid, uname in (
            await db.execute(select(User.id, User.username).where(User.id.in_(user_ids)))
        ).all():
            names[uid] = uname

    unique_ips = (
        await db.scalar(
            select(func.count(func.distinct(VisitLog.ip)))
            .select_from(VisitLog)
            .where(*base_filters, VisitLog.ip.isnot(None))
        )
        or 0
    )
    bot_total = (
        await db.scalar(
            select(func.count())
            .select_from(VisitLog)
            .where(*base_filters, VisitLog.is_bot.is_(True))
        )
        or 0
    )
    earliest = await db.scalar(select(func.min(VisitLog.created_at)))
    if earliest is not None and earliest.tzinfo is None:
        earliest = earliest.replace(tzinfo=UTC)

    retention = settings.log_retention_days
    # 保留窗口比请求窗口短 = 老数据已经被删了，读数只是下界（与 /visits/summary 同口径）。
    window_truncated = bool(retention and retention > 0 and retention < days)

    items = []
    for row in rows:
        created = row.created_at
        if created is not None and created.tzinfo is None:
            created = created.replace(tzinfo=UTC)
        info = parse_user_agent(row.user_agent)
        items.append(
            {
                "id": row.id,
                "path": row.path,
                "method": row.method,
                "ip": row.ip,
                "user_agent": row.user_agent,
                "referer": row.referer,
                "status_code": row.status_code,
                "response_time_ms": int(row.response_time_ms or 0),
                "created_at": created.isoformat() if created else "",
                "user_id": row.user_id,
                "username": names.get(row.user_id) if row.user_id else None,
                "cookie_names": row.cookie_names,
                "accept_language": row.accept_language,
                "is_bot": row.is_bot,
                "os": info.os,
                "os_version": info.os_version,
                "browser": info.browser,
                "browser_version": info.browser_version,
                "device": info.device,
                "bot_name": info.bot_name,
            }
        )

    return {
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
        "days": days,
        "unique_ips": unique_ips,
        "bot_total": bot_total,
        "retention_days": retention,
        "data_since": earliest.isoformat() if earliest is not None else None,
        "window_truncated": window_truncated,
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
        "错误率另算：环形缓冲只记耗时不记状态码，无法判错，故 `error_rate` / `error_count` / "
        "`window_requests` 三个键取自 `visit_logs`（同一 period 窗口，`status_code >= 400` 计为错误，"
        "分母为窗口内全部日志条数），口径与 `/performance/summary` 一致，单位是百分数（13.29 即 13.29%）。"
        "只读、幂等。"
    ),
    responses={
        200: {"model": PerformanceLatencyResponse, "description": "延迟分位数与每分钟请求数"}
    },
)
async def get_performance_metrics(
    db: DB,
    current_user: CurrentStaff,
    period: int = Query(60, ge=1, le=1440, description="统计周期（分钟）"),
):
    """获取性能指标"""
    from backend.models.monitoring import VisitLog

    latencies = _metrics.get("request_latency", [])
    timestamps = _metrics_timestamps.get("request_latency", [])

    # 过滤时间范围内的数据
    now = time.time()
    cutoff = now - period * 60

    # 错误率与延迟分位数**不同源**：缓冲里没有状态码，只能回落到访问日志。
    # 这也让进程刚重启（缓冲为空）时错误率仍是真实读数，而不是伪装成 0。
    filtered_latencies = [l for l, t in zip(latencies, timestamps) if t >= cutoff]

    window_start = datetime.now(UTC) - timedelta(minutes=period)
    window_total = (
        await db.scalar(
            select(func.count()).select_from(VisitLog).where(VisitLog.created_at >= window_start)
        )
        or 0
    )
    error_count = (
        await db.scalar(
            select(func.count())
            .select_from(VisitLog)
            .where(VisitLog.created_at >= window_start, VisitLog.status_code >= 400)
        )
        or 0
    )
    error_stats = {
        "error_count": error_count,
        "window_requests": window_total,
        "error_rate": round(error_count / max(window_total, 1) * 100, 2),
    }

    if not filtered_latencies:
        return {
            "avg_latency": 0,
            "p50_latency": 0,
            "p95_latency": 0,
            "p99_latency": 0,
            "requests_per_minute": 0,
            **error_stats,
        }

    # 环形缓冲里存的是秒，读数统一换算成毫秒
    return {
        "avg_latency": round(sum(filtered_latencies) / len(filtered_latencies) * 1000, 2),
        "p50_latency": round(_percentile(filtered_latencies, 50) * 1000, 2),
        "p95_latency": round(_percentile(filtered_latencies, 95) * 1000, 2),
        "p99_latency": round(_percentile(filtered_latencies, 99) * 1000, 2),
        "requests_per_minute": len(filtered_latencies) / period,
        "sample_count": len(filtered_latencies),
        **error_stats,
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
