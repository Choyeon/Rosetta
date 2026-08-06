# Repository Guidelines

## Project Structure & Module Organization

ROSETTA 后端是基于 **FastAPI** 的异步 Python 博客 API 服务，运行在 `backend/` 目录下。源码组织如下：

- `backend/main.py` — 应用入口，`create_application()` 组装中间件、异常处理器与路由
- `backend/api/` — 按领域拆分的 API 路由（`blog.py`、`users.py`、`core.py`、`media.py`、`bing.py`、`admin.py`、`oobe.py` 等），每个文件通过 `APIRouter` 挂载到 `/api/*` 前缀
- `backend/core/` — 基础设施层：`config.py`（Pydantic Settings）、`database.py`（SQLAlchemy 2.0 异步引擎）、`auth.py`（JWT + bcrypt）、`cache.py`（Redis/内存双后端缓存）、`i18n.py`、`maintenance.py`、`rate_limit.py`、`distributed_lock.py`
- `backend/models/` — SQLAlchemy ORM 模型（`user.py`、`blog.py`、`core.py`、`voting.py`、`message.py` 等），在 `models/__init__.py` 统一导出
- `backend/schemas/` — Pydantic v2 数据模型，`schemas/__init__.py` 作为 barrel 导出请求/响应模型
- `backend/repositories/` — 数据访问层（`base.py`、`post.py`、`user.py`）
- `backend/services/` — 业务服务层（`post_service.py`、`user_service.py`、`email_service.py`、`recommendation.py`、`cache_service.py`）
- `backend/middleware/` — 自定义中间件（`performance.py`）
- `backend/migrations/` — Alembic 数据库迁移，`cli.py` 提供零配置命令行工具
- `backend/scripts/` — 一次性脚本（`mock_data.py`）
- `backend/docs/` — API 参考文档与错误码定义
- `backend/utils/compat.py` — Python 版本兼容层（UTC、timedelta）

## Build, Test, and Development Commands

包管理统一使用 `uv`，依赖定义在项目根目录的 `pyproject.toml`，锁文件为 `uv.lock`（单一事实来源）。

- `uv sync`：根据 `uv.lock` 创建/更新 `.venv` 并安装全部依赖
- `uv sync --frozen --no-dev`：生产部署时仅安装运行时依赖（不更新锁文件）
- `uv run uvicorn backend.main:app --reload --port 8000`：启动开发服务器（从项目根目录运行）
- `uv run uvicorn backend.main:app --host 0.0.0.0 --port 8000`：启动生产服务器
- `uv run python -m backend.migrations upgrade`：升级数据库到最新版本
- `uv run python -m backend.migrations upgrade head`：同上
- `uv run python -m backend.migrations downgrade -1`：回退一个版本
- `uv run python -m backend.migrations revision -m "描述" --autogenerate`：自动生成迁移
- `uv run python -m backend.migrations current`：查看当前数据库版本
- `uv run python -m backend.migrations history`：查看迁移历史
- `uv run python -m backend.migrations status`：查看数据库状态
- `uv run python -m backend.migrations init`：初始化数据库（创建所有表）
- `uv run python -m backend.migrations reset --force`：重置数据库（危险操作）
- `uv run python -m backend.scripts.mock_data`：生成测试数据

访问 `http://localhost:8000/docs` 查看 Swagger 文档（仅 `DEBUG=true` 时开启），`/health` 查看健康检查，`/redoc` 查看 ReDoc 文档。

## Coding Style & Naming Conventions

- **Python 版本**：3.11+，使用 PEP 604 类型联合语法（`str | None`）与 `from __future__ import annotations` 风格的延迟注解
- **缩进**：4 个空格（PEP 8）
- **字符串**：双引号优先
- **导入顺序**：标准库 → 第三方 → 本地模块，每组之间空一行
- **模块命名**：`snake_case.py`
- **类命名**：`PascalCase`（如 `SiteConfigResponse`、`UserController`）
- **函数与变量**：`snake_case`
- **常量**：`UPPER_SNAKE_CASE`（如 `CACHE_TTL`、`NULL_MARKER`）
- **Pydantic 模型**：使用 `Field(...)` 显式声明描述与约束，`model_config = {"from_attributes": True}` 启用 ORM 模式
- **SQLAlchemy 模型**：使用 `DeclarativeBase` + `Mapped[T]` + `mapped_column()` 现代风格
- **API 路由**：每个端点必须包含 `summary` 和 `description` 参数，使用 `response_model` 显式声明响应类型
- **依赖注入**：使用 `Annotated[T, Depends(...)]` 风格（如 `DB = Annotated[AsyncSession, Depends(get_db)]`）
- **异步**：所有数据库操作和 I/O 必须使用 `async`/`await`
- **文档字符串**：模块、类、公共函数必须包含三引号 docstring，描述用途、参数和返回值
- **类型注解**：所有函数签名必须包含完整类型注解

## Testing Guidelines

当前未配置单元测试框架。在提交前：

1. 运行 `python -c "from backend.main import app"` 验证应用可正常导入
2. 启动 `uvicorn backend.main:app --reload` 访问 `/docs` 确认所有路由加载
3. 调用 `/health` 端点确认数据库连接正常
4. 对涉及数据库变更的改动，运行 `python -m backend.migrations status` 确认迁移版本一致

未来添加测试时，使用 `pytest` + `pytest-asyncio` + `httpx.AsyncClient`，测试文件放在 `backend/tests/` 下，命名 `test_*.py`。

## Commit & Pull Request Guidelines

使用 **Conventional Commits**，与现有历史保持一致：

- `feat: 添加文章定时发布功能`
- `fix: 修复用户登录时 token 过期判断`
- `chore: 升级 SQLAlchemy 依赖版本`
- `docs: 更新 API 参考文档`
- `refactor: 重构缓存层支持 Redis 集群`
- `perf: 优化文章列表查询 N+1 问题`

提交和 PR 应聚焦于单一关注点。PR 需包含：简洁摘要、关联的 issue、已运行的验证命令、数据库迁移说明（若涉及 schema 变更）。重大架构调整需先在 issue 或 discussion 中讨论。

## Security & Configuration Tips

- **密钥管理**：`SECRET_KEY` 在生产环境必须替换为至少 32 字符的强密钥，通过环境变量或 `.env` 文件注入，禁止硬编码或提交到仓库
- **环境隔离**：`.env` 文件不入版本控制，参考 `.env.example` 创建本地配置
- **数据库 URL**：生产环境使用 `postgresql+asyncpg://`，开发环境默认 `sqlite+aiosqlite:///./rosetta.db`
- **CORS 配置**：生产环境通过 `CORS_ORIGINS` 显式列出允许的前端域名，开发环境自动放行所有来源
- **JWT 认证**：使用 `HTTPBearer` 方案，access token 1 小时过期，refresh token 7 天过期
- **密码哈希**：bcrypt 算法，超过 72 字节的密码先 SHA-256 再 bcrypt
- **文件上传**：限制 `MAX_UPLOAD_SIZE`（默认 10MB）与 `ALLOWED_EXTENSIONS`，媒体文件存放在 `media/` 目录
- **调试模式**：`DEBUG=true` 时开启 `/docs`、`/redoc`、`/openapi.json` 与详细错误信息，生产环境必须关闭
- **维护模式**：通过 `MaintenanceMiddleware` 控制，可在不停止服务的情况下拒绝写入请求
- **敏感信息**：`SiteConfigResponse` 等响应模型不返回邮件密码、密钥等敏感字段，仅返回 `email_configured: bool` 等状态位
- **OOBE 流程**：首次启动通过 `.oobe_complete` 锁文件与 `rosetta.json` 配置文件标记完成状态，未完成时跳过数据库初始化

## Database Migration Workflow

1. 修改 `backend/models/` 下的 SQLAlchemy 模型
2. 运行 `python -m backend.migrations revision -m "描述变更" --autogenerate`
3. 检查 `backend/migrations/versions/` 下新生成的迁移文件，确认 `upgrade()` 与 `downgrade()` 函数正确
4. 运行 `python -m backend.migrations upgrade` 应用迁移
5. 验证 `python -m backend.migrations status` 显示版本一致

迁移文件命名使用 `alembic` 默认的 hash 前缀 + 描述格式，中文描述可直接用于文件名（如 `5182cb36811d_添加_webhook_收藏_验证码_修订版本等表.py`）。
