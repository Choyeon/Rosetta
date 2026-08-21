/**
 * robots.txt (Nitro BFF → FastAPI).
 *
 * 后端连接单源：统一读 runtimeConfig，禁止本地默认 127.0.0.1。
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
  const target = resolveBackendEndpoint(runtime, '/seo/robots.txt')

  try {
    const res = await $fetch.raw(target, {
      headers: { accept: 'text/plain' },
      redirect: 'follow'
    })
    setHeader(event, 'content-type', 'text/plain; charset=utf-8')
    setHeader(event, 'cache-control', 'public, max-age=3600, s-maxage=3600')
    return res._data ?? res.body
  } catch (err) {
    throw createError({
      statusCode: 502,
      statusMessage: 'robots.txt upstream unavailable',
      data: String(err)
    })
  }
})
