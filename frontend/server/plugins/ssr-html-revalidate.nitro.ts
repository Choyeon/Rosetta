/**
 * Nitro server plugin：把 SSR HTML 响应的 `Cache-Control` 补回
 * `public, max-age=0, s-maxage=<T>, stale-while-revalidate=<T2>`。
 *
 * 背景与判定见 `server/utils/ssrHtmlCacheControl.ts`：routeRules 里已经写了这条口径，
 * 但 Nitro 的 swr 缓存处理器在响应阶段整条覆写成只有 `s-maxage=…`，
 * 浏览器因此按启发式新鲜期复用旧 HTML —— 后台改完站点设置、Nitro 页面缓存已清，
 * 回访访客看到的仍是烘进旧 payload 的设置（`useSite` 客户端见 `loaded=true` 不再重取）。
 *
 * 两道钩子（`render:response` 覆盖真实渲染、`beforeResponse` 覆盖缓存复用与发送前最后一步），
 * 归一函数幂等：第二次拿到已合规的字符串会返回 null 直接跳过。
 */
import type { NitroApp } from 'nitropack'
import { normalizeHtmlCacheControl } from '../utils/ssrHtmlCacheControl'

type HeaderBag = Record<string, unknown> | undefined

type NitroHookShape = {
  hook: (name: string, handler: (a: unknown, b?: unknown) => void | Promise<void>) => unknown
}

function headerOf(headers: HeaderBag, name: string): string | null {
  if (!headers || typeof headers !== 'object') return null
  for (const key of Object.keys(headers)) {
    if (key.toLowerCase() !== name) continue
    const v = headers[key]
    if (typeof v === 'string') return v
    if (Array.isArray(v)) return String(v[0] ?? '')
  }
  return null
}

function setHeader(headers: HeaderBag, name: string, value: string): void {
  if (!headers || typeof headers !== 'object') return
  for (const key of Object.keys(headers)) {
    if (key.toLowerCase() === name) {
      headers[key] = value
      return
    }
  }
  headers[name] = value
}

/** 只动 text/html；其余（JSON / 静态资源 / no-store 页）一律不碰。 */
function normalizeHeaders(headers: HeaderBag): void {
  const ct = headerOf(headers, 'content-type') ?? ''
  if (!ct.includes('text/html')) return
  const fixed = normalizeHtmlCacheControl(headerOf(headers, 'cache-control'))
  if (fixed) setHeader(headers, 'cache-control', fixed)
}

function headersFrom(primary?: unknown, fallback?: unknown): HeaderBag {
  for (const candidate of [primary, fallback]) {
    const headers = (candidate as { headers?: HeaderBag } | undefined)?.headers
    if (headers) return headers
  }
  return undefined
}

export default defineNitroPlugin((nitroApp: NitroApp) => {
  const hooks = nitroApp.hooks as unknown as NitroHookShape

  // render:response —— Nuxt SSR 真实渲染完成时（缓存复用不触发这一道）。
  try {
    hooks.hook('render:response', (response: unknown) => {
      normalizeHeaders(headersFrom(response))
    })
  } catch { /* 老版本 Nitro 缺该钩子：beforeResponse 仍然生效 */ }

  // beforeResponse —— 每个响应写回 client 前的最后一步，覆盖 swr 缓存复用。
  try {
    hooks.hook('beforeResponse', (event: unknown, response?: unknown) => {
      normalizeHeaders(headersFrom(response, event))
    })
  } catch { /* ignore hook unavailability */ }
})
