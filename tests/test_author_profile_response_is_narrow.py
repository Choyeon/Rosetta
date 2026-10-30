"""第三方作者资料口字段收窄（``AuthorProfileResponse``）的回归测试。

线上实测（2026-10-30）匿名 ``GET /api/users/username/<作者>`` 原样回显该作者的**真实 QQ 号**、
``is_superuser: true``、``role: "super_admin"`` 与 ``last_login``——这两条口一直直接
回宽 ``UserResponse``，于是"文章卡片（``PublicUserResponse``）不发的字段，换个路由照样
摊给匿名爬虫"。这比邮箱/社交链接那一族更重：QQ 是直接可联系的个人信息，角色等于替撞库
与定向钓鱼标出管理员账号，``last_login`` 还会告诉外界这个账号何时活动过。

修法选**结构性收窄**（新模型 ``AuthorProfileResponse`` 继承 ``PublicUserResponse``）而不是
逐字段置 null：``is_active`` / ``is_staff`` 在模型里是**非空 bool**，置 null 要么 500 要么
撒谎（"这个账号没激活"），而"干脆不发"既不会 500 也不会给出假值。

钉四件事：
1. 两条口在**任何**访客（匿名 / 登录陌生人 / 本人 / staff）下键集都恰好是那份窄投影；
2. 收窄没顺手砍掉**有消费方**的字段——前台 ``AuthorProfile`` 接口声明的键必须仍在；
3. 隐私开关照旧生效（``email`` 默认遮蔽、``website`` / ``github`` 跟着 ``show_social_links``）；
4. 需要这些字段的口没被误伤：``/users/me`` 与 ``/admin/users/{id}`` 仍回 qq 与角色。
"""

from __future__ import annotations

import re
from datetime import datetime, timedelta
from pathlib import Path

import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.auth import create_access_token, get_password_hash
from backend.main import app
from backend.models.user import User
from backend.schemas import AuthorProfileResponse
from backend.utils.compat import UTC

# 账号隐私与权限信息：这两条第三人公开口一条都不该发（AGENTS §12 / PublicUserResponse 文档早已判明）
LEAKY_FIELDS = frozenset({"qq", "is_active", "is_staff", "is_superuser", "role", "last_login"})

# 第三人作者资料**应当**有的键集。写成硬清单而不是从模型反推——从模型反推等于让
# "往 AuthorProfileResponse 里加字段"这个动作自己给自己盖章通过。
NARROW_KEYS = frozenset(
    {
        "id",
        "username",
        "nickname",
        "bio",
        "avatar",
        "cover_image",
        "avatar_source",
        "resolved_avatar_url",
        "title",
        "created_at",
        "email",
        "website",
        "github",
    }
)

AUTHORS_PAGE = (
    Path(__file__).resolve().parents[1] / "frontend" / "pages" / "authors" / "[username].vue"
)


@pytest_asyncio.fixture
async def privileged_author(db_session: AsyncSession) -> User:
    """一个库里**确实**装着 QQ / 超管位 / 最近登录时间的作者。

    没有这个前提，"响应里没有 qq"会因为源数据本来就是 None 而恒真（假绿）。
    """
    user = User(
        username="probeleakauthor",
        email="probeleakauthor@example.invalid",
        password_hash=get_password_hash("Probe@12345"),
        nickname="带敏感字段的作者",
        bio="测试资料",
        website="https://probe-leak.example",
        github="https://github.com/probe-leak",
        is_active=True,
        is_staff=True,
        is_superuser=True,
        role="super_admin",
        qq="100099999",
    )
    user.last_login = datetime.now(UTC) - timedelta(hours=3)
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


def _urls(user: User) -> list[str]:
    return [f"/api/users/{user.id}", f"/api/users/username/{user.username}"]


class TestThirdPersonProfileIsNarrow:
    @pytest.mark.asyncio
    @pytest.mark.parametrize("visitor", ["anon", "stranger", "self", "staff"])
    async def test_keyset_is_exactly_the_narrow_projection(
        self,
        client: AsyncClient,
        privileged_author: User,
        subscriber_headers: dict,
        admin_headers: dict,
        visitor: str,
    ):
        """每一种访客都只拿到那份窄投影（本人也不例外——看自己要什么字段走 /users/me）。"""
        if visitor == "self":
            token = create_access_token(
                {"sub": str(privileged_author.id), "type": "access"},
                expires_delta=timedelta(minutes=5),
            )
            headers = {"Authorization": f"Bearer {token}"}
        elif visitor == "staff":
            headers = admin_headers
        else:
            headers = subscriber_headers if visitor == "stranger" else None

        for url in _urls(privileged_author):
            resp = await client.get(url, headers=headers)
            assert resp.status_code == 200, f"{visitor} {url}: {resp.text}"
            body = resp.json()
            assert frozenset(body) == NARROW_KEYS, f"{visitor} {url} 键集漂移：{sorted(body)}"

    @pytest.mark.asyncio
    async def test_account_metadata_is_not_emitted_even_though_db_has_it(
        self, client: AsyncClient, privileged_author: User, admin_headers: dict
    ):
        """反向前提：源数据真的有值，响应里连键都不存在（不是 null、更不是原值）。"""
        detail = await client.get(f"/api/admin/users/{privileged_author.id}", headers=admin_headers)
        assert detail.status_code == 200
        admin_body = detail.json()
        for field in LEAKY_FIELDS:
            assert admin_body.get(field) not in (None, ""), f"前提破了：{field} 在库里是空的"

        for url in _urls(privileged_author):
            body = (await client.get(url)).json()
            leaked = LEAKY_FIELDS & frozenset(body)
            assert not leaked, f"{url} 仍向匿名访客摊出 {sorted(leaked)}"

    @pytest.mark.asyncio
    async def test_model_declares_no_privilege_fields(self):
        """结构性闸门：字段压根不在模型上，加一行就会红。"""
        assert LEAKY_FIELDS.isdisjoint(AuthorProfileResponse.model_fields)
        assert set(AuthorProfileResponse.model_fields) == NARROW_KEYS

    @pytest.mark.asyncio
    async def test_email_and_social_privacy_still_apply(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        privileged_author: User,
    ):
        """收窄不是把隐私开关整套换掉：email 仍默认拒绝，社交链接仍跟着 show_social_links。"""
        for url in _urls(privileged_author):
            body = (await client.get(url)).json()
            assert body["email"] == "***", f"{url} 的邮箱遮蔽没了"
            assert body["website"] == "https://probe-leak.example"
            assert body["github"] == "https://github.com/probe-leak"

        # 关掉开关后两条第三人口一起收起（服务层写路径会清 user_profile 缓存）
        from backend.services.user_service import get_user_service

        service = await get_user_service(db_session)
        await service.update_preferences(privileged_author.id, {"show_social_links": False})
        await db_session.commit()

        for url in _urls(privileged_author):
            body = (await client.get(url)).json()
            assert body["website"] is None and body["github"] is None, f"{url} 绕过了社交开关"
            assert body["nickname"] == "带敏感字段的作者", "遮蔽时把整份资料一起清空了"


class TestConsumersAndDocContract:
    @pytest.mark.asyncio
    async def test_frontend_author_profile_interface_keys_are_still_emitted(self):
        """前台 ``AuthorProfile`` 接口声明的键必须仍在这份投影里。

        收窄做成"顺手少发一个字段"的代价是作者主页静默降级（头像没了、称号没了），
        而不是报错——所以这条要按页面源码里的真实接口对账，不能凭记忆写清单。
        """
        source = AUTHORS_PAGE.read_text(encoding="utf-8")
        match = re.search(r"interface AuthorProfile \{(?P<body>.*?)\n\}", source, re.S)
        assert match, "作者主页的 AuthorProfile 接口结构变了，请同步本守卫"
        declared = frozenset(re.findall(r"^\s*(\w+)\??\s*:", match.group("body"), re.M))
        assert declared, "没解析到任何字段，守卫本身坏了"
        missing = declared - NARROW_KEYS
        assert not missing, f"页面声明了投影不再发出的字段：{sorted(missing)}"

    def test_openapi_uses_the_narrow_model_on_both_profile_routes(self):
        """文档面同步：两条第三人口指向 AuthorProfileResponse，/users/me 仍是宽 UserResponse。"""
        paths = app.openapi()["paths"]
        for path in ("/api/users/{user_id}", "/api/users/username/{username}"):
            schema = paths[path]["get"]["responses"]["200"]["content"]["application/json"]["schema"]
            assert schema["$ref"].endswith("AuthorProfileResponse"), f"{path} -> {schema}"
        me_schema = paths["/api/users/me"]["get"]["responses"]["200"]["content"][
            "application/json"
        ]["schema"]
        assert me_schema["$ref"].endswith("UserResponse")

    @pytest.mark.asyncio
    async def test_self_route_still_returns_account_metadata(
        self, client: AsyncClient, privileged_author: User
    ):
        """本人口（/users/me）不受影响——收窄只针对"第三人 + 匿名可读"。"""
        token = create_access_token(
            {"sub": str(privileged_author.id), "type": "access"},
            expires_delta=timedelta(minutes=5),
        )
        body = (
            await client.get("/api/users/me", headers={"Authorization": f"Bearer {token}"})
        ).json()
        assert body["qq"] == "100099999"
        assert body["role"] == "super_admin"
        assert body["is_superuser"] is True
