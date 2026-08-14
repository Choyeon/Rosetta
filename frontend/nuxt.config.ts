// https://nuxt.com/docs/api/configuration/nuxt-config
export default defineNuxtConfig({
  modules: [
    '@nuxt/eslint',
    '@nuxtjs/tailwindcss',
    '@nuxtjs/i18n',
    '@pinia/nuxt'
  ],

  alias: {
    '@': '.',
    '@@': '.'
  },

  devtools: {
    enabled: true
  },

  // css 路径: ~/assets = app/assets（已存在）
  css: ['~/assets/css/main.css'],

  runtimeConfig: {
    public: {
      apiBase: process.env.API_BASE_URL || 'http://localhost:8000/api'
    }
  },

  // 显式声明自动导入目录（相对路径相对于 rootDir = frontend/）
  imports: {
    dirs: [
      './composables',
      './composables/**',
      './stores'
    ]
  },

  // 显式声明组件目录
  components: [
    { path: './components', pathPrefix: false },
    { path: './app/components', pathPrefix: false }
  ],

  // layouts / plugins 目录（相对 rootDir）
  dir: {
    layouts: './layouts',
    plugins: './plugins'
  },

  i18n: {
    locales: [
      { code: 'zh', name: '简体中文', file: 'zh.json' },
      { code: 'en', name: 'English', file: 'en.json' },
      { code: 'ja', name: '日本語', file: 'ja.json' },
      { code: 'zh_Hant', name: '繁體中文', file: 'zh_Hant.json' }
    ],
    defaultLocale: 'zh',
    // @nuxtjs/i18n v10 中 langDir/vueI18n 路径均相对 srcDir/i18n/ 目录（模块的 base 目录）
    // 因此 frontend/i18n/locales/ → './locales/' ; frontend/i18n/index.ts → './index.ts'
    langDir: './locales/',
    vueI18n: './index.ts',
    strategy: 'no_prefix',
    detectBrowserLanguage: {
      useCookie: true,
      cookieKey: 'i18n_redirected',
      redirectOn: 'root'
    }
  },

  // 全局关闭 SSR（纯 SPA），避免 Pinia store payload 序列化和 useFetch 服务端渲染问题
  ssr: false,

  postcss: {
    plugins: {
      tailwindcss: {},
      autoprefixer: {}
    }
  },

  routeRules: {
  },

  compatibilityDate: '2026-06-30',

  eslint: {
    config: {
      stylistic: {
        commaDangle: 'never',
        braceStyle: '1tbs'
      }
    }
  },

  app: {
    head: {
      title: 'Rosetta',
      meta: [
        { charset: 'utf-8' },
        { name: 'viewport', content: 'width=device-width, initial-scale=1' },
        { name: 'description', content: 'Rosetta - Modern Blog System' }
      ],
      link: [
        { rel: 'icon', type: 'image/x-icon', href: '/favicon.ico' }
      ]
    }
  }
})
