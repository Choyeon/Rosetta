"""Webhook CRUD 契约回归测试。

起因：这一组接口此前没有 response_model，FastAPI 会把未声明的查询/ body 字段
静默丢弃，导致「前端发了 active、后端读 is_active」这类开关永不生效的 bug，
而列表还会把明文 secret 吐出去。这里把契约钉在 HTTP 层：
provider 落库、启停真正持久化、密钥只在轮换接口出现一次、SSRF 护栏按配置生效。
"""

import pytest

from backend.api import webhook as wh

CREATABLE = {
    "name": "CI Hook",
    "url": "http://127.0.0.1:9999/rosetta",
    "secret": "s3cr3t-value",
    "events": ["post.published"],
    "provider": "github",
    "active": True,
}


@pytest.fixture
def allow_private_targets(monkeypatch):
    """放行内网目标：CRUD 用例只验证持久化，不该真去连外部地址。

    SSRF 拒绝路径由 test_private_url_rejected 单独覆盖（默认值 False）。
    """
    monkeypatch.setattr(wh.settings, "webhook_allow_private_targets", True)


async def _create(client, headers, **overrides):
    payload = {**CREATABLE, **overrides}
    resp = await client.post("/api/webhooks", json=payload, headers=headers)
    assert resp.status_code == 200, resp.text
    return resp.json()


async def _post(client, headers, payload):
    return await client.post("/api/webhooks", json=payload, headers=headers)


@pytest.mark.asyncio
async def test_create_persists_provider_and_never_echoes_secret(
    client, staff_headers, allow_private_targets
):
    created = await _create(client, staff_headers)

    assert created["provider"] == "github"
    assert created["active"] is True
    assert created["has_secret"] is True
    assert created["events"] == ["post.published"]
    # 明文密钥不得出现在任何常规读写响应里
    assert "secret" not in created

    listing = await client.get("/api/webhooks", headers=staff_headers)
    assert listing.status_code == 200, listing.text
    body = listing.json()
    assert body["total"] == 1
    item = body["items"][0]
    assert item["id"] == created["id"]
    assert item["provider"] == "github"
    assert "secret" not in item


@pytest.mark.asyncio
async def test_missing_provider_defaults_to_generic(client, staff_headers, allow_private_targets):
    payload = {k: v for k, v in CREATABLE.items() if k != "provider"}
    created = await _post(client, staff_headers, payload)
    assert created.status_code == 200, created.text
    assert created.json()["provider"] == "generic"


@pytest.mark.asyncio
async def test_active_toggle_persists(client, staff_headers, allow_private_targets):
    """历史 bug：PUT 读 is_active、前端发 active，开关永远存不上。"""
    created = await _create(client, staff_headers)

    updated = await client.put(
        f"/api/webhooks/{created['id']}", json={"active": False}, headers=staff_headers
    )
    assert updated.status_code == 200, updated.text
    assert updated.json()["active"] is False

    listing = await client.get("/api/webhooks", headers=staff_headers)
    assert listing.json()["items"][0]["active"] is False


@pytest.mark.asyncio
async def test_partial_update_keeps_other_fields(client, staff_headers, allow_private_targets):
    created = await _create(client, staff_headers)

    updated = await client.put(
        f"/api/webhooks/{created['id']}", json={"name": "改名"}, headers=staff_headers
    )
    body = updated.json()
    assert body["name"] == "改名"
    assert body["provider"] == "github"
    assert body["events"] == ["post.published"]
    assert body["has_secret"] is True


@pytest.mark.asyncio
async def test_empty_secret_string_clears_it(client, staff_headers, allow_private_targets):
    created = await _create(client, staff_headers)
    assert created["has_secret"] is True

    updated = await client.put(
        f"/api/webhooks/{created['id']}", json={"secret": ""}, headers=staff_headers
    )
    assert updated.json()["has_secret"] is False


@pytest.mark.asyncio
async def test_unknown_event_name_is_rejected(client, staff_headers, allow_private_targets):
    """事件名唯一清单是 WEBHOOK_EVENTS：拼错的名字不能静默入库后永不触发。"""
    bad = await _post(client, staff_headers, {**CREATABLE, "events": ["post_created"]})
    assert bad.status_code == 422
    empty = await _post(client, staff_headers, {**CREATABLE, "events": []})
    assert empty.status_code == 422
    # 非法事件名的请求不得留下记录
    listing = await client.get("/api/webhooks", headers=staff_headers)
    assert listing.json()["total"] == 0


@pytest.mark.asyncio
async def test_private_url_rejected_by_default(client, staff_headers):
    """默认 WEBHOOK_ALLOW_PRIVATE_TARGETS=false：内网目标 400，且不入库。"""
    resp = await client.post("/api/webhooks", json=CREATABLE, headers=staff_headers)
    assert resp.status_code == 400, resp.text
    listing = await client.get("/api/webhooks", headers=staff_headers)
    assert listing.json()["total"] == 0


@pytest.mark.asyncio
async def test_non_http_scheme_rejected(client, staff_headers):
    resp = await client.post(
        "/api/webhooks",
        json={**CREATABLE, "url": "file:///etc/passwd"},
        headers=staff_headers,
    )
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_regenerate_secret_returns_plaintext_once(
    client, staff_headers, allow_private_targets
):
    created = await _create(client, staff_headers)

    resp = await client.post(
        f"/api/webhooks/{created['id']}/regenerate-secret", headers=staff_headers
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["success"] is True
    new_secret = body["data"]["secret"]
    assert len(new_secret) == 64
    assert new_secret != CREATABLE["secret"]

    # 轮换后列表依旧只有 has_secret，不回显新旧明文
    listing = await client.get("/api/webhooks", headers=staff_headers)
    item = listing.json()["items"][0]
    assert item["has_secret"] is True
    assert new_secret not in listing.text


@pytest.mark.asyncio
async def test_regular_user_cannot_manage_webhooks(client, auth_headers, allow_private_targets):
    """Webhook 是站点级外发配置，普通登录用户一律拒绝。"""
    listing = await client.get("/api/webhooks", headers=auth_headers)
    assert listing.status_code == 403
    created = await client.post("/api/webhooks", json=CREATABLE, headers=auth_headers)
    assert created.status_code == 403


@pytest.mark.asyncio
async def test_delete_removes_row(client, staff_headers, allow_private_targets):
    created = await _create(client, staff_headers)
    resp = await client.delete(f"/api/webhooks/{created['id']}", headers=staff_headers)
    assert resp.status_code == 200, resp.text
    listing = await client.get("/api/webhooks", headers=staff_headers)
    assert listing.json()["total"] == 0


@pytest.mark.asyncio
async def test_events_catalog_matches_bus_names(client, staff_headers):
    """GET /events 是事件名唯一来源，必须与投递侧用的常量一致。"""
    resp = await client.get("/api/webhooks/events")
    assert resp.status_code == 200, resp.text
    events = resp.json()["events"]
    assert [e["type"] for e in events] == list(wh.WEBHOOK_EVENTS)
    assert all(e["description"] for e in events)
