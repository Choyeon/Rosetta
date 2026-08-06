"""add encryption_salt/verifier/algorithm columns to Post model

Revision ID: 20260731_000003
Revises: 20260731_000002
Create Date: 2026-07-31 00:03:00.000000
"""

import sqlalchemy as sa
from alembic import op

revision = "20260731_000003"
down_revision = "20260731_000002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("posts", schema=None) as batch_op:
        batch_op.add_column(sa.Column("encryption_salt", sa.String(length=128), nullable=True))
        batch_op.add_column(sa.Column("encryption_verifier", sa.String(length=256), nullable=True))
        batch_op.add_column(
            sa.Column(
                "encryption_algorithm",
                sa.String(length=50),
                nullable=False,
                server_default="AES-256-GCM",
            )
        )


def downgrade() -> None:
    with op.batch_alter_table("posts", schema=None) as batch_op:
        batch_op.drop_column("encryption_algorithm")
        batch_op.drop_column("encryption_verifier")
        batch_op.drop_column("encryption_salt")
