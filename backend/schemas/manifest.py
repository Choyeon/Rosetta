from __future__ import annotations
from pathlib import Path
import json
from typing import Any, Literal
from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator

class PluginAdminMenuSpec(BaseModel):
    """插件 manifest 中声明的后台菜单项（可选）。"""
    model_config = ConfigDict(extra="allow")
    label: str
    path: str
    icon: str = "material-symbols:extension"
    badge: str | int | None = None


class RosettaPluginManifest(BaseModel):
    model_config = ConfigDict(extra="ignore", populate_by_name=True)
    manifest_version: str = "1.0"
    name: str
    slug: str = Field(..., pattern=r"^[a-z0-9-]{3,64}$")
    version: str = Field(..., pattern=r"^\d+\.\d+\.\d+(?:-[a-zA-Z0-9.-]+)?$")
    requires_rosetta: str = ">=1.0.0"
    description_i18n: dict[str, str] | None = None
    description: str | None = None
    author: dict[str, str] | None = Field(default_factory=lambda: {"name": "Rosetta Community"})
    author_name: str | None = None
    plugin_uri: str | None = None
    author_uri: str | None = None
    textdomain: str | None = None
    tags: list[str] = Field(default_factory=list)
    category: Literal[
        "seo",
        "performance",
        "content",
        "social",
        "media",
        "security",
        "utility",
        "integration",
        "publishing",
        "customization",
        "editorial",
    ] | None = None
    settings_schema: dict[str, Any] | None = Field(default_factory=dict)
    screenshot_urls: list[str] = Field(default_factory=list)
    dependencies: list[dict[str, str]] = Field(default_factory=list)
    entry: str = "plugin.py"
    hooks: list[str] = Field(default_factory=list)
    admin_menu: PluginAdminMenuSpec | None = None

    @field_validator("textdomain")
    @classmethod
    def _default_textdomain(cls, v: str | None, info) -> str | None:
        if not v and hasattr(info, "data") and info.data.get("slug"):
            return info.data.get("slug")
        return v or None

class RosettaThemeManifest(BaseModel):
    model_config = ConfigDict(extra="ignore", populate_by_name=True)
    manifest_version: str = "1.0"
    name: str
    slug: str = Field(..., pattern=r"^[a-z0-9-]{3,64}$")
    version: str = Field(..., pattern=r"^\d+\.\d+\.\d+(?:-[a-zA-Z0-9.-]+)?$")
    requires_rosetta: str = ">=1.0.0"
    description_i18n: dict[str, str] | None = None
    description: str | None = None
    author: dict[str, str] | None = Field(default_factory=lambda: {"name": "Rosetta Team"})
    author_name: str | None = None
    theme_uri: str | None = None
    author_uri: str | None = None
    textdomain: str | None = None
    tags: list[str] = Field(default_factory=list)
    parent_theme: str | None = None
    mods_schema: dict[str, Any] | None = Field(default_factory=dict)
    screenshot_urls: list[str] = Field(default_factory=list)
    stylesheet: str = "style.css"
    template: str | None = None
    features: list[str] = Field(default_factory=list)
    color_palette: list[dict[str, Any]] | None = None

def validate_plugin_manifest(data: dict[str, Any]) -> RosettaPluginManifest:
    try:
        return RosettaPluginManifest(**data)
    except ValidationError as e:
        errs = [str(x.get("loc",()))+": "+str(x.get("msg")) for x in e.errors()]
        raise ValueError("Plugin manifest invalid: " + "; ".join(errs)) from e

def validate_theme_manifest(data: dict[str, Any]) -> RosettaThemeManifest:
    try:
        return RosettaThemeManifest(**data)
    except ValidationError as e:
        errs = [str(x.get("loc",()))+": "+str(x.get("msg")) for x in e.errors()]
        raise ValueError("Theme manifest invalid: " + "; ".join(errs)) from e

def read_manifest_file(manifest_path: Path) -> dict[str, Any]:
    if not manifest_path.exists():
        raise FileNotFoundError(f"Manifest not found: {manifest_path}")
    text = manifest_path.read_text(encoding="utf-8")
    try:
        return json.loads(text)
    except json.JSONDecodeError as e:
        raise ValueError(f"Manifest JSON parse error in {manifest_path}: {e}") from e
