/**
 * 公告排期换算与状态判定（lib/announcement.ts）。
 *
 * 钉住三件容易静默出错的事：
 * ① ISO 与 `<input type="datetime-local">` 的换算必须走本地墙钟。直接 `iso.slice(0,16)`
 *    拿的是 UTC 钟点，UTC+8 的管理员会看到差 8 小时的时间，改完排期才发现生效时刻不对。
 * ② 清空输入框必须发 null 而不是 '' —— 后端 `AnnouncementUpdate` 只接受 datetime 或 null，
 *    空串会被 Pydantic 判成非法 datetime 撞 422，"取消排期"这个操作就直接废了。
 * ③ 状态边界必须和后端过滤条件一致（`start<=now AND end>=now`）：端点值本身属于生效中，
 *    前端判成"待开始/已结束"就会出现"后台说还没开始、前台已经在展示"的对不上。
 */
import { describe, expect, it } from 'vitest'
import {
  ANNOUNCEMENT_CONTENT_MAX,
  announcementScheduleError,
  announcementStatus,
  fromDateTimeLocal,
  toDateTimeLocal,
  type AnnouncementSchedule
} from '../../lib/announcement'

const NOW = new Date('2026-09-29T12:00:00Z')
const row = (over: Partial<AnnouncementSchedule> = {}): AnnouncementSchedule => ({
  is_active: true,
  start_time: null,
  end_time: null,
  ...over
})

describe('toDateTimeLocal / fromDateTimeLocal', () => {
  it('空值双向安全', () => {
    expect(toDateTimeLocal(null)).toBe('')
    expect(toDateTimeLocal(undefined)).toBe('')
    expect(toDateTimeLocal('')).toBe('')
    expect(fromDateTimeLocal('')).toBeNull()
    expect(fromDateTimeLocal(null)).toBeNull()
    expect(fromDateTimeLocal('   ')).toBeNull()
  })

  it('输出 datetime-local 要求的 YYYY-MM-DDTHH:mm 形状', () => {
    expect(toDateTimeLocal('2026-09-29T10:30:00Z')).toMatch(/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}$/)
  })

  it('换算不丢时刻：ISO → 本地输入框 → ISO 回到同一瞬间', () => {
    const iso = '2026-09-29T10:30:00Z'
    const back = fromDateTimeLocal(toDateTimeLocal(iso))
    expect(back, '往返后应仍是合法 ISO').toBeTruthy()
    expect(new Date(back!).getTime()).toBe(new Date(iso).getTime())
  })

  it('datetime-local 的朴素值按本地时区解析，并输出带 Z 的 ISO', () => {
    const out = fromDateTimeLocal('2026-09-29T10:00')
    expect(out).toBeTruthy()
    expect(out!.endsWith('Z')).toBe(true)
    expect(new Date(out!).getTime()).toBe(new Date('2026-09-29T10:00').getTime())
  })

  it('垃圾输入返回 null 而不是抛错', () => {
    expect(fromDateTimeLocal('不是时间')).toBeNull()
  })
})

describe('announcementStatus', () => {
  it('未启用优先于时间窗：一律已停用', () => {
    expect(announcementStatus(row({ is_active: false }), NOW)).toBe('disabled')
    expect(
      announcementStatus(
        row({ is_active: false, start_time: '2026-09-29T13:00:00Z' }),
        NOW
      )
    ).toBe('disabled')
  })

  it('无排期即展示中', () => {
    expect(announcementStatus(row(), NOW)).toBe('active')
  })

  it('开始时间未到 → 待开始', () => {
    expect(announcementStatus(row({ start_time: '2026-09-29T12:00:01Z' }), NOW)).toBe('scheduled')
  })

  it('结束时间已过 → 已结束', () => {
    expect(announcementStatus(row({ end_time: '2026-09-29T11:59:59Z' }), NOW)).toBe('expired')
  })

  it('端点值本身算生效中（与后端 start<=now / end>=now 同口径）', () => {
    expect(announcementStatus(row({ start_time: '2026-09-29T12:00:00Z' }), NOW)).toBe('active')
    expect(announcementStatus(row({ end_time: '2026-09-29T12:00:00Z' }), NOW)).toBe('active')
  })

  it('非法时间串不参与判定，退化成展示中而不是崩掉', () => {
    expect(announcementStatus(row({ start_time: 'garbage' }), NOW)).toBe('active')
    expect(announcementStatus(row({ end_time: 'garbage' }), NOW)).toBe('active')
  })
})

describe('announcementScheduleError', () => {
  it('结束时间不晚于开始时间要报错', () => {
    expect(announcementScheduleError('2026-09-29T10:00', '2026-09-29T10:00')).toContain('晚于')
    expect(announcementScheduleError('2026-09-29T10:00', '2026-09-29T09:00')).toContain('晚于')
  })

  it('顺序正确或只填一边时不拦（后端会做合并后的最终校验）', () => {
    expect(announcementScheduleError('2026-09-29T10:00', '2026-09-30T10:00')).toBeNull()
    expect(announcementScheduleError('', '2026-09-30T10:00')).toBeNull()
    expect(announcementScheduleError('2026-09-29T10:00', '')).toBeNull()
    expect(announcementScheduleError('', '')).toBeNull()
  })
})

describe('正文上限', () => {
  it('与前端提示用的是同一个常量，且是合理上限', () => {
    expect(ANNOUNCEMENT_CONTENT_MAX).toBeGreaterThan(0)
    expect(ANNOUNCEMENT_CONTENT_MAX).toBeLessThanOrEqual(10000)
  })
})
