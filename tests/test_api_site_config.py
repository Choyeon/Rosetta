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
        # 批次 #157：pagination_page_size 退役，每页条数唯一真源是 reading.posts_per_page 分组
        assert "max_upload_size" in data
        assert "pagination_page_size" not in data

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
        assert data["max_upload_size"] > 0

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
                "site_url": "https://multi-field.test",
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
        assert config_data["site_url"] == "https://multi-field.test"

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
                "max_login_attempts": 7,
                "max_upload_size": 20971520,
            },
        )
        assert response.status_code == 200

        config_response = await client.get("/api/config")
        config_data = config_response.json()
        assert config_data["max_login_attempts"] == 7
        assert config_data["max_upload_size"] == 20971520

    @pytest.mark.asyncio
    async def test_retired_flat_keys_are_rejected_not_fakely_saved(
        self,
        client: AsyncClient,
        admin_headers: dict,
    ):
        """批次 #156 退役的扁平键不再「回 200 但库里什么都不做」：写口按 extra=forbid 拦成 422。"""
        for key in ("default_post_cover", "custom_css", "session_timeout", "google_analytics_id"):
            response = await client.post(
                "/api/admin/settings",
                headers=admin_headers,
                json={key: "x"},
            )
            assert response.status_code == 422, f"{key} 又被写口收下了：{response.status_code}"

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
    async def test_retired_flat_mirrors_are_rejected(
        self,
        client: AsyncClient,
        admin_headers: dict,
    ):
        """批次 #157 退役的扁平镜像：写口必须 422，而不是继续 200 + 落一行没人读的 UPPERCASE。

        原先这条用例是 `pagination_page_size` 的边界测试（1 与 100 都回 200），
        那个字段已随镜像族一起删除——留着它等于在文档里教运营者拨一把不存在的开关。
        每页条数的区间闸门在分组写口那一侧（`_NUMERIC_BOUNDS` 的 `reading.posts_per_page`，
        守卫 tests/test_settings_numeric_bounds.py）。
        """
        for key in (
            "pagination_page_size",
            "code_theme",
            "google_site_verification",
            "comment_max_length",
            "author_bio",
        ):
            response = await client.post(
                "/api/admin/settings",
                headers=admin_headers,
                json={key: 1},
            )
            assert response.status_code == 422, f"{key} 又被写口收下了：{response.status_code}"
