"""
主题 API 回归测试（Batch 1 后端修复的对应用例）

覆盖：
- 公开 /api/themes/active：站点过滤（其它站点的激活行不可见）、无激活主题返回 None
- 管理端权限红线：subscriber 不能 activate / patch mods
- 404 THEME_NOT_FOUND 形状
- 删除激活中主题 → 409 THEME_ALREADY_ACTIVE（单一来源，API 层不再重复 400）
- PATCH mods：schema 校验失败透传 MODS_SCHEMA_VIOLATION（不再改写 THEME_MODS_INVALID）
- PATCH mods：schema 未声明键被丢弃（WordPress 风格 sanitize）
- PUT mods：全量替换语义（未提交的键回落到 schema 默认值）
- POST scan：磁盘上不存在的僵尸 DB 行被清理（连带 theme_mods: KV）
"""

from __future__ import annotations

import json

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.tenant import DEFAULT_SITE_ID
from backend.models.core import SiteConfig
from backend.models.extensions import Theme

MODS_SCHEMA = {
    "type": "object",
    "properties": {
        "accent": {"type": "string", "format": "color", "default": "#3B82F6"},
        "per_row": {"type": "integer", "minimum": 1, "maximum": 6, "default": 3},
        "show_avatar": {"type": "boolean", "default": True},
    },
}


async def _mk_theme(
    db: AsyncSession,
    slug: str,
    *,
    site_id: int = DEFAULT_SITE_ID,
    is_active: bool = False,
    schema: dict | None = None,
) -> Theme:
    row = Theme(
        site_id=site_id,
        slug=slug,
        name=f"Test {slug}",
        version="1.0.0",
        status="active" if is_active else "installed",
        is_active=is_active,
        folder=f"frontend/themes/{slug}",
        mods_schema=schema if schema is not None else {},
    )
    db.add(row)
    await db.commit()
    await db.refresh(row)
    return row


# ── 公开 /themes/active ────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_public_active_none_when_no_active_theme(client: AsyncClient):
    resp = await client.get("/api/themes/active")
    assert resp.status_code == 200
    body = resp.json()
    assert body["success"] is True
    assert body["data"] is None


@pytest.mark.asyncio
async def test_public_active_respects_site_filter(client: AsyncClient, db_session: AsyncSession):
    """其它站点（site_id=999）的激活行绝不能泄漏到本站公开端点。"""
    await _mk_theme(db_session, "other-site-theme", site_id=999, is_active=True)

    resp = await client.get("/api/themes/active")
    body = resp.json()
    assert body["data"] is None, "未过滤 site_id 的旧查询会错误返回其它站点的主题"


@pytest.mark.asyncio
async def test_public_active_returns_theme_with_merged_mods(
    client: AsyncClient, db_session: AsyncSession
):
    await _mk_theme(db_session, "active-one", is_active=True, schema=MODS_SCHEMA)
    db_session.add(
        SiteConfig(
            key="theme_mods:active-one",
            value=json.dumps({"per_row": 5}),
            description="x",
        )
    )
    await db_session.commit()

    resp = await client.get("/api/themes/active")
    body = resp.json()
    assert body["data"]["slug"] == "active-one"
    mods = body["data"]["mods"]
    assert mods["per_row"] == 5  # 存储值优先
    assert mods["accent"] == "#3B82F6"  # schema 默认值兜底


# ── 权限红线 / 404 ─────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_activate_requires_staff(client: AsyncClient, subscriber_headers: dict):
    resp = await client.put("/api/admin/themes/whatever/activate", headers=subscriber_headers)
    assert resp.status_code in (401, 403)


@pytest.mark.asyncio
async def test_activate_unknown_slug_404(client: AsyncClient, admin_headers: dict):
    resp = await client.put("/api/admin/themes/no-such-theme/activate", headers=admin_headers)
    assert resp.status_code == 404
    assert resp.json()["error_code"] == "THEME_NOT_FOUND"


# ── 删除激活中主题：409 单一语义 ───────────────────────────────────────


@pytest.mark.asyncio
async def test_delete_active_theme_returns_409(
    client: AsyncClient, admin_headers: dict, db_session: AsyncSession
):
    await _mk_theme(db_session, "busy-theme", is_active=True)
    resp = await client.delete("/api/admin/themes/busy-theme", headers=admin_headers)
    assert resp.status_code == 409
    assert resp.json()["error_code"] == "THEME_ALREADY_ACTIVE"


@pytest.mark.asyncio
async def test_delete_inactive_theme_cleans_mods_kv(
    client: AsyncClient, admin_headers: dict, db_session: AsyncSession
):
    await _mk_theme(db_session, "gone-theme")
    db_session.add(SiteConfig(key="theme_mods:gone-theme", value="{}", description="x"))
    await db_session.commit()

    resp = await client.delete("/api/admin/themes/gone-theme", headers=admin_headers)
    assert resp.status_code == 200

    row = (
        await db_session.execute(select(Theme).where(Theme.slug == "gone-theme"))
    ).scalar_one_or_none()
    assert row is None
    kv = (
        await db_session.execute(
            select(SiteConfig).where(SiteConfig.key == "theme_mods:gone-theme")
        )
    ).scalar_one_or_none()
    assert kv is None


# ── mods 校验错误码透传 + sanitize ─────────────────────────────────────


@pytest.mark.asyncio
async def test_patch_mods_invalid_passthrough_error_code(
    client: AsyncClient, admin_headers: dict, db_session: AsyncSession
):
    await _mk_theme(db_session, "mods-theme", schema=MODS_SCHEMA)
    resp = await client.patch(
        "/api/admin/themes/mods-theme/mods",
        json={"mods": {"per_row": 99}},
        headers=admin_headers,
    )
    assert resp.status_code == 400
    body = resp.json()
    # 曾被迫写成 THEME_MODS_INVALID，掩盖真实的 schema 违规语义
    assert body["error_code"] == "MODS_SCHEMA_VIOLATION"


@pytest.mark.asyncio
async def test_patch_mods_drops_undeclared_keys(
    client: AsyncClient, admin_headers: dict, db_session: AsyncSession
):
    await _mk_theme(db_session, "sanitize-theme", schema=MODS_SCHEMA)
    resp = await client.patch(
        "/api/admin/themes/sanitize-theme/mods",
        json={"mods": {"per_row": 4, "evil_unknown_key": {"x": 1}}},
        headers=admin_headers,
    )
    assert resp.status_code == 200
    saved = resp.json()["data"]
    assert saved["per_row"] == 4
    assert "evil_unknown_key" not in saved


@pytest.mark.asyncio
async def test_put_mods_replace_resets_unsubmitted_keys(
    client: AsyncClient, admin_headers: dict, db_session: AsyncSession
):
    await _mk_theme(db_session, "put-theme", schema=MODS_SCHEMA)
    # 先 PATCH 两个非默认值
    await client.patch(
        "/api/admin/themes/put-theme/mods",
        json={"mods": {"per_row": 6, "show_avatar": False}},
        headers=admin_headers,
    )
    # PUT 只提交 accent → 其余键应回落 schema 默认值（WordPress 全量替换语义）
    resp = await client.put(
        "/api/admin/themes/put-theme/mods",
        json={"mods": {"accent": "#111827"}},
        headers=admin_headers,
    )
    assert resp.status_code == 200
    saved = resp.json()["data"]
    assert saved["accent"] == "#111827"
    assert saved["per_row"] == 3
    assert saved["show_avatar"] is True


# ── 列表批量 mods ──────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_list_themes_carries_mods(
    client: AsyncClient, admin_headers: dict, db_session: AsyncSession
):
    await _mk_theme(db_session, "list-a", schema=MODS_SCHEMA)
    await _mk_theme(db_session, "list-b")
    resp = await client.get("/api/admin/themes?per_page=100", headers=admin_headers)
    assert resp.status_code == 200
    rows = {d["slug"]: d for d in resp.json()["data"] if d["slug"].startswith("list-")}
    assert set(rows) == {"list-a", "list-b"}
    assert rows["list-a"]["mods"]["per_row"] == 3
    assert rows["list-b"]["mods"] == {}


# ── scan 僵尸清理 ──────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_scan_removes_zombie_rows(client: AsyncClient, admin_headers: dict, db_session: AsyncSession):
    """DB 有、磁盘无 → scan 后僵尸行与其 mods KV 一并清除。"""
    await _mk_theme(db_session, "zombie-not-on-disk")
    db_session.add(SiteConfig(key="theme_mods:zombie-not-on-disk", value="{}", description="x"))
    await db_session.commit()

    resp = await client.post("/api/admin/themes/scan", headers=admin_headers)
    assert resp.status_code == 200
    removed = resp.json()["data"]["removed"]
    assert "zombie-not-on-disk" in removed

    row = (
        await db_session.execute(select(Theme).where(Theme.slug == "zombie-not-on-disk"))
    ).scalar_one_or_none()
    assert row is None
    kv = (
        await db_session.execute(
            select(SiteConfig).where(SiteConfig.key == "theme_mods:zombie-not-on-disk")
        )
    ).scalar_one_or_none()
    assert kv is None
