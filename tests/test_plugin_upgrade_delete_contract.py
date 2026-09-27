"""插件 upgrade/delete 端点契约回归。

- upgrade 原为空操作 stub（只动 updated_at），前端「升级完成」后 DB 版本不变，
  与主题侧 upgrade（scan_local 回读磁盘清单）口径分叉。本测试钉死新口径：
  upgrade 必须把磁盘清单上已替换的 version 刷回 DB。
- upgrade/delete 必须走 `_invalidate_rendered_content` 三层失效
  （详情缓存 + 列表/RSS + Nitro 页面缓存），否则 TTL 内访客仍见旧钩子集渲染。
- 未知 slug → 404 PLUGIN_NOT_FOUND（错误信封平铺）。
"""

from __future__ import annotations

import json

import pytest
from httpx import AsyncClient

from backend.api import plugins as plugins_api
from backend.core import manifest_scanner

SLUG = "upgrade-probe"


def _write_plugin(folder, version: str):
    folder.mkdir(parents=True, exist_ok=True)
    (folder / "rosetta-plugin.json").write_text(
        json.dumps({"name": "Upgrade Probe", "slug": SLUG, "version": version}),
        encoding="utf-8",
    )


@pytest.fixture
def probe_plugins_dir(tmp_path, monkeypatch):
    root = tmp_path / "plugins"
    monkeypatch.setattr(manifest_scanner, "PLUGINS_DIR", root)
    yield root


@pytest.fixture
def invalidate_spy(monkeypatch):
    """拦截三层失效的两个出口，记录 reason（含内部 import 的模块属性）。"""
    calls: list[str] = []

    async def _fake_invalidate_cache(prefix: str, *a, **kw):
        calls.append(f"cache:{prefix}")
        return True

    def _fake_purge(reason: str, *a, **kw):
        calls.append(f"purge:{reason}")

    monkeypatch.setattr(plugins_api, "invalidate_cache", _fake_invalidate_cache)
    import backend.services.frontend_cache_purge as fcp

    monkeypatch.setattr(fcp, "purge_frontend_page_cache", _fake_purge)
    return calls


@pytest.mark.asyncio
async def test_upgrade_resyncs_version_from_disk_manifest(
    client: AsyncClient, admin_headers: dict, probe_plugins_dir, invalidate_spy
):
    _write_plugin(probe_plugins_dir / SLUG, "1.0.0")
    scan = await client.post("/api/admin/plugins/scan", headers=admin_headers)
    assert scan.status_code == 200, scan.text

    # 磁盘先替换清单版本（zip 覆盖安装后等价状态）
    _write_plugin(probe_plugins_dir / SLUG, "1.0.1")

    up = await client.post(f"/api/admin/plugins/{SLUG}/upgrade", headers=admin_headers)
    assert up.status_code == 200, up.text
    body = up.json()
    assert body["success"] is True
    assert body["data"]["slug"] == SLUG
    assert body["data"]["version"] == "1.0.1", "upgrade 必须把磁盘清单版本刷回 DB（stub 回归）"
    assert "settings" in body["data"]

    assert "cache:post:" in invalidate_spy
    assert "cache:posts" in invalidate_spy
    assert f"purge:plugin:{SLUG}:upgrade" in invalidate_spy

    await client.delete(f"/api/admin/plugins/{SLUG}", headers=admin_headers)


@pytest.mark.asyncio
async def test_delete_invalidates_rendered_content(
    client: AsyncClient, admin_headers: dict, probe_plugins_dir, invalidate_spy
):
    _write_plugin(probe_plugins_dir / SLUG, "1.0.0")
    scan = await client.post("/api/admin/plugins/scan", headers=admin_headers)
    assert scan.status_code == 200, scan.text

    d = await client.delete(f"/api/admin/plugins/{SLUG}", headers=admin_headers)
    assert d.status_code == 200, d.text
    assert f"purge:plugin:{SLUG}:delete" in invalidate_spy
    assert "cache:post:" in invalidate_spy


@pytest.mark.asyncio
async def test_upgrade_unknown_plugin_returns_404(
    client: AsyncClient, admin_headers: dict, probe_plugins_dir, invalidate_spy
):
    r = await client.post("/api/admin/plugins/no-such-plugin/upgrade", headers=admin_headers)
    assert r.status_code == 404, r.text
    assert r.json()["error_code"] == "PLUGIN_NOT_FOUND"
    assert invalidate_spy == [], "404 分支不得触发缓存失效"
