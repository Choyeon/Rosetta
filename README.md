# Rosetta 🌸

**前后端分离的现代化博客系统 — WordPress 风格主题与插件架构 + 极简 Admin + 渐进式 SSR**

<div align="center">

![Nuxt 4](https://img.shields.io/badge/Nuxt-4.5-00DC82?style=for-the-badge&logo=nuxt.js)
![FastAPI](https://img.shields.io/badge/FastAPI-Python-009688?style=for-the-badge&logo=fastapi)
![SQLAlchemy 2.0](https://img.shields.io/badge/SQLAlchemy-2.0-111111?style=for-the-badge)
![TypeScript](https://img.shields.io/badge/TypeScript-5-3178C6?style=for-the-badge&logo=typescript)
![Python](https://img.shields.io/badge/Python-3.11%2B-3776AB?style=for-the-badge&logo=python)

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg?style=for-the-badge)](LICENSE)

*两套可切换主题 · WordPress 风格插件引擎 · shadcn-vue Admin · Gravatar 代理*

</div>

---

## ✨ 核心特性

### 🎨 双主题系统（可热切换）
- **Editorial WP-Style**（默认）：Magazine 风格，衬线字体 + 天青色 glow ring 卡片动效 + Hero 渐变
- **Minimal Paper**（复刻 Astro Paper）：窄栏 760px + 衬线标题 + 底线分隔的文章列表 + 图标化导航项
- 两个主题通过 `data-rosetta-theme` + `data-layout-scope="frontend"` 四层防御确保**切换不影响后台 Admin UI**
- 主题目录：`frontend/themes/{slug}/style.css`，支持独立 manifest.json + 资源文件

### 🔌 WordPress 风格插件系统
- 钩子引擎（actions / filters / 短代码解析）
- 清单扫描器自动发现 `plugin.json`
- 路由 / 中间件 / 内容注入全部可扩展
- 已内置：`hello-rosetta`（演示钩子）/ `guestbook-rss`（留言板 RSS）

### 🛠️ 后台 Admin
- shadcn-vue 原生组件（Card / Button / Input / Dialog / Table ...）
- 仪表盘 + 文章 / 分类 / 标签 / 评论 / 留言板 / 友情链接 / 媒体 / 用户 / 主题 / 插件 / 设置 全模块
- 站点设置 17 个分组（basic / appearance / security / comments / media / reading / features / email ...）

### 👤 头像代理（国内友好）
- 默认 `https://cravatar.cn/avatar`（2026-08 实测存活、速度最快）
- 白名单域名（Gravatar 官方 + 国内镜像 + GitHub + DiceBear + QQ）307 直跳
- 非白名单走服务端流式代理 + MIME 校验 + 错误兜底
- SSRF 防护：私有 IP / IANA 保留域 / localhost 一律跳过

### 🌐 i18n
- 四种语言：中文 / English / 日本語 / 繁體中文
- 后端 contextvars 多语言上下文 + 前端 @nuxtjs/i18n v10
- 模型文本字段 `dict[str, str]` 存多语言

### 🖥️ 渐进式 SSR
- SPA 起步，`ssr: false` 稳定可运行
- 公开页面按优先级逐个打开 SSR（`routeRules: { swr: N }`）
- Admin / Login / OOBE 保持 SPA

### 🔐 安全
- JWT（access 1h / refresh 7d）+ bcrypt 密码哈希
- CSRF / rate_limit / distributed_lock 中间件
- AppException 统一错误码，前端收到稳定 `error_code`
- OOBE 中间件：未完成安装时 `/api/*` 返回 503 + `OOBE_REQUIRED`
- TrustedHostMiddleware 生产环境校验 Host

---

## 🚀 快速开始

### 环境要求
- **Node.js** 20+（前端）
- **Python** 3.11+（后端）
- **pnpm** 11（前端包管理）
- **uv**（后端包管理）
- 数据库：开发默认 SQLite，生产推荐 PostgreSQL

### 一键启动（开发模式）

```bash
# 克隆
git clone https://github.com/<your-org>/rosetta.git
cd rosetta

# 后端依赖 + 启动
uv sync
uv run uvicorn backend.main:app --reload --port 8000

# 前端依赖 + 启动（会自动 spawn 后端，若 8000 空闲）
cd frontend
pnpm install
pnpm dev
```

- 前端：http://localhost:3001
- 后端：http://localhost:8000 （Swagger 在 `/docs`）
- OOBE：http://localhost:3001/oobe

首次启动走 OOBE 向导（5 步）完成站点初始化，或用 `uv run python -m backend.scripts.mock_data` 写入演示数据。

### 环境变量（可选）

**后端 `.env`**（所有后端配置也可写进 SiteConfig 表）：
```env
APP_ENV=development
DEBUG=true
SECRET_KEY=<32+字节随机串>
DATABASE_URL=sqlite+aiosqlite:///./rosetta.db
# 或 PostgreSQL:
# DATABASE_URL=postgresql+asyncpg://user:pass@localhost/rosetta

# Gravatar CDN（国内推荐 Cravatar）
GRAVATAR_CDN_BASE=https://cravatar.cn/avatar

# Redis（可选，不启用则开发用内存缓存）
REDIS_ENABLED=false
REDIS_URL=redis://localhost:6379

# JWT
ACCESS_TOKEN_EXPIRE_MINUTES=60
REFRESH_TOKEN_EXPIRE_DAYS=7

# 站点
SITE_NAME=Rosetta
SITE_URL=http://localhost:3001

# CORS 生产仅列明确域名
CORS_ORIGINS=["http://localhost:3001"]
```

**前端 `.env`**：
```env
NUXT_PUBLIC_API_BASE=http://localhost:8000/api
```

---

## 📂 项目结构

```
Rosetta/
├── backend/                      FastAPI 后端
│   ├── main.py                   create_application() 入口
│   ├── api/                      API 路由（users / blog / comments / plugins / themes / avatar_proxy / settings_groups ...）
│   ├── core/                     基础设施（config / database / auth / cache / exceptions ...）
│   ├── models/                   SQLAlchemy ORM 模型
│   ├── services/                 业务层（avatar_resolver / plugin_engine / theme_manager ...）
│   ├── migrations/               Alembic 版本化迁移
│   └── scripts/                  mock_data.py
│
├── frontend/                     Nuxt 4.5 前端
│   ├── app/pages/                路由页面
│   ├── components/               Vue 组件（AppHeader / PostCard / admin/*）
│   ├── components/ui/            shadcn-vue 原子组件
│   ├── composables/              useApi / useTheme / useFrontendTheme / useAvatar ...
│   ├── layouts/                  default.vue / admin.vue
│   ├── middleware/               layout-scope.global.ts / oobe.global.ts
│   ├── server/                   Nitro BFF
│   ├── themes/                   editorial-wp-style / astro-paper-inspired
│   ├── assets/css/main.css       Tailwind + 共享组件类（.prose-shadcn / .card-surface）
│   └── i18n/locales/             zh / en / ja / zh_Hant
│
├── pyproject.toml                Python 依赖
├── package.json                  JS 依赖（frontend/pnpm）
├── AGENTS.md                      项目级规范（面向 AI）
├── backend/AGENTS.md              后端规范
├── frontend/AGENTS.md             前端规范
└── README.md
```

---

## 🧩 API 契约

所有 HTTP 2xx：
```json
{ "success": true, "data": {...}, "message": "可选" }
```
失败：
```json
{ "success": false, "error_code": "INVALID_CREDENTIALS", "message": "...", "errors": [...] }
```

主要端点（完整列表见 `/docs`）：
| 模块 | 路由 | 说明 |
|------|------|------|
| 认证 | `POST /api/users/login` | 登录返回 access + refresh token |
| 认证 | `POST /api/users/refresh` | 刷新 access token |
| 博客 | `GET /api/blog/posts` | 文章列表（分页 + 分类/标签过滤） |
| 博客 | `GET /api/blog/posts/{slug}` | 文章详情 |
| 评论 | `GET /api/comments?post_id=N` | 嵌套评论 |
| 头像 | `GET /api/media/avatar?src=<b64>` | 代理头像 |
| 插件 | `GET /api/plugins` / `POST /api/plugins/{slug}/activate` | 插件管理 |
| 主题 | `GET /api/themes` / `POST /api/themes/{slug}/activate` | 主题切换 |
| 设置 | `GET /api/settings` / `PATCH /api/settings/{group}` | 17 组站点设置 |
| Admin | `GET /api/admin/stats` | 仪表盘统计 |

---

## 🛠️ 开发命令速查

### 后端（项目根目录）
```bash
uv sync
uv run uvicorn backend.main:app --reload --port 8000
uv run python -m backend.migrations upgrade
uv run python -m backend.migrations revision -m "msg" --autogenerate
uv run python -m backend.migrations status
uv run python -m backend.scripts.mock_data     # 写演示数据
```

### 前端（frontend/ 目录）
```bash
pnpm install
pnpm dev            # 自动 spawn 后端
pnpm typecheck      # vue-tsc
pnpm lint           # ESLint
pnpm build && pnpm preview
```

### 验证清单
**后端**：`uv run python -c "from backend.main import app"` + `/health` 返回 healthy
**前端**：`pnpm typecheck` + 明/暗主题 ✓ 四语言 ✓ 移动端 ✓ 无 hydrate mismatch

### 提交规范（Conventional Commits）
```
feat: 头像代理新增 DiceBear fallback
fix: 修复 Minimal Paper 主题 navbar 竖排断行
refactor: avatar_resolver 统一 comment/guestbook 的 _gravatar_base 副本
perf: 文章列表缓存 ttl 从 300s 提升到 600s
chore: Alembic 迁移 upgrade
i18n: 补全日语设置页翻译
```

---

## 🎨 设计系统

### 主题令牌（HSL，由 main.css `:root` 定义）
| Token | 默认值 | 说明 |
|-------|--------|------|
| `--primary` | 201 96% 52% | 天青主色 |
| `--accent` | 210 40% 96% | 浅灰强调 |
| `--ring` | 201 96% 52% | 焦点环 |
| `--card-surface` | hsl(0 0% 98% / 0.72) | Editorial 卡片半透明底 |
| `--radius` | 0.75rem | shadcn 默认圆角 |

主题通过覆盖这些 CSS 变量 + 注入自定义 style.css 实现风格切换。

### Typography
- Editorial：Fraunces（衬线 display）+ Geist（sans-serif body）
- Minimal Paper：Iowan Old Style（衬线标题复刻 Astro Paper）
- 统一 16px base，1.25 Major Third 比例

---

## 🔗 文档索引

- **面向 AI / 开发者**：
  - [项目级规范](AGENTS.md)
  - [后端规范](backend/AGENTS.md)
  - [前端规范](frontend/AGENTS.md)
- **OpenAPI 文档**：启动后端后访问 `/docs`（DEBUG=true 时可用）
- **错误码**：`backend/core/exceptions.py` 的 `ERROR_CODES` 字典

---

## 📄 License

MIT — 见 [LICENSE](LICENSE) 文件。

---

<div align="center">
Built with ❤️ using Nuxt 4.5, FastAPI, SQLAlchemy 2.0, and modern web tech.
</div>
