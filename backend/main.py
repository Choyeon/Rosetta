"""
Rosetta FastAPI 后端应用入口

提供完整的博客 API 服务，包括：
- 用户认证和授权
- 文章、分类、标签管理
- 评论系统
- 多语言支持

Example:
    启动开发服务器:
    $ uvicorn backend.main:app --reload

    启动生产服务器:
    $ uvicorn backend.main:app --host 0.0.0.0 --port 8000
"""

import logging
import time
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException as StarletteHTTPException

from backend.api import (
    activity,
    admin,
    admin_logs,
    advanced,
    announcement,
    avatar_proxy,
    bing,
    bing_image,
    blog,
    captcha,
    comment_reactions,
    comments,
    core,
    docs,
    favorite,
    guestbook,
    hero,
    import_export,
    media,
    messages,
    migration,
    monitoring,
    notification,
    oobe,
    performance,
    post_crypto,
    post_encryption,
    post_series,
    ranking,
    scheduled_posts,
    seo,
    settings_groups,
    shortcodes,
    stats,
    themes,
    themes_ext,
    plugins,
    title,
    toc,
    translate,
    admin_tools,
    users,
    voting,
    webhook,
)
from backend.core.config import settings
from backend.core.database import check_db_connection, close_db, get_db_info, init_db
from backend.core.paths import BASE_DIR
from backend.core.exceptions import AppException
from backend.core.i18n import I18nContext, parse_accept_language, t
from backend.core.maintenance import MaintenanceMiddleware
from backend.core.rate_limit import setup_rate_limit_middleware
from backend.core.security_middleware import SecurityHeadersMiddleware
from backend.core.plugin_loader import load_plugins, unload_plugins
from backend.middleware.performance import performance_middleware

logger = logging.getLogger(__name__)


async def _scheduled_publish_loop(db_session_factory):
    """
    定时发布扫描器（每分钟扫描一次）

    Task 7: 后台循环将 status=scheduled 或 scheduled_at<=now 的文章发布。
    同时兼容旧实现：status=published 且 scheduled_at<=now 的也真正生效。
    """
    import asyncio as _asyncio

    from sqlalchemy import select

    from backend.models.blog import Post
    from backend.utils.compat import UTC as _UTC

    def _now():
        return datetime.now(_UTC)

    while True:
        try:
            async with db_session_factory() as session:
                query = select(Post).where(
                    (
                        (Post.status == "scheduled")
                        & (Post.scheduled_at.is_not(None))
                        & (Post.scheduled_at <= _now())
                    )
                    | (
                        (Post.status == "published")
                        & (Post.scheduled_at.is_not(None))
                        & (Post.scheduled_at <= _now())
                    )
                )
                result = await session.execute(query)
                posts = result.scalars().all()
                published_count = 0
                for p in posts:
                    if p.published_at is None:
                        p.published_at = p.scheduled_at
                    p.status = "published"
                    p.scheduled_at = None
                    published_count += 1
                if published_count:
                    await session.commit()
                    logger.info(f"[scheduler] 定时发布 {published_count} 篇文章")
        except Exception as exc:
            logger.exception(f"[scheduler] 扫描失败: {exc}")
        try:
            await _asyncio.sleep(60)
        except _asyncio.CancelledError:
            logger.info("[scheduler] 定时发布循环已取消")
            break


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None]:
    """
    应用生命周期管理

    启动时：
    - 检查 OOBE 是否完成
    - 初始化数据库连接
    - 检查数据库连接状态
    - 启动定时发布循环

    关闭时：
    - 关闭数据库连接池
    - 清理缓存连接
    """
    import asyncio as _asyncio

    from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

    from backend.core.paths import CONFIG_FILE, OOBE_LOCK_FILE

    logger.info(f"正在启动 {settings.app_name}...")
    logger.info(f"运行环境: {settings.environment}")
    logger.info(f"调试模式: {settings.debug}")

    oobe_complete = OOBE_LOCK_FILE.exists() and CONFIG_FILE.exists()

    scheduler_task = None

    if not oobe_complete:
        logger.info("OOBE 未完成，跳过数据库初始化与定时发布循环")
        yield
        if scheduler_task and not scheduler_task.done():
            scheduler_task.cancel()
            try:
                await scheduler_task
            except Exception:
                pass
        return

    await init_db()

    db_connected = await check_db_connection()
    if db_connected:
        db_info = await get_db_info()
        logger.info(f"数据库连接成功: {db_info}")
    else:
        logger.error("数据库连接失败")

    try:
        from backend.core.database import engine

        if engine is None:
            engine = create_async_engine(settings.database_url)
        from sqlalchemy.ext.asyncio import AsyncSession as _AsyncSession

        db_session_factory = async_sessionmaker(
            engine, class_=_AsyncSession, expire_on_commit=False
        )
        scheduler_task = _asyncio.create_task(_scheduled_publish_loop(db_session_factory))
    except Exception as exc:
        logger.exception(f"[scheduler] 启动失败: {exc}")
        scheduler_task = None

    # 加载插件（在数据库就绪后注册路由钩子/事件订阅）
    try:
        loaded = await load_plugins(app)
        if loaded:
            logger.info(f"[plugins] 已加载插件: {', '.join(loaded)}")
    except Exception as exc:
        logger.exception(f"[plugins] 加载插件失败: {exc}")

    # 启动插件与主题平台：扫描清单→对齐DB→重放激活插件→默认激活主题
    try:
        from backend.core.database import async_session_maker
        from backend.core.extensions import bootstrap_extensions

        if async_session_maker is not None:
            async with async_session_maker() as ext_db:
                ext_state = await bootstrap_extensions(ext_db, force_rescan=False)
            logger.info(
                "[extensions] 插件扫描=%s 激活=%s 主题扫描=%s 当前=%s",
                ext_state.get("plugins_scanned"),
                ext_state.get("plugins_booted"),
                ext_state.get("themes_scanned"),
                ext_state.get("theme_active"),
            )
    except Exception as exc:
        logger.exception("[extensions] 启动初始化失败: %s", exc)

    logger.info(f"{settings.app_name} 启动完成")

    yield

    if scheduler_task and not scheduler_task.done():
        scheduler_task.cancel()
        try:
            await scheduler_task
        except _asyncio.CancelledError:
            pass
        except Exception:
            logger.exception("[scheduler] 关闭时出现异常")

    # 卸载插件（调用各插件 deactivate 钩子）
    try:
        await unload_plugins(app)
    except Exception as exc:
        logger.exception(f"[plugins] 卸载插件失败: {exc}")

    logger.info(f"正在关闭 {settings.app_name}...")
    await close_db()

    from backend.core.cache import cache

    if hasattr(cache.backend, "close"):
        await cache.backend.close()

    logger.info(f"{settings.app_name} 已关闭")


def create_application() -> FastAPI:
    """
    创建 FastAPI 应用实例

    配置：
    - 应用元数据
    - 中间件
    - 路由
    - 异常处理器
    - OpenAPI 文档

    Returns:
        FastAPI: 应用实例
    """
    app = FastAPI(
        title=settings.app_name,
        description="""
## Rosetta 博客平台 API

一个现代化的博客平台，使用 FastAPI + Astro 构建。

### 功能特性

- 🔐 **用户认证**: JWT 令牌认证，支持刷新令牌
- 📝 **文章管理**: 支持多语言、Markdown、SEO 优化
- 💬 **评论系统**: 支持嵌套回复、审核机制
- 🏷️ **分类标签**: 灵活的内容组织
- 🌐 **多语言**: 支持中文、英文、日文、繁体中文
- 📱 **媒体管理**: 图片上传、裁剪、压缩

### 认证方式

使用 Bearer Token 认证：
```
Authorization: Bearer <access_token>
```
        """,
        version="1.0.0",
        # 文档端点开关：
        # - production 环境：严格依赖 DEBUG=true 才开启（默认关闭，避免接口泄露）
        # - development/staging 环境：即便 DEBUG=false 也默认开启，便于联调与 OOBE 安装后自查
        docs_url="/docs" if (settings.debug or settings.environment != "production") else None,
        redoc_url="/redoc" if (settings.debug or settings.environment != "production") else None,
        openapi_url="/openapi.json" if (settings.debug or settings.environment != "production") else None,
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.effective_cors_origins,
        allow_credentials=settings.cors_allow_credentials,
        allow_methods=settings.cors_allow_methods,
        allow_headers=settings.cors_allow_headers,
    )

    app.add_middleware(SecurityHeadersMiddleware)

    app.add_middleware(MaintenanceMiddleware)

    # 全局限流中间件（对标 WordPress 防爆破/滥用防护）：
    # - 登录/注册/找回密码等敏感接口强制限流
    # - 普通写接口与全局 API 兜底限流
    # - /health、/docs 等运维端点白名单豁免
    setup_rate_limit_middleware(app)

    # 生产环境受信任主机保护：OOBE 未完成前不限制（站点 URL 尚未写入，默认 localhost 过于狭窄）
    if settings.is_production:
        from backend.core.deps import is_oobe_complete

        oobe_done = is_oobe_complete()
        if oobe_done:
            raw = settings.site_url or ""
            host = raw.replace("https://", "").replace("http://", "").split("/")[0].split(":")[0]
            allowed = [host]
            # 本地调试/回退保护：允许 localhost / 127.0.0.1 访问生产构建
            if host not in ("localhost", "127.0.0.1"):
                allowed.extend(["localhost", "127.0.0.1"])
            app.add_middleware(
                TrustedHostMiddleware,
                allowed_hosts=allowed,
            )
        else:
            # OOBE 期间不做 host 限制；安装完成后 .oobe_complete 文件写入，重启后生效
            logger.info("OOBE incomplete: skipping TrustedHostMiddleware until install completes")

    @app.middleware("http")
    async def i18n_middleware(request: Request, call_next):
        """国际化中间件"""
        accept_language = request.headers.get("Accept-Language")
        language = parse_accept_language(accept_language)
        I18nContext.set_language(language)
        try:
            response = await call_next(request)
        finally:
            I18nContext.reset()
        return response

    @app.middleware("http")
    async def oobe_middleware(request: Request, call_next):
        """OOBE 安装状态中间件

        - 若 .oobe_complete 不存在：
          - 放行 /api/oobe/*、/api/captcha/*、/health、/docs、/openapi.json、/redoc、/favicon.ico
          - 其余 /api/* 返回 503 + {success: false, error_code: OOBE_REQUIRED, message: 请先完成安装向导}
          - 非 /api/*（Astro 静态/页面）放行，由前端自行判断跳转
        - 若 .oobe_complete 存在：访问 /oobe 路径时重定向 /
        """
        from backend.core.deps import is_oobe_complete
        from backend.core.exceptions import OOBE_REQUIRED

        path = request.url.path
        oobe_done = is_oobe_complete()

        if not oobe_done:
            allowed_prefixes = (
                "/api/oobe/",
                "/api/captcha/",
                "/api/media/bing-wallpaper",
            )
            allowed_exact = (
                "/health",
                "/health/",
                "/api/health",
                "/api/health/",
                "/docs",
                "/openapi.json",
                "/redoc",
                "/favicon.ico",
            )
            if path.startswith(allowed_prefixes) or path in allowed_exact:
                return await call_next(request)
            if path.startswith("/api/"):
                return JSONResponse(
                    status_code=503,
                    content={
                        "success": False,
                        "error_code": OOBE_REQUIRED,
                        "message": "请先完成安装向导",
                    },
                )
            return await call_next(request)

        if path.startswith("/oobe"):
            from fastapi.responses import RedirectResponse

            return RedirectResponse(url="/", status_code=302)

        return await call_next(request)

    @app.middleware("http")
    async def tenant_middleware(request: Request, call_next):
        """多租户站点解析中间件

        解析当前请求归属的站点，写入租户上下文（backend.core.tenant）。
        解析优先级：JWT site 声明 → /s/{slug} 路径 → Host 头 → 默认站点(1)。

        阶段说明：当前为骨架实现，默认恒定使用 DEFAULT_SITE_ID=1（单站点行为不变）。
        多站点启用后，此处应查询 sites 表将 slug/domain 映射为 site_id。
        真正的租户数据过滤由业务层通过 require_site_filter() 显式触发，
        未设置的查询保持不过滤（向后兼容）。
        """
        from backend.core.tenant import DEFAULT_SITE_ID, set_current_site_id

        # TODO(多租户启用): 解析 /s/{slug} 或 Host 头 → 查 sites 表 → 设 site_id
        set_current_site_id(DEFAULT_SITE_ID)
        try:
            response = await call_next(request)
        finally:
            set_current_site_id(None)
        return response

    @app.middleware("http")
    async def request_logging_middleware(request: Request, call_next):
        """请求日志中间件"""
        start_time = time.time()

        response = await call_next(request)

        process_time = (time.time() - start_time) * 1000

        logger.info(
            f"{request.method} {request.url.path} - {response.status_code} - {process_time:.2f}ms"
        )

        response.headers["X-Process-Time"] = f"{process_time:.2f}ms"

        # 记录访问日志（不记录API文档和静态资源）
        if not request.url.path.startswith(
            ("/docs", "/openapi.json", "/redoc", "/media", "/health")
        ):
            try:
                from backend.api.monitoring import record_visit

                await record_visit(request, response.status_code, process_time)
            except Exception:
                pass

        return response

    # 性能监控中间件：采样记录请求响应时间到数据库
    app.middleware("http")(performance_middleware)

    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(request: Request, exc: StarletteHTTPException):
        """HTTP 异常处理器，保留 exc.headers（如 Retry-After, WWW-Authenticate 等）"""
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "success": False,
                "message": exc.detail,
                "error_code": exc.status_code,
            },
            headers=dict(exc.headers) if exc.headers else None,
        )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError):
        """请求验证异常处理器"""
        errors = []
        for error in exc.errors():
            field = ".".join(str(loc) for loc in error["loc"])
            errors.append(
                {
                    "field": field,
                    "message": error["msg"],
                    "type": error["type"],
                }
            )

        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={
                "success": False,
                "message": t("validation_error"),
                "error_code": "VALIDATION_ERROR",
                "errors": errors,
            },
        )

    @app.exception_handler(AppException)
    async def app_exception_handler(request: Request, exc: AppException):
        """应用异常处理器"""
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "success": False,
                "message": exc.message,
                "error_code": exc.error_code,
            },
        )

    @app.exception_handler(Exception)
    async def general_exception_handler(request: Request, exc: Exception):
        """通用异常处理器"""
        logger.exception(f"未处理的异常: {exc}")

        if settings.debug:
            return JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content={
                    "success": False,
                    "message": str(exc),
                    "error_code": 500,
                },
            )

        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "success": False,
                "message": t("internal_server_error"),
                "error_code": 500,
            },
        )

    @app.get(
        "/health",
        tags=["系统"],
        summary="健康检查",
        description="检查服务是否正常运行",
    )
    async def health_check():
        """健康检查端点（数据库不可用时返回 503）"""
        db_connected = await check_db_connection()
        health_data = {
            "status": "healthy" if db_connected else "unhealthy",
            "app_name": settings.app_name,
            "version": "1.0.0",
            "environment": settings.environment,
            "database": "connected" if db_connected else "disconnected",
        }

        return JSONResponse(
            status_code=200 if db_connected else 503,
            content={
                "success": db_connected,
                "data": health_data,
                "message": "服务健康" if db_connected else "服务异常：数据库连接失败",
            },
        )

    app.include_router(users.router, prefix="/api/users", tags=["用户"])
    app.include_router(blog.router, prefix="/api/blog", tags=["博客"])
    app.include_router(core.router, prefix="/api", tags=["核心"])
    # avatar_proxy 必须在 media.router 之前挂载，否则 /api/media/avatar 会被
    # media.router 的 /{category}/{filename} 捕获（category=media 不在白名单 -> 404）。
    app.include_router(avatar_proxy.router, prefix="/api", tags=["媒体"])
    app.include_router(media.router, prefix="/api/media", tags=["媒体"])
    app.include_router(migration.router, prefix="/api/admin", tags=["数据库迁移"])
    app.include_router(guestbook.router, prefix="/api", tags=["留言板"])
    app.include_router(voting.router, prefix="/api/voting", tags=["投票"])
    app.include_router(notification.router, prefix="/api/notifications", tags=["通知"])
    app.include_router(favorite.router, prefix="/api/favorites", tags=["收藏"])
    app.include_router(admin.router, prefix="/api/admin", tags=["后台管理"])
    app.include_router(webhook.router, prefix="/api/webhooks", tags=["Webhook"])
    app.include_router(import_export.router, prefix="/api/admin", tags=["导入导出"])
    app.include_router(seo.router, prefix="/api/seo", tags=["SEO"])
    app.include_router(advanced.router, prefix="/api", tags=["高级管理"])
    app.include_router(monitoring.router, prefix="/api/monitoring", tags=["监控"])
    app.include_router(toc.router, prefix="/api/toc", tags=["TOC"])
    app.include_router(shortcodes.router, prefix="/api", tags=["短代码"])
    app.include_router(title.router, prefix="/api/admin", tags=["用户称号"])
    app.include_router(captcha.router, prefix="/api/captcha", tags=["验证码"])
    app.include_router(messages.router, prefix="/api", tags=["私信"])
    app.include_router(translate.router, prefix="/api", tags=["翻译"])
    app.include_router(oobe.router, prefix="/api", tags=["OOBE"])
    app.include_router(announcement.router, prefix="/api", tags=["公告"])
    app.include_router(activity.router, prefix="/api", tags=["网站动态"])
    app.include_router(hero.router, prefix="/api", tags=["Hero轮播"])
    app.include_router(post_series.router, prefix="/api", tags=["文章系列"])
    app.include_router(post_encryption.router, prefix="/api", tags=["内容加密"])
    app.include_router(post_crypto.router, prefix="/api", tags=["文章加密工具"])
    app.include_router(scheduled_posts.router, prefix="/api", tags=["定时发布"])
    app.include_router(comment_reactions.router, prefix="/api", tags=["评论表情反应"])
    app.include_router(ranking.router, prefix="/api", tags=["热门排行"])
    app.include_router(performance.router, prefix="/api/admin", tags=["性能监控"])
    app.include_router(stats.router, prefix="/api/admin", tags=["仪表盘"])
    app.include_router(admin_logs.router, prefix="/api/admin", tags=["操作日志"])
    app.include_router(admin_tools.router, prefix="/api/admin", tags=["Admin 工具"])
    app.include_router(settings_groups.router, prefix="/api", tags=["系统设置"])
    app.include_router(themes.router, prefix="/api", tags=["主题"])
    app.include_router(themes_ext.router, prefix="/api/admin", tags=["主题平台"])
    app.include_router(plugins.router, prefix="/api/admin", tags=["插件平台"])
    app.include_router(docs.router, prefix="/api", tags=["开发文档"])
    app.include_router(bing.router, prefix="/api", tags=["Bing壁纸"])
    app.include_router(bing_image.router, prefix="/api", tags=["Bing壁纸"])
    app.include_router(comments.router, prefix="/api", tags=["评论"])
    # ===== Gallery（相册）：公开 + 管理
    from backend.api.gallery import admin_router as gallery_admin_router
    from backend.api.gallery import public_router as gallery_public_router
    app.include_router(gallery_public_router, prefix="/api", tags=["相册"])
    app.include_router(gallery_admin_router, prefix="/api", tags=["相册管理"])

    media_dir = BASE_DIR / settings.media_dir
    media_dir.mkdir(parents=True, exist_ok=True)
    app.mount("/media", StaticFiles(directory=str(media_dir)), name="media")

    # 静态兜底资源（头像/Bing 壁纸代理的 _FINAL_FALLBACK 指向 /favicon/rosetta-256.png）。
    # 必须挂载到 /favicon，否则代理兜底分支会 307 -> 404，导致前端控制台报错。
    static_dir = BASE_DIR / "static"
    static_dir.mkdir(parents=True, exist_ok=True)
    app.mount("/favicon", StaticFiles(directory=str(static_dir)), name="favicon-static")

    # ── 插件路由统一挂载（必须在所有 include_router 之后） ──────────────────
    # 1) 启动时的 lifespan 已通过 bootstrap_extensions 让已激活插件的 register(ctx)
    #    将 admin/public router / menu 提交到 routing_registry。
    # 2) 后续运行时激活插件：注册新的 router 到 registry 后，FastAPI 仍可通过
    #    app.include_router 动态追加（ASGI 行为）；当前实现只在创建期统一挂载，
    #    运行时动态激活的插件路由会在 mount_all 内部以「重复调用安全」的方式补挂。
    from backend.core.routing_registry import routing_registry

    routing_registry.mount_all(app)

    @app.get("/", tags=["系统"], summary="API 根路径")
    async def root():
        return {
            "name": settings.app_name,
            "version": "1.0.0",
            "docs": "/docs" if settings.debug else None,
            "health": "/health",
            "api": "/api",
        }

    return app


app = create_application()
