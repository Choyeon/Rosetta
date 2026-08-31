"""
主题扩展 REST API (挂载于 /api/admin)

WordPress 风格主题管理接口：
- GET   /themes             管理员列表
- GET   /themes/{slug}      管理员详情
- GET   /themes/current     公开当前激活主题
- PUT   /themes/{slug}/activate
- DELETE /themes/{slug}
- POST  /themes/_scan
- GET   /themes/{slug}/mods
- PATCH /themes/{slug}/mods
- POST  /themes            安装
- POST  /themes/{slug}/upgrade
"""

from __future__ import annotations

from typing import Any, Literal

from fastapi import APIRouter, Depends, Query, Request, status
from sqlalchemy import select

from backend.core.auth import CurrentStaff, CurrentUserOptional, DB
from backend.core.exceptions import AppException
from backend.core.tenant import DEFAULT_SITE_ID
from backend.models.extensions import Theme
from backend.schemas.extensions import (
    ThemeInstallFrom,
    ThemeModsIn,
    ThemeOut,
)

THEME_NOT_FOUND = "THEME_NOT_FOUND"
THEME_ALREADY_ACTIVE = "THEME_ALREADY_ACTIVE"
THEME_MODS_INVALID = "THEME_MODS_INVALID"

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
    await db.refresh(row, attribute_names=["updated_at", "created_at", "activated_at", "installed_at", "screenshot_urls", "tags", "mods_schema"])
    return row


@router.get("")
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
    data = []
    for t in themes:
        out = ThemeOut.model_validate(t)
        try:
            out.mods = await tm.get_mods(db, t.slug)
        except Exception:
            out.mods = None
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


@router.get("/market")
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


@router.get("/active")
async def get_current_active_theme(
    db: DB,
    current_user: CurrentUserOptional,
):
    tm = _get_theme_manager()
    result = await db.execute(select(Theme).where(Theme.is_active == True))  # noqa: E712
    theme = result.scalar_one_or_none()
    if theme is None:
        return {"success": True, "data": None, "message": "未启用自定义主题"}
    out = ThemeOut.model_validate(theme)
    try:
        out.mods = await tm.get_mods(db, theme.slug)
    except Exception:
        out.mods = None
    return {"success": True, "data": out}


@router.get("/{slug}")
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
    try:
        out.mods = await tm.get_mods(db, theme.slug)
    except Exception:
        out.mods = None
    return {"success": True, "data": out}


@router.put("/{slug}/activate")
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
    try:
        out.mods = await tm.get_mods(db, result.slug)
    except Exception:
        out.mods = None
    return {"success": True, "data": out}


@router.delete("/{slug}")
async def delete_theme(
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
    if theme.is_active:
        raise AppException(
            status_code=status.HTTP_400_BAD_REQUEST,
            message=f"当前主题已启用，无法删除: {slug}",
            error_code=THEME_ALREADY_ACTIVE,
        )
    await tm.delete(db, slug)
    await db.commit()
    return {"success": True, "message": "已删除"}


@router.post("/scan")
async def scan_local_themes(
    db: DB,
    current_user: CurrentStaff,
):
    tm = _get_theme_manager()
    added, refreshed = await tm.scan_local(db)
    await db.commit()
    return {
        "success": True,
        "message": f"扫描完成，新增 {added}，更新 {refreshed}",
        "data": {"added": added, "refreshed": refreshed},
    }


@router.get("/{slug}/mods")
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


@router.put("/{slug}/mods")
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
    # PUT 语义：重置为 schema 默认值，再叠加 payload.mods
    schema_props = ((theme.mods_schema or {}).get("properties") or {})
    reset = {
        k: (v.get("default") if isinstance(v, dict) and "default" in v else None)
        for k, v in schema_props.items()
        if isinstance(v, dict)
    }
    if isinstance(payload.mods, dict):
        reset.update(payload.mods)
    try:
        saved = await tm.set_mods(db, slug, reset)
    except Exception as e:
        raise AppException(
            status_code=status.HTTP_400_BAD_REQUEST,
            message=f"主题 Mods 无效: {e}",
            error_code=THEME_MODS_INVALID,
        )
    await db.commit()
    return {"success": True, "data": saved}


@router.patch("/{slug}/mods")
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
    try:
        saved = await tm.set_mods(db, slug, payload.mods)
    except Exception as e:
        raise AppException(
            status_code=status.HTTP_400_BAD_REQUEST,
            message=f"主题 Mods 无效: {e}",
            error_code=THEME_MODS_INVALID,
        )
    await db.commit()
    return {"success": True, "data": saved}


async def _theme_row_to_out(db: DB, slug: str) -> ThemeOut:
    """加载主题 ORM 行并装配 ThemeOut（兼容 asyncio ORM 属性 + mods 读取）。"""
    tm = _get_theme_manager()
    row = await _load_theme_row(db, slug)
    out = ThemeOut.model_validate(row)
    try:
        out.mods = await tm.get_mods(db, slug)
    except Exception:
        out.mods = None
    return out


@router.post("")
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


@router.post("/{slug}/upgrade")
async def upgrade_theme(
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
    await tm.upgrade(db, slug)
    await db.commit()
    return {"success": True, "message": "升级完成 (stub)"}


@router.post("/market/{slug}/install")
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

