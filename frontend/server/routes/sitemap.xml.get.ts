/**
 * Sitemap XML (Nitro BFF → FastAPI).
 *
 * 后端连接单源：统一读 runtimeConfig，禁止本地默认 127.0.0.1。
 * - 生产：必须通过 SSR_API_BASE_URL 或 BACKEND_HOST + BACKEND_PORT 显式声明。
 * - 开发：由 resolveSsrApiBase() 推导写入 runtime.apiBase。
 */
function resolveBackendEndpoint(runtime: ReturnType<typeof useRuntimeConfig>, path: string): string {
  const priv = runtime as unknown as { apiBase?: string, backendHost?: string, backendPort?: string }
  if (priv.apiBase) {
    const base = String(priv.apiBase).replace(/\/$/, '')
    return `${base}${path}`
  }
  if (priv.backendHost && priv.backendPort) {
    return `http://${String(priv.backendHost)}:${String(priv.backendPort)}/api${path}`
  }
  throw createError({
    statusCode: 503,
    statusMessage: 'Server not configured: set SSR_API_BASE_URL or BACKEND_HOST + BACKEND_PORT'
  })
}

export default defineEventHandler(async (event) => {
  const runtime = useRuntimeConfig(event)
  const target = resolveBackendEndpoint(runtime, '/blog/sitemap.xml')

  try {
    const res = await $fetch.raw(target, {
      headers: { accept: 'application/xml' },
      redirect: 'follow'
    })
    setHeader(event, 'content-type', 'application/xml; charset=utf-8')
    setHeader(event, 'cache-control', 'public, max-age=3600, s-maxage=3600')
    return res._data ?? res.body
  } catch {
    throw createError({
      statusCode: 502,
      statusMessage: 'Sitemap upstream unavailable'
    })
  }
})
