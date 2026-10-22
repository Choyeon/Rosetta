"""
管理员改密 / 激活的**语义**回归。

钉住两条以前只在前端文案里承诺、后端却没兑现的口径：

1. 管理员重置密码必须与"本人改密"同构地下线全部会话。此前它走
   `update_profile({"password": ...})`——只换 hash，不 bump token_version、
   不吊销 refresh token，表现是后台提示"密码已重置"，而对方的旧登录态一直用到底。
2. "激活账号"必须让这个人真的能登录。登录闸门是 `is_active and not is_banned`
   两条，只置 is_active 时徽章变绿、toast 报成功，人却还是进不来
   （前端乐观更新与库里状态互相判逆）。
"""

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models.user import RefreshToken

OLD_PW = "Testpass123"
NEW_PW = "Str0ng_Pw@"


async def _login(client: AsyncClient, username: str, password: str):
    return await client.post(
        "/api/users/login",
        json={"username": username, "password": password},
    )


@pytest.mark.asyncio
async def test_admin_reset_bumps_token_version_and_revokes_sessions(
    client: AsyncClient,
    admin_headers: dict,
    db_session: AsyncSession,
    test_user,
):
    """重置成功 → token_version +1、全部 refresh 落库为已吊销、旧 token 刷新 401"""
    login_r = await _login(client, test_user.username, OLD_PW)
    assert login_r.status_code == 200, login_r.text
    refresh_1 = login_r.json()["refresh_token"]

    version_before = test_user.token_version or 0

    r = await client.post(
        f"/api/admin/users/{test_user.id}/reset-password",
        headers=admin_headers,
        json={"new_password": NEW_PW},
    )
    assert r.status_code == 200, r.text

    await db_session.refresh(test_user)
    assert test_user.token_version == version_before + 1, (
        "管理员重置密码没有 bump token_version：refresh 路径按它判会话是否作废，"
        "少这一步等于重置不下线任何人"
    )

    result = await db_session.execute(
        select(RefreshToken).where(RefreshToken.user_id == test_user.id)
    )
    tokens = list(result.scalars().all())
    assert tokens, "登录后应已落一条刷新令牌"
    assert all(t.revoked for t in tokens), "重置后仍存在未吊销的刷新令牌"

    ref_r = await client.post("/api/users/refresh", json={"refresh_token": refresh_1})
    assert ref_r.status_code == 401, f"旧刷新令牌在重置后仍可用: {ref_r.text}"

    new_login = await _login(client, test_user.username, NEW_PW)
    assert new_login.status_code == 200, "重置后的新密码登录失败"


@pytest.mark.asyncio
async def test_admin_reset_rejects_same_as_current_password(
    client: AsyncClient,
    admin_headers: dict,
    test_user,
):
    """新密码与当前密码相同 → 400（强度校验放行，语义校验在写入侧挡下）"""
    r = await client.post(
        f"/api/admin/users/{test_user.id}/reset-password",
        headers=admin_headers,
        json={"new_password": OLD_PW},
    )
    assert r.status_code == 400, r.text
    assert "不能与当前密码相同" in r.text


@pytest.mark.asyncio
async def test_activate_clears_ban_so_the_user_can_login(
    client: AsyncClient,
    admin_headers: dict,
    db_session: AsyncSession,
    test_user,
):
    """封禁 → 激活：is_banned 必须一并清掉，否则"已激活"的徽章是假的"""
    ban_r = await client.post(f"/api/admin/users/{test_user.id}/ban", headers=admin_headers)
    assert ban_r.status_code == 200, ban_r.text

    banned_login = await _login(client, test_user.username, OLD_PW)
    assert banned_login.status_code != 200, "已封禁账号仍然登录成功，后面的断言没有意义"

    act_r = await client.post(f"/api/admin/users/{test_user.id}/activate", headers=admin_headers)
    assert act_r.status_code == 200, act_r.text

    await db_session.refresh(test_user)
    assert test_user.is_active is True
    assert test_user.is_banned is False, (
        "激活只置 is_active 而留着 is_banned：登录闸门是两条条件，"
        "后台会报「已激活」而这个人依然登不进来"
    )

    re_login = await _login(client, test_user.username, OLD_PW)
    assert re_login.status_code == 200, "激活后仍然无法登录"
