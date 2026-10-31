/**
 * 标签目录页的关键词过滤 + 排序（批次 #217）。
 *
 * 三条约束：
 *  1. 过滤与排序都在本地做（标签总量是几十条，不为筛选再打一次接口）：
 *     `syncUrl` 里不得出现 `refresh()`，否则每次输入都发一轮请求。
 *  2. 状态落在 ?q= / ?sort= 上：SSR 首屏按 query 过滤，分享链接打开就是同一视图；
 *     改条件走 replace，不在历史里堆一串筛选态。
 *  3. 过滤为空时工具栏必须还在（否则用户没有入口改回条件），空态给「清除筛选」。
 */

import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { describe, expect, it } from 'vitest'

const ROOT = resolve(__dirname, '..', '..')
const src = readFileSync(resolve(ROOT, 'pages/tags/index.vue'), 'utf-8')
const locales = ['zh', 'en', 'ja', 'zh_Hant'] as const

/** 取某个 `const x = …` 到首个顶格 `}` 的片段（函数 / 常量块通用）。 */
const block = (name: string): string =>
  src.match(new RegExp(`const ${name} = [\\s\\S]*?\\n\\}`))?.[0] ?? ''

describe('标签页过滤状态', () => {
  it('初始条件从地址栏读，sort 只认白名单', () => {
    expect(src).toContain('const filterQuery = ref(')
    expect(src).toContain('route.query.q')
    expect(src).toContain('route.query.sort === \'name\' ? \'name\' : \'count\'')
  })

  it('过滤只看本地化名称与 slug，忽略大小写', () => {
    const fn = block('visibleTags')
    expect(fn).toContain('toLowerCase()')
    expect(fn).toContain('tagName(tag)')
    expect(fn).toContain('String(tag.slug)')
  })

  it('改条件同步到地址栏且不重新请求', () => {
    const fn = block('syncUrl')
    expect(fn).toContain('router.replace({ query })')
    expect(fn).toContain('query.q = kw')
    expect(fn).toContain('query.sort = sortMode.value')
    expect(fn).not.toContain('refresh(')
    expect(src).toContain('watch([filterQuery, sortMode], syncUrl)')
  })

  it('热量条分母取全量标签：筛选时宽度不跳', () => {
    const fn = block('maxPostsCount')
    expect(fn).toContain('tags.value.reduce')
    expect(fn).not.toContain('visibleTags')
  })

  it('排序不用 localeCompare：Node 与浏览器 ICU 排序规则不同，同一 URL 会换序', () => {
    const fn = block('visibleTags')
    expect(fn).not.toContain('localeCompare')
    expect(fn).toContain('compareText(')
    expect(src).toContain('import { compareText } from \'~~/lib/sortText\'')
    const cmp = readFileSync(resolve(ROOT, 'lib/sortText.ts'), 'utf-8')
    expect(cmp).toContain('toLowerCase()')
    expect(cmp).toContain('x < y ? -1')
    expect(cmp).not.toMatch(/\.localeCompare\(/)
  })
})

describe('标签页过滤 UI', () => {
  it('工具栏：输入框 + 排序锚点组 + 清除入口', () => {
    expect(src).toContain('v-model="filterQuery"')
    expect(src).toContain('@click="clearFilter"')
  })

  it('排序 chip 是真实锚点，且 href 带齐当前关键词（批次 #127）', () => {
    expect(src).toContain('role="group"')
    expect(src).not.toContain('role="radio"')
    const start = src.indexOf('v-for="opt in sortOptions"')
    const chip = src.slice(start, src.indexOf('</a>', start))
    expect(chip).toContain(':href="sortHref(opt.value)"')
    expect(chip).toContain('@click.prevent="setSort(opt.value)"')
    expect(chip).toMatch(/:aria-current="sortMode === opt\.value \? 'true' : undefined"/)
    // 只挂 sort 不挂 q = 换排序时把筛选丢了
    expect(src).toContain('q: filterQuery.value.trim()')
    expect(src).toContain('localeHrefWith(\'/tags\', {')
    expect(src).toContain('sort: mode === \'count\' ? \'\' : mode')
  })

  it('网格渲染过滤结果，空结果有独立空态', () => {
    expect(src).toContain('v-for="tag in visibleTags"')
    expect(src).toContain('v-if="visibleTags.length"')
    expect(src).toContain('t(\'tags.noMatch\')')
    expect(src).toContain('t(\'tags.showingCount\', { n: visibleTags.length })')
  })
})

describe('标签页过滤的四语文案', () => {
  const keys = [
    'filterPlaceholder',
    'sortCount',
    'sortName',
    'noMatch',
    'noMatchHint',
    'clearFilter',
    'showingCount'
  ] as const

  it.each(locales)('%s.json 七个键齐全', (loc) => {
    const json = JSON.parse(readFileSync(resolve(ROOT, `i18n/locales/${loc}.json`), 'utf-8')) as {
      tags?: Record<string, string>
    }
    for (const key of keys) {
      expect(json.tags?.[key], `${loc}.json 缺 tags.${key}`).toBeTruthy()
    }
  })
})
