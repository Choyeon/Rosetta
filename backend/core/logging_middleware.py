"""
操作日志统一写入中间件 / 辅助函数

覆盖场景：
a) 登录失败（401）：users.py 捕获前调用 log_operation
b) 权限越权 403：在异常处理或 deps check 前调用
c) site_settings 修改 PATCH /settings/* -> action=settings
d) 文章发布/删除 POST /posts DELETE /admin/posts/:id -> action=publish/delete
e) 用户管理 CRUD（admin/users/*）-> action=create/update/delete target_type=users
f) 批量操作 batch -> action=batch
"""

from __future__ import annotations

import json
import re
from datetime import datetime
from typing import Any

from fastapi import Request
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models.log import OperationLog


def _mask_ip(ip: str | None) -> str | None:
    if not ip:
        return None
    if "." in ip:
        parts = ip.split(".")
        if len(parts) == 4:
            parts[-1] = "*"
            parts[-2] = parts[-2][:1] + "*" if len(parts[-2]) > 1 else "*"
            return ".".join(parts)
    if ":" in ip:
        segs = ip.split(":")
        if len(segs) >= 4:
            return ":".join(segs[:4]) + ":*:*"
    return ip


def _get_client_ip(request: Request) -> str | None:
    try:
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            return forwarded.split(",")[0].strip()
        real = request.headers.get("X-Real-IP")
        if real:
            return real
        return getattr(request.client, "host", None) if request.client else None
    except Exception:
        return None


def _get_path_action_target(request: Request) -> tuple[str, str]:
    """根据请求路径猜测 action 与 target_type。"""
    path = request.url.path
    method = request.method

    if re.search(r"/api/users/login|/api/auth/login", path) and method == "POST":
        return "login", "users"
    if re.search(r"/api/users/logout|/api/auth/logout", path):
        return "logout", "users"
    if re.search(r"/api/settings/|/api/config", path) and method in ("PATCH", "POST", "PUT"):
        return "settings", "settings"

    m = re.search(r"/api/admin/posts(?:/(\d+))?$", path)
    if m:
        if method == "POST":
            return "create", "posts"
        if method == "DELETE":
            return "delete", "posts"
        if method in ("PUT", "PATCH"):
            return "update", "posts"

    m2 = re.search(r"/api/blog/posts$", path)
    if m2 and method == "POST":
        return "publish", "posts"

    m3 = re.search(r"/api/admin/users(?:/(\d+))?$", path)
    if m3:
        if method == "POST":
            return "create", "users"
        if method == "DELETE":
            return "delete", "users"
        if method in ("PUT", "PATCH"):
            return "update", "users"

    if "batch" in path or "batch" in request.url.query:
        return "batch", path.split("/")[-2] if "/" in path else "unknown"

    return method.lower(), path.split("/")[-2] if "/" in path else "unknown"


def _truncate_for_log(data: Any, max_len: int = 2000) -> Any:
    try:
        s = json.dumps(data, ensure_ascii=False) if not isinstance(data, str) else data
    except Exception:
        s = str(data)
    if len(s) > max_len:
        s = s[: max_len - 50] + "...(truncated)"
    try:
        return json.loads(s) if not isinstance(data, str) else s
    except Exception:
        return s


async def log_operation(
    db: AsyncSession,
    request: Request | None = None,
    *,
    user_id: int | None = None,
    action: str | None = None,
    target_type: str | None = None,
    target_id: int | str | None = None,
    details: Any | None = None,
    status: str = "success",
    error_code: str | int | None = None,
    commit: bool = False,
) -> OperationLog | None:
    """统一写操作日志。

    Args:
        db: AsyncSession
        request: FastAPI Request（用来抽 ip / user_agent / path / method）
        user_id: 操作者 id
        action: create/update/delete/login/logout/permission/settings/publish/batch 等
        target_type: users/posts/comments/guestbook/settings/...
        target_id: str 或 int
        details: JSON 可序列化对象，before/after diff 或 payload
        status: success | failed
        error_code: 失败时的错误码
        commit: 是否立即 commit（默认 False，由外层事务提交）
    """
    try:
        if request is not None:
            _auto_action, _auto_target = _get_path_action_target(request)
            action = action or _auto_action
            target_type = target_type or _auto_target
        else:
            action = action or "unknown"
            target_type = target_type or "unknown"

        target_id_int: int | None = None
        if target_id is not None:
            if isinstance(target_id, int):
                target_id_int = target_id
            else:
                try:
                    target_id_int = int(str(target_id))
                except (TypeError, ValueError):
                    target_id_int = None

        details_json = None
        if details is not None:
            try:
                details_json = json.dumps(_truncate_for_log(details), ensure_ascii=False)
            except Exception:
                details_json = json.dumps({"raw": str(details)[:2000]}, ensure_ascii=False)

        ip = _mask_ip(_get_client_ip(request)) if request is not None else None
        ua = (
            request.headers.get("User-Agent")[:500]
            if request is not None and request.headers.get("User-Agent")
            else None
        )
        path = request.url.path if request is not None else None
        method = request.method if request is not None else None

        log = OperationLog(
            user_id=user_id,
            action=action or "action",
            resource_type=target_type or "unknown",
            resource_id=target_id_int,
            detail=details_json,
            ip_address=ip,
            user_agent=ua,
            request_path=path,
            request_method=method,
            status=status,
            error_code=str(error_code) if error_code is not None else None,
            created_at=datetime.utcnow(),
        )
        db.add(log)
        if commit:
            await db.commit()
        else:
            await db.flush()
        return log
    except Exception:
        return None
