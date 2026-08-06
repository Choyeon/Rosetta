"""
站点设置 API 测试

测试站点配置的获取和更新功能。
"""

import pytest
from httpx import AsyncClient


class TestSiteConfig:
    """测试站点配置功能"""

    @pytest.mark.asyncio
    async def test_get_site_config(
        self,
        client: AsyncClient,
    ):
        """测试获取站点配置"""
        response = await client.get("/api/config")
        assert response.status_code == 200
        data = response.json()
        assert "site_name" in data
        assert "site_description" in data
        assert "enable_comments" in data
        assert "pagination_page_size" in data

    @pytest.mark.asyncio
    async def test_site_config_has_default_values(
        self,
        client: AsyncClient,
    ):
        """测试站点配置有默认值"""
        response = await client.get("/api/config")
        assert response.status_code == 200
        data = response.json()
        assert data["site_name"] != ""
        assert data["pagination_page_size"] > 0

    @pytest.mark.asyncio
    async def test_site_config_caching(
        self,
        client: AsyncClient,
    ):
        """测试站点配置缓存"""
        # 第一次请求
        response1 = await client.get("/api/config")
        assert response1.status_code == 200

        # 第二次请求应该从缓存返回
        response2 = await client.get("/api/config")
        assert response2.status_code == 200
        assert response1.json() == response2.json()


class TestSiteConfigFull:
    """测试完整站点配置功能"""

    @pytest.mark.asyncio
    async def test_get_full_config_requires_auth(
        self,
        client: AsyncClient,
    ):
        """测试获取完整配置需要认证"""
        response = await client.get("/api/config/full")
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_get_full_config_requires_admin(
        self,
        client: AsyncClient,
        auth_headers: dict,
    ):
        """测试获取完整配置需要管理员权限"""
        response = await client.get(
            "/api/config/full",
            headers=auth_headers,
        )
        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_get_full_config_success(
        self,
        client: AsyncClient,
        admin_headers: dict,
    ):
        """测试管理员获取完整配置"""
        response = await client.get(
            "/api/config/full",
            headers=admin_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert "groups" in data
        assert len(data["groups"]) > 0

        # 检查分组结构
        group = data["groups"][0]
        assert "name" in group
        assert "label" in group
        assert "settings" in group

        # 检查设置项结构
        setting = group["settings"][0]
        assert "key" in setting
        assert "label" in setting
        assert "type" in setting


class TestSiteConfigUpdate:
    """测试更新站点配置功能"""

    @pytest.mark.asyncio
    async def test_update_config_requires_auth(
        self,
        client: AsyncClient,
    ):
        """测试更新配置需要认证"""
        response = await client.post(
            "/api/admin/settings",
            json={"site_name": "新名称"},
        )
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_update_config_requires_admin(
        self,
        client: AsyncClient,
        auth_headers: dict,
    ):
        """测试更新配置需要管理员权限"""
        response = await client.post(
            "/api/admin/settings",
            headers=auth_headers,
            json={"site_name": "新名称"},
        )
        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_update_single_setting(
        self,
        client: AsyncClient,
        admin_headers: dict,
    ):
        """测试更新单个设置"""
        response = await client.post(
            "/api/admin/settings",
            headers=admin_headers,
            json={"site_name": "测试站点名称"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

        # 验证更新生效
        config_response = await client.get("/api/config")
        assert config_response.json()["site_name"] == "测试站点名称"

    @pytest.mark.asyncio
    async def test_update_multiple_settings(
        self,
        client: AsyncClient,
        admin_headers: dict,
    ):
        """测试更新多个设置"""
        response = await client.post(
            "/api/admin/settings",
            headers=admin_headers,
            json={
                "site_name": "多字段测试",
                "site_description": "测试描述",
                "enable_comments": False,
                "pagination_page_size": 20,
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

        # 验证更新生效
        config_response = await client.get("/api/config")
        config_data = config_response.json()
        assert config_data["site_name"] == "多字段测试"
        assert config_data["site_description"] == "测试描述"
        assert config_data["enable_comments"] is False
        assert config_data["pagination_page_size"] == 20

    @pytest.mark.asyncio
    async def test_update_boolean_settings(
        self,
        client: AsyncClient,
        admin_headers: dict,
    ):
        """测试更新布尔类型设置"""
        response = await client.post(
            "/api/admin/settings",
            headers=admin_headers,
            json={
                "enable_registration": False,
                "enable_dark_mode": True,
                "maintenance_mode": False,
            },
        )
        assert response.status_code == 200

        config_response = await client.get("/api/config")
        config_data = config_response.json()
        assert config_data["enable_registration"] is False
        assert config_data["enable_dark_mode"] is True
        assert config_data["maintenance_mode"] is False

    @pytest.mark.asyncio
    async def test_update_numeric_settings(
        self,
        client: AsyncClient,
        admin_headers: dict,
    ):
        """测试更新数值类型设置"""
        response = await client.post(
            "/api/admin/settings",
            headers=admin_headers,
            json={
                "pagination_page_size": 25,
                "max_upload_size": 20971520,
                "session_timeout": 7200,
            },
        )
        assert response.status_code == 200

        config_response = await client.get("/api/config")
        config_data = config_response.json()
        assert config_data["pagination_page_size"] == 25
        assert config_data["max_upload_size"] == 20971520
        assert config_data["session_timeout"] == 7200

    @pytest.mark.asyncio
    async def test_update_default_post_cover(
        self,
        client: AsyncClient,
        admin_headers: dict,
    ):
        """测试更新默认文章封面"""
        response = await client.post(
            "/api/admin/settings",
            headers=admin_headers,
            json={
                "default_post_cover": "/media/covers/default.jpg",
            },
        )
        assert response.status_code == 200

        config_response = await client.get("/api/config")
        assert config_response.json()["default_post_cover"] == "/media/covers/default.jpg"

    @pytest.mark.asyncio
    async def test_update_social_links(
        self,
        client: AsyncClient,
        admin_headers: dict,
    ):
        """测试更新社交媒体链接"""
        response = await client.post(
            "/api/admin/settings",
            headers=admin_headers,
            json={
                "github_url": "https://github.com/testorg",
                "x_url": "https://x.com/testuser",
                "bilibili_url": "https://space.bilibili.com/12345",
            },
        )
        assert response.status_code == 200

        config_response = await client.get("/api/config")
        config_data = config_response.json()
        assert config_data["github_url"] == "https://github.com/testorg"
        assert config_data["x_url"] == "https://x.com/testuser"

    @pytest.mark.asyncio
    async def test_update_empty_settings(
        self,
        client: AsyncClient,
        admin_headers: dict,
    ):
        """测试空更新"""
        response = await client.post(
            "/api/admin/settings",
            headers=admin_headers,
            json={},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True


class TestSiteConfigValidation:
    """测试站点配置验证"""

    @pytest.mark.asyncio
    async def test_pagination_page_size_bounds(
        self,
        client: AsyncClient,
        admin_headers: dict,
    ):
        """测试分页大小边界"""
        # 测试最小值
        response = await client.post(
            "/api/admin/settings",
            headers=admin_headers,
            json={"pagination_page_size": 1},
        )
        assert response.status_code == 200

        # 测试最大值
        response = await client.post(
            "/api/admin/settings",
            headers=admin_headers,
            json={"pagination_page_size": 100},
        )
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_session_timeout_bounds(
        self,
        client: AsyncClient,
        admin_headers: dict,
    ):
        """测试会话超时边界"""
        # 测试最小值
        response = await client.post(
            "/api/admin/settings",
            headers=admin_headers,
            json={"session_timeout": 300},
        )
        assert response.status_code == 200

        # 测试最大值
        response = await client.post(
            "/api/admin/settings",
            headers=admin_headers,
            json={"session_timeout": 86400},
        )
        assert response.status_code == 200
