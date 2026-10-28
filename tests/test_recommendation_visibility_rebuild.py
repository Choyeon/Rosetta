"""推荐 / 热榜 / 相似这一族的"缓存里只存 id"回源口径回归。

这一族把排序结果缓存成 **id 名单**（ORM 实例不能进 Redis，见
`RecommendationService._rebuild_posts_by_ids` 的说明），每次命中再用名单回源查 ORM。
于是名单的"新鲜度"和文章的"实时可见性"是两件事：把一篇文章改成私密、转成草稿，
缓存清不干净是设计内的常态——`invalidate_pattern` 只清当前进程的 L1 + Redis，
生产跑 `--workers 2`，另一个 worker 的 L1 收不到任何广播。

生产实测症状（批次 #30 门禁里的探针）：同一行从 private 翻成 public 后，用同一个缓存键位
打 `/blog/posts/hot` 拿到的还是私密相位的旧名单，换成一个从未用过的 `days` 键位立刻在场。
所以这一族的判据必须落在**回源那一次 SELECT** 上，而不是只落在算名单的冷路径上。

覆盖的三条判据（单源 `services/post_access.py::publicly_listable_posts`）：
status=published、排除私密档、定时未到不算可见。第三条同时修掉"推荐位点进去是 404"
——详情端点早把未到点的定时稿判成 404，只有派生集合口漏判时才出现"有卡片、无正文"。
"""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta

import pytest
from httpx import AsyncClient
from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models.blog import Category, Post
from backend.models.user import User
from backend.services.cache_service import CacheService
from backend.services.recommendation import RecommendationService
from backend.utils.compat import UTC

pytestmark = pytest.mark.asyncio

LIST = "/api/blog/posts"


def _slug(prefix: str = "recgate") -> str:
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
        content={"zh": "推荐回源回归正文。", "en": "recommendation gate body"},
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


async def _flip(db: AsyncSession, post_id: int, **values) -> None:
    """只改库、不碰任何写口——写口自带清缓存，会把"陈旧名单"这一幕清没了。"""
    await db.execute(update(Post).where(Post.id == post_id).values(**values))
    await db.commit()


async def test_hot_rebuild_drops_row_turned_private_behind_the_cache(
    db_session: AsyncSession,
    test_user: User,
    test_category: Category,
) -> None:
    """热榜：暖好的 id 名单里仍然带着它，但响应必须已经没有它。"""
    cache = CacheService()
    svc = RecommendationService(db_session, cache)
    target = await _mk(db_session, test_user.id, category_id=test_category.id, views=999_999)
    control = await _mk(db_session, test_user.id, category_id=test_category.id, views=1)

    warm_ids = [p.id for p in await svc.get_hot_posts(limit=10, days=30)]
    assert target.id in warm_ids, "冷路径就该有它，否则下面的断言是在赌空集合"

    key = "hotv2:10:30"
    assert await cache.get(key) == warm_ids, "名单没写进缓存 ⇒ 第二次走的是冷路径，等于没测到回源"

    await _flip(db_session, target.id, visibility="private")
    assert target.id in (await cache.get(key)), "前提：缓存仍是私密相位的旧名单"

    after = [p.id for p in await svc.get_hot_posts(limit=10, days=30)]
    assert target.id not in after
    assert control.id in after, "整个口不能因为收紧判据变成空的"
    assert target.id in (await cache.get(key)), (
        "命中路径不回填名单，所以旧 id 会活到 TTL 结束——收敛点只在回源那一次 SELECT，"
        "这条断言把口径钉住：修的时候不要改成'顺手把缓存里的它删掉'"
    )


@pytest.mark.parametrize(
    "values",
    [{"status": "draft"}, {"visibility": "private"}],
    ids=["to-draft", "to-private"],
)
async def test_recommendation_rebuild_applies_both_visibility_axes(
    db_session: AsyncSession,
    test_user: User,
    values: dict[str, str],
) -> None:
    """首页推荐缓存的是整页 dict（items 存 id），翻页命中同一条路径。"""
    cache = CacheService()
    svc = RecommendationService(db_session, cache)
    target = await _mk(db_session, test_user.id, views=500)
    control = await _mk(db_session, test_user.id, views=400)

    first = await svc.get_recommended_posts(page=1, page_size=10)
    # 缓存里存的是 id 名单，返回值里的 items 是回源后的 ORM 实例（line 636 vs 644）
    warm = [p.id for p in first["items"]]
    assert target.id in warm
    key = cache.build_key_with_hash("recsv2", user="anon", p=1, ps=10, excl="")
    cached_list = await cache.get(key)
    assert cached_list is not None, "名单没写进缓存 ⇒ 第二次走的是冷路径"
    assert target.id in cached_list["items"], "缓存名单里就该留着它，否则回源过滤无从发生"

    await _flip(db_session, target.id, **values)

    second = await svc.get_recommended_posts(page=1, page_size=10)
    assert target.id not in [p.id for p in second["items"]]
    assert control.id in [p.id for p in second["items"]]


async def test_similar_rebuild_drops_row_turned_private_behind_the_cache(
    db_session: AsyncSession,
    test_user: User,
    test_category: Category,
) -> None:
    """相似文章：锚点不变、候选被收起，命中缓存时同样不得再给出卡片。"""
    cache = CacheService()
    svc = RecommendationService(db_session, cache)
    anchor = await _mk(db_session, test_user.id, category_id=test_category.id)
    target = await _mk(db_session, test_user.id, category_id=test_category.id, views=888)

    warm = [p.id for p in await svc.get_similar_posts(anchor.id, limit=6)]
    assert target.id in warm, "候选池就该含它，否则断言在赌空集合"

    key = f"simv2:{anchor.id}:6"
    assert await cache.get(key) == warm, "名单没写进缓存 ⇒ 第二次走的是冷路径"

    await _flip(db_session, target.id, visibility="private")
    after = [p.id for p in await svc.get_similar_posts(anchor.id, limit=6)]
    assert target.id not in after
    assert target.id in (await cache.get(key)), "名单里还留着它，正是回源过滤要挡的那一幕"


async def test_scheduled_future_post_stays_out_of_derived_surfaces(
    db_session: AsyncSession,
    test_user: User,
    test_category: Category,
) -> None:
    """定时未到（status 已是 published）不得进热榜/推荐/相似，也不得当相似的锚点。

    `status == "published"` 是定时发布落库时的写法，不是"已经公开"——只圈 status 的
    派生集合口会在到点前就把卡片发出去。
    """
    svc = RecommendationService(db_session, CacheService())
    future = await _mk(
        db_session,
        test_user.id,
        category_id=test_category.id,
        views=999_999,
        published_at=datetime.now(UTC) + timedelta(days=2),
    )
    due = await _mk(
        db_session,
        test_user.id,
        category_id=test_category.id,
        views=1,
        published_at=datetime.now(UTC) - timedelta(hours=1),
    )

    hot_ids = [p.id for p in await svc.get_hot_posts(limit=10, days=30)]
    assert future.id not in hot_ids and due.id in hot_ids

    rec_ids = [p.id for p in (await svc.get_recommended_posts(page=1, page_size=10))["items"]]
    assert future.id not in rec_ids and due.id in rec_ids

    assert [p.id for p in await svc.get_similar_posts(future.id, limit=6)] == []
    similar_ids = [p.id for p in await svc.get_similar_posts(due.id, limit=6)]
    assert future.id not in similar_ids


async def test_hot_endpoint_never_links_to_a_404_detail(
    client: AsyncClient,
    db_session: AsyncSession,
    test_user: User,
    test_category: Category,
) -> None:
    """用户可见症状：热榜/推荐给出的每一条，详情页都必须打得开。

    这是把上面两条判据"对外"钉住的断言——派生集合口与详情端点判据不一致时，表现不是
    报错而是"卡片点进去 404"，所以这里逐个回访真实状态码。
    """
    await _mk(
        db_session,
        test_user.id,
        category_id=test_category.id,
        views=999_999,
        published_at=datetime.now(UTC) + timedelta(days=3),
    )
    await _mk(
        db_session,
        test_user.id,
        category_id=test_category.id,
        views=2,
        published_at=datetime.now(UTC) - timedelta(hours=2),
    )

    for path in (f"{LIST}/hot?limit=50", f"{LIST}/recommended?page_size=50"):
        resp = await client.get(path)
        assert resp.status_code == 200, f"{path} → {resp.status_code}"
        body = resp.json()
        # 热榜是裸 list，推荐是 PaginatedResponse（两者都不带 success/data 信封）
        items = body["items"] if isinstance(body, dict) else body
        assert items, f"{path} 没有任何候选，回访 200 就成了空断言"
        for item in items:
            detail = await client.get(f"{LIST}/{item['slug']}")
            assert detail.status_code == 200, f"{path} 推荐了打不开的 {item['slug']}"
