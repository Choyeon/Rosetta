"""
Rosetta 扩展点引擎（WordPress 风格 Hook / Filter）。

提供四个公开 API：

*   ``register_action(hook_name, priority=10, plugin=None)`` — 装饰器，注册一个 action 处理器。
    Action 处理器用于副作用，不返回值（返回值被忽略）。所有处理器都会在沙箱中被调用，
    任何异常只会被记录、不会冒泡到主链路（满足 F4 隔离性要求）。

*   ``register_filter(hook_name, priority=10, plugin=None)`` — 装饰器，注册一个 filter 处理器。
    Filter 处理器接收当前 ``value``，**必须** 返回同类型（或兼容）的值。链式调用。
    异常发生时跳过该处理器，保留原始 value 继续传递给下一个。

*   ``do_action(hook_name, *args, **kwargs)`` — *async*。按 priority 从小到大依次触发已注册
    action。同一 priority 的执行顺序不保证（先进先出）。

*   ``apply_filters(hook_name, value, *args, **kwargs)`` — *async*。按 priority 链式执行 filter，
    最终返回处理后的 value。

命名规范（与 WordPress 对齐，参考 F6 forces）：

*   action 名：``{domain}.{verb}``（例 ``post.published``、``plugin.activated``、``theme.customizer_saved``）
*   filter 名：``the_{content}``（例 ``the_content``、``the_title``、``the_excerpt``）或
    ``{domain}_{property}_filter``。

性能（F3 forces）：Hook 注册发生在导入时（lifespan bootloader 激活插件阶段），
请求路径只有一次 dict 查找 + 遍历，零 I/O。
"""

from __future__ import annotations

import asyncio
import functools
import inspect
import logging
from dataclasses import dataclass, field
from typing import Any, Callable

logger = logging.getLogger("rosetta.hooks")

# ── 内部存储 ──────────────────────────────────────────────────────────────

@dataclass(order=True)
class _HookHandler:
    priority: int = 10
    sequence: int = field(compare=True, default=0)   # 保证同 priority FIFO
    fn: Callable[..., Any] = field(compare=False, repr=False, default=lambda *a, **kw: None)
    plugin: str | None = field(compare=False, default=None)
    hook_name: str = field(compare=False, default="")


_actions: dict[str, list[_HookHandler]] = {}
_filters: dict[str, list[_HookHandler]] = {}

_seq_counter = 0


def _reset_hooks_for_tests() -> None:  # pragma: no cover - debug helper
    """清空注册表（pytest fixture 使用）。"""
    global _seq_counter
    _actions.clear()
    _filters.clear()
    _seq_counter = 0


# ── 装饰器 ────────────────────────────────────────────────────────────────

def register_action(
    hook_name: str,
    /,
    *,
    priority: int = 10,
    plugin: str | None = None,
) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """注册 action 处理器（副作用）。

    :param hook_name: 规范 ``{domain}.{verb}``。
    :param priority: 数值越小越先执行，默认 10（与 WordPress 一致）。
    :param plugin: 插件 slug（便于后续移除插件时整体摘除）。
    :returns: 原始函数（不做包装，便于调试堆栈）。
    """

    def _decorator(fn: Callable[..., Any]) -> Callable[..., Any]:
        global _seq_counter
        _seq_counter += 1
        handler = _HookHandler(
            priority=priority,
            sequence=_seq_counter,
            fn=fn,
            plugin=plugin,
            hook_name=hook_name,
        )
        _actions.setdefault(hook_name, []).append(handler)
        _actions[hook_name].sort()
        return fn

    return _decorator


def register_filter(
    hook_name: str,
    /,
    *,
    priority: int = 10,
    plugin: str | None = None,
) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """注册 filter 处理器（值转换链）。"""

    def _decorator(fn: Callable[..., Any]) -> Callable[..., Any]:
        global _seq_counter
        _seq_counter += 1
        handler = _HookHandler(
            priority=priority,
            sequence=_seq_counter,
            fn=fn,
            plugin=plugin,
            hook_name=hook_name,
        )
        _filters.setdefault(hook_name, []).append(handler)
        _filters[hook_name].sort()
        return fn

    return _decorator


def remove_hooks_for_plugin(plugin_slug: str) -> int:
    """插件被禁用/删除时摘除其所有 action/filter。返回移除的处理器数量。"""
    removed = 0
    for registry in (_actions, _filters):
        for name, handlers in list(registry.items()):
            before = len(handlers)
            kept = [h for h in handlers if h.plugin != plugin_slug]
            if len(kept) != before:
                registry[name] = kept
                removed += before - len(kept)
    return removed


def has_action(name: str) -> bool:
    return bool(_actions.get(name))


def has_filter(name: str) -> bool:
    return bool(_filters.get(name))


def hooks_registered_for_plugin(plugin_slug: str) -> bool:
    """判断是否已有任何 action/filter 归属该插件（用于冷启动幂等激活判断）。"""
    for registry in (_actions, _filters):
        for handlers in registry.values():
            for h in handlers:
                if h.plugin == plugin_slug:
                    return True
    return False


# ── 运行时沙箱执行器 ──────────────────────────────────────────────────────

async def _safe_call(fn: Callable[..., Any], *args: Any, **kwargs: Any) -> Any:
    """在 try/except 沙箱中调用 sync/async 处理器，返回结果或 None（失败时）。"""
    try:
        if inspect.iscoroutinefunction(fn) or inspect.isasyncgenfunction(fn):
            return await fn(*args, **kwargs)
        # 同步函数；避免阻塞事件循环 -> 线程池
        loop = asyncio.get_running_loop()
        partial = functools.partial(fn, *args, **kwargs)
        return await loop.run_in_executor(None, partial)
    except Exception as exc:  # noqa: BLE001 - intentional sandbox
        logger.exception(
            "Hook handler failed (sandboxed): %s.%s args=%s kwargs=%s exc=%s",
            getattr(fn, "__module__", "?"),
            getattr(fn, "__qualname__", str(fn)),
            args,
            {k: v for k, v in kwargs.items() if k != "self"},
            exc,
        )
        return None


async def do_action(name: str, *args: Any, **kwargs: Any) -> int:
    """触发 action。返回实际执行的 handler 个数（用于断言）。"""
    handlers = _actions.get(name)
    if not handlers:
        return 0
    executed = 0
    # 顺序：按 priority(+) 再 sequence(+)，同步串行执行（WP 语义：顺序确定）
    for h in list(handlers):  # copy: 防止 handler 回调期间的并发修改
        result = await _safe_call(h.fn, *args, **kwargs)
        if result is not None:
            # 允许 handler 返回 False 显式短路后续 actions（扩展行为：可选）
            if result is False:
                logger.info("Action %s short-circuited by %s/%s", name, h.plugin, h.fn.__qualname__)
                break
        executed += 1
    return executed


async def apply_filters(name: str, value: Any, *args: Any, **kwargs: Any) -> Any:
    """应用 filter 链并返回最终值。"""
    handlers = _filters.get(name)
    if not handlers:
        return value
    current = value
    for h in list(handlers):
        result = await _safe_call(h.fn, current, *args, **kwargs)
        if result is None:
            # 异常时跳过，保留 current 不变
            continue
        current = result
    return current
