"""自定义内容类型 API：公开定义读取 + 后台定义 CRUD。

路由设计：
- 公开：``GET /api/content-types`` —— 前台文章页按 ``detail.post_type`` 查定义，
  只渲染"定义里存在且值非空"的键。
- 管理：``/api/admin/content-types``（GET/POST/PUT/DELETE）—— staff 专用。

三条横切约束，改 CRUD 时别只盯着增删改：

1. **公开定义有后端缓存，写侧必须一起失效。** 该接口是每个带自定义字段的文章详情页
   都要读的一份小表；不缓存等于每页一次全表扫描，缓存不失效就是"后台改了字段标签、
   前台标题一整段 TTL 还是旧的"。
2. **定义变更会改 SSR HTML。** 字段标签直接渲染在文章页上，而 Nitro 对文章页 swr 600s，
   所以写操作必须 `purge_frontend_page_cache`，否则"后台改了标签、刷新页面没变化"。
3. **key 不可改、被引用时不可删。** key 是 ``posts.post_type`` 的关联键：改名让历史文章
   指向不存在的类型，删除让它们的 ``meta_fields`` 变成无主数据而详情页仍挂着旧值。
   删除前先数引用行，有引用回 409 并带上数量（前端据此提示"先把文章改到别的类型"），
   不要赌外键或静默级联——``post_type`` 是普通字符串列，没有外键兜底。
"""

from fastapi import APIRouter, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.auth import DB, CurrentStaff
from backend.core.cache import cache, make_cache_key
from backend.core.exceptions import ConflictException, NotFoundException
from backend.core.partial_update import apply_partial_update
from backend.models.blog import Post
from backend.models.content_type import ContentTypeDefinition
from backend.schemas import BaseResponse
from backend.schemas.content_type import (
    ContentTypeCreate,
    ContentTypePublic,
    ContentTypeResponse,
    ContentTypeUpdate,
)
from backend.services.content_type_service import list_content_types
from backend.services.frontend_cache_purge import purge_frontend_page_cache

router = APIRouter(tags=["自定义内容类型"])

CONTENT_TYPES_CACHE_TTL = 300


def _public_cache_key() -> str:
    return make_cache_key("content_types", "public")


async def _invalidate(reason: str) -> None:
    try:
        await cache.delete(_public_cache_key())
    except Exception:  # noqa: BLE001 - 缓存不可用只影响性能，不能把写操作打挂
        pass
    purge_frontend_page_cache(f"内容类型变更: {reason}")


def _to_response(definition: ContentTypeDefinition, posts_count: int = 0) -> ContentTypeResponse:
    # 只喂 parsed_fields：库里若有脏字段条目，模型层已跳过，这里不会再把它塞进响应模型。
    return ContentTypeResponse(
        id=definition.id,
        key=definition.key,
        name=definition.name,
        icon=definition.icon,
        description=definition.description,
        fields=definition.parsed_fields,
        posts_count=posts_count,
    )


def _to_public(definition: ContentTypeDefinition) -> ContentTypePublic:
    return ContentTypePublic(
        key=definition.key,
        name=definition.name,
        icon=definition.icon,
        description=definition.description,
        fields=definition.parsed_fields,
    )


async def _posts_count(db: AsyncSession, key: str) -> int:
    return await db.scalar(select(func.count()).select_from(Post).where(Post.post_type == key)) or 0


# ==================== 公开接口 ====================


@router.get(
    "/content-types",
    response_model=list[ContentTypePublic],
    summary="获取自定义内容类型定义",
    description=(
        "公开列出全部内容类型定义（不含 id），供前台文章页按 post_type 渲染自定义字段标签。"
        "结果缓存 300 秒，后台定义写操作会立即失效缓存。"
    ),
)
async def list_public_content_types(db: DB):
    """公开定义列表。"""
    cache_key = _public_cache_key()
    cached = await cache.get(cache_key)
    if cached is not None:
        return cached

    rows = [_to_public(d) for d in await list_content_types(db)]
    try:
        await cache.set(
            cache_key,
            [r.model_dump(mode="json") for r in rows],
            ttl=CONTENT_TYPES_CACHE_TTL,
        )
    except Exception:  # noqa: BLE001 - 缓存写失败不该让前台首屏 500
        pass
    return rows


# ==================== 管理接口 ====================


@router.get(
    "/admin/content-types",
    response_model=list[ContentTypeResponse],
    summary="管理员获取内容类型定义",
    description="管理员获取全部内容类型定义，并带上每种类型当前被多少篇文章引用（删除前置提示用）。",
)
async def admin_list_content_types(db: DB, current_user: CurrentStaff):
    definitions = await list_content_types(db)
    counts: dict[str, int] = {}
    if definitions:
        result = await db.execute(
            select(Post.post_type, func.count())
            .where(Post.post_type.in_([d.key for d in definitions]))
            .group_by(Post.post_type)
        )
        counts = {row[0]: row[1] for row in result.all()}
    return [_to_response(d, counts.get(d.key, 0)) for d in definitions]


@router.post(
    "/admin/content-types",
    response_model=ContentTypeResponse,
    status_code=status.HTTP_201_CREATED,
    summary="创建内容类型",
    description="管理员创建自定义内容类型。key 重复返回 409。",
)
async def create_content_type(
    data: ContentTypeCreate,
    db: DB,
    current_user: CurrentStaff,
):
    existing = (
        await db.execute(select(ContentTypeDefinition).where(ContentTypeDefinition.key == data.key))
    ).scalar_one_or_none()
    if existing is not None:
        raise ConflictException(message=f"内容类型 key 已存在：{data.key}")

    definition = ContentTypeDefinition(
        key=data.key,
        name=data.name,
        icon=data.icon,
        description=data.description,
        fields=[field.model_dump() for field in data.fields],
    )
    db.add(definition)
    await db.flush()
    await db.refresh(definition)
    await _invalidate("create")
    return _to_response(definition)


@router.put(
    "/admin/content-types/{key}",
    response_model=ContentTypeResponse,
    summary="更新内容类型",
    description=(
        "管理员更新内容类型的显示名/图标/描述/字段定义。key 不可修改"
        "（请求体带 key 会被 extra=forbid 拒绝）；删字段不会清理历史文章里的对应值。"
    ),
)
async def update_content_type(
    key: str,
    data: ContentTypeUpdate,
    db: DB,
    current_user: CurrentStaff,
):
    definition = (
        await db.execute(select(ContentTypeDefinition).where(ContentTypeDefinition.key == key))
    ).scalar_one_or_none()
    if definition is None:
        raise NotFoundException(message="内容类型不存在")

    update_data = data.model_dump(exclude_unset=True)
    if "fields" in update_data and update_data["fields"] is None:
        raise ConflictException(message="字段定义不能设为空，如需清空请传空数组")
    apply_partial_update(definition, update_data)

    await db.flush()
    await db.refresh(definition)
    await _invalidate("update")
    return _to_response(definition, await _posts_count(db, definition.key))


@router.delete(
    "/admin/content-types/{key}",
    response_model=BaseResponse,
    summary="删除内容类型",
    description="管理员删除内容类型。仍被文章引用时返回 409（post_type 是普通字符串列，没有外键兜底）。",
)
async def delete_content_type(
    key: str,
    db: DB,
    current_user: CurrentStaff,
):
    definition = (
        await db.execute(select(ContentTypeDefinition).where(ContentTypeDefinition.key == key))
    ).scalar_one_or_none()
    if definition is None:
        raise NotFoundException(message="内容类型不存在")

    posts_count = await _posts_count(db, key)
    if posts_count:
        raise ConflictException(
            message=f"该内容类型仍被 {posts_count} 篇文章使用，请先把它们改到其它类型",
            details={"posts_count": posts_count},
        )

    await db.delete(definition)
    await db.flush()
    await _invalidate("delete")
    return BaseResponse(message="内容类型已删除")
