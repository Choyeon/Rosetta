// 内容型 slug 前后端口径一致性：slugify 的每个产出必须能通过 CONTENT_SLUG_PATTERN，
// 该正则又必须与后端 backend/schemas/_slug.py::CONTENT_SLUG_PATTERN 逐字符同构，
// 且 admin 四个 taxonomy 页面不得再私有化 ASCII-only 校验（中文 slug 回归的温床）。
import { readFileSync } from 'node:fs'
import { describe, expect, it } from 'vitest'
import { CONTENT_SLUG_PATTERN, slugify } from '@/composables/useAdminI18n'

const root = process.cwd().replace(/[\\/]$/, '')

describe('slugify 产出恒通过 CONTENT_SLUG_PATTERN', () => {
  const samples = [
    '中文分类',
    'Hello World',
    'Qoder 端到端 测试',
    'v2.0 发布!!',
    '  前后端--协同  ',
    'post 1快速上手',
    '混ENG文456'
  ]
  for (const s of samples) {
    it(`slugify(${JSON.stringify(s)}) 合法`, () => {
      const out = slugify(s)
      expect(out).not.toBe('')
      expect(CONTENT_SLUG_PATTERN.test(out)).toBe(true)
    })
  }
})

describe('CONTENT_SLUG_PATTERN 拒绝结构字符', () => {
  for (const bad of ['../../etc/passwd', 'a b', '<script>', 'a%2Db', 'Hello', 'path/x', 'a\\b']) {
    it(`拒绝 ${JSON.stringify(bad)}`, () => {
      expect(CONTENT_SLUG_PATTERN.test(bad)).toBe(false)
    })
  }
  it('接受中文/下划线/连字符', () => {
    expect(CONTENT_SLUG_PATTERN.test('中文_slug-1')).toBe(true)
  })
})

describe('与后端 CONTENT_SLUG_PATTERN 单源同构', () => {
  it('正则字面量与 backend/schemas/_slug.py 完全一致', () => {
    const py = readFileSync(`${root}/../backend/schemas/_slug.py`, 'utf8')
    const m = py.match(/CONTENT_SLUG_PATTERN = r"(.+?)"/)
    expect(m).not.toBeNull()
    expect(CONTENT_SLUG_PATTERN.source).toBe(m![1])
  })
})

describe('admin taxonomy 页面不得私有化 ASCII-only slug 校验', () => {
  const pages = [
    'pages/admin/content/categories.vue',
    'pages/admin/content/tags.vue',
    'pages/admin/content/series.vue',
    'pages/admin/content/pages.vue'
  ]
  for (const p of pages) {
    it(`${p} 只使用共享的 CONTENT_SLUG_PATTERN`, () => {
      const src = readFileSync(`${root}/${p}`, 'utf8')
      expect(src).not.toMatch(/\[a-z0-9-\]\+\$/)
      expect(src).toMatch(/CONTENT_SLUG_PATTERN/)
    })
  }
})
