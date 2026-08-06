# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

ROSETTA 后端是基于 **FastAPI** + **SQLAlchemy 2.0 (async)** + **Pydantic v2** 构建的现代化博客平台 API 服务。采用分层架构（API → Service → Repository → Model），支持多语言（zh / en / ja / zh_Hant）、JWT 认证、Redis 缓存、Alembic 迁移、OOBE 引导流程。前端为 Astro 站点，通过 Vite 代理将 `/api/*` 请求转发到本服务。

## Commands

| Command | Purpose |
|---|---|
| `uvicorn backend.main:app --reload --port 8000` | 开发服务器，监听 `localhost:8000` |
| `uvicorn backend.main:app --host 0.0.0.0 --port 8000` | 生产服务器 |
| `python -m backend.migrations upgrade` | 升级数据库到 head |
| `python -m backend.migrations downgrade -1` | 回退一个版本 |
| `python -m backend.migrations revision -m "msg" --autogenerate` | 自动生成迁移 |
| `python -m backend.migrations current` | 查看当前数据库版本 |
| `python -m backend.migrations history` | 查看迁移历史 |
| `python -m backend.migrations status` | 数据库状态 + 版本对比 |
| `python -m backend.migrations init` | 初始化所有表并标记到 head |
| `python -m backend.migrations reset --force` | 清空并重建数据库（危险） |
| `python -m backend.scripts.mock_data` | 生成测试数据 |

从**项目根目录**运行所有命令（而非 `backend/` 目录内）。Python 3.11+ 必需。

开发模式下访问 `http://localhost:8000/docs` 查看 Swagger，`/redoc` 查看 ReDoc，`/health` 健康检查，`/` 返回 API 元信息。

## Architecture

### 分层架构

```
API (backend/api/)        → 路由、请求校验、依赖注入
  ↓
Service (backend/services/) → 业务逻辑、跨模型编排
  ↓
Repository (backend/repositories/) → 数据访问、查询封装
  ↓
Model (backend/models/)    → SQLAlchemy ORM
  ↓
Schema (backend/schemas/)  → Pydantic 请求/响应模型
```

### 应用入口

`backend/main.py` 的 `create_application()` 工厂函数组装：
- 中间件链：CORS → Maintenance → i18n（按 Accept-Language 切换语言）→ Request Logging → Performance
- 异常处理器：`StarletteHTTPException` / `RequestValidationError` / `AppException` / 兜底 `Exception`
- 路由注册：所有 `APIRouter` 通过 `include_router(prefix="/api/...")` 挂载
- 静态文件：`/media` 挂载到本地 `media/` 目录
- 生命周期：`lifespan` 检查 OOBE 状态 → 初始化 DB → 关闭时清理连接池与缓存

### 认证体系

- **JWT** 双令牌：access token（1 小时）+ refresh token（7 天），`HS256` 算法
- **密码哈希**：bcrypt，超 72 字节先 SHA-256 预处理
- **依赖注入别名**（`backend/core/auth.py`）：
  - `CurrentUser` — 必须登录
  - `CurrentUserOptional` — 可选登录
  - `CurrentStaff` — 必须管理员
  - `DB` — 异步数据库会话
- 使用方式：`async def handler(user: CurrentUser, db: DB)`

### 数据库与缓存

- **SQLAlchemy 2.0 async**，`DeclarativeBase` + `Mapped[T]` + `mapped_column()`
- 开发环境 SQLite + `NullPool`；生产环境 PostgreSQL + `AsyncAdaptedQueuePool`（含 `pool_pre_ping`、`pool_recycle`）
- **缓存层**（`backend/core/cache.py`）双后端：Redis（生产）/ Memory（开发），通过 `settings.redis_enabled` 切换
- `CACHE_TTL` 字典定义各业务键的 TTL（site_config=3600s、post_detail=600s 等），`make_cache_key()` 生成命名空间键
- `get_or_set_with_null()` 支持空值缓存防穿透，`cached()` 装饰器简化缓存模式

### 国际化

- `backend/core/i18n.py` 支持 `zh`、`en`、`ja`、`zh_Hant` 四种语言
- `I18nContext` 基于 `contextvars` 在请求中间件中设置语言
- 模型字段使用 `dict[str, str]` 存储多语言（如 `{"zh": "技术", "en": "Technology"}`）
- `get_i18n_value(data, lang)` 按 lang 取值，`LocalizedResponse.from_model()` 转换本地化响应

### 关键模块

- `backend/core/config.py` — `Settings` 类（Pydantic Settings），从 `.env` 加载，`lru_cache` 单例
- `backend/core/site_config.py` — `SiteConfig` 模型与配置管理（含 music/wallpaper 字段）
- `backend/core/maintenance.py` — 维护模式中间件，拒绝写入请求
- `backend/core/rate_limit.py` — 速率限制
- `backend/core/distributed_lock.py` — 分布式锁（Redis）
- `backend/middleware/performance.py` — 采样记录请求耗时到 `PerformanceMetric` 表
- `backend/api/oobe.py` — 开箱引导流程，写入 `.oobe_complete` 锁文件与 `rosetta.json`

### API 路由总览

所有路由统一前缀 `/api`，按模块分组：

| 模块 | 前缀 | 说明 |
|---|---|---|
| users | `/api/users` | 注册、登录、刷新令牌、个人资料 |
| blog | `/api/blog` | 文章、分类、标签、评论 |
| core | `/api` | 站点配置、导航、友链、页面、搜索占位符 |
| media | `/api/media` | 图片/文件上传 |
| admin | `/api/admin` | 后台管理、用户称号、性能监控、导入导出 |
| bing | `/api` | Bing 每日壁纸 |
| oobe | `/api` | 引导流程 |
| monitoring | `/api/monitoring` | 访问日志、统计 |
| 其他 | `/api/{name}` | guestbook、voting、notification、favorite、webhook、seo、toc、captcha、messages、translate、announcement、activity、hero、post_series、post_encryption、scheduled_posts、comment_reactions、ranking、performance |

### OOBE 流程

首次启动时无 `.oobe_complete` 锁文件，`lifespan` 跳过 DB 初始化，前端 `/api/config` 返回内置默认配置。完成引导后写入 `rosetta.json` 与 `.oobe_complete`，重启后正常加载。

### 关键目录

- `backend/migrations/versions/` — Alembic 迁移文件，命名 `hash_描述.py`
- `backend/docs/` — `api_reference.md`、`error_codes.md`、`types.ts`（前端类型定义）
- `backend/scripts/mock_data.py` — 测试数据生成
- `backend/utils/compat.py` — Python 3.11 前的 `UTC`、`timedelta` 兼容

## Code Style

- **Python 3.11+**，使用 `str | None` 现代联合类型语法
- **PEP 8**，4 空格缩进
- 双引号字符串
- `async`/`await` 全异步 I/O
- `Annotated[T, Depends(...)]` 依赖注入风格
- `Field(...)` 显式声明 Pydantic 字段约束与描述
- API 端点必须包含 `summary`、`description`、`response_model`
- 模块/类/公共函数必须有三引号 docstring
- 完整类型注解
- **Conventional Commits**（`feat:`、`fix:`、`chore:`、`docs:`、`refactor:`、`perf:`）

## Environment Configuration

通过 `.env` 文件配置（参考 `.env.example`），关键变量：

- `APP_ENV` — `development` / `staging` / `production`
- `DEBUG` — 开启 API 文档与详细错误
- `DATABASE_URL` — `sqlite+aiosqlite:///./rosetta.db` 或 `postgresql+asyncpg://...`
- `REDIS_ENABLED` / `REDIS_URL` — 缓存后端
- `SECRET_KEY` — JWT 签名密钥（生产必改，≥32 字符）
- `ACCESS_TOKEN_EXPIRE_MINUTES` / `REFRESH_TOKEN_EXPIRE_DAYS`
- `CORS_ORIGINS` — JSON 数组格式的允许来源
- `SITE_NAME` / `SITE_URL` / `SITE_EMAIL`
- `MAX_UPLOAD_SIZE` / `ALLOWED_EXTENSIONS`

生产环境：`DEBUG=false`、PostgreSQL、Redis、强 `SECRET_KEY`、显式 `CORS_ORIGINS`、`TrustedHostMiddleware` 生效。

## Database Migration

修改 `backend/models/` 下的模型后：

```bash
python -m backend.migrations revision -m "描述变更" --autogenerate
# 检查 versions/ 下新生成的文件
python -m backend.migrations upgrade
python -m backend.migrations status
```

迁移文件使用 alembic hash 前缀 + 中文描述命名（如 `b7f2a9d3c4e1_add_activities_table.py`）。`cli.py` 的 `_clear_pycache()` 会在每次命令前清理 `__pycache__` 确保使用最新代码。

## Caching Patterns

```python
# 简单缓存
await cache.set(key, value, ttl=300)
cached = await cache.get(key)

# 装饰器缓存
@cache.cached("posts", ttl=600, key_builder=lambda slug: f"posts:{slug}")
async def get_post(slug: str): ...

# 防穿透
result = await get_or_set_with_null(
    key,
    fetch_func=lambda: db.execute(...),
    ttl=300,
    null_ttl=60,
)

# 失效
await invalidate_cache("posts:*")
```

## Frontend Integration

前端 Astro 项目通过 `frontend/astro.config.mjs` 的 Vite 代理将 `/api/*` 转发到 `http://localhost:8000`（可通过 `API_BASE_URL` 环境变量覆盖）。前端 `src/api/client.ts` 使用 `ROSETTA_API_BASE` 环境变量或默认 `http://localhost:8000/api`。动态配置通过 `/api/config` 端点加载，含音乐播放器、壁纸、Bing 壁纸等设置。
