"""访问日志内存队列落库（monitoring 批量写）契约

`_flush_visit_queue()` 的返回值同时是后台循环的继续条件：

    while await _flush_visit_queue() > 0: pass

所以"落库失败也返回本批条数"会让一次数据库抖动期间把整个缓冲队列连续取出并丢弃。
本文件钉住：失败返回 0、本批尽量回队、成功才真正写库并返回条数。
"""

import asyncio
from datetime import datetime, timezone

import pytest
from sqlalchemy import select

import backend.api.monitoring as mon
from backend.models.monitoring import VisitLog


def _item(path: str) -> tuple:
    return (
        path,
        "GET",
        "127.0.0.1",
        "pytest-agent",
        None,
        200,
        1.5,
        datetime.now(timezone.utc),
    )


@pytest.fixture
def visit_queue():
    """每个用例独立的内存队列，用例结束后还原模块全局"""
    previous = mon._visit_queue
    mon._visit_queue = asyncio.Queue(maxsize=100)
    yield mon._visit_queue
    mon._visit_queue = previous


@pytest.mark.asyncio
async def test_flush_returns_zero_and_requeues_when_db_fails(visit_queue, monkeypatch):
    class _BoomSession:
        async def __aenter__(self):
            raise RuntimeError("database is unavailable")

        async def __aexit__(self, *exc):
            return False

    monkeypatch.setattr("backend.core.database.async_session_maker", lambda: _BoomSession())

    for path in ("/a", "/b", "/c"):
        await visit_queue.put(_item(path))

    written = await mon._flush_visit_queue()

    assert written == 0, "落库失败必须返回 0，否则外层循环会继续排空整个队列"
    assert visit_queue.qsize() == 3, "失败的批次应尽量回队，而不是整批丢弃"


@pytest.mark.asyncio
async def test_flush_writes_batch_and_drains_queue(visit_queue, db_session):
    await visit_queue.put(_item("/ flushed"))
    await visit_queue.put(_item("/flushed-2"))

    written = await mon._flush_visit_queue()

    assert written == 2
    assert visit_queue.empty()
    rows = (
        (
            await db_session.execute(
                select(VisitLog.path).where(VisitLog.path.in_(["/ flushed", "/flushed-2"]))
            )
        )
        .scalars()
        .all()
    )
    assert sorted(rows) == ["/ flushed", "/flushed-2"]


@pytest.mark.asyncio
async def test_flush_on_empty_queue_is_noop(visit_queue):
    assert await mon._flush_visit_queue() == 0


@pytest.mark.asyncio
async def test_flush_drops_only_when_requeue_overflow(monkeypatch):
    """回队时队列已被并发生产者占满，放不下的部分才允许丢弃"""
    queue: asyncio.Queue = asyncio.Queue(maxsize=4)
    monkeypatch.setattr(mon, "_visit_queue", queue)
    monkeypatch.setattr(mon, "_VISIT_BATCH_SIZE", 4)

    class _BoomSession:
        """模拟落库期间 record_visit 仍在入队，把队列重新占满"""

        async def __aenter__(self):
            for i in range(4):
                queue.put_nowait(_item(f"/busy-{i}"))
            raise RuntimeError("database is unavailable")

        async def __aexit__(self, *exc):
            return False

    monkeypatch.setattr("backend.core.database.async_session_maker", lambda: _BoomSession())

    for i in range(4):
        await queue.put(_item(f"/overflow-{i}"))

    written = await mon._flush_visit_queue()

    assert written == 0
    assert queue.qsize() == 4, "满载时本批无法回队，只保留并发入队的 4 条"
    assert all(item[0].startswith("/busy-") for item in queue._queue), "回队失败的本批不应混写进库"
