# Rosetta 项目快速参考

面向 AI 编程助手的速查卡片。更完整的说明见 [AGENTS.md](file:///d:/WebProjects/Rosetta/AGENTS.md) 及各子目录下同名文件。

## 架构

- 前端：Nuxt 4.5 / Vue 3 / TS，位于 `frontend/`，**渐进式开启 SSR**，不一步到位。
- 后端：FastAPI / SQLAlchemy 2.0 async / Python 3.11+，位于 `backend/`，**禁止重写为 Nitro/Node.js**。
- Nitro（Nuxt Server）只做 BFF：API 代理、SSR 数据聚合。核心业务留在 FastAPI。
- i18n：仅 zh / en / ja / zh_Hant，不新增俄语或韩语。

## 关键文件

| 目的 | 路径 |
|------|------|
| 后端入口与路由装配 | `backend/main.py` |
| 后端配置（环境变量/Setting） | `backend/core/config.py` |
| 后端数据库与会话 | `backend/core/database.py` |
| 后端 JWT 与依赖注入别名 | `backend/core/auth.py` |
| 后端缓存（Redis/Memory 双后端） | `backend/core/cache.py` |
| 后端 OOBE 中间件与锁文件判定 | `backend/main.py` 的 `oobe_middleware` |
| 前端 Nuxt 配置 | `frontend/nuxt.config.ts` |
| 前端 CSS 入口 | `frontend/app/assets/css/main.css` |
| 前端 API 封装 | `frontend/composables/useApi.ts` |
| 前端主题切换 | `frontend/composables/useTheme.ts` + `frontend/plugins/theme.client.ts` |
| 前端 OOBE 守卫 | `frontend/app/middleware/oobe.global.ts` |
| 前端全局布局 | `frontend/layouts/default.vue` / `admin.vue` |
| 前端 Pinia 登录态 | `frontend/stores/auth.ts` |
| i18n 语言包 | `frontend/i18n/locales/{zh,en,ja,zh_Hant}.json` |
| i18n 配置 | `frontend/i18n.config.ts` + `frontend/i18n/index.ts` |
| 后端 API 路由目录 | `backend/api/*.py` |
| Alembic 迁移 | `backend/migrations/versions/*.py` |
| pytest 测试 | `tests/test_*.py` |
| Python 依赖 | `pyproject.toml` + `uv.lock` |
| JS 依赖 | `frontend/package.json` + `pnpm-lock.yaml` |

## 常用命令

### 后端（项目根目录执行）

```bash
uv sync                                                        # 同步依赖
uv run uvicorn backend.main:app --reload --port 8000          # 开发启动
uv run python -m backend.migrations upgrade                   # 应用迁移
uv run python -m backend.migrations revision -m "msg" --autogenerate
uv run python -m backend.migrations status                    # 迁移版本核对
uv run python -m backend.scripts.mock_data                    # 写入示例数据
```

提交前最小验证：
```bash
python -c "from backend.main import app"
```

### 前端（frontend/ 目录执行）

```bash
pnpm install          # 安装依赖
pnpm dev              # 启动开发服务器（自动 spawn 后端）
pnpm typecheck        # 类型检查
pnpm lint             # ESLint
pnpm build && pnpm preview
```

## 前后端通信

- API 基地址从 `useRuntimeConfig().public.apiBase` 读取，禁止硬编码。
- 默认开发模式：`http://localhost:8000/api`。
- 所有响应结构：`{ success, data?, message?, error_code?, errors? }`。
- 401 → 前端清登录态跳转 `/login`。
- 503 + `error_code: OOBE_REQUIRED` → 前端跳转 `/oobe`。

## SSR 注意事项（前端）

- 公开页面逐步启用 SSR；后台 / login / register / oobe 保持 `ssr: false`。
- 顶层 setup 禁止直接使用 `window / document / localStorage`；用 `if (import.meta.client)` 或 `onMounted` 包裹。
- 数据获取优先 `useFetch`（SSR 友好，自动缓存与序列化），避免裸 `$fetch + onMounted` 导致客户端重复请求。
- `useHead` 来自 Nuxt 自动导入，不要单独从 `@unhead/vue` 导入。

## 编码风格摘要

- Python：PEP 8，双引号字符串，Pydantic `Field(...)` 显式约束，全部 `async/await` I/O，使用 `Annotated[T, Depends(...)]` 风格注入依赖。
- 提交信息：`feat: fix: refactor: perf: chore: docs: i18n:` 等 Conventional Commits。
- 命名：组件 PascalCase，composable 名 `useXxx.ts`，页面文件 kebab-case，Python 模块/变量 snake_case。

## 常见陷阱

- Nuxt 4 中 `app/pages/` 与根目录 `pages/` 同时存在会引发混淆；新项目文件一律按 `frontend/AGENTS.md` 指定的位置放置。
- `locales/` 与 `i18n/locales/` 两份语言包目录并存，实际生效的是 `i18n/locales/`。
- OOBE 未完成时后端跳过 DB 初始化；若直接访问非白名单接口必返回 503，不要误判为服务故障。
- SSR 水合不匹配（hydration mismatch）多来自客户端独有 `ref` 初始值，请用 `useState` 或 `default: () => ...` 保证 SSR/客户端值一致。

## 禁止事项

- 禁止重写 FastAPI 后端为 Node.js/Nitro。
- 禁止一次性全量打开 SSR 后提交大量错误修复；按页面渐进式迁移。
- 禁止新增 ru/ko 等已移除语言。
- 禁止在前端存储 JWT 明文、生产密钥或任何 .env 敏感信息到仓库。
- 禁止给卡片组件加左侧彩色条，设计要求扁平化。
