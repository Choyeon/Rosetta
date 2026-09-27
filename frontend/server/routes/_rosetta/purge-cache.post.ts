/**
 * POST /_rosetta/purge-cache — 主题变更后的 Nitro 页面缓存清除端点
 * -------------------------------------------------
 * 由 FastAPI 后端调用（backend/services/frontend_cache_purge.py），
 * 清空 Nitro routeRules 的页面级 SWR 缓存
 * （storage 'cache' 下 `nitro:routes:*` 键）。
 *
 * 为什么需要：公开页 HTML 首字节内嵌了渲染当时的主题标记
 * （data-rosetta-theme / theme <link> / 颜色 tokens），缓存窗口内（'/' 300s，
 * /archive 等 3600s）切换主题后访客仍拿到旧主题 HTML，客户端 app:mounted
 * 纠偏再换 DOM → "默认主题闪一下" 的根因。清除后下一次 SSR 即渲染新主题。
 *
 * 安全：
 *   - 生产必须配置 NUXT_PURGE_SECRET，与后端 FRONTEND_PURGE_SECRET 一致；
 *     未配置时本端点直接 404（功能关闭，不暴露清除面）。
 *   - dev 模式下 Nitro 仅监听本机，允许免密钥调用，方便本地零配置验证。
 */
import { timingSafeEqual } from 'node:crypto'

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

export default defineEventHandler(async (event) => {
  const config = useRuntimeConfig(event)
  const secret = String(config.purgeSecret || '')
  if (!secret && !import.meta.dev) {
    throw createError({ statusCode: 404, statusMessage: 'Not Found' })
  }
  if (secret) {
    const given = getRequestHeader(event, 'x-rosetta-purge-secret') || ''
    if (!secretsEqual(given, secret)) {
      throw createError({ statusCode: 403, statusMessage: 'Forbidden' })
    }
  }
  const cache = useStorage('cache')
  const keys = await cache.getKeys('nitro:routes')
  await Promise.all(keys.map(k => cache.removeItem(k)))
  return { success: true, purged: keys.length }
})
