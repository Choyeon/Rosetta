# Rosetta 前端速查

完整规范见 [frontend/AGENTS.md](file:///d:/WebProjects/Rosetta/frontend/AGENTS.md)。本文件为 AI 助手常见操作准备的索引。

## 工程信息

- 框架：Nuxt 4.5 + Vue 3 + TypeScript
- 样式：Tailwind CSS v3（配合 shadcn-vue 风格组件，位于 `components/ui/`）
- 状态管理：Pinia 2
- i18n：@nuxtjs/i18n v10，仅 `zh / en / ja / zh_Hant` 四种语言
- 包管理：pnpm 11
- 开发模式下自动启动后端 FastAPI（见 `nuxt.config.ts` 内 `spawnBackendModule`）

## 关键文件

| 内容 | 路径 |
|------|------|
| Nuxt 主配置（modules / runtimeConfig / routeRules / ssr） | `frontend/nuxt.config.ts` |
| i18n 模块配置（locales/langDir/vueI18n） | `frontend/i18n.config.ts` |
| VueI18n 初始化（messages / pluralRules / datetime 等） | `frontend/i18n/index.ts` |
| 四种语言包 JSON | `frontend/i18n/locales/{zh,en,ja,zh_Hant}.json` |
| Tailwind 配置（主题色、语义色） | `frontend/tailwind.config.ts` |
| CSS 入口（CSS 变量、语义色、按钮覆盖） | `frontend/app/assets/css/main.css` |
| 根 app 容器（布局选择 + SSR 兼容水合） | `frontend/app/app.vue` |
| 前台布局 | `frontend/layouts/default.vue` |
| 后台布局 | `frontend/layouts/admin.vue` |
| 全局路由中间件（OOBE 守卫） | `frontend/app/middleware/oobe.global.ts` |
| 主题切换逻辑（clip-path 动效 + 持久化） | `frontend/composables/useTheme.ts` |
| 主题色调色板切换 | `frontend/composables/useThemePalette.ts` |
| 统一 API 请求封装 | `frontend/composables/useApi.ts` |
| 文章/博客相关 composables | `frontend/composables/usePosts.ts` |
| 认证相关 composables + 当前用户 | `frontend/composables/useUsers.ts` |
| 核心设置（站点配置、导航、友链） | `frontend/composables/useCore.ts` |
| 后台封装 | `frontend/composables/useAdmin.ts` |
| 评论 / 留言板 / 相册 / 媒体 / Bing 壁纸 / 公告 / Hero / 阅读 UX / OOBE / Toast / 语言切换 | `frontend/composables/*.ts` |
| Pinia 登录态 store | `frontend/stores/auth.ts` |
| 全局工具（cn/clsx merge 等） | `frontend/lib/utils.ts` |
| 主题 client 插件（水合前应用主题，避免 FOUC） | `frontend/plugins/theme.client.ts` |
| 前台导航栏 | `frontend/components/AppHeader.vue` |
| 前台页脚 | `frontend/components/AppFooter.vue` |
| OOBE 专用导航栏（仅 logo + 语言 + 主题） | `frontend/components/OOBENavbar.vue` |
| 后台侧边栏 | `frontend/components/AdminSidebar.vue` |
| 后台顶栏 | `frontend/components/AdminHeader.vue` |
| 语言切换 UI | `frontend/components/LocaleSwitcher.vue` |
| 主题切换按钮 | `frontend/components/ThemeToggle.vue` |
| 调色板切换 | `frontend/components/ThemePaletteSwitcher.vue` |
| 头像裁剪弹窗组件 | `frontend/components/AdminAvatarCropper.vue` |
| shadcn 组件 Barrel 导出 | `frontend/components/ui/*/index.ts` |
| 页面路由实际目录 | `frontend/app/pages/**` |
| API 类型声明（后续自动生成） | `frontend/types/api.ts` |
| 调试插件（仅开发环境 console 信息） | `frontend/plugins/debug.client.ts` |

## 命令

在 `frontend/` 目录下执行：

```bash
pnpm install            # 安装依赖
pnpm dev                # 开发模式。默认 3000 端口，并 spawn FastAPI 8000
pnpm typecheck          # 提交前必须通过
pnpm lint               # 提交前必须通过
pnpm build              # 生产构建
pnpm preview            # 预览生产构建
```

## SSR 渐进式开启步骤

1. 打开 `nuxt.config.ts`，设置 `ssr: true`。
2. 在 `routeRules` 中按页面打开 SSR。公开页面先开，login/admin/oobe 保持 `ssr: false`。
3. 逐个页面修复：
   - 顶层 `window / document / localStorage` 用 `if (import.meta.client)` 或 `onMounted` 守卫
   - 数据获取改为 `useFetch`（传 `key`、`default`、`server`）
   - 登录态接口显式 `server: false`
   - UI 组件若纯客户端依赖，用 `<ClientOnly>` 包裹或封装成 `.client.vue`
4. 打开目标页面，控制台无 hydration mismatch 才算完成该页面。
5. 在 `pnpm typecheck` 通过后提交。

## useFetch 模板

```ts
const config = useRuntimeConfig()
const { data, pending, error, refresh } = await useFetch<DataShape>('/api/blog/posts', {
  baseURL: config.public.apiBase,
  key: 'stable-cache-key',
  default: () => [],
  server: true,          // 公开页面 true；登录相关 false
  lazy: false,           // SEO 页面 false
  // 如需手动触发：immediate: false，并在点击事件中 await refresh()
})
```

不要在页面中写成 `onMounted + $fetch` 组合——SSR 阶段不会执行，客户端重复请求，且丢失 SEO 预取。

## 目录与命名速查

| 新增什么 | 放到哪里 | 命名 |
|----------|----------|------|
| 页面 | `app/pages/...` | `my-page.vue` 或动态路由 `[slug].vue` |
| 组件 | `components/` | `PascalCase.vue`，不要带前缀 `Base`/`App` 除非全局通用 |
| UI 原子组件 | `components/ui/<name>/` | 保持 shadcn 结构 |
| Composable | `composables/` | `useFeatureName.ts` |
| 纯函数工具 | `lib/utils.ts`（加函数）或同目录新 `.ts` | `camelCase.ts` |
| Pinia store | `stores/` | `feature.ts`（导出 `useFeatureStore`） |
| BFF 聚合接口 | `server/api/feature.get.ts` / `.post.ts` | 路径即路由 |
| Nitro 插件 / 钩子 | `server/plugins/*.ts` | 驼峰描述意图 |
| Nuxt 插件 | `plugins/` | 仅客户端的加 `.client.ts`，仅 SSR 的加 `.server.ts` |
| 路由中间件 | `app/middleware/`（目前），后续可迁移到根 `middleware/` | 全局后缀 `.global.ts` |
| i18n 翻译 | `i18n/locales/{zh,en,ja,zh_Hant}.json`，四份同步 | 键名 `module.section.message` |

## i18n 日常使用

```vue
<script setup lang="ts">
const { t, locale } = useI18n()
const greeting = computed(() => t('posts.readingTime', { n: 5 }))
</script>

<template>
  <h1>{{ $t('common.home') }}</h1>
  <p>{{ greeting }}</p>
</template>
```

切换语言后，需要重新拉取的动态内容组件，监听全局事件 `rosetta-lang-change`（由 `LocaleSwitcher` 发出）。

## 提交前验证清单

```
[ ] pnpm typecheck 通过
[ ] pnpm lint 通过
[ ] 页面在明/暗主题下无明显样式错误
[ ] zh / en 切换后新增文案有翻译
[ ] 路由在移动端无横向滚动
[ ] 浏览器控制台无 CORS / Hydration / 401 / 404
[ ] 如涉及 SSR：首次加载时 Network 面板里 HTML 已包含渲染文本（非客户端二次注入）
```

## 常见坑

- `ssr: false` 时仍把文件放错目录：新页面一律 `app/pages/`，新组件 `components/`。
- `i18n.config.ts` 中 `vueI18n: './index.ts'` 相对 `i18n/` 目录解析，不是相对 `frontend/`。
- `@nuxtjs/i18n` 与 TypeScript 严格模式下，`composables/i18n.ts` 承担自动导入桥梁，不要删除。
- 登录态用 Cookie 存储，但后端 OOBE 未完成会把所有 `/api/*` 503。此时所有 composable 的 API 调用应失败并走 OOBE 跳转，不要误判为鉴权逻辑挂了。
- `useRuntimeConfig().public.apiBase` 只有在 SSR 环境才从 `process.env.API_BASE_URL` 读取；开发时直接改 `.env` 即可覆盖。
- 主题切换存储 `localStorage.theme` 仅允许 `light | dark`；若历史遗留为 `system`，`plugins/theme.client.ts` 会把它迁移为具体值。
- BackToTop 和 LanguageSwitcher 等组件在多个布局中被显式 import；不要删除这些显式 import，Nuxt 的自动导入在某些 SSR 水合边界下有解析失败的已知问题。
