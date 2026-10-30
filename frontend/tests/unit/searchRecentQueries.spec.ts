/**
 * 搜索页「最近搜索」（批次 #216）。
 *
 * 三条约束：
 *  1. 只存本机（localStorage），不上报、不同步；隐私模式下 setItem 可能直接抛错，
 *     记忆功能失效不能连带检索本身失败。
 *  2. 首帧两端一致：初始 ref 是空数组，读取只在 onMounted 里发生（SSR 期碰 localStorage
 *     会直接 ReferenceError，也会让 hydrate 的列表长度与 SSR 不同而 mismatch）。
 *  3. 只在用户显式提交检索时记录（runSearch），改筛选/翻页不记录。
 */

import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { describe, expect, it } from 'vitest'

const ROOT = resolve(__dirname, '..', '..')
const src = readFileSync(resolve(ROOT, 'pages/search.vue'), 'utf-8')
const locales = ['zh', 'en', 'ja', 'zh_Hant'] as const

const block = (name: string, body: string) =>
  src.match(new RegExp(`const ${name} = [\\s\\S]*?\\n\\}`))?.[0] ?? body

describe('最近搜索的存储口径', () => {
  it('键名与条数上限是常量，最多 5 条', () => {
    expect(src).toContain('const RECENT_SEARCH_KEY = \'rosetta:recent-searches\'')
    expect(src).toContain('const RECENT_SEARCH_LIMIT = 5')
  })

  it('初始 ref 为空数组，读取只在 onMounted（SSR 期不碰 localStorage）', () => {
    expect(src).toContain('const recentSearches = ref<string[]>([])')
    expect(src).toContain('onMounted(() => {')
    expect(src).toContain('recentSearches.value = readRecentSearches()')
    // 顶层（非 onMounted/函数体内）不得出现 getItem
    const beforeScriptFns = src.split('const readRecentSearches')[0] ?? ''
    expect(beforeScriptFns).not.toContain('localStorage.getItem')
  })

  it('读写在 try/catch 里：隐私模式抛错只让记忆失效', () => {
    const read = block('readRecentSearches', '')
    const write = block('writeRecentSearches', '')
    expect(read).toContain('catch')
    expect(write).toContain('catch')
    expect(read).toContain('Array.isArray(parsed)')
    expect(read).toContain('RECENT_SEARCH_LIMIT')
  })

  it('记录去重并截断到上限', () => {
    const fn = block('rememberSearch', '')
    expect(fn).toContain('filter(item => item !== kw)')
    expect(fn).toContain('[kw, ...rest].slice(0, RECENT_SEARCH_LIMIT)')
    // needle 不能写成完整的 'import.meta.client' —— vitest 把这个字面量当 define
    // 目标替换成 true，断言就变成 toContain(true)（同 favoritesLanding.spec.ts）。
    expect(fn).toContain('if (!import.meta')
    expect(fn).toContain('client) return')
  })
})

describe('最近搜索的入口', () => {
  it('只有显式提交检索才记录', () => {
    const run = block('runSearch', '')
    expect(run).toContain('syncUrl(\'push\', keyword.value)')
    expect(run).toContain('rememberSearch(keyword.value)')
    const filter = block('handleFilter', '')
    expect(filter).not.toContain('rememberSearch')
    const page = block('handlePageChange', '')
    expect(page).not.toContain('rememberSearch')
  })

  it('点历史词等于把词填回输入框再提交', () => {
    const fn = block('applyRecent', '')
    expect(fn).toContain('keyword.value = kw')
    expect(fn).toContain('runSearch()')
  })

  it('模板在开始提示下渲染历史，并可一键清除', () => {
    expect(src).toContain('v-if="recentSearches.length > 0"')
    expect(src).toContain('v-for="kw in recentSearches"')
    expect(src).toContain('@click="applyRecent(kw)"')
    expect(src).toContain('@click="clearRecent"')
  })
})

describe('最近搜索的四语文案', () => {
  it.each(locales)('%s.json 有 recentTitle / clearRecent', (loc) => {
    const json = JSON.parse(readFileSync(resolve(ROOT, `i18n/locales/${loc}.json`), 'utf-8')) as {
      search?: Record<string, string>
    }
    expect(json.search?.recentTitle, `${loc}.json 缺 search.recentTitle`).toBeTruthy()
    expect(json.search?.clearRecent, `${loc}.json 缺 search.clearRecent`).toBeTruthy()
  })
})
