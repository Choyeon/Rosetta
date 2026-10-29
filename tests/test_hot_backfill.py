"""热榜「窗口内不足一页」的补位口径。

线上实测症状（2026-10-29）：`GET /api/blog/posts/hot?limit=20` 只回 **1 条**，
`/posts/hot` 的「综合」默认页签只剩一张卡片，首页 hero 兜底轮播只有一屏。
根因不是没有文章（站点有 ~30 篇已发布），而是热榜先按 30 天窗口筛了一遍，
而站点的发帖节奏比窗口慢——窗口本身没错，错在把"窗口结果"当成"整页内容"。

四条判据（补位仍走同一个可见性谓词、同一个 HN 公式）：
1. 窗口内不足 limit 时用更早的文章补满，且老文章排在窗口内文章之后；
2. 窗口内已经够 limit 时，再高热度也不许把更早的文章挤进来（否则等价于取消时间窗）；
3. 补位候选池仍过 `publicly_listable_posts()`——老草稿 / 老私密稿 / 未来定时稿一律不进；
4. 缓存里存的是**补位后的**完整名单，命中缓存不会把补位丢掉。
"""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models.blog import Category, Post
from backend.models.user import User
from backend.services.cache_service import CacheService
from backend.services.recommendation import RecommendationService
from backend.utils.compat import UTC

pytestmark = pytest.mark.asyncio


def _slug(prefix: str = "hotfill") -> str:
    return f"{prefix}-{uuid.uuid4().hex[:10]}"


async def _mk(
    db: AsyncSession,
    author_id: int,
    *,
    status: str = "published",
    visibility: str = "public",
    category_id: int | None = None,
    views: int = 0,
    published_at: datetime | None = None,
) -> Post:
    name = _slug()
    post = Post(
        title={"zh": name, "en": name},
        slug=name,
        content={"zh": "热榜补位回归正文。", "en": "hot backfill body"},
        excerpt={"zh": "摘要", "en": "excerpt"},
        author_id=author_id,
        category_id=category_id,
        status=status,
        visibility=visibility,
        views=views,
        published_at=published_at,
        allow_comments=True,
    )
    db.add(post)
    await db.commit()
    await db.refresh(post)
    return post


def _days_ago(days: float) -> datetime:
    return datetime.now(UTC) - timedelta(days=days)


async def test_window_shortfall_is_filled_with_older_posts(
    db_session: AsyncSession,
    test_user: User,
) -> None:
    """只有 1 篇落在 30 天窗口里时，limit=4 必须回满 4 条，且新文章排第一。"""
    svc = RecommendationService(db_session, CacheService())
    fresh = await _mk(db_session, test_user.id, views=5, published_at=_days_ago(1))
    older = [
        await _mk(db_session, test_user.id, views=v, published_at=_days_ago(120 + i))
        for i, v in enumerate((10, 300, 7))
    ]

    ids = [p.id for p in await svc.get_hot_posts(limit=4, days=30)]

    assert len(ids) == 4, f"窗口内 1 篇 + 窗口外 3 篇应补满一页，实际 {len(ids)} 条"
    assert ids[0] == fresh.id, "窗口内的文章必须排在补位文章之前"
    assert set(older_ids := {p.id for p in older}) <= set(ids), f"补位丢失：{older_ids - set(ids)}"
    assert ids[1] == older[1].id, "补位内部同样按 HN 分数排序（浏览量 300 的那篇在第二）"


async def test_full_window_never_pulls_in_older_posts(
    db_session: AsyncSession,
    test_user: User,
) -> None:
    """窗口内已经够一页时，更早的高热度文章不得挤进来——否则时间窗等于不存在。"""
    svc = RecommendationService(db_session, CacheService())
    fresh = [
        await _mk(db_session, test_user.id, views=v, published_at=_days_ago(1 + i))
        for i, v in enumerate((3, 2, 1))
    ]
    ancient_hit = await _mk(db_session, test_user.id, views=10_000_000, published_at=_days_ago(400))

    ids = [p.id for p in await svc.get_hot_posts(limit=3, days=30)]

    assert ids == [p.id for p in fresh], "窗口内 3 篇已够 limit，顺序应完全由窗口内分数决定"
    assert ancient_hit.id not in ids


async def test_backfill_candidates_still_go_through_the_public_predicate(
    db_session: AsyncSession,
    test_user: User,
    test_category: Category,
) -> None:
    """补位拉的是"更早的文章"，但"更早"不等于"可见"：草稿/私密/定时未到一律不得补进来。"""
    svc = RecommendationService(db_session, CacheService())
    fresh = await _mk(db_session, test_user.id, views=1, published_at=_days_ago(1))
    visible_old = await _mk(db_session, test_user.id, views=2, published_at=_days_ago(200))
    draft_old = await _mk(
        db_session, test_user.id, status="draft", views=900_000, published_at=_days_ago(210)
    )
    private_old = await _mk(
        db_session, test_user.id, visibility="private", views=900_000, published_at=_days_ago(220)
    )
    # status 已是 published + published_at 在未来 = 定时未到；它在窗口比较里"满足 (> cutoff)"，
    # 只有 publicly_listable_posts 的第三条判据能挡住它。
    future = await _mk(
        db_session,
        test_user.id,
        views=900_000,
        published_at=datetime.now(UTC) + timedelta(days=5),
        category_id=test_category.id,
    )

    ids = [p.id for p in await svc.get_hot_posts(limit=5, days=30)]

    assert ids == [fresh.id, visible_old.id], (
        f"只应剩下两篇可见文章，实际 {ids}；不可见的 {draft_old.id}/{private_old.id}/{future.id}"
    )


async def test_cache_keeps_the_backfilled_ids(
    db_session: AsyncSession,
    test_user: User,
) -> None:
    """缓存名单必须是补位后的结果：否则第二次请求（命中缓存）会退回"只有 1 条"。"""
    cache = CacheService()
    svc = RecommendationService(db_session, cache)
    await _mk(db_session, test_user.id, views=1, published_at=_days_ago(1))
    for i in range(3):
        await _mk(db_session, test_user.id, views=2 + i, published_at=_days_ago(90 + i))

    first = [p.id for p in await svc.get_hot_posts(limit=4, days=10)]
    assert len(first) == 4

    key = "hotv2:4:10"
    assert await cache.get(key) == first, "名单没写进缓存 ⇒ 第二次走冷路径，这条测不到东西"

    second = [p.id for p in await svc.get_hot_posts(limit=4, days=10)]
    assert second == first


async def test_hero_fallback_carousel_gets_a_full_rail(
    client: AsyncClient,
    db_session: AsyncSession,
    test_user: User,
) -> None:
    """首页兜底轮播要 5 屏：DB 无生效轮播时，1 篇窗口内 + 4 篇窗口外也应凑满。"""
    await _mk(db_session, test_user.id, views=1, published_at=_days_ago(2))
    for i in range(4):
        await _mk(db_session, test_user.id, views=2 + i, published_at=_days_ago(80 + 10 * i))

    resp = await client.get("/api/hero/slides", params={"lang": "zh"})
    assert resp.status_code == 200
    rows = resp.json()
    assert len(rows) == 5, f"兜底轮播只有 {len(rows)} 屏"
    assert all(row["id"] < 0 for row in rows), "兜底项必须用负 ID"
