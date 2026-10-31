/**
 * 层级分类（Category.parent_id）在两端的接线契约。
 *
 * 这一列的历史形状是"库里永远 NULL"：模型有列、迁移建过索引、ORM 配了 parent/children，
 * 但 schema 不认、写口不收、读口不回吐、后台没控件、前台没渲染——所以层级从未存在过。
 * 后端那半由 `tests/test_category_parent_wiring.py` 钉（写入可定父、PUT 可改可清、
 * 自指/后代/未知父级一律 400 且一行不动、预热投影与读侧同形、删父级只把子级提到顶级），
 * 这里钉前端这半：
 *
 * 1. `lib/category-tree.ts` 的三条不变量必须是真的（下面按实现跑用例，不读源码猜）：
 *    一条行都不能从结果里消失、环与悬空父级都不能让遍历死循环、id 两形（number/string）混比要成立。
 * 2. 后台必须回填并**始终发送** parent_id（PUT 是 exclude_unset 增量语义，
 *    省略键 = 不改它 = "提到顶级"这个操作根本发不出去），父级候选必须排掉自己与自己的后代。
 * 3. 前台子分类页必须有祖先面包屑与子分类入口，且 JSON-LD 面包屑跟同一条祖先链——
 *    缺子分类入口时，第二层分类除了直接 URL 就是零入链，爬虫发现不了、访客也走不到。
 * 4. 「子分类」这个公开文案必须四语齐全（前台 SSR 页面直接渲染它）。
 */

import { describe, it, expect } from 'vitest'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import {
  buildCategoryTree,
  categoryAncestorPath,
  categoryChildren,
  categoryDescendantIds
} from '~~/lib/category-tree'

const categoriesPage = readFileSync(resolve(process.cwd(), 'pages/admin/content/categories.vue'), 'utf8')
const publicCategoryPage = readFileSync(resolve(process.cwd(), 'pages/categories/[slug].vue'), 'utf8')
const manageSrc = readFileSync(resolve(process.cwd(), 'composables/useAdminManage.ts'), 'utf8')

interface Row {
  id: number | string
  parent_id?: number | string | null
  name?: string
}
const rows = (...pairs: Array<[number | string, number | string | null | undefined]>): Row[] =>
  pairs.map(([id, parent_id]) => ({ id, parent_id }))

describe('lib/category-tree 的展开算术', () => {
  it('父在前、子紧随、孙再缩一档，同层保持输入顺序', () => {
    // 输入故意乱序：结果顺序必须只由层级决定，兄弟之间才沿用后端顺序
    const flat = buildCategoryTree(rows([3, 1], [1, null], [4, 3], [2, null], [5, 2]))
    expect(flat.map(e => `${e.item.id}@${e.depth}`)).toEqual(['1@0', '3@1', '4@2', '2@0', '5@1'])
  })

  it('一条都不能少：悬空父级与自指按顶级落回列表', () => {
    // 父级被删（SET NULL 没跑到 / 旧缓存载荷）与自指都能出现在库里；
    // 后台少一行就等于那条分类再也改不动——这是本文件存在的首要理由。
    const flat = buildCategoryTree(rows([1, 999], [2, 2], [3, null]))
    expect(flat.map(e => e.item.id).sort()).toEqual([1, 2, 3])
    expect(flat.every(e => e.depth === 0)).toBe(true)
  })

  it('环上的分类不死循环，且仍出现在列表里', () => {
    const cyclic = rows([1, 2], [2, 1], [3, 4], [4, 3])
    const flat = buildCategoryTree(cyclic)
    expect(flat.map(e => e.item.id).sort()).toEqual([1, 2, 3, 4])
  })

  it('id 混形（number 父、string 子）照样成树——比较一律走字符串键', () => {
    const flat = buildCategoryTree([{ id: 1 }, { id: '2', parent_id: 1 }, { id: 3, parent_id: '1' }])
    expect(flat.map(e => `${e.item.id}@${e.depth}`)).toEqual(['1@0', '2@1', '3@1'])
  })

  it('后代集合用于排除"选了就是环"的候选，不含自身', () => {
    const all = rows([1, null], [2, 1], [3, 2], [4, null])
    expect([...categoryDescendantIds(all, 1)].sort()).toEqual(['2', '3'])
    expect([...categoryDescendantIds(all, '1')].sort()).toEqual(['2', '3'])
    expect(categoryDescendantIds(all, 4).size).toBe(0)
    expect(categoryDescendantIds(all, null).size).toBe(0)
    // 环不会把 BFS 变成死循环
    expect([...categoryDescendantIds(rows([1, 2], [2, 1]), 1)].sort()).toEqual(['1', '2'])
  })

  it('祖先链由远及近、不含自身；父级不在列表里就整链为空', () => {
    const all = rows([1, null], [2, 1], [3, 2])
    expect(categoryAncestorPath(all, 3).map(r => r.id)).toEqual([1, 2])
    expect(categoryAncestorPath(all, 1)).toEqual([])
    expect(categoryAncestorPath(all, 99)).toEqual([])
    expect(categoryAncestorPath(all, null)).toEqual([])
    // 环上的上溯必须终止（走到 visited 就停），而不是把栈撑爆
    expect(categoryAncestorPath(rows([1, 2], [2, 1]), 1).map(r => r.id)).toEqual([2])
  })

  it('直接子分类只取一层，且永不把自身算进去', () => {
    const all = rows([1, null], [2, 1], [3, 1], [4, 2])
    expect(categoryChildren(all, 1).map(r => r.id)).toEqual([2, 3])
    expect(categoryChildren(all, 2).map(r => r.id)).toEqual([4])
    expect(categoryChildren(all, 1).map(r => r.id)).not.toContain(1)
    expect(categoryChildren(all, '4')).toEqual([])
  })
})

describe('后台分类页的层级写入', () => {
  it('表单有 parent_id 项，编辑必须回填、重置必须清空', () => {
    expect(categoriesPage).toContain('parent_id: null')
    // 不回填则每次 PUT 提交 null：子分类在"改一次名字"后被静默提到顶级
    expect(categoriesPage).toContain('form.parent_id = normalizeParentId(cat.parent_id)')
    expect(categoriesPage).toContain('form.parent_id = null')
  })

  it('提交始终带这个键，提到顶级靠 null 而不是省略键', () => {
    expect(categoriesPage).toContain('parent_id: form.parent_id')
    expect(manageSrc).toContain('if (payload.parent_id !== undefined) body.parent_id = payload.parent_id')
  })

  it('父级候选排除自己与自己的全部后代', () => {
    expect(categoriesPage).toContain('categoryDescendantIds(categories.value, editingId.value)')
    expect(categoriesPage).toMatch(/key !== selfKey && !excluded\.has\(key\)/)
  })

  it('库里躺着无法解析的 parent_id 时归成顶级，不把 400 留在提交那一步', () => {
    expect(categoriesPage).toContain('const normalizeParentId = (raw: unknown): number | null =>')
    // 候选按字符串键比对（id 有 number|string 两形），解析不出就归顶级
    expect(categoriesPage).toContain('parentOptions.value.find(cat => String(cat.id) === key)')
    expect(categoriesPage).toContain('return hit ? Number(hit.id) : null')
  })

  it('列表按树形顺序渲染并显示缩进层级', () => {
    expect(categoriesPage).toContain('buildCategoryTree(categories.value)')
    expect(categoriesPage).toContain(':data="categoryRows"')
    expect(categoriesPage).toContain('indentOf(row as AdminCategory)')
  })

  it('父分类选择器有"顶级"这一档（提交 null，不是缺键）', () => {
    expect(categoriesPage).toContain('<Select v-model="form.parent_id">')
    expect(categoriesPage).toContain('<SelectItem :value="null">')
  })
})

describe('前台分类页消费层级', () => {
  it('祖先面包屑与子分类入口都从公开列表算，且共用同一把缓存键', () => {
    expect(publicCategoryPage).toContain('key: `blog:categories:${locale.value}`')
    expect(publicCategoryPage).toContain('categoryAncestorPath(catList.value, p.id)')
    expect(publicCategoryPage).toContain('categoryChildren(catList.value, catRaw.value?.id)')
  })

  it('子分类入口挂在页面上，且只在分类存在时出现', () => {
    expect(publicCategoryPage).toContain('data-testid="category-children"')
    expect(publicCategoryPage).toContain('data-testid="category-child-link"')
    expect(publicCategoryPage).toContain('v-if="!catNotFound && childCategories.length > 0"')
    // 爬虫读到的必须是真实 href（localeHref 挂语言前缀），不能是纯 button
    expect(publicCategoryPage).toMatch(/:to="localeHref\(`\/categories\/\$\{child\.slug\}`\)"/)
  })

  it('祖先链同时进 JSON-LD 面包屑，且传 computed 而不是静态数组', () => {
    expect(publicCategoryPage).toContain('useBreadcrumbJsonLd(computed<BreadcrumbItem[]>(() => [')
    expect(publicCategoryPage).toContain('...ancestorTrail.value.map(')
  })

  it('父级停用 / 取不到时整段收起，不链去访客打不开的分类页', () => {
    // parentCategory 只在公开列表里找得到那一行时才返回，ancestorTrail 据此回落空数组
    expect(publicCategoryPage).toContain('catList.value.find(row => String(row.id) === String(pid)) ?? null')
    expect(publicCategoryPage).toContain('if (!p) return []')
  })
})

describe('「子分类」文案四语齐全', () => {
  const locales = ['zh', 'en', 'ja', 'zh_Hant'] as const
  for (const code of locales) {
    it(`${code} 有 categories.subcategories`, () => {
      const dict = JSON.parse(
        readFileSync(resolve(process.cwd(), `i18n/locales/${code}.json`), 'utf8')
      ) as Record<string, { subcategories?: string }>
      const value = dict.categories?.subcategories
      expect(typeof value).toBe('string')
      // 空串会渲染成一个没有文字的标签块；照抄英文则等于该语言从未翻译过
      expect((value ?? '').trim()).not.toBe('')
      if (code !== 'en') expect(value).not.toBe('Subcategories')
    })
  }
})
