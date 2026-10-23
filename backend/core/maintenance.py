"""
维护模式中间件

当站点处于维护模式时，阻止普通用户访问，只允许管理员访问。
"""

import json
import logging

from fastapi import Request
from fastapi.responses import JSONResponse
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from starlette.middleware.base import BaseHTTPMiddleware

from backend.core.database import async_session_maker
from backend.core.deps import is_oobe_complete
from backend.core.site_config import get_site_config_value
from backend.models.user import User

logger = logging.getLogger(__name__)


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
        # 走带缓存的配置助手而不是每次请求直查 SiteConfig：该键 1 小时 TTL，
        # 后台切换维护模式时写侧已调 invalidate_site_config_caches() 删前缀，
        # 因此"改完立刻生效"不变，而稳态下每个非豁免请求省掉 1~2 次数据库往返。
        # 曾经这里每个请求都 async_session_maker() + 两条 SELECT，
        # 匿名流量全打在 maintenance 探测查询上。
        maintenance_flag = await get_site_config_value("MAINTENANCE_MODE")
        if not maintenance_flag or maintenance_flag.lower() != "true":
            return await call_next(request)

        # 获取维护消息
        maintenance_message = await get_site_config_value("MAINTENANCE_MESSAGE")

        # 检查用户是否是管理员
        # 从请求头获取 token
        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            # 核验失败就按普通访客处理（降级更严）。异常类型必须收窄：
            # "票不合法 / 查不到人"可降级，导入失败或模型字段改名是真实缺陷，得抛。
            try:
                token = auth_header[7:]
                from backend.core.auth import decode_token

                payload = decode_token(token)
                if payload:
                    user_id = payload.get("sub")
                    if user_id:
                        # 检查用户是否是管理员（仅维护模式开启时才走到，
                        # 每个带票请求查一次用户表；管理员巡检期可接受）
                        async with async_session_maker() as db:
                            user_result = await db.execute(
                                select(User).where(User.id == int(user_id))
                            )
                            user = user_result.scalar_one_or_none()
                            if user and (user.is_staff or user.is_superuser):
                                return await call_next(request)
            except (SQLAlchemyError, ValueError, TypeError) as exc:
                logger.warning("[maintenance] 管理员身份核验失败，按普通访客处理：%s", exc)

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

        # json.dumps 产出合法 JS 字符串字面量；再转义 "</" 防止消息内 </script> 提前闭合标签
        safe_message = json.dumps(maintenance_message or "", ensure_ascii=False).replace(
            "</", "<\\/"
        )

        return HTMLResponse(
            content=f"""
            <!DOCTYPE html>
            <html>
            <head>
                <meta charset="utf-8">
                <title>维护中</title>
                <script>
                    localStorage.setItem('maintenance_mode', 'true');
                    localStorage.setItem('maintenance_message', {safe_message});
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
