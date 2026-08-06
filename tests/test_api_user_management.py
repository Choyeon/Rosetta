"""
用户管理 API 测试

测试用户端和管理员端的用户管理功能。
"""

import pytest
from httpx import AsyncClient

from backend.models.user import User


class TestUserPasswordChange:
    """测试修改密码功能"""

    @pytest.mark.asyncio
    async def test_change_password_success(
        self,
        client: AsyncClient,
        auth_headers: dict,
    ):
        """测试成功修改密码"""
        response = await client.post(
            "/api/users/me/change-password",
            headers=auth_headers,
            json={
                "current_password": "Testpass123",
                "new_password": "NewSecure456",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "密码修改成功" in data["message"]

    @pytest.mark.asyncio
    async def test_change_password_wrong_current(
        self,
        client: AsyncClient,
        auth_headers: dict,
    ):
        """测试当前密码错误"""
        response = await client.post(
            "/api/users/me/change-password",
            headers=auth_headers,
            json={
                "current_password": "WrongPassword",
                "new_password": "NewSecure456",
            },
        )
        assert response.status_code == 400

    @pytest.mark.asyncio
    async def test_change_password_weak_new(
        self,
        client: AsyncClient,
        auth_headers: dict,
    ):
        """测试新密码强度不足"""
        response = await client.post(
            "/api/users/me/change-password",
            headers=auth_headers,
            json={
                "current_password": "Testpass123",
                "new_password": "weak",
            },
        )
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_change_password_same_as_current(
        self,
        client: AsyncClient,
        auth_headers: dict,
    ):
        """测试新密码与当前密码相同"""
        response = await client.post(
            "/api/users/me/change-password",
            headers=auth_headers,
            json={
                "current_password": "Testpass123",
                "new_password": "Testpass123",
            },
        )
        assert response.status_code == 400

    @pytest.mark.asyncio
    async def test_change_password_unauthorized(
        self,
        client: AsyncClient,
    ):
        """测试未授权访问"""
        response = await client.post(
            "/api/users/me/change-password",
            json={
                "current_password": "Testpass123",
                "new_password": "NewSecure456",
            },
        )
        assert response.status_code == 401


class TestUserAccountDeletion:
    """测试注销账户功能"""

    @pytest.mark.asyncio
    async def test_delete_account_success(
        self,
        client: AsyncClient,
        auth_headers: dict,
    ):
        """测试成功注销账户"""
        response = await client.delete(
            "/api/users/me?password=Testpass123",
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

    @pytest.mark.asyncio
    async def test_delete_account_wrong_password(
        self,
        client: AsyncClient,
        auth_headers: dict,
    ):
        """测试密码错误"""
        response = await client.delete(
            "/api/users/me?password=WrongPassword",
            headers=auth_headers,
        )
        assert response.status_code == 400


class TestAdminUserManagement:
    """测试管理员用户管理功能"""

    @pytest.mark.asyncio
    async def test_list_users(
        self,
        client: AsyncClient,
        admin_headers: dict,
        test_user: User,
    ):
        """测试获取用户列表"""
        response = await client.get(
            "/api/admin/users",
            headers=admin_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "total" in data
        assert data["total"] >= 1

    @pytest.mark.asyncio
    async def test_list_users_with_search(
        self,
        client: AsyncClient,
        admin_headers: dict,
        test_user: User,
    ):
        """测试搜索用户"""
        response = await client.get(
            "/api/admin/users?search=testuser",
            headers=admin_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["total"] >= 1

    @pytest.mark.asyncio
    async def test_create_user(
        self,
        client: AsyncClient,
        admin_headers: dict,
    ):
        """测试创建用户"""
        response = await client.post(
            "/api/admin/users",
            headers=admin_headers,
            json={
                "username": "newuser",
                "email": "newuser@example.com",
                "password": "SecurePass123",
                "nickname": "新用户",
                "is_staff": False,
                "is_active": True,
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert data["username"] == "newuser"
        assert data["email"] == "newuser@example.com"

    @pytest.mark.asyncio
    async def test_create_user_duplicate_username(
        self,
        client: AsyncClient,
        admin_headers: dict,
        test_user: User,
    ):
        """测试创建重复用户名"""
        response = await client.post(
            "/api/admin/users",
            headers=admin_headers,
            json={
                "username": "testuser",
                "email": "another@example.com",
                "password": "SecurePass123",
            },
        )
        assert response.status_code == 400

    @pytest.mark.asyncio
    async def test_get_user_detail(
        self,
        client: AsyncClient,
        admin_headers: dict,
        test_user: User,
    ):
        """测试获取用户详情"""
        response = await client.get(
            f"/api/admin/users/{test_user.id}",
            headers=admin_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == test_user.id
        assert data["username"] == test_user.username

    @pytest.mark.asyncio
    async def test_update_user(
        self,
        client: AsyncClient,
        admin_headers: dict,
        test_user: User,
    ):
        """测试更新用户"""
        response = await client.put(
            f"/api/admin/users/{test_user.id}",
            headers=admin_headers,
            json={
                "nickname": "更新后的昵称",
                "bio": "新的个人简介",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["nickname"] == "更新后的昵称"

    @pytest.mark.asyncio
    async def test_reset_user_password(
        self,
        client: AsyncClient,
        admin_headers: dict,
        test_user: User,
    ):
        """测试重置用户密码"""
        response = await client.post(
            f"/api/admin/users/{test_user.id}/reset-password",
            headers=admin_headers,
            json={
                "new_password": "NewPassword123",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

    @pytest.mark.asyncio
    async def test_ban_user(
        self,
        client: AsyncClient,
        admin_headers: dict,
        test_user: User,
    ):
        """测试封禁用户"""
        response = await client.post(
            f"/api/admin/users/{test_user.id}/ban",
            headers=admin_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

    @pytest.mark.asyncio
    async def test_unban_user(
        self,
        client: AsyncClient,
        admin_headers: dict,
        test_user: User,
    ):
        """测试解封用户"""
        # 先封禁
        await client.post(
            f"/api/admin/users/{test_user.id}/ban",
            headers=admin_headers,
        )
        # 再解封
        response = await client.post(
            f"/api/admin/users/{test_user.id}/unban",
            headers=admin_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

    @pytest.mark.asyncio
    async def test_non_admin_cannot_access(
        self,
        client: AsyncClient,
        auth_headers: dict,
    ):
        """测试非管理员无法访问"""
        response = await client.get(
            "/api/admin/users",
            headers=auth_headers,
        )
        assert response.status_code == 403
