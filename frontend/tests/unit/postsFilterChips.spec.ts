/**
 * /posts 的「已应用筛选」chip 必须是真实 <a href>（AGENTS §2.3.3 第 2 条：SSR HTML 里的
 * href 是爬虫能读到的唯一链接图）。三个下拉框都在 ClientOnly 内，SSR 面根本看不到它们，
 * 所以 chip 是爬虫（与右键新标签、复制链接）唯一能发现筛选组合的入口。
 * 三种回归形态：① 退回 `<Button @click>`（只剩 SPA 可用）；② href 忘了从 filterQuery
 * 派生（移除一个筛选＝把其余筛选也清掉）；③ chip 键集合与 hasActiveFilter 数的不是
 * 同一批（界面上"看着筛了"却没有出口）。
 */

import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { describe, expect, it } from 'vitest'

const PAGE_FILE = resolve(__dirname, '../../pages/posts/index.vue')
const LOCALE_DIR = resolve(__dirname, '../../i18n/locales')
const page = readFileSync(PAGE_FILE, 'utf-8')
const locales = ['zh', 'en', 'ja', 'zh_Hant'] as const

/** 取 chip 那一块的模板文本（从 v-if 到 </header>）。 */
const chipBlock = page.slice(
  page.indexOf('v-if="activeFilterChips.length > 0"'),
  page.indexOf('</header>')
)

describe('/posts 筛选 chip（批次 #125）', () => {
  it('chip 是真实锚点：href 由 removeFilterHref 产出，点击仍走 SPA 分支', () => {
    expect(chipBlock).toContain(':href="removeFilterHref(chip.key)"')
    expect(chipBlock).toContain('@click.prevent="removeFilter(chip.key)"')
    expect(chipBlock).toContain(':aria-label="t(\'search.removeFilter\', { name: chip.label })"')
    // 整块在最后一个 ClientOnly 之后：下拉框本体不进 SSR，chip 必须进
    expect(page.lastIndexOf('</ClientOnly>')).toBeLessThan(
      page.indexOf('v-if="activeFilterChips.length > 0"')
    )
  })

  it('移除串与分页锚点共用同一份 filterQuery，且只去掉那一个键', () => {
    const fn = page.match(/const removeFilterHref[\s\S]{0,300}?(?=\n\n)/)?.[0] ?? ''
    expect(fn).toContain('Object.entries(filterQuery.value)')
    expect(fn).toMatch(/filter\(\(\[name\]\) => name !== key\)/)
    expect(fn).toContain('listHref(kept)')
  })

  it('chip 的键集合＝hasActiveFilter 数的那四项（排序不算筛选，与 clearFilters 同口径）', () => {
    expect(page).toMatch(/type FilterChipKey = 'search' \| 'category' \| 'post_type' \| 'media'/)
    const fn = page.match(/const activeFilterChips[\s\S]{0,1400}?(?=\n\/\/ 移除一个筛选)/)?.[0] ?? ''
    for (const key of ['search', 'category', 'post_type', 'media']) {
      expect(fn, key).toContain(`key: '${key}'`)
    }
    // 排序既不在 chip 也不在清除动作里：两边口径必须一致，否则"清除筛选"后仍留在排序视图
    expect(fn).not.toMatch(/key: 'sort'/)
    expect(page.slice(page.indexOf('const clearFilters'))).not.toContain('sortBy.value =')
  })

  it('removeFilter 复位的是各自的缺省值（不是统一空串），并回到第 1 页', () => {
    const fn = page.match(/const removeFilter =[\s\S]{0,600}?(?=\nconst |\n\n)/)?.[0] ?? ''
    expect(fn).toMatch(/searchInput\.value = ''/)
    expect(fn).toMatch(/searchQuery\.value = ''/)
    expect(fn).toMatch(/selectedCategory\.value = ''/)
    expect(fn).toContain('selectedType.value = ALL_TYPES')
    expect(fn).toContain('selectedMedia.value = ALL_MEDIA')
    expect(fn).toContain('currentPage.value = 1')
    expect(fn).toContain('syncUrl()')
  })

  it('chip 用到的文案键四语齐全，且 removeFilter 带 {name} 占位', () => {
    for (const code of locales) {
      const json = JSON.parse(readFileSync(resolve(LOCALE_DIR, `${code}.json`), 'utf-8'))
      expect(json.search?.removeFilter, code).toContain('{name}')
      expect(json.common?.search, code).toBeTruthy()
      expect(json.nav?.categories, code).toBeTruthy()
      expect(json.posts?.selectType, code).toBeTruthy()
      expect(json.posts?.selectMedia, code).toBeTruthy()
      expect(json.posts?.mediaAudio, code).toBeTruthy()
      expect(json.posts?.mediaVideo, code).toBeTruthy()
      expect(json.posts?.typePost, code).toBeTruthy()
    }
  })

  it('标签回落：分类名走 pickLocalized（字典没到时用 slug），自定义类型用本身的 name', () => {
    expect(chipBlock).not.toContain('v-html')
    const fn = page.match(/const activeFilterChips[\s\S]{0,1400}?(?=\n\/\/ 移除一个筛选)/)?.[0] ?? ''
    expect(fn).toContain('pickLocalized(hit.name)')
    expect(fn).toContain('String(hit.name)')
  })
})
