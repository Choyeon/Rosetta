"""
评论表情反应 API

提供接口让登录用户对评论添加/取消表情反应，以及公开获取某评论的表情统计。

路由设计：
- 添加反应（需登录）: POST /api/comments/{comment_id}/reactions
- 取消反应（需登录）: DELETE /api/comments/{comment_id}/reactions/{emoji}
- 公开统计: GET /api/comments/{comment_id}/reactions
"""

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import delete, func, select

from backend.core.auth import DB, CurrentUser, CurrentUserOptional
from backend.models.blog import Comment
from backend.models.comment_reaction import CommentReaction
from backend.schemas import BaseResponse
from backend.schemas.comment_reaction import (
    CommentReactionCreate,
    CommentReactionResponse,
    CommentReactionSummary,
    CommentReactionSummaryList,
)

router = APIRouter(tags=["评论表情反应"])


@router.post(
    "/comments/{comment_id}/reactions",
    response_model=CommentReactionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="添加评论表情反应",
    description="登录用户对指定评论添加一个表情反应。同一用户对同一评论的同一表情只能添加一次。",
)
async def add_comment_reaction(
    comment_id: int,
    data: CommentReactionCreate,
    db: DB,
    current_user: CurrentUser,
):
    """添加评论表情反应"""
    # 检查评论是否存在
    comment = await db.scalar(select(Comment).where(Comment.id == comment_id))
    if not comment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="评论不存在",
        )

    # 幂等：若已存在相同反应，直接返回已有记录
    existing = await db.scalar(
        select(CommentReaction).where(
            CommentReaction.comment_id == comment_id,
            CommentReaction.user_id == current_user.id,
            CommentReaction.emoji == data.emoji,
        )
    )
    if existing:
        return CommentReactionResponse.model_validate(existing)

    reaction = CommentReaction(
        comment_id=comment_id,
        user_id=current_user.id,
        emoji=data.emoji,
    )
    db.add(reaction)
    await db.flush()
    await db.refresh(reaction)
    return CommentReactionResponse.model_validate(reaction)


@router.delete(
    "/comments/{comment_id}/reactions/{emoji}",
    response_model=BaseResponse,
    summary="取消评论表情反应",
    description="登录用户取消自己对指定评论的某个表情反应。",
)
async def remove_comment_reaction(
    comment_id: int,
    emoji: str,
    db: DB,
    current_user: CurrentUser,
):
    """取消评论表情反应"""
    result = await db.execute(
        delete(CommentReaction).where(
            CommentReaction.comment_id == comment_id,
            CommentReaction.user_id == current_user.id,
            CommentReaction.emoji == emoji,
        )
    )
    if result.rowcount == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="未找到对应的表情反应",
        )
    return BaseResponse(message="表情反应已取消")


@router.get(
    "/comments/{comment_id}/reactions",
    response_model=CommentReactionSummaryList,
    summary="获取评论表情反应统计",
    description="公开获取指定评论的所有表情反应统计。如当前用户已登录，返回 reacted 字段标识是否已添加该表情。",
)
async def list_comment_reactions(
    comment_id: int,
    db: DB,
    current_user: CurrentUserOptional,
):
    """获取评论表情反应统计"""
    # 检查评论是否存在
    comment = await db.scalar(select(Comment).where(Comment.id == comment_id))
    if not comment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="评论不存在",
        )

    # 按表情分组统计
    query = (
        select(
            CommentReaction.emoji,
            func.count().label("count"),
        )
        .where(CommentReaction.comment_id == comment_id)
        .group_by(CommentReaction.emoji)
    )
    result = await db.execute(query)
    rows = result.all()

    # 获取当前用户已添加的表情集合
    user_reactions: set[str] = set()
    if current_user:
        user_result = await db.execute(
            select(CommentReaction.emoji).where(
                CommentReaction.comment_id == comment_id,
                CommentReaction.user_id == current_user.id,
            )
        )
        user_reactions = {row[0] for row in user_result.all()}

    reactions = [
        CommentReactionSummary(
            emoji=row.emoji,
            count=row.count,
            reacted=row.emoji in user_reactions,
        )
        for row in rows
    ]
    total = sum(r.count for r in reactions)

    return CommentReactionSummaryList(
        comment_id=comment_id,
        reactions=reactions,
        total=total,
    )
