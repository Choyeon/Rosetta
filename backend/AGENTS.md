# Rosetta 后端开发规范

后端基于 FastAPI + SQLAlchemy 2.0 async 构建，采用分层架构。所有命令从**项目根目录**执行，不要进入 `backend/` 子目录执行。

## 运行环境

- Python 3.11+（使用 PEP 604 语法 `str | None` 与 `from __future__ import annotations`）
- 包管理：`uv`，依赖声明在根目录 `pyproject.toml`，锁文件 `uv.lock`
- ASGI 服务器：Uvicorn
- 生产推荐数据库：PostgreSQL（asyncpg 驱动）；开发默认 SQLite（aiosqlite）

## 目录与分层

```
backend/
├── main.py                 应用入口，create_application() 组装中间件/路由/异常处理
├── api/                    路由层（每个模块一个 APIRouter）
│   ├── users.py            /api/users
│   ├── blog.py             /api/blog（文章/分类/标签/评论）
│   ├── admin.py            /api/admin
│   ├── oobe.py             OOBE 安装流程
│   ├── media.py            文件上传
│   └── ...                 其余领域模块
├── core/                   基础设施
│   ├── config.py           Settings（Pydantic Settings + .env）
│   ├── database.py         引擎、会话、连接池
│   ├── auth.py             JWT 签发/校验、依赖注入别名
│   ├── cache.py            Redis/Memory 双后端缓存
│   ├── i18n.py             多语言上下文（contextvars）
│   ├── crud.py             通用 CRUD 基类
│   ├── deps.py             通用依赖（get_db、is_oobe_complete 等）
│   ├── exceptions.py       AppException + 统一错误码
│   ├── csrf.py / rate_limit.py / distributed_lock.py
│   ├── maintenance.py      维护模式中间件
│   └── setup_*.py          OOBE 阶段初始化助手
├── models/                 SQLAlchemy 2.0 DeclarativeBase 模型
├── schemas/                Pydantic v2 请求/响应模型
├── repositories/           数据访问层（复杂查询封装）
├── services/               业务服务层（跨模型编排、缓存策略）
├── middleware/             FastAPI HTTP 中间件（性能采样等）
├── migrations/             Alembic 数据库迁移
│   ├── cli.py              零配置 CLI 入口
│   └── versions/           每一个迁移脚本
├── scripts/                一次性脚本（mock_data.py 等）
├── docs/                   api_reference.md、error_codes.md、types.ts
└── utils/compat.py         标准库版本兼容（UTC 等）
```

调用方向必须单向：

```
api → services → repositories → models
          ↘        ↓
           ↘   schemas（所有层都可引用）
            ↘
          core（基础设置层，各层可引用，但禁止反向依赖 api）
```

禁止在 `core/` 或 `models/` 中 `import backend.api.*`。

## 生命周期与 OOBE

应用生命周期定义在 `backend/main.py` 的 `lifespan`：

1. 检查 `.oobe_complete` 锁文件与 `rosetta.json` 是否存在
2. 未完成 → 跳过 DB 初始化与定时发布循环，仅暴露 OOBE 必需接口
3. 已完成 → `init_db()` → `check_db_connection()` → 启动 `_scheduled_publish_loop` 后台任务
4. 关闭 → 取消后台任务 → 关闭 DB 连接池 → 关闭缓存后端

`oobe_middleware`（`main.py` 内）在请求层执行：
- OOBE 未完成且路径为 `/api/*` 非白名单 → 返回 503 + `OOBE_REQUIRED`
- OOBE 已完成且用户访问 `/oobe` → 302 重定向到 `/`

## 编码规范

### 通用

- 4 空格缩进，双引号字符串，PEP 8 行宽 100 字符左右（不强制 79）。
- 模块、公共类、公共函数必须包含三引号 docstring。
- 导入顺序按三组空行分隔：标准库 → 第三方 → 本项目模块。

### 类型注解

所有函数签名必须完整注解：

```python
async def list_posts(
    db: DB,
    *,
    page: int = 1,
    per_page: int = 10,
    category_id: int | None = None,
) -> tuple[list[Post], int]: ...
```

`list` / `dict` 使用内置泛型，不导入 `typing.List` / `typing.Dict`。

### 依赖注入

使用 `Annotated` 形式（`backend/core/auth.py` 中定义的别名）：

```python
from backend.core.auth import CurrentUser, CurrentStaff, DB
from backend.core.deps import PageParams

async def handler(
    user: CurrentUser,         # 必须登录，返回 User 模型
    staff: CurrentStaff,       # 必须是管理员
    db: DB,                    # AsyncSession
    page: PageParams,          # 分页参数依赖
): ...
```

### API 路由写法

每个端点必须显式声明 `summary`、`description`、`response_model`：

```python
@router.get(
    "/posts/{slug}",
    summary="获取文章详情",
    description="根据 slug 返回公开文章；如为加密文章需附带密码参数。",
    response_model=PostDetailResponse,
)
async def get_post(slug: str, db: DB) -> PostDetailResponse: ...
```

路由文件内部：不要实例化新的 `FastAPI`，只用 `APIRouter()`，并在 `main.py` 的 `create_application()` 中 `include_router`。

### SQLAlchemy 模型

使用现代 DeclarativeBase 写法：

```python
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

class Base(DeclarativeBase):
    pass

class Post(Base):
    __tablename__ = "posts"

    id: Mapped[int] = mapped_column(primary_key=True)
    slug: Mapped[str] = mapped_column(unique=True, index=True)
    title_i18n: Mapped[dict[str, str]] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(default=lambda: datetime.now(UTC))
```

避免 `backref`，使用显式的 `relationship(back_populates=...)`。

### Pydantic 模型

```python
from pydantic import BaseModel, Field, ConfigDict

class PostCreate(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    slug: str = Field(..., min_length=1, max_length=200, description="URL 友好标识符")
    title_i18n: dict[str, str] = Field(default_factory=dict, description="多语言标题 {zh,en,ja,zh_Hant}")
```

`from_attributes = True` 用于直接把 ORM 对象转成响应模型。

### 缓存

`backend/core/cache.py` 提供双后端（生产 Redis / 开发内存），统一使用：

```python
await cache.set("posts:1", data, ttl=600)
data = await cache.get("posts:1")

# 装饰器模式
@cache.cached("posts", ttl=600, key_builder=lambda slug: f"posts:{slug}")
async def get_post_detail(slug: str): ...

# 防穿透空值缓存
result = await get_or_set_with_null(
    key,
    fetch_func=lambda: db.execute(query),
    ttl=300,
    null_ttl=60,
)

# 批量失效
await invalidate_cache("posts:*")
```

TTL 参考 `CACHE_TTL` 字典，不要在业务代码硬编码数字。

### 异常与错误码

优先使用 `backend/core/exceptions.py` 中的 `AppException`：

```python
raise AppException(
    status_code=404,
    error_code=POST_NOT_FOUND,
    message="文章不存在或已下架",
)
```

通用 HTTP 错误用 `HTTPException`，但语义错误一律走 `AppException`，以保证前端获得稳定的 `error_code` 字段。

### i18n（后端）

- 中间件根据 `Accept-Language` 在 `contextvars` 设置当前语言（zh / en / ja / zh_Hant）。
- 模型文本字段以 `dict[str, str]` 存多语言，响应时由 `get_i18n_value(data, I18nContext.language)` 取值。
- 用户可读错误信息（如表单校验失败）使用 `t("validation_error")` 等翻译键，不要直接硬编码中文。

## 数据库迁移

修改 `backend/models/` 中的模型后：

```bash
uv run python -m backend.migrations revision -m "描述内容" --autogenerate
uv run python -m backend.migrations upgrade
uv run python -m backend.migrations status    # 确认版本 == head
```

生成的迁移文件位于 `backend/migrations/versions/`，**务必人工检查 upgrade/downgrade 是否符合预期**，Alembic 的 autogenerate 对部分索引/重命名场景不完美。

## 测试

使用 `pytest` + `pytest-asyncio` + `httpx.AsyncClient`。测试文件放在根目录 `tests/`，命名 `test_*.py`。

```bash
pytest tests/test_api_posts.py -v
```

不要依赖线上服务或外部网络连接；fixture 在 `tests/conftest.py` 内准备。

## 安全清单

- `SECRET_KEY` 生产环境必须替换为 ≥32 字节的随机字符串，并通过环境变量注入。
- `DEBUG=false` 时 `/docs`、`/redoc`、`/openapi.json` 全部关闭。
- 生产 `CORS_ORIGINS` 仅列出明确的前端域名列表（字符串 JSON 数组）。
- 密码哈希：bcrypt，密码长度超过 72 字节时先 SHA-256，再 bcrypt。
- 文件上传受 `MAX_UPLOAD_SIZE` 与 `ALLOWED_EXTENSIONS` 双重约束，落盘到根目录 `media/`（已通过 `/media` 静态挂载）。
- 敏感配置（SMTP 密码、密钥等）在 SiteConfig 响应中以 `email_configured: bool` 暴露，不得回传明文。
- 生产启用 `TrustedHostMiddleware`，根据 `SITE_URL` 校验 Host。

## 提交前检查

```bash
uv run python -c "from backend.main import app"
uv run python -m backend.migrations status
```

手动启动服务并访问：
- `/health` 返回 healthy
- `/docs`（DEBUG=true 时）能列出所有路由
- 新增/修改的端点至少用 curl 或 Swagger 调用一次
