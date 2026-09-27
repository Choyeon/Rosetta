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
├── main.py                 create_application() 组装中间件链（由外到内：CORS → SecurityHeaders →
│                           Maintenance → rate_limit → TrustedHost(生产且 OOBE 完成后才启用) →
│                           i18n → oobe → tenant → 请求日志 → performance）+ 路由/异常/OpenAPI 元数据
│                           ⚠️ CSRF 不在中间件链里：core/csrf.py::require_csrf 是 per-route 依赖，
│                           目前仅 POST /api/posts/{id}/comments 显式挂载，且只对携带 Bearer 的请求强制
├── api/                    45 个路由模块（activity … webhook；其中 44 个定义 @router 端点，
│                           gallery.py 导出 public_router + admin_router 两个 APIRouter）
├── core/                   基础设施层（禁止反向依赖 api/）
│   ├── config.py           Settings（Pydantic Settings + .env）
│   ├── database.py         引擎 / 会话 / 连接池（async）
│   ├── auth.py             JWT 签发 / 校验 / Annotated 依赖别名（CurrentUser / CurrentStaff / DB）
│   ├── cache.py / cache_v2.py / cache_warmer.py  双后端缓存 + 预热
│   ├── exceptions.py       AppException + 统一错误码
│   ├── csrf.py / rate_limit.py / distributed_lock.py
│   ├── maintenance.py      维护模式中间件
│   ├── manifest_scanner.py 插件/主题清单扫描
│   ├── plugin_loader.py / plugin_bus.py / hooks.py  插件钩子引擎（loader=生命周期与 settings 快照，
│   │                       bus+hooks=do_action/add_action Bus 原语；不存在 services/plugin_engine.py）
│   ├── extensions.py       PluginManager / ThemeManager / bootstrap_extensions（磁盘↔DB 对齐真源）
│   ├── routing_registry.py 插件路由统一挂载注册表
│   ├── site_config.py      SiteConfig 运行时配置
│   ├── i18n.py             contextvars 多语言
│   ├── xss_filter.py / net_guard.py / password_policy.py
│   └── setup_*.py          OOBE 初始化助手
├── models/                 SQLAlchemy 2.0 DeclarativeBase
│   ├── blog.py / user.py / gallery.py / site.py / activity.py …
├── schemas/                Pydantic v2 请求/响应模型 + i18n dict 工厂
├── repositories/           数据访问层（base / post / user）
├── services/               业务层
│   ├── user_service.py / comment_service.py / guestbook_service.py
│   ├── media_service.py / email_service.py
│   ├── avatar_resolver.py + _avatar_helpers.py  统一头像解析
│   ├── recommendation.py   TF-IDF / Jaccard / BM25 推荐
│   ├── cache_service.py / content_renderer.py / frontend_cache_purge.py
│   └── __init__.py
│                           （文章逻辑走 api/blog.py + repositories/post.py；
│                            post_service / content_type_service 已移除，勿再引用）
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

`/api/settings` 支持 17 个分组（`settings_groups.py` 的 `SETTING_GROUPS_17`；公开白名单为 `PUBLIC_SETTING_GROUPS`，11 组）。

| 端点 | 鉴权 | 返回内容 |
|------|------|---------|
| `GET /api/settings` | 需管理员（`CurrentStaff`） | 全部 17 组，含敏感明文值 |
| `GET /api/settings/{group}` | 需管理员 | 单组原文 |
| `PATCH /api/settings/{group}` | 需管理员 | 写日志 + 失效公开缓存 |
| `GET /api/settings/public` | **无鉴权** | `PUBLIC_SETTING_GROUPS` 白名单，敏感值替换为 `******` |

> ⚠️ 前台/SSR 只能调 `GET /api/settings/public`。新增可公开字段先加进 `PUBLIC_SETTING_GROUPS`，不要放宽 `/api/settings` 鉴权。

## 生命周期与 OOBE

`backend/main.py` 的 `lifespan`：
1. 检查 OOBE：`.oobe_complete` 锁文件与 config 文件同时存在才算完成
2. 未完成 → 跳过 DB 初始化 + 定时循环 + 插件加载，仅暴露 OOBE 必需接口（配 `oobe_middleware` 503 短路）
3. 已完成 → `init_db()` → `check_db_connection()` → 启动定时发布循环 → 启动日志保留循环 →
   `load_plugins(app)` → `bootstrap_extensions(db)`（插件/主题磁盘↔DB 对齐、重放激活、默认激活主题）
4. 关闭 → 取消后台任务 → `unload_plugins(app)` → 关闭 DB 连接池 → 关闭缓存

日志保留循环在 `backend/services/log_retention.py`（`prune_expired_logs`）：按 `LOG_RETENTION_DAYS`
收敛 `visit_logs` / `performance_metrics` / `operation_logs` 三张只写不删的表。删除先 `select(id).limit(n)`
再按 id 删（`DELETE ... LIMIT` 只有 MySQL 支持）。保留窗口会截短"固定窗口"指标，所以
`GET /api/monitoring/visits/summary` 的响应自带 `retention_days` + `data_since`（现存最早日志时间）用来自证口径——
消费方拿到 `month` 时必须对照这两个字段判断它是全量还是下界，契约见 `tests/test_api_monitoring_visits.py`。

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
    user: CurrentUser,  # 必须登录
    staff: CurrentStaff,  # 必须管理员
    db: DB,  # AsyncSession
    page: PageParams,  # 分页依赖
): ...
```

### API 路由

```python
@router.get(
    "/posts/{slug}",
    tags=["博客"],
    summary="获取文章详情",
    description="按 slug 读取已发布文章；未找到时 404（error_code: POST_NOT_FOUND）。",
    response_model=PostDetailResponse,
    responses={404: {"description": "文章不存在（error_code: POST_NOT_FOUND）"}},
)
async def get_post(slug: str, db: DB) -> PostDetailResponse: ...
```

每个路由文件只用 `APIRouter()`，在 `main.py` 的 `create_application()` 中统一 `include_router`。

**OpenAPI 文档自描述基线（2026-09 实测：358 个 operation 全部带中文 summary + description）：**
- 新增端点必须写 `summary=` 与 `description=`（或等价 docstring）：说明鉴权级别
  （`CurrentUser` 登录 / `CurrentStaff` 管理员 / 匿名可访问）、关键参数语义、幂等性、
  触发的插件钩子，以及**实现中真实抛出的** `error_code`——只对齐 AppException/映射表里
  已有的精确码写进 `responses={...}`，不得编造
- 新 tag 必须同步登记 `main.py::TAG_METADATA`，Scalar/Redoc 才有中文分组说明
- `@router.*` 装饰器与 `APIRouter(tags=...)` 只允许改文档字段，不得借改文档动路由路径/模型/状态码/依赖

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

**`model_config` 建类后改赋值是无效的（不报错，也不生效）。** Pydantic v2 在类构造时把 config
编译进 core schema，之后再 `Obj.model_config = {...}` 只改字典不动 schema——本项目曾因此让
**整个 `extra="forbid"` 请求加固层形同虚设**（8 个 schema 文件各自复制一段"赋值 +
`except Exception: pass`"的循环，把失败也一起吞掉，2026-09 才查实）。

规则：需要批量给 schema 施加/变更 config，一律走
`backend/schemas/strict_config.py` 的 `apply_strict_extra_forbid(globals(), __name__)`，
它在赋值后调用 `model_rebuild(force=True)` 才真正生效；前向引用暂不可解析的类会进 `_PENDING`，
由包 `__init__` 末尾的 `finalize_strict_extra_forbid()` 补重建（补不上则 `logger.error`，不静默）。
守卫测试：`tests/test_schema_strict_extra_forbid.py`（含"只赋值必须不生效"的反证用例）。

副作用要当心：`forbid` 一旦真正生效，客户端多传字段就是 **422** 而不是被忽略。改任何请求
schema 的字段集合前，先核对前端对应 payload 的键（admin 侧多为 `useAdminManage.ts` 里的
`xxxBody()` 白名单映射）；反之，response 回显了而 request schema 不接受的字段＝写入静默丢数据
（已发生的实例：`UserDetailResponse` 回显 `qq` / `avatar_source`，`AdminUserUpdateFull` 却没有这两个
字段，管理员改 QQ 不生效）。

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

### 重要：async 会话里禁止触发隐式懒加载

`AsyncSession` 的属性加载只在 greenlet 上下文中可用。以下两种写法都会在读到**未加载**属性时抛
`MissingGreenlet: greenlet_spawn has not been called`，而且异常常被外层 `except Exception` 吞成"业务失败"，
表现为功能静默不可用（历史上 `/admin/import/posts` 带标签的 ZIP 一条都导不进来就是这个原因）：

1. `entity.tags.append(tag)` —— 集合未加载时 append 会先发一条 SELECT；
   改为构造入参 `Model(..., tags=[...])`，或先 `selectinload(Model.tags)` 再整体赋值。
2. `select(Model).where(...)` 后直接访问 `obj.category.name` —— 关系未加载；
   批量读写前显式 `.options(selectinload(...))`，跨字段读取永远靠 eager load 而不是靠"顺手就加载"。

写这类接口时用 `db.refresh(obj)` / `selectinload` 是硬要求；只有 `await` 过的路径才允许触碰惰性属性。

### 重要：已确立的表达式与工具函数用法（不要在旁边另造一套）

| 场景 | 必须 | 禁止 | 为什么 |
| ---- | ---- | ---- | ------ |
| 布尔列取反 | `Model.is_read.is_(False)` | `not Model.is_read`、`Model.is_read == False` | Python 的 `not` 作用在 Column 上得到的是常量 `False`，条件直接消失；`== False` 会被 ruff 判 E712 |
| CASE 表达式 | 顶层 `from sqlalchemy import case` + `case((cond, val), else_=...)` | `func.case(...)` | `func.case` 生成的是**名为 case 的普通 SQL 函数**：不接受 `else_`（TypeError → 500），也带不动裸列 GROUP BY（PG 非法）。见 `backend/api/messages.py:29` |
| 取"当前时间" | `from backend.utils.compat import utc_now_naive` | `datetime.utcnow()`、裸 `datetime.now()` | 库内 `created_at/updated_at` 就是 UTC 朴素值（SQLite `CURRENT_TIMESTAMP`）；用本地时区的 `now()` 会让窗口比对整体偏 8 小时 |
| 密码哈希 | `await aget_password_hash(...)` / `await averify_password(...)` | 同步版 `get_password_hash` / `verify_password` | argon2 是 CPU 密集 KDF，同步调用在事件循环里跑会把整个 API 卡住（登录/注册/OOBE 全受影响）。需要顺带重哈希时用 `averify_password_with_rehash` |
| 连接串里的密码 | `quote(pw, safe="")` | `quote_plus(pw)`、或裸插值 | userinfo 段的 `+` 是字面量加号（空格只代表表单编码规矩），SQLAlchemy 解出来的密码就多了个加号 → 连接认证失败；不编码时密码里的 `@ / :` 直接截断 authority。见 `tests/test_setup_database_url.py` |

### OOBE 进度流契约

`GET /oobe/install/stream` 与 `GET /oobe/install-dependencies/stream` 共用 `_sse_progress_stream`：
先回放内存缓冲、再订阅队列，收到 `done`/`error` 或**空闲超过 15s×40（≈10 分钟）**即关闭——两条流位于 OOBE
匿名白名单内，不设上限等于让单个客户端永久占住连接与协程。事件只有 `progress` / `done` / `error` 三种，
前端 `useOOBE.ts` 依赖 `done` 里的 `frontend_url` / `admin_url`；改字段要同步改向导。
安装动作只有一个入口 `POST /oobe/install`（旧分步接口与 `POST /oobe/complete` 已下线，勿复活第二套初始化实现）。
`POST /oobe/reset` 走 `ConfigService.reset_oobe()`：该方法**逐个**删除 lock/env/config/state 并返回
无法删除的项名列表，端点据此回 500——回 200 却残留 `.env`（含 `SECRET_KEY`/DB 连接串）是最难排查的半完成态。

### 查询预算（列表 / 统计 / 扫描类接口）

四条硬约束，各有对应回归用例，改坏即红：

1. **禁止逐年/逐 id 循环发查询**。分组计数一律 `select(expr, func.count()).group_by(expr)`，
   `expr` 必须与 SELECT 里的表达式是同一个对象，否则 PG 判"裸列分组"。
   例：`PostRepository.get_archive_stats` 由 `1 + 1 + N年` 条降到恒定 2 条
   （`tests/test_archive_stats.py` 用 `_CountingSession` 钉住条数上限）。
2. **列表类查询只投影展示列**。`select(Post)` 会把 JSON `content` 正文整列拉进内存并实例化 ORM
   对象；归档/热榜这种全量列表在文章上千时是内存与耗时的主要来源。改列级 `select(Post.id, ...)`
   + `outerjoin`（`tests/test_archive_stats.py` 监听 `before_cursor_execute` 断言 SQL 不含 `content`）。
3. **磁盘扫描对齐 DB 要先批量预取**。`PluginManager.scan_local` / `ThemeManager.scan_local`
   原先对每个 manifest 单发 `SELECT ... WHERE slug=?`，现统一改为一次取本站全表 + 内存 `dict` 比对
   （`tests/test_scan_query_count.py` 钉住常数条数）。
4. **批量接口必须真批量**。前端 `for (const id of ids) await deleteX(id)` 会把 N 项变成 N 次往返
   + N 次全量缓存失效；一律提供 `DELETE .../batch`（一次 `IN` 查询 + 一次 `delete().where(in_)`，
   每个受影响父实体只重算一次计数字段）。注意 `/batch` 必须注册在 `/{id}` **之前**，否则路径段被
   当 int 解析 → 422。响应回 `deleted_count` / `missing_ids`（`tests/test_api_gallery.py`
   `TestAdminPhotoBatchDelete` 钉住计数与跨相册重算）。

### 静默降级红线（`except` 只写 `pass` 的判据）

清理/校验/计数类动作包在 `try` 里、`except Exception: pass`，等于把失败连同**失败处理**一起吞掉。新增此类代码前按三分法定性：

| 该 `except` 吞掉的是什么 | 必须怎么处理 | 已修复的反例 |
| ---- | ---- | ---- |
| 安全门禁（限次、校验、鉴权兜底） | 降级为**更严**：作废凭证 + `raise`，且 `raise` 不得留在同一个 `try` 内 | 密码重置尝试计数：原先计数写失败即锁定制服静默失效 |
| 状态清理 / 文件删除 / 落盘 | 单项失败不阻断其余项，收集失败项**回报给调用方**或 `logger.exception` | `reset_oobe`、`save_state` |
| 纯噪声（可选依赖探测、best-effort 遥测） | 允许吞，但必须收窄异常类型（`ImportError`/`OSError`）并写明为什么可丢 | — |

判据用 `python - <<'EOF'` 走 AST：列出 `handlers` 体内只有 `Pass`/`Ellipsis` 的 `Try`，再筛 try 体含
`raise` / `HTTPException` / `unlink` / `commit` / `run` 的项。禁止把 `raise` 写在会被自身
`except Exception` 命中的位置。

**后台缓冲落库失败要"停手"而不是"跑完"**：`_flush_visit_queue` 这类
`while await flush() > 0` 的排空循环，DB 抖动时必须把本批**整批回队**
（best-effort；队满只能丢弃，但必须 `logger.exception` 记条数）并返回 `0`。
返回本批条数会让外层循环把内存缓冲区一路抽干，等于把"数据库暂时不可用"放大成
"访问日志整段蒸发"。由 `tests/test_monitoring_visit_queue.py` 钉住。

### 全局会话（`async_session_maker` / 裸 `engine`）

非 DI 场景（中间件、后台任务、service）允许 `async with async_session_maker()` 自开会话，
但必须用完即关、不得跨请求持有。这条路径绕开 `get_db`，测试里由 `db_session` fixture
按**属性名**扫描覆写（见「测试」一节），所以函数内的
`from backend.core.database import async_session_maker` 同样被拦；
模块级 `from backend.core.database import engine` 的裸连接（如 monitoring 统计）也一样被覆写。

## 数据库迁移

```bash
uv run python -m backend.migrations status
uv run python -m backend.migrations upgrade
uv run python -m backend.migrations revision -m "描述" --autogenerate
```

**务必人工检查** upgrade / downgrade。如果 autogenerate 生成 "drop all tables"，**立即删除该版本文件**，检查 `env.py` 的 `target_metadata` 是否漏 import 新 model。

## 安全清单

- `SECRET_KEY` 生产必须 ≥32 字节随机串，环境变量注入
- 文档开关：`docs_enabled = DEBUG 或非 production 环境`——production 且 DEBUG=false 时 `/docs` / `/redoc` / `/openapi.json` 全部关闭；dev/staging 默认开启
- `CORS_ORIGINS` 生产仅列明确域名
- 密码哈希：新密码一律 argon2id；现存 bcrypt hash（$2a$/$2b$/$2y$）继续可登录并在成功后自动 rehash 升级；喂给 bcrypt 的超长密码先 SHA-256 + base64（绕 72 字节截断）
- 文件上传受 `MAX_UPLOAD_SIZE` + `ALLOWED_EXTENSIONS` 双重约束
- 敏感 SMTP 密码以 `email_configured: bool` 暴露，不回传明文
- 生产启用 `TrustedHostMiddleware`

## 测试

pytest + pytest-asyncio + httpx.AsyncClient。测试文件在根 `tests/`，命名 `test_*.py`。
当前规模：**657 个用例**（`uv run pytest --collect-only -q` 实测）；pyproject 覆盖率门禁
`fail_under=45%`，全量运行实测约 **84.5%**。

```bash
uv run pytest tests/ -v
```

不依赖线上服务 / 外部网络；fixture 在 `tests/conftest.py`。

**会话隔离铁律：任何需要数据库的用例都必须经 `db_session`（直接或间接），不得自己造会话。**
`db_session` 除了建会话，还负责把全仓库所有模块的 `async_session_maker` / `engine` 属性
覆写到本用例的测试引擎；`client` 只请求它再叠加依赖注入。历史事故：覆写原先只打在 `client`
里，只依赖 `db_session` 的用例调用被测函数时拿到**真实引擎**，测试全绿而 `rosetta.db`
被写进垃圾行。现在由 `tests/test_conftest_session_isolation.py` 做守卫——覆写一旦回退或漏扫，
该用例先红。跑完任何一轮测试后如有疑问，`select count(*) from visit_logs where path like '%flushed%'`
这类真实库残留探测是最快的证据。

## 提交前检查

```bash
uv run python -c "from backend.main import app"
uv run python -m backend.migrations status
uv run ruff check backend tests
```

访问 `/health` → healthy；`/docs`（DEBUG=true）列出路由。
