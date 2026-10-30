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
# 首页横幅支持 YouTube 轮播（media_type=youtube）：iframe 走 privacy-enhanced 的
# youtube-nocookie.com。原先没有 frame-src，`default-src 'self'` 会把所有站外 frame
# 拦掉——这正是"后台存得进、首页一片空白"的另一半原因。只放 nocookie 这一个域，
# 不连 www.youtube.com：嵌入地址由前端从视频 ID 固定拼出，不需要通用 youtube 域。
# 新增任何站外嵌入源时，这里与 `deploy/nginx-site.conf` 的 HTML CSP 必须同改。
CSP_FRAME_SRCS = "'self' https://www.youtube-nocookie.com"

# FastAPI 内置文档（Swagger UI / ReDoc）使用内联脚本，无法注入 nonce，
# 这些端点仅 debug 模式开放，对其放宽 script-src 允许 unsafe-inline。
DOCS_PATHS = ("/docs", "/redoc", "/openapi.json")


def _build_csp(nonce: str, allow_inline_scripts: bool = False) -> str:
    if allow_inline_scripts:
        script_src = (
            "'self' 'unsafe-inline' 'unsafe-eval' "
            "https://cdn.jsdelivr.net https://www.googletagmanager.com https://cdnjs.cloudflare.com"
        )
    else:
        script_src = (
            f"'self' 'nonce-{nonce}' "
            "https://cdn.jsdelivr.net https://www.googletagmanager.com https://cdnjs.cloudflare.com"
        )
    parts = [
        "default-src 'self'",
        f"script-src {script_src}",
        f"style-src {CSP_STYLE_SRCS}",
        f"img-src {CSP_IMG_SRCS}",
        f"font-src {CSP_FONT_SRCS}",
        f"media-src {CSP_MEDIA_SRCS}",
        f"connect-src {CSP_CONNECT_SRCS}",
        f"frame-src {CSP_FRAME_SRCS}",
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
# 不含 interest-cohort：GEL 已于 2024-08 随 Privacy Sandbox 下线并从 Chromium 移除，
# 现代浏览器不再认识这个令牌——它会在每个 /api 响应上展开成 4 条
# "Unrecognized feature" 控制台报错（attribution-reporting / private-aggregation /
# join-ad-interest-group / run-ad-auction）。留着挡不住任何真实能力，只污染控制台。
PERMISSIONS_POLICY = "camera=(), microphone=(), geolocation=(), payment=()"
XFRAME_SAMEORIGIN = "SAMEORIGIN"


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """写入 6 个标准安全响应头 + 每请求生成 CSP nonce"""

    async def dispatch(self, request: Request, call_next) -> Response:
        nonce = secrets.token_hex(16)
        request.state.csp_nonce = nonce

        response = await call_next(request)

        # FastAPI 文档页（Swagger UI / ReDoc）依赖内联脚本，无法使用 nonce，
        # 对这些路径放宽 script-src；其余路径保持严格 nonce 策略。
        path = request.url.path
        is_docs = any(path == p or path.startswith(p + "/") for p in DOCS_PATHS)
        csp_value = _build_csp(nonce, allow_inline_scripts=is_docs)
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
