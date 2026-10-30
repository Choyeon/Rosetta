"""文章详情里的「所属系列」简报契约（批次 #74）。

系列页 `GET /api/series/{slug}` 早就存在，但**全站没有任何指向 `/series/**` 的 href**：
文章详情页一个 `series` 字样都没有，`footerEntryPoints.spec.ts` 的 allowlist 却写着
「入口在文章详情页的系列卡片」——那条注释描述的是一个不存在的组件。结果就是这个公开页
只能从 sitemap 被发现，访客走不到。

本批在 `GET /api/blog/posts/{slug}` 上补 `series` 简报（slug / 本地化 title / 章数 / 本篇序位），
卡片才有数据可渲染。下面每条都对应一个真实的失效形态：

1. 序位与总数必须和系列页同一份排序口径，否则卡片上的「第 N 章」与系列页的实际位置对不上；
2. title 走 `get_i18n_value`，英文页不能还显示中文系列名；
3. 系列停用时必须回 null——系列页对停用系列是 404，卡片不能把访客引向 404；
4. 草稿章节不占位也不计数（与 `publicly_listable_posts` 一致）；
5. 作者预览自己的草稿时，本篇不在公开目录里 → position 为 null，而不是编一个 0 或 1；
6. `prev` / `next` 同样按系列页的顺序算，且跳过公开目录里不存在的章节——邻居指向一篇 404
   与「上一章」这个承诺正好相反。
"""

from datetime import timedelta

import pytest
from httpx import AsyncClient

from backend.models.blog import Post
from backend.models.post_series import PostSeries
from backend.utils.compat import utc_now_naive

BLOG = "/api/blog"
SERIES = "/api/series"


def _unwrap(body):
    """详情口走全局信封 `{success, data}`，系列详情口是裸 dict——两种都接。"""
    if isinstance(body, dict) and "data" in body:
        return body["data"]
    return body


async def _mk_series(db, slug: str, *, title: dict | None = None, is_active: bool = True):
    series = PostSeries(
        title=title or {"zh": f"系列{slug}", "en": f"Series {slug}"},
        slug=slug,
        is_active=is_active,
    )
    db.add(series)
    await db.commit()
    await db.refresh(series)
    return series


async def _mk_post(
    db,
    author_id: int,
    slug: str,
    *,
    series=None,
    order: int = 0,
    status: str = "published",
    age_days: int = 1,
):
    post = Post(
        title={"zh": f"《{slug}》", "en": slug},
        slug=slug,
        content={"zh": "正文", "en": "body"},
        excerpt={"zh": "摘要", "en": "excerpt"},
        author_id=author_id,
        series_id=series.id if series else None,
        series_order=order,
        status=status,
        # 必须是 naive：SQLite 把 aware 值存成带 +00:00 的字符串，
        # `published_at <= now()` 会按字符串比较把刚写的行判成"在未来"（AGENTS §9.1）。
        published_at=utc_now_naive() - timedelta(days=age_days) if status == "published" else None,
    )
    db.add(post)
    await db.commit()
    await db.refresh(post)
    return post


async def _detail(client: AsyncClient, slug: str, *, lang: str = "zh", headers: dict | None = None):
    resp = await client.get(f"{BLOG}/posts/{slug}", params={"lang": lang}, headers=headers or {})
    assert resp.status_code == 200, resp.text
    return _unwrap(resp.json())


class TestSeriesBriefShape:
    @pytest.mark.asyncio
    async def test_position_and_total_match_the_series_page(
        self, client: AsyncClient, db_session, test_post: Post
    ):
        """序位与总数必须与系列页同一份排序口径（series_order → 发布时间倒序）。"""
        series = await _mk_series(db_session, "brief-order")
        await _mk_post(
            db_session, test_post.author_id, "brief-3", series=series, order=3, age_days=30
        )
        second = await _mk_post(
            db_session, test_post.author_id, "brief-1", series=series, order=1, age_days=10
        )
        await _mk_post(
            db_session, test_post.author_id, "brief-2", series=series, order=2, age_days=20
        )

        body = await _detail(client, "brief-1")
        brief = body["series"]
        assert brief is not None
        assert brief["slug"] == "brief-order"
        assert brief["post_count"] == 3
        assert brief["position"] == 1

        chapters = _unwrap((await client.get(f"{SERIES}/brief-order")).json())["posts"]
        order = [row["slug"] for row in chapters]
        for slug in ("brief-1", "brief-2", "brief-3"):
            detail = await _detail(client, slug)
            assert detail["series"]["position"] == order.index(slug) + 1, (
                f"{slug} 的序位与系列页目录不一致：{detail['series']['position']} vs {order.index(slug) + 1}"
            )

        # 交叉用例故意用中间那篇再验一次总数（防止 position 与 post_count 互相覆盖）
        assert (await _detail(client, "brief-2"))["series"]["post_count"] == 3
        assert second.series_id == series.id

    @pytest.mark.asyncio
    async def test_title_follows_request_language(
        self, client: AsyncClient, db_session, test_post: Post
    ):
        """系列名走 get_i18n_value：英文页显示英文名，不能回落成中文。"""
        series = await _mk_series(db_session, "brief-i18n")
        await _mk_post(db_session, test_post.author_id, "brief-i18n-1", series=series, order=1)

        zh = await _detail(client, "brief-i18n-1", lang="zh")
        en = await _detail(client, "brief-i18n-1", lang="en")
        assert zh["series"]["title"] == "系列brief-i18n"
        assert en["series"]["title"] == "Series brief-i18n"

    @pytest.mark.asyncio
    async def test_post_without_series_is_null(
        self, client: AsyncClient, db_session, test_post: Post
    ):
        """不属于任何系列：键必须存在且为 null，页面据此整块不渲染。"""
        await _mk_post(db_session, test_post.author_id, "brief-none")
        body = await _detail(client, "brief-none")
        assert "series" in body
        assert body["series"] is None


class TestSeriesBriefVisibility:
    @pytest.mark.asyncio
    async def test_inactive_series_is_not_linked(
        self, client: AsyncClient, db_session, test_post: Post
    ):
        """停用系列的页面是 404：卡片不能把访客引过去，所以详情也回 null。"""
        series = await _mk_series(db_session, "brief-inactive", is_active=False)
        await _mk_post(db_session, test_post.author_id, "brief-inactive-1", series=series, order=1)

        assert (await _detail(client, "brief-inactive-1"))["series"] is None
        assert (await client.get(f"{SERIES}/brief-inactive")).status_code == 404

    @pytest.mark.asyncio
    async def test_draft_chapter_is_not_counted(
        self, client: AsyncClient, db_session, test_post: Post
    ):
        """草稿不占位也不计数（与 publicly_listable_posts 同口径）。"""
        series = await _mk_series(db_session, "brief-draft-count")
        await _mk_post(db_session, test_post.author_id, "brief-d-1", series=series, order=1)
        await _mk_post(db_session, test_post.author_id, "brief-d-2", series=series, order=2)
        await _mk_post(
            db_session, test_post.author_id, "brief-d-3", series=series, order=3, status="draft"
        )

        body = await _detail(client, "brief-d-1")
        assert body["series"]["post_count"] == 2
        assert body["series"]["position"] == 1

    @pytest.mark.asyncio
    async def test_author_preview_of_own_draft_has_no_position(
        self, client: AsyncClient, db_session, test_post: Post, auth_headers: dict
    ):
        """作者预览草稿：系列信息照给（编辑期就要看到归属），但本篇不在公开目录里 → position 为 null。"""
        series = await _mk_series(db_session, "brief-preview")
        await _mk_post(db_session, test_post.author_id, "brief-p-1", series=series, order=1)
        await _mk_post(
            db_session, test_post.author_id, "brief-p-draft", series=series, order=9, status="draft"
        )

        body = await _detail(client, "brief-p-draft", headers=auth_headers)
        assert body["series"] is not None
        assert body["series"]["post_count"] == 1
        assert body["series"]["position"] is None


class TestSeriesAdjacentChapters:
    """卡片上的「上一章 / 下一章」：按系列页同一份顺序算，而不是按发布时间或插入顺序。"""

    @pytest.mark.asyncio
    async def test_head_middle_tail(self, client: AsyncClient, db_session, test_post: Post):
        """首章只有下一章、中间章两头都有、末章只有上一章——头尾不许编出不存在的邻居。"""
        series = await _mk_series(db_session, "adjacent-chain")
        # 故意让发布时间与序号相反：邻居必须跟 series_order 走
        await _mk_post(
            db_session, test_post.author_id, "adj-1", series=series, order=1, age_days=30
        )
        await _mk_post(
            db_session, test_post.author_id, "adj-2", series=series, order=2, age_days=20
        )
        await _mk_post(
            db_session, test_post.author_id, "adj-3", series=series, order=3, age_days=10
        )

        head = (await _detail(client, "adj-1"))["series"]
        assert head["prev"] is None
        assert head["next"] == {"slug": "adj-2", "title": "《adj-2》"}

        middle = (await _detail(client, "adj-2"))["series"]
        assert middle["prev"] == {"slug": "adj-1", "title": "《adj-1》"}
        assert middle["next"] == {"slug": "adj-3", "title": "《adj-3》"}

        tail = (await _detail(client, "adj-3"))["series"]
        assert tail["prev"] == {"slug": "adj-2", "title": "《adj-2》"}
        assert tail["next"] is None

    @pytest.mark.asyncio
    async def test_neighbour_titles_follow_language(
        self, client: AsyncClient, db_session, test_post: Post
    ):
        series = await _mk_series(db_session, "adjacent-i18n")
        await _mk_post(db_session, test_post.author_id, "adj-i1", series=series, order=1)
        await _mk_post(db_session, test_post.author_id, "adj-i2", series=series, order=2)

        en = (await _detail(client, "adj-i1", lang="en"))["series"]
        assert en["next"] == {"slug": "adj-i2", "title": "adj-i2"}

    @pytest.mark.asyncio
    async def test_hidden_chapter_is_skipped_in_the_chain(
        self, client: AsyncClient, db_session, test_post: Post
    ):
        """序号 2 是草稿：1 的下一章必须直接是 3，不能把访客带到一篇 404 上。"""
        series = await _mk_series(db_session, "adjacent-gap")
        await _mk_post(db_session, test_post.author_id, "gap-1", series=series, order=1, age_days=3)
        await _mk_post(
            db_session, test_post.author_id, "gap-2", series=series, order=2, status="draft"
        )
        await _mk_post(db_session, test_post.author_id, "gap-3", series=series, order=3, age_days=1)

        first = (await _detail(client, "gap-1"))["series"]
        assert first["post_count"] == 2
        assert first["next"]["slug"] == "gap-3"

        last = (await _detail(client, "gap-3"))["series"]
        assert last["prev"]["slug"] == "gap-1"

    @pytest.mark.asyncio
    async def test_preview_of_draft_has_no_neighbours(
        self, client: AsyncClient, db_session, test_post: Post, auth_headers: dict
    ):
        """本篇不在公开目录里时，「下一篇」没有答案：两个邻居都必须是 null，而不是指向首章。"""
        series = await _mk_series(db_session, "adjacent-preview")
        await _mk_post(db_session, test_post.author_id, "adjp-1", series=series, order=1)
        await _mk_post(
            db_session, test_post.author_id, "adjp-draft", series=series, order=5, status="draft"
        )

        body = (await _detail(client, "adjp-draft", headers=auth_headers))["series"]
        assert body["position"] is None
        assert body["prev"] is None
        assert body["next"] is None
