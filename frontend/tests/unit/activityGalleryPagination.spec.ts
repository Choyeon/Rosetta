/**
 * /activity 与 /gallery 的分页契约（批次 #204）。
 *
 * 两页原先都是一次性拉 50 条（`page: 1, page_size: 50`）且没有任何翻页入口：第 51 条
 * 之后的动态/相册在站内**完全没有可达路径**（/posts 早就分页了，这两页被漏掉）。
 * 修好之后有三条东西不能再丢：
 *   ① 请求必须跟着 `currentPage` 走（写死 page:1 等于翻页无效）；
 *   ② 翻页必须是真实 `<a :href>`（AGENTS §2.3.3：SSR HTML 里的 href 是爬虫与无 JS
 *      访客唯一的链接图），href 里带 `?page=` 且语言前缀走 applyLocalePrefix；
 *   ③ 越界页码 SSR 期 301 回裸列表页，且 `no-store`（否则 301 被本页 swr 缓存固化）。
 */

import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { describe, expect, it } from 'vitest'

const ROOT = resolve(__dirname, '..', '..')

const PAGES = [
  { file: 'pages/activity.vue', route: '/activity' },
  { file: 'pages/gallery.vue', route: '/gallery' }
] as const

/**
 * 分页 nav 区域（aria-label="pagination" 的 <nav> 到其 </nav>）。
 * 属性区里会出现 `v-if="totalPages > 1"` 这种带 `>` 的值，所以不能用 `[^>]*`
 * （它会在 `1"` 的 `>` 处截断），改用受限长度的 `[\s\S]`。
 */
const navRegionOf = (src: string): string | null =>
  src.match(/<nav\b[\s\S]{0,400}?aria-label="pagination"[\s\S]*?<\/nav>/)?.[0] ?? null

describe.each(PAGES)('$file 分页', ({ file, route }) => {
  const src = readFileSync(resolve(ROOT, file), 'utf-8')

  it('请求按 currentPage / PAGE_SIZE 发，而不是写死 page:1 / page_size:50', () => {
    expect(src).toContain('page: currentPage.value')
    expect(src).toContain('page_size: PAGE_SIZE')
    // 旧形态：一次性拉 50 条且永远第 1 页
    expect(src).not.toContain('page_size: 50')
    expect(src).not.toMatch(/page:\s*1,\s*\n\s*page_size/)
  })

  it('PAGE_SIZE 落在后端 1–100 的合法区间内', () => {
    const size = Number(src.match(/const PAGE_SIZE = (\d+)/)?.[1])
    expect(Number.isInteger(size)).toBe(true)
    expect(size).toBeGreaterThan(0)
    expect(size).toBeLessThanOrEqual(100)
  })

  it('分页 nav 是真实 <a :href="pageHref(...)"> 锚点', () => {
    const nav = navRegionOf(src)
    expect(nav, `${file} 里找不到 aria-label="pagination" 的 <nav>`).not.toBeNull()
    expect(nav!).toContain(':href="pageHref(currentPage - 1)"')
    expect(nav!).toContain(':href="pageHref(page)"')
    expect(nav!).toContain(':href="pageHref(currentPage + 1)"')
    // 锚点上的 click 只允许 .prevent 修饰（保留 SPA 行为）
    expect(nav!).toContain('@click.prevent="handlePageChange(')
  })

  it(`pageHref 产出语言前缀 + ?page=（${route}）`, () => {
    const fn = src.match(/const pageHref[\s\S]{0,200}?(?=\nconst |\n\n)/)?.[0] ?? ''
    expect(fn).toContain(`applyLocalePrefix('${route}'`)
    expect(fn).toContain('?page=')
  })

  it('越界页码 SSR 期 301 + no-store', () => {
    const block = src.match(/if \(import\.meta\.server\) \{[\s\S]*?\n\}/)?.[0] ?? ''
    expect(block).toContain('app:rendered')
    expect(block).toContain('statusCode = 301')
    expect(block).toContain(`applyLocalePrefix('${route}'`)
    expect(block).toContain('cache-control')
    expect(block).toContain('no-store')
  })
})
