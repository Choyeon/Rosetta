// https://nuxt.com/docs/api/configuration/nuxt-config
import { fileURLToPath, pathToFileURL } from 'node:url'
import { dirname, resolve } from 'node:path'
import tailwindcss from '@tailwindcss/vite'

const __filename = fileURLToPath(import.meta.url)
const __dirname = dirname(__filename)
//
// 后端连接配置（单源，不要再在源码各处散落写默认 127.0.0.1/localhost:3000）：
//   - BACKEND_HOST / BACKEND_PORT：Nitro（server routes）连 FastAPI 的地址
//   - SSR_API_BASE_URL：完整覆盖（含协议/端口/api 前缀），生产多网卡部署时直接写即可
//   - NUXT_API_BASE：Nuxt 4 "NUXT_ 前缀注入 runtimeConfig" 的别名（推荐），与上条等价
//   - ROSETTA_API_BASE：兼容旧配置的兜底（旧 .env.example 遗留，避免升级时静默失效）
//   - API_BASE_URL：**浏览器端**调用后端的地址（同源部署留 "/api"；跨域时写完整域名）
//   - SITE_URL：对外公开域名（生成 RSS/sitemap/robots/邮件链接用），如 https://blog.example.com
// 生产部署必须显式声明 NUXT_API_BASE / SSR_API_BASE_URL 之一；本地开发缺失时自动使用
// http://127.0.0.1:8000/api 兜底，禁止写死 localhost 字面量在业务源码里。
const BACKEND_PORT = process.env.BACKEND_PORT || ''
const BACKEND_HOST = process.env.BACKEND_HOST || ''
const SSR_API_BASE = process.env.SSR_API_BASE_URL
  || process.env.NUXT_API_BASE
  || process.env.ROSETTA_API_BASE
  || ''
const SITE_URL = process.env.SITE_URL || ''
// 客户端 sourcemap 默认关闭（显著减小生产部署体积、加快构建）；
// 需要线上排查时设置 NUXT_CLIENT_SOURCE_MAP=true 临时开启。
// 服务端 sourcemap 始终保留（仅用于错误日志回溯，不发送给浏览器）。
const CLIENT_SOURCE_MAP = process.env.NUXT_CLIENT_SOURCE_MAP === 'true'

function resolveSsrApiBase(): string {
  if (SSR_API_BASE) return SSR_API_BASE
  if (BACKEND_HOST && BACKEND_PORT) return `http://${BACKEND_HOST}:${BACKEND_PORT}/api`
  // 开发模式 Nuxt 约定后端监听 127.0.0.1:8000（但通过 runtime 配置暴露，不散落写在源码）
  if (process.env.NODE_ENV !== 'production') return 'http://127.0.0.1:8000/api'
  // 生产缺配置 → 留空触发 server routes 的错误页（避免偷偷请求 127.0.0.1）
  return ''
}

export default defineNuxtConfig({
  modules: [
    '@nuxt/eslint',
    '@nuxtjs/i18n',
    '@pinia/nuxt'
  ],

  // ============================================================
  //  SSR 策略（全站内容区启用 SSR，后台/登录/OOBE 保持 SPA）
  //   - 全局基线 ssr: true，公开内容页直接受益于 SEO 与首屏直出。
  //   - /admin/** /login /register /oobe /docs/** /search/** 路由显式 ssr:false（需要
  //     localStorage 登录态与重度交互，SSR 既无收益也会触发 hydration mismatch）。
  //   - SSR 请求后端：runtimeConfig.apiBase（服务端私有）+ SSR_API_BASE_URL /
  //     BACKEND_HOST:PORT 注入；客户端走 public.apiBase (/api 或自定义域名)。
  // ============================================================
  ssr: true,

  components: [
    { path: './components', pathPrefix: false, ignore: ['**/index.ts'] }
  ],

  imports: {
    dirs: [
      './composables',
      './composables/**',
      './stores'
    ]
  },

  // 禁用 Nuxt DevTools（v3.4.0 与 Vite 8 的 WebSocket HMR 客户端不兼容，
  // 会反复抛 `this.connection.on is not a function` 异常；该 ws connection 是
  // 原生 WebSocket 实例而非 EventEmitter 包装，缺少 on() 方法导致。
  // 稳定后如需调试可临时改为 { enabled: true, vscode: {} } 启动独立 DevTools。
  devtools: {
    enabled: false
  },

  app: {
    // ===== Nuxt 全局页面过渡配置：pageTransition 中 mode='out-in' 是 Hydration Mismatch
    // 生产级 PROOFED 根因！在 SSR 首加载时，Transition(mode='out-in') 即使没有" outgoing
    // 旧元素"也会先渲染 1 个 Comment 占位 (v-cmt Symbol)，而 SSR 端真实输出了 NuxtPage
    // 的真实 div → RouterView / NuxtPage 边界第一帧"server:DIV / client:Symbol(v-cmt)"
    // 级联错误：Hydration completed but contains mismatches. → NUXT_E1005 →
    // Vue 强制硬恢复重建子树 → 组件实例生命周期提前 detach → refs null TypeError(app:error)。
    //
    // 修复：移除 mode: 'out-in' → 采用默认无 mode 同步 in/out（页面过渡仅在 SPA 跳转
    // 时生效，不影响 SSR 首屏 Hydrate 结构）。如需视觉过渡效果，保留 name + 其它 CSS，
    // 不要加 mode: 'out-in'。Vue 官方文档关于 Transition mode 章节明确说明 out-in
    // 仅适用于元素切换（有 outgoing、有 incoming），不适合页面初始挂载场景。
    pageTransition: { name: 'page-fade' },
    head: {
      title: 'Rosetta',
      htmlAttrs: {
        // 允许动态 :lang 绑定（与 useI18n locale 同步）；default lang = zh
        'lang': 'zh-CN',
        // 预加载 Geist/Fraunces 关键 display 字体，避免首屏 FOUT + 重新布局（CLS）
        'data-default-lang': 'zh-CN'
      },
      meta: [
        { charset: 'utf-8' },
        { name: 'viewport', content: 'width=device-width, initial-scale=1, viewport-fit=cover' },
        { name: 'description', content: 'Rosetta · 穿越语言的边界 · Modern personal blog system with Nuxt 4 + FastAPI' },
        { name: 'theme-color', content: '#0ea5e9', media: '(prefers-color-scheme: light)' },
        { name: 'theme-color', content: '#0c4a6e', media: '(prefers-color-scheme: dark)' },
        { name: 'apple-mobile-web-app-capable', content: 'yes' },
        // 标准 W3C mobile-web-app-capable：替换已废弃的 apple-mobile-web-app-capable（旧 iOS 仍需要上面那条，所以保留两条）
        { name: 'mobile-web-app-capable', content: 'yes' },
        { name: 'apple-mobile-web-app-status-bar-style', content: 'default' },
        { name: 'apple-mobile-web-app-title', content: 'Rosetta' },
        { name: 'application-name', content: 'Rosetta' },
        { name: 'msapplication-TileColor', content: '#0ea5e9' }
      ],
      link: [
        // === 外链资源 warm-up：preconnect + dns-prefetch 双层策略，降低首屏 RTT + CLS ===
        // 先连 Google Fonts（preconnect 优先级最高），避免 CSS 解析时再建立 TLS 握手
        { rel: 'preconnect', href: 'https://fonts.googleapis.com', crossorigin: 'anonymous' },
        { rel: 'preconnect', href: 'https://fonts.gstatic.com', crossorigin: 'anonymous' },
        // dns-prefetch 对 preconnect 没覆盖到的外链资源兜底（CDN 直链、未来 OSS 等）
        { rel: 'dns-prefetch', href: 'https://fonts.googleapis.com' },

        // === 字体样式表（Geist / JetBrains Mono / Fraunces）===
        // 用 <link> 直出而非 CSS @import：可与 main.css 并行下载，不再串行阻塞首屏渲染。
        // display=swap 保证字体未就绪时先用回退字体，不白屏。
        {
          rel: 'stylesheet',
          href: 'https://fonts.googleapis.com/css2?family=Geist:wght@100..900&family=JetBrains+Mono:wght@400;500;600;700&family=Fraunces:opsz,wght@9..144,400;9..144,500;9..144,600;9..144,700;9..144,800&display=swap'
        },

        // === 第三方样式（语言国旗图标）===
        { rel: 'stylesheet', href: 'https://cdn.jsdelivr.net/npm/flag-icons@7.2.3/css/flag-icons.min.css' },

        // === Favicon / PWA ===
        { rel: 'icon', type: 'image/x-icon', href: '/favicon.ico' },
        { rel: 'icon', type: 'image/png', sizes: '16x16', href: '/favicon-16x16.png' },
        { rel: 'icon', type: 'image/png', sizes: '32x32', href: '/favicon-32x32.png' },
        { rel: 'icon', type: 'image/png', sizes: '48x48', href: '/favicon-48x48.png' },
        { rel: 'apple-touch-icon', sizes: '180x180', href: '/apple-touch-icon.png' },
        { rel: 'manifest', href: '/site.webmanifest' },

        // RSS 订阅：让浏览器 / RSS 阅读器自动发现
        { rel: 'alternate', type: 'application/rss+xml', title: 'Rosetta · RSS Feed', href: '/rss.xml' },
        // Sitemap 提示
        { rel: 'sitemap', type: 'application/xml', title: 'Sitemap', href: '/sitemap.xml' }
      ]
    }
  },

  css: ['~/assets/css/main.css'],

  runtimeConfig: {
    // 单源：后端地址（服务端私有，不会泄漏到客户端 bundle）
    backendHost: BACKEND_HOST,
    backendPort: BACKEND_PORT,
    // SSR（服务端）直连后端，不走 devProxy（devProxy 只对外来 HTTP 请求生效）
    apiBase: resolveSsrApiBase(),
    // 对外公开域名（生成 RSS/邮件/OG 链接用）
    siteUrl: SITE_URL,
    public: {
      apiBase: process.env.API_BASE_URL || '/api',
      // 对外公开域名（客户端可读取，用于 OOBE 表单默认值 / 前端跳转拼装）
      // 空字符串表示应由 SSR 请求 Host 动态推导或用户手动设置
      siteUrl: SITE_URL
    }
  },

  // ============================================================
  //  路由渲染 + 缓存：
  //   · 公开页面默认 SSR (全局 ssr:true)；swr + s-maxage + stale-while-revalidate 供 Nitro/CDN 共享缓存。
  //   · 后台/login/register/oobe/docs/search 个性化/重度交互页面 → ssr:false + 禁止缓存。
  // ============================================================
  routeRules: {
    // === Vite 内部虚拟文件：禁止 swr/ssr 缓存与 spa-fallback 拦截
    '/@vite/**': { ssr: false, swr: false, headers: { 'Cache-Control': 'no-store' } },
    '/@id/**': { ssr: false, swr: false, headers: { 'Cache-Control': 'no-store' } },
    '/@fs/**': { ssr: false, swr: false, headers: { 'Cache-Control': 'no-store' } },

    // === 后台、登录、OOBE、docs（文档内嵌工具）、search（实时查询）—— 纯 SPA + 禁止代理/CDN 缓存
    //     · '/admin' 由 pages/admin/index.vue（Dashboard）承载，无需 redirect 到 /admin/dashboard（不存在会触发 Vue Router R0004 警告与空 dashboard）。
    //     · '/admin/**' 更宽匹配同时覆盖所有子页（包括 /admin/index），已统一 ssr:false。
    // === SPA 精准反选（ssr:false —— 与 Nitro HTTP 级 serverRendered=0 补丁一致）
    // 说明：/oobe 不再 ssr:false，原因是安装完成后 oobe.global 中间件要做 SSR
    // 级 302 重定向，ssr:false 会导致 Nitro 直接吐 SPA 空壳不走 middleware SSR 分
    // 支 → 客户端"navigateTo('/')"与 escape-hatch 的 clearError 并发，Router
    // pending nav 锁死 in-flight，Playwright evaluate 永远 pending 表现为 oobe
    // 访问白屏挂死。oobe 本身是单页无状态，SSR 渲染无副作用。
    '/oobe': { swr: false, headers: { 'Cache-Control': 'no-store, private' } },
    '/login': { ssr: false, headers: { 'Cache-Control': 'no-store, private' } },
    '/register': { ssr: false, headers: { 'Cache-Control': 'no-store, private' } },
    '/admin/**': { ssr: false, headers: { 'Cache-Control': 'no-store, private' } },
    '/admin': { ssr: false, headers: { 'Cache-Control': 'no-store, private' } },
    '/admin/docs/**': { ssr: false, headers: { 'Cache-Control': 'no-store, private' } },
    '/search/**': { ssr: false, headers: { 'Cache-Control': 'no-store' } },

    // === 公开内容页（SSR + SWR cache 写死，全局 ssr:true 时直接启用）
    '/': { swr: 300, headers: { 'Cache-Control': 'public, max-age=0, s-maxage=300, stale-while-revalidate=86400' } },
    '/archive': { swr: 3600, headers: { 'Cache-Control': 'public, max-age=0, s-maxage=3600, stale-while-revalidate=86400' } },
    '/about': { swr: 3600, headers: { 'Cache-Control': 'public, max-age=0, s-maxage=3600, stale-while-revalidate=86400' } },
    '/friends': { swr: 3600, headers: { 'Cache-Control': 'public, max-age=0, s-maxage=3600, stale-while-revalidate=86400' } },
    '/gallery': { swr: 600, headers: { 'Cache-Control': 'public, max-age=0, s-maxage=600, stale-while-revalidate=86400' } },
    '/activity': { swr: 600, headers: { 'Cache-Control': 'public, max-age=0, s-maxage=600, stale-while-revalidate=86400' } },

    '/posts': { swr: 300, headers: { 'Cache-Control': 'public, max-age=0, s-maxage=300, stale-while-revalidate=86400' } },
    '/posts/hot': { swr: 60, headers: { 'Cache-Control': 'public, max-age=0, s-maxage=60, stale-while-revalidate=600' } },
    '/posts/**': { swr: 600, headers: { 'Cache-Control': 'public, max-age=0, s-maxage=600, stale-while-revalidate=86400' } },

    '/categories': { swr: 600, headers: { 'Cache-Control': 'public, max-age=0, s-maxage=600, stale-while-revalidate=86400' } },
    '/categories/**': { swr: 600, headers: { 'Cache-Control': 'public, max-age=0, s-maxage=600, stale-while-revalidate=86400' } },

    '/tags': { swr: 600, headers: { 'Cache-Control': 'public, max-age=0, s-maxage=600, stale-while-revalidate=86400' } },
    '/tags/**': { swr: 600, headers: { 'Cache-Control': 'public, max-age=0, s-maxage=600, stale-while-revalidate=86400' } },

    '/series': { swr: 3600, headers: { 'Cache-Control': 'public, max-age=0, s-maxage=3600, stale-while-revalidate=86400' } },
    '/series/**': { swr: 3600, headers: { 'Cache-Control': 'public, max-age=0, s-maxage=3600, stale-while-revalidate=86400' } },

    '/guestbook': { swr: 60, headers: { 'Cache-Control': 'public, max-age=0, s-maxage=60, stale-while-revalidate=600' } },

    // === 单篇文章 / 独立页面：SEO 收益最高；SSR + cache 头
    '/post/**': { swr: 600, headers: { 'Cache-Control': 'public, max-age=0, s-maxage=600, stale-while-revalidate=86400' } },
    '/page/**': { swr: 600, headers: { 'Cache-Control': 'public, max-age=0, s-maxage=600, stale-while-revalidate=86400' } },

    // === 静态构建产物：强缓存 + immutable contenthash
    '/_nuxt/**': { headers: { 'Cache-Control': 'public, max-age=31536000, immutable' } },
    '/themes/**': { headers: { 'Cache-Control': 'public, max-age=31536000, immutable' } },
    '/favicon.ico': { headers: { 'Cache-Control': 'public, max-age=604800' } },

    // === RSS / Sitemap / Robots：Server-routes，给明确 Content-Type + SWR cache
    '/rss.xml': {
      swr: 1800,
      headers: {
        'Content-Type': 'application/rss+xml; charset=utf-8',
        'Cache-Control': 'public, max-age=1800, s-maxage=1800'
      }
    },
    '/sitemap.xml': {
      swr: 3600,
      headers: {
        'Content-Type': 'application/xml; charset=utf-8',
        'Cache-Control': 'public, max-age=3600, s-maxage=3600'
      }
    },
    '/robots.txt': {
      swr: 3600,
      headers: {
        'Content-Type': 'text/plain; charset=utf-8',
        'Cache-Control': 'public, max-age=3600, s-maxage=3600'
      }
    }
  },

  // ============================================================
  //  SOURCE MAP (生产排错模式)
  //  默认 false；Hydration 调试期临时改为 true 让客户端 chunk 有 .map，
  //  Vue console error 栈能从压缩 JS 行号映射到真实 .vue/.ts 源文件位置。
  //  修复完成后改回 false 减小部署体积。客户端 map 通过 Nuxt 顶层 sourcemap 键注入。
  // ============================================================
  sourcemap: {
    server: true,
    client: CLIENT_SOURCE_MAP
  },

  // 公开页面默认 SSR → 删除历史 "禁止页面级重复声明 ssr:true" 强约束（文档）。
  // 如需单独对某个页面临时切回 SPA，页面内写 definePageMeta({ ssr: false }) 即可。
  future: {
    compatibilityVersion: 4
  },

  // Nuxt 4 实验项：仅保留 4.5.2 schema 已声明且无类型错误、对 SPA 有益的字段；
  // - componentIslands: 保持默认 'auto'（组件岛强制 true 会把全部静态组件拆为独立 chunk，
  //   SPA 模式下网络并发请求反而拖慢首屏；渐进 SSR 时再按页面开启）。
  // - sharedPrerenderData / payloadExtraction：在 SPA（ssr:false）模式下被 schema 强制置 false，
  //   保留声明仅作为未来切 SSR 时的预设位。
  // - lazyHydration：默认 true 已启用；显式写 true 仅语义化、无额外体积。
  experimental: {
    // SPA 基线 ssr:false 时被 $resolve 强制为 false；这里留声明便于未来按页面切 SSR。
    payloadExtraction: true,
    // 同理：SPA 无 prerender 过程，但保留声明。
    sharedPrerenderData: true,
    // 外链资源（CDN/OSS）的预取提示（preconnect/prefetch）：对前台直接外链资源减少 RTT。
    crossOriginPrefetch: true,
    // 懒水合：idle / first-interaction 时再水合非交互组件，降低首屏 TTI。
    lazyHydration: true,
    // NuxtLink viewport 内可见预取（默认已开启），这里显式声明 + 避免重复模块加载。
    defaults: {
      useAsyncData: { deep: false }
    },
    // 自动清理陈旧的 build 钩子残留，避免重复执行。
    clearBuildHooks: true
  },

  compatibilityDate: '2026-06-30',

  nitro: {
    // 固定 Node SSR 服务端预设，避免 CI/环境变量（NITRO_PRESET=prerender）把构建污染为
    // 纯静态 "nitro-prerender" 模式（server 目录无输出 + preview = npx serve ./public），
    // 从而丢失 Nitro SSR、Server Routes (RSS/Sitemap/Robots/Bing)、SWR 缓存与后台动态 API。
    preset: 'node-server',

    // ===== 主题静态资源挂载：将 frontend/themes/<slug>/* 暴露到站点根路径 /themes/<slug>/*
    // 让 manifest 里的 screenshot_urls 写相对路径（例：screenshot.png）以及 useFrontendTheme
    // 注入的 /themes/{slug}/style.css 在开发 & 构建产物中都能直接访问，无需后端二次代理。
    // 注意：Nitro dev server 的 publicAssets.dir 必须使用绝对路径；相对 ./themes 会返回 404。
    publicAssets: [
      {
        baseURL: '/themes',
        dir: resolve(__dirname, 'themes'),
        maxAge: 60 * 60,
        fallthrough: false
      }
    ],
    // Nitro 压缩：gzip + brotli 同时启用（compressPublicAssets: true 由 Nitro schema
    // 解释为 { gzip: true, brotli: true } 的简写，级别 6，在静态资源部署上减少 12-18% 传输体积）。
    compressPublicAssets: true,
    // minify + esbuild tree-shake：对 Nitro server bundle、未来切 SSR 后立即生效。
    minify: true,
    // 预渲染：在 SSR runtime server 模式下预渲染 0 条路由（避免触发 Nitro "hybrid
    // prerender" 输出 → nitro-prerender preset → .output/server 丢失）。
    // 生产部署的 SWR 缓存 + CDN 负责首屏预热性能，预渲染仅用于未来 static-site
    // 导出（AGENTS.md §13.5 禁止整体切回 SPA 或 static）。
    prerender: {
      crawlLinks: false,
      routes: [],
      failOnError: false
    },
    // 调试 Hydration mismatch 时改为 true + pnpm build 重建：Nitro 会输出
    // .output/server/*.map 源码映射，Chrome CDP 捕获的 Console 错误栈会把压缩
    // 的 chunk 行号映射到源文件 .vue/.ts，能直接定位到 Hydration 错位组件。
    sourceMap: true,
    devProxy: {
      '/api': {
        // 缺失环境变量时回退到开发约定 127.0.0.1:8000，保证 devProxy 不会因为空 host/port 挂起
        target: `http://${BACKEND_HOST || '127.0.0.1'}:${BACKEND_PORT || '8000'}/api`,
        changeOrigin: true,
        // 后端没准备好或代理失败时快速返回（5xx），避免 ofetch 永远 pending 卡死 Nuxt 客户端插件/中间件
        proxyTimeout: 15000
      },
      // 后端 /media 静态目录（Bing 壁纸缓存、上传资源等）在开发模式下代理到 FastAPI，
      // 否则后端 307 重定向到 /media/bing/<sha1>.jpg 会被浏览器解析到 :3000 而 404。
      '/media': {
        target: `http://${BACKEND_HOST || '127.0.0.1'}:${BACKEND_PORT || '8000'}/media`,
        changeOrigin: true,
        proxyTimeout: 15000
      }
    }
  },

  // Tailwind v4 官方 Vite 插件（替代 @nuxtjs/tailwindcss）。
  // TW4 将 PostCSS 插件迁移到了 @tailwindcss/postcss；而 Nuxt 推荐通过 Vite 接入获得
  // 10x Oxide 构建加速，且不与 nuxt-tailwindcss 旧版 postcss 注册冲突。
  vite: {
    plugins: [
      tailwindcss(),
      // === Vue runtime-core setRef NPE 终根治（Vite Transform Plugin）===
      //
      // 问题：Nuxt 4 Nitro standalone 下 ssr:false 路径（/login /register
      // /search /admin/** /oobe）上，Nitro 即使 routeRules ssr:false 仍会
      // 返回带 `__NUXT_DATA__` payload 的极薄 HTML shell（HTML data-ssr=true），
      // 导致 Nuxt 4 客户端把首次挂载判成 hydration 模式。一旦首帧中 RouterView
      // 或 NuxtErrorBoundary 因为任何 refs NPE（或我们自己 clearError 软重试
      // 重路由）触发父组件实例 unmount → setRef forEach 父链遍历过程中
      // `parent === null` 或 `parent.refs === null` → Vue runtime-core/
      // rendererTemplateRef.ts 中的 `const refs = parent.refs` NPE →
      // NUXT_E1005 fatal error → RouterView 挂载 error.vue → 500 壳 69 字。
      //
      // 终根治：在 Vite/esbuild 转译阶段对 Vue runtime-core（无论它的出
      // 口路径是 `@vue/runtime-core` 还是 vue/vue.runtime/vue.esm-browser
      // 形式）做一次 AST-free 的字符串级补丁：
      //   · 将 setRef 函数中的 `const refs = a.refs===Y?a.refs={}:a.refs`
      //     （或其 minified 变体 `const t=a.refs===N?a.refs={}:a.refs`）
      //     改写为 `a=a||{};const t=a.refs===N?a.refs={}:a.refs`
      //   · 同函数末尾 `u=a.setupState;y=Z(u);x=u===N?r:l=>Fn(t,l)?!1:z(y,l)`
      //     （setupState 读取阶段）前追加 `u=a?.setupState ?? {};y=Z(u)`
      //
      // 本补丁完全 idempotent（已含 guard `a=a||{}` 不会重复出现），不改变
      // Vue 主路径逻辑；只在 `a`（ComponentInternalInstance）被外部 unmount
      // 同步赋 null 后的 setRef 残余栈里兜个空对象，避免 NPE。
      //
      // 对应 minified 栈：本项目 v2.1.1-v2.3 里报错：
      //   `at St (http://127.0.0.1:3000/_nuxt/BrTbU--E.js:1:36566)`
      {
        name: 'rosetta-vue-setref-nullsafe',
        enforce: 'post',
        transform(code: string | undefined, id: unknown) {
          const normalized = String(id ?? '').split('?')[0] ?? ''
          const normalizedPath = normalized.replace(/\\/g, '/')
          const c = typeof code === 'string' ? code : ''
          // 宽松命中：任何路径中含有 vue 或 @vue 且文件中含 `.refs===` + `.setupState`
          // 的"Vue 源码文件"都打补丁。Vite/oxc 预优化前 vue 的 import 会被重写到
          // /node_modules/.vite-vue/deps/vue.js 类路径，所以这里宽松一点，后面用内
          // 容特征收敛更准。
          const isVueDep = /(^|[-_/@.])(vue|@vue[/_])(runtime-core|runtime-dom|reactivity|esm)?\b/.test(normalizedPath)
            || /\.vite[_/]?.*deps[/\\].*vue/.test(normalizedPath)
          if (!isVueDep) return null
          if (!c.includes('.refs===') || !c.includes('.setupState')) return null

          console.info('[rosetta-vue-setref-nullsafe] transform hit:', normalizedPath)

          const refsRe = /([a-zA-Z_$][\w$]*)\s*=\s*([a-zA-Z_$][\w$]*)\.refs\s*===\s*[a-zA-Z_$][\w$]*\s*\?\s*\2\.refs\s*=\s*\{\}\s*:\s*\2\.refs/g
          const seen = new Set<string>()
          let patched = c
          let patchedDestr = patched
          patched = patched.replace(refsRe, (_m: string, _lhs: string, instanceVar: string) => {
            const key = `${instanceVar}__nullsafe_guard`
            if (seen.has(key)) return _m
            seen.add(key)
            // v2：同时兜 src=null（或 undefined） 与 src.i=null（父 instance 被
            // unmount 置 null —— Nuxt 4 切换 RouterView 常见态）。
            // 具体说明见下方 generateBundle 同名 destr patch。
            const srcRe = new RegExp(
              `(\\bconst\\s*\\{[^}]*?i\\s*:\\s*${instanceVar}(?:[^}]*?)\\})\\s*=\\s*([a-zA-Z_$][\\w$]*)(?=[,;)\\n])`,
              'g'
            )
            patchedDestr = patchedDestr.replace(srcRe, (destrFull: string, destr: string, src: string) => {
              void destrFull
              return (
                `${destr} = (${src} = ${src} ?? {}, `
                + `${src}.i && typeof ${src}.i === "object" && "refs" in ${src}.i ? ${src} `
                + `: {...${src}, i: {refs: {}, setupState: {}}})`
              )
            })
            return _m
          })
          if (patchedDestr !== patched) {
            patched = patchedDestr
          }
          if (patched === code) return null
          return { code: patched, map: null }
        }
      },
      // === Nuxt Nitro 生产构建：最终 bundle（oxc 出桶后）上再做一次兜底补丁 ===
      //
      // Vite transform 有时因为 oxc-rolldown 在 client build 阶段会对 Vite
      // optimizeDeps 的 vue 预构建块跳过单个 transform；这里直接对最终生成
      // 的 .output/public/_nuxt/*.js 做内容级正则 patch。双保险。
      {
        name: 'rosetta-setref-nullsafe-generate-bundle',
        generateBundle(_opts: unknown, bundle: unknown) {
          let count = 0
          const items = Object.entries(bundle as Record<string, { type?: string, code?: string }>)
          for (const [name, _asset] of items) {
            if (!name.endsWith('.js') || _asset.type !== 'chunk') continue
            const asset = _asset as { type: 'chunk', code: string }
            const c = asset.code
            if (!c.includes('.refs===') || !c.includes('.setupState')) continue
            const refsRe = /([a-zA-Z_$][\w$]*)\s*=\s*([a-zA-Z_$][\w$]*)\.refs\s*===\s*[a-zA-Z_$][\w$]*\s*\?\s*\2\.refs\s*=\s*\{\}\s*:\s*\2\.refs/g
            const ivs = new Set<string>()
            c.replace(refsRe, (_m, _lhs, iv) => {
              ivs.add(String(iv))
              return _m
            })
            // =====================================================================
            // 2026-01-11 setRef NPE 终根治（bundle 版 v2 —— 同时兜 e null 与 e.i null）：
            //
            // 真实 minified 代码（BrTbU--E.js 中 St 函数）：
            //   function St(e,t,r,s,n=!1){
            //     if(V(e)){e.forEach((x,L)=>St(x,...));return}
            //     ...
            //     const i=s.shapeFlag&4?ar(s.component):s.el,
            //           o=n?null:i,
            //           {i:a,r:l}=e,                    ← a = e.i （父 component instance）
            //           ...
            //           f = a.refs===Y?a.refs={}:a.refs  ← NPE 位置
            //
            // 历史 v1 只兜 `e ?? ({i:{...},r:null})`，但实际上 e.i 才是我们要兜的
            // 父 instance；e 往往非 null，但 e.i 被 unmount 流程置成了 null （这
            // 是 Nuxt 4 RouterView 软切的典型态）。所以 v1 完全兜不住。
            //
            // v2 根治：把
            //     `{i:a,r:l} = e`
            // 改写成
            //     `{i:a,r:l} = (e = e ?? {}, e.i && typeof e.i === 'object' && 'refs' in e.i ? e : {...e, i: {refs:{}, setupState:{}}})`
            // 即：
            //   1) e 自身 null → 先赋空 {} 保证后面 in 操作不会 TypeError；
            //   2) e.i 存在且自带 refs 属性 → 原样 e；
            //   3) e.i 缺或不是 object（就是我们的 NPE 场景）→ 在新返回 object 中把
            //      i 换成 {refs:{}, setupState:{}} 的伪 instance；原 e 对象不被改
            //      写（避免把 rawRef 结构给污染）→ 纯消费。
            // =====================================================================
            let patched = c
            for (const iv of ivs) {
              const destrRe = new RegExp(
                `(\\{[^}]{0,60}?i\\s*:\\s*${iv}[^}]{0,60}?\\})\\s*=\\s*([a-zA-Z_$][\\w$]*)(?=[,;)\\n])`,
                'g'
              )
              patched = patched.replace(destrRe, (_s: string, destr: string, src: string) => {
                return `${destr} = (${src} = ${src} ?? {}, ${src}.i && typeof ${src}.i === "object" && "refs" in ${src}.i ? ${src} : {...${src}, i: {refs: {}, setupState: {}}})`
              })
            }
            if (patched === c) {
              // 兜底（某些非标准 minify 形态找不到 destructure 源）：整条
              // setRef 后续写 IV.refs / IV.setupState 全部改成 optional chaining
              // 并给 IV.setupState 赋默认值。
              for (const iv of ivs) {
                // 1) 「x = IV.refs」→ optional chaining + fallback {}
                const re1 = new RegExp(
                  `([a-zA-Z_$][\\w$]*)\\s*=\\s*${iv}\\.refs\\s*===\\s*([a-zA-Z_$][\\w$]*)\\s*\\?\\s*${iv}\\.refs\\s*=\\s*\\{\\}\\s*:\\s*${iv}\\.refs`,
                  'g'
                )
                patched = patched.replace(re1, (_s: string, lhs: string) => {
                  // 逗号表达式：先给 IV.nullsafe 兜好再读
                  return `${lhs}=${iv}?.refs??(((${lhs})=(${iv}={...${iv}??{},refs:{}})).refs)`
                })
                // 2) 「x = IV.setupState」→ optional chaining + fallback {}
                const re2 = new RegExp(
                  `([^=!<>|&?:,;{}\\s])\\s*=\\s*${iv}\\.setupState(?!\\s*[?:=!])`,
                  'g'
                )
                patched = patched.replace(re2, (_s: string, lhs: string) => {
                  return `${lhs} = ${iv}?.setupState ?? {}`
                })
              }
            }
            if (patched !== c) {
              asset.code = patched
              count++
              console.info('[rosetta-setref-nullsafe:bundle] patched', name, '→ ivs=', ivs.size, 'ivs-values=', Array.from(ivs).join(','))
            }
          }
          if (count > 0) {
            console.info('[rosetta-setref-nullsafe:bundle] TOTAL PATCHED CHUNKS:', count)
          }
        }
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
      } as any,
      // === SSR Lucide 图标空 comment → Hydration mismatch 终根治 (Vite Resolver Plugin) ===
      //
      // 问题：本项目 Windows + Nuxt 4 SSR 环境下 @lucide/vue v1.37 在服务端
      // 一律渲染为 `<!---->` 空 Comment，客户端首帧为真实 <svg> → 每个图标
      // 都贡献 Hydration mismatch（首页 PostCard 列表级联约 80+ 处）。
      // Vue 强制拆 SSR 子树重建 → 组件实例 detach → refs null TypeError。
      //
      // 策略：仅在 SSR 构建/渲染阶段，将 @lucide/vue 解析为
      // `lib/lucide-svg-icons-all.ts` → 已枚举的 28 个图标用真实 Lucide
      // paths 字节同构；其余任何图标名走 Proxy fallback → 输出同维度
      // placeholder <svg> （第一子节点同为 <svg>，Vue 只 diff path-level，
      // 不会触发整子树 tear-down → refs null 链消失）。
      //
      // Client build 保持 npm: @lucide/vue 原生渲染（paths 100% 正确）。
      {
        name: 'rosetta-lucide-ssr-fix',
        enforce: 'pre',
        resolveId(this: { ssr?: boolean }, source: string) {
          // 限定 SSR + 精确匹配 @lucide/vue（不要匹配 `@lucide/vue/*` 子路径，
          // 目前 lucide 无 deep subpath 包，但防 future）。
          if (this.ssr && source === '@lucide/vue') {
            return pathToFileURL(resolve(__dirname, 'lib/lucide-svg-icons-all.ts')).href
          }
          return null
        }
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
      } as any
    ],
    build: {
      // Vite 8 + Rolldown：先用 rolldownOptions.codeSplitting 做细粒度自动分裂，
      // 再叠加 rollupOptions.manualChunks 保留家族语义分桶（HTTP cache invalidation 最小）。
      // 针对 build 警告 >700 kB 的 CCE9WX4N / BLhowXHz / v19V2u8s 三块，
      // 把原先塞在 vendor-vue 中的 markup/i18n/icons/http 等重库单独出桶。
      target: 'es2022',
      cssCodeSplit: true,
      // 客户端 sourcemap 默认关闭以减小生产体积；排查时用 NUXT_CLIENT_SOURCE_MAP=true 开启。
      sourcemap: CLIENT_SOURCE_MAP,
      minify: 'esbuild',
      chunkSizeWarningLimit: 700,
      rolldownOptions: {
        output: {
          // Vite 8 当前 CodeSplittingOptions 仅接收布尔（true=开启自动分裂），
          // 其它尺寸约束通过 rollup 层 chunkSizeWarningLimit + 手工分桶实现。
          codeSplitting: true
        }
      },
      rollupOptions: {
        output: {
          manualChunks: (id: string) => {
            if (/node_modules[\\/](vue|@vue\/)[\\/]/.test(id)) return 'vendor-vue-core'
            if (/[\\/]nuxt[\\/](dist|app)[\\/]/.test(id) || /@nuxt[\\/]nitro-server[\\/]/.test(id)) return 'vendor-nuxt-runtime'
            if (/node_modules[\\/](pinia|@pinia[\\/])[\\/]/.test(id)) return 'vendor-state'
            if (/node_modules[\\/]@vueuse[\\/]/.test(id)) return 'vendor-vueuse'
            if (/node_modules[\\/](i18next|@intlify[\\/]|vue-i18n|@nuxtjs[\\/]i18n)[\\/]/.test(id)) return 'vendor-i18n'
            if (/node_modules[\\/](marked|dompurify|highlight\\.js|shiki|rehype|remark|prism|markdown-it)[\\/]/.test(id)) return 'vendor-markup'
            if (/node_modules[\\/]zod[\\/]/.test(id)) return 'vendor-zod'
            if (/node_modules[\\/](echarts|zrender|vue-echarts)[\\/]/.test(id)) return 'vendor-heavy-viz'
            if (/node_modules[\\/]viewerjs[\\/]/.test(id)) return 'vendor-heavy-gallery'
            if (/node_modules[\\/](@floating-ui|radix-vue|class-variance-authority|clsx|tailwind-merge|reka-ui)[\\/]/.test(id)) return 'vendor-shadcn'
            if (/node_modules[\\/](@iconify|lucide)[\\/]/.test(id)) return 'vendor-icons'
            if (/node_modules[\\/](axios|@tanstack|swrv|ohmyfetch|ofetch|ufo|hookable|h3|nitropack)[\\/]/.test(id)) return 'vendor-http'
            if (/node_modules[\\/](date-fns|dayjs|defu|unhead|@unhead)[\\/]/.test(id)) return 'vendor-util'
            return
          }
        }
      }
    },
    optimizeDeps: {
      // 提前 bundle 重依赖，减少首屏 HMR + cold-start 延迟
      include: [
        'pinia',
        '@vueuse/core',
        'zod',
        'marked',
        'dompurify',
        'class-variance-authority',
        'clsx',
        'tailwind-merge'
      ],
      // 排除被 Nuxt 自动按别名解析的本地包，防 double-bundle
      exclude: ['@vite/client']
    }
  },

  // Tailwind v4：@tailwindcss/vite 插件提供 Oxide 加速与 HMR；
  // @tailwindcss/postcss 负责 @theme 变量解析与 utility 生成。
  // 两者配合：Vite 插件处理构建，PostCSS 插件处理 CSS 转换。
  postcss: {
    plugins: {
      '@tailwindcss/postcss': {},
      'autoprefixer': {}
    }
  },

  // 禁用 Nuxt 遥测，避免 nostics 在 Vite 热链路上反复触发 NUXT_E1001 警告
  telemetry: false,

  eslint: {
    config: {
      stylistic: {
        commaDangle: 'never',
        braceStyle: '1tbs'
      }
    }
  },

  i18n: {
    locales: [
      { code: 'zh', name: '简体中文', file: 'zh.json' },
      { code: 'en', name: 'English', file: 'en.json' },
      { code: 'ja', name: '日本語', file: 'ja.json' },
      { code: 'zh_Hant', name: '繁體中文', file: 'zh_Hant.json' }
    ],
    defaultLocale: 'zh',
    langDir: './locales',
    vueI18n: './index.ts',
    strategy: 'no_prefix',
    detectBrowserLanguage: {
      useCookie: true,
      cookieKey: 'rosetta_lang',
      redirectOn: 'root'
    }
  }
})
