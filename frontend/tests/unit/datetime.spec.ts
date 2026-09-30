/**
 * lib/datetime.ts：datetime-local 与 ISO 的换算。
 *
 * 钉住两条静默出错的路径：
 * ① 直接 `iso.slice(0, 16)` 回填输入框（那是 UTC 钟点，非 UTC 时区差一个时区差）；
 * ② 把输入框原值当 UTC 提交（后端明确把朴素 datetime 按 UTC 解释）。
 */
import { describe, expect, it } from 'vitest'
import { fromDateTimeLocal, isPastDateTimeLocal, toDateTimeLocal } from '../../lib/datetime'

describe('toDateTimeLocal', () => {
  it('空值与非法值都回落成空串，不抛', () => {
    expect(toDateTimeLocal(null)).toBe('')
    expect(toDateTimeLocal(undefined)).toBe('')
    expect(toDateTimeLocal('')).toBe('')
    expect(toDateTimeLocal('   ')).toBe('')
    expect(toDateTimeLocal('not-a-date')).toBe('')
  })

  it('带偏移的 ISO 换算成本地墙钟', () => {
    const out = toDateTimeLocal('2026-09-30T10:00:00Z')
    // 只校验形状与"用的是本地时间分量"，具体钟点随运行环境时区变化
    expect(out).toMatch(/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}$/)
    const d = new Date('2026-09-30T10:00:00Z')
    expect(out).toBe(
      `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}T${String(d.getHours()).padStart(2, '0')}:${String(d.getMinutes()).padStart(2, '0')}`
    )
  })

  it('不带偏移的值按 UTC 解释（后端"朴素即 UTC"同口径）', () => {
    // 关键：如果这里按本地时区解释，东八区会得到 18:00 —— 与 slice(0,16) 不是一回事，
    // 但两者都错。正确行为是把 10:00 当成 10:00Z 再显示成本地。
    const naive = toDateTimeLocal('2026-09-30T10:00:00')
    const aware = toDateTimeLocal('2026-09-30T10:00:00Z')
    expect(naive).toBe(aware)
  })
})

describe('fromDateTimeLocal', () => {
  it('空值返回 null 而不是空串（后端只接受 datetime 或 null）', () => {
    expect(fromDateTimeLocal('')).toBeNull()
    expect(fromDateTimeLocal(null)).toBeNull()
    expect(fromDateTimeLocal('  ')).toBeNull()
  })

  it('输出带偏移的 ISO', () => {
    const iso = fromDateTimeLocal('2026-09-30T10:00')
    expect(iso).toBeTruthy()
    expect(iso).toMatch(/T\d{2}:\d{2}:\d{2}\.\d{3}Z$/)
    // 与本地墙钟解析结果一致：说明提交侧没有把本地时间当 UTC 用
    expect(iso).toBe(new Date('2026-09-30T10:00').toISOString())
  })

  it('往返不丢精度（ISO → 输入框 → ISO 指向同一时刻）', () => {
    const original = '2026-12-01T08:30:00Z'
    const roundTrip = fromDateTimeLocal(toDateTimeLocal(original))
    expect(roundTrip).toBeTruthy()
    // datetime-local 只到分钟，秒与毫秒本来就会丢；比较到分钟即可
    expect(new Date(roundTrip!).getTime()).toBe(new Date(original).getTime())
  })
})

describe('isPastDateTimeLocal', () => {
  it('过去的时间判为已过去，空值不算过去', () => {
    expect(isPastDateTimeLocal('2020-01-01T00:00')).toBe(true)
    expect(isPastDateTimeLocal('')).toBe(false)
    expect(isPastDateTimeLocal(null)).toBe(false)
  })
})
