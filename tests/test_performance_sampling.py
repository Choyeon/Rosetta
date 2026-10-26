"""
性能采样写入不得阻塞响应链路。

`performance_middleware` 原来的写法是在 `call_next` 之后 `await session.commit()`：
响应要等这一条 INSERT + 一次连接池取还才发出去。10% 采样 + 全部慢请求都会付这份钱，
而慢请求恰恰是最不该被再加一截延迟的那一类。

现在改成 fire-and-forget（有界 in-flight 集合）。这里钉住四件事：
1. 采样命中时中间件**不等**写入完成就返回；
2. 写入最终真的发生（不是"丢掉了"）；
3. 积压超过上限时丢弃本次采样，而不是无限堆任务；
4. 写入失败只记日志，绝不影响响应。
"""

from __future__ import annotations

import asyncio
from types import SimpleNamespace

import pytest

from backend.middleware import performance as perf_mod


def _fake_request(path: str = "/api/probe") -> SimpleNamespace:
    return SimpleNamespace(
        client=SimpleNamespace(host="127.0.0.1"),
        headers={"User-Agent": "pytest-agent"},
        url=SimpleNamespace(path=path),
        method="GET",
    )


def _fake_response(status_code: int = 200) -> SimpleNamespace:
    return SimpleNamespace(status_code=status_code)


@pytest.fixture(autouse=True)
def _clean_inflight():
    perf_mod._inflight.clear()
    yield
    for task in list(perf_mod._inflight):
        task.cancel()
    perf_mod._inflight.clear()


@pytest.mark.asyncio
async def test_sampling_does_not_block_the_response(monkeypatch):
    """采样命中：中间件立刻返回，写入在后台完成。"""
    release = asyncio.Event()
    written: list[dict] = []

    async def _slow_persist(payload: dict) -> None:
        await release.wait()
        written.append(payload)

    monkeypatch.setattr(perf_mod, "_persist", _slow_persist)
    monkeypatch.setattr(perf_mod.random, "random", lambda: 0.0)  # 必然采样
    monkeypatch.setattr("backend.core.deps.is_oobe_complete", lambda: True)

    async def _call_next(_request):
        return _fake_response()

    response = await asyncio.wait_for(
        perf_mod.performance_middleware(_fake_request(), _call_next), timeout=1.0
    )

    assert response.status_code == 200
    assert written == [], "写入仍在请求链路里（响应被 commit 阻塞）"
    assert len(perf_mod._inflight) == 1

    release.set()
    await asyncio.gather(*list(perf_mod._inflight))
    assert len(written) == 1
    assert written[0]["endpoint"] == "/api/probe"
    assert written[0]["method"] == "GET"


@pytest.mark.asyncio
async def test_overflow_drops_sample_instead_of_unbounded_growth(monkeypatch):
    """in-flight 达上限时直接丢弃采样，不再创建任务。"""

    async def _hang(_payload: dict) -> None:
        await asyncio.Event().wait()

    monkeypatch.setattr(perf_mod, "_persist", _hang)
    monkeypatch.setattr(perf_mod.random, "random", lambda: 0.0)
    monkeypatch.setattr("backend.core.deps.is_oobe_complete", lambda: True)

    async def _call_next(_request):
        return _fake_response()

    for _ in range(perf_mod._MAX_INFLIGHT):
        await perf_mod.performance_middleware(_fake_request(), _call_next)
    assert len(perf_mod._inflight) == perf_mod._MAX_INFLIGHT

    await perf_mod.performance_middleware(_fake_request(), _call_next)
    assert len(perf_mod._inflight) == perf_mod._MAX_INFLIGHT, "超出上限仍在新建写入任务"


@pytest.mark.asyncio
async def test_persist_failure_is_swallowed(monkeypatch):
    """写入异常只记 warning，不冒泡到请求链路。"""

    async def _boom(_payload: dict) -> None:
        raise RuntimeError("DB 抖动")

    monkeypatch.setattr(perf_mod, "_persist", _boom)
    monkeypatch.setattr(perf_mod.random, "random", lambda: 0.0)
    monkeypatch.setattr("backend.core.deps.is_oobe_complete", lambda: True)

    async def _call_next(_request):
        return _fake_response(500)

    response = await perf_mod.performance_middleware(_fake_request(), _call_next)
    assert response.status_code == 500
    await asyncio.gather(*list(perf_mod._inflight), return_exceptions=True)
    assert perf_mod._inflight == set()


@pytest.mark.asyncio
async def test_not_sampled_creates_no_task(monkeypatch):
    """未命中采样且不是慢请求时，不应产生任何后台任务。"""
    monkeypatch.setattr(perf_mod.random, "random", lambda: 0.999)  # 永远不采样
    monkeypatch.setattr("backend.core.deps.is_oobe_complete", lambda: True)

    async def _call_next(_request):
        return _fake_response()

    await perf_mod.performance_middleware(_fake_request(), _call_next)
    assert perf_mod._inflight == set()


@pytest.mark.asyncio
async def test_oobe_incomplete_skips_sampling(monkeypatch):
    """OOBE 未完成时数据库还没配好，必须直接跳过（历史行为，别改回去）。"""
    monkeypatch.setattr(perf_mod.random, "random", lambda: 0.0)
    monkeypatch.setattr("backend.core.deps.is_oobe_complete", lambda: False)

    async def _call_next(_request):
        return _fake_response()

    await perf_mod.performance_middleware(_fake_request(), _call_next)
    assert perf_mod._inflight == set()
