"""
进度服务

提供安装进度跟踪和实时反馈功能：
- 步骤进度管理
- WebSocket 实时推送
- 日志记录
- 错误恢复支持
"""

import asyncio
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any


class StepStatus(Enum):
    """步骤状态"""

    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    SKIPPED = "skipped"


class LogLevel(Enum):
    """日志级别"""

    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    SUCCESS = "success"


@dataclass
class ProgressStep:
    """进度步骤"""

    id: str
    name: str
    description: str = ""
    status: StepStatus = StepStatus.PENDING
    progress: float = 0.0
    message: str = ""
    started_at: str | None = None
    completed_at: str | None = None
    duration: float | None = None
    error: str | None = None


@dataclass
class ProgressState:
    """进度状态"""

    current_step: int = 0
    total_steps: int = 0
    overall_progress: float = 0.0
    current_step_name: str = ""
    message: str = ""
    is_running: bool = False
    is_completed: bool = False
    is_failed: bool = False
    error: str | None = None
    started_at: str | None = None
    completed_at: str | None = None
    steps: list[ProgressStep] = field(default_factory=list)


@dataclass
class LogEntry:
    """日志条目"""

    level: LogLevel
    message: str
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    step: str = ""
    details: dict | None = None


ProgressCallback = Callable[[dict[str, Any]], None | object]


class ProgressService:
    """进度服务"""

    def __init__(self):
        self.state = ProgressState()
        self._callbacks: list[ProgressCallback] = []
        self._logs: list[LogEntry] = []
        self._log_buffer_size = 1000

    def add_callback(self, callback: ProgressCallback):
        """添加进度回调"""
        self._callbacks.append(callback)

    def remove_callback(self, callback: ProgressCallback):
        """移除进度回调"""
        if callback in self._callbacks:
            self._callbacks.remove(callback)

    async def _notify(self, data: dict[str, Any]):
        """通知所有回调"""
        for callback in self._callbacks:
            try:
                result = callback(data)
                if asyncio.iscoroutine(result):
                    await result
            except Exception:
                pass

    def setup_steps(self, steps: list[dict]):
        """设置步骤"""
        self.state.steps = [
            ProgressStep(
                id=step["id"],
                name=step["name"],
                description=step.get("description", ""),
            )
            for step in steps
        ]
        self.state.total_steps = len(steps)

    def start(self):
        """开始进度"""
        self.state.is_running = True
        self.state.is_completed = False
        self.state.is_failed = False
        self.state.started_at = datetime.now().isoformat()
        self.state.current_step = 1

        asyncio.create_task(
            self._notify(
                {
                    "type": "start",
                    "message": "开始安装...",
                    "current_step": self.state.current_step,
                    "total_steps": self.state.total_steps,
                }
            )
        )

    def set_step(self, step_index: int, step_name: str = ""):
        """设置当前步骤"""
        if 0 <= step_index < len(self.state.steps):
            self.state.current_step = step_index + 1
            self.state.current_step_name = step_name or self.state.steps[step_index].name
            self.state.steps[step_index].status = StepStatus.RUNNING
            self.state.steps[step_index].started_at = datetime.now().isoformat()

            asyncio.create_task(
                self._notify(
                    {
                        "type": "step",
                        "step": step_index + 1,
                        "total_steps": self.state.total_steps,
                        "step_name": self.state.current_step_name,
                        "message": f"正在执行: {self.state.current_step_name}",
                    }
                )
            )

    def update_progress(self, progress: float, message: str = ""):
        """更新进度"""
        self.state.overall_progress = progress

        current_idx = self.state.current_step - 1
        if 0 <= current_idx < len(self.state.steps):
            self.state.steps[current_idx].progress = progress

        if message:
            self.state.message = message
            self.state.steps[current_idx].message = message

        asyncio.create_task(
            self._notify(
                {
                    "type": "progress",
                    "progress": progress,
                    "message": message,
                    "current_step": self.state.current_step,
                    "total_steps": self.state.total_steps,
                }
            )
        )

    def complete_step(self, step_index: int, success: bool = True, message: str = ""):
        """完成步骤"""
        if 0 <= step_index < len(self.state.steps):
            step = self.state.steps[step_index]
            step.status = StepStatus.SUCCESS if success else StepStatus.FAILED
            step.completed_at = datetime.now().isoformat()

            if step.started_at:
                try:
                    start = datetime.fromisoformat(step.started_at)
                    end = datetime.fromisoformat(step.completed_at)
                    step.duration = (end - start).total_seconds()
                except Exception:
                    pass

            if message:
                step.message = message
            elif not step.message:
                step.message = "完成" if success else "失败"

            asyncio.create_task(
                self._notify(
                    {
                        "type": "step_complete",
                        "step": step_index + 1,
                        "success": success,
                        "message": step.message,
                        "duration": step.duration,
                    }
                )
            )

        overall = (step_index + 1) / self.state.total_steps * 100
        self.state.overall_progress = overall

    def complete(self, success: bool = True, message: str = ""):
        """完成进度"""
        self.state.is_running = False
        self.state.is_completed = success
        self.state.is_failed = not success
        self.state.completed_at = datetime.now().isoformat()

        if message:
            self.state.message = message

        asyncio.create_task(
            self._notify(
                {
                    "type": "complete",
                    "success": success,
                    "message": message or ("安装完成" if success else "安装失败"),
                    "overall_progress": self.state.overall_progress,
                }
            )
        )

    def fail(self, error: str, step: int = None):
        """失败"""
        self.state.is_running = False
        self.state.is_failed = True
        self.state.error = error

        if step and 0 <= step - 1 < len(self.state.steps):
            self.state.steps[step - 1].status = StepStatus.FAILED
            self.state.steps[step - 1].error = error

        self.log_error(error, step=step)

        asyncio.create_task(
            self._notify(
                {
                    "type": "error",
                    "error": error,
                    "step": step,
                    "message": error,
                }
            )
        )

    def reset(self):
        """重置进度"""
        self.state = ProgressState()
        self._logs.clear()

    def get_state(self) -> dict:
        """获取当前状态"""
        return {
            "current_step": self.state.current_step,
            "total_steps": self.state.total_steps,
            "overall_progress": self.state.overall_progress,
            "current_step_name": self.state.current_step_name,
            "message": self.state.message,
            "is_running": self.state.is_running,
            "is_completed": self.state.is_completed,
            "is_failed": self.state.is_failed,
            "error": self.state.error,
            "started_at": self.state.started_at,
            "completed_at": self.state.completed_at,
            "steps": [
                {
                    "id": s.id,
                    "name": s.name,
                    "description": s.description,
                    "status": s.status.value,
                    "progress": s.progress,
                    "message": s.message,
                    "duration": s.duration,
                    "error": s.error,
                }
                for s in self.state.steps
            ],
        }

    def log(self, level: LogLevel, message: str, step: str = "", details: dict = None):
        """记录日志"""
        entry = LogEntry(
            level=level,
            message=message,
            step=step,
            details=details,
        )

        self._logs.append(entry)

        if len(self._logs) > self._log_buffer_size:
            self._logs = self._logs[-self._log_buffer_size :]

        asyncio.create_task(
            self._notify(
                {
                    "type": "log",
                    "level": level.value,
                    "message": message,
                    "step": step,
                    "timestamp": entry.timestamp,
                }
            )
        )

    def log_info(self, message: str, step: str = ""):
        """记录信息日志"""
        self.log(LogLevel.INFO, message, step)

    def log_success(self, message: str, step: str = ""):
        """记录成功日志"""
        self.log(LogLevel.SUCCESS, message, step)

    def log_warning(self, message: str, step: str = ""):
        """记录警告日志"""
        self.log(LogLevel.WARNING, message, step)

    def log_error(self, message: str, step: str = ""):
        """记录错误日志"""
        self.log(LogLevel.ERROR, message, step)

    def get_logs(self, level: LogLevel = None, limit: int = 100) -> list[dict]:
        """获取日志"""
        logs = self._logs

        if level:
            logs = [log for log in logs if log.level == level]

        logs = logs[-limit:]

        return [
            {
                "level": log.level.value,
                "message": log.message,
                "timestamp": log.timestamp,
                "step": log.step,
                "details": log.details,
            }
            for log in logs
        ]

    def clear_logs(self):
        """清除日志"""
        self._logs.clear()
