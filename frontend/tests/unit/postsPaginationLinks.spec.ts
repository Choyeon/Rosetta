/**
 * /posts 分页必须是真实 <a href> 锚点（AGENTS §2.3.3：SSR HTML 里的 href 是爬虫
 * 能读到的唯一链接图）。历史上这里是纯 Button + @click：第 2 页起的所有文章零入链
 * （实测 /posts 的 page= 锚点数为 0）。回归形态有两种，都要挡掉：
 *   ① 回到 <Button @click="handlePageChange(...)">（无 href，爬虫不可达）；
 *   ② pageHref 忘了 ?page= 查询串（锚点全指同一页）。
 */

import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { describe, expect, it } from 'vitest'

const ROOT = resolve(__dirname, '..', '..')
const src = readFileSync(resolve(ROOT, 'pages/posts/index.vue'), 'utf-8')

/** 分页 nav 区域（aria-label="pagination" 的 <nav> 到其 </nav>）。 */
const navRegion = src.match(/<nav[^>]*aria-label="pagination"[\s\S]*?<\/nav>/)?.[0] ?? null

describe('posts 分页锚点形态', () => {
  it('分页 nav 区域存在（模板结构变了要同步改本测试）', () => {
    expect(navRegion, 'pages/posts/index.vue 里找不到 aria-label="pagination" 的 <nav>').not.toBeNull()
  })

  it('nav 内是 <a :href="pageHref(...)"> 锚点', () => {
    const nav = navRegion!
    expect(nav).toContain(':href="pageHref(')
    // prev / 页码 / next 三类锚点都在
    expect(nav).toContain(':href="pageHref(currentPage - 1)"')
    expect(nav).toContain(':href="pageHref(page)"')
    expect(nav).toContain(':href="pageHref(currentPage + 1)"')
    // 锚点上的 click 只允许 .prevent 修饰（保留 SPA 行为），href 本身不能被 prevent 掉
    expect(nav).not.toMatch(/href="[^"]*"[\s\S]*?@click="handlePageChange/)
  })

  it('不再存在 Button 形态的分页点击入口（无 href 的旧回归形态）', () => {
    expect(navRegion!).not.toContain('@click="handlePageChange(currentPage - 1)"')
    expect(navRegion!).not.toContain('@click="handlePageChange(currentPage + 1)"')
  })

  it('pageHref 产出的锚点带 ?page= 查询串', () => {
    // 定义是两行的箭头函数：const pageHref = (page) => `...?page=${page}`
    const fn = src.match(/const pageHref[\s\S]{0,200}?(?=\nconst |\n\n)/)?.[0] ?? ''
    expect(fn).toContain('?page=')
    expect(fn).toContain('applyLocalePrefix')
  })
})
