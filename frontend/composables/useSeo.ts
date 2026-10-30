/**
 * useSeo — 统一的 SEO composable
 *
 * 功能：
 * 1. useSeoMeta({ title, description, image, url, type }) — 统一设置
 *    <title>、<meta>、OpenGraph、Twitter Card，自动避免重复。
 * 2. 预构建的 JSON-LD helper：
 *    - useArticleJsonLd(post)     — BlogPosting / Article（文章详情页）
 *    - useBreadcrumbJsonLd(items) — BreadcrumbList（分类/标签/归档页面包屑）
 *    - useWebsiteJsonLd()         — WebSite + SearchAction（首页）
 *
 * 所有 helper 都是 SSR 安全的：仅依赖 useHead（Nuxt 自动导入，在 SSR/SPA 两者下
 * 都正确）。不需要 import.meta.client 守卫。
 */

import { computed } from 'vue'
import { OG_FALLBACK_IMAGE } from '~~/lib/post-cover'
import { DEFAULT_LOCALE_CODE, NON_DEFAULT_LOCALE_CODES, stripLocalePathPrefix } from '~~/lib/rosetta-themes'

/**
 * 分享图取值的单源：调用方显式给了就用它 → 否则用后台 `seo.default_og_image`
 * → 两者都空（OOBE / 分组未下发）才回落站内品牌图。
 *
 * 少这一步时，首页与所有列表页只有 `twitter:card=summary_large_image` 却没有
 * `og:image` / `twitter:image`：社交平台按大字卡渲染却发现无图，退化成纯文字预览，
 * 后台配置的「站内默认分享图」对这些页面完全无效（实测 2026-10-29 全站只有文章页有图）。
 */
export function resolveShareImage(explicit: string, siteDefault: string): string {
  return (explicit || '').trim() || (siteDefault || '').trim() || OG_FALLBACK_IMAGE
}

/**
 * 不可索引页的唯一 robots 口径。
 *
 * 刻意用 `follow` 而不是 `nofollow`：robots.txt 已把这些路径从 Disallow 移出，
 * 移出的理由正是"允许抓取、只禁止入索引"；再叠一层 nofollow 等于把 /search
 * 这类站内链接枢纽上的文章链接也一并掐断，Google 只能靠 sitemap 发现新文章。
 * noindex 本身就足以让页面退出索引。
 *
 * 服务端注入见 `server/utils/noindex-shell.ts`（ssr:false 空壳拿不到这里）。
 */
export const NOINDEX_ROBOTS = 'noindex, follow'

// ---------------------------------------------------------------------------
// 基础类型
// ---------------------------------------------------------------------------

export interface SeoMetaOptions {
  /** 页面标题（不含站点名）。支持 Ref/ComputedRef，undefined 内部 fallback 为空 */
  title?: string | { readonly value?: string | undefined }
  /** 页面描述（100–160 字符）。支持 Ref/ComputedRef */
  description?: string | { readonly value?: string | undefined }
  /** 分享预览图。支持 Ref/ComputedRef（允许内部 value 为 undefined） */
  image?: string | { readonly value?: string | undefined }
  /** og:image:alt 分享预览图描述。支持 Ref/ComputedRef */
  imageAlt?: string | { readonly value?: string | undefined }
  /** 规范链接；留空时由 useHead 推导当前 URL */
  url?: string | { readonly value?: string | undefined }
  /** og:type，默认 "website"；文章详情页传 "article" */
  type?:
    | 'website'
    | 'article'
    | 'blog'
    | 'profile'
    | string
  /** 追加/覆盖 meta（支持 Ref）。用于特殊字段：article:published_time 等 */
  extraMeta?:
    | Array<Record<string, string>>
    | { readonly value?: Array<Record<string, string>> | undefined }
  /** noindex:true 输出 `NOINDEX_ROBOTS`（noindex, follow）+ 抑制 canonical/hreflang。搜索结果页与设置页用 */
  noindex?: boolean | { readonly value?: boolean | undefined }
  /** 覆盖 site.seo.twitter_handle（一般不用） */
  twitterSite?: string | { readonly value?: string | undefined }
}

/**
 * 语言码 → Open Graph 期望的 locale 形式（<lang>_<COUNTRY>）。
 * raw code 'zh' / 'en' / 'ja' / 'zh_Hant' 直接输出会被爬虫标为 invalid。
 * 新增语言：同步更新此处与 nuxt.config i18n.locales。
 */
export const OG_LOCALE_MAP: Record<string, string> = {
  zh: 'zh_CN',
  en: 'en_US',
  ja: 'ja_JP',
  zh_Hant: 'zh_TW'
}

/** hreflang 期望 BCP-47 短标签；zh_Hant → zh-Hant（下划线换连字符）。 */
export const HREFLANG_MAP: Record<string, string> = {
  zh: 'zh-CN',
  en: 'en',
  ja: 'ja',
  zh_Hant: 'zh-Hant'
}

/**
 * i18n 语言码 → BCP-47 标签，喂给 `Intl.*` / `toLocaleDateString` 这类原生 API。
 *
 * i18n 的 `zh_Hant` 不是合法 BCP-47：`new Intl.DateTimeFormat('zh_Hant')` 直接抛
 * `RangeError: Incorrect locale information provided`。实测表现是 /zh_Hant/archive/<年>/<月>
 * 整页渲染成 200 空壳（setup 抛错），en/ja 正常——四个语言码里只有这一个带下划线。
 * 与 hreflang 共用一张表：同一套语言码在整站只允许一种 BCP-47 形态。
 */
export function toBcp47Locale(code: string | undefined | null): string {
  if (!code) return HREFLANG_MAP[DEFAULT_LOCALE_CODE] as string
  return HREFLANG_MAP[code] ?? code.replace(/_/g, '-')
}

/** 非默认语言在 URL 上挂的前缀；默认语言 zh 裸路径。清单唯一来源 lib/rosetta-themes。 */
export { NON_DEFAULT_LOCALE_CODES, DEFAULT_LOCALE_CODE }

/** 剥掉路径开头的 /en /ja /zh_Hant 段，得到"中性"路径供 applyLocalePrefix 重挂。 */
export function stripLocalePrefix(path: string): string {
  return stripLocalePathPrefix(path)
}

/**
 * 中性路径 + 语言码 → 该语言下的真实路径（prefix_except_default 的算术形式）。
 *
 * 为什么不用 @nuxtjs/i18n 的 localePath()：它按**路由名**解析传入的字符串，
 * 而详情页的 `/posts/{中文 slug}` 需要先被 vue-router 解码再匹配 dynamic 段，
 * SSR 期实测回过非字符串对象，直接把 asAbsolute 打进 `e.startsWith is not a function`
 * ——表现是文章详情页整页 500。本仓 i18n 没有配置 per-locale 自定义路径
 * （nuxt.config 的 i18n 块无 `routes`），"默认语言裸路径 + 其余挂 /code 前缀"
 * 就是策略的完整定义，纯字符串拼接既没有解析失败面，也省掉一次 router.resolve。
 *
 * 语言前缀只属于站内绝对路径：绝对 URL、协议相对 URL（//host）、页面内锚点一律
 * 原样透传。导航项 / 页脚链接 / 首页 CTA 的 to 都可能来自后台配置，给外链挂前缀
 * 会产出 `/enhttps://example.com` 这种死链。
 */
export function applyLocalePrefix(neutralPath: string, code: string): string {
  const input = neutralPath || ''
  // 站内绝对路径才挂语言前缀；`#top` 这类页面内锚点也走透传分支。
  if (!input.startsWith('/') || /^\/\//.test(input)) return input
  const p = stripLocalePrefix(input)
  if (!p) return p
  if (code === DEFAULT_LOCALE_CODE || !(NON_DEFAULT_LOCALE_CODES as readonly string[]).includes(code)) {
    return p
  }
  // 查询串/锚点必须留在末尾：/en/posts/x?page=2，不能拼成 /en?page=2/posts/x
  const queryIndex = p.search(/[?#]/)
  const pathname = queryIndex === -1 ? p : p.slice(0, queryIndex)
  const tail = queryIndex === -1 ? '' : p.slice(queryIndex)
  const prefixed = pathname === '/' ? '' : pathname
  return `/${code}${prefixed}${tail}`
}

export interface BreadcrumbItem {
  /** 面包屑层级显示名称 */
  name: string
  /** 绝对或相对 URL（首页传 `/`） */
  url: string
}

export interface ArticleJsonLdAuthor {
  name: string | { readonly value: string }
  url?: string | { readonly value?: string | undefined }
  avatar?: string | { readonly value?: string | undefined }
}

export interface ArticleJsonLdOptions {
  'slug': string | { readonly value: string }
  'title': string | { readonly value: string }
  'headline'?: string | { readonly value: string }
  /** 纯文本摘要（无 Markdown/HTML） */
  'description'?: string | { readonly value?: string | undefined }
  'cover'?: string | { readonly value?: string | undefined }
  /** 发布时间 ISO 字符串 */
  'publishedAt'?: string | { readonly value?: string | undefined }
  /** 最后修改时间 ISO 字符串 */
  'updatedAt'?: string | { readonly value?: string | undefined }
  'author'?: ArticleJsonLdAuthor
  /** 分类名或分类 URL */
  'category'?: string | { readonly value?: string | undefined }
  /**
   * 分类页的中性路径（如 `/categories/<slug>`，prefix_except_default 口径下内部挂语言前缀）。
   *
   * 面包屑里的分类一跳必须落在**真实路由** `pages/categories/[slug].vue` 上——
   * 而后端列表口的 `category` 是本地化名称（与 slug 不保证相等，seed 里
   * slug=technology 而 name=「技术」），单靠 name 拼 `/categories/<name>` 会产出 404 面包屑。
   * 详情页调用点传 slug 形态的这条；缺省时才退化为 `/categories/<category>` 拼接。
   */
  'categoryPath'?: string | { readonly value?: string | undefined }
  /** 关键词数组 */
  'keywords'?: string[] | { readonly value?: string[] | undefined }
  /** BlogPosting / Article / NewsArticle（默认 BlogPosting） */
  '@type'?: 'BlogPosting' | 'Article' | 'NewsArticle'
  /**
   * 结构化数据里 url / mainEntityOfPage 用的路径（中性形态，内部挂语言前缀）。
   *
   * 默认 `/posts/${slug}` ——那是文章详情页的形态。独立页（顶级 catchall `/xxx`
   * 与兼容口 `/page/xxx`）必须显式传自己的路径，否则 Article 的 mainEntityOfPage
   * 会指向一条并不存在的文章 URL，而同一页的 canonical 指向另一个地址：schema.org
   * 校验报 "URL does not match page"，Google 富媒体也不会认这条。
   * 传空串 = 明确要求不输出这块 JSON-LD（内容不存在的 404 分支用）。
   */
  'path'?: string | { readonly value?: string | undefined }
}

// ---------------------------------------------------------------------------
// 内部帮助
// ---------------------------------------------------------------------------

/**
 * 允许用请求 Host 兜底推导站点根的只有本机开发地址。
 * 生产必须显式配 SITE_URL / NUXT_PUBLIC_SITE_URL。
 */
const LOOPBACK_HOST_RE = /^(?:localhost|127\.0\.0\.1|\[::1\])(?::\d+)?$/

/** SSR 事件里三处可能藏着 Host 的容器（web 形态 / node 形态 / 原始对）。 */
export interface RequestHostShapes {
  webHeaders?: Headers | Record<string, unknown> | null
  nodeHeaders?: Record<string, unknown> | null
  rawHeaders?: string[] | null
}

/**
 * 从 SSR 事件的三种形态里取请求 Host。
 *
 * 为什么不直接用 Nuxt 的 useRequestHeaders：本仓的 Nitro 版本把路由器拿到的 event 包成
 * web 形态，`event.node.req.headers` 实测是**空对象**（同 `server/utils/purgeSecret.ts` 的坑），
 * `useRequestHeaders` 读的正是那个袋子，于是"仅回环地址才按 Host 兜底"的分支永远拿到空串。
 * 症状：本地开发（未配 NUXT_PUBLIC_SITE_URL）的 canonical / og:url / 分享链接渲染成相对路径，
 * 而客户端用 `window.location.origin` 算出绝对地址 —— 文章页每次加载都报 hydration mismatch，
 * 预渲染出来的分享链接把 `/posts/xxx` 这种相对地址递给第三方平台。
 */
export function pickRequestHost(shapes: RequestHostShapes): string {
  const web = shapes.webHeaders
  if (web) {
    if (typeof (web as Headers).get === 'function') {
      const v = (web as Headers).get('host')
      if (v) return v
    } else {
      const v = (web as Record<string, unknown>).host
      if (typeof v === 'string' && v) return v
    }
  }
  const nodeHost = shapes.nodeHeaders?.host
  if (typeof nodeHost === 'string' && nodeHost) return nodeHost
  const raw = shapes.rawHeaders
  if (Array.isArray(raw)) {
    for (let i = 0; i + 1 < raw.length; i += 2) {
      if (String(raw[i]).toLowerCase() === 'host') return String(raw[i + 1])
    }
  }
  return ''
}

function readSsrRequestHost(): string {
  const event = useRequestEvent() as
    | {
      req?: { headers?: Headers | Record<string, unknown> }
      node?: { req?: { headers?: Record<string, unknown>, rawHeaders?: string[] } }
    }
    | undefined
  if (!event) return ''
  return pickRequestHost({
    webHeaders: event.req?.headers ?? null,
    nodeHeaders: event.node?.req?.headers ?? null,
    rawHeaders: event.node?.req?.rawHeaders ?? null
  })
}

/** 只有回环 Host 才允许推导成站点根；其余（含 `localhost.evil.com` 这类前缀骗术）一律返回空串。 */
export function loopbackOriginFromHost(host: string): string {
  return LOOPBACK_HOST_RE.test(host) ? `http://${host}` : ''
}

export function usePublicSiteUrl(): Ref<string> {
  const cfg = useRuntimeConfig()
  // 客户端无 SITE_URL 时回退到当前 origin（避免空串导致 broken absolute URL）
  const site = cfg.public?.siteUrl as string | undefined
  // SSR 期没有 window。缺配置时**只**在回环地址上按请求 Host 兜底，让本地开发
  // 也能拿到绝对 canonical；生产环境不接受 Host 推导——公开页带 s-maxage 缓存，
  // 而 Nitro 的缓存键不含 Host，伪造一次 Host 就能把攻击者域名写成整站的
  // canonical / og:url / hreflang 并在 TTL 内投毒（同一口径见
  // server/routes/robots.txt.get.ts 与 server/utils/ssr.ts 的 resolvePublicSiteOrigin）。
  const ssrOrigin = (() => {
    if (!import.meta.server) return ''
    return loopbackOriginFromHost(readSsrRequestHost())
  })()
  return computed(() => {
    if (site && site.trim() !== '') return site.replace(/\/$/, '')
    if (import.meta.client && typeof window !== 'undefined') {
      return window.location.origin
    }
    return ssrOrigin
  })
}

function asAbsolute(path: string | undefined, siteUrl: string): string {
  // 出口闸门：opts.url 由 30 个页面各自传入（有的还是 ref/响应式包装），一旦传进来的是
  // 对象，`path.startsWith` 会抛 `e.startsWith is not a function`——而这段代码跑在 SSR 的
  // useSeo 里，异常直接掀掉整页（实测线上文章详情页四语全 500）。宁可少一条 canonical，
  // 也不能让一个 meta 字段决定页面存活。
  const p = typeof path === 'string' ? path : ''
  if (!p) return ''
  if (/^https?:\/\//i.test(p)) return p
  if (!siteUrl) return p // 缺失时退化为相对路径
  return p.startsWith('/') ? `${siteUrl}${p}` : `${siteUrl}/${p}`
}

/** 取任意 string | string[] | undefined 或响应式包装 { value: T } 的"裸值"。所有 Article 字段均可响应式。 */
function unrefVal<T extends string | string[] | undefined>(
  val: T | { readonly value?: T } | { value: T } | undefined
): T {
  if (val == null) return undefined as T
  const asObj = val as { value?: T }
  // 必须用 `in` 而不是 hasOwnProperty：Vue 3.5 的 computed() 返回 class 实例，
  // `value` 是**原型链上的 getter**，hasOwnProperty 看不到它，于是把整个 ComputedRef
  // 当裸值返回；下游 `applyLocalePrefix(对象)` 在 .startsWith 上抛 TypeError，
  // 而这段跑在 useHead 求值路径上 = 整页 500（实测 /zzznotexist 独立页口）。
  if (typeof asObj === 'object' && 'value' in asObj) {
    return (asObj.value as T) ?? (undefined as T)
  }
  return val as T
}

// SEO 描述出口的最后一道防线：剥掉短代码与 HTML 标签、压缩空白并封顶长度。
// 各页面理应在调用侧先裁成纯文本；这里兜住新页面直传渲染后 HTML 的回退。
// 入参可能是未解包的 ComputedRef（见 unrefVal 的原型链 getter 说明），
// 所以先手动解一层 ref 再校验类型，非字符串一律安全返回空。
const SEO_DESC_LIMIT = 200
function plainTextMeta(input: unknown): string {
  let value = input
  if (value != null && typeof value === 'object' && 'value' in value) {
    value = (value as { value: unknown }).value
  }
  if (typeof value !== 'string') return ''
  return value
    .replace(/\[\/?[A-Za-z_][\w-]*(?:[^\][]*)?\]/g, ' ')
    .replace(/<[^>]+>/g, ' ')
    .replace(/\s+/g, ' ')
    .trim()
    .slice(0, SEO_DESC_LIMIT)
}

// ---------------------------------------------------------------------------
// 1. 通用 Meta：title / description / og / twitter
// ---------------------------------------------------------------------------

/**
 * 自动 canonical 的查询串白名单：只有真正"另一张页"的参数才留在规范链接里。
 * /posts 的 search / category / sort 是同一份列表的视图变体，把它们写进 canonical
 * 等于向搜索引擎声明"每个筛选组合都是一个独立页面"——正是重复内容收录的成因。
 * page=1 不保留：第 1 页的规范链接就是裸路径。
 */
const CANONICAL_QUERY_KEYS = ['page']

function canonicalFromRoute(route: { path: string, query: Record<string, unknown> }): string {
  const kept: string[] = []
  for (const key of CANONICAL_QUERY_KEYS) {
    const value = route.query[key]
    const single = Array.isArray(value) ? value[0] : value
    if (typeof single === 'string' && single && single !== '1') {
      kept.push(`${key}=${encodeURIComponent(single)}`)
    }
  }
  return route.path + (kept.length ? `?${kept.join('&')}` : '')
}

export function useSeo(opts: SeoMetaOptions = {}) {
  const siteUrl = usePublicSiteUrl()
  const i18n = useI18n()
  const { locale } = i18n
  const site = useSite()
  const route = useRoute()
  // prefix_except_default 策略下：所有 canonical / hreflang 都从"中性路径"派生
  // （见 applyLocalePrefix 的说明——不走 localePath，详情页踩过解析坑）。
  // opts.url 缺省时回落到当前页路径（只保留分页参数，见 canonicalFromRoute）：
  // 分类/标签/归档/作者/留言板这些页过去不传 url，结果整页既没有 canonical
  // 也没有 hreflang，四语版本在爬虫眼里是四个互不相关的 URL。

  const siteName = computed(() => site.siteTitle.value || 'Rosetta')
  const defaultDescription = computed(
    () =>
      site.siteDescription.value
      || 'Rosetta · 穿越语言的边界 · Modern personal blog system'
  )

  const _title = computed(() =>
    typeof opts.title === 'string'
      ? opts.title
      : (opts.title?.value ?? '')
  )
  const _description = computed(() => {
    const raw
      = typeof opts.description === 'string'
        ? opts.description
        : (opts.description?.value ?? defaultDescription.value)
    return plainTextMeta(raw) || defaultDescription.value
  })
  const _image = computed(() =>
    asAbsolute(
      resolveShareImage(
        typeof opts.image === 'string'
          ? opts.image
          : (opts.image?.value ?? ''),
        String((site.seo.value as Record<string, unknown>).default_og_image || '')
      ),
      siteUrl.value
    )
  )
  const _imageAlt = computed(() =>
    typeof opts.imageAlt === 'string'
      ? opts.imageAlt
      : (opts.imageAlt?.value ?? '')
  )
  const _noindex = computed(() =>
    typeof opts.noindex === 'boolean'
      ? opts.noindex
      : Boolean((opts.noindex as { value?: boolean } | undefined)?.value)
  )
  const _twitterSite = computed(() => {
    const override
      = typeof opts.twitterSite === 'string'
        ? opts.twitterSite
        : (opts.twitterSite?.value ?? '')
    if (override) return override
    const handle = (site.seo.value as Record<string, unknown>)?.twitter_handle
    return typeof handle === 'string' ? handle : ''
  })
  /** canonical / hreflang / og:url 的共同入参：显式 opts.url 优先，否则当前页 fullPath */
  const _rawUrl = computed(() => {
    const raw = typeof opts.url === 'string'
      ? opts.url
      : (opts.url?.value ?? '')
    if (raw) return raw
    return canonicalFromRoute(route as unknown as { path: string, query: Record<string, unknown> })
  })
  const _url = computed(() => asAbsolute(_rawUrl.value, siteUrl.value))
  /**
   * canonical 走当前语言的实际 URL：先把入参剥成中性路径（/en/posts/x → /posts/x），
   * 再按 strategy 挂回当前语言的前缀，最后补站点根。
   * 已经是绝对 URL 的入参（http/https 开头）视作调用方接管，原样透传。
   */
  const canonicalUrl = computed(() => {
    const raw = _rawUrl.value
    if (!raw) return ''
    if (/^https?:\/\//i.test(raw)) return raw
    return asAbsolute(applyLocalePrefix(raw, locale.value), siteUrl.value)
  })
  /**
   * hreflang alternates：对 HREFLANG_MAP 里的每个 locale 生成一份"该 locale 下的
   * 本页面绝对 URL"。搜索引擎据此把中/英/日/繁中四份内容识别为同一页的语言变体。
   * 绝对 URL 入参（调用方接管）不再产出语言变体；noindex 页同样不产出——
   * Google 会忽略 noindex 页上的 hreflang，而这一组地址指向的其它语言变体若可收录，
   * 就等于用一条不该存在的边把它们拉进同一个集群（自相矛盾的规范信号）。
   */
  const localeAlternates = computed<Array<{ hreflang: string, href: string }>>(() => {
    const raw = _rawUrl.value
    if (_noindex.value) return []
    if (!raw || /^https?:\/\//i.test(raw)) return []
    const out: Array<{ hreflang: string, href: string }> = []
    for (const code of Object.keys(HREFLANG_MAP)) {
      const abs = asAbsolute(applyLocalePrefix(raw, code), siteUrl.value)
      if (abs) out.push({ hreflang: HREFLANG_MAP[code]!, href: abs })
    }
    // x-default：prefix_except_default 语义下 = 默认语言（zh）路径
    const zhPath = asAbsolute(applyLocalePrefix(raw, DEFAULT_LOCALE_CODE), siteUrl.value)
    if (zhPath) out.push({ hreflang: 'x-default', href: zhPath })
    return out
  })
  const _extraMeta = computed<Array<Record<string, string>>>(() => {
    if (!opts.extraMeta) return []
    if (Array.isArray(opts.extraMeta)) return opts.extraMeta
    return (opts.extraMeta as { readonly value?: Array<Record<string, string>> | undefined }).value ?? []
  })

  useHead(() => {
    const fullTitle = _title.value
      ? `${_title.value} · ${siteName.value}`
      : siteName.value

    const ogLocale = OG_LOCALE_MAP[locale.value] ?? locale.value
    const meta = [
      { name: 'description', content: _description.value },
      // OpenGraph
      { property: 'og:site_name', content: siteName.value },
      { property: 'og:type', content: opts.type ?? 'website' },
      { property: 'og:title', content: fullTitle },
      { property: 'og:description', content: _description.value },
      { property: 'og:locale', content: ogLocale },
      // Twitter
      { name: 'twitter:card', content: 'summary_large_image' },
      { name: 'twitter:title', content: fullTitle },
      { name: 'twitter:description', content: _description.value }
    ] as Array<Record<string, string>>

    // 其它三语 og:locale:alternate —— 社交分享爬虫据此判断站点多语言可用性
    for (const code of Object.keys(OG_LOCALE_MAP)) {
      if (code === locale.value) continue
      meta.push({ property: 'og:locale:alternate', content: OG_LOCALE_MAP[code] ?? code })
    }

    if (_image.value) {
      meta.push({ property: 'og:image', content: _image.value })
      meta.push({ name: 'twitter:image', content: _image.value })
      // https 页面补 secure_url（OG 协议里与 og:image 成对，Facebook 据此选缓存变体）；
      // 图片是相对路径时 asAbsolute 已拼过站点根，这里只判最终协议。
      if (/^https:\/\//i.test(_image.value)) {
        meta.push({ property: 'og:image:secure_url', content: _image.value })
      }
      // 尺寸提示只在图片 URL 自身声明了尺寸时可推导（本仓封面来自用户上传，无单源），
      // 所以宁缺毋滥：写一个猜出来的 1200×630 会让爬虫按错比例预留预览框。
      // alt 缺省回落站点名：分享卡上的图若无替代文本，读屏软件只会念出图片 URL。
      const imageAlt = _imageAlt.value || siteName.value
      meta.push({ property: 'og:image:alt', content: imageAlt })
      // Twitter Card 的 alt 是独立字段，缺了读屏软件在 X 的预览里拿不到描述。
      meta.push({ name: 'twitter:image:alt', content: imageAlt })
    }
    if (_url.value) {
      meta.push({ property: 'og:url', content: canonicalUrl.value || _url.value })
    }
    if (_twitterSite.value) {
      meta.push({ name: 'twitter:site', content: _twitterSite.value })
    }
    if (_noindex.value) {
      meta.push({ name: 'robots', content: NOINDEX_ROBOTS })
    } else {
      meta.push({ name: 'robots', content: 'index, follow, max-image-preview:large, max-snippet:-1, max-video-preview:-1' })
    }

    // 站点所有权验证：管理员在 后台 → 站点设置 → SEO 填一次即全站生效。
    const googleV = (site.seo.value as Record<string, unknown>).google_verification
    if (typeof googleV === 'string' && googleV) {
      meta.push({ name: 'google-site-verification', content: googleV })
    }
    const baiduV = (site.seo.value as Record<string, unknown>).baidu_verification
    if (typeof baiduV === 'string' && baiduV) {
      meta.push({ name: 'baidu-site-verification', content: baiduV })
    }

    if (_extraMeta.value && _extraMeta.value.length > 0) {
      meta.push(..._extraMeta.value)
    }

    // canonical：noindex 页不输出（搜索结果页 / 分页尾页自身 canonical 会诱使
    // 搜索引擎把候选页当"重复内容"合并掉，反而不利收录）。
    const link: Array<Record<string, string>> = []
    if (!_noindex.value && canonicalUrl.value) {
      link.push({ rel: 'canonical', href: canonicalUrl.value })
    }
    // hreflang alternates：让爬虫知道中英日韩四份内容互为语言变体。
    // noindex 页也跳过（避免搜索引擎把非索引页当作语言变体候选）。
    if (!_noindex.value) {
      for (const alt of localeAlternates.value) {
        link.push({ rel: 'alternate', hreflang: alt.hreflang, href: alt.href })
      }
    }

    // html lang 必须是 BCP-47（zh_Hant 的下划线形态会被解析器降级，且与本页
    // hreflang 输出的 zh-Hant 口径打架）——直接复用 HREFLANG_MAP 的值，不另建清单。
    const htmlLang = HREFLANG_MAP[locale.value] ?? locale.value

    // Nuxt useHead（@zhead/schema）对 meta 联合类型约束过严，使用 unknown 断
    // 言绕过；运行时实际结构与声明的字段（name/property + content）100% 匹配。
    const head = {
      title: fullTitle,
      htmlAttrs: { lang: htmlLang },
      meta,
      link
    }
    return head as unknown as never
  })
}

// ---------------------------------------------------------------------------
// 1.1 不可索引页闸门
// ---------------------------------------------------------------------------

/**
 * 登录 / 注册 / 找回密码 / 个人中心 / OOBE 这类"有 URL 但没有可收录内容"的页面
 * 必须自带 noindex。robots.txt 的 Disallow 挡不住收录：Google 抓不到页面就读不到
 * robots meta，反而会按已发现的 URL 生成"无摘要索引条目"。正确姿势是允许抓取、
 * 只禁止入索引，所以这里用 noindex, follow（保留站内链接权重流转）。
 *
 * 独立于 useSeo：这些页面是 ssr:false 的 SPA（见 routeRules 反选表），
 * 不能走 useSeo 的站点根推导（会读请求 Host），也不能引入主题副作用。
 *
 * ⚠️ 这里只保证 **hydration 后** 的 DOM 有这行 meta。ssr:false 路径的原始 HTML
 * 是一份不含任何页面 head 的空壳，不执行 JS 的抓取器读不到 noindex —— 那行 meta
 * 由 `server/utils/noindex-shell.ts` + Nitro 插件在服务端字节里补上，
 * 两边的路径清单由 `tests/unit/noindexShellMeta.spec.ts` 钉成同一份。
 */
export function useNoindexPage() {
  useHead(() => ({
    meta: [{ name: 'robots', content: NOINDEX_ROBOTS }]
  }))
}

// ---------------------------------------------------------------------------
// 2. WebSite JSON-LD（首页）
// ---------------------------------------------------------------------------

export function useWebsiteJsonLd() {
  const siteUrl = usePublicSiteUrl()
  const site = useSite()

  useHead(() => {
    const url = siteUrl.value || (import.meta.client ? window.location.origin : '')
    const siteName = site.siteTitle.value || 'Rosetta'
    const description
      = site.siteDescription.value
        || 'Rosetta · 穿越语言的边界 · Modern personal blog system'

    const payload = {
      '@context': 'https://schema.org',
      '@type': 'WebSite',
      'name': siteName,
      description,
      url,
      'potentialAction': {
        '@type': 'SearchAction',
        'target': `${url}/search?q={search_term_string}`,
        'query-input': 'required name=search_term_string'
      },
      'inLanguage': ['zh-CN', 'en-US', 'ja-JP', 'zh-Hant']
    }

    return {
      script: [
        {
          type: 'application/ld+json',
          key: 'jsonld-website',
          innerHTML: jsonLdStringify(payload)
        }
      ]
    }
  })
}

// ---------------------------------------------------------------------------
// 3. Article / BlogPosting JSON-LD（文章详情页，@graph 五实体）
// ---------------------------------------------------------------------------

/**
 * Safe ISO-8601 日期格式化 → 避免 unhead/SSR 因 "Invalid time value"
 * RangeError 整页崩溃返回 500（会把用户带到 error.vue 且 NuxtData 序列化损坏）。
 *
 * 触发条件：new Date(undefined/null/""/空字符串/非 ISO/空 i18n 回退)
 *   → Invalid Date 对象 → .toISOString() 抛 "Invalid time value"。
 *
 * 防御策略：
 * 1. falsy 输入 → 返回 undefined（schema 属性被 JSON-LD omit，可接受）。
 * 2. 构造后显式检查 Number.isNaN(getTime()) 捕获 Invalid Date。
 * 3. catch 兜底任何异常 → 回 undefined。
 */
function safeIsoDate(val: unknown): string | undefined {
  if (val === null || val === undefined || val === '') return undefined
  try {
    const d = new Date(val as string | number | Date)
    if (Number.isNaN(d.getTime())) return undefined
    return d.toISOString()
  } catch {
    return undefined
  }
}

/**
 * Deep-safe JSON serialization for JSON-LD payloads against Vue circular ref structures.
 *
 * Typical chain that produces the last error:
 *   posts/hot URL → matches pages/posts/[slug].vue (slug='hot' dynamic)
 *   → fetch post by slug='hot' returns 404
 *   → reactive computed chain on post.category / keywords might still be
 *     bound to the raw computed object (Ref wrapping ComputedRef wrapping Ref)
 *   → JSON.stringify(ComputedRefImpl) throws "Converting circular structure to JSON
 *     ... property 'dep' -> object with constructor 'Dep' ... closes the circle".
 *
 * Solution: custom JSON.stringify replacer that unwraps Ref-ish `.value` AND
 * safely drops any function / Map / WeakMap / cyclic back-ref that can't be serialized.
 */
function jsonLdStringify(value: unknown): string {
  const seen = new WeakSet<object>()
  const replacer = (_key: string, val: unknown): unknown => {
    // 1) Unwrap any Vue Ref / ComputedRef-like object: extract .value if present
    if (
      val != null
      && typeof val === 'object'
      && Object.prototype.hasOwnProperty.call(val, 'value')
      // Don't recurse into objects that are *supposed* to have `value` key (e.g.
      // schema.org 'PropertyValue'). Only unwrap if it looks like a Vue ref:
      // typeof ref.value matches the wrapped ref generic type and no other
      // schema-ish keys exist. The simplest safe heuristic: unwrap objects
      // that ALSO have `__v_isRef` = true (Vue's own marker), or have `dep`
      // (Vue reactivity internals) = a reactive Dep instance.
      && ((val as { __v_isRef?: unknown }).__v_isRef === true
        || Object.prototype.hasOwnProperty.call(val, 'dep')
        || Object.prototype.hasOwnProperty.call(val, '__v_isComputed')
        || Object.prototype.hasOwnProperty.call(val, 'effect'))
    ) {
      const inner = (val as { value: unknown }).value
      return replacer('', inner)
    }
    // 2) Handle primitives directly — always pass through
    if (val === null || val === undefined || typeof val !== 'object') return val
    // 3) Circular structure guard
    if (seen.has(val as object)) return undefined
    seen.add(val as object)
    // 4) Dates → ISO string (standard JSON replacer default but explicit here)
    if (val instanceof Date) return Number.isNaN(val.getTime()) ? undefined : val.toISOString()
    // 5) Arrays with element-by-element recursion (preserves order)
    if (Array.isArray(val)) {
      const out: unknown[] = []
      for (let i = 0; i < val.length; i++) out.push(replacer(String(i), val[i]))
      return out
    }
    // 6) Plain-like objects: iterate own keys, skip any function / non-serializable
    if (val.constructor === Object || Object.getPrototypeOf(val) === Object.prototype || val.constructor === undefined) {
      const out: Record<string, unknown> = {}
      for (const k of Object.keys(val as Record<string, unknown>)) {
        const v = (val as Record<string, unknown>)[k]
        if (typeof v === 'function' || v instanceof WeakMap || v instanceof WeakSet) continue
        out[k] = replacer(k, v)
      }
      return out
    }
    // 7) Map/Set/RegExp/Promise/other classes: can't reliably serialize → omit
    if (val instanceof Map || val instanceof Set || val instanceof RegExp || val instanceof Promise) return undefined
    // 8) Fallback for custom classes: try Object.keys copy, if fails return undefined
    try {
      return replacer('', { ...(val as Record<string, unknown>) })
    } catch {
      return undefined
    }
  }
  return JSON.stringify(value, replacer)
}

/** BlogPosting 封面 ImageObject 的声明尺寸。
 *  对齐 lib/post-cover.ts 的 `POST_COVER_DETAIL`（详情页头图 1200×800）——
 *  此处刻意不 import 那个 lib（本文件跑在 useHead 求值路径上，保持零额外依赖），
 *  那边改数值时这里必须同步。 */
const PRIMARY_IMAGE_WIDTH = 1200
const PRIMARY_IMAGE_HEIGHT = 800

/** Organization logo 的兜底图标：public/ 根下真实存在的 512×512 PNG
 *  （public/favicon/ 目录里只有 rosetta-256.png，不能用 /favicon/favicon-512x512.png）。 */
const ORG_LOGO_FALLBACK_PATH = '/favicon-512x512.png'
const ORG_LOGO_FALLBACK_SIZE = 512

/** 脏 URL（裸 `%`）会让 decodeURIComponent 抛 URIError，而这段跑在 useHead 求值
 *  路径上 = 整页 500（同一防御口径见 asAbsolute 的注释）。抛错即原样返回。 */
function safeDecodeURIComponent(value: string): string {
  try {
    return decodeURIComponent(value)
  } catch {
    return value
  }
}

/**
 * buildArticleJsonLdGraph 的入参——全部是调用方已经解包好的纯值。
 * URL 一律传"中性形态"（未挂语言前缀），前缀与站点根由本函数内部按
 * applyLocalePrefix + asAbsolute 单源口径拼装（根 AGENTS.md §2.3.3）。
 */
export interface ArticleGraphInput {
  /** 站点根（绝对、无尾斜杠）；空串时所有 URL 退化为相对形态 */
  base: string
  /** 当前语言码（zh/en/ja/zh_Hant） */
  locale: string
  /** BlogPosting / Article / NewsArticle */
  type: string
  /** 文章/页面的中性路径，如 /posts/hello */
  articlePath: string
  headline: string
  title: string
  description?: string | undefined
  keywords?: string | undefined
  articleSection?: string | undefined
  /** ISO 时间串（已过 safeIsoDate） */
  published?: string | undefined
  updated?: string | undefined
  /** 封面原始 URL（绝对或站内相对） */
  cover?: string | undefined
  /** author.url 为中性路径（如 /authors/lyn）或绝对 URL */
  author?: { name: string, url?: string | undefined, avatar?: string | undefined } | undefined
  /** 分类名或分类 URL */
  category?: string | undefined
  /** 分类页中性路径（/categories/<slug>），优先于按名称拼接 */
  categoryPath?: string | undefined
  siteName: string
  /** 站点 logo（site_logo 配置值，绝对或站内相对） */
  logo?: string | undefined
  /** 面包屑首项（首页）的本地化名称；调用方有 i18n 时必须传，缺省才回落 'Home' */
  homeLabel?: string | undefined
}

/**
 * 产出 @graph 五实体结构：BlogPosting（必留）+ Person / Organization /
 * ImageObject / BreadcrumbList（各自按数据存在与否整块省略）。
 *
 * 三条硬口径：
 * 1. 每个被引用的 @id 必须在 @graph 内有对应节点——"cover 缺失"这类分支
 *    必须让引用与节点**同时**消失，悬空 @id 比少一块实体更糟。
 * 2. 无法建 @id 时退化为内联对象（无 author.url → 内联 Person；
 *    无站点根 base → 内联 Organization publisher），保持旧行为不输出坏引用。
 * 3. dateModified 缺省回落后等于 datePublished（updated ?? published），不产生
 *    "修改早于发布"的负数时间差。
 *
 * 导出为纯函数（无 Nuxt 依赖）也是为了让 tests/unit/articleJsonLdGraph.spec.ts
 * 能脱离 Nuxt 上下文直接断言结构。
 */
export function buildArticleJsonLdGraph(input: ArticleGraphInput): Record<string, unknown> {
  const base = input.base || ''
  const locale = input.locale || DEFAULT_LOCALE_CODE

  // prefix_except_default：详情页 JSON-LD 的 url/mainEntityOfPage 必须落到
  // 当前语言的实际 URL（中文裸路径 /en/ja/zh_Hant 挂前缀），否则中英日
  // 三语页面在 schema.org 里会共享同一个 zh canonical，Google 富媒体测试报
  // "URL does not match page"。
  const articleUrl = asAbsolute(applyLocalePrefix(input.articlePath, locale), base)
  const primaryImageId = articleUrl ? `${articleUrl}#primaryimage` : ''
  const orgId = base ? `${base}#organization` : ''

  const blogPosting: Record<string, unknown> = {
    '@type': input.type,
    'headline': input.headline || input.title,
    'datePublished': input.published,
    // updated ?? published：保留旧口径，缺"最后修改"时两者相等而不是更早
    'dateModified': input.updated ?? input.published
  }
  if (articleUrl) {
    blogPosting['@id'] = `${articleUrl}#article`
    blogPosting.url = articleUrl
    blogPosting.mainEntityOfPage = { '@type': 'WebPage', '@id': articleUrl }
  }
  if (input.description) blogPosting.description = input.description
  if (input.keywords) blogPosting.keywords = input.keywords
  if (input.articleSection) blogPosting.articleSection = input.articleSection

  const nodes: Record<string, unknown>[] = [blogPosting]

  // ── ImageObject：仅当 cover 存在；引用与节点同进退 ──
  const coverUrl = input.cover ? asAbsolute(input.cover, base) : ''
  if (coverUrl && primaryImageId) {
    blogPosting.image = { '@id': primaryImageId }
    nodes.push({
      '@type': 'ImageObject',
      '@id': primaryImageId,
      'url': coverUrl,
      // 与 lib/post-cover.ts 的 POST_COVER_DETAIL（详情页头图声明尺寸）同一对数值
      'width': PRIMARY_IMAGE_WIDTH,
      'height': PRIMARY_IMAGE_HEIGHT,
      'caption': input.description || input.title
    })
  }

  // ── Person：仅当 author 存在；有资料页 URL 才建可引用的独立节点 ──
  const author = input.author
  if (author?.name) {
    const authorUrlAbs = author.url ? asAbsolute(applyLocalePrefix(author.url, locale), base) : ''
    const personId = authorUrlAbs ? `${authorUrlAbs}#person` : ''
    const avatarUrl = author.avatar ? asAbsolute(author.avatar, base) : ''
    if (personId) {
      blogPosting.author = { '@id': personId }
      const person: Record<string, unknown> = {
        '@type': 'Person',
        '@id': personId,
        'name': author.name,
        'url': authorUrlAbs
      }
      if (avatarUrl) person.image = { '@type': 'ImageObject', 'url': avatarUrl }
      nodes.push(person)
    } else {
      // 无 url：退化为内联对象（旧行为），不产出无法解析的 @id
      const inline: Record<string, unknown> = { '@type': 'Person', 'name': author.name }
      if (avatarUrl) inline.image = { '@type': 'ImageObject', 'url': avatarUrl }
      blogPosting.author = inline
    }
  }

  // ── Organization：publisher 引用 ↔ 节点 ──
  // name 必须与站点名一致（Google 会把 Article 的 publisher 与站点品牌对齐）；
  // 写死 'Rosetta' 会让实际站名不同的部署产出错的组织名。
  if (orgId) {
    blogPosting.publisher = { '@id': orgId }
    const configuredLogo = input.logo ? asAbsolute(input.logo, base) : ''
    const org: Record<string, unknown> = {
      '@type': 'Organization',
      '@id': orgId,
      'name': input.siteName || 'Rosetta',
      'url': base
    }
    if (configuredLogo) {
      // 后台上传的 logo 尺寸不定，不猜 width/height
      org.logo = { '@type': 'ImageObject', 'url': configuredLogo }
    } else {
      org.logo = {
        '@type': 'ImageObject',
        'url': `${base}${ORG_LOGO_FALLBACK_PATH}`,
        'width': ORG_LOGO_FALLBACK_SIZE,
        'height': ORG_LOGO_FALLBACK_SIZE
      }
    }
    nodes.push(org)
  } else {
    // 无站点根：@id 立不住，保留旧的内联 publisher（url 缺失即省略）
    blogPosting.publisher = { '@type': 'Organization', 'name': input.siteName || 'Rosetta' }
  }

  // ── BreadcrumbList：Home →（可选分类）→ 本篇；position 由 map 下标保证连续 ──
  const crumbs: Array<{ name: string, url: string }> = []
  const homeUrl = asAbsolute(applyLocalePrefix('/', locale), base)
  if (homeUrl) crumbs.push({ name: input.homeLabel || 'Home', url: homeUrl })
  const category = input.category
  if (category) {
    const isUrl = /^https?:\/\//i.test(category) || category.startsWith('/')
    // 面包屑的分类一跳必须落在真实路由 pages/categories/[slug].vue（按 slug 解析）。
    // 调用点传 categoryPath（slug 形态）时优先用它；纯名称才退化拼 /categories/<name>。
    const neutralPath = input.categoryPath
      ? input.categoryPath
      : isUrl
        ? category
        : `/categories/${encodeURIComponent(category)}`
    const catUrl = asAbsolute(applyLocalePrefix(neutralPath, locale), base)
    const catName = isUrl && !input.categoryPath
      ? safeDecodeURIComponent(
          category.split(/[?#]/)[0]!.replace(/\/+$/, '').split('/').pop() || category
        )
      : category
    if (catUrl) crumbs.push({ name: catName, url: catUrl })
  }
  if (articleUrl) crumbs.push({ name: input.headline || input.title, url: articleUrl })
  if (articleUrl && crumbs.length > 0) {
    nodes.push({
      '@type': 'BreadcrumbList',
      '@id': `${articleUrl}#breadcrumb`,
      'itemListElement': crumbs.map((crumb, idx) => ({
        '@type': 'ListItem',
        'position': idx + 1,
        'name': crumb.name,
        'item': crumb.url
      }))
    })
  }

  return {
    '@context': 'https://schema.org',
    '@graph': nodes
  }
}

export function useArticleJsonLd(opts: ArticleJsonLdOptions) {
  const siteUrl = usePublicSiteUrl()
  const { locale, t } = useI18n()
  const site = useSite()
  const siteNameForJsonLd = computed(() => site.siteTitle.value || 'Rosetta')

  // 全部字段都支持 Ref：用 computed 包装，由 useHead 闭包响应式追踪
  const _slug = computed(() => unrefVal(opts.slug))
  const _title = computed(() => unrefVal(opts.title))
  const _headline = computed(() => unrefVal(opts.headline))
  const _description = computed(() => plainTextMeta(unrefVal(opts.description)))
  const _cover = computed(() => unrefVal(opts.cover))
  const _publishedAt = computed(() => unrefVal(opts.publishedAt))
  const _updatedAt = computed(() => unrefVal(opts.updatedAt))
  const _category = computed(() => unrefVal(opts.category))
  const _categoryPath = computed(() => unrefVal(opts.categoryPath))
  const _keywords = computed(() => unrefVal(opts.keywords))
  const _type = opts['@type'] ?? 'BlogPosting'
  const _author = computed(() => {
    const a = opts.author
    if (!a) return undefined
    const name = unrefVal(a.name)
    if (!name) return undefined // author 姓名为空时不输出整块（避免 schema.org 校验警告）
    return {
      name,
      url: unrefVal(a.url),
      avatar: unrefVal(a.avatar)
    }
  })

  useHead(() => {
    const base = siteUrl.value || (import.meta.client ? window.location.origin : '')
    const slug = _slug.value
    // path 显式传了就以它为准（独立页形态）；空串是调用方的"别说这块"信号。
    const pathOverride = opts.path === undefined ? undefined : unrefVal(opts.path)
    if (pathOverride !== undefined) {
      if (!pathOverride) return { script: [] }
    } else if (!slug) {
      return { script: [] }
    }

    const articlePath = pathOverride ?? `/posts/${slug}`
    const published = safeIsoDate(_publishedAt.value)
    const updated = safeIsoDate(_updatedAt.value) ?? published
    const keywordsRaw = _keywords.value
    // unrefVal 返回类型被 T extends string | string[] | undefined 精确约束，
    // TS 不允许 string[] 分支上写 instanceof Set/Map（会 TS2358）。
    // 兜底：string[] → join；string → 原样；null/undefined/其余数字/未知对象 → String() 安全转或丢弃。
    const keywords
      = Array.isArray(keywordsRaw)
        ? keywordsRaw.join(', ')
        : typeof keywordsRaw === 'string'
          ? keywordsRaw
          : keywordsRaw == null
            ? undefined
            : String(keywordsRaw)

    const payload = buildArticleJsonLdGraph({
      base,
      locale: locale.value,
      type: _type,
      articlePath,
      headline: _headline.value || _title.value,
      title: _title.value,
      description: _description.value,
      keywords,
      articleSection: _category.value,
      published,
      updated,
      cover: _cover.value,
      author: _author.value,
      category: _category.value,
      categoryPath: _categoryPath.value,
      siteName: siteNameForJsonLd.value,
      // 面包屑首项跟着页面语言走：中文页给爬虫一个 "Home" 英文名等于让
      // BreadcrumbList 与访客在地址栏/搜索结果里看到的层级对不上。
      homeLabel: t('nav.home'),
      // Organization logo 的站点设置来源：basic.logo（/api/config 的 site_logo 键）
      logo: site.basic.value.logo || undefined
    })

    return {
      script: [
        {
          type: 'application/ld+json',
          key: `jsonld-article-${slug}`,
          innerHTML: jsonLdStringify(payload)
        }
      ]
    }
  })
}

// ---------------------------------------------------------------------------
// 4. BreadcrumbList JSON-LD（分类/标签/归档页的面包屑）
// ---------------------------------------------------------------------------

export function useBreadcrumbJsonLd(items: BreadcrumbItem[] | Ref<BreadcrumbItem[]>) {
  const siteUrl = usePublicSiteUrl()
  const { locale } = useI18n()

  useHead(() => {
    const list
      = Array.isArray(items) ? items : (items as Ref<BreadcrumbItem[]>).value
    const base = siteUrl.value || (import.meta.client ? window.location.origin : '')

    const payload = {
      '@context': 'https://schema.org',
      '@type': 'BreadcrumbList',
      'itemListElement': list
        .filter(i => i && i.name)
        .map((item, idx) => {
          // 与 useArticleJsonLd 同口径：面包屑里的相对路径必须挂上当前语言前缀
          // 才能与页面 URL 一致，绝对 URL 原样透传。
          const raw = item.url || ''
          const localized = /^https?:\/\//i.test(raw) || !raw
            ? raw
            : applyLocalePrefix(raw, locale.value)
          return {
            '@type': 'ListItem',
            'position': idx + 1,
            'name': item.name,
            'item': asAbsolute(localized, base)
          }
        })
    }

    return {
      script: [
        {
          type: 'application/ld+json',
          key: 'jsonld-breadcrumb',
          innerHTML: jsonLdStringify(payload)
        }
      ]
    }
  })
}
