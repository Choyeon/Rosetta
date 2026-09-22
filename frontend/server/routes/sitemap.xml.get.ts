/**
 * Sitemap 索引 (Nitro BFF → FastAPI /blog/sitemap.xml)
 *
 * 后端连接单源：server/utils/ssr#resolveBackendEndpoint。
 * 子表（posts 分页 / taxonomies / pages）均有独立 Nitro 路由，与索引同域名。
 */

const SITEMAP_NS = 'xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"'
const EMPTY_URLSET = `<?xml version="1.0" encoding="UTF-8"?>\n<urlset ${SITEMAP_NS}></urlset>`

export default defineEventHandler((event) => {
  const runtime = useRuntimeConfig(event)
  const target = resolveBackendEndpoint(runtime, '/blog/sitemap.xml')
  return proxyUpstreamText(event, target, EMPTY_URLSET, {
    accept: 'application/xml',
    cacheControl: 'public, max-age=3600, s-maxage=3600, stale-while-revalidate=86400'
  })
})
