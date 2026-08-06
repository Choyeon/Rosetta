"""add user auth fields: token_version, locked_until, notify_by_email, failed_login_attempts

Revision ID: 20260731_000000
Revises: a1576082c8a6
Create Date: 2026-07-31 00:00:00.000000
"""

import sqlalchemy as sa
from alembic import op

revision = "20260731_000000"
down_revision = "a1576082c8a6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("users", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column(
                "token_version",
                sa.Integer(),
                server_default="0",
                nullable=False,
            )
        )
        batch_op.create_index(
            "ix_users_token_version",
            ["token_version"],
            unique=False,
        )
        batch_op.add_column(
            sa.Column(
                "locked_until",
                sa.DateTime(timezone=True),
                nullable=True,
            )
        )
        batch_op.add_column(
            sa.Column(
                "notify_by_email",
                sa.Boolean(),
                server_default=sa.true(),
                nullable=False,
            )
        )
        batch_op.add_column(
            sa.Column(
                "failed_login_attempts",
                sa.Integer(),
                server_default="0",
                nullable=False,
            )
        )


def downgrade() -> None:
    with op.batch_alter_table("users", schema=None) as batch_op:
        batch_op.drop_column("failed_login_attempts")
        batch_op.drop_column("notify_by_email")
        batch_op.drop_column("locked_until")
        batch_op.drop_index("ix_users_token_version")
        batch_op.drop_column("token_version")
