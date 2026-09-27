"""`update_available` 必须是磁盘清单真值，而不是恒 false 的死字段。

后台插件卡片把它当唯一开关：
- 「可升级」Badge `v-if="row.update_available"`；
- 「升级」按钮 `:disabled="!row.update_available"`。

该字段在 schema 里默认 false 且全仓没有任何写入点，等于升级入口在 UI 上永久锁死
（哪怕磁盘目录里已经躺着新版本、后端 upgrade 也已实现）。本文件钉死新口径：
列表/详情必须按「磁盘清单版本 vs DB 版本」计算，upgrade 同步后自动归位 false。
"""

from __future__ import annotations

import json

import pytest
from httpx import AsyncClient

from backend.core import manifest_scanner
from backend.core.manifest_scanner import is_newer

SLUG = "avail-probe"


@pytest.mark.parametrize(
    ("disk", "db", "expected"),
    [
        ("1.0.1", "1.0.0", True),
        ("1.0.0", "1.0.0", False),
        ("1.0", "1.0.0", False),  # 缺位补零后相等，不是新版本
        ("1.10", "1.9", True),  # 数值比较，不是字符串比较
        ("1.9", "1.10", False),
        (None, "1.0.0", False),  # 磁盘目录已消失 → 无从升级
        ("", "1.0.0", False),
        ("2.0.0-beta", "2.0.0", True),  # 非纯数字版本退化为「不同即可同步」
    ],
)
def test_is_newer_compares_versions(disk, db, expected):
    assert is_newer(disk, db) is expected


def _write_manifest(folder, *, slug: str, version: str, filename: str):
    folder.mkdir(parents=True, exist_ok=True)
    (folder / filename).write_text(
        json.dumps({"name": "Avail Probe", "slug": slug, "version": version}),
        encoding="utf-8",
    )


@pytest.fixture
def disk_dirs(tmp_path, monkeypatch):
    plugins = tmp_path / "plugins"
    themes = tmp_path / "themes"
    monkeypatch.setattr(manifest_scanner, "PLUGINS_DIR", plugins)
    monkeypatch.setattr(manifest_scanner, "THEMES_DIR", themes)
    return plugins, themes


async def _plugin_field(client: AsyncClient, headers: dict, field: str):
    r = await client.get("/api/admin/plugins", headers=headers)
    assert r.status_code == 200, r.text
    items = r.json()["data"]
    match = [i for i in items if i["slug"] == SLUG]
    assert match, f"列表里没有 {SLUG}：{items}"
    return match[0][field]


@pytest.mark.asyncio
async def test_plugin_list_marks_update_available_from_disk(
    client: AsyncClient, admin_headers: dict, disk_dirs
):
    plugins, _ = disk_dirs
    _write_manifest(plugins / SLUG, slug=SLUG, version="1.0.0", filename="rosetta-plugin.json")
    scan = await client.post("/api/admin/plugins/scan", headers=admin_headers)
    assert scan.status_code == 200, scan.text

    assert await _plugin_field(client, admin_headers, "update_available") is False

    # 模拟 zip 覆盖安装后的磁盘状态：目录里已是新版本，DB 还没同步
    _write_manifest(plugins / SLUG, slug=SLUG, version="1.0.1", filename="rosetta-plugin.json")
    assert await _plugin_field(client, admin_headers, "update_available") is True

    detail = await client.get(f"/api/admin/plugins/{SLUG}", headers=admin_headers)
    assert detail.status_code == 200, detail.text
    assert detail.json()["data"]["update_available"] is True, "详情与列表口径必须一致"

    # 同步一次后回到 false —— 否则「可升级」会永久挂着
    up = await client.post(f"/api/admin/plugins/{SLUG}/upgrade", headers=admin_headers)
    assert up.status_code == 200, up.text
    assert up.json()["data"]["version"] == "1.0.1"
    assert await _plugin_field(client, admin_headers, "update_available") is False

    await client.delete(f"/api/admin/plugins/{SLUG}", headers=admin_headers)


@pytest.mark.asyncio
async def test_theme_list_marks_update_available_from_disk(
    client: AsyncClient, admin_headers: dict, disk_dirs
):
    _, themes = disk_dirs
    _write_manifest(themes / SLUG, slug=SLUG, version="1.0.0", filename="rosetta-theme.json")
    scan = await client.post("/api/admin/themes/scan", headers=admin_headers)
    assert scan.status_code == 200, scan.text

    async def _theme_update_flag() -> bool:
        r = await client.get("/api/admin/themes", headers=admin_headers)
        assert r.status_code == 200, r.text
        match = [i for i in r.json()["data"] if i["slug"] == SLUG]
        assert match, "主题列表缺少刚扫描进来的记录"
        return match[0]["update_available"]

    assert await _theme_update_flag() is False
    _write_manifest(themes / SLUG, slug=SLUG, version="1.1.0", filename="rosetta-theme.json")
    assert await _theme_update_flag() is True, "主题侧必须与插件侧同口径"

    await client.delete(f"/api/admin/themes/{SLUG}", headers=admin_headers)
