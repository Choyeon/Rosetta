"""
Rosetta FastAPI 后端数据库配置

提供异步数据库连接管理，使用 SQLAlchemy 2.0 异步引擎。

环境优化：
- 开发环境 (SQLite): NullPool，无连接池，check_same_thread=False
- 生产环境 (PostgreSQL): AsyncAdaptedQueuePool，连接池，pool_pre_ping，pool_recycle

Example:
    >>> from backend.core.database import get_db, async_session_maker
    >>>
    >>> async with async_session_maker() as session:
    >>>     result = await session.execute(select(User))
    >>>     users = result.scalars().all()
"""

import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from sqlalchemy import event, text
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.pool import AsyncAdaptedQueuePool, NullPool

from backend.core.config import settings

logger = logging.getLogger(__name__)


def create_engine(database_url: str | None = None) -> AsyncEngine:
    """
    创建异步数据库引擎

    根据环境自动选择最优配置：

    开发环境 (SQLite):
        - NullPool: 无连接池，SQLite 不需要
        - check_same_thread=False: 允许多线程访问
        - 外键支持: 启用 PRAGMA foreign_keys

    生产环境 (PostgreSQL):
        - AsyncAdaptedQueuePool: 连接池，提高性能
        - pool_pre_ping: 检查连接有效性
        - pool_recycle: 定期回收连接，防止连接过期
        - SSL 支持: 生产环境安全连接
        - 服务端游标: 大数据集分页优化

    Args:
        database_url: 可选的数据库连接 URL，默认使用 settings.database_url

    Returns:
        AsyncEngine: 异步数据库引擎
    """
    database_url = database_url or settings.database_url

    if database_url.startswith("sqlite"):
        engine = create_async_engine(
            database_url,
            echo=settings.database_echo or settings.debug,
            poolclass=NullPool,
            connect_args={"check_same_thread": False},
        )

        @event.listens_for(engine.sync_engine, "connect")
        def set_sqlite_pragma(dbapi_conn, connection_record):
            """设置 SQLite PRAGMA 选项"""
            cursor = dbapi_conn.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.execute("PRAGMA journal_mode=WAL")
            cursor.execute("PRAGMA synchronous=NORMAL")
            cursor.execute("PRAGMA cache_size=-64000")
            cursor.execute("PRAGMA busy_timeout=5000")
            cursor.close()

        logger.info("SQLite 数据库引擎已创建 (开发模式)")
        return engine

    if database_url.startswith("postgresql"):
        connect_args = {}

        if settings.database_ssl:
            connect_args["ssl"] = "require"

        engine = create_async_engine(
            database_url,
            echo=settings.database_echo,
            poolclass=AsyncAdaptedQueuePool,
            pool_size=settings.database_pool_size,
            max_overflow=settings.database_max_overflow,
            pool_pre_ping=True,
            pool_recycle=3600,
            pool_timeout=30,
            connect_args=connect_args,
            execution_options={
                "isolation_level": "READ COMMITTED",
            },
        )

        logger.info(
            f"PostgreSQL 数据库引擎已创建 "
            f"(连接池: {settings.database_pool_size}, "
            f"最大溢出: {settings.database_max_overflow})"
        )
        return engine

    return create_async_engine(
        database_url,
        echo=settings.database_echo or settings.debug,
        poolclass=AsyncAdaptedQueuePool,
        pool_size=settings.database_pool_size,
        max_overflow=settings.database_max_overflow,
        pool_pre_ping=True,
        pool_recycle=3600,
    )


engine: AsyncEngine = create_engine()


async_session_maker: async_sessionmaker[AsyncSession] = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


def reset_engine(database_url: str | None = None) -> None:
    """
    重置数据库引擎

    用于在运行时切换数据库连接（如 OOBE 阶段写入新的 .env 后）。
    会重新创建全局 engine 和 async_session_maker。

    Args:
        database_url: 新的数据库连接 URL，默认使用当前 settings.database_url
    """
    global engine, async_session_maker

    engine = create_engine(database_url)
    async_session_maker = async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autocommit=False,
        autoflush=False,
    )
    logger.info(f"数据库引擎已重置: {database_url or settings.database_url}")


class Base(DeclarativeBase):
    """
    SQLAlchemy 声明式基类

    所有模型类都应继承此类。

    Example:
        >>> class User(Base):
        >>>     __tablename__ = "users"
        >>>     id: Mapped[int] = mapped_column(primary_key=True)
    """

    pass


async def get_db() -> AsyncGenerator[AsyncSession]:
    """
    获取数据库会话（FastAPI 依赖注入）

    提供自动事务管理的数据库会话：
    - 请求成功：自动提交
    - 请求失败：自动回滚
    - 请求结束：自动关闭

    Yields:
        AsyncSession: 数据库会话

    Example:
        >>> @router.get("/users")
        >>> async def get_users(db: AsyncSession = Depends(get_db)):
        >>>     result = await db.execute(select(User))
        >>>     return result.scalars().all()
    """
    async with async_session_maker() as session:
        try:
            yield session
            await session.commit()
        except Exception as e:
            try:
                await session.rollback()
            except Exception:
                pass
            logger.error(f"Database session error: {e}")
            raise


@asynccontextmanager
async def get_db_context() -> AsyncGenerator[AsyncSession]:
    """
    获取数据库会话（上下文管理器）

    用于非 FastAPI 依赖注入场景，如后台任务、脚本等。

    Yields:
        AsyncSession: 数据库会话

    Example:
        >>> async with get_db_context() as db:
        >>>     result = await db.execute(select(User))
        >>>     users = result.scalars().all()
    """
    async with async_session_maker() as session:
        try:
            yield session
            await session.commit()
        except Exception as e:
            try:
                await session.rollback()
            except Exception:
                pass
            logger.error(f"Database context error: {e}")
            raise


async def init_db() -> None:
    """
    初始化数据库

    创建所有表结构。在生产环境中应使用数据库迁移工具（如 Alembic）。

    额外：对已存在但缺列的表（SQLite 常见，如测试残留的旧文件库）执行 ADD COLUMN，
    避免「no such column: xxx」错误。
    """
    from sqlalchemy import inspect as _sa_inspect
    from sqlalchemy.schema import CreateColumn

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

        def _repair_columns(sync_conn):
            insp = _sa_inspect(sync_conn)
            dialect_name = sync_conn.dialect.name
            for table in Base.metadata.sorted_tables:
                tname = table.name
                try:
                    actual_cols = {c["name"] for c in insp.get_columns(tname)}
                except Exception:
                    actual_cols = set()
                if not actual_cols:
                    continue
                for col in table.columns:
                    if col.name in actual_cols:
                        continue
                    try:
                        stmt = f"ALTER TABLE {tname} ADD COLUMN "
                        compiled = CreateColumn(col).compile(
                            dialect=sync_conn.dialect,
                            compile_kwargs={"literal_binds": True},
                        )
                        stmt += str(compiled).strip()
                        if dialect_name == "sqlite":
                            sync_conn.exec_driver_sql(stmt)
                        else:
                            sync_conn.execute(text(stmt))
                        logger.info(f"init_db 补列 {tname}.{col.name}: {stmt}")
                    except Exception as e:
                        logger.warning(f"init_db 补列失败 {tname}.{col.name}: {e}")
                        try:
                            coltype = col.type.compile(dialect=sync_conn.dialect)
                            nullable = " NULL" if col.nullable else ""
                            default_clause = ""
                            if col.server_default is not None:
                                compiled_default = col.server_default.arg.compile(
                                    dialect=sync_conn.dialect,
                                    compile_kwargs={"literal_binds": True},
                                )
                                default_clause = f" DEFAULT {compiled_default}"
                            stmt2 = f'ALTER TABLE {tname} ADD COLUMN "{col.name}" {coltype}{default_clause}{nullable}'
                            if dialect_name == "sqlite":
                                sync_conn.exec_driver_sql(stmt2)
                            else:
                                sync_conn.execute(text(stmt2))
                            logger.info(f"init_db 补列 fallback {tname}.{col.name}: {stmt2}")
                        except Exception as e2:
                            logger.warning(f"init_db 补列 fallback 失败 {tname}.{col.name}: {e2}")

        await conn.run_sync(_repair_columns)

    logger.info("Database tables created")


async def close_db() -> None:
    """
    关闭数据库连接

    清理数据库连接池，应在应用关闭时调用。
    """
    await engine.dispose()
    logger.info("Database connections closed")


async def check_db_connection() -> bool:
    """
    检查数据库连接是否正常

    Returns:
        bool: 连接正常返回 True，否则返回 False
    """
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        return True
    except Exception as e:
        logger.error(f"Database connection check failed: {e}")
        return False


async def get_db_info() -> dict:
    """
    获取数据库信息

    Returns:
        dict: 数据库类型、版本等信息
    """
    info = {
        "type": "sqlite" if settings.is_sqlite else "postgresql",
        "connected": False,
        "version": None,
    }

    try:
        async with engine.connect() as conn:
            if settings.is_sqlite:
                result = await conn.execute(text("SELECT sqlite_version()"))
                version = result.scalar()
                info["version"] = version
                info["connected"] = True
            else:
                result = await conn.execute(text("SELECT version()"))
                version = result.scalar()
                info["version"] = version.split(",")[0] if version else None
                info["connected"] = True
    except Exception as e:
        info["error"] = str(e)

    return info


DB = AsyncSession
