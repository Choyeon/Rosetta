"""system_health 打分语义守卫：未知不等于健康，也不等于满分。

回归的三条真实缺陷（修复前实测复现）：
  - DB `SELECT 1` 探活失败时 `db_rtt_ms` 为 None，被当作 0ms 参与扣分，health_score 反而 =100；
  - psutil 未安装 + 无缓存流量 → 所有指标不可观测，依旧得满分；
  - 缓存命中率不参与打分，但前端雷达有"缓存"这一轴，前后端各算一套口径。
"""

from __future__ import annotations

import builtins

import pytest
from sqlalchemy.exc import SQLAlchemyError

from backend.api import stats as stats_mod
from backend.api.stats import (
    _aggregate_score,
    _cache_score,
    _cpu_score,
    _db_score,
    _get_system_health,
    _memory_score,
)


class _FakeDB:
    """探活用的假会话：`reachable=False` 时抛 SQLAlchemyError，否则瞬时返回（RTT≈0）。"""

    def __init__(self, *, reachable: bool = True) -> None:
        self.reachable = reachable

    async def execute(self, *_args, **_kwargs):
        if not self.reachable:
            raise SQLAlchemyError("db down")
        return None


class _ZeroTrafficCache:
    """刚启动、零流量：hit_rate=0.0 表示"还没跑过"，不是"全是 miss"。"""

    async def get_stats(self):
        return {"hits": 0, "misses": 0, "hit_rate": 0.0}


def _block_psutil(monkeypatch: pytest.MonkeyPatch) -> None:
    """让 `import psutil` 失败，等价于"CPU/内存测不到"。"""
    real_import = builtins.__import__

    def _fake_import(name, *args, **kwargs):
        if name == "psutil":
            raise ImportError("psutil blocked")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", _fake_import)


@pytest.mark.parametrize(
    ("raw", "expected"),
    [(None, None), (0.0, 100.0), (70.0, 100.0), (85.0, 70.0), (100.0, 40.0), (130.0, 0.0)],
)
def test_cpu_score_is_linear_after_threshold(raw, expected):
    assert _cpu_score(raw) == expected


@pytest.mark.parametrize(
    ("raw", "expected"), [(None, None), (80.0, 100.0), (90.0, 75.0), (100.0, 50.0), (120.0, 0.0)]
)
def test_memory_score_is_linear_after_threshold(raw, expected):
    assert _memory_score(raw) == expected


@pytest.mark.parametrize(
    ("rtt", "reachable", "expected"),
    [
        (None, True, None),  # 没测到：未知
        (0.0, True, 100.0),
        (250.0, True, 50.0),
        (500.0, True, 0.0),
        (9000.0, True, 0.0),  # 超界钳到 0，不给负分
        (None, False, 0.0),  # 探活异常：直接判 0，不是"未知"
    ],
)
def test_db_score(rtt, reachable, expected):
    assert _db_score(rtt, reachable=reachable) == expected


@pytest.mark.parametrize(
    ("rate", "expected"), [(None, None), (0.0, 0.0), (93.7, 93.7), (120.0, 100.0)]
)
def test_cache_score(rate, expected):
    assert _cache_score(rate) == expected


def test_aggregate_excludes_unobserved_axes():
    """未测到的轴从权重里剔除并归一化：既不虚高也不误伤。"""
    assert (
        _aggregate_score(
            {"cpu": 60.0, "memory": None, "db": 60.0, "cache": None}, db_reachable=True
        )
        == 60
    )
    assert (
        _aggregate_score(
            {"cpu": None, "memory": None, "db": None, "cache": None}, db_reachable=True
        )
        is None
    )
    # DB 不可达是硬故障：其余轴再健康也判 0
    assert (
        _aggregate_score(
            {"cpu": 100.0, "memory": 100.0, "db": 0.0, "cache": 100.0}, db_reachable=False
        )
        == 0
    )


@pytest.mark.asyncio
async def test_db_unreachable_scores_zero(monkeypatch: pytest.MonkeyPatch):
    """核心回归：数据库探活失败必须把总分打到 0，而不是虚报满屏健康。"""
    _block_psutil(monkeypatch)
    monkeypatch.setattr("backend.core.cache.cache", _ZeroTrafficCache())

    health = await _get_system_health(_FakeDB(reachable=False))
    assert health["db_rtt_ms"] is None
    assert health["metric_scores"]["db"] == 0.0
    assert health["health_score"] == 0


@pytest.mark.asyncio
async def test_only_db_observed_still_scores(monkeypatch: pytest.MonkeyPatch):
    """只测到 DB 一轴时按该轴计分，不再凭空给满分。"""
    _block_psutil(monkeypatch)
    monkeypatch.setattr("backend.core.cache.cache", _ZeroTrafficCache())

    health = await _get_system_health(_FakeDB())
    assert health["cpu_percent"] is None
    assert health["memory_percent"] is None
    assert health["cache_hit_percent"] is None
    assert health["metric_scores"]["db"] is not None
    assert health["health_score"] == round(health["metric_scores"]["db"])


@pytest.mark.asyncio
async def test_zero_traffic_cache_is_excluded(monkeypatch: pytest.MonkeyPatch):
    """缓存零流量不能按 0 分计入，否则刚启动的站点会被判"不健康"。"""
    _block_psutil(monkeypatch)
    monkeypatch.setattr("backend.core.cache.cache", _ZeroTrafficCache())

    health = await _get_system_health(_FakeDB())
    assert health["metric_scores"]["cache"] is None
    assert health["health_score"] >= 95


@pytest.mark.asyncio
async def test_metric_scores_cover_every_frontend_axis():
    """前端雷达 4 轴直接消费 metric_scores，键位或权重缺项会退回旧口径。"""
    assert set(stats_mod._HEALTH_WEIGHTS) == {"cache", "cpu", "db", "memory"}
    health = await _get_system_health(_FakeDB())
    assert set(health["metric_scores"]) == set(stats_mod._HEALTH_WEIGHTS)
