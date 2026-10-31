/**
 * llms.txt (Nitro BFF → FastAPI) — 面向 LLM 爬虫的纯文本站点索引。
 *
 * 后端连接单源：server/utils/ssr#resolveBackendEndpoint（与 robots/rss 同轨；
 * 生产缺配置时它会抛 503，这里整体 try/catch 成"仅站点信息的最小文本"，
 * llms.txt 的口径是后端不可达也必须 200，500/503 对抓取器不可接受）。
 *
 * 组成：站点名 + 一句话描述（/settings/public 的 basic 组）、核心页面清单
 * （CORE_PAGES，每条都必须在 pages/ 有真实路由——由 geoDeliveryRoutes.spec 钉住，
 * 指向 404 的"给 AI 的索引"比不列更糟）、四语首页 URL（prefix_except_default
 * 口径，语言前缀清单复用 lib/rosetta-themes 的 LOCALE_PATH_PREFIX_VARIANTS）、
 * 最新 10 篇文章（/blog/posts，同 rss 路由的"上游取数 + 本地组装"手法）。
 *
 * 站点根只认配置（resolvePublicSiteOrigin），绝不从请求 Host 推导——
 * 这些路由带 s-maxage，一次 Host 伪造会被缓存固化给所有访客（同一红线见
 * robots.txt.get.ts）。CSP / 安全头由 nginx 层统一叠加，本文件无需动作。
 */

import { DEFAULT_LOCALE_CODE, LOCALE_PATH_PREFIX_VARIANTS, NON_DEFAULT_LOCALE_CODES } from '../../lib/rosetta-themes'

/**
 * 核心页面清单：[显示名, 中性路径]。默认语言（zh）裸路径，四语入口在首页一节单列。
 *
 * 口径 = 后端 `_STATIC_SITEMAP_ROUTES`（「恒存在且恒可索引」的固定公开路由）+ 三个分类学
 * 根目录（`/categories` `/tags` `/series`，它们由 `generate_taxonomy_sitemap` 输出，所以不在
 * 那张表里，但同样是目录页）+ 两个 feed 出口。**那张表是本清单的判据之一**：往 sitemap 固定
 * 路由里加一页而 llms.txt 没跟上，等于给爬虫一份少了条目的站点索引——由
 * `tests/test_llms_core_pages_match_sitemap.py` 跨语言对账钉住（集合相等，例外只有上面两类）。
 * 反过来，可索引性由运行时配置决定的页面（/sponsor 看捐助配置、/gallery 与 /wallpapers 看有没有
 * 内容）不写在这里：把动态答案写死进一份带 3600s 缓存的静态索引，等于让 llms.txt 替 sitemap
 * 做它做不了的判断。
 */
const CORE_PAGES = [
  ['Home', '/'],
  ['Posts', '/posts'],
  ['Hot posts', '/posts/hot'],
  ['Archive', '/archive'],
  ['Categories', '/categories'],
  ['Tags', '/tags'],
  ['Series', '/series'],
  ['Authors', '/authors'],
  ['Activity', '/activity'],
  ['Guestbook', '/guestbook'],
  ['Friends', '/friends'],
  ['About', '/about'],
  ['RSS', '/rss.xml'],
  ['Sitemap', '/sitemap.xml']
] as const

const POSTS_LIMIT = 10

/** 后端 i18n 字段可能是本地化字符串或 {zh,en,…} 字典，统一压成一行纯文本。 */
function flatText(value: unknown, limit = 160): string {
  let raw = ''
  if (typeof value === 'string') {
    raw = value
  } else if (value && typeof value === 'object' && !Array.isArray(value)) {
    const dict = value as Record<string, unknown>
    // 语言清单唯一来源 lib/rosetta-themes：默认语言优先，再按其余三语
    for (const code of [DEFAULT_LOCALE_CODE, ...NON_DEFAULT_LOCALE_CODES]) {
      const v = dict[code]
      if (typeof v === 'string' && v.trim()) {
        raw = v
        break
      }
    }
  }
  return raw.replace(/[\r\n]+/g, ' ').replace(/\s+/g, ' ').trim().slice(0, limit)
}

interface PostListRow {
  slug?: string | number | null
  title?: unknown
  excerpt?: unknown
}

interface PublicSettingsResponse {
  groups?: { basic?: Record<string, unknown> }
}

interface PostListResponse {
  items?: PostListRow[]
}

export default defineEventHandler(async (event) => {
  const runtime = useRuntimeConfig(event)
  const origin = resolvePublicSiteOrigin(runtime)
  // 上游全挂时的最小文本底：站点名连 runtime 都拿不到就用品牌默认值。
  let siteName = String((runtime as unknown as { siteName?: string }).siteName || 'Rosetta')
  let siteDescription = ''
  const posts: PostListRow[] = []

  // 两个上游各自独立降级：settings 失败不影响文章列表，反之亦然。
  try {
    const pub = await $fetch<PublicSettingsResponse>(
      resolveBackendEndpoint(runtime, '/settings/public'),
      { timeout: 8000 }
    )
    const basic = pub?.groups?.basic
    if (basic) {
      const name = flatText(basic.site_name, 100)
      if (name) siteName = name
      siteDescription = flatText(basic.site_description, 200)
    }
  } catch (e) {
    console.warn('[llms.txt] /settings/public unavailable, using runtime defaults.', String(e))
  }
  try {
    const list = await $fetch<PostListResponse>(
      resolveBackendEndpoint(runtime, '/blog/posts'),
      { query: { page: 1, page_size: POSTS_LIMIT, lang: 'zh' }, timeout: 8000 }
    )
    if (Array.isArray(list?.items)) posts.push(...list.items.slice(0, POSTS_LIMIT))
  } catch (e) {
    console.warn('[llms.txt] /blog/posts unavailable, omitting post list.', String(e))
  }

  const lines: string[] = [`# ${siteName}`]
  if (siteDescription) lines.push('', `> ${siteDescription}`)

  if (origin) {
    lines.push('', '## Core pages')
    for (const [label, path] of CORE_PAGES) {
      lines.push(`- [${label}](${origin}${path})`)
    }

    lines.push('', '## Homepage (four languages)')
    // LOCALE_PATH_PREFIX_VARIANTS：默认语言裸路径，其余三语各自挂 /en、/ja、/zh_Hant 前缀
    // （清单唯一真源 lib/rosetta-themes，这里只消费不再写死一份）
    for (const variant of LOCALE_PATH_PREFIX_VARIANTS) {
      const code = variant ? variant.slice(1) : DEFAULT_LOCALE_CODE
      lines.push(`- ${code}: ${origin}${variant}/`)
    }

    if (posts.length > 0) {
      lines.push('', '## Latest posts')
      for (const post of posts) {
        const slug = String(post.slug ?? '').trim()
        if (!slug) continue
        const title = flatText(post.title, 120) || slug
        const excerpt = flatText(post.excerpt, 200)
        const url = `${origin}/posts/${encodeURIComponent(slug)}`
        lines.push(excerpt ? `- [${title}](${url}): ${excerpt}` : `- [${title}](${url})`)
      }
    }
  }

  setHeader(event, 'content-type', 'text/plain; charset=utf-8')
  setHeader(event, 'cache-control', 'public, max-age=3600, s-maxage=3600, stale-while-revalidate=86400')
  return `${lines.join('\n')}\n`
})
