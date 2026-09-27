"""公开响应 PII 与文章详情缓存契约的回归测试。

覆盖三类曾经真实存在、修完后必须有守卫的缺陷：

1. 文章 / 动态的 ``author`` 字段直接复用 ``UserResponse``，把 email、qq、
   is_staff / is_superuser / role / last_login 一并发给匿名访客（提权情报泄露）。
2. ``GET /users/{user_id}`` 不做 ``show_email`` 遮蔽：同一份数据换个路由就绕过隐私开关；
   且"没有偏好行"必须按默认值 False 处理，否则注册后没动过设置的用户一律泄露邮箱。
3. 文章详情缓存此前只写不读，改为可读后必须钉住读写口径一致：
   只有匿名 + 按 slug + 非加密文章才允许命中/写入，且删除文章要立刻失效。
4. 服务层的偏好可写字段白名单与二级缓存的失效键族：
   ``update_preferences`` 曾只放行 ``theme`` / ``public_profile``，其余隐私开关被静默
   丢弃；``invalidate_user_cache`` 曾只删 ``user:<id>*``，漏掉 ``user_profile`` 键族。
5. 启动预热曾写入 ``categories:<lang>`` / ``tags:<lang>`` / ``hot_posts:<lang>`` 这类
   读侧根本不看的键，且 ``warmup_cache()`` 从未被 lifespan 调用——预热指标报"预热 N 项"，
   实际一次都没命中过。现在键/形态与读侧同源，并有下面的端到端契约钉住。
"""

from __future__ import annotations

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.cache import cache, make_cache_key
from backend.models.activity import Activity
from backend.models.blog import Category, Comment, Post, Tag
from backend.models.user import User
from backend.services.cache_service import CacheService

# 这些字段只应出现在后台/本人接口，绝不允许出现在公开 author 里
PRIVATE_USER_FIELDS = {
    "email",
    "qq",
    "is_active",
    "is_staff",
    "is_superuser",
    "role",
    "last_login",
}


def _payload(body: dict) -> dict:
    """兼容统一响应封装：取出真正的业务负载。"""
    if isinstance(body, dict) and "data" in body and "success" in body:
        return body["data"] or {}
    return body or {}


class TestPublicAuthorContract:
    """公开资源的 author 字段不得携带私密/提权字段"""

    @pytest.mark.asyncio
    async def test_post_detail_author_excludes_private_fields(
        self, client: AsyncClient, test_post: Post
    ):
        response = await client.get(f"/api/blog/posts/{test_post.slug}", params={"lang": "zh"})
        assert response.status_code == 200
        author = _payload(response.json())["author"]
        assert set(author) & PRIVATE_USER_FIELDS == set()
        # 公开卡片仍要能渲染作者身份，别把必要字段一起砍掉
        assert author["username"] == "testuser"
        assert "avatar" in author and "created_at" in author

    @pytest.mark.asyncio
    async def test_post_list_author_excludes_private_fields(
        self, client: AsyncClient, test_post: Post
    ):
        response = await client.get("/api/blog/posts", params={"page_size": 10})
        assert response.status_code == 200
        items = _payload(response.json())["items"]
        assert items, "列表应有数据，否则本用例形同空断言"
        for item in items:
            assert set(item["author"]) & PRIVATE_USER_FIELDS == set()

    @pytest.mark.asyncio
    async def test_activity_author_excludes_private_fields(
        self, client: AsyncClient, test_user: User, db_session: AsyncSession
    ):
        db_session.add(
            Activity(
                content={"zh": "发布了一条动态", "en": "posted an update"},
                type="say",
                author_id=test_user.id,
                is_published=True,
            )
        )
        await db_session.commit()

        response = await client.get("/api/activities", params={"page_size": 10})
        assert response.status_code == 200
        items = _payload(response.json())["items"]
        assert items
        for item in items:
            assert set(item["author"]) & PRIVATE_USER_FIELDS == set()

    @pytest.mark.asyncio
    async def test_openapi_author_schema_is_public_model(self, client: AsyncClient):
        """OpenAPI 层面也必须引用 PublicUserResponse——防止有人把字段加回 UserResponse。"""
        response = await client.get("/openapi.json")
        assert response.status_code == 200
        schema = response.json()["components"]["schemas"]["PostLocalizedResponse"]
        ref = schema["properties"]["author"]["$ref"]
        assert ref.endswith("/PublicUserResponse")
        public = response.json()["components"]["schemas"]["PublicUserResponse"]
        assert set(public["properties"]) & PRIVATE_USER_FIELDS == set()


class TestEmailPrivacy:
    """show_email 开关在两个公开路由上口径一致，且默认拒绝"""

    @pytest.mark.asyncio
    async def test_user_without_preference_row_masks_email(
        self, client: AsyncClient, test_user: User
    ):
        """没有偏好行 == 没开过开关：按模型默认 show_email=False 处理"""
        by_id = await client.get(f"/api/users/{test_user.id}")
        by_name = await client.get(f"/api/users/username/{test_user.username}")
        assert by_id.status_code == 200 and by_name.status_code == 200
        assert _payload(by_id.json())["email"] == "***"
        assert _payload(by_name.json())["email"] == "***"

    @pytest.mark.asyncio
    async def test_explicit_opt_in_shows_email_on_both_routes(
        self, client: AsyncClient, test_user: User, auth_headers: dict
    ):
        """开开关必须走真实的 PUT 接口：只有它带 ``invalidate_user_cache``。

        直接往库里插一行 ``UserPreference`` 会绕开服务层的缓存失效，测出来的是
        "缓存没清时旧值还在"——那是正确行为，不是我们要钉的契约。
        """
        put = await client.put(
            "/api/users/me/preferences", json={"show_email": True}, headers=auth_headers
        )
        assert put.status_code == 200

        by_id = await client.get(f"/api/users/{test_user.id}")
        by_name = await client.get(f"/api/users/username/{test_user.username}")
        assert _payload(by_id.json())["email"] == "test@example.com"
        assert _payload(by_name.json())["email"] == "test@example.com"

    @pytest.mark.asyncio
    async def test_all_privacy_toggles_are_persisted(self, client: AsyncClient, auth_headers: dict):
        """服务层的可写白名单必须覆盖 Schema 声明的每个开关。

        旧实现只放行 ``theme`` / ``public_profile``，其余四个隐私开关从 API 传进来
        被静默丢掉：接口 200、响应里却仍是旧值。
        """
        payload = {
            "show_email": True,
            "show_posts": False,
            "show_comments": False,
            "show_stats": False,
        }
        put = await client.put("/api/users/me/preferences", json=payload, headers=auth_headers)
        assert put.status_code == 200
        saved = _payload(put.json())
        for key, value in payload.items():
            assert saved[key] == value, f"{key} 未落库：服务层白名单又漏字段了"

        again = await client.get("/api/users/me/preferences", headers=auth_headers)
        reread = _payload(again.json())
        for key, value in payload.items():
            assert reread[key] == value, f"{key} 重新读取时丢失"

    @pytest.mark.asyncio
    async def test_self_still_sees_own_email(
        self, client: AsyncClient, test_user: User, auth_headers: dict
    ):
        response = await client.get(f"/api/users/{test_user.id}", headers=auth_headers)
        assert response.status_code == 200
        assert _payload(response.json())["email"] == "test@example.com"


class TestPostDetailCache:
    """详情缓存读写口径：匿名 + slug + 公开文章，且计数保持实时"""

    @pytest.mark.asyncio
    async def test_anonymous_visit_populates_cache_and_serves_second_hit(
        self, client: AsyncClient, test_post: Post, db_session: AsyncSession
    ):
        cache_key = make_cache_key("post", test_post.slug, "zh")
        await cache.clear()

        first = await client.get(f"/api/blog/posts/{test_post.slug}", params={"lang": "zh"})
        assert first.status_code == 200
        assert await cache.get(cache_key) is not None, "匿名公开文章应写入详情缓存"

        # 绕开缓存直接改库：第二次请求若命中缓存，标题必然仍是旧值。
        # 改的是 ORM 实例而非裸 UPDATE——路由与用例共用同一个 AsyncSession
        # （conftest 的 get_db override）且 expire_on_commit=False，
        # 用 Core update 会让 identity map 留着旧值，"缓存生效"退化成恒真断言。
        db_session.add(
            Comment(
                post_id=test_post.id,
                user_id=test_post.author_id,
                parent_id=None,
                author_name="评论者",
                author_email="c@example.com",
                content="缓存期间的实时计数来源",
                status="approved",
                active=True,
            )
        )
        test_post.title = {"zh": "改后的标题", "en": "renamed"}
        await db_session.commit()

        second = await client.get(f"/api/blog/posts/{test_post.slug}", params={"lang": "zh"})
        data = _payload(second.json())
        assert data["title"] == "测试文章", "命中缓存不应回源重算渲染管线"
        assert data["comments_count"] == 1, "计数必须实时，不能吃缓存快照"

    @pytest.mark.asyncio
    async def test_logged_in_view_never_writes_cache(
        self, client: AsyncClient, test_post: Post, auth_headers: dict
    ):
        await cache.clear()
        response = await client.get(
            f"/api/blog/posts/{test_post.slug}", params={"lang": "zh"}, headers=auth_headers
        )
        assert response.status_code == 200
        assert await cache.get(make_cache_key("post", test_post.slug, "zh")) is None

    @pytest.mark.asyncio
    async def test_password_protected_post_is_not_cached(
        self, client: AsyncClient, test_post: Post, db_session: AsyncSession
    ):
        """加密文章的读侧门禁：匿名请求既不能拿到正文，也不能把任何版本写进共享键。"""
        test_post.password = "not-a-valid-hash"  # 非 bcrypt 串，验证必然失败
        await db_session.commit()
        await cache.clear()

        response = await client.get(f"/api/blog/posts/{test_post.slug}", params={"lang": "zh"})
        assert response.status_code == 200
        data = _payload(response.json())
        assert data["is_password_protected"] is True
        assert not data["content"], "未授权时不得返回正文"
        assert await cache.get(make_cache_key("post", test_post.slug, "zh")) is None

    @pytest.mark.asyncio
    async def test_delete_post_invalidates_detail_cache(
        self,
        client: AsyncClient,
        admin_headers: dict,
        test_post: Post,
    ):
        """删除后详情键必须立刻消失，否则 600s 内匿名访客还能读到已删文章正文。"""
        await client.get(f"/api/blog/posts/{test_post.slug}", params={"lang": "zh"})
        assert await cache.get(make_cache_key("post", test_post.slug, "zh")) is not None

        response = await client.delete(f"/api/blog/posts/{test_post.id}", headers=admin_headers)
        assert response.status_code == 200
        assert await cache.get(make_cache_key("post", test_post.slug, "zh")) is None

        gone = await client.get(f"/api/blog/posts/{test_post.slug}")
        assert gone.status_code == 404


class TestUserCacheInvalidation:
    """``invalidate_user_cache`` 必须覆盖读侧全部三族键"""

    @pytest.mark.asyncio
    @pytest.mark.parametrize("prefix", ["user", "user_profile", "user_stats"])
    async def test_each_user_key_family_is_removed(self, prefix: str):
        """旧实现只删 ``user:<id>*`` 前缀，``user_profile`` 与 ``user_stats`` 漏网。

        表现：用户改完资料/开关后，公开页最长 300s 仍返回旧值。
        """
        service = CacheService()
        key = service.build_key(prefix, 4242)
        await service.set(key, {"marker": "stale"}, ttl=60)
        assert await service.get(key) is not None, "写入本身应生效（无 Redis 时走本地层）"

        assert await service.invalidate_user_cache(4242) >= 1
        assert await service.get(key) is None


class TestCommentReplyVisibility:
    """reply_total 只能统计"看的人有权看到"的回复"""

    @staticmethod
    async def _seed(db_session: AsyncSession, post: Post, author: User) -> Comment:
        root = Comment(
            post_id=post.id,
            user_id=author.id,
            parent_id=None,
            author_name=author.nickname,
            author_email=author.email,
            content="顶层评论",
            status="approved",
            active=True,
        )
        db_session.add(root)
        await db_session.flush()

        for i, status in enumerate(["approved", "approved", "approved", "pending", "rejected"]):
            db_session.add(
                Comment(
                    post_id=post.id,
                    user_id=None,
                    parent_id=root.id,
                    author_name=f"回复者{i}",
                    author_email=f"r{i}@example.com",
                    content=f"第 {i} 条回复 status={status}",
                    status=status,
                    active=(status == "approved"),
                )
            )
        await db_session.commit()
        await db_session.refresh(root)
        return root

    @pytest.mark.asyncio
    async def test_anonymous_reply_total_counts_only_approved(
        self, client: AsyncClient, test_post: Post, test_user: User, db_session: AsyncSession
    ):
        root = await self._seed(db_session, test_post, test_user)

        response = await client.get(f"/api/posts/{test_post.slug}/comments")
        assert response.status_code == 200
        items = _payload(response.json())["items"]
        target = next(item for item in items if item["id"] == root.id)
        assert target["reply_total"] == 3, "待审/驳回的回复不能计入公开计数"
        assert len(target["replies"]) == 3
        assert all(r["status"] != "pending" for r in target["replies"])


class TestCacheWarmerMatchesReader:
    """启动预热的键与载荷形态必须与读侧同源，否则预热永远打空。"""

    @pytest.mark.asyncio
    async def test_warmed_categories_are_consumed_by_endpoint(
        self, client: AsyncClient, test_category: Category
    ):
        from backend.core.cache import CACHE_KEY_CATEGORIES
        from backend.core.cache_warmer import cache_warmer

        assert await cache_warmer._warmup_categories() == 1
        warmed = await cache.get(CACHE_KEY_CATEGORIES)
        assert warmed, "预热写到了读侧不看的键（或形态不符）"

        response = await client.get("/api/blog/categories")
        assert response.status_code == 200
        # 端点必须直接命中预热结果：内容逐字段相等，而不是"都能返回 200"
        assert _payload(response.json()) == warmed

        # 再钉住"形态"：清掉缓存做冷读，结果必须与预热载荷逐字段一致。
        # 只比"命中缓存后返回什么"是空断言——读侧会把预热结果原样吐回来。
        await cache.clear()
        cold = _payload((await client.get("/api/blog/categories")).json())
        assert cold == warmed

    @pytest.mark.asyncio
    async def test_warmed_tags_are_consumed_by_endpoint(self, client: AsyncClient, test_tag: Tag):
        from backend.core.cache import CACHE_KEY_TAGS
        from backend.core.cache_warmer import cache_warmer

        assert await cache_warmer._warmup_tags() == 1
        warmed = await cache.get(CACHE_KEY_TAGS)
        assert warmed, "预热写到了读侧不看的键（或形态不符）"

        response = await client.get("/api/blog/tags")
        assert response.status_code == 200
        assert _payload(response.json()) == warmed

        await cache.clear()
        cold = _payload((await client.get("/api/blog/tags")).json())
        assert cold == warmed

    @pytest.mark.asyncio
    async def test_warmed_site_config_carries_group_overlay(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        """预热写入的 site_config 必须是 /api/config 权威口径（扁平键 → 分组 JSON 覆写）。

        历史缺陷：预热复刻了一套只认大写扁平键的手工拼装——既没有分组覆写也读不到
        小写键行，冷启动即把默认站点名毒进缓存，改站点名要等 TTL 到期才生效，
        RSS/前台/OG 与后台设置口径分裂。"""
        import json as _json

        from backend.core.cache_warmer import cache_warmer
        from backend.models.core import SiteConfig

        db_session.add(
            SiteConfig(
                key="basic",
                value=_json.dumps(
                    {"site_name": "预热权威名", "site_url": "https://warm.example.com"}
                ),
            )
        )
        await db_session.commit()
        await cache.clear()

        assert await cache_warmer._warmup_site_config() == 1
        warmed = await cache.get(make_cache_key("site_config"))
        assert isinstance(warmed, dict), "预热没有写到读侧看的 site_config 键"
        assert warmed["site_name"] == "预热权威名"
        assert warmed["site_url"] == "https://warm.example.com"

        # 读侧命中预热结果：/api/config 返回的必须就是这份权威载荷
        cfg = (await client.get("/api/config")).json()
        assert cfg["site_name"] == "预热权威名"
        assert cfg["site_url"] == "https://warm.example.com"

    @pytest.mark.asyncio
    async def test_warmed_navigations_match_reader_shape(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        """预热导航载荷必须与 GET /blog/navigations 冷读逐字段一致。

        读侧命中缓存是原样透传（不再过 NavigationResponse）——预热侧手写 dict
        少一个键（如 icon/parent_id），冷启动后菜单图标就凭空消失。"""
        from backend.core.cache_warmer import cache_warmer
        from backend.models.core import Navigation

        db_session.add(
            Navigation(
                title={"zh": "首页", "en": "Home", "ja": "ホーム", "zh_Hant": "首頁"},
                url="/",
                icon="house",
                location="header",
                order=1,
                is_active=True,
            )
        )
        await db_session.commit()
        await cache.clear()

        assert await cache_warmer._warmup_navigations() == 4
        warmed = await cache.get(make_cache_key("navigations", "header"))
        assert warmed and warmed[0]["icon"] == "house", "预热载荷丢字段"

        hot = _payload(
            (await client.get("/api/navigations", params={"location": "header"})).json()
        )
        assert hot == warmed

        await cache.clear()
        cold = _payload(
            (await client.get("/api/navigations", params={"location": "header"})).json()
        )
        assert cold == warmed

    @pytest.mark.asyncio
    async def test_warmed_friend_links_match_reader_shape(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        """预热友链载荷必须与 GET /friend-links 冷读逐字段一致（含必填 status）。"""
        from backend.core.cache_warmer import cache_warmer
        from backend.models.core import FriendLink

        db_session.add(
            FriendLink(
                name={"zh": "友站", "en": "Friend", "ja": "フレンド", "zh_Hant": "友站"},
                url="https://friend.example.com",
                description=None,
                logo="",
                order=1,
                status="approved",
                is_active=True,
            )
        )
        await db_session.commit()
        await cache.clear()

        assert await cache_warmer._warmup_friend_links() == 2
        warmed = await cache.get(make_cache_key("friend_links", "active"))
        assert warmed and "status" in warmed[0], "预热载荷丢字段"

        hot = _payload((await client.get("/api/friend-links")).json())
        assert hot == warmed

        await cache.clear()
        cold = _payload((await client.get("/api/friend-links")).json())
        assert cold == warmed
