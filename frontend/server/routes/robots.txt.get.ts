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

/** 从 Nitro 响应体安全导出合法 string（兼容 stream / Uint8Array / string / Blob） */
async function stringifyBody(raw: unknown): Promise<string> {
  if (typeof raw === 'string') return raw
  if (raw == null) return ''
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const anyGlobal = globalThis as any
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const anyRaw = raw as any
  if (typeof anyGlobal.Blob !== 'undefined' && raw instanceof anyGlobal.Blob) {
    const ab = await anyRaw.arrayBuffer() as ArrayBuffer
    return Buffer.from(ab).toString('utf8')
  }
  try {
    if (typeof ArrayBuffer !== 'undefined' && raw instanceof ArrayBuffer) {
      return Buffer.from(raw).toString('utf8')
    }
    if (typeof Buffer !== 'undefined' && Buffer.isBuffer(raw)) {
      return raw.toString('utf8')
    }
    if (raw instanceof Uint8Array) {
      return Buffer.from(raw as Uint8Array).toString('utf8')
    }
  } catch { /* ignore */ }
  return String(raw)
}

export default defineEventHandler(async (event) => {
  const runtime = useRuntimeConfig(event)
  const target = resolveBackendEndpoint(runtime, '/seo/robots.txt')

  try {
    const text = await $fetch(target, {
      headers: { accept: 'text/plain' },
      redirect: 'follow',
      responseType: 'text'
    })
    setHeader(event, 'content-type', 'text/plain; charset=utf-8')
    setHeader(event, 'cache-control', 'public, max-age=3600, s-maxage=3600')
    const body = typeof text === 'string' ? text : await stringifyBody(text)
    if (body) return body
  } catch (e) {
    console.warn('[robots.txt] upstream unavailable, returning minimal fallback.', String(e))
  }
  setHeader(event, 'content-type', 'text/plain; charset=utf-8')
  setHeader(event, 'cache-control', 'public, max-age=300, s-maxage=300')
  return 'User-agent: *\nAllow: /\nSitemap: /sitemap.xml\n'
})
