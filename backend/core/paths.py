"""
Rosetta 路径常量 — 所有模块的统一来源

所有 OOBE / 配置文件 / 状态文件的路径定义集中于此，避免散落在 5+ 文件中。
"""

from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent.parent
CONFIG_FILE = BASE_DIR / "rosetta.json"
OOBE_LOCK_FILE = BASE_DIR / ".oobe_complete"
STATE_FILE = BASE_DIR / ".oobe_state.json"
ENV_FILE = BASE_DIR / ".env"