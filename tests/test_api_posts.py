"""
博客文章 API 测试
"""

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

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
