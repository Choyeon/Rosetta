# Rosetta 项目开发规范

本文档面向参与 Rosetta 项目开发的工程师与 AI 助手。开始工作前，请先阅读本文件及对应子目录的规范文件。

## 项目架构

Rosetta 是前后端分离的博客系统，采用双语言栈，各取所长：

| 层级 | 技术 | 目录 | 说明 |
|------|------|------|------|
| 前端 | Nuxt 4 + Vue 3 + TypeScript | `frontend/` | 页面渲染、交互、SSR 渐进式启用 |
| 后端 | FastAPI + SQLAlchemy 2.0 + Python 3.11+ | `backend/` | 业务逻辑、数据持久化、认证、缓存 |

### 架构决策

以下决策已固定，不再讨论：

1. 后端保留 FastAPI，不迁移到 Nitro/Node.js。现有实现含 40+ API 模块、完整的认证/缓存/迁移/定时任务体系。
2. Nuxt 从当前 SPA 模式渐进式开启 SSR，不做一次性全量切换。
3. Nitro（Nuxt Server）只作为 BFF 层：API 代理、SSR 数据聚合、轻量接口，不承载核心业务。
4. i18n 仅支持 zh / en / ja / zh_Hant 四种语言。

## 目录结构

```
Rosetta/
├── backend/               FastAPI 后端（见 backend/AGENTS.md）
│   ├── api/               API 路由模块
│   ├── core/              基础设施（配置、数据库、鉴权、缓存）
│   ├── models/            SQLAlchemy ORM 模型
│   ├── schemas/           Pydantic 请求/响应模型
│   ├── services/          业务服务层
│   └── repositories/      数据访问层
│
├── frontend/              Nuxt 4 前端（见 frontend/AGENTS.md）
│   ├── app/pages/         路由页面
│   ├── components/        Vue 组件
│   ├── composables/       组合式函数（自动导入）
│   ├── layouts/           布局
│   ├── stores/            Pinia 状态管理
│   ├── server/            Nitro BFF / 代理
│   └── i18n/locales/      语言包 JSON
│
├── tests/                 Python 后端集成测试
├── deploy/                部署脚本（Nginx / systemd）
├── docker/                Docker 配置
├── pyproject.toml         Python 依赖声明（uv）
├── uv.lock                Python 依赖锁
└── AGENTS.md              本文件
```

子目录规范：
- [backend/AGENTS.md](file:///d:/WebProjects/Rosetta/backend/AGENTS.md)
- [frontend/AGENTS.md](file:///d:/WebProjects/Rosetta/frontend/AGENTS.md)

## 前后端接口约定

### API 基础信息

- 后端统一前缀：`/api/*`
- 开发模式：Nuxt 启动时自动监听 `127.0.0.1:8000`（FastAPI）
- 前端读取：`useRuntimeConfig().public.apiBase`
- 生产部署：Nginx 将 `/api/*` 转发到 uvicorn，其余路径转发到 Nuxt

### 统一响应格式

所有 HTTP 2xx 返回统一 JSON 结构：

```json
{
  "success": true,
  "data": { "...": "..." },
  "message": "可选的描述信息"
}
```

失败时：

```json
{
  "success": false,
  "error_code": "INVALID_CREDENTIALS",
  "message": "用户名或密码错误",
  "errors": [
    { "field": "password", "message": "密码不能为空", "type": "value_error" }
  ]
}
```

字段 `data` 承载业务数据，`errors` 用于表单级字段校验错误。

### 认证

1. 登录接口返回 `access_token`（1 小时）与 `refresh_token`（7 天）
2. 请求时携带 `Authorization: Bearer <access_token>`
3. 收到 401 时前端清除本地登录态并跳转 `/login`

### OOBE 流程

首次安装时后端无 `.oobe_complete` 标记：
- `/api/*`（OOBE 与验证码除外）返回 503 + `error_code: OOBE_REQUIRED`
- 前端 middleware 检测到此错误码跳转 `/oobe`
- 完成后写入 `.oobe_complete` 与 `rosetta.json`，重启后端加载配置

## 包管理与命令

前后端使用不同的包管理器，不可混用。

### Python / 后端

从**项目根目录**执行。

```bash
uv sync                                  # 安装/同步 Python 依赖
uv run uvicorn backend.main:app --reload --port 8000   # 后端开发模式

uv run python -m backend.migrations upgrade            # 数据库迁移到最新版本
uv run python -m backend.migrations revision -m "msg" --autogenerate
uv run python -m backend.migrations status

uv run python -m backend.scripts.mock_data             # 生成测试数据
```

### JavaScript / 前端

从**frontend/** 目录执行。

```bash
pnpm install                             # 安装前端依赖
pnpm dev                                 # 开发模式（自动启动后端 FastAPI）
pnpm typecheck                           # TypeScript 类型检查
pnpm lint                                # ESLint 检查
pnpm build                               # 生产构建
pnpm preview                             # 预览构建产物
```

## 验证清单

任何代码改动提交前，按以下清单自检：

### 后端

```bash
python -c "from backend.main import app"     # 模块导入无错
uvicorn backend.main:app                     # 进程能启动
python -m backend.migrations status          # 迁移版本一致
```

手动访问 `http://localhost:8000/health` 与 `/docs`（DEBUG=true 时）。

### 前端

```bash
pnpm typecheck   # 无类型错误
pnpm lint        # 无 ESLint 错误
```

手动确认：
- 明/暗主题样式正常
- 四种语言切换后文本生效
- 移动端与桌面端布局无错位
- 浏览器控制台无 hydrate mismatch / CORS / 401 等错误

## 提交规范

使用 Conventional Commits 格式：

```
feat: 为文章详情页添加阅读进度条
fix: 修复 OOBE 第五步数据库连接检查的空指针
refactor: 将前端请求封装统一迁移到 useFetch
perf: 优化文章列表查询，消除 N+1 问题
chore: 升级 SQLAlchemy 到 2.0.32
i18n: 补全日语和繁体中文翻译
```

聚焦单一关注点，避免大而全的提交。

## 注意事项

- 不要在任何文件中硬编码密钥、生产数据库连接串、JWT secret。通过环境变量或 `.env` 注入，`.env` 已加入 `.gitignore`。
- 不要给 UI 组件的卡片加左侧彩色装饰条，设计规范要求扁平化。
- 不要在 SSR 环境的顶层作用域访问 `window` / `document` / `localStorage`；用 `import.meta.client` 守卫或 `onMounted`。
- 遇到架构层面的取舍时，先查看本规范和对应子目录规范；仍有歧义时选择与现有代码最一致的实现方式。
