/**
 * `/feed` —— WordPress 惯例的订阅地址，301 到唯一的真源 `/rss.xml`。
 *
 * 为什么不做成第二条 feed 生成器：订阅者按 URL 去重，同一条 feed 挂两个地址会让
 * 同一个阅读器把一次更新算成两条，且 `features.enable_rss` 的开关只在 `/rss.xml`
 * 这一条链上生效——第二份正文迟早与它分叉。
 *
 * 缓存由 `'/**'` 的 swr 规则统一套（对静态跳转目标无害）；handler 自己不再写
 * Cache-Control —— swr 处理器会整条覆写它，写了也只是"文档承诺、运行时不算数"。
 */
import { sendRedirect } from 'h3'

export default defineEventHandler(event => sendRedirect(event, '/rss.xml', 301))
