/**
 * POST /_rosetta/purge-cache — 主题变更后的 Nitro 页面缓存清除端点
 * -------------------------------------------------
 * 由 FastAPI 后端调用（backend/services/frontend_cache_purge.py），
 * 清空 Nitro routeRules 的页面级 SWR 缓存。
 *
 * 为什么需要：公开页 HTML 首字节内嵌了渲染当时的主题标记
 * （data-rosetta-theme / theme <link> / 颜色 tokens），缓存窗口内（'/' 300s，
 * /archive 等 3600s）切换主题后访客仍拿到旧主题 HTML，客户端 app:mounted
 * 纠偏再换 DOM → "默认主题闪一下" 的根因。清除后下一次 SSR 即渲染新主题。
 * 独立页正文、公告、站点设置同理。
 *
 * 安全：
 *   - 生产必须配置 NUXT_PURGE_SECRET，与后端 FRONTEND_PURGE_SECRET 一致；
 *     未配置时本端点直接 404（功能关闭，不暴露清除面）。
 *   - dev 模式下 Nitro 仅监听本机，允许免密钥调用，方便本地零配置验证。
 */
import { timingSafeEqual } from 'node:crypto'

import { readPurgeSecretHeader } from '../../utils/purgeSecret'

/**
 * 常数时间比较：`given !== secret` 的字符串比较会在首个差异字节短路，
 * 攻击者可通过计时侧信道逐字节猜出 purge 密钥。
 * 长度差异无法隐藏（timingSafeEqual 要求等长），但内容比对全程常数时间。
 */
function secretsEqual(given: string, secret: string): boolean {
  const a = Buffer.from(given, 'utf8')
  const b = Buffer.from(secret, 'utf8')
  return a.length === b.length && timingSafeEqual(a, b)
}

/**
 * 页面级 SWR 缓存的键**特征**（不依赖具体前缀拼法）。
 *
 * 实测（Nitro 2.13 产物）里，同一个页面的缓存键至少以两种形态出现过：
 *   · 默认 storage：`cache:nitro:routes:_:posts.<hash>.json`
 *   · `cache` 挂载点：`nitro:routes:_:posts.<hash>.json`
 * 而本端点原先写死 `useStorage('cache').getKeys('nitro:routes')`：只要实现换了
 * 命名空间，它就静默变成"只清掉 server-routes 那几条"，页面 HTML 一条都不清——
 * 主题切换、独立页改动、后台任何"清缓存"操作对公开页全部无效，直到 TTL 自然过期，
 * 且后端是 fire-and-forget，失败只记 debug，没有任何可见信号。
 *
 * 所以这里改成：把两个 storage 的全部键拉出来，按"键里含 nitro:routes / nitro/routes"
 * 匹配。前缀形态再怎么变都命中，而且不会误删 i18n / assets 之类无关缓存。
 */
const ROUTE_CACHE_KEY_RE = /nitro[/:]routes/

async function purgePageCaches(): Promise<{ purged: number, keys: string[] }> {
  const purgedKeys: string[] = []
  for (const storage of [useStorage(), useStorage('cache')]) {
    try {
      const keys = await storage.getKeys('')
      const targets = keys.filter(key => ROUTE_CACHE_KEY_RE.test(key))
      if (!targets.length) continue
      await Promise.all(targets.map(key => storage.removeItem(key)))
      purgedKeys.push(...targets)
    } catch (error) {
      // 一个 storage 出问题不能拦住另一个；清除失败按"没清到"如实返回
      console.warn('[purge-cache] 清除失败', error)
    }
  }
  return { purged: purgedKeys.length, keys: purgedKeys }
}

export default defineEventHandler(async (event) => {
  const config = useRuntimeConfig(event)
  const secret = String(config.purgeSecret || '')
  if (!secret && !import.meta.dev) {
    throw createError({ statusCode: 404, statusMessage: 'Not Found' })
  }
  if (secret) {
    const given = readPurgeSecretHeader(event)
    if (!secretsEqual(given, secret)) {
      throw createError({ statusCode: 403, statusMessage: 'Forbidden' })
    }
  }
  return { success: true, ...(await purgePageCaches()) }
})
