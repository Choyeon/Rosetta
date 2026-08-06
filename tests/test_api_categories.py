"""
分类和标签 API 测试
"""

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models.blog import Category, Tag


class TestCategoryList:
    """分类列表测试"""

    @pytest.mark.asyncio
    async def test_list_categories(self, client: AsyncClient, test_category: Category):
        """测试获取分类列表"""
        response = await client.get("/api/blog/categories")
        assert response.status_code == 200


class TestCategoryCreate:
    """创建分类测试"""

    @pytest.mark.asyncio
    async def test_create_category(self, client: AsyncClient, admin_headers: dict):
        """测试管理员创建分类"""
        response = await client.post(
            "/api/blog/categories",
            headers=admin_headers,
            json={
                "name": {"zh": "新分类", "en": "New Category"},
                "slug": "new-category",
                "description": {"zh": "新分类描述", "en": "New category description"},
            },
        )
        assert response.status_code in [200, 201]

    @pytest.mark.asyncio
    async def test_create_category_unauthorized(self, client: AsyncClient):
        """测试未授权创建分类"""
        response = await client.post(
            "/api/blog/categories",
            json={
                "name": {"zh": "新分类"},
                "slug": "new-category",
            },
        )
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_create_duplicate_slug(
        self, client: AsyncClient, admin_headers: dict, test_category: Category
    ):
        """测试重复 slug"""
        response = await client.post(
            "/api/blog/categories",
            headers=admin_headers,
            json={
                "name": {"zh": "另一个分类", "en": "Another Category"},
                "slug": test_category.slug,
            },
        )
        assert response.status_code in [400, 409]


class TestCategoryUpdate:
    """更新分类测试"""

    @pytest.mark.asyncio
    async def test_update_category(
        self, client: AsyncClient, admin_headers: dict, test_category: Category
    ):
        """测试更新分类"""
        response = await client.put(
            f"/api/blog/categories/{test_category.id}",
            headers=admin_headers,
            json={
                "name": {"zh": "更新后的分类", "en": "Updated Category"},
                "description": {"zh": "更新后的描述", "en": "Updated description"},
            },
        )
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_update_category_unauthorized(self, client: AsyncClient, test_category: Category):
        """测试未授权更新分类"""
        response = await client.put(
            f"/api/blog/categories/{test_category.id}",
            json={"name": {"zh": "更新"}},
        )
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_update_nonexistent_category(self, client: AsyncClient, admin_headers: dict):
        """测试更新不存在的分类"""
        response = await client.put(
            "/api/blog/categories/99999",
            headers=admin_headers,
            json={"name": {"zh": "更新"}},
        )
        assert response.status_code == 404


class TestCategoryDelete:
    """删除分类测试"""

    @pytest.mark.asyncio
    async def test_delete_category(
        self, client: AsyncClient, admin_headers: dict, db_session: AsyncSession
    ):
        """测试删除分类"""
        category = Category(
            name={"zh": "待删除分类"},
            slug="to-delete-cat",
        )
        db_session.add(category)
        await db_session.commit()
        await db_session.refresh(category)
        category_id = category.id

        response = await client.delete(
            f"/api/blog/categories/{category_id}",
            headers=admin_headers,
        )
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_delete_category_unauthorized(self, client: AsyncClient, test_category: Category):
        """测试未授权删除分类"""
        response = await client.delete(f"/api/blog/categories/{test_category.id}")
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_delete_nonexistent_category(self, client: AsyncClient, admin_headers: dict):
        """测试删除不存在的分类"""
        response = await client.delete(
            "/api/blog/categories/99999",
            headers=admin_headers,
        )
        assert response.status_code == 404


class TestTagList:
    """标签列表测试"""

    @pytest.mark.asyncio
    async def test_list_tags(self, client: AsyncClient, test_tag: Tag):
        """测试获取标签列表"""
        response = await client.get("/api/blog/tags")
        assert response.status_code == 200


class TestTagCreate:
    """创建标签测试"""

    @pytest.mark.asyncio
    async def test_create_tag(self, client: AsyncClient, admin_headers: dict):
        """测试管理员创建标签"""
        response = await client.post(
            "/api/blog/tags",
            headers=admin_headers,
            json={
                "name": {"zh": "新标签", "en": "New Tag"},
                "slug": "new-tag",
            },
        )
        assert response.status_code in [200, 201]

    @pytest.mark.asyncio
    async def test_create_tag_unauthorized(self, client: AsyncClient):
        """测试未授权创建标签"""
        response = await client.post(
            "/api/blog/tags",
            json={
                "name": {"zh": "新标签"},
                "slug": "new-tag",
            },
        )
        assert response.status_code == 401


class TestTagUpdate:
    """更新标签测试"""

    @pytest.mark.asyncio
    async def test_update_tag(self, client: AsyncClient, admin_headers: dict, test_tag: Tag):
        """测试更新标签"""
        response = await client.put(
            f"/api/blog/tags/{test_tag.id}",
            headers=admin_headers,
            json={
                "name": {"zh": "更新后的标签", "en": "Updated Tag"},
                "color": "#FF5733",
            },
        )
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_update_tag_unauthorized(self, client: AsyncClient, test_tag: Tag):
        """测试未授权更新标签"""
        response = await client.put(
            f"/api/blog/tags/{test_tag.id}",
            json={"name": {"zh": "更新"}},
        )
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_update_nonexistent_tag(self, client: AsyncClient, admin_headers: dict):
        """测试更新不存在的标签"""
        response = await client.put(
            "/api/blog/tags/99999",
            headers=admin_headers,
            json={"name": {"zh": "更新"}},
        )
        assert response.status_code == 404


class TestTagDelete:
    """删除标签测试"""

    @pytest.mark.asyncio
    async def test_delete_tag(
        self, client: AsyncClient, admin_headers: dict, db_session: AsyncSession
    ):
        """测试删除标签"""
        tag = Tag(
            name={"zh": "待删除标签"},
            slug="to-delete-tag-test",
        )
        db_session.add(tag)
        await db_session.commit()
        await db_session.refresh(tag)
        tag_id = tag.id

        response = await client.delete(
            f"/api/blog/tags/{tag_id}",
            headers=admin_headers,
        )
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_delete_tag_unauthorized(self, client: AsyncClient, test_tag: Tag):
        """测试未授权删除标签"""
        response = await client.delete(f"/api/blog/tags/{test_tag.id}")
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_delete_nonexistent_tag(self, client: AsyncClient, admin_headers: dict):
        """测试删除不存在的标签"""
        response = await client.delete(
            "/api/blog/tags/99999",
            headers=admin_headers,
        )
        assert response.status_code == 404
