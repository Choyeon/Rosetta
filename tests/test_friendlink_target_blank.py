"""友情链接 `target_blank` 的读写两端守卫。

这一族此前的形状是**半接通**：`FriendLink.target_blank` 列存在、Create/Update/Response
三个模型都带这个键、前台 `pages/friends.vue` 也按它决定 `target=_blank` + `rel=noopener`，
唯独后台管理页提交的 payload 从不带它 —— 于是访客行为只能由导入/接口直接写库来决定，
管理员在界面上无论怎么设都没有对应控件（与已修的导航 target 同一种缺陷形状）。

后端这一侧必须钉住四件事：
* 四个模型（Create/Update/Response/Localized）都声明 `target_blank`，字段名与前端一致。
* 创建缺省为 False（老数据与"没勾"同义），显式 True 能落库并回读。
* 两口都回吐这一位：公示口（前台 `pages/friends.vue`）与管理口（后台编辑/审核页，
  含未通过审核的行）——缺任一口就是"改了看不见"或"前台读不到"。
* PUT 的 `exclude_unset` 语义：只改别的字段不得顺手把这一位清掉。
"""

from typing import Any

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models.core import FriendLink
from backend.schemas import (
    FriendLinkCreate,
    FriendLinkLocalizedResponse,
    FriendLinkResponse,
    FriendLinkUpdate,
)


def _payload(body: Any) -> Any:
    """兼容统一响应封装：取出真正的业务负载。"""
    if isinstance(body, dict) and "data" in body and "success" in body:
        return body["data"]
    return body


def _link(**overrides) -> FriendLink:
    data = {
        "name": {"zh": "友站", "en": "Friend", "ja": "フレンド", "zh_Hant": "友站"},
        "url": "https://friend.example.com",
        "description": None,
        "logo": "",
        "order": 1,
        "status": "approved",
        "is_active": True,
        "target_blank": True,
    }
    data.update(overrides)
    return FriendLink(**data)


async def _create(client: AsyncClient, headers: dict, **body) -> dict:
    payload = {
        "name": {"zh": "新友链", "en": "New Friend"},
        "url": "https://created.example.com",
        **body,
    }
    response = await client.post("/api/friend-links", headers=headers, json=payload)
    assert response.status_code in (200, 201), response.text
    return _payload(response.json())


@pytest.mark.usefixtures("db_session")
class TestSchemaDeclaresTheColumn:
    def test_all_four_models_declare_target_blank(self) -> None:
        for model in (
            FriendLinkCreate,
            FriendLinkUpdate,
            FriendLinkResponse,
            FriendLinkLocalizedResponse,
        ):
            assert "target_blank" in model.model_fields, f"{model.__name__} 丢了这个键"

    def test_create_default_is_false(self) -> None:
        """缺省 False：老数据与"没勾新窗口"同义，不能反转成 True。"""
        assert FriendLinkCreate.model_fields["target_blank"].default is False


@pytest.mark.usefixtures("db_session")
class TestWriteReadRoundTrip:
    @pytest.mark.asyncio
    async def test_create_carries_explicit_true(self, client: AsyncClient, admin_headers: dict):
        created = await _create(client, admin_headers, target_blank=True)
        assert created["target_blank"] is True
        assert created["url"] == "https://created.example.com"

    @pytest.mark.asyncio
    async def test_create_omitting_the_key_defaults_false(
        self, client: AsyncClient, admin_headers: dict
    ):
        created = await _create(client, admin_headers)
        assert created["target_blank"] is False

    @pytest.mark.asyncio
    async def test_both_list_surfaces_expose_the_flag(
        self, client: AsyncClient, db_session: AsyncSession, admin_headers: dict
    ):
        """前台读公开口、后台编辑读管理口；任一口不回吐这一位就等于没接通。

        管理口必须带出未通过审核的行 —— 审核页看不到就没有"改回通过"的入口
        （`?all=true` 那套匿名管理视图已退役，见 test_friendlink_status_gate.py）。
        """
        db_session.add(_link(url="https://blank.example.com", target_blank=True))
        db_session.add(_link(url="https://self.example.com", target_blank=False))
        db_session.add(
            _link(url="https://pending-blank.example.com", status="pending", target_blank=True)
        )
        await db_session.commit()

        public = _payload((await client.get("/api/friend-links")).json())
        assert {row["url"] for row in public} == {
            "https://blank.example.com",
            "https://self.example.com",
        }

        admin = _payload(
            (await client.get("/api/admin/friend-links", headers=admin_headers)).json()
        )
        assert len(admin) == 3, "管理口漏掉未审核行"

        for rows in (public, admin):
            by_url = {row["url"]: row for row in rows}
            assert by_url["https://blank.example.com"]["target_blank"] is True
            assert by_url["https://self.example.com"]["target_blank"] is False

        pending_row = next(r for r in admin if r["url"] == "https://pending-blank.example.com")
        assert pending_row["target_blank"] is True

    @pytest.mark.asyncio
    async def test_update_toggles_both_directions(
        self, client: AsyncClient, admin_headers: dict, db_session: AsyncSession
    ):
        link = _link(target_blank=True)
        db_session.add(link)
        await db_session.commit()
        await db_session.refresh(link)

        off = await client.put(
            f"/api/friend-links/{link.id}",
            headers=admin_headers,
            json={"target_blank": False},
        )
        assert off.status_code == 200, off.text
        assert _payload(off.json())["target_blank"] is False

        on = await client.put(
            f"/api/friend-links/{link.id}",
            headers=admin_headers,
            json={"target_blank": True},
        )
        assert _payload(on.json())["target_blank"] is True

    @pytest.mark.asyncio
    async def test_partial_update_does_not_clobber_the_flag(
        self, client: AsyncClient, admin_headers: dict, db_session: AsyncSession
    ):
        """PUT 只提交 status 时不得顺手清掉新窗口设置（exclude_unset 语义）。"""
        link = _link(target_blank=True)
        db_session.add(link)
        await db_session.commit()
        await db_session.refresh(link)

        response = await client.put(
            f"/api/friend-links/{link.id}",
            headers=admin_headers,
            json={"status": "pending"},
        )
        assert response.status_code == 200, response.text
        data = _payload(response.json())
        assert data["status"] == "pending"
        assert data["target_blank"] is True
