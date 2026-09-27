from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING

logger = logging.getLogger(__name__)

PROJECT_ROOT: Path = Path(__file__).resolve().parents[2]
PLUGINS_DIR: Path = PROJECT_ROOT / "backend" / "plugins"
THEMES_DIR: Path = PROJECT_ROOT / "frontend" / "themes"


# 覆盖安装会把被替换的旧目录改名为 `<slug>.old.<timestamp>` 留作备份。
# 备份目录内仍带完整清单，若不跳过，同 slug 的两份清单会在 scan 对齐时
# 让 DB 记录被排序靠后的旧版本回写（版本/ folder 打回备份目录）。
def _is_install_backup(name: str) -> bool:
    return ".old." in name


if TYPE_CHECKING:
    from backend.schemas.manifest import RosettaPluginManifest, RosettaThemeManifest


def _safe_read_json(path: Path) -> dict | None:
    try:
        from backend.schemas.manifest import read_manifest_file

        return read_manifest_file(path)
    except Exception as e:
        logger.warning("Skip invalid manifest at %s: %s", path, e)
        return None


def scan_plugins_dir() -> list[tuple[str, RosettaPluginManifest]]:
    from backend.schemas.manifest import validate_plugin_manifest

    PLUGINS_DIR.mkdir(parents=True, exist_ok=True)
    results: list[tuple[str, RosettaPluginManifest]] = []
    if not PLUGINS_DIR.is_dir():
        return results
    for entry in sorted(PLUGINS_DIR.iterdir()):
        if not entry.is_dir():
            continue
        if entry.name.startswith(".") or entry.name.startswith("_"):
            continue
        if _is_install_backup(entry.name):
            continue
        mf = entry / "rosetta-plugin.json"
        data = _safe_read_json(mf)
        if data is None:
            continue
        try:
            manifest = validate_plugin_manifest(data)
        except ValueError as e:
            logger.warning("Plugin folder %s manifest invalid: %s", entry.name, e)
            continue
        rel = f"backend/plugins/{entry.name}"
        results.append((rel, manifest))
    return results


def _version_parts(version: str) -> tuple[int, ...] | None:
    parts = version.strip().split(".")
    try:
        return tuple(int(part) for part in parts)
    except ValueError:
        return None


def is_newer(disk_version: str | None, db_version: str | None) -> bool:
    """磁盘清单版本相对 DB 记录是否「值得同步」。

    升级的实现口径就是「回读磁盘清单」，所以 update_available 的唯一真值来源
    是磁盘 manifest 的 version 与库里的不一致。点分数字版本按数值比较，只有
    磁盘更新才算可升级（磁盘被回滚成旧版不该催用户点升级）；
    带后缀的版本（1.0.0-beta）无法数值化，退化为「不同即可同步」。
    """
    if not disk_version or not db_version or disk_version == db_version:
        return False
    left = _version_parts(disk_version)
    right = _version_parts(db_version)
    if left is not None and right is not None:
        width = max(len(left), len(right))
        left += (0,) * (width - len(left))
        right += (0,) * (width - len(right))
        return left > right
    return True


def plugin_versions_on_disk() -> dict[str, str]:
    """slug → 磁盘清单声明的插件版本（安装备份目录已被 scan 排除）。"""
    return {manifest.slug: manifest.version for _, manifest in scan_plugins_dir()}


def theme_versions_on_disk() -> dict[str, str]:
    """slug → 磁盘清单声明的主题版本。"""
    return {manifest.slug: manifest.version for _, manifest in scan_themes_dir()}


def scan_themes_dir() -> list[tuple[str, RosettaThemeManifest]]:
    from backend.schemas.manifest import validate_theme_manifest

    THEMES_DIR.mkdir(parents=True, exist_ok=True)
    results: list[tuple[str, RosettaThemeManifest]] = []
    if not THEMES_DIR.is_dir():
        return results
    for entry in sorted(THEMES_DIR.iterdir()):
        if not entry.is_dir():
            continue
        if entry.name.startswith(".") or entry.name.startswith("_"):
            continue
        if _is_install_backup(entry.name):
            continue
        mf = entry / "rosetta-theme.json"
        data = _safe_read_json(mf)
        if data is None:
            continue
        try:
            manifest = validate_theme_manifest(data)
        except ValueError as e:
            logger.warning("Theme folder %s manifest invalid: %s", entry.name, e)
            continue
        rel = f"frontend/themes/{entry.name}"
        results.append((rel, manifest))
    return results
