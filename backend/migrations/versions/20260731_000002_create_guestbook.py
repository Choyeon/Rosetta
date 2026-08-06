"""create guestbook_entries table with status, pinned, featured, soft-delete

Revision ID: 20260731_000002
Revises: 20260731_000001
Create Date: 2026-07-31 00:02:00.000000
"""

import sqlalchemy as sa
from alembic import op

revision = "20260731_000002"
down_revision = "20260731_000001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "guestbook_entries",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True, nullable=False),
        sa.Column(
            "user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True
        ),
        sa.Column("author_name", sa.String(length=30), nullable=False),
        sa.Column("author_email", sa.String(length=254), nullable=True),
        sa.Column("author_website", sa.String(length=200), nullable=True),
        sa.Column("author_ip", sa.String(length=64), nullable=True),
        sa.Column("author_user_agent", sa.String(length=200), nullable=True),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False, server_default="pending"),
        sa.Column("is_pinned", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("is_featured", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("likes_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )

    with op.batch_alter_table("guestbook_entries", schema=None) as batch_op:
        batch_op.create_index("ix_guestbook_entries_user_id", ["user_id"], unique=False)
        batch_op.create_index("ix_guestbook_entries_status", ["status"], unique=False)
        batch_op.create_index("ix_guestbook_entries_is_pinned", ["is_pinned"], unique=False)
        batch_op.create_index("ix_guestbook_entries_created_at", ["created_at"], unique=False)
        batch_op.create_index(
            "ix_guestbook_status_deleted_pinned_created",
            ["status", "deleted_at", "is_pinned", "created_at"],
            unique=False,
        )
        batch_op.create_index(
            "ix_guestbook_author_ip_created",
            ["author_ip", "created_at"],
            unique=False,
        )


def downgrade() -> None:
    with op.batch_alter_table("guestbook_entries", schema=None) as batch_op:
        batch_op.drop_index("ix_guestbook_author_ip_created")
        batch_op.drop_index("ix_guestbook_status_deleted_pinned_created")
        batch_op.drop_index("ix_guestbook_entries_created_at")
        batch_op.drop_index("ix_guestbook_entries_is_pinned")
        batch_op.drop_index("ix_guestbook_entries_status")
        batch_op.drop_index("ix_guestbook_entries_user_id")

    op.drop_table("guestbook_entries")
