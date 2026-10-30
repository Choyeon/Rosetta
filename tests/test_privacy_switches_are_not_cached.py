"""隐私闸门不得由响应缓存供给旧开关（跨 worker 陈旧窗口）。

线上实测（批次 #227，2026-10-30）：探针把作者的 `show_social_links` 翻成 False 之后，
SSR 的 `/authors/<u>` 已经把两条链接藏起来了，`GET /users/username/<u>/preferences`
也回 False，但同一时刻匿名 `GET /users/username/<u>` 仍原样回显 website 与 GitHub。

根因不是遮蔽函数没跑，而是**判据的来源**：`get_user_profile` 曾把 `UserPreference`
实例连同用户行一起放进 `user_profile:{id}` 载荷，而这份载荷含 ORM 实例、Redis 层会
显式拒收（`cache_v2.set` 的"不支持的值类型"告警），所以它只活在第一个服务过它的那个
worker 的进程内本地层里；写口的失效动作同样只清"执行它的那个进程"。生产按
`--workers N` 跑：用户在 A worker 关了开关，B/C 会带着旧开关服务到整个
`USER_PROFILE_TTL`（300s）。`public_profile` / `show_email` / `show_social_links`
三个闸门全读这份快照，所以最重的一条是"关了公开资料的人，主页在别人那儿还活 5 分钟"。

修法：开关每读必查（`preferences` 不进缓存载荷）。下面的用例按"缓存已热 + 写口刻意
**不**失效"复现当时的形态——直接改偏好行再 commit，不走 `update_preferences`，
等价于另一个 worker 只看见库里的新值、却收不到任何失效通知。
"""

from __future__ import annotations

from datetime import timedelta

import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.auth import create_access_token, get_password_hash
from backend.models.user import User, UserPreference
from backend.services.cache_service import CacheService

CACHE = CacheService()


def profile_key(user_id: int) -> str:
    return CACHE.build_key("user_profile", user_id)


@pytest_asyncio.fixture
async def social_author(db_session: AsyncSession) -> User:
    """库里装着真实 website / github / 邮箱，且三个开关都放在"可见"侧的作者。

    首轮必须先读到明文，才有"陈旧"可言：如果源数据一开始就是遮蔽态，
    后面的"改了开关立刻遮蔽"会因为恒真而假绿。
    """
    user = User(
        username="cachegateauthor",
        email="cachegateauthor@example.invalid",
        password_hash=get_password_hash("Probe@12345"),
        nickname="缓存闸门作者",
        website="https://cache-gate.example",
        github="https://github.com/cache-gate",
        is_active=True,
        is_staff=False,
        is_superuser=False,
    )
    db_session.add(user)
    await db_session.flush()
    db_session.add(
        UserPreference(
            user_id=user.id,
            public_profile=True,
            show_email=True,
            show_social_links=True,
        )
    )
    await db_session.commit()
    return user


async def flip_switches(db_session: AsyncSession, author: User, **switches: bool) -> None:
    """直接改偏好行并提交——刻意绕过 `update_preferences`，即不发任何失效通知。

    这正是"另一个 worker"的处境：库里的值已经变了，但它进程内那份载荷没人清。
    """
    row = (
        await db_session.execute(select(UserPreference).where(UserPreference.user_id == author.id))
    ).scalar_one()
    for name, value in switches.items():
        setattr(row, name, value)
    await db_session.commit()


async def read_both_profile_routes(client: AsyncClient, author: User) -> tuple[dict, dict]:
    """两条第三人资料口都读一遍：作者主页走 username，其它消费方走 id。"""
    by_id = await client.get(f"/api/users/{author.id}")
    by_name = await client.get(f"/api/users/username/{author.username}")
    assert by_id.status_code == 200, by_id.text
    assert by_name.status_code == 200, by_name.text
    return by_id.json(), by_name.json()


@pytest.mark.asyncio
async def test_profile_read_does_warm_the_cache(social_author: User, client: AsyncClient):
    """前置：这条口确实在写 `user_profile:{id}`。

    没有这一条，后面"开关立刻生效"可能是缓存压根没生效的假绿。
    """
    await client.get(f"/api/users/{social_author.id}")
    assert await CACHE.get(profile_key(social_author.id)) is not None


@pytest.mark.asyncio
async def test_cached_profile_payload_carries_no_preferences(
    social_author: User, client: AsyncClient
):
    """结构闸门：隐私判据不得进缓存载荷（进了就必然跨进程陈旧）。"""
    await client.get(f"/api/users/{social_author.id}")
    payload = await CACHE.get(profile_key(social_author.id))
    assert "preferences" not in payload


@pytest.mark.asyncio
async def test_show_email_gate_is_not_served_from_warm_cache(
    social_author: User, db_session: AsyncSession, client: AsyncClient
):
    by_id, by_name = await read_both_profile_routes(client, social_author)
    assert by_id["email"] == social_author.email
    assert by_name["email"] == social_author.email

    await flip_switches(db_session, social_author, show_email=False)

    by_id, by_name = await read_both_profile_routes(client, social_author)
    assert by_id["email"] == "***"
    assert by_name["email"] == "***"


@pytest.mark.asyncio
async def test_show_social_links_gate_is_not_served_from_warm_cache(
    social_author: User, db_session: AsyncSession, client: AsyncClient
):
    """这一条复现批次 #227 线上那个 FAIL（翻开关后 username 口仍回原始链接）。"""
    by_id, by_name = await read_both_profile_routes(client, social_author)
    assert by_name["website"] == social_author.website
    assert by_name["github"] == social_author.github

    await flip_switches(db_session, social_author, show_social_links=False)

    by_id, by_name = await read_both_profile_routes(client, social_author)
    assert by_id["website"] is None and by_id["github"] is None
    assert by_name["website"] is None and by_name["github"] is None


@pytest.mark.asyncio
async def test_public_profile_gate_is_not_served_from_warm_cache(
    social_author: User, db_session: AsyncSession, client: AsyncClient
):
    """最重的一条：关掉"公开资料"后，主页对外必须**立刻**是 404，而不是等 TTL。"""
    assert (await client.get(f"/api/users/{social_author.id}")).status_code == 200
    assert (await client.get(f"/api/users/username/{social_author.username}")).status_code == 200

    await flip_switches(db_session, social_author, public_profile=False)

    by_id = await client.get(f"/api/users/{social_author.id}")
    by_name = await client.get(f"/api/users/username/{social_author.username}")
    assert by_id.status_code == 404, by_id.text
    assert by_name.status_code == 404, by_name.text


@pytest.mark.asyncio
async def test_self_exemption_still_reads_the_fresh_switch(
    social_author: User, db_session: AsyncSession, client: AsyncClient
):
    """本人豁免与"每读必查"两个口径同时成立：匿名被遮蔽，本人仍拿原始值。

    豁免判定读的是 `is_self`（由 current_user_id 推导，本来就在缓存之外），
    这条用例挡的是"为了让开关立刻生效，把豁免一起改没了"这种反向回归。
    """
    await flip_switches(db_session, social_author, show_social_links=False, show_email=False)
    _, by_name = await read_both_profile_routes(client, social_author)
    assert by_name["github"] is None and by_name["email"] == "***"

    token = create_access_token(
        {"sub": str(social_author.id), "type": "access"},
        expires_delta=timedelta(minutes=5),
    )
    mine = await client.get(
        f"/api/users/username/{social_author.username}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert mine.status_code == 200, mine.text
    assert mine.json()["github"] == social_author.github
    assert mine.json()["email"] == social_author.email
