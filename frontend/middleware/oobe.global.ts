/**
 * 全局 OOBE 中间件：
 * - 首次进入任意页面时调用后端 /api/oobe/status 检查安装状态
 * - 未安装：自动进入 /oobe 向导
 * - 已安装：禁止回到 /oobe（重定向首页）
 * - 检查结果用进程内变量缓存，避免每次路由切换都请求后端
 */
import { useOOBE } from '~~/composables/useOOBE'

let cachedStatus: boolean | null = null
let inFlight: Promise<boolean> | null = null
const STATIC_OR_API_RE = /^\/(?:favicon|api|media|_nuxt|_ipx|site\.webmanifest|logo|assets|apple-touch-icon)/

function shouldSkipRoute(path: string): boolean {
  if (STATIC_OR_API_RE.test(path)) return true
  if (path.endsWith('.png') || path.endsWith('.jpg') || path.endsWith('.jpeg') ||
      path.endsWith('.svg') || path.endsWith('.ico') || path.endsWith('.webp')) return true
  return false
}

/**
 * 获取 oobe 完成状态（带缓存和并发合并）
 */
async function resolveOOBEComplete(): Promise<boolean> {
  if (cachedStatus !== null) return cachedStatus
  if (inFlight) return inFlight
  inFlight = (async () => {
    try {
      const { getOOBEStatus } = useOOBE()
      const { data, error } = await getOOBEStatus()
      if (error.value) {
        cachedStatus = false
        return false
      }
      const complete = Boolean((data.value as { oobe_complete?: boolean })?.oobe_complete)
      cachedStatus = complete
      return complete
    } catch {
      cachedStatus = false
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
