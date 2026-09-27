"""
文章系列 API

提供公开接口获取文章系列，以及管理员接口管理系列 CRUD。

路由设计：
- 公开接口:
    GET /api/series          列出有已发布文章的活跃系列
    GET /api/series/{slug}   系列详情（含已发布文章列表）
- 管理接口: /api/admin/series (GET/POST/PUT/DELETE)
- 编辑器辅助:
    POST /api/post_series/complete   根据关键词 autocomplete 系列文章
"""

from datetime import datetime

from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import String, and_, cast, func, or_, select

from backend.core.auth import DB, CurrentStaff
from backend.core.partial_update import apply_partial_update
from backend.models.blog import Category, Post
from backend.models.post_series import PostSeries
from backend.schemas import BaseResponse
from backend.schemas.post_series import (
    PostSeriesCreate,
    PostSeriesResponse,
    PostSeriesUpdate,
)

router = APIRouter(tags=["文章系列"])


# ═══════════════════════════════════════════════════════════════════════════
# 响应体文档模型（仅供 OpenAPI `responses={200: {"model": ...}}` 声明使用，
# 运行时不做序列化过滤——实际响应以 handler 返回字面量为准）
# ═══════════════════════════════════════════════════════════════════════════


class SeriesPostItemDoc(BaseModel):
    """系列详情页文章列表的单条投影（列级 select，只取渲染所需的 7 个字段）。"""

    id: int = Field(..., description="文章 ID")
    title: dict[str, str] = Field(
        ..., description="多语言标题 dict（JSON 列原样返回，如 {'zh': ..., 'en': ...}）"
    )
    slug: str = Field(..., description="文章 slug")
    cover_image: str | None = Field(None, description="封面图 URL，未设置时为 null")
    series_order: int | None = Field(
        None, description="系列内排序权重（模型列 NOT NULL default 0；历史脏数据可能为 null）"
    )
    views: int | None = Field(None, description="累计浏览量（模型列 NOT NULL default 0）")
    published_at: datetime | None = Field(
        None, description="发布时间，尚未发布（草稿入镜等历史态）时为 null"
    )


class SeriesDetailDoc(BaseModel):
    """``GET /api/series/{slug}`` 的响应体（裸 dict，无 success/data 信封）。

    注意：本端点**不输出** ``is_active``（未激活的系列直接 404），
    与 ``PostSeriesResponse``（列表/管理端点使用）字段集合不同。
    """

    id: int = Field(..., description="系列 ID")
    title: dict[str, str] = Field(..., description="多语言系列标题（JSON 列原样返回）")
    description: dict[str, str] | None = Field(None, description="多语言系列描述，未设置时为 null")
    slug: str = Field(..., description="系列 slug")
    cover_image: str | None = Field(None, description="系列封面图 URL，未设置时为 null")
    sort_order: int = Field(..., description="系列间排序权重，越小越靠前")
    created_at: datetime = Field(..., description="创建时间（响应序列化为 ISO 8601 字符串）")
    updated_at: datetime = Field(..., description="更新时间（响应序列化为 ISO 8601 字符串）")
    post_count: int = Field(..., description="已发布文章数，等于 posts 数组长度")
    posts: list[SeriesPostItemDoc] = Field(
        default_factory=list, description="已发布文章列表，按 series_order 升序、再按发布时间倒序"
    )


class SeriesCompleteRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=100, description="搜索关键词")


class SeriesCompleteItem(BaseModel):
    id: int
    title: str
    slug: str


def _to_response(series: PostSeries, post_count: int = 0) -> PostSeriesResponse:
    """构建系列响应对象"""
    return PostSeriesResponse(
        id=series.id,
        title=series.title,
        description=series.description,
        slug=series.slug,
        cover_image=series.cover_image,
        is_active=series.is_active,
        sort_order=series.sort_order,
        created_at=series.created_at,
        updated_at=series.updated_at,
        post_count=post_count,
    )


# ==================== 公开接口 ====================


@router.get(
    "/series",
    response_model=list[PostSeriesResponse],
    summary="获取文章系列列表",
    description="获取所有启用且包含已发布文章的系列，按 sort_order 升序排列。",
)
async def list_series(db: DB):
    """获取活跃且有文章的系列列表（公开接口）"""
    query = (
        select(PostSeries, func.count(Post.id).label("post_count"))
        .outerjoin(
            Post,
            and_(Post.series_id == PostSeries.id, Post.status == "published"),
        )
        .where(PostSeries.is_active.is_(True))
        .group_by(PostSeries.id)
        .having(func.count(Post.id) > 0)
        .order_by(PostSeries.sort_order.asc(), PostSeries.created_at.desc())
    )

    result = await db.execute(query)
    rows = result.all()

    return [_to_response(row.PostSeries, row.post_count or 0) for row in rows]


@router.get(
    "/series/{slug}",
    summary="获取系列详情",
    description=(
        "根据 slug 获取系列详情，包含该系列下所有已发布文章列表（按 series_order 排序）。"
        "公开接口、无需鉴权；响应为裸 dict（无 success/data 信封），"
        "post_count 恒等于 posts 长度；系列不存在或未激活返回 404。"
    ),
    responses={200: {"model": SeriesDetailDoc}},
)
async def get_series(slug: str, db: DB):
    """获取系列详情及文章列表（公开接口）"""
    result = await db.execute(select(PostSeries).where(PostSeries.slug == slug))
    series = result.scalar_one_or_none()

    if not series or not series.is_active:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="系列不存在",
        )

    # 只投影系列页真正渲染的列。`select(Post)` 会把每篇文章的正文与 excerpt 一并读进
    # 内存——一个 200 篇的系列就是几百 KB 到几 MB 的无效 IO，而响应用到的只有下面 7 个字段。
    posts_result = await db.execute(
        select(
            Post.id,
            Post.title,
            Post.slug,
            Post.cover_image,
            Post.series_order,
            Post.views,
            Post.published_at,
        )
        .where(Post.series_id == series.id, Post.status == "published")
        .order_by(Post.series_order.asc(), Post.published_at.desc())
    )
    rows = posts_result.all()

    return {
        "id": series.id,
        "title": series.title,
        "description": series.description,
        "slug": series.slug,
        "cover_image": series.cover_image,
        "sort_order": series.sort_order,
        "created_at": series.created_at,
        "updated_at": series.updated_at,
        "post_count": len(rows),
        "posts": [
            {
                "id": r.id,
                "title": r.title,
                "slug": r.slug,
                "cover_image": r.cover_image,
                "series_order": r.series_order,
                "views": r.views,
                "published_at": r.published_at,
            }
            for r in rows
        ],
    }


# ==================== 管理接口 ====================


@router.get(
    "/admin/series",
    response_model=list[PostSeriesResponse],
    summary="管理员获取所有系列",
    description="管理员获取所有系列列表，支持按激活状态过滤，并包含各系列下的文章数量。",
)
async def admin_list_series(
    db: DB,
    current_user: CurrentStaff,
    is_active: bool | None = Query(None, description="按激活状态过滤"),
):
    """管理员获取所有系列"""
    query = (
        select(PostSeries, func.count(Post.id).label("post_count"))
        .outerjoin(Post, Post.series_id == PostSeries.id)
        .group_by(PostSeries.id)
        .order_by(PostSeries.sort_order.asc(), PostSeries.created_at.desc())
    )

    if is_active is not None:
        query = query.where(PostSeries.is_active == is_active)

    result = await db.execute(query)
    rows = result.all()

    return [_to_response(row.PostSeries, row.post_count or 0) for row in rows]


@router.post(
    "/admin/series",
    response_model=PostSeriesResponse,
    status_code=status.HTTP_201_CREATED,
    summary="创建系列",
    description="管理员创建新文章系列。",
)
async def create_series(
    data: PostSeriesCreate,
    db: DB,
    current_user: CurrentStaff,
):
    """创建系列"""
    existing = await db.execute(select(PostSeries).where(PostSeries.slug == data.slug))
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="系列 slug 已存在",
        )

    series = PostSeries(
        title=data.title,
        description=data.description,
        slug=data.slug,
        cover_image=data.cover_image,
        is_active=data.is_active,
        sort_order=data.sort_order,
    )
    db.add(series)
    await db.flush()
    await db.refresh(series)

    return _to_response(series, 0)


@router.put(
    "/admin/series/{series_id}",
    response_model=PostSeriesResponse,
    summary="更新系列",
    description="管理员更新指定系列。",
)
async def update_series(
    series_id: int,
    data: PostSeriesUpdate,
    db: DB,
    current_user: CurrentStaff,
):
    """更新系列"""
    result = await db.execute(select(PostSeries).where(PostSeries.id == series_id))
    series = result.scalar_one_or_none()

    if not series:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="系列不存在",
        )

    update_data = data.model_dump(exclude_unset=True)

    if "slug" in update_data and update_data["slug"] != series.slug:
        existing = await db.execute(
            select(PostSeries).where(PostSeries.slug == update_data["slug"])
        )
        if existing.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="系列 slug 已存在",
            )

    apply_partial_update(series, update_data)

    await db.flush()
    await db.refresh(series)

    post_count = (
        await db.scalar(select(func.count()).select_from(Post).where(Post.series_id == series.id))
        or 0
    )

    return _to_response(series, post_count)


@router.delete(
    "/admin/series/{series_id}",
    response_model=BaseResponse,
    summary="删除系列",
    description="管理员删除指定系列。系列下的文章 series_id 会被置空（级联 SET NULL）。",
)
async def delete_series(
    series_id: int,
    db: DB,
    current_user: CurrentStaff,
):
    """删除系列"""
    result = await db.execute(select(PostSeries).where(PostSeries.id == series_id))
    series = result.scalar_one_or_none()

    if not series:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="系列不存在",
        )

    await db.delete(series)
    return BaseResponse(message="系列已删除")


@router.put(
    "/admin/series/{series_id}/toggle",
    response_model=PostSeriesResponse,
    summary="切换系列激活状态",
    description="管理员切换系列的激活状态。",
)
async def toggle_series(
    series_id: int,
    db: DB,
    current_user: CurrentStaff,
):
    """切换系列激活状态"""
    result = await db.execute(select(PostSeries).where(PostSeries.id == series_id))
    series = result.scalar_one_or_none()

    if not series:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="系列不存在",
        )

    series.is_active = not series.is_active
    await db.flush()
    await db.refresh(series)

    post_count = (
        await db.scalar(select(func.count()).select_from(Post).where(Post.series_id == series.id))
        or 0
    )

    return _to_response(series, post_count)


@router.post(
    "/post_series/complete",
    response_model=list[SeriesCompleteItem],
    summary="编辑器 autocomplete 同系列文章",
    description="根据关键词 autocomplete 系列文章（最多前 8 条）。"
    "优先匹配 PostSeries；否则按分类（Category）近似作为系列。",
)
async def series_complete(data: SeriesCompleteRequest, db: DB) -> list[SeriesCompleteItem]:
    q = data.query.strip().lower()
    if not q:
        return []

    like = f"%{q}%"
    results: list[SeriesCompleteItem] = []
    seen: set[int] = set()

    series_subq = (
        select(PostSeries.id)
        .where(
            or_(
                PostSeries.title.ilike(like),
                PostSeries.slug.ilike(like),
            )
        )
        .limit(8)
    )
    series_result = await db.execute(series_subq)
    series_ids = [row[0] for row in series_result.all()]

    def _collect(rows) -> bool:
        """把候选文章并入结果，凑满 8 条返回 True。

        投影查询（id/title/slug）而不是 ``select(Post)``：autocomplete 只要这三个字段，
        而整行会把正文读进来——三段查询就是 24 篇全文的无效 IO。
        """
        for r in rows:
            if r.id in seen:
                continue
            title = r.title.get("zh") or r.title.get("en") or next(iter(r.title.values()), "")
            results.append(SeriesCompleteItem(id=r.id, title=title, slug=r.slug))
            seen.add(r.id)
            if len(results) >= 8:
                return True
        return False

    light_fields = (Post.id, Post.title, Post.slug)

    if series_ids:
        rows = (
            await db.execute(
                select(*light_fields)
                .where(Post.series_id.in_(series_ids), Post.status == "published")
                .order_by(Post.published_at.desc())
                .limit(8)
            )
        ).all()
        if _collect(rows):
            return results

    try:
        cat_subq = (
            select(Category.id)
            .where(
                or_(
                    Category.name["zh"].astext.ilike(like),
                    Category.name["en"].astext.ilike(like),
                    Category.slug.ilike(like),
                )
            )
            .limit(4)
        )
        cat_r = await db.execute(cat_subq)
        cat_ids = [row[0] for row in cat_r.all()]
    except Exception:
        cat_subq = (
            select(Category.id)
            .where(or_(cast(Category.name, String).ilike(like), Category.slug.ilike(like)))
            .limit(4)
        )
        cat_r = await db.execute(cat_subq)
        cat_ids = [row[0] for row in cat_r.all()]
    if cat_ids:
        rows = (
            await db.execute(
                select(*light_fields)
                .where(Post.category_id.in_(cat_ids), Post.status == "published")
                .order_by(Post.published_at.desc())
                .limit(8)
            )
        ).all()
        if _collect(rows):
            return results

    rows = (
        await db.execute(
            select(*light_fields)
            .where(
                Post.status == "published",
                or_(
                    cast(Post.title["zh"], String).ilike(like),
                    cast(Post.title["en"], String).ilike(like),
                ),
            )
            .order_by(Post.published_at.desc())
            .limit(8)
        )
    ).all()
    _collect(rows)

    return results
