/**
 * Nitro server plugin：把 SSR HTML 响应的 `Cache-Control` 补回
 * `public, max-age=0, s-maxage=<T>, stale-while-revalidate=<T2>`。
 *
 * 背景与判定见 `server/utils/ssrHtmlCacheControl.ts`：routeRules 里已经写了这条口径，
 * 但 Nitro 的 swr 缓存处理器在响应阶段整条覆写成只有 `s-maxage=…`，
 * 浏览器因此按启发式新鲜期复用旧 HTML —— 后台改完站点设置、Nitro 页面缓存已清，
 * 回访访客看到的仍是烘进旧 payload 的设置（`useSite` 客户端见 `loaded=true` 不再重取）。
 *
 * ⚠️ 头部不只存在一个地方：swr 那条截断值走的是 Node `ServerResponse`
 * （线上实测回的是小写 `cache-control`，即 `res.setHeader` 的产物），
 * h3 自己的 outHeaders 与钩子 payload 里的 `headers` 是另外的袋。
 * 所以这里对"能看到的每一个头存放处"都过一遍归一，
 * 归一函数幂等，已补好的字符串会返回 null 直接跳过。
 *
 * 两道钩子：`render:response` 覆盖真实渲染，`beforeResponse` 覆盖 swr 缓存复用
 * 与发送前的最后一步。
 */
import type { NitroApp } from 'nitropack'
import {
  errorHtmlCacheControl,
  normalizeHtmlCacheControl
} from '../utils/ssrHtmlCacheControl'

type Accessor = {
  get: (name: string) => string | null
  set: (name: string, value: string) => void
  getStatus?: () => number | null
}

type NitroHookShape = {
  hook: (name: string, handler: (a: unknown, b?: unknown) => void | Promise<void>) => unknown
}

function asString(raw: unknown): string | null {
  if (typeof raw === 'string') return raw
  if (Array.isArray(raw)) return String(raw[0] ?? '')
  return null
}

/** 普通对象形态的 headers 袋（键大小写不定）。 */
function bagAccessor(headers: unknown): Accessor | null {
  if (!headers || typeof headers !== 'object') return null
  if ('get' in headers && 'set' in headers) return null
  const bag = headers as Record<string, unknown>
  const findKey = (name: string): string | undefined =>
    Object.keys(bag).find(key => key.toLowerCase() === name)
  return {
    get: name => asString(bag[findKey(name) ?? ''] ?? null),
    set: (name, value) => {
      bag[findKey(name) ?? name] = value
    }
  }
}

/** Headers 实例形态（有 get/set 方法）。 */
function fetchHeadersAccessor(headers: unknown): Accessor | null {
  const h = headers as { get?: (n: string) => unknown, set?: (n: string, v: string) => unknown }
  if (!h || typeof h.get !== 'function' || typeof h.set !== 'function') return null
  return {
    get: name => asString(h.get?.(name)),
    set: (name, value) => h.set?.(name, value)
  }
}

/** Node ServerResponse 形态（swr 覆写后真正上线的那一份）。 */
function resAccessor(res: unknown): Accessor | null {
  const r = res as { getHeader?: (n: string) => unknown, setHeader?: (n: string, v: string) => unknown, getStatusCode?: () => number }
  if (!r || typeof r.getHeader !== 'function' || typeof r.setHeader !== 'function') return null
  return {
    get: name => asString(r.getHeader?.(name)),
    set: (name, value) => {
      try {
        r.setHeader?.(name, value)
      } catch { /* 头部已发出，改不动就算了 */ }
    },
    getStatus: typeof r.getStatusCode === 'function' ? () => r.getStatusCode?.() ?? null : undefined
  }
}

/**
 * 错误状态（≥400）的兜底探测：render:response 的 payload 带 status，
 * beforeResponse 时 h3 的 event.res.statusCode 已定案（useContentStatus 闸门
 * 在 app:rendered 里 setResponseStatus 之后才轮到这里）。
 */
function statusFrom(event: unknown, response?: unknown): number | null {
  const r = (response as { status?: number } | undefined)?.status
  if (typeof r === 'number') return r
  const evt = event as {
    res?: { statusCode?: number }
    node?: { res?: { statusCode?: number } }
    context?: { res?: { statusCode?: number } }
  } | undefined
  return evt?.res?.statusCode ?? evt?.node?.res?.statusCode ?? evt?.context?.res?.statusCode ?? null
}

/** 只动 text/html；其余（JSON / 静态资源 / no-store 页）一律不碰。 */
function normalizeVia(accessor: Accessor, status: number | null = null): void {
  const ct = accessor.get('content-type') ?? ''
  if (!ct.includes('text/html')) return
  const errored = errorHtmlCacheControl(
    status ?? accessor.getStatus?.() ?? null,
    accessor.get('cache-control'),
    ct
  )
  if (errored) {
    accessor.set('cache-control', errored)
    return
  }
  const fixed = normalizeHtmlCacheControl(accessor.get('cache-control'))
  if (fixed) accessor.set('cache-control', fixed)
}

function accessorsFor(event: unknown, response?: unknown): Accessor[] {
  const evt = event as {
    node?: { res?: unknown }
    res?: unknown
    headers?: unknown
    context?: { res?: unknown, outHeaders?: unknown }
  } | undefined
  const bags: unknown[] = [
    (response as { headers?: unknown } | undefined)?.headers,
    evt?.headers,
    // h3 v1 的 outHeaders 在 flush 到 res 之前才是真源，晚于本钩子写入会盖掉 res 的修改
    evt?.context?.outHeaders
  ]
  const found: Accessor[] = [
    resAccessor(evt?.node?.res),
    resAccessor(evt?.res),
    resAccessor(evt?.context?.res)
  ].filter((a): a is Accessor => a !== null)
  for (const bag of bags) {
    const accessor = bagAccessor(bag) ?? fetchHeadersAccessor(bag)
    if (accessor) found.push(accessor)
  }
  return found
}

export default defineNitroPlugin((nitroApp: NitroApp) => {
  const hooks = nitroApp.hooks as unknown as NitroHookShape

  // render:response —— Nuxt SSR 真实渲染完成时（缓存复用不触发这一道）。
  try {
    hooks.hook('render:response', (response: unknown, event?: unknown) => {
      const status = statusFrom(event, response)
      for (const accessor of accessorsFor(event, response)) normalizeVia(accessor, status)
    })
  } catch { /* 老版本 Nitro 缺该钩子：beforeResponse 仍然生效 */ }

  // beforeResponse —— 每个响应写回 client 前的最后一步，覆盖 swr 缓存复用。
  try {
    hooks.hook('beforeResponse', (event: unknown, response?: unknown) => {
      const status = statusFrom(event, response)
      for (const accessor of accessorsFor(event, response)) normalizeVia(accessor, status)
    })
  } catch { /* ignore hook unavailability */ }
})
