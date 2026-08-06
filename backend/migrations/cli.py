"""
迁移命令行工具

提供简洁的迁移命令，零配置使用。

命令:
    upgrade [revision]     升级到指定版本（默认 head）
    downgrade [revision]   回退到指定版本（默认 -1）
    revision               创建新迁移
    current                查看当前版本
    history                查看迁移历史
    init                   初始化迁移（创建表）
    reset                  重置数据库（危险操作）
"""

import argparse
import shutil
from collections.abc import Sequence
from pathlib import Path

from alembic import command
from alembic.script import ScriptDirectory

from backend.migrations.config import (
    MIGRATIONS_DIR,
    get_alembic_config,
    run_async,
)


def cmd_upgrade(args):
    """升级数据库到指定版本"""
    config = get_alembic_config()
    revision = args.revision or "head"

    print(f"⬆️  升级数据库到版本: {revision}")
    command.upgrade(config, revision)
    print("✅ 升级完成")


def cmd_downgrade(args):
    """回退数据库到指定版本"""
    config = get_alembic_config()
    revision = args.revision or "-1"

    print(f"⬇️  回退数据库到版本: {revision}")
    command.downgrade(config, revision)
    print("✅ 回退完成")


def cmd_revision(args):
    """创建新迁移"""
    config = get_alembic_config()

    if args.autogenerate:
        print("🔍 自动检测模型变更...")

    command.revision(
        config,
        autogenerate=args.autogenerate,
        message=args.message,
    )
    print("✅ 迁移文件已创建")


def cmd_current(args):
    """查看当前数据库版本"""
    config = get_alembic_config()
    command.current(config)


def cmd_history(args):
    """查看迁移历史"""
    config = get_alembic_config()
    command.history(config, verbose=args.verbose)


def cmd_init(args):
    """初始化数据库（创建所有表）"""

    async def _init():
        from sqlalchemy import text

        from backend.core.database import Base, engine

        print("🔧 初始化数据库...")

        versions_dir = MIGRATIONS_DIR / "versions"
        versions_dir.mkdir(parents=True, exist_ok=True)

        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        config = get_alembic_config()
        script = ScriptDirectory.from_config(config)

        head_revision = script.get_current_head()

        if head_revision:
            async with engine.begin() as conn:
                await conn.execute(
                    text(
                        "CREATE TABLE IF NOT EXISTS alembic_version (version_num VARCHAR(32) NOT NULL PRIMARY KEY)"
                    )
                )
                await conn.execute(
                    text(f"INSERT INTO alembic_version (version_num) VALUES ('{head_revision}')")
                )

        print("✅ 数据库初始化完成")

    run_async(_init())


def cmd_reset(args):
    """重置数据库（删除所有表并重新创建）"""
    if not args.force:
        confirm = input("⚠️  这将删除所有数据！确定要继续吗？(yes/no): ")
        if confirm.lower() != "yes":
            print("❌ 操作已取消")
            return

    async def _reset():
        from sqlalchemy import text

        from backend.core.database import Base, engine

        print("🗑️  删除所有表...")

        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)

        print("🔧 重新创建表...")

        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        config = get_alembic_config()
        script = ScriptDirectory.from_config(config)
        head_revision = script.get_current_head()

        if head_revision:
            async with engine.begin() as conn:
                await conn.execute(
                    text(
                        "CREATE TABLE IF NOT EXISTS alembic_version (version_num VARCHAR(32) NOT NULL PRIMARY KEY)"
                    )
                )
                await conn.execute(
                    text(f"INSERT INTO alembic_version (version_num) VALUES ('{head_revision}')")
                )

        print("✅ 数据库重置完成")

    run_async(_reset())


def cmd_status(args):
    """查看数据库状态"""

    async def _status():
        from backend.core.database import check_db_connection, get_db_info

        print("📊 数据库状态\n")

        connected = await check_db_connection()
        if not connected:
            print("❌ 数据库连接失败")
            return

        info = await get_db_info()

        print(f"类型: {info.get('type', 'unknown')}")
        print(f"版本: {info.get('version', 'unknown')}")
        print(f"状态: {'✅ 已连接' if info.get('connected') else '❌ 未连接'}")

        config = get_alembic_config()
        script = ScriptDirectory.from_config(config)

        head = script.get_current_head()
        print(f"\n最新迁移版本: {head or '无'}")

        try:
            from sqlalchemy import text

            from backend.core.database import engine

            async with engine.connect() as conn:
                result = await conn.execute(text("SELECT version_num FROM alembic_version"))
                current = result.scalar()
                print(f"当前数据库版本: {current or '无'}")

                if current == head:
                    print("\n✅ 数据库已是最新版本")
                elif current:
                    print("\n⚠️  数据库需要升级")
                else:
                    print("\n⚠️  数据库未初始化迁移")
        except Exception:
            print("\n⚠️  数据库未初始化迁移")

    run_async(_status())


def main(argv: Sequence[str] | None = None):
    """主入口"""
    parser = argparse.ArgumentParser(
        prog="migrations",
        description="数据库迁移工具 - 零配置，开箱即用",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  %(prog)s upgrade head              升级到最新版本
  %(prog)s downgrade -1              回退一个版本
  %(prog)s revision -m "添加用户表"  创建空迁移
  %(prog)s revision --autogenerate -m "自动迁移"  自动生成迁移
  %(prog)s current                   查看当前版本
  %(prog)s history                   查看迁移历史
  %(prog)s status                    查看数据库状态
  %(prog)s init                      初始化数据库
  %(prog)s reset --force             重置数据库
        """,
    )

    subparsers = parser.add_subparsers(dest="command", help="可用命令")

    upgrade_parser = subparsers.add_parser("upgrade", help="升级数据库")
    upgrade_parser.add_argument("revision", nargs="?", help="目标版本（默认 head）")
    upgrade_parser.set_defaults(func=cmd_upgrade)

    downgrade_parser = subparsers.add_parser("downgrade", help="回退数据库")
    downgrade_parser.add_argument("revision", nargs="?", help="目标版本（默认 -1）")
    downgrade_parser.set_defaults(func=cmd_downgrade)

    revision_parser = subparsers.add_parser("revision", help="创建新迁移")
    revision_parser.add_argument("-m", "--message", help="迁移描述")
    revision_parser.add_argument("--autogenerate", action="store_true", help="自动检测变更")
    revision_parser.set_defaults(func=cmd_revision)

    current_parser = subparsers.add_parser("current", help="查看当前版本")
    current_parser.set_defaults(func=cmd_current)

    history_parser = subparsers.add_parser("history", help="查看迁移历史")
    history_parser.add_argument("-v", "--verbose", action="store_true", help="详细信息")
    history_parser.set_defaults(func=cmd_history)

    status_parser = subparsers.add_parser("status", help="查看数据库状态")
    status_parser.set_defaults(func=cmd_status)

    init_parser = subparsers.add_parser("init", help="初始化数据库")
    init_parser.set_defaults(func=cmd_init)

    reset_parser = subparsers.add_parser("reset", help="重置数据库")
    reset_parser.add_argument("--force", action="store_true", help="跳过确认")
    reset_parser.set_defaults(func=cmd_reset)

    args = parser.parse_args(argv)

    if args.command is None:
        parser.print_help()
        return

    _clear_pycache()

    if hasattr(args, "func"):
        args.func(args)


def _clear_pycache():
    """清理 Python 缓存，确保使用最新代码"""
    project_root = Path(__file__).parent.parent.parent
    cache_dirs = list(project_root.rglob("__pycache__"))

    for cache_dir in cache_dirs:
        try:
            shutil.rmtree(cache_dir, ignore_errors=True)
        except Exception:
            pass


if __name__ == "__main__":
    main()
