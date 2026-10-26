/**
 * purge-cache 端点的请求头读取（跨 event 形态）。
 *
 * Nitro 2.13 的路由处理器拿到的是 web 形态 event：真实请求头挂在
 * `event.req.headers`（Headers 实例）上，而随包打入的 `getRequestHeader`
 * 读的是 `event.node.req.headers`——在该路由里实测是空对象，于是
 * **即使前后端密钥一致，清除请求也恒被 403**：主题切换 / 独立页改动在缓存
 * 窗口内一直不生效（后端那侧是 fire-and-forget，失败只记 debug，没人会发现）。
 * 中间件（`server/middleware/00-api-proxy.ts`）不走这条路径，所以只有
 * "路由处理器读请求头"这一种写法会踩到。
 */

/** 后端（backend/services/frontend_cache_purge.py）发来的共享密钥头名。 */
// 显式导入而不是依赖 Nitro 自动导入：本模块同时被 vitest 单测直接 import，
// 在测试环境里自动导入不存在，未导入的符号只会掉进下面的 catch 分支。
import { getRequestHeader } from 'h3'

export const PURGE_SECRET_HEADER = 'x-rosetta-purge-secret'

type HeaderGetter = { get?: (name: string) => string | null }
type NodeLikeHeaders = Record<string, string | string[] | undefined>

/**
 * 依次尝试：h3 规范 API → web `Headers`（event.headers / event.req.headers）
 * → 旧 node 对象。任何一个能拿到就返回，全拿不到返回空串（调用方按失败处理）。
 */
export function readPurgeSecretHeader(event: unknown): string {
  try {
    const direct = getRequestHeader(
      event as Parameters<typeof getRequestHeader>[0],
      PURGE_SECRET_HEADER
    )
    if (direct) return String(direct)
  } catch {
    // node 侧 headers 不可用：继续走 web 形态
  }

  const asWeb = (event ?? {}) as {
    headers?: HeaderGetter
    req?: { headers?: HeaderGetter }
    node?: { req?: { headers?: NodeLikeHeaders, rawHeaders?: string[] } }
  }

  const fromHeaders = asWeb.headers?.get?.(PURGE_SECRET_HEADER)
  if (fromHeaders) return String(fromHeaders)

  const fromReq = asWeb.req?.headers?.get?.(PURGE_SECRET_HEADER)
  if (fromReq) return String(fromReq)

  const raw = asWeb.node?.req?.headers?.[PURGE_SECRET_HEADER]
  if (Array.isArray(raw)) return raw[0] ?? ''
  if (raw) return String(raw)

  // 最后一道：本机实测（Node 22 + Nitro 2.13 的 node-server 产物）请求对象的
  // `headers` 是**空对象**，而 `rawHeaders` 里请求头齐全（Host/UA/x-rosetta-…）。
  // 这是唯一还能拿到密钥的地方；没有它，清除端点在生产构建里恒 403。
  const rawHeaders = asWeb.node?.req?.rawHeaders
  if (Array.isArray(rawHeaders)) {
    for (let i = 0; i + 1 < rawHeaders.length; i += 2) {
      if (String(rawHeaders[i]).toLowerCase() === PURGE_SECRET_HEADER) {
        return String(rawHeaders[i + 1] ?? '')
      }
    }
  }

  return ''
}
