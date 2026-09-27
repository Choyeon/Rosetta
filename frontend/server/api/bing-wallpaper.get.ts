// Nitro BFF：Bing 每日壁纸（无 CORS，且一次性剥离多余字段 + 补齐大图 URL）
//
// Query:
//   idx?: number   0=今天 (默认)，1=昨天，… 最大 7 (Bing 官方归档仅保留最近 8 天)
//   mkt?: string   zh-CN (默认) / en-US / ja-JP 等
//
// Response:
//   {
//     url:           string   // 4K 分辨率直链 (https://cn.bing.com/...)
//     title:         string   // 当天标题（中文区域通常含图片描述）
//     copyright:     string   // 版权行（如 "© 摄影师 / 机构名称"）—— 用于在页面角落展示
//     copyrightLink: string   // 版权详情链接
//     startDate:     string   // YYYYMMDD
//     idx:           number   // 回显入参
//     totalDays:     8
//   }

import type { H3Event } from 'h3'

interface BingImage {
  url: string
  urlbase: string
  copyright: string
  copyrightlink: string
  title: string
  startdate: string
}

interface BingMetaResponse {
  images: BingImage[]
}

/** 归一化 query 参数（handler 与缓存 key 共用，保证两者一致）。 */
function parseParams(event: H3Event) {
  const query = getQuery(event)
  const idx = Math.max(0, Math.min(7, Number(query.idx) || 0))
  const mkt = typeof query.mkt === 'string' && query.mkt.trim() ? query.mkt.trim() : 'zh-CN'
  return { idx, mkt }
}

// Nitro 层结果缓存（真正的 30m SWR）：此前只有成功路径的响应头缓存，
// 缓存头只影响下游 CDN/浏览器，Nitro 自身每次请求仍串行打 Bing；
// Bing 不可达时 SSR 引用会拖垮 TTFB。现在：
//   · 30m 内命中缓存直接回放（含 setHeader 的响应头，Nitro 会缓存并 replay）
//   · 过期后先回旧值、后台刷新（swr），上游报错时降级继续用旧值
//   · 仅「从未成功缓存过 + 上游失败」才落到 502
export default defineCachedEventHandler(async (event) => {
  const { idx, mkt } = parseParams(event)

  const bingUrl
    = `https://cn.bing.com/HPImageArchive.aspx?format=js&idx=${idx}&n=1&mkt=${encodeURIComponent(mkt)}`

  const headers = new Headers({
    'User-Agent':
      'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36',
    'Accept': 'application/json, text/javascript, */*; q=0.01'
  })

  let data: BingMetaResponse
  try {
    const res = await fetch(bingUrl, {
      headers,
      // Nitro 在 node 运行时支持 AbortSignal；给一个合理的超时，别让 SSR 卡住
      signal: AbortSignal.timeout(5000) as unknown as AbortSignal
    })
    if (!res.ok) throw new Error(`Bing responded ${res.status}`)
    data = (await res.json()) as BingMetaResponse
  } catch (err) {
    throw createError({
      statusCode: 502,
      statusMessage: 'BingWallpaperUpstreamError',
      message: err instanceof Error ? err.message : 'Unknown upstream error',
      data: { idx, mkt }
    })
  }

  const img = data?.images?.[0]
  if (!img) {
    throw createError({
      statusCode: 502,
      statusMessage: 'BingWallpaperEmpty',
      message: `No image returned for idx=${idx} mkt=${mkt}`
    })
  }

  // 取 UHD 大图（1920x1080 已够；UHD=3840x2160 体积大效果好）
  // url 形如 /th?id=OHR.MadagascarTsingy_ZH-CN11176168567_1920x1080.jpg&rf=...
  // 把 1920x1080 换成 UHD
  let uhd = img.url
  if (uhd.startsWith('/')) uhd = `https://cn.bing.com${uhd}`
  uhd = uhd.replace(/_(1920x1080|1366x768|1280x720)\.(jpg|jpeg|png)/i, '_UHD.jpg')

  // 响应头随缓存条目一起被 Nitro replay，命中时同样携带
  setHeader(event, 'Cache-Control', 'public, max-age=1800, s-maxage=3600, stale-while-revalidate=86400')
  setHeader(event, 'Vary', 'Accept, Accept-Language')

  return {
    url: uhd,
    title: img.title || '',
    copyright: img.copyright || '',
    copyrightLink: img.copyrightlink || '',
    startDate: img.startdate || '',
    idx,
    totalDays: 8
  }
}, {
  maxAge: 1800, // 30m 内直接命中缓存，不打上游
  swr: true, // 过期后先回旧值、后台静默刷新；刷新失败时旧值继续顶住（降级不 502）
  staleMaxAge: 86400, // 旧值最长可容忍 24h（声明意图；本版 Nitro swr:true 下主要靠 mtime 判断）
  getKey: (event: H3Event) => {
    const { idx, mkt } = parseParams(event)
    return `idx:${idx}:mkt:${mkt}`
  }
})
