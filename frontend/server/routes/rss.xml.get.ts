/**
 * RSS XML (Nitro BFF → FastAPI /blog/rss)
 *
 * 后端连接单源：server/utils/ssr#resolveBackendEndpoint。
 * 透传 lang / limit 查询参数；上游不可达时返回最小合法 feed（200，不直接 502）。
 */

const RSS_NS = 'xmlns:atom="http://www.w3.org/2005/Atom"'

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

  // 透传 lang / limit（若提供）
  const q = getQuery(event)
  const params = new URLSearchParams()
  if (typeof q.lang === 'string' && q.lang) params.set('lang', q.lang)
  const limitNum = Number(q.limit)
  if (Number.isInteger(limitNum) && limitNum >= 1 && limitNum <= 100) {
    params.set('limit', String(limitNum))
  }
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
