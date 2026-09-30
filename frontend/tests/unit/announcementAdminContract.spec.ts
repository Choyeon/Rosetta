/**
 * 公告系统的跨端契约守卫（扫源码文本，不挂组件）。
 *
 * 这几条不变量全是"写法"层面的：类型检查和单测都不会报错，但线上会立刻出问题——
 * ① 公告正文上限前后端必须同值，否则管理员在前端能写、提交才被 422 弹回；
 * ② 排期字段此前后端一直支持而 UI 完全不可达（只能改库），表单控件被删就会悄悄退化；
 * ③ 清空排期要发 null 而不是 ''；
 * ④ AdminAnnouncement 的 title/content 必须是字符串——写成 i18n dict 联合类型
 *    就会逼出永远走不到的 dict 分支（历史上真的有过）；
 * ⑤ 公告写路径发的钩子事件必须在 WEBHOOK_EVENTS 里登记，否则后台订阅 UI 里
 *    看不到这几个事件、配了也订阅不上。
 */
import { describe, expect, it } from 'vitest'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

const read = (rel: string) => readFileSync(resolve(process.cwd(), rel), 'utf8')

describe('公告正文上限前后端同值', () => {
  it('lib/announcement.ts 的 ANNOUNCEMENT_CONTENT_MAX 等于后端常量', () => {
    const backend = read('../backend/schemas/announcement.py')
    const m = backend.match(/^ANNOUNCEMENT_CONTENT_MAX_LENGTH\s*=\s*(\d+)/m)
    expect(m, '未能在 backend/schemas/announcement.py 找到 ANNOUNCEMENT_CONTENT_MAX_LENGTH').toBeTruthy()

    const frontend = read('lib/announcement.ts')
    const f = frontend.match(/ANNOUNCEMENT_CONTENT_MAX\s*=\s*(\d+)/)
    expect(f, '未能在 lib/announcement.ts 找到 ANNOUNCEMENT_CONTENT_MAX').toBeTruthy()
    expect(Number(f![1])).toBe(Number(m![1]))
  })
})

describe('后台公告表单必须能编辑排期与排序', () => {
  const page = read('pages/admin/interaction/announcements.vue')

  it('表单含 sort_order / start_time / end_time 三个控件', () => {
    expect(page).toMatch(/id="ann-sort"/)
    expect(page).toMatch(/id="ann-start"/)
    expect(page).toMatch(/id="ann-end"/)
    expect(page).toMatch(/type="datetime-local"/)
  })

  it('提交前把 datetime-local 的空串换成 null（后端只接受 datetime 或 null）', () => {
    expect(page).toMatch(/start_time:\s*fromDateTimeLocal\(/)
    expect(page).toMatch(/end_time:\s*fromDateTimeLocal\(/)
  })

  it('提交前本地校验时间窗，别让管理员等 422', () => {
    expect(page).toMatch(/announcementScheduleError\(/)
  })

  it('列表给出排期状态列（否则管理员看不出某条为何没展示）', () => {
    expect(page).toMatch(/announcementStatus\(/)
    expect(page).toMatch(/statusText\(/)
  })

  it('不再用 eslint-disable 整文件关检查', () => {
    expect(page).not.toMatch(/eslint-disable/)
  })

  it('表单字段名与后端一致（content / is_active，不是 content_md / active）', () => {
    expect(page).not.toMatch(/content_md/)
    expect(page).toMatch(/v-model="form\.is_active"/)
  })
})

describe('AdminAnnouncement 类型贴合后端 AnnouncementResponse', () => {
  const src = read('composables/useAdminManage.ts')
  const m = src.match(/export interface AdminAnnouncement \{([\s\S]*?)\n\}/)
  expect(m, '未找到 AdminAnnouncement 接口').toBeTruthy()
  const body = m![1]!

  it('title / content 是明文字符串，不是 i18n dict', () => {
    expect(body).toMatch(/^\s*title:\s*string$/m)
    expect(body).toMatch(/^\s*content:\s*string$/m)
    expect(body).not.toMatch(/Record<string,\s*string>/)
  })

  it('带齐 start_time / end_time / sort_order / updated_at', () => {
    expect(body).toMatch(/start_time/)
    expect(body).toMatch(/end_time/)
    expect(body).toMatch(/sort_order/)
    expect(body).toMatch(/updated_at/)
  })
})

describe('公告钩子事件必须在 Webhook 事件清单里登记', () => {
  it('backend/api/webhook.py::WEBHOOK_EVENTS 含三个 announcement 事件', () => {
    const src = read('../backend/api/webhook.py')
    const m = src.match(/WEBHOOK_EVENTS\s*=\s*\{([\s\S]*?)\n\}/)
    expect(m, '未找到 WEBHOOK_EVENTS').toBeTruthy()
    const block = m![1]!
    for (const name of ['announcement.created', 'announcement.updated', 'announcement.deleted']) {
      expect(block, `WEBHOOK_EVENTS 缺少 ${name}`).toContain(`"${name}"`)
    }
  })

  it('公告 API 的写路径确实发了这三个同名事件', () => {
    const src = read('../backend/api/announcement.py')
    for (const name of ['announcement.created', 'announcement.updated', 'announcement.deleted']) {
      expect(src, `announcement.py 未触发 ${name}`).toContain(`do_action("${name}"`)
    }
  })
})

describe('公告写操作必须清前台页面缓存', () => {
  it('announcement.py 调用 purge_frontend_page_cache（前台每页 SSR 都带公告条）', () => {
    const src = read('../backend/api/announcement.py')
    expect(src).toMatch(/from backend\.services\.frontend_cache_purge import purge_frontend_page_cache/)
    // 四个写路径都要清：create / update / delete / toggle
    expect(src.match(/_purge\("/g)?.length ?? 0).toBeGreaterThanOrEqual(4)
  })
})
