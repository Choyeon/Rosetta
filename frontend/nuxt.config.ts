// https://nuxt.com/docs/api/configuration/nuxt-config
<<<<<<< Updated upstream
=======
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
    sock.on('timeout', () => { sock.destroy(); res(false) })
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
      try { watcher.close() } catch { /* ignore */ }
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

>>>>>>> Stashed changes
export default defineNuxtConfig({
  modules: [
    '@nuxt/eslint',
    '@nuxtjs/tailwindcss',
    '@nuxtjs/i18n',
<<<<<<< Updated upstream
    '@pinia/nuxt'
  ],

  alias: {
    '@': '.',
    '@@': '.'
  },

=======
    '@pinia/nuxt',
    spawnBackendModule
  ],

>>>>>>> Stashed changes
  devtools: {
    enabled: true
  },

<<<<<<< Updated upstream
  // css 路径: ~/assets = app/assets（已存在）
  css: ['~/assets/css/main.css'],

  runtimeConfig: {
    public: {
      apiBase: process.env.API_BASE_URL || 'http://localhost:8000/api'
    }
  },

  // 显式声明自动导入目录（相对路径相对于 rootDir = frontend/）
=======
  css: ['~/assets/css/main.css'],

  app: {
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
        { rel: 'preload', as: 'image', href: '/logo/rosetta-primary-icon.png' }
      ]
    }
  },

  runtimeConfig: {
    public: {
      apiBase: process.env.API_BASE_URL || '/api'
    }
  },

  nitro: {
    devProxy: {
      '/api': {
        target: `http://${BACKEND_HOST}:${BACKEND_PORT}/api`,
        changeOrigin: true
      }
    }
  },

>>>>>>> Stashed changes
  imports: {
    dirs: [
      './composables',
      './composables/**',
      './stores'
    ]
  },

<<<<<<< Updated upstream
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

=======
  components: [
    { path: './components', pathPrefix: false, ignore: ['**/index.ts'] }
  ],

>>>>>>> Stashed changes
  i18n: {
    locales: [
      { code: 'zh', name: '简体中文', file: 'zh.json' },
      { code: 'en', name: 'English', file: 'en.json' },
      { code: 'ja', name: '日本語', file: 'ja.json' },
      { code: 'zh_Hant', name: '繁體中文', file: 'zh_Hant.json' }
    ],
    defaultLocale: 'zh',
<<<<<<< Updated upstream
    // @nuxtjs/i18n v10 中 langDir/vueI18n 路径均相对 srcDir/i18n/ 目录（模块的 base 目录）
    // 因此 frontend/i18n/locales/ → './locales/' ; frontend/i18n/index.ts → './index.ts'
    langDir: './locales/',
=======
    langDir: './locales',
>>>>>>> Stashed changes
    vueI18n: './index.ts',
    strategy: 'no_prefix',
    detectBrowserLanguage: {
      useCookie: true,
<<<<<<< Updated upstream
      cookieKey: 'i18n_redirected',
=======
      cookieKey: 'rosetta_lang',
>>>>>>> Stashed changes
      redirectOn: 'root'
    }
  },

<<<<<<< Updated upstream
  // 全局关闭 SSR（纯 SPA），避免 Pinia store payload 序列化和 useFetch 服务端渲染问题
=======
>>>>>>> Stashed changes
  ssr: false,

  postcss: {
    plugins: {
      tailwindcss: {},
      autoprefixer: {}
    }
  },

<<<<<<< Updated upstream
  routeRules: {
  },
=======
  routeRules: {},
>>>>>>> Stashed changes

  compatibilityDate: '2026-06-30',

  eslint: {
    config: {
      stylistic: {
        commaDangle: 'never',
        braceStyle: '1tbs'
      }
    }
<<<<<<< Updated upstream
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
=======
>>>>>>> Stashed changes
  }
})
