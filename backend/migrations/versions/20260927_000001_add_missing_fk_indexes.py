"""add_missing_fk_indexes

外键列缺索引会导致两类全表扫描：
1. 反向关系加载（category.posts / user.comments / navigation.children 等
   集合按 FK 惰性加载时 `SELECT ... WHERE <fk> = ?`）；
2. ON DELETE CASCADE / SET NULL 触发时数据库需按 FK 反查子行。

本迁移为此前审计出的 9 个未建索引外键列补建单列索引，与模型层 index=True 对齐。
纯 ADDITIVE：只 create_index，downgrade 只 drop_index，绝不触碰表/列结构。

Revision ID: 20260927_000001
Revises: 20260926_000001
Create Date: 2026-09-27 02:39:00

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "20260927_000001"
down_revision: str | None = "20260926_000001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# (table, column) —— 索引名沿用 SQLAlchemy 默认约定 ix_<table>_<column>，
# 与模型 mapped_column(index=True) 生成的名称保持一致，避免 autogenerate 抖动。
_TARGETS: tuple[tuple[str, str], ...] = (
    ("posts", "category_id"),
    ("comments", "user_id"),
    ("media", "uploaded_by_id"),
    ("navigations", "parent_id"),
    ("notifications", "actor_id"),
    ("post_revisions", "author_id"),
    ("trash_items", "deleted_by_id"),
    ("users", "title_id"),
    # post_id 仅是复合唯一索引 (user_id, post_id) 的第二列，
    # 按 post_id 反查（删除文章时 CASCADE）走不到最左前缀，需单列索引。
    ("post_view_histories", "post_id"),
)


def _indexes(table_name: str) -> set[str]:
    inspector = sa.inspect(op.get_bind())
    return {idx["name"] for idx in inspector.get_indexes(table_name)}


def upgrade() -> None:
    for table, column in _TARGETS:
        idx_name = f"ix_{table}_{column}"
        if idx_name in _indexes(table):
            continue
        op.create_index(idx_name, table, [column])


def downgrade() -> None:
    # 逆序删除，与 upgrade 对称；仅删本迁移新建的索引。
    for table, column in reversed(_TARGETS):
        idx_name = f"ix_{table}_{column}"
        if idx_name in _indexes(table):
            op.drop_index(idx_name, table_name=table)
