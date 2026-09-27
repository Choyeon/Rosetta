"""顺序执行一组数据库查询协程。

名字里的 "concurrent" 是历史遗留。本模块最初真的用 ``asyncio.gather`` 并行跑，
但 SQLAlchemy 的 ``AsyncSession`` **不是并发安全的**：同一会话上并发执行会踩到
greenlet 重入 / "Session is already flushing" 一类的随机故障。因此现在明确按顺序
``await``——调用方得到的是"一条语句写完多个查询"的简洁，而不是并行加速。
需要真并行请为每个查询各开一个会话，不要在共享会话上 gather。

原先同文件里的 ``QueryBatch`` / ``ConcurrentQueryExecutor`` / ``execute_concurrent``
等约 330 行全仓库零引用，且 ``execute_batch`` 正是拿 ``asyncio.gather`` 跑共享会话的
危险实现——留着只会被"这个工具看起来很专业"的后来者误用，故整体删除。
"""

from collections.abc import Coroutine
from typing import Any


async def concurrent_query(*coroutines: Coroutine[Any, Any, Any]) -> list[Any]:
    """按顺序 await 多个协程，返回结果列表（顺序与入参一致）。

    异常照常抛出，不做静默降级；发生异常时把尚未执行的协程 ``close()``，
    避免"coroutine was never awaited" 警告淹没真正的报错。
    """
    pending = list(coroutines)
    results: list[Any] = []
    try:
        for coro in pending:
            results.append(await coro)
        return results
    finally:
        for coro in pending[len(results) :]:
            coro.close()
