/**
 * `/page/<slug>` 兼容口的服务端 301（slug 命中内建顶级路由时）。
 *
 * 起因：`/page/about` 这类旧 WordPress 链接同时被三条口径描述——
 *  - 页面自己把 canonical 指回 `/<slug>`（`pages/page/[slug].vue`）；
 *  - 页面在 `onBeforeMount` 里客户端 301 到 `/<slug>`；
 *  - sitemap 不再提交这些别名（`backend/api/blog.py::generate_pages_sitemap`）。
 * 但 SSR 本身一直回 200，正文来自库里那条同名独立页记录：绕过 JS 的抓取器看到的
 * 是一份与 canonical 所指页面**内容不同**的 200 重复页，等于三条口径全落空。
 * 收口放在这里：渲染器之前就 301，爬虫、首屏、sitemap 三处从此看同一个地址。
 *
 * 两条实现约束（与 `05-url-normalize.ts` 同源）：
 *  - `no-store` 必须就地写：本中间件用 `sendRedirect` 直接结束响应，不走渲染器，
 *    routeRules 的 `public, max-age=0, s-maxage=…` 会原样留在 301 上（实测过）。
 *  - 只处理单段 slug 且限定清单：`/page/<库里真正的独立页>` 必须继续由渲染器出正文，
 *    否则"独立页"这个功能就没了。语言前缀用 `stripLocalePathPrefix` 剥（`/en/page/about`
 *    也必须跳，且跳回带前缀的 `/en/about`）。
 */
import { defineEventHandler, sendRedirect, setHeader } from 'h3'
import { stripLocalePathPrefix } from '../../lib/rosetta-themes'
import { TOP_LEVEL_ROUTE_SLUGS } from '../../lib/top-level-routes'

export default defineEventHandler((event) => {
  if (!['GET', 'HEAD'].includes(event.method)) return
  const raw = String(event.node.req.url || '')
  const qIdx = raw.indexOf('?')
  const path = qIdx === -1 ? raw : raw.slice(0, qIdx)
  const search = qIdx === -1 ? '' : raw.slice(qIdx)

  if (!path.startsWith('/')) return
  const neutral = stripLocalePathPrefix(path)
  const matched = /^\/page\/([^/]+)$/.exec(neutral)
  if (!matched) return

  const slug = matched[1]!.toLowerCase()
  if (!TOP_LEVEL_ROUTE_SLUGS.includes(slug)) return

  const prefix = neutral === path ? '' : path.slice(0, path.length - neutral.length)
  setHeader(event, 'cache-control', 'no-store')
  return sendRedirect(event, `${prefix}/${slug}${search}`, 301)
})
