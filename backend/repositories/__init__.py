"""
Rosetta FastAPI 后端 - 仓储层

提供数据访问层的抽象，将数据库操作与业务逻辑分离。

仓储层职责：
- 封装数据库操作
- 提供统一的查询接口
- 支持并发查询优化
- 支持依赖注入

Example:
    >>> from backend.repositories import get_post_repository, get_user_repository
    >>> from backend.core.database import get_db
    >>>
    >>> @router.get("/posts/{post_id}")
    >>> async def get_post(
    ...     post_id: int,
    ...     repo: PostRepository = Depends(get_post_repository),
    ... ):
    ...     post = await repo.get_by_id(post_id)
    ...     return post
"""

from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.database import get_db
from backend.repositories.base import BaseRepository, PaginationResult
from backend.repositories.post import PostRepository
from backend.repositories.user import (
    RefreshTokenRepository,
    UserPreferenceRepository,
    UserRepository,
    UserTitleRepository,
)

__all__ = [
    "BaseRepository",
    "PaginationResult",
    "PostRepository",
    "UserRepository",
    "UserPreferenceRepository",
    "RefreshTokenRepository",
    "UserTitleRepository",
    "get_post_repository",
    "get_user_repository",
    "get_user_preference_repository",
    "get_refresh_token_repository",
    "get_user_title_repository",
    "PostRepositoryDep",
    "UserRepositoryDep",
    "UserPreferenceRepositoryDep",
    "RefreshTokenRepositoryDep",
    "UserTitleRepositoryDep",
]


async def get_post_repository(
    db: AsyncSession = Depends(get_db),
) -> PostRepository:
    """
    获取文章仓储实例（依赖注入）

    Args:
        db: 数据库会话

    Returns:
        PostRepository 实例
    """
    return PostRepository(db)


async def get_user_repository(
    db: AsyncSession = Depends(get_db),
) -> UserRepository:
    """
    获取用户仓储实例（依赖注入）

    Args:
        db: 数据库会话

    Returns:
        UserRepository 实例
    """
    return UserRepository(db)


async def get_user_preference_repository(
    db: AsyncSession = Depends(get_db),
) -> UserPreferenceRepository:
    """
    获取用户偏好设置仓储实例（依赖注入）

    Args:
        db: 数据库会话

    Returns:
        UserPreferenceRepository 实例
    """
    return UserPreferenceRepository(db)


async def get_refresh_token_repository(
    db: AsyncSession = Depends(get_db),
) -> RefreshTokenRepository:
    """
    获取刷新令牌仓储实例（依赖注入）

    Args:
        db: 数据库会话

    Returns:
        RefreshTokenRepository 实例
    """
    return RefreshTokenRepository(db)


async def get_user_title_repository(
    db: AsyncSession = Depends(get_db),
) -> UserTitleRepository:
    """
    获取用户头衔仓储实例（依赖注入）

    Args:
        db: 数据库会话

    Returns:
        UserTitleRepository 实例
    """
    return UserTitleRepository(db)


PostRepositoryDep = Annotated[PostRepository, Depends(get_post_repository)]
UserRepositoryDep = Annotated[UserRepository, Depends(get_user_repository)]
UserPreferenceRepositoryDep = Annotated[
    UserPreferenceRepository, Depends(get_user_preference_repository)
]
RefreshTokenRepositoryDep = Annotated[RefreshTokenRepository, Depends(get_refresh_token_repository)]
UserTitleRepositoryDep = Annotated[UserTitleRepository, Depends(get_user_title_repository)]
