/**
 * Nitro server plugin：把 ssr:false 精准反选路径的 `window.__NUXT_DATA__` payload 中
 * `serverRendered: 1` 强制写 0，避免 Nuxt 4 客户端在"空壳 HTML + serverRendered:1"
 * 的组合下走 hydrate 分支，触发 runtime-core setRef 的 NPE → NUXT_E1005 → 500 壳。
 *
 * 实现：
 *  挂 Nitro 的 'request'/'response' 流，在响应 body 真正被写回 client 前拦截；
 *  若 path ∈ /login|/register|/oobe|/search|/admin|前缀 + Content-Type 包含 text/html，
 *  就把 body 串正则替换首处的 "serverRendered":1 → 0。
 *
 * 之所以用流式拦截：Nuxt 4.5 + Nitro preset node-server 的最终响应 body 是字符串，
 * 无论有没有 render:html 钩子都能命中；是"所有路径的最终兜底"。
 */
import type { NitroApp } from 'nitropack'
import type { H3Event } from 'h3'

// 2026-01-11：/oobe 改为 SSR（ssr:true + swr:false）后从这里移除，避免 Nitro
// 错误把 SSR 页面的 serverRendered 改成 0。剩下 login/register/search/admin 是
// 精准反选的 ssr:false 路径，它们仍需要这个补丁。
const SPA_PREFIXES: ReadonlyArray<string> = [
  '/login',
  '/register',
  '/search',
  '/admin'
] as const

function isSpa(p: string): boolean {
  for (const prefix of SPA_PREFIXES) {
    if (p === prefix) return true
    if (p.startsWith(prefix + '/')) return true
  }
  return false
}

/** 只在 <script id="__NUXT_DATA__"> 段内把首个 "serverRendered": 1 → 0 */
function patchBody(bodyStr: string): string {
  if (!bodyStr.includes('id="__NUXT_DATA__"')) return bodyStr
  if (!bodyStr.includes('serverRendered')) return bodyStr
  return bodyStr.replace(
    /(<script[^>]*id="__NUXT_DATA__"[^>]*>)([\s\S]*?)(<\/script>)/gi,
    (_m, open, content, close) => {
      const c = String(content)
      if (!c.includes('serverRendered')) return open + c + close
      // 替换：首个数组元素里 "serverRendered":1/ "serverRendered": 1 / \"serverRendered\":1 三态
      const c2 = c.replace(
        /(\\"serverRendered\\"|"serverRendered")\s*:\s*1(?=\s*[,\]}])/,
        (_mm, key) => `${key}:0`
      )
      return open + c2 + close
    }
  )
}

export default defineNitroPlugin((nitroApp: NitroApp) => {
  // —— Nuxt 在 Nitro 侧导出的渲染钩子：render:html 改 html 数组片段。
  //    Nuxt 4 SSR / ssr:false 共用此钩子，是最干净的切入点。——
  type NitroHookShape = {
    hook: (name: string, handler: (segments: unknown) => void | Promise<void>) => unknown
  }
  const nitroHooks = nitroApp.hooks as NitroHookShape
  try {
    nitroHooks.hook('render:html', (htmlSegments: unknown) => {
      if (!Array.isArray(htmlSegments)) return
      for (let i = 0; i < htmlSegments.length; i++) {
        const seg = htmlSegments[i]
        if (typeof seg !== 'string') continue
        if (!seg.includes('id="__NUXT_DATA__"')) continue
        const before = seg
        const after = patchBody(seg)
        if (before !== after) htmlSegments[i] = after
      }
    })
  } catch { /* ignore old Nitro 版本缺钩子 */ }

  // —— H3/Nitro 响应层兜底：若 render:html 因 routeRules ssr:false 不触发，
  //    直接在 afterResponse 前的 body 字符串上再做一次补丁。
  //    beforeResponse 钩子运行时类型与打包后 Nitro 类型声明偶发交叉不一致，
  //    运行时存在即可，这里绕开 strict TS 校验。——
  try {
    type NitroHookShape2 = {
      hook: (name: string, handler: (event: H3Event, response: { body?: unknown, headers?: Record<string, unknown> }) => void | Promise<void>) => unknown
    }
    const hooks = nitroApp.hooks as NitroHookShape2
    hooks.hook(
      'beforeResponse',
      (event: H3Event, response: { body?: unknown, headers?: Record<string, unknown> }) => {
        // event.path 在 H3 v2 为 getRequestPath(event)；兼容新旧写法
        let path = ''
        try {
          const evt = event as unknown as { path?: string }
          path = evt?.path ?? ''
        } catch {
          /* ignore */
        }
        if (!path) {
          try {
            // @ts-expect-error globalThis 上的 h3 util 可能不存在，optional chain 兜底
            path = (globalThis.getRequestPath?.(event) as string) ?? ''
          } catch {
            /* ignore */
          }
        }
        if (!path) return
        if (!isSpa(path)) return

        let body = response.body
        if (body instanceof Uint8Array || Buffer.isBuffer(body)) {
          try {
            body = Buffer.from(body as Buffer | Uint8Array).toString('utf8')
          } catch {
            return
          }
        }
        if (typeof body !== 'string') return
        if (!body.includes('serverRendered')) return
        const ct = (response.headers?.['content-type'] as string | undefined) ?? ''
        if (ct && !/text\/html/.test(ct)) return
        const beforeLen = body.length
        const after = patchBody(body)
        if (after === body) return
        response.body = after
        if (response.headers) {
          response.headers['content-length'] = String(Buffer.byteLength(after, 'utf-8'))
          if (!ct) response.headers['content-type'] = 'text/html; charset=utf-8'
        }
        void beforeLen
      }
    )
  } catch { /* ignore hook unavailability */ }
})
