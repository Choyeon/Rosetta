"""
插件管理 REST API (挂载于 /api/admin/plugins)

WordPress 风格插件管理接口：
- 管理员：列表 / 详情 / 扫描 / 安装 / 启用 / 停用 / 配置 / 批量 / 删除 / 升级
- 插件安装三种来源：
  - source=local  ：扫描本地目录并写 DB（JSON body 带 slug）
  - source=upload ：multipart/form-data 上传 zip 文件（Task A 新增）
  - source=remote ：从市场 URL 下载 zip + 可选 SHA-256 校验（Task A 新增）
"""

from __future__ import annotations

from typing import Annotated, Literal

from fastapi import APIRouter, Body, Depends, File, Query, Request, UploadFile, status

from backend.core.auth import CurrentStaff, DB
from backend.core.exceptions import AppException
from backend.schemas.extensions import (
    BulkOperationOut,
    PluginActivateIn,
    PluginBulkIn,
    PluginConfigIn,
    PluginInstallFrom,
    PluginOut,
    PluginStatusToggleIn,
)

PLUGIN_NOT_FOUND = "PLUGIN_NOT_FOUND"
PLUGIN_ALREADY_ACTIVE = "PLUGIN_ALREADY_ACTIVE"
PLUGIN_NOT_ACTIVE = "PLUGIN_NOT_ACTIVE"
PLUGIN_INVALID_STATUS = "PLUGIN_INVALID_STATUS"
PLUGIN_SETTINGS_INVALID = "PLUGIN_SETTINGS_INVALID"

router = APIRouter(prefix="/plugins", tags=["插件"])


def _get_plugin_manager():
    from backend.core.extensions import plugin_manager
    return plugin_manager


# ═══════════════════════════════════════════════════════════════════════════
# 注意：FastAPI 的 `/{slug}` 路径参数不会吞掉 `/menu-registry` 这样的「固定段」
# 路由（Starlette 按注册顺序 + 静态段优先匹配）。但为了防御性编程，所有不依赖
# slug 参数的固定路径仍统一放在 `@router.get("")` 之后、`@router.get("/{slug}")`
# 之前 —— 保证在任何 URL 匹配策略下都先落到真实 handler。
# ═══════════════════════════════════════════════════════════════════════════


@router.get("")
async def list_admin_plugins(
    db: DB,
    current_user: CurrentStaff,
    status: str | None = Query(None, description="按状态过滤：inactive|active|error|installed"),
    search: str | None = Query(None, description="搜索名称或 slug"),
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
):
    pm = _get_plugin_manager()
    plugins, total = await pm.list(db, status=status, search=search, page=page, per_page=per_page)
    data = []
    for p in plugins:
        out = PluginOut.model_validate(p)
        try:
            out.settings = await pm.get_settings(db, p.slug)
        except Exception:
            out.settings = None
        data.append(out)
    total_pages = (total + per_page - 1) // per_page if per_page else 1
    return {
        "success": True,
        "data": data,
        "total": total,
        "page": page,
        "per_page": per_page,
        "total_pages": total_pages,
        "has_next": page * per_page < total,
    }


@router.get("/menu-registry")
async def list_plugin_menu_registry(
    db: DB,
    current_user: CurrentStaff,
):
    """返回已激活插件声明的后台菜单项（Sidebar「插件」分组用）。

    返回字段：
    - ``items``: ``[{slug, label, icon, path, admin_route_prefix, badge?}]`` 列表
    - ``admin_route_prefix``: 插件后台路由的固定前缀 ``/api/admin/plugins/{slug}``
    """
    from backend.core.routing_registry import routing_registry

    items: list[dict] = []
    for entry in routing_registry.list_menu():
        slug = entry["slug"]
        enriched = dict(entry)
        enriched["admin_route_prefix"] = f"/api/admin/plugins/{slug}"
        items.append(enriched)
    return {
        "success": True,
        "data": {
            "items": items,
            "total": len(items),
        },
    }


@router.post("/scan")
async def scan_local_plugins(
    db: DB,
    current_user: CurrentStaff,
):
    pm = _get_plugin_manager()
    added, refreshed = await pm.scan_local(db)
    await db.commit()
    return {
        "success": True,
        "message": f"扫描完成，新增 {added}，更新 {refreshed}",
        "data": {"added": added, "refreshed": refreshed},
    }


@router.post("/bulk")
async def bulk_plugin_operation(
    db: DB,
    current_user: CurrentStaff,
    payload: PluginBulkIn,
):
    pm = _get_plugin_manager()
    result = await pm.bulk(db, payload.action, payload.slugs)
    await db.commit()
    return {"success": True, "data": result}


# ═══════════════════════════════════════════════════════════════════════════
# 市场（Market）索引 + 一键安装
# ═══════════════════════════════════════════════════════════════════════════


@router.get("/market")
async def list_plugin_market(
    current_user: CurrentStaff,
    force: bool = Query(False, description="true=跳过本地 8h 缓存重新拉远端"),
):
    from backend.core.market import fetch_market_index

    data = await fetch_market_index("plugins", force=force)
    items = data.get("items") if isinstance(data, dict) else None
    return {
        "success": True,
        "data": {
            "index": data,
            "items": list(items) if isinstance(items, list) else [],
            "total": len(items) if isinstance(items, list) else 0,
            "cached_at": data.get("_cached_at") if isinstance(data, dict) else None,
        },
    }


@router.post("/market/{slug}/install")
async def install_plugin_from_market(
    db: DB,
    current_user: CurrentStaff,
    slug: str,
):
    """在市场索引中按 slug 查找条目，然后调用 install_from_remote 安装。"""
    from backend.core.market import fetch_market_index

    from backend.core.exceptions import AppException
    from backend.schemas.extensions import PackageInstallRemote, PluginInstallFrom

    index = await fetch_market_index("plugins")
    items = index.get("items") if isinstance(index, dict) else None
    if not isinstance(items, list):
        raise AppException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            error_code="MARKET_INDEX_INVALID",
            message="市场索引格式异常：缺少 items 列表",
        )
    item = next(
        (x for x in items if isinstance(x, dict) and x.get("slug") == slug),
        None,
    )
    if item is None:
        raise AppException(
            status_code=status.HTTP_404_NOT_FOUND,
            error_code="MARKET_ITEM_NOT_FOUND",
            message=f"市场中未找到插件 slug={slug}",
        )
    zip_url = item.get("zip_url")
    if not isinstance(zip_url, str) or not zip_url:
        raise AppException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            error_code="MARKET_ITEM_MISSING_ZIP_URL",
            message=f"市场条目 {slug} 缺少 zip_url 字段",
        )
    checksum = item.get("checksum_sha256")
    payload = PluginInstallFrom(
        source="remote",
        slug=slug,
        remote=PackageInstallRemote(
            url=zip_url,
            checksum_sha256=checksum if isinstance(checksum, str) and checksum else None,
            allow_pre_release=bool(item.get("allow_pre_release")),
        ),
    )
    pm = _get_plugin_manager()
    row = await pm.install_from_remote(db, payload)
    await db.commit()
    await db.refresh(row)
    return {"success": True, "data": PluginOut.model_validate(row)}


# ═══════════════════════════════════════════════════════════════════════════
# 下方路由均依赖 {slug}：放在固定段路由之后（避免按注册顺序匹配时被误吞）
# ═══════════════════════════════════════════════════════════════════════════


@router.get("/{slug}")
async def get_plugin_detail(
    db: DB,
    current_user: CurrentStaff,
    slug: str,
):
    pm = _get_plugin_manager()
    plugin = await pm.get(db, slug)
    if plugin is None:
        raise AppException(
            status_code=status.HTTP_404_NOT_FOUND,
            message=f"插件不存在: {slug}",
            error_code=PLUGIN_NOT_FOUND,
        )
    out = PluginOut.model_validate(plugin)
    try:
        out.settings = await pm.get_settings(db, slug)
    except Exception:
        out.settings = None
    return {"success": True, "data": out}


@router.post("/scan")
async def scan_local_plugins(
    db: DB,
    current_user: CurrentStaff,
):
    pm = _get_plugin_manager()
    added, refreshed = await pm.scan_local(db)
    await db.commit()
    return {
        "success": True,
        "message": f"扫描完成，新增 {added}，更新 {refreshed}",
        "data": {"added": added, "refreshed": refreshed},
    }


@router.post("")
async def install_plugin(
    request: Request,
    db: DB,
    current_user: CurrentStaff,
    source: Literal["local", "remote", "upload"] = Query(
        "local",
        description="安装来源：local=本地目录扫描、upload=zip 文件上传、remote=从市场 URL 下载",
    ),
):
    """统一安装入口。三种来源互斥，由 query 参数 `source` 决定分支。

    由于同一签名同时声明 Body(...) + File(...) 会强制 multipart/form-data，
    导致 upload 与 remote/local 请求互斥，故此处基于 Request 手动解析：
    - ``upload`` 来源：按 multipart/form-data 读取 ``file`` 字段
    - 其他来源：按 application/json 读取 body → Pydantic ``PluginInstallFrom``
    """
    import json as _json

    from fastapi import UploadFile as _UploadFile  # noqa: F401  (保留以便未来扩展)

    pm = _get_plugin_manager()

    # ── upload：multipart/form-data，取 file ──────────────────────────
    if source == "upload":
        form = await request.form()
        uploaded = form.get("file")
        # Starlette 实际返回 starlette.datastructures.UploadFile；FastAPI UploadFile
        # 是其别名，但在 httpx ASGITransport + direct Request.form() 下未必一致。
        # 采用鸭子类型：非 None + 具有 read() 异步方法即视为上传文件。
        if uploaded is None or not hasattr(uploaded, "read"):
            raise AppException(
                status_code=status.HTTP_400_BAD_REQUEST,
                message="source=upload 时必须通过 multipart/form-data 提供 file 字段",
                error_code="PACKAGE_UPLOAD_FILE_REQUIRED",
            )
        data = await uploaded.read()
        filename = uploaded.filename or "plugin.zip"
        row = await pm.install_from_uploaded_bytes(db, filename, data)
        await db.commit()
        await db.refresh(row)
        return {"success": True, "data": PluginOut.model_validate(row)}

    # ── local / remote：JSON body ─────────────────────────────────────
    raw = await request.body()
    if not raw:
        payload = None
    else:
        try:
            payload = PluginInstallFrom.model_validate(_json.loads(raw.decode("utf-8")))
        except Exception as e:  # noqa: BLE001
            raise AppException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                message=f"JSON body 校验失败: {e}",
                error_code="PAYLOAD_INVALID",
            ) from e

    if source == "local":
        slug = getattr(payload, "slug", None) if payload else None
        if not slug:
            raise AppException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                message="source=local 时必须通过 JSON body 提供 slug 字段",
                error_code="PLUGIN_SLUG_REQUIRED",
            )
        plugin = await pm.install_local(db, slug)
        await db.commit()
        return {"success": True, "data": PluginOut.model_validate(plugin)}

    if source == "remote":
        if payload is None or not getattr(payload, "remote", None):
            raise AppException(
                status_code=status.HTTP_400_BAD_REQUEST,
                message="source=remote 时必须通过 JSON body 提供 {remote:{url,checksum_sha256?}}",
                error_code="REMOTE_INFO_MISSING",
            )
        row = await pm.install_from_remote(db, payload)
        await db.commit()
        await db.refresh(row)
        return {"success": True, "data": PluginOut.model_validate(row)}

    raise AppException(
        status_code=status.HTTP_400_BAD_REQUEST,
        message=f"未知 source={source}",
        error_code="INVALID_INSTALL_SOURCE",
    )


@router.patch("/{slug}/status")
async def toggle_plugin_status(
    db: DB,
    current_user: CurrentStaff,
    slug: str,
    payload: PluginStatusToggleIn,
):
    """切换插件启用状态。

    幂等：若插件已处于目标状态，直接返回当前记录（不抛 4xx），
    保证客户端重试与前端 Switch 组件二次触发安全。
    """
    pm = _get_plugin_manager()
    plugin = await pm.get(db, slug)
    if plugin is None:
        raise AppException(
            status_code=status.HTTP_404_NOT_FOUND,
            message=f"插件不存在: {slug}",
            error_code=PLUGIN_NOT_FOUND,
        )
    is_active = plugin.status == "active"
    if payload.enabled == is_active:
        return {
            "success": True,
            "message": "插件已处于目标状态",
            "data": PluginOut.model_validate(plugin),
        }
    if payload.enabled:
        result = await pm.activate(db, slug)
    else:
        result = await pm.deactivate(db, slug)
    await db.commit()
    return {"success": True, "data": PluginOut.model_validate(result)}


@router.get("/{slug}/settings")
async def get_plugin_settings(
    db: DB,
    current_user: CurrentStaff,
    slug: str,
):
    pm = _get_plugin_manager()
    plugin = await pm.get(db, slug)
    if plugin is None:
        raise AppException(
            status_code=status.HTTP_404_NOT_FOUND,
            message=f"插件不存在: {slug}",
            error_code=PLUGIN_NOT_FOUND,
        )
    data = await pm.get_settings(db, slug)
    return {"success": True, "data": data}


@router.put("/{slug}/settings")
async def replace_plugin_settings(
    db: DB,
    current_user: CurrentStaff,
    slug: str,
    payload: PluginConfigIn,
):
    pm = _get_plugin_manager()
    plugin = await pm.get(db, slug)
    if plugin is None:
        raise AppException(
            status_code=status.HTTP_404_NOT_FOUND,
            message=f"插件不存在: {slug}",
            error_code=PLUGIN_NOT_FOUND,
        )
    # PUT 语义：先读取 schema 默认值，再用 payload.settings 覆盖（等同于重置为默认后应用 payload）
    settings = await pm.get_settings(db, slug)
    merged = {
        k: (v.get("default") if isinstance(v, dict) and "default" in v else None)
        for k, v in ((getattr(plugin, "settings_schema", None) or {}).get("properties") or {}).items()
        if isinstance(v, dict)
    }
    if isinstance(payload.settings, dict):
        merged.update(payload.settings)
    try:
        saved = await pm.set_settings(db, slug, merged)
    except Exception as e:
        raise AppException(
            status_code=status.HTTP_400_BAD_REQUEST,
            message=f"插件设置无效: {e}",
            error_code=PLUGIN_SETTINGS_INVALID,
        )
    await db.commit()
    return {"success": True, "data": saved}


@router.patch("/{slug}/settings")
async def update_plugin_settings(
    db: DB,
    current_user: CurrentStaff,
    slug: str,
    payload: PluginConfigIn,
):
    pm = _get_plugin_manager()
    plugin = await pm.get(db, slug)
    if plugin is None:
        raise AppException(
            status_code=status.HTTP_404_NOT_FOUND,
            message=f"插件不存在: {slug}",
            error_code=PLUGIN_NOT_FOUND,
        )
    try:
        saved = await pm.set_settings(db, slug, payload.settings)
    except Exception as e:
        raise AppException(
            status_code=status.HTTP_400_BAD_REQUEST,
            message=f"插件设置无效: {e}",
            error_code=PLUGIN_SETTINGS_INVALID,
        )
    await db.commit()
    return {"success": True, "data": saved}


@router.post("/{slug}/activate")
async def activate_plugin(
    db: DB,
    current_user: CurrentStaff,
    slug: str,
):
    pm = _get_plugin_manager()
    plugin = await pm.get(db, slug)
    if plugin is None:
        raise AppException(
            status_code=status.HTTP_404_NOT_FOUND,
            message=f"插件不存在: {slug}",
            error_code=PLUGIN_NOT_FOUND,
        )
    if plugin.status == "active":
        return {"success": True, "message": "插件已处于激活态", "data": PluginOut.model_validate(plugin)}
    result = await pm.activate(db, slug)
    await db.commit()
    return {"success": True, "data": PluginOut.model_validate(result)}


@router.post("/{slug}/deactivate")
async def deactivate_plugin(
    db: DB,
    current_user: CurrentStaff,
    slug: str,
):
    pm = _get_plugin_manager()
    plugin = await pm.get(db, slug)
    if plugin is None:
        raise AppException(
            status_code=status.HTTP_404_NOT_FOUND,
            message=f"插件不存在: {slug}",
            error_code=PLUGIN_NOT_FOUND,
        )
    if plugin.status != "active":
        return {"success": True, "message": "插件已处于禁用态", "data": PluginOut.model_validate(plugin)}
    result = await pm.deactivate(db, slug)
    await db.commit()
    return {"success": True, "data": PluginOut.model_validate(result)}


@router.post("/bulk")
async def bulk_plugin_operation(
    db: DB,
    current_user: CurrentStaff,
    payload: PluginBulkIn,
):
    pm = _get_plugin_manager()
    result = await pm.bulk(db, payload.action, payload.slugs)
    await db.commit()
    return {"success": True, "data": result}


@router.delete("/{slug}")
async def delete_plugin(
    db: DB,
    current_user: CurrentStaff,
    slug: str,
):
    pm = _get_plugin_manager()
    plugin = await pm.get(db, slug)
    if plugin is None:
        raise AppException(
            status_code=status.HTTP_404_NOT_FOUND,
            message=f"插件不存在: {slug}",
            error_code=PLUGIN_NOT_FOUND,
        )
    await pm.delete(db, slug)
    await db.commit()
    return {"success": True, "message": "已删除"}


@router.post("/{slug}/upgrade")
async def upgrade_plugin(
    db: DB,
    current_user: CurrentStaff,
    slug: str,
):
    pm = _get_plugin_manager()
    plugin = await pm.get(db, slug)
    if plugin is None:
        raise AppException(
            status_code=status.HTTP_404_NOT_FOUND,
            message=f"插件不存在: {slug}",
            error_code=PLUGIN_NOT_FOUND,
        )
    await pm.upgrade(db, slug)
    await db.commit()
    return {"success": True, "message": "升级完成 (stub)"}


@router.get("/menu-registry")
async def list_plugin_menu_registry(
    db: DB,
    current_user: CurrentStaff,
):
    """返回已激活插件声明的后台菜单项（Sidebar「插件」分组用）。

    返回字段：
    - ``items``: ``[{slug, label, icon, path, admin_route_prefix, badge?}]`` 列表
    - ``admin_route_prefix``: 插件后台路由的固定前缀 ``/api/admin/plugins/{slug}``
    """
    from backend.core.routing_registry import routing_registry

    items: list[dict] = []
    for entry in routing_registry.list_menu():
        slug = entry["slug"]
        enriched = dict(entry)
        enriched["admin_route_prefix"] = f"/api/admin/plugins/{slug}"
        items.append(enriched)
    return {
        "success": True,
        "data": {
            "items": items,
            "total": len(items),
        },
    }
