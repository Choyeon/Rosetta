"""缓存击穿锁不可用时必须"降级为直接回源"，而不是把一次正常的读打成 500。

``get_or_set`` 的分布式锁是**性能护栏**（防击穿），不是安全门禁，所以两种
"拿不到锁"都必须 fail open：

1. ``REDIS_ENABLED=true`` 但 Redis 没起来 / 抖动（内存后端同样是有效缓存，
   单机部署这是合法形态）；
2. 锁竞争超过 ``wait_timeout`` → ``lock_manager.lock()`` 抛 ``TimeoutError``。

修前实测：Redis 不可达时 ``GET /api/users/me/preferences`` 稳定 500——异常从
``distributed_lock.acquire`` 里的 ``redis.set`` 一路冒到 HTTP 层，缓存后端故障
被放大成整站业务接口不可用。同一条请求路径还覆盖了所有走 ``get_or_set`` 的
公开页读接口。

注：本仓 venv 是 Python 3.10，`asyncio.TimeoutError` 与内建 `TimeoutError`
**不是同一个类**（3.11 才合并），所以捕获集合必须两者都含。
"""

from __future__ import annotations

from contextlib import asynccontextmanager

import pytest

from backend.core import cache_v2
from backend.core.cache_v2 import TwoLevelCache
from backend.core.config import settings


def _lock_that_raises(exc: BaseException):
    """构造一个 __aenter__ 直接抛错的 distributed_lock 替身。"""

    @asynccontextmanager
    async def _fake_lock(*args, **kwargs):
        raise exc
        yield  # pragma: no cover

    return _fake_lock


@pytest.fixture
def cache() -> TwoLevelCache:
    return TwoLevelCache()


@pytest.mark.asyncio
async def test_lock_timeout_degrades_to_direct_fetch(
    cache: TwoLevelCache,
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.setattr(settings, "redis_enabled", True)
    calls = []

    async def fetch():
        calls.append(1)
        return {"value": 42}

    monkeypatch.setattr(cache_v2, "distributed_lock", _lock_that_raises(TimeoutError("获取锁超时")))

    result = await cache.get_or_set("guard:lock-timeout", fetch, ttl=60)

    assert result == {"value": 42}, "锁竞争超时被冒泡成业务失败"
    assert len(calls) == 1


@pytest.mark.asyncio
async def test_redis_unreachable_degrades_to_direct_fetch(
    cache: TwoLevelCache,
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.setattr(settings, "redis_enabled", True)
    calls = []

    async def fetch():
        calls.append(1)
        return ["ok"]

    monkeypatch.setattr(
        cache_v2,
        "distributed_lock",
        _lock_that_raises(ConnectionRefusedError(1225, "远程计算机拒绝网络连接")),
    )

    result = await cache.get_or_set("guard:lock-refused", fetch, ttl=60)

    assert result == ["ok"]
    assert len(calls) == 1


@pytest.mark.asyncio
async def test_degraded_fetch_still_populates_cache(
    cache: TwoLevelCache,
    monkeypatch: pytest.MonkeyPatch,
):
    """降级只该去掉锁，不该顺带把写缓存也跳过——否则退化成每次回源。"""
    monkeypatch.setattr(settings, "redis_enabled", True)
    calls = []

    async def fetch():
        calls.append(1)
        return {"n": 1}

    monkeypatch.setattr(cache_v2, "distributed_lock", _lock_that_raises(TimeoutError("获取锁超时")))
    key = "guard:lock-refill"
    await cache.delete(key)

    assert await cache.get_or_set(key, fetch, ttl=600) == {"n": 1}

    # 锁恢复正常后，第二次读应命中缓存，不再回源
    @asynccontextmanager
    async def _ok_lock(*args, **kwargs):
        yield object()

    monkeypatch.setattr(cache_v2, "distributed_lock", _ok_lock)
    assert await cache.get_or_set(key, fetch, ttl=600) == {"n": 1}
    assert calls == [1], "降级路径未写缓存，锁恢复后仍在回源"

    await cache.delete(key)


@pytest.mark.asyncio
async def test_programming_errors_are_not_swallowed(
    cache: TwoLevelCache,
    monkeypatch: pytest.MonkeyPatch,
):
    """只放行"锁拿不到"这一类；锁内部暴露的编码错误必须外抛，不得伪装成缓存抖动。"""
    monkeypatch.setattr(settings, "redis_enabled", True)

    async def fetch():
        return {"n": 1}

    monkeypatch.setattr(
        cache_v2,
        "distributed_lock",
        _lock_that_raises(RuntimeError("分布式锁必须在事件循环外使用")),
    )

    with pytest.raises(RuntimeError):
        await cache.get_or_set("guard:lock-raise", fetch, ttl=60)
