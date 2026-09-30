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
import re
import time
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from datetime import datetime

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from scalar_fastapi import get_scalar_api_reference
from starlette.exceptions import HTTPException as StarletteHTTPException

from backend.api import (
    activity,
    admin,
    admin_logs,
    admin_tools,
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
    plugins,
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
    title,
    toc,
    translate,
    users,
    voting,
    webhook,
)
from backend.core.config import settings
from backend.core.database import check_db_connection, close_db, get_db_info, init_db
from backend.core.exceptions import RATE_LIMIT_EXCEEDED, AppException
from backend.core.i18n import I18nContext, parse_accept_language, t
from backend.core.maintenance import MaintenanceMiddleware
from backend.core.paths import BASE_DIR
from backend.core.plugin_loader import load_plugins, unload_plugins
from backend.core.rate_limit import setup_rate_limit_middleware
from backend.core.security_middleware import SecurityHeadersMiddleware
from backend.middleware.performance import performance_middleware

logger = logging.getLogger(__name__)


def _resolve_app_version() -> str:
    """版本单一真源：读取根 pyproject.toml [project].version。

    settings.app_version 默认值会漂移（硬编码 "1.0.0"），发布版本号只维护
    pyproject 一处；读取失败时回退 settings.app_version 保证可启动。
    """
    try:
        content = (BASE_DIR / "pyproject.toml").read_text(encoding="utf-8")
        match = re.search(r"^version\s*=\s*\"([^\"]+)\"", content, re.MULTILINE)
        if match:
            return match.group(1)
    except OSError:
        pass
    return settings.app_version


APP_VERSION = _resolve_app_version()

# ── OpenAPI 标签元数据 ──────────────────────────────────────────────────────
# 为每个 API 分组提供中文说明，Scalar / Redoc / Swagger 会在侧边栏展示。
TAG_METADATA: list[dict[str, str]] = [
    {"name": "系统", "description": "应用健康检查与基础信息"},
    {"name": "用户", "description": "注册、登录、令牌刷新、个人资料与密码管理"},
    {"name": "博客", "description": "文章、分类、标签、评论的公开与管理接口"},
    {"name": "核心", "description": "站点公开配置、导航、友情链接等前台核心数据"},
    {"name": "媒体", "description": "文件上传、头像代理、图片处理"},
    {"name": "数据库迁移", "description": "Alembic 迁移状态查询与执行"},
    {"name": "留言板", "description": "访客留言的提交、审核与管理"},
    {"name": "投票", "description": "文章投票与统计"},
    {"name": "通知", "description": "站内通知的读取与标记"},
    {"name": "收藏", "description": "文章收藏管理"},
    {"name": "后台管理", "description": "仪表盘统计、用户管理、系统概览"},
    {"name": "Webhook", "description": "外部服务回调配置与日志"},
    {"name": "导入导出", "description": "内容数据的批量导入与导出"},
    {"name": "SEO", "description": "站点地图、Robots、SEO 设置"},
    {"name": "高级管理", "description": "缓存清理、系统维护等高级操作"},
    {"name": "监控", "description": "运行状态、访问日志、性能指标"},
    {"name": "TOC", "description": "文章目录生成"},
    {"name": "短代码", "description": "内容短代码解析与预览"},
    {"name": "用户称号", "description": "用户头衔与徽章管理"},
    {"name": "验证码", "description": "图形验证码生成与校验"},
    {"name": "私信", "description": "用户间私信收发"},
    {"name": "翻译", "description": "多语言内容翻译接口"},
    {"name": "OOBE", "description": "开箱即用安装向导（首次部署时使用）"},
    {"name": "公告", "description": "站点公告发布与管理"},
    {"name": "网站动态", "description": "用户活动时间线"},
    {"name": "Hero轮播", "description": "首页 Hero 区轮播图配置"},
    {"name": "文章系列", "description": "系列文章的组织与展示"},
    {"name": "内容加密", "description": "文章内容加密访问"},
    {"name": "文章加密工具", "description": "文章加密的管理工具"},
    {"name": "定时发布", "description": "定时发布任务管理"},
    {"name": "评论表情反应", "description": "评论表情互动"},
    {"name": "热门排行", "description": "热门文章排行榜"},
    {"name": "性能监控", "description": "接口性能数据查询"},
    {"name": "仪表盘", "description": "后台仪表盘统计数据"},
    {"name": "操作日志", "description": "管理员操作审计日志"},
    {"name": "Admin 工具", "description": "后台通用工具接口"},
    {"name": "系统设置", "description": "站点配置分组读写"},
    {"name": "主题", "description": "前台主题切换与配置"},
    {"name": "主题平台", "description": "主题市场与安装管理"},
    {"name": "插件平台", "description": "插件市场与安装管理"},
    {"name": "开发文档", "description": "API 文档与开发指南"},
    {"name": "Bing壁纸", "description": "Bing 每日壁纸获取"},
    {"name": "评论", "description": "文章评论的提交与管理"},
    {"name": "相册", "description": "公开相册浏览"},
    {"name": "相册管理", "description": "相册与照片管理"},
]


def _build_openapi(app: FastAPI) -> dict:
    """生成带中文元数据的 OpenAPI schema。

    在 FastAPI 默认 schema 基础上补充：
    - 应用描述、联系信息、许可证
    - 服务器列表（按环境区分）
    - Bearer 认证方案说明
    - 标签分组描述
    """
    if app.openapi_schema:
        return app.openapi_schema

    from fastapi.openapi.utils import get_openapi

    schema = get_openapi(
        title=settings.app_name,
        version=APP_VERSION,
        description=(
            "## Rosetta 博客平台 API\n\n"
            "一个现代化的多语言博客平台，基于 FastAPI 构建。\n\n"
            "### 认证方式\n\n"
            "除公开接口外，所有请求需在 Header 中携带 Bearer Token：\n"
            "```\nAuthorization: Bearer <access_token>\n```\n\n"
            "通过 `/api/users/login` 获取 access_token（1 小时有效），"
            "过期后使用 `/api/users/refresh` 换取新令牌。\n\n"
            "### 响应格式\n\n"
            "所有接口统一返回如下结构：\n"
            '```json\n{"success": true, "data": {...}, "message": "..."}\n```\n\n'
            "失败时返回：\n"
            '```json\n{"success": false, "error_code": "...", "message": "..."}\n```'
        ),
        contact={
            "name": "Rosetta Project",
            "url": settings.site_url or "https://github.com/Choyeon/Rosetta",
        },
        license_info={
            "name": "MIT License",
            "url": "https://opensource.org/licenses/MIT",
        },
        routes=app.routes,
    )

    # 标签描述
    schema["tags"] = TAG_METADATA

    # 服务器列表
    servers = [{"url": settings.site_url or "/", "description": "当前站点"}]
    if settings.site_url and "localhost" not in settings.site_url:
        servers.append({"url": "http://127.0.0.1:8000", "description": "本地开发"})
    schema["servers"] = servers

    # 安全方案说明
    if "components" in schema and "securitySchemes" in schema["components"]:
        scheme = schema["components"]["securitySchemes"]
        if "HTTPBearer" in scheme:
            scheme["HTTPBearer"]["description"] = (
                "登录后获取的 access_token，有效期 1 小时。"
                "Header 格式：`Authorization: Bearer <token>`"
            )

    app.openapi_schema = schema
    return schema


async def _scheduled_publish_loop(db_session_factory):
    """定时发布扫描器，每分钟扫描一次。

    将到达 scheduled_at 的文章状态切换为 published，并清空 scheduled_at。
    兼容历史数据：status 已为 published 但 scheduled_at 仍在的也一并清理。
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


async def _log_retention_loop(db_session_factory):
    """按保留期收敛只增日志表（visit_logs / performance_metrics / operation_logs）。

    刻意**先睡后删**：进程启动的那一轮不做删除，既不给冷启动加锁开销，
    也让短生命周期进程（含测试）不会误删数据。多 worker 各跑各的没问题——
    删除以 id 集合为条件、幂等，不额外引分布式锁（该锁要求启用 Redis，
    单机 / 内存缓存部署直接抛错）。
    """
    import asyncio as _asyncio

    from backend.services.log_retention import (
        prune_expired_logs,
        retention_loop_interval_seconds,
    )

    while True:
        try:
            await _asyncio.sleep(retention_loop_interval_seconds())
        except _asyncio.CancelledError:
            logger.info("[retention] 日志保留循环已取消")
            break

        try:
            async with db_session_factory() as session:
                await prune_expired_logs(session)
        except Exception as exc:
            logger.exception(f"[retention] 日志清理失败: {exc}")


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
    retention_task = None

    if not oobe_complete:
        logger.info("OOBE 未完成，跳过数据库初始化与定时发布循环")
        yield
        if scheduler_task and not scheduler_task.done():
            scheduler_task.cancel()
            try:
                await scheduler_task
            except _asyncio.CancelledError:
                pass
            except Exception:
                logger.exception("[scheduler] 关闭时出现异常")
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
        retention_task = _asyncio.create_task(_log_retention_loop(db_session_factory))
    except Exception as exc:
        logger.exception(f"[scheduler] 启动失败: {exc}")
        scheduler_task = None
        retention_task = None

    # Webhook 事件投递：把 WEBHOOK_EVENTS 挂到 hooks 总线。
    # 没这一步，后台配置的订阅就是一张永远不会兑现的清单（历史缺陷）。
    try:
        from backend.api.webhook import register_webhook_listeners

        register_webhook_listeners()
    except Exception as exc:
        logger.exception(f"[webhook] 事件监听注册失败: {exc}")

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

    # 缓存预热：后台任务跑，不拖慢启动；同时拉起定时刷新保持缓存热度。
    # AGENTS.md 把"缓存预热"列为已落地能力，但 warmup_cache / 定时刷新器此前从未被调用。
    from backend.core.cache_warmer import scheduled_cache_refresher, warmup_cache

    async def _run_cache_warmup():
        stats = await warmup_cache()
        logger.info(f"[cache] 启动预热结果: {stats}")

    cache_warmup_task = _asyncio.create_task(_run_cache_warmup())
    await scheduled_cache_refresher.start()

    logger.info(f"{settings.app_name} 启动完成")

    yield

    await scheduled_cache_refresher.stop()

    if cache_warmup_task and not cache_warmup_task.done():
        cache_warmup_task.cancel()
        try:
            await cache_warmup_task
        except _asyncio.CancelledError:
            pass
        except Exception:
            logger.exception("[cache] 预热任务取消时出现异常")

    for _bg_task in (scheduler_task, retention_task):
        if _bg_task and not _bg_task.done():
            _bg_task.cancel()
            try:
                await _bg_task
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
    # 文档端点开关：
    # - production 环境：仅 DEBUG=true 时开启（避免接口结构泄露）
    # - development/staging 环境：默认开启，便于联调与 OOBE 后自查
    docs_enabled = settings.debug or settings.environment != "production"

    app = FastAPI(
        title=settings.app_name,
        version=APP_VERSION,
        openapi_url="/openapi.json" if docs_enabled else None,
        docs_url=None,
        redoc_url=None,
        lifespan=lifespan,
    )
    app.openapi = lambda: _build_openapi(app)

    if docs_enabled:

        @app.get("/docs", include_in_schema=False, tags=["系统"])
        async def scalar_docs():
            return get_scalar_api_reference(
                openapi_url=app.openapi_url,
                title=f"{settings.app_name} · API 文档",
                layout="modern",
                theme="default",
                dark_mode=True,
                hide_download_button=False,
                default_open_all_tags=False,
                servers=[{"url": "/", "description": "当前站点"}],
                overrides={
                    "localization": {"locale": "zh-CN"},
                },
            )

        from fastapi.openapi.docs import get_redoc_html

        @app.get("/redoc", include_in_schema=False, tags=["系统"])
        async def redoc_docs():
            return get_redoc_html(
                openapi_url=app.openapi_url,
                title=f"{settings.app_name} · ReDoc",
            )

    # CORS 中间件已移至所有中间件注册之后（最后 add = 最外层），见本函数末尾。
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
                # OOBE 向导页背景壁纸：服务端 Bing 中继（域名白名单 + net_guard，
                # 无凭据、无个人信息），不放行则向导只能直连 bing.com 被 CORS 拦死。
                "/api/bing/",
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
            except (ImportError, RuntimeError) as exc:
                # 遥测不得拖垮业务请求：monitoring 未加载、或此刻没有运行中的事件循环
                # （record_visit 内部已消化 QueueFull）时跳过这一条即可。
                # 其余异常（签名改动、属性拼错）是真实缺陷，必须照样抛出而不是被吞。
                logger.debug("[access-log] 访问记录入队失败：%s", exc)

        return response

    # 性能监控中间件：采样记录请求响应时间到数据库
    app.middleware("http")(performance_middleware)

    # CORSMiddleware 最后 add：Starlette 中后注册的中间件位于最外层，这样
    # OOBE 503 / 限流 429 / 维护模式 503 等所有短路响应都会带上 CORS 头，
    # OPTIONS 预检也不会被内层中间件先行拦截。CSRF 校验依赖的是请求头
    # （X-CSRF-Token / Authorization），与响应侧 CORS 头互不影响。
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.effective_cors_origins,
        allow_credentials=settings.cors_allow_credentials,
        allow_methods=settings.cors_allow_methods,
        allow_headers=settings.cors_allow_headers,
    )

    # HTTPException.detail → 语义化 error_code 的回退映射。
    # 注意：401 的 error_code 必须是字符串语义码（如 UNAUTHORIZED）——
    # 前端 apiFetch/useAPI 判定刷新走 HTTP status === 401（lib/utils.ts::isOobeRequiredError
    # 判定 OOBE 走 503 + error_code === "OOBE_REQUIRED"），均不依赖裸数字状态码，
    # 语义化映射不会破坏 401 刷新 / 503 OOBE 跳转链路。
    _STATUS_ERROR_CODES: dict[int, str] = {
        400: "BAD_REQUEST",
        401: "UNAUTHORIZED",
        403: "FORBIDDEN",
        404: "NOT_FOUND",
        405: "METHOD_NOT_ALLOWED",
        409: "CONFLICT",
        413: "PAYLOAD_TOO_LARGE",
        # 与下方 RequestValidationError 处理器的产出码同源——同一个 422
        # 不得在"schema 拦截"与"字符串 detail 回退"两条链路上长出两个码。
        422: "VALIDATION_ERROR",
        423: "ACCOUNT_LOCKED",
        # 与 core/exceptions.py 的 RateLimitException、core/rate_limit.py 的三个触发点同源，
        # 避免同一个 429 在不同链路上长出四种 error_code。
        429: RATE_LIMIT_EXCEEDED,
        503: "SERVICE_UNAVAILABLE",
    }

    def _fallback_error_code(status_code: int) -> str:
        if status_code in _STATUS_ERROR_CODES:
            return _STATUS_ERROR_CODES[status_code]
        return "INTERNAL_SERVER_ERROR" if status_code >= 500 else "REQUEST_FAILED"

    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(request: Request, exc: StarletteHTTPException):
        """HTTP 异常处理器，保留 exc.headers（如 Retry-After, WWW-Authenticate 等）

        契约（AGENTS.md §7.2）：error_code 必须是语义化字符串。
        1) detail 已是本项目的错误包络（dict 且含 error_code 或 message）→
           原样透传 error_code / message / errors 及其余扩展键（如
           retry_after_seconds），绝不用数字状态码覆盖 error_code；
        2) detail 是校验错误列表 → 展开为 errors:[{field,message,type}]；
        3) detail 是普通字符串 → error_code 回退到按状态码映射的语义默认值。
        """
        detail = exc.detail
        content: dict = {"success": False}

        if isinstance(detail, dict) and ("error_code" in detail or "message" in detail):
            # 包络透传：success 强制为 False，其余键（含 retry_after_seconds 等扩展键、
            # errors 列表）原样保留。不输出 detail 键——包络形状以 message 为准，
            # 前端 extractApiErrorMessage 优先读 message（字符串），不会误读 dict。
            content.update(detail)
            content["success"] = False
            ec = content.get("error_code")
            if not isinstance(ec, str) or not ec:
                content["error_code"] = _fallback_error_code(exc.status_code)
            msg = content.get("message")
            if not isinstance(msg, str):
                content["message"] = str(msg) if msg is not None else "请求处理失败"
        elif isinstance(detail, list):
            # FastAPI 校验形状的 list detail：展开为 field/message/type，禁止 [object Object]
            errors: list[dict] = []
            for item in detail:
                if isinstance(item, dict):
                    loc = item.get("loc")
                    field = (
                        ".".join(str(x) for x in loc)
                        if isinstance(loc, (list, tuple))
                        else str(item.get("field", ""))
                    )
                    errors.append(
                        {
                            "field": field,
                            "message": str(item.get("msg") or item.get("message") or item),
                            "type": str(item.get("type", "")),
                        }
                    )
                else:
                    errors.append({"field": "", "message": str(item), "type": "value_error"})
            content["message"] = t("validation_error")
            content["error_code"] = _fallback_error_code(exc.status_code)
            content["errors"] = errors
        else:
            content["message"] = str(detail)
            content["error_code"] = _fallback_error_code(exc.status_code)

        return JSONResponse(
            status_code=exc.status_code,
            content=content,
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
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
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
                    "error_code": "INTERNAL_SERVER_ERROR",
                },
            )

        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "success": False,
                "message": t("internal_server_error"),
                "error_code": "INTERNAL_SERVER_ERROR",
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
            "version": app.version,
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

    # /api/health 别名：前端生产 Nitro 代理同源 /api/* 时，
    # 前端代码调 /api/health 可直接命中（无需特殊处理根路径路由）。
    app.get(
        "/api/health",
        tags=["系统"],
        summary="健康检查 (/api 前缀别名)",
        description="前端 SSR/Nitro 同源代理场景下的健康检查入口，与 /health 等价。",
    )(health_check)

    app.include_router(users.router, prefix="/api/users")
    app.include_router(blog.router, prefix="/api/blog")
    app.include_router(core.router, prefix="/api")
    # avatar_proxy 必须在 media.router 之前挂载，否则 /api/media/avatar 会被
    # media.router 的 /{category}/{filename} 捕获（category=media 不在白名单 -> 404）。
    app.include_router(avatar_proxy.router, prefix="/api")
    app.include_router(media.router, prefix="/api/media")
    app.include_router(migration.router, prefix="/api/admin")
    app.include_router(guestbook.router, prefix="/api")
    app.include_router(voting.router, prefix="/api/voting")
    app.include_router(notification.router, prefix="/api/notifications")
    app.include_router(favorite.router, prefix="/api/favorites")
    app.include_router(admin.router, prefix="/api/admin")
    app.include_router(webhook.router, prefix="/api/webhooks")
    app.include_router(import_export.router, prefix="/api/admin")
    app.include_router(seo.router, prefix="/api/seo")
    app.include_router(advanced.router, prefix="/api")
    app.include_router(monitoring.router, prefix="/api/monitoring")
    app.include_router(toc.router, prefix="/api/toc")
    app.include_router(shortcodes.router, prefix="/api")
    app.include_router(title.router, prefix="/api/admin")
    app.include_router(captcha.router, prefix="/api/captcha")
    app.include_router(messages.router, prefix="/api")
    app.include_router(translate.router, prefix="/api")
    app.include_router(oobe.router, prefix="/api")
    app.include_router(announcement.router, prefix="/api")
    app.include_router(activity.router, prefix="/api")
    app.include_router(hero.router, prefix="/api")
    app.include_router(post_series.router, prefix="/api")
    app.include_router(post_encryption.router, prefix="/api")
    app.include_router(post_crypto.router, prefix="/api")
    app.include_router(scheduled_posts.router, prefix="/api")
    app.include_router(comment_reactions.router, prefix="/api")
    app.include_router(ranking.router, prefix="/api")
    app.include_router(performance.router, prefix="/api/admin")
    app.include_router(stats.router, prefix="/api/admin")
    app.include_router(admin_logs.router, prefix="/api/admin")
    app.include_router(admin_tools.router, prefix="/api/admin")
    app.include_router(settings_groups.router, prefix="/api")
    app.include_router(themes.router, prefix="/api")
    app.include_router(themes_ext.router, prefix="/api/admin")
    app.include_router(plugins.router, prefix="/api/admin")
    app.include_router(docs.router, prefix="/api")
    app.include_router(bing.router, prefix="/api")
    app.include_router(bing_image.router, prefix="/api")
    app.include_router(comments.router, prefix="/api")
    # ===== Gallery（相册）：公开 + 管理
    from backend.api.gallery import admin_router as gallery_admin_router
    from backend.api.gallery import public_router as gallery_public_router

    app.include_router(gallery_public_router, prefix="/api")
    app.include_router(gallery_admin_router, prefix="/api")

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

    @app.get(
        "/",
        tags=["系统"],
        summary="API 根路径",
        description="返回应用名、版本与文档/健康检查入口的导航信息，无需鉴权。",
    )
    async def root():
        return {
            "name": settings.app_name,
            "version": app.version,
            "docs": "/docs" if docs_enabled else None,
            "health": "/health",
            "api": "/api",
        }

    return app


app = create_application()
