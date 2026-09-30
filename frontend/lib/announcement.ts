/**
 * 公告的纯逻辑（排期换算 + 状态判定），刻意脱离 .vue 以便单测。
 *
 * 硬契约（与后端 schemas/announcement.py、api/announcement.py 对齐）：
 * · `start_time` / `end_time` 后端存的是 `DateTime(timezone=True)`，序列化成带偏移的
 *   ISO 字符串；**朴素值一律按 UTC 补齐**（后端 `_ensure_utc` 同口径）。前端这里负责
 *   把它换算成 `<input type="datetime-local">` 的本地墙钟字符串，再换回带偏移的 ISO。
 *   （换算函数实际住在 `lib/datetime.ts`，公告与文章排期共用同一套口径。）
 * · 谁在过滤：公开接口 `GET /announcements` 已经按 `is_active + 时间窗` 过滤，前端
 *   **不得**拿 `announcementStatus()` 去决定前台横幅显不显示（口径会漂）——
 *   它只服务于后台列表的"这条为什么没在展示"的状态列。
 * · 正文上限 2000：与后端 `ANNOUNCEMENT_CONTENT_MAX_LENGTH` 同值，
 *   `announcementAdmin.spec.ts` 有一条跨端对齐断言钉住它。
 */

/** 与 backend/schemas/announcement.py::ANNOUNCEMENT_CONTENT_MAX_LENGTH 同值。 */
export const ANNOUNCEMENT_CONTENT_MAX = 2000

/** 公告排期相关的字段子集——后台列表行与表单行都够用，不需要整条 AnnouncementResponse。 */
export interface AnnouncementSchedule {
  is_active: boolean
  start_time?: string | null
  end_time?: string | null
}

/** 后台列表状态列的四种取值；`active` 特指"已启用且当前在窗口内"。 */
export type AnnouncementStatus = 'active' | 'scheduled' | 'expired' | 'disabled'

// datetime-local 的换算是跨模块口径（公告排期、文章定时发布都要用），
// 实现在 lib/datetime.ts，这里转出以保持既有 import 路径不变。
export { toDateTimeLocal, fromDateTimeLocal, isPastDateTimeLocal } from './datetime'

/**
 * 这条公告当前处于哪个阶段（仅用于后台展示，不参与前台过滤）。
 *
 * 判定边界必须和后端一致：后端是 `start_time <= now AND end_time >= now`，
 * 所以"还没到"是 `start > now`，"已过期"是 `end < now`，端点值本身都属于生效中。
 */
export function announcementStatus(
  row: AnnouncementSchedule,
  now: Date = new Date()
): AnnouncementStatus {
  if (!row.is_active) return 'disabled'
  const nowMs = now.getTime()
  const startMs = row.start_time ? new Date(row.start_time).getTime() : null
  const endMs = row.end_time ? new Date(row.end_time).getTime() : null
  if (startMs !== null && !Number.isNaN(startMs) && startMs > nowMs) return 'scheduled'
  if (endMs !== null && !Number.isNaN(endMs) && endMs < nowMs) return 'expired'
  return 'active'
}

/**
 * 表单侧的排期自检：结束时间必须晚于开始时间，且都传或都不传的语义由调用方保证。
 * 后端会再判一次（防绕过），这里只是为了让管理员在提交前就看到原因。
 */
export function announcementScheduleError(
  startTimeLocal: string,
  endTimeLocal: string
): string | null {
  if (!startTimeLocal || !endTimeLocal) return null
  const start = new Date(startTimeLocal).getTime()
  const end = new Date(endTimeLocal).getTime()
  if (Number.isNaN(start) || Number.isNaN(end)) return '时间格式不正确'
  if (end <= start) return '结束时间必须晚于开始时间'
  return null
}
