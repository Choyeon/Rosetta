"""编辑器「同系列文章」快选的候选面守卫（批次 #50 的前端消费口）。

``POST /api/post_series/complete`` 是**无鉴权** POST，产出的是可以直接粘进正文的
``[标题](/posts/slug)`` 内链。它的入选口径因此必须是"前台已经承认这篇对外存在"，
而不是"这条 id 在库里"——否则编辑器会替作者把草稿、定时未到、私密的标题与 slug
做成出站内链（slug 本身就是可枚举的泄露面，正文里再挂一条等于替搜索引擎指路）。

三条判据的单一来源是 ``services/post_access.py::publicly_listable_posts()``
（status / 密码外的 visibility / 定时是否到点）。三段召回（系列 → 分类 → 标题）
每一段都得叠上它，漏一段即成缺口——这与评论读口泄漏草稿正文是同一族。

空白与超长关键词的形态单独钉住：前端调用方做了本地剪枝（`trim()` 后空串不发请求），
后端这一层仍要给出可预期的返回，两侧行为一致才不会出现"清空输入框却在面板里
留下上一次的结果"。
"""

from datetime import datetime, timedelta
from uuid import uuid4

import pytest

from backend.models.blog import Post
from backend.models.post_series import PostSeries
from backend.models.user import User
from backend.utils.compat import UTC


def _utc_now() -> datetime:
    return datetime.now(UTC)


async def _series(db_session, slug: str, title_zh: str) -> PostSeries:
    series = PostSeries(
        title={"zh": title_zh, "en": title_zh}, slug=slug, sort_order=0, is_active=True
    )
    db_session.add(series)
    await db_session.commit()
    await db_session.refresh(series)
    return series


async def _post(
    db_session,
    author: User,
    series_id: int | None,
    slug: str,
    *,
    status: str = "published",
    title: dict | None = None,
    published_at: datetime | None = None,
    **kwargs,
) -> Post:
    post = Post(
        title=title or {"zh": f"标题-{slug}", "en": f"Title-{slug}"},
        slug=slug,
        content="正文",
        excerpt={"zh": "摘要"},
        status=status,
        author_id=author.id,
        series_id=series_id,
        published_at=published_at or _utc_now() - timedelta(hours=1),
        **kwargs,
    )
    db_session.add(post)
    await db_session.commit()
    await db_session.refresh(post)
    return post


async def _complete(client, query: str):
    response = await client.post("/api/post_series/complete", json={"query": query})
    assert response.status_code == 200, response.text
    body = response.json()
    return response, body if isinstance(body, list) else (body.get("data") or [])


@pytest.mark.asyncio
async def test_draft_scheduled_and_private_posts_are_not_suggestions(client, db_session, test_user):
    """同一个系列里只有"匿名已可读"的那一篇能进候选。"""
    suffix = uuid4().hex[:8]
    series = await _series(db_session, f"guard-series-{suffix}", f"守卫系列{suffix}")
    slug_prefix = f"g50-{suffix}"
    visible = await _post(db_session, test_user, series.id, f"{slug_prefix}-pub")
    await _post(db_session, test_user, series.id, f"{slug_prefix}-draft", status="draft")
    await _post(
        db_session,
        test_user,
        series.id,
        f"{slug_prefix}-future",
        published_at=_utc_now() + timedelta(days=3),
    )
    await _post(db_session, test_user, series.id, f"{slug_prefix}-private", visibility="private")

    _, items = await _complete(client, series.slug)

    ids = [item["id"] for item in items]
    assert ids == [visible.id], f"候选里混进了未发布文章：{items}"


@pytest.mark.asyncio
async def test_series_whose_posts_are_all_drafts_returns_empty(client, db_session, test_user):
    """系列名命中但文章全是草稿 → 空数组，不得退到"标题匹配"档把草稿捞回来。

    三段召回是顺序 fallthrough：第一段没凑满 8 条就会继续查分类与标题。所以闸门
    必须逐段都在，只在第一段加过滤等于什么都没加。
    """
    suffix = uuid4().hex[:8]
    series = await _series(db_session, f"guard-empty-{suffix}", f"空系列{suffix}")
    await _post(
        db_session,
        test_user,
        series.id,
        f"g50e-{suffix}-a",
        status="draft",
        title={"zh": f"草稿标题{suffix}"},
    )
    await _post(
        db_session,
        test_user,
        series.id,
        f"g50e-{suffix}-b",
        status="published",
        visibility="private",
        title={"zh": f"私密标题{suffix}"},
    )

    _, by_series = await _complete(client, series.slug)
    assert by_series == []

    _, by_title = await _complete(client, suffix)
    assert by_title == [], "标题档绕过了可见性谓词，把草稿/私密重新放了出来"


@pytest.mark.asyncio
async def test_suggestion_title_is_a_plain_string(client, db_session, test_user):
    """前端把 title 当锚文本直接用，所以后端必须投影成单条字符串而不是四语 dict。"""
    suffix = uuid4().hex[:8]
    series = await _series(db_session, f"guard-shape-{suffix}", f"形态系列{suffix}")
    await _post(db_session, test_user, series.id, f"g50s-{suffix}-pub")

    _, items = await _complete(client, series.slug)

    assert len(items) == 1
    assert set(items[0]) == {"id", "title", "slug"}, items[0]
    assert isinstance(items[0]["title"], str), "title 变成 dict 会让编辑器插入 [object Object]"


@pytest.mark.asyncio
@pytest.mark.parametrize("query", ["   ", "\n\t "])
async def test_whitespace_query_is_a_plain_empty_list(client, query):
    """纯空白剪枝后为空 → 200 + []，不是 422 也不是"全库前 8 条"。"""
    response, items = await _complete(client, query)
    assert response.status_code == 200
    assert items == []


@pytest.mark.asyncio
async def test_over_long_query_is_rejected(client):
    """上限 100 字符由 schema 挡下；前端调用方截断，两侧口径要一致。"""
    response = await client.post("/api/post_series/complete", json={"query": "x" * 101})
    assert response.status_code == 422, response.text
