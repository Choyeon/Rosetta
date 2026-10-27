"""回收站快照写入 helper（删除侧唯一入口）。

`POST /admin/trash/{id}/restore` 按 `resource_type` 反序列化这里写下的字段并重建原行。
此前每个删除端点各自内联一份 `json.dumps({...})`，结果是**写侧与读侧的字段表分别演化**：
评论的恢复分支只认 post_id/user_id/parent_id/content，而 `author_name`/`status` 都是 NOT NULL，
真去恢复一条评论会当场撞非空约束——即使有人删了评论，这条恢复路径也从未成立过。
新增可恢复资源时，在这里加一个 `<type>_trash_payload()`，恢复分支读同一组键。
"""

import json
import logging
from datetime import datetime
from typing import Any

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models.blog import Comment
from backend.models.core import Page
from backend.models.log import TrashItem
from backend.utils.compat import UTC, timedelta

logger = logging.getLogger(__name__)

# 回收站保留期：前台回收站页的"保留 30 天"文案与自动清理任务都以此为口径。
TRASH_RETENTION_DAYS = 30


def comment_trash_payload(comment: Comment) -> dict:
    """评论快照：覆盖恢复时需要重建的每一列（都是 NOT NULL 或有非默认语义）。

    含 `qq` / `github`：`avatar_source` 为这两档时头像解析要靠对应用户名，漏存会让
    恢复后的评论头像退回 DiceBear。不含 `author_ip` / `author_user_agent`：那是删除时
    的取证信息，复原一条评论不需要、也不该把同一个 IP 再写回审计列。
    """
    return {
        "post_id": comment.post_id,
        "user_id": comment.user_id,
        "parent_id": comment.parent_id,
        "content": comment.content,
        "author_name": comment.author_name,
        "author_email": comment.author_email,
        "author_website": comment.author_website,
        "qq": comment.qq,
        "github": comment.github,
        "avatar_source": comment.avatar_source,
        "status": comment.status,
        "active": comment.active,
        "likes_count": comment.likes_count,
        "is_pinned": comment.is_pinned,
    }


def page_trash_payload(page: Page) -> dict:
    """独立页快照：`pages` 的全部可写列（时间戳由数据库重新生成）。"""
    return {
        "title": page.title,
        "slug": page.slug,
        "content": page.content,
        "status": page.status,
    }


async def snapshot_to_trash(
    db,
    *,
    resource_type: str,
    resource_id: int,
    data: dict[str, Any],
    deleted_by_id: int | None,
) -> TrashItem:
    """把删除前的字段快照写入回收站（调用方随后删除原行）。

    只做 `db.add`，不 flush：调用方本来就要 flush/commit，多一次往返没有意义。
    """
    item = TrashItem(
        resource_type=resource_type,
        resource_id=resource_id,
        resource_data=json.dumps(data),
        deleted_by_id=deleted_by_id,
        auto_delete_at=datetime.now(UTC) + timedelta(days=TRASH_RETENTION_DAYS),
    )
    db.add(item)
    return item


# 分批删的行数上限：与日志保留同口径（单条大 DELETE 会在 SQLite 上长持写锁）。
_BATCH_SIZE = 5000


async def prune_expired_trash(
    db: AsyncSession,
    *,
    now: datetime | None = None,
    batch_size: int = _BATCH_SIZE,
) -> int:
    """删除已到期的回收站记录，返回删除条数。

    回收站页的文案承诺「已删除的内容在此保留 30 天」，而快照里存的是**整篇正文**
    （文章的 `content` 多语言 JSON 全量）。没有这个清理，那条承诺只是免责声明的反面：
    用户删掉的内容会永久留在库里，后台「回收站」也只会一直变长。
    由 ``main.py`` 的日志保留循环按同一节奏调用（刻意**先睡后删**，见那里）。

    只删 `auto_delete_at` 已落库且已过期的行：历史数据里该列为 NULL 的行不动——
    那可能是手工插入或旧版本写入的记录，宁可让管理员在回收站里手动清。
    """
    cutoff = now or datetime.now(UTC)
    total = 0
    while True:
        ids = list(
            (
                await db.execute(
                    select(TrashItem.id)
                    .where(TrashItem.auto_delete_at.isnot(None))
                    .where(TrashItem.auto_delete_at < cutoff)
                    .limit(batch_size)
                )
            )
            .scalars()
            .all()
        )
        if not ids:
            break
        await db.execute(delete(TrashItem).where(TrashItem.id.in_(ids)))
        total += len(ids)
        if len(ids) < batch_size:
            break

    await db.commit()
    if total:
        logger.info("[retention] 清理 %s 之前的回收站记录 %d 条", cutoff.isoformat(), total)
    return total


__all__ = [
    "TRASH_RETENTION_DAYS",
    "comment_trash_payload",
    "page_trash_payload",
    "prune_expired_trash",
    "snapshot_to_trash",
]
