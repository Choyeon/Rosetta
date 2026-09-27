"""
文章修订版本（版本历史）服务

版本快照的唯一写入口。此前全仓只有 ``restore_post_revision`` 会落一条
「恢复前备份」，正常的编辑保存路径一条都不写 —— 于是版本列表恒空，
compare / restore 两个端点在真实数据下永远不可达。
"""

from __future__ import annotations

import json
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models.blog import Post
from backend.models.revision import PostRevision

# 只有这些字段参与版本内容：改状态/改封面不构成一个可回滚的「版本」。
SNAPSHOT_FIELDS = ("title", "content", "excerpt")


def _as_json_text(value: Any) -> str | None:
    """快照列是 Text，统一把 dict 序列化成 JSON 字符串（字符串原样存）。"""
    if value is None:
        return None
    return json.dumps(value, ensure_ascii=False) if isinstance(value, (dict, list)) else value


async def snapshot_post_revision(
    db: AsyncSession,
    *,
    post: Post,
    author_id: int | None,
    change_summary: str | None = None,
) -> PostRevision:
    """把文章**当前**内容另存为一个修订版本（不落库由调用方的 flush 统一提交）。"""
    next_number = (
        await db.scalar(
            select(func.max(PostRevision.revision_number)).where(PostRevision.post_id == post.id)
        )
        or 0
    ) + 1

    revision = PostRevision(
        post_id=post.id,
        revision_number=next_number,
        # title/content 列是 NOT NULL：历史数据里存在空标题时也要能落快照，不能 500。
        title=_as_json_text(post.title) or "",
        content=_as_json_text(post.content) or "",
        excerpt=_as_json_text(post.excerpt),
        author_id=author_id,
        change_summary=change_summary,
    )
    db.add(revision)
    return revision


def has_content_change(post: Post, update_data: dict[str, Any]) -> bool:
    """本次更新是否会改动版本快照覆盖的内容字段（且值确实不同）。

    必须逐字段比对：编辑器每次保存都会把整份表单 PUT 回来，若只看键存在，
    「只改状态」的保存也会生成一条与上一版字节相同的空版本。
    """
    return any(
        field in update_data and getattr(post, field, None) != update_data[field]
        for field in SNAPSHOT_FIELDS
    )
