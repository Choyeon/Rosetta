"""
Rosetta FastAPI 后端 - 后台任务管理模块

提供后台任务管理功能，包括：
- 任务状态追踪
- 任务队列管理
- 任务执行和重试
- 任务超时处理

Example:
    >>> from backend.core.tasks import background_task, task_manager
    >>>
    >>> @background_task(name="send_email", max_retries=3)
    >>> async def send_email_task(to: str, subject: str, body: str):
    >>>     # 发送邮件逻辑
    >>>     pass
    >>>
    >>> # 执行任务
    >>> task_id = await send_email_task("user@example.com", "主题", "内容")
    >>> # 查询任务状态
    >>> status = task_manager.get_task_status(task_id)
"""

import asyncio
import functools
import logging
import uuid
from collections.abc import Callable, Coroutine
from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from typing import Any, TypeVar

logger = logging.getLogger(__name__)

T = TypeVar("T")


class TaskStatus(StrEnum):
    """
    任务状态枚举

    Attributes:
        PENDING: 等待执行
        RUNNING: 正在执行
        COMPLETED: 执行完成
        FAILED: 执行失败
        TIMEOUT: 执行超时
        CANCELLED: 已取消
    """

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    TIMEOUT = "timeout"
    CANCELLED = "cancelled"


@dataclass
class TaskResult:
    """
    任务执行结果数据类

    Attributes:
        task_id: 任务唯一标识
        name: 任务名称
        status: 任务状态
        result: 执行结果（成功时）
        error: 错误信息（失败时）
        created_at: 创建时间
        started_at: 开始执行时间
        completed_at: 完成时间
        retries: 重试次数
        max_retries: 最大重试次数
        timeout: 超时时间（秒）
        metadata: 任务元数据
    """

    task_id: str
    name: str
    status: TaskStatus = TaskStatus.PENDING
    result: Any = None
    error: str | None = None
    created_at: datetime = field(default_factory=datetime.now)
    started_at: datetime | None = None
    completed_at: datetime | None = None
    retries: int = 0
    max_retries: int = 3
    timeout: float | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def duration(self) -> float | None:
        """
        计算任务执行时长

        Returns:
            float | None: 执行时长（秒），如果任务未完成则返回 None
        """
        if self.started_at and self.completed_at:
            return (self.completed_at - self.started_at).total_seconds()
        return None

    @property
    def is_finished(self) -> bool:
        """
        检查任务是否已完成（包括成功、失败、超时、取消）

        Returns:
            bool: 任务是否已完成
        """
        return self.status in (
            TaskStatus.COMPLETED,
            TaskStatus.FAILED,
            TaskStatus.TIMEOUT,
            TaskStatus.CANCELLED,
        )

    def to_dict(self) -> dict[str, Any]:
        """
        转换为字典格式

        Returns:
            dict: 任务结果字典
        """
        return {
            "task_id": self.task_id,
            "name": self.name,
            "status": self.status.value,
            "result": self.result,
            "error": self.error,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": (self.completed_at.isoformat() if self.completed_at else None),
            "duration": self.duration,
            "retries": self.retries,
            "max_retries": self.max_retries,
            "timeout": self.timeout,
            "metadata": self.metadata,
        }


class BackgroundTaskManager:
    """
    后台任务管理器

    管理后台任务的执行、状态追踪和重试机制。

    Attributes:
        max_concurrent_tasks: 最大并发任务数
        default_timeout: 默认超时时间（秒）
        default_max_retries: 默认最大重试次数
        retry_delay: 重试延迟（秒）

    Example:
        >>> manager = BackgroundTaskManager()
        >>> task_id = await manager.submit(my_task, arg1, arg2)
        >>> status = manager.get_task_status(task_id)
    """

    def __init__(
        self,
        max_concurrent_tasks: int = 100,
        default_timeout: float = 300.0,
        default_max_retries: int = 3,
        retry_delay: float = 1.0,
    ):
        self.max_concurrent_tasks = max_concurrent_tasks
        self.default_timeout = default_timeout
        self.default_max_retries = default_max_retries
        self.retry_delay = retry_delay

        self._tasks: dict[str, TaskResult] = {}
        self._running_tasks: dict[str, asyncio.Task] = {}
        self._registered_functions: dict[str, Callable] = {}
        self._lock = asyncio.Lock()

    def register_function(self, name: str, func: Callable) -> None:
        """
        注册任务函数

        Args:
            name: 任务名称
            func: 任务函数
        """
        self._registered_functions[name] = func
        logger.debug(f"注册后台任务函数: {name}")

    def get_registered_functions(self) -> list[str]:
        """
        获取所有已注册的任务函数名称

        Returns:
            list[str]: 任务函数名称列表
        """
        return list(self._registered_functions.keys())

    async def submit(
        self,
        func: Callable[..., Coroutine[Any, Any, T]],
        *args: Any,
        name: str | None = None,
        timeout: float | None = None,
        max_retries: int | None = None,
        metadata: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> str:
        """
        提交任务到队列

        Args:
            func: 要执行的异步函数
            *args: 位置参数
            name: 任务名称（默认使用函数名）
            timeout: 超时时间（秒）
            max_retries: 最大重试次数
            metadata: 任务元数据
            **kwargs: 关键字参数

        Returns:
            str: 任务 ID
        """
        task_id = str(uuid.uuid4())
        task_name = name or func.__name__

        task_result = TaskResult(
            task_id=task_id,
            name=task_name,
            timeout=timeout or self.default_timeout,
            max_retries=max_retries or self.default_max_retries,
            metadata=metadata or {},
        )

        async with self._lock:
            self._tasks[task_id] = task_result

        async def run_task() -> None:
            """执行任务的内部函数"""
            await self._execute_task(task_id, func, *args, **kwargs)

        task = asyncio.create_task(run_task())
        self._running_tasks[task_id] = task

        task.add_done_callback(lambda t: self._cleanup_task(task_id))

        logger.info(f"提交后台任务: {task_name} (ID: {task_id})")
        return task_id

    async def _execute_task(
        self,
        task_id: str,
        func: Callable[..., Coroutine[Any, Any, T]],
        *args: Any,
        **kwargs: Any,
    ) -> None:
        """
        执行任务（内部方法）

        Args:
            task_id: 任务 ID
            func: 要执行的函数
            *args: 位置参数
            **kwargs: 关键字参数
        """
        task_result = self._tasks.get(task_id)
        if not task_result:
            return

        task_result.status = TaskStatus.RUNNING
        task_result.started_at = datetime.now()

        while task_result.retries <= task_result.max_retries:
            try:
                if task_result.timeout:
                    result = await asyncio.wait_for(
                        func(*args, **kwargs),
                        timeout=task_result.timeout,
                    )
                else:
                    result = await func(*args, **kwargs)

                task_result.result = result
                task_result.status = TaskStatus.COMPLETED
                task_result.completed_at = datetime.now()
                logger.info(
                    f"任务执行成功: {task_result.name} (ID: {task_id}, "
                    f"耗时: {task_result.duration:.2f}s)"
                )
                return

            except TimeoutError:
                task_result.status = TaskStatus.TIMEOUT
                task_result.error = f"任务执行超时（{task_result.timeout}秒）"
                task_result.completed_at = datetime.now()
                logger.warning(f"任务执行超时: {task_result.name} (ID: {task_id})")
                return

            except asyncio.CancelledError:
                task_result.status = TaskStatus.CANCELLED
                task_result.error = "任务被取消"
                task_result.completed_at = datetime.now()
                logger.info(f"任务被取消: {task_result.name} (ID: {task_id})")
                return

            except Exception as e:
                task_result.retries += 1
                task_result.error = str(e)

                if task_result.retries <= task_result.max_retries:
                    logger.warning(
                        f"任务执行失败，准备重试: {task_result.name} "
                        f"(ID: {task_id}, 重试: {task_result.retries}/{task_result.max_retries}), "
                        f"错误: {e}"
                    )
                    await asyncio.sleep(self.retry_delay * task_result.retries)
                else:
                    task_result.status = TaskStatus.FAILED
                    task_result.completed_at = datetime.now()
                    logger.error(
                        f"任务执行失败（已重试{task_result.max_retries}次）: "
                        f"{task_result.name} (ID: {task_id}), 错误: {e}"
                    )
                    return

    def _cleanup_task(self, task_id: str) -> None:
        """
        清理已完成的任务

        Args:
            task_id: 任务 ID
        """
        if task_id in self._running_tasks:
            del self._running_tasks[task_id]

    def get_task_status(self, task_id: str) -> TaskResult | None:
        """
        获取任务状态

        Args:
            task_id: 任务 ID

        Returns:
            TaskResult | None: 任务结果，如果任务不存在则返回 None
        """
        return self._tasks.get(task_id)

    def get_all_tasks(
        self,
        status: TaskStatus | None = None,
        limit: int = 100,
    ) -> list[TaskResult]:
        """
        获取所有任务

        Args:
            status: 过滤状态（可选）
            limit: 返回数量限制

        Returns:
            list[TaskResult]: 任务结果列表
        """
        tasks = list(self._tasks.values())

        if status:
            tasks = [t for t in tasks if t.status == status]

        tasks.sort(key=lambda t: t.created_at, reverse=True)
        return tasks[:limit]

    def get_running_tasks(self) -> list[TaskResult]:
        """
        获取正在运行的任务

        Returns:
            list[TaskResult]: 正在运行的任务列表
        """
        return [self._tasks[task_id] for task_id in self._running_tasks if task_id in self._tasks]

    async def cancel_task(self, task_id: str) -> bool:
        """
        取消任务

        Args:
            task_id: 任务 ID

        Returns:
            bool: 是否成功取消
        """
        if task_id not in self._running_tasks:
            return False

        task = self._running_tasks[task_id]
        task.cancel()

        try:
            await task
        except asyncio.CancelledError:
            pass

        return True

    def clear_completed_tasks(self, max_age_hours: int = 24) -> int:
        """
        清理已完成的任务

        Args:
            max_age_hours: 最大保留时间（小时）

        Returns:
            int: 清理的任务数量
        """
        now = datetime.now()
        tasks_to_remove = []

        for task_id, task_result in self._tasks.items():
            if task_result.is_finished and task_result.completed_at:
                age_hours = (now - task_result.completed_at).total_seconds() / 3600
                if age_hours > max_age_hours:
                    tasks_to_remove.append(task_id)

        for task_id in tasks_to_remove:
            del self._tasks[task_id]

        if tasks_to_remove:
            logger.info(f"清理了 {len(tasks_to_remove)} 个已完成任务")

        return len(tasks_to_remove)

    async def wait_for_task(
        self,
        task_id: str,
        timeout: float | None = None,
    ) -> TaskResult | None:
        """
        等待任务完成

        Args:
            task_id: 任务 ID
            timeout: 等待超时时间（秒）

        Returns:
            TaskResult | None: 任务结果，如果超时则返回 None
        """
        if task_id not in self._tasks:
            return None

        task_result = self._tasks[task_id]

        start_time = datetime.now()
        while not task_result.is_finished:
            if timeout:
                elapsed = (datetime.now() - start_time).total_seconds()
                if elapsed > timeout:
                    return None
            await asyncio.sleep(0.1)

        return task_result

    @property
    def stats(self) -> dict[str, int]:
        """
        获取任务统计信息

        Returns:
            dict: 统计信息
        """
        tasks = list(self._tasks.values())
        return {
            "total": len(tasks),
            "pending": sum(1 for t in tasks if t.status == TaskStatus.PENDING),
            "running": sum(1 for t in tasks if t.status == TaskStatus.RUNNING),
            "completed": sum(1 for t in tasks if t.status == TaskStatus.COMPLETED),
            "failed": sum(1 for t in tasks if t.status == TaskStatus.FAILED),
            "timeout": sum(1 for t in tasks if t.status == TaskStatus.TIMEOUT),
            "cancelled": sum(1 for t in tasks if t.status == TaskStatus.CANCELLED),
        }

    async def shutdown(self, timeout: float = 10.0) -> None:
        """
        关闭任务管理器

        取消所有正在运行的任务并等待它们完成。

        Args:
            timeout: 等待任务完成的最长时间（秒）
        """
        logger.info(f"正在关闭后台任务管理器，{len(self._running_tasks)} 个任务正在运行")

        for task_id, task in list(self._running_tasks.items()):
            task.cancel()

        if self._running_tasks:
            try:
                await asyncio.wait_for(
                    asyncio.gather(*self._running_tasks.values(), return_exceptions=True),
                    timeout=timeout,
                )
            except TimeoutError:
                logger.warning(f"关闭任务管理器超时，{len(self._running_tasks)} 个任务未完成")

        self._tasks.clear()
        self._running_tasks.clear()
        logger.info("后台任务管理器已关闭")


task_manager = BackgroundTaskManager()


def background_task(
    name: str | None = None,
    timeout: float | None = None,
    max_retries: int = 3,
    metadata: dict[str, Any] | None = None,
) -> Callable:
    """
    后台任务装饰器

    将异步函数注册为后台任务，支持自动提交到任务队列。

    Args:
        name: 任务名称（默认使用函数名）
        timeout: 超时时间（秒）
        max_retries: 最大重试次数
        metadata: 任务元数据

    Returns:
        Callable: 装饰后的函数

    Example:
        >>> @background_task(name="send_email", max_retries=3)
        >>> async def send_email_task(to: str, subject: str, body: str):
        >>>     # 发送邮件逻辑
        >>>     pass
        >>>
        >>> # 执行任务
        >>> task_id = await send_email_task("user@example.com", "主题", "内容")
    """

    def decorator(func: Callable[..., Coroutine[Any, Any, T]]) -> Callable:
        task_name = name or func.__name__

        task_manager.register_function(task_name, func)

        @functools.wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> str:
            return await task_manager.submit(
                func,
                *args,
                name=task_name,
                timeout=timeout,
                max_retries=max_retries,
                metadata=metadata,
                **kwargs,
            )

        wrapper._is_background_task = True
        wrapper._task_name = task_name

        return wrapper

    return decorator
