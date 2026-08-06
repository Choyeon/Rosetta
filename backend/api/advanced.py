"""
回收站和批量操作 API

提供文章回收站、批量操作、修订版本等功能。
"""

import json
import math
from datetime import datetime

from fastapi import APIRouter, Body, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.orm import selectinload

from backend.core.auth import DB, CurrentStaff
from backend.core.concurrency import concurrent_query
from backend.models.blog import Category, Comment, Post, Tag
from backend.models.log import OperationLog, TrashItem
from backend.models.revision import PostRevision
from backend.utils.compat import UTC, timedelta

router = APIRouter(prefix="/admin", tags=["高级管理"])


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


@router.get(
    "/trash",
    summary="回收站列表",
    description="获取回收站中的项目列表。",
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
    - 使用并发查询获取总数和列表
    """
    query = select(TrashItem).options(selectinload(TrashItem.deleted_by))

    if resource_type:
        query = query.where(TrashItem.resource_type == resource_type)

    query = query.order_by(TrashItem.created_at.desc())

    # 并发执行计数和列表查询
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
    description="从回收站恢复项目。",
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
    description="永久删除回收站中的项目。",
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
    description="清空回收站中的所有项目。",
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


@router.post(
    "/posts/batch",
    summary="批量操作文章",
    description="对多篇文章执行批量操作。",
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

    # 查询文章
    result = await db.execute(select(Post).where(Post.id.in_(request.post_ids)))
    posts = result.scalars().all()

    if not posts:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="未找到文章",
        )

    affected_count = 0

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

    return {
        "success": True,
        "message": f"已处理 {affected_count} 篇文章",
        "affected_count": affected_count,
    }


# ==================== 文章修订版本 API ====================


@router.get(
    "/posts/{post_id}/revisions",
    summary="文章修订历史",
    description="获取文章的修订版本列表。",
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
    "/posts/{post_id}/revisions/{revision_id}",
    summary="修订版本详情",
    description="获取指定修订版本的详细内容。",
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
    description="将文章恢复到指定的修订版本。",
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

    return {
        "success": True,
        "message": f"已恢复到版本 #{revision.revision_number}",
    }


# ==================== 操作日志 API ====================


@router.get(
    "/logs",
    summary="操作日志列表",
    description="获取系统操作日志列表。",
)
async def list_operation_logs(
    db: DB,
    current_user: CurrentStaff,
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(50, ge=1, le=200, description="每页数量"),
    user_id: int | None = Query(None, description="用户 ID"),
    action: str | None = Query(None, description="操作类型"),
    resource_type: str | None = Query(None, description="资源类型"),
):
    """获取操作日志列表"""
    query = select(OperationLog).options(selectinload(OperationLog.user))

    if user_id:
        query = query.where(OperationLog.user_id == user_id)
    if action:
        query = query.where(OperationLog.action == action)
    if resource_type:
        query = query.where(OperationLog.resource_type == resource_type)

    query = query.order_by(OperationLog.created_at.desc())

    # 并发执行计数和列表查询
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
    "/posts/{post_id}/revisions/compare",
    summary="比较修订版本",
    description="比较两个修订版本的差异。",
)
async def compare_revisions(
    post_id: int,
    db: DB,
    current_user: CurrentStaff,
    rev1: int = Query(..., description="第一个修订版本 ID"),
    rev2: int = Query(..., description="第二个修订版本 ID"),
):
    """比较两个修订版本"""
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
    "/logs/export",
    summary="导出操作日志",
    description="导出操作日志为 CSV 或 JSON 格式。",
)
async def export_operation_logs(
    db: DB,
    current_user: CurrentStaff,
    format: str = Query("json", description="导出格式：json 或 csv"),
    user_id: int | None = Query(None, description="用户 ID"),
    action: str | None = Query(None, description="操作类型"),
    resource_type: str | None = Query(None, description="资源类型"),
):
    """导出操作日志"""
    from fastapi.responses import Response

    query = select(OperationLog).options(selectinload(OperationLog.user))

    if user_id:
        query = query.where(OperationLog.user_id == user_id)
    if action:
        query = query.where(OperationLog.action == action)
    if resource_type:
        query = query.where(OperationLog.resource_type == resource_type)

    query = query.order_by(OperationLog.created_at.desc()).limit(1000)

    result = await db.execute(query)
    logs = result.scalars().all()

    if format == "csv":
        import csv
        import io

        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(
            ["ID", "用户", "操作", "资源类型", "资源ID", "详情", "IP地址", "状态", "创建时间"]
        )

        for log in logs:
            writer.writerow(
                [
                    log.id,
                    log.user.username if log.user else "",
                    log.action,
                    log.resource_type,
                    log.resource_id,
                    log.detail or "",
                    log.ip_address or "",
                    log.status or "",
                    log.created_at.isoformat() if log.created_at else "",
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
