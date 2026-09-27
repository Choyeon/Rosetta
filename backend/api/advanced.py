"""
回收站和批量操作 API

提供文章回收站、批量操作、修订版本等功能。
"""

import json
import logging
import math
from datetime import datetime
from typing import Any

from fastapi import APIRouter, Body, HTTPException, Query, status
from fastapi.responses import Response
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.orm import selectinload

from backend.core.auth import DB, CurrentStaff
from backend.core.cache import invalidate_cache, invalidate_post_detail_cache
from backend.core.concurrency import concurrent_query
from backend.models.blog import Category, Comment, Post, Tag
from backend.models.log import OperationLog, TrashItem
from backend.models.revision import PostRevision
from backend.utils.compat import UTC, parse_utc_date, timedelta
from backend.utils.reading_time import compute_reading_time_from_content

router = APIRouter(prefix="/admin", tags=["高级管理"])

logger = logging.getLogger(__name__)


# ==================== 回收站 API ====================


class TrashItemResponse(BaseModel):
    """回收站项目响应"""

    id: int
    resource_type: str
    resource_id: int
    resource_data: dict
    deleted_by: dict | None = None
    auto_delete_at: str | None = None
    created_at: str

    model_config = {"from_attributes": True}


class OperatorOut(BaseModel):
    """回收站/日志里回显的操作者摘要。"""

    id: int = Field(..., description="用户 ID")
    username: str = Field(..., description="登录用户名")
    nickname: str | None = Field(default=None, description="昵称；未设置时为 null")


class TrashEntryOut(BaseModel):
    """回收站单条记录（``/admin/trash`` 列表项的实际字段形态）。"""

    id: int = Field(..., description="回收站记录 ID")
    resource_type: str = Field(..., description="资源类型：post / comment / page")
    resource_id: int = Field(..., description="原始资源 ID（原记录已删除，仅作展示）")
    resource_data: dict = Field(
        ...,
        description=(
            "删除时快照的字段集合（JSON 反序列化结果）。"
            "文章为 title/slug/content/excerpt/cover_image/author_id/category_id/status/views；"
            "评论为 post_id/user_id/parent_id/content"
        ),
    )
    deleted_by: OperatorOut | None = Field(
        default=None, description="执行删除的管理员摘要；账号已注销时为 null"
    )
    auto_delete_at: str | None = Field(
        default=None, description="到期自动清除时间（ISO 8601）；未设置时为 null"
    )
    created_at: str | None = Field(
        default=None, description="进入回收站的时间（ISO 8601）；异常数据下可能为 null"
    )


class TrashListResponse(BaseModel):
    """GET /admin/trash 的响应体（裸分页对象，不带 success 信封）。"""

    items: list[TrashEntryOut] = Field(..., description="当前页回收站记录，按创建时间倒序")
    total: int = Field(..., description="符合筛选条件的总条数")
    page: int = Field(..., description="当前页码（从 1 开始）")
    page_size: int = Field(..., description="每页数量")
    total_pages: int = Field(..., description="总页数；total 为 0 时是 0")


class SimpleActionResultResponse(BaseModel):
    """只回「成功 + 提示语」的写操作响应（恢复、永久删除、清空回收站、恢复修订版本）。"""

    success: bool = Field(..., description="固定为 true；失败走 4xx 错误信封")
    message: str = Field(..., description="人类可读结果提示（如「项目已恢复」）")


@router.get(
    "/trash",
    summary="回收站列表",
    description=(
        "需 CurrentStaff。分页读取回收站记录，可按资源类型过滤，按入站时间倒序。"
        "只读、幂等；返回裸分页对象（无 success 信封）。"
    ),
    responses={200: {"model": TrashListResponse, "description": "分页的回收站记录"}},
)
async def list_trash(
    db: DB,
    current_user: CurrentStaff,
    resource_type: str | None = Query(None, description="资源类型：post/comment/page"),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
):
    """
    获取回收站列表

    性能优化：
    """
    query = select(TrashItem).options(selectinload(TrashItem.deleted_by))

    if resource_type:
        query = query.where(TrashItem.resource_type == resource_type)

    query = query.order_by(TrashItem.created_at.desc())

    # 计数 + 列表（两条顺序查询；concurrent_query 不并行）
    count_query = select(func.count()).select_from(query.subquery())

    total, result = await concurrent_query(
        db.scalar(count_query),
        db.execute(query.offset((page - 1) * page_size).limit(page_size)),
    )

    items = result.scalars().all()
    total = total or 0

    # 转换为响应格式
    response_items = []
    for item in items:
        response_items.append(
            {
                "id": item.id,
                "resource_type": item.resource_type,
                "resource_id": item.resource_id,
                "resource_data": json.loads(item.resource_data)
                if isinstance(item.resource_data, str)
                else item.resource_data,
                "deleted_by": {
                    "id": item.deleted_by.id,
                    "username": item.deleted_by.username,
                    "nickname": item.deleted_by.nickname,
                }
                if item.deleted_by
                else None,
                "auto_delete_at": item.auto_delete_at.isoformat() if item.auto_delete_at else None,
                "created_at": item.created_at.isoformat() if item.created_at else None,
            }
        )

    return {
        "items": response_items,
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": math.ceil(total / page_size) if total > 0 else 0,
    }


@router.post(
    "/trash/{trash_id}/restore",
    summary="恢复项目",
    description=(
        "需 CurrentStaff。按回收站记录重建原始资源（仅支持 post / comment）并删除该条记录，"
        "同时写入 restore 操作日志。非幂等：文章 slug 已被占用时返回 400，记录不存在返回 404。"
    ),
    responses={
        200: {"model": SimpleActionResultResponse, "description": "恢复完成"},
        400: {"description": "文章 slug 已被使用，无法恢复"},
        404: {"description": "回收站项目不存在"},
    },
)
async def restore_trash_item(
    trash_id: int,
    db: DB,
    current_user: CurrentStaff,
):
    """从回收站恢复项目"""
    result = await db.execute(select(TrashItem).where(TrashItem.id == trash_id))
    trash_item = result.scalar_one_or_none()

    if not trash_item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="回收站项目不存在",
        )

    resource_data = (
        json.loads(trash_item.resource_data)
        if isinstance(trash_item.resource_data, str)
        else trash_item.resource_data
    )

    # 根据类型恢复
    if trash_item.resource_type == "post":
        # 检查 slug 是否已被使用
        existing = await db.execute(select(Post).where(Post.slug == resource_data.get("slug")))
        if existing.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="文章 slug 已被使用，无法恢复",
            )

        post = Post(
            title=resource_data.get("title", {}),
            slug=resource_data.get("slug", ""),
            content=resource_data.get("content", {}),
            excerpt=resource_data.get("excerpt"),
            cover_image=resource_data.get("cover_image"),
            author_id=resource_data.get("author_id"),
            category_id=resource_data.get("category_id"),
            status=resource_data.get("status", "draft"),
            views=resource_data.get("views", 0),
        )
        db.add(post)

    elif trash_item.resource_type == "comment":
        comment = Comment(
            post_id=resource_data.get("post_id"),
            user_id=resource_data.get("user_id"),
            parent_id=resource_data.get("parent_id"),
            content=resource_data.get("content", ""),
            active=True,
        )
        db.add(comment)

    # 删除回收站记录
    await db.delete(trash_item)

    # 记录操作日志
    log = OperationLog(
        user_id=current_user.id,
        action="restore",
        resource_type=trash_item.resource_type,
        resource_id=trash_item.resource_id,
        detail=json.dumps({"from_trash": True}),
    )
    db.add(log)
    await db.flush()

    return {"success": True, "message": "项目已恢复"}


@router.delete(
    "/trash/{trash_id}",
    summary="永久删除",
    description=(
        "需 CurrentStaff。不可逆：删除回收站记录本体（原始资源在入站时已删除），"
        "并写入 permanent_delete 操作日志。记录不存在返回 404。"
    ),
    responses={
        200: {"model": SimpleActionResultResponse, "description": "已永久删除"},
        404: {"description": "回收站项目不存在"},
    },
)
async def permanently_delete(
    trash_id: int,
    db: DB,
    current_user: CurrentStaff,
):
    """永久删除回收站项目"""
    result = await db.execute(select(TrashItem).where(TrashItem.id == trash_id))
    trash_item = result.scalar_one_or_none()

    if not trash_item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="回收站项目不存在",
        )

    resource_type = trash_item.resource_type
    resource_id = trash_item.resource_id

    await db.delete(trash_item)

    # 记录操作日志
    log = OperationLog(
        user_id=current_user.id,
        action="permanent_delete",
        resource_type=resource_type,
        resource_id=resource_id,
    )
    db.add(log)
    await db.flush()

    return {"success": True, "message": "项目已永久删除"}


@router.delete(
    "/trash",
    summary="清空回收站",
    description=(
        "需 CurrentStaff。不可逆：逐条删除回收站记录（可限定资源类型，不传则清空全部），"
        "message 里回显实际清除条数。"
    ),
    responses={200: {"model": SimpleActionResultResponse, "description": "已清空，提示语含条数"}},
)
async def empty_trash(
    db: DB,
    current_user: CurrentStaff,
    resource_type: str | None = Query(None, description="资源类型，不指定则清空全部"),
):
    """清空回收站"""
    query = select(TrashItem)
    if resource_type:
        query = query.where(TrashItem.resource_type == resource_type)

    result = await db.execute(query)
    items = result.scalars().all()

    count = 0
    for item in items:
        await db.delete(item)
        count += 1

    await db.flush()

    return {"success": True, "message": f"已清空 {count} 个项目"}


# ==================== 批量操作 API ====================


class BatchActionRequest(BaseModel):
    """批量操作请求"""

    action: str  # publish/draft/delete/move_category/add_tag/remove_tag
    post_ids: list[int]
    category_id: int | None = None
    tag_ids: list[int] | None = None


class BatchActionResponse(BaseModel):
    """POST /admin/posts/batch 的响应体。"""

    success: bool = Field(..., description="固定为 true；失败走 4xx 错误信封")
    message: str = Field(..., description="提示语，含实际处理篇数")
    affected_count: int = Field(
        ...,
        description="状态真正发生变化的文章篇数（publish/draft 会跳过本就符合目标的记录）",
    )


@router.post(
    "/posts/batch",
    summary="批量操作文章",
    description=(
        "需 CurrentStaff。对多篇文章执行同一种动作，成功后失效 posts 列表与详情缓存。"
        "delete 为软删除（移入回收站，30 天后自动清除）；其余动作幂等。"
        "未选中任何文章返回 400，全部找不到返回 404。"
    ),
    responses={
        200: {"model": BatchActionResponse, "description": "批量处理完成"},
        400: {"description": "未选择文章 / 缺少 category_id 或 tag_ids / 不支持的 action"},
        404: {"description": "未找到任何匹配的文章或目标分类"},
    },
)
async def batch_action_posts(
    db: DB,
    current_user: CurrentStaff,
    request: BatchActionRequest = Body(...),
):
    """
    批量操作文章

    支持的操作：
    - publish: 批量发布
    - draft: 批量转为草稿
    - delete: 批量删除（移入回收站）
    - move_category: 批量移动分类
    - add_tag: 批量添加标签
    - remove_tag: 批量移除标签
    - pin: 批量置顶
    - unpin: 批量取消置顶
    """
    if not request.post_ids:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="请选择要操作的文章",
        )

    # 查询文章：add_tag / remove_tag 会读写 post.tags 集合，
    # 不做 selectinload 就是"未加载属性 + async 会话"= MissingGreenlet 500。
    result = await db.execute(
        select(Post).options(selectinload(Post.tags)).where(Post.id.in_(request.post_ids))
    )
    posts = result.scalars().all()

    if not posts:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="未找到文章",
        )

    affected_count = 0
    # slug 要在任何删除动作之前采集：db.delete + flush 之后再读属性会对已删行发 SELECT
    affected_slugs = [post.slug for post in posts]

    if request.action == "publish":
        for post in posts:
            if post.status != "published":
                post.status = "published"
                post.published_at = post.published_at or datetime.now(UTC)
                affected_count += 1

    elif request.action == "draft":
        for post in posts:
            if post.status == "published":
                post.status = "draft"
                affected_count += 1

    elif request.action == "delete":
        for post in posts:
            # 保存到回收站
            trash_item = TrashItem(
                resource_type="post",
                resource_id=post.id,
                resource_data=json.dumps(
                    {
                        "title": post.title,
                        "slug": post.slug,
                        "content": post.content,
                        "excerpt": post.excerpt,
                        "cover_image": post.cover_image,
                        "author_id": post.author_id,
                        "category_id": post.category_id,
                        "status": post.status,
                        "views": post.views,
                    }
                ),
                deleted_by_id=current_user.id,
                auto_delete_at=datetime.now(UTC) + timedelta(days=30),
            )
            db.add(trash_item)
            await db.delete(post)
            affected_count += 1

    elif request.action == "move_category":
        if not request.category_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="请指定目标分类",
            )
        category = await db.get(Category, request.category_id)
        if not category:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="分类不存在",
            )
        for post in posts:
            post.category_id = request.category_id
            affected_count += 1

    elif request.action == "add_tag":
        if not request.tag_ids:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="请指定要添加的标签",
            )
        tags_result = await db.execute(select(Tag).where(Tag.id.in_(request.tag_ids)))
        tags = tags_result.scalars().all()
        for post in posts:
            for tag in tags:
                if tag not in post.tags:
                    post.tags.append(tag)
            affected_count += 1

    elif request.action == "remove_tag":
        if not request.tag_ids:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="请指定要移除的标签",
            )
        for post in posts:
            for tag in list(post.tags):
                if tag.id in request.tag_ids:
                    post.tags.remove(tag)
            affected_count += 1

    elif request.action == "pin":
        for post in posts:
            post.is_pinned = True
            affected_count += 1

    elif request.action == "unpin":
        for post in posts:
            post.is_pinned = False
            affected_count += 1

    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"不支持的操作: {request.action}",
        )

    # 记录操作日志
    log = OperationLog(
        user_id=current_user.id,
        action=f"batch_{request.action}",
        resource_type="post",
        detail=json.dumps(
            {
                "post_ids": request.post_ids,
                "affected_count": affected_count,
            }
        ),
    )
    db.add(log)
    await db.flush()

    # 批量操作绕过了 blog.py 的写侧失效逻辑：列表类缓存在 posts 前缀下，详情缓存是
    # 逐 slug/语言的 post:{slug}:{lang}，两层都要清，否则转草稿/删除的文章会继续对外可见。
    await invalidate_cache("posts")
    await invalidate_post_detail_cache(*affected_slugs)

    return {
        "success": True,
        "message": f"已处理 {affected_count} 篇文章",
        "affected_count": affected_count,
    }


# ==================== 文章修订版本 API ====================


class RevisionAuthorOut(BaseModel):
    """修订版本作者摘要。"""

    id: int = Field(..., description="用户 ID")
    username: str = Field(..., description="登录用户名")
    nickname: str | None = Field(default=None, description="昵称；未设置时为 null")


class RevisionListItemOut(BaseModel):
    """``/admin/posts/{post_id}/revisions`` 列表项：不含正文，只给摘要信息。"""

    id: int = Field(..., description="修订版本 ID")
    revision_number: int = Field(..., description="版本号（同一文章内递增）")
    title: dict[str, Any] | str | None = Field(
        default=None, description="该版本的多语言标题字典；历史脏数据下可能是纯字符串"
    )
    change_summary: str | None = Field(
        default=None, description="变更说明（如「恢复到版本 #N 前的备份」）"
    )
    author: RevisionAuthorOut | None = Field(
        default=None, description="作者摘要；作者账号已删除时为 null"
    )
    created_at: str | None = Field(
        default=None, description="版本创建时间（ISO 8601）；异常数据下可能为 null"
    )


class RevisionListResponse(BaseModel):
    """GET /admin/posts/{post_id}/revisions 的响应体（裸对象，无 success 信封）。"""

    post_id: int = Field(..., description="文章 ID")
    current_title: dict[str, Any] | str | None = Field(
        default=None, description="文章当前标题（多语言字典），供前端对比各版本"
    )
    revisions: list[RevisionListItemOut] = Field(
        ..., description="修订版本列表，按 revision_number 倒序（最新在前）"
    )
    total: int = Field(..., description="版本条数（等于 revisions 长度）")


class RevisionSnapshotOut(BaseModel):
    """版本比对里单侧的内容快照。"""

    id: int = Field(..., description="修订版本 ID")
    revision_number: int = Field(..., description="版本号")
    content: dict[str, Any] = Field(
        ...,
        description="该版本正文（多语言字典，键为语言码；缺失时为空对象）",
    )
    created_at: str | None = Field(default=None, description="版本创建时间（ISO 8601）")


class RevisionCompareResponse(BaseModel):
    """GET /admin/posts/{post_id}/revisions/compare 的响应体。"""

    revision1: RevisionSnapshotOut = Field(..., description="rev1 查询参数对应的版本快照")
    revision2: RevisionSnapshotOut = Field(..., description="rev2 查询参数对应的版本快照")


class RevisionDetailResponse(BaseModel):
    """GET /admin/posts/{post_id}/revisions/{revision_id} 的响应体。"""

    id: int = Field(..., description="修订版本 ID")
    post_id: int = Field(..., description="所属文章 ID")
    revision_number: int = Field(..., description="版本号")
    title: dict[str, Any] | str | None = Field(default=None, description="该版本多语言标题")
    content: dict[str, Any] | str | None = Field(default=None, description="该版本正文")
    excerpt: dict[str, Any] | str | None = Field(
        default=None, description="该版本摘要；未设置时为 null"
    )
    change_summary: str | None = Field(default=None, description="变更说明")
    created_at: str | None = Field(default=None, description="版本创建时间（ISO 8601）")


@router.get(
    "/posts/{post_id}/revisions",
    summary="文章修订历史",
    description=(
        "需 CurrentStaff。读取某篇文章的全部修订版本（不含正文，正文走单版本详情接口），"
        "按版本号倒序。文章不存在返回 404。只读、幂等。"
    ),
    responses={
        200: {"model": RevisionListResponse, "description": "版本摘要列表"},
        404: {"description": "文章不存在"},
    },
)
async def list_post_revisions(
    post_id: int,
    db: DB,
    current_user: CurrentStaff,
):
    """获取文章修订历史"""
    # 检查文章是否存在
    post = await db.get(Post, post_id)
    if not post:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="文章不存在",
        )

    result = await db.execute(
        select(PostRevision)
        .where(PostRevision.post_id == post_id)
        .options(selectinload(PostRevision.author))
        .order_by(PostRevision.revision_number.desc())
    )
    revisions = result.scalars().all()

    items = []
    for rev in revisions:
        items.append(
            {
                "id": rev.id,
                "revision_number": rev.revision_number,
                "title": json.loads(rev.title) if isinstance(rev.title, str) else rev.title,
                "change_summary": rev.change_summary,
                "author": {
                    "id": rev.author.id,
                    "username": rev.author.username,
                    "nickname": rev.author.nickname,
                }
                if rev.author
                else None,
                "created_at": rev.created_at.isoformat() if rev.created_at else None,
            }
        )

    return {
        "post_id": post_id,
        "current_title": post.title,
        "revisions": items,
        "total": len(items),
    }


@router.get(
    "/posts/{post_id}/revisions/compare",
    summary="比较修订版本",
    description=(
        "需 CurrentStaff。按 ``rev1`` / ``rev2`` 两个版本 ID 返回正文快照，由前端做 diff。"
        "任一 ID 不属于该文章（或只传到一个）时返回 404。只读、幂等。"
    ),
    responses={
        200: {"model": RevisionCompareResponse, "description": "左右两版本的正文快照"},
        404: {"description": "找不到指定的修订版本"},
    },
)
async def compare_revisions(
    post_id: int,
    db: DB,
    current_user: CurrentStaff,
    rev1: int = Query(..., description="第一个修订版本 ID"),
    rev2: int = Query(..., description="第二个修订版本 ID"),
):
    """比较两个修订版本

    路由顺序注意：本路由必须声明在 ``/revisions/{revision_id}`` **之前**，
    否则 "compare" 会被路径参数捕获（int 解析失败 → 422），端点永远不可达。
    """
    result = await db.execute(
        select(PostRevision).where(
            PostRevision.post_id == post_id,
            PostRevision.id.in_([rev1, rev2]),
        )
    )
    revisions = {r.id: r for r in result.scalars().all()}

    if len(revisions) < 2:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="找不到指定的修订版本",
        )

    r1 = revisions[rev1]
    r2 = revisions[rev2]

    def get_content(rev):
        content = rev.content
        if isinstance(content, str):
            return json.loads(content)
        return content or {}

    return {
        "revision1": {
            "id": r1.id,
            "revision_number": r1.revision_number,
            "content": get_content(r1),
            "created_at": r1.created_at.isoformat() if r1.created_at else None,
        },
        "revision2": {
            "id": r2.id,
            "revision_number": r2.revision_number,
            "content": get_content(r2),
            "created_at": r2.created_at.isoformat() if r2.created_at else None,
        },
    }


@router.get(
    "/posts/{post_id}/revisions/{revision_id}",
    summary="修订版本详情",
    description=(
        "需 CurrentStaff。返回指定修订版本的标题 / 正文 / 摘要全文，用于版本预览与恢复前确认。"
        "版本不存在或不属于该文章返回 404。只读、幂等。"
    ),
    responses={
        200: {"model": RevisionDetailResponse, "description": "单版本完整内容"},
        404: {"description": "修订版本不存在"},
    },
)
async def get_post_revision(
    post_id: int,
    revision_id: int,
    db: DB,
    current_user: CurrentStaff,
):
    """获取修订版本详情"""
    result = await db.execute(
        select(PostRevision).where(
            PostRevision.post_id == post_id,
            PostRevision.id == revision_id,
        )
    )
    revision = result.scalar_one_or_none()

    if not revision:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="修订版本不存在",
        )

    return {
        "id": revision.id,
        "post_id": revision.post_id,
        "revision_number": revision.revision_number,
        "title": json.loads(revision.title) if isinstance(revision.title, str) else revision.title,
        "content": json.loads(revision.content)
        if isinstance(revision.content, str)
        else revision.content,
        "excerpt": json.loads(revision.excerpt)
        if revision.excerpt and isinstance(revision.excerpt, str)
        else revision.excerpt,
        "change_summary": revision.change_summary,
        "created_at": revision.created_at.isoformat() if revision.created_at else None,
    }


@router.post(
    "/posts/{post_id}/revisions/{revision_id}/restore",
    summary="恢复到指定版本",
    description=(
        "需 CurrentStaff。有副作用：先把文章当前内容另存为新版本（避免丢失），"
        "再用目标版本的 title/content/excerpt 覆盖文章，并重算阅读时长，"
        "最后失效该文章详情缓存与 posts 列表缓存。文章或版本不存在返回 404。"
    ),
    responses={
        200: {"model": SimpleActionResultResponse, "description": "恢复完成，提示语含目标版本号"},
        404: {"description": "文章不存在或修订版本不存在"},
    },
)
async def restore_post_revision(
    post_id: int,
    revision_id: int,
    db: DB,
    current_user: CurrentStaff,
):
    """恢复到指定修订版本"""
    # 获取文章
    post = await db.get(Post, post_id)
    if not post:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="文章不存在",
        )

    # 获取修订版本
    result = await db.execute(
        select(PostRevision).where(
            PostRevision.post_id == post_id,
            PostRevision.id == revision_id,
        )
    )
    revision = result.scalar_one_or_none()

    if not revision:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="修订版本不存在",
        )

    # 保存当前版本到修订历史
    current_revision_number = (
        await db.scalar(
            select(func.max(PostRevision.revision_number)).where(PostRevision.post_id == post_id)
        )
        or 0
    )

    current_revision = PostRevision(
        post_id=post_id,
        revision_number=current_revision_number + 1,
        title=json.dumps(post.title) if isinstance(post.title, dict) else post.title,
        content=json.dumps(post.content) if isinstance(post.content, dict) else post.content,
        excerpt=json.dumps(post.excerpt)
        if post.excerpt and isinstance(post.excerpt, dict)
        else post.excerpt,
        author_id=current_user.id,
        change_summary=f"恢复到版本 #{revision.revision_number} 前的备份",
    )
    db.add(current_revision)

    # 恢复内容
    revision_title = (
        json.loads(revision.title) if isinstance(revision.title, str) else revision.title
    )
    revision_content = (
        json.loads(revision.content) if isinstance(revision.content, str) else revision.content
    )
    revision_excerpt = (
        json.loads(revision.excerpt)
        if revision.excerpt and isinstance(revision.excerpt, str)
        else revision.excerpt
    )

    post.title = revision_title
    post.content = revision_content
    post.excerpt = revision_excerpt
    # 正文回退后必须重算阅读时长：列表接口 defer(content) 只读 reading_time，
    # 不重算会让"恢复版本"后的文章继续显示旧内容的时长（blog.py 更新路径同样这么做）。
    post.reading_time = compute_reading_time_from_content(post.content)

    # 记录操作日志
    log = OperationLog(
        user_id=current_user.id,
        action="restore_revision",
        resource_type="post",
        resource_id=post_id,
        detail=json.dumps(
            {
                "revision_id": revision_id,
                "revision_number": revision.revision_number,
            }
        ),
    )
    db.add(log)
    await db.flush()

    # 正文已整体回退，两层缓存都会失真：详情缓存存的是新版正文，列表缓存的排序/摘要同样过期
    await invalidate_post_detail_cache(post.slug)
    await invalidate_cache("posts")

    return {
        "success": True,
        "message": f"已恢复到版本 #{revision.revision_number}",
    }


# ==================== 操作日志 API ====================


class OperationLogEntryOut(BaseModel):
    """``/admin/logs`` 列表项：一条系统操作日志。"""

    id: int = Field(..., description="日志 ID")
    user: OperatorOut | None = Field(
        default=None, description="操作者摘要（id/username/nickname）；匿名或账号已删除时为 null"
    )
    action: str = Field(
        ...,
        description="动作标识，如 create/update/delete/restore/permanent_delete/batch_publish",
    )
    resource_type: str | None = Field(default=None, description="被操作资源类型，如 post/comment")
    resource_id: int | None = Field(default=None, description="被操作资源 ID")
    detail: dict[str, Any] | str | None = Field(
        default=None, description="详情载荷（能解析为 JSON 时给对象，否则原样字符串）"
    )
    ip_address: str | None = Field(default=None, description="请求来源 IP；取不到时为 null")
    status: str | None = Field(default=None, description="操作结果状态（成功/失败标记）")
    created_at: str | None = Field(
        default=None, description="日志时间（ISO 8601）；异常数据下可能为 null"
    )


class OperationLogListResponse(BaseModel):
    """GET /admin/logs 的响应体（裸分页对象，无 success 信封）。"""

    items: list[OperationLogEntryOut] = Field(
        ..., description="当前页日志，按创建时间倒序（最新在前）"
    )
    total: int = Field(..., description="符合筛选条件的总条数")
    page: int = Field(..., description="当前页码（从 1 开始）")
    page_size: int = Field(..., description="每页数量（上限 200）")
    total_pages: int = Field(..., description="总页数；total 为 0 时是 0")


@router.get(
    "/logs",
    summary="操作日志列表",
    description=(
        "需 CurrentStaff。分页读取操作日志，支持按用户、动作、资源类型、时间区间"
        "（from/to，仅给日期时 to 扩展到当天末尾）与关键词（匹配 detail / error_code / ip）过滤。"
        "只读、幂等。"
    ),
    operation_id="list_advanced_operation_logs",
    responses={200: {"model": OperationLogListResponse, "description": "分页日志列表"}},
)
async def list_operation_logs(
    db: DB,
    current_user: CurrentStaff,
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(50, ge=1, le=200, description="每页数量"),
    user_id: int | None = Query(None, description="用户 ID"),
    action: str | None = Query(None, description="操作类型"),
    resource_type: str | None = Query(None, description="资源类型"),
    from_date: str | None = Query(None, alias="from", description="开始日期 ISO（含边界）"),
    to_date: str | None = Query(None, alias="to", description="结束日期 ISO（含边界）"),
    q: str | None = Query(None, description="关键词搜索(details/error_code/ip)"),
):
    """获取操作日志列表"""
    from sqlalchemy import String as SAString
    from sqlalchemy import cast, or_

    query = select(OperationLog).options(selectinload(OperationLog.user))

    if user_id:
        query = query.where(OperationLog.user_id == user_id)
    if action:
        query = query.where(OperationLog.action == action)
    if resource_type:
        query = query.where(OperationLog.resource_type == resource_type)

    from_dt = parse_utc_date(from_date)
    to_dt = parse_utc_date(to_date)
    if from_dt:
        query = query.where(OperationLog.created_at >= from_dt)
    if to_dt:
        # 结束日期若只是 YYYY-MM-DD（零点），扩展到当天 23:59:59.999 以包含整天
        if to_dt.hour == 0 and to_dt.minute == 0 and to_dt.second == 0:
            to_dt = to_dt + timedelta(days=1) - timedelta(microseconds=1)
        query = query.where(OperationLog.created_at <= to_dt)

    if q:
        like = f"%{q}%"
        query = query.where(
            or_(
                cast(OperationLog.detail, SAString).ilike(like),
                OperationLog.error_code.ilike(like)
                if hasattr(OperationLog, "error_code")
                else False,
                OperationLog.ip_address.ilike(like),
            )
        )

    query = query.order_by(OperationLog.created_at.desc())

    # 计数 + 列表（两条顺序查询；concurrent_query 不并行）
    count_query = select(func.count()).select_from(query.subquery())

    total, result = await concurrent_query(
        db.scalar(count_query),
        db.execute(query.offset((page - 1) * page_size).limit(page_size)),
    )

    logs = result.scalars().all()
    total = total or 0

    items = []
    for log in logs:
        items.append(
            {
                "id": log.id,
                "user": {
                    "id": log.user.id,
                    "username": log.user.username,
                    "nickname": log.user.nickname,
                }
                if log.user
                else None,
                "action": log.action,
                "resource_type": log.resource_type,
                "resource_id": log.resource_id,
                "detail": json.loads(log.detail)
                if log.detail and isinstance(log.detail, str)
                else log.detail,
                "ip_address": log.ip_address,
                "status": log.status,
                "created_at": log.created_at.isoformat() if log.created_at else None,
            }
        )

    return {
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": math.ceil(total / page_size) if total > 0 else 0,
    }


@router.get(
    "/logs/export",
    summary="导出操作日志",
    description=(
        "需 CurrentStaff。按与列表接口相同的过滤条件导出**最多 1000 条**日志为文件下载"
        "（带 Content-Disposition: attachment）：``format=csv`` 回 text/csv"
        "（单元格已做公式注入防护），``format=json``（默认）回 application/json 数组。"
        "只读、无副作用。"
    ),
    responses={
        200: {
            "description": "文件下载体：CSV 文本或 JSON 数组，取决于 format 参数",
            "content": {
                "text/csv": {"schema": {"type": "string", "description": "CSV 全文（含表头）"}},
                "application/json": {
                    "schema": {
                        "type": "array",
                        "items": {"$ref": "#/components/schemas/OperationLogEntryOut"},
                    }
                },
            },
        }
    },
)
async def export_operation_logs(
    db: DB,
    current_user: CurrentStaff,
    format: str = Query("json", description="导出格式：json 或 csv"),
    user_id: int | None = Query(None, description="用户 ID"),
    action: str | None = Query(None, description="操作类型"),
    resource_type: str | None = Query(None, description="资源类型"),
    from_date: str | None = Query(None, alias="from", description="开始日期 ISO（含边界）"),
    to_date: str | None = Query(None, alias="to", description="结束日期 ISO（含边界）"),
) -> Response:
    """导出操作日志"""
    query = select(OperationLog).options(selectinload(OperationLog.user))

    if user_id:
        query = query.where(OperationLog.user_id == user_id)
    if action:
        query = query.where(OperationLog.action == action)
    if resource_type:
        query = query.where(OperationLog.resource_type == resource_type)

    from_dt = parse_utc_date(from_date)
    to_dt = parse_utc_date(to_date)
    if from_dt:
        query = query.where(OperationLog.created_at >= from_dt)
    if to_dt:
        if to_dt.hour == 0 and to_dt.minute == 0 and to_dt.second == 0:
            to_dt = to_dt + timedelta(days=1) - timedelta(microseconds=1)
        query = query.where(OperationLog.created_at <= to_dt)

    query = query.order_by(OperationLog.created_at.desc()).limit(1000)

    result = await db.execute(query)
    logs = result.scalars().all()

    if format == "csv":
        import csv
        import io

        def _csv_safe(value) -> str:
            """CSV 公式注入防护：以 =/+/-/@ 开头的单元格前置制表符，
            防止日志内容（可含用户输入）在 Excel/WPS 打开时被执行为公式。"""
            s = "" if value is None else str(value)
            if s.startswith(("=", "+", "-", "@")):
                return "\t" + s
            return s

        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(
            ["ID", "用户", "操作", "资源类型", "资源ID", "详情", "IP地址", "状态", "创建时间"]
        )

        for log in logs:
            writer.writerow(
                [
                    log.id,
                    _csv_safe(log.user.username if log.user else ""),
                    _csv_safe(log.action),
                    _csv_safe(log.resource_type),
                    _csv_safe(log.resource_id),
                    _csv_safe(log.detail or ""),
                    _csv_safe(log.ip_address or ""),
                    _csv_safe(log.status or ""),
                    _csv_safe(log.created_at.isoformat() if log.created_at else ""),
                ]
            )

        return Response(
            content=output.getvalue(),
            media_type="text/csv",
            headers={"Content-Disposition": "attachment; filename=operation_logs.csv"},
        )

    else:
        items = []
        for log in logs:
            items.append(
                {
                    "id": log.id,
                    "user": {
                        "id": log.user.id,
                        "username": log.user.username,
                        "nickname": log.user.nickname,
                    }
                    if log.user
                    else None,
                    "action": log.action,
                    "resource_type": log.resource_type,
                    "resource_id": log.resource_id,
                    "detail": json.loads(log.detail)
                    if log.detail and isinstance(log.detail, str)
                    else log.detail,
                    "ip_address": log.ip_address,
                    "status": log.status,
                    "created_at": log.created_at.isoformat() if log.created_at else None,
                }
            )

        return Response(
            content=json.dumps(items, ensure_ascii=False, indent=2),
            media_type="application/json",
            headers={"Content-Disposition": "attachment; filename=operation_logs.json"},
        )
