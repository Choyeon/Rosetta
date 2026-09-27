"""归档统计 `PostRepository.get_archive_stats` 的正确性与查询次数

原实现对每个年份单发一条 `COUNT`（先 DISTINCT 年份再逐年统计），归档统计的
查询数随年份数线性增长。现改为一次 `GROUP BY`。本文件同时钉住：
1. 结果与逐年统计完全等价（含"草稿不计入"、"published_at 为空回落 created_at"）
2. 查询次数恒为常数
"""

from __future__ import annotations

from datetime import datetime

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models.blog import Category, Post
from backend.models.user import User
from backend.repositories.post import PostRepository


class _CountingSession:
    """透明代理：统计 `execute` 次数，其余转发给真实 session"""

    def __init__(self, inner: AsyncSession) -> None:
        self._inner = inner
        self.executes = 0

    def __getattr__(self, name):
        attr = getattr(self._inner, name)
        if name != "execute":
            return attr

        async def counted(*args, **kwargs):
            self.executes += 1
            return await attr(*args, **kwargs)

        return counted


async def _mk(
    db: AsyncSession, author: User, slug: str, status: str, published_at: datetime | None
) -> Post:
    post = Post(
        title={"zh": slug, "en": slug},
        slug=slug,
        content={"zh": "内容", "en": "content"},
        author_id=author.id,
        status=status,
        published_at=published_at,
    )
    db.add(post)
    await db.commit()
    return post


@pytest.mark.asyncio
async def test_archive_stats_groups_by_year(db_session: AsyncSession, test_user: User):
    """跨年样本：2024×2、2026×1 已发布 + 2025×1 草稿；草稿不得计入任何年份"""
    await _mk(db_session, test_user, "arch-2024-a", "published", datetime(2024, 3, 1))
    await _mk(db_session, test_user, "arch-2024-b", "published", datetime(2024, 11, 9))
    await _mk(db_session, test_user, "arch-2026-a", "published", datetime(2026, 1, 2))
    await _mk(db_session, test_user, "arch-2025-draft", "draft", datetime(2025, 6, 6))

    stats = await PostRepository(db_session).get_archive_stats()

    assert stats["year_stats"] == {2024: 2, 2026: 1}, stats
    assert stats["years"] == [2026, 2024], "年份必须降序（供归档时间线倒排）"
    assert stats["total_years"] == 2
    assert stats["total_posts"] == 3, "总数与分年统计必须同口径（只算 published）"
    assert sum(stats["year_stats"].values()) == stats["total_posts"]


@pytest.mark.asyncio
async def test_archive_stats_query_count_is_constant(db_session: AsyncSession, test_user: User):
    """3 个年份只允许 2 条 SELECT（总数 + 分组），而不是 1 + 1 + N 条"""
    for i, dt in enumerate([datetime(2023, 5, 1), datetime(2024, 5, 1), datetime(2025, 5, 1)]):
        await _mk(db_session, test_user, f"qc-{i}", "published", dt)

    spy = _CountingSession(db_session)
    stats = await PostRepository(spy).get_archive_stats()

    assert len(stats["years"]) == 3
    assert spy.executes <= 2, f"归档统计应恒为 2 条查询，实际={spy.executes}（逐年 COUNT 回潮）"


@pytest.mark.asyncio
async def test_archive_stats_falls_back_to_created_at(db_session: AsyncSession, test_post: Post):
    """published_at 为空的文章必须按 created_at 归年，不能整体漏计"""
    stats = await PostRepository(db_session).get_archive_stats()

    assert stats["total_posts"] >= 1
    assert sum(stats["year_stats"].values()) == stats["total_posts"], (
        f"有文章未落进任何年份桶：{stats}"
    )


@pytest.mark.asyncio
async def test_archive_data_projects_columns_only(
    db_session: AsyncSession, test_post: Post, test_category: Category
):
    """归档列表必须只投影展示列：把 JSON `content` 整列读出来等于每篇长文都全量取正文"""
    from sqlalchemy import event

    sql_seen: list[str] = []

    def _capture(conn, cursor, statement, parameters, context, executemany):
        sql_seen.append(statement)

    # AsyncSession.get_bind 在不同 SQLAlchemy 版本下可能已返回同步 Engine
    engine = getattr(db_session.get_bind(), "sync_engine", db_session.get_bind())
    event.listen(engine, "before_cursor_execute", _capture)
    try:
        data = await PostRepository(db_session).get_archive_data("zh")
    finally:
        event.remove(engine, "before_cursor_execute", _capture)

    archive_sql = [s for s in sql_seen if "posts" in s]
    assert archive_sql, f"应发出归档查询，实际 SQL={sql_seen}"
    assert "content" not in archive_sql[0].lower(), (
        f"归档查询不得 SELECT 正文列，实际={archive_sql[0]}"
    )

    assert data, "fixture 文章应出现在归档里"
    bucket = data[0]
    assert {"year", "month", "count", "posts"} <= set(bucket)
    row = bucket["posts"][0]
    assert row["slug"] == test_post.slug
    assert row["title"] == test_post.title["zh"]
    assert row["category"]["id"] == test_category.id
    assert row["category"]["name"] == test_category.name["zh"]
    assert "content" not in row, "响应里不应带出正文"
