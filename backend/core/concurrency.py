"""
并发查询模块

提供高效的并发查询能力，支持：
- 并行执行多个协程
- 批量查询支持
- 查询超时控制
- 错误处理和日志记录
- 查询结果缓存
"""

import asyncio
import logging
import time
from collections.abc import Awaitable, Callable, Coroutine
from dataclasses import dataclass
from enum import IntEnum
from typing import Any, Generic, TypeVar

from backend.core.cache import cache

logger = logging.getLogger(__name__)

T = TypeVar("T")


class QueryPriority(IntEnum):
    """查询优先级"""

    LOW = 1
    NORMAL = 5
    HIGH = 10
    CRITICAL = 20


@dataclass
class QueryResult(Generic[T]):
    """查询结果包装类"""

    success: bool
    data: T | None = None
    error: Exception | None = None
    query_name: str = ""
    duration_ms: float = 0.0

    def unwrap(self) -> T:
        """解包结果，失败时抛出异常"""
        if not self.success:
            raise self.error or RuntimeError("查询失败")
        if self.data is None:
            raise ValueError("查询结果为空")
        return self.data

    def unwrap_or(self, default: T) -> T:
        """解包结果，失败时返回默认值"""
        if not self.success or self.data is None:
            return default
        return self.data


@dataclass
class QueryTask(Generic[T]):
    """查询任务"""

    name: str
    coroutine: Coroutine[Any, Any, T]
    priority: int = QueryPriority.NORMAL
    timeout: float | None = None
    cache_key: str | None = None
    cache_ttl: int | None = None


async def concurrent_query(
    *coroutines: Coroutine[Any, Any, Any],
    return_exceptions: bool = False,
    timeout: float | None = None,
) -> list[Any]:
    """
    顺序执行多个协程（数据库会话安全）

    注意：由于 SQLAlchemy AsyncSession 不是并发安全的，
    共享同一会话的查询必须顺序执行。

    Args:
        *coroutines: 要执行的协程列表
        return_exceptions: 是否将异常作为结果返回，而非抛出
        timeout: 整体超时时间（秒）

    Returns:
        结果列表，顺序与输入协程顺序一致
    """
    if not coroutines:
        return []

    results: list[Any] = []
    start_time = time.time()

    try:
        for coro in coroutines:
            if timeout is not None and (time.time() - start_time) > timeout:
                raise TimeoutError(f"并发查询超时: {timeout}秒")
            try:
                results.append(await coro)
            except Exception as e:
                if return_exceptions:
                    results.append(e)
                else:
                    raise
        return results
    except TimeoutError as e:
        logger.error(f"并发查询超时: {timeout}秒")
        if return_exceptions:
            return [e] * len(coroutines)
        raise


async def concurrent_query_typed(
    *coroutines: Coroutine[Any, Any, Any],
    return_exceptions: bool = False,
    timeout: float | None = None,
) -> tuple[Any, ...]:
    """
    并行执行多个协程并返回元组

    与 concurrent_query 类似，但返回类型化的元组，便于解包。

    Args:
        *coroutines: 要执行的协程列表
        return_exceptions: 是否将异常作为结果返回
        timeout: 整体超时时间（秒）

    Returns:
        结果元组，顺序与输入协程顺序一致

    Example:
        >>> user, posts, comments = await concurrent_query_typed(
        ...     get_user(user_id),
        ...     get_posts(user_id),
        ...     get_comments(user_id),
        ... )
    """
    results = await concurrent_query(
        *coroutines, return_exceptions=return_exceptions, timeout=timeout
    )
    return tuple(results)


class QueryBatch(Generic[T]):
    """
    批量查询构建器

    支持添加多个查询任务，设置查询优先级和缓存。

    Example:
        >>> batch = QueryBatch()
        >>> batch.add("user", get_user(user_id), priority=QueryPriority.HIGH)
        >>> batch.add("posts", get_posts(user_id), cache_key="user_posts")
        >>> results = await batch.execute()
        >>> user = results["user"]
    """

    def __init__(self, default_timeout: float | None = None):
        self._tasks: dict[str, QueryTask[Any]] = {}
        self.default_timeout = default_timeout

    def add(
        self,
        name: str,
        coroutine: Coroutine[Any, Any, Any],
        priority: int = QueryPriority.NORMAL,
        timeout: float | None = None,
        cache_key: str | None = None,
        cache_ttl: int | None = None,
    ) -> "QueryBatch[Any]":
        """
        添加查询任务

        Args:
            name: 任务名称，用于结果索引
            coroutine: 要执行的协程
            priority: 查询优先级
            timeout: 任务超时时间
            cache_key: 缓存键
            cache_ttl: 缓存时间（秒）

        Returns:
            self，支持链式调用
        """
        self._tasks[name] = QueryTask(
            name=name,
            coroutine=coroutine,
            priority=priority,
            timeout=timeout or self.default_timeout,
            cache_key=cache_key,
            cache_ttl=cache_ttl,
        )
        return self

    def remove(self, name: str) -> "QueryBatch[Any]":
        """移除查询任务"""
        if name in self._tasks:
            del self._tasks[name]
        return self

    def clear(self) -> "QueryBatch[Any]":
        """清空所有任务"""
        self._tasks.clear()
        return self

    def get_task_names(self) -> list[str]:
        """获取所有任务名称"""
        return list(self._tasks.keys())

    def __len__(self) -> int:
        return len(self._tasks)

    def __contains__(self, name: str) -> bool:
        return name in self._tasks


class ConcurrentQueryExecutor:
    """
    并发查询执行器

    提供批量并行查询支持，包含超时控制、错误处理、日志记录和缓存。

    Example:
        >>> executor = ConcurrentQueryExecutor(timeout=30.0)
        >>> batch = QueryBatch()
        >>> batch.add("user", get_user(user_id))
        >>> batch.add("posts", get_posts(user_id))
        >>> results = await executor.execute_batch(batch)
        >>> print(results["user"].data)
    """

    def __init__(
        self,
        default_timeout: float = 30.0,
        max_concurrent: int = 10,
        enable_cache: bool = True,
    ):
        """
        初始化执行器

        Args:
            default_timeout: 默认超时时间（秒）
            max_concurrent: 最大并发数
            enable_cache: 是否启用缓存
        """
        self.default_timeout = default_timeout
        self.max_concurrent = max_concurrent
        self.enable_cache = enable_cache
        self._semaphore = asyncio.Semaphore(max_concurrent)

    async def execute_single(
        self,
        coroutine: Coroutine[Any, Any, Any],
        timeout: float | None = None,
        cache_key: str | None = None,
        cache_ttl: int | None = None,
    ) -> QueryResult[Any]:
        """
        执行单个查询

        Args:
            coroutine: 要执行的协程
            timeout: 超时时间
            cache_key: 缓存键
            cache_ttl: 缓存时间

        Returns:
            QueryResult 包装的查询结果
        """
        start_time = time.perf_counter()
        timeout = timeout or self.default_timeout

        if cache_key and self.enable_cache:
            cached = await cache.get(cache_key)
            if cached is not None:
                duration_ms = (time.perf_counter() - start_time) * 1000
                return QueryResult(
                    success=True,
                    data=cached,
                    query_name="cached",
                    duration_ms=duration_ms,
                )

        try:
            async with self._semaphore:
                if timeout:
                    result = await asyncio.wait_for(coroutine, timeout=timeout)
                else:
                    result = await coroutine

            if cache_key and self.enable_cache and result is not None:
                await cache.set(cache_key, result, ttl=cache_ttl)

            duration_ms = (time.perf_counter() - start_time) * 1000
            return QueryResult(
                success=True,
                data=result,
                duration_ms=duration_ms,
            )

        except TimeoutError as e:
            duration_ms = (time.perf_counter() - start_time) * 1000
            logger.warning(f"查询超时: {timeout}秒")
            return QueryResult(
                success=False,
                error=e,
                duration_ms=duration_ms,
            )
        except Exception as e:
            duration_ms = (time.perf_counter() - start_time) * 1000
            logger.error(f"查询执行失败: {e}")
            return QueryResult(
                success=False,
                error=e,
                duration_ms=duration_ms,
            )

    async def execute_batch(
        self,
        batch: QueryBatch[Any],
        fail_fast: bool = False,
    ) -> dict[str, QueryResult[Any]]:
        """
        执行批量查询

        按优先级排序后并行执行所有任务。

        Args:
            batch: 查询批次
            fail_fast: 是否在第一个失败时立即返回

        Returns:
            任务名称到结果的映射
        """
        if not batch._tasks:
            return {}

        sorted_tasks = sorted(
            batch._tasks.items(),
            key=lambda x: x[1].priority,
            reverse=True,
        )

        async def execute_task(name: str, task: QueryTask[Any]) -> tuple[str, QueryResult[Any]]:
            result = await self.execute_single(
                task.coroutine,
                timeout=task.timeout,
                cache_key=task.cache_key,
                cache_ttl=task.cache_ttl,
            )
            result.query_name = name
            return name, result

        coroutines = [execute_task(name, task) for name, task in sorted_tasks]

        if fail_fast:
            results = await asyncio.gather(*coroutines, return_exceptions=False)
        else:
            results = await asyncio.gather(*coroutines, return_exceptions=True)

        output: dict[str, QueryResult[Any]] = {}
        for item in results:
            if isinstance(item, Exception):
                logger.error(f"批量查询任务异常: {item}")
                continue
            name, result = item
            output[name] = result

        return output

    async def execute_batch_simple(
        self,
        batch: QueryBatch[Any],
    ) -> dict[str, Any]:
        """
        简化版批量查询执行

        直接返回数据，失败时返回 None。

        Args:
            batch: 查询批次

        Returns:
            任务名称到数据的映射
        """
        results = await self.execute_batch(batch)
        return {name: result.data for name, result in results.items()}

    async def execute_with_callback(
        self,
        batch: QueryBatch[Any],
        callback: Callable[[str, QueryResult[Any]], Awaitable[None]],
    ) -> dict[str, QueryResult[Any]]:
        """
        执行批量查询并逐个回调

        每个任务完成后立即调用回调函数，适用于流式处理场景。

        Args:
            batch: 查询批次
            callback: 回调函数，接收任务名称和结果

        Returns:
            任务名称到结果的映射
        """
        if not batch._tasks:
            return {}

        results: dict[str, QueryResult[Any]] = {}

        async def execute_and_callback(name: str, task: QueryTask[Any]) -> None:
            result = await self.execute_single(
                task.coroutine,
                timeout=task.timeout,
                cache_key=task.cache_key,
                cache_ttl=task.cache_ttl,
            )
            result.query_name = name
            results[name] = result
            await callback(name, result)

        tasks = [execute_and_callback(name, task) for name, task in batch._tasks.items()]
        await asyncio.gather(*tasks, return_exceptions=True)

        return results


default_executor = ConcurrentQueryExecutor()


async def execute_concurrent(
    *coroutines: Coroutine[Any, Any, Any],
    timeout: float | None = None,
) -> list[QueryResult[Any]]:
    """
    快捷并发执行函数

    使用默认执行器并行执行多个协程。

    Args:
        *coroutines: 要执行的协程列表
        timeout: 整体超时时间

    Returns:
        QueryResult 列表
    """
    batch: QueryBatch[Any] = QueryBatch()
    for i, coro in enumerate(coroutines):
        batch.add(f"task_{i}", coro, timeout=timeout)

    results = await default_executor.execute_batch(batch)
    return [results[f"task_{i}"] for i in range(len(coroutines))]
