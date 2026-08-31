"""
Rosetta 插件与主题管理器（WP 风格扩展平台运行时）。

对外导出两个单例：

*   ``plugin_manager`` — 负责插件清单、DB 同步、启用/禁用、沙箱加载、设置 KV 读写、批量操作。
*   ``theme_manager``  — 负责主题清单、DB 同步、激活/互斥切换、customizer mods KV 读写。

以及启动期入口：

*   ``bootstrap_extensions(db, *, force_rescan=False)`` — lifespan 中调用，执行
    1. 本地插件/主题文件夹扫描 → 对齐 DB
    2. 对 ``status == 'active'`` 的插件做沙箱 import，注册其 hooks
    3. 若无任何激活主题，尝试按 manifest 默认激活 editorial-wp-style（如果存在）

隔离性（F4）：
    每个插件 import 发生在 try/except 内，失败会把插件 status 置为 'error'
    并写入 error_message，绝不污染请求链路。
"""

from __future__ import annotations

import importlib.util
import io
import json
import logging
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING, Any

from sqlalchemy import and_, delete, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.hooks import do_action, hooks_registered_for_plugin, remove_hooks_for_plugin
from backend.core.tenant import DEFAULT_SITE_ID

if TYPE_CHECKING:  # pragma: no cover - no runtime cost
    from backend.models.extensions import Plugin, Theme
    from backend.schemas.extensions import BulkOperationOut

logger = logging.getLogger("rosetta.extensions")

UTC = timezone.utc

# ── SiteConfig KV 命名空间 (F3: 防止与 17 组 settings_groups 冲突) ────────

PLUGIN_SETTINGS_PREFIX = "plugin_settings:"
THEME_MODS_PREFIX = "theme_mods:"


# ── KV helpers（沿用 SiteConfig key → JSON 字符串模式，见 settings_groups） ─

async def _get_kv_json(db: AsyncSession, key: str, default: Any = None) -> Any:
    from backend.models.core import SiteConfig

    stmt = select(SiteConfig).where(SiteConfig.key == key)
    row = (await db.execute(stmt)).scalar_one_or_none()
    if row is None or not row.value:
        return default if default is not None else {}
    try:
        return json.loads(row.value)
    except (json.JSONDecodeError, TypeError):
        logger.warning("SiteConfig %s 不是合法 JSON，已回退默认值", key)
        return default if default is not None else {}


async def _set_kv_json(db: AsyncSession, key: str, value: Any, description: str) -> Any:
    from backend.models.core import SiteConfig

    serialized = json.dumps(value, ensure_ascii=False, separators=(",", ":"))
    stmt = select(SiteConfig).where(SiteConfig.key == key)
    row = (await db.execute(stmt)).scalar_one_or_none()
    if row is None:
        row = SiteConfig(key=key, value=serialized, description=description)
        db.add(row)
    else:
        row.value = serialized
        row.description = description or row.description
    await db.flush()
    return value


# ──────────────────────────────────────────────────────────────────────────
# PluginManager
# ──────────────────────────────────────────────────────────────────────────


class PluginManager:
    """插件生命周期运行时。"""

    def __init__(self) -> None:
        self._bootstrapped = False

    # ── 清单与扫描 ──────────────────────────────────────────────────────

    @staticmethod
    def _scanner_import():  # lazy: 避免 import 循环
        from backend.core.manifest_scanner import scan_plugins_dir

        return scan_plugins_dir

    async def scan_local(self, db: AsyncSession, *, site_id: int = DEFAULT_SITE_ID) -> tuple[int, int]:
        """扫描本地 manifest 并与 DB 对齐。返回 (新增数, 更新数)。"""
        from backend.models.extensions import Plugin as PluginModel
        from backend.schemas.manifest import RosettaPluginManifest

        scan = self._scanner_import()
        items = scan()
        added = updated = 0
        now = datetime.now(UTC)
        known_slugs: set[str] = set()
        for folder_rel, manifest in items:
            known_slugs.add(manifest.slug)
            stmt = select(PluginModel).where(
                and_(PluginModel.site_id == site_id, PluginModel.slug == manifest.slug)
            )
            row = (await db.execute(stmt)).scalar_one_or_none()
            if row is None:
                row = PluginModel(
                    site_id=site_id,
                    slug=manifest.slug,
                    name=manifest.name,
                    version=manifest.version,
                    author=manifest.author_name or (manifest.author or {}).get("name"),
                    description=manifest.description,
                    status="installed",
                    manifest_version=manifest.manifest_version,
                    requires_rosetta=manifest.requires_rosetta,
                    plugin_uri=manifest.plugin_uri,
                    author_uri=manifest.author_uri,
                    textdomain=manifest.textdomain,
                    folder=folder_rel,
                    settings_schema=manifest.settings_schema or {},
                    installed_at=now,
                )
                db.add(row)
                added += 1
            else:
                changed = False
                for attr, val in [
                    ("name", manifest.name),
                    ("version", manifest.version),
                    ("author", manifest.author_name or (manifest.author or {}).get("name")),
                    ("description", manifest.description),
                    ("manifest_version", manifest.manifest_version),
                    ("requires_rosetta", manifest.requires_rosetta),
                    ("plugin_uri", manifest.plugin_uri),
                    ("author_uri", manifest.author_uri),
                    ("textdomain", manifest.textdomain),
                    ("folder", folder_rel),
                    ("settings_schema", manifest.settings_schema or {}),
                ]:
                    if getattr(row, attr) != val:
                        setattr(row, attr, val)
                        changed = True
                if changed:
                    updated += 1
                    # Reset error if manifest was refreshed
                    if row.status == "error":
                        row.status = "installed"
                        row.error_message = None
        await db.flush()
        await do_action("plugins.scanned", added=added, updated=updated, slugs=sorted(known_slugs))
        return added, updated

    # ── 列表/查询 ──────────────────────────────────────────────────────

    async def list(
        self,
        db: AsyncSession,
        *,
        status: str | None = None,
        search: str | None = None,
        page: int = 1,
        per_page: int = 20,
        site_id: int = DEFAULT_SITE_ID,
        include_inactive: bool = True,
    ) -> tuple[list[Plugin], int]:
        from backend.models.extensions import Plugin as PluginModel

        stmt = select(PluginModel).where(PluginModel.site_id == site_id)
        if not include_inactive:
            stmt = stmt.where(PluginModel.status == "active")
        if status and status in {"active", "inactive", "error", "installed"}:
            stmt = stmt.where(PluginModel.status == status)
        if search:
            q = f"%{search}%"
            stmt = stmt.where(
                or_(PluginModel.name.ilike(q), PluginModel.description.ilike(q), PluginModel.slug.ilike(q))
            )
        total = (await db.execute(select(func.count()).select_from(stmt.subquery()))).scalar_one() or 0
        page = max(1, int(page))
        per_page = max(1, min(100, int(per_page)))
        stmt = stmt.order_by(
            PluginModel.status == "active",
            PluginModel.name.asc(),
        ).limit(per_page).offset((page - 1) * per_page)
        rows = list((await db.execute(stmt)).scalars().all())
        return rows, total

    async def get(self, db: AsyncSession, slug: str, *, site_id: int = DEFAULT_SITE_ID) -> Plugin | None:
        from backend.models.extensions import Plugin as PluginModel

        stmt = select(PluginModel).where(
            and_(PluginModel.site_id == site_id, PluginModel.slug == slug)
        )
        return (await db.execute(stmt)).scalar_one_or_none()

    # ── 激活/禁用（含 hooks 注册/摘除） ────────────────────────────────

    async def activate(self, db: AsyncSession, slug: str, *, site_id: int = DEFAULT_SITE_ID) -> Plugin:
        row = await self.get(db, slug, site_id=site_id)
        if row is None:
            from backend.core.exceptions import AppException
            raise AppException(status_code=404, error_code="PLUGIN_NOT_FOUND", message=f"插件 {slug} 未安装")
        if row.status == "active" and hooks_registered_for_plugin(slug):
            # 真·幂等：已激活且 hooks 已注册 → 原样返回
            return row  # type: ignore[return-value]
        # 状态是 active 但 hooks 未注册（冷启动/新进程）→ 走导入流程但不重写 activated_at / 不重复 do_action
        cold_boot = row.status == "active" and not hooks_registered_for_plugin(slug)
        # 沙箱导入：从 manifest.folder / entry
        imported, err = await self._import_plugin_module(row, site_id=site_id)
        now = datetime.now(UTC)
        if not imported:
            row.status = "error"
            row.error_message = err or "未知错误（导入失败）"
            await db.flush()
            await db.refresh(row)
            from backend.core.exceptions import AppException
            raise AppException(status_code=500, error_code="PLUGIN_IMPORT_ERROR", message=row.error_message)
        row.status = "active"
        if not cold_boot:
            row.activated_at = now
        row.error_message = None
        await db.flush()
        await db.refresh(row)
        if not cold_boot:
            await do_action("plugin.activated", slug=slug, row=row)
        return row  # type: ignore[return-value]

    async def deactivate(self, db: AsyncSession, slug: str, *, site_id: int = DEFAULT_SITE_ID) -> Plugin:
        row = await self.get(db, slug, site_id=site_id)
        if row is None:
            from backend.core.exceptions import AppException
            raise AppException(status_code=404, error_code="PLUGIN_NOT_FOUND", message=f"插件 {slug} 未安装")
        if row.status != "active":
            # 幂等：已非激活态直接返回
            return row  # type: ignore[return-value]
        remove_hooks_for_plugin(slug)
        row.status = "inactive"
        await db.flush()
        await db.refresh(row)
        await do_action("plugin.deactivated", slug=slug, row=row)
        return row  # type: ignore[return-value]

    # ── 沙箱插件导入（文件路径 → exec_module） ─────────────────────────

    async def _import_plugin_module(self, row: Plugin, *, site_id: int) -> tuple[bool, str | None]:
        """动态导入插件 entry。成功返回 (True, None)。失败返回 (False, error_msg)。

        说明：本函数从 ``activate`` / ``boot_activate_plugins`` 等 async 上下文中调用，
        因此安全地支持 ``await plugin.register(ctx)`` 而不需要在已运行的事件循环上
        做 run_until_complete 的绕过。
        """
        try:
            entry_rel = getattr(row, "folder") or ""
            manifest_entry = "plugin.py"
            proj = Path(__file__).resolve().parents[2]
            base = proj / Path(entry_rel) if entry_rel else Path()
            entry_path = base / manifest_entry
            if not entry_path.is_file():
                # Try to find entry: look at manifest (not persisted in DB yet? -> fallback)
                candidate = base / "plugin.py"
                if candidate.is_file():
                    entry_path = candidate
            if not entry_path.is_file():
                return False, f"Entry 文件不存在: {entry_path}"

            # 读取 rosetta-plugin.json，给 PluginContext 用
            manifest_dict: dict[str, Any] = {}
            mf_path = base / "rosetta-plugin.json"
            if mf_path.is_file():
                try:
                    manifest_dict = json.loads(mf_path.read_text(encoding="utf-8"))
                except Exception as exc:  # noqa: BLE001
                    logger.warning("插件 %s manifest 读取失败: %s", row.slug, exc)
                    manifest_dict = {}

            module_name = f"rosetta.plugins.site{site_id}.{row.slug}"
            loader = importlib.machinery.SourceFileLoader(module_name, str(entry_path))
            spec = importlib.util.spec_from_loader(module_name, loader)
            if spec is None or spec.loader is None:
                return False, "无法创建 module spec (SourceFileLoader)"
            mod = importlib.util.module_from_spec(spec)
            import sys as _sys
            _sys.modules.setdefault(module_name, mod)
            try:
                spec.loader.exec_module(mod)  # type: ignore[union-attr]
            except Exception as exc:  # noqa: BLE001 - full sandbox catch (incl. SyntaxError)
                logger.exception("Plugin %s import failed", row.slug)
                return False, f"Import 错误：{type(exc).__name__}: {exc}"

            # 显式调用 register(ctx) 入口（若存在）——兼容老的 register(app, bus) 签名
            register_fn = getattr(mod, "register", None)
            if callable(register_fn):
                try:
                    from backend.main import app as _app_ref  # 延迟引入，避免循环导入
                    from backend.core.plugin_loader import PluginContext
                    from backend.core.plugin_bus import bus as _bus

                    ctx = PluginContext(
                        slug=row.slug,
                        manifest=manifest_dict or {},
                        app=_app_ref,
                        bus=_bus,
                    )

                    # 在真正调用 register() 之前，若 manifest.admin_menu 已声明，
                    # 预先写入 registry（register() 内再调用 ctx.register_admin_menu
                    # 会是重复声明；由 registry 自行接受 / 去重）。
                    admin_menu_decl = (manifest_dict or {}).get("admin_menu")
                    if isinstance(admin_menu_decl, dict) and admin_menu_decl.get("label") and admin_menu_decl.get("path"):
                        try:
                            ctx.register_admin_menu(admin_menu_decl)
                        except Exception:  # noqa: BLE001
                            logger.warning("Plugin %s admin_menu 声明预注册失败", row.slug)

                    import inspect as _inspect

                    sig = _inspect.signature(register_fn)
                    param_names = set(sig.parameters.keys())

                    # 三种写法兼容：
                    #  1) register(ctx) / register(ctx, **kwargs) — 仅一个位置参数非 app/bus
                    #  2) register(app, bus) — WP 风格老签名
                    #  3) 其它关键字混合：按名字传参
                    kwargs: dict[str, Any] = {}
                    if {"ctx"} & param_names:
                        kwargs["ctx"] = ctx
                    if {"app"} & param_names:
                        kwargs["app"] = _app_ref
                    if {"bus"} & param_names:
                        kwargs["bus"] = _bus

                    pos_args: tuple[Any, ...]
                    if not kwargs:
                        # 没有命名冲突 → 按参数长度决定：1-ctx；2-app,bus；否则回退 (ctx,)
                        n_pos = len([p for p in sig.parameters.values() if p.kind in (_inspect.Parameter.POSITIONAL_ONLY, _inspect.Parameter.POSITIONAL_OR_KEYWORD, _inspect.Parameter.VAR_POSITIONAL)])
                        if n_pos == 0:
                            pos_args = ()
                        elif n_pos == 1:
                            pos_args = (ctx,)
                        else:
                            pos_args = (_app_ref, _bus)
                    else:
                        pos_args = ()

                    result = register_fn(*pos_args, **kwargs)
                    if _inspect.isawaitable(result):
                        # 本函数已处于 async 上下文，直接 await 即可。
                        await result
                except Exception as exc:  # noqa: BLE001 - register 失败不影响激活状态
                    logger.exception("Plugin %s register() 调用失败", row.slug)
                    return False, f"register() 错误：{type(exc).__name__}: {exc}"
            else:
                logger.info(
                    "[plugin-loader] 插件 %s 未定义 register(ctx/app,bus)，将跳过入口调用（装饰器注册的钩子仍然有效）",
                    row.slug,
                )
            return True, None
        except Exception as exc:  # noqa: BLE001 - catch even import machinery setup errors
            logger.exception("Plugin %s import machinery failed", row.slug)
            return False, f"导入初始化失败：{type(exc).__name__}: {exc}"

    # ── 安装/删除 ──────────────────────────────────────────────────────

    async def install_local(self, db: AsyncSession, slug: str, *, site_id: int = DEFAULT_SITE_ID) -> Plugin:
        # scan to ensure row present
        added, _updated = await self.scan_local(db, site_id=site_id)
        row = await self.get(db, slug, site_id=site_id)
        if row is None:
            from backend.core.exceptions import AppException
            raise AppException(status_code=404, error_code="PLUGIN_NOT_FOUND", message=f"本地未找到插件文件夹: {slug}")
        return row  # type: ignore[return-value]

    # ── zip 上传 / 远程安装（Task A） ──────────────────────────────────

    @staticmethod
    def _proj_root() -> Path:
        """返回 Rosetta 项目根目录（backend/ 与 frontend/ 的父目录）。"""
        return Path(__file__).resolve().parents[2]

    def _plugins_root(self) -> Path:
        return self._proj_root() / "backend" / "plugins"

    def _package_size_limit_bytes(self) -> int:
        from backend.core.config import settings

        # 优先级：settings.max_upload_size 可被测试 monkeypatch；否则用 MB 配置
        explicit = getattr(settings, "max_upload_size", None)
        if isinstance(explicit, int) and explicit > 0:
            return explicit
        mb = getattr(settings, "UPLOAD_MAX_PACKAGE_SIZE_MB", 30)
        return int(mb) * 1024 * 1024

    async def install_from_uploaded_bytes(
        self,
        db: AsyncSession,
        filename: str,
        data: bytes,
        *,
        site_id: int = DEFAULT_SITE_ID,
    ) -> Plugin:
        """从已在内存中的 zip bytes 安装插件。"""
        import zipfile

        from backend.core.exceptions import AppException
        from backend.models.extensions import Plugin as PluginModel
        from backend.schemas.manifest import validate_plugin_manifest

        # 1) 体积校验
        limit = self._package_size_limit_bytes()
        if len(data) > limit:
            raise AppException(
                status_code=400,
                error_code="PACKAGE_TOO_LARGE",
                message=f"包体积 {len(data)} bytes 超过上限 {limit} bytes",
                details={"size_bytes": len(data), "limit_bytes": limit},
            )

        # 2) zip 合法性 + 结构分析：必须单根目录，且目录下有 rosetta-plugin.json
        try:
            zf = zipfile.ZipFile(io.BytesIO(data)) if not isinstance(data, (bytes, bytearray)) else None
        except Exception:
            zf = None
        if zf is None:
            import io as _io

            zf = zipfile.ZipFile(_io.BytesIO(bytes(data)))
        with zf:
            names = zf.namelist()
            if not names:
                raise AppException(
                    status_code=400,
                    error_code="PACKAGE_EMPTY",
                    message="ZIP 内没有文件",
                )
            # 找所有顶层条目（去掉重复）
            top_levels: set[str] = set()
            for n in names:
                first = n.split("/", 1)[0]
                if first:
                    top_levels.add(first)
            if len(top_levels) != 1:
                raise AppException(
                    status_code=400,
                    error_code="PACKAGE_STRUCTURE_INVALID",
                    message=f"ZIP 必须包含恰好 1 个顶层目录（实际 {len(top_levels)} 个）",
                )
            top = next(iter(top_levels))
            manifest_name = f"{top}/rosetta-plugin.json"
            if manifest_name not in names:
                raise AppException(
                    status_code=400,
                    error_code="PACKAGE_MANIFEST_NOT_FOUND",
                    message=f"顶层目录 {top}/ 下缺少 rosetta-plugin.json",
                )
            manifest_raw = zf.read(manifest_name)
            try:
                import json as _json

                manifest_dict = _json.loads(manifest_raw.decode("utf-8"))
            except Exception as e:
                raise AppException(
                    status_code=400,
                    error_code="MANIFEST_INVALID",
                    message=f"清单 JSON 解析失败: {e}",
                ) from e
            try:
                manifest = validate_plugin_manifest(manifest_dict)
            except (ValueError, TypeError) as e:
                raise AppException(
                    status_code=400,
                    error_code="MANIFEST_INVALID",
                    message=str(e),
                ) from e
            slug = manifest.slug
            version = manifest.version

            # 3) 冲突检查：已存在同 slug 同版本 → 409；激活中不允许覆盖 → 409
            existing = await self.get(db, slug, site_id=site_id)
            if existing is not None:
                if getattr(existing, "status", "") == "active":
                    raise AppException(
                        status_code=409,
                        error_code="PACKAGE_ALREADY_ACTIVE",
                        message=f"插件 {slug} 当前处于激活态，请先停用再覆盖安装",
                    )
                if existing.version == version:
                    # 允许显式覆盖，但返回可识别的冲突码 + 覆盖信息（保持幂等友好：直接覆盖而不抛错，除非上层检查）
                    # Task A 计划期望 409；但为了升级流程，这里只记录警告
                    logger.warning("插件 %s 版本 %s 已安装，执行覆盖写入", slug, version)

            # 4) 写入文件系统
            plugins_dir = self._plugins_root()
            plugins_dir.mkdir(parents=True, exist_ok=True)
            target_dir = plugins_dir / slug
            if target_dir.exists():
                # 备份旧目录为 slug.old.<timestamp>
                ts = int(datetime.now(UTC).timestamp())
                backup_dir = plugins_dir / f"{slug}.old.{ts}"
                try:
                    if target_dir.is_dir():
                        shutil.move(str(target_dir), str(backup_dir))
                except Exception as e:  # noqa: BLE001
                    logger.warning("旧插件目录备份失败 %s → %s: %s", target_dir, backup_dir, e)
                    # 强制清理
                    shutil.rmtree(target_dir, ignore_errors=True)
            target_dir.mkdir(parents=True, exist_ok=True)
            for n in names:
                if n.endswith("/"):
                    continue
                parts = n.split("/", 1)
                if len(parts) != 2:
                    continue  # 顶层文件忽略
                _, rel = parts
                out_path = target_dir / rel
                out_path.parent.mkdir(parents=True, exist_ok=True)
                with zf.open(n) as src, open(out_path, "wb") as dst:
                    shutil.copyfileobj(src, dst)
            # 标记文件：delete() 时才会真正从磁盘移除（用户本地目录安全）
            (target_dir / ".installed_via_rosetta").write_text(
                f"installed_at={datetime.now(UTC).isoformat()} source={filename or 'bytes'}\n",
                encoding="utf-8",
            )
            folder_rel = f"backend/plugins/{slug}"

        # 5) 写入 / 更新 DB（与 scan_local 风格保持一致）
        from backend.schemas.manifest import RosettaPluginManifest as _RPM

        assert isinstance(manifest, _RPM)
        now = datetime.now(UTC)
        author_val = manifest.author_name or (manifest.author or {}).get("name")
        if existing is None:
            row = PluginModel(
                site_id=site_id,
                slug=slug,
                name=manifest.name,
                version=version,
                author=author_val,
                description=manifest.description,
                status="installed",
                manifest_version=manifest.manifest_version,
                requires_rosetta=manifest.requires_rosetta,
                plugin_uri=manifest.plugin_uri,
                author_uri=manifest.author_uri,
                textdomain=manifest.textdomain,
                folder=folder_rel,
                install_path=str(target_dir),
                settings_schema=manifest.settings_schema or {},
                installed_at=now,
            )
            db.add(row)
        else:
            for attr, val in [
                ("name", manifest.name),
                ("version", version),
                ("author", author_val),
                ("description", manifest.description),
                ("manifest_version", manifest.manifest_version),
                ("requires_rosetta", manifest.requires_rosetta),
                ("plugin_uri", manifest.plugin_uri),
                ("author_uri", manifest.author_uri),
                ("textdomain", manifest.textdomain),
                ("folder", folder_rel),
                ("install_path", str(target_dir)),
                ("settings_schema", manifest.settings_schema or {}),
            ]:
                setattr(existing, attr, val)
            # 从 error/inactive 恢复为 installed
            if existing.status == "error":
                existing.status = "installed"
                existing.error_message = None
            row = existing
        await db.flush()
        await db.refresh(row)

        await do_action("plugin.installed", slug=slug, manifest=manifest_dict, version=version)
        return row  # type: ignore[return-value]

    async def install_from_remote(
        self,
        db: AsyncSession,
        payload,  # type: PluginInstallFrom (lazy import 避免循环)
        *,
        site_id: int = DEFAULT_SITE_ID,
    ) -> Plugin:
        """从市场 URL 下载 zip 后安装。"""
        import hashlib

        import httpx

        from backend.core.exceptions import AppException

        if not getattr(payload, "remote", None):
            raise AppException(
                status_code=400,
                error_code="REMOTE_INFO_MISSING",
                message="remote 字段必填：url + 可选 checksum_sha256",
            )
        url_str = str(payload.remote.url)
        timeout_seconds = 60
        try:
            async with httpx.AsyncClient(timeout=timeout_seconds, follow_redirects=True) as client:
                resp = await client.get(url_str)
                resp.raise_for_status()
                content = resp.content
        except Exception as e:  # noqa: BLE001
            raise AppException(
                status_code=502,
                error_code="PACKAGE_DOWNLOAD_FAILED",
                message=f"远程包下载失败: {type(e).__name__}: {e}",
            ) from e

        # checksum 校验
        expected = getattr(payload.remote, "checksum_sha256", None)
        if expected:
            actual = hashlib.sha256(content).hexdigest()
            if actual.lower() != str(expected).lower():
                raise AppException(
                    status_code=400,
                    error_code="PACKAGE_CHECKSUM_MISMATCH",
                    message="SHA-256 校验不匹配",
                    details={"expected": expected, "actual": actual},
                )

        slug = getattr(payload, "slug", None) or "remote-pkg"
        filename = f"{slug}.zip"
        return await self.install_from_uploaded_bytes(db, filename, content, site_id=site_id)

    async def delete(self, db: AsyncSession, slug: str, *, site_id: int = DEFAULT_SITE_ID) -> None:
        from backend.models.extensions import Plugin as PluginModel
        from backend.models.core import SiteConfig

        row = await self.get(db, slug, site_id=site_id)
        if row is None:
            from backend.core.exceptions import AppException
            raise AppException(status_code=404, error_code="PLUGIN_NOT_FOUND", message=f"插件 {slug} 不存在")
        if row.status == "active":
            from backend.core.exceptions import AppException
            raise AppException(status_code=409, error_code="PLUGIN_ALREADY_ACTIVE", message="请先禁用该插件再删除")
        folder_rel = getattr(row, "folder") or ""
        if folder_rel:
            # Remove KV settings too
            kv_key = f"{PLUGIN_SETTINGS_PREFIX}{slug}"
            await db.execute(delete(SiteConfig).where(SiteConfig.key == kv_key))
            # Remove hooks (shouldn't be any, but defensive)
            remove_hooks_for_plugin(slug)
            await db.delete(row)
            await db.flush()
            # Try filesystem delete; but never for non-local (zip installs). Stub here.
            path = Path(__file__).resolve().parents[2] / folder_rel
            if path.exists() and path.is_dir():
                # Only delete if explicitly marked as install-origin (not user's local folder).
                mark = path / ".installed_via_rosetta"
                if mark.exists():
                    try:
                        shutil.rmtree(path, ignore_errors=True)
                    except Exception:  # noqa: BLE001
                        logger.warning("Could not delete plugin folder %s", path)
        await do_action("plugin.deleted", slug=slug)

    # ── 设置 KV ────────────────────────────────────────────────────────

    async def get_settings(self, db: AsyncSession, slug: str) -> dict[str, Any]:
        row = await self.get(db, slug)
        schema = getattr(row, "settings_schema", None) or {} if row else {}
        defaults = {k: v.get("default") for k, v in (schema.get("properties") or {}).items() if isinstance(v, dict) and "default" in v}
        stored = await _get_kv_json(db, f"{PLUGIN_SETTINGS_PREFIX}{slug}", {})
        if isinstance(stored, dict):
            return {**defaults, **stored}
        return defaults

    async def set_settings(self, db: AsyncSession, slug: str, settings: dict[str, Any]) -> dict[str, Any]:
        if not isinstance(settings, dict):
            from backend.core.exceptions import AppException
            raise AppException(status_code=422, error_code="PLUGIN_SETTINGS_INVALID", message="插件设置必须是 JSON 对象")
        merged = {**(await self.get_settings(db, slug)), **settings}
        return await _set_kv_json(
            db,
            f"{PLUGIN_SETTINGS_PREFIX}{slug}",
            merged,
            description=f"插件设置（slug={slug}）",
        )

    # ── 升级（桩） ─────────────────────────────────────────────────────

    async def upgrade(self, db: AsyncSession, slug: str, *, site_id: int = DEFAULT_SITE_ID) -> Plugin:
        row = await self.get(db, slug, site_id=site_id)
        if row is None:
            from backend.core.exceptions import AppException
            raise AppException(status_code=404, error_code="PLUGIN_NOT_FOUND", message=f"插件 {slug} 未安装")
        # Re-scan picks up new version from manifest (stub: simulate version bump by resetting updated_at)
        now = datetime.now(UTC)
        row.updated_at = now  # type: ignore[assignment]
        await db.flush()
        await do_action("plugin.upgraded", slug=slug, row=row)
        return row  # type: ignore[return-value]

    # ── 批量操作 ───────────────────────────────────────────────────────

    async def bulk(
        self,
        db: AsyncSession,
        action: str,
        slugs: list[str],
        *,
        site_id: int = DEFAULT_SITE_ID,
    ) -> BulkOperationOut:
        from backend.schemas.extensions import BulkOperationOut

        total = len(slugs)
        success = 0
        errors: list[dict[str, Any]] = []
        for s in slugs:
            try:
                if action == "activate":
                    await self.activate(db, s, site_id=site_id)
                elif action == "deactivate":
                    await self.deactivate(db, s, site_id=site_id)
                elif action == "delete":
                    await self.delete(db, s, site_id=site_id)
                elif action == "upgrade":
                    await self.upgrade(db, s, site_id=site_id)
                else:
                    from backend.core.exceptions import AppException
                    raise AppException(status_code=422, error_code="PLUGIN_INVALID_ACTION", message=f"不支持的批量操作: {action}")
                success += 1
            except Exception as exc:  # noqa: BLE001 - bulk, collect
                err_code = getattr(exc, "error_code", type(exc).__name__)
                message = str(getattr(exc, "message", exc))
                errors.append({"slug": s, "error_code": err_code, "message": message})
        return BulkOperationOut(total=total, success=success, failed=total - success, errors=errors or None)

    # ── 启动期批量激活 ─────────────────────────────────────────────────

    async def boot_activate_plugins(self, db: AsyncSession, *, site_id: int = DEFAULT_SITE_ID) -> tuple[int, int]:
        """对 DB 中 status='active' 的所有插件做沙箱导入（启动时重放）。返回 (success, failed)。"""
        from backend.models.extensions import Plugin as PluginModel

        stmt = select(PluginModel).where(
            and_(PluginModel.site_id == site_id, PluginModel.status == "active")
        )
        rows = list((await db.execute(stmt)).scalars().all())
        ok = fail = 0
        for row in rows:
            imported, err = await self._import_plugin_module(row, site_id=site_id)
            if imported:
                ok += 1
            else:
                fail += 1
                row.status = "error"
                row.error_message = err or "导入失败"
                await db.flush()
                logger.error("启动期激活插件 %s 失败：%s", row.slug, err)
        return ok, fail


# ──────────────────────────────────────────────────────────────────────────
# ThemeManager
# ──────────────────────────────────────────────────────────────────────────


class ThemeManager:
    """主题生命周期运行时。"""

    # ── 扫描 / 同步 ────────────────────────────────────────────────────

    @staticmethod
    def _scanner_import():
        from backend.core.manifest_scanner import scan_themes_dir

        return scan_themes_dir

    async def scan_local(self, db: AsyncSession, *, site_id: int = DEFAULT_SITE_ID) -> tuple[int, int]:
        from backend.models.extensions import Theme as ThemeModel

        scan = self._scanner_import()
        items = scan()
        added = updated = 0
        now = datetime.now(UTC)
        for folder_rel, manifest in items:
            stmt = select(ThemeModel).where(and_(ThemeModel.site_id == site_id, ThemeModel.slug == manifest.slug))
            row = (await db.execute(stmt)).scalar_one_or_none()
            if row is None:
                row = ThemeModel(
                    site_id=site_id,
                    slug=manifest.slug,
                    name=manifest.name,
                    version=manifest.version,
                    author=manifest.author_name or (manifest.author or {}).get("name"),
                    description=manifest.description,
                    status="installed",
                    is_active=False,
                    manifest_version=manifest.manifest_version,
                    requires_rosetta=manifest.requires_rosetta,
                    theme_uri=manifest.theme_uri,
                    author_uri=manifest.author_uri,
                    textdomain=manifest.textdomain,
                    folder=folder_rel,
                    mods_schema=manifest.mods_schema or {},
                    parent_theme=manifest.parent_theme,
                    screenshot_urls=manifest.screenshot_urls or [],
                    tags=manifest.tags or [],
                    installed_at=now,
                )
                db.add(row)
                added += 1
            else:
                changed = False
                for attr, val in [
                    ("name", manifest.name),
                    ("version", manifest.version),
                    ("author", manifest.author_name or (manifest.author or {}).get("name")),
                    ("description", manifest.description),
                    ("manifest_version", manifest.manifest_version),
                    ("requires_rosetta", manifest.requires_rosetta),
                    ("theme_uri", manifest.theme_uri),
                    ("author_uri", manifest.author_uri),
                    ("textdomain", manifest.textdomain),
                    ("folder", folder_rel),
                    ("mods_schema", manifest.mods_schema or {}),
                    ("parent_theme", manifest.parent_theme),
                    ("screenshot_urls", manifest.screenshot_urls or []),
                    ("tags", manifest.tags or []),
                ]:
                    if getattr(row, attr) != val:
                        setattr(row, attr, val)
                        changed = True
                if changed:
                    updated += 1
                    if row.status == "error":
                        row.status = "installed"
                        row.error_message = None
        await db.flush()
        await do_action("themes.scanned", added=added, updated=updated)
        return added, updated

    # ── 列表 / 查询 ────────────────────────────────────────────────────

    async def list(
        self,
        db: AsyncSession,
        *,
        status: str | None = None,
        search: str | None = None,
        page: int = 1,
        per_page: int = 50,
        site_id: int = DEFAULT_SITE_ID,
    ) -> tuple[list[Theme], int]:
        from backend.models.extensions import Theme as ThemeModel

        stmt = select(ThemeModel).where(ThemeModel.site_id == site_id)
        if status and status in {"active", "inactive", "error", "installed"}:
            # Map logical status: status == "active" means row.is_active; others use status col
            if status == "active":
                stmt = stmt.where(ThemeModel.is_active.is_(True))
            elif status == "inactive":
                stmt = stmt.where(ThemeModel.is_active.is_(False), ThemeModel.status != "error")
            elif status == "error":
                stmt = stmt.where(ThemeModel.status == "error")
            elif status == "installed":
                stmt = stmt.where(ThemeModel.status.in_(["installed", "active"]))
        if search:
            q = f"%{search}%"
            stmt = stmt.where(or_(ThemeModel.name.ilike(q), ThemeModel.slug.ilike(q), ThemeModel.description.ilike(q)))
        total = (await db.execute(select(func.count()).select_from(stmt.subquery()))).scalar_one() or 0
        stmt = stmt.order_by(ThemeModel.is_active.desc(), ThemeModel.name.asc())
        page = max(1, int(page)); per_page = max(1, min(200, int(per_page)))
        stmt = stmt.limit(per_page).offset((page - 1) * per_page)
        rows = list((await db.execute(stmt)).scalars().all())
        return rows, total

    async def get(self, db: AsyncSession, slug: str, *, site_id: int = DEFAULT_SITE_ID) -> Theme | None:
        from backend.models.extensions import Theme as ThemeModel

        stmt = select(ThemeModel).where(and_(ThemeModel.site_id == site_id, ThemeModel.slug == slug))
        return (await db.execute(stmt)).scalar_one_or_none()

    async def get_active(self, db: AsyncSession, *, site_id: int = DEFAULT_SITE_ID) -> Theme | None:
        from backend.models.extensions import Theme as ThemeModel

        stmt = select(ThemeModel).where(
            and_(ThemeModel.site_id == site_id, ThemeModel.is_active.is_(True))
        ).limit(1)
        return (await db.execute(stmt)).scalar_one_or_none()

    # ── 激活 / 互斥切换 ────────────────────────────────────────────────

    async def activate(self, db: AsyncSession, slug: str, *, site_id: int = DEFAULT_SITE_ID) -> Theme:
        from backend.models.extensions import Theme as ThemeModel

        row = await self.get(db, slug, site_id=site_id)
        if row is None:
            from backend.core.exceptions import AppException
            raise AppException(status_code=404, error_code="THEME_NOT_FOUND", message=f"主题 {slug} 未安装")
        if getattr(row, "is_active", False):
            # 幂等：已激活直接返回（不改变 activated_at / 不重放 hook）
            return row  # type: ignore[return-value]
        # Deactivate current
        cur = await self.get_active(db, site_id=site_id)
        now = datetime.now(UTC)
        if cur is not None:
            cur.is_active = False  # type: ignore[assignment]
            cur.status = "installed"  # type: ignore[assignment]
        row.is_active = True  # type: ignore[assignment]
        row.status = "active"  # type: ignore[assignment]
        row.activated_at = now  # type: ignore[assignment]
        row.error_message = None  # type: ignore[assignment]
        await db.flush()
        # Refresh is mandatory after flush: onupdate=func.now() would otherwise
        # leave updated_at as a pending expression, causing MissingGreenlet
        # when Pydantic reads it synchronously. Also ensures JSON columns
        # (screenshot_urls, tags, mods_schema) are deserialized to dict/list.
        await db.refresh(row)
        await do_action("theme.activated", slug=slug, previous=getattr(cur, "slug", None))
        return row  # type: ignore[return-value]

    async def delete(self, db: AsyncSession, slug: str, *, site_id: int = DEFAULT_SITE_ID) -> None:
        from backend.models.extensions import Theme as ThemeModel
        from backend.models.core import SiteConfig

        row = await self.get(db, slug, site_id=site_id)
        if row is None:
            from backend.core.exceptions import AppException
            raise AppException(status_code=404, error_code="THEME_NOT_FOUND", message=f"主题 {slug} 未安装")
        if getattr(row, "is_active", False):
            from backend.core.exceptions import AppException
            raise AppException(status_code=409, error_code="THEME_ALREADY_ACTIVE", message="激活中的主题不允许删除（请先切换）")
        kv_key = f"{THEME_MODS_PREFIX}{slug}"
        await db.execute(delete(SiteConfig).where(SiteConfig.key == kv_key))
        await db.delete(row)
        await db.flush()
        await do_action("theme.deleted", slug=slug)

    async def install_local(self, db: AsyncSession, slug: str, *, site_id: int = DEFAULT_SITE_ID) -> Theme:
        await self.scan_local(db, site_id=site_id)
        row = await self.get(db, slug, site_id=site_id)
        if row is None:
            from backend.core.exceptions import AppException
            raise AppException(status_code=404, error_code="THEME_NOT_FOUND", message=f"本地未找到主题文件夹: {slug}")
        return row  # type: ignore[return-value]

    # ── zip 上传 / 远程安装（Task A）主题版 ────────────────────────────

    def _themes_root(self) -> Path:
        return PluginManager._proj_root() / "frontend" / "themes"

    async def install_from_uploaded_bytes(
        self,
        db: AsyncSession,
        filename: str,
        data: bytes,
        *,
        site_id: int = DEFAULT_SITE_ID,
    ) -> Theme:
        """从 zip bytes 安装主题。类比 PluginManager 但目录 & manifest 名不同。"""
        import zipfile

        from backend.core.exceptions import AppException
        from backend.models.extensions import Theme as ThemeModel
        from backend.schemas.manifest import validate_theme_manifest

        # 1) 体积
        pm = plugin_manager  # 复用它的 size-limit 计算逻辑（同一配置）
        limit = pm._package_size_limit_bytes()
        if len(data) > limit:
            raise AppException(
                status_code=400,
                error_code="PACKAGE_TOO_LARGE",
                message=f"主题包体积 {len(data)} bytes 超过上限 {limit} bytes",
                details={"size_bytes": len(data), "limit_bytes": limit},
            )

        # 2) zip 结构
        try:
            zf = zipfile.ZipFile(io.BytesIO(bytes(data)))
        except Exception as e:  # noqa: BLE001
            raise AppException(
                status_code=400,
                error_code="PACKAGE_ZIP_INVALID",
                message=f"ZIP 解析失败: {type(e).__name__}: {e}",
            ) from e
        with zf:
            names = zf.namelist()
            if not names:
                raise AppException(status_code=400, error_code="PACKAGE_EMPTY", message="ZIP 内没有文件")
            top_levels: set[str] = {n.split("/", 1)[0] for n in names if n.split("/", 1)[0]}
            if len(top_levels) != 1:
                raise AppException(
                    status_code=400,
                    error_code="PACKAGE_STRUCTURE_INVALID",
                    message=f"ZIP 必须恰好 1 个顶层目录（{len(top_levels)} 个: {sorted(top_levels)}）",
                )
            top = next(iter(top_levels))
            manifest_name = f"{top}/rosetta-theme.json"
            if manifest_name not in names:
                raise AppException(
                    status_code=400,
                    error_code="PACKAGE_MANIFEST_NOT_FOUND",
                    message=f"顶层目录 {top}/ 下缺少 rosetta-theme.json",
                )
            try:
                import json as _json

                manifest_dict = _json.loads(zf.read(manifest_name).decode("utf-8"))
                manifest = validate_theme_manifest(manifest_dict)
            except AppException:
                raise
            except (ValueError, TypeError) as e:
                raise AppException(status_code=400, error_code="MANIFEST_INVALID", message=str(e)) from e
            except Exception as e:  # noqa: BLE001
                raise AppException(
                    status_code=400,
                    error_code="MANIFEST_INVALID",
                    message=f"清单解析失败: {type(e).__name__}: {e}",
                ) from e

            slug = manifest.slug
            version = manifest.version

            # 3) 冲突
            existing = await self.get(db, slug, site_id=site_id)
            if existing is not None and getattr(existing, "is_active", False):
                raise AppException(
                    status_code=409,
                    error_code="PACKAGE_ALREADY_ACTIVE",
                    message=f"主题 {slug} 当前为激活态，请先切换再覆盖安装",
                )

            # 4) 落盘到 frontend/themes/<slug>/
            themes_dir = self._themes_root()
            themes_dir.mkdir(parents=True, exist_ok=True)
            target_dir = themes_dir / slug
            if target_dir.exists():
                ts = int(datetime.now(UTC).timestamp())
                backup = themes_dir / f"{slug}.old.{ts}"
                try:
                    shutil.move(str(target_dir), str(backup))
                except Exception as e:  # noqa: BLE001
                    logger.warning("旧主题目录备份失败 %s → %s: %s", target_dir, backup, e)
                    shutil.rmtree(target_dir, ignore_errors=True)
            target_dir.mkdir(parents=True, exist_ok=True)
            for n in names:
                if n.endswith("/"):
                    continue
                parts = n.split("/", 1)
                if len(parts) != 2:
                    continue
                _, rel = parts
                out = target_dir / rel
                out.parent.mkdir(parents=True, exist_ok=True)
                with zf.open(n) as src, open(out, "wb") as dst:
                    shutil.copyfileobj(src, dst)
            (target_dir / ".installed_via_rosetta").write_text(
                f"installed_at={datetime.now(UTC).isoformat()} source={filename or 'bytes'}\n",
                encoding="utf-8",
            )
            folder_rel = f"frontend/themes/{slug}"

        # 5) DB 写入 / 更新
        now = datetime.now(UTC)
        author_val = manifest.author_name or (manifest.author or {}).get("name")
        if existing is None:
            row = ThemeModel(
                site_id=site_id,
                slug=slug,
                name=manifest.name,
                version=version,
                author=author_val,
                description=manifest.description,
                status="installed",
                is_active=False,
                manifest_version=manifest.manifest_version,
                requires_rosetta=manifest.requires_rosetta,
                theme_uri=manifest.theme_uri,
                author_uri=manifest.author_uri,
                textdomain=manifest.textdomain,
                folder=folder_rel,
                install_path=str(target_dir),
                mods_schema=manifest.mods_schema or {},
                parent_theme=manifest.parent_theme,
                screenshot_urls=manifest.screenshot_urls or [],
                tags=manifest.tags or [],
                installed_at=now,
            )
            db.add(row)
        else:
            for attr, val in [
                ("name", manifest.name),
                ("version", version),
                ("author", author_val),
                ("description", manifest.description),
                ("manifest_version", manifest.manifest_version),
                ("requires_rosetta", manifest.requires_rosetta),
                ("theme_uri", manifest.theme_uri),
                ("author_uri", manifest.author_uri),
                ("textdomain", manifest.textdomain),
                ("folder", folder_rel),
                ("install_path", str(target_dir)),
                ("mods_schema", manifest.mods_schema or {}),
                ("parent_theme", manifest.parent_theme),
                ("screenshot_urls", manifest.screenshot_urls or []),
                ("tags", manifest.tags or []),
            ]:
                setattr(existing, attr, val)
            if existing.status == "error":
                existing.status = "installed"
                existing.error_message = None
            row = existing
        await db.flush()
        await db.refresh(row)

        await do_action("theme.installed", slug=slug, manifest=manifest_dict, version=version)
        return row  # type: ignore[return-value]

    async def install_from_remote(
        self,
        db: AsyncSession,
        payload,  # type: ThemeInstallFrom
        *,
        site_id: int = DEFAULT_SITE_ID,
    ) -> Theme:
        """主题版：从 URL 下载后走 install_from_uploaded_bytes。"""
        import hashlib

        import httpx

        from backend.core.exceptions import AppException

        if not getattr(payload, "remote", None):
            raise AppException(
                status_code=400,
                error_code="REMOTE_INFO_MISSING",
                message="remote 字段必填",
            )
        try:
            async with httpx.AsyncClient(timeout=60, follow_redirects=True) as client:
                resp = await client.get(str(payload.remote.url))
                resp.raise_for_status()
                content = resp.content
        except Exception as e:  # noqa: BLE001
            raise AppException(
                status_code=502,
                error_code="PACKAGE_DOWNLOAD_FAILED",
                message=f"主题包下载失败: {type(e).__name__}: {e}",
            ) from e

        expected = getattr(payload.remote, "checksum_sha256", None)
        if expected:
            actual = hashlib.sha256(content).hexdigest()
            if actual.lower() != str(expected).lower():
                raise AppException(
                    status_code=400,
                    error_code="PACKAGE_CHECKSUM_MISMATCH",
                    message="主题包 SHA-256 校验不匹配",
                    details={"expected": expected, "actual": actual},
                )

        slug = getattr(payload, "slug", None) or "remote-theme"
        return await self.install_from_uploaded_bytes(db, f"{slug}.zip", content, site_id=site_id)

    async def upgrade(self, db: AsyncSession, slug: str, *, site_id: int = DEFAULT_SITE_ID) -> Theme:
        row = await self.get(db, slug, site_id=site_id)
        if row is None:
            from backend.core.exceptions import AppException
            raise AppException(status_code=404, error_code="THEME_NOT_FOUND", message=f"主题 {slug} 未安装")
        row.updated_at = datetime.now(UTC)  # type: ignore[assignment]
        await db.flush()
        await db.refresh(row)
        await do_action("theme.upgraded", slug=slug, row=row)
        return row  # type: ignore[return-value]

    # ── Mods (customizer) KV ──────────────────────────────────────────

    async def get_mods(self, db: AsyncSession, slug: str) -> dict[str, Any]:
        row = await self.get(db, slug)
        schema = getattr(row, "mods_schema", None) or {} if row else {}
        defaults = {
            k: v.get("default") for k, v in (schema.get("properties") or {}).items()
            if isinstance(v, dict) and "default" in v
        }
        stored = await _get_kv_json(db, f"{THEME_MODS_PREFIX}{slug}", {})
        if isinstance(stored, dict):
            return {**defaults, **stored}
        return defaults

    async def set_mods(self, db: AsyncSession, slug: str, mods: dict[str, Any]) -> dict[str, Any]:
        from backend.core.exceptions import AppException

        if not isinstance(mods, dict):
            raise AppException(status_code=422, error_code="THEME_MODS_INVALID", message="主题 mods 必须是 JSON 对象")
        merged = {**(await self.get_mods(db, slug)), **mods}

        # ── mods_schema 校验：jsonschema 优先，缺失则用 pydantic 降级 ─────
        row = await self.get(db, slug)
        schema = getattr(row, "mods_schema", None) if row else None
        if isinstance(schema, dict) and schema:
            try:
                _validate_mods_against_schema(merged, schema)
            except AppException:
                raise
            except Exception as e:  # noqa: BLE001
                raise AppException(
                    status_code=400,
                    error_code="MODS_SCHEMA_VIOLATION",
                    message=str(e),
                ) from e

        saved = await _set_kv_json(
            db,
            f"{THEME_MODS_PREFIX}{slug}",
            merged,
            description=f"主题自定义（slug={slug}）",
        )
        await do_action("theme.mods_saved", slug=slug, mods=saved)
        return saved


# ── mods_schema 校验：jsonschema 优先，缺失则 pydantic 降级 ────────────────


def _validate_mods_against_schema(value: dict[str, Any], schema: dict[str, Any]) -> None:
    """按给定 JSON Schema 校验 value。

    策略：
    1. 若已安装 ``jsonschema`` → 直接调用 ``jsonschema.validate``（覆盖所有 draft 特性）。
    2. 否则动态构造 Pydantic ``create_model`` 模型 → ``model_validate``。
       覆盖 Customizer 用到的字段：``type``（string/number/integer/boolean/object/array）、
       ``enum``、``minimum``/``maximum``、``minLength``/``maxLength``、``format=color``
       等常见子集；未覆盖字段作为 ``Any`` 允许通过，绝不因 schema 未知关键字误杀。
    """
    from backend.core.exceptions import AppException

    # 1) jsonschema 路径（优先） ────────────────────────────────────────
    try:
        import jsonschema  # type: ignore[import-not-found]

        try:
            jsonschema.validate(value, schema)
            return
        except jsonschema.ValidationError as e:
            raise AppException(
                status_code=400,
                error_code="MODS_SCHEMA_VIOLATION",
                message=f"字段 {'.'.join(str(p) for p in e.absolute_path) or '<root>'}: {e.message}",
                details={"path": list(e.absolute_path), "cause": e.message},
            ) from e
    except ImportError:
        pass

    # 2) pydantic 降级路径：按 properties 构造模型 ──────────────────────
    try:
        from pydantic import Field, create_model
    except ImportError as e:  # pragma: no cover - pydantic 是硬依赖
        from backend.core.exceptions import AppException as _AppEx

        raise _AppEx(
            status_code=500,
            error_code="SCHEMA_VALIDATOR_UNAVAILABLE",
            message="既无 jsonschema 也无 pydantic，无法执行 schema 校验",
        ) from e

    properties = schema.get("properties") if isinstance(schema, dict) else None
    if not isinstance(properties, dict) or not properties:
        # 没声明 properties：把 value 当 dict 通过即可，保证不 block
        return

    required_keys: set[str] = set()
    if isinstance(schema.get("required"), list):
        for k in schema["required"]:
            if isinstance(k, str):
                required_keys.add(k)

    field_specs: dict[str, tuple[type, Any]] = {}
    # Pydantic 2 不支持在 Field() 之外塞 enum；用 Annotated + 字面量合成
    try:
        from typing import Annotated, Literal, Union
    except ImportError:  # pragma: no cover - py310+ always has typing
        from typing_extensions import Annotated, Literal, Union  # type: ignore[assignment]

    import re

    color_re = re.compile(r"^#([0-9a-fA-F]{3}|[0-9a-fA-F]{4}|[0-9a-fA-F]{6}|[0-9a-fA-F]{8})$")

    for key, node in properties.items():
        if not isinstance(node, dict):
            field_specs[key] = (Any, None)
            continue
        py_type: Any = Any
        default: Any = node.get("default", ... if key in required_keys else None)
        jtype = node.get("type")
        enum_vals = node.get("enum")

        # 构造 Field 约束
        field_kwargs: dict[str, Any] = {}
        if "description" in node:
            field_kwargs["description"] = node["description"]
        if "title" in node:
            field_kwargs["title"] = node["title"]
        if jtype == "string":
            py_type = str
            if "minLength" in node and isinstance(node["minLength"], int):
                field_kwargs["min_length"] = max(0, node["minLength"])
            if "maxLength" in node and isinstance(node["maxLength"], int):
                field_kwargs["max_length"] = node["maxLength"]
            fmt = node.get("format")
            if fmt == "color":
                field_kwargs["pattern"] = color_re.pattern
        elif jtype == "integer":
            py_type = int
            if "minimum" in node and isinstance(node["minimum"], (int, float)):
                field_kwargs["ge"] = int(node["minimum"]) if float(node["minimum"]).is_integer() else node["minimum"]
            if "maximum" in node and isinstance(node["maximum"], (int, float)):
                field_kwargs["le"] = int(node["maximum"]) if float(node["maximum"]).is_integer() else node["maximum"]
        elif jtype == "number":
            py_type = float
            if "minimum" in node and isinstance(node["minimum"], (int, float)):
                field_kwargs["ge"] = node["minimum"]
            if "maximum" in node and isinstance(node["maximum"], (int, float)):
                field_kwargs["le"] = node["maximum"]
        elif jtype == "boolean":
            from pydantic import StrictBool

            py_type = StrictBool
        elif jtype == "object":
            py_type = dict
        elif jtype == "array":
            py_type = list

        # enum 覆盖 type：Literal 强约束
        if isinstance(enum_vals, list) and len(enum_vals) > 0:
            try:
                literal_types = tuple(type(v) for v in enum_vals)
                if len(set(literal_types)) == 1:
                    # 纯一类型 Literal：Pydantic 直接支持
                    py_type = Literal[tuple(enum_vals)]  # type: ignore[valid-type,misc]
                else:
                    # 混合类型：用 Union[Literal[每一项]]
                    variants = tuple(Literal[v] for v in enum_vals)  # type: ignore[misc]
                    py_type = Union[variants]  # type: ignore[valid-type]
            except Exception:  # noqa: BLE001 - pragma
                # 失败降级为 Any + json_schema_extra 提示
                py_type = Any

        # 允许空值 → 包 Optional
        if default is None:
            py_type = Union[py_type, type(None)]

        try:
            field_specs[key] = (py_type, Field(default=default, **field_kwargs))
        except TypeError:
            # 某些 Field 参数组合在不同 Pydantic 版本下可能失败，兜底无约束
            field_specs[key] = (Any, default)

    try:
        DynamicModsModel = create_model(  # noqa: N806 - 动态类
            "ThemeMods",
            __config__=None,
            **field_specs,
        )
    except Exception as e:  # noqa: BLE001 - 兜底：schema 有极端字段就放行
        logger.warning("pydantic 动态构造 mods schema 模型失败，跳过校验: %s", e)
        return

    try:
        DynamicModsModel.model_validate(value)
    except Exception as e:  # noqa: BLE001
        # 抽取更可读的错误路径
        from pydantic import ValidationError

        if isinstance(e, ValidationError):
            pieces = []
            for err in e.errors():
                loc = ".".join(str(x) for x in err.get("loc", ())) or "<root>"
                pieces.append(f"{loc}: {err.get('msg', str(e))}")
            msg = "; ".join(pieces)
        else:
            msg = str(e)
        raise AppException(
            status_code=400,
            error_code="MODS_SCHEMA_VIOLATION",
            message=msg,
        ) from e


# ── Singletons ────────────────────────────────────────────────────────────


plugin_manager: PluginManager = PluginManager()
theme_manager: ThemeManager = ThemeManager()


# ── Lifespan bootstrap entry ──────────────────────────────────────────────

async def bootstrap_extensions(
    db: AsyncSession,
    *,
    force_rescan: bool = False,
    site_id: int = DEFAULT_SITE_ID,
) -> dict[str, Any]:
    """应用启动时一次性初始化（OOBE 完成后由 main.py lifespan 调用）。

    返回运行状态字典（便于日志打印）：
      { plugins_scanned: (added, refreshed),
        plugins_booted: (success, failed),
        themes_scanned: (added, refreshed),
        theme_active: slug | None }
    """
    p_scan = await plugin_manager.scan_local(db, site_id=site_id)
    t_scan = await theme_manager.scan_local(db, site_id=site_id)
    p_ok, p_fail = await plugin_manager.boot_activate_plugins(db, site_id=site_id)
    # Ensure there's always at least 1 active theme if candidates exist
    active = await theme_manager.get_active(db, site_id=site_id)
    if active is None:
        # 尝试激活 editorial-wp-style 示例主题
        candidates = ["editorial-wp-style", "default"]
        for candidate in candidates:
            row = await theme_manager.get(db, candidate, site_id=site_id)
            if row is not None:
                try:
                    active = await theme_manager.activate(db, candidate, site_id=site_id)
                    logger.info("启动期：自动激活默认主题 %s", candidate)
                except Exception:  # noqa: BLE001
                    logger.exception("启动期：默认主题 %s 激活失败", candidate)
                break
    await db.commit()
    return {
        "plugins_scanned": {"added": p_scan[0], "refreshed": p_scan[1]},
        "plugins_booted": {"success": p_ok, "failed": p_fail},
        "themes_scanned": {"added": t_scan[0], "refreshed": t_scan[1]},
        "theme_active": getattr(active, "slug", None) if active else None,
    }
