/**
 * /activity、/gallery、/guestbook 的分页契约（批次 #204 / #205）。
 *
 * activity 与 gallery 原先都是一次性拉 50 条（`page: 1, page_size: 50`）且没有任何翻页
 * 入口：第 51 条之后的动态/相册在站内**完全没有可达路径**（/posts 早就分页了，这两页被漏掉）。
 * guestbook 有翻页逻辑但整条 nav 是 `<Button @click>`：SSR HTML 里零个 href，无 JS 访客
 * 与爬虫只能看到第 1 页，且越界页码回 200 空列表。
 * 修好之后这三条东西不能再丢：
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
  { file: 'pages/gallery.vue', route: '/gallery' },
  { file: 'pages/guestbook.vue', route: '/guestbook' }
] as const

/**
 * 分页 nav 区域（分页 <nav> 到其 </nav>）。两种可访问名写法都认：
 * 静态 `aria-label="pagination"` 与 i18n 的 `:aria-label="t('common.pagination', …)"`
 * （作者主页必须用后者，authorArchivePage.spec.ts 钉着四语文案）。
 * 属性区里会出现 `v-if="totalPages > 1"` 这种带 `>` 的值，所以不能用 `[^>]*`
 * （它会在 `1"` 的 `>` 处截断），改用受限长度的 `[\s\S]`。
 */
const navRegionOf = (src: string): string | null =>
  src.match(
    /<nav\b[\s\S]{0,400}?(?:aria-label="pagination"|:aria-label="t\('common\.pagination')[\s\S]*?<\/nav>/
  )?.[0] ?? null

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

/**
 * 分类页 / 标签页：URL 驱动与真锚点早已在，唯独缺「越界页码 301」——`?page=99` 会
 * 渲染 200 空列表（soft 404）并带自指 canonical。与其余公开列表页同一道闸门。
 */
describe.each([
  { file: 'pages/categories/[slug].vue', route: '/categories/${slug.value}' },
  { file: 'pages/tags/[slug].vue', route: '/tags/${slug.value}' }
])('$file 越界页码', ({ file, route }) => {
  const src = readFileSync(resolve(ROOT, file), 'utf-8')

  it('请求页页码有快照（钳位 watch 之后仍认得出越界）', () => {
    expect(src).toContain('const requestedPage = Math.max(1, Number(route.query.page) || 1)')
  })

  it('越界页码 SSR 期 301 + no-store', () => {
    const block = src.match(/if \(import\.meta\.server\) \{[\s\S]*?\n\}/)?.[0] ?? ''
    expect(block).toContain('app:rendered')
    expect(block).toContain('statusCode = 301')
    expect(block).toContain(`applyLocalePrefix(\`${route}\``)
    expect(block).toContain('cache-control')
    expect(block).toContain('no-store')
  })

  it('pageHref 带语言前缀 + ?page=', () => {
    const fn = src.match(/const pageHref[\s\S]{0,200}?(?=\nconst |\n\n)/)?.[0] ?? ''
    expect(fn).toContain(`applyLocalePrefix(\`${route}\``)
    expect(fn).toContain('?page=')
  })
})

/**
 * 作者主页（/authors/{username}）是同一族的最后一条：翻页原先只是页内 `ref(1)`，
 * 连地址栏都不带页码——刷新/后退回第 1 页、分享「第 2 页」办不到、SSR HTML 里
 * 也没有任何 href 指向后续页。它的每页条数来自站点设置（不是常量），所以放在
 * 单独一组里，只钉「URL 驱动 + 真锚点 + 301」这三件与页大小无关的事。
 */
describe('pages/authors/[username].vue 分页', () => {
  const src = readFileSync(resolve(ROOT, 'pages/authors/[username].vue'), 'utf-8')
  const AUTHOR_PAGE_HREF = 'applyLocalePrefix(`/authors/${username.value}`'

  it('页码从 URL 读、翻页写回 URL（可分享、可后退）', () => {
    expect(src).toContain('Number(route.query.page)')
    expect(src).toContain('router.replace({ query:')
    // 旧形态：纯页内状态，按钮直接 currentPage += 1
    expect(src).not.toContain('@click="currentPage')
  })

  it('分页 nav 是真实 <a :href="pageHref(...)"> 锚点', () => {
    const nav = navRegionOf(src)
    expect(nav, '作者主页里找不到 aria-label="pagination" 的 <nav>').not.toBeNull()
    expect(nav!).toContain(':href="pageHref(currentPage - 1)"')
    expect(nav!).toContain(':href="pageHref(p)"')
    expect(nav!).toContain(':href="pageHref(currentPage + 1)"')
    expect(nav!).toContain('@click.prevent="handlePageChange(')
  })

  it('pageHref 带作者路径 + 语言前缀 + ?page=', () => {
    const fn = src.match(/const pageHref[\s\S]{0,200}?(?=\nconst |\n\n)/)?.[0] ?? ''
    expect(fn).toContain(AUTHOR_PAGE_HREF)
    expect(fn).toContain('?page=')
  })

  it('越界页码 SSR 期 301 回裸作者页 + no-store', () => {
    const block = src.match(/if \(import\.meta\.server\) \{[\s\S]*?\n\}/)?.[0] ?? ''
    expect(block).toContain('app:rendered')
    expect(block).toContain('statusCode = 301')
    expect(block).toContain(AUTHOR_PAGE_HREF)
    expect(block).toContain('cache-control')
    expect(block).toContain('no-store')
  })
})
