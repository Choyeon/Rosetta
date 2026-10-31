"""
博客文章 API 测试
"""

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from backend.models.blog import Category, Post, Tag
from backend.models.user import User


class TestPostList:
    """文章列表测试"""

    @pytest.mark.asyncio
    async def test_list_posts(self, client: AsyncClient, test_post: Post):
        """测试获取文章列表"""
        response = await client.get("/api/blog/posts")
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_list_posts_pagination(self, client: AsyncClient, test_post: Post):
        """测试分页"""
        response = await client.get("/api/blog/posts?page=1&page_size=10")
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_list_posts_by_category(
        self, client: AsyncClient, test_post: Post, test_category: Category
    ):
        """测试按分类筛选"""
        response = await client.get(f"/api/blog/posts?category={test_category.slug}")
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_list_posts_by_tag(self, client: AsyncClient, test_post: Post, test_tag: Tag):
        """测试按标签筛选"""
        response = await client.get(f"/api/blog/posts?tag={test_tag.slug}")
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_list_posts_search(self, client: AsyncClient, test_post: Post):
        """测试搜索"""
        response = await client.get("/api/blog/posts?search=测试")
        assert response.status_code == 200


class TestPostDetail:
    """文章详情测试"""

    @pytest.mark.asyncio
    async def test_get_post_by_slug(self, client: AsyncClient, test_post: Post):
        """测试获取文章详情（按slug）"""
        response = await client.get(f"/api/blog/posts/{test_post.slug}")
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_get_nonexistent_post(self, client: AsyncClient):
        """测试获取不存在的文章"""
        response = await client.get("/api/blog/posts/nonexistent-slug")
        assert response.status_code == 404


class TestPostGetById:
    """按ID获取文章测试"""

    @pytest.mark.asyncio
    async def test_get_post_by_id(self, client: AsyncClient, test_post: Post):
        """测试按ID获取文章"""
        response = await client.get(f"/api/blog/posts/id/{test_post.id}")
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == test_post.id

    @pytest.mark.asyncio
    async def test_get_post_by_id_nonexistent(self, client: AsyncClient):
        """测试获取不存在的文章（按ID）"""
        response = await client.get("/api/blog/posts/id/99999")
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_get_post_by_id_draft_invisible_to_anonymous(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        test_user: User,
        test_category: Category,
    ):
        """草稿不得按 ID 匿名直读（与 slug 详情端点同口径，此前无任何门禁）"""
        draft = Post(
            title={"zh": "草稿文章", "en": "Draft Post"},
            slug="draft-by-id",
            content={"zh": "未发布的秘密内容", "en": "Secret draft content"},
            author_id=test_user.id,
            category_id=test_category.id,
            status="draft",
            allow_comments=True,
        )
        db_session.add(draft)
        await db_session.commit()
        await db_session.refresh(draft)

        response = await client.get(f"/api/blog/posts/id/{draft.id}")
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_get_post_by_id_password_protected_hides_body_and_hash(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        test_user: User,
        test_category: Category,
    ):
        """加密文章未提供密码：正文置空、标记受保护，密码散列绝不出现在响应里"""
        guarded = Post(
            title={"zh": "加密文章", "en": "Guarded Post"},
            slug="guarded-by-id",
            content={"zh": "需要密码的正文", "en": "Password gated body"},
            excerpt={"zh": "加密摘要", "en": "Guarded excerpt"},
            author_id=test_user.id,
            category_id=test_category.id,
            status="published",
            password="$argon2id$fake.placeholder.hash",
            allow_comments=True,
        )
        db_session.add(guarded)
        await db_session.commit()
        await db_session.refresh(guarded)

        response = await client.get(f"/api/blog/posts/id/{guarded.id}")
        assert response.status_code == 200
        data = response.json()
        assert data["is_password_protected"] is True
        assert data["content"] == ""
        assert data.get("password") is None
        assert "fake.placeholder.hash" not in response.text
        assert "需要密码的正文" not in response.text


class TestContentPipelineCoverage:
    """统一渲染管线覆盖：所有响应路径必须过插件 filter 链，不得只跑短代码。

    content_renderer 的契约是"核心请求端点只调用这里的函数"——若某条路径
    退回裸 do_shortcode，the_content / the_excerpt 上的插件（seo-toolkit、
    hello-rosetta）就会在该端点静默失效。本类钉住三条曾绕过的路径。
    """

    @staticmethod
    def _append(marker: str):
        def _fn(value, **_kw):
            return value + marker if isinstance(value, str) and value else value

        _fn.__name__ = f"append_{marker.strip('[]')}"
        return _fn

    @pytest.mark.asyncio
    async def test_by_id_detail_applies_filters(self, client: AsyncClient, test_post: Post):
        from backend.core.hooks import add_filter, remove_filter

        c_fn = self._append("[C]")
        e_fn = self._append("[E]")
        add_filter("the_content", c_fn)
        add_filter("the_excerpt", e_fn)
        try:
            data = (await client.get(f"/api/blog/posts/id/{test_post.id}")).json()
            assert data["content"].endswith("[C]")
            assert data["excerpt"].endswith("[E]")
        finally:
            remove_filter("the_content", c_fn)
            remove_filter("the_excerpt", e_fn)

    @pytest.mark.asyncio
    async def test_post_list_excerpt_applies_filters(self, client: AsyncClient, test_post: Post):
        from backend.core.hooks import add_filter, remove_filter

        e_fn = self._append("[E]")
        t_fn = self._append("[T]")
        add_filter("the_excerpt", e_fn)
        add_filter("the_title", t_fn)
        try:
            payload = (await client.get("/api/blog/posts")).json()
            items = payload["items"]
            target = next(i for i in items if i["id"] == test_post.id)
            assert target["excerpt"].endswith("[E]")
            assert target["title"].endswith("[T]")
        finally:
            remove_filter("the_excerpt", e_fn)
            remove_filter("the_title", t_fn)

    @pytest.mark.asyncio
    async def test_rss_feed_applies_filters(self, client: AsyncClient, test_post: Post):
        from backend.core.hooks import add_filter, remove_filter

        c_fn = self._append("[C]")
        e_fn = self._append("[E]")
        t_fn = self._append("[T]")
        add_filter("the_content", c_fn)
        add_filter("the_excerpt", e_fn)
        add_filter("the_title", t_fn)
        try:
            xml = (await client.get("/api/blog/rss")).text
            assert "[C]" in xml  # content:encoded 过了 the_content
            assert "[E]" in xml  # description 过了 the_excerpt
            assert "测试文章[T]" in xml  # item title 过了 the_title
        finally:
            remove_filter("the_content", c_fn)
            remove_filter("the_excerpt", e_fn)
            remove_filter("the_title", t_fn)

    @pytest.mark.asyncio
    async def test_rss_channel_uses_admin_site_config(
        self, client: AsyncClient, db_session: AsyncSession, test_post: Post
    ):
        """channel 标题/链接必须来自管理端 SiteConfig（含分组覆写后的 /config 缓存），
        而不是 env settings 的 app_name/site_url——否则改站点名后订阅源与前台口径分裂。"""
        from backend.core.cache import cache
        from backend.models.core import SiteConfig

        # SiteConfig 主键是自增 id，session.get(str) 永不命中；按 key 显式 SELECT。
        # conftest 已预置 SITE_NAME=Rosetta Test（未 flush 的 pending 行也能被 autoflush SELECT 看到）。
        for key, value in [
            ("SITE_NAME", "站点名测试RSS"),
            ("SITE_URL", "https://rss-test.example.com"),
        ]:
            row = (
                await db_session.execute(select(SiteConfig).where(SiteConfig.key == key))
            ).scalar_one_or_none()
            if row:
                row.value = value
            else:
                db_session.add(SiteConfig(key=key, value=value))
        await db_session.commit()
        # 清空响应缓存：既去掉 site_config 旧缓存，也去掉 conftest 预热进 posts 前缀的 rss 条目
        await cache.clear()
        xml = (await client.get("/api/blog/rss")).text
        assert "<title>站点名测试RSS</title>" in xml
        assert "https://rss-test.example.com/" in xml

    @pytest.mark.asyncio
    async def test_user_posts_excerpt_applies_filters(self, client: AsyncClient, test_post: Post):
        """作者主页文章列表：多语言摘要 dict 的每个值都必须过 the_excerpt 链。"""
        from backend.core.hooks import add_filter, remove_filter

        e_fn = self._append("[E]")
        add_filter("the_excerpt", e_fn)
        try:
            payload = (await client.get(f"/api/users/{test_post.author_id}/posts")).json()
            data = payload.get("data") or payload
            target = next(i for i in data["items"] if i["id"] == test_post.id)
            excerpt = target["excerpt"]
            assert isinstance(excerpt, dict)
            assert all(v.endswith("[E]") for v in excerpt.values() if v)
        finally:
            remove_filter("the_excerpt", e_fn)

    @pytest.mark.asyncio
    async def test_page_detail_content_applies_filters(self, client: AsyncClient, db_session):
        """独立页详情：多语言正文 dict 的每个值都必须过 the_content 链（列表端点保持原文）。"""
        from backend.core.hooks import add_filter, remove_filter
        from backend.models.core import Page

        c_fn = self._append("[C]")
        add_filter("the_content", c_fn)
        page = Page(
            title={"zh": "关于", "en": "About"},
            slug="about-pipeline",
            content={"zh": "读者侧正文", "en": "reader body"},
            status="published",
        )
        db_session.add(page)
        await db_session.commit()
        try:
            detail = (await client.get("/api/pages/about-pipeline")).json()
            assert all(v.endswith("[C]") for v in detail["content"].values())
            listed = (await client.get("/api/pages")).json()
            data = listed.get("data") or listed
            target = next(i for i in data["items"] if i["slug"] == "about-pipeline")
            assert target["content"] == {"zh": "读者侧正文", "en": "reader body"}
        finally:
            remove_filter("the_content", c_fn)


class TestPostCreate:
    """创建文章测试"""

    @pytest.mark.asyncio
    async def test_create_post_as_admin(
        self, client: AsyncClient, admin_headers: dict, test_category: Category
    ):
        """测试管理员创建文章"""
        response = await client.post(
            "/api/blog/posts",
            headers=admin_headers,
            json={
                "title": {"zh": "新文章", "en": "New Post"},
                "slug": "new-post",
                "content": {"zh": "这是新文章的内容", "en": "This is new post content"},
                "category_id": test_category.id,
                "status": "published",
            },
        )
        assert response.status_code in [200, 201]

    @pytest.mark.asyncio
    async def test_create_post_with_tags_roundtrip(
        self,
        client: AsyncClient,
        admin_headers: dict,
        test_tag: Tag,
        db_session: AsyncSession,
    ):
        """带标签新建文章必须 201，并且标签真的落库、响应里带得回来。

        create_post 曾在 flush + refresh **之后**才碰 post.tags：`refresh` 把集合标成过期，
        于是 `clear()` 与 `= []`（多对多赋值要先取旧集合算差量）都会在事件循环里发隐式 IO，
        异步会话直接 `MissingGreenlet` → 编辑器「勾选标签再保存」每次 500。
        PUT 路径同一段代码却没事——它的 SELECT 带 `selectinload(Post.tags)`，集合一开始就是
        已加载态，所以这条缺陷只在"新建"这一侧存在，而既有套件从未 POST 过带 tag_ids 的载荷。
        """
        tagged = Tag(
            name={"zh": "带图标", "en": "With icon"},
            slug="tagged-create-tag",
            color="#0ea5e9",
            icon="🐍",
            is_active=True,
        )
        db_session.add(tagged)
        await db_session.commit()
        await db_session.refresh(tagged)

        response = await client.post(
            "/api/blog/posts",
            headers=admin_headers,
            json={
                "title": {"zh": "带标签新文章"},
                "slug": "tagged-create",
                "content": {"zh": "内容"},
                "tag_ids": [test_tag.id, tagged.id],
                "status": "published",
            },
        )
        assert response.status_code == 201, response.text
        body = response.json()
        assert sorted(t["slug"] for t in body["tags"]) == ["python", "tagged-create-tag"]
        # 标签图标随响应回来（后台表单与公开渲染面读的就是这一份）
        icons = {t["slug"]: t.get("icon") for t in body["tags"]}
        assert icons["tagged-create-tag"] == "🐍"

        stored = (
            await db_session.execute(
                select(Post).options(selectinload(Post.tags)).where(Post.slug == "tagged-create")
            )
        ).scalar_one()
        assert sorted(t.slug for t in stored.tags) == ["python", "tagged-create-tag"]

    @pytest.mark.asyncio
    async def test_create_post_unauthorized(self, client: AsyncClient):
        """测试未授权创建文章"""
        response = await client.post(
            "/api/blog/posts",
            json={
                "title": {"zh": "新文章"},
                "content": {"zh": "内容"},
            },
        )
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_create_post_as_normal_user(self, client: AsyncClient, auth_headers: dict):
        """测试普通用户创建文章（应该失败）"""
        response = await client.post(
            "/api/blog/posts",
            headers=auth_headers,
            json={
                "title": {"zh": "新文章"},
                "content": {"zh": "内容"},
            },
        )
        assert response.status_code in [401, 403]

    @pytest.mark.asyncio
    async def test_create_post_duplicate_slug_is_rejected_not_renamed(
        self, client: AsyncClient, admin_headers: dict, test_post: Post
    ):
        """slug 撞车必须回 409，不能再静默改名。

        旧行为：撞车时给 slug 加一段时间戳后缀。作者按下发布时以为地址是
        /posts/<他写的 slug>，实际拿到 /posts/<slug>-20261017120000 —— 不报错、
        不提示，分享出去才对不上；而 Post.slug 本就有唯一约束，改名只是把冲突藏起来。
        """
        response = await client.post(
            "/api/blog/posts",
            headers=admin_headers,
            json={
                "title": {"zh": "撞名文章"},
                "slug": test_post.slug,
                "content": {"zh": "内容"},
                "status": "draft",
            },
        )
        assert response.status_code == 409

    @pytest.mark.asyncio
    async def test_update_post_to_taken_slug_is_rejected(
        self, client: AsyncClient, admin_headers: dict, test_post: Post, db_session
    ):
        """改名撞到别人的 slug 时给 409，而不是让唯一索引抛 IntegrityError（表现是 500）。"""
        other = Post(
            title={"zh": "另一篇"},
            slug="the-other-slug",
            content={"zh": "内容"},
            author_id=test_post.author_id,
            status="published",
        )
        db_session.add(other)
        await db_session.flush()

        response = await client.put(
            f"/api/blog/posts/{test_post.id}",
            headers=admin_headers,
            json={"slug": "the-other-slug"},
        )
        assert response.status_code == 409

    @pytest.mark.asyncio
    async def test_update_post_keeps_own_slug(
        self, client: AsyncClient, admin_headers: dict, test_post: Post
    ):
        """编辑器每次 PUT 都整份提交，slug 原样回传不能被判成"和别人撞名"。"""
        response = await client.put(
            f"/api/blog/posts/{test_post.id}",
            headers=admin_headers,
            json={"slug": test_post.slug, "title": {"zh": "改标题"}},
        )
        assert response.status_code == 200


class TestPostSeriesRoundTrip:
    """系列章节必须能被编辑器读回来再写回去。

    GET /blog/posts/{id}/edit 不回 series_id 时，编辑器 PUT 整份表单就等于每次都提交
    "没有系列"，一次普通的改标题就把文章踢出系列（前台系列页章节目录随之清空）。
    """

    @pytest.mark.asyncio
    async def test_edit_endpoint_exposes_series(
        self, client: AsyncClient, admin_headers: dict, test_post: Post, db_session
    ):
        from backend.models import PostSeries

        series = PostSeries(title={"zh": "测试系列"}, slug="round-trip-series")
        db_session.add(series)
        await db_session.flush()

        put = await client.put(
            f"/api/blog/posts/{test_post.id}",
            headers=admin_headers,
            json={"series_id": series.id, "series_order": 3},
        )
        assert put.status_code == 200

        got = await client.get(f"/api/blog/posts/{test_post.id}/edit", headers=admin_headers)
        assert got.status_code == 200
        body = got.json()
        assert body["series_id"] == series.id
        assert body["series_order"] == 3


class TestPostUpdate:
    """更新文章测试"""

    @pytest.mark.asyncio
    async def test_update_post(self, client: AsyncClient, admin_headers: dict, test_post: Post):
        """测试更新文章"""
        response = await client.put(
            f"/api/blog/posts/{test_post.id}",
            headers=admin_headers,
            json={
                "title": {"zh": "更新后的标题", "en": "Updated Title"},
                "content": {"zh": "更新后的内容", "en": "Updated content"},
            },
        )
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_update_nonexistent_post(self, client: AsyncClient, admin_headers: dict):
        """测试更新不存在的文章"""
        response = await client.put(
            "/api/blog/posts/99999",
            headers=admin_headers,
            json={"title": {"zh": "标题"}},
        )
        assert response.status_code == 404


class TestPostDelete:
    """删除文章测试"""

    @pytest.mark.asyncio
    async def test_delete_post(
        self,
        client: AsyncClient,
        admin_headers: dict,
        test_category: Category,
        test_user: User,
        db_session: AsyncSession,
    ):
        """测试删除文章"""
        post = Post(
            title={"zh": "待删除文章"},
            slug="to-delete",
            content={"zh": "内容"},
            author_id=test_user.id,
            category_id=test_category.id,
            status="published",
        )
        db_session.add(post)
        await db_session.commit()
        await db_session.refresh(post)
        post_id = post.id

        response = await client.delete(
            f"/api/blog/posts/{post_id}",
            headers=admin_headers,
        )
        assert response.status_code in [200, 204]


class TestPostLike:
    """文章点赞测试"""

    @pytest.mark.asyncio
    async def test_like_post(self, client: AsyncClient, auth_headers: dict, test_post: Post):
        """测试点赞文章"""
        response = await client.post(
            f"/api/blog/posts/{test_post.id}/like",
            headers=auth_headers,
        )
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_unlike_post(self, client: AsyncClient, auth_headers: dict, test_post: Post):
        """测试取消点赞"""
        await client.post(
            f"/api/blog/posts/{test_post.id}/like",
            headers=auth_headers,
        )
        response = await client.post(
            f"/api/blog/posts/{test_post.id}/like",
            headers=auth_headers,
        )
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_like_unauthorized(self, client: AsyncClient, test_post: Post):
        """测试未授权点赞"""
        response = await client.post(f"/api/blog/posts/{test_post.id}/like")
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_like_nonexistent_post(self, client: AsyncClient, auth_headers: dict):
        """测试点赞不存在的文章"""
        response = await client.post(
            "/api/blog/posts/99999/like",
            headers=auth_headers,
        )
        assert response.status_code == 404
