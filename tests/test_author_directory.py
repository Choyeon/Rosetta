"""作者目录（``GET /api/users/authors``）的契约回归。

前台 `/authors` 目录页的唯一取数来源。这条路最容易退化的四件事：

1. **匿名可读**：目录是公开页，任何一个鉴权依赖都会让它变成 401 空壳，
   而 SSR 端只会渲染出"还没有作者"——错得悄无声息。
2. **计数与可见性同源**：`post_count` 必须只算 `publicly_listable_posts()`
   （published、非私密、已到发布时间）。手写 `Post.status == "published"` 会把草稿的
   私密档、定时未到的稿一起算进卡片数字，而点进去列表是空的——用户看到的是"这个作者
   有 5 篇，点进去 2 篇"。
3. **隐私与主页 404 同口径**：`public_profile=False` / `show_posts=False` / 停用账号
   的人**不进目录**。他们的主页对外按不存在处理，列进目录等于把"这个人存在、只是藏起来了"
   念出来（AGENTS §9.1「用户隐私开关只有两种语义」）。
4. **路由顺序**：`/authors` 必须声明在 `/{user_id}` 之前，否则会被整数解析吃掉回 422
   ——本文件的每一条用例都会先踩到这层。
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models.blog import Post
from backend.models.user import User, UserPreference

USERS_API = Path(__file__).resolve().parents[1] / "backend" / "api" / "users.py"
BLOG_API = Path(__file__).resolve().parents[1] / "backend" / "api" / "blog.py"


async def _add_post(
    db: AsyncSession,
    author: User,
    slug: str,
    *,
    status: str = "published",
    visibility: str = "public",
    published_at: datetime | None = None,
) -> Post:
    post = Post(
        title={"zh": slug, "en": slug},
        slug=slug,
        content={"zh": "正文", "en": "body"},
        author_id=author.id,
        status=status,
        visibility=visibility,
        published_at=published_at,
        allow_comments=True,
    )
    db.add(post)
    await db.commit()
    await db.refresh(post)
    return post


async def _add_user(db: AsyncSession, username: str, **kwargs) -> User:
    user = User(
        username=username,
        email=f"{username}@example.com",
        password_hash="x",
        nickname=username,
        is_active=kwargs.pop("is_active", True),
        is_staff=False,
        is_superuser=False,
        **kwargs,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


def _items(body: dict) -> list[dict]:
    return body.get("items") or []


def _usernames(body: dict) -> list[str]:
    return [i["username"] for i in _items(body)]


class TestAuthorDirectoryVisibility:
    @pytest.mark.asyncio
    async def test_anonymous_read_returns_bare_paginated_shape(
        self, client: AsyncClient, test_post: Post, test_user: User
    ):
        r = await client.get("/api/users/authors")
        assert r.status_code == 200, r.text
        body = r.json()
        # 裸分页 dict（无 success/data 信封），键集与 /users/ 一致
        assert set(body) >= {"items", "total", "page", "page_size", "total_pages"}
        assert "data" not in body
        assert _usernames(body) == [test_user.username]
        item = body["items"][0]
        assert item["post_count"] == 1
        # 目录不是名片墙：联系方式一个都不下发
        for leaked in ("email", "website", "github", "qq"):
            assert leaked not in item

    @pytest.mark.asyncio
    async def test_counts_only_publicly_listable_posts(
        self, client: AsyncClient, db_session: AsyncSession, test_post: Post, test_user: User
    ):
        await _add_post(db_session, test_user, "draft-post", status="draft")
        await _add_post(db_session, test_user, "private-post", visibility="private")
        # "published 但发布时间在未来"是定时发布的常态落库形态，不算已公开
        await _add_post(
            db_session,
            test_user,
            "future-post",
            published_at=datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(days=2),
        )
        await _add_post(db_session, test_user, "second-live-post")

        r = await client.get("/api/users/authors")
        assert r.status_code == 200, r.text
        items = _items(r.json())
        assert len(items) == 1
        # 2 篇公开（test-post + second-live-post）；草稿 / 私密 / 定时未到都不计
        assert items[0]["post_count"] == 2

    @pytest.mark.asyncio
    async def test_hidden_profile_is_not_listed(
        self, client: AsyncClient, db_session: AsyncSession, test_post: Post, test_user: User
    ):
        db_session.add(UserPreference(user_id=test_user.id, public_profile=False))
        await db_session.commit()

        r = await client.get("/api/users/authors")
        assert r.status_code == 200, r.text
        assert _usernames(r.json()) == []

    @pytest.mark.asyncio
    async def test_hidden_posts_is_not_listed(
        self, client: AsyncClient, db_session: AsyncSession, test_post: Post, test_user: User
    ):
        """show_posts=False 是「隐藏即空」：主页还在，但目录不该把他算作可浏览的作者。"""
        db_session.add(UserPreference(user_id=test_user.id, show_posts=False))
        await db_session.commit()

        r = await client.get("/api/users/authors")
        assert r.status_code == 200, r.text
        assert _usernames(r.json()) == []

    @pytest.mark.asyncio
    async def test_author_without_visible_posts_is_not_listed(
        self, client: AsyncClient, db_session: AsyncSession, test_post: Post
    ):
        await _add_user(db_session, "silent-writer")
        only_draft_user = await _add_user(db_session, "draft-only")
        await _add_post(db_session, only_draft_user, "only-draft", status="draft")

        r = await client.get("/api/users/authors")
        assert r.status_code == 200, r.text
        names = _usernames(r.json())
        assert "silent-writer" not in names
        assert "draft-only" not in names

    @pytest.mark.asyncio
    async def test_inactive_author_is_not_listed(
        self, client: AsyncClient, db_session: AsyncSession, test_post: Post
    ):
        disabled = await _add_user(db_session, "disabled-writer", is_active=False)
        await _add_post(db_session, disabled, "disabled-post")

        r = await client.get("/api/users/authors")
        assert r.status_code == 200, r.text
        assert "disabled-writer" not in _usernames(r.json())


class TestAuthorDirectoryOrderingAndPaging:
    @pytest.mark.asyncio
    async def test_orders_by_post_count_desc_then_username(
        self, client: AsyncClient, db_session: AsyncSession, test_post: Post, test_user: User
    ):
        prolific = await _add_user(db_session, "aaa-prolific")
        await _add_post(db_session, prolific, "p1")
        await _add_post(db_session, prolific, "p2")
        await _add_post(db_session, prolific, "p3")
        # testuser 只有 test-post 一篇
        r = await client.get("/api/users/authors")
        assert r.status_code == 200, r.text
        body = r.json()
        assert _usernames(body)[0] == "aaa-prolific"
        assert body["items"][0]["post_count"] == 3
        assert _usernames(body)[1] == test_user.username

    @pytest.mark.asyncio
    async def test_pagination_totals(
        self, client: AsyncClient, db_session: AsyncSession, test_post: Post, test_user: User
    ):
        second = await _add_user(db_session, "second-writer")
        await _add_post(db_session, second, "second-post")

        r = await client.get("/api/users/authors", params={"page": 1, "page_size": 1})
        assert r.status_code == 200, r.text
        body = r.json()
        assert len(body["items"]) == 1
        assert body["total"] == 2
        assert body["total_pages"] == 2
        assert body["page"] == 1 and body["page_size"] == 1

        r2 = await client.get("/api/users/authors", params={"page": 2, "page_size": 1})
        assert r2.status_code == 200, r2.text
        assert _usernames(r2.json()) != _usernames(body)

    @pytest.mark.asyncio
    async def test_last_published_at_is_exposed(
        self, client: AsyncClient, test_post: Post, test_user: User
    ):
        r = await client.get("/api/users/authors")
        assert r.status_code == 200, r.text
        item = r.json()["items"][0]
        # test_post 的 published_at 是 NULL（fixture 刻意不写），所以只断言键存在
        assert "last_published_at" in item


def test_route_declared_before_dynamic_user_id():
    """`/authors` 必须挂在 `/{user_id}` 之前。

    FastAPI 按声明顺序匹配：晚一行，`/api/users/authors` 就会被整数解析吃掉回 422，
    而目录页的 SSR 会把 422 渲染成"还没有作者"——本文件其余用例会一起红，但把原因
    写在路由顺序上比让人去猜 422 从哪来省得多。
    """
    src = USERS_API.read_text(encoding="utf-8")
    assert src.index('"/authors"') < src.index('"/{user_id}"')


def test_count_predicate_is_single_sourced():
    """计数与列表必须同一条可见性谓词（AGENTS §9.1：集合口只准走 publicly_listable_posts）。"""
    src = USERS_API.read_text(encoding="utf-8")
    body = src[src.index("async def list_authors") :]
    body = body[: body.index("@router.get(", 1)] if "@router.get(" in body[1:] else body
    assert "publicly_listable_posts()" in body
    assert 'Post.status == "published"' not in body


def test_directory_route_is_in_static_sitemap():
    """目录页本身要进 sitemap：作者主页由分类学 sitemap 出，裸 `/authors` 只有固定路由表能提交。

    漏了不会 404，只是这个 URL 的发现入口只剩页脚那一条内链——新页面上线时最容易漏的一步。
    """
    src = BLOG_API.read_text(encoding="utf-8")
    body = src[src.index("_STATIC_SITEMAP_ROUTES: list") :]
    body = body[: body.index("\n]")]
    assert '"/authors"' in body
    # 分类学根路径不能重复进固定表（Search Console 会报重复网址）
    assert '"/categories"' not in body and '"/tags"' not in body
