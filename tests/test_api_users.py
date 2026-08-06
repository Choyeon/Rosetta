"""
用户认证 API 测试
"""

import pytest
from httpx import AsyncClient

from backend.models.user import User


class TestUserRegistration:
    """用户注册测试"""

    @pytest.mark.asyncio
    async def test_register_success(self, client: AsyncClient):
        """测试成功注册"""
        response = await client.post(
            "/api/users/register",
            json={
                "username": "newuser",
                "email": "newuser@example.com",
                "password": "Testpass999",
                "nickname": "新用户",
            },
        )
        assert response.status_code in [200, 201]
        data = response.json()
        assert "access_token" in data

    @pytest.mark.asyncio
    async def test_register_duplicate_username(self, client: AsyncClient, test_user: User):
        """测试重复用户名注册 — 统一 422 + error_code USERNAME_EXISTS (AppException)"""
        response = await client.post(
            "/api/users/register",
            json={
                "username": "testuser",
                "email": "another@example.com",
                "password": "Testpass999",
            },
        )
        assert response.status_code == 422
        body = response.json()
        # AppException 统一格式: success + message + error_code (顶层)
        assert body.get("success") is False
        assert body.get("error_code") == "USERNAME_EXISTS"

    @pytest.mark.asyncio
    async def test_register_duplicate_email(self, client: AsyncClient, test_user: User):
        """测试重复邮箱注册 — 统一 422 + error_code EMAIL_TAKEN (AppException)"""
        response = await client.post(
            "/api/users/register",
            json={
                "username": "anotheruser",
                "email": "test@example.com",
                "password": "Testpass999",
            },
        )
        assert response.status_code == 422
        body = response.json()
        assert body.get("success") is False
        assert body.get("error_code") == "EMAIL_TAKEN"

    @pytest.mark.asyncio
    async def test_register_short_password(self, client: AsyncClient):
        """测试密码过短 — Pydantic 字段验证 min_length=8 → RequestValidationError 422"""
        response = await client.post(
            "/api/users/register",
            json={
                "username": "newuser",
                "email": "newuser@example.com",
                "password": "Pass1",
            },
        )
        assert response.status_code == 422
        body = response.json()
        # RequestValidationError: success=False, message=validation_error, errors[]
        assert body.get("success") is False
        errors = body.get("errors", [])
        # 至少存在 body.password 相关的字段错误
        assert any("password" in (e.get("field") or "") for e in errors), f"Expected password field error: {body}"

    @pytest.mark.asyncio
    async def test_register_weak_password(self, client: AsyncClient):
        """测试弱密码（无大写字母）— Pydantic field_validator 或 endpoint validate_password → 422"""
        response = await client.post(
            "/api/users/register",
            json={
                "username": "newuser",
                "email": "newuser@example.com",
                "password": "password123",
            },
        )
        assert response.status_code == 422
        body = response.json()
        assert body.get("success") is False
        # Pydantic 可能先捕获 → errors[]；或 endpoint validate_password 捕获 → error_code=WEAK_PASSWORD
        has_errors = bool(body.get("errors"))
        has_weak_code = body.get("error_code") == "WEAK_PASSWORD"
        assert has_errors or has_weak_code, f"Neither errors[] nor WEAK_PASSWORD code: {body}"


class TestUserLogin:
    """用户登录测试"""

    @pytest.mark.asyncio
    async def test_login_success(self, client: AsyncClient, test_user: User):
        """测试成功登录"""
        response = await client.post(
            "/api/users/login",
            json={
                "username": "testuser",
                "password": "Testpass123",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data

    @pytest.mark.asyncio
    async def test_login_wrong_password(self, client: AsyncClient, test_user: User):
        """测试错误密码"""
        response = await client.post(
            "/api/users/login",
            json={
                "username": "testuser",
                "password": "Wrongpassword123",
            },
        )
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_login_nonexistent_user(self, client: AsyncClient):
        """测试不存在的用户"""
        response = await client.post(
            "/api/users/login",
            json={
                "username": "nonexistent",
                "password": "Password123",
            },
        )
        assert response.status_code == 401


class TestUserProfile:
    """用户信息测试"""

    @pytest.mark.asyncio
    async def test_get_current_user(self, client: AsyncClient, auth_headers: dict):
        """测试获取当前用户"""
        response = await client.get("/api/users/me", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert "id" in data
        assert "username" in data

    @pytest.mark.asyncio
    async def test_get_current_user_unauthorized(self, client: AsyncClient):
        """测试未授权获取用户"""
        response = await client.get("/api/users/me")
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_update_profile(self, client: AsyncClient, auth_headers: dict):
        """测试更新用户资料"""
        response = await client.put(
            "/api/users/me",
            headers=auth_headers,
            json={
                "nickname": "新昵称",
                "bio": "这是我的简介",
            },
        )
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_get_user_by_id(self, client: AsyncClient, test_user: User):
        """测试根据 ID 获取用户"""
        response = await client.get(f"/api/users/{test_user.id}")
        assert response.status_code == 200


class TestUserLogout:
    """用户登出测试"""

    @pytest.mark.asyncio
    async def test_logout_success(self, client: AsyncClient, auth_headers: dict):
        """测试成功登出"""
        response = await client.post("/api/users/logout", headers=auth_headers)
        assert response.status_code == 200
