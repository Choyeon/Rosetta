// https://nuxt.com/docs/api/configuration/nuxt-config
import { fileURLToPath } from "node:url";
import tailwindcss from "@tailwindcss/vite";

const ROOT_DIR = fileURLToPath(new URL("./", import.meta.url));

const API_BASE_URL = process.env.API_BASE_URL || "http://127.0.0.1:8000";
const SSR_API_BASE_URL = process.env.API_BASE_URL_SSR || API_BASE_URL;

export default defineNuxtConfig({
  // Nuxt 4：因 app/ 目录存在会自动开启 app-as-srcDir（~/ -> app/），
  // 但我们的 assets/components/pages 都在项目根下，故显式 srcDir="." 保持稳定路径解析。
  srcDir: ".",
  compatibilityDate: "2025-08-10",
  devtools: { enabled: true },

  // ============================================================
  // 渲染模式：Nuxt 4 默认 SSR，与原 Astro "hybrid" 等价。
  //   - 大部分内容页静态化（由 Nitro prerender 配置控制）
  //   - admin / login / oobe / notifications / 搜索结果 走 SSR（动态）
  // ============================================================
  ssr: true,

  // ============================================================
  // 实验特性
  // ============================================================
  experimental: {
    /** 允许在页面/组件中写 asyncData/useFetch 时使用 payload 抽取 */
    payloadExtraction: true,
    /** 优化模板编译后的客户端水合大小 */
    treeshakeClientOnly: true,
    /** Nuxt 4 共享路由片段缓存，对文章详情页极有用 */
    componentIslands: {
      selectiveClient: true,
    },
  },

  // ============================================================
  // 全局模块（版本已通过 npm view 确认真实存在）
  // ============================================================
  modules: [
    "@nuxtjs/color-mode",         // Dark/Light 自动切换
    "@nuxtjs/seo",                // sitemap/robots/og/schema-org 统一管理（含 sitemap + robots）
    "@nuxt/content",               // 替代 Astro Content Collections
    "@nuxt/icon",                  // 替代 astro-icon（Iconify 离线 + 在线）
    "@nuxt/image",                 // 图片优化
    // "@nuxt/fonts",              // 字体优化（需联网下载 Google Fonts，离线禁用，改为本地系统字体栈兜底）
    // "@nuxt/scripts",            // 第三方脚本安全加载（离线/无外网时禁用，避免 Gravatar 等脚本下载超时）
    "@nuxt/ui",                    // 官方 UI 组件库（shadcn 风格）
    "@pinia/nuxt",                 // 状态管理（含 defineStore/storeToRefs 自动导入）
    "@vueuse/nuxt",                // VueUse composables
    "@vueuse/motion/nuxt",         // 动画（CSS/View Transitions 轻量）
    "nuxt-auth-utils",             // 鉴权中间件辅助
    "@nuxtjs/i18n",                // i18n：4 语言（zh-CN/zh-TW/en/ja）
  ],


  // ============================================================
  // Nitro（服务端 / 构建引擎）
  // ============================================================
  nitro: {
    // 预渲染内容路由（保持与 Astro output:static 等价的首屏速度 + SEO）
    prerender: {
      crawlLinks: false, // 离线构建禁用爬虫扫描（需后端运行时再启用）
      failOnError: false, // 预渲染页面报错不阻断打包（SSR 报错在 dev 期单独调试）
      routes: [
        "/403",
        "/404",
        "/500",
      ],
    },
    // 开发 / SSR 阶段直接代理到 FastAPI 后端（同源免 CORS）
    devProxy: {
      "/api": { target: API_BASE_URL, changeOrigin: true, prependPath: false },
      "/media": { target: API_BASE_URL, changeOrigin: true, prependPath: false },
    },
    // 生产部署的 routeRules 中，也做代理映射（使浏览器端仍走同源 /api）
    routeRules: {
      "/api/**": {
        proxy: `${SSR_API_BASE_URL}/api/**`,
        cache: false,
        cors: true,
      },
      "/media/**": {
        proxy: `${SSR_API_BASE_URL}/media/**`,
        headers: { "cache-control": "public, max-age=86400, immutable" },
      },
      // 预渲染（静态化）页面：永久缓存
      "/": { prerender: true, isr: true, swr: 3600 },
      "/posts": { prerender: true, isr: true, swr: 600 },
      "/archive/**": { prerender: true, isr: true, swr: 3600 },
      "/tags/**": { prerender: true, isr: true, swr: 600 },
      "/categories/**": { prerender: true, isr: true, swr: 600 },
      "/posts/**": { isr: true, swr: 600, headers: { "cache-control": "public, s-maxage=600, stale-while-revalidate=86400" } },
      "/dynamic/**": { isr: true, swr: 300 },
      "/gallery/**": { isr: true, swr: 3600 },
      "/anime": { prerender: true, isr: true, swr: 3600 },
      "/bangumi": { prerender: true, isr: true, swr: 3600 },
      "/about": { prerender: true, isr: true, swr: 3600 },
      "/friends": { prerender: true, isr: true, swr: 3600 },
      "/guestbook": { prerender: true, isr: true, swr: 300 },
      "/sponsor": { prerender: true, isr: true, swr: 3600 },
      // 必须 SSR 的动态页面
      "/admin/**": { ssr: true, cache: false, headers: { "cache-control": "private, no-store" } },
      "/login": { ssr: true, cache: false },
      "/oobe": { ssr: true, cache: false },
      "/notifications/**": { ssr: true, cache: false, headers: { "cache-control": "private, no-store" } },
      "/search": { ssr: true, cache: false },
      // 4xx / 5xx
      "/403": { prerender: true },
      "/404": { prerender: true },
      "/500": { prerender: true },
    },
    esbuild: {
      options: {
        target: "es2022",
        drop: ["debugger"],
        pure: ["console.log", "console.debug"],
      },
    },
  },

  // ============================================================
  // 运行时环境变量（客户端 / 服务端可见度控制）
  //   public runtimeConfig → 客户端可见
  //   顶级 runtimeConfig → 仅服务端可见
  // ============================================================
  runtimeConfig: {
    // ——— 仅服务端可见 ———
    apiBaseUrlSsr: SSR_API_BASE_URL,
    sessionSecret: process.env.SESSION_SECRET || "rosetta-change-me-in-prod",
    public: {
      // ——— 客户端可见 ———
      siteName: "Rosetta",
      siteUrl: process.env.SITE_URL || "http://localhost:3000",
      apiBaseUrl: "", // 留空 = 浏览器端走同源 /api（Nitro routeRules 代理）
      enableComments: true,
      enableBangumi: true,
      enableAnime: true,
      enableGallery: true,
      enableDynamic: true,
      enableGuestbook: true,
      enableFriends: true,
      enableSponsor: true,
    },
  },

  // ============================================================
  // 别名：与 Astro 保持一致，方便迁移
  //   Nuxt/vite 需真实的绝对路径（用 fileURLToPath + import.meta.url 解析）
  // ============================================================
  alias: {
    "@": ROOT_DIR,
    "@components": `${ROOT_DIR}components`,
    "@assets": `${ROOT_DIR}assets`,
    "@constants": `${ROOT_DIR}constants`,
    "@utils": `${ROOT_DIR}utils`,
    "@i18n": `${ROOT_DIR}i18n`,
    "@layouts": `${ROOT_DIR}layouts`,
    "@api": `${ROOT_DIR}server/api`,
    "@stores": `${ROOT_DIR}stores`,
    "@types": `${ROOT_DIR}types`,
    "@composables": `${ROOT_DIR}composables`,
    "@plugins": `${ROOT_DIR}plugins`,
  },

  // ============================================================
  // 导入自动注册（减少 import 样板）
  // ============================================================
  imports: {
    dirs: [
      "stores",
      "composables/**",
      "utils/**",
    ],
    presets: [
      { from: "dayjs", imports: [{ name: "default", as: "dayjs" }] },
    ],
  },

  // ============================================================
  // Tailwind / CSS
  //   Tailwind v4 不走 @nuxtjs/tailwindcss 模块：
  //     - 开发/构建阶段由 vite 插件 @tailwindcss/vite 负责（零 PostCSS）
  //     - 仍保留 PostCSS 管线（autoprefixer + @tailwindcss/postcss）作为 SSR/Nitro 兜底
  // ============================================================
  css: [
    "~/assets/css/main.css",
    "~/assets/css/tokens.css",
    // —— 三方库官方样式（Nuxt SSR 统一注入，避免组件里单独 import 导致 HMR 样式抖动）
    "aplayer/dist/APlayer.min.css",
    "katex/dist/katex.min.css",
    "photoswipe/dist/photoswipe.css",
    "@fancyapps/ui/dist/fancybox/fancybox.css",
  ],
  postcss: {
    plugins: {
      "@tailwindcss/postcss": {},
    },
  },
  // （vite.plugins 已经配置了 tailwindcss()，见下方）
  tailwindcss: {
    cssPath: "~/assets/css/main.css",
    viewer: false,
  },

  // ============================================================
  // Vite
  // ============================================================
  vite: {
    plugins: [tailwindcss()],
    optimizeDeps: {
      include: [
        "dayjs",
        "pinia",
        "dompurify",
        "highlight.js",
        "fuse.js",
      ],
    },
    server: {
      proxy: {
        // 开发阶段代理到后端（同源免 CORS），与 Astro astro.config.mjs vite.server.proxy 保持行为一致
        "/api": {
          target: API_BASE_URL,
          changeOrigin: true,
          secure: false,
        },
        "/media": {
          target: API_BASE_URL,
          changeOrigin: true,
          secure: false,
        },
      },
      fs: {
        allow: [".."], // 允许读取 root public/static（打包器共享资源）
      },
    },
    resolve: {
      alias: {
        "highlight.js/styles": "highlight.js/scss",
      },
    },
    build: {
      target: "es2022",
      minify: "esbuild",
      cssCodeSplit: true,
      assetsInlineLimit: 4096,
      sourcemap: false,
    },
  },

  // ============================================================
  // App 全局
  // ============================================================
  app: {
    head: {
      htmlAttrs: { lang: "zh-CN" },
      title: "Rosetta — 轻羽博客系统",
      meta: [
        { charset: "utf-8" },
        { name: "viewport", content: "width=device-width, initial-scale=1, viewport-fit=cover" },
        { name: "theme-color", content: "#6366f1" },
        { name: "description", content: "Rosetta：以内容与体验为核心的现代化博客系统，Vue/Nuxt + FastAPI 双端构建" },
      ],
      link: [
        { rel: "icon", type: "image/svg+xml", href: "/favicon.svg" },
      ],
    },
    /** 页面跳转过渡：保持与 Swup transition-swup-* 一致的视觉体验 */
    pageTransition: { name: "page", mode: "out-in" },
    layoutTransition: { name: "layout", mode: "out-in" },
  },

  // ============================================================
  // SEO (@nuxtjs/seo)
  // ============================================================
  site: {
    url: process.env.SITE_URL || "http://localhost:3000",
    name: "Rosetta",
    description: "Rosetta — 轻羽博客系统",
    defaultLocale: "zh-CN",
  },
  sitemap: {
    // 离线构建禁用自定义数据源（运行时后端启动后，/api/__sitemap__/urls 会自动注入）
    // sources: ["/api/__sitemap__/urls"],
    exclude: [
      "/admin/**",
      "/login/**",
      "/oobe/**",
      "/api/**",
      "/403",
      "/500",
    ],
    autoLastmod: true,
  },
  robots: {
    UserAgent: "*",
    Disallow: ["/admin", "/login", "/oobe", "/api"],
    Allow: "/",
  },

  // ============================================================
  // Content（@nuxt/content 3.x — 替代 Astro Content Collections）
  //   目录约定：content/posts/*.md   → 路由 /posts/<slug>
  //            content/spec/*.md    → 路由 /spec/<slug>（独立页面内容层，pages 层可覆盖）
  //            content/dynamic/*.md → 路由 /dynamic/<date>
  //   frontmatter schema 与 Astro src/content.config.ts 1:1 对齐
  // ============================================================
  content: {
    // 开发期文件变更实时热更
    watch: true,
    // 自动生成 content 侧边导航 /tags, /categories 等可直接用 <ContentNavigation>
    navigation: {
      fields: ["published", "pinned", "category", "tags", "image", "author", "description", "draft", "lang"],
    },
    // Content 数据源（posts/spec/dynamic 对应 Astro src/content/{posts,spec,dynamic}）
    sources: {
      content: {
        driver: "fs",
        prefix: "/",
        base: "./content",
      },
    },
    // Markdown 解析 + 插件（与 Astro remarkPlugins 对齐，减少能力丢失）
    markdown: {
      anchorLinks: true,
      toc: { depth: 3, searchDepth: 4 },
      // MDC 语法（Astro 里的 ::github{repo="..."} 也支持）
      mdc: true,
      remarkPlugins: {
        "remark-gfm": {},
        "remark-math": {},
        "remark-directive": {},
      },
      rehypePlugins: {
        "rehype-katex": {},
        "rehype-slug": {},
        "rehype-highlight": {},
      },
    },
    // Shiki 代码高亮 — 匹配 main.css 的 one-light / one-dark-pro 两套 data-theme
    highlight: {
      theme: {
        default: "one-light",
        "one-dark-pro": "one-dark-pro",
      },
      langs: [
        "md","mdc","markdown","json","yaml","yml","toml","bash","sh","shell","powershell","cmd",
        "ts","tsx","js","jsx","vue","svelte","astro","html","xml","css","scss","sass","stylus",
        "python","go","rust","java","kotlin","c","cpp","cs","sql","dockerfile","nginx","diff","graphql",
        "mermaid","plantuml","toml","dockerfile","docker",
      ],
      preload: ["ts","tsx","js","jsx","vue","python","go","bash","sh","yaml","yml","json","md","mdx","sql","css","scss","html","rust","java","kotlin","c","cpp","dockerfile","diff","mermaid","plantuml","toml"],
    },
    // 支持 .md / .mdx / .yml / .json / .csv
    contentHead: true,
    // 全文检索（替代 Pagefind）
    fullTextSearchFields: ["title", "description", "content", "tags", "category", "author"],
  },

  // ============================================================
  // @nuxt/icon
  // ============================================================
  icon: {
    provider: "iconify",
    collections: [
      "material-symbols",
      "fa7-brands",
      "fa7-regular",
      "fa7-solid",
      "simple-icons",
      "mdi",
      "mingcute",
      "heroicons",
      "heroicons-outline",
      "heroicons-solid",
    ],
    mode: "css",
  },

  // ============================================================
  // @nuxt/image
  // ============================================================
  image: {
    quality: 80,
    format: ["avif", "webp", "jpg"],
    domains: [
      "localhost",
      "127.0.0.1",
      "cdn.jsdelivr.net",
      "fastly.jsdelivr.net",
      "raw.githubusercontent.com",
    ],
  },

  // ============================================================
  // Color Mode（@nuxtjs/color-mode）
  // ============================================================
  colorMode: {
    preference: "system",
    fallback: "light",
    classSuffix: "",
    dataValue: "theme",
    storageKey: "rosetta-color-mode",
  },

  // ============================================================
  // i18n (@nuxtjs/i18n 10.x — 4 语言：zh-CN / zh-TW / en / ja)
  //   - Composition API（legacy: false）与 i18n/index.ts 对齐
  //   - 路由前缀策略：默认语言 zh-CN 无前缀，其余 3 种加前缀 /zh-TW /en /ja
  //   - 浏览器语言检测：初次访问时根据 Accept-Language 自动跳转
  //   - Cookie 存储键：rosetta_lang（与 useApi.ts / backend i18n 对齐）
  // ============================================================
  i18n: {
    strategy: "prefix_except_default",
    defaultLocale: "zh-CN",
    locales: [
      { code: "zh-CN", language: "zh-CN", name: "简体中文", flag: "🇨🇳", file: undefined },
      { code: "zh-TW", language: "zh-TW", name: "繁體中文", flag: "🇹🇼", file: undefined },
      { code: "en",    language: "en-US", name: "English",    flag: "🇺🇸", file: undefined },
      { code: "ja",    language: "ja-JP", name: "日本語",    flag: "🇯🇵", file: undefined },
    ],
    detectBrowserLanguage: {
      useCookie: true,
      cookieKey: "rosetta_lang",
      cookieSecure: process.env.NODE_ENV === "production",
      cookieSameSite: "lax",
      alwaysRedirect: false,
      fallbackLocale: "en",
      redirectOn: "root",
    },
    vueI18n: "./i18n/index.ts",
    langDir: undefined,
    vueRouter: {
      skipSettingLocaleOnNavigate: false,
    },
  },

  // ============================================================
  // @nuxt/ui（ShadCN-style 组件）
  // ============================================================
  ui: {
    /** 保持与 Rosetta 设计系统一致的基调 */
    theme: {
      colors: {
        primary: "indigo",
        neutral: "slate",
      },
      radius: "lg",
    },
  },

  // ============================================================
  // TypeScript
  // ============================================================
  typescript: {
    strict: true,
    typeCheck: false, // 显式执行 `pnpm typecheck` 才跑；dev 阶段用 Volar/HMR 提升速度
    shim: false,
  },

  // ============================================================
  // Feature flags（禁用不需要的能力节省构建时间）
  // ============================================================
  features: {
    inlineStyles: true,
  },
});
