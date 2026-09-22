# Rosetta 后端开发规范

FastAPI + SQLAlchemy 2.0 async + Pydantic v2 + Alembic。所有命令从**项目根目录**执行。

> 跨域规则（SSR 策略、BaseURL、API 契约）见根 `AGENTS.md`。本文档聚焦后端编码细节。

## 运行环境

- Python 3.10+（`pyproject.toml: requires-python = ">=3.10"`）
- 包管理：`uv`，依赖声明根目录 `pyproject.toml`
- ASGI：Uvicorn，端口 8000
- 数据库：开发默认 SQLite（aiosqlite），生产推荐 PostgreSQL（asyncpg）
- Redis：可选缓存后端（开发 fallback 到内存）

## 目录与分层

```
backend/
├── main.py                 create_application() 组装中间件/路由/异常
├── api/                    41 个 API 模块（activity … webhook），每个模块一个 APIRouter
├── core/                   基础设施层（禁止反向依赖 api/）
│   ├── config.py           Settings（Pydantic Settings + .env）
│   ├── database.py         引擎 / 会话 / 连接池（async）
│   ├── auth.py             JWT 签发 / 校验 / Annotated 依赖别名（CurrentUser / CurrentStaff / DB）
│   ├── cache.py / cache_v2.py / cache_warmer.py  双后端缓存 + 预热
│   ├── exceptions.py       AppException + 统一错误码
│   ├── csrf.py / rate_limit.py / distributed_lock.py
│   ├── maintenance.py      维护模式中间件
│   ├── manifest_scanner.py 插件/主题清单扫描
│   ├── plugin_bus.py / plugin_loader.py  插件钩子引擎
│   ├── site_config.py      SiteConfig 运行时配置
│   ├── i18n.py             contextvars 多语言
│   ├── xss_filter.py / net_guard.py / password_policy.py
│   └── setup_*.py          OOBE 初始化助手
├── models/                 SQLAlchemy 2.0 DeclarativeBase
│   ├── blog.py / user.py / gallery.py / site.py / activity.py …
├── schemas/                Pydantic v2 请求/响应模型 + i18n dict 工厂
├── repositories/           数据访问层（base / post / user）
├── services/               业务层
│   ├── post_service.py / user_service.py / comment_service.py
│   ├── guestbook_service.py / media_service.py / email_service.py
│   ├── avatar_resolver.py + _avatar_helpers.py  统一头像解析
│   ├── recommendation.py   TF-IDF / Jaccard / BM25 推荐
│   ├── content_type_service.py / cache_service.py
│   └── __init__.py
├── migrations/             Alembic（cli.py / env.py / config.py）
├── plugins/                hello-rosetta / guestbook-rss / seo-toolkit
├── scripts/                mock_data / auto_oobe / reset_admin_password …
└── data/                   四语 seed_content + 市场缓存
```

调用方向（必须单向）：
```
api → services → repositories → models
          ↘        ↓
           ↘   schemas（所有层可引用）
            ↘
          core（各层可引用，禁止反向依赖 api）
```

## 头像链路

**入口**：`avatar_resolver.resolve(AvatarInput)` → 统一出口。`comment_service` / `guestbook_service` 已全部改为调用 avatar_resolver。

**默认镜像**：`https://cravatar.cn/avatar`（国内速度最快）。通过 `GRAVATAR_CDN_BASE` 环境变量或站点设置覆盖。

**白名单**（`avatar_proxy.py` `_ALLOWED_HOST_SUFFIXES`）：gravatar.com / cravatar.cn / gravatar.cat.net / gravatar.loli.net / geekzu.org / v2ex.com / github.com / dicebear.com / dicebear.me / qlogo.cn / qpic.cn / wp.com。

**SSRF 防护**：私有 IP / 回环 / IANA 保留域一律跳过代理。

## 站点设置

`/api/settings` 支持 17 个分组（`settings_groups.py` 的 `GROUPS` 数组）。

| 端点 | 鉴权 | 返回内容 |
|------|------|---------|
| `GET /api/settings` | 需管理员（`CurrentStaff`） | 全部 17 组，含敏感明文值 |
| `GET /api/settings/{group}` | 需管理员 | 单组原文 |
| `PATCH /api/settings/{group}` | 需管理员 | 写日志 + 失效公开缓存 |
| `GET /api/settings/public` | **无鉴权** | `PUBLIC_SETTING_GROUPS` 白名单，敏感值替换为 `******` |

> ⚠️ 前台/SSR 只能调 `GET /api/settings/public`。新增可公开字段先加进 `PUBLIC_SETTING_GROUPS`，不要放宽 `/api/settings` 鉴权。

## 生命周期与 OOBE

`backend/main.py` 的 `lifespan`：
1. 检查 `.oobe_complete` 锁文件
2. 未完成 → 跳过 DB 初始化 + 定时循环，仅暴露 OOBE 必需接口
3. 已完成 → `init_db()` → `check_db_connection()` → 启动定时发布循环
4. 关闭 → 取消后台任务 → 关闭 DB 连接池 → 关闭缓存

`oobe_middleware`：OOBE 未完成且路径 `/api/*` 非白名单 → 503 + `error_code: OOBE_REQUIRED`。

## 编码规范

- 4 空格缩进，双引号字符串，ruff line-length=100
- 模块 / 公共类 / 公共函数必须有三引号 docstring
- 导入顺序：标准库 → 第三方 → 本项目

### 类型注解

```python
async def list_posts(
    db: DB,
    *,
    page: int = 1,
    per_page: int = 10,
    category_id: int | None = None,
) -> tuple[list[Post], int]: ...
```

### 依赖注入（Annotated 形式）

```python
from backend.core.auth import CurrentUser, CurrentStaff, DB
from backend.core.deps import PageParams

async def handler(
    user: CurrentUser,      # 必须登录
    staff: CurrentStaff,    # 必须管理员
    db: DB,                 # AsyncSession
    page: PageParams,       # 分页依赖
): ...
```

### API 路由

```python
@router.get(
    "/posts/{slug}",
    summary="获取文章详情",
    response_model=PostDetailResponse,
)
async def get_post(slug: str, db: DB) -> PostDetailResponse: ...
```

每个路由文件只用 `APIRouter()`，在 `main.py` 的 `create_application()` 中统一 `include_router`。

### SQLAlchemy 模型

```python
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

class Base(DeclarativeBase):
    pass

class Post(Base):
    __tablename__ = "posts"
    id: Mapped[int] = mapped_column(primary_key=True)
    slug: Mapped[str] = mapped_column(unique=True, index=True)
    title_i18n: Mapped[dict[str, str]] = mapped_column(JSON, default=dict)
```

避免 `backref`，用显式 `relationship(back_populates=...)`。JSON 字段用 `MutableList/MutableDict` 变更追踪。

### Pydantic v2

```python
from pydantic import BaseModel, Field, ConfigDict

class PostCreate(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    slug: str = Field(..., min_length=1, max_length=200)
    title_i18n: dict[str, str] = Field(default_factory=dict)
```

### 缓存

```python
await cache.set("posts:1", data, ttl=600)
data = await cache.get("posts:1")

@cache.cached("posts", ttl=600, key_builder=lambda slug: f"posts:{slug}")
async def get_post_detail(slug: str): ...
```

TTL 统一参考 `CACHE_TTL` 字典，不硬编码数字。

### 异常

```python
from backend.core.exceptions import AppException

raise AppException(
    status_code=404,
    error_code=POST_NOT_FOUND,
    message="文章不存在或已下架",
)
```

通用 HTTP 错误用 `HTTPException`，语义错误一律走 `AppException`（保证前端获得稳定 `error_code`）。

### 重要：flush 后必须 refresh

新建/更新接口中，`db.flush()` 后**必须**立刻 `await db.refresh(entity)`，否则 SQLAlchemy 返回的 JSON 字段仍是字符串，前端 I18nTabsEditor 直接崩溃。

## 数据库迁移

```bash
uv run python -m backend.migrations status
uv run python -m backend.migrations upgrade
uv run python -m backend.migrations revision -m "描述" --autogenerate
```

**务必人工检查** upgrade / downgrade。如果 autogenerate 生成 "drop all tables"，**立即删除该版本文件**，检查 `env.py` 的 `target_metadata` 是否漏 import 新 model。

## 安全清单

- `SECRET_KEY` 生产必须 ≥32 字节随机串，环境变量注入
- `DEBUG=false` 时 `/docs` / `/redoc` / `/openapi.json` 全部关闭
- `CORS_ORIGINS` 生产仅列明确域名
- 密码 bcrypt 哈希，超过 72 字节先 SHA-256 再 bcrypt
- 文件上传受 `MAX_UPLOAD_SIZE` + `ALLOWED_EXTENSIONS` 双重约束
- 敏感 SMTP 密码以 `email_configured: bool` 暴露，不回传明文
- 生产启用 `TrustedHostMiddleware`

## 测试

pytest + pytest-asyncio + httpx.AsyncClient。测试文件在根 `tests/`，命名 `test_*.py`。

```bash
uv run pytest tests/ -v
```

不依赖线上服务 / 外部网络；fixture 在 `tests/conftest.py`。

## 提交前检查

```bash
uv run python -c "from backend.main import app"
uv run python -m backend.migrations status
uv run ruff check backend tests
```

访问 `/health` → healthy；`/docs`（DEBUG=true）列出路由。
