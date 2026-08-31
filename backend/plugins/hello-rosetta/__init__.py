# 空：实际逻辑位于 backend/plugins/hello-rosetta/plugin.py
# 并通过本文件 re-export register() 供 plugin_loader 使用。
from .plugin import register

__all__ = ["register"]
