"""add plugins and themes tables

Revision ID: 87a2ae42cf45
Revises: 20260806_000003
Create Date: 2026-08-27 20:53:43.323321

注意：本文件最初的 autogenerate 产物是错误的"drop 全部核心表"迁移
（upgrade 会删除 users/posts 等所有表且从不创建 themes/plugins），
已按修订名重做为真正的建表迁移。幂等设计：若表已由 ORM create_all
建立则跳过，绝不触碰其它表。

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "87a2ae42cf45"
down_revision: str | None = "20260806_000003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _json_type() -> sa.types.TypeEngine:
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        return postgresql.JSONB(astext_type=sa.Text())
    return sa.JSON()


def _has_table(name: str) -> bool:
    return name in sa.inspect(op.get_bind()).get_table_names()


def _define_plugin_table(metadata: sa.MetaData) -> sa.Table:
    return sa.Table(
        "plugins",
        metadata,
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("slug", sa.String(length=100), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("version", sa.String(length=32), nullable=False),
        sa.Column("author", sa.String(length=200), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column(
            "status", sa.String(length=16), server_default="inactive", nullable=False
        ),
        sa.Column(
            "manifest_version", sa.String(length=8), server_default="1.0", nullable=False
        ),
        sa.Column("requires_rosetta", sa.String(length=16), nullable=True),
        sa.Column("plugin_uri", sa.String(length=500), nullable=True),
        sa.Column("author_uri", sa.String(length=500), nullable=True),
        sa.Column("textdomain", sa.String(length=64), nullable=True),
        sa.Column("folder", sa.String(length=300), nullable=False),
        sa.Column("settings_schema", _json_type(), nullable=True),
        sa.Column("install_path", sa.String(length=500), nullable=True),
        sa.Column("installed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("activated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("site_id", sa.Integer(), server_default="1", nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("site_id", "slug", name="uq_plugins_site_slug"),
        comment="Plugins installed metadata",
    )


def _define_theme_table(metadata: sa.MetaData) -> sa.Table:
    return sa.Table(
        "themes",
        metadata,
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("slug", sa.String(length=100), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("version", sa.String(length=32), nullable=False),
        sa.Column("author", sa.String(length=200), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column(
            "status", sa.String(length=16), server_default="installed", nullable=False
        ),
        sa.Column(
            "is_active",
            sa.Boolean(),
            server_default=sa.false(),
            nullable=False,
        ),
        sa.Column(
            "manifest_version", sa.String(length=8), server_default="1.0", nullable=False
        ),
        sa.Column("requires_rosetta", sa.String(length=16), nullable=True),
        sa.Column("theme_uri", sa.String(length=500), nullable=True),
        sa.Column("author_uri", sa.String(length=500), nullable=True),
        sa.Column("textdomain", sa.String(length=64), nullable=True),
        sa.Column("folder", sa.String(length=300), nullable=False),
        sa.Column("mods_schema", _json_type(), nullable=True),
        sa.Column("parent_theme", sa.String(length=100), nullable=True),
        sa.Column("screenshot_urls", _json_type(), nullable=True),
        sa.Column("tags", _json_type(), nullable=True),
        sa.Column("install_path", sa.String(length=500), nullable=True),
        sa.Column("installed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("activated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("site_id", sa.Integer(), server_default="1", nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("site_id", "slug", name="uq_themes_site_slug"),
        comment="Themes installed metadata",
    )


def upgrade() -> None:
    """创建 plugins / themes 元数据表（幂等：已存在则跳过）。"""
    bind = op.get_bind()
    for define in (_define_plugin_table, _define_theme_table):
        table = define(sa.MetaData())
        if not _has_table(table.name):
            table.create(bind=bind)
            with op.batch_alter_table(table.name, schema=None) as batch_op:
                batch_op.create_index(f"ix_{table.name}_slug", ["slug"], unique=False)
                batch_op.create_index(
                    f"ix_{table.name}_status", ["status"], unique=False
                )
                batch_op.create_index(
                    f"ix_{table.name}_site_id", ["site_id"], unique=False
                )
                if table.name == "themes":
                    batch_op.create_index(
                        "ix_themes_is_active", ["is_active"], unique=False
                    )


def downgrade() -> None:
    """仅回退本迁移创建的两张表，不触碰其它任何表。"""
    for name in ("themes", "plugins"):
        if _has_table(name):
            op.drop_table(name)
