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
    >>> from backend.services import PostService, UserService
    >>> from backend.core.database import get_db
    >>>
    >>> @router.get("/posts/{post_id}")
    >>> async def get_post(
    ...     post_id: int,
    ...     service: PostService = Depends(get_post_service),
    ... ):
    ...     post = await service.get_post_detail(post_id)
    ...     return post
"""

from typing import Annotated

from fastapi import Depends

from backend.services.cache_service import CacheService, get_cache_service
from backend.services.post_service import PostService, get_post_service
from backend.services.recommendation import RecommendationService, get_recommendation_service
from backend.services.user_service import UserService, get_user_service

__all__ = [
    "CacheService",
    "PostService",
    "RecommendationService",
    "UserService",
    "get_cache_service",
    "get_post_service",
    "get_recommendation_service",
    "get_user_service",
    "CacheServiceDep",
    "PostServiceDep",
    "RecommendationServiceDep",
    "UserServiceDep",
]


CacheServiceDep = Annotated[CacheService, Depends(get_cache_service)]
PostServiceDep = Annotated[PostService, Depends(get_post_service)]
RecommendationServiceDep = Annotated[RecommendationService, Depends(get_recommendation_service)]
UserServiceDep = Annotated[UserService, Depends(get_user_service)]
