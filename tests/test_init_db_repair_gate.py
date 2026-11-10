"""init_db 的逐列扫描补列（_repair_missing_columns）应仅非生产环境执行（P1-13）。

生产环境由 Alembic 独占 DDL，每次启动对 20+ 表 × 10+ 列做 200+ 次元数据查询是浪费；
开发/测试仍保留补列以兼容 SQLite 测试残留与旧 create_all 漂移。
"""

from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from sqlalchemy.ext.asyncio import create_async_engine

import backend.core.database as dbmod


@pytest.mark.asyncio
async def test_init_db_skips_repair_in_production(monkeypatch):
    # 内存 SQLite，避免触碰真实库；create_all 在该连接内完成即可。
    eng = create_async_engine("sqlite+aiosqlite:///:memory:")
    monkeypatch.setattr(dbmod, "engine", eng)

    # 用最小替身替换 settings，只暴露 is_production，避免改动全局配置对象。
    fake_settings = SimpleNamespace(is_production=False)
    monkeypatch.setattr(dbmod, "settings", fake_settings)

    spy = MagicMock()
    monkeypatch.setattr(dbmod, "_repair_missing_columns", spy)

    # 生产环境：不应调用补列扫描
    fake_settings.is_production = True
    await dbmod.init_db()
    spy.assert_not_called()

    # 非生产环境：应调用一次补列扫描
    spy.reset_mock()
    fake_settings.is_production = False
    await dbmod.init_db()
    spy.assert_called_once()

    await eng.dispose()
