/**
 * 全局 OOBE 中间件：
 * - 首次进入任意页面时调用后端 /api/oobe/status 检查安装状态
 * - 未安装：自动进入 /oobe 向导
 * - 已安装：禁止回到 /oobe（重定向首页）
 * - 检查结果用进程内变量缓存，避免每次路由切换都请求后端
 */
let cachedStatus: boolean | null = null
let inFlight: Promise<boolean> | null = null
const STATIC_OR_API_RE = /^\/(?:favicon|api|media|_nuxt|_ipx|site\.webmanifest|logo|assets|apple-touch-icon)/

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
 */
async function resolveOOBEComplete(): Promise<boolean> {
  if (cachedStatus !== null) return cachedStatus
  if (inFlight) return inFlight
  inFlight = (async () => {
    try {
      const apiBase = useRuntimeConfig().public.apiBase as string
      // 带超时 + AbortController 兜底：devProxy/后端不可用时不要把导航卡死（空白页）
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
      return complete
    } catch (e) {
      // 后端不可达/异常：本次视为未完成，但不落缓存，
      // 避免后端恢复后仍被锁死在 /oobe（下次路由切换会重试）
      if (import.meta.dev) console.warn('[oobe.middleware] status fetch failed:', e)
      cachedStatus = null
      return false
    } finally {
      inFlight = null
    }
  })()
  return inFlight
}

export default defineNuxtRouteMiddleware(async (to) => {
  if (!import.meta.client) return

  const path = to.path

  if (shouldSkipRoute(path)) return

  const isOOBEPage = path === '/oobe' || path.startsWith('/oobe/')

  try {
    const done = await resolveOOBEComplete()
    if (done) {
      if (isOOBEPage) {
        return navigateTo('/', { replace: true })
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
