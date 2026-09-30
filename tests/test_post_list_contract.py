"""文章列表接口的排序 / 稳定分页 / sort 参数契约测试。

守的是三条线上可感知的行为：
1. 草稿（`published_at IS NULL`）不能沉到末页——管理员新建的草稿看不见，会以为保存失败；
2. 分页必须稳定——时间戳并列时同一篇文章不能同时出现在两页、也不能两页都不出现；
3. `sort` 必须进缓存键——否则"最热"视图会命中"最新"视图缓存下来的那一页。
"""

from datetime import datetime, timedelta

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

# 项目用 backend.utils.compat.UTC：运行时是 Python 3.10，datetime.UTC 要 3.11+ 才有
from backend.api.blog import LIST_SORT_LATEST, LIST_SORT_POPULAR, _normalize_list_sort
from backend.models.blog import Post
from backend.utils.compat import UTC

LIST = "/api/blog/posts"


async def _make_post(
    db_session: AsyncSession,
    author_id: int,
    *,
    slug: str,
    status: str = "published",
    views: int = 0,
    published_at: datetime | None = None,
    title_zh: str | None = None,
) -> Post:
    post = Post(
        title={"zh": title_zh or slug, "en": slug},
        slug=slug,
        content={"zh": "正文", "en": "content"},
        author_id=author_id,
        status=status,
        views=views,
        published_at=published_at,
        post_type="post",
    )
    db_session.add(post)
    await db_session.flush()
    return post


@pytest.mark.asyncio
async def test_draft_is_not_buried_on_last_page(
    client: AsyncClient, staff_headers: dict, db_session: AsyncSession, staff_user
) -> None:
    """草稿 published_at 为 NULL。

    SQLite 把 NULL 当最小值、PostgreSQL 当最大值，两种库对 `ORDER BY published_at DESC`
    给出相反的"最新"。只按 published_at 排，东家库上刚建的草稿会沉到最后一页。
    """
    base = datetime.now(UTC) - timedelta(days=1)
    for i in range(12):
        await _make_post(
            db_session,
            staff_user.id,
            slug=f"old-pub-{i}",
            status="published",
            published_at=base - timedelta(hours=i),
        )
    await _make_post(db_session, staff_user.id, slug="fresh-draft", status="draft")
    await db_session.commit()

    resp = await client.get(f"{LIST}?status=all&page_size=20", headers=staff_headers)
    assert resp.status_code == 200
    slugs = [item["slug"] for item in resp.json()["items"]]

    assert "fresh-draft" in slugs
    # 置顶位之外，刚建的草稿应当排在最前面，而不是像 NULL-last 那样落到末尾
    assert slugs.index("fresh-draft") < 3, f"草稿沉底了：{slugs}"


@pytest.mark.asyncio
async def test_pagination_is_stable_when_timestamps_tie(
    client: AsyncClient, staff_headers: dict, db_session: AsyncSession, staff_user
) -> None:
    """时间戳完全并列时，LIMIT/OFFSET 不保证稳定。

    没有唯一键做 tiebreaker 的话，"第 1 页 + 第 2 页"合起来会重复若干篇、漏掉若干篇，
    而 total 是对的——管理员只会觉得列表在跳。
    """
    same = datetime(2026, 1, 1, 12, 0, 0, tzinfo=UTC)
    for i in range(10):
        await _make_post(
            db_session, staff_user.id, slug=f"tied-{i}", status="published", published_at=same
        )
    await db_session.commit()

    seen: list[str] = []
    for page in (1, 2):
        resp = await client.get(
            f"{LIST}?status=all&page={page}&page_size=5", headers=staff_headers
        )
        assert resp.status_code == 200
        body = resp.json()
        assert len(body["items"]) == 5
        seen.extend(item["slug"] for item in body["items"])

    assert len(seen) == len(set(seen)), f"翻页出现重复项：{seen}"
    assert len(seen) == 10


@pytest.mark.asyncio
async def test_sort_popular_orders_by_views(
    client: AsyncClient, staff_headers: dict, db_session: AsyncSession, staff_user
) -> None:
    """sort=popular 按浏览量倒序；置顶位仍然优先。"""
    now = datetime.now(UTC)
    await _make_post(
        db_session, staff_user.id, slug="low-views", views=1, published_at=now
    )
    await _make_post(
        db_session,
        staff_user.id,
        slug="high-views",
        views=999,
        published_at=now - timedelta(days=30),
    )
    await db_session.commit()

    resp = await client.get(f"{LIST}?sort=popular&page_size=20", headers=staff_headers)
    assert resp.status_code == 200
    slugs = [item["slug"] for item in resp.json()["items"]]
    assert slugs.index("high-views") < slugs.index("low-views")


@pytest.mark.asyncio
async def test_unknown_sort_falls_back_to_latest(
    client: AsyncClient, staff_headers: dict, db_session: AsyncSession, staff_user
) -> None:
    """未知取值不报错：排序是展示偏好，拒绝它会让收藏夹里的旧链接直接 422。"""
    resp = await client.get(f"{LIST}?sort=bogus&page_size=5", headers=staff_headers)
    assert resp.status_code == 200

    assert _normalize_list_sort("BOGUS") == LIST_SORT_LATEST
    assert _normalize_list_sort(None) == LIST_SORT_LATEST
    assert _normalize_list_sort("  popular ") == LIST_SORT_POPULAR


@pytest.mark.asyncio
async def test_sort_is_part_of_cache_key(
    client: AsyncClient, staff_headers: dict, db_session: AsyncSession, staff_user
) -> None:
    """匿名访客的两种排序必须各占一条缓存键。

    少这一段时，先有人访问 `?sort=popular`，随后所有 `?sort=latest`（以及首页）在 TTL 内
    都会拿到按浏览量排的那一页。
    """
    from backend.api.blog import _get_post_list_cache_key

    latest_key = await _get_post_list_cache_key(
        "zh", 1, 12, None, None, None, None, None, "post", LIST_SORT_LATEST
    )
    popular_key = await _get_post_list_cache_key(
        "zh", 1, 12, None, None, None, None, None, "post", LIST_SORT_POPULAR
    )
    assert latest_key != popular_key


@pytest.mark.asyncio
async def test_list_item_exposes_updated_at(
    client: AsyncClient, staff_headers: dict, db_session: AsyncSession, staff_user
) -> None:
    """后台列表的「最后更新」列依赖它；草稿没有 published_at，只看发布时间会误判。"""
    await _make_post(db_session, staff_user.id, slug="with-updated", status="published")
    await db_session.commit()

    resp = await client.get(f"{LIST}?status=all&page_size=20", headers=staff_headers)
    assert resp.status_code == 200
    items = [i for i in resp.json()["items"] if i["slug"] == "with-updated"]
    assert items, "列表里没找到刚建的文章"
    assert items[0].get("updated_at"), "列表项缺少 updated_at"


@pytest.mark.asyncio
async def test_scheduled_at_naive_value_is_read_as_utc(
    client: AsyncClient, staff_headers: dict, db_session: AsyncSession, staff_user
) -> None:
    """朴素 scheduled_at 按 UTC 解释，而不是运行机器的本地时区。

    前端把 datetime-local 的本地墙钟换成带偏移的 ISO 后再提交，这里守的是
    "后端收到朴素值时不会把它当本地时间"——那会让东八区的排期整体偏 8 小时。
    """
    # 用一个远离当前时刻的未来时间，避免被"不晚于现在 → 降级为立即发布"分支吃掉
    target = datetime.now(UTC) + timedelta(days=3)
    naive = target.replace(tzinfo=None).replace(second=0, microsecond=0)

    resp = await client.post(
        "/api/blog/posts",
        headers=staff_headers,
        json={
            "title": {"zh": "定时文章"},
            "slug": "scheduled-by-naive",
            "content": {"zh": "正文"},
            "status": "scheduled",
            "scheduled_at": naive.isoformat(),
        },
    )
    assert resp.status_code == 201, resp.text

    row = (
        await db_session.execute(select(Post).where(Post.slug == "scheduled-by-naive"))
    ).scalars().one()
    assert row.status == "scheduled"
    stored = row.scheduled_at
    assert stored is not None
    if stored.tzinfo is not None:
        stored = stored.astimezone(UTC)
    # 钟点不能被搬动：给的是 UTC 10:00，库里就必须是 10:00
    assert stored.replace(tzinfo=None) == naive
