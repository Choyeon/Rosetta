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
