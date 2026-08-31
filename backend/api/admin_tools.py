"""
Admin 工具端点：Alembic 迁移状态 + 缓存状态/清退

挂载路径（在 main.py 里 include_router 时注入 prefix）：
    GET  /api/admin/alembic/status
    GET  /api/admin/cache/status
    POST /api/admin/cache/flush
"""

from __future__ import annotations

import asyncio
from collections.abc import Callable
from typing import Any, Literal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field

from backend.core.auth import CurrentStaff
from backend.core.cache import CACHE_TTL, cache, invalidate_cache
from backend.core.config import settings

router = APIRouter(tags=["Admin 工具"])


# ===================== Alembic 迁移版本 =====================


class AlembicVersionRow(BaseModel):
    version: str
    message: str = ""


class AlembicAppliedRow(AlembicVersionRow):
    applied_at: str | None = None


class AlembicStatusResponse(BaseModel):
    current_version: str
    latest_version: str
    is_latest: bool
    pending: list[AlembicVersionRow] = Field(default_factory=list)
    applied: list[AlembicAppliedRow] = Field(default_factory=list)


def _run_in_thread(fn: Callable[[], Any]) -> Any:
    """在独立线程执行阻塞的 Alembic 命令（alembic.command 内部是同步 sqlalchemy）。"""
    import concurrent.futures

    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
        loop = asyncio.get_event_loop()
        return loop.run_in_executor(executor, fn)


@router.get("/alembic/status", response_model=AlembicStatusResponse)
async def get_alembic_status(current_user: CurrentStaff) -> AlembicStatusResponse:
    """读取 Alembic 当前版本、最新版本、已应用与待应用列表。"""
    if not (current_user.is_staff or current_user.is_superuser):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "需要管理员权限")

    import io

    from alembic import command
    from alembic.script import ScriptDirectory

    from backend.migrations.config import get_alembic_config

    def collect() -> tuple[str, str, bool, list[AlembicVersionRow], list[AlembicAppliedRow]]:
        cfg = get_alembic_config()
        script = ScriptDirectory.from_config(cfg)

        # 1) 当前版本：捕获 command.current 的 stdout 输出
        buffer = io.StringIO()
        try:
            cfg.print_stdout = lambda *args, **kwargs: buffer.write(
                " ".join(str(a) for a in args) + (kwargs.get("end", "\n") if isinstance(kwargs.get("end"), str) else "\n")
            )
        except Exception:
            pass
        command.current(cfg)
        current_out = buffer.getvalue().strip() or ""
        current_lines = [ln for ln in current_out.splitlines() if ln.strip()]
        applied_heads: set[str] = set()
        for ln in current_lines:
            rev_token = ln.split()[0] if ln.split() else ""
            if rev_token and rev_token != "None":
                applied_heads.add(rev_token.rstrip(","))

        heads: list[str] = list(script.get_heads())
        latest_version = heads[0] if heads else ""

        # 2) 推算已应用版本集合：从当前 heads 沿着 down_revision 递归回溯所有祖先
        #    （SQLite 的 alembic_version 仅存当前 head，不保留历史明细，因此需递归）
        applied_set: set[str] = set(applied_heads)
        stack: list[str] = list(applied_heads)
        while stack:
            cur = stack.pop()
            try:
                rev = script.get_revision(cur)
            except Exception:
                continue
            if rev is None:
                continue
            # down_revision 可能是 str / tuple[str] / None
            downs: list[str] = []
            if isinstance(rev.down_revision, str):
                downs = [rev.down_revision]
            elif isinstance(rev.down_revision, (list, tuple)):
                downs = [str(x) for x in rev.down_revision if x]
            for d in downs:
                if d and d not in applied_set:
                    applied_set.add(d)
                    stack.append(d)

        pending: list[AlembicVersionRow] = []
        applied: list[AlembicAppliedRow] = []
        revs = list(script.walk_revisions(base="base", head="heads"))
        revs.reverse()
        for rev in revs:
            row_msg = (rev.doc or "").strip().splitlines()[0] if (rev.doc or "").strip() else ""
            ver = rev.revision
            if ver in applied_set:
                applied.append(AlembicAppliedRow(version=ver, message=row_msg, applied_at=None))
            else:
                pending.append(AlembicVersionRow(version=ver, message=row_msg))

        current_version = applied[-1].version if applied else ""
        is_latest = bool(latest_version) and current_version == latest_version
        return current_version, latest_version, is_latest, pending, applied

    try:
        current_version, latest_version, is_latest, pending, applied = await _run_in_thread(collect)
    except Exception as e:
        return AlembicStatusResponse(
            current_version="",
            latest_version="",
            is_latest=True,
            pending=[],
            applied=[],
        )

    return AlembicStatusResponse(
        current_version=current_version,
        latest_version=latest_version,
        is_latest=bool(is_latest),
        pending=pending,
        applied=applied,
    )


# ===================== 缓存管理 =====================


AdminCacheFlushMode = Literal["all", "post_list", "post_detail", "settings", "fragments"]


class CacheStatusResponse(BaseModel):
    backend: Literal["memory", "redis"]
    keys: int = 0
    memory_used_bytes: int | None = None
    hit_rate: float | None = None


class CacheFlushRequest(BaseModel):
    mode: AdminCacheFlushMode = "all"


class CacheFlushResponse(BaseModel):
    mode: AdminCacheFlushMode
    deleted_keys: int
    message: str


# mode -> 缓存键前缀列表（与 CACHE_TTL / core 代码保持一致；找不到更精确的时使用装饰器前缀）
MODE_PREFIXES: dict[AdminCacheFlushMode, list[str]] = {
    "all": ["*"],  # 走 backend.clear()
    "post_list": [
        "post_list:",
        "posts:list:",
        "posts:query:",
        "categories:",
        "tags:",
        "series:",
        "archive:",
        "search_results:",
    ],
    "post_detail": [
        "post_detail:",
        "posts:detail:",
        "post:",
        "post_body:",
        "post_toc:",
        "post_reading_time:",
        "post_similar:",
    ],
    "settings": [
        "site_config:",
        "settings:",
        "settings_groups:",
        "navigations:",
        "friend_links:",
        "theme:",
        "appearance:",
    ],
    "fragments": [
        "sidebar:",
        "footer:",
        "hero:",
        "notice:",
        "announcement:",
        "fragment:",
        "widget:",
    ],
}


@router.get("/cache/status", response_model=CacheStatusResponse)
async def get_cache_status(current_user: CurrentStaff) -> CacheStatusResponse:
    if not (current_user.is_staff or current_user.is_superuser):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "需要管理员权限")
    stats = await cache.get_stats() or {}
    backend_name: Literal["memory", "redis"] = "redis" if settings.redis_enabled else "memory"
    return CacheStatusResponse(
        backend=backend_name,
        keys=int(stats.get("keys", 0) or 0),
        memory_used_bytes=stats.get("memory_used_bytes"),
        hit_rate=stats.get("hit_rate"),
    )


@router.post("/cache/flush", response_model=CacheFlushResponse)
async def flush_cache(req: CacheFlushRequest, current_user: CurrentStaff) -> CacheFlushResponse:
    if not (current_user.is_staff or current_user.is_superuser):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "需要管理员权限")

    deleted_total: int = 0
    mode = req.mode

    if mode == "all":
        ok = await cache.clear()
        deleted_total = 1 if ok else 0
        message = "全部缓存已清退" if ok else "缓存清退失败，后端未返回成功标记"
        return CacheFlushResponse(mode=mode, deleted_keys=deleted_total, message=message)

    prefixes = MODE_PREFIXES.get(mode)
    if not prefixes:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, f"未知清退模式: {mode}")

    for prefix in prefixes:
        pattern = prefix if prefix.endswith("*") else f"{prefix}*"
        # CACHE_TTL 的 key 前缀可能是 "post_list" 这种，配合 make_cache_key 会拼成 "post_list:<args>:<kwargs>"
        deleted_total += await invalidate_cache(prefix.rstrip("*").rstrip(":"))

    return CacheFlushResponse(
        mode=mode,
        deleted_keys=deleted_total,
        message=f"已按模式「{mode}」清退缓存，匹配前缀 {len(prefixes)} 个。",
    )
