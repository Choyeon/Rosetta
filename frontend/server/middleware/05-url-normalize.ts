/**
 * URL 规范化中间件（服务端 301）：
 *
 * 1. 折叠百分号叠加编码：`%25E6` → `%E6`（历史 bug 会在每次 SSR 给 URL 多包一层
 *    %→%25，浏览器地址栏/历史记录可能已停留在污染形态，这里做单向自愈重定向）。
 * 2. 去掉页面路径末尾多余的 `/`（`/posts/xxx/` 不匹配 vue-router 的 `[slug]`，
 *    会落 404；对 SEO 也统一了 canonical 形态）。
 *
 * 范围：仅 GET/HEAD 的页面请求；`/api*`（走后端/upstream）、`/_nuxt`、`/@vite`
 * 等内部资源一律放过。
 *
 * `no-store` 必须在这里就地写：本中间件用 `sendRedirect` 直接结束响应，不走渲染器，
 * 于是 `ssr-html-revalidate` 的 `render:response` / `beforeResponse` 两道钩子都轮不到它，
 * routeRules 给该路径的 `public, max-age=0, s-maxage=…` 会原样留在 301 上。
 * 实测 `/en/` 回了 `s-maxage=300` 的 301（CDN 缓存 5 分钟），与本仓「3xx 的 HTML 一律
 * no-store」的口径冲突（见 AGENTS §2.3）。
 */
import { defineEventHandler, sendRedirect, setHeader } from 'h3'

const MAX_DECODE_PASSES = 4

function collapsePercentLayers(path: string): string {
  let cur = path
  // 只折叠 %25 层（%25XX → %XX）；绝不调 decodeURIComponent——那会连真实
  // %XX 一起解掉（如 %2D 连字符丢失），把干净 URL 解成不存在的死链。
  for (let i = 0; i < MAX_DECODE_PASSES && /%25/i.test(cur); i++) {
    const next = cur.replace(/%25/gi, '%')
    if (next === cur) break
    cur = next
  }
  return cur
}

export default defineEventHandler((event) => {
  if (!['GET', 'HEAD'].includes(event.method)) return
  const raw = String(event.node.req.url || '')
  const qIdx = raw.indexOf('?')
  const original = qIdx === -1 ? raw : raw.slice(0, qIdx)
  const search = qIdx === -1 ? '' : raw.slice(qIdx)

  if (original === '/' || original.startsWith('/api') || original.startsWith('/_')
    || original.startsWith('/@')) return

  let target = collapsePercentLayers(original)
  // 防协议相对跳转注入（'//evil'），同时统一重复斜杠前缀
  target = target.replace(/^\/{2,}/, '/')
  if (target.length > 1 && target.endsWith('/')) {
    target = target.replace(/\/+$/, '') || '/'
  }

  if (target !== original) {
    setHeader(event, 'cache-control', 'no-store')
    return sendRedirect(event, target + search, 301)
  }
})
