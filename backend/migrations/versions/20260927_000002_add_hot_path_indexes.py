"""add_hot_path_indexes

性能审计第二轮：外键索引（20260927_000001）之后仍有一批「热查询谓词无索引」，
全部落在只增表 / 关联表上，随数据量线性退化为顺序扫描：

1. post_tags.tag_id —— 复合主键 (post_id, tag_id) 服务不到「按标签筛文章」；
2. post_likes.user_id —— 复合主键 (post_id, user_id) 服务不到 /users/me/likes；
3. webhook_deliveries (endpoint_id, delivered_at) —— 全表零索引，且端点列表按行
   做 `max(delivered_at)` 相关子查询；
4. notifications (recipient_id, is_read) / (recipient_id, created_at) —— 角标轮询的
   未读 COUNT 与 `ORDER BY created_at DESC LIMIT`；
5. private_messages (recipient_id, is_read) —— 未读总数与按对端分组的未读 COUNT；
6. favorites.folder_id —— 收藏夹计数 `WHERE folder_id IN (...)` 与按夹筛选；
7. post_view_histories (user_id, viewed_at) —— /users/me/history 按用户排序浏览时间。

与模型层声明（index=True / __table_args__ 内的 Index）一一对应，名称沿用
SQLAlchemy 默认约定 ix_<table>_<cols>，保证后续 autogenerate 无抖动。
纯 ADDITIVE：只 create_index，downgrade 只 drop_index，绝不触碰表/列结构。
索引列一律升序（B 树反向扫描即可满足 DESC，SQLite 与 PostgreSQL 同样成立），
不使用 postgresql_where / postgresql_ops，两种方言共用同一份 DDL。

Revision ID: 20260927_000002
Revises: 20260927_000001
Create Date: 2026-09-27 04:10:00

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "20260927_000002"
down_revision: str | None = "20260927_000001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# (索引名, 表名, 列清单) —— 顺序即 upgrade 创建顺序，downgrade 逆序删除。
_TARGETS: tuple[tuple[str, str, tuple[str, ...]], ...] = (
    ("ix_post_tags_tag_id", "post_tags", ("tag_id",)),
    ("ix_post_likes_user_id", "post_likes", ("user_id",)),
    (
        "ix_webhook_deliveries_endpoint_delivered",
        "webhook_deliveries",
        ("endpoint_id", "delivered_at"),
    ),
    ("ix_notifications_recipient_read", "notifications", ("recipient_id", "is_read")),
    ("ix_notifications_recipient_created", "notifications", ("recipient_id", "created_at")),
    ("ix_private_messages_recipient_read", "private_messages", ("recipient_id", "is_read")),
    ("ix_favorites_folder_id", "favorites", ("folder_id",)),
    ("ix_post_view_histories_user_viewed", "post_view_histories", ("user_id", "viewed_at")),
)


def _indexes(table_name: str) -> set[str]:
    inspector = sa.inspect(op.get_bind())
    return {idx["name"] for idx in inspector.get_indexes(table_name)}


def upgrade() -> None:
    for idx_name, table, columns in _TARGETS:
        if idx_name in _indexes(table):
            continue
        op.create_index(idx_name, table, list(columns))


def downgrade() -> None:
    # 逆序删除，与 upgrade 对称；仅删本迁移新建的索引。
    for idx_name, table, _columns in reversed(_TARGETS):
        if idx_name in _indexes(table):
            op.drop_index(idx_name, table_name=table)
