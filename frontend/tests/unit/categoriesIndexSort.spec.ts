/**
 * 分类目录页排序（批次 #219）。
 *
 * 背景：接口按 id 返回，字段顺序对读者没有意义（线上是 技术/教程/前端/后端/…）。
 * 三条约束：
 *  1. 默认按文章数倒序，?sort=name 切名称序；状态在地址栏，SSR 首屏与分享链接同口径。
 *  2. 名称比较走 lib/sortText 的码位比较，不用 localeCompare（ICU 排序 SSR/浏览器不一致，
 *     同一 URL 会在交互后静默换序）。
 *  3. 空态只在「确实取到空列表」时出现（categoriesEmpty），加载中/失败不显示「暂无分类」。
 */

import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { describe, expect, it } from 'vitest'

const ROOT = resolve(__dirname, '..', '..')
const src = readFileSync(resolve(ROOT, 'pages/categories/index.vue'), 'utf-8')
const locales = ['zh', 'en', 'ja', 'zh_Hant'] as const

const block = (name: string): string =>
  src.match(new RegExp(`const ${name} = [\\s\\S]*?\\n\\}`))?.[0] ?? ''

describe('分类页排序状态', () => {
  it('初始条件从地址栏读，sort 只认白名单', () => {
    expect(src).toContain('route.query.sort === \'name\' ? \'name\' : \'count\'')
  })

  it('改条件走 replace，不在本地重发请求', () => {
    expect(src).toContain('router.replace({ query })')
    const fn = block('setSort')
    expect(fn).toContain('sortMode.value === next')
    expect(src).not.toMatch(/watch\(sortMode[\s\S]{0,120}refresh\(/)
  })

  it('默认排序是文章数倒序，名称序用码位比较', () => {
    const fn = block('sortedCategories')
    expect(fn).toContain('getPostsCount(b) - getPostsCount(a)')
    expect(fn).toContain('compareText(')
    expect(fn).not.toContain('localeCompare')
    expect(src).toContain('import { compareText } from \'~~/lib/sortText\'')
  })

  it('网格渲染的是排序后的列表，工具栏与网格同源', () => {
    expect(src).toContain('v-for="cat in sortedCategories"')
  })

  it('排序 chip 是真实锚点：href 走 localeHrefWith，缺省档不挂查询键（批次 #127）', () => {
    expect(src).toContain('role="group"')
    expect(src).not.toContain('role="radio"')
    const start = src.indexOf('v-for="opt in sortOptions"')
    const chip = src.slice(start, src.indexOf('</a>', start))
    expect(chip).toContain(':href="sortHref(opt.value)"')
    expect(chip).toContain('@click.prevent="setSort(opt.value)"')
    expect(chip).toMatch(/:aria-current="sortMode === opt\.value \? 'true' : undefined"/)
    expect(chip).not.toContain(':variant')
    expect(src).toContain('localeHrefWith(\'/categories\', { sort: mode === \'count\' ? \'\' : mode })')
    // 缺省档写成空串而不是省键：让「按数量」与「不带参数」落到同一个 URL，不给同一视图两个地址
    expect(src).not.toMatch(/localeHrefWith\('\/categories', \{ sort: mode \}/)
    expect(src).toContain('const { localeHref, localeHrefWith } = useLocaleLink()')
  })

  it('空态只在确认为空时显示，加载中不出现「暂无分类」', () => {
    expect(src).toContain('v-if="categoriesEmpty"')
    expect(src).toContain('categories.noCategories')
    expect(src).not.toContain('v-if="categories.length === 0"')
  })
})

describe('分类页排序文案', () => {
  it.each(locales)('%s 有三条排序/计数文案', (loc) => {
    const json = JSON.parse(readFileSync(resolve(ROOT, `i18n/locales/${loc}.json`), 'utf-8'))
    for (const key of ['sortCount', 'sortName', 'showingCount']) {
      expect(json.categories[key], `${loc}.categories.${key}`).toBeTruthy()
    }
    expect(json.categories.showingCount).toContain('{n}')
  })
})
