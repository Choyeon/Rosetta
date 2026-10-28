/**
 * 分类「启用/停用」（`is_active`）后台接线的守卫。
 *
 * 此前这一族是**半接通**：`Category.is_active` 列存在（迁移里带 `server_default=true`），
 * 但请求/响应模型都不带这一项、后台分类页也没有开关 —— 停用一个分类只能改库，
 * 而标签页早已把这一项做成了可见可控的字段。两个页面对不齐时，
 * 运营者会按标签的经验去分类页找那个根本不存在的开关。
 *
 * 四条口径必须钉住：
 * * 后台列表的数据源必须带 `?all=true`：公开口只回启用行，用它当数据源的话
 *   「停用」是单向按钮 —— 一关就从后台消失，再也无法打开（标签页此前正是这个形状）。
 * * `is_active` 必须同时出现在类型、默认值、编辑回填、提交载荷里，少一处即"改了不保存"。
 * * 编辑回填必须容忍缺键（响应缓存里可能还是上线前的旧形状），
 *   否则打开一次编辑弹窗就把没动的分类判成停用。
 * * 后端 `?all=` 的缺省必须是 `False`：默认值翻成 true 等于把停用行投给前台访客。
 */
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { describe, expect, it } from 'vitest'

const ROOT = resolve(__dirname, '../..')

// 仓库混用 CRLF 与 LF：多行标记必须先归一，否则 indexOf 永远找不到
function readSource(rel: string): string {
  return readFileSync(resolve(ROOT, rel), 'utf8').replace(/\r\n/g, '\n')
}

const composable = readSource('composables/useAdminManage.ts')
const categoriesPage = readSource('pages/admin/content/categories.vue')
const tagsPage = readSource('pages/admin/content/tags.vue')
const blogApi = readSource('../backend/api/blog.py')

describe('分类启停后台接线', () => {
  it('AdminCategory 类型声明这一项（缺类型时载荷会被 TS 拦掉，改口即静默丢字段）', () => {
    const iface = composable.slice(
      composable.indexOf('export interface AdminCategory'),
      composable.indexOf('export interface AdminTag')
    )
    expect(iface).toContain('is_active: boolean')
  })

  it('分类与标签的后台列表都从 ?all=true 取数（否则停用是单向按钮）', () => {
    for (const [fn, path] of [
      ['fetchAdminCategories', '/blog/categories'],
      ['fetchAdminTags', '/blog/tags']
    ] as const) {
      const body = composable.slice(composable.indexOf(`export function ${fn}`))
      const slice = body.slice(0, body.indexOf('\n}\n'))
      expect(slice, `${fn} 找不到`).toContain(path)
      expect(slice, `${fn} 的列表数据源必须带 all=true`).toContain('query: { all: true }')
    }
  })

  it('后端 ?all= 的缺省是 False（公开列表默认摘掉停用行）', () => {
    for (const [fn, allKey, activeKey] of [
      ['async def list_categories(', 'CACHE_KEY_CATEGORIES_ALL', 'CACHE_KEY_CATEGORIES'],
      ['async def list_tags(', 'CACHE_KEY_TAGS_ALL', 'CACHE_KEY_TAGS']
    ] as const) {
      const body = blogApi.slice(blogApi.indexOf(fn))
      const slice = body.slice(0, body.indexOf('\n@router'))
      expect(slice, `${fn} 定位失败`).not.toBe('')
      expect(slice).toContain('all: bool = Query(False')
      // 判别位进了 WHERE 就必须进缓存键，否则后台一次 all=true 就把停用行烘进前台键位
      expect(slice).toContain(`${allKey} if all else ${activeKey}`)
      expect(slice).toContain('if not all:')
    }
  })

  it('分类页把这一项当开关渲染，并与标签页同构', () => {
    expect(categoriesPage).toContain('is_active: boolean')
    expect(categoriesPage).toContain('is_active: true')
    expect(categoriesPage).toContain('form.is_active = true')
    // 缺键按启用：响应缓存里可能还是上线前的旧形状
    expect(categoriesPage).toContain('form.is_active = cat.is_active ?? true')
    expect(categoriesPage).toContain('is_active: form.is_active')
    expect(categoriesPage).toMatch(/key: 'is_active', title: '状态'/)
    expect(categoriesPage).toContain('id="category-form-active"')
    expect(categoriesPage).toContain('v-model="form.is_active"')
    // 两个页面必须保持同构：标签页少一个开关与分类页多一个开关都是缺陷
    expect(tagsPage).toContain('v-model="form.is_active"')
    expect(tagsPage).toMatch(/key: 'is_active', title: '状态'/)
  })
})
