"""add user qq and avatar_source fields

Revision ID: 20260806_000001
Revises: 5018757acef3
Create Date: 2026-08-06 00:00:01.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260806_000001"
down_revision: str | None = "5018757acef3"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("users", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column(
                "qq",
                sa.String(length=20),
                nullable=True,
                comment="QQ 号（可选）",
            )
        )
        batch_op.create_index(
            "ix_users_qq",
            ["qq"],
            unique=False,
        )
        batch_op.add_column(
            sa.Column(
                "avatar_source",
                sa.String(length=16),
                nullable=False,
                server_default="auto",
                comment="头像来源 auto/custom/github/qq/gravatar",
            )
        )


def downgrade() -> None:
    with op.batch_alter_table("users", schema=None) as batch_op:
        batch_op.drop_index("ix_users_qq")
        batch_op.drop_column("qq")
        batch_op.drop_column("avatar_source")
