"""
用户称号管理 API

提供用户称号的 CRUD 操作。
"""

from datetime import datetime
from typing import Iterable

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from backend.core.auth import DB, CurrentStaff, CurrentUser
from backend.models.blog import Post
from backend.models.user import User, UserTitle
from backend.schemas.admin_reads import UserTitleBadgeDoc
from backend.services.cache_service import CacheService
from backend.services.post_cache import invalidate_post_caches_by_slugs

router = APIRouter(tags=["用户称号"])

# 称号图标只允许"预设 ID / 单枚 emoji"这类纯文本，禁止任何标记语言。
# 旧实现不做校验，后台"自定义图标"输入框还明晃晃提示可以贴 `<svg>...</svg>`，
# 而前台 TitleIconSvg 会把以 `<` 开头的值原样 v-html 渲染到每个访客页面上——
# 等于让任意持有 staff 权限的人对全站投放存储型 XSS（AGENTS.md §12 零容忍）。
# 50 上限：emoji 与预设 ID 都远短于此，超长只可能是被塞进的片段。
_ICON_PATTERN = r"^[^<>]*$"

# color 落进 `String(20)` 列，且模型文档声明为十六进制；
# 校验放宽到 CSS 合法的 3/4/6/8 位写法（#fff、#fff0、#ffffff、#ffffffff），
# 但拒掉 "red; background:url(...)" 这类混进内联样式的自由文本。
_COLOR_PATTERN = r"^#(?:[0-9a-fA-F]{3,4}|[0-9a-fA-F]{6}|[0-9a-fA-F]{8})$"


class UserTitleCreate(BaseModel):
    """用户称号创建模型"""

    name: dict[str, str] = Field(..., description="称号名称（多语言）")
    color: str = Field(
        default="#3B82F6",
        max_length=20,
        pattern=_COLOR_PATTERN,
        description="显示颜色（十六进制，如 #3B82F6）",
    )
    icon: str | None = Field(
        None,
        max_length=50,
        pattern=_ICON_PATTERN,
        description="图标：预设 ID（star/crown/…）或 emoji，不接受 HTML/SVG 标记",
    )
    description: dict[str, str] | None = Field(None, description="称号描述（多语言）")


class UserTitleUpdate(BaseModel):
    """用户称号更新模型"""

    name: dict[str, str] | None = Field(None, description="称号名称（多语言）")
    color: str | None = Field(
        None,
        max_length=20,
        pattern=_COLOR_PATTERN,
        description="显示颜色（十六进制）；省略该 key 表示不修改（列非空，不能置 null）",
    )
    icon: str | None = Field(
        None,
        max_length=50,
        pattern=_ICON_PATTERN,
        description="图标：预设 ID（star/crown/…）或 emoji，不接受 HTML/SVG 标记",
    )
    description: dict[str, str] | None = Field(None, description="称号描述（多语言）")


class UserTitleResponse(BaseModel):
    """用户称号响应模型"""

    id: int
    name: dict[str, str]
    color: str
    icon: str | None = None
    description: dict[str, str] | None = None
    created_at: datetime
    users_count: int = 0

    model_config = {"from_attributes": True}


class UserTitleAssign(BaseModel):
    """分配称号模型"""

    user_id: int = Field(..., description="用户ID")
    title_id: int = Field(..., description="称号ID")


class TitleAssignResult(BaseModel):
    """分配称号结果"""

    message: str = Field("称号分配成功", description="人类可读结果提示")
    user_id: int = Field(..., description="被分配称号的用户ID")
    title_id: int = Field(..., description="已分配的称号ID")


class TitleRemoveResult(BaseModel):
    """移除称号结果"""

    message: str = Field("称号已移除", description="人类可读结果提示")
    user_id: int = Field(..., description="被移除称号的用户ID")


# ═══════════════════════════════════════════════════════════════════════════
# 响应体文档模型（仅供 OpenAPI `responses={200: {"model": ...}}` 声明使用，
# 运行时不做序列化过滤——实际响应以 handler 返回字面量为准）
# ═══════════════════════════════════════════════════════════════════════════


class UserTitleGetResultDoc(BaseModel):
    """``GET /api/users/{user_id}/title`` 的响应体（裸 dict，无信封）。"""

    user_id: int = Field(..., description="查询的用户 ID（取自用户行，与路径参数一致）")
    title: UserTitleBadgeDoc | None = Field(
        ...,
        description=(
            "用户当前头衔徽章（id/name/color/icon/description）；"
            "用户尚未分配头衔时为 null（键仍在，不是缺字段）"
        ),
    )


# ==================== 称号管理接口 ====================


def _title_name_keys(name: dict | str | None) -> set[str]:
    """把一个称号的多语言 name 归一化成"用于查重的一组键"。

    读的是 Python 侧已反序列化的 JSON，所以不受 `CAST(json AS CHAR)` 在 SQLite 里
    被转成 `\\uXXXX` 的影响——这正是旧的 `like('%名称%')` 查重对中文永远不生效的原因。
    同时用精确匹配取代子串匹配：旧写法会把 "VIP" 判成 "VIP Pro" 的重复。
    """
    values = [name] if isinstance(name, str) else list((name or {}).values())
    return {text.strip().casefold() for text in map(str, values) if text.strip()}


async def _title_name_conflict(
    db: DB,
    name: dict | str,
    *,
    exclude_id: int | None = None,
) -> bool:
    """任一语言的名字与既有称号完全相同即视为冲突（称号表规模是个位数~几十，全量比对即可）。"""
    keys = _title_name_keys(name)
    if not keys:
        return False
    stmt = select(UserTitle.name)
    if exclude_id is not None:
        stmt = stmt.where(UserTitle.id != exclude_id)
    rows = (await db.execute(stmt)).scalars().all()
    return any(keys & _title_name_keys(row) for row in rows)


async def _holder_ids_of_title(db: AsyncSession, title_id: int) -> list[int]:
    """查出当前持有某称号的用户 ID（改名/改色/删除前先抓，删除后关系就查不到了）。"""
    rows = await db.execute(select(User.id).where(User.title_id == title_id))
    return list(rows.scalars().all())


async def _invalidate_title_holder_caches(db: AsyncSession, user_ids: Iterable[int]) -> None:
    """称号内容或其归属变化后，清除所有会把称号显示出去的缓存。

    称号的 name/color/icon 会被嵌进文章详情缓存的 `author.title` 段
    （见 `blog._build_author_data`），而详情键是 `post:{slug}:{lang}`：
    它既不在 `posts` 前缀下，也不属于 `invalidate_user_cache` 的三族键。
    后果是后台改个名、换个色、授予或撤销称号后，持有者的全部文章页在
    `CACHE_TTL["post_detail"]`（600s）内继续显示旧徽章——匿名访客看到的
    是已被删除的称号。这里按持有者捞出其文章 slug，一并失效详情缓存与
    列表/RSS 缓存；公开资料缓存（`user_profile:` 同样嵌了称号）单独清。
    """
    ids = {uid for uid in user_ids if uid is not None}
    if not ids:
        return

    cache_service = CacheService()
    for user_id in ids:
        await cache_service.invalidate_user_cache(user_id)

    rows = await db.execute(select(Post.slug).where(Post.author_id.in_(ids)))
    await invalidate_post_caches_by_slugs(rows.scalars().all())


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

    # 单次 GROUP BY 聚合所有称号的使用数，避免逐条 count 的 N+1 查询
    counts_result = await db.execute(
        select(User.title_id, func.count())
        .where(User.title_id.is_not(None))
        .group_by(User.title_id)
    )
    counts_map = {title_id: cnt for title_id, cnt in counts_result.fetchall()}

    return [
        UserTitleResponse(
            id=title.id,
            name=title.name,
            color=title.color,
            icon=title.icon,
            description=title.description,
            created_at=title.created_at,
            users_count=counts_map.get(title.id, 0),
        )
        for title in titles
    ]


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
    if not _title_name_keys(data.name):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="称号名称不能为空",
        )
    if await _title_name_conflict(db, data.name):
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


@router.put(
    "/titles/{title_id}",
    response_model=UserTitleResponse,
    summary="更新称号",
    description=(
        "更新称号信息，需要管理员权限。称号的 name/color/icon 会被嵌入文章详情"
        "与公开资料缓存，更新后自动失效全部持有者的相关缓存。"
    ),
)
@router.patch(
    "/titles/{title_id}",
    response_model=UserTitleResponse,
    summary="更新称号",
    description=(
        "更新称号信息，需要管理员权限。称号的 name/color/icon 会被嵌入文章详情"
        "与公开资料缓存，更新后自动失效全部持有者的相关缓存。"
    ),
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

    # name/color 在模型里是 NOT NULL 列。PATCH 走 exclude_unset，显式传 null 会被理解为
    # "把它改成 null"，setattr 后 flush 直接撞 IntegrityError 变 500
    # （后台清空取色器再保存，发出的正是 `{"color": null}` 这种包）。
    for required_field, label in (("name", "称号名称"), ("color", "称号颜色")):
        if required_field in update_data and update_data[required_field] is None:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail=f"{label}不能为空",
            )

    # 改名同样要查重（旧实现只在创建时查，等于允许把 B 称号改名成 A 的名字）
    if "name" in update_data:
        if not _title_name_keys(update_data["name"]):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail="称号名称不能为空",
            )
        if await _title_name_conflict(db, update_data["name"], exclude_id=title_id):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="称号名称已存在",
            )

    for field, value in update_data.items():
        setattr(title, field, value)

    await db.flush()
    await db.refresh(title)

    await _invalidate_title_holder_caches(db, await _holder_ids_of_title(db, title_id))

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
    description=(
        "删除称号，需要管理员权限。删除会同时摘除全部持有者，"
        "并失效其文章详情/列表与公开资料缓存，避免前台残留已删称号的徽章。"
    ),
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

    # 逐个摘除持有者并清空*关系*（而不是批量 UPDATE users SET title_id=NULL）：
    # 同一 session 内已装载过 title 关系的 User 不会被裸 bulk 语句同步，
    # 于是删除后仍能从缓存对象里读到这个已删称号（测试用共享 session 直接复现了脏读）。
    # 单个称号的持有者是"用户中的一小撮"，量级可控，逐条写比脏数据便宜。
    holders = (await db.execute(select(User).where(User.title_id == title_id))).scalars().all()
    holder_ids = [holder.id for holder in holders]
    for holder in holders:
        holder.title = None

    await db.delete(title)
    await db.flush()

    # 称号已经不存在了，但它的副本还留在缓存里的 author.title 段上——
    # 不清就会产生"前台给已删称号继续挂徽章"的幽灵显示。
    await _invalidate_title_holder_caches(db, holder_ids)


# ==================== 用户称号分配接口 ====================


@router.post(
    "/titles/assign",
    response_model=TitleAssignResult,
    summary="分配称号",
    description=(
        "为用户分配称号。称号会被嵌进该用户文章的作者段与公开资料缓存，"
        "因此成功后自动失效其全部文章详情/列表缓存与用户资料缓存。"
    ),
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

    user.title = title
    await db.flush()

    await _invalidate_title_holder_caches(db, [user.id])

    return TitleAssignResult(
        message="称号分配成功",
        user_id=user.id,
        title_id=title.id,
    )


@router.delete(
    "/users/{user_id}/title",
    response_model=TitleRemoveResult,
    summary="移除用户称号",
    description=(
        "移除用户的称号。同样会失效该用户的公开资料缓存与其全部"
        "文章详情/列表缓存，避免前台继续显示已撤销的徽章。"
    ),
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

    # 改"关系"而不是只改 FK 标量：同一个 session 里若这个 User 的 title 关系已被
    # selectinload 装载过（例如刚调过 GET /users/{id}/title），只写 title_id=None
    # 会在 flush 时被关系侧反向覆盖回旧 ID——接口返回 200、库里却什么都没变。
    user.title = None
    await db.flush()

    await _invalidate_title_holder_caches(db, [user.id])

    return {"message": "称号已移除", "user_id": user.id}


@router.get(
    "/users/{user_id}/title",
    summary="获取用户称号",
    description=(
        "获取用户的当前称号。需登录（CurrentUser）。响应为裸 dict："
        "user_id + title（头衔徽章投影，name/description 为多语言 dict，"
        "icon 为纯文本、color 为十六进制串）；用户无头衔时 title 为 null 而非缺键。"
        "用户不存在返回 404。"
    ),
    responses={200: {"model": UserTitleGetResultDoc}},
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
