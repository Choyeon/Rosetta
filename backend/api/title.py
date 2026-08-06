"""
用户称号管理 API

提供用户称号的 CRUD 操作。
"""

from datetime import datetime

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import func, select, update
from sqlalchemy.orm import selectinload

from backend.core.auth import DB, CurrentStaff, CurrentUser
from backend.models.user import User, UserTitle

router = APIRouter(tags=["用户称号"])


class UserTitleCreate(BaseModel):
    """用户称号创建模型"""

    name: str = Field(..., min_length=1, max_length=50, description="称号名称")
    color: str = Field(default="#3B82F6", description="显示颜色")
    icon: str | None = Field(None, description="图标类名")
    description: str | None = Field(None, max_length=200, description="称号描述")


class UserTitleUpdate(BaseModel):
    """用户称号更新模型"""

    name: str | None = Field(None, min_length=1, max_length=50, description="称号名称")
    color: str | None = Field(None, description="显示颜色")
    icon: str | None = Field(None, description="图标类名")
    description: str | None = Field(None, max_length=200, description="称号描述")


class UserTitleResponse(BaseModel):
    """用户称号响应模型"""

    id: int
    name: str
    color: str
    icon: str | None = None
    description: str | None = None
    created_at: datetime
    users_count: int = 0

    model_config = {"from_attributes": True}


class UserTitleAssign(BaseModel):
    """分配称号模型"""

    user_id: int = Field(..., description="用户ID")
    title_id: int = Field(..., description="称号ID")


# ==================== 称号管理接口 ====================


@router.get(
    "/titles",
    response_model=list[UserTitleResponse],
    summary="称号列表",
    description="获取所有用户称号及其使用数量。",
)
async def get_titles(
    db: DB,
    current_user: CurrentStaff,
):
    """获取所有称号"""
    titles_result = await db.execute(select(UserTitle).order_by(UserTitle.created_at.desc()))
    titles = titles_result.scalars().all()

    title_responses = []
    for title in titles:
        count_result = await db.execute(
            select(func.count()).select_from(User).where(User.title_id == title.id)
        )
        users_count = count_result.scalar() or 0

        title_responses.append(
            UserTitleResponse(
                id=title.id,
                name=title.name,
                color=title.color,
                icon=title.icon,
                description=title.description,
                created_at=title.created_at,
                users_count=users_count,
            )
        )

    return title_responses


@router.post(
    "/titles",
    response_model=UserTitleResponse,
    summary="创建称号",
    description="创建新的用户称号，需要管理员权限。",
)
async def create_title(
    data: UserTitleCreate,
    db: DB,
    current_user: CurrentStaff,
):
    """创建新称号"""
    existing = await db.execute(select(UserTitle).where(UserTitle.name == data.name))
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="称号名称已存在",
        )

    title = UserTitle(
        name=data.name,
        color=data.color,
        icon=data.icon,
        description=data.description,
    )
    db.add(title)
    await db.flush()
    await db.refresh(title)

    return UserTitleResponse(
        id=title.id,
        name=title.name,
        color=title.color,
        icon=title.icon,
        description=title.description,
        created_at=title.created_at,
        users_count=0,
    )


@router.get(
    "/titles/{title_id}",
    response_model=UserTitleResponse,
    summary="称号详情",
    description="获取指定称号的详细信息。",
)
async def get_title(
    title_id: int,
    db: DB,
    current_user: CurrentStaff,
):
    """获取称号详情"""
    result = await db.execute(select(UserTitle).where(UserTitle.id == title_id))
    title = result.scalar_one_or_none()

    if not title:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="称号不存在",
        )

    count_result = await db.execute(
        select(func.count()).select_from(User).where(User.title_id == title.id)
    )
    users_count = count_result.scalar() or 0

    return UserTitleResponse(
        id=title.id,
        name=title.name,
        color=title.color,
        icon=title.icon,
        description=title.description,
        created_at=title.created_at,
        users_count=users_count,
    )


@router.patch(
    "/titles/{title_id}",
    response_model=UserTitleResponse,
    summary="更新称号",
    description="更新称号信息，需要管理员权限。",
)
async def update_title(
    title_id: int,
    data: UserTitleUpdate,
    db: DB,
    current_user: CurrentStaff,
):
    """更新称号"""
    result = await db.execute(select(UserTitle).where(UserTitle.id == title_id))
    title = result.scalar_one_or_none()

    if not title:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="称号不存在",
        )

    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(title, field, value)

    await db.flush()
    await db.refresh(title)

    count_result = await db.execute(
        select(func.count()).select_from(User).where(User.title_id == title.id)
    )
    users_count = count_result.scalar() or 0

    return UserTitleResponse(
        id=title.id,
        name=title.name,
        color=title.color,
        icon=title.icon,
        description=title.description,
        created_at=title.created_at,
        users_count=users_count,
    )


@router.delete(
    "/titles/{title_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="删除称号",
    description="删除称号，需要管理员权限。",
)
async def delete_title(
    title_id: int,
    db: DB,
    current_user: CurrentStaff,
):
    """删除称号"""
    result = await db.execute(select(UserTitle).where(UserTitle.id == title_id))
    title = result.scalar_one_or_none()

    if not title:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="称号不存在",
        )

    await db.execute(update(User).where(User.title_id == title_id).values(title_id=None))

    await db.delete(title)
    await db.flush()


# ==================== 用户称号分配接口 ====================


@router.post(
    "/titles/assign",
    summary="分配称号",
    description="为用户分配称号。",
)
async def assign_title(
    data: UserTitleAssign,
    db: DB,
    current_user: CurrentStaff,
):
    """为用户分配称号"""
    user_result = await db.execute(select(User).where(User.id == data.user_id))
    user = user_result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="用户不存在",
        )

    title_result = await db.execute(select(UserTitle).where(UserTitle.id == data.title_id))
    title = title_result.scalar_one_or_none()

    if not title:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="称号不存在",
        )

    user.title_id = data.title_id
    await db.flush()

    return {"message": "称号分配成功", "user_id": user.id, "title_id": title.id}


@router.delete(
    "/users/{user_id}/title",
    summary="移除用户称号",
    description="移除用户的称号。",
)
async def remove_user_title(
    user_id: int,
    db: DB,
    current_user: CurrentStaff,
):
    """移除用户称号"""
    user_result = await db.execute(select(User).where(User.id == user_id))
    user = user_result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="用户不存在",
        )

    user.title_id = None
    await db.flush()

    return {"message": "称号已移除", "user_id": user.id}


@router.get(
    "/users/{user_id}/title",
    summary="获取用户称号",
    description="获取用户的当前称号。",
)
async def get_user_title(
    user_id: int,
    db: DB,
    current_user: CurrentUser,
):
    """获取用户称号"""
    user_result = await db.execute(
        select(User).options(selectinload(User.title)).where(User.id == user_id)
    )
    user = user_result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="用户不存在",
        )

    if not user.title:
        return {"user_id": user.id, "title": None}

    return {
        "user_id": user.id,
        "title": {
            "id": user.title.id,
            "name": user.title.name,
            "color": user.title.color,
            "icon": user.title.icon,
            "description": user.title.description,
        },
    }
