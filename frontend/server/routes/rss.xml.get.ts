/**
 * RSS XML (Nitro BFF → FastAPI /blog/rss)
 *
 * 后端连接单源：server/utils/ssr#resolveBackendEndpoint。
 * 透传 lang / limit / category / tag 查询参数；上游不可达时返回最小合法 feed（200，不直接 502）。
 *
 * category / tag 会进缓存键，所以先过一道形状闸门（长度 + 字符集）：不拦的话，
 * 任意垃圾串都能生成一个"合法但没人再访问"的缓存条目（键空间无界），而乱码里的
 * `<`/`&` 还会顺着上游 URL 走一趟。routeRules 的 swr 键含 query hash
 * （nitropack defineCachedEventHandler 默认 getKey），所以 `/rss.xml?category=x`
 * 与 `/rss.xml` 天然各占一份缓存，不会互相串味。
 */

const RSS_NS = 'xmlns:atom="http://www.w3.org/2005/Atom"'

/** 分类/标签 slug 的形状闸门：库里是 String(100) + unique，超长的必然查无此值。 */
const FEED_SLUG_MAX_LEN = 100
/** 控制字符、空白首尾、XML/URL 定界符一律拒绝（后端也会拒，但别让它们进缓存键）。 */
// 这里的控制字符是要**拒掉**的输入，不是拿去匹配正常文本，故不是可转义写法的问题
// eslint-disable-next-line no-control-regex
const FEED_SLUG_BAD_CHARS = /[\u0000-\u001f\u007f<>&"'\\]/

function feedSlug(raw: unknown): string | null {
  if (typeof raw !== 'string') return null
  const value = raw.trim()
  if (!value || value.length > FEED_SLUG_MAX_LEN) return null
  if (FEED_SLUG_BAD_CHARS.test(value)) return null
  return value
}

/** XML 文本节点/属性转义：siteName 等任意配置值直插 <title> 会产出非法 XML。 */
function escapeXml(value: string): string {
  return value.replace(/[<>&"']/g, (c) => {
    switch (c) {
      case '<': return '&lt;'
      case '>': return '&gt;'
      case '&': return '&amp;'
      case '"': return '&quot;'
      default: return '&apos;'
    }
  })
}

export default defineEventHandler((event) => {
  const runtime = useRuntimeConfig(event)
  const siteName = (runtime as unknown as { siteName?: string }).siteName || 'Rosetta'

  // 透传 lang / limit / category / tag（若提供）
  const q = getQuery(event)
  const params = new URLSearchParams()
  if (typeof q.lang === 'string' && q.lang) params.set('lang', q.lang)
  const limitNum = Number(q.limit)
  if (Number.isInteger(limitNum) && limitNum >= 1 && limitNum <= 100) {
    params.set('limit', String(limitNum))
  }
  const categorySlug = feedSlug(q.category)
  if (categorySlug) params.set('category', categorySlug)
  const tagSlug = feedSlug(q.tag)
  if (tagSlug) params.set('tag', tagSlug)
  const qs = params.toString()
  const target = resolveBackendEndpoint(runtime, `/blog/rss${qs ? `?${qs}` : ''}`)

  // channel/link 必须是绝对 URL（RSS 2.0 规范，相对路径会被部分阅读器拒解析）；
  // origin 只认 SITE_URL 配置，不从请求头推导（x-forwarded-host 可被伪造投毒）。
  const siteOrigin = String(
    (runtime as unknown as { siteUrl?: string }).siteUrl
    || (runtime.public as unknown as { siteUrl?: string })?.siteUrl
    || ''
  ).replace(/\/$/, '')

  const fallback = `<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0" ${RSS_NS}>
  <channel>
    <title>${escapeXml(siteName)} RSS</title>
    <link>${siteOrigin ? `${escapeXml(siteOrigin)}/` : '/'}</link>
    <description>Feed is temporarily unavailable.</description>
  </channel>
</rss>`

  return proxyUpstreamText(event, target, fallback, {
    accept: 'application/rss+xml',
    contentType: 'application/rss+xml; charset=utf-8',
    cacheControl: 'public, max-age=1800, s-maxage=1800, stale-while-revalidate=86400',
    fallbackCacheControl: 'public, max-age=180, s-maxage=180'
  })
})
