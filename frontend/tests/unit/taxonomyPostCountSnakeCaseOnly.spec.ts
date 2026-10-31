/**
 * 批次 #154：分类/标签文章数的两种命名只有一种是真的。
 *
 * 后端一个 camelCase 键都不发（`post_count` 由 SQL 聚合，`CategoryResponse`/`TagResponse`
 * 与集合口同轨），所以前台那些 `post_count ?? postsCount` 的兜底分支从未命中过；
 * 而文章载荷里嵌套的 `category.post_count` 更是恒 0 的幽灵键（模型上没这列，
 * `getattr(category, "post_count", 0)` 一直吃默认值），谁都别去读它。
 * 这里双向钉住：兜底命名不许回来，真命名不许被顺手删掉。
 */
import { readFileSync } from 'node:fs'
import { join } from 'node:path'
import { describe, expect, it } from 'vitest'

const ROOT = join(__dirname, '..', '..')
const REPO = join(ROOT, '..')

const READERS = [
  'pages/categories/index.vue',
  'pages/tags/index.vue',
  'pages/categories/[slug].vue',
  'pages/tags/[slug].vue',
  'components/SiteNavSidebar.vue'
]

function read(rel: string): string {
  return readFileSync(join(ROOT, rel), 'utf-8')
}

describe('分类/标签文章数只认后端的 snake_case', () => {
  it.each(READERS)('%s 不再读从未存在的 postsCount', (rel) => {
    const source = read(rel)
    expect(source).not.toContain('postsCount')
    expect(source).toContain('post_count')
  })

  it('类型声明里不许再留 camelCase 成员（留着等于宣称两种命名都合法）', () => {
    for (const rel of READERS) {
      expect(read(rel)).not.toMatch(/postsCount\?:/)
    }
  })

  it('后台列表页继续用真计数键（这批不许把有消费方的键一起删掉）', () => {
    expect(read('pages/admin/content/categories.vue')).toContain('post_count')
    expect(read('pages/admin/content/tags.vue')).toContain('post_count')
  })
})

describe('后端嵌套投影里的恒 0 计数已退役', () => {
  const schemas = readFileSync(join(REPO, 'backend', 'schemas', '__init__.py'), 'utf-8')

  it('不再对分类/标签实例 getattr 取 post_count 默认值', () => {
    expect(schemas).not.toContain('getattr(category, "post_count"')
    expect(schemas).not.toContain('getattr(tag, "post_count"')
  })

  it('两个 Localized 模型（只出现在文章载荷嵌套位）不声明该键', () => {
    const body = (name: string): string => {
      const start = schemas.indexOf(`class ${name}(`)
      expect(start).toBeGreaterThan(-1)
      const next = schemas.indexOf('\nclass ', start + 1)
      return schemas.slice(start, next === -1 ? schemas.length : next)
    }
    expect(body('CategoryLocalizedResponse')).not.toContain('post_count')
    expect(body('TagLocalizedResponse')).not.toContain('post_count')
    // 集合口那两份是真聚合，必须还在
    expect(body('CategoryResponse')).toContain('post_count')
    expect(body('TagResponse')).toContain('post_count')
  })
})
