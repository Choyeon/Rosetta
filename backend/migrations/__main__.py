"""
迁移工具入口

直接运行: python -m backend.migrations [command]
"""

from backend.migrations.cli import main

if __name__ == "__main__":
    main()
