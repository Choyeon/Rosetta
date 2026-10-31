/**
 * 「预计阅读 N 分钟」的单源契约（批次 #136 / #137 / #138）。
 *
 * 分钟数只有一个真源：`Post.reading_time` 持久化列（写入侧 `utils/reading_time.py` 算好）。
 * 这组断言各挡一次"两处数字打架"：
 * - 卡片读列、不复算：列表口 `defer(Post.content)`，正文根本不在载荷里，前端算不出来；
 *   而详情页曾自己按 380 字/分钟算，同一篇 卡片 6 分钟 / 正文页 4 分钟。
 * - 后端两套出口（列表投影 + `PostLocalizedResponse`）不得再各留一套公式：
 *   `_calculate_reading_time` 曾独立写 `len(content) // 500`，把 Markdown 标记当字数算。
 * - 闸门同源：后台「显示预估阅读时间」关掉后卡片与详情页一起收起，不能只关一半。
 * - 四语都有 `post.minRead`：缺语时 `t()` 回落键名字面量，卡片显示 "minRead"。
 */

import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { describe, expect, it } from 'vitest'

const root = resolve(__dirname, '..', '..', '..')
const card = readFileSync(resolve(root, 'frontend/components/PostCard.vue'), 'utf8')
const chip = readFileSync(resolve(root, 'frontend/components/PostReadingTime.vue'), 'utf8')
const detail = readFileSync(resolve(root, 'frontend/pages/posts/[slug].vue'), 'utf8')
const schemas = readFileSync(resolve(root, 'backend/schemas/__init__.py'), 'utf8')
const blogApi = readFileSync(resolve(root, 'backend/api/blog.py'), 'utf8')
const rankingApi = readFileSync(resolve(root, 'backend/api/ranking.py'), 'utf8')
const hotPage = readFileSync(resolve(root, 'frontend/pages/posts/hot.vue'), 'utf8')
const repoApi = readFileSync(resolve(root, 'backend/repositories/post.py'), 'utf8')
const blogReads = readFileSync(resolve(root, 'backend/schemas/blog_reads.py'), 'utf8')
const seriesApi = readFileSync(resolve(root, 'backend/api/post_series.py'), 'utf8')
const archiveIndex = readFileSync(resolve(root, 'frontend/pages/archive/index.vue'), 'utf8')
const archiveYear = readFileSync(resolve(root, 'frontend/pages/archive/[year]/index.vue'), 'utf8')
const archiveMonth = readFileSync(resolve(root, 'frontend/pages/archive/[year]/[month].vue'), 'utf8')
const seriesPage = readFileSync(resolve(root, 'frontend/pages/series/[slug].vue'), 'utf8')
const util = readFileSync(resolve(root, 'backend/utils/reading_time.py'), 'utf8')

describe('卡片侧（PostCard）', () => {
  it('三个变体各挂一次徽标，且只读 reading_time', () => {
    expect((card.match(/<PostReadingTime :post="post" \/>/g) ?? []).length).toBe(3)
    expect(card).toContain('import PostReadingTime from \'~~/components/PostReadingTime.vue\'')
    expect(chip).toContain('props.post.reading_time')
  })

  it('组件不自己估分钟数：正文不在列表载荷里（defer(content)）', () => {
    expect(chip).not.toMatch(/estimateReadingStats|content\.length/)
  })

  it('脏值/缺键整段不渲染，而不是显示 undefined 分钟', () => {
    expect(chip).toMatch(/Number\.isInteger\(n\) && n > 0/)
    expect(chip).toMatch(/const minutes = computed\(\(\) => \{[\s\S]*?\}\)/)
  })

  it('卡片与详情页读同一个后台闸门（reading.show_reading_time）', () => {
    expect(chip).toContain('site.reading.value.show_reading_time')
    expect(detail).toContain('site.reading.value.show_reading_time')
  })
})

describe('详情页侧（posts/[slug]）', () => {
  it('展示分钟数优先读后端持久化列', () => {
    expect(detail).toContain('Number(post.value?.reading_time)')
  })

  it('两个渲染点都按「有值才显示」收：锁定文章不报分钟数', () => {
    expect((detail.match(/showReadingTime && readingTime !== null/g) ?? []).length).toBe(2)
    expect(detail).toMatch(/if \(needPassword\.value\) return null/)
  })

  it('估算器只作兜底，不再是展示值的主源', () => {
    expect(detail).toMatch(
      /return readingStats\.value\.minutes > 0 \? readingStats\.value\.minutes : null/
    )
  })
})

describe('后端侧（两套出口同一条公式）', () => {
  it('PostLocalizedResponse 的读数委托给同一个函数，不另写公式', () => {
    const body = schemas.slice(schemas.indexOf('def _calculate_reading_time'))
    expect(body).toContain('from backend.utils.reading_time import calculate_reading_time')
    expect(body).toContain('calculate_reading_time(content or "")')
    // `// 500` 是漂移出来的第二套公式：把 Markdown 标记和半个词都算进字数
    expect(body).not.toMatch(/\/\/\s*500/)
  })

  it('列表与详情出口都取持久化列（缺失回落 1，不给 0 分钟）', () => {
    expect((blogApi.match(/reading_time=post\.reading_time or 1/g) ?? []).length)
      .toBeGreaterThanOrEqual(5)
    expect((blogApi.match(/"reading_time": post\.reading_time or 1/g) ?? []).length)
      .toBeGreaterThanOrEqual(1)
    expect(blogApi).toContain('_reading_time = post.reading_time')
  })

  it('唯一公式的兜底：空正文不得算出 0 分钟', () => {
    expect(util).toContain('return max(1, math.ceil(minutes))')
    expect(util).toContain('return 1')
  })
})

describe('周期榜族（/ranking/posts → 热榜页周期页签，批次 #137）', () => {
  // 这条口不经过 PostListItemLocalized：它自己拼 dict，热榜页再把条目补齐成 PostCard
  // 认得的形状。漏一处就是"综合页签有分钟数、日/周/月页签整排没有"（同批 #121 的媒体徽标）。
  it('后端条目带出持久化列并在文档模型声明默认值', () => {
    expect(rankingApi).toContain('"reading_time": p.reading_time or 1,')
    const body = rankingApi.slice(
      rankingApi.indexOf('class HotPostItemDoc('),
      rankingApi.indexOf('class HotPostsRankingResponseDoc(')
    )
    expect(body).toContain('reading_time: int = Field(1')
  })

  it('热榜页把分钟数透传给同一套卡片渲染，缺键按不显示处理', () => {
    expect(hotPage).toContain('reading_time?: number | null')
    expect(hotPage).toContain('reading_time: row.reading_time ?? null')
  })
})

describe('归档 / 系列族（批次 #138）', () => {
  // 归档三面（全量 / 年 / 月）与系列章节目录都是手搭投影：仓储点名取列、端点自己拼 dict。
  // 漏一处的表现和 #122 的媒体徽标一样——「列表卡片有分钟数，归档那一列整排没有」。
  it('仓储归档投影点名取列并落进同一行载荷', () => {
    expect(repoApi).toContain('Post.reading_time,')
    expect(repoApi).toContain('"reading_time": reading_time or 1,')
  })

  it('后端四条投影都带出该键，文档模型给默认值（旧缓存载荷不能整口 500）', () => {
    expect((blogApi.match(/"reading_time": post\.reading_time or 1/g) ?? []).length)
      .toBeGreaterThanOrEqual(2)
    expect(blogReads).toContain('reading_time: int = Field(1')
    expect(seriesApi).toContain('"reading_time": r.reading_time or 1,')
    expect(seriesApi).toContain('reading_time: int = Field(1')
  })

  it('四个渲染面各挂一次 chip，且项类型允许缺键', () => {
    for (const src of [archiveIndex, archiveYear, archiveMonth, seriesPage]) {
      expect((src.match(/<PostReadingTime :post=/g) ?? []).length).toBe(1)
      expect(src).toContain('import PostReadingTime from \'~~/components/PostReadingTime.vue\'')
      expect(src).toContain('reading_time?: number | null')
    }
  })
})

describe('四语文案', () => {
  it('卡片用到的 post.minRead / post.readingTime 四语齐全', () => {
    for (const locale of ['zh', 'en', 'ja', 'zh_Hant']) {
      const text = readFileSync(resolve(root, `frontend/i18n/locales/${locale}.json`), 'utf8')
      expect(text, locale).toContain('"minRead"')
      expect(text, locale).toContain('"readingTime"')
    }
  })

  it('zh_Hant 不得混进简体字形（卡片是访客直接读到的一面）', () => {
    const text = readFileSync(resolve(root, 'frontend/i18n/locales/zh_Hant.json'), 'utf8')
    expect(text).toContain('" 分鐘閱讀"')
    expect(text).not.toContain('阅读')
  })
})
