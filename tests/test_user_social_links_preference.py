"""`show_social_links`（第六个隐私开关）读写与强制点的回归测试。

`UserPreference.show_social_links` 曾是一列僵尸：模型有列、迁移有列，但写口
（`UserPreferenceUpdate`）、读口（本人偏好口 + 匿名 6 键组）、遮蔽点和消费方
（作者主页的网站 / GitHub 行）全都没有它——用户页面上没有这个开关，开关关掉后
访客照样能翻出他的网站和 GitHub。

按 `show_email` 一族的既有口径钉四段：写口 → 存储 → 响应 → 强制点。
另外钉住这一位与邮箱**相反的默认**（建表默认 True，所以"没有偏好行"必须按展示处理，
把它做成默认拒绝等于凭空禁掉全站社交链接），以及"换个路由就绕过"的旁路：
第三人作者卡片（`PublicUserResponse` / `blog._build_author_data`）不再携带
website / github——全站没有任何消费方渲染作者卡片上的这两个字段，留着它们只是
给遮蔽开关留一条绕过路径。
"""

from __future__ import annotations

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.main import app
from backend.models.user import User, UserPreference

PUBLIC_SWITCH_KEYS = {
    "public_profile",
    "show_email",
    "show_posts",
    "show_comments",
    "show_stats",
    "show_social_links",
}

WEBSITE_URL = "https://choyeon.test"
GITHUB_URL = "https://github.com/choyeon"


def _payload(body: dict) -> dict:
    if isinstance(body, dict) and "data" in body and "success" in body:
        return body["data"] or {}
    return body or {}


async def _set_social_profile(db_session: AsyncSession, user: User) -> None:
    """给作者装上真实的网站 / GitHub（遮蔽断言的前提，否则 None == None 恒真）。

    GitHub 用完整主页 URL：模型注释「GitHub 主页」、后台表单 placeholder
    `github.com/username`、写入侧 `_normalize_optional_url` 补 scheme 三点同口径，
    作者主页也因此把这一列**直接当 href 用**（契约见
    `frontend/tests/unit/authorSocialLinks.spec.ts`）。
    """
    user.website = WEBSITE_URL
    user.github = GITHUB_URL
    await db_session.commit()


async def _preference_row(db_session: AsyncSession, user_id: int) -> UserPreference | None:
    return (
        await db_session.execute(select(UserPreference).where(UserPreference.user_id == user_id))
    ).scalar_one_or_none()


class TestWriteAndReadRoundTrip:
    @pytest.mark.asyncio
    async def test_put_persists_the_switch_instead_of_echoing_it(
        self, client: AsyncClient, auth_headers: dict, test_user: User, db_session: AsyncSession
    ):
        """接口 200 + 响应回显不够：必须核对库里的行真的改了。"""
        resp = await client.put(
            "/api/users/me/preferences", headers=auth_headers, json={"show_social_links": False}
        )
        assert resp.status_code == 200, resp.text
        assert _payload(resp.json())["show_social_links"] is False

        row = await _preference_row(db_session, test_user.id)
        assert row is not None, "写口没有创建偏好行"
        assert row.show_social_links is False, "服务层白名单又漏了这一列"

    @pytest.mark.asyncio
    async def test_omitting_it_leaves_the_row_untouched(
        self, client: AsyncClient, auth_headers: dict, test_user: User, db_session: AsyncSession
    ):
        """`exclude_unset`：动别的开关不能把这一位重置回默认值。"""
        await client.put(
            "/api/users/me/preferences", headers=auth_headers, json={"show_social_links": False}
        )
        resp = await client.put(
            "/api/users/me/preferences", headers=auth_headers, json={"show_posts": False}
        )
        assert resp.status_code == 200, resp.text
        assert resp.json()["show_social_links"] is False
        row = await _preference_row(db_session, test_user.id)
        assert row is not None and row.show_social_links is False

    @pytest.mark.asyncio
    async def test_get_my_preferences_projects_it(self, client: AsyncClient, auth_headers: dict):
        await client.put(
            "/api/users/me/preferences", headers=auth_headers, json={"show_social_links": False}
        )
        resp = await client.get("/api/users/me/preferences", headers=auth_headers)
        assert resp.status_code == 200
        assert _payload(resp.json())["show_social_links"] is False


class TestAnonymousPreferenceProjection:
    @pytest.mark.asyncio
    async def test_public_preferences_carries_six_switches(
        self, client: AsyncClient, test_user: User
    ):
        resp = await client.get(f"/api/users/username/{test_user.username}/preferences")
        assert resp.status_code == 200, resp.text
        assert set(resp.json()) == PUBLIC_SWITCH_KEYS

    @pytest.mark.asyncio
    async def test_missing_row_defaults_to_showing_links(
        self, client: AsyncClient, test_user: User
    ):
        """建表默认 True ⇒ "从没动过设置"必须等同"展示社交链接"。

        按 show_email 那样做成默认拒绝，等于给全站用户凭空禁掉网站 / GitHub。
        """
        resp = await client.get(f"/api/users/username/{test_user.username}/preferences")
        assert resp.status_code == 200
        assert resp.json()["show_social_links"] is True

    def test_openapi_doc_declares_it(self):
        """响应体文档必须与裸 dict 的字段清单同数（文档缺口由 baseline 守卫挡，形态漂移靠这条）。"""
        schema = app.openapi()["components"]["schemas"]["UserPreferencesPublicDoc"]
        assert set(schema["properties"]) == PUBLIC_SWITCH_KEYS


class TestMaskingOnProfileEndpoints:
    """资料口的遮蔽：两个路由都得管，漏一个就等于开关形同虚设（邮箱的同型缺陷）。"""

    @pytest.mark.asyncio
    @pytest.mark.parametrize("path_prefix", ["/api/users/username", "/api/users"])
    async def test_anonymous_sees_links_when_on(
        self,
        client: AsyncClient,
        test_user: User,
        db_session: AsyncSession,
        path_prefix: str,
    ):
        await _set_social_profile(db_session, test_user)
        target = (
            f"{path_prefix}/{test_user.username}"
            if path_prefix.endswith("username")
            else f"{path_prefix}/{test_user.id}"
        )
        resp = await client.get(target)
        assert resp.status_code == 200, resp.text
        body = _payload(resp.json())
        assert body["website"] == WEBSITE_URL
        assert body["github"] == GITHUB_URL

    @pytest.mark.asyncio
    @pytest.mark.parametrize("path_prefix", ["/api/users/username", "/api/users"])
    async def test_anonymous_sees_nothing_when_off(
        self,
        client: AsyncClient,
        test_user: User,
        auth_headers: dict,
        db_session: AsyncSession,
        path_prefix: str,
    ):
        await _set_social_profile(db_session, test_user)
        put = await client.put(
            "/api/users/me/preferences", headers=auth_headers, json={"show_social_links": False}
        )
        assert put.status_code == 200, put.text

        target = (
            f"{path_prefix}/{test_user.username}"
            if path_prefix.endswith("username")
            else f"{path_prefix}/{test_user.id}"
        )
        resp = await client.get(target)
        assert resp.status_code == 200, resp.text
        body = _payload(resp.json())
        assert body["website"] is None
        assert body["github"] is None
        # 关掉这一位不等于关掉整个主页：昵称与文章列表仍在
        assert body["nickname"] == test_user.nickname

    @pytest.mark.asyncio
    async def test_self_still_sees_own_links(
        self, client: AsyncClient, test_user: User, auth_headers: dict, db_session: AsyncSession
    ):
        await _set_social_profile(db_session, test_user)
        await client.put(
            "/api/users/me/preferences", headers=auth_headers, json={"show_social_links": False}
        )
        resp = await client.get(f"/api/users/{test_user.id}", headers=auth_headers)
        assert resp.status_code == 200
        body = _payload(resp.json())
        assert body["website"] == WEBSITE_URL, "本人读自己的资料不该被遮蔽"

    @pytest.mark.asyncio
    async def test_staff_sees_the_links(
        self,
        client: AsyncClient,
        test_user: User,
        staff_headers: dict,
        db_session: AsyncSession,
    ):
        """后台需要联系用户 / 核实身份，豁免口径与 show_email 一致。

        这里直接插偏好行而不是走 PUT：PUT 改的是**当前登录者**（staff）自己的偏好，
        而这一条要钉的是"作者关了开关、staff 仍能读出真值"。
        """
        await _set_social_profile(db_session, test_user)
        db_session.add(
            UserPreference(user_id=test_user.id, public_profile=True, show_social_links=False)
        )
        await db_session.commit()

        anon = await client.get(f"/api/users/username/{test_user.username}")
        assert _payload(anon.json())["website"] is None, "插行后匿名口应已遮蔽（本条前提）"

        resp = await client.get(f"/api/users/username/{test_user.username}", headers=staff_headers)
        assert resp.status_code == 200, resp.text
        assert _payload(resp.json())["website"] == WEBSITE_URL


class TestThirdPersonCardCarriesNoSocialFields:
    """作者卡片根本不带这两个字段——比"带着但按开关置 null"更稳，因为少一处能绕过的读口。"""

    @pytest.mark.asyncio
    async def test_post_detail_author_has_no_social_keys(
        self, client: AsyncClient, test_post, test_user: User, db_session: AsyncSession
    ):
        """作者行**带着**真实值时卡片仍不带这两个键——证的是投影，不是数据恰好为空。"""
        await _set_social_profile(db_session, test_user)
        resp = await client.get(f"/api/blog/posts/{test_post.slug}", params={"lang": "zh"})
        assert resp.status_code == 200
        author = _payload(resp.json())["author"]
        assert author["username"] == test_user.username, "卡片还是那位作者，只是不带社交链接"
        assert "website" not in author
        assert "github" not in author

    @pytest.mark.asyncio
    async def test_post_list_author_has_no_social_keys(self, client: AsyncClient, test_post):
        resp = await client.get("/api/blog/posts", params={"page_size": 10})
        assert resp.status_code == 200
        items = _payload(resp.json())["items"]
        assert items, "列表应有数据，否则本用例形同空断言"
        for item in items:
            assert "website" not in item["author"]
            assert "github" not in item["author"]

    def test_openapi_public_user_excludes_social_fields(self):
        props = app.openapi()["components"]["schemas"]["PublicUserResponse"]["properties"]
        assert "website" not in props
        assert "github" not in props


class TestPageCacheIsPurged:
    """关掉开关后，已经烘进 swr 缓存的那份 `/authors/<u>` HTML 必须被通知重渲染。

    响应层的置 null 管不到缓存里的旧页面（swr 600s + stale 窗口），所以写口要自己 purge。
    """

    @pytest.mark.asyncio
    async def test_switch_off_purges_frontend_page_only(
        self,
        client: AsyncClient,
        auth_headers: dict,
        monkeypatch: pytest.MonkeyPatch,
    ):
        import backend.services.user_service as us

        purged: list[str] = []
        monkeypatch.setattr(us, "purge_frontend_page_cache", lambda reason: purged.append(reason))
        invalidated: list[int] = []

        async def _spy(_self, user_id: int) -> None:
            invalidated.append(user_id)

        monkeypatch.setattr(us.UserService, "_invalidate_author_post_caches", _spy, raising=True)

        resp = await client.put(
            "/api/users/me/preferences", headers=auth_headers, json={"show_social_links": False}
        )
        assert resp.status_code == 200, resp.text
        assert purged, "改了 SSR 可见内容却没有清前端页面缓存 = 旧链接在 TTL 内继续公开"
        assert invalidated == [], "这一位不影响文章列表可见性，不该连带清文章缓存"

    @pytest.mark.asyncio
    async def test_archive_switch_still_purges_and_invalidates(
        self,
        client: AsyncClient,
        auth_headers: dict,
        monkeypatch: pytest.MonkeyPatch,
    ):
        """回归护栏：新增分支不能把 show_posts / public_profile 原来那套动作改掉。"""
        import backend.services.user_service as us

        purged: list[str] = []
        monkeypatch.setattr(us, "purge_frontend_page_cache", lambda reason: purged.append(reason))
        invalidated: list[int] = []

        async def _spy(_self, user_id: int) -> None:
            invalidated.append(user_id)

        monkeypatch.setattr(us.UserService, "_invalidate_author_post_caches", _spy, raising=True)

        resp = await client.put(
            "/api/users/me/preferences", headers=auth_headers, json={"show_posts": False}
        )
        assert resp.status_code == 200, resp.text
        assert len(invalidated) == 1
        assert purged
