"""`spawn_background` 的两条契约：任务不被 GC 吞掉、异常不会静默。

坑：asyncio 对 Task 只持弱引用，`asyncio.create_task(...)` 的返回值没人接时，
解释器可以在任务跑完前回收它——表现是通知/邮件类 fire-and-forget 静默消失，
而调用点的 `try/except` 只会捕获"提交失败"，捕不到任务内部的异常。
"""

import asyncio
import logging

import pytest

from backend.core import concurrency
from backend.core.concurrency import spawn_background


@pytest.mark.asyncio
async def test_completed_task_releases_its_reference(caplog):
    done = asyncio.Event()

    async def work():
        done.set()

    task = spawn_background(work())
    assert task in concurrency._BACKGROUND_TASKS
    await asyncio.wait_for(done.wait(), timeout=5)
    await task
    # done_callback 在下一轮事件循环里摘除引用
    for _ in range(10):
        if task not in concurrency._BACKGROUND_TASKS:
            break
        await asyncio.sleep(0)
    assert task not in concurrency._BACKGROUND_TASKS
    assert task.exception() is None


@pytest.mark.asyncio
async def test_task_exception_is_logged_not_swallowed(caplog):
    async def boom():
        raise RuntimeError("后台炸了")

    with caplog.at_level(logging.ERROR, logger="backend.core.concurrency"):
        task = spawn_background(boom())
        with pytest.raises(RuntimeError):
            await task
        for _ in range(10):
            if "后台炸了" in caplog.text:
                break
            await asyncio.sleep(0)

    assert "后台炸了" in caplog.text
