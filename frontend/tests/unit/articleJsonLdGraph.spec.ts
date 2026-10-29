/**
 * 文章页 JSON-LD @graph 五实体契约（blog-schema 口径）。
 *
 * 断言对象是 useSeo.ts 导出的纯函数 buildArticleJsonLdGraph（不依赖 Nuxt 上下文，
 * 与 seoLocaleUrl.spec.ts 同法直接 import 模块），外加两条接线静态断言：
 * 三个 JSON-LD 全部用 unhead 的 `key` 认领 SSR 标签、详情页不得再另挂一份独立 BreadcrumbList
 * （@graph 里已内嵌，重复声明会让爬虫拿到两套面包屑）。
 *
 * 核心红线是"空值防御"：
 * - 被引用的 @id 必须在 @graph 内有对应节点（cover 缺失 → 引用与节点同时消失）；
 * - author 无资料页 URL → 内联 Person；无 author → 整个字段省略；
 * - 无站点根 → publisher 退化为内联，绝不产出 {@id: ''} 这类坏引用；
 * - breadcrumb position 从 1 连续、item 全部绝对 URL。
 */
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { describe, expect, it } from 'vitest'
import { buildArticleJsonLdGraph } from '../../composables/useSeo'
import type { ArticleGraphInput } from '../../composables/useSeo'

const ROOT = resolve(__dirname, '..', '..')
const BASE = 'https://blog.example.com'

function input(overrides: Partial<ArticleGraphInput> = {}): ArticleGraphInput {
  return {
    base: BASE,
    locale: 'zh',
    type: 'BlogPosting',
    articlePath: '/posts/hello-world',
    headline: '你好，世界',
    title: '你好，世界',
    description: '一篇测试文章的摘要。',
    keywords: 'a, b',
    articleSection: '技术',
    published: '2026-01-01T00:00:00.000Z',
    updated: '2026-02-01T00:00:00.000Z',
    cover: '/uploads/cover.png',
    author: { name: 'Lyn', url: '/authors/lyn', avatar: '/uploads/avatar.png' },
    category: '技术',
    categoryPath: '/categories/technology',
    siteName: 'Choyeon 的小站',
    logo: '',
    ...overrides
  }
}

interface Node {
  '@type'?: string
  '@id'?: string
  [k: string]: unknown
}

function graphOf(payload: Record<string, unknown>): Node[] {
  expect(Array.isArray(payload['@graph']), 'payload 必须输出 @graph 数组').toBe(true)
  return payload['@graph'] as Node[]
}

function nodeOf(graph: Node[], type: string): Node | undefined {
  return graph.find(n => n['@type'] === type)
}

/** 收集 payload 里所有 {"@id": X} 形态的引用（悬空检查用）。 */
function collectIdRefs(value: unknown, refs: Array<string>): void {
  if (Array.isArray(value)) {
    for (const item of value) collectIdRefs(item, refs)
    return
  }
  if (value && typeof value === 'object') {
    const obj = value as Record<string, unknown>
    if (typeof obj['@id'] === 'string' && Object.keys(obj).length === 1) refs.push(obj['@id'])
    for (const v of Object.values(obj)) collectIdRefs(v, refs)
  }
}

describe('buildArticleJsonLdGraph：@graph 五实体结构', () => {
  const payload = buildArticleJsonLdGraph(input())
  const graph = graphOf(payload)
  const blog = nodeOf(graph, 'BlogPosting')!
  const articleUrl = `${BASE}/posts/hello-world`

  it('BlogPosting 必留且带可解析的 @id / mainEntityOfPage', () => {
    expect(blog).toBeTruthy()
    expect(blog['@id']).toBe(`${articleUrl}#article`)
    expect(blog.url).toBe(articleUrl)
    expect(blog.mainEntityOfPage).toEqual({ '@type': 'WebPage', '@id': articleUrl })
    expect(blog.datePublished).toBe('2026-01-01T00:00:00.000Z')
    expect(blog.dateModified).toBe('2026-02-01T00:00:00.000Z')
  })

  it('author 是 {@id} 引用，且 @graph 里有对应 Person 节点（URL 全绝对、挂语言前缀）', () => {
    const person = nodeOf(graph, 'Person')
    expect(person).toBeTruthy()
    expect(blog.author).toEqual({ '@id': `${BASE}/authors/lyn#person` })
    expect(person!['@id']).toBe(`${BASE}/authors/lyn#person`)
    expect(person!.name).toBe('Lyn')
    expect(person!.url).toBe(`${BASE}/authors/lyn`)
  })

  it('publisher 的 @id 引用被 Organization 节点解析，logo 缺配置时落到真实存在的 favicon 文件', () => {
    const org = nodeOf(graph, 'Organization')
    expect(blog.publisher).toEqual({ '@id': `${BASE}#organization` })
    expect(org!['@id']).toBe(`${BASE}#organization`)
    expect(org!.name).toBe('Choyeon 的小站')
    expect(org!.url).toBe(BASE)
    const logo = org!.logo as Record<string, unknown>
    expect(logo.url).toBe(`${BASE}/favicon-512x512.png`)
    expect(logo.width).toBe(512)
    expect(logo.height).toBe(512)
  })

  it('ImageObject 带 1200×800（对齐 POST_COVER_DETAIL）与 caption，BlogPosting.image 是引用', () => {
    const image = nodeOf(graph, 'ImageObject')
    // author avatar 也是 ImageObject，取 @id 为主图那条
    const primary = graph.find(n => n['@id'] === `${articleUrl}#primaryimage`)!
    expect(primary).toBeTruthy()
    expect(image).toBeTruthy()
    expect(primary.width).toBe(1200)
    expect(primary.height).toBe(800)
    expect(primary.url).toBe(`${BASE}/uploads/cover.png`)
    expect(primary.caption).toBe('一篇测试文章的摘要。')
    expect(blog.image).toEqual({ '@id': `${articleUrl}#primaryimage` })
  })

  it('BreadcrumbList：Home → 分类（走 categoryPath 的真实路由）→ 本篇，position 从 1 连续且全绝对 URL', () => {
    const crumb = nodeOf(graph, 'BreadcrumbList')!
    expect(crumb['@id']).toBe(`${articleUrl}#breadcrumb`)
    const items = crumb.itemListElement as Node[]
    expect(items.map(i => i.position)).toEqual([1, 2, 3])
    expect(items.map(i => i.item)).toEqual([
      `${BASE}/`,
      `${BASE}/categories/technology`,
      articleUrl
    ])
    for (const item of items) {
      expect(String(item.item)).toMatch(/^https?:\/\//)
    }
    expect(items[1]!.name).toBe('技术')
  })

  it('英文页：@graph 里每个站内 URL 都挂 /en 前缀（prefix_except_default 单源口径）', () => {
    const en = graphOf(buildArticleJsonLdGraph(input({ locale: 'en' })))
    const enBlog = nodeOf(en, 'BlogPosting')!
    expect(enBlog.url).toBe(`${BASE}/en/posts/hello-world`)
    const items = nodeOf(en, 'BreadcrumbList')!.itemListElement as Node[]
    expect(items[0]!.item).toBe(`${BASE}/en`)
    expect(items[1]!.item).toBe(`${BASE}/en/categories/technology`)
    expect(items[2]!.item).toBe(`${BASE}/en/posts/hello-world`)
    expect(nodeOf(en, 'Person')!['@id']).toBe(`${BASE}/en/authors/lyn#person`)
  })
})

describe('buildArticleJsonLdGraph：空值防御（引用与节点同进退）', () => {
  it('cover 缺失：primaryimage 节点与 BlogPosting.image 引用同时消失，不留悬空 @id', () => {
    const payload = buildArticleJsonLdGraph(input({ cover: undefined }))
    const raw = JSON.stringify(payload)
    expect(raw).not.toContain('primaryimage')
    const graph = graphOf(payload)
    expect(nodeOf(graph, 'ImageObject')).toBeUndefined()
    expect('image' in nodeOf(graph, 'BlogPosting')!).toBe(false)
  })

  it('无 author.url：退化为内联 Person（保持旧行为），不产出独立节点或坏引用', () => {
    const payload = buildArticleJsonLdGraph(input({ author: { name: 'Lyn', avatar: '/uploads/a.png' } }))
    const graph = graphOf(payload)
    const blog = nodeOf(graph, 'BlogPosting')!
    expect(blog.author).toMatchObject({ '@type': 'Person', 'name': 'Lyn' })
    expect((blog.author as Node)['@id']).toBeUndefined()
    expect(nodeOf(graph, 'Person')).toBeUndefined()
  })

  it('无 author：BlogPosting.author 整个字段省略', () => {
    const payload = buildArticleJsonLdGraph(input({ author: undefined }))
    const blog = nodeOf(graphOf(payload), 'BlogPosting')!
    expect('author' in blog).toBe(false)
  })

  it('无站点根：publisher 内联且不带空 @id，Organization 节点不产出', () => {
    const payload = buildArticleJsonLdGraph(input({ base: '' }))
    const raw = JSON.stringify(payload)
    expect(raw).not.toContain('"@id":""')
    const graph = graphOf(payload)
    expect(nodeOf(graph, 'Organization')).toBeUndefined()
    expect(nodeOf(graph, 'BlogPosting')!.publisher).toMatchObject({ '@type': 'Organization' })
  })

  it('无分类：面包屑只剩 Home → 本篇，position 仍从 1 连续', () => {
    const payload = buildArticleJsonLdGraph(input({ category: undefined, categoryPath: undefined }))
    const items = nodeOf(graphOf(payload), 'BreadcrumbList')!.itemListElement as Node[]
    expect(items.map(i => i.position)).toEqual([1, 2])
  })

  it('分类只有名称（无 categoryPath）：退化为 /categories/<name> 拼接并做 URL 编码', () => {
    const payload = buildArticleJsonLdGraph(input({ categoryPath: undefined, category: '技术' }))
    const items = nodeOf(graphOf(payload), 'BreadcrumbList')!.itemListElement as Node[]
    expect(items[1]!.item).toBe(`${BASE}/categories/${encodeURIComponent('技术')}`)
  })

  it('dateModified 缺省回落 datePublished，永不早于发布时间', () => {
    const payload = buildArticleJsonLdGraph(input({ updated: undefined }))
    const blog = nodeOf(graphOf(payload), 'BlogPosting')!
    expect(blog.dateModified).toBe(blog.datePublished)
  })

  it('所有 {@id} 引用都能在 @graph 内解析（全结构扫描）', () => {
    const payload = buildArticleJsonLdGraph(input())
    const graph = graphOf(payload)
    const declared = new Set(graph.map(n => n['@id']).filter(Boolean))
    const refs: string[] = []
    collectIdRefs(payload, refs)
    expect(refs.length).toBeGreaterThan(0)
    for (const ref of refs) {
      expect(declared.has(ref), `悬空 @id 引用：${ref}`).toBe(true)
    }
  })
})

describe('useHead 接线与详情页调用点（静态）', () => {
  const seo = readFileSync(resolve(ROOT, 'composables/useSeo.ts'), 'utf-8')

  it('JSON-LD 用 unhead 的 key 认领 SSR 标签（hid 是 Vue Meta 遗产，会导致 hydration 后再插一份）', () => {
    expect(seo).toContain('key: `jsonld-article-${slug}`')
    expect(seo).not.toMatch(/\bhid:/)
    expect(seo).toContain('buildArticleJsonLdGraph({')
  })

  it('详情页不再另调 useBreadcrumbJsonLd（BreadcrumbList 已由 @graph 内嵌）', () => {
    const page = readFileSync(resolve(ROOT, 'pages/posts/[slug].vue'), 'utf-8')
    expect(page).not.toContain('useBreadcrumbJsonLd')
    // 详情页把 slug 形态的分类路径交给了 JSON-LD（面包屑落在真实路由上）
    expect(page).toContain('categoryPath')
  })
})

describe('BreadcrumbList 首项本地化', () => {
  function crumbNames(payload: Record<string, unknown>): string[] {
    const list = graphOf(payload).find(n => n['@type'] === 'BreadcrumbList')
    expect(list, '@graph 必须有 BreadcrumbList').toBeTruthy()
    return (list!['itemListElement'] as Array<{ name: string }>).map(i => i.name)
  }

  it('调用方给了 homeLabel 就用它，缺省才回落 Home', () => {
    expect(crumbNames(buildArticleJsonLdGraph(input({ homeLabel: '首页' })))[0]).toBe('首页')
    expect(crumbNames(buildArticleJsonLdGraph(input()))[0]).toBe('Home')
  })

  it('useArticleJsonLd 把当前语言的 nav.home 交给 homeLabel', () => {
    const seo = readFileSync(resolve(ROOT, 'composables/useSeo.ts'), 'utf-8')
    expect(seo).toMatch(/homeLabel: t\(['"]nav\.home['"]\)/)
  })
})
