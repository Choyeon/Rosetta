"""extend comments with author fields, status, likes, pinned, updated_at + indexes

Revision ID: 20260731_000001
Revises: 20260731_000000
Create Date: 2026-07-31 00:01:00.000000
"""

import sqlalchemy as sa
from alembic import op

revision = "20260731_000001"
down_revision = "20260731_000000"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("comments", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column(
                "author_name",
                sa.String(length=30),
                nullable=False,
                server_default="Guest",
            )
        )
        batch_op.add_column(
            sa.Column(
                "author_email",
                sa.String(length=254),
                nullable=True,
            )
        )
        batch_op.add_column(
            sa.Column(
                "author_website",
                sa.String(length=200),
                nullable=True,
            )
        )
        batch_op.add_column(
            sa.Column(
                "author_ip",
                sa.String(length=64),
                nullable=True,
            )
        )
        batch_op.add_column(
            sa.Column(
                "author_user_agent",
                sa.String(length=200),
                nullable=True,
            )
        )
        batch_op.add_column(
            sa.Column(
                "status",
                sa.String(length=16),
                nullable=False,
                server_default="pending",
            )
        )
        batch_op.add_column(
            sa.Column(
                "likes_count",
                sa.Integer(),
                nullable=False,
                server_default="0",
            )
        )
        batch_op.add_column(
            sa.Column(
                "is_pinned",
                sa.Boolean(),
                nullable=False,
                server_default=sa.false(),
            )
        )
        batch_op.add_column(
            sa.Column(
                "reported_at",
                sa.DateTime(timezone=True),
                nullable=True,
            )
        )
        batch_op.add_column(
            sa.Column(
                "updated_at",
                sa.DateTime(timezone=True),
                nullable=False,
                server_default=sa.func.now(),
            )
        )
        batch_op.alter_column(
            "user_id",
            existing_type=sa.Integer(),
            nullable=True,
        )
        batch_op.create_index(
            "ix_comments_status",
            ["status"],
            unique=False,
        )
        batch_op.create_index(
            "ix_comments_post_status_created",
            ["post_id", "status", "created_at"],
            unique=False,
        )
        batch_op.create_index(
            "ix_comments_author_ip_created",
            ["author_ip", "created_at"],
            unique=False,
        )


def downgrade() -> None:
    with op.batch_alter_table("comments", schema=None) as batch_op:
        batch_op.drop_index("ix_comments_author_ip_created")
        batch_op.drop_index("ix_comments_post_status_created")
        batch_op.drop_index("ix_comments_status")
        batch_op.alter_column(
            "user_id",
            existing_type=sa.Integer(),
            nullable=False,
        )
        batch_op.drop_column("updated_at")
        batch_op.drop_column("reported_at")
        batch_op.drop_column("is_pinned")
        batch_op.drop_column("likes_count")
        batch_op.drop_column("status")
        batch_op.drop_column("author_user_agent")
        batch_op.drop_column("author_ip")
        batch_op.drop_column("author_website")
        batch_op.drop_column("author_email")
        batch_op.drop_column("author_name")
