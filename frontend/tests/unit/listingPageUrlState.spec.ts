/**
 * 公开列表页的页码必须是 URL 状态（AGENTS §2.3.3：爬虫能读到的站内链接只在 SSR HTML 里；
 * 分享/刷新/后退还原的也是地址栏，不是页内 ref）。
 *
 * 这批页面曾各自把 `currentPage` 只存在本地 ref：`?page=3` 打开永远是第一页，
 * 分类/标签的第 2 页起所有文章零入链，留言板与搜索的深链接同样落回第一页。
 * /posts 一直是正确形态，本 spec 把它当成对拍基线，防止后续又退化回纯按钮。
 */

import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { describe, expect, it } from 'vitest'

const ROOT = resolve(__dirname, '..', '..')
const read = (rel: string) => readFileSync(resolve(ROOT, rel), 'utf-8')

/** 页码 ↔ URL 双向：初始值从 query 读、变更写回 query、越界拉回、前进后退回读。 */
const URL_STATE_CONTRACT = [
  'const currentPage = ref(Math.max(1, Number(route.query.page) || 1))',
  'router.replace({ query:',
  'String(page)',
  'route.query.page'
]

const PAGES_WITH_URL_PAGE = [
  'pages/categories/[slug].vue',
  'pages/tags/[slug].vue',
  'pages/guestbook.vue',
  'pages/search.vue'
]

describe.each(PAGES_WITH_URL_PAGE)('%s 页码进 URL', (rel) => {
  const src = read(rel)

  it.each(URL_STATE_CONTRACT)('包含口径片段 %s', (needle) => {
    expect(src, `${rel} 缺少：${needle}`).toContain(needle)
  })

  it('越界页码拉回最后一页（?page=99 不能停在空列表）', () => {
    expect(src).toContain('currentPage.value = totalPages.value')
  })

  it('不再有"页码只存在本地 ref"的旧形态（ref(1) 且没有 route.query 回读）', () => {
    expect(src).not.toMatch(/const currentPage = ref\(1\)/)
  })
})

describe.each(['pages/categories/[slug].vue', 'pages/tags/[slug].vue'])(
  '%s 分页是真实锚点（与 /posts 同口径）',
  (rel) => {
    const src = read(rel)
    const nav = src.match(/<nav[^>]*aria-label="pagination"[\s\S]*?<\/nav>/)?.[0] ?? null

    it('分页 nav 区域存在', () => {
      expect(nav, `${rel} 里找不到 aria-label="pagination" 的 <nav>`).not.toBeNull()
    })

    it('nav 内是 <a :href="pageHref(...)">，当前页渲染成 aria-current 的 span', () => {
      const region = nav!
      expect(region).toContain(':href="pageHref(currentPage - 1)"')
      expect(region).toContain(':href="pageHref(currentPage + 1)"')
      expect(region).toContain('aria-current="page"')
      // 锚点上的 click 必须带 .prevent，否则 href 抢在 SPA 行为之前整页跳转
      expect(region).not.toMatch(/:href="pageHref\([\s\S]*?@click="goToPage/)
    })

    it('没有 Button 形态的翻页入口（纯 click 等于爬虫零入链）', () => {
      expect(nav!).not.toMatch(/<Button[\s\S]*?@click="handlePageChange|<Button[\s\S]*?@click="currentPage\s*[-+=]/)
    })

    it('pageHref 产出带 ?page= 的前缀化地址', () => {
      const fn = src.match(/const pageHref[\s\S]{0,200}?(?=\nconst |\n\n)/)?.[0] ?? ''
      expect(fn).toContain('?page=')
      expect(fn).toContain('applyLocalePrefix')
    })
  }
)
