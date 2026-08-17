# Rosetta 前端开发规范

前端基于 Nuxt 4.5 / Vue 3 / TypeScript / Tailwind CSS / Pinia / @nuxtjs/i18n v10。包管理器为 pnpm 11（`packageManager` 已写入 package.json），所有命令在 `frontend/` 目录下执行。

## 运行模式与 SSR 策略

当前 `nuxt.config.ts` 中 `ssr: false`，为纯 SPA 模式。项目目标为**渐进式 SSR**，页面按优先级逐个迁移，禁止一次性全量开启。

迁移顺序与策略：

| 路由 | 模式 | 缓存 | 说明 |
|------|------|------|------|
| `/` | SSR + SWR 60s | `routeRules: { swr: 60 }` | 首页 |
| `/posts/**` | SSR + SWR 300s | 同上 | 文章列表与详情（搜索引擎流量主入口） |
| `/categories/**` | SSR + SWR 300s | 同上 | 分类归档 |
| `/archive` | SSR + SWR 600s | 同上 | 时间归档 |
| `/activity` | SSR + SWR 120s | 同上 | 网站动态 |
| `/gallery` | SSR + SWR 300s | 同上 | 相册 |
| `/guestbook` | SSR + SWR 60s | 同上 | 留言板 |
| `/friends` | SSR + SWR 3600s | 同上 | 友情链接 |
| `/about` | SSR + SWR 3600s | 同上 | 关于 |
| `/admin/**` | SPA | `routeRules: { ssr: false }` | 管理后台（依赖登录态，且搜索引擎无需索引） |
| `/login`, `/register` | SPA | 同上 | 认证页面 |
| `/oobe` | SPA | 同上 | 安装向导（需要与后端频繁交互，且流程依赖客户端状态） |

迁移单个页面时，先打开该路由的 SSR，修复其 hydrate/SSR 特有问题，通过后再处理下一个。不要在一次提交中打开所有路由。

## 目录结构与使用约定

由于历史原因，`app/` 与根目录同时存在部分目录。**新增文件按以下规则放置**，不要继续扩充重复目录。重复目录中的文件在后续重构中会被逐步合并。

| 类型 | 放置位置 | 备注 |
|------|----------|------|
| 页面路由 | `app/pages/` | 当前生效位置；与 nuxt.config.ts 中的 `dir: { layouts, plugins }` 共存。 |
| 业务组件 | `components/` | 根目录，不含 `pathPrefix`，直接 `<AppHeader />` 使用。 |
| UI 原子组件 | `components/ui/<name>/` | shadcn-vue 风格，由 CLI 生成，通常不要手动编辑。 |
| 组合式函数 | `composables/` | 命名 `useXxx.ts`，Nuxt 自动导入（递归两层）。 |
| 布局 | `layouts/` | 根目录，`default.vue` 前台通用，`admin.vue` 后台专用。 |
| Pinia stores | `stores/` | 仅放跨页面共享状态；页面私有数据留在组件内。 |
| Nitro BFF / 代理 | `server/api/` 与 `server/plugins/` | BFF 聚合层、SWR 缓存、开发模式后端启动。 |
| i18n 语言包 | `i18n/locales/{zh,en,ja,zh_Hant}.json` | 根目录旧 `locales/` 已废弃，不要写入。 |
| i18n 运行时配置 | `i18n/index.ts` | 由 `nuxt.config.ts` → `i18n.vueI18n: './index.ts'` 引入（相对 `i18n/`）。 |
| 类型定义 | `types/` | 前端自定义 TS 类型；API 返回类型后续由 OpenAPI 生成。 |
| 工具函数 | `lib/utils.ts` | 纯函数工具；UI 逻辑放 composables。 |
| 全局 CSS | `app/assets/css/main.css` | 由 `css: ['~/assets/css/main.css']` 引入。 |
| Nuxt 插件 | `plugins/` | 根目录；主题初始化使用 `.client.ts` 后缀表示仅客户端执行。 |
| 路由中间件 | `app/middleware/` | 目前 OOBE 守卫位于此；后续可迁移到根目录 `middleware/`。 |
| 静态资源 | `public/` | favicon、logo、manifest，直接以 `/` 根路径访问。 |

引用路径：
- `~/assets/*` → 解析到 `app/assets/*`
- `~/components/*` → 解析到根 `components/*`
- `~/*` 其余 → 相对 `frontend/` 根目录

## 组件与脚本

### SFC 标准写法

```vue
<script setup lang="ts">
// 自动导入：ref、useState、useHead、useFetch、useI18n、useToast 等
// 如需 props / emits：
const props = defineProps<{ title: string; createdAt?: Date }>()
const emit = defineEmits<{ (e: 'update', v: string): void }>()

const { t } = useI18n()
const config = useRuntimeConfig()

// 数据获取：公开页面用 useFetch（SSR 友好）
const { data: posts, pending, error, refresh } = await useFetch<Post[]>(
  '/api/blog/posts',
  {
    baseURL: config.public.apiBase,
    key: 'posts-index-page-1',   // 提供稳定 key 便于缓存
    default: () => [],           // SSR/客户端水合前的默认值
    server: true,                // 在服务端执行
    lazy: false,                 // 路由导航前等待数据
  }
)
</script>

<template>
  <div class="container mx-auto p-4">
    <h1 class="text-2xl font-semibold">{{ t('posts.title') }}</h1>
    <PostCard v-for="p in posts" :key="p.id" :post="p" />
  </div>
</template>
```

### SSR 环境下的客户端特有 API

以下内容必须用 `if (import.meta.client)` 或 `onMounted` 包裹，否则在 Node 侧报 `window is not defined`：

- `window` / `document` / `navigator` / `localStorage` / `sessionStorage`
- `matchMedia`、剪贴板 API、Web Audio、Canvas、拖拽
- 第三方脚本（如 viewerjs、代码高亮、主题切换 DOM 操作）

推荐模式：

```ts
const mounted = ref(false)
onMounted(() => { mounted.value = true })
const theme = useState<'light' | 'dark'>('theme-mode', () => 'light')
if (import.meta.client) {
  theme.value = document.documentElement.dataset.theme as any || 'light'
}
```

`useFetch` 内部会自动在 SSR 侧携带由 Nitro 转发的 cookie；认证类接口显式传 `server: false` 避免服务端无登录态时错误。

```ts
// 只在客户端请求的接口示例
const { data: me } = await useFetch<User>('/api/users/me', {
  baseURL: config.public.apiBase,
  server: false,
  immediate: false,
})
```

### 主题切换

`composables/useTheme.ts` + `plugins/theme.client.ts` 配合实现：
- 持久化：`localStorage.theme` 只允许 `'light'` / `'dark'`；若检测到 `'system'` 或未知值，按系统外观迁移为具体值。
- 切换动效：clip-path 圆形扩散（light→dark 从点击点扩展；dark→light 收缩到点击点），960ms，`cubic-bezier(0.22,1,0.36,1)`。
- 语义色统一：明/暗主题均以 `--bg` / `--fg` / `--primary` 等 CSS 变量暴露，业务代码只引用变量，不写具体色号。

### i18n

模板内：`{{ $t('posts.readingTime', { n: minutes }) }}`

脚本内：
```ts
const { t, locale, setLocale } = useI18n()
```

支持语言：`zh` / `en` / `ja` / `zh_Hant`。新增翻译时四个 JSON 同步补全，缺键会在运行时 fallback 到默认语言（zh），但仍应补齐以免 QA 时发现。

向后端传递语言：通过 `rosetta_lang` cookie（`zh_CN → zh`，`zh_TW → zh_Hant`）。语言变更时发出全局事件 `rosetta-lang-change`，动态内容组件监听后重新拉取数据。

## 状态管理

全局状态走 Pinia（`stores/auth.ts` 为现有示例），但**不要滥用**：

- 用户登录态、权限、语言 → store
- 页面级搜索条件、分页 → 页面内 `ref` + `useState`（后者跨 SSR 水合）
- 表单临时值 → 组件内部 `ref` / `reactive`

store 中禁止直接发起请求；把请求逻辑封装到对应的 composable（`useUsers`、`usePosts` 等），store 只保存结果。

## API 请求封装

`composables/useApi.ts` 是统一入口：
- 自动注入 `Authorization: Bearer <token>`
- 统一错误处理（失败时调用 toast，401 跳转登录）
- 与后端返回的 `{ success, data, message, error_code }` 契约匹配

当需要 SSR 预取数据时，**不要在 composable 里返回裸 Promise**，改为在页面中直接用 `useFetch` 调用，这样 SSR 阶段序列化的 payload 会被客户端复用，避免二次请求。

后续可在 `server/api/[...].ts` 增加 Nitro 反向代理，使前端统一请求同源 `/api/*`，消除 CORS 与 cookie 跨域问题。

## UI 约定

- 主色调为青蓝色（sky），具体由 `useThemePalette.ts` 的语义色暴露，组件不写固定色号。
- 扁平化设计：所有卡片不使用左侧彩色装饰条、不使用渐变外框、不使用厚重阴影。
- 标签样式：淡色胶囊底 + 原色文字，无边框、无阴影、hover 仅改变背景色，不做位移或缩放。
- 动画：hover 反馈轻量；页面切换使用 `useMotion.ts` 中统一的 motion，避免每个页面重写过渡。
- 深色模式：所有页面在明暗主题下都需验证；暗色模式下不使用显式边框来表达分隔，使用对比度不同的背景层次。
- 响应式：默认桌面设计，但 `md:` 断点以下保证可用；按钮/输入框/图标按钮触碰区域不小于 24px。

## 性能与安全

- 长列表（>100 项）考虑分页或虚拟滚动。
- 大体积依赖异步加载：vue-advanced-cropper、viewerjs、代码高亮用 `defineAsyncComponent` 或 `onMounted` 后再加载。
- 图片必须加 `width` / `height` 防止 CLS；相册页已用 viewerjs，后续可接入 Nuxt Image。
- 用户生成内容（Markdown、评论）渲染时走标记库自带的 sanitize 选项，禁止直接 `v-html` 信任原始字符串。
- 密钥 / token / 内部服务地址不进前端源码；统一走 `runtimeConfig`（public 或私有）。
- 不要在 localStorage 保存 JWT；后续升级为 httpOnly cookie。当前临时方案下，XSS 风险下最小化存留时间。

## 开发与验证命令

```bash
pnpm install
pnpm dev                  # 启动开发服务器。端口冲突时修改 process.env.PORT
pnpm typecheck            # vue-tsc，发现 SSR 水合/类型问题
pnpm lint                 # ESLint
pnpm build && pnpm preview
```

`pnpm dev` 会通过 `server/plugins/spawn-backend.ts`（在 nuxt.config.ts 中作为内联模块）在后台启动 FastAPI。若 8000 端口已有进程在监听，则复用现有服务，避免重复 spawn。

提交前必须通过 `pnpm typecheck` 和 `pnpm lint`。此外，对涉及 SSR 水合的变更，在浏览器控制台检查：
- 无 Hydration node mismatch
- 无重复请求（SSR payload 未被正确复用时会发生）
- 明/暗主题切换无闪烁或布局跳动

## 常见问题

- **Hydration mismatch 提示 text 内容不一致**：通常因为 `ref()` 默认值在 SSR 和客户端不同。使用 `useState` 或 `useFetch` 的 `default()` 来保持一致。
- **SSR 阶段登录态缺失**：对需要用户态的接口传 `server: false`；或者在 Nitro 代理层注入从请求头读出的 cookie。
- **目录重复导致组件无法解析**：优先使用根目录 `components/`、`layouts/`；`app/` 下同名旧组件后续会被清理，不要新增。
- **旧的 `locales/` 与 `i18n/locales/` 同时存在**：i18n 配置只认后者，新增翻译不写入前者。
- **语言切换后动态内容未刷新**：确保对应 composable 监听了全局 `rosetta-lang-change` 事件并重新拉取。
