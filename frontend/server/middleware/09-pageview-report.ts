/**
 * 页面浏览上报（批次 #59：让访客记录页看到的是"谁在浏览站点"，而不是"谁在调 API"）。
 *
 * 为什么必须由边缘上报：nginx 只把 `/api` 与 `/media` 转给 FastAPI，HTML 文档全部由
 * Nitro 自己渲染并直接回给浏览器，后端**从来没见过**这次请求。所以后端的访问日志采集口
 * 数出来的只有浏览器发出的 XHR 与后台自己的调用：真实访客读完一篇文章、Googlebot 抓走
 * 一个页面，一条都不进 `visit_logs`。批次 #53 上线后线上实测：经 nginx 打 `/页面路径`
 * 的两次访问在后端零记录，只有打 `/api/**` 的那两次留下了行。
 *
 * 口径与红线：
 * * 只报 HTML 文档请求（`Accept` 含 `text/html`），跳过 `/api`、`/_*`、`/@*`、`/themes`、
 *   `/media`、`/rss.xml`、`/sitemap*.xml`、`/robots.txt` 与带扩展名的静态资源——
 *   把机器面对象当"页面浏览量"会让读数失去意义。
 * * IP 取 `x-forwarded-for` 第一跳（nginx `$proxy_add_x_forwarded_for` 写进去的那一跳），
 *   没有转发头时退回 socket 对端。绝不从 Host / x-forwarded-host 推导任何东西。
 * * **Cookie 只发名字、不发值**：值是会话凭证。后端落库前还会再重导一次名称
 *   （`backend/api/monitoring.py::_cookie_names_from_raw`），所以就算这里写错也不会把值送进表。
 * * 不阻塞响应：登记 `res` 的 `finish` 事件后立刻返回，上报本身 fire-and-forget、
 *   失败静默丢弃。后端不可达时访客照常拿到页面（这条链只影响遥测）。
 * * 密钥缺失（本地开发没配 `NUXT_PURGE_SECRET`）时整条链**静默关闭**，
 *   而不是发一个注定 403 的请求刷日志——与页面缓存清除用的是同一对共享密钥。
 */
import { defineEventHandler } from 'h3'
import { resolveBackendEndpoint } from '../utils/ssr'

/** 后端内部上报口（与 backend/api/monitoring.py::report_pageview 对齐）。 */
export const PAGEVIEW_PATH = '/monitoring/pageviews'

/** 后端鉴权头名：复用前后端已有的共享密钥，不新增配置项。 */
export const SHARED_SECRET_HEADER = 'x-rosetta-purge-secret'

/** 明显不是"人看的页面"的路径前缀。 */
const NON_DOCUMENT_PREFIXES = [
  '/api',
  '/media',
  '/themes',
  '/_nuxt',
  '/_rosetta',
  '/@',
  '/.well-known',
  '/favicon',
  '/robots.txt',
  '/rss.xml',
  '/feed',
  '/sitemap',
  '/placeholder-covers'
]

/** 带扩展名的请求不是文档（`/posts/xxx` 这类无扩展名路径照常计入）。 */
const STATIC_EXT_RE
  = /\.(?:ico|png|jpe?g|gif|webp|avif|svg|css|js|mjs|json|xml|txt|webmanifest|woff2?|ttf|map)$/i

/** 这次请求算不算"有人看了一个页面"。拆成纯函数是为了让口径本身可单测。 */
export function isDocumentRequest(input: {
  method: string
  path: string
  accept: string
}): boolean {
  if (input.method !== 'GET') return false
  const path = input.path || '/'
  for (const prefix of NON_DOCUMENT_PREFIXES) {
    if (path.startsWith(prefix)) return false
  }
  if (STATIC_EXT_RE.test(path)) return false
  const accept = input.accept || ''
  return accept.includes('text/html') || accept.includes('application/xhtml+xml')
}

/** XFF 的第一跳＝最外层反代看到的客户端；拿不到就回空串（调用方再退回 socket 对端）。 */
export function firstForwardedHop(value: string | string[] | undefined): string {
  const raw = Array.isArray(value) ? value[0] : value
  if (!raw) return ''
  const hop = (String(raw).split(',')[0] ?? '').trim()
  return hop.length <= 50 ? hop : ''
}

/**
 * Cookie 名清单（`a; b; c`）。这里就切掉 `=` 右侧：会话凭证不出本机进程，
 * 后端还会再重导一次名称（`_cookie_names_from_raw`），两侧同规则。
 */
export function cookieNameList(raw: string | string[] | undefined): string {
  const value = Array.isArray(raw) ? raw.join('; ') : String(raw || '')
  const seen: string[] = []
  for (const part of value.split(';')) {
    const name = (part.split('=')[0] ?? '').trim()
    if (name && !seen.includes(name)) seen.push(name)
    if (seen.length >= 24) break
  }
  return seen.slice(0, 24).join('; ').slice(0, 255)
}

/** 一次上报的载荷（与后端 PageviewReport 对齐；刻意没有 cookie 原文这个字段）。 */
export interface PageviewPayload {
  path: string
  method: string
  ip: string
  user_agent: string
  referer: string
  cookie_names: string
  accept_language: string
  status_code: number
  response_time_ms: number
}

/**
 * 从请求头组装上报载荷。纯函数、可单测：中间件里真正发出去的每个字段都由它产出，
 * 所以"值不落库""IP 取第一跳"这两条红线在这里钉住即可，不必去读产物字符串。
 */
export function buildPageviewPayload(input: {
  path: string
  headers: Record<string, string | string[] | undefined>
  socketPeer?: string
  statusCode: number
  responseTimeMs: number
}): PageviewPayload {
  const headers = input.headers || {}
  return {
    path: input.path.slice(0, 500),
    method: 'GET',
    ip: (firstForwardedHop(headers['x-forwarded-for']) || String(input.socketPeer || '')).slice(0, 50),
    user_agent: String(headers['user-agent'] || '').slice(0, 500),
    referer: String(headers.referer || '').slice(0, 500),
    cookie_names: cookieNameList(headers.cookie),
    accept_language: String(headers['accept-language'] || '').slice(0, 100),
    status_code: input.statusCode,
    response_time_ms: Math.max(0, Math.trunc(input.responseTimeMs))
  }
}

export default defineEventHandler((event) => {
  const url = String(event.node.req.url || '')
  const path = url.split('?')[0] || '/'
  const headers = event.node.req.headers as Record<string, string | string[] | undefined>
  if (!isDocumentRequest({ method: event.method, path, accept: String(headers.accept || '') })) return

  const config = useRuntimeConfig(event as never)
  const secret = String((config as { purgeSecret?: string }).purgeSecret || '')
  if (!secret) return // 没配共享密钥＝这条链没装配，静默跳过（不发注定 403 的请求）

  const startedAt = Date.now()
  event.node.res.once('finish', () => {
    const body = buildPageviewPayload({
      path,
      headers,
      socketPeer: event.node.req.socket?.remoteAddress,
      statusCode: event.node.res.statusCode,
      responseTimeMs: Date.now() - startedAt
    })
    let target: string
    try {
      target = resolveBackendEndpoint(config as never, PAGEVIEW_PATH)
    } catch {
      return // 后端地址没配：遥测链不参与请求成败
    }
    // 刻意不 await：上报失败绝不能变成访客看到的 500。
    globalThis
      .fetch(target, {
        method: 'POST',
        headers: { 'content-type': 'application/json', [SHARED_SECRET_HEADER]: secret },
        body: JSON.stringify(body),
        signal: AbortSignal.timeout(3000)
      })
      .catch(() => {
        /* 后端不可达 / 超时：丢弃这一次页面浏览 */
      })
  })
})
