"""「到点没到」的时钟口径回归（批次 #39）。

判一篇文章"发布时刻到了没有"，两侧必须是**同一个时钟**。这一轮修掉两处各说各话：

1. `services/post_access.py::publicly_listable_posts()` 原先拿 SQL 的 `now()` 当"现在"。
   SQLite 的 `CURRENT_TIMESTAMP` 只到**秒**（`'2026-10-28 21:42:09'`），而 `published_at`
   落库是带微秒与偏移的 TEXT（`'2026-10-28 21:42:09.961356+00:00'`）——同一秒内发布的文章
   按字符串比就大于这个"现在"。PG 侧 `now()` 是**事务开始**时刻，同一事务里刚写入的行同样
   判成"未到"。症状不是报错，而是"刚点完发布，RSS/列表/热榜里没有这篇"，且这一份少一篇的
   快照会按 `post_list` 的 300s 缓存下去；测试里它表现为同一文件内忽红忽绿的假失败。
2. `api/blog.py::get_post_adjacent` 的"已到达发布时间"用的是**本机时区**的朴素
   `datetime.now()`。生产机是 UTC+8，这个值比库里所有 UTC 时刻都晚 8 小时，闸门等于不存在：
   定时未到两小时内的稿子会出现在上一篇文章的"下一篇"里，点进去是 404（详情端点判得到）。

守卫的分工：`TestJustPublishedIsListable` 判修复本身（SQL 谓词 + 真实 RSS/列表口），
`TestFutureStillExcluded` 是它的反向——挡住"为了不再抖动把闸门整个删掉"这类变异；
`TestAdjacentRespectsSchedule` 判第 2 条；`TestClockSourceIsSingleSourced` 是源码级守卫，
因为"本机时区"这一条在 UTC 主机上行为守卫与修复前同形（测试跑在什么时区不该决定红绿）。
"""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta
from pathlib import Path

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.cache import invalidate_cache
from backend.models.blog import Post
from backend.services.post_access import publicly_listable_posts
from backend.utils.compat import UTC

BACKEND_DIR = Path(__file__).resolve().parent.parent / "backend"


def _slug(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex[:10]}"


async def _mk_published(
    db: AsyncSession, author_id: int, *, published_at: datetime | None, prefix: str
) -> Post:
    name = _slug(prefix)
    post = Post(
        title={"zh": name, "en": name},
        slug=name,
        content={"zh": "时钟口径回归正文。", "en": "clock boundary body"},
        excerpt={"zh": "摘要", "en": "excerpt"},
        author_id=author_id,
        status="published",
        visibility="public",
        published_at=published_at,
        allow_comments=True,
    )
    db.add(post)
    await db.commit()
    await db.refresh(post)
    return post


class TestJustPublishedIsListable:
    @pytest.mark.asyncio
    async def test_row_published_moments_ago_passes_the_predicate(
        self, db_session: AsyncSession, test_user
    ) -> None:
        """刚过几毫秒的文章必须"已到点"——SQL 侧的秒级 `now()` 会把它判成未来。

        循环而不是单次：只有"落在同一秒内"才暴露旧写法，逐轮重新取时刻把这种命中
        变成稳定发生；修复后的判定与落在哪一秒无关，所以循环只会让它更绿不会更红。
        """
        for _ in range(6):
            just = await _mk_published(
                db_session,
                test_user.id,
                published_at=datetime.now(UTC) - timedelta(milliseconds=200),
                prefix="clkjust",
            )
            hits = (
                (
                    await db_session.execute(
                        select(Post.id).where(publicly_listable_posts(), Post.slug == just.slug)
                    )
                )
                .scalars()
                .all()
            )
            assert list(hits) == [just.id], "发布时刻刚过即被判成未到（两侧不是同一个时钟）"

    @pytest.mark.asyncio
    async def test_api_publish_is_immediately_in_rss_and_list(
        self, client: AsyncClient, admin_headers
    ) -> None:
        """端到端：走后台发布口写完，立刻打访客面，RSS 与列表都得有这篇。

        这两个口都会把结果按 300s 缓存，"少一篇"的快照一旦被暖上就是几分钟的可见错误。
        """
        for _ in range(3):
            slug = _slug("clke2e")
            created = await client.post(
                "/api/blog/posts",
                json={
                    "title": {"zh": "时钟口径端到端", "en": "clock boundary e2e"},
                    "content": {"zh": "刚发布就要出现在访客面。", "en": "publish then read"},
                    "slug": slug,
                    "status": "published",
                },
                headers=admin_headers,
            )
            assert created.status_code == 201, created.text
            # 缓存键只由语言/分页构成，不带"本用例刚写了什么"，先清一次再断言
            await invalidate_cache("posts")

            rss = await client.get("/api/blog/rss")
            assert rss.status_code == 200, rss.text
            assert slug in rss.text, "刚发布的文章不在 RSS 里"

            listing = await client.get("/api/blog/posts", params={"page_size": 200, "lang": "zh"})
            assert listing.status_code == 200, listing.text
            body = listing.json()
            items = ((body.get("data") or {}) if "success" in body else body).get("items") or []
            assert slug in {it.get("slug") for it in items}, "刚发布的文章不在主列表里"

    @pytest.mark.asyncio
    async def test_null_published_at_is_still_listable(
        self, db_session: AsyncSession, test_user
    ) -> None:
        """`published_at IS NULL` 的 published 行不能被收紧成"一律不到点"（历史行没有该列值）。"""
        legacy = await _mk_published(db_session, test_user.id, published_at=None, prefix="clknull")
        hits = (
            (
                await db_session.execute(
                    select(Post.id).where(publicly_listable_posts(), Post.slug == legacy.slug)
                )
            )
            .scalars()
            .all()
        )
        assert list(hits) == [legacy.id]


class TestFutureStillExcluded:
    """反向守卫：把闸门"修"成永不过期（删掉时间条件）必须让本类变红。"""

    @pytest.mark.asyncio
    async def test_predicate_excludes_future_published_at(
        self, db_session: AsyncSession, test_user
    ) -> None:
        future = await _mk_published(
            db_session,
            test_user.id,
            published_at=datetime.now(UTC) + timedelta(days=2),
            prefix="clkfuture",
        )
        hits = (
            (
                await db_session.execute(
                    select(Post.id).where(publicly_listable_posts(), Post.slug == future.slug)
                )
            )
            .scalars()
            .all()
        )
        assert list(hits) == [], "定时未到的稿子被集合口发出去了"

    @pytest.mark.asyncio
    async def test_rss_excludes_future_published_at(
        self, client: AsyncClient, db_session: AsyncSession, test_user
    ) -> None:
        future = await _mk_published(
            db_session,
            test_user.id,
            published_at=datetime.now(UTC) + timedelta(days=2),
            prefix="clkfutrss",
        )
        due = await _mk_published(
            db_session,
            test_user.id,
            published_at=datetime.now(UTC) - timedelta(days=1),
            prefix="clkdrss",
        )
        await invalidate_cache("posts")
        rss = await client.get("/api/blog/rss")
        assert rss.status_code == 200, rss.text
        assert due.slug in rss.text, "已到点的文章都不在 RSS 里，断言退化成整口为空"
        assert future.slug not in rss.text


class TestAdjacentRespectsSchedule:
    @pytest.mark.asyncio
    async def test_next_link_skips_not_yet_due_post(
        self, client: AsyncClient, db_session: AsyncSession, test_user
    ) -> None:
        """上下篇口的"已到点"判据不得用本机时区的朴素时间。

        在 UTC+8 的生产/开发机上，`datetime.now()` 比 UTC 晚 8 小时，+2h 的定时稿会被判成
        "已过点"从而挂进"下一篇"，点进去详情端点判 404。UTC 主机上这条行为守卫修复前后同形，
        所以时钟来源另有 `TestClockSourceIsSingleSourced` 的源码级守卫兜底。
        """
        due = await _mk_published(
            db_session,
            test_user.id,
            published_at=datetime.now(UTC) - timedelta(days=1),
            prefix="clkadj",
        )
        future = await _mk_published(
            db_session,
            test_user.id,
            published_at=datetime.now(UTC) + timedelta(hours=2),
            prefix="clkadjf",
        )
        resp = await client.get(f"/api/blog/posts/{due.slug}/adjacent")
        assert resp.status_code == 200, resp.text
        data = resp.json().get("data") or {}
        assert (data.get("next") or {}).get("slug") != future.slug, "下一篇指向定时未到的文章"


class TestClockSourceIsSingleSourced:
    def test_collection_predicate_does_not_use_sql_now(self) -> None:
        text = (BACKEND_DIR / "services" / "post_access.py").read_text(encoding="utf-8")
        assert "Post.published_at <= datetime.now" in text, (
            "集合口的到点判据又回到 SQL 侧 now()：SQLite 截到秒、PG 取事务开始时刻"
        )
        assert "Post.published_at <= func.now()" not in text

    def test_adjacent_gate_uses_utc_not_local_clock(self) -> None:
        text = (BACKEND_DIR / "api" / "blog.py").read_text(encoding="utf-8")
        assert "now = datetime.now(UTC)" in text, (
            "上下篇的到点判据必须是 UTC 时刻：本机时区（如 UTC+8）会让闸门永远打开"
        )
        assert "now = datetime.now()\n" not in text
