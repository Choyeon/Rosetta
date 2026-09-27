# Rosetta 前端开发规范

前端栈：Nuxt 4.5 / Vue 3 / TypeScript / Tailwind CSS v4 / shadcn-vue / Pinia / @nuxtjs/i18n v10。
包管理器 pnpm 11（`package.json` 中 `packageManager` 已固定），所有命令在 `frontend/` 目录执行。

> 跨域规则（SSR 策略、BaseURL、主题解耦、API 契约）见根 `AGENTS.md`。本文档聚焦前端编码细节。

## 运行模式与 SSR 策略

`nuxt.config.ts` 中 `ssr: true`（**全局 SSR 基线**），仅以下路由精准反选为 SPA：
- `/admin/**`（登录态 + 重交互 + localStorage）
- `/login` / `/register`（表单状态、敏感输入）
- `/admin/docs/**`（内嵌 Markdown 编辑器）
- `/search/**`（实时查询）

`/oobe` **不在**反选之列：它保留 SSR，只设 `swr:false + no-store`——安装完成后 `middleware/oobe.global.ts` 要做 SSR 级 302，`ssr:false` 会让 Nitro 直接吐空壳、不走 middleware SSR 分支（表现为白屏挂死）。

如需单页临时切回 SPA：`definePageMeta({ ssr: false })`。

### 导航必须是真 SPA（硬约束）

公开页之间点导航**只允许**换页组件，不允许重载整文档：`<NuxtPage page-key="fullPath" />`
（`app.vue`）已经覆盖"同组件不同参数（`/posts/a → /posts/b`）实例被复用、内容不换"这一类
问题，代价只有页组件重建，`<NuxtLayout>`（顶栏/页脚/侧栏）保持挂载。

因此禁止：

- ❌ 给 `app.vue` 里的 `<NuxtLayout>` 外层再加 `:key` 屏障（历史上是
  `__navSlotBusterKey` + `plugins/03-global-page-render-tick.client.ts`，每次导航
  把 layout+page 整体 unmount/remount，等价于整页重载：滚动复位、顶栏重建、图片重请、
  主题 link 重建 → 用户看到"闪一下默认样式再重新加载"。已删除）
- ❌ 在 `router.afterEach` / `page:finish` 里用 `window.location.replace` 兜底
  （历史上是 `plugins/04-route-hard-fallback.global.client.ts`，判据是 h1/title 文本 diff，
  首页在默认主题下本就没有 `<h1>`，误判率极高，每条导航都被硬重载。已删除）
- ❌ 新增"检测 DOM 没变就重载"的客户端插件

若再遇到"URL 变了内容不变"，先定位到具体路由与组件（多半是该页 `useAPI` 的 key 没跟随
参数、或 `<Suspense>` 数据链断了），修那一处，不要加回全局屏障。
`plugins/02-hydration-safety.global.client.ts` 只在真实抛错（`vue:error` 命中 hydration
级联特征）时做**有界软重挂**（每文档上限 2 次，预算耗尽如实暴露错误），正常导航不介入。

### 禁止把吞错的"逃生舱"插件加回来（硬约束）

历史上存在过 `plugins/00-spa-global-error-escape-hatch.global.client.ts` 与
`plugins/05-safe-console-error-downgrade.global.client.ts`（以及旧版 02），它们通过
覆写 `window.onerror`、按消息子串吞 `unhandledrejection`、改写
`window.__NUXT_DATA__.serverRendered`、`eval('clearError')` 复活 App 等手段让控制台
"看起来干净"。这些全部是**欺骗性掩盖**，已于 2026-09 拆除，禁止任何形式的回归：

- 插件期改写 `serverRendered` 是 no-op —— nuxt/dist/app/entry.js 在 `applyPlugins()`
  **之前**就用它决定 hydrate/mount；真正生效的是 HTTP 层
  `server/plugins/spa-serverrendered-zero.nitro.ts`
- `window.onerror` 直接赋值会被 `error-handler.client.ts` 冲掉，本就不是可靠拦截点
- 吞错让真实的水合缺陷静默累积，等到以白屏/数据错乱形式爆发时已失去定位能力

Hydration / setRef 崩溃的**真实修复点**（都在构建/服务端层，改动请去这几处）：
- vite 插件 `rosetta-vue-setref-nullsafe`（Vue setRef 父链 null-safe，`nuxt.config.ts`）
- vite 插件 `rosetta-lucide-ssr-fix`（SSR lucide 图标 first-child 与客户端同构，消除 mismatch 源）
- nitro 插件 `spa-serverrendered-zero`（ssr:false 空壳页不再进 hydrate 分支）
- `app.pageTransition` 禁用 `mode:'out-in'`（SSR 首帧 Comment 占位是 mismatch 源）

## 目录与文件放置规则

| 类型 | 路径 | 备注 |
|------|------|------|
| 页面路由 | `pages/` | **唯一有效位置**，禁止创建 `app/pages/` |
| 业务组件 | `components/` | Nuxt 自动导入 |
| UI 原子组件 | `components/ui/<name>/` | shadcn-vue 生成，不手动编辑 |
| Admin 组件 | `components/admin/` | AdminPageHeader / StatCard / AdminDataTable … |
| 组合式函数 | `composables/` | `useXxx.ts`，自动导入两层 |
| 布局 | `layouts/` | `default.vue` 前台 / `admin.vue` 后台 |
| Pinia stores | `stores/` | 仅跨页面共享状态 |
| Nitro BFF | `server/api/` + `server/routes/` | API 代理 / RSS/Sitemap/Robots |
| i18n 语言包 | `i18n/locales/{zh,en,ja,zh_Hant}.json` | **唯一生效目录**，根 `locales/` 已废弃 |
| 主题目录 | `themes/{slug}/` | 每个主题一个目录，`rosetta-theme.json` + `style.css` |
| 全局 CSS | `assets/css/main.css` + `assets/css/admin-ui.css` | main.css = 主题中性基础设施（令牌/prose/`.card-surface` 中性基座）；admin-ui.css = Admin 冻结装饰层（锁 `data-layout-scope="admin"`） |
| 路由中间件 | `middleware/` | Nuxt 自动注册 |

引用别名：`@/*` 与 `~~/*` 双前缀同时生效。

### 后台页面排版约定（强制）

1. 页头一律用 `<AdminPageHeader :title :description :icon>`，`#actions` 插槽放主操作按钮
2. 页面根容器不要重复写 `p-6 / p-4`（`layouts/admin.vue` 的 `<main>` 已是 `p-4 md:p-6`），统一 `flex flex-col gap-5`
3. 主操作按钮 `size="sm"`，图标按钮 `size="icon-sm"` + `Tooltip`
4. 二次确认用 `<AdminConfirmDialog>`，不要手写 Dialog
5. 列表页复用 `<AdminDataTable>` + `<AdminFilterBar>` + `<AdminPagination>`

### 后台接口层约定（强制）

1. **单源**：`/admin/**` 与后台用到的业务端点，请求函数一律写在 `composables/useAdminManage.ts`，页面只 import wrapper。页面内再写一遍 `apiFetch('/同一个路径')` = 重复契约（历史上 cache / import-export / seo / user-role 各有一份），要么删 wrapper 要么改页面，二者不得并存。
2. **错误必须外泄**：wrapper 一律走 `apiFetch`（失败即 reject），**禁止**用 `silentApiFetch` + `catch` 把失败降级成"看起来像成功的空值/默认值"——那会让"后端宕机"显示成"已是最新"或"没有数据"。`silentApiFetch` 仅用于纯装饰数据（文章页相似推荐、上/下一篇）。
3. **`AdminToolRequestOptions`**：`{ silentToast?: boolean }` 统一控制是否由 wrapper 弹 toast。轮询 / 首屏静默加载传 `{ silentToast: true }`，页面自己渲染 `role="alert"` 错误条 + 重试按钮；用户主动触发的写操作保持默认 toast。
4. **响应信封**：后端只在**失败**时返回 `{success:false,error_code,…}`；列表/详情返回裸对象。唯一例外是 `GET /seo/sitemap-check` 与 `migration` 的任务接口手工返回 `{success,data}`/`{success,job}`，对应 wrapper 在内部解包并在数据缺失时 throw。
5. **初始化错误要可见**：任何写进 `xxxError` 的失败，其展示节点不能嵌在 `v-if="该次请求的产物"` 里面——首次加载就失败时产物为 `null`，banner 永远不渲染。初始化错误用独立状态 + `v-else-if` 分支（见 `pages/admin/tools/migrations.vue` 的 `jobInitError`）。

## 三层 CSS 分工（2026-09 主题解耦架构）

| 位置 | 内容 | 允许写 |
|------|------|--------|
| `assets/css/main.css` | 主题中性基础设施 | Tailwind 入口、@theme 令牌、`:root`/`.dark` 语义色板、palette-*、prose-shadcn、toast、动效工具、`.card-surface` **中性基座版**（素色+细边框）；**禁止**新增任何"皮肤"装饰 |
| `assets/css/admin-ui.css` | Admin 冻结设计系统 | 装饰版玻璃卡 / 彗星发光描边 / lift-hover，每条选择器必须以 `html[data-layout-scope="admin"]` 开头；与主题包零依赖 |
| `themes/{slug}/style.css` | 主题完整皮肤 | 通用规则必须加 `[data-layout-scope="frontend"]` 守卫；认证页定制必须显式用 `[data-layout-scope="public-auth"]` 守卫，禁止 blanket 规则。默认主题 editorial-wp-style 自带全套装饰层（Admin 观感不受其影响） |

## 主题解耦机制（四层防御）

1. **CSS 层**：主题 style.css 全部规则按 scope 守卫（`frontend` / `public-auth`），Admin 永不加载主题文件
2. **运行时层**：`useFrontendTheme.ts` 的 `applyThemeVisual(path)` 检测路由 → `/admin /oobe` 调用 `clearThemeVisual()`；`/login /register`（scope=public-auth）允许注入 slug 属性 + `<link>`，但 frontend 守卫规则在认证页不命中，主题若要定制认证页必须显式写 public-auth 段落
3. **布局层**：`layouts/admin.vue` onMounted + watch(route) 清理并写 `data-layout-scope=admin`
4. **中间件层**：`middleware/layout-scope.global.ts` 兜底（仅 admin 做 DOM 轻量清理）

## SFC 标准写法

```vue
<script setup lang="ts">
const { t } = useI18n()

// SSR 友好的数据获取 —— 用 useAPI，不要裸写 $fetch
const { data: posts, pending } = await useAPI<Post[]>('/blog/posts', {
  query: { page: 1, per_page: 10 }
})
</script>

<template>
  <div class="container mx-auto px-4 py-8">
    <h1 class="text-2xl font-semibold">{{ t('posts.title') }}</h1>
    <PostCard v-for="p in posts" :key="p.id" :post="p" />
  </div>
</template>
```

## SSR 环境下的客户端特有 API

必须用 `if (import.meta.client)` 或 `onMounted` 包裹：
- `window` / `document` / `navigator` / `localStorage` / `sessionStorage`
- `matchMedia` / 剪贴板 / Web Audio / Canvas / 拖拽
- 第三方脚本（viewerjs、代码高亮、主题切换 DOM 操作）

```ts
const theme = useState<'light' | 'dark'>('theme-mode', () => 'light')
if (import.meta.client) {
  theme.value = document.documentElement.dataset.theme as any || 'light'
}
```

## 主题切换

`composables/useTheme.ts` + `plugins/theme.client.ts`：
- localStorage 持久化（`light` / `dark`，禁止 `system`）
- 切换动效：clip-path 圆形扩散 960ms
- 语义色 CSS 变量驱动，业务代码只引用变量

## 主题系统（WordPress 风格）

内建主题恒为两套（`lib/rosetta-themes.ts` 是唯一权威来源：`KNOWN_ROSETTA_THEMES` 主题白名单、`MINIMAL_THEME_SLUGS` 极简变体判定、`THEME_VISUAL_EXCLUDE_PREFIXES` / `isThemeVisualExcluded` 路径排除、`resolveThemeAssetPath` / `bustThemeAssetCache` 资源 URL 归一与缓存 bust）。页头/页脚/登录/注册/错误页/首页等组件一律 import，**禁止再写本地 `MINIMAL_THEME_SLUGS` 副本**）：

```
themes/
├── editorial-wp-style/     # 默认主题（杂志风）
│   ├── rosetta-theme.json  # slug / name / version / requires / tags / mods_schema
│   ├── style.css           # 每条选择器必须带 [data-layout-scope="frontend"] 守卫
│   └── screenshot.png
└── astro-paper-inspired/   # 极简主题（880px 窄栏 / 无 hero / 竖排列表 / 极简登录注册页+错误页+toast，见 style.css public-auth 段）
    ├── rosetta-theme.json
    ├── style.css
    └── screenshot.svg
```

激活与加载链路（**前端没有 setTheme，激活是后端行为**）：

1. 激活：后台 `PUT /admin/themes/{slug}/activate`（需 CurrentStaff）改写后端 active 主题。
2. 读取：`useFrontendTheme().ensureLoaded()` 调 `GET /themes/active` → 写入 `useState('frontend-theme:state')`（slug / name / version / mods / mods_schema）。
3. SSR 注入：`registerFrontendThemeHead()` 在 **app 级插件** `plugins/01-site-bootstrap.global.ts` 里同步注册一次 `useHead(() => …state.value…)`（**禁止放进 `useFrontendTheme()` 内部**：那会让 10+ 个调用方各自创建组件作用域 head entry，SPA 导航 / soft CSR remount 卸载组件时 unhead dispose 掉它们，主题 `<link>` 出现"掉一帧"窗口 → 前台闪一下默认样式再恢复）。reactive 回调把 `data-rosetta-theme` / `data-theme` / `theme-{slug}` class + `/themes/{slug}/style.css?v=<version>` `<link>` + 颜色 token 写进首字节 HTML。`/themes/**` 是 immutable 强缓存（nuxt.config routeRules），**`?v=` 由 `bustThemeAssetCache` 统一追加，缺了它主题升级后访客永远拿旧 CSS**。禁止在 `await` 之后调用 `useHead`（NUXT_E1001）。
4. 客户端：`applyThemeVisual(slug, version, path)` 直接操作 DOM（htmlAttrs + 带版本的 `<link>`，登记进 `_INSTALLED_LINKS`，同 slug 且 href 相同则复用）；路径命中 `isThemeVisualExcluded`（`/admin /oobe`）时改调 `clearThemeVisual()` 彻底清理。`/login /register` 允许注入（供 public-auth 段落消费）。
5. mods：`mergeMods()` 对已声明键按类型校验（如 `posts_per_row` 必须是 1-6 整数），未声明键在运行时读取时被忽略——后端 `set_mods` 会**直接丢弃** schema 未声明的键（只记 warning，不整单拒绝），所以 `mods_schema.properties` 就是控件的唯一清单：多写一个键就多一个死控件。新增主题 mod 必须同步补进 `ThemeModsRuntime` + `MODS_DEFAULTS` **并且**在页面/组件里出现真实消费点，否则不予登记。
6. 预览：后台「主题管理」预览按钮打开 `/?rosetta_theme_preview=<slug>`；`ensureLoaded` 读取该 query（仅限 `KNOWN_ROSETTA_THEMES` 白名单）覆盖 `state.slug` 并置 `previewing=true`，**不改动后端 active 主题**。

## 主题变体契约（两层，2026-09 QA 确认）

主题可以只在 CSS 层换皮，也可以换 DOM 结构。两层契约不同，**不要混**：

| 层 | 覆盖范围 | 契约 |
| -- | -------- | ---- |
| **皮肤层** | 颜色、字体、圆角、线、阴影、宽度、显隐装饰 | 只写在 `themes/<slug>/style.css`，选择器带 §三层 CSS 的双守卫；组件 DOM 不变，新主题零成本获得变体 |
| **骨架层**（variant） | 首页 hero vs 竖排列表、页脚结构、登录/注册排版、错误页排版 | 组件里的 `v-if` 分支，判定唯一来源是 `lib/rosetta-themes.ts` 的 `MINIMAL_THEME_SLUGS` |

骨架层是**有意的**成本：同一份 DOM 无法同时表达"杂志网格"和"窄栏竖排"。约束如下：

1. 判断是否真需要骨架层分支：能用 `style.css` 的 `display:none` / 栅格覆写做到的，一律留在皮肤层，不加 `v-if`。
2. 新主题若要走极简骨架（当前成员仅 `astro-paper-inspired`），**必须**在 `MINIMAL_THEME_SLUGS` 登记一次；组件侧永远 `import`，禁止本地复制 Set 或写 `slug === 'astro-paper-inspired'` 字面量。
3. 消费骨架变体的组件必须从 `useFrontendTheme().slug` 派生（SSR 已 `ensureLoaded`，两端一致），禁止用 `localStorage`/`matchMedia` 等客户端态判定变体。
4. 新增第三套内建主题若不登记，则自动落回 editorial 骨架 + 自己的皮肤层——这是**默认且受支持**的行为，不算 bug。


## i18n

- 四种语言：`zh` / `en` / `ja` / `zh_Hant`（不新增）
- 模板：`{{ $t('posts.readingTime', { n: minutes }) }}`
- 脚本：`const { t, locale, setLocale } = useI18n()`
- 后端语言传递：`rosetta_lang` cookie
- 语言切换事件：`rosetta-lang-change`

## 状态管理

Pinia 只用于跨页面共享状态（auth / permissions）。页面级搜索条件、分页、表单临时值 → `ref` / `useState`。store 中禁止直接发请求，请求封装到 composable。

## UI 约定

- 主色调青蓝色（sky 201°），由 `--primary` / `--ring` CSS 变量驱动
- 扁平化：卡片不加左侧彩色装饰条 / 渐变外框 / 厚重阴影
- 标签：淡色胶囊底 + 原色文字 + 无边框
- 响应式：默认桌面设计，`md:` 断点以下保证可用
- 深色模式：用对比度背景层次，不用显式边框
- 文章封面取值只有 `lib/post-cover.ts` 一个来源：`postCoverUrl(post, size)` 有封面用封面，
  没封面回落到 `https://picsum.photos/seed/rosetta-post-<id>/<w>/<h>`（seed 由文章标识派生，
  同篇恒定、篇篇不同，SSR/hydrate 字节一致）。只在公开读取链路使用，禁止把默认值写回
  `cover_image`（管理端表单/PUT 必须保持"未设置封面 = 空"）

### 语义状态色配对铁律

状态色 `info / success / warning / error`，每个色 4 个 token：

| token | 用途 |
|-------|------|
| `bg-X` | 实心填充底（配 `text-X-foreground`） |
| `text-X` | 实色文字/图标 |
| `bg-X-muted` | 淡色底（**必须**配 `text-X-muted-foreground`） |
| `text-X-muted-foreground` | `-muted` 底上的文字 |

**禁止 `bg-X-muted` + `text-X-foreground`**：会出现隐形文本。

### 颜色真源在 main.css 的 @theme，不在 tailwind.config.ts

项目用 Tailwind v4 + `@tailwindcss/vite`，CSS 里没有 `@config` 指令，因此 `tailwind.config.ts` **未被加载**。
- 新增颜色/字体/阴影/动画 → 写进 `main.css` 的 `@theme` 块
- 颜色 HSL 值 → 写在 `@layer base` 的 `:root` / `.dark`，再由 `@theme` 用 `hsl(var(--x))` 暴露
- 字体栈同理：`--font-sans` / `--font-mono` / `--font-display` 只在 `@theme` 声明（`tailwind.config.ts` 里的 `fontFamily` 已删除，避免第二真源漂移）

### Webfont 只以 preload 引入，不做渲染阻塞

`nuxt.config.ts` 的 Google Fonts 链接写的是 `rel="preload" as="style"`，真正生效由
`plugins/06-font-stylesheet.client.ts` 在客户端把 `rel` 换成 `stylesheet`。
- 原因：外站不可达时 `<link rel="stylesheet">` 会阻塞首屏渲染，最长可拖到请求超时
- 因此字体栈的本地兜底（含中文族名）**必须保留**，首屏就是靠它渲染的
- 不要把这条链接改回 `rel="stylesheet"`，也不要在 `main.css` 里 `@import` 字体（同样阻塞且串行）

## 性能

- 长列表 → 分页 / 虚拟滚动
- 大体积依赖 → `defineAsyncComponent`
- 图片必须加 width/height 防 CLS
- 用户生成 Markdown → 走 sanitize，禁止 `v-html` 信任原始字符串

## 开发命令

```bash
pnpm install
pnpm dev
pnpm typecheck
pnpm lint
pnpm build && pnpm preview
```

## 常见坑

- **Hydration mismatch**：`ref()` 默认值 SSR/客户端不同 → 用 `useState` 或 `onMounted` 赋值
- **SSR 登录态缺失**：需要用户态的接口用 `apiFetch` 而非 setup 期 `useAPI`
- **i18n 双目录陷阱**：只改 `i18n/locales/*.json`，根 `locales/` 是废弃影子目录
- **语言切换后动态内容未刷新**：组件监听 `rosetta-lang-change`
- **主题切换后 admin 错乱**：style.css blanket 规则没加守卫 → 立即修复
- **`/api/api` 双前缀**：`useAPI/apiFetch` 的 URL 参数不带 `/api` 前缀
