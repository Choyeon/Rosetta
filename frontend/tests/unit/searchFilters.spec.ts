/**
 * /search 的筛选栏（分类 / 标签 / 排序）与 URL 单源。
 *
 * 两条回归形态必须挡掉：
 *   ① 搜索必须留在当前语言前缀下。本页曾 `router.push({ path: '/search' })` 写死裸路径，
 *      英文用户在 /en/search 点搜索会被整站切回中文页（AGENTS §2.3.3 第 2 条）。
 *   ② 筛选状态只在组件里、不进 URL：分享/后退会丢筛选，且「清除筛选」如果顺手清掉关键词，
 *      用户点一下就回到开始提示，等于把一次重查变成一次复位。
 *
 * 另钉住：仅筛选、无关键词时计数改用「共 N 篇」——搜索口径的「与「」相关」在空关键词下是病句。
 */

import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { describe, expect, it } from 'vitest'

const ROOT = resolve(__dirname, '..', '..')
const src = readFileSync(resolve(ROOT, 'pages/search.vue'), 'utf-8')
const locales = ['zh', 'en', 'ja', 'zh_Hant'] as const

const clearFiltersBody = src.match(/const clearFilters = \(\) => \{[\s\S]*?\n\}/)?.[0] ?? ''
const pageHrefBody = src.match(/const pageHref = \(page: number\) => \{[\s\S]*?\n\}/)?.[0] ?? ''

describe('search 筛选栏接线', () => {
  it('三个筛选控件都绑到 URL 状态', () => {
    expect(src).toContain('v-model="selectedCategory"')
    expect(src).toContain('v-model="selectedTag"')
    expect(src).toContain('v-model="sortBy"')
    expect(src).toContain('@update:model-value="handleFilter"')
  })

  it('请求串同时带上 search / category / tag / sort', () => {
    const query = src.match(/query: computed\(\(\) => \(\{[\s\S]*?\}\)\)/)?.[0] ?? ''
    expect(query).toContain('search: keywordLabel.value || undefined')
    expect(query).toContain('category: selectedCategory.value || undefined')
    expect(query).toContain('tag: selectedTag.value || undefined')
    // 排序只回发白名单值
    expect(query).toContain('sort: sortBy.value === \'popular\' ? \'popular\' : undefined')
  })

  it('初始状态从 route.query 读，且 sort 只接受白名单', () => {
    expect(src).toContain('slugFromUrl(route.query.category)')
    expect(src).toContain('slugFromUrl(route.query.tag)')
    expect(src).toContain('sortFromUrl(route.query.sort)')
    const sortFn = src.match(/const sortFromUrl = [\s\S]*?\n(?=const )/)?.[0] ?? ''
    expect(sortFn).toContain('SORT_VALUES.includes(raw as SortValue)')
  })

  it('地址栏同步包含全部筛选位与页码', () => {
    const urlQuery = src.match(/const urlQuery = computed<Record<string, string>>[\s\S]*?\n\}\)/)?.[0] ?? ''
    expect(urlQuery).toContain('q.q = keywordLabel.value')
    expect(urlQuery).toContain('q.category = selectedCategory.value')
    expect(urlQuery).toContain('q.tag = selectedTag.value')
    expect(urlQuery).toContain('q.sort = sortBy.value')
    expect(urlQuery).toContain('q.page = String(currentPage.value)')
  })

  it('搜索跳转保留语言前缀，不再写死裸 /search 路径', () => {
    expect(src).toContain('const searchPath = computed(() => applyLocalePrefix(\'/search\', locale.value))')
    expect(src).toContain('path: searchPath.value')
    expect(src).not.toMatch(/path:\s*['"]\/search['"]/)
  })
})

describe('search 清除筛选与计数口径', () => {
  it('清除筛选只重置筛选，不动关键词', () => {
    expect(clearFiltersBody).not.toBe('')
    expect(clearFiltersBody).toContain('selectedCategory.value = \'\'')
    expect(clearFiltersBody).toContain('selectedTag.value = \'\'')
    expect(clearFiltersBody).toContain('sortBy.value = \'latest\'')
    expect(clearFiltersBody).not.toContain('keyword.value')
    expect(clearFiltersBody).not.toContain('router.push')
  })

  it('有关键词走搜索口径计数，仅筛选走「共 N 篇」', () => {
    expect(src).toContain('t(\'search.resultCount\', { count: total, keyword: keywordLabel })')
    expect(src).toContain('t(\'posts.resultCount\', { n: total })')
    expect(src).toContain('v-if="hasFilter"')
  })

  it('开始提示只在既无关键词也无筛选时出现', () => {
    expect(src).toContain('v-if="!hasKeyword && !hasFilter"')
  })
})

describe('search 分页锚点', () => {
  it('分页是真实 <a :href> 锚点，点击走 prevent 保留 SPA 翻页', () => {
    const nav = src.match(/<nav[^>]*aria-label="pagination"[\s\S]*?<\/nav>/)?.[0] ?? ''
    expect(nav).not.toBe('')
    expect(nav).toContain(':href="pageHref(')
    expect(nav).toContain('@click.prevent="handlePageChange(')
  })

  it('pageHref 带语言前缀并在查询串里写 page', () => {
    expect(pageHrefBody).not.toBe('')
    expect(pageHrefBody).toContain('URLSearchParams')
    expect(pageHrefBody).toContain('page: String(page)')
    expect(pageHrefBody).toContain('searchPath.value')
  })
})

describe('search 标签筛选的四语文案', () => {
  it.each(locales)('%s.json 有 allTags / selectTag', (loc) => {
    const json = JSON.parse(readFileSync(resolve(ROOT, `i18n/locales/${loc}.json`), 'utf-8')) as {
      search?: Record<string, string>
    }
    expect(json.search?.allTags, `${loc}.json 缺 search.allTags`).toBeTruthy()
    expect(json.search?.selectTag, `${loc}.json 缺 search.selectTag`).toBeTruthy()
  })
})
