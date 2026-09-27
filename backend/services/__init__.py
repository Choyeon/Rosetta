"""
Rosetta FastAPI 后端 - 服务层

提供业务逻辑层的抽象，将业务逻辑与数据访问分离。

服务层职责：
- 封装业务逻辑
- 协调多个仓储的操作
- 集成缓存
- 提供事务管理
- 支持依赖注入

Example:
    >>> from backend.services import UserService
    >>> from backend.core.database import get_db
    >>>
    >>> @router.get("/users/{user_id}")
    >>> async def get_user(
    ...     user_id: int,
    ...     service: UserService = Depends(get_user_service),
    ... ):
    ...     user = await service.get_user_detail(user_id)
    ...     return user
"""

from typing import Annotated

from fastapi import Depends

from backend.services.cache_service import CacheService, get_cache_service
from backend.services.recommendation import RecommendationService, get_recommendation_service
from backend.services.user_service import UserService, get_user_service

__all__ = [
    "CacheService",
    "RecommendationService",
    "UserService",
    "get_cache_service",
    "get_recommendation_service",
    "get_user_service",
    "CacheServiceDep",
    "RecommendationServiceDep",
    "UserServiceDep",
]


CacheServiceDep = Annotated[CacheService, Depends(get_cache_service)]
RecommendationServiceDep = Annotated[RecommendationService, Depends(get_recommendation_service)]
UserServiceDep = Annotated[UserService, Depends(get_user_service)]
