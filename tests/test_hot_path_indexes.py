"""热路径索引守卫（纯模型元数据 + Alembic 版本图，不连接任何数据库）。

背景：性能审计第二轮补建了 8 个「热查询谓词无索引」的索引 —— 集中在关联表与
只增表（webhook_deliveries / notifications / private_messages）上，缺索引时
每次轮询都是一次顺序扫描。落地为 ADDITIVE 迁移
`backend/migrations/versions/20260927_000002_add_hot_path_indexes.py`，
并在模型层同步声明（`index=True` / `__table_args__` 内的 `Index`）。

本用例钉住三件事：
1. 每个索引名与列清单在 Base.metadata 上真实存在（模型声明没被悄悄删掉）；
2. 迁移文件的 _TARGETS 与模型声明逐字一致（否则 autogenerate 会抖动）；
3. Alembic 只有一个 head，且新迁移是它（无分叉、无遗留并行分支）。

与 test_fk_index_guards.py 一样只看元数据：CI 里静态导入 async_session_maker
会绕过 get_db 覆写、误写真实 rosetta.db，元数据检查无副作用。
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

from alembic.script import ScriptDirectory

# 导入全部模型，确保 Base.metadata 收齐所有表定义。
# Favorite / WebhookDelivery 这类历史遗留模型直接定义在 api 层，必须显式导入。
import backend.api.favorite  # noqa: F401
import backend.api.webhook  # noqa: F401
import backend.models  # noqa: F401  (触发模型注册)
import backend.models.log  # noqa: F401
import backend.models.revision  # noqa: F401
from backend.core.database import Base
from backend.migrations.config import get_alembic_config

REPO_ROOT = Path(__file__).resolve().parents[1]
MIGRATION_REVISION = "20260927_000002"
PREVIOUS_REVISION = "20260927_000001"
MIGRATION_PATH = (
    REPO_ROOT
    / "backend"
    / "migrations"
    / "versions"
    / f"{MIGRATION_REVISION}_add_hot_path_indexes.py"
)

# 索引名 -> (表名, 列清单（按索引内顺序）)
HOT_PATH_INDEXES: dict[str, tuple[str, tuple[str, ...]]] = {
    # 关联表复合主键 (post_id, tag_id) / (post_id, user_id) 的最左前缀
    # 服务不到「按标签筛文章」与「我点赞的文章」。
    "ix_post_tags_tag_id": ("post_tags", ("tag_id",)),
    "ix_post_likes_user_id": ("post_likes", ("user_id",)),
    # 只增表：端点列表的相关子查询 max(delivered_at) + 投递记录分页过滤。
    "ix_webhook_deliveries_endpoint_delivered": (
        "webhook_deliveries",
        ("endpoint_id", "delivered_at"),
    ),
    # 角标轮询的未读 COUNT，与列表页 ORDER BY created_at DESC LIMIT。
    "ix_notifications_recipient_read": ("notifications", ("recipient_id", "is_read")),
    "ix_notifications_recipient_created": ("notifications", ("recipient_id", "created_at")),
    "ix_private_messages_recipient_read": ("private_messages", ("recipient_id", "is_read")),
    # 收藏夹计数 `WHERE folder_id IN (...)`（folder_id 可为 NULL = 默认收藏）。
    "ix_favorites_folder_id": ("favorites", ("folder_id",)),
    # /users/me/history 按用户取浏览时间排序。
    "ix_post_view_histories_user_viewed": ("post_view_histories", ("user_id", "viewed_at")),
}


def _load_migration_module():
    assert MIGRATION_PATH.exists(), f"缺少迁移文件：{MIGRATION_PATH}"
    spec = importlib.util.spec_from_file_location("hot_path_indexes_migration", MIGRATION_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_hot_path_indexes_declared_on_metadata():
    tables = Base.metadata.tables
    for index_name, (table_name, columns) in HOT_PATH_INDEXES.items():
        assert table_name in tables, f"缺少表 {table_name}（模型未导入？）"
        table = tables[table_name]
        matched = [idx for idx in table.indexes if idx.name == index_name]
        assert matched, (
            f"{table_name} 上不存在索引 {index_name} —— 热查询会退化为全表扫描，"
            "请补回模型层声明（index=True / __table_args__ 的 Index）"
        )
        actual = tuple(col.name for col in matched[0].columns)
        assert actual == columns, f"索引 {index_name} 列清单漂移：期望 {columns}，实际 {actual}"


def test_migration_targets_match_model_declarations():
    """迁移 _TARGETS 与模型声明必须逐字一致，否则未来 autogenerate 会抖出多余索引。"""
    module = _load_migration_module()
    migration_targets = {
        (index_name, table_name, tuple(columns))
        for index_name, table_name, columns in module._TARGETS
    }
    model_targets = {
        (index_name, table_name, columns)
        for index_name, (table_name, columns) in HOT_PATH_INDEXES.items()
    }
    assert migration_targets == model_targets, (
        "迁移与模型声明不一致："
        f"仅迁移有 {sorted(migration_targets - model_targets)}，"
        f"仅模型有 {sorted(model_targets - migration_targets)}"
    )
    assert module.revision == MIGRATION_REVISION
    assert module.down_revision == PREVIOUS_REVISION


def test_alembic_has_single_linear_head():
    script = ScriptDirectory.from_config(get_alembic_config())
    heads = script.get_heads()
    assert len(heads) == 1, f"Alembic 出现多 head 分叉：{heads}，需要先 merge 再提交"
    assert heads[0] == MIGRATION_REVISION, f"当前 head 应为 {MIGRATION_REVISION}，实际 {heads[0]}"

    # 头节点往回走的链条上不得再次出现分叉入口（同一 down_revision 被多个迁移引用）。
    children: dict[str, list[str]] = {}
    for rev in script.walk_revisions():
        for parent in rev.down_revision or ():
            children.setdefault(parent, []).append(rev.revision)
    branched = {parent: kids for parent, kids in children.items() if len(kids) > 1}
    # 历史里允许的合并点（merge 迁移）之后不得再产生新的分叉父节点。
    assert MIGRATION_REVISION not in branched, (
        f"{MIGRATION_REVISION} 之后又分叉出 {branched[MIGRATION_REVISION]}"
    )
