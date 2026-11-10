"""hot_score 物化列维护。

热榜接口直接 ``ORDER BY posts.hot_score``（见 ``api/ranking.py``），不再每次请求对
``post_view_histories`` / ``comments`` 做全表聚合。

热度公式：``hot_score = views + likes_count * 5 + 有效评论数(active=1) * 3``

维护策略：
- 增量（高频信号）：浏览自增 / 点赞 toggle / 评论审核 等写入事件用 ``add_hot_score``
  做一次原子 ``UPDATE ... SET hot_score = hot_score + delta``，零额外回源。
- 全量（低频补偿）：``recompute_all_hot_scores`` 供启动回填 / 周期任务调用，一次往返覆盖
  全表；单个 ``recompute_hot_score`` 供写事件不方便算增量时兜底自校正。
"""

from __future__ import annotations

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models.blog import Comment, Post, post_likes


async def add_hot_score(db: AsyncSession, post_id: int, delta: int) -> None:
    """原子自增/自减某篇文章的 hot_score（写入事件增量维护用）。

    delta 为正表示热度上升（浏览、点赞、评论转可见），为负表示下降（取消点赞、
    评论转不可见/删除）。delta 为 0 是空操作，调用方可直接传入无需提前判断。
    """
    if delta == 0:
        return
    await db.execute(
        update(Post).where(Post.id == post_id).values(hot_score=Post.hot_score + delta)
    )


async def recompute_hot_score(db: AsyncSession, post_id: int) -> int:
    """按公式重算单篇文章的 hot_score，返回新值（自校正兜底用）。

    likes 由 post_likes 关联表计数（Post 无 likes_count 列）。
    """
    row = await db.execute(
        select(
            func.coalesce(Post.views, 0),
            func.coalesce(
                select(func.count())
                .where(post_likes.c.post_id == post_id)
                .correlate(Post)
                .scalar_subquery(),
                0,
            ),
            func.coalesce(
                select(func.count())
                .where(Comment.post_id == post_id, Comment.active.is_(True))
                .correlate(Post)
                .scalar_subquery(),
                0,
            ),
        ).where(Post.id == post_id)
    )
    views, likes, comments = row.one()
    new_score = int(views) + int(likes) * 5 + int(comments) * 3
    await db.execute(update(Post).where(Post.id == post_id).values(hot_score=new_score))
    return new_score


async def recompute_all_hot_scores(db: AsyncSession) -> int:
    """全量重算所有文章的 hot_score（启动回填 / 周期任务用）。

    likes 由 post_likes 关联表计数（Post 无 likes_count 列）。单条 UPDATE +
    相关子查询，一次往返覆盖全表，避免逐行查询。返回受影响行数（部分驱动对带
    子查询的 UPDATE 返回 -1/None，这里尽力而为）。
    """
    result = await db.execute(
        update(Post).values(
            hot_score=func.coalesce(Post.views, 0)
            + func.coalesce(
                select(func.count())
                .where(post_likes.c.post_id == Post.id)
                .correlate(Post)
                .scalar_subquery(),
                0,
            )
            * 5
            + func.coalesce(
                select(func.count())
                .where(Comment.post_id == Post.id, Comment.active.is_(True))
                .correlate(Post)
                .scalar_subquery(),
                0,
            )
            * 3
        )
    )
    await db.commit()
    return result.rowcount or 0
