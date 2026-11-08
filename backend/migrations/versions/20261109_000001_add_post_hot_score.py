"""add_post_hot_score_column

为 posts 表新增 hot_score 物化列（综合热度），避免热榜接口每次请求对
PostViewHistory / comments 做全表聚合。

热度公式：hot_score = views + likes_count * 5 + 有效评论数(active=1) * 3。
该列由写入事件增量维护（视图自增 / 点赞 toggle / 评论审核）并支持周期重算，
详见 backend/services/hot_score.py。

Revision ID: 20261109_000001
Revises: 20260927_000002
Create Date: 2026-11-09 00:00:00

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "20261109_000001"
down_revision: Union[str, None] = "20260927_000002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """升级：新增 hot_score 列与索引，并回填已有数据。"""
    with op.batch_alter_table("posts", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column(
                "hot_score",
                sa.Integer(),
                nullable=False,
                server_default=sa.text("0"),
                comment="综合热度物化列：views + likes_count*5 + 有效评论数*3，热榜排序用",
            )
        )
        batch_op.create_index("ix_posts_hot_score", ["hot_score"])

    # 回填已有行：热度 = views + likes_count*5 + 有效评论数*3。
    # likes 由 post_likes 关联表计数（posts 无 likes_count 列）。
    # 同步迁移上下文，op.execute 可用；相关子查询在 SQLite / Postgres 均成立。
    op.execute(
        sa.text(
            """
            UPDATE posts
            SET hot_score = COALESCE(views, 0)
                + (
                    SELECT COUNT(*)
                    FROM post_likes
                    WHERE post_likes.post_id = posts.id
                ) * 5
                + (
                    SELECT COUNT(*)
                    FROM comments
                    WHERE comments.post_id = posts.id AND comments.active = 1
                ) * 3
            """
        )
    )


def downgrade() -> None:
    """回退：删除 hot_score 索引与列。"""
    with op.batch_alter_table("posts", schema=None) as batch_op:
        batch_op.drop_index("ix_posts_hot_score")
        batch_op.drop_column("hot_score")
