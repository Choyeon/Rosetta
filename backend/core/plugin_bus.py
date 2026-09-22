"""
Rosetta 插件事件总线（兼容门面 · PluginBus）。

历史上 Rosetta 存在两套互不相通的钩子实现：

1. 本模块的 ``PluginBus``（核心 API ``blog/admin/comments`` 通过
   ``bus.do_action(...)`` 触发）；
2. :mod:`backend.core.hooks` 的模块级注册表（插件通过
   ``register_action/register_filter`` 装饰器注册）。

二者注册表不同、钩子名也不一致，导致插件监听的 ``post.published`` /
``the_content`` 等钩子在真实请求路径中永远不会被触发。

本次重构后，``PluginBus`` 成为一个**薄兼容门面**：所有注册 / 移除 / 触发
都直接委托给 :mod:`backend.core.hooks` 的唯一注册表，同时保留
``loaded_plugins`` 属性（``plugin_loader`` 仍用它记录已加载插件）。
因此：

- 核心代码 ``bus.do_action("post.created", ...)`` 无需任何改动即可触达插件；
- 插件 ``register_action(...)`` 与 ``bus.add_action(...)`` 落到同一份表；
- 沙箱隔离、priority + FIFO、插件级摘除等语义全部由 hooks 引擎统一保证。
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from backend.core import hooks as _hooks


class PluginBus:
    """委托到 :mod:`backend.core.hooks` 的兼容门面。"""

    def __init__(self) -> None:
        # load_plugins 写入成功的插件 id 列表，用于测试与排障
        # （这是门面唯一自持的状态；钩子本身全部存在 hooks 模块中）。
        self.loaded_plugins: list[str] = []

    # ── Action 钩子（委托） ───────────────────────────────────────────────

    def add_action(self, name: str, callback: Callable[..., Any], priority: int = 10) -> None:
        """注册 action 钩子（同优先级按注册顺序执行）。"""
        _hooks.add_action(name, callback, priority=priority)

    def remove_action(self, name: str, callback: Callable[..., Any]) -> bool:
        """移除一个已注册的 action。返回是否存在并被删除。"""
        return _hooks.remove_action(name, callback)

    async def do_action(self, name: str, *args: Any, **kwargs: Any) -> int:
        """触发 action 钩子。返回实际执行的 handler 个数。"""
        return await _hooks.do_action(name, *args, **kwargs)

    # ── Filter 钩子（委托） ───────────────────────────────────────────────

    def add_filter(self, name: str, callback: Callable[..., Any], priority: int = 10) -> None:
        """注册 filter 钩子（同优先级按注册顺序执行）。"""
        _hooks.add_filter(name, callback, priority=priority)

    def remove_filter(self, name: str, callback: Callable[..., Any]) -> bool:
        """移除一个已注册的 filter。返回是否存在并被删除。"""
        return _hooks.remove_filter(name, callback)

    async def apply_filters(self, name: str, value: Any, **kwargs: Any) -> Any:
        """依次把 value 传过 filter 管道，返回最终值。"""
        return await _hooks.apply_filters(name, value, **kwargs)


# 进程内单例：全局唯一事件总线（门面）
bus = PluginBus()
