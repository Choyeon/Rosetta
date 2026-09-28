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
5. 隐私开关对**资料接口**与 **sitemap** 的口径：`public_profile=False` 的作者
   在 `GET /users/{id}` 与 `GET /users/username/{u}` 上统一 404（不是 403/500），
   且与 `show_posts=False` 一样不进作者归档清单。
6. 主页 404 之后，它**下面**的四个同级入口（文章列表 / 评论列表 / 统计 /
   隐私开关组）必须一起消失，并且开关变更要失效已缓存的归档列表——
   见 `TestHiddenProfileSubResources`。
"""

from __future__ import annotations

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import object_session

from backend.api.blog import _get_post_list_cache_key
from backend.core.cache import cache
from backend.models.blog import Post
from backend.models.user import User, UserPreference
from backend.services.cache_service import CacheService
from backend.services.user_service import UserService


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

    @pytest.mark.asyncio
    async def test_author_with_private_profile_is_not_listed(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        test_post: Post,
        test_user: User,
    ):
        """关了「公开资料」的作者同样不得进 sitemap：他的资料接口对外就是 404，
        提交一个爬虫取回 404 的 URL 与提交空归档页是同一类错误。"""
        db_session.add(UserPreference(user_id=test_user.id, public_profile=False, show_posts=True))
        await db_session.commit()

        r = await client.get("/api/blog/sitemap-taxonomies.xml")
        assert f"/authors/{test_user.username}" not in r.text


class TestPrivateAuthorProfileStatus:
    """`public_profile=False` 时资料接口的状态码口径：**统一 404**。

    三条理由（任一都足以否掉旧行为）：
    - 403 承认账号真实存在，等于给了一个用户名枚举 oracle；
    - 前台 `/authors/[username]` 的 404 闸门（`useContentStatus`）只认 404/空对象，
      403 会渲染兜底 UI 却返回 HTTP 200，再被该路由的 swr 缓存成可索引页；
    - 服务层对「非本人 + 不公开」返回的精简视图不含 email，
      旧闸门带 `and not current_user` 放行登录访客后直接把它喂给 `UserResponse`
      → 必填字段缺失 → 500。
    """

    @pytest.mark.asyncio
    @pytest.mark.parametrize("route", ["by_id", "by_username"])
    async def test_anonymous_gets_404(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        test_user: User,
        route: str,
    ):
        db_session.add(UserPreference(user_id=test_user.id, public_profile=False))
        await db_session.commit()

        url = (
            f"/api/users/{test_user.id}"
            if route == "by_id"
            else f"/api/users/username/{test_user.username}"
        )
        assert (await client.get(url)).status_code == 404

    @pytest.mark.asyncio
    @pytest.mark.parametrize("route", ["by_id", "by_username"])
    async def test_logged_in_stranger_gets_404_not_500(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        test_user: User,
        subscriber_headers: dict,
        route: str,
    ):
        """登录访客与匿名同口径：既不泄露存在性，也不走进精简视图把响应打成 500。"""
        db_session.add(UserPreference(user_id=test_user.id, public_profile=False))
        await db_session.commit()

        url = (
            f"/api/users/{test_user.id}"
            if route == "by_id"
            else f"/api/users/username/{test_user.username}"
        )
        assert (await client.get(url, headers=subscriber_headers)).status_code == 404

    @pytest.mark.asyncio
    async def test_owner_still_reads_own_profile(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        test_user: User,
        auth_headers: dict,
    ):
        db_session.add(UserPreference(user_id=test_user.id, public_profile=False))
        await db_session.commit()

        r = await client.get(f"/api/users/{test_user.id}", headers=auth_headers)
        assert r.status_code == 200
        # 该端点直接返回 UserResponse（无 data 信封）
        assert r.json()["email"] == "test@example.com"

    @pytest.mark.asyncio
    async def test_missing_preference_row_defaults_to_public(
        self, client: AsyncClient, test_user: User
    ):
        """没有偏好行 == 没动过开关：模型默认 public_profile=True，必须照常可读。"""
        r = await client.get(f"/api/users/username/{test_user.username}")
        assert r.status_code == 200


class TestCachedProfilePayloadIsReusable:
    """资料缓存的载荷必须能被**下一个请求**原样读出来。

    回归（活体实测，冷缓存第一次正常、第二次起 500）：``user_profile`` 缓存把 ORM 实例
    一起存进了载荷。第一次请求结束后它所属的会话 commit + close，``expire_on_commit``
    把实例属性全部标成过期；TTL 内的第二次请求命中缓存再读任何一个属性——隐私闸门读
    ``preferences.public_profile``、邮箱遮蔽读 ``show_email``、组装响应读用户列——
    都会走延迟刷新而没有会话可刷 → ``DetachedInstanceError`` → HTTP 500。
    表现是「作者主页刷新一下就成了服务器错误」，且公开/不公开两种资料都中招。
    """

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        ("public_profile", "expected"),
        [(True, 200), (False, 404)],
    )
    async def test_repeated_reads_keep_the_same_status(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        test_user: User,
        public_profile: bool,
        expected: int,
    ):
        db_session.add(UserPreference(user_id=test_user.id, public_profile=public_profile))
        await db_session.commit()

        for _ in range(3):
            assert (await client.get(f"/api/users/{test_user.id}")).status_code == expected
            by_name = await client.get(f"/api/users/username/{test_user.username}")
            assert by_name.status_code == expected

    @pytest.mark.asyncio
    async def test_email_masking_is_stable_across_cache_hit(
        self, client: AsyncClient, test_user: User
    ):
        """缓存命中不得改变遮蔽结果：show_email 默认拒绝，两次读都必须是 ``***``。"""
        first = await client.get(f"/api/users/{test_user.id}")
        second = await client.get(f"/api/users/{test_user.id}")
        assert first.json()["email"] == second.json()["email"] == "***"

    @pytest.mark.asyncio
    async def test_profile_cache_payload_holds_no_session_bound_instances(
        self,
        db_session: AsyncSession,
        test_user: User,
    ):
        """进缓存的资料载荷必须是**脱离会话**的实例（只读快照）。

        为什么这条要单独钉：测试里所有请求共用一个会话，所以"另一个请求的会话已
        commit/关闭、载荷属性已过期"这个真实故障条件在 HTTP 层复现不出来（上面的
        重复读用例只锁状态码）。这里直接查缓存载荷的归属——只要还挂着 session 绑定
        实例，下一次请求读到任何属性都可能抛 ``DetachedInstanceError``。
        """
        # 必须有偏好行：故障正是发生在闸门读 preferences.public_profile 的那一刻
        db_session.add(UserPreference(user_id=test_user.id, public_profile=True))
        await db_session.commit()

        cache_service = CacheService()
        service = UserService(db_session, cache=cache_service)
        key = cache_service.build_key("user_profile", test_user.id)
        await cache_service.delete(key)

        profile = await service.get_user_profile(test_user.id, None)
        assert profile is not None and profile["is_public"] is True

        raw = await cache_service.get(key)
        assert raw is not None, "首次读取应已写入 user_profile 缓存"
        for obj in (raw["user"], raw["title"], raw["preferences"]):
            if obj is not None:
                assert object_session(obj) is None, "缓存载荷里不得放会话绑定实例"

        # 脱离会话后属性仍可读（已加载值），否则展示路径会拿到空对象
        assert raw["user"].username == test_user.username
        assert raw["preferences"].public_profile is True


class TestHiddenProfileSubResources:
    """「关闭公开资料」必须让这个主页的**全部**读取面一起消失。

    资料接口先修成了统一 404，但它下面四个同级入口当时完全不查 `public_profile`：
    文章列表、评论列表、统计、以及整组隐私开关本身。表现是"主页 404 了，
    但内容一个不少"——尤其 `GET /users/username/{u}/preferences` 会把
    `public_profile: false` 原样回给匿名调用方，等于当面承认"这个账号存在，只是藏起来了"，
    把刻意选 404 的防枚举口径直接打穿。另一半：`show_stats` 开关全仓零读侧消费者，
    用户在设置页关掉"显示统计"什么也不会发生（死配置）。
    """

    @staticmethod
    async def _hide_profile(db_session: AsyncSession, user_id: int) -> None:
        db_session.add(
            UserPreference(
                user_id=user_id,
                public_profile=False,
                show_posts=True,
                show_comments=True,
                show_stats=True,
            )
        )
        await db_session.commit()

    @pytest.mark.asyncio
    async def test_anonymous_cannot_read_any_sub_resource(
        self, client: AsyncClient, db_session: AsyncSession, test_user: User, test_post: Post
    ):
        await self._hide_profile(db_session, test_user.id)

        for url in (
            f"/api/users/{test_user.id}/posts",
            f"/api/users/{test_user.id}/comments",
            f"/api/users/{test_user.id}/stats",
            f"/api/users/username/{test_user.username}/preferences",
        ):
            r = await client.get(url)
            assert r.status_code == 404, f"{url} 应随主页一起 404，实际 {r.status_code}"

        # 作者归档列表：空页 200（列表不替资料接口表态），但一条都不给。
        r = await client.get("/api/blog/posts", params={"author": test_user.username})
        assert r.status_code == 200
        assert _items(r.json()) == []

    @pytest.mark.asyncio
    async def test_owner_still_reads_every_sub_resource(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        test_user: User,
        test_post: Post,
        auth_headers: dict,
    ):
        await self._hide_profile(db_session, test_user.id)

        for url in (
            f"/api/users/{test_user.id}/posts",
            f"/api/users/{test_user.id}/comments",
            f"/api/users/{test_user.id}/stats",
            f"/api/users/username/{test_user.username}/preferences",
        ):
            r = await client.get(url, headers=auth_headers)
            assert r.status_code == 200, f"本人应越过闸门：{url} -> {r.status_code}"

        r = await client.get(
            "/api/blog/posts", params={"author": test_user.username}, headers=auth_headers
        )
        assert [p["slug"] for p in _items(r.json())] == ["test-post"]

    @pytest.mark.asyncio
    async def test_show_posts_is_empty_list_not_404(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        test_user: User,
        test_post: Post,
    ):
        """两个开关语义不同，不得合并：`show_posts` 是"列表为空"，`public_profile` 才是"页面不存在"。"""
        db_session.add(UserPreference(user_id=test_user.id, public_profile=True, show_posts=False))
        await db_session.commit()

        r = await client.get(f"/api/users/{test_user.id}/posts")
        assert r.status_code == 200
        assert _items(r.json()) == []

    @pytest.mark.asyncio
    async def test_show_stats_switch_zeroes_the_counters(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        test_user: User,
        test_post: Post,
        auth_headers: dict,
    ):
        db_session.add(UserPreference(user_id=test_user.id, public_profile=True, show_stats=False))
        await db_session.commit()

        hidden = (await client.get(f"/api/users/{test_user.id}/stats")).json()
        assert hidden["posts_count"] == 0, "show_stats=False 必须真的把统计藏起来"
        assert hidden["total_views"] == 0 and hidden["total_likes"] == 0

        mine = (await client.get(f"/api/users/{test_user.id}/stats", headers=auth_headers)).json()
        assert mine["posts_count"] == 1, "本人读到的必须是真实值"

    @pytest.mark.asyncio
    async def test_hiding_profile_evicts_the_author_list_cache(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        test_user: User,
        test_post: Post,
    ):
        """闸门结果本身进缓存，所以开关变更必须一起失效它——否则 TTL 内访客仍拿到旧列表。"""
        key = await _get_post_list_cache_key(
            "zh", 1, 10, None, None, None, None, test_user.username
        )
        r = await client.get(
            "/api/blog/posts",
            params={"author": test_user.username, "lang": "zh", "page": 1, "page_size": 10},
        )
        assert r.status_code == 200 and len(_items(r.json())) == 1
        # 读写必须走 blog.py 用的同一个入口：列表键由 core.cache.make_cache_key 生成，
        # 而 CacheService.build_key 带命名空间，用它读这条键会永远得到 None（假失败）。
        assert await cache.get(key) is not None, "前置条件：作者归档列表应已进缓存"

        service = UserService(db_session)
        await service.update_preferences(test_user.id, {"public_profile": False})
        assert await cache.get(key) is None, "隐私开关变更必须清掉该作者的归档列表缓存"
