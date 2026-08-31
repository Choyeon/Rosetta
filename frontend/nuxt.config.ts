// https://nuxt.com/docs/api/configuration/nuxt-config
import { fileURLToPath } from 'node:url'
import { dirname, resolve } from 'node:path'

const __filename = fileURLToPath(import.meta.url)
const __dirname = dirname(__filename)
//
// 后端连接配置（单源，不要再在源码各处散落写默认 127.0.0.1/localhost:3000）：
//   - BACKEND_HOST / BACKEND_PORT：Nitro（server routes）连 FastAPI 的地址
//   - SSR_API_BASE_URL：完整覆盖（含协议/端口/api 前缀），生产多网卡部署时直接写即可
//   - SITE_URL：对外公开域名（生成 RSS/sitemap/robots/邮件链接用），如 https://blog.example.com
// 生产部署必须显式声明；本地开发缺失时使用 SSR 请求 Host 推导，禁止写死 localhost 字面量。
const BACKEND_PORT = process.env.BACKEND_PORT || ''
const BACKEND_HOST = process.env.BACKEND_HOST || ''
const SSR_API_BASE = process.env.SSR_API_BASE_URL || ''
const SITE_URL = process.env.SITE_URL || ''

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
    '@nuxtjs/tailwindcss',
    '@nuxtjs/i18n',
    '@pinia/nuxt'
  ],

  // ============================================================
  //  SSR 策略（严格遵循 AGENTS.md：「从 SPA 模式渐进式开启 SSR，不做一次性全量切换」）
  //   - 全局基线 ssr: false → 所有页面按 SPA 运行，规避 reka-ui Primitive/Tooltip/PopperAnchor
  //     等组件在 SSR 下输出 span/button/PrimitiveSlot undefined 的 hydration mismatch。
  //   - 对 SEO 强相关页面（文章列表/详情/分类/标签/归档等），通过 routeRules 或页面内部
  //     definePageMeta({ ssr: true }) 逐个渐进式开启 SSR，调试通过后再放开下一个。
  //   - 管理后台 / login / register / oobe 等页面始终 ssr: false（需要 localStorage 登录态
  //     与重度交互，SSR 既无收益也容易出问题）。
  // ============================================================
  ssr: false,

  // 渐进式 SSR：逐个对 SEO 敏感页面开启（需要配合各页面首屏 DOM 审计后再添加条目，
  // 确保 reka-ui 组件已被 ClientOnly 隔离或首屏渲染路径完全不经过它们）。
  // routeRules: {
  //   '/posts/**':        { ssr: true },
  //   '/posts/[slug]/**': { ssr: true },
  //   '/categories/**':   { ssr: true },
  //   '/tags/**':         { ssr: true },
  //   '/archive':         { ssr: true },
  //   '/':                { ssr: true },
  // },

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
    // Nuxt 原生页面过渡：由框架在 NuxtPage 内部正确挂载，
    // 避免在 app.vue 手动嵌套 Transition/Suspense 引发渲染死锁
    pageTransition: { name: 'page-fade', mode: 'out-in' },
    head: {
      title: 'Rosetta',
      htmlAttrs: { lang: 'zh-CN' },
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
        { rel: 'stylesheet', href: 'https://cdn.jsdelivr.net/npm/flag-icons@7.2.3/css/flag-icons.min.css' },
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

  routeRules: {
    // === Vite 内部虚拟文件：禁止 swr/ssr 缓存与 spa-fallback 拦截，
    // 否则 Nuxt 会把 /@vite/client 当作不存在的页面路由返回 404（"Page not found: /@vite/client"），
    // 触发 Vite HMR 客户端初始化失败。
    '/@vite/**': { ssr: false, swr: false, headers: { 'cache-control': 'no-store' } },
    '/@id/**': { ssr: false, swr: false, headers: { 'cache-control': 'no-store' } },
    '/@fs/**': { ssr: false, swr: false, headers: { 'cache-control': 'no-store' } },
    '/_nuxt/**': { ssr: false, swr: false, headers: { 'cache-control': 'public, max-age=31536000, immutable' } },
    // === SPA 模式：需要登录态 / 重型交互 / 不被搜索引擎索引 ===
    '/admin/**': { ssr: false },
    '/login': { ssr: false },
    '/register': { ssr: false },
    '/oobe': { ssr: false },
    // === 公开页面 SSR + SWR（Stale-While-Revalidate）缓存，降低后端压力 ===
    // 已完成组件首屏 DOM 审计：PostCard/PostList 等首屏路径不依赖 reka-ui Primitive
    // 的 mounted-only 特性，LocaleSwitcher/DropdownMenu 在 SSR 路径下渲染为"关闭态"
    // （默认未设置 default-open），无 hydration mismatch 风险。
    '/': { ssr: true, swr: 3600 },
    '/posts': { ssr: true, swr: 3600 },
    '/posts/**': { ssr: true, swr: 600 },
    '/categories': { ssr: true, swr: 3600 },
    '/categories/**': { ssr: true, swr: 3600 },
    '/tags': { ssr: true, swr: 3600 },
    '/tags/**': { ssr: true, swr: 3600 },
    '/series': { ssr: true, swr: 3600 },
    '/series/**': { ssr: true, swr: 3600 },
    '/archive': { ssr: true, swr: 3600 },
    '/about': { ssr: true, swr: 86400 },
    '/friends': { ssr: true, swr: 86400 },
    '/gallery': { ssr: true, swr: 86400 },
    '/guestbook': { ssr: true, swr: 600 },
    '/activity': { ssr: true, swr: 600 },
    '/page/**': { ssr: true, swr: 3600 },
    // === 静态产物：SEO/RSS/Robots server routes 缓存头 + SWR ===
    '/rss.xml': {
      swr: 1800,
      headers: {
        'content-type': 'application/rss+xml; charset=utf-8',
        'cache-control': 'public, max-age=1800, s-maxage=1800'
      }
    },
    '/sitemap.xml': {
      swr: 3600,
      headers: {
        'content-type': 'application/xml; charset=utf-8',
        'cache-control': 'public, max-age=3600, s-maxage=3600'
      }
    },
    '/robots.txt': {
      swr: 3600,
      headers: {
        'content-type': 'text/plain; charset=utf-8',
        'cache-control': 'public, max-age=3600, s-maxage=3600'
      }
    }
  },

  compatibilityDate: '2026-06-30',

  nitro: {
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

  postcss: {
    plugins: {
      tailwindcss: {},
      autoprefixer: {}
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
