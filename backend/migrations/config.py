"""
迁移工具配置

自动检测项目结构，零配置使用。
"""

import asyncio
import os
from pathlib import Path

from alembic.config import Config

PROJECT_ROOT = Path(__file__).parent.parent.parent
MIGRATIONS_DIR = Path(__file__).parent


def get_alembic_config() -> Config:
    """获取 Alembic 配置，自动检测数据库连接"""
    config = Config()

    config.set_main_option("script_location", str(MIGRATIONS_DIR))
    config.set_main_option("version_locations", str(MIGRATIONS_DIR / "versions"))

    migrations_dir = MIGRATIONS_DIR / "versions"
    migrations_dir.mkdir(parents=True, exist_ok=True)

    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        try:
            from backend.core.config import settings

            database_url = settings.database_url
        except ImportError:
            database_url = "sqlite+aiosqlite:///./rosetta.db"

    if database_url.startswith("postgresql://"):
        database_url = database_url.replace("postgresql://", "postgresql+asyncpg://")

    config.set_main_option("sqlalchemy.url", database_url)

    return config


def get_async_engine():
    """获取异步数据库引擎"""
    from backend.core.database import engine

    return engine


def get_metadata():
    """获取模型元数据"""
    from backend.core.database import Base

    return Base.metadata


def run_async(coro):
    """运行异步函数"""
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None

    if loop and loop.is_running():
        import concurrent.futures

        with concurrent.futures.ThreadPoolExecutor() as executor:
            future = executor.submit(asyncio.run, coro)
            return future.result()
    else:
        return asyncio.run(coro)
