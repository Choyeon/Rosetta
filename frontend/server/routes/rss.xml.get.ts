/**
 * RSS XML (Nitro BFF → FastAPI /blog/rss)
 *
 * 后端连接单源：server/utils/ssr#resolveBackendEndpoint。
 * 透传 lang / limit 查询参数；上游不可达时返回最小合法 feed（200，不直接 502）。
 */

const RSS_NS = 'xmlns:atom="http://www.w3.org/2005/Atom"'

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

  const fallback = `<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0" ${RSS_NS}>
  <channel>
    <title>${siteName} RSS</title>
    <link>/</link>
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
