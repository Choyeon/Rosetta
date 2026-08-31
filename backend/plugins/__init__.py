"""
插件包

本目录存放 Rosetta 的全部插件。每个子目录是一个独立插件，需暴露 ``register(app, bus)``。
加载逻辑见 ``backend.core.plugin_loader``。
"""
