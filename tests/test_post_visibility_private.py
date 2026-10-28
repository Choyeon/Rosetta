"""``Post.visibility == "private"`` 私密档的读写两端回归。

这一列此前的形状是"写进去没人读"：``Post`` 有列、``PostCreate``/``PostUpdate`` 都收这个
键、后台编辑器下拉里有"公开 / 密码保护 / 私密"三档，但 **create 端点构造 ORM 对象时把
`visibility` 整个丢掉**（永远是列默认 public），而所有匿名读口也从不看它。表现就是作者
点了"私密"、后台显示保存成功，文章却照常出现在列表、RSS、sitemap、热榜、推荐位和上下篇
里——这是隐私开关失效，不是显示瑕疵。

接通后的口径（判据单源见 :mod:`backend.services.post_access`）：

1. **对象级**（详情口、评论口）：``post_is_publicly_visible`` 覆盖私密档 → 非作者非管理员
   一律 404（不是 403：承认存在即可枚举）。
2. **集合级**（列表 / RSS / sitemap / 归档 / 热榜 / 推荐 / 系列 / 作者主页 / 收藏）：SQL
   带不动"作者本人可见"这层身份语义，所以按最保守的匿名视角整条排除；作者找回私密稿
   走后台列表（staff 分支）。
3. **可见性是独立的一轴**：与 status/密码正交，"已发布 + 私密"是合法组合；列表必须带出
   ``visibility`` 才谈得上审计。
4. 历史脏值（空串 / NULL）按 public 处理——迁移 0482c6771d47 之前留的行不能被误判成私密，
   那会把已发布文章整篇藏掉。
"""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.cache import cache
from backend.models.blog import Category, Comment, Post
from backend.models.post_series import PostSeries
from backend.models.user import User
from backend.services.post_access import is_private_post, private_posts_excluded
from backend.utils.compat import UTC

pytestmark = pytest.mark.asyncio

BASE = "/api/blog"
LIST = f"{BASE}/posts"


def _slug(prefix: str = "vis") -> str:
    return f"{prefix}-{uuid.uuid4().hex[:10]}"


def _payload(body):
    """兼容统一响应封装：取出真正的业务负载。"""
    if isinstance(body, dict) and "data" in body and "success" in body:
        return body["data"] or {}
    return body or {}


async def _mk(
    db_session: AsyncSession,
    author_id: int,
    *,
    slug: str | None = None,
    status: str = "published",
    visibility: str | None = "private",
    title: str | None = None,
    published_at: datetime | None = None,
    views: int = 0,
    **kwargs,
) -> Post:
    name = slug or _slug()
    post = Post(
        title={"zh": title or name, "en": title or name},
        slug=name,
        content={"zh": "只有作者该看到的正文", "en": "author-only body"},
        excerpt={"zh": "私密摘要", "en": "private excerpt"},
        author_id=author_id,
        status=status,
        visibility=visibility,
        published_at=published_at or (datetime.now(UTC) - timedelta(hours=1)),
        allow_comments=True,
        views=views,
        **kwargs,
    )
    db_session.add(post)
    await db_session.commit()
    await db_session.refresh(post)
    return post


def _year_count(stats: dict, year: int) -> int:
    """归档统计的年份桶（JSON 往返后键是字符串，直读时是整数）。"""
    counts = stats.get("year_stats") or {}
    return counts.get(str(year), counts.get(year, 0))


def _iter_slugs(node) -> list[str]:
    """把"文章集合"的几种响应形态摊平成 slug 列表。

    列表口是 {items: [...]}，归档年口是 [{month, posts: [...]}, ...]，归档月口是
    {month, posts: [...]}——断言只关心"哪些 slug 出现了"，不该为每种壳写一遍。
    """
    if isinstance(node, dict):
        out: list[str] = []
        for key in ("items", "posts"):
            if key in node:
                out.extend(_iter_slugs(node[key]))
        return out
    if isinstance(node, list):
        out = []
        for item in node:
            if isinstance(item, dict) and "slug" in item:
                out.append(item["slug"])
            else:
                out.extend(_iter_slugs(item))
        return out
    return []


async def _slugs(client: AsyncClient, url: str, **kwargs) -> list[str]:
    resp = await client.get(url, **kwargs)
    assert resp.status_code == 200, f"{url} -> {resp.status_code} {resp.text}"
    return _iter_slugs(_payload(resp.json()))


class TestPredicateShape:
    """判据本身的两条口径（集合口与对象口各一份形态）。"""

    async def test_blank_and_null_are_not_private(self):
        assert is_private_post(Post(visibility="private")) is True
        assert is_private_post(Post(visibility="public")) is False
        assert is_private_post(Post(visibility="")) is False
        assert is_private_post(Post(visibility=None)) is False

    async def test_sql_predicate_is_a_column_expression(self):
        """谓词要能进 SQL（不是 Python 闭包）——否则整条集合口没法过滤。"""
        from sqlalchemy import select
        from sqlalchemy.dialects import sqlite

        sql = str(
            select(Post.id)
            .where(private_posts_excluded())
            .compile(
                dialect=sqlite.dialect(),
                compile_kwargs={"literal_binds": True},
            )
        )
        assert "COALESCE" in sql.upper()
        assert "'private'" in sql


class TestWritePath:
    async def test_create_persists_visibility(
        self, client: AsyncClient, admin_headers: dict, db_session: AsyncSession
    ):
        """创建口不再丢键：响应与库里的 visibility 都是 private。

        回归的正是"schema 收得到、ORM 构造时漏传"这一类静默失效——接口回 200、后台显示
        成功，列里却永远是默认值。
        """
        slug = _slug()
        created = await client.post(
            LIST,
            json={
                "title": {"zh": "一篇私密文章", "en": "private one"},
                "content": {"zh": "正文", "en": "body"},
                "slug": slug,
                "status": "published",
                "visibility": "private",
            },
            headers=admin_headers,
        )
        assert created.status_code == 201, created.text
        assert _payload(created.json())["visibility"] == "private"

        row = (await db_session.execute(select(Post).where(Post.slug == slug))).scalar_one()
        assert row.visibility == "private"

    async def test_put_moves_visibility_back_to_public(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        admin_user: User,
        admin_headers: dict,
    ):
        """私密 → 公开要真的重新出现在公开列表里（写口双向都通 + 缓存被清）。"""
        post = await _mk(db_session, admin_user.id, slug=_slug())
        assert post.slug not in await _slugs(client, LIST, params={"page_size": 200})

        updated = await client.put(
            f"{LIST}/{post.id}", json={"visibility": "public"}, headers=admin_headers
        )
        assert updated.status_code == 200, updated.text
        assert _payload(updated.json())["visibility"] == "public"
        assert post.slug in await _slugs(client, LIST, params={"page_size": 200})


class TestObjectLevelGate:
    async def test_slug_detail_404_for_anonymous_but_readable_by_author_and_staff(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        test_user: User,
        auth_headers: dict,
        staff_headers: dict,
    ):
        post = await _mk(db_session, test_user.id)

        anon = await client.get(f"{LIST}/{post.slug}")
        assert anon.status_code == 404, anon.text

        as_author = await client.get(f"{LIST}/{post.slug}", headers=auth_headers)
        assert as_author.status_code == 200, as_author.text
        assert _payload(as_author.json())["visibility"] == "private"

        as_staff = await client.get(f"{LIST}/{post.slug}", headers=staff_headers)
        assert as_staff.status_code == 200, as_staff.text

    async def test_by_id_detail_uses_the_same_gate(
        self, client: AsyncClient, db_session: AsyncSession, test_user: User
    ):
        """按 ID 的详情口必须与 slug 口同判据——两条口各写一套规则就是泄漏的起点。"""
        post = await _mk(db_session, test_user.id)
        resp = await client.get(f"{LIST}/id/{post.id}")
        assert resp.status_code == 404, resp.text

    async def test_a_private_post_never_enters_the_anonymous_detail_cache(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        test_user: User,
        auth_headers: dict,
    ):
        """详情缓存读在闸门之前，所以闸门必须管得住 visibility。

        顺序刻意是"匿名 → 作者 → 匿名"：作者那次读会命中特权分支，绝不能把正文留在
        ``post:{slug}:{lang}`` 里给下一个访客回放。
        """
        post = await _mk(db_session, test_user.id)
        assert (await client.get(f"{LIST}/{post.slug}")).status_code == 404
        assert (await client.get(f"{LIST}/{post.slug}", headers=auth_headers)).status_code == 200

        replay = await client.get(f"{LIST}/{post.slug}")
        assert replay.status_code == 404, replay.text

    async def test_comments_on_a_private_post_are_not_readable(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        test_user: User,
        auth_headers: dict,
    ):
        """正文藏了、评论没藏 = 泄漏；两条评论口与详情口共用同一条判据。

        形状差异是刻意的（见 :mod:`backend.services.post_access` 模块注释）：
        列表口回空页，详情型口按不存在处理回 404。
        """
        post = await _mk(db_session, test_user.id)
        db_session.add(
            Comment(
                post_id=post.id,
                content="引用了正文的评论",
                author_name="访客",
                author_email="guest@example.com",
                status="approved",
                active=True,
            )
        )
        await db_session.commit()

        as_list = await client.get(f"{LIST}/{post.id}/comments")
        assert as_list.status_code == 200, as_list.text
        assert as_list.json() == []

        as_detail = await client.get(f"/api/posts/{post.slug}/comments")
        assert as_detail.status_code == 404, as_detail.text
        assert as_detail.json()["error_code"] == "POST_NOT_FOUND"

        as_author = await client.get(f"{LIST}/{post.id}/comments", headers=auth_headers)
        assert as_author.status_code == 200, as_author.text
        assert len(as_author.json()) == 1

    async def test_adjacent_404s_on_a_private_anchor_and_skips_it_as_neighbor(
        self, client: AsyncClient, db_session: AsyncSession, test_user: User
    ):
        """上下篇：私密稿既不能当锚点，也不能出现在别人的上下篇里。"""
        anchor = await _mk(
            db_session,
            test_user.id,
            visibility="public",
            slug=_slug("adj"),
            published_at=datetime.now(UTC) - timedelta(days=2),
        )
        private = await _mk(db_session, test_user.id)

        resp = await client.get(f"{LIST}/{private.slug}/adjacent")
        assert resp.status_code == 404, resp.text

        neighbours = _payload((await client.get(f"{LIST}/{anchor.slug}/adjacent")).json())
        got = [d["slug"] for d in (neighbours["previous"], neighbours["next"]) if d]
        assert private.slug not in got


class TestCollectiveSurfaces:
    async def test_anonymous_list_excludes_while_staff_list_includes(
        self, client: AsyncClient, db_session: AsyncSession, test_user: User, staff_headers: dict
    ):
        hidden = await _mk(db_session, test_user.id)
        shown = await _mk(db_session, test_user.id, visibility="public", slug=_slug("pub"))

        anon_slugs = await _slugs(client, LIST, params={"page_size": 200})
        assert hidden.slug not in anon_slugs
        assert shown.slug in anon_slugs

        staff_slugs = await _slugs(
            client, LIST, params={"status": "all", "page_size": 200}, headers=staff_headers
        )
        assert hidden.slug in staff_slugs, "私密稿必须在后台可见，否则作者再也找不回它"

    async def test_list_items_carry_visibility_for_the_admin_badge(
        self, client: AsyncClient, db_session: AsyncSession, test_user: User, staff_headers: dict
    ):
        """列表项带出 ``visibility``：后台靠它标"私密/密码"，没有这个键就无从审计。"""
        post = await _mk(db_session, test_user.id)
        resp = await client.get(
            LIST, params={"status": "all", "page_size": 200}, headers=staff_headers
        )
        assert resp.status_code == 200
        row = next(item for item in resp.json()["items"] if item["slug"] == post.slug)
        assert row["visibility"] == "private"
        assert row["status"] == "published", "私密与已发布是两条正交的轴"

    async def test_search_and_taxonomy_filters_still_exclude(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        test_user: User,
        test_category: Category,
    ):
        """筛选条件只是同一张查询追加 WHERE，不得绕过排除谓词。

        搜索词直接用 slug：标题就是它，`%词%` 只能命中这一篇，公开那篇当对照组
        证明"搜不到"不是因为搜索口整个是空的。
        """
        hidden = await _mk(db_session, test_user.id)
        hidden.category_id = test_category.id
        shown = await _mk(db_session, test_user.id, visibility="public", slug=_slug("vispub"))
        shown.category_id = test_category.id
        await db_session.commit()

        assert hidden.slug not in await _slugs(client, LIST, params={"search": hidden.slug})
        assert shown.slug in await _slugs(client, LIST, params={"search": shown.slug})

        cat_slugs = await _slugs(client, LIST, params={"category": test_category.slug})
        assert hidden.slug not in cat_slugs
        assert shown.slug in cat_slugs

    async def test_hot_recommended_similar_and_ranking_exclude(
        self, client: AsyncClient, db_session: AsyncSession, test_user: User, test_post: Post
    ):
        hidden = await _mk(db_session, test_user.id, views=999_999)

        assert hidden.slug not in await _slugs(client, f"{LIST}/hot", params={"limit": 50})
        assert hidden.slug not in await _slugs(
            client, f"{LIST}/recommended", params={"page_size": 100}
        )
        assert hidden.slug not in await _slugs(client, f"{LIST}/{test_post.id}/similar")

        body = _payload((await client.get("/api/ranking/posts")).json())
        items = body["items"] if isinstance(body, dict) else body
        assert hidden.slug not in [item["slug"] for item in items]

    async def test_private_anchor_yields_no_similar_posts(
        self, client: AsyncClient, db_session: AsyncSession, test_user: User
    ):
        """私密稿自己也不该成为推荐锚点（候选与锚点两侧同口径）。"""
        hidden = await _mk(db_session, test_user.id)
        resp = await client.get(f"{LIST}/{hidden.id}/similar")
        assert resp.status_code == 200, resp.text
        assert resp.json() == []

    async def test_archive_lists_and_stats_exclude(
        self, client: AsyncClient, db_session: AsyncSession, test_user: User
    ):
        year, month = 2024, 5
        shown = await _mk(
            db_session,
            test_user.id,
            visibility="public",
            slug=_slug("archpub"),
            published_at=datetime(year, 6, 10, 12),
        )
        await cache.clear()
        before = _payload((await client.get(f"{BASE}/archive/stats")).json())

        hidden = await _mk(db_session, test_user.id, published_at=datetime(year, month, 10, 12))

        year_slugs = await _slugs(client, f"{BASE}/archive/{year}")
        assert hidden.slug not in year_slugs
        assert shown.slug in year_slugs
        assert hidden.slug not in await _slugs(client, f"{BASE}/archive/{year}/{month:02d}")

        await cache.clear()
        after = _payload((await client.get(f"{BASE}/archive/stats")).json())
        assert after["total_posts"] == before["total_posts"], "归档总数不得算进私密稿"
        assert _year_count(after, year) == _year_count(before, year), (
            f"该年桶计数必须不变：{before.get('year_stats')} -> {after.get('year_stats')}"
        )

    async def test_public_counts_exclude(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        test_user: User,
        test_category: Category,
    ):
        """站点统计 / 分类计数不得把"对外不存在"的文章算进去。"""
        await cache.clear()
        before_stats = _payload((await client.get(f"{BASE}/site-stats")).json())
        before_cat = {
            c["id"]: c["post_count"]
            for c in _payload((await client.get(f"{BASE}/categories")).json())
        }

        hidden = await _mk(db_session, test_user.id)
        hidden.category_id = test_category.id
        await db_session.commit()
        await cache.clear()

        after_stats = _payload((await client.get(f"{BASE}/site-stats")).json())
        assert after_stats["total_posts"] == before_stats["total_posts"]

        after_cat = {
            c["id"]: c["post_count"]
            for c in _payload((await client.get(f"{BASE}/categories")).json())
        }
        assert after_cat == before_cat

        one_cat = _payload(
            (await client.get(f"{BASE}/categories/slug/{test_category.slug}")).json()
        )
        assert one_cat["post_count"] == before_cat[test_category.id]

    async def test_rss_and_sitemap_exclude(
        self, client: AsyncClient, db_session: AsyncSession, test_user: User
    ):
        hidden = await _mk(db_session, test_user.id, title="绝不该出现在订阅源的标题")
        await cache.clear()
        for url in (
            "/api/blog/rss",
            "/api/blog/sitemap.xml",
            "/api/blog/sitemap-posts.xml",
            "/api/blog/sitemap-taxonomies.xml",
            "/api/blog/sitemap-pages.xml",
        ):
            resp = await client.get(url)
            assert resp.status_code == 200, f"{url} -> {resp.status_code}"
            assert hidden.slug not in resp.text, f"私密稿泄漏进了 {url}"

    async def test_author_archive_and_stats_exclude(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        test_user: User,
        test_post: Post,
    ):
        hidden = await _mk(db_session, test_user.id)

        slugs = await _slugs(client, f"/api/users/{test_user.id}/posts", params={"page_size": 50})
        assert hidden.slug not in slugs
        assert test_post.slug in slugs

        stats = _payload((await client.get(f"/api/users/{test_user.id}/stats")).json())
        assert stats["posts_count"] == 1, stats

    async def test_series_listing_excludes_private_posts(
        self, client: AsyncClient, db_session: AsyncSession, test_user: User
    ):
        series = PostSeries(title={"zh": "混合系列", "en": "mixed"}, slug=_slug("ser"))
        db_session.add(series)
        await db_session.commit()
        await db_session.refresh(series)

        hidden = await _mk(db_session, test_user.id)
        hidden.series_id = series.id
        shown = await _mk(db_session, test_user.id, visibility="public", slug=_slug("srv"))
        shown.series_id = series.id
        await db_session.commit()

        detail = _payload((await client.get(f"/api/series/{series.slug}")).json())
        got = [p["slug"] for p in detail["posts"]]
        assert hidden.slug not in got
        assert shown.slug in got
        assert detail["post_count"] == 1


class TestLegacyValues:
    async def test_blank_and_null_visibility_stay_public(
        self, client: AsyncClient, db_session: AsyncSession, test_user: User
    ):
        """迁移前的脏值（空串 / NULL）不能被当成私密。"""
        blank = await _mk(db_session, test_user.id, visibility="", slug=_slug("blank"))
        nullish = await _mk(db_session, test_user.id, visibility=None, slug=_slug("null"))

        slugs = await _slugs(client, LIST, params={"page_size": 200})
        assert blank.slug in slugs
        assert nullish.slug in slugs
        assert (await client.get(f"{LIST}/{blank.slug}")).status_code == 200
        assert (await client.get(f"{LIST}/{nullish.slug}")).status_code == 200


class TestWarmedCacheMatchesReadSide:
    async def test_category_count_warmup_excludes_private(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        test_user: User,
    ):
        """预热口必须与读侧同一条谓词，且计数值本身要钉死。

        `cache_warmer` 用自己的会话把 `CACHE_KEY_CATEGORIES` 整份写进缓存，匿名请求命中后
        直接回放——读侧加了排除而预热没加的话，访客看到的分类计数仍是把私密稿算进去的那个数，
        而且在缓存 TTL 内稳定地错。

        这里不能拿"读侧接口的返回值"当期望：那条接口读的就是同一个键位，两边都是预热写进去的
        载荷，怎么变异都不会红（实测过）。所以用一条独立算出来的绝对值——一篇公开 + 一篇私密
        落在同一个新建分类里，正确读数就是 1。
        """
        from backend.core.cache import CACHE_KEY_CATEGORIES
        from backend.core.cache_warmer import cache_warmer

        cat = Category(name={"zh": "计数专用", "en": "counting"}, slug=_slug("cnt"), is_active=True)
        db_session.add(cat)
        await db_session.commit()
        await db_session.refresh(cat)

        await _mk(
            db_session,
            test_user.id,
            visibility="public",
            slug=_slug("warmpub"),
            category_id=cat.id,
        )
        await _mk(db_session, test_user.id, category_id=cat.id)

        # 直接跑那一个预热任务：`warmup_cache()` 还带全局开关与"只跑一次"的状态机，
        # 在测试进程里会被提前 return，那样这条断言就永远只是空通过。
        await cache.delete(CACHE_KEY_CATEGORIES)
        assert await cache_warmer._warmup_categories() == 1
        warmed = await cache.get(CACHE_KEY_CATEGORIES)
        assert warmed is not None, "预热没写进这个键位，对照断言会退化成空通过"
        row = next((r for r in warmed if r.get("slug") == cat.slug), None)
        assert row is not None, f"预热载荷里没有该分类：{str(warmed)[:120]}"
        assert row["post_count"] == 1, (
            f"预热计数={row['post_count']}：一篇公开 + 一篇私密只该数到 1，"
            "多出来的那篇就是私密稿漏进了匿名缓存"
        )


class TestAuthorRecoveryPath:
    async def test_own_posts_listing_keeps_the_private_draft(
        self, client: AsyncClient, db_session: AsyncSession, test_user: User, auth_headers: dict
    ):
        """作者的"我的文章"口必须仍然看得见私密稿。

        集合口的排除是身份盲的，一旦有人图省事把谓词也叠到这条按 `author_id` 圈定的口上，
        表现就是"作者自己存了篇私密文章，然后再也找不到它"——所以这条得正反各钉一遍。
        """
        hidden = await _mk(db_session, test_user.id)

        got = await _slugs(
            client, f"{BASE}/users/me/posts", params={"page_size": 50}, headers=auth_headers
        )
        assert hidden.slug in got, "作者必须能找回自己的私密稿"
        assert hidden.slug not in await _slugs(client, LIST, params={"page_size": 200})
