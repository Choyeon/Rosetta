/**
 * `/feed` —— WordPress 惯例的订阅地址，301 到唯一的真源 `/rss.xml`。
 *
 * 为什么不做成第二条 feed 生成器：订阅者按 URL 去重，同一条 feed 挂两个地址会让
 * 同一个阅读器把一次更新算成两条，且 `features.enable_rss` 的开关只在 `/rss.xml`
 * 这一条链上生效——第二份正文迟早与它分叉。
 *
 * 301 本身可缓存，所以这里只发一个短静态缓存头，不让反代把它固定成一整天的软过期窗口
 * （切主题/改站点名与它无关，真正的内容在 `/rss.xml`）。
 */
import { sendRedirect, setHeader } from 'h3'

export default defineEventHandler((event) => {
  setHeader(event, 'cache-control', 'public, max-age=3600, s-maxage=3600')
  return sendRedirect(event, '/rss.xml', 301)
})
