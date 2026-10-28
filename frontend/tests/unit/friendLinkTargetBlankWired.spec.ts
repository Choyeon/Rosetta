/**
 * 友情链接「新窗口打开」(target_blank) 的后台接线守卫。
 *
 * 后端一族（列 / Create / Update / Response / Localized / CRUD）与前台读取端
 * `pages/friends.vue` 都是通的，缺的只有后台：包装层 `mapFriendLink` 不映射这个布尔、
 * 管理页 payload 从不提交 —— 于是管理员没有任何控件能决定访客点开友链是换页还是开新窗口，
 * 而这一位又确实被线上 HTML 消费（和已修的导航 target 同一种半接通形状）。
 *
 * 三条口径：
 * * 布尔只能用 `=== true` 判：导航一族曾用 `String(x.target_blank) === '_blank'` 比对布尔，
 *   恒 false，"后台勾了新窗口、前台永远当前页打开"。
 * * 写口 `sort_order → order` 的既有改名规则不得顺手吞掉 `target_blank`。
 * * 编辑口必须回填，否则每次保存都把已设好的新窗口改回当前页。
 */
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { describe, expect, it, vi, beforeEach } from 'vitest'

const apiFetchMock = vi.fn()

vi.mock('~~/composables/useApi', () => ({
  apiFetch: (...args: unknown[]) => apiFetchMock(...args),
  silentApiFetch: (...args: unknown[]) => apiFetchMock(...args)
}))

const ROOT = resolve(__dirname, '../..')
function readSource(path: string): string {
  return readFileSync(resolve(ROOT, path), 'utf8').replace(/\r\n/g, '\n')
}
const wrapper = readSource('composables/useAdminManage.ts')
const page = readSource('pages/admin/system/friendlinks.vue')
const reader = readSource('pages/friends.vue')

const { fetchAdminFriendLinks, createAdminFriendLink, updateAdminFriendLink }
  = await import('~~/composables/useAdminManage')

function lastBody(): Record<string, unknown> {
  const [, opts] = apiFetchMock.mock.calls.at(-1) as [string, { body: Record<string, unknown> }]
  return opts.body
}

describe('友链 target_blank 读写接线', () => {
  beforeEach(() => apiFetchMock.mockReset())

  it('读侧把布尔 target_blank 映射进 AdminFriendLink（不是字符串比对）', async () => {
    apiFetchMock.mockResolvedValue([
      { id: 1, name: '站内', url: '/about', order: 0, status: 'approved', target_blank: false },
      { id: 2, name: '友站', url: 'https://f.example.com', order: 1, status: 'approved', target_blank: true }
    ])
    const items = await fetchAdminFriendLinks()
    expect(items[0]!.target_blank).toBe(false)
    expect(items[1]!.target_blank).toBe(true)
    // 缺字段的老行按 false 处理，不能是 undefined（模板里要做真值判断）
    apiFetchMock.mockResolvedValue([{ id: 3, name: '旧数据', url: '/x', status: 'approved' }])
    const legacy = await fetchAdminFriendLinks()
    expect(legacy[0]!.target_blank).toBe(false)
  })

  it('写口提交布尔 target_blank，且 sort_order→order 改名不吞掉它', async () => {
    apiFetchMock.mockResolvedValue({ id: 9 })
    await createAdminFriendLink({
      name: { zh: '友站', en: 'Friend', ja: '友', zh_Hant: '友站' },
      url: 'https://f.example.com',
      status: 'approved',
      sort_order: 3,
      target_blank: true
    })
    const body = lastBody()
    expect(body.target_blank).toBe(true)
    expect(body.order).toBe(3)
    expect('sort_order' in body).toBe(false)

    await updateAdminFriendLink(9, { status: 'pending', sort_order: 1, target_blank: false })
    const putBody = lastBody()
    expect(putBody.target_blank).toBe(false)
    expect(putBody.is_active).toBe(false)
  })

  it('管理页有开关、编辑回填、payload 提交，卡片预览也按布尔渲染', () => {
    expect(page).toContain('v-model="form.target_blank"')
    expect(page).toContain('target_blank: false')
    expect(page).toContain('target_blank: link.target_blank')
    expect(page).toContain('target_blank: form.value.target_blank === true')
    expect(page).toContain(':target="link.target_blank ? ')
    expect(page).toContain('import { Switch } from')
    // 卡片预览过去写死 target="_blank"，管理员看不到访客真实行为
    expect(page).not.toContain('target="_blank"')
  })

  it('读侧与后端字段名同轨：包装层与 pages/friends.vue 都读 target_blank', () => {
    expect(wrapper).toContain('target_blank: r.target_blank === true')
    expect(reader).toContain(':target="friend.target_blank ? ')
    // 导航一族的反例不得在这一族复发
    expect(wrapper).not.toContain('String(r.target_blank)')
    expect(page).not.toContain('String(link.target_blank)')
  })
})
