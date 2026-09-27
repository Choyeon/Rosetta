"""外键索引守卫（纯模型元数据，不触碰任何数据库）。

背景：8 个高频外键列此前缺索引 —— 反向关系按 FK 惰性加载、以及
ON DELETE CASCADE/SET NULL 反查子行时都会退化为全表扫描。已在模型层
补 `index=True` 并写 ADDITIVE 迁移落地。本用例锁定这一状态：任何后续
改动若悄悄移除了这些列的索引守卫，测试立即失败。

为什么只读 Base.metadata 而不连库：CI 里静态导入的 async_session_maker
会绕过 get_db 覆写、误写真实 rosetta.db（见既有约束），元数据检查无副作用。
"""

from __future__ import annotations

# 导入全部模型，确保 Base.metadata 收齐所有表定义。
# 注意：backend.models 包 __init__ 未 re-export revision / log，需显式导入，
# 否则 post_revisions / trash_items 不在 metadata 里。
import backend.models  # noqa: F401  (触发模型注册)
import backend.models.log  # noqa: F401
import backend.models.revision  # noqa: F401
from backend.core.database import Base

# (表名, 列名) —— 需要被某个索引作为「最左列」覆盖的外键列。
INDEXED_FK_COLUMNS = {
    ("posts", "category_id"),
    ("comments", "user_id"),
    ("media", "uploaded_by_id"),
    ("navigations", "parent_id"),
    ("notifications", "actor_id"),
    ("post_revisions", "author_id"),
    ("trash_items", "deleted_by_id"),
    ("users", "title_id"),
    # post_view_histories：user_id 是复合唯一索引最左列，post_id 需独立索引
    ("post_view_histories", "post_id"),
}


def _indexed_leading_columns(table) -> set[str]:
    """收集该表所有索引（含单列 index=True、__table_args__ 里的 Index）的最左列。"""
    cols: set[str] = set()
    for idx in table.indexes:
        for part in idx.columns:
            cols.add(part.name)
            break  # 只认最左列，复合索引非最左列不算覆盖
    return cols


def test_all_target_fk_columns_have_index():
    tables = Base.metadata.tables
    for table_name, column_name in INDEXED_FK_COLUMNS:
        assert table_name in tables, f"缺少表 {table_name}（模型未导入？）"
        table = tables[table_name]
        assert column_name in table.columns, f"{table_name} 没有列 {column_name}"
        covered = _indexed_leading_columns(table)
        assert column_name in covered, (
            f"{table_name}.{column_name} 未被任何索引最左列覆盖 —— "
            "外键查询/级联删除会全表扫描，请补回 index=True"
        )
