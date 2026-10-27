"""文章密码提示（``encryption_hint``）读写两端的回归测试。

这一族此前的形状是"半接通"：列在 ``Post`` 上、``PostCreate``/``PostUpdate`` 都收这个键、
前台闸门页 ``pages/posts/[slug].vue`` 也在读 ``detail.encryption_hint``，
但**详情响应模型不带这个键**，编辑器表单也从不发送——于是锁屏上的提示永远不会出现，
后台多一个"填了没反应"的字段。本文件钉住接通之后的四条口径：

1. 匿名请求加密文章：正文为空，但提示必须原样给到（它就是给锁屏看的）。
2. 提示只随"真有密码哈希"输出：没有密码的文章即便库里留着脏值也不外泄。
3. 写口（POST 创建 / PUT 更新）与读口（slug 详情、按 ID 详情、编辑口）同一条值。
4. 密码散列绝不因这条新字段而出现在任何响应里。
"""

from __future__ import annotations

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.cache import cache
from backend.models.blog import Category, Post
from backend.models.user import User

GUARDED_PASSWORD_HASH = "$argon2id$fake.placeholder.hash"
HINT_TEXT = "密码写在留言板第一条"


def _payload(body: dict) -> dict:
    """兼容统一响应封装：取出真正的业务负载。"""
    if isinstance(body, dict) and "data" in body and "success" in body:
        return body["data"] or {}
    return body or {}


async def _guarded_post(
    db_session: AsyncSession,
    test_user: User,
    test_category: Category,
    *,
    slug: str = "hint-guarded",
    password: str | None = GUARDED_PASSWORD_HASH,
    hint: str | None = HINT_TEXT,
) -> Post:
    post = Post(
        title={"zh": "带提示的加密文章", "en": "Guarded With Hint"},
        slug=slug,
        content={"zh": "需要密码的正文", "en": "Password gated body"},
        excerpt={"zh": "加密摘要", "en": "Guarded excerpt"},
        author_id=test_user.id,
        category_id=test_category.id,
        status="published",
        visibility="password" if password else "public",
        password=password,
        encryption_hint=hint,
        allow_comments=True,
    )
    db_session.add(post)
    await db_session.commit()
    await db_session.refresh(post)
    return post


class TestReaderSide:
    """锁屏闸门：提示可达，正文与散列不可达。"""

    @pytest.mark.asyncio
    async def test_slug_detail_returns_hint_without_body(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        test_user: User,
        test_category: Category,
    ):
        post = await _guarded_post(db_session, test_user, test_category)
        await cache.clear()

        response = await client.get(f"/api/blog/posts/{post.slug}", params={"lang": "zh"})
        assert response.status_code == 200
        data = _payload(response.json())
        assert data["is_password_protected"] is True
        assert data["encryption_hint"] == HINT_TEXT
        assert not data["content"], "未授权时不得返回正文"
        assert GUARDED_PASSWORD_HASH not in response.text
        assert "需要密码的正文" not in response.text

    @pytest.mark.asyncio
    async def test_by_id_detail_returns_hint_too(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        test_user: User,
        test_category: Category,
    ):
        """两条详情口必须同口径：闸门页可能按 slug 拉，也可能按 ID 拉。"""
        post = await _guarded_post(db_session, test_user, test_category, slug="hint-by-id")
        response = await client.get(f"/api/blog/posts/id/{post.id}")
        assert response.status_code == 200
        data = _payload(response.json())
        assert data["encryption_hint"] == HINT_TEXT
        assert data["content"] == ""

    @pytest.mark.asyncio
    async def test_public_post_never_carries_a_stale_hint(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        test_user: User,
        test_category: Category,
    ):
        """没有密码哈希就没有提示：库里留着的脏值不得外泄给匿名方。"""
        post = await _guarded_post(
            db_session, test_user, test_category, slug="hint-no-password", password=None
        )
        await cache.clear()

        response = await client.get(f"/api/blog/posts/{post.slug}", params={"lang": "zh"})
        data = _payload(response.json())
        assert data["is_password_protected"] is False
        assert data["encryption_hint"] is None
        assert response.json()  # 响应仍可序列化，字段是 None 而不是键消失

        by_id = _payload((await client.get(f"/api/blog/posts/id/{post.id}")).json())
        assert by_id["encryption_hint"] is None


class TestWriterSide:
    """写口与读口同源：POST/PUT 提交的提示要能被下一次 GET 读到。"""

    @pytest.mark.asyncio
    async def test_create_post_persists_and_returns_hint(
        self, client: AsyncClient, admin_headers: dict
    ):
        response = await client.post(
            "/api/blog/posts",
            headers=admin_headers,
            json={
                "title": {"zh": "新建加密文章", "en": "Created Guarded"},
                "slug": "hint-created",
                "content": {"zh": "正文", "en": "body"},
                "status": "published",
                "visibility": "password",
                "password": "letmein-123",
                "encryption_hint": "问作者要",
            },
        )
        assert response.status_code == 201, response.text
        data = _payload(response.json())
        assert data["encryption_hint"] == "问作者要"
        assert data["is_password_protected"] is True

        detail = _payload(
            (await client.get("/api/blog/posts/hint-created", params={"lang": "zh"})).json()
        )
        assert detail["encryption_hint"] == "问作者要"

    @pytest.mark.asyncio
    async def test_update_can_rewrite_and_clear_hint(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        admin_headers: dict,
        test_user: User,
        test_category: Category,
    ):
        post = await _guarded_post(db_session, test_user, test_category, slug="hint-put")

        rewritten = await client.put(
            f"/api/blog/posts/{post.id}",
            headers=admin_headers,
            json={"encryption_hint": "换了一条提示"},
        )
        assert rewritten.status_code == 200, rewritten.text
        await cache.clear()
        detail = _payload((await client.get(f"/api/blog/posts/{post.slug}")).json())
        assert detail["encryption_hint"] == "换了一条提示"

        # 空串是合法值（作者不要提示了），不得被 exclude_unset 当成"不动它"永远删不掉
        cleared = await client.put(
            f"/api/blog/posts/{post.id}",
            headers=admin_headers,
            json={"encryption_hint": ""},
        )
        assert cleared.status_code == 200, cleared.text
        await cache.clear()
        after = _payload((await client.get(f"/api/blog/posts/{post.slug}")).json())
        assert not after["encryption_hint"]

    @pytest.mark.asyncio
    async def test_edit_endpoint_returns_hint_for_backfill(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        admin_headers: dict,
        test_user: User,
        test_category: Category,
    ):
        """编辑器必须回填提示：否则改一次标题就把提示提交成空串清掉。"""
        post = await _guarded_post(db_session, test_user, test_category, slug="hint-edit")
        response = await client.get(f"/api/blog/posts/{post.id}/edit", headers=admin_headers)
        assert response.status_code == 200, response.text
        data = _payload(response.json())
        assert data["encryption_hint"] == HINT_TEXT
        assert data["has_password"] is True
