/**
 * 全局 OOBE 中间件：
 * - 首次进入任意页面时调用后端 /api/oobe/status 检查安装状态
 * - 未安装：自动进入 /oobe 向导
 * - 已安装：禁止回到 /oobe（重定向首页）
 * - 检查结果用进程内变量缓存，避免每次路由切换都请求后端
 */
let cachedStatus: boolean | null = null
let cachedStatusAt = 0
let inFlight: Promise<boolean> | null = null
let lastFailAt = 0
let lastFailSticky: boolean | null = null
const CACHE_MS = 60_000 // 正常完成：60s 内完全信任缓存
const FAIL_STICKY_MS = 30_000 // 失败/429：30s 内继续信任上次结果，不打爆限流
const STATIC_OR_API_RE = /^\/(?:favicon|api|media|_nuxt|_ipx|site\.webmanifest|logo|assets|apple-touch-icon)/
const OOBE_API_BASE_STORAGE_KEY = 'rosetta:oobe:apiBase'

function shouldSkipRoute(path: string): boolean {
  if (STATIC_OR_API_RE.test(path)) return true
  if (path.endsWith('.png') || path.endsWith('.jpg') || path.endsWith('.jpeg')
    || path.endsWith('.svg') || path.endsWith('.ico') || path.endsWith('.webp')) return true
  return false
}

/**
 * 获取 oobe 完成状态（带缓存和并发合并）。
 * 注意：中间件在初始导航期间执行，此时组件 setup 上下文不可用，
 * 不能调用 useOOBE()（内部依赖 useI18n/Pinia 等 setup 绑定的 composable），
 * 必须使用无上下文要求的 $fetch。
 *
 * SSR 端用 runtimeConfig.apiBase（绝对直连后端，不走 devProxy）；
 * 客户端用 runtimeConfig.public.apiBase（相对路径，经浏览器 devProxy / nginx 同源）。
 */
async function resolveOOBEComplete(): Promise<boolean> {
  const now = Date.now()

  // 命中：客户端成功缓存（60s）
  if (cachedStatus !== null && now - cachedStatusAt < CACHE_MS) return cachedStatus
  // 命中：客户端 sticky 失败（30s），不重复打爆后端 429 限流
  if (cachedStatus === null && lastFailSticky !== null && now - lastFailAt < FAIL_STICKY_MS) {
    return lastFailSticky
  }

  if (inFlight) return inFlight
  inFlight = (async () => {
    try {
      // ====== SSR/客户端 双端单源 baseURL ======
      const nuxtConf = useRuntimeConfig()
      let apiBase = import.meta.server
        ? ((nuxtConf as unknown as { apiBase?: string }).apiBase || '')
        : ((nuxtConf.public as unknown as { apiBase?: string }).apiBase || '')
      if (!String(apiBase).trim()) {
        apiBase = (import.meta.server && process.env.NODE_ENV !== 'production')
          ? 'http://127.0.0.1:8000/api'
          : '/api'
      }

      if (import.meta.client && typeof localStorage !== 'undefined') {
        try {
          const raw = localStorage.getItem(OOBE_API_BASE_STORAGE_KEY)
          if (raw) {
            const parsed = JSON.parse(raw)
            if (typeof parsed === 'string' && parsed.trim()) {
              apiBase = parsed.trim()
            }
          }
        } catch { /* ignore */ }
      }
      const ctrl = new AbortController()
      const timer = setTimeout(() => ctrl.abort(), 8000)
      const res = await $fetch<{ success?: boolean, oobe_complete?: boolean }>('/oobe/status', {
        baseURL: apiBase,
        signal: ctrl.signal,
        timeout: 8000
      })
      clearTimeout(timer)
      const complete = Boolean(res?.oobe_complete)
      cachedStatus = complete
      cachedStatusAt = now
      lastFailSticky = complete
      lastFailAt = now
      return complete
    } catch (e) {
      const status = (e as { status?: number })?.status ?? 0
      // —— 失败分类兜底（Sticky）：
      //   429/5xx/网络不可达：30s 内不再重复调用，避免首页死循环打满 300+ 条红 error。
      //   429 视为后端健康 → 已安装；其余失败保守 false（下次再试仍会等 30s sticky）。
      const sticky = status === 429
        ? true
        : (status >= 500 || status === 0 || status === 502 || status === 503 || status === 504 ? false : null)
      if (sticky !== null) {
        lastFailSticky = sticky
        lastFailAt = now
        cachedStatus = null
        return sticky
      }
      if (import.meta.dev) console.warn('[oobe.middleware] status fetch failed:', e)
      cachedStatus = null
      lastFailSticky = null
      lastFailAt = now
      return false
    } finally {
      inFlight = null
    }
  })()
  return inFlight
}

export default defineNuxtRouteMiddleware(async (to) => {
  const path = to.path

  if (shouldSkipRoute(path)) return

  const isOOBEPage = path === '/oobe' || path.startsWith('/oobe/')

  // ===== SSR 分支：首字节决定是否 302 重定向，避免"先吐 SPA 壳再在客户端跳"的白屏 =====
  // 服务端每次渲染全新 HTML，module-level cachedStatus 跨请求复用没问题（OOBE 是一次性状态）。
  // 关键：SSR 环境下没有 localStorage，跳过 rosetta:oobe:apiBase 手动覆写。
  //
  // ⚠️ 2026-01-11 强化：即使命中当前 defineNuxtRouteMiddleware 之前有客户端导航
  // 队列（比如 Nuxt 4 SPA ssr:false 首屏 client hydration 先跳一次 /oobe 再被
  // 我们 SSR 中间件接管），这里一律用 302 HTTP 级重定向，彻底绕开客户端
  // "/oobe → navigateTo('/')" 死循环。
  if (import.meta.server) {
    try {
      const done = await resolveOOBEComplete()
      if (done) {
        if (isOOBEPage) return navigateTo('/', { replace: true, redirectCode: 302 })
        return
      }
      if (!isOOBEPage) return navigateTo('/oobe', { replace: true, redirectCode: 302 })
    } catch {
      // 后端不可达：保守起见仍允许公开页 SSR 渲染（避免一挂就全跳 OOBE 死循环）。
      if (!isOOBEPage) return
    }
    return
  }

  // ===== Client 分支：信任 SSR 先做过 302，这里仅在 SPA 软切命中 /oobe 时兜底，
  // 防止 SSR 未覆盖（纯客户端 navigateTo('/oobe') 时）走到 oobe 页面。
  // 加并发合并锁（window 级 __ros_oobe_reroute_lock__）：_doClearErrorOnce 的
  // clearError{redirect} 与 oobe middleware 若同 tick 触发，会把 Nuxt Router
  // 置成"pending nav 永不 resolve"，Playwright evaluate 永久 pending → 白屏。
  if (!import.meta.client) return

  const client = globalThis as typeof globalThis & {
    __ros_oobe_reroute_lock__?: boolean
    __ros_oobe_reroute_done__?: boolean
  }
  if (client.__ros_oobe_reroute_done__) return
  try {
    const done = await resolveOOBEComplete()
    if (done) {
      if (isOOBEPage) {
        // /oobe 已安装：不用 navigateTo（会被 pending nav 锁死 in-flight），
        // 直接原生级 replace 避免死锁。
        client.__ros_oobe_reroute_lock__ = true
        client.__ros_oobe_reroute_done__ = true
        return navigateTo('/', { replace: true, external: false })
      }
      return
    }
    if (!isOOBEPage) {
      return navigateTo('/oobe', { replace: true })
    }
  } catch {
    if (!isOOBEPage) {
      return navigateTo('/oobe', { replace: true })
    }
  }
})

export function resetOOBECache(nextValue: boolean | null = null) {
  cachedStatus = nextValue
}
