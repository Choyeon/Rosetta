/**
 * Nitro 全局代理中间件：把浏览器同源的 `/api/**` 请求透传到 FastAPI 后端 (:8000)。
 *
 * 为什么需要？
 *   - 暴露给浏览器的 runtimeConfig.public.apiBase 固定为 `/api`（同源路径），
 *     避免部署跨域 + CORS 复杂问题（登录 JWT / CSRF / cookies 更安全）。
 *   - 开发模式下：`nuxt.config vite.devProxy['/api']` 基于 Vite http-proxy 处理。
 *   - 生产 standalone 构建 (NITRO_PRESET=node-server)：Vite devProxy 不复存在，
 *     Nitro 接收到浏览器请求 `/api/config` 时找不到匹配的 Server Route → 404。
 *   - Nginx 部署（deploy/nginx-site.conf）已有 `/api` upstream 配置，生产 Nginx
 *     场景下本中间件永远不会命中（请求在反代层就被转发）。
 *
 * 适用范围：
 *   · ✅ Windows / Linux 原生启动 (node .output/server/index.mjs)
 *   · ✅ `pnpm dev`（仍走 devProxy，本中间件在 proxy 之前判断并 early-return）
 *   · ❌ Docker compose / Nginx 反代下不执行（请求被 Nginx 先拦截）
 *
 * 性能：与普通 devProxy 等价 —— h3 stream 零拷贝 + header 保留 + onResponse 流式写回。
 * 使用：通过 resolveBackendEndpoint / resolveSsrBackendBase 拿私有后端直连地址，
 *       确保 本地 / 生产 NODE_ENV=production 都能正确解析。
 */
import { defineEventHandler, getRequestHeader, getRequestHeaders, getRequestWebStream, setResponseHeader, setResponseHeaders, sendStream, createError } from 'h3'
import { $fetch } from 'ofetch'
import { resolveSsrBackendBase } from '../utils/ssr'

const BODYLESS_METHODS = new Set(['GET', 'HEAD', 'OPTIONS'])
const PROXIED_PATH_PREFIX = '/api/'

/**
 * 前端 Nitro 自身提供的 BFF /api/* 路由（代理中间件不应拦截，需放过让 Nitro 处理）。
 * 目前只有 `/api/bing-wallpaper`（Bing 每日壁纸 去 CORS+合成 UHD+30m SWR 缓存，对应
 * server/api/bing-wallpaper.get.ts）。后端 FastAPI 不存在同名端点。
 */
const NITRO_OWN_API_ROUTES = new Set([
  '/api/bing-wallpaper'
])

const HOP_BY_HOP_HEADERS = new Set([
  'connection', 'keep-alive', 'proxy-authenticate', 'proxy-authorization',
  'te', 'trailers', 'transfer-encoding', 'upgrade', 'host',
  'content-length', 'content-encoding', 'accept-encoding'
])

const filterHeaders = (h: Record<string, string | string[] | undefined> | Headers): Record<string, string> => {
  const out: Record<string, string> = {}
  if (h instanceof Headers) {
    h.forEach((v, k) => {
      const low = k.toLowerCase()
      if (HOP_BY_HOP_HEADERS.has(low)) return
      out[k] = v
    })
  } else {
    for (const [k, v] of Object.entries(h)) {
      const low = k.toLowerCase()
      if (HOP_BY_HOP_HEADERS.has(low)) continue
      if (v == null) continue
      out[k] = Array.isArray(v) ? v.join(', ') : String(v)
    }
  }
  return out
}

export default defineEventHandler(async (event) => {
  const url = event.node.req.url || '/'
  if (!url.startsWith(PROXIED_PATH_PREFIX)) return // 非 /api/* 直接放过

  // 放过前端 Nitro 自身提供的 BFF /api/* 路由（如 /api/bing-wallpaper）
  const rawUrl: string = String(event.node.req.url || '')
  const question = rawUrl.indexOf('?')
  const hashIdx = rawUrl.indexOf('#')
  const endOfPath = question >= 0
    ? (hashIdx >= 0 ? Math.min(question, hashIdx) : question)
    : hashIdx >= 0 ? hashIdx : rawUrl.length
  const pathOnly = endOfPath > 0 ? rawUrl.slice(0, endOfPath) : rawUrl
  if (pathOnly && NITRO_OWN_API_ROUTES.has(pathOnly)) return

  // 允许 SSR 阶段 (server/utils) 用特殊标记跳过本中间件，避免死循环。
  if (getRequestHeader(event, 'x-nitro-skip-api-proxy') === '1') return

  // 解析私有后端 base（直连 FastAPI）。若未配置且为生产环境，返回 503 提示运维配置 env。
  let backendBase: string
  try {
    const runtime = useRuntimeConfig()
    backendBase = resolveSsrBackendBase(runtime)
    // 若生产环境下解析结果为空字符串（未配置 env）→ 抛 503（与 resolveBackendEndpoint 策略一致）
    if (!backendBase) {
      throw createError({
        statusCode: 503,
        statusMessage:
          'Rosetta /api 代理未配置：请在 .env 中设置 NUXT_API_BASE / SSR_API_BASE_URL 或 BACKEND_HOST + BACKEND_PORT'
      })
    }
  } catch (err) {
    if (err && (err as { statusCode?: number }).statusCode === 503) throw err
    // 其他解析错误（非预期）：开发期兜底 127.0.0.1:8000/api
    backendBase = 'http://127.0.0.1:8000/api'
  }

  const method = event.method || 'GET'
  const subPath = url.slice(PROXIED_PATH_PREFIX.length - 1) // 保留开头的 /
  const target = `${backendBase}${subPath}`

  // 请求头：取浏览器发送的真实 headers（含 Authorization Bearer / Accept-Language / Cookie / Content-Type）
  const inHeaders = filterHeaders(getRequestHeaders(event) as Record<string, string | undefined>)

  // 请求体（h3 原生流）—— 仅非 GET/HEAD 等需要 body 的方法才 attach。
  let body: BodyInit | undefined
  if (!BODYLESS_METHODS.has(method.toUpperCase())) {
    try {
      const stream = getRequestWebStream(event)
      if (stream) body = stream as unknown as BodyInit
    } catch {
      // Fallback to undefined（$fetch 内部会读原始 body；极少数情况会到此分支）
    }
  }

  try {
    const resp = await $fetch.raw(target, {
      method,
      headers: inHeaders,
      body,
      redirect: 'manual',
      // 重要：不要对代理的 4xx/5xx 抛 ofetch 原生错误 → 原样返回给前端，
      // 前端 useApi / apiFetch 的 onResponseError 钩子会统一处理（弹 toast / 刷新 token）。
      ignoreResponseError: true,
      // 不自动解 gzip —— 透传后端原始编码（减少 CPU）
      responseType: 'stream' as unknown as undefined,
      // 后端若未就绪，超时 15s 回 502
      timeout: 15000
    })

    // 回写响应状态码
    event.node.res.statusCode = resp.status || 200
    if (resp.statusText) event.node.res.statusMessage = resp.statusText

    // 回写响应头（hop by hop 过滤，保留 set-cookie / content-type / cache-control 等）
    const outHeaders = filterHeaders(resp.headers)
    // 显式处理 Set-Cookie（Headers.getSetCookie() 多 cookie）
    try {
      const setCookies = (resp.headers as unknown as { getSetCookie?: () => string[] }).getSetCookie?.()
      if (setCookies && setCookies.length) {
        // h3 set-cookie multi: use array via appendHeader
        for (const c of setCookies) {
          setResponseHeader(event, 'set-cookie', c as unknown as never)
        }
        delete outHeaders['set-cookie']
      }
    } catch { /* ignore */ }
    setResponseHeaders(event, outHeaders)

    // 响应体：流式零拷贝写回
    try {
      // resp.body 在 ofetch raw + responseType=stream 下为 ReadableStream (Web)
      const readable = (resp as unknown as { body?: ReadableStream<Uint8Array> }).body
      if (readable) return await sendStream(event, readable as Parameters<typeof sendStream>[1])
    } catch { /* fallback text */ }
    // 兜底：如果 stream 不可用，用 _data
    return (resp as unknown as { _data?: unknown })._data ?? null
  } catch (err) {
    const msg = err instanceof Error ? err.message : String(err)
    // 典型：backend 未启动 → ECONNREFUSED / ECONNRESET / AbortError (timeout)
    if (/(ECONNREFUSED|ECONNRESET|ETIMEDOUT|fetch failed|aborted|timeout)/i.test(msg)) {
      throw createError({
        statusCode: 502,
        statusMessage: 'Bad Gateway (Backend /api 代理失败)',
        message: `Rosetta Nitro /api proxy 无法连接到后端 ${backendBase}。请确认 FastAPI 正在 127.0.0.1:8000 运行：${msg}`
      })
    }
    // 其他错误 → 500
    throw createError({
      statusCode: 500,
      statusMessage: 'Proxy Error',
      message: msg,
      cause: err as Error
    })
  }
})
