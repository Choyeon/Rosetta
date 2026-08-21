/**
 * RSS XML (Nitro BFF → FastAPI).
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

const RSS_NS = 'xmlns:atom="http://www.w3.org/2005/Atom"'

/** 从响应体安全导出合法 string（兼容 stream / Uint8Array / string / Blob） */
async function stringifyBody(raw: unknown): Promise<string> {
  if (typeof raw === 'string') return raw
  if (raw == null) return ''
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const anyRaw = raw as any
  // 兜底判 Blob：不同 realm 的 instanceof 不可靠，用构造名 + arrayBuffer 方法双保险。
  if (anyRaw && typeof anyRaw.arrayBuffer === 'function'
    && (anyRaw.constructor?.name === 'Blob' || anyRaw.constructor?.name === 'File')) {
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
    if (anyRaw && typeof anyRaw.text === 'function') {
      const t = await anyRaw.text()
      if (typeof t === 'string') return t
    }
  } catch { /* ignore */ }
  return String(raw)
}

export default defineEventHandler(async (event) => {
  const runtime = useRuntimeConfig(event)
  const target = resolveBackendEndpoint(runtime, '/blog/rss')
  const siteName = (runtime as unknown as { siteName?: string }).siteName || 'Rosetta'

  try {
    // 强制以纯文本取后端 XML，避免 Nitro/ohmyfetch 返回 Blob 被直接序列化。
    const text = await $fetch(target, {
      headers: { accept: 'application/rss+xml' },
      redirect: 'follow',
      responseType: 'text'
    })
    setHeader(event, 'content-type', 'application/rss+xml; charset=utf-8')
    setHeader(event, 'cache-control', 'public, max-age=1800, s-maxage=1800')
    const body = typeof text === 'string' ? text : await stringifyBody(text)
    if (body) return body
  } catch (e) {
    console.warn('[rss.xml] upstream unavailable, returning minimal empty feed.', String(e))
  }
  // 最小合法空 RSS：保证爬虫/阅读器 200 拿到合法 XML，不直接 502
  setHeader(event, 'content-type', 'application/rss+xml; charset=utf-8')
  setHeader(event, 'cache-control', 'public, max-age=180, s-maxage=180')
  return `<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0" ${RSS_NS}>
  <channel>
    <title>${siteName} RSS</title>
    <link>/</link>
    <description>Feed is temporarily unavailable.</description>
  </channel>
</rss>`
})
