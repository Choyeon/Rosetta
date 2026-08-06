"""
全局安全响应头中间件

对所有响应写入 6 个安全头：
1. Content-Security-Policy (含 per-request nonce)
2. HTTP Strict-Transport-Security (HTTPS 或 force_hsts 时)
3. X-Content-Type-Options: nosniff
4. Referrer-Policy: strict-origin-when-cross-origin
5. Permissions-Policy
6. X-Frame-Options: SAMEORIGIN
"""

import secrets

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from backend.core.config import settings

CSP_IMG_SRCS = "'self' data: https: blob:"
CSP_FONT_SRCS = "'self' data: https://fonts.gstatic.com https://cdn.jsdelivr.net"
CSP_MEDIA_SRCS = "'self' blob: data:"
CSP_CONNECT_SRCS = "'self' https: wss: blob:"
CSP_STYLE_SRCS = "'self' 'unsafe-inline' https://cdn.jsdelivr.net https://fonts.googleapis.com"
CSP_SCRIPT_BASE = (
    "'self' https://cdn.jsdelivr.net https://www.googletagmanager.com https://cdnjs.cloudflare.com"
)


def _build_csp(nonce: str) -> str:
    script_src = f"'self' 'nonce-{nonce}' https://cdn.jsdelivr.net https://www.googletagmanager.com https://cdnjs.cloudflare.com"
    parts = [
        "default-src 'self'",
        f"script-src {script_src}",
        f"style-src {CSP_STYLE_SRCS}",
        f"img-src {CSP_IMG_SRCS}",
        f"font-src {CSP_FONT_SRCS}",
        f"media-src {CSP_MEDIA_SRCS}",
        f"connect-src {CSP_CONNECT_SRCS}",
        "frame-ancestors 'self'",
        "form-action 'self'",
        "base-uri 'self'",
        "object-src 'none'",
        "worker-src 'self' blob:",
    ]
    return "; ".join(parts)


HSTS_HEADER = "max-age=63072000; includeSubDomains; preload"
NOSNIFF = "nosniff"
REFERRER_POLICY = "strict-origin-when-cross-origin"
PERMISSIONS_POLICY = "camera=(), microphone=(), geolocation=(), payment=(), interest-cohort=()"
XFRAME_SAMEORIGIN = "SAMEORIGIN"


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """写入 6 个标准安全响应头 + 每请求生成 CSP nonce"""

    async def dispatch(self, request: Request, call_next) -> Response:
        nonce = secrets.token_hex(16)
        request.state.csp_nonce = nonce

        response = await call_next(request)

        csp_value = _build_csp(nonce)
        response.headers["Content-Security-Policy"] = csp_value
        response.headers["X-Content-Type-Options"] = NOSNIFF
        response.headers["Referrer-Policy"] = REFERRER_POLICY
        response.headers["Permissions-Policy"] = PERMISSIONS_POLICY
        response.headers["X-Frame-Options"] = XFRAME_SAMEORIGIN

        scheme = request.url.scheme
        force_hsts = getattr(settings, "force_hsts", False)
        if scheme == "https" or force_hsts:
            response.headers["Strict-Transport-Security"] = HSTS_HEADER

        return response
