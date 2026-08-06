"""add comment and guestbook qq, github, avatar_source fields

Revision ID: 20260806_000002
Revises: 20260806_000001
Create Date: 2026-08-06 00:00:02.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260806_000002"
down_revision: str | None = "20260806_000001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("comments", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column(
                "qq",
                sa.String(length=20),
                nullable=True,
            )
        )
        batch_op.create_index(
            "ix_comments_qq",
            ["qq"],
            unique=False,
        )
        batch_op.add_column(
            sa.Column(
                "github",
                sa.String(length=64),
                nullable=True,
            )
        )
        batch_op.add_column(
            sa.Column(
                "avatar_source",
                sa.String(length=16),
                nullable=False,
                server_default="auto",
            )
        )

    with op.batch_alter_table("guestbook_entries", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column(
                "qq",
                sa.String(length=20),
                nullable=True,
            )
        )
        batch_op.create_index(
            "ix_guestbook_qq",
            ["qq"],
            unique=False,
        )
        batch_op.add_column(
            sa.Column(
                "github",
                sa.String(length=64),
                nullable=True,
            )
        )
        batch_op.add_column(
            sa.Column(
                "avatar_source",
                sa.String(length=16),
                nullable=False,
                server_default="auto",
            )
        )


def downgrade() -> None:
    with op.batch_alter_table("guestbook_entries", schema=None) as batch_op:
        batch_op.drop_column("avatar_source")
        batch_op.drop_column("github")
        batch_op.drop_index("ix_guestbook_qq")
        batch_op.drop_column("qq")

    with op.batch_alter_table("comments", schema=None) as batch_op:
        batch_op.drop_column("avatar_source")
        batch_op.drop_column("github")
        batch_op.drop_index("ix_comments_qq")
        batch_op.drop_column("qq")
