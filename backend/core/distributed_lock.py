"""
分布式锁模块

基于 Redis 实现的分布式锁，支持：
- 锁超时自动释放
- 锁续期（看门狗）
- 可重入锁
- 上下文管理器
- 装饰器模式
"""

import asyncio
import logging
import uuid
from collections.abc import Callable
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from typing import Any, ParamSpec, TypeVar

from backend.core.config import settings

logger = logging.getLogger(__name__)

P = ParamSpec("P")
T = TypeVar("T")


@dataclass
class LockConfig:
    """锁配置"""

    lock_timeout: int = 30
    wait_timeout: int = 10
    retry_interval: float = 0.1
    auto_renewal: bool = True
    renewal_interval: float = 10.0


@dataclass
class LockInfo:
    """锁信息"""

    key: str
    token: str
    holder_id: str
    acquire_time: float
    timeout: int
    renewal_count: int = 0
    renewal_task: asyncio.Task | None = field(default=None, repr=False)


class DistributedLock:
    """
    分布式锁实现

    基于 Redis SET NX EX 命令实现分布式锁，支持：
    - 锁超时自动释放（防止死锁）
    - 锁续期（看门狗机制）
    - 可重入锁（同一线程可多次获取）
    """

    LOCK_PREFIX = "distributed_lock:"

    def __init__(
        self,
        key: str,
        timeout: int = 30,
        auto_renewal: bool = True,
        renewal_interval: float = 10.0,
    ):
        """
        初始化分布式锁

        Args:
            key: 锁的唯一标识
            timeout: 锁超时时间（秒）
            auto_renewal: 是否自动续期
            renewal_interval: 续期间隔（秒）
        """
        self.key = f"{self.LOCK_PREFIX}{key}"
        self.timeout = timeout
        self.auto_renewal = auto_renewal and timeout > renewal_interval
        self.renewal_interval = renewal_interval
        self.token = str(uuid.uuid4())
        self.holder_id = f"{id(self)}:{self.token}"
        self._lock_info: LockInfo | None = None
        self._renewal_task: asyncio.Task | None = None
        self._reentrant_count = 0
        self._client = None

    async def _get_client(self):
        """获取 Redis 客户端"""
        if self._client is None:
            if not settings.redis_enabled:
                raise RuntimeError("分布式锁需要启用 Redis，请在配置中设置 redis_enabled=True")
            import redis.asyncio as redis

            self._client = redis.from_url(
                settings.redis_url,
                encoding="utf-8",
                decode_responses=True,
            )
        return self._client

    async def acquire(self, wait_timeout: int = 10, retry_interval: float = 0.1) -> bool:
        """
        获取锁

        Args:
            wait_timeout: 等待超时时间（秒）
            retry_interval: 重试间隔（秒）

        Returns:
            是否成功获取锁
        """
        client = await self._get_client()

        if self._reentrant_count > 0:
            self._reentrant_count += 1
            logger.debug(f"可重入锁获取成功: {self.key}, 计数: {self._reentrant_count}")
            return True

        import time

        start_time = time.time()
        wait_timeout = max(0, wait_timeout)

        while True:
            acquired = await client.set(self.key, self.holder_id, ex=self.timeout, nx=True)

            if acquired:
                self._reentrant_count = 1
                self._lock_info = LockInfo(
                    key=self.key,
                    token=self.token,
                    holder_id=self.holder_id,
                    acquire_time=time.time(),
                    timeout=self.timeout,
                )

                if self.auto_renewal:
                    self._start_renewal_task()

                logger.debug(f"锁获取成功: {self.key}, 超时: {self.timeout}s")
                return True

            if time.time() - start_time >= wait_timeout:
                logger.warning(f"锁获取超时: {self.key}, 等待时间: {wait_timeout}s")
                return False

            await asyncio.sleep(retry_interval)

    async def release(self) -> bool:
        """
        释放锁

        Returns:
            是否成功释放锁
        """
        if self._reentrant_count > 1:
            self._reentrant_count -= 1
            logger.debug(f"可重入锁释放（计数减少）: {self.key}, 剩余计数: {self._reentrant_count}")
            return True

        if self._reentrant_count == 0:
            logger.warning(f"尝试释放未持有的锁: {self.key}")
            return False

        self._stop_renewal_task()

        client = await self._get_client()

        lua_script = """
        if redis.call("get", KEYS[1]) == ARGV[1] then
            return redis.call("del", KEYS[1])
        else
            return 0
        end
        """

        result = await client.eval(lua_script, 1, self.key, self.holder_id)

        self._reentrant_count = 0
        self._lock_info = None

        if result:
            logger.debug(f"锁释放成功: {self.key}")
            return True
        else:
            logger.warning(f"锁释放失败（可能已过期或被其他持有者释放）: {self.key}")
            return False

    async def renew(self) -> bool:
        """
        续期锁

        Returns:
            是否成功续期
        """
        if not self._lock_info:
            return False

        client = await self._get_client()

        lua_script = """
        if redis.call("get", KEYS[1]) == ARGV[1] then
            return redis.call("expire", KEYS[1], ARGV[2])
        else
            return 0
        end
        """

        result = await client.eval(lua_script, 1, self.key, self.holder_id, self.timeout)

        if result:
            self._lock_info.renewal_count += 1
            logger.debug(f"锁续期成功: {self.key}, 续期次数: {self._lock_info.renewal_count}")
            return True
        else:
            logger.warning(f"锁续期失败: {self.key}")
            return False

    def _start_renewal_task(self):
        """启动续期任务"""

        async def renewal_loop():
            while self._reentrant_count > 0:
                try:
                    await asyncio.sleep(self.renewal_interval)
                    if self._reentrant_count > 0:
                        await self.renew()
                except asyncio.CancelledError:
                    break
                except Exception as e:
                    logger.error(f"锁续期任务异常: {self.key}, 错误: {e}")
                    break

        self._renewal_task = asyncio.create_task(renewal_loop())

    def _stop_renewal_task(self):
        """停止续期任务"""
        if self._renewal_task and not self._renewal_task.done():
            self._renewal_task.cancel()
            self._renewal_task = None

    async def is_locked(self) -> bool:
        """
        检查锁是否被持有

        Returns:
            锁是否被持有
        """
        client = await self._get_client()
        holder = await client.get(self.key)
        return holder is not None

    async def get_holder(self) -> str | None:
        """
        获取当前锁持有者

        Returns:
            锁持有者标识，如果锁未被持有则返回 None
        """
        client = await self._get_client()
        return await client.get(self.key)

    async def __aenter__(self) -> "DistributedLock":
        """异步上下文管理器入口"""
        acquired = await self.acquire()
        if not acquired:
            raise TimeoutError(f"获取锁超时: {self.key}")
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """异步上下文管理器出口"""
        await self.release()
        return False

    async def close(self):
        """关闭 Redis 连接"""
        if self._client:
            await self._client.close()
            self._client = None


class LockManager:
    """
    锁管理器

    提供锁的统一管理，支持：
    - 锁的获取和释放
    - 上下文管理器
    - 装饰器模式
    """

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._initialized = True
        self._locks: dict[str, DistributedLock] = {}
        self._default_config = LockConfig()

    def get_lock(
        self,
        key: str,
        timeout: int | None = None,
        auto_renewal: bool | None = None,
        renewal_interval: float | None = None,
    ) -> DistributedLock:
        """
        获取或创建锁实例

        Args:
            key: 锁的唯一标识
            timeout: 锁超时时间
            auto_renewal: 是否自动续期
            renewal_interval: 续期间隔

        Returns:
            分布式锁实例
        """
        if key in self._locks:
            return self._locks[key]

        lock = DistributedLock(
            key=key,
            timeout=timeout or self._default_config.lock_timeout,
            auto_renewal=auto_renewal
            if auto_renewal is not None
            else self._default_config.auto_renewal,
            renewal_interval=renewal_interval or self._default_config.renewal_interval,
        )
        self._locks[key] = lock
        return lock

    @asynccontextmanager
    async def lock(
        self,
        key: str,
        timeout: int | None = None,
        wait_timeout: int | None = None,
        retry_interval: float | None = None,
        auto_renewal: bool | None = None,
    ):
        """
        上下文管理器方式获取锁

        Args:
            key: 锁的唯一标识
            timeout: 锁超时时间
            wait_timeout: 等待超时时间
            retry_interval: 重试间隔
            auto_renewal: 是否自动续期

        Yields:
            分布式锁实例

        Raises:
            TimeoutError: 获取锁超时

        Example:
            async with lock_manager.lock("my_resource", timeout=30):
                # 执行需要保护的代码
                pass
        """
        lock = self.get_lock(key, timeout=timeout, auto_renewal=auto_renewal)

        acquired = await lock.acquire(
            wait_timeout=wait_timeout or self._default_config.wait_timeout,
            retry_interval=retry_interval or self._default_config.retry_interval,
        )

        if not acquired:
            raise TimeoutError(f"获取锁超时: {key}")

        try:
            yield lock
        finally:
            await lock.release()

    async def try_lock(
        self,
        key: str,
        timeout: int | None = None,
        auto_renewal: bool | None = None,
    ) -> DistributedLock | None:
        """
        尝试获取锁（不等待）

        Args:
            key: 锁的唯一标识
            timeout: 锁超时时间
            auto_renewal: 是否自动续期

        Returns:
            成功返回锁实例，失败返回 None
        """
        lock = self.get_lock(key, timeout=timeout, auto_renewal=auto_renewal)
        acquired = await lock.acquire(wait_timeout=0)
        return lock if acquired else None

    async def is_locked(self, key: str) -> bool:
        """
        检查锁是否被持有

        Args:
            key: 锁的唯一标识

        Returns:
            锁是否被持有
        """
        lock = self.get_lock(key)
        return await lock.is_locked()

    async def force_unlock(self, key: str) -> bool:
        """
        强制释放锁（谨慎使用）

        Args:
            key: 锁的唯一标识

        Returns:
            是否成功释放
        """
        lock = self._locks.get(key)
        if lock:
            lock._stop_renewal_task()
            lock._reentrant_count = 0
            lock._lock_info = None

        import redis.asyncio as redis

        client = redis.from_url(settings.redis_url, encoding="utf-8", decode_responses=True)
        try:
            result = await client.delete(f"{DistributedLock.LOCK_PREFIX}{key}")
            return result > 0
        finally:
            await client.close()

    def set_default_config(
        self,
        lock_timeout: int | None = None,
        wait_timeout: int | None = None,
        retry_interval: float | None = None,
        auto_renewal: bool | None = None,
        renewal_interval: float | None = None,
    ):
        """
        设置默认配置

        Args:
            lock_timeout: 默认锁超时时间
            wait_timeout: 默认等待超时时间
            retry_interval: 默认重试间隔
            auto_renewal: 默认是否自动续期
            renewal_interval: 默认续期间隔
        """
        if lock_timeout is not None:
            self._default_config.lock_timeout = lock_timeout
        if wait_timeout is not None:
            self._default_config.wait_timeout = wait_timeout
        if retry_interval is not None:
            self._default_config.retry_interval = retry_interval
        if auto_renewal is not None:
            self._default_config.auto_renewal = auto_renewal
        if renewal_interval is not None:
            self._default_config.renewal_interval = renewal_interval

    async def cleanup(self):
        """清理所有锁"""
        for lock in self._locks.values():
            try:
                if lock._reentrant_count > 0:
                    await lock.release()
                await lock.close()
            except Exception as e:
                logger.error(f"清理锁失败: {lock.key}, 错误: {e}")
        self._locks.clear()


lock_manager = LockManager()


def with_lock(
    key: str | Callable[..., str],
    timeout: int = 30,
    wait_timeout: int = 10,
    retry_interval: float = 0.1,
    auto_renewal: bool = True,
    on_lock_failed: Callable[..., Any] | None = None,
):
    """
    分布式锁装饰器

    用于保护关键代码段，确保同一时间只有一个实例可以执行。

    Args:
        key: 锁的唯一标识，可以是字符串或返回字符串的函数
        timeout: 锁超时时间（秒）
        wait_timeout: 等待超时时间（秒）
        retry_interval: 重试间隔（秒）
        auto_renewal: 是否自动续期
        on_lock_failed: 获取锁失败时的回调函数

    Returns:
        装饰器函数

    Example:
        @with_lock("process_order:{order_id}")
        async def process_order(order_id: str):
            # 处理订单逻辑
            pass

        # 使用函数动态生成锁键
        @with_lock(lambda args, kwargs: f"process_order:{kwargs['order_id']}")
        async def process_order(order_id: str):
            pass

        # 处理锁获取失败
        @with_lock("critical_task", on_lock_failed=lambda: {"error": "系统繁忙"})
        async def critical_task():
            pass
    """

    def decorator(func: Callable[P, T]) -> Callable[P, T]:
        async def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
            if callable(key):
                lock_key = key(args, kwargs)
            else:
                lock_key = key
                for i, arg in enumerate(args):
                    lock_key = lock_key.replace(f"{{{i}}}", str(arg))
                for arg_name, arg_value in kwargs.items():
                    lock_key = lock_key.replace(f"{{{arg_name}}}", str(arg_value))

            try:
                async with lock_manager.lock(
                    key=lock_key,
                    timeout=timeout,
                    wait_timeout=wait_timeout,
                    retry_interval=retry_interval,
                    auto_renewal=auto_renewal,
                ):
                    return await func(*args, **kwargs)
            except TimeoutError:
                logger.warning(f"装饰器获取锁超时: {lock_key}")
                if on_lock_failed is not None:
                    if asyncio.iscoroutinefunction(on_lock_failed):
                        return await on_lock_failed(*args, **kwargs)
                    else:
                        return on_lock_failed(*args, **kwargs)
                raise

        return wrapper

    return decorator


@asynccontextmanager
async def distributed_lock(
    key: str,
    timeout: int = 30,
    wait_timeout: int = 10,
    auto_renewal: bool = True,
):
    """
    分布式锁上下文管理器快捷方式

    Args:
        key: 锁的唯一标识
        timeout: 锁超时时间（秒）
        wait_timeout: 等待超时时间（秒）
        auto_renewal: 是否自动续期

    Yields:
        分布式锁实例

    Example:
        async with distributed_lock("my_resource"):
            # 执行需要保护的代码
            pass
    """
    async with lock_manager.lock(
        key=key,
        timeout=timeout,
        wait_timeout=wait_timeout,
        auto_renewal=auto_renewal,
    ) as lock:
        yield lock
