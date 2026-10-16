/**
 * Nitro 插件：给精准反选（ssr:false）的不可索引页在**服务端 HTML** 里补
 * `<meta name="robots" content="noindex, follow">`。
 *
 * 背景见 `server/utils/noindex-shell.ts` 的注释：这些页面的 noindex 原本只在
 * hydration 之后才出现，而 robots.txt 已经放弃 Disallow、把担子全压在页面 meta 上。
 *
 * 幂等：两道钩子（render:html / beforeResponse）都先检测 `name="robots"` 是否存在，
 * 已存在就原样返回 —— 所以 SSR 页（/settings、/oobe 由 useSeo 输出）不会被注入第二条，
 * 同一份 body 被跑两次也不会重复。
 */
import type { NitroApp } from 'nitropack'
import type { H3Event } from 'h3'
import { needsNoindexShell } from '../utils/noindex-shell'

const ROBOTS_META = '<meta name="robots" content="noindex, follow">'

/** head 里已经有 robots 指令 → 什么都不做 */
function hasRobots(html: string): boolean {
  return html.includes('name="robots"') || html.includes('name=\'robots\'')
}

/** 在 `<head …>` 开标签后插入 meta；找不到开标签（异常壳）返回 null */
function injectIntoHead(html: string): string | null {
  if (hasRobots(html)) return null
  const m = /<head(?:\s[^>]*)?>/i.exec(html)
  if (!m) return null
  return `${html.slice(0, m.index + m[0].length)}${ROBOTS_META}${html.slice(m.index + m[0].length)}`
}

export default defineNitroPlugin((nitroApp: NitroApp) => {
  // 与 spa-serverrendered-zero.nitro.ts 同族：Nitro 的钩子签名在这个版本对
  // render:html / beforeResponse 的入参声明并不统一，按钩子各自声明局部形状，
  // 运行时缺钩子一律 try/catch 兜住（老版本只是少一道保险，不会崩）。
  type RenderHtmlHooks = {
    hook: (name: string, handler: (segments: unknown, event?: { path?: string }) => void | Promise<void>) => unknown
  }
  type BeforeResponseHooks = {
    hook: (name: string, handler: (event: H3Event, response: { body?: unknown, headers?: Record<string, unknown> }) => void | Promise<void>) => unknown
  }

  try {
    (nitroApp.hooks as unknown as RenderHtmlHooks).hook('render:html', (segments: unknown, event?: { path?: string }) => {
      if (!Array.isArray(segments)) return
      if (!needsNoindexShell(event?.path ?? '')) return
      // 任意片段已带 robots（SSR 页的 useHead 输出）→ 整页跳过
      if (segments.some(seg => typeof seg === 'string' && hasRobots(seg))) return
      for (let i = 0; i < segments.length; i++) {
        const seg = segments[i]
        if (typeof seg !== 'string') continue
        const next = injectIntoHead(seg)
        if (next === null) continue
        segments[i] = next
        return
      }
    })
  } catch { /* 老版本 Nitro 缺钩子时静默，交给下面的兜底 */ }

  try {
    (nitroApp.hooks as unknown as BeforeResponseHooks).hook(
      'beforeResponse',
      (event: H3Event, response: { body?: unknown, headers?: Record<string, unknown> }) => {
        const path = (event as unknown as { path?: string })?.path ?? ''
        if (!path || !needsNoindexShell(path)) return
        let body = response.body
        if (body instanceof Uint8Array || Buffer.isBuffer(body)) {
          try {
            body = Buffer.from(body as Buffer | Uint8Array).toString('utf8')
          } catch {
            return
          }
        }
        if (typeof body !== 'string') return
        if (!body.includes('<head')) return
        const ct = (response.headers?.['content-type'] as string | undefined) ?? ''
        if (ct && !/text\/html/.test(ct)) return
        const next = injectIntoHead(body)
        if (next === null) return
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
