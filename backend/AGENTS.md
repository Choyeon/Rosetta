# Rosetta 后端开发规范

FastAPI + SQLAlchemy 2.0 async + Pydantic v2 + Alembic。所有命令从**项目根目录**执行。

## 运行环境

- Python 3.11+（PEP 604 `str | None` + `from __future__ import annotations`）
- 包管理：`uv`，依赖声明根目录 `pyproject.toml`
- ASGI：Uvicorn，端口 8000
- 数据库：开发默认 SQLite（aiosqlite），生产推荐 PostgreSQL（asyncpg）
- Redis：可选缓存后端（开发 fallback 到内存）

## 目录与分层

```
backend/
├── main.py                 create_application() 组装中间件/路由/异常
├── api/                    路由层（每个模块一个 APIRouter，不实例化 FastAPI）
│   ├── users.py            /api/users（注册/登录/refresh/logout）
│   ├── blog.py             /api/blog（文章/分类/标签/评论/点赞/草稿）
│   ├── comments.py         /api/comments（嵌套评论/审核）
│   ├── guestbook.py        /api/guestbook（留言板）
│   ├── admin.py            /api/admin（仪表盘/统计/审核）
│   ├── oobe.py             OOBE 安装流程（白名单，不受 OOBE 中间件阻断）
│   ├── media.py            文件上传
│   ├── avatar_proxy.py     /api/media/avatar（白名单域名直跳 + 非白名单流式代理 + DiceBear fallback）
│   ├── plugins.py         /api/plugins（列表/安装/激活/停用/卸载）
│   ├── themes.py           /api/themes（列表/激活/上传/设置 Mods）
│   ├── settings_groups.py  /api/settings（17 个分组：basic/appearance/security/features/comments/media/reading ...）
│   └── nav/ 或其他领域模块
├── core/                   基础设施层（禁止反向依赖 api/）
│   ├── config.py           Settings（Pydantic Settings + .env）— gravatar_cdn_base 默认 Cravatar（2026-08 实测存活）
│   ├── database.py         引擎 / 会话 / 连接池（async）
│   ├── auth.py             JWT 签发 / 校验 / Annotated 依赖别名（CurrentUser / CurrentStaff / DB / PageParams）
│   ├── cache.py            双后端缓存（生产 Redis / 开发内存），含 cache.cached 装饰器 + CACHE_TTL 字典
│   ├── i18n.py             contextvars 多语言
│   ├── crud.py             通用 CRUD 基类
│   ├── deps.py             get_db / is_oobe_complete / PageParams 等通用依赖
│   ├── exceptions.py       AppException + 统一错误码（POST_NOT_FOUND / INVALID_CREDENTIALS / OOBE_REQUIRED ...）
│   ├── csrf.py / rate_limit.py / distributed_lock.py
│   ├── maintenance.py     维护模式中间件
│   └── setup_*.py          OOBE 初始化助手
├── models/                 SQLAlchemy 2.0 DeclarativeBase
│   ├── user.py / post.py / category.py / tag.py / comment.py / guestbook.py
│   ├── theme.py / plugin.py / site.py
│   └── friendlink.py / activity.py / gallery.py
├── schemas/                Pydantic v2 请求/响应模型
├── repositories/           数据访问层（复杂查询封装）
├── services/               业务层（跨模型编排 + 缓存策略）
│   ├── avatar_resolver.py  统一头像解析（GitHub / Gravatar / QQ / DiceBear fallback）
│   ├── _avatar_helpers.py  代理包装 + resolved_for_user / resolved_for_comment / resolved_for_guestbook
│   ├── comment_service.py  评论业务（⚠ 旧 _gravatar_base 副本已统一改为 avatar_resolver）
│   ├── guestbook_service.py 留言板业务
│   ├── plugin_engine.py    WP 风格钩子引擎
│   ├── plugin_registry.py  插件清单扫描
│   ├── theme_manager.py    主题激活 / deactivate / Mods
│   ├── settings_service.py 站点设置读写（SiteConfig 表）
│   ├── media_service.py    媒体处理
│   ├── post_service.py     文章 CRUD + 发布定时
│   └── cache_service.py    缓存管理接口
├── migrations/             Alembic
│   ├── cli.py              零配置 CLI
│   └── versions/           每版本一个文件（当前 head 87a2ae42cf45）
└── scripts/
    └── mock_data.py        开发/OOBE mock 数据入口（幂等 + 异常降级）
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

**入口**：`avatar_resolver.resolve(AvatarInput)` → 统一出口。`comment_service` / `guestbook_service` 历史版本各有独立 `_gravatar_base()` 副本，**已全部同步改为调用 avatar_resolver**。

**默认镜像**：`https://cravatar.cn/avatar`（2026-08 实测存活、国内速度最快）。通过 `GRAVATAR_CDN_BASE` 环境变量或站点设置 → 基本配置覆盖。

**可用镜像清单**（2026-08 实测）：
| 镜像 | 存活 | 速度 |
|------|------|------|
| cravatar.cn | ✅ | 快 |
| gravatar.cat.net | ✅ | 快 |
| gravatar.loli.net | ✅ | 中 |
| sdn.geekzu.org | ⚠ | 偶发超时 |
| www.gravatar.com | ❌ | 国内常超时 |

**前端展示**：`composables/useAvatar.ts` 读取 `user.avatar_source` → 调 `/api/media/avatar?src=<b64>`。白名单域名返回 307 直跳（省带宽 + 浏览器缓存友好）；非白名单走服务端流式代理 + 错误兜底。

**白名单**（`avatar_proxy.py` `_ALLOWED_HOST_SUFFIXES`）：gravatar.com / cravatar.cn / gravatar.cat.net / gravatar.loli.net / geekzu.org / v2ex.com / github.com / dicebear.com / dicebear.me / qlogo.cn / qpic.cn / wp.com。

**SSRF 防护**：私有 IP / 回环 / IANA 保留域一律跳过代理，避免把内网请求暴露给前端。

## 站点设置

`/api/settings` 支持 17 个分组（`settings_groups.py` 的 `GROUPS` 数组）：

| Group | 字段示例 |
|-------|---------|
| basic | site_name / site_description / site_url / timezone / language |
| appearance | primary_color / accent_color / default_theme / code_theme / page_width_px |
| security | registration_open / login_rate_limit / max_login_attempts |
| comments | anonymous_allowed / require_email / moderation / notify_admin |
| media | max_upload_size / allowed_extensions / use_cdn / cdn_prefix |
| reading | posts_per_page / excerpt_length / show_toc |
| features | enable_search / enable_rss / enable_guestbook / enable_friendlinks |
| email | smtp_host / smtp_port / email_configured（敏感字段不回传明文） |
| cache | cache_ttl / redis_enabled |
| oobe | 只读 |
| ... | 其余 |

持久化：`SiteConfig` 表（`site_configs`），key-value + JSON blob。加载时与默认值合并，保存时只写入 `GROUPS` 中定义过的字段。

## 生命周期与 OOBE

`backend/main.py` 的 `lifespan`：
1. 检查 `.oobe_complete` 锁文件 + `rosetta.json`
2. 未完成 → 跳过 DB 初始化 + 定时循环，仅暴露 OOBE 必需接口
3. 已完成 → `init_db()` → `check_db_connection()` → 启动定时发布循环
4. 关闭 → 取消后台任务 → 关闭 DB 连接池 → 关闭缓存

`oobe_middleware`：OOBE 未完成且路径 `/api/*` 非白名单 → 503 + `error_code: OOBE_REQUIRED`；OOBE 已完成且访问 `/oobe` → 302 `/`。

## 编码规范

- 4 空格缩进，双引号字符串，PEP 8 行宽 ~100（不强制 79）
- 模块 / 公共类 / 公共函数必须有三引号 docstring
- 导入顺序三组空行：标准库 → 第三方 → 本项目

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
    user: CurrentUser,       # 必须登录
    staff: CurrentStaff,     # 必须管理员
    db: DB,                  # AsyncSession
    page: PageParams,        # 分页依赖
): ...
```

### API 路由
```python
@router.get(
    "/posts/{slug}",
    summary="获取文章详情",
    description="根据 slug 返回公开文章；加密文章需密码。",
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
    created_at: Mapped[datetime] = mapped_column(default=lambda: datetime.now(UTC))
```
避免 `backref`，用显式 `relationship(back_populates=...)`。

### Pydantic v2
```python
from pydantic import BaseModel, Field, ConfigDict

class PostCreate(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    slug: str = Field(..., min_length=1, max_length=200, description="URL 友好标识符")
    title_i18n: dict[str, str] = Field(default_factory=dict)
```

### 缓存
```python
await cache.set("posts:1", data, ttl=600)
data = await cache.get("posts:1")

@cache.cached("posts", ttl=600, key_builder=lambda slug: f"posts:{slug}")
async def get_post_detail(slug: str): ...

# 防穿透空值缓存
result = await get_or_set_with_null(key, fetch_func, ttl=300, null_ttl=60)
await invalidate_cache("posts:*")
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

## 数据库迁移

```bash
uv run python -m backend.migrations revision -m "描述" --autogenerate
uv run python -m backend.migrations upgrade
uv run python -m backend.migrations status    # 版本 == head？
```
**务必人工检查** upgrade / downgrade 是否符合预期（Alembic autogenerate 对索引/重命名不完美）。

## 安全清单

- `SECRET_KEY` 生产必须替换为 ≥32 字节随机串，环境变量注入
- `DEBUG=false` 时 `/docs` / `/redoc` / `/openapi.json` 全部关闭
- `CORS_ORIGINS` 生产仅列明确域名（JSON 数组）
- 密码 bcrypt 哈希，超过 72 字节先 SHA-256 再 bcrypt
- 文件上传受 `MAX_UPLOAD_SIZE` + `ALLOWED_EXTENSIONS` 双重约束
- 敏感 SMTP 密码等在 SiteConfig 响应中以 `email_configured: bool` 暴露，不回传明文
- 生产启用 `TrustedHostMiddleware`，按 `SITE_URL` 校验 Host

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
```
访问 `/health` → healthy；`/docs`（DEBUG=true）列出路由。
