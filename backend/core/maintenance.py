"""
维护模式中间件

当站点处于维护模式时，阻止普通用户访问，只允许管理员访问。
"""

from fastapi import Request
from fastapi.responses import JSONResponse
from sqlalchemy import select
from starlette.middleware.base import BaseHTTPMiddleware

from backend.core.database import async_session_maker
from backend.core.deps import is_oobe_complete
from backend.models.core import SiteConfig


class MaintenanceMiddleware(BaseHTTPMiddleware):
    """维护模式中间件"""

    # 不受维护模式影响的路径
    EXEMPT_PATHS = [
        "/api/users/login",
        "/api/users/logout",
        "/api/users/refresh",
        "/api/config",
        "/api/admin/",
        "/docs",
        "/redoc",
        "/openapi.json",
        "/health",
        "/media/",
    ]

    # 静态资源和前端路由
    EXEMPT_PREFIXES = [
        "/_nuxt",
        "/media",
        "/favicon",
        "/robots.txt",
        "/sitemap",
    ]

    async def dispatch(self, request: Request, call_next):
        # 检查是否是豁免路径
        path = request.url.path

        # OOBE 未完成时直接放行，数据库表尚未创建
        if not is_oobe_complete():
            return await call_next(request)

        # 检查前缀豁免
        for prefix in self.EXEMPT_PREFIXES:
            if path.startswith(prefix):
                return await call_next(request)

        # 检查完整路径豁免
        for exempt_path in self.EXEMPT_PATHS:
            if path.startswith(exempt_path):
                return await call_next(request)

        # 检查维护模式状态
        async with async_session_maker() as db:
            result = await db.execute(
                select(SiteConfig).where(SiteConfig.key == "MAINTENANCE_MODE")
            )
            config = result.scalar_one_or_none()

            if not config or config.value.lower() != "true":
                return await call_next(request)

            # 获取维护消息
            message_result = await db.execute(
                select(SiteConfig).where(SiteConfig.key == "MAINTENANCE_MESSAGE")
            )
            message_config = message_result.scalar_one_or_none()
            maintenance_message = message_config.value if message_config else None

        # 检查用户是否是管理员
        # 从请求头获取 token
        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            try:
                token = auth_header[7:]
                from backend.core.auth import decode_token

                payload = decode_token(token)
                if payload:
                    user_id = payload.get("sub")
                    if user_id:
                        # 检查用户是否是管理员
                        async with async_session_maker() as db:
                            from backend.models.user import User

                            user_result = await db.execute(
                                select(User).where(User.id == int(user_id))
                            )
                            user = user_result.scalar_one_or_none()
                            if user and (user.is_staff or user.is_superuser):
                                return await call_next(request)
            except Exception:
                pass

        # 返回维护模式响应
        if path.startswith("/api/"):
            return JSONResponse(
                status_code=503,
                content={
                    "success": False,
                    "message": maintenance_message or "站点维护中，请稍后再试",
                    "error_code": 503,
                    "maintenance_mode": True,
                },
            )

        # 前端路由返回 HTML 重定向
        from fastapi.responses import HTMLResponse

        return HTMLResponse(
            content=f"""
            <!DOCTYPE html>
            <html>
            <head>
                <meta charset="utf-8">
                <title>维护中</title>
                <script>
                    localStorage.setItem('maintenance_mode', 'true');
                    localStorage.setItem('maintenance_message', '{maintenance_message or ""}');
                    window.location.href = '/maintenance';
                </script>
            </head>
            <body>
                <p>站点维护中，请稍后再试...</p>
            </body>
            </html>
            """,
            status_code=503,
        )
