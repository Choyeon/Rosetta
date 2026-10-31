/**
 * 导航行上两个恒假判据的拆除回归（批次 #150）。
 *
 * 背景：`frontend/lib/navigation.ts` 曾读 `row.link_type === 'page'` 与
 * `raw.is_external === true` / `raw.link_type === 'external'`，而 `GET /navigations`
 * 的响应模型 `NavigationResponse` 从未声明这三个字段（后端全仓 grep `link_type` /
 * `is_external` 零命中）。恒假读的危害不是"多此一举"，而是**撒谎**：
 * — 那一条 `link_type === 'page'` 分支看起来在支持"独立页按 slug 挂链接"，实际从不成立；
 * — `is_external === true` 看起来允许"内部路径也当外链新窗口打开"，实际外链判定只认 scheme。
 * 本 spec 把两件事钉住：判据不再被读取（后端也永远不得新增），以及拆除前后真实行为一致。
 */
import { readFileSync } from 'node:fs'
import { join } from 'node:path'
import { describe, expect, it } from 'vitest'

import { navRowsToLinks, normalizeNavRowUrl } from '~~/lib/navigation'
import type { NavApiRow } from '~~/lib/navigation'

const ROOT = join(__dirname, '..', '..')
const REPO = join(ROOT, '..')

const navLib = readFileSync(join(ROOT, 'lib', 'navigation.ts'), 'utf-8')
const schemas = readFileSync(join(REPO, 'backend', 'schemas', '__init__.py'), 'utf-8')
const navSchema = schemas.slice(
  schemas.indexOf('class NavigationBase'),
  schemas.indexOf('class NavigationLocalizedResponse')
)

describe('两个恒假判据已从读取面拆除', () => {
  it('lib 里不再有任何 .link_type / .is_external 属性访问', () => {
    expect(navLib).not.toMatch(/\.\s*link_type\b/)
    expect(navLib).not.toMatch(/\.\s*is_external\b/)
  })

  it('NavApiRow 的类型声明里也没有这两个字段（留着就是继续撒谎）', () => {
    const iface = navLib.slice(navLib.indexOf('export interface NavApiRow'), navLib.indexOf('export function isNavActive'))
    expect(iface).not.toContain('link_type')
    expect(iface).not.toContain('is_external')
    expect(iface.length).toBeGreaterThan(50)
  })

  it('反向闸门：后端导航 schema 从未声明它们（新增了就重新红，别再顺手读）', () => {
    expect(navSchema.length).toBeGreaterThan(100)
    expect(navSchema).not.toContain('link_type')
    expect(navSchema).not.toContain('is_external')
  })
})

describe('拆掉之后真实行为与旧代码等价', () => {
  it('/page/<slug> 老写法仍折成 /<slug>（这条一直靠折前缀，不靠 link_type）', () => {
    expect(normalizeNavRowUrl({ url: '/page/about' })).toBe('/about')
    expect(normalizeNavRowUrl({ url: '/page/guestbook/' })).toBe('/guestbook')
  })

  it('只有 slug 的行仍按 /<slug> 归一（走的是取值链的最后一档）', () => {
    expect(normalizeNavRowUrl({ slug: 'about' })).toBe('/about')
    expect(normalizeNavRowUrl({ slug: '/about' })).toBe('/about')
  })

  it('url 在场时优先于 slug，link_type=page 不再能把它们调包', () => {
    const row = { url: '/posts', slug: 'about', link_type: 'page' } as unknown as NavApiRow
    expect(normalizeNavRowUrl(row)).toBe('/posts')
  })

  it('外链判定只认 scheme：is_external 不再能把内部路径判成外链', () => {
    const label = (row: NavApiRow) => String(row.label ?? '')
    const rows = [
      { label: '站内', url: '/about', is_external: true },
      { label: '站外', url: 'https://example.com' }
    ] as unknown as NavApiRow[]
    const links = navRowsToLinks(rows, label, { includeExternal: false })
    expect(links.map(l => l.to)).toEqual(['/about'])
  })

  it('includeExternal 缺省时外链原样透传，target_blank 仍翻译成真 target', () => {
    const label = (row: NavApiRow) => String(row.label ?? '')
    const links = navRowsToLinks(
      [{ label: '文档', url: 'https://docs.example.com', target_blank: true }] as unknown as NavApiRow[],
      label
    )
    expect(links[0]!.to).toBe('https://docs.example.com')
    expect(links[0]!.target).toBe('_blank')
  })
})
