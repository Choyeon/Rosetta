/**
 * useSeo — 统一的 SEO composable
 *
 * 功能：
 * 1. useSeoMeta({ title, description, image, url, type }) — 统一设置
 *    <title>、<meta>、OpenGraph、Twitter Card，自动避免重复。
 * 2. useJsonLd(data) — 注入 <script type="application/ld+json"> 结构化数据。
 * 3. 预构建的 JSON-LD helper：
 *    - useArticleJsonLd(post)     — BlogPosting / Article（文章详情页）
 *    - useBreadcrumbJsonLd(items) — BreadcrumbList（分类/标签/归档页面包屑）
 *    - useWebsiteJsonLd()         — WebSite + SearchAction（首页）
 *
 * 所有 helper 都是 SSR 安全的：仅依赖 useHead（Nuxt 自动导入，在 SSR/SPA 两者下
 * 都正确）。不需要 import.meta.client 守卫。
 */

import { computed } from 'vue'

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
  /** 关键词数组 */
  'keywords'?: string[] | { readonly value?: string[] | undefined }
  /** BlogPosting / Article / NewsArticle（默认 BlogPosting） */
  '@type'?: 'BlogPosting' | 'Article' | 'NewsArticle'
}

// ---------------------------------------------------------------------------
// 内部帮助
// ---------------------------------------------------------------------------

function usePublicSiteUrl(): Ref<string> {
  const cfg = useRuntimeConfig()
  // 客户端无 SITE_URL 时回退到当前 origin（避免空串导致 broken absolute URL）
  const site = cfg.public?.siteUrl as string | undefined
  return computed(() => {
    if (site && site.trim() !== '') return site.replace(/\/$/, '')
    if (import.meta.client && typeof window !== 'undefined') {
      return window.location.origin
    }
    return ''
  })
}

function asAbsolute(path: string | undefined, siteUrl: string): string {
  if (!path) return ''
  if (/^https?:\/\//i.test(path)) return path
  if (!siteUrl) return path // 缺失时退化为相对路径
  return path.startsWith('/') ? `${siteUrl}${path}` : `${siteUrl}/${path}`
}

/** 取任意 string | string[] | undefined 或响应式包装 { value: T } 的"裸值"。所有 Article 字段均可响应式。 */
function unrefVal<T extends string | string[] | undefined>(
  val: T | { readonly value?: T } | { value: T } | undefined
): T {
  if (val == null) return undefined as T
  const asObj = val as { value?: T }
  if (typeof asObj === 'object' && Object.prototype.hasOwnProperty.call(asObj, 'value')) {
    return (asObj.value as T) ?? (undefined as T)
  }
  return val as T
}

// ---------------------------------------------------------------------------
// 1. 通用 Meta：title / description / og / twitter
// ---------------------------------------------------------------------------

export function useSeo(opts: SeoMetaOptions = {}) {
  const siteUrl = usePublicSiteUrl()
  const i18n = useI18n()
  const { locale } = i18n
  const site = useSite()

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
    return raw || defaultDescription.value
  })
  const _image = computed(() =>
    asAbsolute(
      typeof opts.image === 'string'
        ? opts.image
        : (opts.image?.value ?? ''),
      siteUrl.value
    )
  )
  const _url = computed(() =>
    asAbsolute(
      typeof opts.url === 'string'
        ? opts.url
        : (opts.url?.value ?? ''),
      siteUrl.value
    )
  )
  const _extraMeta = computed<Array<Record<string, string>>>(() => {
    if (!opts.extraMeta) return []
    if (Array.isArray(opts.extraMeta)) return opts.extraMeta
    return (opts.extraMeta as { readonly value?: Array<Record<string, string>> | undefined }).value ?? []
  })

  useHead(() => {
    const fullTitle = _title.value
      ? `${_title.value} · ${siteName.value}`
      : siteName.value

    const meta = [
      { name: 'description', content: _description.value },
      // OpenGraph
      { property: 'og:site_name', content: siteName.value },
      { property: 'og:type', content: opts.type ?? 'website' },
      { property: 'og:title', content: fullTitle },
      { property: 'og:description', content: _description.value },
      { property: 'og:locale', content: locale.value },
      // Twitter
      { name: 'twitter:card', content: 'summary_large_image' },
      { name: 'twitter:title', content: fullTitle },
      { name: 'twitter:description', content: _description.value }
    ] as Array<Record<string, string>>

    if (_image.value) {
      meta.push({ property: 'og:image', content: _image.value })
      meta.push({ name: 'twitter:image', content: _image.value })
    }
    if (_url.value) {
      meta.push({ property: 'og:url', content: _url.value })
    }
    if (_extraMeta.value && _extraMeta.value.length > 0) {
      meta.push(..._extraMeta.value)
    }

    // Nuxt useHead（@zhead/schema）对 meta 联合类型约束过严，使用 unknown 断
    // 言绕过；运行时实际结构与声明的字段（name/property + content）100% 匹配。
    const head = {
      title: fullTitle,
      htmlAttrs: { lang: locale.value },
      meta
    }
    return head as unknown as never
  })
}

// ---------------------------------------------------------------------------
// 2. 通用 JSON-LD 注入（任何 schema.org 类型）
// ---------------------------------------------------------------------------

export function useJsonLd<T = unknown>(data: T | Ref<T>) {
  useHead(() => {
    const raw
      = data && typeof (data as Ref).value !== 'undefined'
        ? (data as Ref<T>).value
        : (data as T)
    return {
      script: [
        {
          type: 'application/ld+json',
          innerHTML: JSON.stringify(raw),
          // 阻止 SSR/客户端 hydration 冲突：同一页多次调用时通过 hid 去重
          hid: `jsonld-${stableHash(JSON.stringify(raw))}`
        }
      ]
    }
  })
}

// ---------------------------------------------------------------------------
// 3. WebSite JSON-LD（首页）
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
          hid: 'jsonld-website',
          innerHTML: JSON.stringify(payload)
        }
      ]
    }
  })
}

// ---------------------------------------------------------------------------
// 4. Article / BlogPosting JSON-LD（文章详情页）
// ---------------------------------------------------------------------------

export function useArticleJsonLd(opts: ArticleJsonLdOptions) {
  const siteUrl = usePublicSiteUrl()

  // 全部字段都支持 Ref：用 computed 包装，由 useHead 闭包响应式追踪
  const _slug = computed(() => unrefVal(opts.slug))
  const _title = computed(() => unrefVal(opts.title))
  const _headline = computed(() => unrefVal(opts.headline))
  const _description = computed(() => unrefVal(opts.description))
  const _cover = computed(() => unrefVal(opts.cover))
  const _publishedAt = computed(() => unrefVal(opts.publishedAt))
  const _updatedAt = computed(() => unrefVal(opts.updatedAt))
  const _category = computed(() => unrefVal(opts.category))
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
    if (!slug) return { script: [] }

    const articleUrl = asAbsolute(`/posts/${slug}`, base)
    const cover = _cover.value ? asAbsolute(_cover.value, base) : undefined
    const published = _publishedAt.value
      ? new Date(_publishedAt.value).toISOString()
      : undefined
    const updated = _updatedAt.value
      ? new Date(_updatedAt.value).toISOString()
      : published
    const keywords = _keywords.value?.join(', ')

    const payload: Record<string, unknown> = {
      '@context': 'https://schema.org',
      '@type': _type,
      'headline': _headline.value || _title.value,
      'mainEntityOfPage': {
        '@type': 'WebPage',
        '@id': articleUrl
      },
      'url': articleUrl,
      'datePublished': published,
      'dateModified': updated,
      keywords,
      'articleSection': _category.value
    }

    if (_description.value) {
      payload.description = _description.value
    }
    if (cover) {
      payload.image = { '@type': 'ImageObject', 'url': cover }
    }
    const author = _author.value
    if (author) {
      payload.author = {
        '@type': 'Person',
        'name': author.name,
        ...(author.url ? { url: author.url } : {}),
        ...(author.avatar
          ? { image: { '@type': 'ImageObject', 'url': asAbsolute(author.avatar, base) } }
          : {})
      }
    }
    payload.publisher = {
      '@type': 'Organization',
      'name': 'Rosetta',
      'url': base
    }

    return {
      script: [
        {
          type: 'application/ld+json',
          hid: `jsonld-article-${slug}`,
          innerHTML: JSON.stringify(payload)
        }
      ]
    }
  })
}

// ---------------------------------------------------------------------------
// 5. BreadcrumbList JSON-LD（分类/标签/归档页的面包屑）
// ---------------------------------------------------------------------------

export function useBreadcrumbJsonLd(items: BreadcrumbItem[] | Ref<BreadcrumbItem[]>) {
  const siteUrl = usePublicSiteUrl()

  useHead(() => {
    const list
      = Array.isArray(items) ? items : (items as Ref<BreadcrumbItem[]>).value
    const base = siteUrl.value || (import.meta.client ? window.location.origin : '')

    const payload = {
      '@context': 'https://schema.org',
      '@type': 'BreadcrumbList',
      'itemListElement': list
        .filter(i => i && i.name)
        .map((item, idx) => ({
          '@type': 'ListItem',
          'position': idx + 1,
          'name': item.name,
          'item': asAbsolute(item.url, base)
        }))
    }

    return {
      script: [
        {
          type: 'application/ld+json',
          hid: 'jsonld-breadcrumb',
          innerHTML: JSON.stringify(payload)
        }
      ]
    }
  })
}

// ---------------------------------------------------------------------------
// 工具：稳定的短 hash（用于 JSON-LD hid 去重，避免每次渲染生成随机值引发 mismatch）
// ---------------------------------------------------------------------------

function stableHash(input: string): string {
  let h = 2166136261 >>> 0
  for (let i = 0; i < input.length; i++) {
    h ^= input.charCodeAt(i)
    h = Math.imul(h, 16777619)
  }
  return `fnv-${(h >>> 0).toString(36)}`
}
