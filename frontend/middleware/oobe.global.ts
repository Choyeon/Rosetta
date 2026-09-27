/**
 * 全局 OOBE 中间件：
 * - 首次进入任意页面时调用后端 /api/oobe/status 检查安装状态
 * - 未安装：自动进入 /oobe 向导
 * - 已安装：禁止回到 /oobe（重定向首页）
 * - 缓存策略双端分离：SSR 端 per-request（useState，随 payload 水合供客户端
 *   首屏复用）；客户端进程内 60s（浏览器标签页视角，跨导航复用没问题）。
 */

// ===== 客户端（浏览器标签页）缓存：模块级变量在浏览器里天然按标签页隔离 =====
let cachedStatus: boolean | null = null
let cachedStatusAt = 0
let inFlight: Promise<boolean | null> | null = null
let lastFailAt = 0
// 客户端是否已拿到过明确判定（成功 fetch / SSR 水合种子 / resetOOBECache），
// 用于把「消费 SSR 水合值」限制为首屏一次性动作——安装完成后 payload 里的旧值
// 不得再覆盖 resetOOBECache(true) 的新状态。
let clientResolved = false
const CACHE_MS = 60_000 // 正常完成：60s 内完全信任缓存
const FAIL_STICKY_MS = 30_000 // 失败（未知态）：30s 内继续放行，不重复打后端
const STATUS_TIMEOUT_MS = 8_000
const SSR_STATE_KEY = 'oobe:status'
const STATIC_OR_API_RE = /^\/(?:favicon|api|media|_nuxt|_ipx|site\.webmanifest|logo|assets|apple-touch-icon)/

function shouldSkipRoute(path: string): boolean {
  if (STATIC_OR_API_RE.test(path)) return true
  if (path.endsWith('.png') || path.endsWith('.jpg') || path.endsWith('.jpeg')
    || path.endsWith('.svg') || path.endsWith('.ico') || path.endsWith('.webp')) return true
  return false
}

/**
 * 实际请求一次 /oobe/status。返回三态：
 *   · true  —— 后端明确回答"已安装"
 *   · false —— 后端明确回答"未安装"（此时才允许 302 到 /oobe）
 *   · null  —— **状态未知**（后端不可达 / 5xx / 超时 / 429 等一切失败）。
 *              调用方必须放行当前路由，绝不重定向：Nitro 的 routeRules SWR
 *              会按 URL（含 query）缓存 302 响应，一次因后端冷启动产生的
 *              "/?rosetta_theme_preview=xxx → /oobe" 会在缓存窗口内持续吐给
 *              后续访客，表现为「预览主题」落到向导页 / 页面不存在。
 *
 * 注意：中间件在初始导航期间执行，此时组件 setup 上下文不可用，
 * 不能调用 useOOBE()（内部依赖 useI18n/Pinia 等 setup 绑定的 composable），
 * 必须使用无上下文要求的 $fetch。
 *
 * SSR 端用 runtimeConfig.apiBase（绝对直连后端，不走 devProxy）；
 * 客户端用 runtimeConfig.public.apiBase（相对路径，经浏览器 devProxy / nginx 同源）。
 * 客户端**不接受**任何 localStorage 对 apiBase 的覆写——那是任意 API 重定向面；
 * 向导期的临时后端地址覆写只保留在 useOOBE() 请求内部使用。
 */
async function fetchOOBEStatus(): Promise<boolean | null> {
  try {
    const nuxtConf = useRuntimeConfig()
    let apiBase = import.meta.server
      ? ((nuxtConf as unknown as { apiBase?: string }).apiBase || '')
      : ((nuxtConf.public as unknown as { apiBase?: string }).apiBase || '')
    if (!String(apiBase).trim()) {
      // 生产 SSR 未配置后端：按未知处理直接放行。相对 '/api' 在 Nitro 进程内
      // 是自请求，行为依赖部署形态（nginx/代理中间件），不是可靠的探测路径。
      if (import.meta.server) return null
      apiBase = '/api'
    }
    const ctrl = new AbortController()
    const timer = setTimeout(() => ctrl.abort(), STATUS_TIMEOUT_MS)
    const res = await $fetch<{ success?: boolean, oobe_complete?: boolean }>('/oobe/status', {
      baseURL: apiBase,
      signal: ctrl.signal,
      timeout: STATUS_TIMEOUT_MS
    })
    clearTimeout(timer)
    return Boolean(res?.oobe_complete)
  } catch (e) {
    // —— 失败分类：一律按"未知"放行，不再把 429 判成"已安装"。
    // 429 只能说明后端活着，不能说明装完了：全新实例安装期被自己/CDN 限流时，
    // 误判 true 会把 /oobe 重定向回 /，恰好挡死安装入口。
    const status = (e as { status?: number })?.status ?? 0
    if (import.meta.dev) {
      console.warn(`[oobe.middleware] status fetch failed (status=${status}) → 状态未知，放行当前路由:`, e)
    }
    return null
  }
}

/**
 * 带缓存的 OOBE 完成状态读取（缓存策略见文件头注释：SSR per-request / 客户端 60s）。
 */
async function resolveOOBEComplete(): Promise<boolean | null> {
  // ===== SSR：per-request 缓存 =====
  // 模块级缓存会在 SSR 进程内跨请求共享：OOBE 状态刚变更（安装完成/异常回滚）时，
  // 最长 1 分钟仍把访客锁在 /oobe（或放行未安装实例）。useState 每个请求全新，
  // 且随 HTML payload 水合，客户端首屏直接复用该判定、不再重复请求。
  if (import.meta.server) {
    const state = useState<boolean | null | undefined>(SSR_STATE_KEY, () => undefined)
    if (state.value === undefined) state.value = await fetchOOBEStatus()
    return state.value
  }

  // ===== 客户端 =====
  const now = Date.now()
  // 首屏一次性消费 SSR 水合结果（之后以本标签页内的最新判定为准）
  if (!clientResolved) {
    const hydrated = useState<boolean | null | undefined>(SSR_STATE_KEY, () => undefined).value
    if (typeof hydrated === 'boolean') {
      clientResolved = true
      cachedStatus = hydrated
      cachedStatusAt = now
      return hydrated
    }
  }
  // 命中：成功缓存（60s）
  if (cachedStatus !== null && now - cachedStatusAt < CACHE_MS) return cachedStatus
  // 命中：失败 sticky（30s），未知态也不重复打后端，避免首页死循环请求
  if (cachedStatus === null && lastFailAt > 0 && now - lastFailAt < FAIL_STICKY_MS) return null

  if (inFlight) return inFlight
  inFlight = (async () => {
    try {
      const value = await fetchOOBEStatus()
      const settledAt = Date.now()
      if (value === null) {
        cachedStatus = null
        lastFailAt = settledAt
      } else {
        clientResolved = true
        cachedStatus = value
        cachedStatusAt = settledAt
        lastFailAt = 0
      }
      return value
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
  //
  // ⚠️ 2026-01-11 强化：即使命中当前 defineNuxtRouteMiddleware 之前有客户端导航
  // 队列（比如 Nuxt 4 SPA ssr:false 首屏 client hydration 先跳一次 /oobe 再被
  // 我们 SSR 中间件接管），这里一律用 302 HTTP 级重定向，彻底绕开客户端
  // "/oobe → navigateTo('/')" 死循环。
  if (import.meta.server) {
    try {
      const done = await resolveOOBEComplete()
      // 状态未知（后端不可达 / 超时 / 5xx）：放行当前路由。这里绝不 302——
      // Nitro 会把 302 也按 URL 缓存进 routeRules 的 SWR，后端恢复后仍继续
      // 把访客送到 /oobe，表现为「预览主题」等入口落到向导页 / 页面不存在。
      if (done === null) return
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
    // 未知态：客户端同样放行，不做任何重定向（与 SSR 分支一致）
    if (done === null) return
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
    // 抛异常 = 状态未知：放行当前路由，不进向导（向导由 SSR 302 / 用户手动访问触发）
    return
  }
})

/**
 * 客户端安装完成后即时翻转缓存（oobe.vue 安装成功时调用），
 * 避免 60s 缓存窗口内中间件仍认为"未安装"。
 */
export function resetOOBECache(nextValue: boolean | null = null) {
  cachedStatus = nextValue
  cachedStatusAt = Date.now()
  if (nextValue !== null) {
    clientResolved = true
    lastFailAt = 0
  }
}
