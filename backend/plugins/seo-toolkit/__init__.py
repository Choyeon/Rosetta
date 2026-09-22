# 插件加载入口：实际实现位于 plugin.py
# 必须 re-export register()，否则 plugin_loader 在 import 本包时找不到入口，
# 会跳过该插件（且其模块级钩子 @register_action / @register_filter 也永远不会执行）。
from .plugin import register

__all__ = ["register"]
