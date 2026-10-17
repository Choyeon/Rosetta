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
import type { H3Event } from 'h3'
import { normalizeHtmlCacheControl } from '../utils/ssrHtmlCacheControl'

function headerOf(headers: unknown, name: string): string | null {
  if (!headers || typeof headers !== 'object') return null
  const bag = headers as Record<string, unknown>
  for (const key of Object.keys(bag)) {
    if (key.toLowerCase() !== name) continue
    const v = bag[key]
    if (typeof v === 'string') return v
    if (Array.isArray(v)) return String(v[0] ?? '')
  }
  return null
}

function setHeader(headers: unknown, name: string, value: string): void {
  if (!headers || typeof headers !== 'object') return
  const bag = headers as Record<string, unknown>
  for (const key of Object.keys(bag)) {
    if (key.toLowerCase() === name) {
      bag[key] = value
      return
    }
  }
  bag[name] = value
}

/** 只动 text/html；其余（JSON / 静态资源 / no-store 页）原样返回 false。 */
function isHtmlResponse(headers: unknown): boolean {
  const ct = headerOf(headers, 'content-type') ?? ''
  return ct.includes('text/html')
}

function apply(event: H3Event | undefined, headers: unknown): void {
  if (!isHtmlResponse(headers)) return
  const fixed = normalizeHtmlCacheControl(headerOf(headers, 'cache-control'))
  if (!fixed) return
  setHeader(headers, 'cache-control', fixed)
}

export default defineNitroPlugin((nitroApp: NitroApp) => {
  type HeaderCarrier = { headers?: unknown }

  try {
    nitroApp.hooks.hook('render:response' as never, (response: HeaderCarrier, ctx: { event?: H3Event }) => {
      apply(ctx?.event, response?.headers)
    })
  } catch { /* 老版本 Nitro 缺该钩子：beforeResponse 仍然生效 */ }

  try {
    nitroApp.hooks.hook('beforeResponse' as never, (event: H3Event, response: HeaderCarrier) => {
      apply(event, response?.headers ?? (event as unknown as HeaderCarrier)?.headers)
    })
  } catch { /* ignore hook unavailability */ }
})
