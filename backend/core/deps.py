"""
Rosetta FastAPI 后端 - 依赖注入模块

提供统一的依赖注入配置，包括：
- 数据库会话
- 用户认证
- 分页参数
- 通用过滤条件

Example:
    >>> from backend.core.deps import CurrentUser, DB, PaginationParams
    >>>
    >>> @router.get("/posts")
    >>> async def list_posts(
    >>>     db: DB,
    >>>     user: CurrentUser,
    >>>     pagination: PaginationParams,
    >>> ):
    >>>     pass
"""

from typing import Annotated, TypeVar

from fastapi import Depends, Query
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.auth import (
    get_current_staff,
    get_current_superuser,
    get_current_user,
    get_current_user_optional,
)
from backend.core.database import get_db
from backend.core.paths import CONFIG_FILE, OOBE_LOCK_FILE
from backend.models.user import User

T = TypeVar("T")


DB = Annotated[AsyncSession, Depends(get_db)]
CurrentUser = Annotated[User, Depends(get_current_user)]
CurrentUserOptional = Annotated[User | None, Depends(get_current_user_optional)]
CurrentStaff = Annotated[User, Depends(get_current_staff)]
CurrentSuperUser = Annotated[User, Depends(get_current_superuser)]


def is_oobe_complete() -> bool:
    """全局 OOBE 完成状态判断（供中间件、依赖共用）"""
    return OOBE_LOCK_FILE.exists() and CONFIG_FILE.exists()


class PaginationParams(BaseModel):
    """分页参数"""

    page: int = 1
    page_size: int = 12

    @property
    def offset(self) -> int:
        """计算偏移量"""
        return (self.page - 1) * self.page_size

    @property
    def limit(self) -> int:
        """获取限制数量"""
        return self.page_size


def get_pagination(
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(12, ge=1, le=100, description="每页数量"),
) -> PaginationParams:
    """获取分页参数"""
    return PaginationParams(page=page, page_size=page_size)


Pagination = Annotated[PaginationParams, Depends(get_pagination)]


class SearchParams(BaseModel):
    """搜索参数"""

    query: str | None = None
    order_by: str = "created_at"
    order: str = "desc"


def get_search(
    q: str | None = Query(None, alias="q", description="搜索关键词"),
    order_by: str = Query("created_at", description="排序字段"),
    order: str = Query("desc", pattern="^(asc|desc)$", description="排序方向"),
) -> SearchParams:
    """获取搜索参数"""
    return SearchParams(query=q, order_by=order_by, order=order)


Search = Annotated[SearchParams, Depends(get_search)]


class FilterParams(BaseModel):
    """过滤参数"""

    status: str | None = None
    category: str | None = None
    tag: str | None = None
    start_date: str | None = None
    end_date: str | None = None


def get_filters(
    status: str | None = Query(None, description="状态过滤"),
    category: str | None = Query(None, description="分类过滤"),
    tag: str | None = Query(None, description="标签过滤"),
    start_date: str | None = Query(None, description="开始日期"),
    end_date: str | None = Query(None, description="结束日期"),
) -> FilterParams:
    """获取过滤参数"""
    return FilterParams(
        status=status,
        category=category,
        tag=tag,
        start_date=start_date,
        end_date=end_date,
    )


Filters = Annotated[FilterParams, Depends(get_filters)]


security = HTTPBearer()
security_optional = HTTPBearer(auto_error=False)

Credentials = Annotated[HTTPAuthorizationCredentials, Depends(security)]
CredentialsOptional = Annotated[HTTPAuthorizationCredentials | None, Depends(security_optional)]


from backend.core.csrf import require_csrf  # noqa: E402

RequireCSRF = Annotated[None, Depends(require_csrf)]


async def require_oobe_incomplete():
    """依赖：确保 OOBE 未完成，否则抛出 409 + OOBE_ALREADY_COMPLETED"""
    if is_oobe_complete():
        from backend.core.exceptions import OOBEAlreadyCompletedException

        raise OOBEAlreadyCompletedException()
