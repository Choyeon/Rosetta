/**
 * 文章 Sitemap（分页）Nitro BFF → FastAPI /blog/sitemap-posts.xml?page=N
 *
 * 由 /sitemap.xml 索引引用；对外与索引同域名，避免子表指向后端 /api 地址。
 */

const SITEMAP_NS = 'xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"'
const EMPTY_URLSET = `<?xml version="1.0" encoding="UTF-8"?>\n<urlset ${SITEMAP_NS}></urlset>`

export default defineEventHandler((event) => {
  const runtime = useRuntimeConfig(event)
  const q = getQuery(event)
  // 仅透传 page（后端已做 ge=1 校验）；非法/缺失时后端回落到第 1 页。
  let suffix = ''
  const rawPage = Array.isArray(q.page) ? q.page[0] : q.page
  const pageNum = Number(rawPage)
  if (Number.isInteger(pageNum) && pageNum >= 1) {
    suffix = `?page=${pageNum}`
  }
  const target = resolveBackendEndpoint(runtime, `/blog/sitemap-posts.xml${suffix}`)
  return proxyUpstreamText(event, target, EMPTY_URLSET, {
    accept: 'application/xml',
    cacheControl: 'public, max-age=3600, s-maxage=3600, stale-while-revalidate=86400'
  })
})
