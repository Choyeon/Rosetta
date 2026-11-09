# Rosetta

> **Rosetta** —— 前后端分离的现代化博客系统。WordPress 风格的主题与插件架构、shadcn-vue 管理后台、渐进式 SSR、四语 i18n、内置 SEO/OOBE 向导与必应每日壁纸。

<div align="center">

![Nuxt 4.5](https://img.shields.io/badge/Nuxt-4.5-00DC82?style=for-the-badge&logo=nuxt.js)
![FastAPI](https://img.shields.io/badge/FastAPI-Python-009688?style=for-the-badge&logo=fastapi)
![SQLAlchemy 2.0](https://img.shields.io/badge/SQLAlchemy-2.0-111111?style=for-the-badge)
![TypeScript 5](https://img.shields.io/badge/TypeScript-5-3178C6?style=for-the-badge&logo=typescript)
![Python 3.11+](https://img.shields.io/badge/Python-3.11%2B-3776AB?style=for-the-badge&logo=python)
[![CI](https://github.com/Choyeon/Rosetta/actions/workflows/ci.yml/badge.svg)](https://github.com/Choyeon/Rosetta/actions/workflows/ci.yml)

*多主题热切换 · 钩子驱动插件引擎 · 四层解耦前后台 · 头像/Gravatar 国内友好代理*

</div>

---

## 📖 项目简介

Rosetta 是一个以「可扩展、可定制、可自托管」为目标的博客平台：

- **前台** 基于 Nuxt 4 + Vue 3 的渐进式 SSR 应用，支持多套 WordPress 风格主题热切换；
- **后台** 基于 shadcn-vue 的管理面板，覆盖文章 / 评论 / 用户 / 主题 / 插件 / 设置等全模块；
- **后端** 基于 FastAPI + SQLAlchemy 2.0（async）的 REST API，提供 JWT 认证、缓存、分布式锁、Webhook 等基础设施；
- **BFF** 由 Nitro Server-Route 承担 RSS / Sitemap / Robots / llms.txt 等 SEO 聚合与必应壁纸代理。

> 本 README 中的界面预览均来自本地开发环境（`ChoyeonBlog` 演示数据，52 篇文章 / 13 个分类 / 36 个标签 / 270+ 评论）。

---

## ✨ 功能特性

| 模块 | 关键能力 |
|------|----------|
| 🎨 **主题系统** | 2 套内建主题（Editorial WP-Style / Minimal Paper）；`rosetta-theme.json` 声明式 Customizer；磁盘 ↔ 数据库扫描同步；四层样式隔离不污染后台 |
| 🔌 **插件系统** | WordPress 风格钩子引擎（actions / filters / 短代码）；清单扫描自动发现；内置 `hello-rosetta` · `guestbook-rss` · `seo-toolkit` |
| 🛡️ **安全** | JWT（access 1h / refresh 7d）+ argon2id / bcrypt 密码哈希；CSRF / rate_limit / 分布式锁；统一错误码 `error_code`；OOBE 锁；TrustedHost |
| 🌐 **国际化** | 四语 `zh · en · ja · zh_Hant`，后端 contextvars + 前端 @nuxtjs/i18n v10，模型字段 `dict[str,str]` 原生多语言 |
| 🖼️ **头像代理** | 默认 `cravatar.cn`，白名单直跳 + 流式代理 + DiceBear SVG 兜底，SSRF 防护 |
| 🔍 **SEO** | Nitro 生成 RSS 2.0 / Sitemap 索引 / Robots / llms.txt / security.txt；服务端渲染友好 |
| 🌄 **必应每日壁纸** | Nitro BFF 聚合归档 + 站内 4K 代理下载，可一键关闭收录 |
| ⚙️ **OOBE 向导** | 5 步安装向导完成站点初始化，未完成时后端返回 `503 OOBE_REQUIRED` |

---

## 🖥️ 界面预览

所有截图均在本地 `http://localhost:3000`（前端）/ `http://localhost:8000`（后端）实拍。

### 前台（访客视角）

| 首页 Home | 文章列表 Posts |
|---|---|
| ![首页](docs/screenshots/home.png) | ![文章列表](docs/screenshots/posts.png) |

| 文章详情 Post Detail | 热门文章 Hot Posts |
|---|---|
| ![文章详情](docs/screenshots/post-detail.png) | ![热门文章](docs/screenshots/posts-hot.png) |

| 归档 Archive | 分类 Categories |
|---|---|
| ![归档](docs/screenshots/archive.png) | ![分类](docs/screenshots/categories.png) |

| 分类详情 Category | 标签 Tags |
|---|---|
| ![分类详情](docs/screenshots/category-detail.png) | ![标签](docs/screenshots/tags.png) |

| 标签详情 Tag | 作者 Authors |
|---|---|
| ![标签详情](docs/screenshots/tag-detail.png) | ![作者](docs/screenshots/authors.png) |

| 作者主页 Author | 关于 About |
|---|---|
| ![作者主页](docs/screenshots/author-detail.png) | ![关于](docs/screenshots/about.png) |

| 留言板 Guestbook | 友情链接 Friends |
|---|---|
| ![留言板](docs/screenshots/guestbook.png) | ![友链](docs/screenshots/friends.png) |

| 相册 Gallery | 动态 Activity |
|---|---|
| ![相册](docs/screenshots/gallery.png) | ![动态](docs/screenshots/activity.png) |

| 专题 Series | 搜索 Search |
|---|---|
| ![专题](docs/screenshots/series.png) | ![搜索](docs/screenshots/search.png) |

| 必应每日一图 Wallpapers | 赞助 Sponsor |
|---|---|
| ![壁纸](docs/screenshots/wallpapers.png) | ![赞助](docs/screenshots/sponsor.png) |

**多语言（i18n）**：同一套前台可切换 `简体中文 / English / 日本語 / 繁體中文`，URL 以 `/en` `/ja` `/zh_Hant` 前缀区分（中文为默认无前缀）。

| English 🇬🇧 | 日本語 🇯🇵 | 繁體中文 🇹🇼 |
|---|---|---|
| ![英文](docs/screenshots/i18n-en.png) | ![日文](docs/screenshots/i18n-ja.png) | ![繁体](docs/screenshots/i18n-zh-hant.png) |

---

### 用户中心（登录后）

| 账户中心 Account | 账户设置 Settings |
|---|---|
| ![账户中心](docs/screenshots/account.png) | ![账户设置](docs/screenshots/account-settings.png) |

| 我的消息 Messages | 通知 Notifications |
|---|---|
| ![消息](docs/screenshots/account-messages.png) | ![通知](docs/screenshots/account-notifications.png) |

---

### 后台管理（Admin）

登录入口与仪表盘：

| 登录页 Login | 仪表盘 Dashboard |
|---|---|
| ![登录](docs/screenshots/admin-login.png) | ![仪表盘](docs/screenshots/admin-dashboard.png) |

**内容管理**

| 文章管理 Posts | 文章编辑器 Editor |
|---|---|
| ![文章管理](docs/screenshots/admin-posts.png) | ![编辑器](docs/screenshots/admin-post-editor.png) |

| 分类 Categories | 标签 Tags |
|---|---|
| ![分类](docs/screenshots/admin-categories.png) | ![标签](docs/screenshots/admin-tags.png) |

| 页面 Pages | 专题 Series |
|---|---|
| ![页面](docs/screenshots/admin-pages.png) | ![专题](docs/screenshots/admin-series.png) |

**互动管理**

| 评论 Comments | 留言板 Guestbook |
|---|---|
| ![评论](docs/screenshots/admin-comments.png) | ![留言板](docs/screenshots/admin-guestbook.png) |

| 动态 Activities | 公告 Announcements |
|---|---|
| ![动态](docs/screenshots/admin-activities.png) | ![公告](docs/screenshots/admin-announcements.png) |

| 投票 Polls | |
|---|---|
| ![投票](docs/screenshots/admin-polls.png) | |

**媒体与用户**

| 媒体库 Media Library | 媒体相册 Gallery |
|---|---|
| ![媒体库](docs/screenshots/admin-media-library.png) | ![媒体相册](docs/screenshots/admin-media-gallery.png) |

| 用户 Users | 头衔/称号 Titles |
|---|---|
| ![用户](docs/screenshots/admin-users.png) | ![头衔](docs/screenshots/admin-user-titles.png) |

**系统与扩展**

| 主题管理 Themes | 插件管理 Plugins |
|---|---|
| ![主题](docs/screenshots/admin-themes.png) | ![插件](docs/screenshots/admin-plugins.png) |

| 站点设置 Settings | 短代码 Shortcodes |
|---|---|
| ![设置](docs/screenshots/admin-settings.png) | ![短代码](docs/screenshots/admin-shortcodes.png) |

| 友链 Friend Links | 导航菜单 Navigation |
|---|---|
| ![友链](docs/screenshots/admin-friendlinks.png) | ![导航](docs/screenshots/admin-navigation.png) |

| Webhook | 搜索占位符 |
|---|---|
| ![Webhook](docs/screenshots/admin-webhooks.png) | ![搜索占位](docs/screenshots/admin-search-placeholders.png) |

**工具箱（Tools）**

| SEO 工具 | 监控 Monitoring |
|---|---|
| ![SEO](docs/screenshots/admin-tools-seo.png) | ![监控](docs/screenshots/admin-tools-monitoring.png) |

| 性能 Performance | 缓存 Cache |
|---|---|
| ![性能](docs/screenshots/admin-tools-performance.png) | ![缓存](docs/screenshots/admin-tools-cache.png) |

| 审计日志 Audit Logs | 导入导出 Import/Export |
|---|---|
| ![审计](docs/screenshots/admin-tools-audit-logs.png) | ![导入导出](docs/screenshots/admin-tools-import-export.png) |

| 数据库迁移 Migrations | 翻译 Translate |
|---|---|
| ![迁移](docs/screenshots/admin-tools-migrations.png) | ![翻译](docs/screenshots/admin-tools-translate.png) |

| 访问统计 Visits | |
|---|---|
| ![访问](docs/screenshots/admin-tools-visits.png) | |

---

## 🏗️ 技术架构

```
              ┌────────────────────────────────────────────────┐
              │                    Browser                       │
              └──────────────────────┬─────────────────────────┘
                                     │ https://domain (Nginx :80/443)
                                     ▼
              ┌────────────────────────────────────────────────┐
              │   Nginx (deploy/nginx-site.conf)                 │
              │   /api  ──► backend upstream :8000              │
              │   /     ──► frontend upstream :3000             │
              └─────┬──────────────────────────────────────────┘
                    │                                   │
                    ▼                                   ▼
         FastAPI :8000 (backend/)                 Nuxt SSR :3000 (frontend/)
          - Auth/JWT + CSRF + rate-limit         - SSR 公开页 / SPA 后台页
          - SQLAlchemy 2.0 async (PG/SQLite)     - composables: useAPI / apiFetch
          - Alembic 迁移                         - Pinia auth（skipHydrate）
          - OOBE 锁 + 插件钩子 + 主题管理          - i18n @nuxtjs/i18n 10.x
          - RSS/SEO/Bing 代理接口                 - Nitro BFF: rss/sitemap/robots/bing
```

| 层级 | 技术栈 | 位置 |
|------|--------|------|
| Web 前端 | Nuxt 4.5 + Vue 3 + TS + Tailwind v4 + shadcn-vue + Pinia 4 + @nuxtjs/i18n | `frontend/` |
| Nitro BFF | h3 + ohmyfetch（API 代理 · RSS/Sitemap/Robots 聚合 · 必应壁纸代理） | `frontend/server/` |
| 后端 API | FastAPI + uvicorn + asyncpg / aiosqlite + Pydantic | `backend/` |
| ORM / 迁移 | SQLAlchemy 2.0 async + Alembic（`backend/migrations/`） | `backend/models` · `backend/migrations` |
| 缓存 | Redis 8 + Memory 双后端；分布式锁 / 预热器 | `backend/core/cache*.py` |
| 认证 | PyJWT + argon2-cffi + bcrypt + cryptography | `backend/core/auth.py` |
| 国际化 | 四语 `zh · en · ja · zh_Hant`（fallback `en`） | `frontend/i18n/*` |
| 测试 | 后端 pytest-asyncio + pytest-cov（45% fail_under）；前端 vitest + happy-dom | `tests/` · `frontend/tests/` |

---

## 🚀 快速开始

### 环境要求

| 组件 | 版本 | 包管理器 |
|------|------|----------|
| Node.js | 20+ | pnpm 11 |
| Python | 3.11+ | uv |
| 数据库 | SQLite（开发）/ PostgreSQL（生产）| — |

### 本地启动（推荐：前后端并发）

```bash
# 1. 安装依赖
uv sync                       # 后端（在仓库根目录）
cd frontend && pnpm install   # 前端

# 2. 一键并发启动（后端 :8000 + 前端 :3000）
.\dev.ps1                     # Windows PowerShell
# 或
pnpm dev:all
```

启动后访问：

| 入口 | URL |
|------|-----|
| 前端首页 | http://localhost:3000 |
| 后端 Swagger | http://localhost:8000/docs |
| OOBE 安装向导 | http://localhost:3000/oobe |

### 初始化与演示数据

- **首次启动** 走 OOBE 向导（5 步）完成站点初始化并创建管理员账号；
- 或跳过向导，直接写入演示数据：

```bash
uv run python -m backend.scripts.mock_data    # 生成演示文章/分类/标签/评论/用户
```

### 本地测试账号

> 演示用账号，**生产环境请务必修改密码**。

```
用户名：admin
密码：  admin123
```

登录入口：前台右上角「登录」或 `http://localhost:3000/login`；登录后可访问 `/admin` 管理后台。

### 环境变量

复制 `.env.example` 为 `.env` 后按需调整：

```env
# 必需
APP_ENV=development
SECRET_KEY=<32+字节随机串>

# 数据库（开发用 SQLite；生产用 PostgreSQL）
DATABASE_URL=sqlite+aiosqlite:///./rosetta.db
# DATABASE_URL=postgresql+asyncpg://user:pass@localhost/rosetta

# 头像 CDN（国内友好镜像）
GRAVATAR_CDN_BASE=https://cravatar.cn/avatar

# Redis（可选，不启用则用内存缓存）
REDIS_ENABLED=false
REDIS_URL=redis://localhost:6379

# CORS（生产必须显式列域名）
CORS_ORIGINS=["http://localhost:3000"]
```

---

## 📁 项目结构

```
Rosetta/
├── backend/                      FastAPI 后端
│   ├── main.py                   create_application() 入口
│   ├── api/                      API 路由（users · blog · comments · media · plugins · themes · webhook …）
│   ├── core/                     基础设施（config · database · auth · cache · plugin_loader · plugin_bus）
│   ├── models/                   SQLAlchemy ORM 模型
│   ├── services/                 业务层（avatar_resolver · theme_manager · site_settings …）
│   ├── migrations/               Alembic 版本化迁移
│   └── scripts/                  mock_data.py · migrate_database.py
│
├── frontend/                     Nuxt 4.5 前端
│   ├── pages/                    路由页面（前台 + /admin 后台）
│   ├── components/               Vue 组件
│   ├── components/ui/            shadcn-vue 原子组件
│   ├── composables/              useApi · useTheme · useFrontendTheme · useAvatar
│   ├── layouts/                  default.vue（前台）· admin.vue（后台）
│   ├── middleware/               layout-scope · oobe · auth-required
│   ├── server/                   Nitro BFF（API 代理 / RSS / Sitemap / Robots / 必应壁纸）
│   ├── themes/                   editorial-wp-style · astro-paper-inspired
│   ├── assets/css/main.css       Tailwind + 共享组件类
│   └── i18n/locales/             zh · en · ja · zh_Hant
│
├── tests/                        后端 pytest 测试套件
├── deploy/                       部署配置（nginx-site.conf · systemd service）
├── .github/workflows/ci.yml      GitHub Actions CI
├── pyproject.toml                Python 依赖（uv 管理）
├── frontend/package.json         JS 依赖（pnpm 管理）
└── README.md
```

---

## 🔌 API 契约

**成功响应**

```json
{ "success": true, "data": { "...": "..." }, "message": "可选" }
```

**失败响应**

```json
{ "success": false, "error_code": "INVALID_CREDENTIALS", "message": "...", "errors": [...] }
```

**主要端点**

| 模块 | 路由 | 说明 |
|------|------|------|
| 认证 | `POST /api/users/login` | 登录返回 access + refresh token |
| 认证 | `POST /api/users/refresh` | 刷新 access token |
| 博客 | `GET /api/blog/posts` | 文章列表（分页 + 分类/标签过滤） |
| 博客 | `GET /api/blog/posts/{slug}` | 文章详情 |
| 评论 | `GET /api/comments?post_id=N` | 嵌套评论 |
| 头像 | `GET /api/media/avatar?src=<b64>` | 代理头像（白名单 / 兜底） |
| 插件 | `GET /api/plugins` · `POST /api/plugins/{slug}/activate` | 插件列表 / 激活 |
| 主题 | `GET /api/themes` · `POST /api/themes/{slug}/activate` | 主题列表 / 切换 |
| 设置 | `GET /api/settings` | 17 组站点设置 |
| Admin | `GET /api/admin/stats` | 仪表盘统计 |

> 完整契约见后端 Swagger：`http://localhost:8000/docs`。

---

## 🛠️ 开发命令速查

### 后端（仓库根目录）

```bash
uv sync
uv run uvicorn backend.main:app --reload --port 8000
uv run pytest -q --no-cov                 # 运行测试
uv run python -m backend.migrations upgrade
uv run python -m backend.migrations revision -m "msg" --autogenerate
uv run python -m backend.migrations status
uv run python -m backend.scripts.mock_data # 写入演示数据
```

### 前端（`frontend/`）

```bash
pnpm install
pnpm dev                # 开发服务器（默认 :3000）
pnpm typecheck          # vue-tsc
pnpm lint               # ESLint
pnpm build && pnpm preview
```

### CI 检查清单

- 后端：`uv run pytest -q` 全部通过
- 前端：`pnpm typecheck` + `pnpm lint`（0 error）

---

## 🌐 国际化

- 固定四语：`zh`（默认）· `en` · `ja` · `zh_Hant`，`fallbackLocale = en`；
- 策略 `prefix_except_default`：中文裸路径（`/admin`、`/login`），其余语言挂 `/en` `/ja` `/zh_Hant` 前缀；
- 模型文本字段以 `dict[str, str]` 原生多语言存储，前端按 `locale` 取值。

---

## 🧪 测试

```bash
# 后端（pytest-asyncio 自动模式 + 覆盖率 45% 底线）
uv run pytest -q

# 前端（vitest + happy-dom 单测）
cd frontend && pnpm test
```

---

## 📝 提交规范（Conventional Commits）

```
feat:   头像代理新增 DiceBear fallback
fix:    修复 Minimal Paper 主题 navbar 竖排断行
refactor: avatar_resolver 统一 comment/guestbook 的副本
perf:   文章列表缓存 ttl 从 300s 提升到 600s
chore:  Alembic 迁移 upgrade
i18n:   补全日语设置页翻译
```

---

## 📄 License

MIT —— 自由用于学习、二次开发与自托管。
