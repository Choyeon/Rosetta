"""添加网站动态表

Revision ID: b7f2a9d3c4e1
Revises: 5182cb36811d
Create Date: 2026-07-31 00:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "b7f2a9d3c4e1"
down_revision: str | None = "5182cb36811d"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """升级数据库"""
    op.create_table(
        "activities",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("content", sa.JSON(), nullable=False),
        sa.Column("type", sa.String(length=20), nullable=False),
        sa.Column("author_id", sa.Integer(), nullable=False),
        sa.Column("is_published", sa.Boolean(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.ForeignKeyConstraint(["author_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_activities_type"), "activities", ["type"], unique=False)
    op.create_index(op.f("ix_activities_author_id"), "activities", ["author_id"], unique=False)
    op.create_index(
        op.f("ix_activities_is_published"), "activities", ["is_published"], unique=False
    )
    op.create_index(op.f("ix_activities_created_at"), "activities", ["created_at"], unique=False)


def downgrade() -> None:
    """回退数据库"""
    op.drop_index(op.f("ix_activities_created_at"), table_name="activities")
    op.drop_index(op.f("ix_activities_is_published"), table_name="activities")
    op.drop_index(op.f("ix_activities_author_id"), table_name="activities")
    op.drop_index(op.f("ix_activities_type"), table_name="activities")
    op.drop_table("activities")
