/**
 * 友链「审核状态」(status) 的前后台接线守卫。
 *
 * 后端一族此前是三种半接通形状叠在一起（详见 `tests/test_friendlink_status_gate.py`
 * 的头注释），其中两条直接落在前端可见的范围里：
 *
 * 1. **管理页读的是无鉴权公开口**：`fetchAdminFriendLinks` 打
 *    `/friend-links?all=true` —— 公开口为了当管理视图而开了个后门，
 *    于是任何访客（含抓取器）都能枚举未通过审核的友链名称、URL、logo、提交时间。
 *    现在管理页走独立的 `/admin/friend-links`（staff only），公开口不再认识 `all`。
 * 2. **档位清单两处各写一份**：后台页签/下拉的档位与后端 `FriendLink.VALID_STATUSES`
 *    必须集合相等。多一档＝筛出来永远为空（分类/回收站两族都踩过），
 *    少一档＝那一档的行在管理界面里根本改不回来。
 *
 * 公开读口 (`composables/useFriendLinks.ts`) 保持"只拿公示行"，前台不需要
 * 也拿不到未审核的数据。
 */
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { describe, expect, it, vi } from 'vitest'

const apiFetchMock = vi.fn()

vi.mock('~~/composables/useApi', () => ({
  apiFetch: (...args: unknown[]) => apiFetchMock(...args),
  silentApiFetch: (...args: unknown[]) => apiFetchMock(...args)
}))

const FRONTEND = resolve(__dirname, '../..')
const REPO = resolve(FRONTEND, '..')

function readSource(path: string): string {
  return readFileSync(resolve(FRONTEND, path), 'utf8').replace(/\r\n/g, '\n')
}

const wrapper = readSource('composables/useAdminManage.ts')
const publicReader = readSource('composables/useFriendLinks.ts')
const page = readSource('pages/admin/system/friendlinks.vue')
const model = readFileSync(resolve(REPO, 'backend/models/core.py'), 'utf8').replace(/\r\n/g, '\n')

function friendLinkSection(source: string, marker: string): string {
  const start = source.indexOf(marker)
  expect(start, `找不到 ${marker}`).toBeGreaterThan(-1)
  const rest = source.slice(start + marker.length)
  const next = rest.search(/\n(?:export function|function|const \w+ = )/)
  return next === -1 ? rest : rest.slice(0, next)
}

/** 后端档位唯一清单：模型类常量。 */
const backendStatuses = [...model.matchAll(/STATUS_(PENDING|APPROVED|REJECTED) = "(\w+)"/g)].map(
  m => m[2]!
)

describe('友链管理口接线', () => {
  it('管理读口走独立的 /admin/friend-links，不再点公开口的 all 开关', async () => {
    apiFetchMock.mockResolvedValue([])
    const { fetchAdminFriendLinks } = await import('~~/composables/useAdminManage')
    await fetchAdminFriendLinks()
    expect(apiFetchMock.mock.calls[0]![0]).toBe('/admin/friend-links')

    const section = friendLinkSection(wrapper, 'export function fetchAdminFriendLinks')
    // 正则而不是字符串：本仓 lint 口径要求单引号， needle 里全是引号
    expect(section).toMatch(/apiFetch<.*>\('\/admin\/friend-links'\)/)
    expect(section).not.toContain('all=true')
    // 整个友链族都不许再出现公开管理视图的写法
    expect(wrapper).not.toContain('/friend-links?all')
  })

  it('公开读口只取公示行，且不认识 all 参数', () => {
    expect(publicReader).toMatch(/useAPI<FriendLink\[\]>\(\s*'\/friend-links'\s*,/)
    expect(publicReader).not.toContain('all')
    expect(publicReader).not.toContain('admin')
  })

  it('后台档位与后端 VALID_STATUSES 集合相等', () => {
    expect(backendStatuses).toEqual(['pending', 'approved', 'rejected'])

    const tabs = [...page.matchAll(/key: '(approved|pending|rejected|all)'/g)].map(m => m[1]!)
    // 页签含"全部"这一档是纯视图档，不进后端清单
    expect(new Set(tabs.filter(k => k !== 'all'))).toEqual(new Set(backendStatuses))

    const options = [...page.matchAll(/value="(approved|pending|rejected)"/g)].map(m => m[1]!)
    expect(new Set(options)).toEqual(new Set(backendStatuses))
    expect(options.length).toBe(3)
  })

  it('包装层保留后端档位本身，并按 status 投影镜像列', async () => {
    apiFetchMock.mockResolvedValue([
      { id: 1, name: 'A', url: 'https://a.example.com', order: 0, status: 'rejected', is_active: true },
      { id: 2, name: 'B', url: 'https://b.example.com', order: 1, status: 'pending', is_active: false },
      { id: 3, name: 'C', url: 'https://c.example.com', order: 2, status: 'approved', is_active: true }
    ])
    const { fetchAdminFriendLinks } = await import('~~/composables/useAdminManage')
    const items = await fetchAdminFriendLinks()
    expect(items.map(i => i.status)).toEqual(['rejected', 'pending', 'approved'])

    // 脏行（rejected 但镜像列还是 True）必须照档位显示，不能被镜像列翻案
    expect(items[0]!.status).toBe('rejected')
  })

  it('写口提交档位，并且 is_active 只作为兼容镜像同步', async () => {
    apiFetchMock.mockResolvedValue({ id: 7 })
    const { createAdminFriendLink } = await import('~~/composables/useAdminManage')
    await createAdminFriendLink({
      name: { zh: '友站', en: 'Friend', ja: '友', zh_Hant: '友站' },
      url: 'https://f.example.com',
      status: 'rejected',
      sort_order: 2
    })
    const [, opts] = apiFetchMock.mock.calls.at(-1) as [string, { body: Record<string, unknown> }]
    expect(opts.body.status).toBe('rejected')
    expect(opts.body.is_active).toBe(false)
    expect(opts.body.order).toBe(2)
  })

  it('管理页把每档计数显示出来（整表读口的存在理由）', () => {
    expect(page).toContain('function countOf(key: string): number')
    expect(page).toMatch(/filter = ref<typeof statusFilters\[number\]\['key'\]>\('all'\)/)
    // 服务端不做档位筛选：页签计数依赖整表
    expect(page).not.toContain('params: { status')
  })
})
