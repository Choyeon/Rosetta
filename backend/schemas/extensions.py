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
    设置值**必须**包在 ``settings`` 里：``{"settings": {"k":"v"}}``。
    刻意不接受裸 ``{"k":"v"}`` —— 少一层包装时无法区分"这就是设置项"
    和"字段名写错了"，静默收下会让插件配置变成黑洞。
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


# ═══════════════════════════════════════════════════════════════════════════
# 响应体文档模型（仅供 OpenAPI `responses={200: {"model": ...}}` 声明使用，
# 运行时不做序列化过滤——实际响应以 handler 返回字面量为准）
# ═══════════════════════════════════════════════════════════════════════════


class PluginListResponse(BaseModel):
    """``GET /api/admin/plugins`` 的响应体（分页信封）。"""

    success: bool = Field(..., description="固定为 true（失败走 AppException 错误信封）")
    data: list[PluginOut] = Field(default_factory=list, description="当前页插件记录列表")
    total: int = Field(0, description="符合过滤条件的插件总数")
    page: int = Field(1, description="当前页码（从 1 开始）")
    per_page: int = Field(20, description="每页条数（上限 100）")
    total_pages: int = Field(0, description="总页数 = ceil(total / per_page)")
    has_next: bool = Field(False, description="是否还有下一页")


class PluginMenuItem(BaseModel):
    """已激活插件声明的单条后台菜单项（Sidebar「插件」分组用）。"""

    slug: str = Field(..., description="声明该菜单项的插件 slug")
    label: str = Field(..., description="菜单显示文案")
    path: str = Field(..., description="前端后台路由路径")
    icon: str = Field(
        "material-symbols:extension",
        description="图标标识（默认 material-symbols:extension）",
    )
    badge: str | int | None = Field(default=None, description="可选角标（未设置时整个键缺席响应）")
    extras: dict[str, Any] | None = Field(
        default=None, description="插件自定义的扩展字段（为空时整个键缺席响应）"
    )
    admin_route_prefix: str = Field(
        ..., description="插件后台路由固定前缀 /api/admin/plugins/{slug}"
    )


class PluginMenuRegistryData(BaseModel):
    """``GET /api/admin/plugins/menu-registry`` 的 data 载荷。"""

    items: list[PluginMenuItem] = Field(default_factory=list, description="菜单项列表")
    total: int = Field(0, description="菜单项条数")


class PluginMenuRegistryResponse(BaseModel):
    """``GET /api/admin/plugins/menu-registry`` 的响应体。"""

    success: bool = Field(..., description="固定为 true")
    data: PluginMenuRegistryData = Field(
        default_factory=PluginMenuRegistryData, description="菜单注册表载荷"
    )


class PluginScanStats(BaseModel):
    """插件本地目录扫描计数。"""

    added: int = Field(0, description="新登记进 DB 的插件数")
    refreshed: int = Field(0, description="清单变更被刷回 DB 的插件数")


class PluginScanResponse(BaseModel):
    """``POST /api/admin/plugins/scan`` 的响应体。"""

    success: bool = Field(..., description="固定为 true")
    message: str = Field("", description="人类可读的扫描结果摘要（含新增/更新计数）")
    data: PluginScanStats = Field(default_factory=PluginScanStats, description="扫描对齐结果计数")


class PluginBulkResponse(BaseModel):
    """``POST /api/admin/plugins/bulk`` 的响应体（逐插件执行，失败项汇总）。"""

    success: bool = Field(..., description="固定为 true（个别插件失败不影响整体 200）")
    data: BulkOperationOut = Field(
        default_factory=BulkOperationOut,
        description="total/success/failed 计数；errors 为 [{slug, error_code, message}] 列表，全部成功时为 null",
    )


class MarketIndexData(BaseModel):
    """远端市场索引载荷（插件/主题共用结构）。"""

    index: dict[str, Any] = Field(
        default_factory=dict,
        description="完整索引 JSON（含 items 及远端附加元数据；本地缓存 8 小时）",
    )
    items: list[dict[str, Any]] = Field(
        default_factory=list,
        description="可安装条目列表（每项含 slug/zip_url/checksum_sha256 等）；索引缺 items 时为空数组",
    )
    total: int = Field(0, description="条目条数")
    cached_at: int | str | None = Field(
        default=None,
        description="索引落盘时间戳（Unix 秒）；旧缓存无该字段时为 null",
    )


class PluginMarketResponse(BaseModel):
    """``GET /api/admin/plugins/market`` 的响应体。"""

    success: bool = Field(..., description="固定为 true")
    data: MarketIndexData = Field(default_factory=MarketIndexData, description="市场索引载荷")


class PluginDetailResponse(BaseModel):
    """插件详情/安装/激活/状态切换类端点的响应体（data 为 PluginOut）。"""

    success: bool = Field(..., description="固定为 true")
    data: PluginOut = Field(
        ..., description="插件记录（列表/详情场景附带 settings，读取失败时为 null）"
    )
    message: str | None = Field(
        default=None, description="可选提示（如幂等分支的「插件已处于目标状态」），常规成功时缺席"
    )


class PluginSettingsResponse(BaseModel):
    """插件 settings GET/PUT/PATCH 的响应体。"""

    success: bool = Field(..., description="固定为 true")
    data: dict[str, Any] = Field(
        default_factory=dict,
        description="插件设置键值对（settings_schema.properties 是合法键的唯一清单，已应用 schema 默认值）",
    )


class PluginDeactivateResponse(BaseModel):
    """``POST /api/admin/plugins/{slug}/deactivate`` 的响应体。"""

    success: bool = Field(..., description="固定为 true（本就未激活时同样返回成功，幂等）")
    data: dict[str, Any] = Field(
        default_factory=dict,
        description=(
            "停用后的插件记录：幂等分支为 PluginOut 序列化结果；"
            "真实停用分支当前直接序列化 ORM 行（键为表列名超集，如含 site_id/settings_schema）"
        ),
    )
    message: str | None = Field(default=None, description="幂等分支的提示语，真实停用时缺席")


class PackageMessageResponse(BaseModel):
    """仅含操作结果的轻量响应体（插件/主题删除、升级 stub 共用）。"""

    success: bool = Field(..., description="固定为 true")
    message: str = Field("", description="人类可读结果（如「已删除」「升级完成 (stub)」）")


class ThemeListResponse(BaseModel):
    """``GET /api/admin/themes`` 的响应体（分页信封）。"""

    success: bool = Field(..., description="固定为 true（失败走 AppException 错误信封）")
    data: list[ThemeOut] = Field(
        default_factory=list, description="当前页主题记录列表，每项附带合并后的 mods 值"
    )
    total: int = Field(0, description="符合过滤条件的主题总数")
    page: int = Field(1, description="当前页码（从 1 开始）")
    per_page: int = Field(50, description="每页条数（上限 200）")
    total_pages: int = Field(0, description="总页数 = ceil(total / per_page)")
    has_next: bool = Field(False, description="是否还有下一页")


class ThemeMarketResponse(BaseModel):
    """``GET /api/admin/themes/market`` 的响应体。"""

    success: bool = Field(..., description="固定为 true")
    data: MarketIndexData = Field(default_factory=MarketIndexData, description="市场索引载荷")


class ThemeDetailResponse(BaseModel):
    """主题详情/激活/安装/升级类端点的响应体（data 为 ThemeOut）。"""

    success: bool = Field(..., description="固定为 true")
    data: ThemeOut = Field(..., description="主题记录，mods 为 schema 默认值与 DB 存值的合并结果")
    message: str | None = Field(
        default=None, description="可选提示（如升级端点的「已从磁盘清单重新同步元数据」）"
    )


class ThemeScanStats(BaseModel):
    """主题本地目录扫描结果。"""

    added: int = Field(0, description="新登记进 DB 的主题数")
    refreshed: int = Field(0, description="清单变更被刷回 DB 的主题数")
    removed: list[str] = Field(
        default_factory=list, description="被清理的僵尸记录 slug 列表（非激活且磁盘已不存在）"
    )


class ThemeScanResponse(BaseModel):
    """``POST /api/admin/themes/scan`` 的响应体。"""

    success: bool = Field(..., description="固定为 true")
    message: str = Field("", description="人类可读的扫描结果摘要（含清理僵尸条数）")
    data: ThemeScanStats = Field(
        default_factory=ThemeScanStats, description="扫描对齐结果计数与清理清单"
    )


class ThemeModsData(BaseModel):
    """``GET /api/admin/themes/{slug}/mods`` 的 data 载荷。"""

    mods: dict[str, Any] = Field(
        default_factory=dict, description="schema 默认值与 DB 已存值的合并结果"
    )
    mods_schema: dict[str, Any] | None = Field(
        default=None,
        description="JSON Schema Draft-07 声明；properties 是 Customizer 控件的唯一清单",
    )


class ThemeModsResponse(BaseModel):
    """``GET /api/admin/themes/{slug}/mods`` 的响应体。"""

    success: bool = Field(..., description="固定为 true")
    data: ThemeModsData = Field(default_factory=ThemeModsData, description="mods 与 schema 载荷")


class ThemeModsSavedResponse(BaseModel):
    """主题 mods PUT/PATCH 的响应体。"""

    success: bool = Field(..., description="固定为 true（写库成功且已清空前台页面缓存）")
    data: dict[str, Any] = Field(
        default_factory=dict,
        description="保存后的最终 mods（schema 未声明的键已被静默丢弃）",
    )
