"""
性能监控中间件

记录每个请求的响应时间，异步写入 PerformanceMetric 表。

采样策略：
- 10% 概率随机采样普通请求
- 所有响应时间超过 500ms 的慢请求全部记录
"""

import logging
import random
import time

from fastapi import Request

from backend.models.performance_metric import PerformanceMetric

logger = logging.getLogger(__name__)

# 采样配置
SAMPLE_RATE = 0.1  # 10% 采样
SLOW_REQUEST_THRESHOLD_MS = 500  # 慢请求阈值


async def performance_middleware(request: Request, call_next):
    """性能监控中间件

    记录请求响应时间，按采样策略写入数据库。
    中间件出错不影响主流程。
    """
    start_time = time.time()
    response = await call_next(request)
    duration_ms = int((time.time() - start_time) * 1000)

    # 采样策略：所有 >500ms 的请求 或 10% 概率的普通请求
    should_record = duration_ms > SLOW_REQUEST_THRESHOLD_MS or random.random() < SAMPLE_RATE

    if should_record:
        try:
            # 延迟导入以避免 setup_engine 重赋值导致的过期引用
            from backend.core.database import async_session_maker

            # 提取客户端信息
            client_ip = request.client.host if request.client else None
            user_agent = request.headers.get("User-Agent")
            if user_agent and len(user_agent) > 500:
                user_agent = user_agent[:500]
            endpoint = request.url.path
            if len(endpoint) > 500:
                endpoint = endpoint[:500]

            async with async_session_maker() as session:
                metric = PerformanceMetric(
                    endpoint=endpoint,
                    method=request.method,
                    status_code=response.status_code,
                    response_time_ms=duration_ms,
                    user_agent=user_agent,
                    ip=client_ip,
                )
                session.add(metric)
                await session.commit()
        except Exception as e:
            # 中间件出错不应影响主流程
            logger.warning(f"性能指标记录失败: {e}")

    return response
