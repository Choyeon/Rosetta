"""阅读分钟数的单源契约（批次 #136）。

同一篇文章的「预计阅读 N 分钟」以前有三套算法：持久化列走
``utils/reading_time.calculate_reading_time``（汉字 300/分钟 + 英文词 150/分钟），
``PostLocalizedResponse._calculate_reading_time`` 自己写 ``len(content) // 500``
（把 Markdown 标记与半个词都当字数），详情页再按 380 字/分钟算第三遍。
表现是列表卡片 6 分钟、正文页 4 分钟，读者以为点开了另一篇。

现在两处出口都委托给持久化列那一个函数。这里钉四件事：
1. 出口函数与持久化算法对同一份正文给同一个数（含空正文的 1 分钟兜底）；
2. 旧的第二套公式不以任何形态留在后端（就地重算＝第四套算法）；
3. 列表/详情读的是列，不是正文 —— 列表口 ``defer(Post.content)``，
   正文根本不在载荷里，任何「读出来再算一遍」连输入都拿不到；
4. 不走 ``PostListItemLocalized`` 的裸 dict 投影（周期榜单）同样带出这一列，
   且文档模型给默认值 —— 批次 #137，同族缺陷的表现是「切个页签分钟数就没了」。
"""

import re
from datetime import datetime, timezone
from pathlib import Path

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.cache import cache
from backend.models.blog import Category, Post
from backend.models.user import User
from backend.schemas import PostLocalizedResponse
from backend.utils.reading_time import (
    calculate_reading_time,
    compute_reading_time_from_content,
)

BACKEND = Path(__file__).resolve().parents[1] / "backend"

SAMPLES = [
    "",
    "   ",
    "一两句中文",
    "汉字" * 300,
    "汉字" * 601,
    "word " * 150,
    "混合 content 与 english words 和中文汉字",
    "# 标题\n\n**加粗** 与 [链接](https://example.com) 的 Markdown 标记",
]


def test_outlet_matches_persisted_formula():
    """出口读数必须与写入侧持久化算法一致，否则卡片与详情页又会分叉。"""
    for text in SAMPLES:
        content = {"zh": text, "en": text, "ja": text, "zh_Hant": text}
        expected = compute_reading_time_from_content(content)
        assert PostLocalizedResponse._calculate_reading_time(text) == expected, text[:20]


def test_empty_content_is_one_minute_not_zero():
    """空正文给 1 分钟：卡片和详情页都不该显示「0 分钟阅读」。"""
    assert PostLocalizedResponse._calculate_reading_time("") == 1
    assert calculate_reading_time("") == 1
    assert compute_reading_time_from_content(None) == 1


def test_second_formula_never_comes_back():
    """``len(...) // 500`` 是漂移出来的第二套公式；就地重算一律视为回归。"""
    offenders = [
        str(path.relative_to(BACKEND))
        for path in sorted(BACKEND.rglob("*.py"))
        if re.search(r"len\([^()]*\)\s*//\s*500", path.read_text(encoding="utf-8"))
    ]
    assert offenders == []


def test_list_and_detail_outlets_read_the_column():
    """列表/详情出口取持久化列。"""
    blog = (BACKEND / "api" / "blog.py").read_text(encoding="utf-8")
    assert "reading_time=post.reading_time or 1" in blog
    assert "_reading_time = post.reading_time" in blog
    assert "reading_time=_reading_time or 1" in blog
    # 列表口 defer 正文：就地重算拿不到输入，这是「只能读列」的结构性理由
    assert re.search(r"defer\(\s*Post\.content", blog)


@pytest.mark.asyncio
async def test_ranking_surface_carries_the_column(
    client: AsyncClient,
    db_session: AsyncSession,
    test_user: User,
    test_category: Category,
):
    """榜单口（``GET /api/ranking/posts``）自己手搭 dict，不经过 PostListItemLocalized。

    批次 #136 只收了走模型的那一族，热榜页的日/周/月/总四个页签吃这条口，于是表现是
    「综合榜卡片有分钟数，切到周期榜整排消失」——与 #121 的媒体徽标同一族构造点漏写。
    这里断言的是**列的值**而不是 1：落一个和正文长度对不上的数，才证明它读的是列。
    """
    content = {"zh": "正文内容", "en": "body text"}
    post = Post(
        title={"zh": "榜单分钟数", "en": "Ranking Minutes"},
        slug="reading-ranking",
        content=content,
        excerpt={"zh": "摘要", "en": "excerpt"},
        author_id=test_user.id,
        category_id=test_category.id,
        status="published",
        visibility="public",
        views=50,
        allow_comments=True,
        # 与正文真实长度故意不一致：读列会得到 7，就地重算会得到 1
        reading_time=7,
    )
    db_session.add(post)
    await db_session.commit()

    await cache.clear()
    for period in ("all", "week"):
        response = await client.get("/api/ranking/posts", params={"period": period, "limit": 50})
        assert response.status_code == 200, response.text
        body = response.json()
        items = body["items"] if isinstance(body, dict) else body
        row = next((i for i in items if i.get("slug") == "reading-ranking"), None)
        assert row is not None, f"{period} 榜里没有这条：{[i.get('slug') for i in items]}"
        assert row["reading_time"] == 7, f"{period} 榜没带出持久化列：{row['reading_time']}"


def test_ranking_doc_model_declares_the_key():
    """文档模型必须给默认值：榜单载荷进 60s 响应缓存，旧载荷没这个键时不能整口 500。"""
    from backend.api.ranking import HotPostItemDoc

    field = HotPostItemDoc.model_fields["reading_time"]
    assert field.default == 1
    assert field.is_required() is False


# 批次 #138：其余"自己拼 dict / 列级投影"的读面
# ---------------------------------------------------------------------------

PUBLISHED_AT = datetime(2001, 2, 3, 4, 5, tzinfo=timezone.utc)
YEAR, MONTH = 2001, 2
# 故意与正文真实长度不一致：读列得到 7，就地重算得到 1
STORED_MINUTES = 7


async def _dated_post(
    db_session: AsyncSession,
    test_user: User,
    *,
    slug: str,
    series_id: int | None = None,
) -> Post:
    post = Post(
        title={"zh": "归档里的分钟数", "en": "Archived Minutes"},
        slug=slug,
        content={"zh": "正文内容", "en": "body text"},
        excerpt={"zh": "摘要", "en": "excerpt"},
        author_id=test_user.id,
        status="published",
        visibility="public",
        published_at=PUBLISHED_AT,
        views=7,
        allow_comments=True,
        series_id=series_id,
        reading_time=STORED_MINUTES,
    )
    db_session.add(post)
    await db_session.commit()
    await db_session.refresh(post)
    return post


def _groups(payload: dict) -> list[dict]:
    data = payload.get("data") if isinstance(payload, dict) and "data" in payload else payload
    return data if isinstance(data, list) else []


def _find_in_groups(payload: dict, slug: str) -> dict:
    for group in _groups(payload):
        found = [p for p in (group.get("posts") or []) if p.get("slug") == slug]
        if found:
            return found[0]
    raise AssertionError(f"归档分组里没有 {slug}")


@pytest.mark.asyncio
async def test_archive_three_surfaces_carry_the_column(
    client: AsyncClient,
    db_session: AsyncSession,
    test_user: User,
):
    """归档首页 / 年页 / 月页三面各自一条构造路径，缺哪面就那一面整列没有分钟数。

    归档首页走 ``PostRepository.get_archive_data`` 的**列级投影**（连 Post 实例都不建，
    漏了 select 里的列就拿不到值）；年页/月页各自手搭 dict。三条路径同族缺陷同形。
    """
    await _dated_post(db_session, test_user, slug="minutes-archive")
    await cache.clear()

    response = await client.get("/api/blog/archive")
    assert response.status_code == 200, response.text
    item = _find_in_groups(response.json(), "minutes-archive")
    assert item.get("reading_time") == STORED_MINUTES, f"归档首页：{item.get('reading_time')}"

    for path in (f"/api/blog/archive/{YEAR}", f"/api/blog/archive/{YEAR}/{MONTH}"):
        await cache.clear()
        response = await client.get(path)
        assert response.status_code == 200, response.text
        body = response.json()
        if "posts" in body:
            item = next(i for i in body["posts"] if i.get("slug") == "minutes-archive")
        else:
            item = _find_in_groups(body, "minutes-archive")
        assert item.get("reading_time") == STORED_MINUTES, f"{path}：{item.get('reading_time')}"


@pytest.mark.asyncio
async def test_series_chapter_list_carries_the_column(
    client: AsyncClient,
    db_session: AsyncSession,
    test_user: User,
):
    """系列目录走列级 select（``Post.reading_time`` 必须点名取），漏列即整目录没有分钟数。"""
    from backend.models.post_series import PostSeries

    series = PostSeries(
        title={"zh": "分钟数系列", "en": "Minutes Series"},
        slug="minutes-series",
        is_active=True,
    )
    db_session.add(series)
    await db_session.commit()
    await db_session.refresh(series)

    await _dated_post(db_session, test_user, slug="minutes-series-row", series_id=series.id)
    await cache.clear()

    response = await client.get("/api/series/minutes-series")
    assert response.status_code == 200, response.text
    body = response.json()
    data = body.get("data") if isinstance(body, dict) and "data" in body else body
    row = next((p for p in data["posts"] if p.get("slug") == "minutes-series-row"), None)
    assert row is not None, f"目录里没有这一章：{[p.get('slug') for p in data['posts']]}"
    assert row.get("reading_time") == STORED_MINUTES, f"系列目录：{row.get('reading_time')}"


def test_lean_projection_doc_models_default_the_key():
    """归档与系列的文档模型同样要给默认值——两份响应都进缓存。"""
    from backend.api.post_series import SeriesPostItemDoc
    from backend.schemas.blog_reads import ArchivePostItem

    for model in (ArchivePostItem, SeriesPostItemDoc):
        field = model.model_fields["reading_time"]
        assert field.default == 1, model.__name__
        assert field.is_required() is False, model.__name__
