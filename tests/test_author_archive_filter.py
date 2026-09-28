"""作者归档（``GET /blog/posts?author=<username>``）的契约回归。

这个过滤参数是前台 ``/authors/[username]`` 的唯一取数来源，钉四件事：

1. 只返回该作者的已发布文章，用户名查无此人时是**空页而不是 404**
   （404 由资料接口负责；列表接口替它表态会让页面在两条请求上拿到两种"不存在"）。
2. 缓存键必须带作者段 —— 少了这一段，B 作者的列表会命中 A 作者（或全站）的缓存，
   而缓存键不含查看者，属于跨用户数据串味。
3. ``show_posts=False`` 的隐私闸门与 ``GET /users/{user_id}/posts`` 同口径：
   匿名/他人挡掉，本人与管理员放行；**本人那次不能进缓存**，
   否则特权视图会被缓存成公共视图（与 user_profile 缓存同一类缺陷）。
4. 作者过滤与分类/标签过滤可以叠加（组合条件不串）。
"""

from __future__ import annotations

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from backend.api.blog import _get_post_list_cache_key
from backend.models.blog import Post
from backend.models.user import User, UserPreference


def _items(body: dict) -> list[dict]:
    data = body.get("data") if isinstance(body, dict) and "data" in body else body
    return (data or {}).get("items", [])


class TestAuthorArchiveFilter:
    @pytest.mark.asyncio
    async def test_returns_only_that_authors_posts(
        self, client: AsyncClient, test_post: Post, test_user: User
    ):
        r = await client.get("/api/blog/posts", params={"author": test_user.username})
        assert r.status_code == 200
        items = _items(r.json())
        assert [p["slug"] for p in items] == ["test-post"]

    @pytest.mark.asyncio
    async def test_unknown_username_is_empty_page_not_404(
        self, client: AsyncClient, test_post: Post, test_user: User
    ):
        r = await client.get("/api/blog/posts", params={"author": "ghost-user"})
        assert r.status_code == 200
        body = r.json()
        data = body.get("data", body)
        assert data["items"] == [] and data["total"] == 0 and data["total_pages"] == 0

    @pytest.mark.asyncio
    async def test_cache_key_isolates_authors(self):
        """不同作者/无作者必须是不同键，否则列表结果跨作者命中。"""
        base = {
            "language": "zh",
            "page": 1,
            "page_size": 12,
            "category": None,
            "tag": None,
            "search": None,
            "status_filter": None,
        }
        keys = {
            await _get_post_list_cache_key(**base),
            await _get_post_list_cache_key(**base, author="alice"),
            await _get_post_list_cache_key(**base, author="bob"),
        }
        assert len(keys) == 3

    @pytest.mark.asyncio
    async def test_hidden_posts_preference_blocks_anonymous_but_not_self_or_staff(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        test_post: Post,
        auth_headers: dict,
        staff_headers: dict,
        test_user: User,
    ):
        db_session.add(UserPreference(user_id=test_user.id, public_profile=True, show_posts=False))
        await db_session.commit()

        anon = await client.get("/api/blog/posts", params={"author": test_user.username})
        assert _items(anon.json()) == []

        # 本人放行
        me = await client.get(
            "/api/blog/posts",
            params={"author": test_user.username},
            headers=auth_headers,
        )
        assert [p["slug"] for p in _items(me.json())] == ["test-post"]

        # 管理员放行
        staff = await client.get(
            "/api/blog/posts",
            params={"author": test_user.username},
            headers=staff_headers,
        )
        assert len(_items(staff.json())) == 1

    @pytest.mark.asyncio
    async def test_self_view_is_not_written_to_shared_cache(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        test_post: Post,
        auth_headers: dict,
        test_user: User,
    ):
        """本人（绕过隐私闸门）看到的结果不得进缓存——缓存键里没有查看者。"""
        db_session.add(UserPreference(user_id=test_user.id, show_posts=False))
        await db_session.commit()

        await client.get(
            "/api/blog/posts",
            params={"author": test_user.username},
            headers=auth_headers,
        )
        # 紧接着匿名请求必须仍是空页（不能被上一次的"特权结果"污染）
        anon = await client.get("/api/blog/posts", params={"author": test_user.username})
        assert _items(anon.json()) == []

    @pytest.mark.asyncio
    async def test_author_filter_combines_with_category(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        test_post: Post,
        test_category,
    ):
        """叠加条件不串：另一位作者在同一分类下不该被 author+category 查出来。"""
        other = User(
            username="other-author",
            email="other@example.com",
            password_hash="x",
            nickname="Other",
            is_active=True,
        )
        db_session.add(other)
        await db_session.commit()
        await db_session.refresh(other)
        db_session.add(
            Post(
                title={"zh": "他人文章", "en": "Other Post"},
                slug="other-author-post",
                content={"zh": "内容", "en": "content"},
                excerpt={"zh": "摘要", "en": "excerpt"},
                author_id=other.id,
                category_id=test_category.id,
                status="published",
                allow_comments=True,
            )
        )
        await db_session.commit()

        r = await client.get(
            "/api/blog/posts",
            params={"author": other.username, "category": test_category.slug},
        )
        assert [p["slug"] for p in _items(r.json())] == ["other-author-post"]


class TestAuthorArchiveSitemap:
    """作者归档落地页必须进 sitemap，且隐私关闭的作者不得进。

    与年份归档同一口径：页面声明自己是可索引的 SSR 页，只靠文章详情里的作者卡
    给爬虫发现 URL 太弱。反过来，`show_posts=False` 的归档页对访客是空页，
    提交上去等于承认一个没内容的 URL。
    """

    @pytest.mark.asyncio
    async def test_author_with_posts_is_listed(
        self, client: AsyncClient, test_post: Post, test_user: User
    ):
        r = await client.get("/api/blog/sitemap-taxonomies.xml")
        assert r.status_code == 200
        assert f"/authors/{test_user.username}" in r.text

    @pytest.mark.asyncio
    async def test_author_with_hidden_posts_is_not_listed(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        test_post: Post,
        test_user: User,
    ):
        db_session.add(UserPreference(user_id=test_user.id, public_profile=True, show_posts=False))
        await db_session.commit()

        r = await client.get("/api/blog/sitemap-taxonomies.xml")
        assert f"/authors/{test_user.username}" not in r.text
