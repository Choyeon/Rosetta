/**
 * 后台媒体库的排序入口（批次 #223）。
 *
 * `GET /api/media/library` 的 `sort_by` / `sort_order` 支持了很久（`_SORTABLE` 四个字段），
 * 但 `pages/admin/media/library.vue` 从来不发这两个参数，也没有任何控件：管理员只能在
 * 「最新上传」这一条顺序里翻页，找大文件、按名核对都做不了。
 * 这一族最容易烂在两个地方，所以两侧一起钉：
 *   ① UI 的排序选项集合必须与后端 `_SORTABLE` 的键集合**相等**。
 *      多一个＝选了它后端静默回落 created_at（表现是"排序没生效"，接口一个错都不报）；
 *      少一个＝后端能力没接（就是本批修掉的缺陷）。
 *   ② 参数必须真的从页面流到请求里（`AdminMediaQuery` 声明 + fetchData 实参），
 *      只在 ref 里存着等于什么都没接。
 */

import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { describe, expect, it } from 'vitest'

const ROOT = resolve(__dirname, '..', '..')
const REPO = resolve(ROOT, '..')

const read = (path: string) => readFileSync(resolve(path), 'utf-8').replace(/\r\n/g, '\n')

const PAGE = read(resolve(ROOT, 'pages/admin/media/library.vue'))
const WRAPPER = read(resolve(ROOT, 'composables/useAdminManage.ts'))
const BACKEND = read(resolve(REPO, 'backend/api/media.py'))

/** 后端排序白名单的唯一清单（`_SORTABLE` 的键）。 */
const backendSortable = (): string[] => {
  const block = BACKEND.match(/_SORTABLE = \{[\s\S]*?\n {4}\}/)?.[0] ?? ''
  return [...block.matchAll(/"(\w+)":\s*Media\./g)].map(m => m[1] as string)
}

/** 页面排序下拉的唯一清单（`MEDIA_SORT_FIELDS` 的字面量）。 */
const pageSortFields = (): string[] => {
  const literal = PAGE.match(/const MEDIA_SORT_FIELDS = \[([^\]]*)\] as const/)?.[1] ?? ''
  return [...literal.matchAll(/'([^']+)'/g)].map(m => m[1] as string)
}

describe('media library 排序', () => {
  it('UI 的排序字段集合与后端 _SORTABLE 的键集合相等', () => {
    expect(backendSortable().length, '后端 _SORTABLE 没解析出来').toBeGreaterThan(0)
    expect(pageSortFields().sort()).toEqual(backendSortable().sort())
  })

  it('后端 sort_by 的文档把每个可排序字段都列出来（选项不得是未声明能力）', () => {
    const desc = BACKEND.match(/sort_by: str = Query\([\s\S]*?\)/)?.[0] ?? ''
    expect(desc).not.toBe('')
    for (const column of backendSortable()) {
      expect(desc, `sort_by 的 Query 描述缺少 ${column}`).toContain(column)
    }
  })

  it('排序状态有初值，且类型收口在后端白名单内', () => {
    expect(PAGE).toContain('const sortBy = ref<MediaSortField>(\'created_at\')')
    expect(PAGE).toContain('const sortOrder = ref<\'asc\' | \'desc\'>(\'desc\')')
    // 服务端默认是 created_at desc：初值不同就会让首屏与地址栏判成两套顺序。
    // 用正则读：ruff format 会按行宽把这一条折行，写死整行会假红。
    expect(BACKEND).toMatch(/sort_by: str = Query\(\s*"created_at"/)
    expect(BACKEND).toMatch(/sort_order: str = Query\(\s*"desc"/)
    // 下拉的值先过白名单判定，非白名单值不得进请求
    expect(PAGE).toContain('const isMediaSortField = (value: unknown): value is MediaSortField =>')
  })

  it('两个参数都进了请求，且封装层接得住（不声明就被 TS 丢掉）', () => {
    const call = PAGE.match(/fetchAdminMediaLibrary\(\{[\s\S]*?\n\s*\}\)/)?.[0] ?? ''
    expect(call).toContain('sort_by: sortBy.value')
    expect(call).toContain('sort_order: sortOrder.value')
    const query = WRAPPER.match(/interface AdminMediaQuery \{[\s\S]*?\n\}/)?.[0] ?? ''
    expect(query).toContain('sort_by?: \'created_at\' | \'file_size\' | \'filename\' | \'updated_at\'')
    expect(query).toContain('sort_order?: \'asc\' | \'desc\'')
    // params 整份展开进 query：只加接口不加发送＝点了没反应
    expect(WRAPPER).toContain('...params')
  })

  it('控件是真的：字段下拉由清单驱动，方向切换是独立按钮', () => {
    const sortSelect = PAGE.match(/<Select\n\s+:model-value="sortBy"[\s\S]*?<\/Select>/)?.[0] ?? ''
    expect(sortSelect, '找不到绑定 sortBy 的排序下拉').not.toBe('')
    expect(sortSelect).toContain('v-for="field in MEDIA_SORT_FIELDS"')
    expect(sortSelect).toContain(':value="field"')
    expect(sortSelect).toContain('{{ SORT_LABELS[field] }}')
    expect(sortSelect).toContain('aria-label="排序字段"')
    expect(sortSelect).toContain('@update:model-value="onSortChange"')
    const toggle = PAGE.match(/<Button\n\s+variant="outline"\n\s+size="icon-sm"\n\s+:title=[\s\S]*?<\/Button>/)?.[0] ?? ''
    expect(toggle, '找不到排序方向按钮').not.toBe('')
    expect(toggle).toContain('@click="toggleSortOrder"')
    expect(toggle).toContain(':aria-label="sortOrder ===')
    // §10.2：Button 子树里的图标必须带 data-icon，且不再手写尺寸
    expect(toggle).toContain('data-icon="inline-start"')
    expect(toggle).not.toMatch(/class="size-4/)
    expect(PAGE).toContain('ArrowDownWideNarrow, ArrowUpNarrowWide')
  })

  it('每个字段都有中文标签，漏一个下拉里就是一个空白项', () => {
    const labels = PAGE.match(/const SORT_LABELS: Record<MediaSortField, string> = \{[\s\S]*?\n\}/)?.[0] ?? ''
    for (const field of pageSortFields()) {
      expect(labels, `SORT_LABELS 缺少 ${field}`).toContain(`  ${field}: `)
    }
  })

  it('换排序与换筛选同构：回到第 1 页并清选中', () => {
    const onSortChange = PAGE.match(/function onSortChange\(value: unknown\) \{[\s\S]*?\n\}/)?.[0] ?? ''
    expect(onSortChange).toContain('sortBy.value = value')
    expect(onSortChange).toContain('applyFilter()')
    const toggleOrder = PAGE.match(/function toggleSortOrder\(\) \{[\s\S]*?\n\}/)?.[0] ?? ''
    expect(toggleOrder).toContain('sortOrder.value = sortOrder.value === \'asc\' ? \'desc\' : \'asc\'')
    expect(toggleOrder).toContain('applyFilter()')
    const applyFilter = PAGE.match(/function applyFilter\(\) \{[\s\S]*?\n\}/)?.[0] ?? ''
    expect(applyFilter).toContain('selectedIds.value = []')
    expect(applyFilter).toContain('page.value = 1')
  })
})
