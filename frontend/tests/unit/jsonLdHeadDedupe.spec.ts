/**
 * JSON-LD 的 head 去重契约（2026-10-29 线上实测）。
 *
 * 现场：`https://choyeon.cc/` 与文章详情页的 SSR HTML 里各只有 1 个
 * `<script type="application/ld+json">`，但 hydration 之后 DOM 里是 2 个，
 * 内容完全相同（首页两份 WebSite、文章页两份五实体 @graph）。
 *
 * 根因：三个 JSON-LD 用的是 `hid:` —— 那是 Vue Meta 时代的字段，unhead 3 完全不认。
 * unhead 只把 `key` 序列化成 `data-hid` 属性、hydration 时再按它认领已有标签
 * （见 unhead `tag.props['data-hid'] = tag._h = tag.key`）。没有 key 的 SSR 标签
 * 客户端认领不到，只能再插一份。
 *
 * 口径：所有 JSON-LD script 必须带 `key`（unhead 的唯一性键），且全仓不得再出现 `hid:`。
 */
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { describe, expect, it } from 'vitest'

const ROOT = resolve(__dirname, '..', '..')
const seo = readFileSync(resolve(ROOT, 'composables/useSeo.ts'), 'utf8')
const MARKER = /'application\/ld\+json'/g

function jsonLdBlocks(source: string): string[] {
  return source
    .split(/'application\/ld\+json'/)
    .slice(1)
    .map(p => p.slice(0, 240))
}

describe('JSON-LD script 必须用 unhead 的 key 认领 SSR 标签', () => {
  it('三个 JSON-LD 入口（WebSite / Article / Breadcrumb）都在', () => {
    expect([...seo.matchAll(MARKER)].length).toBe(3)
  })

  it('每个 JSON-LD 对象都带 key', () => {
    const blocks = jsonLdBlocks(seo)
    expect(blocks.length).toBe(3)
    for (const block of blocks) {
      expect(block, `缺少 key：\n${block}`).toMatch(/\bkey:\s*['`]/)
    }
  })

  it('三条 key 各自可区分', () => {
    expect(seo).toContain('key: \'jsonld-website\'')
    expect(seo).toContain('key: `jsonld-article-${slug}`')
    expect(seo).toContain('key: \'jsonld-breadcrumb\'')
  })

  it('全文件不得再出现 hid（Vue Meta 遗产，unhead 3 不认）', () => {
    expect(seo).not.toMatch(/\bhid:/)
  })
})
