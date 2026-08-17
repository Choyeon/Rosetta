# Rosetta 后端速查

详细规范见 [backend/AGENTS.md](file:///d:/WebProjects/Rosetta/backend/AGENTS.md)。本文件聚焦 AI 助手最常需要的入口与命令。

## 工程信息

- 语言/版本：Python 3.11+
- 框架：FastAPI + SQLAlchemy 2.0 async + Pydantic v2
- 包管理：`uv`（根目录 `pyproject.toml` + `uv.lock`）
- 迁移：Alembic（封装在 `backend.migrations.cli`）
- 测试：pytest + pytest-asyncio，文件位于 `tests/test_*.py`

## 关键文件

| 内容 | 路径 |
|------|------|
| 应用入口 / 中间件 / 路由装配 / 异常处理器 | `backend/main.py` |
| Settings（环境变量，lru_cache 单例） | `backend/core/config.py` |
| 引擎 & 会话 & `init_db` / `check_db_connection` / `close_db` | `backend/core/database.py` |
| JWT 签发、hash、依赖别名 `CurrentUser / CurrentStaff / DB` | `backend/core/auth.py` |
| 双后端缓存（Redis/Memory）与 `cached` 装饰器 | `backend/core/cache.py` |
| `AppException` + 错误码常量（`POST_NOT_FOUND` 等） | `backend/core/exceptions.py` |
| OOBE 完成判定、通用依赖（分页等） | `backend/core/deps.py` |
| 通用 CRUD 基类 | `backend/core/crud.py` |
| SiteConfig（音乐/壁纸等运行时配置） | `backend/core/site_config.py` |
| i18n 中间件：parse_accept_language + contextvars | `backend/core/i18n.py` |
| Base Model 导出 | `backend/models/__init__.py` |
| 用户/角色模型 | `backend/models/user.py` |
| 文章/分类/标签/评论/系列 模型 | `backend/models/blog.py` |
| 其余：log / voting / message / gallery / hero / monitoring / activity / guestbook / post_series / comment_reaction / revision | `backend/models/*.py` |
| Pydantic 模型 barrel 导出 | `backend/schemas/__init__.py` |
| 数据访问层（Repository） | `backend/repositories/base.py` / `post.py` / `user.py` |
| 业务逻辑层：Post/User/Email/Cache/Recommendation | `backend/services/*.py` |
| 所有路由模块 | `backend/api/*.py` |
| 迁移版本目录 | `backend/migrations/versions/` |
| 前端可复用的 TS 类型定义 | `backend/docs/types.ts` |
| 错误码说明 | `backend/docs/error_codes.md` |

## 命令（从项目根目录执行）

```bash
# 依赖
uv sync                                       # 根据 uv.lock 创建/同步 .venv
uv sync --frozen --no-dev                     # 生产部署（只装运行时依赖）

# 启动
uv run uvicorn backend.main:app --reload --port 8000      # 开发
uv run uvicorn backend.main:app --host 0.0.0.0 --port 8000   # 生产

# 迁移
uv run python -m backend.migrations upgrade                # 升级到 head
uv run python -m backend.migrations downgrade -1           # 回退一版
uv run python -m backend.migrations revision -m "msg" --autogenerate
uv run python -m backend.migrations init                   # 首次初始化（全部建表 + 标记 head）
uv run python -m backend.migrations reset --force          # 清空重建（危险）
uv run python -m backend.migrations status                 # 版本校验

# 脚本
uv run python -m backend.scripts.mock_data                 # 写入示例数据

# 校验（提交前必跑）
uv run python -c "from backend.main import app"
uv run python -m backend.migrations status
```

## 路由前缀总览

在 `main.py` 的 `create_application()` 中注册：

| Router | 前缀 |
|--------|------|
| users | `/api/users` |
| blog | `/api/blog` |
| core | `/api` |
| media | `/api/media` |
| admin | `/api/admin`（含 stats / performance / admin_logs / migration / import_export / title） |
| monitoring | `/api/monitoring` |
| gallery（公开） | `/api` |
| gallery（管理） | `/api` |
| 其余：guestbook / voting / notifications / favorites / webhook / seo / advanced / toc / captcha / messages / translate / oobe / announcement / activity / hero / post_series / post_encryption / post_crypto / scheduled_posts / comment_reactions / ranking / settings_groups / bing / comments / avatar_proxy | `/api` 或各自前缀 |

静态媒体挂载：`/media → media/`（应用内创建）。

## 中间件顺序（main.py）

1. `CORSMiddleware`
2. `SecurityHeadersMiddleware`
3. `MaintenanceMiddleware`
4. 生产环境加 `TrustedHostMiddleware`
5. i18n context（`Accept-Language` → `I18nContext`）
6. OOBE 状态守卫（未完成时 503）
7. Request 日志 + `record_visit`
8. 性能采样 `performance_middleware`

## 响应结构与常见错误码

成功：`{ success: true, data: T?, message?: str }`

失败：`{ success: false, error_code: str|int, message: str, errors?: [{field, message, type}] }`

常用错误码（见 `backend/core/exceptions.py`）：
- `UNAUTHORIZED` 401 — 未登录或 token 失效
- `FORBIDDEN` 403 — 无权限
- `NOT_FOUND` 404
- `VALIDATION_ERROR` 422 — 表单字段校验失败，附带 `errors` 数组
- `OOBE_REQUIRED` 503 — 未完成安装
- `RATE_LIMITED` 429
- `MAINTENANCE_MODE` 503

## 编码模板

端点写法：

```python
from fastapi import APIRouter, Depends
from backend.core.auth import CurrentUser, DB

router = APIRouter()

@router.get(
    "/ping",
    summary="健康测试",
    description="返回 pong，用于心跳。",
    response_model=dict[str, str],
)
async def ping(user: CurrentUser, db: DB) -> dict[str, str]:
    return {"message": "pong"}
```

异常：

```python
from backend.core.exceptions import AppException, POST_NOT_FOUND

raise AppException(status_code=404, error_code=POST_NOT_FOUND, message="文章不存在")
```

## 典型坑

- OOBE 未完成时 `lifespan` 跳过 DB 初始化；不要对数据库相关接口抓不到表就以为迁移挂了。
- SQLite + 异步连接下默认池为 `NullPool`，不要假设会话间共享状态；生产 PostgreSQL 使用 `AsyncAdaptedQueuePool` + `pool_pre_ping`。
- Alembic autogenerate 对 JSON 字段、部分 index 重命名、枚举变更不严谨；每次生成后必须打开迁移文件人工核对。
- 缓存层对 `None` 也会缓存（防穿透）。当数据源返回值语义变更时，记得显式 `invalidate_cache("pattern:*")`。
- JWT access token 1h、refresh token 7d（`ACCESS_TOKEN_EXPIRE_MINUTES` / `REFRESH_TOKEN_EXPIRE_DAYS` 可配置）。
- 密码长度超过 72 字节时先 SHA-256 再 bcrypt，避免被截断。
