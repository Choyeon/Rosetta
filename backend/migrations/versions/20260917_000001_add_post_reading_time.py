"""add_post_reading_time_column

为 posts 表新增 reading_time 列，预计算阅读时长（分钟），
避免列表接口实时对大文本 content 做正则统计。

Revision ID: 20260917_000001
Revises: 20260914_000001
Create Date: 2026-09-17 13:05:00

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "20260917_000001"
down_revision: Union[str, None] = "20260914_000001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """升级：为 posts 表添加 reading_time 列（默认 1 分钟）。"""
    with op.batch_alter_table("posts", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column(
                "reading_time",
                sa.Integer(),
                nullable=False,
                server_default=sa.text("1"),
                comment="预计算阅读时长（分钟），写入时根据 content 字数计算",
            )
        )


def downgrade() -> None:
    """回退：删除 posts 表的 reading_time 列。"""
    with op.batch_alter_table("posts", schema=None) as batch_op:
        batch_op.drop_column("reading_time")
