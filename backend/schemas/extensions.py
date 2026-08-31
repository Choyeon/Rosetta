from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import AnyHttpUrl, BaseModel, ConfigDict, Field


class PackageInstallRemote(BaseModel):
    """远程安装 ZIP 下载参数（插件/主题共用）。"""

    url: AnyHttpUrl = Field(..., description="官方市场 zip URL 或 raw GitHub zip URL")
    checksum_sha256: str | None = Field(
        default=None,
        min_length=16,
        max_length=64,
        description="可选：SHA-256 十六进制摘要校验，提供则在下载落盘前强制比对",
    )
    allow_pre_release: bool = Field(
        default=False,
        description="是否允许包含 pre-release 标记的版本（如 1.0.0-beta.1）",
    )


class PluginBase(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True, extra="ignore")
    slug: str
    name: str
    version: str
    author: str | None = None
    description: str | None = None
    plugin_uri: str | None = None
    author_uri: str | None = None
    textdomain: str | None = None
    requires_rosetta: str | None = None
    settings_schema: dict[str, Any] | None = None
    folder: str | None = None
    install_path: str | None = None
    status: str = "inactive"


class PluginOut(PluginBase):
    id: int
    manifest_version: str = "1.0"
    installed_at: datetime | None = None
    activated_at: datetime | None = None
    updated_at: datetime
    created_at: datetime
    error_message: str | None = None
    settings: dict[str, Any] | None = None
    update_available: bool = False


class PluginActivateIn(BaseModel):
    slug: str | None = None
    enabled: bool


class PluginStatusToggleIn(BaseModel):
    """``PATCH /plugins/{slug}/status`` 专用输入体。

    仅接受 ``{"enabled": true/false}``；与 URL ``{slug}`` 组合使用，
    避免与 ``PluginActivateIn`` 混用导致 body 参数解析歧义。
    """

    enabled: bool


class PluginConfigIn(BaseModel):
    """Plugin settings PUT/PATCH 输入体。

    URL 路径里已有 ``{slug}``，因此 body 里的 ``slug`` 可省略。
    两种写法都接受：``{"settings": {"k":"v"}}`` 或 直接 ``{"k":"v"}``
    —— 后者通过路由层转换为 settings 值。
    """

    slug: str | None = None
    settings: dict[str, Any]


class PluginBulkIn(BaseModel):
    action: Literal["activate", "deactivate", "delete", "upgrade"]
    slugs: list[str]


class PluginInstallFrom(BaseModel):
    source: Literal["local", "remote", "upload"] = Field(
        default="local",
        description="安装来源：local=本地扫描注册, remote=从 URL 下载 zip, upload=multipart/form-data 上传 zip",
    )
    slug: str | None = Field(
        default=None,
        pattern=r"^[a-z][a-z0-9\-]{1,48}$",
        description="来源=local 时必填；remote 时可从 manifest 自动读取",
    )
    remote: PackageInstallRemote | None = Field(
        default=None,
        description="来源=remote 时必填：下载 URL 与校验参数",
    )


class ThemeInstallFrom(BaseModel):
    """主题安装入参（结构与 PluginInstallFrom 一致，复用 PackageInstallRemote）。"""

    source: Literal["local", "remote", "upload"] = Field(
        default="local",
        description="安装来源：local/remote/upload",
    )
    slug: str | None = Field(
        default=None,
        pattern=r"^[a-z][a-z0-9\-]{1,48}$",
    )
    remote: PackageInstallRemote | None = None


class ThemeBase(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True, extra="ignore")
    slug: str
    name: str
    version: str
    author: str | None = None
    description: str | None = None
    theme_uri: str | None = None
    author_uri: str | None = None
    textdomain: str | None = None
    requires_rosetta: str | None = None
    mods_schema: dict[str, Any] | None = None
    folder: str | None = None
    parent_theme: str | None = None
    screenshot_urls: list[str] = []
    tags: list[str] = []
    status: str = "installed"
    is_active: bool = False


class ThemeOut(ThemeBase):
    id: int
    manifest_version: str = "1.0"
    installed_at: datetime | None = None
    activated_at: datetime | None = None
    updated_at: datetime
    created_at: datetime
    error_message: str | None = None
    mods: dict[str, Any] | None = None
    update_available: bool = False


class ThemeModsIn(BaseModel):
    mods: dict[str, Any]


class ThemeActivateIn(BaseModel):
    slug: str


class BulkOperationOut(BaseModel):
    total: int
    success: int
    failed: int
    errors: list[dict[str, Any]] | None = None
