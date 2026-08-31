"""
Rosetta 插件事件总线（PluginBus）。

提供两种钩子：

1. **Action Hook** —— 广播型事件，回调返回值被忽略，所有回调顺序执行，
   单个回调抛异常不影响其它回调（异常仅记录到 logger）。
   接口：``bus.add_action(name, fn, priority=10)`` / ``bus.remove_action(name, fn)``
   / ``await bus.do_action(name, *args, **kwargs)``

2. **Filter Hook** —— 管道型：初始 value 逐次传给每个回调，返回值作为下一个回调的
   输入，最终结果由 ``apply_filters`` 返回。回调抛异常时跳过该次并保留原值，
   不中断整个管道。
   接口：``bus.add_filter(name, fn, priority=10)`` / ``bus.remove_filter(name, fn)``
   / ``await bus.apply_filters(name, value, **kwargs)``
"""

from __future__ import annotations

import asyncio
import functools
import logging
from dataclasses import dataclass, field
from typing import Any, Callable

logger = logging.getLogger(__name__)


@dataclass(order=True)
class _Hook:
    priority: int
    seq: int = field(compare=True)
    callback: Callable[..., Any] = field(compare=False)


class PluginBus:
    def __init__(self) -> None:
        self._actions: dict[str, list[_Hook]] = {}
        self._filters: dict[str, list[_Hook]] = {}
        self._seq = 0
        # load_plugins 写入成功的插件 id 列表，用于测试与排障
        self.loaded_plugins: list[str] = []

    # ── Action 钩子 ────────────────────────────────────────────────────────

    def add_action(self, name: str, callback: Callable[..., Any], priority: int = 10) -> None:
        """注册 action 钩子（同优先级按注册顺序执行）。"""
        self._seq += 1
        self._actions.setdefault(name, []).append(_Hook(priority, self._seq, callback))
        self._actions[name].sort()

    def remove_action(self, name: str, callback: Callable[..., Any]) -> bool:
        """移除一个已注册的 action。返回是否存在并被删除。"""
        hooks = self._actions.get(name, [])
        new_hooks = [h for h in hooks if h.callback is not callback]
        existed = len(new_hooks) != len(hooks)
        if existed:
            self._actions[name] = new_hooks
        return existed

    async def do_action(self, name: str, *args: Any, **kwargs: Any) -> None:
        """触发 action 钩子：顺序执行，回调异常被隔离并记录日志。"""
        hooks = list(self._actions.get(name, []))
        for hook in hooks:
            cb = hook.callback
            try:
                if asyncio.iscoroutinefunction(cb) or asyncio.iscoroutinefunction(getattr(cb, "__call__", cb)):
                    maybe_await = cb(*args, **kwargs)
                else:
                    # sync callback - wrap to avoid blocking the loop too long
                    maybe_await = asyncio.to_thread(functools.partial(cb, *args, **kwargs))
                result = maybe_await
                if asyncio.iscoroutine(result) or hasattr(result, "__await__"):
                    await result
            except Exception as exc:  # pragma: no cover - 插件错误不影响主流程
                logger.exception(
                    "[plugin-bus] action 回调抛异常已隔离: hook=%s cb=%s err=%s",
                    name, getattr(cb, "__qualname__", repr(cb)), exc,
                )

    # ── Filter 钩子 ────────────────────────────────────────────────────────

    def add_filter(self, name: str, callback: Callable[..., Any], priority: int = 10) -> None:
        """注册 filter 钩子（同优先级按注册顺序执行）。"""
        self._seq += 1
        self._filters.setdefault(name, []).append(_Hook(priority, self._seq, callback))
        self._filters[name].sort()

    def remove_filter(self, name: str, callback: Callable[..., Any]) -> bool:
        hooks = self._filters.get(name, [])
        new_hooks = [h for h in hooks if h.callback is not callback]
        existed = len(new_hooks) != len(hooks)
        if existed:
            self._filters[name] = new_hooks
        return existed

    async def apply_filters(self, name: str, value: Any, **kwargs: Any) -> Any:
        """依次把 value 传过 filter 管道，返回最终值。单步异常跳过。"""
        current = value
        for hook in list(self._filters.get(name, [])):
            cb = hook.callback
            try:
                if asyncio.iscoroutinefunction(cb) or asyncio.iscoroutinefunction(getattr(cb, "__call__", cb)):
                    maybe_await = cb(current, **kwargs)
                else:
                    maybe_await = asyncio.to_thread(functools.partial(cb, current, **kwargs))
                if asyncio.iscoroutine(maybe_await) or hasattr(maybe_await, "__await__"):
                    next_val = await maybe_await
                else:
                    next_val = maybe_await
                current = next_val
            except Exception as exc:  # pragma: no cover
                logger.exception(
                    "[plugin-bus] filter 回调抛异常已跳过: hook=%s cb=%s err=%s",
                    name, getattr(cb, "__qualname__", repr(cb)), exc,
                )
        return current


# 进程内单例：全局唯一事件总线
bus = PluginBus()
