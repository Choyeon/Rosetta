"""add category parent_id and is_active fields

Revision ID: 20260806_000003
Revises: 20260806_000002
Create Date: 2026-08-06 00:00:03.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260806_000003"
down_revision: str | None = "20260806_000002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("categories", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column(
                "parent_id",
                sa.Integer(),
                nullable=True,
            )
        )
        batch_op.add_column(
            sa.Column(
                "is_active",
                sa.Boolean(),
                nullable=False,
                server_default=sa.true(),
            )
        )
        batch_op.create_foreign_key(
            "fk_categories_parent_id_categories",
            "categories",
            ["parent_id"],
            ["id"],
            ondelete="SET NULL",
        )
        batch_op.create_index(
            "ix_categories_parent_id",
            ["parent_id"],
            unique=False,
        )
        batch_op.create_index(
            "ix_categories_is_active",
            ["is_active"],
            unique=False,
        )


def downgrade() -> None:
    with op.batch_alter_table("categories", schema=None) as batch_op:
        batch_op.drop_index("ix_categories_is_active")
        batch_op.drop_index("ix_categories_parent_id")
        batch_op.drop_constraint(
            "fk_categories_parent_id_categories",
            type_="foreignkey",
        )
        batch_op.drop_column("is_active")
        batch_op.drop_column("parent_id")
