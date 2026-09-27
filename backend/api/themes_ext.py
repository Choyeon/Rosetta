"""
主题扩展 REST API (挂载于 /api/admin)

WordPress 风格主题管理接口：
- GET   /themes             管理员列表
- GET   /themes/{slug}      管理员详情
- PUT   /themes/{slug}/activate
- DELETE /themes/{slug}
- POST  /themes/scan
- GET   /themes/{slug}/mods
- PUT   /themes/{slug}/mods   全量替换（重置为 schema 默认值再写入）
- PATCH /themes/{slug}/mods   增量更新
- POST  /themes            安装（local / remote / upload）
- POST  /themes/{slug}/upgrade

注意：公开侧 ``GET /api/themes/active``（供前台 useFrontendTheme 消费）
定义在 ``backend/api/themes.py``，本模块不再重复提供 active 查询端点。
"""

from __future__ import annotations

from typing import Any, Literal

from fastapi import APIRouter, Query, Request, status
from sqlalchemy import select

from backend.core.auth import DB, CurrentStaff
from backend.core.exceptions import AppException
from backend.core.tenant import DEFAULT_SITE_ID
from backend.models.extensions import Theme
from backend.schemas.extensions import (
    PackageMessageResponse,
    ThemeDetailResponse,
    ThemeInstallFrom,
    ThemeListResponse,
    ThemeMarketResponse,
    ThemeModsIn,
    ThemeModsResponse,
    ThemeModsSavedResponse,
    ThemeOut,
    ThemeScanResponse,
)
from backend.services.frontend_cache_purge import purge_frontend_page_cache

THEME_NOT_FOUND = "THEME_NOT_FOUND"

router = APIRouter(prefix="/themes", tags=["主题平台"])


def _get_theme_manager():
    from backend.core.extensions import theme_manager

    return theme_manager


async def _load_theme_row(db: DB, slug: str, *, site_id: int = DEFAULT_SITE_ID) -> Theme:
    """Load an ORM row and force fresh SQL read so datetime / JSON columns are
    concrete Python values. This avoids Pydantic ``from_attributes`` triggering
    lazy attribute access (MissingGreenlet).

    ``populate_existing`` + ``with_for_update`` are intentionally omitted here:
    after ``commit``, ``select`` already bypasses session cache. The mandatory
    ``db.refresh`` call then replaces any stale ``func.now()`` expressions
    inside attributes with real values.
    """
    stmt = (
        select(Theme)
        .execution_options(populate_existing=True, autoflush=False)
        .where(Theme.site_id == site_id, Theme.slug == slug)
    )
    row = (await db.execute(stmt)).scalar_one_or_none()
    if row is None:
        raise AppException(
            status_code=status.HTTP_404_NOT_FOUND,
            message=f"主题不存在: {slug}",
            error_code=THEME_NOT_FOUND,
        )
    await db.refresh(
        row,
        attribute_names=[
            "updated_at",
            "created_at",
            "activated_at",
            "installed_at",
            "screenshot_urls",
            "tags",
            "mods_schema",
        ],
    )
    return row


@router.get(
    "",
    summary="获取主题列表（管理员）",
    description=(
        "需 CurrentStaff。按 status（inactive|active|error|installed）与 search（名称/slug 模糊）"
        "过滤分页（默认 50 条/页，上限 200）。每项附带该主题当前生效的 mods 值"
        "（schema 默认值与 DB 存储值合并结果），供后台主题管理卡片渲染。"
    ),
    responses={200: {"model": ThemeListResponse}},
)
async def list_admin_themes(
    db: DB,
    current_user: CurrentStaff,
    status: str | None = Query(None, description="按状态过滤：inactive|active|error|installed"),
    search: str | None = Query(None, description="搜索名称或 slug"),
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=200),
):
    tm = _get_theme_manager()
    themes, total = await tm.list(db, status=status, search=search, page=page, per_page=per_page)
    mods_map = await tm.get_mods_bulk(db, [t.slug for t in themes])
    data = []
    for t in themes:
        out = ThemeOut.model_validate(t)
        out.mods = mods_map.get(t.slug, {})
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


# ═══════════════════════════════════════════════════════════════════════════
# 市场索引（固定段路由，必须在 /{slug} 之前注册）
# ═══════════════════════════════════════════════════════════════════════════


@router.get(
    "/market",
    summary="获取主题市场索引",
    description=(
        "需 CurrentStaff。返回远端主题市场索引（本地缓存 8 小时），force=true 跳过缓存重拉。"
        "响应附带 items 列表、total 与 cached_at（缓存时间戳，便于前端展示数据新鲜度）。"
    ),
    responses={200: {"model": ThemeMarketResponse}},
)
async def list_theme_market(
    current_user: CurrentStaff,
    force: bool = Query(False, description="true=跳过本地 8h 缓存重新拉远端"),
):
    from backend.core.market import fetch_market_index

    data = await fetch_market_index("themes", force=force)
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


@router.get(
    "/{slug}",
    summary="获取主题详情（管理员）",
    description=(
        "需 CurrentStaff。返回主题完整记录（含 mods_schema 与当前 mods 值）。"
        "主题未安装时返回 404（error_code: THEME_NOT_FOUND）。"
    ),
    responses={
        200: {"model": ThemeDetailResponse},
        404: {"description": "主题不存在（error_code: THEME_NOT_FOUND）"},
    },
)
async def get_theme_detail(
    db: DB,
    current_user: CurrentStaff,
    slug: str,
):
    tm = _get_theme_manager()
    theme = await tm.get(db, slug)
    if theme is None:
        raise AppException(
            status_code=status.HTTP_404_NOT_FOUND,
            message=f"主题不存在: {slug}",
            error_code=THEME_NOT_FOUND,
        )
    out = ThemeOut.model_validate(theme)
    out.mods = await tm.get_mods(db, theme.slug)
    return {"success": True, "data": out}


@router.put(
    "/{slug}/activate",
    summary="激活主题",
    description=(
        "需 CurrentStaff。同一站点同时只有一个激活主题：激活新主题时旧激活项自动降为 installed。"
        "幂等：目标主题已激活时直接返回现状（不刷新 activated_at、不重放钩子）。"
        "成功后清空前台页面缓存，前台经 GET /api/themes/active 拉取新 slug 与 mods。"
    ),
    responses={
        200: {"model": ThemeDetailResponse},
        404: {"description": "主题未安装（error_code: THEME_NOT_FOUND）"},
    },
)
async def activate_theme(
    db: DB,
    current_user: CurrentStaff,
    slug: str,
):
    tm = _get_theme_manager()
    theme = await tm.get(db, slug)
    if theme is None:
        raise AppException(
            status_code=status.HTTP_404_NOT_FOUND,
            message=f"主题不存在: {slug}",
            error_code=THEME_NOT_FOUND,
        )
    result = await tm.activate(db, slug)
    # Commit FIRST: onupdate=func.now() columns are evaluated server-side only
    # on commit.  After commit, re-issue a SELECT then explicitly refresh
    # columns that SQLAlchemy's asyncio ORM could otherwise leave as deferred /
    # stale expressions — this prevents MissingGreenlet when Pydantic reads
    # ``updated_at`` during ThemeOut.model_validate.
    await db.commit()
    purge_frontend_page_cache(f"主题激活: {slug}")
    theme = await _load_theme_row(db, result.slug)

    # Build response WITHOUT using from_attributes on the live ORM object.
    # The async ORM attributes carry greenlet state and can fail when Pydantic
    # reads them synchronously; convert to a plain dict first.
    raw: dict[str, Any] = {
        "id": int(theme.id),
        "slug": str(theme.slug),
        "name": str(theme.name),
        "version": str(theme.version),
        "author": theme.author,
        "description": theme.description,
        "theme_uri": theme.theme_uri,
        "author_uri": theme.author_uri,
        "textdomain": theme.textdomain,
        "requires_rosetta": theme.requires_rosetta,
        "folder": theme.folder,
        "parent_theme": theme.parent_theme,
        "status": str(theme.status),
        "is_active": bool(theme.is_active),
        "manifest_version": str(getattr(theme, "manifest_version", "1.0") or "1.0"),
        "update_available": bool(getattr(theme, "update_available", False)),
        "error_message": theme.error_message,
    }
    # DateTime columns — access only after refresh above (otherwise raises
    # MissingGreenlet on asyncio greenlets that were never spawned).
    raw["updated_at"] = theme.updated_at
    raw["created_at"] = theme.created_at
    raw["installed_at"] = theme.installed_at
    raw["activated_at"] = theme.activated_at
    # JSON columns → already dict/list after refresh.
    raw["screenshot_urls"] = list(theme.screenshot_urls or [])
    raw["tags"] = list(theme.tags or [])
    raw["mods_schema"] = dict(theme.mods_schema) if theme.mods_schema else None

    out = ThemeOut(**raw)
    out.mods = await tm.get_mods(db, result.slug)
    return {"success": True, "data": out}


@router.delete(
    "/{slug}",
    summary="删除主题记录",
    description=(
        "需 CurrentStaff。404/409 判定统一在 ThemeManager.delete 内：未安装 → 404 THEME_NOT_FOUND；"
        "仍为激活主题 → 409 THEME_ALREADY_ACTIVE（须先激活其他主题）。"
        "仅清除 DB 记录，不删除磁盘文件（磁盘 ↔ DB 由扫描同步）。"
    ),
    responses={
        200: {"model": PackageMessageResponse},
        404: {"description": "主题未安装（error_code: THEME_NOT_FOUND）"},
        409: {"description": "主题处于激活态，禁止删除（error_code: THEME_ALREADY_ACTIVE）"},
    },
)
async def delete_theme(
    db: DB,
    current_user: CurrentStaff,
    slug: str,
):
    tm = _get_theme_manager()
    # 404 / 409（激活中禁止删除）的判定统一在 ThemeManager.delete 内，
    # API 层不再重复检查 is_active（曾出现 400 vs 409 双标）。
    await tm.delete(db, slug)
    await db.commit()
    return {"success": True, "message": "已删除"}


@router.post(
    "/scan",
    summary="扫描本地主题目录",
    description=(
        "需 CurrentStaff。扫描 frontend/themes/*/rosetta-theme.json 与 DB 对齐："
        "新增未登记主题、刷新清单变更（version/mods_schema 等）、"
        "清理非激活且磁盘已不存在的僵尸记录。返回 added/refreshed/removed 计数。幂等。"
    ),
    responses={200: {"model": ThemeScanResponse}},
)
async def scan_local_themes(
    db: DB,
    current_user: CurrentStaff,
):
    tm = _get_theme_manager()
    added, refreshed, removed = await tm.scan_local(db)
    await db.commit()
    return {
        "success": True,
        "message": f"扫描完成，新增 {added}，更新 {refreshed}，清理僵尸 {len(removed)}",
        "data": {"added": added, "refreshed": refreshed, "removed": removed},
    }


@router.get(
    "/{slug}/mods",
    summary="获取主题 Mods 与 Schema",
    description=(
        "需 CurrentStaff。返回 mods（schema 默认值与 DB 已存值的合并结果）与 mods_schema"
        "（JSON Schema Draft-07）。mods_schema.properties 是 Customizer 控件的唯一清单。"
    ),
    responses={
        200: {"model": ThemeModsResponse},
        404: {"description": "主题未安装（error_code: THEME_NOT_FOUND）"},
    },
)
async def get_theme_mods(
    db: DB,
    current_user: CurrentStaff,
    slug: str,
):
    tm = _get_theme_manager()
    theme = await tm.get(db, slug)
    if theme is None:
        raise AppException(
            status_code=status.HTTP_404_NOT_FOUND,
            message=f"主题不存在: {slug}",
            error_code=THEME_NOT_FOUND,
        )
    mods = await tm.get_mods(db, slug)
    return {
        "success": True,
        "data": {
            "mods": mods,
            "mods_schema": theme.mods_schema,
        },
    }


@router.put(
    "/{slug}/mods",
    summary="全量替换主题 Mods",
    description=(
        "需 CurrentStaff。PUT 全量替换语义：先重置为 mods_schema 声明的默认值，再叠加 payload.mods。"
        "schema 未声明的键被静默丢弃（仅记 warning，不整单拒绝）；payload 非 JSON 对象返回 422"
        "（error_code: THEME_MODS_INVALID）。写入 SiteConfig KV theme_mods:<slug>，"
        "成功后清空前台页面缓存。"
    ),
    responses={
        200: {"model": ThemeModsSavedResponse},
        404: {"description": "主题未安装（error_code: THEME_NOT_FOUND）"},
    },
)
async def replace_theme_mods(
    db: DB,
    current_user: CurrentStaff,
    slug: str,
    payload: ThemeModsIn,
):
    tm = _get_theme_manager()
    theme = await tm.get(db, slug)
    if theme is None:
        raise AppException(
            status_code=status.HTTP_404_NOT_FOUND,
            message=f"主题不存在: {slug}",
            error_code=THEME_NOT_FOUND,
        )
    # PUT 全量替换语义：manager 内先重置为 schema 默认值再叠加 payload，
    # 并丢弃 schema 未声明的键。校验失败时 AppException（含 MODS_SCHEMA_VIOLATION
    # 等精确 error_code）直接透传，不再统一改写成 THEME_MODS_INVALID。
    saved = await tm.set_mods(db, slug, payload.mods or {}, replace=True)
    await db.commit()
    purge_frontend_page_cache(f"主题 mods 全量替换: {slug}")
    return {"success": True, "data": saved}


@router.patch(
    "/{slug}/mods",
    summary="增量更新主题 Mods",
    description=(
        "需 CurrentStaff。在现有值上仅覆盖 payload.mods 出现的键，其余保持不变；"
        "schema 未声明的键同样被静默丢弃，非 JSON 对象返回 422（error_code: THEME_MODS_INVALID）。"
        "成功后清空前台页面缓存。"
    ),
    responses={
        200: {"model": ThemeModsSavedResponse},
        404: {"description": "主题未安装（error_code: THEME_NOT_FOUND）"},
    },
)
async def set_theme_mods(
    db: DB,
    current_user: CurrentStaff,
    slug: str,
    payload: ThemeModsIn,
):
    tm = _get_theme_manager()
    theme = await tm.get(db, slug)
    if theme is None:
        raise AppException(
            status_code=status.HTTP_404_NOT_FOUND,
            message=f"主题不存在: {slug}",
            error_code=THEME_NOT_FOUND,
        )
    saved = await tm.set_mods(db, slug, payload.mods)
    await db.commit()
    purge_frontend_page_cache(f"主题 mods 增量更新: {slug}")
    return {"success": True, "data": saved}


async def _theme_row_to_out(db: DB, slug: str) -> ThemeOut:
    """加载主题 ORM 行并装配 ThemeOut（兼容 asyncio ORM 属性 + mods 读取）。"""
    tm = _get_theme_manager()
    row = await _load_theme_row(db, slug)
    out = ThemeOut.model_validate(row)
    out.mods = await tm.get_mods(db, slug)
    return out


@router.post(
    "",
    summary="安装主题（local / upload / remote）",
    description=(
        "需 CurrentStaff。统一安装入口，由 query 参数 source 决定分支："
        "local=按 JSON body 的 slug 扫描本地目录并登记（缺 slug 422 THEME_SLUG_REQUIRED）；"
        "upload=multipart/form-data 上传 zip（缺 file 字段 400 PACKAGE_UPLOAD_FILE_REQUIRED）；"
        "remote=按 {remote:{url,checksum_sha256?}} 下载 zip 安装（缺 remote 400 REMOTE_INFO_MISSING）。"
        "JSON body 校验失败 422（PAYLOAD_INVALID）；未知 source 400（INVALID_INSTALL_SOURCE）。"
        "成功后返回安装完成的主题记录（含合并后的 mods）。"
    ),
    responses={200: {"model": ThemeDetailResponse}},
)
async def install_theme(
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
    - 其他来源：按 application/json 读取 body → Pydantic ``ThemeInstallFrom``
    """
    import json as _json

    tm = _get_theme_manager()

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
        filename = uploaded.filename or "theme.zip"
        row = await tm.install_from_uploaded_bytes(db, filename, data)
        await db.commit()
        return {"success": True, "data": await _theme_row_to_out(db, row.slug)}

    # ── local / remote：JSON body ─────────────────────────────────────
    raw = await request.body()
    if not raw:
        payload = None
    else:
        try:
            payload = ThemeInstallFrom.model_validate(_json.loads(raw.decode("utf-8")))
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
                error_code="THEME_SLUG_REQUIRED",
            )
        await tm.install_local(db, slug)
        await db.commit()
        return {"success": True, "data": await _theme_row_to_out(db, slug)}

    if source == "remote":
        if payload is None or not getattr(payload, "remote", None):
            raise AppException(
                status_code=status.HTTP_400_BAD_REQUEST,
                message="source=remote 时必须通过 JSON body 提供 {remote:{url,checksum_sha256?}}",
                error_code="REMOTE_INFO_MISSING",
            )
        row = await tm.install_from_remote(db, payload)
        await db.commit()
        return {"success": True, "data": await _theme_row_to_out(db, row.slug)}

    raise AppException(
        status_code=status.HTTP_400_BAD_REQUEST,
        message=f"未知 source={source}",
        error_code="INVALID_INSTALL_SOURCE",
    )


@router.post(
    "/{slug}/upgrade",
    summary="升级主题（重扫磁盘清单）",
    description=(
        "需 CurrentStaff。主题没有独立的下载通道：升级 = 重新扫描磁盘清单并把 "
        "version / mods_schema 等元数据刷回 DB（zip 覆盖安装请走 POST /themes?source=upload|remote）。"
        "version 变化会使前台 <link> 的 ?v= bust 参数失效，故同步清空前台页面缓存。"
        "主题未安装时由 ThemeManager 抛出 404（error_code: THEME_NOT_FOUND）。"
    ),
    responses={
        200: {"model": ThemeDetailResponse},
        404: {"description": "主题未安装（error_code: THEME_NOT_FOUND）"},
    },
)
async def upgrade_theme(
    db: DB,
    current_user: CurrentStaff,
    slug: str,
):
    tm = _get_theme_manager()
    row = await tm.upgrade(db, slug)
    await db.commit()
    # 升级可能改变 version → 缓存 HTML 里的 ?v=<old> 链接失效，需清页面缓存
    purge_frontend_page_cache(f"主题升级: {slug}")
    return {
        "success": True,
        "message": "已从磁盘清单重新同步元数据",
        "data": await _theme_row_to_out(db, row.slug),
    }


@router.post(
    "/market/{slug}/install",
    summary="从市场一键安装主题",
    description=(
        "需 CurrentStaff。在市场索引（本地缓存 8h）中按 slug 查找条目，"
        "复用 install_from_remote 通道下载 zip 并安装（含 SHA-256 校验与 pre-release 开关）。"
        "索引缺 items 时 502（MARKET_INDEX_INVALID）；市场无该 slug 时 404（MARKET_ITEM_NOT_FOUND）；"
        "条目缺 zip_url 时 502（MARKET_ITEM_MISSING_ZIP_URL）。成功后返回安装完成的主题记录。"
    ),
    responses={
        200: {"model": ThemeDetailResponse},
        404: {"description": "市场中未找到该主题（error_code: MARKET_ITEM_NOT_FOUND）"},
        502: {
            "description": "市场索引异常或缺 zip_url（error_code: MARKET_INDEX_INVALID / MARKET_ITEM_MISSING_ZIP_URL）"
        },
    },
)
async def install_theme_from_market(
    db: DB,
    current_user: CurrentStaff,
    slug: str,
):
    """在市场索引中按 slug 查找条目，然后调用 install_from_remote 安装主题。"""
    from backend.core.market import fetch_market_index
    from backend.schemas.extensions import PackageInstallRemote, ThemeInstallFrom

    index = await fetch_market_index("themes")
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
            message=f"市场中未找到主题 slug={slug}",
        )
    zip_url = item.get("zip_url")
    if not isinstance(zip_url, str) or not zip_url:
        raise AppException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            error_code="MARKET_ITEM_MISSING_ZIP_URL",
            message=f"市场主题 {slug} 缺少 zip_url 字段",
        )
    checksum = item.get("checksum_sha256")
    payload = ThemeInstallFrom(
        source="remote",
        slug=slug,
        remote=PackageInstallRemote(
            url=zip_url,
            checksum_sha256=checksum if isinstance(checksum, str) and checksum else None,
            allow_pre_release=bool(item.get("allow_pre_release")),
        ),
    )
    tm = _get_theme_manager()
    row = await tm.install_from_remote(db, payload)
    await db.commit()
    return {"success": True, "data": await _theme_row_to_out(db, row.slug)}
