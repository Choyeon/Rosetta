"""生产限流后端启动门禁回归（审查 P1-7）。

修复前：`cache.backend` 惰性绑定 + Redis 连不上只打一条 warning，服务照常对外，
多 worker 下每个进程各算各的内存限流桶、重启即清零，登录/注册限流实际失效，
而运维在日志里完全看不出这件事。

现在 `main.py::lifespan` 在 `init_db()` 之后主动探测一次：
- 非生产跳过；
- 生产且 Redis 已连通 → 放行；
- 生产但未连通 → `RATE_LIMIT_REQUIRE_REDIS=true` 时拒绝启动，否则打 error 级告警。

本文件不打真实 Redis，用可注入的 stub 覆盖 `cache._backend` 验证四条分支。
"""

import logging

import pytest

from backend.core.cache import cache
from backend.core.config import settings
from backend.core.rate_limit import assert_rate_limit_backend_ready


class _RedisStub:
    """只实现门禁需要的两个成员，避免碰真实网络。"""

    def __init__(self, connected: bool):
        self._connected = connected

    async def _get_client(self):
        return object() if self._connected else None


class _MemoryStub:
    """未启用 Redis 时的内存后端：没有 _get_client。"""


@pytest.fixture
def _production(monkeypatch):
    monkeypatch.setattr(settings, "environment", "production")
    monkeypatch.setattr(settings, "redis_enabled", True)
    monkeypatch.setattr(settings, "rate_limit_require_redis", True)


@pytest.mark.asyncio
async def test_non_production_skips_the_probe(monkeypatch):
    """本地开发允许内存态，绝不因为没 Redis 就起不来。"""
    monkeypatch.setattr(settings, "environment", "development")
    monkeypatch.setattr(settings, "redis_enabled", True)
    monkeypatch.setattr(settings, "rate_limit_require_redis", True)
    monkeypatch.setattr(cache, "_backend", _RedisStub(connected=False))

    # 不抛异常即通过；顺带钉住"非生产不探测"，否则下面的 stub 会被调用
    await assert_rate_limit_backend_ready()


@pytest.mark.asyncio
async def test_production_with_connected_redis_passes(monkeypatch, _production):
    monkeypatch.setattr(cache, "_backend", _RedisStub(connected=True))
    await assert_rate_limit_backend_ready()


@pytest.mark.asyncio
async def test_production_redis_down_and_required_refuses_start(monkeypatch, _production):
    monkeypatch.setattr(cache, "_backend", _RedisStub(connected=False))
    with pytest.raises(RuntimeError, match="拒绝以降级态启动"):
        await assert_rate_limit_backend_ready()


@pytest.mark.asyncio
async def test_production_redis_not_enabled_but_required_refuses_start(monkeypatch, _production):
    """声明强制却压根没启用 Redis：内存后端同样不能算"生产限流就绪"。"""
    monkeypatch.setattr(settings, "redis_enabled", False)
    monkeypatch.setattr(cache, "_backend", _MemoryStub())
    with pytest.raises(RuntimeError, match="Redis 未启用"):
        await assert_rate_limit_backend_ready()


@pytest.mark.asyncio
async def test_legacy_production_deploy_is_allowed_but_loud(monkeypatch, _production, caplog):
    """存量部署（开关未开）保持兼容，但降级必须留下 error 级痕迹，不再静默。"""
    monkeypatch.setattr(settings, "rate_limit_require_redis", False)
    monkeypatch.setattr(cache, "_backend", _RedisStub(connected=False))
    with caplog.at_level(logging.ERROR, logger="backend.core.rate_limit"):
        await assert_rate_limit_backend_ready()
    assert any("限流后端不可用" in r.getMessage() for r in caplog.records), (
        "降级必须打 error 级告警，否则运维无从察觉限流已失效"
    )
