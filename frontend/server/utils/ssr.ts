/**
 * Nitro Server-Routes (SSR/BFF) 侧的后端连接统一工具。
 *
 * 背景：SSR 阶段 Nitro 内部存在两套机制 —— "内部 server route 匹配" 和 "外部 $fetch"。
 * 如果把 baseURL 误设为相对路径（例如浏览器端默认的 '/api'），会命中 Nitro 自身的
 * 内部路由匹配并得到 404，而不是把请求转发到 FastAPI。
 *
 * 为了消除 rss/sitemap/robots 等 4 个 server route 内重复散落的相同推导逻辑，
 * 并且统一失败策略，这里集中实现 endpoint 解析 + 安全回退 。
 *
 * 优先级（与 nuxt.config.ts 的 runtimeConfig 注入策略一一对应）：
 *   1. runtimeConfig.apiBase       — 来自 NUXT_API_BASE / SSR_API_BASE_URL
 *   2. runtimeConfig.backendHost + runtimeConfig.backendPort
 *                                     — 来自 BACKEND_HOST / BACKEND_PORT
 *   3. 开发模式（process.env.NODE_ENV !== 'production'）
 *      自动回退 http://127.0.0.1:8000/api，保证 pnpm dev 开箱即用
 *   4. 生产模式：抛 503，防止静默 404（SSR 期间 /users/login 这类路径若被
 *      Nitro 当内部 route 处理，只会返回 404 HTML 片段，极难排查）。
 */

import type { H3Event } from 'h3'

interface RosettaRuntimePrivate {
  apiBase?: string
  backendHost?: string
  backendPort?: string
}

const DEFAULT_DEV_SSR_BASE = 'http://127.0.0.1:8000/api'

/**
 * 把 runtimeConfig（private 部分）解析为 FastAPI 的绝对 baseURL（末尾不带斜杠）。
 */
export function resolveSsrBackendBase(
  runtime: RosettaRuntimePrivate | ReturnType<typeof useRuntimeConfig>
): string {
  const priv = runtime as RosettaRuntimePrivate
  if (priv.apiBase) return String(priv.apiBase).replace(/\/$/, '')
  if (priv.backendHost && priv.backendPort) {
    return `http://${String(priv.backendHost)}:${String(priv.backendPort)}/api`
  }
  // 开发期后端进程默认监听 127.0.0.1:8000（与 dev.ps1 / AGENTS.md 一致）。
  if (import.meta.dev || process.env.NODE_ENV !== 'production') {
    return DEFAULT_DEV_SSR_BASE
  }
  return ''
}

/**
 * 拼接路径：返回完整的 endpoint URL。生产缺配置时抛 503 H3 Error。
 */
export function resolveBackendEndpoint(
  runtime: RosettaRuntimePrivate | ReturnType<typeof useRuntimeConfig>,
  path: string
): string {
  const base = resolveSsrBackendBase(runtime)
  if (base) return `${base}${path.startsWith('/') ? path : `/${path}`}`
  throw createError({
    statusCode: 503,
    statusMessage:
      'Server not configured: set NUXT_API_BASE / SSR_API_BASE_URL or BACKEND_HOST + BACKEND_PORT'
  })
}

// ── 上游文本（XML / TXT）通用代理 ──────────────────────────────────────

/** 从上游响应体安全导出字符串（兼容 stream / Uint8Array / string / Blob）。 */
export async function stringifyUpstreamBody(raw: unknown): Promise<string> {
  if (typeof raw === 'string') return raw
  if (raw == null) return ''
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const anyGlobal = globalThis as any
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const anyRaw = raw as any
  if (typeof anyGlobal.Blob !== 'undefined' && raw instanceof anyGlobal.Blob) {
    const ab = (await anyRaw.arrayBuffer()) as ArrayBuffer
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
  } catch {
    /* ignore */
  }
  return String(raw)
}

interface ProxyTextOptions {
  /** 上游 accept 头 */
  accept?: string
  /** 成功时回写的 content-type */
  contentType?: string
  /** 成功时的 cache-control */
  cacheControl?: string
  /** 回退时的 cache-control */
  fallbackCacheControl?: string
}

/**
 * 代理上游文本（RSS / Sitemap / robots）：成功则透传文本与缓存头，
 * 失败则返回 ``fallback``，保证爬虫/阅读器永远拿到 200 的合法内容。
 */
export async function proxyUpstreamText(
  event: H3Event,
  target: string,
  fallback: string,
  opts: ProxyTextOptions = {}
): Promise<string> {
  const accept = opts.accept ?? 'application/xml'
  const contentType = opts.contentType ?? 'application/xml; charset=utf-8'
  const cacheControl = opts.cacheControl ?? 'public, max-age=3600, s-maxage=3600'
  try {
    const text = await $fetch(target, {
      headers: { accept },
      redirect: 'follow',
      responseType: 'text'
    })
    const body = typeof text === 'string' ? text : await stringifyUpstreamBody(text)
    if (body) {
      setHeader(event, 'content-type', contentType)
      setHeader(event, 'cache-control', cacheControl)
      return body
    }
  } catch (e) {
    console.warn(`[proxy] upstream unavailable (${target}), using fallback.`, String(e))
  }
  setHeader(event, 'content-type', contentType)
  setHeader(
    event,
    'cache-control',
    opts.fallbackCacheControl ?? 'public, max-age=300, s-maxage=300'
  )
  return fallback
}
