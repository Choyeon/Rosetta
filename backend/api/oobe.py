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
import re
import shutil
import subprocess
import sys
import traceback
import uuid as _uuid
from datetime import datetime
from typing import Any, Literal

from fastapi import APIRouter, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import select

from backend.core.auth import aget_password_hash
from backend.core.config import settings
from backend.core.database import async_session_maker, init_db, reset_engine
from backend.core.deps import (
    CurrentUserOptional,
    is_oobe_complete,
    require_oobe_incomplete,
)
from backend.core.exceptions import (
    AppException,
    OOBEAlreadyCompletedException,
    WeakPasswordException,
)
from backend.core.i18n import t
from backend.core.oobe_constants import (
    EMAIL_PATTERN,
    FEATURE_FLAG_DB_KEY_MAP,
    PASSWORD_MIN_LENGTH,
    USERNAME_MAX_LENGTH,
    USERNAME_MIN_LENGTH,
    USERNAME_PATTERN,
)
from backend.core.paths import BASE_DIR, CONFIG_FILE, ENV_FILE, OOBE_LOCK_FILE, STATE_FILE
from backend.core.setup_config import ConfigService, Environment
from backend.core.setup_database import (
    DB_UNKNOWN,
    DatabaseService,
    classify_db_error,
    generate_database_url,
    scrub_database_url,
)
from backend.core.setup_dependency import DependencyService
from backend.core.setup_progress import ProgressService
from backend.core.setup_system import SystemService
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

    # 安全：管理员凭据一律必填，禁止默认值。
    # 历史版本这里给了 default（明文写死的用户名/邮箱/口令），后果有两个：
    #   1) POST /oobe/install 是匿名端点，body 省略 admin_password 即按默认口令建超管；
    #   2) 默认值会进 OpenAPI schema，非生产环境 /docs、/openapi.json 任何人可读到该口令。
    admin_username: str = Field(..., min_length=USERNAME_MIN_LENGTH, max_length=USERNAME_MAX_LENGTH)
    admin_email: str = Field(...)
    admin_password: str = Field(..., min_length=PASSWORD_MIN_LENGTH)
    # 空串而非写死昵称：`_run_combined_install` 里是 `admin_nickname or admin_username`，
    # 留空即自动取用户名，不需要任何"看起来像示例"的占位值。
    admin_nickname: str = ""

    # 管理员扩展资料（简介 / QQ / GitHub / 个人网站）。
    # 全部默认空串：这些字段以前填的是本项目作者的真实 QQ 号与个人域名，
    # 于是每一个用默认参数装出来的站点都会把作者的联系方式写进管理员资料、写进
    # 站点 URL 配置。OOBE 是**匿名**端点，等于任何人都能读到并复制这组个人信息。
    admin_bio: str = ""
    admin_qq: str = ""
    admin_github: str = ""
    admin_website: str = ""
    admin_avatar_source: str = "auto"

    site_name: str = "Rosetta"
    site_description: str = "一个功能齐全、主题优雅、开箱即用的现代博客引擎"
    # 站点 URL 必填：它会被写进 SiteConfig 并用来拼 admin_url / RSS / sitemap 的绝对地址，
    # 给默认值就会让所有省略该字段的部署都指向别人的域名。
    # 前端 OOBE 表单与 scripts/auto_oobe.py 都会显式传，省略只可能来自自研脚本。
    site_url: str = Field(..., min_length=1, description="站点对外访问地址（用于拼接绝对 URL）")
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

    @field_validator("admin_username")
    @classmethod
    def _check_admin_username(cls, v: str) -> str:
        # 长度由 Field(min_length/max_length) 兜住，这里补**字符集**。
        # 之前只查长度不查字符集，于是 `admin_username="张 三"` 能通过一键安装，
        # 却在后台用户列表/登录处表现不一致（`/oobe/check-username` 明明校验了字符集，
        # 但 install 走的是另一条路 —— 同一个字段两套口径）。
        if not re.match(USERNAME_PATTERN, v):
            raise ValueError("管理员用户名需为 3-20 位字母、数字、下划线或短横线")
        return v

    @field_validator("admin_email")
    @classmethod
    def _check_admin_email(cls, v: str) -> str:
        if not re.match(EMAIL_PATTERN, v):
            raise ValueError("管理员邮箱格式不正确")
        return v

    @field_validator("site_url")
    @classmethod
    def _check_site_url(cls, v: str) -> str:
        # 站点 URL 会被写进 SiteConfig 并用于拼 RSS / sitemap / 头像的绝对地址，
        # 写成 `example.com`（缺协议）会让生成的链接变成相对路径而 404。
        if not re.match(r"^https?://[^\s/$.?#].[^\s]*$", v):
            raise ValueError("站点地址需以 http:// 或 https:// 开头")
        return v.rstrip("/")

    @field_validator("admin_password")
    @classmethod
    def _check_admin_password(cls, v: str) -> str:
        if len(v) < PASSWORD_MIN_LENGTH:
            raise ValueError(f"管理员密码至少 {PASSWORD_MIN_LENGTH} 位")
        return v


def _refresh_settings_inplace() -> None:
    """重读 .env 并**原地**刷新全局 settings 单例。

    不能 `config_module.settings = config_module.get_settings()` 重绑：
    各模块（rate_limit / users / csrf 等）在 import 时以
    `from backend.core.config import settings` 拿到的旧引用会全部失效，
    导致安装完成后这些模块永远读取不到新配置（内存中出现两个 settings 对象）。
    原地交换 __dict__ 可保持对象身份不变，所有持有引用的模块立即看到新值。
    """
    try:
        from backend.core import config as config_module

        if hasattr(config_module.get_settings, "cache_clear"):
            config_module.get_settings.cache_clear()
        _fresh = config_module.get_settings()
        _existing = config_module.settings
        object.__setattr__(_existing, "__dict__", dict(_fresh.__dict__))
        object.__setattr__(
            _existing, "__pydantic_fields_set__", set(_fresh.__pydantic_fields_set__)
        )
    except Exception:
        logger.exception("刷新全局 settings 失败（将沿用安装前配置）")


class OOBEInstallFailedException(AppException):
    """安装期失败：带结构化错误码与可操作提示，且不回显数据库口令。

    单独定义而不是直接 `HTTPException(500, str(e))`，是因为后者会把 asyncpg 的
    异常原文（可能含 `postgresql://user:password@host/db`）原样回给匿名调用方。
    """

    def __init__(self, message: str, error_code: str, hint: str | None = None):
        super().__init__(status_code=500, message=message, error_code=error_code,
                         details={"hint": hint} if hint else None)
        self.hint = hint


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

# 进度流空闲上限：15s 心跳 × 40 ≈ 10 分钟无事件即关闭。两条 /stream 端点位于
# OOBE 白名单内（匿名可连），不设上限会让单个客户端永久占住连接与协程。
_STREAM_MAX_IDLE_PINGS = 40

# R1-U2: 安装幂等性 —— 单 worker 内禁止并发重入一键安装，
# 避免 OOBE 标记文件写入前两个请求交错进入导致双写 admin/重复 mock 数据。
_INSTALL_LOCK = asyncio.Lock()
_INSTALL_LOCK_ACQUIRED = False


def _append_progress(evt: dict):
    _INSTALL_STREAM_BUFFER.append(evt)
    if len(_INSTALL_STREAM_BUFFER) > _INSTALL_STREAM_BUFFER_MAX:
        _INSTALL_STREAM_BUFFER[:] = _INSTALL_STREAM_BUFFER[-_INSTALL_STREAM_BUFFER_MAX:]
    for q in list(_INSTALL_STREAM_QUEUES.values()):
        try:
            q.put_nowait(evt)
        except asyncio.QueueFull:
            # 订阅者掉线/消费不过来时丢弃该事件：缓冲 `_INSTALL_STREAM_BUFFER` 仍是完整真相，
            # 客户端重连会重放缓冲。只收窄到 QueueFull，其余异常照抛。
            pass


def _append_dep_progress(evt: dict):
    """依赖安装流式日志广播（SSE 共享同一缓冲语义）"""
    _DEP_STREAM_BUFFER.append(evt)
    if len(_DEP_STREAM_BUFFER) > _DEP_STREAM_BUFFER_MAX:
        _DEP_STREAM_BUFFER[:] = _DEP_STREAM_BUFFER[-_DEP_STREAM_BUFFER_MAX:]
    for q in list(_DEP_STREAM_QUEUES.values()):
        try:
            q.put_nowait(evt)
        except asyncio.QueueFull:
            pass


def _sse_progress_stream(
    queues: dict[str, asyncio.Queue],
    buffer: list[dict],
    sid: str,
    *,
    maxsize: int,
) -> StreamingResponse:
    """OOBE 进度 SSE 通用实现：回放缓冲 → 订阅队列 → done/error 或空闲超限关闭。

    调用方（两条 GET /stream 端点）必须先 ``await require_oobe_incomplete()``：
    缓冲内含安装期 pip/npm 命令输出，安装完成后不得再向匿名请求回放。
    """

    async def _event_generator():
        q: asyncio.Queue = asyncio.Queue(maxsize=maxsize)
        queues[sid] = q
        idle_pings = 0
        try:
            connected = {"sid": sid, "buffered": len(buffer)}
            yield f"event: connected\ndata: {json.dumps(connected, ensure_ascii=False)}\n\n"
            for past in list(buffer):
                yield f"data: {json.dumps(past, ensure_ascii=False)}\n\n"
            while True:
                try:
                    evt = await asyncio.wait_for(q.get(), timeout=15.0)
                except asyncio.TimeoutError:
                    idle_pings += 1
                    if idle_pings >= _STREAM_MAX_IDLE_PINGS:
                        timeout_evt = {
                            "type": "error",
                            "message": "进度流空闲超时，已关闭（可重新连接）",
                        }
                        yield f"data: {json.dumps(timeout_evt, ensure_ascii=False)}\n\n"
                        break
                    yield ": ping\n\n"
                    continue
                idle_pings = 0
                yield f"data: {json.dumps(evt, ensure_ascii=False)}\n\n"
                if evt.get("type") in ("done", "error"):
                    break
        finally:
            queues.pop(sid, None)

    return StreamingResponse(
        _event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


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


def _read_config_file() -> dict | None:
    """同步读取配置文件（供 asyncio.to_thread 调用）"""
    with open(CONFIG_FILE, encoding="utf-8") as f:
        return json.load(f)


# ======================================================================
# 响应体文档模型（仅用于 OpenAPI 的 responses 声明，不参与序列化过滤）
# ======================================================================


class OobeWizardState(BaseModel):
    """向导断点状态（``_load_state()`` 的字段形态）。"""

    current_step: int = Field(..., description="当前所处步骤序号（1 起）")
    total_steps: int = Field(..., description="总步骤数，固定 5")
    environment: str = Field(..., description="环境选择：development 或 production")
    database_config: dict[str, Any] = Field(
        ...,
        description=(
            "数据库/Redis 配置草稿的键值集合（db_type、db_host、db_port、db_name、db_user、"
            "db_path、redis_host、redis_port、redis_enabled 等）；尚未填写时为空对象，"
            "密码类键不落在此处回显"
        ),
    )
    site_config: dict[str, Any] = Field(
        ...,
        description="站点配置草稿（site_name / site_url / 社交链接 / 功能开关等字段），未填写时为空对象",
    )
    admin_config: dict[str, Any] = Field(
        ..., description="管理员资料草稿（username / email / nickname），未填写时为空对象"
    )
    completed: bool = Field(..., description="向导是否已走到最后一步")
    errors: list[str] = Field(..., description="各步骤累积的错误摘要列表")


class OobeStateResponse(OobeWizardState):
    """GET /oobe/state 的响应体（状态字段平铺在顶层，无 data 信封）。"""

    success: bool = Field(..., description="固定为 true；OOBE 已完成时该端点被 503 短路")


class OobeStatusResponse(BaseModel):
    """GET /oobe/status 的响应体（匿名可访问，前端启动时首先调用）。"""

    success: bool = Field(..., description="固定为 true")
    oobe_complete: bool = Field(
        ..., description="安装锁是否存在；true 时前台正常放行，false 时其余接口 503"
    )
    has_config: bool = Field(..., description="配置文件是否已落盘")
    state: OobeWizardState | None = Field(
        default=None, description="向导断点状态；OOBE 已完成时为 null（不再对外暴露进度）"
    )
    config: dict[str, Any] | None = Field(
        default=None,
        description=(
            "已落盘配置文件的回显；数据库/Redis/管理员密码与 secret_key 一律替换为掩码串。"
            "文件不存在或读取失败时为 null"
        ),
    )


class OobeCheckItem(BaseModel):
    """环境检测单项结果（``_ok()`` 的字段形态）。"""

    ok: bool = Field(..., description="该项是否通过（可选组件失败也可能为 true）")
    value: Any = Field(
        default=None,
        description="探测值，类型随项而定：版本号字符串 / 布尔连通性 / 数值（GB 或 MB）；探测失败为 null",
    )
    error: str | None = Field(default=None, description="失败原因或告警提示；通过时为 null")


class OobeUvCheckItem(BaseModel):
    """uv 工具链检测项（额外带版本快照）。"""

    ok: bool = Field(..., description="uv 是否可用")
    value: bool = Field(..., description="与 ok 同义的布尔探针结果")
    error: str | None = Field(default=None, description="未检测到时的安装指引文本")
    uv_version: str | None = Field(
        default=None, description="解析出的 uv 版本号；仅在检测成功时存在该键"
    )


class OobeDiskCheckItem(OobeCheckItem):
    """磁盘可用空间检测项（附带总量与使用率）。"""

    display: str = Field(..., description="供向导直接渲染的一行摘要文案")
    os_summary: str = Field(..., description="系统概览文案（系统名 · 架构 · 核数）")
    total_gb: int = Field(..., description="卷总容量（GB）")
    used_gb: int = Field(..., description="已用容量（GB）")
    usage_pct: int = Field(..., description="使用率百分比")
    path: str = Field(..., description="被探测的卷路径")


class OobeMemoryCheckItem(OobeCheckItem):
    """可用内存检测项（附带总量、使用率与 CPU 概览）。"""

    display: str = Field(..., description="供向导直接渲染的一行摘要文案")
    cpu_count: int = Field(..., description="逻辑 CPU 核数")
    cpu_name: str = Field(..., description="CPU 型号名称，探测不到时为空串")
    arch: str = Field(..., description="CPU 架构标识，如 AMD64 / x86_64")
    total_mb: int = Field(..., description="物理内存总量（MB）")
    used_mb: int = Field(..., description="已用内存（MB）")
    usage_pct: int = Field(..., description="内存使用率百分比")
    avail_gb: float = Field(..., description="可用内存（GB，保留一位小数）")
    total_gb: float = Field(..., description="内存总量（GB，保留一位小数）")
    used_gb: float = Field(..., description="已用内存（GB，保留一位小数）")
    os_summary: str = Field(..., description="系统概览文案")


class OobeCheckResponse(BaseModel):
    """GET /oobe/check 的响应体：各项环境探测结果平铺在顶层。

    单项失败不影响整体 HTTP 200（前端按项渲染红绿灯）。
    """

    success: bool = Field(..., description="固定为 true")
    python_version: OobeCheckItem = Field(..., description="Python 解释器版本探测")
    uv_installed: OobeUvCheckItem = Field(..., description="uv 是否可用")
    uv_version: OobeCheckItem = Field(..., description="uv 版本号探测")
    node_version: OobeCheckItem = Field(..., description="node --version 探测")
    pnpm_version: OobeCheckItem = Field(..., description="pnpm --version 探测")
    database_connectivity: OobeCheckItem = Field(..., description="当前数据库连通性")
    redis_connectivity: OobeCheckItem = Field(
        ..., description="Redis 连通性（可选组件，失败也只给提示不阻断）"
    )
    disk_free_gb: OobeDiskCheckItem = Field(..., description="磁盘剩余空间")
    memory_free_mb: OobeMemoryCheckItem = Field(..., description="可用内存")


class OobeSystemInfoResponse(BaseModel):
    """GET /oobe/system-info 的响应体。"""

    success: bool = Field(..., description="固定为 true")
    os_name: str = Field(..., description="友好的操作系统名，如 Windows / macOS / 发行版全名")
    os_version: str = Field(..., description="操作系统版本串")
    os_type: str = Field(..., description="平台族标识：Windows / Darwin / Linux")
    processor: str = Field(..., description="CPU 型号名称，探测不到时为空串")
    python_version: str = Field(..., description="Python 解释器版本串")
    architecture: str = Field(..., description="机器架构标识，如 AMD64 / x86_64")
    total_memory_mb: int = Field(..., description="物理内存总量（MB，四舍五入）")
    available_memory_mb: int = Field(..., description="可用内存（MB，四舍五入）")
    disk_total_gb: int = Field(..., description="启动盘总容量（GB，四舍五入）")
    disk_free_gb: int = Field(..., description="启动盘剩余容量（GB，四舍五入）")
    python_path: str = Field(..., description="当前解释器可执行文件路径")
    cpu_count: int = Field(..., description="逻辑 CPU 核数")
    hostname: str = Field(..., description="主机名")


class OobeDependencyItem(BaseModel):
    """单个依赖/工具链的可用性条目。"""

    available: bool = Field(..., description="是否已安装（INSTALLED / COMPATIBLE 视为可用）")
    version: str = Field(..., description="当前版本串；探测不到时为空串")
    required: str = Field(..., description="要求版本；npm/pip/sqlite 等项不校验，恒为空串")
    message: str = Field(..., description="展示文案，如「已安装」「未检测到」「npm x.y 已安装」")


class OobeDependenciesResponse(BaseModel):
    """GET /oobe/dependencies 的响应体：按依赖名平铺的可用性条目。"""

    success: bool = Field(..., description="固定为 true")
    python: OobeDependencyItem = Field(..., description="Python 解释器")
    uv: OobeDependencyItem = Field(..., description="uv 包管理器")
    node: OobeDependencyItem = Field(..., description="Node.js（键名 node，检测项为 nodejs）")
    pnpm: OobeDependencyItem = Field(..., description="pnpm 包管理器")
    postgresql: OobeDependencyItem = Field(..., description="PostgreSQL 服务端")
    redis: OobeDependencyItem = Field(..., description="Redis 服务端（可选）")
    npm: OobeDependencyItem = Field(..., description="npm（随 Node 安装，仅作补充提示）")
    pip: OobeDependencyItem = Field(..., description="pip（当前解释器内置）")
    sqlite: OobeDependencyItem = Field(..., description="SQLite（Python 内置，恒为可用）")


class OobeInstallResultItem(BaseModel):
    """单个依赖的安装结果。"""

    status: str = Field(
        ..., description="安装状态：pending / installing / success / failed / skipped"
    )
    message: str = Field(..., description="结果说明")
    duration: float | None = Field(default=None, description="耗时（秒）；未执行为 null")


class OobeInstallDependenciesResponse(BaseModel):
    """POST /oobe/install-dependencies 的响应体（安装摘要平铺在顶层）。"""

    success: int | bool = Field(
        ...,
        description=(
            "注意：该键被展开的安装摘要覆盖，实际含义是**安装成功项计数**（int），"
            "不是布尔成功标记；判断整体是否全绿请看 all_success"
        ),
    )
    total: int = Field(..., description="参与安装的依赖项总数")
    failed: int = Field(..., description="失败项数")
    skipped: int = Field(..., description="跳过项数（已满足要求）")
    all_success: bool = Field(..., description="是否零失败")
    results: dict[str, OobeInstallResultItem] = Field(..., description="按依赖名聚合的逐项安装结果")
    logs: list[dict[str, Any]] = Field(..., description="安装期日志条目（命令输出等）")


class OobeEnvironmentResponse(BaseModel):
    """POST /oobe/environment 的响应体。"""

    success: bool = Field(..., description="固定为 true")
    environment: str = Field(..., description="已写入状态的运行环境：development 或 production")


class OobePreflightRequest(BaseModel):
    """安装前干跑校验的请求体：**所有字段可选**，只校验提交上来的那部分。

    设计成可选是因为向导要分步校验：Step2 只带管理员字段、Step3 只带站点与数据库字段，
    最后一次（点安装前）带全量。若强制必填，前端就得为每一步拼一份假 payload。
    """

    admin_username: str | None = None
    admin_email: str | None = None
    admin_password: str | None = None
    site_name: str | None = None
    site_url: str | None = None
    database_type: Literal["sqlite", "postgresql"] = "sqlite"
    db_host: str = "localhost"
    db_port: int = 5432
    db_name: str = "rosetta"
    db_user: str = ""
    db_password: str = ""
    db_path: str = "rosetta.db"
    # 是否真的去连数据库。默认 True；只想校验表单时传 false 可省掉一次网络往返。
    check_database: bool = True


class OobePreflightIssue(BaseModel):
    """预检发现的一条问题。前端按 `code` 分支渲染，不要去匹配 `message` 文案。"""

    field: str = Field(..., description="出问题的字段名（admin_username / site_url / database 等）")
    level: Literal["error", "warn"] = Field(..., description="error 阻断安装；warn 只提示")
    code: str = Field(..., description="结构化错误码，如 USERNAME_INVALID / DB_AUTH_FAILED")
    message: str = Field(..., description="人读的问题描述")
    hint: str | None = Field(default=None, description="可操作的下一步建议；无建议时为 null")


class OobePreflightDatabaseResult(BaseModel):
    """预检里的数据库体检结果。"""

    checked: bool = Field(..., description="是否真的做了连接探测")
    ok: bool = Field(..., description="是否可继续安装（库不存在但账号能建库时仍为 true）")
    code: str = Field(..., description="结构化错误码（DB_* 系列）")
    message: str = Field(..., description="人读结论")
    hint: str | None = Field(default=None, description="可操作的下一步建议")
    version: str | None = Field(default=None, description="探测到的 PostgreSQL 版本串")


class OobePreflightResponse(BaseModel):
    """POST /oobe/preflight 的响应体。"""

    success: bool = Field(..., description="固定为 true")
    ok: bool = Field(..., description="是否没有任何 error 级问题（warn 不影响）")
    issues: list[OobePreflightIssue] = Field(..., description="问题清单；全绿时为空数组")
    database: OobePreflightDatabaseResult = Field(..., description="数据库体检结果")


class OobeInstallResponse(BaseModel):
    """POST /oobe/install 的响应体（与 SSE done 事件字段口径一致）。"""

    success: bool = Field(..., description="固定为 true；失败走 4xx/5xx 错误信封")
    frontend_url: str = Field(..., description="站点前台地址（取自提交的站点 URL）")
    admin_url: str = Field(..., description="后台入口地址（前台 URL 追加 /admin）")


class OobeDatabaseConfigResponse(BaseModel):
    """POST /oobe/database-config 的响应体。"""

    success: bool = Field(..., description="固定为 true")
    config: dict[str, Any] = Field(
        ...,
        description=(
            "已保存的数据库/Redis 配置草稿回显，**密码类键（db_password、redis_password）已被剔除**，"
            "不随响应外泄"
        ),
    )


class OobeDatabaseTestResponse(BaseModel):
    """GET /oobe/test-database 的响应体（两种分支共用一个形态）。"""

    success: bool = Field(..., description="连接是否成功（SQLite 分支恒为 true）")
    message: str = Field(..., description="结果说明文案，含失败原因与安装依赖提示")
    database_url: str | None = Field(
        default=None, description="仅 SQLite 分支返回：由表单构建出的连接串（不含凭据）"
    )
    details: dict[str, Any] | None = Field(
        default=None,
        description="仅 PostgreSQL 分支返回：附加信息，成功时含服务端 version 文本，异常时含 warning",
    )


class OobeSimpleSuccessResponse(BaseModel):
    """只回布尔成功标记的写操作响应（站点配置、管理员账户、重置）。"""

    success: bool = Field(..., description="固定为 true；校验失败走 4xx/5xx 错误信封")


class OobeUsernameCheckResponse(BaseModel):
    """GET /oobe/check-username 的响应体（裸对象，无 success 信封）。"""

    available: bool = Field(..., description="用户名是否可用（长度与字符集校验通过即 true）")
    message: str | None = Field(
        default=None, description="不可用原因（四语文案）；可用时不返回该键"
    )


@router.get(
    "/status",
    summary="获取 OOBE 状态",
    description=(
        "匿名可访问（安装锁未摘时也在白名单内）。前端启动插件据此判断是否跳转 /oobe 向导；"
        "已完成时不再返回 state 进度。只读、幂等、无副作用。"
    ),
    responses={200: {"model": OobeStatusResponse, "description": "安装锁 + 断点状态 + 配置回显"}},
)
async def get_oobe_status():
    """获取 OOBE 状态

    返回 OOBE 是否已完成以及当前配置状态。
    前端在启动时调用此接口判断是否需要进入 OOBE 向导。
    """
    oobe_complete = is_oobe_complete()

    config_data = None
    if CONFIG_FILE.exists():
        try:
            # 文件读取为同步 IO，放入线程池避免阻塞事件循环
            config_data = await asyncio.to_thread(_read_config_file)
            sensitive = ["db_password", "redis_password", "secret_key", "admin_password"]
            for field in sensitive:
                if config_data and field in config_data:
                    config_data[field] = "***"
        except (OSError, ValueError, TypeError) as exc:
            # ValueError 覆盖 json.JSONDecodeError / UnicodeDecodeError。
            # 配置文件存在却读不出来时，向导会退回空配置（用户以为"上次填的没了"），
            # 判定不变但必须留痕，否则排障时无法区分"没写过配置"和"配置损坏"。
            logger.warning("[oobe] 配置文件读取失败，按未配置处理：%s", exc)

    return {
        "success": True,
        "oobe_complete": oobe_complete,
        "has_config": CONFIG_FILE.exists(),
        "state": None if oobe_complete else _load_state(),
        "config": config_data,
    }


@router.get(
    "/state",
    summary="获取向导断点状态",
    description=(
        "匿名可访问，但**仅 OOBE 未完成时可用**（require_oobe_incomplete），安装完成后返回 "
        "``503 OOBE_REQUIRED``。返回断点续传所需的步骤与环境/配置草稿。只读、幂等。"
    ),
    responses={
        200: {"model": OobeStateResponse, "description": "向导状态字段平铺（无 data 信封）"},
        503: {"description": "OOBE 已完成（error_code: OOBE_REQUIRED）"},
    },
)
async def get_oobe_state():
    """获取当前 OOBE 详细状态（仅在 OOBE 未完成时可用）"""
    await require_oobe_incomplete()
    return {"success": True, **_load_state()}


@router.get(
    "/check",
    summary="环境检测",
    description=(
        "匿名可访问（OOBE 白名单）。逐项探测 Python / uv / node / pnpm 版本、数据库与 Redis 连通性、"
        "磁盘与内存余量。**单项失败不影响整体 HTTP 200**，前端按项渲染红绿灯。只读、幂等。"
    ),
    responses={200: {"model": OobeCheckResponse, "description": "各检测项结果平铺在顶层"}},
)
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
    result["uv_installed"] = _ok(
        uv_result.get("ok", False), ok=uv_result.get("ok", False), error=uv_result.get("error")
    )
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


@router.get(
    "/system-info",
    summary="获取系统信息",
    description=(
        "匿名可访问（OOBE 白名单）。返回操作系统、CPU、内存、磁盘与当前解释器等主机概览，"
        "供向导第一步展示运行环境。只读、幂等。"
    ),
    responses={200: {"model": OobeSystemInfoResponse, "description": "主机概览"}},
)
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


@router.get(
    "/dependencies",
    summary="检查系统依赖",
    description=(
        "匿名可访问（OOBE 白名单）。逐项检测 python / uv / node / pnpm / postgresql / redis / npm / "
        "pip / sqlite 是否可用及版本；有副作用：检测后会刷新进程 PATH（``_refresh_path``），"
        "让刚安装的工具立即可见。"
    ),
    responses={200: {"model": OobeDependenciesResponse, "description": "按依赖名聚合的可用性条目"}},
)
async def check_dependencies():
    """检查系统依赖状态"""
    # check_all 内部调用 shutil.which / subprocess.run（同步阻塞），放入线程池
    deps = await asyncio.to_thread(dependency_service.check_all)

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

    # shutil.which 和 subprocess.run 为同步阻塞操作，放入线程池避免阻塞事件循环
    npm_available = await asyncio.to_thread(shutil.which, "npm") is not None
    npm_version = ""
    if npm_available:
        try:
            r = await asyncio.to_thread(
                lambda: subprocess.run(
                    ["npm", "--version"], capture_output=True, text=True, timeout=10
                )
            )
            if r.returncode == 0:
                npm_version = r.stdout.strip().lstrip("v")
        except (OSError, subprocess.SubprocessError, asyncio.TimeoutError):
            # 只影响版本号展示；类型收窄以免连带吞掉 NameError 等真实缺陷
            pass
    if not npm_version:
        for npm_cmd in ["npm.cmd", "npm"]:
            try:
                npm_path = await asyncio.to_thread(shutil.which, npm_cmd)
                if npm_path:
                    r = await asyncio.to_thread(
                        lambda: subprocess.run(
                            [npm_path, "--version"], capture_output=True, text=True, timeout=10
                        )
                    )
                    if r.returncode == 0 and r.stdout.strip():
                        npm_version = r.stdout.strip().lstrip("v")
                        npm_available = True
                        break
            except (OSError, subprocess.SubprocessError, asyncio.TimeoutError):
                # 只影响版本号展示；类型收窄以免连带吞掉 NameError 等真实缺陷
                pass
    result["npm"] = {
        "available": npm_available,
        "version": npm_version,
        "required": "",
        "message": f"npm {npm_version} 已安装"
        if npm_available and npm_version
        else ("已安装" if npm_available else "未检测到"),
    }

    pip_available = (
        await asyncio.to_thread(shutil.which, "pip") is not None
        or await asyncio.to_thread(shutil.which, "pip3") is not None
    )
    pip_version = ""
    if pip_available:
        try:
            r = await asyncio.to_thread(
                lambda: subprocess.run(
                    [sys.executable, "-m", "pip", "--version"],
                    capture_output=True,
                    text=True,
                    timeout=10,
                )
            )
            if r.returncode == 0:
                parts = r.stdout.strip().split()
                if len(parts) >= 2:
                    pip_version = parts[1]
        except (OSError, subprocess.SubprocessError, asyncio.TimeoutError):
            # 只影响版本号展示；类型收窄以免连带吞掉 NameError 等真实缺陷
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


@router.post(
    "/install-dependencies",
    summary="一键安装缺失依赖",
    description=(
        "匿名可访问，但**仅 OOBE 未完成时可调用**，完成后返回 ``503 OOBE_REQUIRED``。"
        "**高危副作用**：在服务器上执行 uv / npm / pip 等安装命令（工具链 + 后端 + 前端依赖），"
        "耗时较长；实时日志走 GET /oobe/install-dependencies/stream。"
        "响应里的 ``success`` 键是安装成功项计数而非布尔值，判断整体结果请看 ``all_success``。"
    ),
    responses={
        200: {"model": OobeInstallDependenciesResponse, "description": "安装摘要（平铺在顶层）"},
        503: {"description": "OOBE 已完成（error_code: OOBE_REQUIRED）"},
    },
)
async def install_dependencies():
    """安装缺失的依赖（工具链 + 后端 + 前端），对标 WordPress 一键安装

    触发时会在 HTTP 响应返回前立即开始执行；同时通过
    GET /api/oobe/install-dependencies/stream 广播实时日志。
    """
    await require_oobe_incomplete()

    # 将 DependencyService 的回调接到 SSE 广播，前端可实时看日志
    dep_logs: list[str] = []

    def _on_progress(name: str, status: str, message: str):
        _append_dep_progress(
            {
                "type": "progress",
                "name": name,
                "status": status,
                "message": message,
                "timestamp": datetime.now().isoformat(),
            }
        )

    def _on_log(message: str):
        dep_logs.append(message)
        _append_dep_progress(
            {
                "type": "log",
                "message": message,
                "timestamp": datetime.now().isoformat(),
            }
        )

    dependency_service.set_progress_callback(_on_progress)
    dependency_service.set_log_callback(_on_log)

    try:
        loop = asyncio.get_running_loop()
        # 注意：install_all 内部会做长时间 subprocess 调用，放到线程池中避免阻塞事件循环
        results = await loop.run_in_executor(None, dependency_service.install_all)
        summary = dependency_service.get_install_summary(results)
        # 广播最终 done
        all_ok = summary.get("all_success", False)
        _append_dep_progress(
            {
                "type": "done",
                "success": all_ok,
                "summary": {k: v for k, v in summary.items() if k != "logs"},
                "timestamp": datetime.now().isoformat(),
            }
        )
        return {"success": True, **summary}
    finally:
        dependency_service.set_progress_callback(None)
        dependency_service.set_log_callback(None)


@router.get(
    "/install-dependencies/stream",
    summary="依赖安装进度 SSE 流",
    description=(
        "与 POST /oobe/install-dependencies 配对：点击「一键安装」后连接本端点，"
        "实时接收 ``connected`` 握手、逐依赖进度、命令行日志与 ``done`` 汇总。"
        "**仅安装未完成（OOBE 锁存在）时可访问**：缓冲内含 pip/npm 命令输出，"
        "OOBE 完成后返回 ``503 OOBE_REQUIRED``；空闲约 10 分钟无事件自动关闭。"
        "事件载荷为 SSE 文本帧（type: connected / progress / log / done），不是 JSON 响应体。"
    ),
    responses={
        200: {
            "description": "SSE 事件流（逐帧 data: JSON 文本，以空行分隔）",
            "content": {"text/event-stream": {"schema": {"type": "string"}}},
        },
        503: {"description": "OOBE 已完成（error_code: OOBE_REQUIRED）"},
    },
)
async def install_dependencies_stream(
    sid: str = Query(default_factory=lambda: _uuid.uuid4().hex),
) -> StreamingResponse:
    """依赖安装进度 SSE 流（与 install-dependencies 配对）"""
    await require_oobe_incomplete()
    return _sse_progress_stream(_DEP_STREAM_QUEUES, _DEP_STREAM_BUFFER, sid, maxsize=1000)


@router.post(
    "/environment",
    summary="保存环境选择（已废弃）",
    description=(
        "**Deprecated**：旧分步式接口，仅为兼容保留，请改用 POST /oobe/install 一键安装。"
        "仅 OOBE 未完成时可用；把 environment 写进向导 state（development 会连带把库类型定为 sqlite、"
        "production 定为 postgresql）。非法取值返回 400。"
    ),
    responses={
        200: {"model": OobeEnvironmentResponse, "description": "已写入的环境标识"},
        400: {"description": "environment 不是 development / production"},
        503: {"description": "OOBE 已完成（error_code: OOBE_REQUIRED）"},
    },
)
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


@router.get(
    "/install/stream",
    summary="一键安装进度 SSE 流",
    description=(
        "客户端在发起 POST /oobe/install 前后连接，通过 ``sid`` 订阅安装进度事件。"
        "**仅安装未完成（OOBE 锁存在）时可访问**；空闲约 10 分钟无事件自动关闭。"
        "事件载荷为 SSE 文本帧（type: connected / progress / done / error），不是 JSON 响应体；"
        "``done`` 帧里的 frontend_url / admin_url 由向导消费，改字段需同步 useOOBE。"
    ),
    responses={
        200: {
            "description": "SSE 事件流（逐帧 data: JSON 文本，以空行分隔）",
            "content": {"text/event-stream": {"schema": {"type": "string"}}},
        },
        503: {"description": "OOBE 已完成（error_code: OOBE_REQUIRED）"},
    },
)
async def oobe_install_stream(
    sid: str = Query(default_factory=lambda: _uuid.uuid4().hex),
) -> StreamingResponse:
    """OOBE 安装进度 SSE 流"""
    await require_oobe_incomplete()
    return _sse_progress_stream(_INSTALL_STREAM_QUEUES, _INSTALL_STREAM_BUFFER, sid, maxsize=500)


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
        # ⚠️ 这里曾经一进来就把 8 个步骤的「正在…」全部播报一遍再开始干活
        # （percent 3→96 在 0.16s 内冲完）。后果是 UI 的步骤列表**瞬间全部点亮**、
        # 进度条直接跳到 96%，然后用户盯着一个"早就走完"的进度条等真正耗时的建表。
        # 现在改成：每个阶段开始前播「正在…」，结束后播「…完成」，进度条才跟得上真实进度。
        await _broadcast_progress(steps[0][0], f"正在{steps[0][1]}...", 2)

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
        full_config.update(
            {
                "enable_bing_wallpaper": req.enable_bing_wallpaper,
                "enable_pagefind_search": req.enable_pagefind_search,
                "enable_encrypted_posts": req.enable_encrypted_posts,
                "enable_music_player": req.enable_music_player,
                "footer_text": "",
                "default_cover_image": "",
            }
        )

        env_content = config_service.generate_env_content(full_config)
        with open(ENV_FILE, "w", encoding="utf-8") as f:
            f.write(env_content)

        database_url = generate_database_url(full_config)
        reset_engine(database_url)

        _refresh_settings_inplace()

        await _broadcast_progress(steps[0][0], "环境配置已写入", _pct(0))

        await _broadcast_progress(steps[1][0], f"正在{steps[1][1]}...", max(0, _pct(1) - 6))
        await init_db()
        await _broadcast_progress(steps[1][0], "表结构初始化完成", _pct(1))

        # R1-U2（二次幂等检查点）：拿到进程锁 + env/schema 写入后再次校验 OOBE 是否完成，
        # 防止并发请求在"未拿锁时"都通过了入口检查。
        if is_oobe_complete():
            raise OOBEAlreadyCompletedException()

        await _broadcast_progress(steps[2][0], f"正在{steps[2][1]}...", max(0, _pct(2) - 6))
        admin_id: int | None = None
        async with async_session_maker() as session:
            result = await session.execute(select(User).where(User.username == req.admin_username))
            admin = result.scalar_one_or_none()
            if not admin:
                admin = User(
                    username=req.admin_username,
                    email=req.admin_email,
                    password_hash=await aget_password_hash(req.admin_password),
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
            (
                FEATURE_FLAG_DB_KEY_MAP.get("enable_rss", "enable_rss_feed"),
                str(req.enable_rss).lower(),
                "启用RSS",
            ),
            ("enable_bing_wallpaper", str(req.enable_bing_wallpaper).lower(), "启用Bing壁纸"),
            ("enable_pagefind_search", str(req.enable_pagefind_search).lower(), "启用Pagefind搜索"),
            ("enable_encrypted_posts", str(req.enable_encrypted_posts).lower(), "启用加密文章"),
            ("enable_music_player", str(req.enable_music_player).lower(), "启用音乐播放器"),
            ("default_cover_image", full_config["default_cover_image"], "默认封面图"),
            # 作者 / 侧边栏资料：与 OOBE 管理员昵称/bio 对齐，避免前端 fallback 为 ROSETTA 示例文案
            (
                "author_name",
                full_config.get("author_name") or req.admin_nickname or req.admin_username,
                "作者昵称",
            ),
            (
                "author_bio",
                full_config.get("author_bio") or getattr(req, "admin_bio", "") or "",
                "作者签名",
            ),
            ("author_avatar", full_config.get("author_avatar", "") or "", "作者头像"),
            (
                "author_links_json",
                full_config.get("author_links_json", "[]") or "[]",
                "作者社交链接",
            ),
            ("enable_pio", "false", "启用看板娘(Pio)"),
        ]
        await _broadcast_progress(steps[3][0], f"正在{steps[3][1]}...", max(0, _pct(3) - 6))
        async with async_session_maker() as session:
            for k, v, desc in site_config_rows:
                ex = await session.execute(select(DbSiteConfig).where(DbSiteConfig.key == k))
                if ex.scalar_one_or_none():
                    continue
                session.add(DbSiteConfig(key=k, value=str(v), description=desc))
            await session.commit()
        await _broadcast_progress(steps[3][0], "站点配置写入完成", _pct(3))

        from backend.scripts.mock_data import generate_oobe_mock_data

        await _broadcast_progress(steps[4][0], f"正在{steps[4][1]}...", max(0, _pct(4) - 6))
        async with async_session_maker() as session:
            await generate_oobe_mock_data(session, admin_id=admin_id)
        await _broadcast_progress(steps[4][0], "示例数据生成完成", _pct(4))

        await _broadcast_progress(steps[5][0], f"正在{steps[5][1]}...", max(0, _pct(5) - 6))
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

        await _broadcast_progress(steps[6][0], f"正在{steps[6][1]}...", max(0, _pct(6) - 6))
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

        await _broadcast_progress(steps[7][0], f"正在{steps[7][1]}...", max(0, _pct(7) - 6))
        for sensitive_field in ["admin_password", "db_password", "redis_password"]:
            full_config.pop(sensitive_field, None)

        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(full_config, f, indent=2, ensure_ascii=False)

        with open(OOBE_LOCK_FILE, "w", encoding="utf-8") as f:
            f.write(datetime.now().isoformat())

        if STATE_FILE.exists():
            try:
                STATE_FILE.unlink()
            except OSError as exc:
                # 安装已成功（OOBE 锁文件已写），残留 state 不影响可用性；
                # 但下次进入向导可能读到旧进度，必须警告而非静默。
                logger.warning(
                    "[oobe] 安装完成但 state 文件删除失败，请手动清理 %s：%s", STATE_FILE, exc
                )

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
        # 分类 + 脱敏：安装期最常见也最要命的失败是「库连不上」。
        # 原实现直接把异常原文回给客户端，而 asyncpg 的异常文本可能带出
        # `postgresql+asyncpg://user:PASSWORD@host/db` —— OOBE 是匿名端点，
        # SSE 缓冲对任何能连 /oobe/install/stream 的人都可见，等于公开数据库口令。
        code, message, hint = classify_db_error(e)
        if code == DB_UNKNOWN:
            # 不是数据库问题：给一句脱敏后的通用说明，细节留在服务端日志里
            message = f"安装失败：{scrub_database_url(str(e))}"
            hint = "请查看后端日志定位具体步骤；修正后可重新提交安装（本接口幂等）。"
        # 失败发生在哪一步：从已播报的进度缓冲里倒着找最后一条 progress。
        # 不用额外维护游标变量，避免和分散在各阶段的播报点走偏。
        last_evt = next(
            (e for e in reversed(_INSTALL_STREAM_BUFFER)
             if e.get("type") == "progress" and e.get("step_id")),
            None,
        )
        failed_step = (last_evt or {}).get("step_id") or steps[0][0]
        err_evt = {
            "type": "error",
            "success": False,
            "step_id": failed_step,
            "error_code": code,
            "message": message,
            "hint": hint,
            # SSE 订阅端（GET /oobe/install/stream）对匿名可用，堆栈会外泄绝对路径与
            # 数据库连接信息；完整堆栈只进服务端日志（上面的 logger.exception），
            # 只有在显式开 DEBUG 时才随事件下发——与 main.py 通用 500 处理器同口径。
            "traceback": traceback.format_exc() if settings.debug else None,
        }
        _append_progress(err_evt)
        raise OOBEInstallFailedException(message=message, error_code=code, hint=hint) from e


@router.post(
    "/preflight",
    summary="安装前干跑校验",
    description=(
        "匿名可访问（OOBE 白名单），**只读、不写任何文件、不建库、不建账号**。"
        "把向导里已填的内容提交上来做一次体检：用户名/邮箱/密码强度/站点地址走表单校验，"
        "数据库（postgresql 时）走真实连接探测并给出结构化错误码。"
        "**所有字段可选**，只校验提交上来的那部分——因此可分别在管理员步骤和站点步骤调用，"
        "点安装前再带全量跑一次。返回的 `issues[].code` 是稳定标识，前端按 code 分支渲染，"
        "不要匹配 `message` 文案（文案会随 i18n 变）。"
    ),
    responses={
        200: {"model": OobePreflightResponse, "description": "体检结果（HTTP 恒为 200，问题放在 issues 里）"},
    },
)
async def oobe_preflight(req: OobePreflightRequest):
    """安装前干跑校验 —— 让用户在点「安装」之前就知道哪里会炸。

    对标 WordPress 的 `wp-admin/setup-config.php`：WP 也是先让你填库信息、点提交后
    **当场**连一次库，连不上就把错误直接摆在你眼前，而不是等 install.php 跑到一半
    再抛 "Error establishing a database connection"。
    """
    issues: list[dict] = []

    def _add(field: str, level: str, code: str, message: str, hint: str | None = None):
        issues.append({"field": field, "level": level, "code": code, "message": message, "hint": hint})

    if req.admin_username is not None:
        if not re.match(USERNAME_PATTERN, req.admin_username):
            _add("admin_username", "error", "USERNAME_INVALID",
                 "用户名需为 3-20 位字母、数字、下划线或短横线",
                 "去掉空格与中文，改用字母数字组合。")
    if req.admin_email is not None:
        if not re.match(EMAIL_PATTERN, req.admin_email):
            _add("admin_email", "error", "EMAIL_INVALID", "邮箱格式不正确", "例如 admin@example.com")
    if req.admin_password is not None:
        if len(req.admin_password) < PASSWORD_MIN_LENGTH:
            _add("admin_password", "error", "PASSWORD_TOO_SHORT",
                 f"密码至少 {PASSWORD_MIN_LENGTH} 位")
        else:
            # 与注册/改密同口径（受 security_password_policy 开关控制）
            from backend.core.password_policy import validate_password

            for msg in validate_password(req.admin_password):
                _add("admin_password", "error", "PASSWORD_WEAK", msg,
                     "大小写字母 + 数字混合，且不要用常见弱口令。")

    if req.site_url is not None:
        if not req.site_url.strip():
            _add("site_url", "error", "SITE_URL_EMPTY", "站点地址不能为空",
                 "它用于拼接 RSS / sitemap / 头像的绝对地址，例如 https://example.com")
        elif not re.match(r"^https?://[^\s/$.?#].[^\s]*$", req.site_url.strip()):
            _add("site_url", "error", "SITE_URL_INVALID", "站点地址需以 http:// 或 https:// 开头")
        elif req.site_url.strip().startswith("http://"):
            _add("site_url", "warn", "SITE_URL_INSECURE",
                 "站点地址使用明文 HTTP，管理员密码与登录态将以明文传输",
                 "生产环境请配置 HTTPS 后再安装。")

    if req.site_name is not None and not req.site_name.strip():
        _add("site_name", "error", "SITE_NAME_EMPTY", "站点名称不能为空")

    # ---- 数据库体检 ----
    db_result = {"checked": False, "ok": True, "code": "DB_SKIPPED", "message": "未做连接探测", "hint": None, "version": None}
    if req.database_type == "sqlite":
        db_result = {
            "checked": False,
            "ok": True,
            "code": "DB_SQLITE_NO_PROBE",
            "message": "SQLite 无需预先连接，安装时会自动创建数据库文件",
            "hint": None,
            "version": None,
        }
        if not (req.db_path or req.db_name):
            _add("database", "error", "DB_PATH_EMPTY", "SQLite 数据库文件名不能为空")
    elif req.check_database:
        if not req.db_user:
            _add("database", "error", "DB_USER_EMPTY", "PostgreSQL 需要填写数据库用户名",
                 "例如 postgres")
        if not req.db_name:
            _add("database", "error", "DB_NAME_EMPTY", "数据库名不能为空", "例如 rosetta")

        if req.db_user and req.db_name:
            res = await database_service.probe_database(
                host=req.db_host,
                port=req.db_port,
                user=req.db_user,
                password=req.db_password,
                database=req.db_name,
                timeout=5,
            )
            version = (res.details or {}).get("version") if res.details else None
            db_result = {
                "checked": True,
                "ok": res.success,
                "code": res.code,
                "message": res.message,
                "hint": res.hint,
                "version": str(version) if version else None,
            }
            if not res.success:
                _add("database", "error", res.code, res.message, res.hint)
            elif res.code == "DB_NOT_EXIST":
                # 库不存在但账号有 CREATEDB → 不阻断，给一条提示即可
                _add("database", "warn", res.code, res.message, res.hint)

    ok = not any(i["level"] == "error" for i in issues)
    return {"success": True, "ok": ok, "issues": issues, "database": db_result}


class DatabaseTestRequest(BaseModel):
    """POST /oobe/test-database 的请求体。

    为什么必须走 POST：**旧的 GET 版本把数据库密码放在 query string 里**
    （`?db_password=...`），而 query string 会被 Nginx / uvicorn / 浏览器历史 /
    各类 APM 原样记进访问日志 —— 等于把数据库口令明文写进日志文件。
    """

    db_type: str = "sqlite"
    db_host: str = "localhost"
    db_port: int = 5432
    db_name: str = "rosetta"
    db_user: str = ""
    db_password: str = ""
    db_path: str = "rosetta.db"


class OobeDatabaseTestPostResponse(BaseModel):
    """POST /oobe/test-database 的响应体（比 GET 版多 code / hint / exists）。"""

    success: bool = Field(..., description="连接是否成功（SQLite 分支恒为 true）")
    message: str = Field(..., description="结论文案（已脱敏，不含口令）")
    code: str = Field(..., description="结构化错误码（DB_* 系列）")
    hint: str | None = Field(default=None, description="可操作的下一步建议")
    database_url: str | None = Field(
        default=None, description="仅 SQLite 分支返回：由表单构建出的连接串（不含凭据）"
    )
    details: dict[str, Any] | None = Field(default=None, description="附加信息：version / exists 等")


@router.post(
    "/test-database",
    summary="测试数据库连接（推荐）",
    description=(
        "匿名可访问（OOBE 白名单）。**请优先使用本端点而不是同路径的 GET**："
        "GET 会把数据库密码带在 query string 里，从而落进访问日志。"
        "postgresql 分支先连维护库证明账号密码可用，再查目标库是否存在、账号有无建库权限；"
        "结果以结构化 `code`（DB_* 系列）返回，失败也回 HTTP 200。"
    ),
    responses={200: {"model": OobeDatabaseTestPostResponse, "description": "连接测试结果"}},
)
async def test_database_post(request: DatabaseTestRequest):
    """测试数据库连接（POST，密码走请求体）"""
    if request.db_type == "sqlite":
        database_url = generate_database_url(
            {"db_type": "sqlite", "db_name": request.db_name, "db_path": request.db_path}
        )
        return {
            "success": True,
            "message": t("oobe_sqlite_no_test"),
            "code": "DB_OK",
            "hint": None,
            "database_url": database_url,
            "details": None,
        }
    res = await database_service.probe_database(
        host=request.db_host,
        port=request.db_port,
        user=request.db_user,
        password=request.db_password,
        database=request.db_name,
        timeout=5,
    )
    return {
        "success": res.success,
        "message": res.message,
        "code": res.code,
        "hint": res.hint,
        "database_url": None,
        "details": res.details,
    }


@router.post(
    "/install",
    summary="OOBE 一键安装",
    description=(
        "唯一的安装入口（匿名可访问，但仅 OOBE 未完成时可用）。**危险且不可逆的副作用**："
        "写 .env 与配置文件、重建数据库引擎并建表、创建超级管理员、写入站点设置与示例数据/页面/导航，"
        "最后落 OOBE 完成锁。三层幂等防线（入口检查 + 进程内 asyncio.Lock + 拿锁后二次检查），"
        "已完成返回 409 + ``OOBE_ALREADY_COMPLETED``，密码过短回 422，其余异常回 500。"
        "实时进度走 GET /oobe/install/stream。"
    ),
    responses={
        200: {"model": OobeInstallResponse, "description": "安装完成，回前台与后台入口地址"},
        409: {"description": "OOBE 已完成（error_code: OOBE_ALREADY_COMPLETED）"},
    },
)
async def oobe_install(req: CombinedInstallRequest):
    """OOBE 一键安装端点

    幂等：若 OOBE 已完成则返回 409 + OOBE_ALREADY_COMPLETED。
    安装顺序严格按 spec 执行：env -> schema -> admin -> site_settings -> mock_data -> pages/navs -> 标记文件。
    R1-U2: 进程级 asyncio.Lock 防并发重入；拿到锁后 + 创建 admin 前都会执行二次 is_oobe_complete()。
    """
    # R1-U2: 3 层幂等防线 —— 第一层：入口无锁快速检查（409 立即返回）
    if is_oobe_complete():
        raise OOBEAlreadyCompletedException()

    # 与注册/改密走同一套密码策略（受 security_password_policy 开关控制）：
    # 一键安装此前只查 `len >= 8`，于是超管口令可以是 `12345678` ——
    # 而同一个系统的普通注册却会被策略拦下，口径是自相矛盾的。
    if len(req.admin_password) < PASSWORD_MIN_LENGTH:
        raise WeakPasswordException(f"管理员密码至少 {PASSWORD_MIN_LENGTH} 位")
    from backend.core.password_policy import validate_password

    pw_errors = validate_password(req.admin_password)
    if pw_errors:
        raise WeakPasswordException("；".join(pw_errors))

    # R1-U2: 第二层：进程级 asyncio.Lock（单 worker 串行化，避免两请求都过第一层后交错）
    global _INSTALL_LOCK_ACQUIRED
    acquired = False
    try:
        await _INSTALL_LOCK.acquire()
        acquired = True
        _INSTALL_LOCK_ACQUIRED = True
        # R1-U2: 第三层：拿到锁后立即二次检查（若第一个持锁请求刚完成，第二个直接 409）
        if is_oobe_complete():
            raise OOBEAlreadyCompletedException()
        # 清空上一轮的安装进度缓冲：SSE 连接时会回放缓冲，
        # 不清的话「上次失败的 error 帧」会先被重放一遍，UI 一进来就闪红。
        _INSTALL_STREAM_BUFFER.clear()
        try:
            done = await _run_combined_install(req)
        except OOBEAlreadyCompletedException:
            raise
        except WeakPasswordException:
            raise
        except OOBEInstallFailedException:
            # 已分类 + 已脱敏，原样抛出让全局 AppException 处理器带上 error_code/hint
            raise
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"安装失败: {e}\n{traceback.format_exc()}")
            raise HTTPException(status_code=500, detail=f"安装失败: {e}")
    finally:
        if acquired:
            _INSTALL_LOCK_ACQUIRED = False
            _INSTALL_LOCK.release()

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


@router.post(
    "/database-config",
    summary="保存数据库配置（已废弃）",
    description=(
        "**Deprecated**：旧分步式接口，请改用 POST /oobe/install。仅 OOBE 未完成时可用。"
        "把数据库/Redis 配置草稿写入向导 state 文件（不落库、不建连接）；"
        "响应回显时**剔除所有密码字段**。非 sqlite 且缺 db_user、或 db_name 为空时返回 400。"
    ),
    responses={
        200: {"model": OobeDatabaseConfigResponse, "description": "已保存的配置（无密码字段）"},
        400: {"description": "数据库用户名或库名缺失"},
        503: {"description": "OOBE 已完成（error_code: OOBE_REQUIRED）"},
    },
)
async def save_database_config(request: DatabaseConfigRequest):
    """保存数据库配置（旧分步式接口，兼容保留）

    .. deprecated::
        此接口将在未来版本移除，请使用 POST /api/oobe/install 一键安装代替。
    """
    await require_oobe_incomplete()
    logger.warning(
        "DEPRECATED: POST /api/oobe/database-config 被调用，请迁移到 POST /api/oobe/install"
    )
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


@router.get(
    "/test-database",
    summary="测试数据库连接（已废弃）",
    description=(
        "**Deprecated**：请改用 **POST /oobe/test-database**。本端点把数据库密码放在 "
        "query string 里（`?db_password=...`），而 query string 会被 Nginx / uvicorn / "
        "浏览器历史 / APM 原样写进访问日志——等于把口令明文落盘。保留仅为兼容。"
        "匿名可访问（OOBE 白名单，安装前不存在任何凭证可保护它）。sqlite 分支不建连接，"
        "只回一句提示与由表单参数构建出的连接串；postgresql 分支用 asyncpg 实连维护库做探测，"
        "连接失败也回 HTTP 200 + success=false（原因在 message/details，均已脱敏）。"
    ),
    responses={200: {"model": OobeDatabaseTestResponse, "description": "连接测试结果"}},
)
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


@router.post(
    "/site-config",
    summary="保存站点配置（已废弃）",
    description=(
        "**Deprecated**：旧分步式接口，请改用 POST /oobe/install。仅 OOBE 未完成时可用。"
        "把站点名称/描述/社交链接/页脚与评论、注册、RSS 开关写进向导 state 文件，不落库。"
        "site_name 或 site_email 为空时返回 400。"
    ),
    responses={
        200: {"model": OobeSimpleSuccessResponse, "description": "已写入向导状态"},
        400: {"description": "站点名称或联系邮箱为空"},
        503: {"description": "OOBE 已完成（error_code: OOBE_REQUIRED）"},
    },
)
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


@router.get(
    "/check-username",
    summary="检查用户名是否可用",
    description=(
        "匿名可访问（OOBE 白名单）。只校验长度与字符集（字母数字，允许下划线/连字符），"
        "不查库、不建账号，因此**不保证最终唯一性**。返回裸对象（无 success 信封）。"
    ),
    responses={200: {"model": OobeUsernameCheckResponse, "description": "可用性与不可用原因"}},
)
async def check_username(username: str):
    """检查用户名是否可用"""
    if len(username) < USERNAME_MIN_LENGTH:
        return {"available": False, "message": t("oobe_username_min")}
    if len(username) > USERNAME_MAX_LENGTH:
        return {"available": False, "message": t("oobe_username_max")}
    if not username.replace("_", "").replace("-", "").isalnum():
        return {"available": False, "message": t("oobe_username_invalid")}
    return {"available": True}


@router.post(
    "/admin-account",
    summary="保存管理员账户信息（已废弃）",
    description=(
        "**Deprecated**：旧分步式接口，请改用 POST /oobe/install。仅 OOBE 未完成时可用。"
        "把管理员资料草稿写进向导 state 文件，**此步骤不创建任何用户、不校验邮箱是否已注册**；"
        "用户名长度/字符集或密码长度不合规返回 400。"
    ),
    responses={
        200: {"model": OobeSimpleSuccessResponse, "description": "已写入向导状态"},
        400: {"description": "用户名不合规或密码过短"},
        503: {"description": "OOBE 已完成（error_code: OOBE_REQUIRED）"},
    },
)
async def save_admin_account(request: AdminAccountRequest):
    """保存管理员账户信息（旧分步式接口，兼容保留）

    .. deprecated::
        此接口将在未来版本移除，请使用 POST /api/oobe/install 一键安装代替。
    """
    await require_oobe_incomplete()
    logger.warning(
        "DEPRECATED: POST /api/oobe/admin-account 被调用，请迁移到 POST /api/oobe/install"
    )
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


@router.post(
    "/reset",
    summary="重置 OOBE 状态",
    description=(
        "**危险操作**：删除安装锁、.env、配置文件与向导 state，使站点回到未安装态（其余接口立即 503）。"
        "站点已安装时必须携带超级管理员凭证，否则 403；尚未安装时开放。"
        "任一文件删除失败回 500 并在 detail 列明残留项，不会返回半成功状态。"
    ),
    responses={
        200: {"model": OobeSimpleSuccessResponse, "description": "已全部清理，可重跑向导"},
        403: {"description": "站点已安装，需要超级管理员权限"},
        500: {"description": "部分文件无法删除（detail 列出残留项）"},
    },
)
async def reset_oobe(current_user: CurrentUserOptional = None):
    """重置 OOBE 状态（测试/开发使用），同时清空内存中的 SSE 进度缓冲

    安全约束：站点已完成安装（OOBE 完成态）后，重置会删除安装锁并允许
    重跑向导创建新超管，属于高危操作，必须携带超级管理员凭证；
    尚未安装时不存在任何管理员，向导本就开放，放行。
    """
    if is_oobe_complete() and (current_user is None or not current_user.is_superuser):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="站点已安装，重置 OOBE 需要超级管理员权限",
        )
    # reset_oobe 逐个删除并回报失败项；原先这里还重复 unlink 一遍且全被 `except: pass`
    # 吞掉，"重置失败"会回 200 —— 前端据此认为向导可重跑，安装锁却还在。
    leftover = config_service.reset_oobe()
    if leftover:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"OOBE 重置未完成，以下文件无法删除: {', '.join(leftover)}",
        )
    _INSTALL_STREAM_BUFFER.clear()
    return {"success": True}
