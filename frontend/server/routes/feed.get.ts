/**
 * `/feed` —— WordPress 惯例的订阅地址，301 到唯一的真源 `/rss.xml`。
 *
 * 为什么不做成第二条 feed 生成器：订阅者按 URL 去重，同一条 feed 挂两个地址会让
 * 同一个阅读器把一次更新算成两条，且 `features.enable_rss` 的开关只在 `/rss.xml`
 * 这一条链上生效——第二份正文迟早与它分叉。
 *
 * 缓存头不在这里写：3xx 的 HTML 由 `server/utils/ssrHtmlCacheControl.ts`
 * 的 `redirectHtmlCacheControl` 统一改写成 `no-store`（线上实测本路由即回
 * `301 + no-store`），handler 里再写一份只会是"文档承诺、运行时不算数"。
 */
import { sendRedirect } from 'h3'

export default defineEventHandler(event => sendRedirect(event, '/rss.xml', 301))
