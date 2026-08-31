# Rosetta 前端开发规范

前端栈：Nuxt 4.5 / Vue 3 / TypeScript / Tailwind CSS / shadcn-vue / Pinia / @nuxtjs/i18n v10。
包管理器 pnpm 11（`package.json` 中 `packageManager` 已固定），所有命令在 `frontend/` 目录执行。

## 运行模式与 SSR 策略

当前 `nuxt.config.ts` 中 `ssr: false`，纯 SPA。**渐进式 SSR**，按页面逐个迁移，禁止一次性全量开启。

SPA 路由（不做 SSR）：
- `/admin/**`（登录态 + 搜索引擎不索引）
- `/login` / `/register` / `/oobe`（安装向导 / 客户端状态依赖）

SSR 路由（迁移后）：`/`（swr:60）→ `/posts/**`（swr:300）→ `/categories/**`（swr:300）→ `/archive` → `/guestbook` → `/friends` → `/about`。
一次提交只迁移 1 个页面。

## 目录与文件放置规则

| 类型 | 路径 | 备注 |
|------|------|------|
| 页面路由 | `app/pages/` | 唯一有效位置 |
| 业务组件 | `components/` | 根目录，Nuxt 自动导入 |
| UI 原子组件 | `components/ui/<name>/` | shadcn-vue CLI 生成，不手动编辑 |
| Admin 组件 | `components/admin/` | AdminCard / StatCard / MarkdownEditor ... |
| 组合式函数 | `composables/` | `useXxx.ts`，自动导入两层 |
| 布局 | `layouts/` | `default.vue` 前台 / `admin.vue` 后台 |
| Pinia stores | `stores/` | 仅跨页面共享状态 |
| Nitro BFF | `server/api/` + `server/plugins/` | API 代理 / SWR 缓存 / 自动 spawn 后端 |
| i18n 语言包 | `i18n/locales/{zh,en,ja,zh_Hant}.json` | 根目录旧 `locales/` 已废弃 |
| 主题目录 | `themes/{slug}/` | 每个主题一个目录，manifest.json + style.css |
| 全局 CSS | `assets/css/main.css` | Tailwind 变量 + `.prose-shadcn` + `.card-surface` 等**共享组件类** |
| 路由中间件 | `middleware/` | 根目录（Nuxt 自动注册） |
| 主题中间件 | `middleware/layout-scope.global.ts` | 三层解耦守卫之一 |

引用：`~/components/*` → 根 `components/`；`~/*` → `frontend/` 其余

## ⚠️ main.css 共享组件 vs 主题 style.css

**关键区分**：

| 位置 | 内容 | 允许写 |
|------|------|--------|
| `assets/css/main.css` | 全站共享基础样式 | `.prose-shadcn`、`.card-surface`、`:root` CSS 变量、`.hero-gradient`、`.glow-ring` — **admin 和前台都要用的公共组件类** |
| `themes/{slug}/style.css` | 主题特定样式 | 必须加 `[data-layout-scope="frontend"]` 守卫，**禁止** blanket `main .grid-cols-*` / `main [class*="shadow-"]` / `main [class*="rounded-xl"]` 这种会误伤其他页面的规则 |

新增主题 style.css 规则时，**只作用于特定组件名**（如 `[class*="PostCard"]`、`main header h1`、`main article > img`），不要 blanket 干掉通用 tailwind 类。

## 主题解耦机制（三层防御）

1. **CSS 层**：主题 style.css 全部规则加 `[data-layout-scope="frontend"]` 守卫
2. **运行时层**：`useFrontendTheme.ts` 的 `applyThemeVisual(path)` 检测路由 → `/admin` / `/login` / `/oobe` 路径调用 `clearThemeVisual()` 清理 html 上的 `data-theme` / `data-rosetta-theme` / `theme-*` class + 移除主题 `<link>`
3. **布局层**：`layouts/admin.vue` onMounted + watch(route) 主动清理并写 `data-layout-scope=admin`
4. **中间件层**：`middleware/layout-scope.global.ts` 作为兜底，SPA 路由跳转时立即写入正确 scope

**修改主题样式后**，在浏览器切到 admin 路由确认 shadcn Card 仍保持原生 rounded-xl + border 外观。

## SFC 标准写法

```vue
<script setup lang="ts">
// 自动导入：ref / useState / useHead / useFetch / useI18n / useToast / useRuntimeConfig
// 组件 props / emits
const props = defineProps<{ title: string }>()
const emit = defineEmits<{ (e: 'update'): void }>()

const { t } = useI18n()
const config = useRuntimeConfig()

// SSR 友好的数据获取
const { data: posts, pending, error, refresh } = await useFetch<Post[]>(
  '/api/blog/posts',
  {
    baseURL: config.public.apiBase,
    key: 'posts-index-page-1',
    default: () => [],    // SSR/客户端水合前默认值
    server: true,
    lazy: false,
  }
)
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

推荐模式：
```ts
const theme = useState<'light' | 'dark'>('theme-mode', () => 'light')
if (import.meta.client) {
  theme.value = document.documentElement.dataset.theme as any || 'light'
}
```

## 主题切换

`composables/useTheme.ts` + `plugins/theme.client.ts`：
- localStorage 持久化（`light` / `dark`，禁止 `system`）
- 切换动效：clip-path 圆形扩散 960ms `cubic-bezier(0.22,1,0.36,1)`
- 语义色 CSS 变量驱动（`--primary` / `--accent` / `--muted` ...），业务代码只引用变量

## 主题系统（WordPress 风格）

目录结构：
```
themes/
├── editorial-wp-style/     # 默认主题，Editorial Magazine 风格，衬线字体 + glow ring 卡片
│   ├── manifest.json       # slug / name / version / requires / tags
│   ├── style.css           # WordPress convention 元信息头（实际样式在 main.css 公共类 + Vue scoped）
│   └── resources/          # 可选：主题特有的 SVG / 字体
└── astro-paper-inspired/   # Minimal Paper 主题，复刻 Astro Paper 风格
    ├── manifest.json
    ├── style.css           # 600+ 行，全部带 [data-layout-scope="frontend"] 守卫
    └── resources/
```

激活流程：`useFrontendTheme.setTheme(slug)` → 写入 localStorage + `<html>` 上写 `data-rosetta-theme={slug}` + 动态注入主题 `<link>`（style.css）。

开发新主题：**只改 `themes/{slug}/style.css`**，所有规则必须加守卫，禁止 blanket 规则。

## i18n

- 四种语言：`zh` / `en` / `ja` / `zh_Hant`（不新增）
- 模板：`{{ $t('posts.readingTime', { n: minutes }) }}`
- 脚本：`const { t, locale, setLocale } = useI18n()`
- 后端语言传递：`rosetta_lang` cookie
- 语言切换事件：`rosetta-lang-change`（动态内容组件监听重新拉取）

## 状态管理

Pinia 只用于跨页面共享状态（auth / permissions）。页面级搜索条件、分页、表单临时值 → `ref` / `useState`。store 中禁止直接发请求，请求封装到 composable。

## UI 约定

- 主色调青蓝色（sky 201°），由 `--primary` / `--ring` CSS 变量驱动
- 扁平化：卡片**不**加左侧彩色装饰条 / 渐变外框 / 厚重阴影
- 标签：淡色胶囊底 + 原色文字 + 无边框 + hover 仅改背景
- 响应式：默认桌面设计，`md:` 断点以下保证可用
- 深色模式：暗色不用显式边框表达分隔，用对比度背景层次

## 性能

- 长列表 → 分页 / 虚拟滚动
- 大体积依赖 → `defineAsyncComponent`
- 图片必须加 width/height 防 CLS
- 用户生成 Markdown → 走 sanitize，禁止 `v-html` 信任原始字符串

## 开发命令

```bash
pnpm install
pnpm dev            # 8000 空闲时自动 spawn 后端
pnpm typecheck      # vue-tsc
pnpm lint
pnpm build && pnpm preview
```

## 常见坑

- **Hydration mismatch**：`ref()` 默认值 SSR / 客户端不同 → 用 `useState` 或 `useFetch({ default: () => ... })`
- **SSR 登录态缺失**：需要用户态的接口 → `server: false`
- **目录重复**：`app/pages/` 生效；`pages/` 根目录已废弃
- **旧 locales/ 与 i18n/locales/ 并存**：只认后者
- **语言切换后动态内容未刷新**：组件要监听 `rosetta-lang-change`
- **主题切换后 admin 错乱**：style.css 里 blanket 规则没加守卫 → 立即修复
