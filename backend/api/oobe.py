"""
OOBE (Out-of-Box Experience) API 路由

提供开箱即用配置向导的所有 API 接口，包括：
- OOBE 状态检测
- 环境检测 (check)
- 一键式安装 (install) + SSE 进度 (install/stream)
- 数据库配置
- 站点配置
- 管理员账户创建
- 配置完成
"""

import asyncio
import json
import logging
import shutil
import subprocess
import sys
import traceback
import uuid as _uuid
from datetime import datetime
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.auth import get_password_hash
from backend.core.database import async_session_maker, get_db, init_db, reset_engine
from backend.core.deps import is_oobe_complete, require_oobe_incomplete
from backend.core.exceptions import (
    OOBEAlreadyCompletedException,
    WeakPasswordException,
)
from backend.core.i18n import t
from backend.core.oobe_constants import (
    FEATURE_FLAG_DB_KEY_MAP,
    PASSWORD_MIN_LENGTH,
    USERNAME_MAX_LENGTH,
    USERNAME_MIN_LENGTH,
)
from backend.core.paths import BASE_DIR, CONFIG_FILE, ENV_FILE, OOBE_LOCK_FILE, STATE_FILE
from backend.core.setup_config import ConfigService, Environment
from backend.core.setup_database import DatabaseService, generate_database_url
from backend.core.setup_dependency import DependencyService
from backend.core.setup_progress import ProgressService
from backend.core.setup_system import SystemService
from backend.models.blog import Category, Tag
from backend.models.core import Navigation, Page
from backend.models.core import SiteConfig as DbSiteConfig
from backend.models.user import User

logger = logging.getLogger(__name__)


class CombinedInstallRequest(BaseModel):
    """合并式安装请求体 - 一键完成所有配置"""

    database_type: Literal["sqlite", "postgresql"] = "sqlite"
    db_host: str = "localhost"
    db_port: int = 5432
    db_name: str = "rosetta"
    db_user: str = ""
    db_password: str = ""
    db_path: str = "rosetta.db"

    redis_enabled: bool = False
    redis_host: str = "localhost"
    redis_port: int = 6379
    redis_password: str = ""

    admin_username: str = Field(default="Choyeon", min_length=USERNAME_MIN_LENGTH, max_length=USERNAME_MAX_LENGTH)
    admin_email: str = "choyeon@foxmail.com"
    admin_password: str = Field(default="Choyeon@2025", min_length=PASSWORD_MIN_LENGTH)
    admin_nickname: str = "Choyeon"

    # 管理员扩展资料（简介 / QQ / GitHub / 个人网站）
    admin_bio: str = "Full-Stack Development"
    admin_qq: str = "952223950"
    admin_github: str = "Choyeon"
    admin_website: str = "https://rosetta.choyeon.cc"
    admin_avatar_source: str = "auto"

    site_name: str = "Rosetta"
    site_description: str = "一个功能齐全、主题优雅、开箱即用的现代博客引擎"
    site_url: str = "https://rosetta.choyeon.cc"
    site_keywords: str = ""
    site_author: str = ""
    site_email: str = ""

    enable_comments: bool = True
    enable_registration: bool = True
    enable_rss: bool = True
    enable_bing_wallpaper: bool = True
    enable_pagefind_search: bool = True
    enable_encrypted_posts: bool = False
    enable_music_player: bool = True

    environment: Literal["development", "production"] = "production"

    @field_validator("admin_password")
    @classmethod
    def _check_admin_password(cls, v: str) -> str:
        if len(v) < PASSWORD_MIN_LENGTH:
            raise ValueError(f"管理员密码至少 {PASSWORD_MIN_LENGTH} 位")
        return v


router = APIRouter(prefix="/oobe", tags=["OOBE"])

config_service = ConfigService()
system_service = SystemService()
dependency_service = DependencyService(BASE_DIR)
database_service = DatabaseService()
progress_service = ProgressService()

_INSTALL_STREAM_QUEUES: dict[str, asyncio.Queue] = {}
_INSTALL_STREAM_BUFFER: list[dict] = []
_INSTALL_STREAM_BUFFER_MAX = 200

_DEP_STREAM_QUEUES: dict[str, asyncio.Queue] = {}
_DEP_STREAM_BUFFER: list[dict] = []
_DEP_STREAM_BUFFER_MAX = 500


def _append_progress(evt: dict):
    _INSTALL_STREAM_BUFFER.append(evt)
    if len(_INSTALL_STREAM_BUFFER) > _INSTALL_STREAM_BUFFER_MAX:
        _INSTALL_STREAM_BUFFER[:] = _INSTALL_STREAM_BUFFER[-_INSTALL_STREAM_BUFFER_MAX:]
    for q in list(_INSTALL_STREAM_QUEUES.values()):
        try:
            q.put_nowait(evt)
        except Exception:
            pass


def _append_dep_progress(evt: dict):
    """依赖安装流式日志广播（SSE 共享同一缓冲语义）"""
    _DEP_STREAM_BUFFER.append(evt)
    if len(_DEP_STREAM_BUFFER) > _DEP_STREAM_BUFFER_MAX:
        _DEP_STREAM_BUFFER[:] = _DEP_STREAM_BUFFER[-_DEP_STREAM_BUFFER_MAX:]
    for q in list(_DEP_STREAM_QUEUES.values()):
        try:
            q.put_nowait(evt)
        except Exception:
            pass


async def _broadcast_progress(step_id: str, message: str, percent: int):
    evt = {
        "type": "progress",
        "step_id": step_id,
        "message": message,
        "percent": max(0, min(100, int(percent))),
        "timestamp": datetime.now().isoformat(),
    }
    _append_progress(evt)


def _load_state() -> dict:
    """加载保存的 OOBE 状态"""
    saved = config_service.load_state()
    if saved:
        return {
            "current_step": saved.current_step,
            "total_steps": 5,
            "environment": saved.environment.value,
            "database_config": saved.database_config or {},
            "site_config": saved.site_config.__dict__ if saved.site_config else {},
            "admin_config": saved.admin_config.__dict__ if saved.admin_config else {},
            "completed": saved.completed,
            "errors": saved.errors,
        }
    return {
        "current_step": 1,
        "total_steps": 5,
        "environment": "development",
        "database_config": {},
        "site_config": {},
        "admin_config": {},
        "completed": False,
        "errors": [],
    }


@router.get("/status")
async def get_oobe_status():
    """获取 OOBE 状态

    返回 OOBE 是否已完成以及当前配置状态。
    前端在启动时调用此接口判断是否需要进入 OOBE 向导。
    """
    oobe_complete = is_oobe_complete()

    config_data = None
    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE, encoding="utf-8") as f:
                config_data = json.load(f)
            sensitive = ["db_password", "redis_password", "secret_key", "admin_password"]
            for field in sensitive:
                if field in config_data:
                    config_data[field] = "***"
        except Exception:
            pass

    return {
        "success": True,
        "oobe_complete": oobe_complete,
        "has_config": CONFIG_FILE.exists(),
        "state": None if oobe_complete else _load_state(),
        "config": config_data,
    }


@router.get("/state")
async def get_oobe_state():
    """获取当前 OOBE 详细状态（仅在 OOBE 未完成时可用）"""
    await require_oobe_incomplete()
    return {"success": True, **_load_state()}


@router.get("/check")
async def oobe_check_environment():
    """OOBE 环境检测端点

    返回各子环境字段（ok + 数据），单个子项失败不影响整体 HTTP 200 响应。
    """
    from backend.core.oobe_utils import (
        _ok,
        check_database_connectivity,
        check_disk_free_gb,
        check_memory_free_mb,
        check_python_version,
        check_redis_connectivity,
        check_uv_installed,
        run_command_check,
    )

    result: dict = {}

    result["python_version"] = check_python_version()

    # uv 检测
    uv_result = check_uv_installed()
    result["uv_installed"] = _ok(uv_result.get("ok", False), ok=uv_result.get("ok", False), error=uv_result.get("error"))
    if "uv_version" in uv_result:
        result["uv_version"] = _ok(uv_result["uv_version"])
    else:
        result["uv_version"] = {"ok": False, "value": None, "error": "not detected"}

    result["node_version"] = run_command_check("node_version", ["node", "--version"])
    result["pnpm_version"] = run_command_check("pnpm_version", ["pnpm", "--version"])

    result["database_connectivity"] = await check_database_connectivity()
    result["redis_connectivity"] = await check_redis_connectivity()
    result["disk_free_gb"] = check_disk_free_gb()
    result["memory_free_mb"] = check_memory_free_mb()

    return {"success": True, **result}


@router.get("/system-info")
async def get_system_info():
    """获取系统信息"""
    info = system_service.get_system_info()
    resources = info.resources
    return {
        "success": True,
        "os_name": info.system,
        "os_version": info.version,
        "os_type": info.platform,
        "processor": info.processor,
        "python_version": info.python_version,
        "architecture": info.machine,
        "total_memory_mb": round(resources.memory_total / (1024 * 1024)),
        "available_memory_mb": round(resources.memory_available / (1024 * 1024)),
        "disk_total_gb": round(resources.disk_total / (1024 * 1024 * 1024)),
        "disk_free_gb": round(resources.disk_available / (1024 * 1024 * 1024)),
        "python_path": sys.executable,
        "cpu_count": resources.cpu_count,
        "hostname": info.hostname,
    }


@router.get("/dependencies")
async def check_dependencies():
    """检查系统依赖状态"""
    deps = dependency_service.check_all()

    def _map_dep(_name, dep):
        from backend.core.setup_dependency import DependencyStatus

        available = dep.status in (DependencyStatus.INSTALLED, DependencyStatus.COMPATIBLE)
        return {
            "available": available,
            "version": dep.current_version or "",
            "required": dep.required_version or "",
            "message": dep.message or ("已安装" if available else "未检测到"),
        }

    result = {
        "success": True,
        "python": _map_dep("python", deps["python"]),
        "uv": _map_dep("uv", deps["uv"]),
        "node": _map_dep("nodejs", deps["nodejs"]),
        "pnpm": _map_dep("pnpm", deps["pnpm"]),
        "postgresql": _map_dep("postgresql", deps["postgresql"]),
        "redis": _map_dep("redis", deps["redis"]),
    }

    dependency_service._refresh_path()

    npm_available = shutil.which("npm") is not None
    npm_version = ""
    if npm_available:
        try:
            r = subprocess.run(["npm", "--version"], capture_output=True, text=True, timeout=10)
            if r.returncode == 0:
                npm_version = r.stdout.strip().lstrip("v")
        except Exception:
            pass
    if not npm_version:
        for npm_cmd in ["npm.cmd", "npm"]:
            try:
                npm_path = shutil.which(npm_cmd)
                if npm_path:
                    r = subprocess.run(
                        [npm_path, "--version"], capture_output=True, text=True, timeout=10
                    )
                    if r.returncode == 0 and r.stdout.strip():
                        npm_version = r.stdout.strip().lstrip("v")
                        npm_available = True
                        break
            except Exception:
                pass
    result["npm"] = {
        "available": npm_available,
        "version": npm_version,
        "required": "",
        "message": f"npm {npm_version} 已安装"
        if npm_available and npm_version
        else ("已安装" if npm_available else "未检测到"),
    }

    pip_available = shutil.which("pip") is not None or shutil.which("pip3") is not None
    pip_version = ""
    if pip_available:
        try:
            r = subprocess.run(
                [sys.executable, "-m", "pip", "--version"],
                capture_output=True,
                text=True,
                timeout=10,
            )
            if r.returncode == 0:
                parts = r.stdout.strip().split()
                if len(parts) >= 2:
                    pip_version = parts[1]
        except Exception:
            pass
    result["pip"] = {
        "available": pip_available,
        "version": pip_version,
        "required": "",
        "message": "已安装" if pip_available else "未检测到",
    }

    result["sqlite"] = {
        "available": True,
        "version": "",
        "required": "",
        "message": "Python 内置支持",
    }

    return result


@router.post("/install-dependencies")
async def install_dependencies():
    """安装缺失的依赖（工具链 + 后端 + 前端），对标 WordPress 一键安装

    触发时会在 HTTP 响应返回前立即开始执行；同时通过
    GET /api/oobe/install-dependencies/stream 广播实时日志。
    """
    await require_oobe_incomplete()

    # 将 DependencyService 的回调接到 SSE 广播，前端可实时看日志
    dep_logs: list[str] = []

    def _on_progress(name: str, status: str, message: str):
        _append_dep_progress({
            "type": "progress",
            "name": name,
            "status": status,
            "message": message,
            "timestamp": datetime.now().isoformat(),
        })

    def _on_log(message: str):
        dep_logs.append(message)
        _append_dep_progress({
            "type": "log",
            "message": message,
            "timestamp": datetime.now().isoformat(),
        })

    dependency_service.set_progress_callback(_on_progress)
    dependency_service.set_log_callback(_on_log)

    try:
        loop = asyncio.get_running_loop()
        # 注意：install_all 内部会做长时间 subprocess 调用，放到线程池中避免阻塞事件循环
        results = await loop.run_in_executor(None, dependency_service.install_all)
        summary = dependency_service.get_install_summary(results)
        # 广播最终 done
        all_ok = summary.get("all_success", False)
        _append_dep_progress({
            "type": "done",
            "success": all_ok,
            "summary": {k: v for k, v in summary.items() if k != "logs"},
            "timestamp": datetime.now().isoformat(),
        })
        return {"success": True, **summary}
    finally:
        dependency_service.set_progress_callback(None)
        dependency_service.set_log_callback(None)


@router.get("/install-dependencies/stream")
async def install_dependencies_stream(sid: str = Query(default_factory=lambda: _uuid.uuid4().hex)):
    """依赖安装进度 SSE 流（与 install-dependencies 配对）

    客户端在点击「一键安装」后立即连接此端点，实时接收：
      - event: connected    → 握手成功，含 buffered 数量
      - data: {...progress} → 单依赖进度回调
      - data: {...log}      → 实时命令行输出
      - data: {...done}     → 全部完成（success + summary）
    """

    async def _event_generator():
        q: asyncio.Queue = asyncio.Queue(maxsize=1000)
        _DEP_STREAM_QUEUES[sid] = q
        try:
            yield (
                f"event: connected\n"
                f"data: {json.dumps({'sid': sid, 'buffered': len(_DEP_STREAM_BUFFER)}, ensure_ascii=False)}\n\n"
            )
            for past in _DEP_STREAM_BUFFER:
                yield f"data: {json.dumps(past, ensure_ascii=False)}\n\n"
            while True:
                try:
                    evt = await asyncio.wait_for(q.get(), timeout=15.0)
                except asyncio.TimeoutError:
                    yield ": ping\n\n"
                    continue
                yield f"data: {json.dumps(evt, ensure_ascii=False)}\n\n"
                if evt.get("type") == "done" or evt.get("type") == "error":
                    break
        finally:
            _DEP_STREAM_QUEUES.pop(sid, None)

    return StreamingResponse(
        _event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


@router.post("/environment")
async def save_environment(request):
    """保存环境选择（旧分步式接口，兼容保留）

    .. deprecated::
        此接口将在未来版本移除，请使用 POST /api/oobe/install 一键安装代替。
    """
    await require_oobe_incomplete()
    logger.warning("DEPRECATED: POST /api/oobe/environment 被调用，请迁移到 POST /api/oobe/install")

    if not hasattr(request, "environment"):
        data = await request.json() if hasattr(request, "json") else {}
        env = data.get("environment", "production")
    else:
        env = request.environment

    if env not in ["development", "production"]:
        raise HTTPException(status_code=400, detail=t("oobe_invalid_env"))

    state = config_service.load_state() or config_service.state
    state.environment = Environment(env)
    if state.database_config:
        state.database_config["db_type"] = "sqlite" if env == "development" else "postgresql"
    config_service.save_state()

    return {"success": True, "environment": env}


@router.get("/install/stream")
async def oobe_install_stream(sid: str = Query(default_factory=lambda: _uuid.uuid4().hex)):
    """OOBE 安装进度 SSE 流

    客户端在发起 POST /api/oobe/install 之前或之后连接此端点，
    通过 sid 订阅安装进度事件（SSE text/event-stream）。
    """

    async def _event_generator():
        q: asyncio.Queue = asyncio.Queue(maxsize=500)
        _INSTALL_STREAM_QUEUES[sid] = q
        try:
            yield f"event: connected\ndata: {json.dumps({'sid': sid, 'buffered': len(_INSTALL_STREAM_BUFFER)}, ensure_ascii=False)}\n\n"
            for past in _INSTALL_STREAM_BUFFER:
                yield f"data: {json.dumps(past, ensure_ascii=False)}\n\n"
            while True:
                try:
                    evt = await asyncio.wait_for(q.get(), timeout=15.0)
                except asyncio.TimeoutError:
                    yield ": ping\n\n"
                    continue
                yield f"data: {json.dumps(evt, ensure_ascii=False)}\n\n"
                if evt.get("type") == "done" or evt.get("type") == "error":
                    break
        finally:
            _INSTALL_STREAM_QUEUES.pop(sid, None)

    return StreamingResponse(
        _event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


async def _run_combined_install(req: CombinedInstallRequest):
    """内部执行安装步骤，向 SSE 广播进度"""
    steps = [
        ("write_env", "写入环境配置 (.env)", 7),
        ("init_schema", "初始化数据库表结构", 20),
        ("create_admin", "创建管理员账户", 35),
        ("write_site_settings", "写入站点配置项", 50),
        ("mock_data", "生成示例数据 (Hello World)", 68),
        ("write_pages", "创建关于和留言板页面", 78),
        ("write_nav", "写入导航菜单", 88),
        ("finalize", "写入 rosetta.json 与 OOBE 完成标记", 100),
    ]

    def _pct(idx: int) -> int:
        return steps[idx][2]

    try:
        for idx, (sid_, msg, _) in enumerate(steps):
            await _broadcast_progress(sid_, f"正在{msg}...", max(0, _pct(idx) - 4))
            await asyncio.sleep(0.02)

        db_cfg_dict = {
            "db_type": req.database_type,
            "db_host": req.db_host,
            "db_port": req.db_port,
            "db_name": req.db_name,
            "db_user": req.db_user,
            "db_password": req.db_password,
            "db_path": req.db_path,
            "redis_host": req.redis_host,
            "redis_port": req.redis_port,
            "redis_password": req.redis_password,
            "redis_enabled": req.redis_enabled,
        }

        # 使用 ConfigService 构建配置（单源，避免与 setup_config.py 双写）
        state = config_service.state
        state.environment = Environment(req.environment)
        state.database_config = db_cfg_dict
        state.site_config = ConfigService._create_site_config(req)
        state.admin_config = ConfigService._create_admin_config(req)
        full_config = config_service.generate_config(state)
        # 补全 CombinedInstallRequest 独有字段
        full_config.update({
            "enable_bing_wallpaper": req.enable_bing_wallpaper,
            "enable_pagefind_search": req.enable_pagefind_search,
            "enable_encrypted_posts": req.enable_encrypted_posts,
            "enable_music_player": req.enable_music_player,
            "footer_text": "",
            "default_cover_image": "",
        })

        env_content = config_service.generate_env_content(full_config)
        with open(ENV_FILE, "w", encoding="utf-8") as f:
            f.write(env_content)

        database_url = generate_database_url(full_config)
        reset_engine(database_url)

        try:
            from backend.core import config as config_module

            if hasattr(config_module.get_settings, "cache_clear"):
                config_module.get_settings.cache_clear()
            config_module.settings = config_module.get_settings()
        except Exception:
            pass

        await _broadcast_progress(steps[0][0], "环境配置已写入", _pct(0))

        await init_db()
        await _broadcast_progress(steps[1][0], "表结构初始化完成", _pct(1))

        admin_id: int | None = None
        async with async_session_maker() as session:
            result = await session.execute(select(User).where(User.username == req.admin_username))
            admin = result.scalar_one_or_none()
            if not admin:
                admin = User(
                    username=req.admin_username,
                    email=req.admin_email,
                    password_hash=get_password_hash(req.admin_password),
                    nickname=req.admin_nickname or req.admin_username,
                    bio=getattr(req, "admin_bio", None) or None,
                    qq=getattr(req, "admin_qq", None) or None,
                    github=(
                        f"https://github.com/{req.admin_github}"
                        if getattr(req, "admin_github", None) and "://" not in req.admin_github
                        else (getattr(req, "admin_github", None) or None)
                    ),
                    website=getattr(req, "admin_website", None) or None,
                    avatar_source=getattr(req, "admin_avatar_source", "auto") or "auto",
                    is_active=True,
                    is_staff=True,
                    is_superuser=True,
                )
                session.add(admin)
                await session.flush()
            admin_id = admin.id
            await session.commit()
        await _broadcast_progress(steps[2][0], "管理员账户已创建", _pct(2))

        site_config_rows = [
            ("site_name", req.site_name, "站点名称"),
            ("site_description", req.site_description, "站点描述"),
            ("site_url", req.site_url, "站点URL"),
            ("site_keywords", req.site_keywords, "SEO关键词"),
            ("site_author", req.site_author, "站点作者"),
            ("site_email", req.site_email, "联系邮箱"),
            ("footer_text", full_config["footer_text"], "页脚介绍文本"),
            ("enable_comments", str(req.enable_comments).lower(), "启用评论"),
            ("enable_registration", str(req.enable_registration).lower(), "开放注册"),
            (FEATURE_FLAG_DB_KEY_MAP.get("enable_rss", "enable_rss_feed"), str(req.enable_rss).lower(), "启用RSS"),
            ("enable_bing_wallpaper", str(req.enable_bing_wallpaper).lower(), "启用Bing壁纸"),
            ("enable_pagefind_search", str(req.enable_pagefind_search).lower(), "启用Pagefind搜索"),
            ("enable_encrypted_posts", str(req.enable_encrypted_posts).lower(), "启用加密文章"),
            ("enable_music_player", str(req.enable_music_player).lower(), "启用音乐播放器"),
            ("default_cover_image", full_config["default_cover_image"], "默认封面图"),
            # 作者 / 侧边栏资料：与 OOBE 管理员昵称/bio 对齐，避免前端 fallback 为 ROSETTA 示例文案
            ("author_name", full_config.get("author_name") or req.admin_nickname or req.admin_username, "作者昵称"),
            ("author_bio", full_config.get("author_bio") or getattr(req, "admin_bio", "") or "", "作者签名"),
            ("author_avatar", full_config.get("author_avatar", "") or "", "作者头像"),
            ("author_links_json", full_config.get("author_links_json", "[]") or "[]", "作者社交链接"),
            ("enable_pio", "false", "启用看板娘(Pio)"),
        ]
        async with async_session_maker() as session:
            for k, v, desc in site_config_rows:
                ex = await session.execute(select(DbSiteConfig).where(DbSiteConfig.key == k))
                if ex.scalar_one_or_none():
                    continue
                session.add(DbSiteConfig(key=k, value=str(v), description=desc))
            await session.commit()
        await _broadcast_progress(steps[3][0], "站点配置写入完成", _pct(3))

        from backend.scripts.mock_data import generate_oobe_mock_data

        async with async_session_maker() as session:
            await generate_oobe_mock_data(session, admin_id=admin_id)
        await _broadcast_progress(steps[4][0], "示例数据生成完成", _pct(4))

        async with async_session_maker() as session:
            existing_about = await session.execute(select(Page).where(Page.slug == "about"))
            if not existing_about.scalar_one_or_none():
                session.add(
                    Page(
                        title={"zh": "关于", "en": "About", "ja": "概要", "zh_TW": "關於"},
                        slug="about",
                        content={
                            "zh": "# 关于\n\n欢迎来到我们的博客！",
                            "en": "# About\n\nWelcome to our blog!",
                            "ja": "# 概要\n\n私たちのブログへようこそ！",
                            "zh_TW": "# 關於\n\n歡迎來到我們的部落格！",
                        },
                        status="published",
                    )
                )
            existing_gb = await session.execute(select(Page).where(Page.slug == "guestbook"))
            if not existing_gb.scalar_one_or_none():
                session.add(
                    Page(
                        title={
                            "zh": "留言板",
                            "en": "Guestbook",
                            "ja": "ゲストブック",
                            "zh_TW": "留言板",
                        },
                        slug="guestbook",
                        content={
                            "zh": "# 留言板\n\n欢迎留言！",
                            "en": "# Guestbook\n\nLeave a message!",
                            "ja": "# ゲストブック\n\nメッセージを残してください！",
                            "zh_TW": "# 留言板\n\n歡迎留言！",
                        },
                        status="published",
                    )
                )
            await session.commit()
        await _broadcast_progress(steps[5][0], "默认页面创建完成", _pct(5))

        default_navs = [
            ("首页", "Home", "ホーム", "首頁", "/", 1),
            ("文章", "Posts", "記事", "文章", "/posts", 2),
            ("分类", "Categories", "カテゴリー", "分類", "/categories", 3),
            ("标签", "Tags", "タグ", "標籤", "/tags", 4),
            ("关于", "About", "概要", "關於", "/page/about", 5),
            ("留言板", "Guestbook", "ゲストブック", "留言板", "/page/guestbook", 6),
        ]
        async with async_session_maker() as session:
            for zh, en, ja, tw, url, order in default_navs:
                ex = await session.execute(select(Navigation).where(Navigation.url == url))
                if ex.scalar_one_or_none():
                    continue
                session.add(
                    Navigation(
                        title={"zh": zh, "en": en, "ja": ja, "zh_TW": tw},
                        url=url,
                        location="header",
                        order=order,
                        is_active=True,
                    )
                )
            await session.commit()
        await _broadcast_progress(steps[6][0], "导航菜单写入完成", _pct(6))

        for sensitive_field in ["admin_password", "db_password", "redis_password"]:
            full_config.pop(sensitive_field, None)

        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(full_config, f, indent=2, ensure_ascii=False)

        with open(OOBE_LOCK_FILE, "w", encoding="utf-8") as f:
            f.write(datetime.now().isoformat())

        if STATE_FILE.exists():
            try:
                STATE_FILE.unlink()
            except Exception:
                pass

        await _broadcast_progress(steps[7][0], "安装完成！", 100)
        done_evt = {
            "type": "done",
            "success": True,
            "frontend_url": req.site_url,
            "admin_url": f"{req.site_url.rstrip('/')}/admin",
        }
        _append_progress(done_evt)
        return done_evt

    except Exception as e:
        logger.exception("OOBE combined install failed")
        err_evt = {
            "type": "error",
            "success": False,
            "message": str(e),
            "traceback": traceback.format_exc(),
        }
        _append_progress(err_evt)
        raise


@router.post("/install")
async def oobe_install(req: CombinedInstallRequest):
    """OOBE 一键安装端点

    幂等：若 OOBE 已完成则返回 409 + OOBE_ALREADY_COMPLETED。
    安装顺序严格按 spec 执行：env -> schema -> admin -> site_settings -> mock_data -> pages/navs -> 标记文件。
    """
    if is_oobe_complete():
        raise OOBEAlreadyCompletedException()

    if len(req.admin_password) < 8:
        raise WeakPasswordException("管理员密码至少 8 位")

    try:
        done = await _run_combined_install(req)
    except OOBEAlreadyCompletedException:
        raise
    except WeakPasswordException:
        raise
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"安装失败: {e}\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"安装失败: {e}")

    return {
        "success": True,
        "frontend_url": done.get("frontend_url", req.site_url),
        "admin_url": done.get("admin_url", f"{req.site_url.rstrip('/')}/admin"),
    }


class DatabaseConfigRequest(BaseModel):
    db_type: str = "sqlite"
    db_host: str = "localhost"
    db_port: int = 5432
    db_name: str = "rosetta"
    db_user: str = ""
    db_password: str = ""
    db_path: str = "rosetta.db"
    redis_host: str = "localhost"
    redis_port: int = 6379
    redis_password: str = ""
    redis_enabled: bool = False


class SiteConfigRequest(BaseModel):
    site_name: str = "Rosetta"
    site_title: str = ""
    site_description: str = ""
    site_keywords: str = ""
    site_author: str = ""
    site_email: str = ""
    site_url: str = "http://localhost:4321"
    github_url: str = ""
    x_url: str = ""
    bilibili_url: str = ""
    footer_text: str = ""
    enable_comments: bool = True
    enable_registration: bool = True
    enable_rss: bool = True
    default_cover_image: str = ""


class AdminAccountRequest(BaseModel):
    username: str
    email: str
    nickname: str = ""
    password: str


class EnvironmentRequest(BaseModel):
    environment: str = "development"


@router.post("/database-config")
async def save_database_config(request: DatabaseConfigRequest):
    """保存数据库配置（旧分步式接口，兼容保留）

    .. deprecated::
        此接口将在未来版本移除，请使用 POST /api/oobe/install 一键安装代替。
    """
    await require_oobe_incomplete()
    logger.warning("DEPRECATED: POST /api/oobe/database-config 被调用，请迁移到 POST /api/oobe/install")
    if request.db_type != "sqlite" and not request.db_user:
        raise HTTPException(status_code=400, detail=t("oobe_db_user_empty"))
    if not request.db_name:
        raise HTTPException(status_code=400, detail=t("oobe_db_name_empty"))

    state = config_service.load_state() or config_service.state
    db_config_dict = {
        "db_type": request.db_type,
        "db_host": request.db_host,
        "db_port": request.db_port,
        "db_name": request.db_name,
        "db_user": request.db_user,
        "db_password": request.db_password,
        "db_path": request.db_path,
        "redis_host": request.redis_host,
        "redis_port": request.redis_port,
        "redis_password": request.redis_password,
        "redis_enabled": request.redis_enabled,
    }
    state.database_config = db_config_dict
    config_service.save_state()

    return {
        "success": True,
        "config": {k: v for k, v in db_config_dict.items() if "password" not in k},
    }


@router.get("/test-database")
async def test_database(
    db_type: str = "sqlite",
    db_host: str = "localhost",
    db_port: int = 5432,
    db_name: str = "rosetta",
    db_user: str = "",
    db_password: str = "",
):
    """测试数据库连接"""
    if db_type == "sqlite":
        database_url = generate_database_url({"db_type": "sqlite", "db_name": db_name})
        return {
            "success": True,
            "message": t("oobe_sqlite_no_test"),
            "database_url": database_url,
        }
    return await database_service.test_postgresql_connection(
        host=db_host,
        port=db_port,
        user=db_user,
        password=db_password,
        database="postgres",
        timeout=5,
    )


@router.post("/site-config")
async def save_site_config(request: SiteConfigRequest):
    """保存站点配置（旧分步式接口，兼容保留）

    .. deprecated::
        此接口将在未来版本移除，请使用 POST /api/oobe/install 一键安装代替。
    """
    await require_oobe_incomplete()
    logger.warning("DEPRECATED: POST /api/oobe/site-config 被调用，请迁移到 POST /api/oobe/install")
    if not request.site_name:
        raise HTTPException(status_code=400, detail=t("oobe_site_name_empty"))
    if not request.site_email:
        raise HTTPException(status_code=400, detail=t("oobe_site_email_empty"))

    state = config_service.load_state() or config_service.state
    if not state.site_config:
        from backend.core.setup_config import SiteConfig as _SiteConfig

        state.site_config = _SiteConfig()

    state.site_config.site_name = request.site_name
    state.site_config.site_title = request.site_title
    state.site_config.site_description = request.site_description
    state.site_config.site_keywords = request.site_keywords
    state.site_config.site_author = request.site_author
    state.site_config.site_email = request.site_email
    state.site_config.site_url = request.site_url
    state.site_config.github_url = request.github_url
    state.site_config.x_url = request.x_url
    state.site_config.bilibili_url = request.bilibili_url
    state.site_config.footer_text = request.footer_text
    state.site_config.enable_comments = request.enable_comments
    state.site_config.enable_registration = request.enable_registration
    state.site_config.enable_rss = request.enable_rss
    state.site_config.default_cover_image = request.default_cover_image
    config_service.save_state()

    return {"success": True}


@router.get("/check-username")
async def check_username(username: str):
    """检查用户名是否可用"""
    if len(username) < USERNAME_MIN_LENGTH:
        return {"available": False, "message": t("oobe_username_min")}
    if len(username) > USERNAME_MAX_LENGTH:
        return {"available": False, "message": t("oobe_username_max")}
    if not username.replace("_", "").replace("-", "").isalnum():
        return {"available": False, "message": t("oobe_username_invalid")}
    return {"available": True}


@router.post("/admin-account")
async def save_admin_account(request: AdminAccountRequest):
    """保存管理员账户信息（旧分步式接口，兼容保留）

    .. deprecated::
        此接口将在未来版本移除，请使用 POST /api/oobe/install 一键安装代替。
    """
    await require_oobe_incomplete()
    logger.warning("DEPRECATED: POST /api/oobe/admin-account 被调用，请迁移到 POST /api/oobe/install")
    if len(request.username) < USERNAME_MIN_LENGTH:
        raise HTTPException(status_code=400, detail=t("oobe_username_min"))
    if len(request.username) > USERNAME_MAX_LENGTH:
        raise HTTPException(status_code=400, detail=t("oobe_username_max"))
    if not request.username.replace("_", "").replace("-", "").isalnum():
        raise HTTPException(status_code=400, detail=t("oobe_username_invalid"))
    if len(request.password) < PASSWORD_MIN_LENGTH:
        raise HTTPException(status_code=400, detail=t("oobe_password_min"))

    state = config_service.load_state() or config_service.state
    if not state.admin_config:
        from backend.core.setup_config import AdminConfig as _AdminConfig

        state.admin_config = _AdminConfig()

    state.admin_config.username = request.username
    state.admin_config.email = request.email
    state.admin_config.password = request.password
    state.admin_config.nickname = request.nickname or request.username
    config_service.save_state()

    return {"success": True}


@router.post("/complete")
async def complete_oobe(db: AsyncSession = Depends(get_db)):
    """完成 OOBE 配置 - 写入配置并初始化数据库（旧分步式接口，兼容保留）

    .. deprecated::
        此接口将在未来版本移除，请使用 POST /api/oobe/install 一键安装代替。
    """
    await require_oobe_incomplete()
    logger.warning("DEPRECATED: POST /api/oobe/complete 被调用，请迁移到 POST /api/oobe/install")

    state = config_service.load_state()
    if not state or not state.admin_config or not state.admin_config.username:
        raise HTTPException(status_code=400, detail=t("oobe_admin_not_created"))

    try:
        admin_cfg = state.admin_config
        site_cfg = state.site_config
        db_cfg = state.database_config or {}
        if not db_cfg:
            db_cfg = {
                "db_type": "sqlite",
                "db_host": "",
                "db_port": 5432,
                "db_name": "rosetta",
                "db_user": "",
                "db_password": "",
                "db_path": "rosetta.db",
                "redis_host": "localhost",
                "redis_port": 6379,
                "redis_password": "",
            }

        config_dict = config_service.generate_config(state)

        env_content = config_service.generate_env_content(config_dict)
        with open(ENV_FILE, "w", encoding="utf-8") as f:
            f.write(env_content)

        database_url = generate_database_url(config_dict)
        reset_engine(database_url)

        try:
            from backend.core import config as config_module

            if hasattr(config_module.get_settings, "cache_clear"):
                config_module.get_settings.cache_clear()
            config_module.settings = config_module.get_settings()
        except Exception:
            pass

        await init_db()

        result = await db.execute(
            select(User).where(User.username == config_dict["admin_username"])
        )
        admin_id: int | None = None
        if not result.scalar_one_or_none():
            admin = User(
                username=config_dict["admin_username"],
                email=config_dict["admin_email"],
                password_hash=get_password_hash(config_dict["admin_password"]),
                nickname=config_dict["admin_nickname"],
                is_active=True,
                is_staff=True,
                is_superuser=True,
            )
            db.add(admin)
            await db.flush()
            admin_id = admin.id

        site_configs = [
            DbSiteConfig(key="site_name", value=config_dict["site_name"], description="站点名称"),
            DbSiteConfig(
                key="site_title", value=config_dict.get("site_title", ""), description="网站标题"
            ),
            DbSiteConfig(
                key="site_description",
                value=config_dict["site_description"],
                description="站点描述",
            ),
            DbSiteConfig(
                key="site_keywords", value=config_dict["site_keywords"], description="SEO关键词"
            ),
            DbSiteConfig(
                key="site_author", value=config_dict["site_author"], description="站点作者"
            ),
            DbSiteConfig(key="site_email", value=config_dict["site_email"], description="联系邮箱"),
            DbSiteConfig(key="site_url", value=config_dict["site_url"], description="站点URL"),
            DbSiteConfig(key="github_url", value=config_dict["github_url"], description="GitHub"),
            DbSiteConfig(key="x_url", value=config_dict["x_url"], description="X (Twitter)"),
            DbSiteConfig(
                key="bilibili_url", value=config_dict["bilibili_url"], description="Bilibili"
            ),
            DbSiteConfig(
                key="footer_text",
                value=config_dict.get("footer_text", ""),
                description="页脚介绍文本",
            ),
            DbSiteConfig(
                key="enable_comments",
                value=str(config_dict["enable_comments"]).lower(),
                description="启用评论",
            ),
            DbSiteConfig(
                key="enable_registration",
                value=str(config_dict["enable_registration"]).lower(),
                description="开放注册",
            ),
            DbSiteConfig(
                key=FEATURE_FLAG_DB_KEY_MAP.get("enable_rss", "enable_rss_feed"),
                value=str(config_dict["enable_rss"]).lower(),
                description="启用RSS",
            ),
            DbSiteConfig(
                key="default_cover_image",
                value=config_dict["default_cover_image"],
                description="默认封面图",
            ),
            # 作者 / 侧边栏资料：与 OOBE 管理员昵称/bio 对齐
            DbSiteConfig(
                key="author_name",
                value=config_dict.get("author_name") or config_dict.get("admin_nickname") or "",
                description="作者昵称",
            ),
            DbSiteConfig(
                key="author_bio",
                value=config_dict.get("author_bio", "") or "",
                description="作者签名",
            ),
            DbSiteConfig(
                key="author_avatar",
                value=config_dict.get("author_avatar", "") or "",
                description="作者头像",
            ),
            DbSiteConfig(
                key="author_links_json",
                value=config_dict.get("author_links_json", "[]") or "[]",
                description="作者社交链接",
            ),
        ]
        for sc in site_configs:
            existing = await db.execute(select(DbSiteConfig).where(DbSiteConfig.key == sc.key))
            if existing.scalar_one_or_none():
                continue
            db.add(sc)

        cat_result = await db.execute(select(Category).where(Category.slug == "uncategorized"))
        if not cat_result.scalar_one_or_none():
            default_category = Category(
                name={"zh": "未分类", "en": "Uncategorized", "ja": "未分類", "zh_TW": "未分類"},
                slug="uncategorized",
                description={
                    "zh": "默认分类",
                    "en": "Default category",
                    "ja": "デフォルト分類",
                    "zh_TW": "預設分類",
                },
                color="primary",
            )
            db.add(default_category)

        default_tags = [
            Tag(
                name={"zh": "技术", "en": "Technology", "ja": "技術", "zh_TW": "技術"},
                slug="technology",
                color="#3B82F6",
            ),
            Tag(
                name={"zh": "生活", "en": "Life", "ja": "生活", "zh_TW": "生活"},
                slug="life",
                color="#10B981",
            ),
            Tag(
                name={"zh": "随笔", "en": "Essay", "ja": "随筆", "zh_TW": "隨筆"},
                slug="essay",
                color="#8B5CF6",
            ),
        ]
        for tag in default_tags:
            tresult = await db.execute(select(Tag).where(Tag.slug == tag.slug))
            if not tresult.scalar_one_or_none():
                db.add(tag)

        page_about = await db.execute(select(Page).where(Page.slug == "about"))
        if not page_about.scalar_one_or_none():
            about_page = Page(
                title={"zh": "关于", "en": "About", "ja": "概要", "zh_TW": "關於"},
                slug="about",
                content={
                    "zh": "# 关于\n\n欢迎来到我们的博客！",
                    "en": "# About\n\nWelcome to our blog!",
                    "ja": "# 概要\n\n私たちのブログへようこそ！",
                    "zh_TW": "# 關於\n\n歡迎來到我們的部落格！",
                },
                status="published",
            )
            db.add(about_page)

        page_gb = await db.execute(select(Page).where(Page.slug == "guestbook"))
        if not page_gb.scalar_one_or_none():
            guestbook_page = Page(
                title={"zh": "留言板", "en": "Guestbook", "ja": "ゲストブック", "zh_TW": "留言板"},
                slug="guestbook",
                content={
                    "zh": "# 留言板\n\n欢迎留言！",
                    "en": "# Guestbook\n\nLeave a message!",
                    "ja": "# ゲストブック\n\nメッセージを残してください！",
                    "zh_TW": "# 留言板\n\n歡迎留言！",
                },
                status="published",
            )
            db.add(guestbook_page)

        default_navs = [
            Navigation(
                title={"zh": "首页", "en": "Home", "ja": "ホーム", "zh_TW": "首頁"},
                url="/",
                location="header",
                order=1,
                is_active=True,
            ),
            Navigation(
                title={"zh": "文章", "en": "Posts", "ja": "記事", "zh_TW": "文章"},
                url="/posts",
                location="header",
                order=2,
                is_active=True,
            ),
            Navigation(
                title={"zh": "分类", "en": "Categories", "ja": "カテゴリー", "zh_TW": "分類"},
                url="/categories",
                location="header",
                order=3,
                is_active=True,
            ),
            Navigation(
                title={"zh": "标签", "en": "Tags", "ja": "タグ", "zh_TW": "標籤"},
                url="/tags",
                location="header",
                order=4,
                is_active=True,
            ),
            Navigation(
                title={"zh": "关于", "en": "About", "ja": "概要", "zh_TW": "關於"},
                url="/page/about",
                location="header",
                order=5,
                is_active=True,
            ),
            Navigation(
                title={"zh": "留言板", "en": "Guestbook", "ja": "ゲストブック", "zh_TW": "留言板"},
                url="/page/guestbook",
                location="header",
                order=6,
                is_active=True,
            ),
        ]
        for nav in default_navs:
            nresult = await db.execute(select(Navigation).where(Navigation.url == nav.url))
            if not nresult.scalar_one_or_none():
                db.add(nav)

        await db.commit()

        if admin_id is None:
            r2 = await db.execute(
                select(User).where(User.username == config_dict["admin_username"])
            )
            u = r2.scalar_one_or_none()
            if u:
                admin_id = u.id

        if admin_id:
            try:
                from backend.scripts.mock_data import generate_oobe_mock_data

                await generate_oobe_mock_data(db, admin_id=admin_id)
            except Exception:
                pass

        for sensitive_field in ["admin_password", "db_password", "redis_password"]:
            config_dict.pop(sensitive_field, None)

        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(config_dict, f, indent=2, ensure_ascii=False)

        if state.admin_config:
            state.admin_config.password = ""
        if state.database_config:
            state.database_config["db_password"] = ""
            state.database_config["redis_password"] = ""
        config_service.save_state()

        with open(OOBE_LOCK_FILE, "w") as f:
            f.write(datetime.now().isoformat())

        if STATE_FILE.exists():
            try:
                STATE_FILE.unlink()
            except Exception:
                pass

        frontend_url = config_dict["site_url"]
        return {
            "success": True,
            "message": t("oobe_complete_success"),
            "frontend_url": frontend_url,
            "admin_url": f"{frontend_url}/admin",
            "config": {
                "site_name": config_dict["site_name"],
                "environment": config_dict["environment"],
                "admin_username": config_dict["admin_username"],
            },
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"完成配置失败: {e}\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"{t('oobe_complete_failed')}: {str(e)}")


@router.post("/reset")
async def reset_oobe():
    """重置 OOBE 状态（测试/开发使用），同时清空内存中的 SSE 进度缓冲"""
    config_service.reset_oobe()
    if STATE_FILE.exists():
        try:
            STATE_FILE.unlink()
        except Exception:
            pass
    if OOBE_LOCK_FILE.exists():
        try:
            OOBE_LOCK_FILE.unlink()
        except Exception:
            pass
    if CONFIG_FILE.exists():
        try:
            CONFIG_FILE.unlink()
        except Exception:
            pass
    _INSTALL_STREAM_BUFFER.clear()
    return {"success": True}
