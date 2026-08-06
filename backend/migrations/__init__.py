"""
数据库迁移工具

基于 Alembic 的简化迁移工具，零配置开箱即用。

使用方法:
    uv run python -m backend.migrations upgrade head    # 升级到最新版本
    uv run python -m backend.migrations downgrade -1    # 回退一个版本
    uv run python -m backend.migrations revision --autogenerate -m "描述"  # 自动生成迁移
    uv run python -m backend.migrations current         # 查看当前版本
    uv run python -m backend.migrations history         # 查看迁移历史
"""

from backend.migrations.cli import main

__all__ = ["main"]
