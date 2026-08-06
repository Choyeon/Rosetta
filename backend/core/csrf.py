"""
CSRF 保护依赖（无状态 Origin 白名单 + Cookie/Header 双提交兜底）

策略：
- 对有 Authorization: Bearer 登录态 + POST/PUT/PATCH/DELETE 的写方法校验：
  a) 若有 Origin 头，必须 ∈ csrf_origins（默认复用 CORS_ORIGINS）
  b) 若 <meta name="csrf-token"> / Cookie csrf_token 存在：X-CSRF-Token header 与 Cookie 中值一致（双提交）
- 失败：403 + error_code=CSRF_CHECK_FAILED（不写 log 防刷屏）
- 绕过：GET/HEAD/OPTIONS/TRACE、/health、/api/oobe/*、/docs、/openapi.json、/redoc
"""

from __future__ import annotations

from collections.abc import Iterable
from urllib.parse import urlparse

from fastapi import Depends, HTTPException, Request, status

from backend.core.config import Settings, get_settings

CSRF_CHECK_FAILED = "CSRF_CHECK_FAILED"

_BYPASS_METHODS = {"GET", "HEAD", "OPTIONS", "TRACE"}
_BYPASS_PREFIXES = ("/api/oobe/", "/api/captcha/")
_BYPASS_EXACT = ("/health", "/docs", "/openapi.json", "/redoc", "/favicon.ico")


def _normalize_origin(url: str | None) -> str | None:
    if not url:
        return None
    try:
        parsed = urlparse(url.strip())
        if not parsed.scheme or not parsed.netloc:
            return None
        return f"{parsed.scheme.lower()}://{parsed.netloc.lower()}"
    except Exception:
        return None


def _origin_in_whitelist(origin: str, whitelist: Iterable[str]) -> bool:
    norm = _normalize_origin(origin)
    if not norm:
        return False
    for allowed in whitelist:
        a = _normalize_origin(allowed)
        if a and a == norm:
            return True
        if allowed == "*":
            return True
    return False


async def require_csrf(
    request: Request,
    settings: Settings = Depends(get_settings),
) -> None:
    """FastAPI Depends：执行 CSRF 校验。不通过则抛 HTTPException(403, CSRF_CHECK_FAILED)。"""
    method = request.method.upper()
    if method in _BYPASS_METHODS:
        return

    path = request.url.path
    if path in _BYPASS_EXACT or path.startswith(_BYPASS_PREFIXES):
        return

    auth_header = request.headers.get("Authorization") or ""
    has_bearer = auth_header.lower().startswith("bearer ")
    if not has_bearer:
        return

    csrf_origins = list(getattr(settings, "csrf_origins", None) or settings.cors_origins)

    origin = request.headers.get("Origin") or request.headers.get("X-Forwarded-For")
    if origin:
        if not _origin_in_whitelist(origin, csrf_origins):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "success": False,
                    "message": "CSRF check failed: origin not allowed",
                    "error_code": CSRF_CHECK_FAILED,
                },
            )

    csrf_cookie = request.cookies.get("csrf_token")
    csrf_header = request.headers.get("X-CSRF-Token")
    if csrf_cookie and csrf_header:
        import hmac

        if not hmac.compare_digest(csrf_cookie, csrf_header):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "success": False,
                    "message": "CSRF check failed: token mismatch",
                    "error_code": CSRF_CHECK_FAILED,
                },
            )
