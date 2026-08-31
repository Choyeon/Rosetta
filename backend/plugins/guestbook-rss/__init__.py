# 插件加载入口：实际实现位于 plugin.py
from .plugin import register

__all__ = ["register"]
