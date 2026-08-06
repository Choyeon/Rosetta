"""add_performance_indexes

Revision ID: 20260731_000005
Revises: 20260731_000004
Create Date: 2026-07-31 00:00:05.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260731_000005"
down_revision: str | None = "20260731_000004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _index_exists(table_name: str, index_name: str) -> bool:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    existing = {idx["name"] for idx in inspector.get_indexes(table_name)}
    return index_name in existing


def upgrade() -> None:
    dialect = op.get_context().dialect.name
    is_pg = dialect == "postgresql"

    # ========== posts ==========
    if not _index_exists("posts", "ix_posts_cat_status_created"):
        op.create_index(
            "ix_posts_cat_status_created",
            "posts",
            ["category_id", "status", "created_at"],
            postgresql_ops={
                "category_id": "ASC",
                "status": "ASC",
                "created_at": "DESC",
            }
            if is_pg
            else None,
        )

    if not _index_exists("posts", "ix_posts_status_published_created"):
        sa.text("published_at DESC NULLS LAST") if is_pg else "published_at"
        op.execute(
            sa.text(
                "CREATE INDEX IF NOT EXISTS ix_posts_status_published_created "
                "ON posts (status ASC, published_at DESC NULLS LAST, created_at DESC)"
            )
            if is_pg
            else "CREATE INDEX IF NOT EXISTS ix_posts_status_published_created "
            "ON posts (status, published_at, created_at)"
        )

    # ========== comments ==========
    if not _index_exists("comments", "ix_comments_parent_status_created_asc"):
        op.create_index(
            "ix_comments_parent_status_created_asc",
            "comments",
            ["parent_id", "status", "created_at"],
            postgresql_ops={
                "parent_id": "ASC",
                "status": "ASC",
                "created_at": "ASC",
            }
            if is_pg
            else None,
        )

    # ========== operation_logs ==========
    if not _index_exists("operation_logs", "ix_operation_logs_created_action_user"):
        op.create_index(
            "ix_operation_logs_created_action_user",
            "operation_logs",
            ["created_at", "action", "user_id"],
            postgresql_ops={
                "created_at": "DESC",
                "action": "ASC",
                "user_id": "ASC",
            }
            if is_pg
            else None,
        )


def downgrade() -> None:
    if _index_exists("operation_logs", "ix_operation_logs_created_action_user"):
        op.drop_index("ix_operation_logs_created_action_user", table_name="operation_logs")

    if _index_exists("comments", "ix_comments_parent_status_created_asc"):
        op.drop_index("ix_comments_parent_status_created_asc", table_name="comments")

    if _index_exists("posts", "ix_posts_status_published_created"):
        op.drop_index("ix_posts_status_published_created", table_name="posts")

    if _index_exists("posts", "ix_posts_cat_status_created"):
        op.drop_index("ix_posts_cat_status_created", table_name="posts")
