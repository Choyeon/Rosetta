/**
 * 后台表单里 `<input type="datetime-local">` 与 ISO 字符串之间的换算。
 *
 * 这两条函数存在的唯一理由：**datetime-local 的 value 是本地墙钟，不是 UTC**。
 * 后端把朴素 datetime 按 UTC 解释（见 `backend/api/blog.py` 里 scheduled_at 的
 * `replace(tzinfo=UTC)`），所以直接 `iso.slice(0, 16)` 回填、再把输入框原值提交，
 * 在非 UTC 时区下会整体偏移一个时区差（东八区就是 8 小时）——管理员看到的
 * "10:00 发布"实际在 18:00 才生效，而且他没有任何办法察觉。
 */

function pad2(n: number): string {
  return String(n).padStart(2, '0')
}

/**
 * ISO 字符串 → `<input type="datetime-local">` 的 value（`YYYY-MM-DDTHH:mm`，本地墙钟）。
 *
 * 入参没有时区偏移时（SQLite 回读 `DateTime(timezone=True)` 列给的是朴素时间）按 UTC
 * 解释，与后端"朴素即 UTC"的口径保持一致。
 */
export function toDateTimeLocal(iso?: string | null): string {
  if (!iso) return ''
  const raw = iso.trim()
  if (!raw) return ''
  // 形如 `2026-09-30T10:00:00`（无偏移）：JS 会按本地时区解析，必须显式钉成 UTC
  const normalized = /[zZ]|[+-]\d{2}:?\d{2}$/.test(raw) ? raw : `${raw}Z`
  const d = new Date(normalized)
  if (Number.isNaN(d.getTime())) return ''
  return `${d.getFullYear()}-${pad2(d.getMonth() + 1)}-${pad2(d.getDate())}T${pad2(d.getHours())}:${pad2(d.getMinutes())}`
}

/**
 * `<input type="datetime-local">` 的 value → 带偏移的 ISO 字符串；空值返回 null。
 *
 * 返回 null 而不是 ''：后端 schema 允许显式 null 表示"清除"，传空字符串会被
 * Pydantic 判成非法 datetime 撞 422。
 */
export function fromDateTimeLocal(value?: string | null): string | null {
  const raw = (value ?? '').trim()
  if (!raw) return null
  // 不带偏移的 date-time 在 JS 里按**本地时区**解析，正是 datetime-local 输入框的语义。
  const d = new Date(raw)
  if (Number.isNaN(d.getTime())) return null
  return d.toISOString()
}

/** 该本地墙钟字符串是否已过去（用于"定时时间必须晚于现在"的前端校验）。 */
export function isPastDateTimeLocal(value?: string | null): boolean {
  const iso = fromDateTimeLocal(value)
  if (!iso) return false
  return new Date(iso).getTime() <= Date.now()
}
