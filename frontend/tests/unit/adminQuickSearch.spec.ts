/**
 * 顶栏「快速跳转」契约：搜索框曾经是死的（placeholder 承诺 Ctrl+K，敲词回车毫无反应）。
 * 候选唯一真源是 config/admin-menu，匹配口径也写在那里；这里同时钉住
 * 纯函数行为与 AdminHeader 的接线，防止再退回无处理器的输入框。
 */

import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { describe, expect, it } from 'vitest'
import { adminMenuFlat, filterAdminMenuItems } from '../../config/admin-menu'

const headerSrc = readFileSync(
  resolve(__dirname, '..', '..', 'components/admin/AdminHeader.vue'),
  'utf-8'
)

describe('filterAdminMenuItems', () => {
  it('空查询不返回候选（下拉只在真的打字时出现）', () => {
    expect(filterAdminMenuItems('')).toEqual([])
    expect(filterAdminMenuItems('   ')).toEqual([])
  })

  it('按菜单名匹配', () => {
    expect(filterAdminMenuItems('文章').map(i => i.path)).toContain('/admin/content/posts')
  })

  it('按路径匹配且大小写不敏感', () => {
    expect(filterAdminMenuItems('seo').map(i => i.path)).toContain('/admin/tools/seo')
    expect(filterAdminMenuItems('WEBHOOK').map(i => i.path)).toContain('/admin/system/webhooks')
  })

  it('候选数有上限，且全部来自菜单真源', () => {
    const matches = filterAdminMenuItems('admin')
    expect(matches.length).toBeGreaterThan(1)
    expect(matches.length).toBeLessThanOrEqual(8)
    for (const item of matches) expect(adminMenuFlat).toContain(item)
  })
})

describe('AdminHeader 快速跳转接线', () => {
  it('输入框必须真的被绑定并被键盘驱动', () => {
    expect(headerSrc).toContain('v-model="quickQuery"')
    expect(headerSrc).toContain('@keydown="onQuickKeydown"')
    expect(headerSrc).toContain('filterAdminMenuItems')
    expect(headerSrc).toContain("!== 'k'")
  })

  it('placeholder 里的快捷键承诺必须与监听一致', () => {
    expect(headerSrc).toContain('Ctrl+K')
    expect(headerSrc).toContain("addEventListener('keydown', onGlobalKeydown)")
    expect(headerSrc).toContain("removeEventListener('keydown', onGlobalKeydown)")
  })
})
