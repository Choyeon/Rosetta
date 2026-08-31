# Rosetta

**前后端分离的现代化博客系统 — WordPress 风格主题与插件架构 · shadcn-vue Admin · 渐进式 SSR**

<div align="center">

![Nuxt 4.5](https://img.shields.io/badge/Nuxt-4.5-00DC82?style=for-the-badge&logo=nuxt.js)
![FastAPI](https://img.shields.io/badge/FastAPI-Python-009688?style=for-the-badge&logo=fastapi)
![SQLAlchemy 2.0](https://img.shields.io/badge/SQLAlchemy-2.0-111111?style=for-the-badge)
![TypeScript 5](https://img.shields.io/badge/TypeScript-5-3178C6?style=for-the-badge&logo=typescript)
![Python 3.11+](https://img.shields.io/badge/Python-3.11%2B-3776AB?style=for-the-badge&logo=python)
[![CI](https://github.com/Choyeon/Rosetta/actions/workflows/ci.yml/badge.svg)](https://github.com/Choyeon/Rosetta/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg?style=for-the-badge)](LICENSE)

*多主题热切换 · 钩子驱动插件引擎 · 四层解耦前后台 · Gravatar 代理国内友好*

</div>

---

## 特性

### 主题系统
- **Editorial WP-Style**（默认）：Magazine 风格，衬线字体 + 卡片 glow ring + Hero 渐变
- **Minimal Paper**：窄栏 760px + 衬线标题 + 底线分隔 + 图标化导航
- 四层样式隔离（路径检测 · 布局清理 · 全局中间件 · CSS 作用域守卫）确保主题切换不污染 Admin UI
- 主题目录：`frontend/themes/{slug}/style.css` + 独立 `rosetta-theme.json` manifest

### 插件系统
- WordPress 风格钩子引擎（actions / filters / 短代码解析）
- 清单扫描器自动发现 `plugin.json`
- 路由注入 / 中间件挂载 / 内容过滤全部可扩展
- 内置示例：`hello-rosetta`、`guestbook-rss`

### 后台 Admin
- shadcn-vue 原生组件（Card · Button · Input · Dialog · Table · Select ...）
- 仪表盘 + 文章 / 分类 / 标签 / 评论 / 留言板 / 友情链接 / 媒体 / 用户 / 主题 / 插件 / 设置 全模块
- 站点设置 17 个分组（basic · appearance · security · comments · media · reading · features · email ...）

### 头像代理（国内友好）
- 默认 `https://cravatar.cn/avatar`（2026 实测最快镜像）
- 白名单域名直跳（Gravatar 官方 + 国内镜像 + GitHub + DiceBear + QQ）
- 非白名单流式代理 + MIME 校验 + DiceBear SVG fallback
- SSRF 防护：私有 IP / IANA 保留域 / localhost 一律跳过

### i18n
- 四种语言：简体中文 · English · 日本語 · 繁體中文
- 后端 contextvars 多语言上下文 + 前端 @nuxtjs/i18n v10
- 模型文本字段 `dict[str, str]` 原生多语言存储

### 安全
- JWT（access 1h / refresh 7d）+ bcrypt 密码哈希
- CSRF / rate_limit / distributed_lock 中间件
- AppException 统一错误码，前端收到稳定 `error_code`
- OOBE 中间件：未完成安装时 `/api/*` 返回 503
- TrustedHostMiddleware 生产环境校验 Host

---

## 快速开始

### 环境要求
| 组件 | 版本 | 包管理器 |
|------|------|----------|
| Node.js | 20+ | pnpm 11 |
| Python | 3.11+ | uv |
| 数据库 | SQLite（开发）/ PostgreSQL（生产）| — |

### 开发模式

```bash
# 克隆仓库
git clone https://github.com/Choyeon/Rosetta.git
cd Rosetta

# 后端依赖 + 启动（开发端口 8000）
uv sync
uv run uvicorn backend.main:app --reload --port 8000

# 前端依赖 + 启动（自动 spawn 后端）
cd frontend
pnpm install
pnpm dev
```

访问：
| 入口 | URL |
|------|-----|
| 前端首页 | http://localhost:3001 |
| 后端 Swagger | http://localhost:8000/docs |
| OOBE 安装向导 | http://localhost:3001/oobe |

首次启动走 OOBE 向导（5 步）完成站点初始化，或：

```bash
uv run python -m backend.scripts.mock_data    # 写入演示数据
```

### 环境变量

复制 `.env.example` 为 `.env`，按需调整：

```env
# 必需
APP_ENV=development
SECRET_KEY=<32+字节随机串>

# 数据库
DATABASE_URL=sqlite+aiosqlite:///./rosetta.db
# 生产: postgresql+asyncpg://user:pass@localhost/rosetta

# Gravatar CDN
GRAVATAR_CDN_BASE=https://cravatar.cn/avatar

# Redis（可选，不启用则用内存缓存）
REDIS_ENABLED=false
REDIS_URL=redis://localhost:6379

# CORS（生产必须显式列域名）
CORS_ORIGINS=["http://localhost:3001"]
```

---

## 项目结构

```
Rosetta/
├── backend/                      FastAPI 后端
│   ├── main.py                   create_application() 入口
│   ├── api/                      API 路由
│   ├── core/                     基础设施（config · database · auth · cache）
│   ├── models/                   SQLAlchemy ORM 模型
│   ├── services/                 业务层（avatar_resolver · plugin_engine · theme_manager）
│   ├── migrations/               Alembic 版本化迁移
│   └── scripts/                  mock_data.py · migrate_database.py
│
├── frontend/                     Nuxt 4.5 前端
│   ├── app/pages/                路由页面
│   ├── components/               Vue 组件
│   ├── components/ui/            shadcn-vue 原子组件
│   ├── composables/              useApi · useTheme · useFrontendTheme · useAvatar
│   ├── layouts/                  default.vue（前台）· admin.vue（后台）
│   ├── middleware/               layout-scope · oobe 全局守卫
│   ├── server/                   Nitro BFF（仅做 API 代理 / SSR 数据聚合）
│   ├── themes/                   editorial-wp-style · astro-paper-inspired
│   ├── assets/css/main.css       Tailwind + 共享组件类
│   └── i18n/locales/             zh · en · ja · zh_Hant
│
├── tests/                        后端 pytest 测试套件
├── .github/workflows/ci.yml      GitHub Actions CI
├── pyproject.toml                Python 依赖
├── frontend/package.json         JS 依赖
└── README.md
```

---

## API 契约

**成功响应**
```json
{ "success": true, "data": { "...": "..." }, "message": "可选" }
```

**失败响应**
```json
{ "success": false, "error_code": "INVALID_CREDENTIALS", "message": "...", "errors": [...] }
```

### 主要端点

| 模块 | 路由 | 说明 |
|------|------|------|
| 认证 | `POST /api/users/login` | 登录返回 access + refresh token |
| 认证 | `POST /api/users/refresh` | 刷新 access token |
| 博客 | `GET /api/blog/posts` | 文章列表（分页 + 分类/标签过滤） |
| 博客 | `GET /api/blog/posts/{slug}` | 文章详情 |
| 评论 | `GET /api/comments?post_id=N` | 嵌套评论 |
| 头像 | `GET /api/media/avatar?src=<b64>` | 代理头像 |
| 插件 | `GET /api/plugins` | 插件列表 |
| 插件 | `POST /api/plugins/{slug}/activate` | 激活插件 |
| 主题 | `GET /api/themes` | 主题列表 |
| 主题 | `POST /api/themes/{slug}/activate` | 切换主题 |
| 设置 | `GET /api/settings` | 17 组站点设置 |
| Admin | `GET /api/admin/stats` | 仪表盘统计 |

---

## 开发命令速查

### 后端（项目根目录）
```bash
uv sync
uv run uvicorn backend.main:app --reload --port 8000
uv run pytest -q --no-cov               # 运行测试
uv run python -m backend.migrations upgrade
uv run python -m backend.migrations revision -m "msg" --autogenerate
uv run python -m backend.migrations status
uv run python -m backend.scripts.mock_data
```

### 前端（frontend/ 目录）
```bash
pnpm install
pnpm dev                # 开发（自动 spawn 后端）
pnpm typecheck          # vue-tsc
pnpm lint               # ESLint
pnpm build && pnpm preview
```

### CI 检查清单
- 后端：`uv run pytest -q` 全部通过
- 前端：`pnpm typecheck` + `pnpm lint`（0 error，warning 可接受）

---

## 提交规范（Conventional Commits）

```
feat:   头像代理新增 DiceBear fallback
fix:    修复 Minimal Paper 主题 navbar 竖排断行
refactor: avatar_resolver 统一 comment/guestbook 的副本
perf:   文章列表缓存 ttl 从 300s 提升到 600s
chore:  Alembic 迁移 upgrade
i18n:   补全日语设置页翻译
```

---

## 设计系统

### CSS 令牌（HSL）
| Token | 值 | 说明 |
|-------|----|------|
| `--primary` | 201 96% 52% | 天青主色 |
| `--accent` | 210 40% 96% | 浅灰强调 |
| `--ring` | 201 96% 52% | 焦点环 |
| `--radius` | 0.75rem | 默认圆角 |

### Typography
- Editorial：Fraunces（衬线 display）+ Geist（sans-serif body）
- Minimal Paper：Iowan Old Style（衬线标题）
- 统一 16px base，1.25 Major Third 比例

---

## License

MIT — 见 [LICENSE](LICENSE) 文件。
