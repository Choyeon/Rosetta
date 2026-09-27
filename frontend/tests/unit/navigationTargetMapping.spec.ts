/**
 * 导航 target ↔ 后端 target_blank 映射回归（useAdminManage 导航段）。
 * 曾有缺陷：读侧用 String(x.target_blank)==='_blank' 比对布尔，恒得 '_self' →
 * 后台「新窗口」Badge 永不动效、编辑重存静默把 _blank 还原成 _self。
 * 本 spec 钉死双向口径：读 NavigationResponse.target_blank(bool) → AdminNavItem.target；
 * 写 AdminNavItem.target → 请求体 target_blank(bool)。
 */
import { describe, expect, it, vi, beforeEach } from 'vitest'

const apiFetchMock = vi.fn()

vi.mock('~~/composables/useApi', () => ({
  apiFetch: (...args: unknown[]) => apiFetchMock(...args),
  silentApiFetch: (...args: unknown[]) => apiFetchMock(...args)
}))

const { fetchAdminNavigations, createAdminNavigation } = await import('~~/composables/useAdminManage')

describe('navigation target_blank mapping', () => {
  beforeEach(() => apiFetchMock.mockReset())

  it('reads boolean target_blank=true as _blank (regression: String(true) never equals _blank)', async () => {
    apiFetchMock.mockResolvedValue([
      { id: 1, title: '首页', url: '/', target_blank: false, is_active: true },
      { id: 2, title: '文档', url: 'https://docs.example.com', target_blank: true, is_active: true }
    ])
    const items = await fetchAdminNavigations()
    expect(items[0]!.target).toBe('_self')
    expect(items[1]!.target).toBe('_blank')
  })

  it('still accepts a literal target string from legacy-shaped rows', async () => {
    apiFetchMock.mockResolvedValue([
      { id: 3, label: '旧数据', url: '/about', target: '_blank' }
    ])
    const items = await fetchAdminNavigations()
    expect(items[0]!.target).toBe('_blank')
  })

  it('re-save sends target as boolean target_blank (edit round-trip cannot silently revert)', async () => {
    apiFetchMock.mockResolvedValue({ id: 3 })
    await createAdminNavigation({ label: { zh: '文档' }, url: 'https://docs.example.com', target: '_blank' })
    const [, opts] = apiFetchMock.mock.calls[0] as [string, { body: Record<string, unknown> }]
    expect(opts.body.target_blank).toBe(true)
    expect('target' in opts.body).toBe(false)
    expect('label' in opts.body).toBe(false)
  })
})
