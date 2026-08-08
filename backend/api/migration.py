"""
数据库迁移任务 API（Admin Only）

功能：
- POST /api/admin/migration/start     发起一次跨库迁移（后台 asyncio task）
- GET  /api/admin/migration/status    获取最新一次任务的进度事件流（SSE 或轮询 JSON）
- GET  /api/admin/migration/presets   返回一些常见连接预设（SQLite 默认、当前 env 的 PG）
- POST /api/admin/migration/cancel    取消当前运行中的任务（若支持）

认证：沿用 CurrentStaff（admin 权限）。
"""

from __future__ import annotations

import asyncio
import time
import uuid
from collections import deque
from contextlib import suppress
from dataclasses import dataclass, field
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from backend.core.auth import CurrentStaff

router = APIRouter(prefix="/migration", tags=["数据库迁移"])


# ======================================================================
# 后台任务管理器：单例，负责启动/取消/记录进度事件
# ======================================================================


@dataclass
class MigrationJob:
    job_id: str
    source: str
    target: str
    dry_run: bool
    skip_schema: bool
    created_by: str
    created_at: float = field(default_factory=time.time)
    started_at: float | None = None
    finished_at: float | None = None
    status: str = "pending"  # pending | running | done | error | cancelled
    latest_progress: dict[str, Any] | None = None
    events: deque[dict[str, Any]] = field(default_factory=lambda: deque(maxlen=2000))
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    _task: asyncio.Task | None = field(default=None, repr=False)
    _cancel_flag: asyncio.Event | None = field(default=None, repr=False)

    def to_public(self) -> dict[str, Any]:
        return {
            "job_id": self.job_id,
            "source": self.source,
            "target": self.target,
            "dry_run": self.dry_run,
            "skip_schema": self.skip_schema,
            "created_by": self.created_by,
            "created_at": self.created_at,
            "started_at": self.started_at,
            "finished_at": self.finished_at,
            "status": self.status,
            "latest_progress": self.latest_progress,
            "events_count": len(self.events),
            "events_tail": list(self.events)[-200:],
            "errors": list(self.errors),
            "warnings": list(self.warnings),
        }


class _MigrationManager:
    def __init__(self) -> None:
        self.history: list[MigrationJob] = []
        self._lock = asyncio.Lock()

    async def submit(
        self,
        source: str,
        target: str,
        dry_run: bool,
        skip_schema: bool,
        created_by: str,
    ) -> MigrationJob:
        async with self._lock:
            # 全局只允许一个 running job
            for j in self.history:
                if j.status == "running":
                    raise HTTPException(
                        status_code=409,
                        detail=f"已有迁移任务运行中: {j.job_id}",
                    )
            job = MigrationJob(
                job_id=uuid.uuid4().hex,
                source=source,
                target=target,
                dry_run=dry_run,
                skip_schema=skip_schema,
                created_by=created_by,
            )
            self.history.append(job)
            job._cancel_flag = asyncio.Event()
            job._task = asyncio.create_task(self._run(job))
            return job

    async def cancel(self, job_id: str) -> MigrationJob:
        async with self._lock:
            job = self._find(job_id)
            if job.status != "running":
                raise HTTPException(status_code=400, detail="任务未在运行")
            if job._cancel_flag:
                job._cancel_flag.set()
            if job._task and not job._task.done():
                job._task.cancel()
                with suppress(Exception):
                    await job._task
            job.status = "cancelled"
            job.finished_at = time.time()
            return job

    def latest(self) -> MigrationJob | None:
        return self.history[-1] if self.history else None

    def _find(self, job_id: str) -> MigrationJob:
        for j in self.history:
            if j.job_id == job_id:
                return j
        raise HTTPException(status_code=404, detail="任务不存在")

    async def _run(self, job: MigrationJob) -> None:
        from backend.scripts.migrate_database import run_migration

        job.started_at = time.time()
        job.status = "running"
        try:
            async for event in run_migration(
                job.source, job.target, dry_run=job.dry_run, skip_schema=job.skip_schema
            ):
                job.latest_progress = event
                job.events.append(event)
                if event.get("warnings"):
                    job.warnings.extend(event["warnings"][-20:])
                if event.get("errors"):
                    job.errors.extend(event["errors"][-20:])
                if event.get("stage") == "done":
                    job.status = "done"
                if event.get("stage") == "error":
                    job.status = "error"
                if job._cancel_flag and job._cancel_flag.is_set():
                    break
        except asyncio.CancelledError:
            job.status = "cancelled"
        except Exception as exc:  # noqa: BLE001
            job.status = "error"
            job.errors.append(f"[task] {exc}")
        finally:
            job.finished_at = time.time()


_manager = _MigrationManager()


# ======================================================================
# Request / Response models
# ======================================================================


class MigrationStartIn(BaseModel):
    source: str = Field(
        ...,
        description="源库 SQLAlchemy URL，如 sqlite+aiosqlite:///./rosetta.db",
        min_length=6,
    )
    target: str = Field(
        ...,
        description="目标库 SQLAlchemy URL，如 postgresql+asyncpg://user:pass@localhost:5432/rosetta",
        min_length=6,
    )
    dry_run: bool = False
    skip_schema: bool = False


# ======================================================================
# Routes
# ======================================================================


@router.post("/start", summary="发起跨库迁移任务", description="管理员专属。后台异步运行，通过 /status 查看进度。全局同时只允许一个运行中的任务。")
async def start_migration(
    payload: MigrationStartIn,
    current_user: CurrentStaff,
):
    job = await _manager.submit(
        source=payload.source,
        target=payload.target,
        dry_run=payload.dry_run,
        skip_schema=payload.skip_schema,
        created_by=getattr(current_user, "username", "staff"),
    )
    return {"success": True, "job": job.to_public()}


@router.get("/status", summary="查询最新迁移任务状态", description="返回最新一次任务（包括 running/done/error）的完整进度。")
async def status_migration(current_user: CurrentStaff):
    job = _manager.latest()
    return {"success": True, "job": job.to_public() if job else None}


@router.post("/cancel", summary="取消当前运行中的迁移任务")
async def cancel_migration(current_user: CurrentStaff):
    latest = _manager.latest()
    if not latest:
        raise HTTPException(status_code=404, detail="当前没有迁移任务")
    job = await _manager.cancel(latest.job_id)
    return {"success": True, "job": job.to_public()}


@router.get("/presets", summary="获取常用连接预设", description="返回当前实例已配置的数据库 URL、SQLite 默认路径等，方便前端快速填。")
async def presets(current_user: CurrentStaff):
    from backend.core.config import settings

    result: dict[str, str] = {
        "sqlite_default": "sqlite+aiosqlite:///./rosetta.db",
        "current_database": settings.database_url,
    }
    if settings.redis_enabled:
        result["current_redis"] = settings.redis_url
    return {"success": True, "presets": result}
