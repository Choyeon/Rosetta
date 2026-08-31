from __future__ import annotations
from pathlib import Path
import logging
from typing import TYPE_CHECKING

logger = logging.getLogger(__name__)

PROJECT_ROOT: Path = Path(__file__).resolve().parents[2]
PLUGINS_DIR: Path = PROJECT_ROOT / "backend" / "plugins"
THEMES_DIR: Path = PROJECT_ROOT / "frontend" / "themes"

if TYPE_CHECKING:
    from backend.schemas.manifest import RosettaPluginManifest, RosettaThemeManifest

def _safe_read_json(path: Path) -> dict | None:
    try:
        from backend.schemas.manifest import read_manifest_file
        return read_manifest_file(path)
    except Exception as e:
        logger.warning("Skip invalid manifest at %s: %s", path, e)
        return None

def scan_plugins_dir() -> list[tuple[str, "RosettaPluginManifest"]]:
    from backend.schemas.manifest import validate_plugin_manifest, RosettaPluginManifest
    PLUGINS_DIR.mkdir(parents=True, exist_ok=True)
    results: list[tuple[str, RosettaPluginManifest]] = []
    if not PLUGINS_DIR.is_dir():
        return results
    for entry in sorted(PLUGINS_DIR.iterdir()):
        if not entry.is_dir(): continue
        if entry.name.startswith(".") or entry.name.startswith("_"): continue
        mf = entry / "rosetta-plugin.json"
        data = _safe_read_json(mf)
        if data is None: continue
        try:
            manifest = validate_plugin_manifest(data)
        except ValueError as e:
            logger.warning("Plugin folder %s manifest invalid: %s", entry.name, e)
            continue
        rel = f"backend/plugins/{entry.name}"
        results.append((rel, manifest))
    return results

def scan_themes_dir() -> list[tuple[str, "RosettaThemeManifest"]]:
    from backend.schemas.manifest import validate_theme_manifest, RosettaThemeManifest
    THEMES_DIR.mkdir(parents=True, exist_ok=True)
    results: list[tuple[str, RosettaThemeManifest]] = []
    if not THEMES_DIR.is_dir():
        return results
    for entry in sorted(THEMES_DIR.iterdir()):
        if not entry.is_dir(): continue
        if entry.name.startswith(".") or entry.name.startswith("_"): continue
        mf = entry / "rosetta-theme.json"
        data = _safe_read_json(mf)
        if data is None: continue
        try:
            manifest = validate_theme_manifest(data)
        except ValueError as e:
            logger.warning("Theme folder %s manifest invalid: %s", entry.name, e)
            continue
        rel = f"frontend/themes/{entry.name}"
        results.append((rel, manifest))
    return results
