/**
 * 分类 / 标签 / 系列 Sitemap Nitro BFF → FastAPI /blog/sitemap-taxonomies.xml
 */

const SITEMAP_NS = 'xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"'
const EMPTY_URLSET = `<?xml version="1.0" encoding="UTF-8"?>\n<urlset ${SITEMAP_NS}></urlset>`

export default defineEventHandler((event) => {
  const runtime = useRuntimeConfig(event)
  const target = resolveBackendEndpoint(runtime, '/blog/sitemap-taxonomies.xml')
  return proxyUpstreamText(event, target, EMPTY_URLSET, {
    accept: 'application/xml',
    cacheControl: 'public, max-age=3600, s-maxage=3600, stale-while-revalidate=86400'
  })
})
