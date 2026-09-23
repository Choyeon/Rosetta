# Rosetta 项目开发规范（v2026.09）

> 面向 AI 编程助手与人类工程师的项目级速查卡。开始工作前先读本文件，
> 再按子目录进入 `backend/AGENTS.md` 与 `frontend/AGENTS.md`。
> **本文档为唯一权威来源，所有与代码现状冲突的旧约束以本版为准。**

***

## 0. 元信息

| 项目        | 值                                                                            |
| --------- | ---------------------------------------------------------------------------- |
| 名称/版本     | Rosetta Blog `v2.1.1`（`pyproject.toml:3`）                                    |
| 定位        | 前后端分离博客平台（多主题、插件、i18n 四语、OOBE 向导、SEO）                                        |
| 前端目录      | `frontend/`（Nuxt 4.5 + Vue 3 + TS + Pinia + shadcn-vue + Tailwind v4）        |
| 后端目录      | `backend/`（FastAPI + SQLAlchemy 2.0 async + Pydantic v2 + Alembic + Aiohttp） |
| 包管理（后端）   | `uv`（根目录 `pyproject.toml` + `uv.lock`）`python>=3.10`                         |
| 包管理（前端）   | `pnpm@11.20`（`frontend/package.json` packageManager 锁版本）                     |
| Nitro BFF | `frontend/server/`（RSS / Sitemap / Robots / Bing 壁纸）                |
| 运行端口约定    | 后端 `127.0.0.1:8000`、前端 Nuxt `3000`、Nginx/NAT 对外 `80/443`                     |
| 统一入口（推荐）  | 项目根：`.\dev.ps1`（Windows PowerShell）并发启前后端                                    |

***

## 1. 架构（已固定，不讨论）

```
              ┌────────────────────────────────────────────────┐
              │                    Browser                       │
              └──────────────────────┬─────────────────────────┘
                                     │ https://domain (Nginx:80)
                                     ▼
              ┌────────────────────────────────────────────────┐
              │   Nginx (deploy/nginx-site.conf)                 │
              │   /api  ──► rosetta_backend upstream :8000      │
              │   /     ──► rosetta_frontend upstream :3000     │
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

| 层级        | 技术栈                                                                                                          | 代码位置                                                                                      |
| --------- | ------------------------------------------------------------------------------------------------------------ | ----------------------------------------------------------------------------------------- |
| Web 前端    | Nuxt `4.5.2` + Vue 3 + TypeScript + Tailwind CSS v4 + shadcn-vue + Pinia 4 + @nuxtjs/i18n + zod/vee-validate | `frontend/`                                                                               |
| Nitro BFF | h3 + ohmyfetch（API 代理 · RSS/Sitemap/Robots 服务端聚合 · Bing 壁纸无 CORS 代理）                                         | `frontend/server/`                                                                        |
| 后端 API    | FastAPI `[standard]` + uvicorn `[standard]` + asyncpg / aiosqlite + Pydantic Settings                        | `backend/`                                                                                |
| ORM / 迁移  | SQLAlchemy 2.0 `[asyncio]` + Alembic `1.13+`（`backend/migrations/`）                                          | `backend/models/*` · `backend/migrations/*`                                               |
| 缓存        | Redis 8 + Memory 双后端；分布式锁 / 预热器                                                                              | `backend/core/cache*.py` · `cache_warmer.py` · `distributed_lock.py`                      |
| 认证        | PyJWT 2.10+ + argon2-cffi 24+ + bcrypt 5+ + cryptography 45+                                                 | `backend/core/auth.py` / `stores/auth.ts`                                                 |
| 国际化 i18n  | 固定四语：`zh` · `en` · `ja` · `zh_Hant`（fallbackLocale=`en`）                                                     | `frontend/i18n.config.ts` · `frontend/i18n/locales/*.json` + `frontend/i18n/index.ts` 双加载 |
| 管理端 UI    | shadcn-vue（reka-ui / radix-vue）+ Pinia + 46 个 admin 子页（`/admin/**`）                                          | `frontend/pages/admin/*` · `frontend/components/admin/*` · `frontend/components/ui/*`     |
| 测试        | 后端 pytest-asyncio 自动模式 + pytest-cov 45% fail\_under；前端 vitest 单测 happy-dom                                   | `tests/test_*.py` · `frontend/tests/unit/*.spec.ts`                                       |
| CI        | GitHub Actions（`.github/workflows/ci.yml`、`frontend/.github/workflows/ci.yml`）                                          | lint + typecheck + pytest + coverage 底线                                                   |

### 1.1 已落地的扩展系统

1. **主题系统**（WordPress 风格，2 套内建）：`frontend/themes/{editorial-wp-style,astro-paper-inspired}/`，必需 `rosetta-theme.json` + `style.css`（必须带作用域守卫）+ `screenshot.png|svg`；Customizer 字段在 `rosetta-theme.json` 内以 `mods_schema`（JSON Schema Draft-07）内联声明，mods 值存 SiteConfig KV `theme_mods:<slug>`。磁盘 ↔ DB 由「扫描」同步：非激活且磁盘已不存在的主题会被清为僵尸记录，激活主题升级前必须磁盘文件存在。
2. **插件系统**（FastAPI 侧 Hook Engine）：`backend/services/plugin_engine.py`（Bus 模式），三内建插件 `hello-rosetta` · `guestbook-rss` · `seo-toolkit`。
3. **头像代理 / 解析器**：`/api/media/avatar?src=<base64>`，白名单 302 直跳 → 非白名单流式代理 → DiceBear SVG 兜底；前端 `useResolvedAvatar`。
4. **OOBE 安装向导**：锁文件 `backend/.oobe_complete`，缺则非白名单接口返回 `503 OOBE_REQUIRED`。
5. **SEO 服务端生成**：RSS 2.0 / Sitemap / Robots 三条 Nitro Server-Route。
6. **Bing 每日壁纸 BFF**：`frontend/server/api/bing-wallpaper.get.ts`，30m SWR cache。

***

## 2. SSR 策略 & 混合渲染

### 2.1 基线

**全局 `ssr: true` + 精准反选 `ssr: false`。** 公开内容页全站 SSR 已验收。如需单页切回 SPA，写 `definePageMeta({ ssr: false })`。

### 2.2 精准反选表（Nitro routeRules）

| 路由                                            | SSR     | Cache               | 原因                               |
| --------------------------------------------- | ------- | ------------------- | -------------------------------- |
| `/admin/**` · `/admin`                         | ❌ false | `no-store, private` | 登录态 + 重交互 + localStorage       |
| `/login` · `/register` · `/oobe`              | ❌ false | `no-store, private` | 表单状态、敏感输入                        |
| `/admin/docs/**`                              | ❌ false | `no-store, private` | 内嵌 Markdown 编辑器与执行工具             |
| `/search/**`                                  | ❌ false | `no-store`          | 实时查询 + 高频率                      |
| Vite 虚拟文件：`/@vite/**` · `/@id/**` · `/@fs/**` | ❌ false | `no-store`          | 防 HMR 404 被 spa-fallback 拦截      |

### 2.3 公开页 SWR / Cache 头

首页 swr 300s · 归档/关于/友情/系列 swr 3600s · 活动/图库 swr 600s · 文章列表/分类/标签/文章详情/独立页 swr 600s · 热门榜 `/posts/hot` swr 60s · 留言板 swr 60s。全部附带 `Cache-Control: public, max-age=0, s-maxage=<T>, stale-while-revalidate=86400`。
静态资源 `/_nuxt/**` 与 `/themes/**` 使用强缓存 immutable（31536000s）。

### 2.4 SSR 安全守则（违反必出 Hydrate 错）

1. 组件 `setup()` 顶层禁止直接读 `window / document / localStorage / navigator / matchMedia`；必须包 `if (import.meta.client) { … }` 或 `onMounted`
2. `useHead` / `useState` / `useRoute` / `useRuntimeConfig` 由 **Nuxt 自动导入**；不得从 `@unhead/vue`、`vue`、`vue-router` 导入同名函数
3. 首渲染字节级一致：`ref()` 初始值两端相同；客户端独有状态在 `onMounted` 赋值或用 `useState` 序列化
4. Pinia token/user：`auth.ts` 使用 `skipHydrate`，仅在客户端写 localStorage
5. 明/暗主题首渲染：`useTheme.ts` 首帧 useState 恒为 light；`plugins/theme.client.ts` Hydrate 后才真正应用

***

## 3. 主题样式 ↔ Admin UI 解耦（四层防御）

**永远不能让前台主题样式影响后台（shadcn Card / Button / Input）。**

| 层 | 机制 | 位置 |
| - | --- | --- |
| 1 | 运行时路径检测：进入 `/admin/**` / `/oobe` 时 `clearThemeVisual`，反之 `applyThemeVisual`；`/login` / `/register`（scope=`public-auth`）允许注入主题属性/链接，frontend 守卫规则在认证页不命中 | `composables/useFrontendTheme.ts` |
| 2 | 布局主动清理：`layouts/admin.vue` 与 `layouts/default.vue` 在 `onMounted` + `watch(route)` 双节点清理 | `frontend/layouts/*.vue` |
| 3 | 全局中间件兜底：`layout-scope.global.ts` 向 `<html>` 写 `data-layout-scope="frontend"|"admin"|"public-auth"`（`/oobe` 与 `/admin/**` 同按 admin 处理，判定共用 lib `isThemeVisualExcluded`） | `frontend/middleware/layout-scope.global.ts` |
| 4 | CSS 选择器作用域守卫：主题 `style.css` 通用选择器必须最前带 `:is([data-theme="..."],[data-rosetta-theme="..."])[data-layout-scope="frontend"]` | `frontend/themes/*/style.css` |

硬红线：
- 主题 style.css **禁止**重写 `.card-surface`（它是 `main.css` 的共享类，Admin 也在用）
- Admin 保留 shadcn 原生 Tailwind 原子类，禁止为"视觉统一"套主题自定义
- 禁止给 Admin 卡片加左侧彩条 `.border-l-4 border-primary/…`

***

## 4. BaseURL 双端单源（不可散落改写）

### 4.1 环境变量别名链（优先级由高到低）

```
SSR / Nitro 侧私有：  SSR_API_BASE_URL  >  NUXT_API_BASE  >  ROSETTA_API_BASE  >  BACKEND_HOST+BACKEND_PORT  >  (开发默认 http://127.0.0.1:8000/api)
浏览器端公开：        API_BASE_URL      (同源 / 跨域填完整域名)
                         ↓ 注入为
                    runtimeConfig.public.apiBase
```

生产必须在 `.env` 中显式提供三选一或 `BACKEND_HOST+PORT`；开发缺失自动回退到 `127.0.0.1:8000/api`。

### 4.2 代码侧单源调用

| 场景 | 该用的函数/Composable | 不该用的写法 |
| ---- | ------------------- | ----------- |
| 页面/组件 setup 期数据获取（SSR 友好） | `useAPI<T>(url, { query, method, … })` | 裸 `$fetch` + `onMounted` 调（首屏白屏） |
| 用户交互/提交 | `apiFetch<T>(url, { method, body })` | 硬写 `/api/xxx` + 手写 baseURL 拼接 |
| 后台静默刷新（无 toast） | `silentApiFetch<T>(url)` | 直接 `$fetch`（401 不会自动刷新 token） |
| Nitro Server-Route 连 FastAPI | `resolveBackendEndpoint(runtime, '/blog/rss')` from `server/utils/ssr.ts` | 写死 `'http://127.0.0.1:8000/api'` 字面量 |

**路径书写铁律：** `useAPI / apiFetch / silentApiFetch / resolveBackendEndpoint` 的 URL 参数**永远不带 `/api` 前缀**；baseURL 已自带。

### 4.3 实现位置

- 浏览器侧：`frontend/composables/useApi.ts`（`resolveApiBase` · `useAPI` · `apiFetch` · `silentApiFetch`）
- Server-Route 侧：`frontend/server/utils/ssr.ts`（`resolveSsrBackendBase` · `resolveBackendEndpoint`）

***

## 5. 目录结构

```
Rosetta/
├─ backend/                          FastAPI 后端
│  ├─ main.py                        入口；CORS / CSRF / OOBE / 日志 / 速率 / 安全 / 维护 八层中间件
│  ├─ api/                           41 个 API 模块（activity … webhook）
│  ├─ core/                          基础设施（config / database / auth / cache / csrf / rate_limit / exceptions …）
│  ├─ models/                        SQLAlchemy 2.0 DeclarativeBase（blog / user / gallery / site …）
│  ├─ schemas/                       Pydantic v2 请求/响应模型 + i18n dict 工厂
│  ├─ repositories/                  Repository 层（base / post / user）
│  ├─ services/                      业务层（post_service / plugin_engine / avatar_resolver / recommendation …）
│  ├─ migrations/                    Alembic 版本化迁移
│  ├─ scripts/                       mock_data / auto_oobe / reset_admin_password …
│  ├─ plugins/                       hello-rosetta / guestbook-rss / seo-toolkit
│  └─ data/                          四语 seed_content + 市场缓存
│
├─ frontend/                         Nuxt 4.5 前端（srcDir = 根 `frontend/`，无 app/ 目录）
│  ├─ pages/                          28 个页面 + 20 条前台公开路由（SSR）+ 46 个 admin 子页（SPA）
│  ├─ components/                    共享组件 + admin/ + ui/（shadcn-vue 24 种原子组件）
│  ├─ composables/                   27 个 useXxx 组合函数
│  ├─ layouts/                       default.vue（前台）· admin.vue（后台）
│  ├─ stores/                        Pinia：auth.ts（skipHydrate）
│  ├─ middleware/                    admin.global · layout-scope.global · oobe.global
│  ├─ plugins/                       debug.client / echarts.client / error-handler.client / site-title.global / theme.client
│  ├─ server/                        Nitro BFF（routes/ + api/ + utils/ssr.ts）
│  ├─ themes/                        editorial-wp-style · astro-paper-inspired
│  ├─ i18n/locales/                  {zh,en,ja,zh_Hant}.json + .ts 工厂（唯一生效目录）
│  ├─ assets/css/main.css            Tailwind v4 变量入口；.card-surface 共享类
│  ├─ nuxt.config.ts                 SSR · runtimeConfig · routeRules · i18n
│  └─ package.json                   pnpm 11.20 packageManager 锁
│
├─ tests/                            Pytest（386+ 用例，覆盖率基线 61%，fail_under=45%）
├─ deploy/                           生产部署脚本（linux-install.sh / windows-start.ps1 / nginx-site.conf）
├─ docker/                           backend-entrypoint.sh · nginx.conf
├─ .github/workflows/ci.yml          根级 CI
├─ dev.ps1 · dev.bat                 并发启前后端
├─ .env.example · .env.production · .env.docker
├─ pyproject.toml / uv.lock
├─ docker-compose.yml · Dockerfile
└─ AGENTS.md                         本文件
```

***

## 6. 环境变量模板

| 位置 | 用途 | 必备 SSR 变量 | 必备浏览器变量 |
| ---- | ---- | ------------ | ------------- |
| `.env.example`（根） | 开发模板 | `NUXT_API_BASE=http://127.0.0.1:8000/api` · `SSR_API_BASE_URL=…` · `BACKEND_HOST/PORT` | `API_BASE_URL=/api` · `NUXT_PUBLIC_API_BASE=/api` |
| `.env.production`（根） | 生产部署 | 同三条写死 | `API_BASE_URL=/api` · `SITE_URL=https://…` |
| `.env.docker`（根） | Docker compose | `NUXT_API_BASE=http://backend:8000/api` · `SSR_API_BASE_URL=http://backend:8000/api` | `NUXT_PUBLIC_API_BASE=/api` |
| `frontend/.env.example` | 纯前端子目录 | 三别名 + 默认 127.0.0.1:8000/api | `API_BASE_URL=/api` |

***

## 7. API 响应契约

### 7.1 HTTP 成功（2xx）

```jsonc
{
  "success": true,
  "data": { /* Pydantic response_model 序列化结果 */ },
  "message": "可选人类可读提示"
}
```

### 7.2 HTTP 失败（4xx / 5xx）

```jsonc
{
  "success": false,
  "error_code": "INVALID_CREDENTIALS | OOBE_REQUIRED | VALIDATION_FAILED | THEME_MODS_INVALID | PLUGIN_ZIP_BAD_MANIFEST | …",
  "message": "人类可读错误描述",
  "errors": [ { "field": "password", "message": "密码至少 8 位", "type": "value_error" } ]
}
```

- `401` → apiFetch 自动 `refreshAccessToken`；刷新失败 → 清 login 态 → 跳 `/login`
- `503 OOBE_REQUIRED` → 前端跳 `/oobe`
- 失败**一律** toast 给用户，"静默失败"是 bug

### 7.3 i18n 字段类型规范

- 管理模块 `name / title / description` 类 i18n 字段：后端必须返回完整 dict `{zh, en, ja, zh_Hant}`，不得返回单个字符串或缺失 key
- UGC 通知（留言、评论）的 title/message：明文字符串存，禁止自动翻译

***

## 8. 命令

### 8.1 项目根（后端 / 统一启动）

```bash
uv sync                                              # 依赖安装
pwsh -File dev.ps1                                   # 推荐：并发 FastAPI(8000) + Nuxt(3000)
./dev.ps1 -NoFrontend ; ./dev.ps1 -NoBackend         # 仅后端 / 仅前端
./stop.ps1                                           # 清理子进程
uv run uvicorn backend.main:app --reload --host 127.0.0.1 --port 8000
uv run python -m backend.migrations status|upgrade|revision -m "msg" --autogenerate
uv run python -m backend.scripts.mock_data           # 示例数据
uv run python -m backend.scripts.auto_oobe           # 静默 OOBE（需 ADMIN_PASSWORD）
uv run pytest                                        # 386+ cases；覆盖率 ≥45%
uv run ruff check backend tests ; uv run ruff format --check backend tests
```

### 8.2 frontend/ 目录

```bash
cd frontend
pnpm install
pnpm dev                      # Nuxt 3000
pnpm build ; pnpm preview --host --port 3000
pnpm lint                     # 0 error；warnings == 7（vue/no-v-html 固定基线）
pnpm typecheck                # 0 TS error
pnpm test                     # 15/15 Vitest
```

### 8.3 部署

```bash
docker compose up -d                          # Docker
sudo bash deploy/linux-install.sh             # Linux 原生
powershell -ExecutionPolicy Bypass -File deploy/windows-start.ps1  # Windows
```

***

## 9. 验证清单

### 9.1 后端

```bash
uv run python -c "from backend.main import app"    # 模块导入无错
uv run python -m backend.migrations status         # 'head' == 当前版本
uv run pytest                                      # 覆盖率 ≥ fail_under=45%
curl http://127.0.0.1:8000/health                  # {"status":"healthy"}
```

- 新建/更新接口：`db.flush()` 后**必须**立刻 `await db.refresh(entity)`，否则 JSON 字段仍为字符串
- 新 API 路径必须用 `useAPI` 或 `apiFetch` 包装，不得裸写 `$fetch`

### 9.2 前端

```bash
pnpm lint          # 0 error，warnings == 7
pnpm typecheck     # 0 TS error
pnpm build         # Total ≤ 43.2 MB / gzip ≤ 9.76 MB
pnpm test          # 15/15
```

构建日志零命中：`Hydration node mismatch` · `Failed to fetch` · `/api/api` · `CORS`

### 9.3 产品验收

- 明/暗主题切换：前台 2 套 + Admin 原生均 OK；Admin 不被前台 CSS 污染
- 四语切换：zh / en / ja / zh_Hant 无 404
- SSR 关键页 `Ctrl+U`：首页、文章详情、分类、留言板有真实 HTML
- SSR 反选页：`/admin/*` · `/login` · `/oobe` · `/search/*` 是空壳 SPA

***

## 10. shadcn-vue 硬性规范

1. **Button SVG Icon**：`buttonVariants` 已声明 `[&_svg]:size-4`，Button 子树 lucide icon 不再写 `w-4 h-4 / size-*`
2. **Lucide icon 数据属性**：Label / Button / Tab / DropdownItem 中的图标必须写 `data-icon="inline-start"` 或 `data-icon="inline-end"`
3. **Gap 代替 Space**：`flex / grid` 容器用 `gap-*`，禁止 `space-x-* / space-y-*`
4. **reka-ui 绑定**：reka-ui 2.10.x 的 Switch/Checkbox 受控 prop/事件是 `modelValue` / `@update:model-value`（1.x 的 `checked`/`@update:checked` 命名已不适用，误用会导致开关状态不显示/不回写）
5. **shadcn Forms + Zod**：`useForm` 与 `FormItem / FormMessage` 配对，错误不要 toast + FormMessage 双报
6. **Admin 扁平化**：禁止给 Card / 表格行加左侧彩条

***

## 11. 编码风格 / 命名

| 对象 | 约定 |
| ---- | ---- |
| Vue 组件 | PascalCase，目录 kebab-case（`components/admin/StatCard.vue`） |
| Composable | `useXxx.ts`，导出 `useXxx()` 同名函数 |
| Pinia store | `stores/xxx.ts`；`defineStore('xxx', () => …)` setup 语法 |
| 页面路由 | `pages/**` kebab-case；动态参数 `[param].vue` / catchall `[...catchall].vue` |
| Python 模块/变量 | snake_case；类名 PascalCase；`Annotated[T, Depends(…)]` DI |
| Pydantic 字段 | 双引号；`Field(…, min_length=, max_length=, pattern=)` 显式约束 |
| SQLAlchemy model | `__tablename__ = "snake_case"`；JSON 字段用 `MutableList/MutableDict` |

Python 细节：双引号字符串；I/O 全 `async/await`；插件注册入口是**同步** `register()`。

### Conventional Commits

```
feat/fix/refactor/perf/i18n/chore/docs: 描述
```
PR 标题：`{scope}: {message}`，例如 `feat(frontend): SSR 留言板 apiFetch 化`

***

## 12. 安全红线（零容忍）

1. 密钥 / JWT `SECRET_KEY` / DB 连接串 / 邮箱密码 / GitHub PAT 必须通过 `.env`，严禁硬编码
2. SSR 顶层 setup 不得直接使用 `window / document / localStorage / navigator / matchMedia`
3. 主题 `style.css` 禁止 blanket 通用选择器（`main / header / a / h1 / .btn`），必须带作用域守卫
4. `.card-surface` 共享类禁止主题重写
5. 不得把 JWT / admin 资料以 `useState` 序列化到 HTML，用 Pinia `skipHydrate` + localStorage
6. CSP / 安全头只能更严不能更松
7. 用户上传文件：`MAX_UPLOAD_SIZE` + `ALLOWED_EXTENSIONS` 双校验；图片 Pillow verify；头像代理 SSRF 白名单

***

## 13. 不做清单（Hard Constraints）

1. ❌ 后端不迁移到 Nitro / Node.js
2. ❌ i18n 不新增 zh/en/ja/zh_Hant 以外的语言
3. ❌ SSR 不回退到全局 SPA（仅 routeRules 精准反选）
4. ❌ 不创建 `frontend/app/pages/` 与 `frontend/pages/` 双目录并存
5. ❌ 不在 Admin 页面注入前台主题 CSS 作用域
6. ❌ 不应用 Alembic autogenerate "drop all tables" 文件（立即删除，检查 env.py target_metadata）
7. ❌ 不给 Admin 卡片加彩色左侧条

***

## 14. 维护者补充

- 本文档随代码演进。发现规范与实际冲突时，修改代码或修改本规范二选一，不得长期不一致。
- 新增内建主题：`frontend/themes/{slug}/` 创建 `rosetta-theme.json + style.css + screenshot`，`style.css` 必须满足 §3 CSS 守卫。
- 新增插件：`backend/plugins/{slug}/` 创建 `rosetta-plugin.json + plugin.py`，注册入口是同步 `register(app, ctx)`。
- 新增语言：必须先在 §13.2 去掉禁止，然后同步补 `i18n.config.ts` · `i18n/locales/xx.json` · `schemas/i18n.py` · site_settings 默认值全链路。

— 本文件 v2026.09 由 Rosetta 项目组维护，对应代码基线 v2.1.1 —
