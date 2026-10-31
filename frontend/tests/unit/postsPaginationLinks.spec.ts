/**
 * /posts 分页必须是真实 <a href> 锚点（AGENTS §2.3.3：SSR HTML 里的 href 是爬虫
 * 能读到的唯一链接图）。历史上这里是纯 Button + @click：第 2 页起的所有文章零入链
 * （实测 /posts 的 page= 锚点数为 0）。回归形态有三种，都要挡掉：
 *   ① 回到 <Button @click="handlePageChange(...)">（无 href，爬虫不可达）；
 *   ② pageHref 忘了 ?page= 查询串（锚点全指同一页）；
 *   ③ pageHref 只写页码、丢了筛选（批次 #124）：SPA 点分页看着一切正常，
 *      右键新标签 / 复制链接 / 爬虫读到的却是全量列表，越界 301 还会顺手清掉筛选。
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

  it('pageHref 产出的锚点带页码查询串，且基址走语言前缀单源', () => {
    const fn = src.match(/const pageHref[\s\S]{0,200}?(?=\nconst |\n\n)/)?.[0] ?? ''
    expect(fn).toContain('page: String(page)')
    expect(fn).toContain('listHref(')
    const href = src.match(/const listHref[\s\S]{0,300}?(?=\nconst |\n\n)/)?.[0] ?? ''
    expect(href).toMatch(/applyLocalePrefix\('\/posts', locale\.value\)/)
    expect(href).toContain('new URLSearchParams(query)')
  })

  it('分页锚点与越界 301 共用同一份不带页码的筛选串（批次 #124）', () => {
    // 单源：pageHref / syncUrl / 301 三处都从 filterQuery 派生。
    // 回到"href 只写页码"的形态＝右键新标签与爬虫读到的都是全量列表，
    // 而且每加一个筛选都要记得改三处（media 就是加在 canonicalQuery 里的那一批）。
    expect(src).toContain('const pageHref = (page: number) => listHref({ ...filterQuery.value, page: String(page) })')
    expect(src).toMatch(/if \(currentPage\.value > 1\) q\.page = String\(currentPage\.value\)/)
    expect(src).toContain('const q = { ...filterQuery.value }')
    expect(src).toMatch(/setHeader\('location', listHref\(filterQuery\.value\)\)/)
    // 筛选项一个都不能从这份单源里掉出去
    for (const key of ['category', 'post_type', 'search', 'sort', 'media']) {
      expect(src, key).toContain(`q.${key} =`)
    }
    // 旧形态：分页 href 只有页码
    expect(src).not.toMatch(/`\$\{applyLocalePrefix\('\/posts'[^`]*\}\?page=\$\{page\}`/)
  })
})
