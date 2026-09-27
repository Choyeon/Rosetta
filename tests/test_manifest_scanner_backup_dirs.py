"""覆盖安装备份目录不得参与磁盘扫描对齐。

install_from_uploaded_bytes 会把被替换的旧目录改名为 `<slug>.old.<ts>`
留作备份。若 scan 不跳过它，同 slug 的两份清单会让 DB 记录在每次扫描时
被备份目录里的旧 version/folder 回写（安装等于没装上）。
"""

from __future__ import annotations

import json

from backend.core import manifest_scanner


def _write_manifest(root, folder: str, filename: str, slug: str, version: str):
    d = root / folder
    d.mkdir(parents=True)
    (d / filename).write_text(
        json.dumps({"name": slug.title(), "slug": slug, "version": version}),
        encoding="utf-8",
    )


def test_theme_scan_skips_install_backups(tmp_path, monkeypatch):
    _write_manifest(tmp_path, "probe-theme", "rosetta-theme.json", "probe-theme", "2.0.0")
    _write_manifest(
        tmp_path, "probe-theme.old.1700000000", "rosetta-theme.json", "probe-theme", "1.0.0"
    )
    monkeypatch.setattr(manifest_scanner, "THEMES_DIR", tmp_path)
    items = manifest_scanner.scan_themes_dir()
    assert [rel for rel, _ in items] == ["frontend/themes/probe-theme"]
    assert items[0][1].version == "2.0.0"


def test_plugin_scan_skips_install_backups(tmp_path, monkeypatch):
    _write_manifest(tmp_path, "probe-plugin", "rosetta-plugin.json", "probe-plugin", "2.0.0")
    _write_manifest(
        tmp_path, "probe-plugin.old.1700000000", "rosetta-plugin.json", "probe-plugin", "1.0.0"
    )
    monkeypatch.setattr(manifest_scanner, "PLUGINS_DIR", tmp_path)
    items = manifest_scanner.scan_plugins_dir()
    assert [rel for rel, _ in items] == ["backend/plugins/probe-plugin"]
    assert items[0][1].version == "2.0.0"
