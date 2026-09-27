"""
仪表盘 Stats API

GET /api/admin/stats?range=7d|30d

返回：
{
  timeseries: { labels: string[], datasets: [pv, uv, comments, posts, users] },
  top_articles: [...],
  active_commenters: [...],
  system_health: { cpu_percent, memory_percent, db_rtt_ms, cache_hit_percent,
                   health_score, metric_scores: {cpu, memory, db, cache} },
  summary: { total_posts, total_drafts, total_published, total_comments, total_pending_comments,
             total_users, total_views_today, total_comments_today }
}

口径说明：
- pv / uv 与"今日浏览"取自 ``visit_logs``（请求中间件批量落库），与监控面板同源；
- 没有真实数据就返回 0 / 空数组，由前端渲染空状态。**不得**回填演示数据——
  管理员据此做内容决策，假曲线比空曲线危害更大。
"""

from __future__ import annotations

import asyncio
import logging
import time
from datetime import datetime, timedelta

from fastapi import APIRouter, Query
from pydantic import BaseModel, Field
from sqlalchemy import func, select, text
from sqlalchemy.exc import SQLAlchemyError

from backend.core.auth import DB, CurrentStaff
from backend.models.blog import Comment, Post
from backend.models.monitoring import VisitLog
from backend.models.user import User, UserTitle
from backend.schemas.admin_reads import UserTitleBadgeDoc
from backend.utils.compat import UTC

logger = logging.getLogger(__name__)

router = APIRouter(prefix="", tags=["仪表盘"])


# ═══════════════════════════════════════════════════════════════════════════
# 响应体文档模型（仅供 OpenAPI `responses={200: {"model": ...}}` 声明使用，
# 运行时不做序列化过滤——实际响应以 handler 返回字面量为准）
# ═══════════════════════════════════════════════════════════════════════════


class StatsDatasetDoc(BaseModel):
    """时间序列里的单条曲线。"""

    key: str = Field(
        ...,
        description="曲线标识：pv / uv / comments / posts / users 之一（数组顺序固定为这 5 条）",
    )
    values: list[int] = Field(
        default_factory=list, description="逐日计数，长度与 timeseries.labels 一致，无数据日为 0"
    )


class StatsTimeseriesDoc(BaseModel):
    """仪表盘折线图数据。"""

    labels: list[str] = Field(
        default_factory=list, description="日期标签（YYYY-MM-DD），按时间正序，长度等于所选天数"
    )
    datasets: list[StatsDatasetDoc] = Field(default_factory=list, description="5 条统计曲线")


class TopArticleDoc(BaseModel):
    """浏览量 Top 5 文章条目。"""

    id: int = Field(..., description="文章 ID")
    title: str = Field(
        ...,
        description="标题纯文本：JSON 多语言列按 zh → en 取值，皆缺时「Untitled」，非 dict 时 str() 兜底",
    )
    views: int = Field(..., description="累计浏览量")
    comments_count: int = Field(..., description="该文章的评论总数（GROUP BY 批量取，含未过审）")


class ActiveCommenterDoc(BaseModel):
    """活跃评论人 Top 5 条目。"""

    name: str = Field(..., description="显示名：nickname → username → 兜底字符串「User」")
    avatar: str | None = Field(None, description="头像原始 URL，未设置时为空串归一成 null")
    comments_count: int = Field(..., description="该用户的评论条数（含未过审，JOIN 全量计数）")
    title: UserTitleBadgeDoc | None = Field(
        None,
        description="头衔徽章投影（id/name/icon/color；本端点不输出 description），无头衔时为 null",
    )


class HealthMetricScoresDoc(BaseModel):
    """每轴折算后的 0-100 健康分（高=好）；该轴未测到时如实为 null。"""

    cpu: float | None = Field(
        None, description="CPU 轴得分（保留 1 位小数），cpu_percent 未采到时为 null"
    )
    memory: float | None = Field(
        None, description="内存轴得分（保留 1 位小数），memory_percent 未采到时为 null"
    )
    db: float | None = Field(
        None, description="DB 轴得分：按 SELECT 1 往返耗时折算；探活失败直接记 0 分"
    )
    cache: float | None = Field(
        None,
        description="缓存轴得分：等于命中率百分比本身；无命中率计数器或零请求时为 null",
    )


class SystemHealthDoc(BaseModel):
    """系统健康探测（各指标独立降级：探测失败如实为 null，未知 ≠ 健康）。"""

    cpu_percent: float | None = Field(
        None, description="CPU 使用率百分比（保留 1 位小数）；psutil 未安装或采样失败时为 null"
    )
    memory_percent: float | None = Field(
        None, description="内存使用率百分比（保留 1 位小数）；psutil 未安装或采样失败时为 null"
    )
    db_rtt_ms: float | None = Field(
        None, description="SELECT 1 探活往返耗时毫秒（保留 2 位小数），DB 异常时为 null"
    )
    cache_hit_percent: float | None = Field(
        None,
        description="响应缓存命中率百分比（保留 1 位小数）；缓存后端无命中率计数器或零操作时为 null",
    )
    health_score: int | None = Field(
        ...,
        description="0-100 综合健康分：只取「确实测到」的轴按权重求平均；"
        "DB 探活失败直接记 0；一轴都没测到时为 null（未知，不编造分数）",
    )
    metric_scores: HealthMetricScoresDoc = Field(
        ..., description="每轴健康分明细，供雷达/仪表盘直接消费，避免前后端各算一套口径"
    )


class StatsSummaryDoc(BaseModel):
    """仪表盘顶部的 8 个总量/今日计数。"""

    total_posts: int = Field(..., description="文章总数（含草稿）")
    total_drafts: int = Field(..., description="草稿数（status=draft）")
    total_published: int = Field(..., description="已发布数（status=published）")
    total_comments: int = Field(..., description="评论总数（含未过审）")
    total_pending_comments: int = Field(..., description="未过审评论数（active=False）")
    total_users: int = Field(..., description="用户总数")
    total_views_today: int = Field(
        ..., description="今日访问量（visit_logs 今日行数，与 PV 曲线同源，不是 Post.views 总和）"
    )
    total_comments_today: int = Field(..., description="今日新增评论数")


class AdminStatsDataDoc(BaseModel):
    """仪表盘统计的 data 载荷。"""

    timeseries: StatsTimeseriesDoc = Field(..., description="逐日折线数据")
    top_articles: list[TopArticleDoc] = Field(
        default_factory=list, description="浏览量 Top 5（无文章时为空数组）"
    )
    active_commenters: list[ActiveCommenterDoc] = Field(
        default_factory=list, description="评论数 Top 5 用户（无数据时为空数组）"
    )
    system_health: SystemHealthDoc = Field(..., description="系统健康探测")
    summary: StatsSummaryDoc = Field(..., description="总量/今日计数")


class AdminStatsResponse(BaseModel):
    """``GET /api/admin/stats`` 的完整响应体（success/data/message 信封）。"""

    success: bool = Field(True, description="固定为 true（失败走错误信封）")
    data: AdminStatsDataDoc = Field(..., description="统计数据；无真实数据时计数为 0、数组为空")
    message: str = Field("获取仪表盘统计成功", description="人类可读提示")


def _parse_range(range_str: str) -> int:
    if range_str == "30d":
        return 30
    return 7


def _build_labels(days: int) -> list[str]:
    today = datetime.now(UTC).date()
    return [(today - timedelta(days=i)).isoformat() for i in reversed(range(days))]


# 各轴在总分里的权重。DB 权重最高——数据库不可用等于整站不可用。
_HEALTH_WEIGHTS = {"cpu": 0.25, "memory": 0.25, "db": 0.35, "cache": 0.15}


def _clamp(value: float) -> float:
    return max(0.0, min(100.0, value))


def _cpu_score(cpu_percent: float | None) -> float | None:
    """70% 以内满分，满载折到 40 分（单轴不应判死全站）。"""
    if cpu_percent is None:
        return None
    return _clamp(100.0 - max(0.0, cpu_percent - 70.0) / 30.0 * 60.0)


def _memory_score(memory_percent: float | None) -> float | None:
    if memory_percent is None:
        return None
    return _clamp(100.0 - max(0.0, memory_percent - 80.0) / 20.0 * 50.0)


def _db_score(db_rtt_ms: float | None, *, reachable: bool) -> float | None:
    """与前端雷达同口径：0ms=100 分、500ms=0 分；探活异常直接 0 分。"""
    if not reachable:
        return 0.0
    if db_rtt_ms is None:
        return None
    return _clamp(100.0 - min(500.0, max(0.0, db_rtt_ms)) / 500.0 * 100.0)


def _cache_score(cache_hit_percent: float | None) -> float | None:
    if cache_hit_percent is None:
        return None
    return _clamp(cache_hit_percent)


def _aggregate_score(scores: dict[str, float | None], *, db_reachable: bool) -> int | None:
    """各轴健康分 -> 总分。只对被实测到的轴取加权平均，一个都没有则返回 None（未知）。"""
    if not db_reachable:
        return 0
    observed = [(key, value) for key, value in scores.items() if value is not None]
    total_weight = sum(_HEALTH_WEIGHTS[key] for key, _ in observed)
    if total_weight <= 0:
        return None
    score = sum(value * _HEALTH_WEIGHTS[key] for key, value in observed) / total_weight
    return int(round(_clamp(score)))


async def _get_system_health(db: DB):
    """系统健康探针。

    打分原则：**未知 ≠ 健康**。原先缺失指标被当作 0 负载参与扣分，实测
    "psutil 未安装 + DB 探活失败"反而得到 health_score=100（满屏绿色）。
    现在每轴先折算成 0..100 健康分，总分只取"确实测到"的轴的加权平均；
    一轴都测不到时如实返回 None，由前端显示"未知"而不是 0 分或 100 分。
    DB 是唯一例外：探活必然执行，失败即视为 0 分（硬故障）。
    """
    result: dict = {
        "cpu_percent": None,
        "memory_percent": None,
        "db_rtt_ms": None,
        "cache_hit_percent": None,
        "health_score": None,
        # 每轴健康分（高=好），供雷达/仪表直接消费，避免前后端各算一套口径
        "metric_scores": {"cpu": None, "memory": None, "db": None, "cache": None},
    }

    try:
        import psutil as _psutil  # type: ignore
    except ImportError:
        logger.warning("[stats] psutil 未安装，跳过 CPU/Memory 指标")
        _psutil = None

    if _psutil is not None:
        # cpu_percent(interval=0.1) 是阻塞采样：放在事件循环里会占住整个 worker 100ms。
        def _sample() -> tuple[float, float]:
            return (
                float(_psutil.cpu_percent(interval=0.1)),
                float(_psutil.virtual_memory().percent),
            )

        try:
            cpu_percent, memory_percent = await asyncio.to_thread(_sample)
            result["cpu_percent"] = round(cpu_percent, 1)
            result["memory_percent"] = round(memory_percent, 1)
        except Exception:
            logger.debug("[stats] psutil 采样失败", exc_info=True)

    db_reachable = True
    t0 = time.perf_counter()
    try:
        await db.execute(text("SELECT 1"))
        result["db_rtt_ms"] = round((time.perf_counter() - t0) * 1000, 2)
    except SQLAlchemyError as exc:
        # 探活失败如实记为"不可达"（分数直接归零），但必须留痕：
        # 原先连异常类型都不分，DB 驱动换掉 / SQL 写错也一起被当成"数据库不可用"。
        db_reachable = False
        logger.warning("[stats] SELECT 1 探活失败：%s", exc)

    try:
        from backend.core.cache import cache as _cache

        # 命中率来自缓存后端自己的计数器。此前读的是
        # ``cache.hit_count`` / ``cache.miss_count`` 两个**不存在**的属性，
        # getattr 拿到 None 后静默留空——面板上的"缓存命中率"永远是未知。
        stats = await _cache.get_stats()
        hit_rate = stats.get("hit_rate")
        total_ops = int(stats.get("hits") or 0) + int(stats.get("misses") or 0)
        # 零请求时 hit_rate=0.0 是"还没跑过"而不是"全 miss"，不能当成 0 分。
        if isinstance(hit_rate, (int, float)) and total_ops > 0:
            result["cache_hit_percent"] = round(float(hit_rate) * 100.0, 1)
    except (AttributeError, ImportError, TypeError, ValueError) as exc:
        # 命中率是可选指标：后端没这两个计数器就留空。
        logger.debug("[stats] 缓存命中率不可用：%s", exc)

    scores = {
        "cpu": _cpu_score(result["cpu_percent"]),
        "memory": _memory_score(result["memory_percent"]),
        "db": _db_score(result["db_rtt_ms"], reachable=db_reachable),
        "cache": _cache_score(result["cache_hit_percent"]),
    }
    result["metric_scores"] = {
        key: None if value is None else round(value, 1) for key, value in scores.items()
    }
    result["health_score"] = _aggregate_score(scores, db_reachable=db_reachable)
    return result


@router.get(
    "/stats",
    summary="管理后台统计数据",
    description=(
        "获取文章、评论、用户、媒体等模块的统计概览数据。需 CurrentStaff。"
        "range 参数选 7d（默认）或 30d（其它值一律按 7 天处理）。"
        "响应为 success/data/message 信封；没有真实数据时返回 0 / 空数组，"
        "绝不回填演示数据，由前端渲染空状态。"
    ),
    responses={200: {"model": AdminStatsResponse}},
)
async def get_admin_stats(
    db: DB,
    current_user: CurrentStaff,
    time_range: str = Query("7d", alias="range", description="范围：7d|30d"),
):
    days = _parse_range(time_range)
    labels = _build_labels(days)
    label_index = {label: i for i, label in enumerate(labels)}
    today = datetime.now(UTC).date()
    start = datetime.combine(today - timedelta(days=days - 1), datetime.min.time(), tzinfo=UTC)
    today_start = datetime.combine(today, datetime.min.time(), tzinfo=UTC)

    # 同表的条件计数合并为一条查询（SQL FILTER 子句）。
    # 原先每个数字一条 SQL，还把 6 条 SQL 交给 concurrent_query 在**同一个**
    # AsyncSession 上并发跑：SQLAlchemy 的会话不支持并发执行，能跑通只是调度顺序的运气。
    post_counts = (
        await db.execute(
            select(
                func.count().label("total"),
                func.count().filter(Post.status == "draft").label("drafts"),
                func.count().filter(Post.status == "published").label("published"),
            ).select_from(Post)
        )
    ).one()
    comment_counts = (
        await db.execute(
            select(
                func.count().label("total"),
                func.count().filter(Comment.active.is_(False)).label("pending"),
                func.count().filter(Comment.created_at >= today_start).label("today"),
            ).select_from(Comment)
        )
    ).one()
    total_users = await db.scalar(select(func.count()).select_from(User))

    async def _daily_counts(column) -> list[int]:
        """按天统计某张表的 created_at 分布，直接产出一条曲线。"""
        rows = (
            (
                await db.execute(
                    select(func.date(column).label("d"), func.count().label("c"))
                    .where(column >= start)
                    .group_by(func.date(column))
                )
            )
            .mappings()
            .all()
        )
        series = [0] * days
        for r in rows:
            i = label_index.get(str(r["d"]))
            if i is not None:
                series[i] = int(r["c"])
        return series

    # PV / UV 与监控面板同源（visit_logs 由请求中间件批量落库）。
    # 此前 UV 曲线从未被赋过值，却在下面被填成"看着像真的"的假数；
    # PV 取的是 post_view_histories —— 一张只记录登录用户"最近阅读"的去重表，
    # 匿名访客一条都不在里面，作为流量曲线是系统性低估。
    pv_rows = (
        (
            await db.execute(
                select(
                    func.date(VisitLog.created_at).label("d"),
                    func.count().label("pv"),
                    func.count(func.distinct(VisitLog.ip)).label("uv"),
                )
                .where(VisitLog.created_at >= start)
                .group_by(func.date(VisitLog.created_at))
            )
        )
        .mappings()
        .all()
    )
    pv_series = [0] * days
    uv_series = [0] * days
    for r in pv_rows:
        i = label_index.get(str(r["d"]))
        if i is not None:
            pv_series[i] = int(r["pv"])
            uv_series[i] = int(r["uv"])

    # "今日浏览"取今天的真实访问量，不是 Post.views 的历史总和。
    total_views_today = await db.scalar(
        select(func.count()).select_from(VisitLog).where(VisitLog.created_at >= today_start)
    )
    comments_series = await _daily_counts(Comment.created_at)
    posts_series = await _daily_counts(Post.created_at)
    users_series = await _daily_counts(User.created_at)

    top_articles_q = select(Post.id, Post.title, Post.views).order_by(Post.views.desc()).limit(5)
    top_rows = (await db.execute(top_articles_q)).all()
    # 评论数一次 GROUP BY 取回（原先每篇文章再补一条 COUNT）
    comment_count_map: dict[int, int] = {}
    if top_rows:
        cc_rows = await db.execute(
            select(Comment.post_id, func.count(Comment.id))
            .where(Comment.post_id.in_([r.id for r in top_rows]))
            .group_by(Comment.post_id)
        )
        comment_count_map = {int(pid): int(cnt) for pid, cnt in cc_rows.all()}
    top_articles: list[dict] = []
    for r in top_rows:
        title = r.title
        if isinstance(title, dict):
            title_text = title.get("zh") or title.get("en") or "Untitled"
        else:
            title_text = str(title)
        top_articles.append(
            {
                "id": r.id,
                "title": title_text,
                "views": int(r.views or 0),
                "comments_count": comment_count_map.get(r.id, 0),
            }
        )

    act_q = (
        select(
            User.id,
            User.nickname,
            User.username,
            User.avatar,
            User.title_id,
            func.count(Comment.id).label("c"),
        )
        .join(Comment, Comment.user_id == User.id)
        .group_by(User.id)
        .order_by(func.count(Comment.id).desc())
        .limit(5)
    )
    act_rows = (await db.execute(act_q)).all()

    # 批量查询用户头衔
    user_ids = [r.id for r in act_rows]
    title_map: dict[int, dict | None] = {}
    if user_ids:
        titles_q = select(UserTitle).where(
            UserTitle.id.in_([r.title_id for r in act_rows if r.title_id is not None])
        )
        title_rows = (await db.execute(titles_q)).scalars().all()
        title_map = {
            t.id: {"id": t.id, "name": t.name, "icon": t.icon, "color": t.color} for t in title_rows
        }

    active_commenters: list[dict] = []
    for r in act_rows:
        name = r.nickname or r.username or "User"
        title_data = title_map.get(r.title_id) if r.title_id else None
        active_commenters.append(
            {
                "name": name,
                "avatar": r.avatar or None,
                "comments_count": int(r.c),
                "title": title_data,
            }
        )

    system_health = await _get_system_health(db)

    return {
        "success": True,
        "data": {
            "timeseries": {
                "labels": labels,
                "datasets": [
                    {"key": "pv", "values": pv_series},
                    {"key": "uv", "values": uv_series},
                    {"key": "comments", "values": comments_series},
                    {"key": "posts", "values": posts_series},
                    {"key": "users", "values": users_series},
                ],
            },
            "top_articles": top_articles,
            "active_commenters": active_commenters,
            "system_health": system_health,
            "summary": {
                "total_posts": int(post_counts.total or 0),
                "total_drafts": int(post_counts.drafts or 0),
                "total_published": int(post_counts.published or 0),
                "total_comments": int(comment_counts.total or 0),
                "total_pending_comments": int(comment_counts.pending or 0),
                "total_users": int(total_users or 0),
                "total_views_today": int(total_views_today or 0),
                "total_comments_today": int(comment_counts.today or 0),
            },
        },
        "message": "获取仪表盘统计成功",
    }
