"""日志保留期自动清理（backend/services/log_retention.py）的行为守卫。

背景：``visit_logs`` / ``performance_metrics`` / ``operation_logs`` 是只增表，
开发库实测 64.5 万 / 6.7 万行，而清理**只有**两个手动端点
（``DELETE /api/admin/logs/retention``、``DELETE /api/admin/performance/cleanup``）——
没人点就永远不清。现在由 lifespan 后台循环按 ``settings.log_retention_days`` 自动收敛。

这里钉住三件容易写错的事：
1. 只删过期行，保留期内的行必须一条都不动（误删用户数据是最高优先级风险）；
2. 分批删除要真正排空（只跑一批的话，几十万行永远删不完）；
3. 后台循环**先睡后删**，且取消时干净退出（短生命周期进程不得误删数据）。
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timedelta

import pytest
from sqlalchemy import func, select

from backend.models.log import OperationLog
from backend.models.monitoring import VisitLog
from backend.models.performance_metric import PerformanceMetric
from backend.services import log_retention
from backend.utils.compat import UTC

_NOW = datetime(2026, 9, 27, 12, 0, 0, tzinfo=UTC)


def _ago(days: int) -> datetime:
    return _NOW - timedelta(days=days)


def _visit(path: str, when: datetime) -> VisitLog:
    return VisitLog(path=path, method="GET", status_code=200, response_time_ms=1, created_at=when)


def _metric(when: datetime) -> PerformanceMetric:
    return PerformanceMetric(
        endpoint="/api/blog/posts",
        method="GET",
        status_code=200,
        response_time_ms=12,
        created_at=when,
    )


def _oplog(when: datetime) -> OperationLog:
    return OperationLog(
        action="delete",
        resource_type="post",
        resource_id=1,
        status="success",
        created_at=when,
    )


async def _count(db, model) -> int:
    return await db.scalar(select(func.count()).select_from(model)) or 0


@pytest.mark.asyncio
async def test_prune_removes_only_expired_rows(db_session):
    """过期行删掉、保留期内一行都不能少。"""
    db_session.add_all(
        [
            _visit("/old-a", _ago(40)),
            _visit("/old-b", _ago(8)),
            _visit("/fresh", _ago(1)),
            _metric(_ago(30)),
            _metric(_ago(2)),
            _oplog(_ago(9)),
            _oplog(_ago(3)),
        ]
    )
    await db_session.commit()

    deleted = await log_retention.prune_expired_logs(db_session, days=7, now=_NOW)

    assert deleted == {
        "visit_logs": 2,
        "performance_metrics": 1,
        "operation_logs": 1,
    }
    assert await _count(db_session, VisitLog) == 1
    assert await _count(db_session, PerformanceMetric) == 1
    assert await _count(db_session, OperationLog) == 1

    # 留下的必须正好是保留期内的那些（而不是"碰巧删了两条"）
    kept_paths = (await db_session.execute(select(VisitLog.path))).scalars().all()
    assert list(kept_paths) == ["/fresh"]


@pytest.mark.asyncio
async def test_prune_drains_every_batch(db_session):
    """单批装不下时必须继续排空，而不是删一批就收工。"""
    db_session.add_all([_visit(f"/old-{i}", _ago(20)) for i in range(12)])
    db_session.add(_visit("/fresh", _ago(1)))
    await db_session.commit()

    deleted = await log_retention.prune_expired_logs(db_session, days=7, now=_NOW, batch_size=5)

    # 12 条过期 = 5 + 5 + 2 三批；只跑一批的话这里会是 5
    assert deleted["visit_logs"] == 12
    assert await _count(db_session, VisitLog) == 1


@pytest.mark.asyncio
async def test_prune_defaults_to_configured_window(db_session, monkeypatch):
    """不传 days 时按 settings.log_retention_days 取窗口。"""
    monkeypatch.setattr(log_retention.settings, "log_retention_days", 7)
    db_session.add_all([_visit("/just-outside", _ago(8)), _visit("/just-inside", _ago(6))])
    await db_session.commit()

    deleted = await log_retention.prune_expired_logs(db_session, now=_NOW)

    assert deleted["visit_logs"] == 1
    remaining = (await db_session.execute(select(VisitLog.path))).scalars().all()
    assert list(remaining) == ["/just-inside"]


@pytest.mark.asyncio
async def test_retention_loop_prunes_repeatedly_and_survives_failure(monkeypatch):
    """循环要能持续跑下去：一次清理失败不能让后台任务静默退出。"""
    attempts: list[int] = []

    async def _flaky_prune(_session):
        attempts.append(len(attempts))
        if not attempts:
            raise RuntimeError("DB 连接抖动")

    class _FakeSession:
        async def __aenter__(self):
            return object()

        async def __aexit__(self, *exc):
            return False

    monkeypatch.setattr(log_retention, "retention_loop_interval_seconds", lambda: 0.01)
    monkeypatch.setattr(log_retention, "prune_expired_logs", _flaky_prune)

    from backend.main import _log_retention_loop

    task = asyncio.create_task(_log_retention_loop(lambda: _FakeSession()))
    await asyncio.sleep(0.2)

    assert task.done() is False, "后台循环因一次清理失败就退出了"
    assert len(attempts) >= 2, f"清理未持续执行（只尝试 {len(attempts)} 次）"

    task.cancel()
    # 循环内部吞掉 CancelledError 后 break，因此 await 不应再抛
    await task


def test_first_sweep_is_delayed():
    """扫描间隔必须 ≥ 1 小时：进程刚启动就删数据，短生命周期进程（含测试）会误删。"""
    assert log_retention.settings.log_retention_interval_hours >= 1
    assert log_retention.retention_loop_interval_seconds() == (
        log_retention.settings.log_retention_interval_hours * 3600
    )
