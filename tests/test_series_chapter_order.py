"""系列详情页的章节顺序契约（批次 #41）。

后台的「序号」输入（`components/admin/PostForm.vue`）与 `PUT /api/blog/posts/{id}` 早就写得到
`Post.series_order`，公开口 `GET /api/series/{slug}` 也按它排序，但**这条排序从来没有一条断言**：
把 `order_by(Post.series_order.asc(), Post.published_at.desc())` 改成只按 `published_at`、
或者把 `series_order` 排成倒序，全套测试仍然全绿——而系列页的全部意义就是"按顺序阅读"。
后台系列页更进一步把这件事写成"待后端接口上线后启用"，而接口其实一直在。

覆盖面（每条都对应一个真实的失效形态）：
1. 章节顺序跟 `series_order` 走，不跟插入顺序、也不跟发布时间走；
2. 同序号时按发布时间倒序补位（缺省序号全是 0，没有 tie-break 就等于章节顺序由 DB 说了算）；
3. 行投影只有详情页真正渲染的列——多带 `content` 会让一个几百篇的系列每次请求读进几 MB；
4. `post_count` 恒等于 `posts` 长度（不是 `COUNT(*)` 的另一个口径）；
5. 写口改序号 → 公开口立刻按新序返回（这条是"后台那个输入框真的接到前台"的闭环）；
6. 草稿/定时稿不占序位也不打乱其余章节（过滤走 `publicly_listable_posts`，不是排完序再筛）。
"""

from datetime import timedelta

import pytest
from httpx import AsyncClient
from sqlalchemy import select

from backend.models.blog import Post
from backend.models.post_series import PostSeries
from backend.utils.compat import utc_now_naive

SERIES = "/api/series"
BLOG = "/api/blog"

CHAPTER_KEYS = {"id", "title", "slug", "cover_image", "series_order", "views", "published_at"}


def _unwrap(body):
    """两种形态都接：全局信封 ``{success, data}`` 与裸 dict（这个口刻意是裸 dict）。"""
    if isinstance(body, dict) and "data" in body:
        return body["data"]
    return body


async def _mk_series(db, slug: str) -> PostSeries:
    series = PostSeries(title={"zh": f"系列{slug}", "en": slug}, slug=slug, is_active=True)
    db.add(series)
    await db.commit()
    await db.refresh(series)
    return series


async def _mk_chapter(db, series, author_id, slug, *, order, age_days, status="published") -> Post:
    post = Post(
        title={"zh": f"《{slug}》", "en": slug},
        slug=slug,
        content={"zh": "正文", "en": "body"},
        excerpt={"zh": "摘要", "en": "excerpt"},
        author_id=author_id,
        series_id=series.id,
        series_order=order,
        status=status,
        published_at=utc_now_naive() - timedelta(days=age_days),
    )
    db.add(post)
    await db.commit()
    await db.refresh(post)
    return post


async def _chapters(slug: str, client: AsyncClient):
    resp = await client.get(f"{SERIES}/{slug}")
    assert resp.status_code == 200, resp.text
    return _unwrap(resp.json())


class TestChapterOrderIsSeriesOrder:
    @pytest.mark.asyncio
    async def test_order_beats_insert_and_time_order(
        self, client: AsyncClient, db_session, test_post: Post
    ):
        """序号 3/1/2 按 3→1→2 插入，且发布顺序也故意相反：返回列表必须是 1、2、3 那三篇。"""
        series = await _mk_series(db_session, "order-beats-everything")
        await _mk_chapter(db_session, series, test_post.author_id, "ch-third", order=3, age_days=30)
        await _mk_chapter(db_session, series, test_post.author_id, "ch-first", order=1, age_days=10)
        await _mk_chapter(
            db_session, series, test_post.author_id, "ch-second", order=2, age_days=20
        )

        data = await _chapters(series.slug, client)
        assert [row["slug"] for row in data["posts"]] == ["ch-first", "ch-second", "ch-third"]
        assert [row["series_order"] for row in data["posts"]] == [1, 2, 3]

    @pytest.mark.asyncio
    async def test_equal_order_falls_back_to_newest_first(
        self, client: AsyncClient, db_session, test_post: Post
    ):
        """缺省序号全是 0 时排序仍有定义：tie-break 必须是发布时间倒序，不能交给 DB 的行序。"""
        series = await _mk_series(db_session, "same-order-tiebreak")
        await _mk_chapter(db_session, series, test_post.author_id, "old", order=0, age_days=90)
        await _mk_chapter(db_session, series, test_post.author_id, "mid", order=0, age_days=45)
        await _mk_chapter(db_session, series, test_post.author_id, "new", order=0, age_days=1)

        data = await _chapters(series.slug, client)
        assert [row["slug"] for row in data["posts"]] == ["new", "mid", "old"]

    @pytest.mark.asyncio
    async def test_unpublished_chapters_do_not_take_a_slot(
        self, client: AsyncClient, db_session, test_post: Post
    ):
        """序号 2 是草稿：它既不出现，也不把 1、3 的相对顺序搅乱（过滤在 ORDER BY 之前）。"""
        series = await _mk_series(db_session, "draft-in-the-middle")
        await _mk_chapter(db_session, series, test_post.author_id, "d-1", order=1, age_days=5)
        await _mk_chapter(db_session, series, test_post.author_id, "d-2", order=2, age_days=4)
        await _mk_chapter(
            db_session, series, test_post.author_id, "d-3", order=3, age_days=3, status="draft"
        )

        data = await _chapters(series.slug, client)
        assert [row["slug"] for row in data["posts"]] == ["d-1", "d-2"]
        assert data["post_count"] == len(data["posts"]) == 2


class TestRowShape:
    @pytest.mark.asyncio
    async def test_projection_is_only_what_the_page_renders(
        self, client: AsyncClient, db_session, test_post: Post
    ):
        """正文/摘要不得进投影：这个口一个系列要返回全部章节。"""
        series = await _mk_series(db_session, "lean-projection")
        await _mk_chapter(db_session, series, test_post.author_id, "lean-1", order=1, age_days=1)

        data = await _chapters(series.slug, client)
        row = data["posts"][0]
        assert set(row) == CHAPTER_KEYS, f"投影列集变了：{sorted(set(row) ^ CHAPTER_KEYS)}"
        assert "content" not in row and "excerpt" not in row

    @pytest.mark.asyncio
    async def test_detail_envelope_counts_and_identity(
        self, client: AsyncClient, db_session, test_post: Post
    ):
        series = await _mk_series(db_session, "envelope-check")
        await _mk_chapter(db_session, series, test_post.author_id, "env-1", order=1, age_days=1)

        data = await _chapters(series.slug, client)
        assert data["id"] == series.id
        assert data["slug"] == "envelope-check"
        assert data["post_count"] == len(data["posts"])


class TestWriteSideDrivesPublicOrder:
    """后台那个「序号」输入框的消费点在这里：改完前台章节顺序必须跟着变。"""

    @pytest.mark.asyncio
    async def test_put_series_order_reorders_the_chapter_list(
        self,
        client: AsyncClient,
        admin_headers: dict,
        db_session,
        test_post: Post,
    ):
        series = await _mk_series(db_session, "reorder-by-put")
        first = await _mk_chapter(
            db_session, series, test_post.author_id, "r-1", order=1, age_days=3
        )
        await _mk_chapter(db_session, series, test_post.author_id, "r-2", order=2, age_days=2)

        data = await _chapters(series.slug, client)
        assert [row["slug"] for row in data["posts"]] == ["r-1", "r-2"]

        put = await client.put(
            f"{BLOG}/posts/{first.id}",
            headers=admin_headers,
            json={"series_id": series.id, "series_order": 9},
        )
        assert put.status_code == 200, put.text

        data = await _chapters(series.slug, client)
        assert [row["slug"] for row in data["posts"]] == ["r-2", "r-1"], "序号写了、公开口仍是旧序"

        row = (
            await db_session.execute(select(Post.series_order).where(Post.id == first.id))
        ).scalar_one()
        await db_session.rollback()
        assert row == 9
