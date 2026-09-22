"""make tag color nullable for auto-palette assignment

Revision ID: 20260914_000001
Revises: 87a2ae42cf45
Create Date: 2026-09-14 00:00:01.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260914_000001"
down_revision: str | None = "87a2ae42cf45"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("tags", schema=None) as batch_op:
        batch_op.alter_column(
            "color",
            existing_type=sa.String(20),
            nullable=True,
            server_default=None,
        )


def downgrade() -> None:
    with op.batch_alter_table("tags", schema=None) as batch_op:
        batch_op.alter_column(
            "color",
            existing_type=sa.String(20),
            nullable=False,
            server_default="#64748B",
        )
