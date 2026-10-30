"""
评论可读性闸门（跨接口单源）。

评论的派生读口（表情统计 / 举报）与写口（添加表情 / 举报）都必须先回答同一个问题：
「这条评论所属的文章，当前调用者能不能看见？」。原先这段判定内联在
``api/comment_reactions.py::_readable_comment`` 里，新加的举报口若各自复制一份，
漏掉密码闸门的那一份就会让"正文已按密码藏好、同一篇文章的评论（常直接引用正文）
却能被匿名按 comment_id 枚举"重新出现。

口径同 ``services/post_access``：
- 文章不存在 / 不可见 / 未解锁一律 404，**不回 403**——承认存在即可按 id 枚举草稿；
- 身份只用于 ``post_is_publicly_visible`` 的作者与 staff 短路，闸门本身不读其它身份信息。
"""

from __future__ import annotations

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models.blog import Comment, Post
from backend.models.user import User
from backend.services.post_access import post_content_unlocked, post_is_publicly_visible

COMMENT_NOT_FOUND_DETAIL = "评论不存在"


async def readable_comment_or_404(
    db: AsyncSession, comment_id: int, current_user: User | None
) -> Comment:
    """返回可读的评论，否则抛 404（消息固定为 ``评论不存在``）。"""
    row = (
        await db.execute(
            select(Comment, Post)
            .join(Post, Post.id == Comment.post_id)
            .where(Comment.id == comment_id)
        )
    ).first()
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=COMMENT_NOT_FOUND_DETAIL)
    comment, post = row
    if not post_is_publicly_visible(post, current_user):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=COMMENT_NOT_FOUND_DETAIL)
    if not await post_content_unlocked(post, current_user):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=COMMENT_NOT_FOUND_DETAIL)
    return comment
