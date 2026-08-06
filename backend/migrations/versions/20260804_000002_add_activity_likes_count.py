"""为 activities 表增加 likes_count 字段

Revision ID: 20260804_000002
Revises: 20260804_000001
Create Date: 2026-08-04 14:10:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260804_000002"
down_revision: str | None = "20260804_000001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "activities",
        sa.Column("likes_count", sa.Integer(), server_default="0", nullable=False),
    )


def downgrade() -> None:
    op.drop_column("activities", "likes_count")
