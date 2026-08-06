"""
核心 API 测试
"""

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models.core import FriendLink, Navigation, SiteConfig


class TestHealthCheck:
    """健康检查测试"""

    @pytest.mark.asyncio
    async def test_health_check(self, client: AsyncClient):
        """测试健康检查端点"""
        response = await client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert "status" in data


class TestSiteConfig:
    """站点配置测试"""

    @pytest.mark.asyncio
    async def test_get_site_config(self, client: AsyncClient, db_session: AsyncSession):
        """测试获取站点配置"""
        config = SiteConfig(
            key="site_name",
            value="Rosetta",
            description="站点名称",
        )
        db_session.add(config)
        await db_session.commit()

        response = await client.get("/api/config")
        assert response.status_code == 200


class TestNavigation:
    """导航测试"""

    @pytest.mark.asyncio
    async def test_list_navigations(self, client: AsyncClient, db_session: AsyncSession):
        """测试获取导航列表"""
        nav = Navigation(
            title={"zh": "首页", "en": "Home"},
            url="/",
            order=1,
            is_active=True,
        )
        db_session.add(nav)
        await db_session.commit()

        response = await client.get("/api/navigations")
        assert response.status_code == 200


class TestFriendLink:
    """友情链接测试"""

    @pytest.mark.asyncio
    async def test_list_friend_links(self, client: AsyncClient, db_session: AsyncSession):
        """测试获取友链列表"""
        link = FriendLink(
            name={"zh": "GitHub", "en": "GitHub"},
            url="https://github.com",
            is_active=True,
        )
        db_session.add(link)
        await db_session.commit()

        response = await client.get("/api/friend-links")
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_create_friend_link(self, client: AsyncClient, admin_headers: dict):
        """测试创建友链"""
        response = await client.post(
            "/api/friend-links",
            headers=admin_headers,
            json={
                "name": {"zh": "新友链", "en": "New Friend Link"},
                "url": "https://example.com",
            },
        )
        assert response.status_code in [200, 201]

    @pytest.mark.asyncio
    async def test_create_friend_link_unauthorized(self, client: AsyncClient):
        """测试未授权创建友链"""
        response = await client.post(
            "/api/friend-links",
            json={
                "name": {"zh": "新友链"},
                "url": "https://example.com",
            },
        )
        assert response.status_code == 401


class TestRootEndpoint:
    """根路径测试"""

    @pytest.mark.asyncio
    async def test_root(self, client: AsyncClient):
        """测试根路径"""
        response = await client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert "name" in data
        assert "version" in data
