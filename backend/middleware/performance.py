"""
性能监控中间件

记录每个请求的响应时间，按采样策略异步写入 PerformanceMetric 表。

采样策略：
- 10% 概率随机采样普通请求
- 所有响应时间超过 500ms 的慢请求全部记录

写入不阻塞响应：`call_next` 之后把这一条指标丢给后台任务（有界 in-flight 集合），
中间件立刻返回。原先是 `await session.commit()`，等于每次采样都要多付一次
连接池取还 + INSERT 往返——10% 的请求变慢，而"慢请求"本来就已经慢了还要再加一截。
写入失败只记 warning，绝不影响响应；积压超过上限时丢弃本次采样（宁可少一条指标，
也不让后台任务无限堆在内存里）。
"""

import asyncio
import logging
import random
import time

from fastapi import Request

from backend.models.performance_metric import PerformanceMetric

logger = logging.getLogger(__name__)

# 采样配置
SAMPLE_RATE = 0.1  # 10% 采样
SLOW_REQUEST_THRESHOLD_MS = 500  # 慢请求阈值

# 同时在飞的后台写入上限。DB 抖动时 in-flight 会堆起来，超过上限就丢弃采样：
# 指标是尽力而为的数据，不值得让它把事件循环的内存吃满。
_MAX_INFLIGHT = 32
_inflight: set[asyncio.Task] = set()


async def _persist(payload: dict) -> None:
    """把一条采样落库。异常只记日志（中间件不得影响主流程）。"""
    # 延迟导入以避免 setup_engine 重赋值导致的过期引用
    from backend.core.database import async_session_maker

    try:
        async with async_session_maker() as session:
            session.add(PerformanceMetric(**payload))
            await session.commit()
    except Exception as e:  # noqa: BLE001 - 指标写入失败不影响业务
        logger.warning(f"性能指标记录失败: {e}")


def _dispatch(payload: dict) -> None:
    """把一次采样交给后台任务（不 await）。"""
    if len(_inflight) >= _MAX_INFLIGHT:
        logger.debug("性能指标写入积压已达上限，丢弃本次采样")
        return
    try:
        task = asyncio.create_task(_persist(payload))
    except RuntimeError:
        # 没有运行中的事件循环（同步上下文 / 关闭阶段）：直接放弃这次采样
        return
    _inflight.add(task)
    task.add_done_callback(_inflight.discard)


async def performance_middleware(request: Request, call_next):
    """性能监控中间件

    记录请求响应时间，按采样策略写入数据库。
    中间件出错不影响主流程。
    """
    start_time = time.time()
    response = await call_next(request)
    duration_ms = int((time.time() - start_time) * 1000)

    # OOBE 未完成时数据库尚未就绪（DATABASE_URL 由用户在向导里填写），
    # performance_metrics 表不存在，写库只会每批刷 OperationalError——直接跳过。
    from backend.core.deps import is_oobe_complete

    if not is_oobe_complete():
        return response

    # 采样策略：所有 >500ms 的请求 或 10% 概率的普通请求
    should_record = duration_ms > SLOW_REQUEST_THRESHOLD_MS or random.random() < SAMPLE_RATE

    if should_record:
        client_ip = request.client.host if request.client else None
        user_agent = request.headers.get("User-Agent")
        if user_agent and len(user_agent) > 500:
            user_agent = user_agent[:500]
        endpoint = request.url.path
        if len(endpoint) > 500:
            endpoint = endpoint[:500]

        _dispatch(
            {
                "endpoint": endpoint,
                "method": request.method,
                "status_code": response.status_code,
                "response_time_ms": duration_ms,
                "user_agent": user_agent,
                "ip": client_ip,
            }
        )

    return response
