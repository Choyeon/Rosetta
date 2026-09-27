"""测试会话隔离守卫。

历史事故：全局 `async_session_maker` 的补丁原先只打在 `client` fixture 里，
只请求 `db_session` 的用例（如 monitoring 批量落库）拿到的仍是真实引擎 ——
测试"通过"的同时把行写进了开发用的 `rosetta.db`。

本文件不测业务，只钉住 conftest 的不变量：**任何持有 `async_session_maker` /
`engine` 的模块都必须指向当前用例的测试引擎**。补丁再被挪走或漏扫时，
这里先红，而不是让数据悄悄落到真实库里。
"""

import sys

from sqlalchemy.ext.asyncio import AsyncEngine

# 顶层导入：模块必须在本文件的 fixture 扫描之前进入 sys.modules，
# 否则"未被覆写"会被误报成"没被扫到"。
import backend.api.monitoring as monitoring  # noqa: E402
from backend.core.database import async_session_maker  # noqa: F401, E402


def _maker_bind(maker):
    """取 sessionmaker 绑定的引擎；取不到返回 None（跳过非会话工厂的同名属性）。"""
    bind = getattr(maker, "bind", None) or getattr(maker, "_bind", None)
    return bind if isinstance(bind, AsyncEngine) else None


def test_every_module_session_maker_points_at_test_engine(db_session, test_engine):
    """所有静态持有 async_session_maker 的模块都被绑到测试引擎。"""
    offenders = []
    for name, mod in list(sys.modules.items()):
        if mod is None:
            continue
        maker = getattr(mod, "async_session_maker", None)
        if not callable(maker):
            continue
        bind = _maker_bind(maker)
        if bind is None or str(bind.url) == str(test_engine.url):
            continue
        offenders.append(name)

    assert not offenders, f"以下模块的 async_session_maker 仍连真实库，会泄漏写入：{offenders}"


def test_direct_engine_users_are_rebound(db_session, test_engine):
    """`monitoring` 这类模块级 `from ... import engine` 的直连路径同样被覆写。"""

    assert monitoring.engine is test_engine, "monitoring.engine 未绑定测试引擎，统计读的是开发库"
