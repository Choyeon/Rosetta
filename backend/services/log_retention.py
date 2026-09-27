"""只增日志表的保留期清理。

`visit_logs` / `performance_metrics` / `operation_logs` 三张表只写不删，
开发库实测已经涨到 64.5 万 / 6.7 万行。此前只有两个手动端点
（``DELETE /api/admin/logs/retention``、``DELETE /api/admin/performance/cleanup``），
没人点就永远不清理。本模块把同样的裁剪动作提供一个可复用的实现，
由 ``main.py`` 的后台循环按 ``settings.log_retention_days`` 定期调用。

分批删（默认 5000 行/批）是刻意的：首次真实运行要抹掉几十万行，
单条 ``DELETE`` 会在 SQLite 上持有一个很长的写锁，把同时进来的访问请求全堵住。
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.config import settings
from backend.models.log import OperationLog
from backend.models.monitoring import VisitLog
from backend.models.performance_metric import PerformanceMetric
from backend.utils.compat import UTC

logger = logging.getLogger(__name__)

# 每批删除的行数：足够大以免来回折腾，足够小以免长事务锁库
_BATCH_SIZE = 5000

# 表名 -> 模型。循环侧只关心"这三张表都要清"，加表就改这里。
_RETENTION_MODELS: tuple[tuple[str, type], ...] = (
    ("visit_logs", VisitLog),
    ("performance_metrics", PerformanceMetric),
    ("operation_logs", OperationLog),
)


async def prune_expired_logs(
    db: AsyncSession,
    *,
    days: int | None = None,
    now: datetime | None = None,
    batch_size: int = _BATCH_SIZE,
) -> dict[str, int]:
    """删除保留期之外的日志行，返回 ``{表名: 删除行数}``。

    Args:
        db: 复用的异步会话（调用方负责 commit）。
        days: 保留天数，默认取 ``settings.log_retention_days``。
        now: 当前时间，仅测试注入用；默认 UTC now。
        batch_size: 单批删除行数。
    """
    retention_days = days if days is not None else settings.log_retention_days
    cutoff = (now or datetime.now(UTC)) - timedelta(days=retention_days)

    deleted: dict[str, int] = {}
    for table, model in _RETENTION_MODELS:
        total = 0
        while True:
            # 先取 id 再按 id 删：`DELETE ... LIMIT` 只有 MySQL 支持，
            # 这样写在 SQLite / PostgreSQL 上等价且都能吃到 created_at 索引。
            ids = list(
                (
                    await db.execute(
                        select(model.id).where(model.created_at < cutoff).limit(batch_size)
                    )
                )
                .scalars()
                .all()
            )
            if not ids:
                break
            await db.execute(delete(model).where(model.id.in_(ids)))
            total += len(ids)
            if len(ids) < batch_size:
                break
        deleted[table] = total

    await db.commit()

    removed = sum(deleted.values())
    if removed:
        logger.info(
            "[retention] 清理 %s 之前的日志共 %d 行：%s",
            cutoff.isoformat(),
            removed,
            deleted,
        )
    return deleted


def retention_loop_interval_seconds() -> float:
    """后台循环的休眠秒数（读配置，集中一处便于测试注入）。"""
    return settings.log_retention_interval_hours * 3600


__all__ = ["prune_expired_logs", "retention_loop_interval_seconds"]
