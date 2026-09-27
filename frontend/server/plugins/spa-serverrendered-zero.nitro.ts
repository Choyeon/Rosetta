/**
 * Nitro server plugin：确保 ssr:false 精准反选路径的 `__NUXT_DATA__` payload 中
 * `serverRendered` 反序列化后是布尔 false，避免 Nuxt 4 客户端在"空壳 HTML +
 * serverRendered 真值"的组合下走 hydrate 分支，触发 runtime-core setRef 的 NPE
 * → NUXT_E1005 → 500 壳。
 *
 * ⚠️ 2026-09-27 修复：payload 是 devalue「扁平数组」格式——对象属性里的整数
 * 不是字面量，而是**数组下标引用**（`serverRendered:7` 表示真值在 d[7]）。
 * 旧实现用正则把 `:1` 改成字面 `:0`，本意"写 false"，实际把引用指回了下标 0
 * 的根对象本身 → 客户端 revive 出循环真值对象 → auth store 误判仍在 hydrate、
 * 等 app:mounted，而 admin.global 中间件 await initialize() 阻塞挂载 →
 * **未登录冷访问 /admin 永久白屏死锁**（iframe 对照实验：/login 5s 挂载，
 * /admin 50s 空壳）。正确做法：解析 payload 数组，让 serverRendered 指向
 * 数组里真实存在的布尔 false 元素（没有就 push 一个，不影响既有下标）。
 *
 * 实现：
 *  挂 Nitro 的 'render:html' / 'beforeResponse' 两道钩子，在响应写回 client 前
 *  拦截 body；若 path ∈ /login|/register|/search|/admin 前缀 + text/html，
 *  就对 <script id="__NUXT_DATA__"> 段做上述语义修正。
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

/**
 * 语义修正：把 payload 根对象的 serverRendered 引用指向布尔 false。
 * 输入是 <script id="__NUXT_DATA__"> 内的 JSON 文本；已为 false / 解析失败
 * 一律原样返回（幂等，可安全地被 render:html 与 beforeResponse 双跑）。
 */
export function fixServerRendered(payloadJson: string): string {
  let d: unknown
  try {
    d = JSON.parse(payloadJson)
  } catch {
    return payloadJson
  }
  if (!Array.isArray(d) || d.length === 0) return payloadJson
  const root = d[0]
  if (!root || typeof root !== 'object' || !('serverRendered' in root)) return payloadJson
  const holder = root as { serverRendered: unknown }
  const resolved = typeof holder.serverRendered === 'number'
    ? d[holder.serverRendered]
    : holder.serverRendered
  if (resolved === false) return payloadJson
  if (resolved !== true) return payloadJson
  let falseIdx = d.findIndex(x => x === false)
  if (falseIdx < 0) falseIdx = d.push(false) - 1
  holder.serverRendered = falseIdx
  return JSON.stringify(d)
}

/** 只在 <script id="__NUXT_DATA__"> 段内应用 fixServerRendered */
function patchBody(bodyStr: string): string {
  if (!bodyStr.includes('id="__NUXT_DATA__"')) return bodyStr
  if (!bodyStr.includes('serverRendered')) return bodyStr
  return bodyStr.replace(
    /(<script[^>]*id="__NUXT_DATA__"[^>]*>)([\s\S]*?)(<\/script>)/gi,
    (_m, open, content, close) => open + fixServerRendered(String(content)) + close
  )
}

export default defineNitroPlugin((nitroApp: NitroApp) => {
  // —— Nuxt 在 Nitro 侧导出的渲染钩子：render:html 改 html 数组片段。
  //    Nuxt 4 SSR / ssr:false 共用此钩子，是最干净的切入点。
  //    ⚠️ 必须按 isSpa(event.path) 过滤：SSR 页（如 /oobe）的 serverRendered
  //    合法为 true，若无差别改写会把真页面骗成 CSR 分支、丢掉 hydrate。——
  type NitroHookShape = {
    hook: (name: string, handler: (segments: unknown, event?: { path?: string }) => void | Promise<void>) => unknown
  }
  const nitroHooks = nitroApp.hooks as NitroHookShape
  try {
    nitroHooks.hook('render:html', (htmlSegments: unknown, event?: { path?: string }) => {
      if (!Array.isArray(htmlSegments)) return
      if (!isSpa(event?.path ?? '')) return
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
