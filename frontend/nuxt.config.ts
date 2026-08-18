// https://nuxt.com/docs/api/configuration/nuxt-config
import { spawn } from 'node:child_process'
import { existsSync, watch } from 'node:fs'
import { resolve, dirname, join } from 'node:path'
import { fileURLToPath } from 'node:url'
import { createConnection } from 'node:net'
import type { NuxtModule } from 'nuxt/schema'

const BACKEND_PORT = process.env.BACKEND_PORT || '8000'
const BACKEND_HOST = process.env.BACKEND_HOST || '127.0.0.1'
const BACKEND_STARTED_KEY = '__rosetta_backend_started__'

function isPortTaken(host: string, port: number): Promise<boolean> {
  return new Promise((res) => {
    const sock = createConnection({ host, port, timeout: 1500 }, () => {
      sock.destroy()
      res(true)
    })
    sock.on('error', () => res(false))
    sock.on('timeout', () => {
      sock.destroy()
      res(false)
    })
  })
}

function findProjectRoot(start: string): string {
  let cur = start
  for (let i = 0; i < 10; i++) {
    const hasBackend = existsSync(join(cur, 'backend', 'main.py'))
    const hasLock = existsSync(join(cur, 'uv.lock')) || existsSync(join(cur, 'pyproject.toml'))
    if (hasBackend && hasLock) return cur
    const parent = resolve(cur, '..')
    if (parent === cur) break
    cur = parent
  }
  return start
}

function killProcessTree(pid: number | undefined) {
  if (!pid) return
  try {
    if (process.platform === 'win32') {
      spawn('taskkill', ['/PID', String(pid), '/T', '/F'], { stdio: 'ignore' })
    } else {
      process.kill(-pid, 'SIGTERM')
    }
  } catch { /* ignore */ }
}

function createBackendStarter(projectRoot: string) {
  let backendProcess: ReturnType<typeof spawn> | null = null
  let restarting = false

  const logger = (tag: string, ...args: unknown[]) => {
    const color = tag === 'ok' ? '\x1b[32m' : tag === 'err' ? '\x1b[31m' : tag === 'warn' ? '\x1b[33m' : '\x1b[36m'
    console.log(`${color}[nuxt:backend]\x1b[0m`, ...args)
  }

  const startBackend = () => {
    const hasUvLock = existsSync(join(projectRoot, 'uv.lock'))
    const bin: string = hasUvLock ? 'uv' : process.platform === 'win32' ? 'py' : 'python3'
    const args: string[] = hasUvLock
      ? ['run', 'uvicorn', 'backend.main:app', `--host=${BACKEND_HOST}`, `--port=${BACKEND_PORT}`, '--no-access-log']
      : ['-m', 'uvicorn', 'backend.main:app', `--host=${BACKEND_HOST}`, `--port=${BACKEND_PORT}`, '--no-access-log']

    logger('info', `启动后端: ${bin} ${args.join(' ')}`)
    logger('info', `工作目录: ${projectRoot}`)

    const env: NodeJS.ProcessEnv = {
      ...process.env,
      PYTHONUNBUFFERED: '1',
      PYTHONPATH: `${projectRoot}${process.platform === 'win32' ? ';' : ':'}${process.env.PYTHONPATH || ''}`
    }

    const child = spawn(bin, args, {
      cwd: projectRoot,
      env,
      stdio: ['ignore', 'pipe', 'pipe'],
      windowsHide: true
    })

    child.stdout.on('data', (chunk: Buffer) => {
      const lines = chunk.toString().replace(/\s+$/, '').split('\n')
      for (const line of lines) {
        if (line.trim()) logger('info', '•', line.trim())
      }
    })

    child.stderr.on('data', (chunk: Buffer) => {
      const lines = chunk.toString().replace(/\s+$/, '').split('\n')
      for (const raw of lines) {
        const line = raw.trim()
        if (!line) continue
        if (line.includes('Application startup complete') || line.includes('Uvicorn running on')) {
          logger('ok', '✨', line)
        } else if (line.includes('ERROR') || line.includes('Error') || line.includes('Exception')) {
          logger('err', line)
        } else {
          logger('info', line)
        }
      }
    })

    child.on('error', (err: Error) => logger('err', '启动失败:', err.message))
    child.on('close', (code, signal) => {
      if (!restarting) logger('warn', `后端进程已退出 code=${code} signal=${signal}`)
      if (backendProcess === child) backendProcess = null
    })

    return child
  }

  const cleanup = () => {
    if (watcher) {
      try {
        watcher.close()
      } catch { /* ignore */ }
    }
    if (backendProcess) {
      killProcessTree(backendProcess.pid)
      backendProcess = null
    }
  }

  let watcher: ReturnType<typeof watch> | null = null

  const start = async () => {
    const g = globalThis as unknown as Record<string, boolean>
    if (g[BACKEND_STARTED_KEY]) return
    g[BACKEND_STARTED_KEY] = true

    const alreadyListening = await isPortTaken(BACKEND_HOST, Number(BACKEND_PORT))
    if (alreadyListening) {
      logger('info', `端口 ${BACKEND_HOST}:${BACKEND_PORT} 已有服务监听，跳过后端启动`)
      return
    }

    logger('info', '自动启动 Rosetta 后端（FastAPI）...')
    backendProcess = startBackend()

    const oobeLock = join(projectRoot, '.oobe_complete')
    try {
      watcher = watch(projectRoot, { persistent: false }, (eventType, filename) => {
        if (filename === '.oobe_complete' && eventType === 'rename' && existsSync(oobeLock) && !restarting) {
          restarting = true
          logger('info', '检测到 OOBE 完成，重启后端应用新配置...')
          killProcessTree(backendProcess?.pid)
          setTimeout(() => {
            backendProcess = startBackend()
            restarting = false
          }, 1500)
        }
      })
    } catch (e) {
      logger('warn', '无法启动 OOBE 文件监听：', (e as Error).message)
    }

    for (const sig of ['exit', 'SIGINT', 'SIGTERM', 'SIGHUP', 'beforeExit']) {
      process.on(sig as NodeJS.Signals | 'beforeExit', cleanup)
    }
  }

  return { start, cleanup }
}

// 注意：后端启动逻辑放在 Nuxt 模块中（而非 Nitro 插件），
// 因为在 SPA 模式下 Nitro 插件初始化较晚，会导致前端先加载而后端未就绪。
// 使用 globalThis 标志防止重复启动（即使 Nitro 插件也尝试启动）。
const MODULE_HERE = dirname(fileURLToPath(import.meta.url))
let PROJECT_ROOT = resolve(MODULE_HERE, '..')
PROJECT_ROOT = findProjectRoot(PROJECT_ROOT)
if (!existsSync(join(PROJECT_ROOT, 'backend', 'main.py'))) {
  PROJECT_ROOT = findProjectRoot(process.cwd())
}

const backendStarter = createBackendStarter(PROJECT_ROOT)

const spawnBackendModule: NuxtModule = function (_inlineOptions, nuxt) {
  nuxt.hook('listen', async () => {
    await backendStarter.start()
  })
  nuxt.hook('close', () => {
    backendStarter.cleanup()
  })
}

export default defineNuxtConfig({
  modules: [
    '@nuxt/eslint',
    '@nuxtjs/tailwindcss',
    '@nuxtjs/i18n',
    '@pinia/nuxt',
    spawnBackendModule
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

  routeRules: {},

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
