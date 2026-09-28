"""
用户管理 API 测试

测试用户端和管理员端的用户管理功能。
"""

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models.user import User
from backend.services.cache_service import CacheService
from backend.services.user_service import UserService


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

    @pytest.mark.asyncio
    async def test_change_password_v2_wrong_current_is_not_401(
        self,
        client: AsyncClient,
        auth_headers: dict,
    ):
        """新路径「旧密码错误」不得返回 401。

        带有效 token 的请求被打成 401 会被前端 apiFetch 认成凭证失效：
        它会刷新 token 重试、重试仍 401 就清空登录态跳 /login，
        于是「打错一个字符的旧密码」= 用户被整站登出。
        """
        response = await client.post(
            "/api/users/me/password",
            headers=auth_headers,
            json={
                "old_password": "TotallyWrongPass1",
                "new_password": "NewSecure456",
            },
        )
        assert response.status_code == 400, response.text
        # 会话必须仍然有效：拿同一个 token 再读一次 /me 应当照常 200
        me = await client.get("/api/users/me", headers=auth_headers)
        assert me.status_code == 200


class TestUserAccountDeletion:
    """测试注销账户功能"""

    @pytest.mark.asyncio
    async def test_delete_account_success(
        self,
        client: AsyncClient,
        auth_headers: dict,
    ):
        """测试成功注销账户"""
        response = await client.request(
            "DELETE",
            "/api/users/me",
            headers=auth_headers,
            json={"password": "Testpass123"},
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
        response = await client.request(
            "DELETE",
            "/api/users/me",
            headers=auth_headers,
            json={"password": "WrongPassword"},
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
    async def test_repeated_admin_writes_on_the_same_user_read_fresh_state(
        self,
        client: AsyncClient,
        admin_headers: dict,
        db_session: AsyncSession,
        test_user: User,
    ):
        """后台对同一个用户的连续两次写操作都要成立。

        回归：``get_user_by_id`` 带 300 秒缓存，而这六个调用点全在写路径上。
        第二次请求命中缓存时拿到的是**上一个请求会话**里的实例——那次请求 commit 后
        它的属性已过期，端点里一句 ``user.is_superuser`` 就能抛 ``DetachedInstanceError``
        （500）；就算侥幸读得到，写在脱离会话对象上的字段也不会进本次事务，
        接口回 200 而库里没变（静默丢写）。所以这里连续封禁两次，再解封，
        逐步核对库里的真实状态。
        """
        for attempt in (1, 2):
            r = await client.post(f"/api/admin/users/{test_user.id}/ban", headers=admin_headers)
            assert r.status_code == 200, f"第 {attempt} 次封禁不应因缓存实例失效而 500"

        await db_session.refresh(test_user)
        assert test_user.is_banned is True

        r = await client.post(f"/api/admin/users/{test_user.id}/unban", headers=admin_headers)
        assert r.status_code == 200
        await db_session.refresh(test_user)
        assert test_user.is_banned is False

    @pytest.mark.asyncio
    async def test_get_user_by_id_is_not_served_from_response_cache(
        self, db_session: AsyncSession, test_user: User
    ):
        """写路径的取用户不得进响应缓存（测试会话共享，上面那条例外复现不出故障）。

        ``get_user_by_id`` 的六个调用点全在后台写路径上。一旦它带缓存，命中时返回的
        就是别的会话里的实例：读属性 500、写属性静默丢。这里直接钉"缓存里没有这份载荷"。
        """
        cache_service = CacheService()
        service = UserService(db_session, cache=cache_service)
        await service.get_user_by_id(test_user.id)

        assert await cache_service.get(cache_service.build_key("user", test_user.id)) is None

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
