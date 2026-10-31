"""
CSRF 保护依赖（无状态 Origin 白名单 + Cookie/Header 双提交兜底）

策略：
- 对有 Authorization: Bearer 登录态 + POST/PUT/PATCH/DELETE 的写方法校验：
  a) 若有 Origin 头，必须 ∈ csrf_origins（默认复用 CORS_ORIGINS）
  b) 若 <meta name="csrf-token"> / Cookie csrf_token 存在：X-CSRF-Token header 与 Cookie 中值一致（双提交）
- 失败：403 + error_code=CSRF_CHECK_FAILED（不写 log 防刷屏）
- 绕过：GET/HEAD/OPTIONS/TRACE、/health、/api/oobe/*、/docs、/openapi.json、/redoc

三条容易被误读的口径（2026-10-29 复核，回归 `tests/test_csrf_wired_set.py`）：

1. **本站不发任何 cookie**（全仓 `set_cookie` 零命中，登录态只在 `Authorization` 头里）。
   没有环境凭证就没有经典 CSRF，所以 b) 那条双提交分支目前**永不触发**——它是给
   "将来改成 cookie 会话"预留的钩子，不是"现在靠 token 挡跨站"的证据。
   反过来讲：一旦有人真的加了 cookie 鉴权，这条依赖必须重审（守卫会因 `set_cookie`
   出现而红，逼着改动作出决定，而不是让 200 多条写接口悄悄裸奔）。
2. **它是 per-route 依赖，不是全局中间件**，且刻意只挂在评论的三条写口
   （`api/comments.py` 的创建与删除自己的评论、`api/comment_report.py` 的举报）。
   因此"某个 admin 写口带站外 Origin 仍回 200"
   是**设计如此**（Bearer 头跨站带不上，攻击者拿不到），不要按"漏挂"去补线——
   补线会把合法的同源请求一起挡在 CORS 白名单外，2026 年那次评论 403 就是这么来的。
   哪个口该挂由这条守卫集中清点，改动必须是有意的。
3. 匿名写请求（无 Bearer）**直接放行**：跨站表单本来就能提交无凭证请求，
   这一层挡不住，靠频控与敏感词过滤兜；把这里改成 403 只会把游客评论全打死。
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
    except ValueError:
        # 解析不了的 Origin 归一化为 None → 白名单判定不通过（fail closed）。
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

    origin = request.headers.get("Origin")
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
