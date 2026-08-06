"""添加相册（Gallery）表 - albums 和 photos

Revision ID: 20260804_000001
Revises: cdbb46311155
Create Date: 2026-08-04 14:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260804_000001"
down_revision: str | None = "cdbb46311155"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "albums",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("cover", sa.String(length=500), nullable=True),
        sa.Column("sort_order", sa.Integer(), server_default="0", nullable=False),
        sa.Column("is_published", sa.Boolean(), server_default=sa.true(), nullable=False),
        sa.Column("photo_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("author_id", sa.Integer(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["author_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_albums_is_published"), "albums", ["is_published"], unique=False)
    op.create_index(op.f("ix_albums_author_id"), "albums", ["author_id"], unique=False)
    op.create_index(op.f("ix_albums_created_at"), "albums", ["created_at"], unique=False)

    op.create_table(
        "photos",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("album_id", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=200), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("url", sa.String(length=500), nullable=False),
        sa.Column("sort_order", sa.Integer(), server_default="0", nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["album_id"], ["albums.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_photos_album_id"), "photos", ["album_id"], unique=False)
    op.create_index(op.f("ix_photos_created_at"), "photos", ["created_at"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_photos_created_at"), table_name="photos")
    op.drop_index(op.f("ix_photos_album_id"), table_name="photos")
    op.drop_table("photos")

    op.drop_index(op.f("ix_albums_created_at"), table_name="albums")
    op.drop_index(op.f("ix_albums_author_id"), table_name="albums")
    op.drop_index(op.f("ix_albums_is_published"), table_name="albums")
    op.drop_table("albums")
