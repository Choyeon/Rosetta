"""create_operation_logs_add_error_code

Revision ID: 20260731_000004
Revises: 20260731_000003
Create Date: 2026-07-31 00:00:04.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260731_000004"
down_revision: str | None = "20260731_000003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    cols = [c["name"] for c in inspector.get_columns("operation_logs")]
    if "error_code" not in cols:
        op.add_column(
            "operation_logs",
            sa.Column("error_code", sa.String(length=100), nullable=True),
        )


def downgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    cols = [c["name"] for c in inspector.get_columns("operation_logs")]
    if "error_code" in cols:
        op.drop_column("operation_logs", "error_code")
