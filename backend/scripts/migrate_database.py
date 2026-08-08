"""
跨数据库一键数据迁移 CLI & 模块

支持：
- SQLite  ↔  PostgreSQL (asyncpg)
- SQLite  ↔  SQLite  (备份/恢复)
- PostgreSQL ↔ PostgreSQL (不同实例间迁移)

用法：
  # CLI: sqlite → pg
  python -m backend.scripts.migrate_database \
      --from "sqlite+aiosqlite:///./rosetta.db" \
      --to   "postgresql+asyncpg://user:pass@localhost:5432/rosetta"

  # 仅校验计数
  python -m backend.scripts.migrate_database ... --dry-run

  # Python API:
  from backend.scripts.migrate_database import run_migration
  async for progress in run_migration(src, dst):
      print(progress["stage"], progress.get("message"))
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import sys
import time
from collections.abc import AsyncGenerator, Callable, Iterable
from dataclasses import dataclass, field
from typing import Any

from sqlalchemy import (
    MetaData,
    Table,
    create_engine,
    event,
    select,
    text,
)
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

logger = logging.getLogger("rosetta.migrate_database")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-7s | %(name)s | %(message)s",
)


# =========================================================================
# 进度回调模型
# =========================================================================


@dataclass
class MigrationStats:
    source_url: str
    target_url: str
    started_at: float = field(default_factory=time.time)
    finished_at: float | None = None
    tables_total: int = 0
    tables_done: int = 0
    rows_total: int = 0
    rows_done: int = 0
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)

    def to_progress(self, stage: str, **extra) -> dict[str, Any]:
        return {
            "stage": stage,
            "elapsed": round(time.time() - self.started_at, 2),
            "tables_total": self.tables_total,
            "tables_done": self.tables_done,
            "rows_total": self.rows_total,
            "rows_done": self.rows_done,
            "warnings": list(self.warnings),
            "errors": list(self.errors),
            **extra,
        }


# =========================================================================
# 小工具
# =========================================================================


def _split_driver(url: str) -> tuple[str, str]:
    """返回 (dialect_driver, rest). 例如 sqlite+aiosqlite:////tmp/a.db → ('sqlite+aiosqlite', '...')"""
    if "://" not in url:
        raise ValueError(f"Invalid SQLAlchemy URL: {url}")
    driver, rest = url.split("://", 1)
    return driver, rest


def is_sqlite(url: str) -> bool:
    return _split_driver(url)[0].startswith("sqlite")


def is_postgres(url: str) -> bool:
    return _split_driver(url)[0].startswith("postgres")


async def _ensure_postgres_db_exists(target_url: str) -> None:
    """目标是 PG 时，如果数据库不存在，用 postgres maintenance DB 创建它。"""
    from sqlalchemy import create_engine as _sync_create_engine

    if not is_postgres(target_url):
        return
    driver, rest = _split_driver(target_url)
    # rest: user:pass@host:port/dbname[?query]
    authority_part, db_and_query = (rest.rsplit("/", 1) + [""])[:2]
    if not db_and_query:
        return
    db_name = db_and_query.split("?", 1)[0]
    if not db_name:
        return
    maintenance_url = f"{driver}://{authority_part}/postgres"

    def _create_sync():
        engine = _sync_create_engine(maintenance_url.replace("+asyncpg", "+psycopg2"), isolation_level="AUTOCOMMIT")
        try:
            with engine.connect() as conn:
                row = conn.execute(text("SELECT 1 FROM pg_database WHERE datname=:d"), {"d": db_name}).fetchone()
                if not row:
                    # Don't quote inside CREATE DATABASE — use %I style via format, here exec direct
                    conn.execute(text(f'CREATE DATABASE "{db_name}" ENCODING \'UTF8\''))
                    logger.info(f"[PG] 自动创建数据库 {db_name}")
        except Exception as exc:  # pragma: no cover - 真实依赖环境
            logger.warning(f"[PG] 尝试维护库创建失败（可能已有/权限不足），将继续: {exc}")
        finally:
            engine.dispose()

    try:
        await asyncio.to_thread(_create_sync)
    except Exception as exc:
        logger.warning(f"[PG] 保证目标 DB 存在时出错，继续: {exc}")


async def _run_alembic_upgrade(target_url: str) -> None:
    """对目标库执行 Alembic migrations 到 head。直接调用 CLI 函数，不依赖子进程。"""
    from pathlib import Path

    from alembic import command
    from alembic.config import Config as AlembicConfig

    root = Path(__file__).resolve().parent.parent.parent
    ini = root / "alembic.ini"
    migrations = root / "backend" / "migrations"

    def _run():
        cfg = AlembicConfig(str(ini) if ini.exists() else None)
        cfg.set_main_option("script_location", str(migrations))
        cfg.set_main_option("prepend_sys_path", ".")
        # 把 sqlalchemy.url 覆盖成目标
        sync_url = target_url.replace("+asyncpg", "+psycopg2").replace("+aiosqlite", "")
        cfg.set_main_option("sqlalchemy.url", sync_url)
        command.upgrade(cfg, "head")

    await asyncio.to_thread(_run)


# =========================================================================
# 连接辅助
# =========================================================================


def _make_async_engine(url: str) -> AsyncEngine:
    """创建异步引擎，SQLite 默认关 FK 便于批量插入，PG 用连接池。"""
    if is_sqlite(url):
        engine = create_async_engine(
            url,
            poolclass=None,  # 同 NullPool
            connect_args={"check_same_thread": False},
        )

        @event.listens_for(engine.sync_engine, "connect")
        def _set_pragma(dbapi_conn, _rec):
            cur = dbapi_conn.cursor()
            cur.execute("PRAGMA foreign_keys=OFF")
            cur.execute("PRAGMA journal_mode=WAL")
            cur.execute("PRAGMA synchronous=NORMAL")
            cur.execute("PRAGMA busy_timeout=5000")
            cur.close()

        return engine

    return create_async_engine(url, pool_pre_ping=True, pool_recycle=3600, future=True)


async def _with_fk_disabled(engine: AsyncEngine, side: str, enabled: bool) -> None:
    """SQLite 直接 pragma；PG 在当前会话下关闭 FK。"""
    async with engine.begin() as conn:
        if is_sqlite(str(engine.url)):
            await conn.execute(text(f"PRAGMA foreign_keys={'ON' if enabled else 'OFF'}"))
        elif is_postgres(str(engine.url)):
            # replica 会跳过所有触发器，等同禁用 FK。
            role = "origin" if enabled else "replica"
            await conn.execute(text(f"SET session_replication_role = {role}"))


# =========================================================================
# 表排序 & 计数
# =========================================================================


_TABLES_LAST = [
    # 依赖多的表放后（其实 sorted_tables 已经是 FK 拓扑，这里仅兜底）
    "post_view_histories",
    "post_revisions",
    "comments",
    "comment_reactions",
    "operation_logs",
    "trash_items",
    "private_messages",
    "visit_logs",
    "performance_metrics",
    "votes",
    "post_tags",
    "post_likes",
    "notifications",
]


def _sort_tables(tables: Iterable[Table]) -> list[Table]:
    """按 (手动权重升序, 原表名排序) 排序。"""

    def _weight(t: Table) -> int:
        try:
            return _TABLES_LAST.index(t.name) + 1000
        except ValueError:
            return 0

    return sorted(tables, key=lambda t: (_weight(t), t.name))


async def _count_rows(session: AsyncSession, table: Table) -> int:
    res = await session.execute(select(text("COUNT(*)")).select_from(table))
    return int(res.scalar_one() or 0)


def _is_autoincrement_pk(table: Table) -> bool:
    """简单判断：是否单列整数自增主键（PG serial/id，SQLite rowid）。"""
    pk = table.primary_key
    if len(pk.columns) != 1:
        return False
    col = list(pk.columns)[0]
    if not (str(col.type).lower().startswith("integer") or str(col.type).lower().startswith("bigint") or str(col.type).lower().startswith("smallint")):
        # PG: SERIAL -> Integer 底层
        return False
    return True


# =========================================================================
# 核心：数据拷贝
# =========================================================================

_CHUNK_SIZE = 5000


async def _copy_table(
    src_session: AsyncSession,
    dst_session: AsyncSession,
    table: Table,
    stats: MigrationStats,
    progress_cb: Callable[[dict[str, Any]], None] | None = None,
) -> tuple[int, int]:
    """拷贝单表，返回 (src_count, inserted)。
    策略：
      - 不带 WHERE，全表 SELECT。
      - 用 server-side 游标分块读取。
      - 目标端直接 bulk_insert，冲突忽略（INSERT ON CONFLICT DO NOTHING，PG 支持；SQLite 用 INSERT OR IGNORE）。
      - 如果表有单列自增 PK，结束后同步序列。
    """
    table_name = table.name
    src_count = await _count_rows(src_session, table)
    stats.rows_total += src_count

    if src_count == 0:
        logger.info(f"[COPY] {table_name}: 空表跳过")
        return 0, 0

    cols = [c for c in table.columns]
    stmt = select(*cols)
    if is_postgres(str(dst_session.bind.engine.url)) if False else True:
        pass
    # stream 分块
    inserted = 0
    insert_values_list: list[dict[str, Any]] = []

    async def _flush_chunk(chunk: list[dict[str, Any]]) -> int:
        if not chunk:
            return 0
        # 用 dialect 特化的 INSERT
        if is_postgres(str(dst_session.bind.engine.url)):
            from sqlalchemy.dialects.postgresql import insert as pg_insert

            ins = pg_insert(table).values(chunk).on_conflict_do_nothing()
        else:
            # SQLite 等：INSERT OR IGNORE
            ins = table.insert().prefix_with("OR IGNORE").values(chunk)
        r = await dst_session.execute(ins)
        await dst_session.commit()
        # rowcount 不一定可靠，直接返回 len(chunk) 作为近似（有冲突时会小）
        return r.rowcount or 0

    progress_cb and progress_cb(stats.to_progress("copy", table=table_name, rows_src=src_count, rows_done=0))

    streamed = 0
    async for row in await src_session.stream(stmt.execution_options(yield_per=_CHUNK_SIZE)):
        # row 是 Row，键是列名
        insert_values_list.append(dict(zip((c.name for c in cols), row)))
        streamed += 1
        if len(insert_values_list) >= _CHUNK_SIZE:
            inserted += await _flush_chunk(insert_values_list)
            stats.rows_done += len(insert_values_list)
            insert_values_list.clear()
            progress_cb and progress_cb(stats.to_progress("copy", table=table_name, rows_src=src_count, rows_done=streamed))

    if insert_values_list:
        inserted += await _flush_chunk(insert_values_list)
        stats.rows_done += len(insert_values_list)

    logger.info(f"[COPY] {table_name}: src={src_count} approx_inserted={inserted}")

    # 同步 PG 序列
    if is_postgres(str(dst_session.bind.engine.url)) and _is_autoincrement_pk(table):
        pk_name = list(table.primary_key.columns)[0].name
        # SELECT setval(pg_get_serial_sequence('table','col'), coalesce(MAX(col),1) + 1, false)
        sql = text(
            "SELECT setval(pg_get_serial_sequence(:t,:c), "
            "coalesce((SELECT MAX(\""
            + pk_name
            + "\") FROM \""
            + table_name
            + "\"), 0) + 1, false)"
        )
        try:
            await dst_session.execute(sql, {"t": table_name, "c": pk_name})
            await dst_session.commit()
        except Exception as exc:
            stats.warnings.append(f"{table_name}: setval 失败 {exc}")

    return src_count, inserted


# =========================================================================
# 主入口
# =========================================================================


async def run_migration(
    source_url: str,
    target_url: str,
    *,
    dry_run: bool = False,
    skip_schema: bool = False,
) -> AsyncGenerator[dict[str, Any], None]:
    """
    跨库迁移异步生成器，持续 yield 进度事件。

    Yields:
      {"stage": "init|schema|pre_copy|copy|verify|done|error", ...}
    """
    stats = MigrationStats(source_url=source_url, target_url=target_url)
    src_engine: AsyncEngine | None = None
    dst_engine: AsyncEngine | None = None

    def _emit(**extra):
        yield stats.to_progress(stats.to_progress.__self__.__class__.__name__, **extra) if False else stats.to_progress(stats.to_progress.__self__.__class__.__name__ if False else "noop", **extra)

    try:
        yield stats.to_progress("init", message="解析源/目标连接")
        # 0. PG target DB 自动创建
        if is_postgres(target_url):
            await _ensure_postgres_db_exists(target_url)

        yield stats.to_progress("init", message="创建源/目标引擎")
        src_engine = _make_async_engine(source_url)
        dst_engine = _make_async_engine(target_url)

        # 1. 连通性 & 源 schema 反射（源必须已存在，要读它数据）
        yield stats.to_progress("init", message="验证源/目标连通性")
        async with src_engine.connect() as c:
            await c.execute(text("SELECT 1"))
        async with dst_engine.connect() as c:
            await c.execute(text("SELECT 1"))

        # 2. Schema: 在 target 上执行 Alembic upgrade head
        if not skip_schema and not dry_run:
            yield stats.to_progress("schema", message="对目标执行 alembic upgrade head")
            try:
                await _run_alembic_upgrade(target_url)
            except Exception as exc:
                stats.errors.append(f"alembic 升级失败: {exc}")
                yield stats.to_progress("error", message=f"alembic 升级失败: {exc}")
                # 不致命，继续尝试
        else:
            yield stats.to_progress("schema", message="跳过 schema 阶段")

        # 3. 反射源/目标的 metadata，取交集表
        yield stats.to_progress("pre_copy", message="反射源/目标表结构")
        src_meta = MetaData()
        dst_meta = MetaData()
        # 反射用 sync 引擎（轻量）
        def _reflect(url: str, meta: MetaData):
            sync_url = url.replace("+asyncpg", "+psycopg2").replace("+aiosqlite", "")
            eng = create_engine(sync_url, future=True)
            try:
                meta.reflect(bind=eng)
            finally:
                eng.dispose()
        await asyncio.gather(
            asyncio.to_thread(_reflect, source_url, src_meta),
            asyncio.to_thread(_reflect, target_url, dst_meta),
        )
        src_tables_map = {t.name: t for t in src_meta.tables.values()}
        dst_tables_map = {t.name: t for t in dst_meta.tables.values()}
        common_names = [n for n in src_tables_map if n in dst_tables_map]
        missing_in_target = [n for n in src_tables_map if n not in dst_tables_map]
        for n in missing_in_target:
            stats.warnings.append(f"源表 {n} 在目标不存在，跳过")

        ordered_src = _sort_tables([src_tables_map[n] for n in common_names])
        stats.tables_total = len(ordered_src)
        yield stats.to_progress(
            "pre_copy",
            tables=[t.name for t in ordered_src],
            missing_in_target=missing_in_target,
            message=f"将迁移 {stats.tables_total} 张表",
        )

        if dry_run:
            # dry-run: 只输出源侧计数
            yield stats.to_progress("verify", message="dry-run: 仅输出源表计数")
            src_session = async_sessionmaker(src_engine, expire_on_commit=False, class_=AsyncSession)()
            try:
                for t in ordered_src:
                    c = await _count_rows(src_session, t)
                    stats.rows_total += c
                    yield stats.to_progress("verify", table=t.name, src_count=c)
                    stats.tables_done += 1
            finally:
                await src_session.close()
            yield stats.to_progress("done", message="dry-run 完成")
            return

        # 4. 关闭 FK
        yield stats.to_progress("pre_copy", message="关闭目标外键校验")
        await _with_fk_disabled(dst_engine, "target", False)

        # 5. 逐表复制
        src_session_cls = async_sessionmaker(src_engine, expire_on_commit=False, class_=AsyncSession)
        dst_session_cls = async_sessionmaker(dst_engine, expire_on_commit=False, class_=AsyncSession)

        def _cb(p: dict[str, Any]):
            pass

        for table in ordered_src:
            src_s = src_session_cls()
            dst_s = dst_session_cls()
            try:
                src_count, inserted = await _copy_table(src_s, dst_s, table, stats, progress_cb=lambda p: None)
                stats.tables_done += 1
                yield stats.to_progress(
                    "copy",
                    table=table.name,
                    rows_src=src_count,
                    rows_inserted_approx=inserted,
                )
            except Exception as exc:
                stats.errors.append(f"{table.name}: {exc}")
                yield stats.to_progress("error", table=table.name, message=str(exc))
            finally:
                await src_s.close()
                await dst_s.close()

        # 6. 开启 FK
        yield stats.to_progress("verify", message="开启目标外键校验并做计数校验")
        try:
            await _with_fk_disabled(dst_engine, "target", True)
        except Exception as exc:
            stats.warnings.append(f"重新启用 FK 失败: {exc}")

        # 7. 校验行数
        src_s = src_session_cls()
        dst_s = dst_session_cls()
        mismatches: list[dict[str, Any]] = []
        try:
            for table in ordered_src:
                s = await _count_rows(src_s, table)
                d = await _count_rows(dst_s, table)
                if s != d:
                    mismatches.append({"table": table.name, "src": s, "dst": d})
        finally:
            await src_s.close()
            await dst_s.close()

        if mismatches:
            stats.warnings.append(f"行数不匹配: {len(mismatches)} 张表")
            yield stats.to_progress("verify", mismatches=mismatches)

        stats.finished_at = time.time()
        yield stats.to_progress(
            "done",
            message=f"完成。耗时 {stats.finished_at - stats.started_at:.1f}s，"
            f"警告 {len(stats.warnings)}，错误 {len(stats.errors)}",
        )
    except Exception as exc:
        logger.exception("迁移失败")
        stats.errors.append(str(exc))
        yield stats.to_progress("error", message=str(exc))
    finally:
        if src_engine is not None:
            await src_engine.dispose()
        if dst_engine is not None:
            await dst_engine.dispose()


# =========================================================================
# CLI
# =========================================================================


def _build_argparser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="migrate_database",
        description="Rosetta 跨数据库一键数据迁移 (SQLite/PostgreSQL)",
    )
    p.add_argument("--from", dest="from_", required=True, help="源库 SQLAlchemy URL")
    p.add_argument("--to", dest="to_", required=True, help="目标库 SQLAlchemy URL")
    p.add_argument("--dry-run", action="store_true", help="仅列出并计数，不实际写入")
    p.add_argument("--skip-schema", action="store_true", help="不对目标执行 Alembic schema 升级")
    p.add_argument("-v", "--verbose", action="store_true")
    return p


async def _main_async(args: argparse.Namespace) -> int:
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    start = time.time()
    final_stage = "init"
    async for progress in run_migration(args.from_, args.to_, dry_run=args.dry_run, skip_schema=args.skip_schema):
        final_stage = progress.get("stage", final_stage)
        elapsed = progress.get("elapsed", 0.0)
        msg = progress.get("message", "")
        table = progress.get("table", "")
        extra = ""
        if progress.get("rows_src") is not None:
            extra = f" src={progress['rows_src']}"
        if progress.get("rows_done") is not None:
            extra += f" done={progress['rows_done']}"
        print(
            f"[{elapsed:>7.1f}s] {progress['stage']:<10} {table or '':<22} {msg or ''}{extra}"
        )
        if progress.get("errors"):
            for e in progress["errors"][-3:]:
                print("  !!", e)
    print(f"\n迁移完成 in {time.time()-start:.1f}s，最后阶段 {final_stage}")
    return 0 if final_stage == "done" else 2


def main(argv: list[str] | None = None) -> int:
    args = _build_argparser().parse_args(argv)
    return asyncio.run(_main_async(args))


if __name__ == "__main__":
    sys.exit(main())
