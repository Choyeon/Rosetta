# Rosetta 项目开发规范

> 面向 AI 编程助手与人类工程师的项目级速查卡。开始工作前先读本文件，再按子目录进入对应 AGENTS.md。

## 架构（已固定，不讨论）

Rosetta 是**前后端分离**博客系统，双语言栈各取所长：

| 层级 | 技术 | 目录 |
|------|------|------|
| 前端 | Nuxt 4.5 + Vue 3 + TypeScript + Tailwind CSS + shadcn-vue + Pinia | `frontend/` |
| 后端 | FastAPI + SQLAlchemy 2.0 + async + Pydantic v2 + Alembic | `backend/` |
| Nitro | BFF（仅做 API 代理 / SSR 数据聚合 / 开发模式自动启动后端） | `frontend/server/` |

### 已落地的扩展系统

- **主题系统**（WordPress 风格）：`frontend/themes/{slug}/style.css` + 主题内资源；通过 `data-rosetta-theme` / `data-theme` / `data-layout-scope="frontend"` 三层守卫确保主题样式不泄漏 admin
- **插件系统**：`backend/services/plugin_engine.py` 钩子引擎 + `plugin_registry.py` 清单扫描；路由注册 / 中间件注入 / 短代码解析全部可扩展
- **头像代理**：`/api/media/avatar?src=<b64>` 白名单域名直跳 + 非白名单流式代理 + DiceBear SVG fallback

### 不做清单（硬约束）

1. ❌ 后端不迁移到 Nitro/Node.js（40+ API 模块 + 完整 auth/cache/migration/scheduler）
2. ❌ 不一次性全量开启 SSR（SPA → 渐进式逐页面迁移）
3. ❌ i18n 不新增 zh/ja 之外的语言（当前 zh / en / ja / zh_Hant 四种）
4. ❌ 不在主题 style.css 里写不带 `[data-layout-scope="frontend"]` 守卫的通用选择器（`main` / `header` / `main [class*="rounded-xl"]` 这种 blanket 规则一律禁止）

## 解耦层（主题 ↔ Admin）

四层防御确保"切主题不影响后台 UI"：

| 层 | 机制 | 位置 |
|---|---|---|
| 1 | 运行时路径检测 + 主题清理 | `composables/useFrontendTheme.ts` 的 `applyThemeVisual` / `clearThemeVisual` |
| 2 | 布局主动清理 | `layouts/admin.vue` / `layouts/default.vue` 的 onMounted + watch(route) |
| 3 | 全局中间件兜底 | `middleware/layout-scope.global.ts`（`/admin` / `/login` / `/oobe` / 前台路由） |
| 4 | CSS 选择器作用域守卫 | 主题 style.css 所有规则必须加 `:is([data-theme="..."],[data-rosetta-theme="..."])[data-layout-scope="frontend"]` |

admin 页面 shadcn Card / Button / Input 组件保持原生 Tailwind 类（rounded-xl / border / bg-card），**不**依赖任何主题覆盖。

## 目录结构

```
Rosetta/
├── backend/               FastAPI 后端（见 backend/AGENTS.md）
│   ├── api/               API 路由（users / blog / comments / admin / oobe / plugins / themes / avatar_proxy / settings_groups ...）
│   ├── core/              基础设施（config / database / auth / cache / i18n / csrf / rate_limit / exceptions）
│   ├── models/            SQLAlchemy 2.0 DeclarativeBase（users / posts / categories / tags / comments / guests / themes / plugins / site_configs ...）
│   ├── schemas/           Pydantic v2 请求/响应模型
│   ├── services/          业务层（avatar_resolver / _avatar_helpers / comment_service / guestbook_service / plugin_engine / theme_manager / settings_service）
│   ├── migrations/        Alembic 版本化迁移
│   └── scripts/           一次性脚本（mock_data.py）
│
├── frontend/              Nuxt 4.5 前端（见 frontend/AGENTS.md）
│   ├── app/pages/         路由页面
│   ├── components/        Vue 组件（AppHeader / PostCard / admin/StatCard ...）
│   ├── components/ui/     shadcn-vue 原子组件
│   ├── composables/       组合式函数（useApi / useTheme / useFrontendTheme / useAvatar ...）
│   ├── layouts/           布局（default.vue 前台 / admin.vue 后台）
│   ├── stores/            Pinia（auth.ts）
│   ├── middleware/        全局路由中间件（layout-scope.global.ts / oobe.global.ts）
│   ├── server/            Nitro BFF
│   ├── themes/            主题目录（editorial-wp-style / astro-paper-inspired）
│   ├── assets/css/        全局样式（main.css：Tailwind 变量 + .prose-shadcn + .card-surface 共享组件）
│   ├── i18n/locales/      四语言 JSON
│   └── public/            静态资源
│
├── pyproject.toml         Python 依赖（uv）
├── uv.lock
├── package.json           JS 依赖（frontend/pnpm）
└── README.md
```

## API 契约

所有 HTTP 2xx 统一返回：
```json
{ "success": true, "data": {...}, "message": "可选" }
```
失败：
```json
{ "success": false, "error_code": "INVALID_CREDENTIALS", "message": "...", "errors": [{ "field": "password", "message": "...", "type": "value_error" }] }
```

- 后端统一前缀 `/api/*`，开发端口 `127.0.0.1:8000`
- 前端读取 `useRuntimeConfig().public.apiBase`（默认 `http://localhost:8000/api`）
- 认证：`Authorization: Bearer <access_token>`（1 小时），refresh 7 天；401 → 前端清登录态跳 `/login`
- OOBE 锁文件 `.oobe_complete` 不存在时，非白名单接口返回 503 + `error_code: OOBE_REQUIRED`

## 包管理 & 命令（不要混）

### 后端 — 从**项目根目录**执行
```bash
uv sync
uv run uvicorn backend.main:app --reload --port 8000
uv run python -m backend.migrations upgrade
uv run python -m backend.migrations revision -m "msg" --autogenerate
uv run python -m backend.scripts.mock_data
```

### 前端 — 从**frontend/** 目录执行
```bash
pnpm install
pnpm dev           # 自动 spawn 后端 FastAPI（若 8000 空闲）
pnpm typecheck     # vue-tsc
pnpm lint
pnpm build && pnpm preview
```

## 验证清单

### 后端（提交前）
```bash
uv run python -c "from backend.main import app"       # 模块导入无错
uv run python -m backend.migrations status            # 版本 == head
```
访问 `http://localhost:8000/health` → healthy

### 前端（提交前）
```bash
pnpm typecheck
pnpm lint
```
手动：明/暗主题 ✓ 四语言 ✓ 移动端 ✓ 控制台无 hydrate mismatch / CORS / 401 ✓

## 提交规范

Conventional Commits：`feat:` / `fix:` / `refactor:` / `perf:` / `chore:` / `i18n:`

## 安全红线

- 密钥 / 连接串 / JWT secret 一律通过 `.env` 注入，`.env` 已在 `.gitignore`
- 禁止 SSR 顶层作用域直接访问 `window` / `document` / `localStorage`
- 禁止在主题 style.css 写不带 `[data-layout-scope="frontend"]` 守卫的通用 blanket 选择器
- 禁止写 `.card-surface` 样式到主题 style.css — 它是 main.css 共享类，admin 也在用
