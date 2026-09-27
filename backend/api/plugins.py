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

import logging
from typing import Literal

from fastapi import APIRouter, Query, Request, status

from backend.core.auth import DB, CurrentStaff
from backend.core.cache import invalidate_cache
from backend.core.exceptions import AppException
from backend.schemas.extensions import (
    PackageMessageResponse,
    PluginBulkIn,
    PluginBulkResponse,
    PluginConfigIn,
    PluginDeactivateResponse,
    PluginDetailResponse,
    PluginInstallFrom,
    PluginListResponse,
    PluginMarketResponse,
    PluginMenuRegistryResponse,
    PluginOut,
    PluginScanResponse,
    PluginSettingsResponse,
    PluginStatusToggleIn,
)

PLUGIN_NOT_FOUND = "PLUGIN_NOT_FOUND"
PLUGIN_ALREADY_ACTIVE = "PLUGIN_ALREADY_ACTIVE"
PLUGIN_SETTINGS_INVALID = "PLUGIN_SETTINGS_INVALID"

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/plugins", tags=["插件平台"])


def _get_plugin_manager():
    from backend.core.extensions import plugin_manager

    return plugin_manager


async def _invalidate_rendered_content(*, reason: str) -> None:
    """插件钩子/设置变化后，抹掉一切嵌有插件渲染结果的缓存。

    插件挂在 the_content / the_excerpt 上的 filter 输出会进详情（``post:{slug}:{lang}``）、
    列表与 RSS（``posts*``，RSS 刻意挂该前缀）响应缓存，以及 Nitro 页面缓存。
    启停/改设置不清 = 访客在 TTL（最长 10 分钟）内仍看到旧钩子集的渲染，
    后台拨了开关却没效果——插件前后端协同的最后一公里就是这里。
    """
    from backend.services.frontend_cache_purge import purge_frontend_page_cache

    await invalidate_cache("post:")  # 详情键不在 posts 前缀下，必须单独清
    await invalidate_cache("posts")  # 列表 + RSS
    purge_frontend_page_cache(f"plugin:{reason}")


# ═══════════════════════════════════════════════════════════════════════════
# 注意：FastAPI 的 `/{slug}` 路径参数不会吞掉 `/menu-registry` 这样的「固定段」
# 路由（Starlette 按注册顺序 + 静态段优先匹配）。但为了防御性编程，所有不依赖
# slug 参数的固定路径仍统一放在 `@router.get("")` 之后、`@router.get("/{slug}")`
# 之前 —— 保证在任何 URL 匹配策略下都先落到真实 handler。
# ═══════════════════════════════════════════════════════════════════════════


@router.get(
    "",
    summary="获取插件列表（管理员）",
    description=(
        "需 CurrentStaff。按 status（inactive|active|error|installed）与 search（名称/slug 模糊）"
        "过滤分页（默认 20 条/页，上限 100）。每项附带当前 settings"
        "（单插件读取失败时置 null，不影响整体列表）。"
    ),
    responses={200: {"model": PluginListResponse}},
)
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
        except Exception as exc:
            logger.warning("list_plugins: 读取 %s settings 失败，已置 null: %s", p.slug, exc)
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


@router.get(
    "/menu-registry",
    summary="获取插件后台菜单注册表",
    description=(
        "需 CurrentStaff。返回已激活插件经 routing_registry 声明的后台菜单项"
        "（Sidebar「插件」分组数据源），每项附带其 admin_route_prefix。只读、幂等。"
    ),
    responses={200: {"model": PluginMenuRegistryResponse}},
)
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


@router.post(
    "/scan",
    summary="扫描本地插件目录",
    description=(
        "需 CurrentStaff。扫描 backend/plugins/*/rosetta-plugin.json 与 DB 对齐："
        "登记新插件、刷新清单变更。返回 added/refreshed 计数。幂等，可安全重复调用。"
    ),
    responses={200: {"model": PluginScanResponse}},
)
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


@router.post(
    "/bulk",
    summary="批量插件操作",
    description=(
        "需 CurrentStaff。请求体 {action: activate|deactivate|delete|upgrade, slugs:[...]}，"
        "action 越界在 Pydantic 层即 422（VALIDATION_ERROR）。"
        "逐插件执行：单个失败不中断整体，失败项以 {slug, error_code, message} 汇总在 data 中返回。"
    ),
    responses={200: {"model": PluginBulkResponse}},
)
async def bulk_plugin_operation(
    db: DB,
    current_user: CurrentStaff,
    payload: PluginBulkIn,
):
    pm = _get_plugin_manager()
    result = await pm.bulk(db, payload.action, payload.slugs)
    await db.commit()
    await _invalidate_rendered_content(reason=f"bulk:{payload.action}")
    return {"success": True, "data": result}


# ═══════════════════════════════════════════════════════════════════════════
# 市场（Market）索引 + 一键安装
# ═══════════════════════════════════════════════════════════════════════════


@router.get(
    "/market",
    summary="获取插件市场索引",
    description=(
        "需 CurrentStaff。返回远端插件市场索引（本地缓存 8 小时），force=true 跳过缓存重新拉取。"
        "响应附带 items 列表、total 与 cached_at。"
    ),
    responses={200: {"model": PluginMarketResponse}},
)
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


@router.post(
    "/market/{slug}/install",
    summary="从市场一键安装插件",
    description=(
        "需 CurrentStaff。在市场索引（本地缓存 8h）中按 slug 查找条目，"
        "复用 install_from_remote 通道下载 zip 并安装（含 SHA-256 校验与 pre-release 开关）。"
        "索引缺 items 时 502（MARKET_INDEX_INVALID）；市场无该 slug 时 404（MARKET_ITEM_NOT_FOUND）；"
        "条目缺 zip_url 时 502（MARKET_ITEM_MISSING_ZIP_URL）。"
    ),
    responses={
        200: {"model": PluginDetailResponse},
        404: {"description": "市场中未找到该插件（error_code: MARKET_ITEM_NOT_FOUND）"},
        502: {
            "description": "市场索引异常或缺 zip_url（error_code: MARKET_INDEX_INVALID / MARKET_ITEM_MISSING_ZIP_URL）"
        },
    },
)
async def install_plugin_from_market(
    db: DB,
    current_user: CurrentStaff,
    slug: str,
):
    """在市场索引中按 slug 查找条目，然后调用 install_from_remote 安装。"""
    from backend.core.exceptions import AppException
    from backend.core.market import fetch_market_index
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


@router.get(
    "/{slug}",
    summary="获取插件详情（管理员）",
    description=(
        "需 CurrentStaff。返回插件记录（PluginOut）并附带当前 settings；"
        "settings 读取失败时置 null 而不报错。未安装时 404（error_code: PLUGIN_NOT_FOUND）。"
    ),
    responses={
        200: {"model": PluginDetailResponse},
        404: {"description": "插件不存在（error_code: PLUGIN_NOT_FOUND）"},
    },
)
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
    except Exception as exc:
        logger.warning("get_plugin_detail: 读取 %s settings 失败，已置 null: %s", slug, exc)
        out.settings = None
    return {"success": True, "data": out}


@router.post(
    "",
    summary="安装插件（local / upload / remote）",
    description=(
        "需 CurrentStaff。统一安装入口，由 query 参数 source 决定分支："
        "local=按 JSON body 的 slug 扫描本地目录并登记；upload=multipart/form-data 上传 zip"
        "（缺 file 字段 400 PACKAGE_UPLOAD_FILE_REQUIRED）；remote=按 {remote:{url,checksum_sha256?}}"
        "下载 zip 安装（缺 remote 400 REMOTE_INFO_MISSING）。"
        "JSON body 校验失败 422（PAYLOAD_INVALID）；source=local 缺 slug 422（PLUGIN_SLUG_REQUIRED）；"
        "未知 source 400（INVALID_INSTALL_SOURCE）。成功后返回安装完成的插件记录。"
    ),
    responses={200: {"model": PluginDetailResponse}},
)
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


@router.patch(
    "/{slug}/status",
    summary="切换插件启用状态",
    description=(
        "需 CurrentStaff。请求体 {enabled: true|false}。幂等：插件已处于目标状态时"
        "直接返回现状并附 message，不抛 4xx，保证前端 Switch 二次触发与客户端重试安全。"
        "状态真实变化时失效文章详情/列表/RSS 与前端页面缓存，钩子渲染结果即刻生效。"
        "未安装时 404（error_code: PLUGIN_NOT_FOUND）。"
    ),
    responses={
        200: {"model": PluginDetailResponse},
        404: {"description": "插件不存在（error_code: PLUGIN_NOT_FOUND）"},
    },
)
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
    await _invalidate_rendered_content(reason=f"{slug}:toggle")
    return {"success": True, "data": PluginOut.model_validate(result)}


@router.get(
    "/{slug}/settings",
    summary="获取插件设置",
    description=(
        "需 CurrentStaff。返回该插件在 SiteConfig 中持久化的 settings（已应用 schema 默认值）。"
        "未安装时 404（error_code: PLUGIN_NOT_FOUND）。"
    ),
    responses={
        200: {"model": PluginSettingsResponse},
        404: {"description": "插件不存在（error_code: PLUGIN_NOT_FOUND）"},
    },
)
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


@router.put(
    "/{slug}/settings",
    summary="全量替换插件设置",
    description=(
        "需 CurrentStaff。PUT 全量替换语义：先重置为 settings_schema 声明的默认值，"
        "再叠加 payload.settings 后整体保存。保存后立即刷新插件运行时 settings 快照"
        "（plugin_loader.set_settings_snapshot），无需重启；"
        "并失效已渲染文章缓存（设置可影响 filter 输出）。"
        "未安装 404（PLUGIN_NOT_FOUND）；保存校验失败 400（PLUGIN_SETTINGS_INVALID）。"
    ),
    responses={
        200: {"model": PluginSettingsResponse},
        404: {"description": "插件不存在（error_code: PLUGIN_NOT_FOUND）"},
    },
)
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
    await pm.get_settings(db, slug)
    merged = {
        k: (v.get("default") if isinstance(v, dict) and "default" in v else None)
        for k, v in (
            (getattr(plugin, "settings_schema", None) or {}).get("properties") or {}
        ).items()
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
    from backend.core.plugin_loader import set_settings_snapshot

    set_settings_snapshot(slug, saved)
    await _invalidate_rendered_content(reason=f"{slug}:settings")
    return {"success": True, "data": saved}


@router.patch(
    "/{slug}/settings",
    summary="增量更新插件设置",
    description=(
        "需 CurrentStaff。仅覆盖 payload.settings 中出现的键，其余保持现值。"
        "保存后立即刷新运行时 settings 快照，并失效已渲染文章缓存。"
        "未安装 404（PLUGIN_NOT_FOUND）；保存校验失败 400（PLUGIN_SETTINGS_INVALID）。"
    ),
    responses={
        200: {"model": PluginSettingsResponse},
        404: {"description": "插件不存在（error_code: PLUGIN_NOT_FOUND）"},
    },
)
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
    from backend.core.plugin_loader import set_settings_snapshot

    set_settings_snapshot(slug, saved)
    await _invalidate_rendered_content(reason=f"{slug}:settings")
    return {"success": True, "data": saved}


@router.post(
    "/{slug}/activate",
    summary="激活插件",
    description=(
        "需 CurrentStaff。加载插件包并执行 register/activate 钩子（Bus 模式，见 core/plugin_loader + plugin_bus）。"
        "幂等：已激活时直接返回现状（success=true，不报错）。激活后失效已渲染文章缓存。"
        "未安装 404（PLUGIN_NOT_FOUND）；导入/初始化失败 500（PLUGIN_IMPORT_ERROR）。"
    ),
    responses={
        200: {"model": PluginDetailResponse},
        404: {"description": "插件不存在（error_code: PLUGIN_NOT_FOUND）"},
    },
)
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
        return {
            "success": True,
            "message": "插件已处于激活态",
            "data": PluginOut.model_validate(plugin),
        }
    result = await pm.activate(db, slug)
    await db.commit()
    await _invalidate_rendered_content(reason=f"{slug}:activate")
    return {"success": True, "data": PluginOut.model_validate(result)}


@router.post(
    "/{slug}/deactivate",
    summary="停用插件",
    description=(
        "需 CurrentStaff。执行插件 deactivate 钩子并置为禁用态。"
        "幂等：本就未激活时直接返回现状（success=true，不报错）。停用后失效已渲染文章缓存。"
        "未安装时 404（error_code: PLUGIN_NOT_FOUND）。"
    ),
    responses={
        200: {"model": PluginDeactivateResponse},
        404: {"description": "插件不存在（error_code: PLUGIN_NOT_FOUND）"},
    },
)
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
        return {
            "success": True,
            "message": "插件已处于禁用态",
            "data": PluginOut.model_validate(plugin),
        }
    result = await pm.deactivate(db, slug)
    await db.commit()
    await _invalidate_rendered_content(reason=f"{slug}:deactivate")
    return {"success": True, "data": result}


@router.delete(
    "/{slug}",
    summary="删除插件",
    description=(
        "需 CurrentStaff。删除 DB 记录与 settings KV；仅安装态（非 active）可删，"
        "激活中返回 409（PLUGIN_ALREADY_ACTIVE，需先停用）。"
        "未安装时 404（error_code: PLUGIN_NOT_FOUND）。"
    ),
    responses={
        200: {"model": PackageMessageResponse},
        404: {"description": "插件不存在（error_code: PLUGIN_NOT_FOUND）"},
        409: {"description": "插件处于激活态，禁止删除（error_code: PLUGIN_ALREADY_ACTIVE）"},
    },
)
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


@router.post(
    "/{slug}/upgrade",
    summary="升级插件（stub）",
    description=(
        "需 CurrentStaff。当前为占位实现：仅刷新 updated_at 并触发 plugin.upgraded 钩子，"
        "响应 message 标注 stub；真正的版本替换请走 zip 覆盖安装（POST /plugins?source=upload|remote）。"
        "未安装时 404（error_code: PLUGIN_NOT_FOUND）。"
    ),
    responses={
        200: {"model": PackageMessageResponse},
        404: {"description": "插件不存在（error_code: PLUGIN_NOT_FOUND）"},
    },
)
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
