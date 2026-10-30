/**
 * 文章详情页「所属系列」卡片的接线守卫（批次 #74）。
 *
 * 缺口形状：公开页 `/series` 与 `/series/{slug}` 早就存在，sitemap 也投递了它们，
 * 但**全站没有任何指向 `/series/**` 的 href** —— `pages/posts/[slug].vue` 连 `series`
 * 这个字样都没有。`footerEntryPoints.spec.ts` 的 allowlist 写着「入口在文章详情页的系列卡片」，
 * 而那张卡片从未存在，于是这条注释只是把一个孤儿页登记成了"有入口"。
 *
 * 本批补的是「写口 → 存储 → 响应模型 → 消费方」四段里的后两段（前两段一直在）：
 * `GET /api/blog/posts/{slug}` 输出 series 简报，详情页渲染一张指向系列页的卡片。
 *
 * 钉住的口径：
 * 1. 卡片只在后端给了 series 时渲染（系列停用时后端回 null，正好对上系列页的 404）；
 * 2. 链接必须走 `localeHref`——SSR 的 href 是爬虫唯一的链接图，裸 `/series/x` 会把
 *    英文/日文页的权重全推给默认语言版本（AGENTS §2.3.3 第 2 条）；
 * 3. 序位与章数和系列页同一份查询口径，否则「第 N 章」和系列目录对不上；
 * 4. 系列停用/无系列时后端不得输出简报（把访客引向一张 404 比没有入口更糟）。
 */
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { describe, expect, it } from 'vitest'

const ROOT = resolve(__dirname, '../..')
const LOCALES = ['zh', 'en', 'ja', 'zh_Hant'] as const

function readSource(rel: string): string {
  return readFileSync(resolve(ROOT, rel), 'utf8').replace(/\r\n/g, '\n')
}

const page = readSource('pages/posts/[slug].vue')
const schemas = readSource('../backend/schemas/__init__.py')
const blogApi = readSource('../backend/api/blog.py')

describe('文章详情页 · 所属系列卡片', () => {
  it('卡片只在后端给了 series 时渲染（停用系列后端回 null，正好对上系列页 404）', () => {
    expect(page).toMatch(/<NuxtLink\s+v-if="seriesInfo"/)
    expect(page).toMatch(/const seriesInfo = computed\(\(\) => \{[\s\S]{0,160}s && s\.slug && s\.title/)
  })

  it('链接走 localeHref 且指向 /series/<slug>（SSR href 是爬虫唯一的链接图）', () => {
    expect(page).toContain(':to="localeHref(`/series/${seriesInfo.slug}`)"')
    // 裸站内href会让四语页面共用一条默认语言链接
    expect(page).not.toMatch(/(?<!localeHref\()\s+:?to="\/series/)
  })

  it('章数与序位来自后端，前端不再自己算一遍', () => {
    expect(page).toMatch(/t\('series\.chapterPosition', \{ n: seriesInfo\.position, total: seriesInfo\.post_count \}\)/)
    expect(page).toMatch(/t\('series\.postsCount', \{ n: seriesInfo\.post_count \}\)/)
    // 作者预览草稿时 position 为 null：不得编一个 0 或 1 当章号
    expect(page).toMatch(/<span v-if="seriesInfo\.position">/)
  })

  it('详情响应模型带 series，写入口把简报真的塞进响应', () => {
    expect(schemas).toMatch(/class PostSeriesBrief\(BaseModel\)/)
    expect(schemas).toMatch(/series: PostSeriesBrief \| None = None/)
    expect(blogApi).toContain('series=series_brief')
    expect(blogApi).toContain('series_brief = None')
  })

  it('简报与系列页同一份排序口径 + 同一份可见性谓词', () => {
    const start = blogApi.indexOf('series_brief = None')
    expect(start).toBeGreaterThan(-1)
    const block = blogApi.slice(start, start + 1600)
    expect(block).toContain('publicly_listable_posts()')
    expect(block).toMatch(/\.order_by\(Post\.series_order\.asc\(\), Post\.published_at\.desc\(\)\)/)
    // 停用系列不输出，避免卡片指向 404
    expect(block).toMatch(/if series_row and series_row\.is_active/)
  })

  it('四语的卡片文案齐备（缺 key 会渲染成裸 key）', () => {
    for (const code of LOCALES) {
      const dict = JSON.parse(readFileSync(resolve(ROOT, `i18n/locales/${code}.json`), 'utf8')) as Record<
        string,
        Record<string, unknown>
      >
      for (const key of ['inSeries', 'chapterPosition', 'viewSeries'] as const) {
        expect(dict.series?.[key], `${code}.series.${key} 缺失`).toBeTruthy()
      }
      // 两个占位符都要在：少一个会让 t() 把 {total} 原样打到页面上
      expect(String(dict.series?.chapterPosition)).toContain('{n}')
      expect(String(dict.series?.chapterPosition)).toContain('{total}')
    }
  })
})
