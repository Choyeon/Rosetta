/**
 * Bing 壁纸的站内直链与归档载荷归一（SSR 与客户端必须同结果）。
 *
 * 两件事都必须单源：
 * 1. **图片一律走站内代理**（`/api/bing/image?src=<base64>`）。把 `cn.bing.com` 原链直接挂进
 *    `<img src>` 会让访客的浏览器绕过本站缓存去打 Bing（Bing 侧有限流与地区差异），而且
 *    站内代理那一份 30 天 `immutable` 强缓存与兜底 SVG 全部失效。
 * 2. **代理串在 SSR 渲染期就要算好**。页面是 SSR 的，首帧 `<img src>` 由服务端产出，
 *    客户端 hydration 再算一遍必须逐字节相同，否则每个卡片都是一次节点级 mismatch。
 */

export interface BingWallpaperCard {
  /** `YYYY-MM-DD`，来自上游 `startdate`（Bing 认定这张图属于哪一天） */
  date: string
  title: string
  /** 1920x1080 站内代理直链 */
  image: string
  /** 4K UHD 站内代理直链；上游没给就是空串 */
  download: string
  copyright: string
  /** 版权详情页（上游 copyrightlink）；没有就是空串，不渲染成链接 */
  source: string
}

/**
 * 原始图片地址 → 站内代理地址。
 *
 * 空串原样返回空串（调用方据此决定是否渲染 `<img>`）；编码失败时退回原链——
 * 代理口本身有兜底图，但宁可显示外链也不要一张碎图。
 */
export function bingProxyUrl(rawUrl: string, apiBase = '/api'): string {
  const url = String(rawUrl || '').trim()
  if (!url) return ''
  if (url.startsWith('data:') || url.startsWith(apiBase)) return url
  const abs = url.startsWith('http') ? url : `https://cn.bing.com${url}`
  try {
    const encoded = btoa(unescape(encodeURIComponent(abs)))
    return `${apiBase || '/api'}/bing/image?src=${encoded}`
  } catch {
    return abs
  }
}

function text(value: unknown): string {
  return typeof value === 'string' ? value.trim() : ''
}

/**
 * 归档响应 → 卡片列表。
 *
 * 接受 `{ success, data: [...] }`、`{ data: { data: [...] } }` 与裸数组三种形态：后端信封在
 * 不同版本里叠过一层，`useAPI` 不做解包，所以读侧按"能解出数组就用"处理，而不是赌一种形状。
 * 没有日期也没有图片地址的条目丢弃——那等于一张没有署名的空卡片。
 */
export function parseBingArchive(payload: unknown, apiBase = '/api'): BingWallpaperCard[] {
  let node: unknown = payload
  for (let depth = 0; depth < 3; depth += 1) {
    if (Array.isArray(node)) break
    if (node && typeof node === 'object') node = (node as Record<string, unknown>).data
    else return []
  }
  if (!Array.isArray(node)) return []

  const cards: BingWallpaperCard[] = []
  const seen = new Set<string>()
  for (const item of node) {
    if (!item || typeof item !== 'object') continue
    const row = item as Record<string, unknown>
    const date = text(row.date)
    const image = bingProxyUrl(text(row.url), apiBase)
    if (!image && !date) continue
    const key = `${date}|${image}`
    if (seen.has(key)) continue
    seen.add(key)
    cards.push({
      date,
      title: text(row.title) || date,
      image,
      download: bingProxyUrl(text(row.url_uhd), apiBase),
      copyright: text(row.copyright),
      source: text(row.copyright_url ?? row.copyrightlink)
    })
  }
  return cards
}
