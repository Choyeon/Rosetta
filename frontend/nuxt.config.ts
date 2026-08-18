// https://nuxt.com/docs/api/configuration/nuxt-config

const BACKEND_PORT = process.env.BACKEND_PORT || '8000'
const BACKEND_HOST = process.env.BACKEND_HOST || '127.0.0.1'

export default defineNuxtConfig({
  modules: [
    '@nuxt/eslint',
    '@nuxtjs/tailwindcss',
    '@nuxtjs/i18n',
    '@pinia/nuxt'
  ],

  // 全局开启 SSR：公开页面数据在服务端渲染到 HTML，
  //   1) 彻底解决"从详情返回首页/列表空白"：数据跟着 HTML 一起下发，不再依赖 onMounted 才拉；
  //   2) 让搜索引擎直接抓到正文，解决 SEO 空壳问题。
  // 管理后台、登录注册、OOBE 通过 routeRules 单独关闭 SSR（需要 localStorage 登录态和重交互）。
  ssr: true,

  routeRules: {
    // === SPA 模式：需要登录态 / 重型交互 / 不被搜索引擎索引 ===
    '/admin/**': { ssr: false },
    '/login':    { ssr: false },
    '/register': { ssr: false },
    '/oobe':     { ssr: false },
    // === 公开页面 SSR + SWR（Stale-While-Revalidate）缓存，降低后端压力 ===
    '/':               { swr: 3600 },
    '/posts':          { swr: 3600 },
    '/posts/**':       { swr: 600  },
    '/categories':     { swr: 3600 },
    '/categories/**':  { swr: 3600 },
    '/about':          { swr: 86400 },
    '/archive':        { swr: 3600 },
    '/friends':        { swr: 86400 },
    '/gallery':        { swr: 86400 },
    '/guestbook':      { swr: 600  },
    '/activity':       { swr: 600  }
  },

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

  devtools: {
    enabled: true
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
        { rel: 'alternate', type: 'application/rss+xml', title: 'Rosetta · RSS Feed', href: '/api/blog/rss' },
        // Sitemap 提示
        { rel: 'sitemap', type: 'application/xml', title: 'Sitemap', href: '/api/blog/sitemap.xml' }
      ]
    }
  },

  css: ['~/assets/css/main.css'],

  runtimeConfig: {
    public: {
      apiBase: process.env.API_BASE_URL || '/api'
    }
  },

  compatibilityDate: '2026-06-30',

  nitro: {
    devProxy: {
      '/api': {
        target: `http://${BACKEND_HOST}:${BACKEND_PORT}/api`,
        changeOrigin: true
      }
    }
  },

  postcss: {
    plugins: {
      tailwindcss: {},
      autoprefixer: {}
    }
  },

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
