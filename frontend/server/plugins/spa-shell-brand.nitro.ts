/**
 * Nitro 插件：给精准反选（ssr:false）的 SPA 壳页在服务端 HTML 里补品牌标题。
 *
 * 背景与名单口径见 `server/utils/spaShellBrand.ts`：这六条路径的空壳 HTML 里
 * `<title>` 来自 nuxt.config 的构建期常量，站点名与「SEO · 页面默认标题」都存在
 * 数据库里，构建期拿不到。这里在响应写回前按 `/settings/public` 的实际值改写一次。
 *
 * 失败策略 = 不改写（保留构建期占位）：后端不可用时宁可标题旧，也不能没有标题。
 * 标题源数据按 15s 进程内缓存（含失败结果）：TTL 刻意短于后端 /settings/public 的 300s
 * 窗口，而 PATCH 会立即清掉后端那份 —— 管理员保存设置后标签页标题一轮内就跟上；
 * 后端挂死时也不会每个壳请求都发一次往返。
 */
import type { NitroApp } from 'nitropack'
import type { H3Event } from 'h3'
import { buildShellTitle, isSpaShellPath, rewriteShellTitle } from '../utils/spaShellBrand'
import { pickBrandSubtitle } from '../../lib/utils'
import { resolveBackendEndpoint } from '../utils/ssr'

const BRAND_TTL_MS = 15_000
const BRAND_TIMEOUT_MS = 3_000

interface PublicGroupsResponse {
  groups?: Record<string, Record<string, unknown> | undefined>
}

let cachedTitle = ''
let cachedAt = 0
let inflight: Promise<string> | null = null

/** 读 basic.site_name + seo.default_title（留空回落 basic.subtitle），产出壳页标题。 */
async function fetchShellTitle(): Promise<string> {
  try {
    const url = resolveBackendEndpoint(useRuntimeConfig(), '/settings/public')
    const res = await $fetch<PublicGroupsResponse>(url, {
      headers: { accept: 'application/json' },
      timeout: BRAND_TIMEOUT_MS
    })
    const basic = res?.groups?.basic ?? {}
    const seo = res?.groups?.seo ?? {}
    const name = String(basic.site_name ?? '')
    return buildShellTitle(
      name,
      pickBrandSubtitle(name, String(seo.default_title ?? ''), String(basic.subtitle ?? ''))
    )
  } catch {
    // 后端不可用 / 缺 SSR baseURL 配置：留空让调用方原样返回构建期壳
    return ''
  }
}

async function loadShellTitle(): Promise<string> {
  if (cachedAt > 0 && Date.now() - cachedAt < BRAND_TTL_MS) return cachedTitle
  if (inflight) return inflight
  inflight = (async () => {
    const title = await fetchShellTitle()
    // 失败结果同样缓存，避免故障期每请求一次往返
    cachedTitle = title
    cachedAt = Date.now()
    inflight = null
    return title
  })()
  return inflight
}

/** 片段/正文里根本没有 `<title>` 时不动（异常壳、非 HTML）。 */
function needsTitle(html: string): boolean {
  return /<title(?:\s[^>]*)?>/i.test(html)
}

export default defineNitroPlugin((nitroApp: NitroApp) => {
  // 与 noindex-shell-meta / spa-serverrendered-zero 同族：两道钩子都挂，
  // 本插件的改写是幂等的（同一份 body 跑两次结果一致），双跑安全。
  type RenderHtmlHooks = {
    hook: (name: string, handler: (segments: unknown, event?: { path?: string }) => void | Promise<void>) => unknown
  }
  type BeforeResponseHooks = {
    hook: (name: string, handler: (event: H3Event, response: { body?: unknown, headers?: Record<string, unknown> }) => void | Promise<void>) => unknown
  }

  try {
    (nitroApp.hooks as unknown as RenderHtmlHooks).hook(
      'render:html',
      async (segments: unknown, event?: { path?: string }) => {
        if (!Array.isArray(segments)) return
        if (!isSpaShellPath(event?.path ?? '')) return
        const title = await loadShellTitle()
        if (!title) return
        for (let i = 0; i < segments.length; i++) {
          const seg = segments[i]
          if (typeof seg !== 'string' || !needsTitle(seg)) continue
          const next = rewriteShellTitle(seg, title)
          if (next !== seg) segments[i] = next
          return
        }
      }
    )
  } catch { /* 老版本 Nitro 缺钩子时静默，交给下面的兜底 */ }

  try {
    (nitroApp.hooks as unknown as BeforeResponseHooks).hook(
      'beforeResponse',
      async (event: H3Event, response: { body?: unknown, headers?: Record<string, unknown> }) => {
        const path = (event as unknown as { path?: string })?.path ?? ''
        if (!path || !isSpaShellPath(path)) return
        let body = response.body
        if (body instanceof Uint8Array || Buffer.isBuffer(body)) {
          try {
            body = Buffer.from(body as Buffer | Uint8Array).toString('utf8')
          } catch {
            return
          }
        }
        if (typeof body !== 'string' || !body.includes('<title')) return
        const ct = (response.headers?.['content-type'] as string | undefined) ?? ''
        if (ct && !/text\/html/.test(ct)) return
        const title = await loadShellTitle()
        if (!title) return
        const next = rewriteShellTitle(body, title)
        if (next === body) return
        const buf = Buffer.from(next, 'utf-8')
        response.body = buf
        if (response.headers) {
          response.headers['content-length'] = String(buf.byteLength)
          if (!ct) response.headers['content-type'] = 'text/html; charset=utf-8'
        }
      }
    )
  } catch { /* ignore hook unavailability */ }
})
