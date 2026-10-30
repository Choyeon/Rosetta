/**
 * 自定义内容类型（Content Type / ACF）API 封装。
 *
 * 四段式里的「消费方」这一段只有两个职责：
 * 1. **后台编辑器**读定义（`/admin/content-types`）决定渲染哪些自定义字段；
 * 2. **公开文章页**读定义（`/content-types`，匿名可读 + 300s 缓存）决定展示哪些 meta。
 *
 * 硬契约：
 * - 后端返回**裸数组/裸对象**，没有 `{success,data}` 信封（与 series 同口径）。
 * - `fields[].label` / 类型 `name` 都是**单字符串**，不是四语 dict —— 不要套
 *   `getLocalizedStr`，那会把字符串当对象解构出空串。
 * - 读侧必须宽容：定义可以在有文章之后被改（删字段/改必填），历史文章的
 *   `meta_fields` 可能留着定义之外的键。展示侧只渲染"定义里存在且值非空"的键，
 *   写侧才按定义校验——把这条校验搬到读侧，一次定义调整就会让一批详情页报错。
 * - 定义变更会改变 SSR 页面上的字段卡片，所以后端写口已在响应前清前台页面缓存；
 *   这里的读缓存（公开定义 300s）是后端第二层，前端不再叠内存缓存。
 */
import { apiFetch } from '~~/composables/useApi'

/** 后端 `models/content_type.py::FIELD_TYPES` 的镜像。新增类型要两处同改。 */
export const CONTENT_FIELD_TYPES = [
  'text',
  'textarea',
  'number',
  'boolean',
  'select',
  'date',
  'datetime',
  'image',
  'url',
  'markdown'
] as const

export type ContentFieldType = typeof CONTENT_FIELD_TYPES[number]

/** 字段键与后端 ContentField.key 的 pattern 同口径（小写字母开头，仅小写/数字/下划线）。 */
export const CONTENT_FIELD_KEY_PATTERN = /^[a-z][a-z0-9_]{0,63}$/
/** 类型 key 与后端 ContentTypeCreate.key 的 pattern 同口径。 */
export const CONTENT_TYPE_KEY_PATTERN = /^[a-z][a-z0-9_-]{0,49}$/

export interface ContentFieldDef {
  key: string
  label: string
  field_type: ContentFieldType
  required: boolean
  default?: unknown
  description?: string | null
  options?: string[] | null
}

export interface ContentTypePublic {
  key: string
  name: string
  icon?: string | null
  description?: string | null
  fields: ContentFieldDef[]
}

export interface AdminContentType extends ContentTypePublic {
  id: number
  posts_count: number
}

/** 后端 `ContentField` 的 `extra=forbid` + `field_type` 约束：脏条目整条丢弃而不是半截渲染。 */
function _toField(raw: unknown): ContentFieldDef | null {
  if (typeof raw !== 'object' || raw === null) return null
  const r = raw as Record<string, unknown>
  const key = String(r.key ?? '')
  const fieldType = String(r.field_type ?? '')
  if (!CONTENT_FIELD_KEY_PATTERN.test(key)) return null
  if (!(CONTENT_FIELD_TYPES as readonly string[]).includes(fieldType)) return null
  const options = Array.isArray(r.options)
    ? r.options.map(o => String(o)).filter(o => o !== '')
    : null
  if (fieldType === 'select' && !options?.length) return null
  return {
    key,
    label: String(r.label ?? key),
    field_type: fieldType as ContentFieldType,
    required: r.required === true,
    default: r.default ?? undefined,
    description: typeof r.description === 'string' ? r.description : null,
    options: fieldType === 'select' ? options : null
  }
}

function _toPublic(raw: unknown): ContentTypePublic | null {
  if (typeof raw !== 'object' || raw === null) return null
  const r = raw as Record<string, unknown>
  const key = String(r.key ?? '')
  if (!CONTENT_TYPE_KEY_PATTERN.test(key)) return null
  const fields = Array.isArray(r.fields)
    ? r.fields.map(_toField).filter((f): f is ContentFieldDef => f !== null)
    : []
  return {
    key,
    name: String(r.name ?? key),
    icon: typeof r.icon === 'string' ? r.icon : null,
    description: typeof r.description === 'string' ? r.description : null,
    fields
  }
}

/**
 * 裸响应 → 定义数组的唯一解析入口。
 * 公开文章页用 `$fetch`（不走 `apiFetch`，理由见该页 `useAsyncData` 的取数口径），
 * 拿到的是同一份裸数组，解析必须复用这一条而不是再写一遍 isinstance——
 * 否则字段类型清单改动只会红其中一边。
 */
export function parseContentTypes(raw: unknown): ContentTypePublic[] {
  const rows = Array.isArray(raw) ? raw : []
  return rows.map(_toPublic).filter((t): t is ContentTypePublic => t !== null)
}

/**
 * GET /api/content-types（匿名）——公开文章页按 `post_type` 找定义用。
 * 失败返回空数组：内容类型是**装饰数据**，取不到时文章页要正常渲染正文，
 * 不能因为定义接口抖一下就整页 500。
 */
export async function fetchContentTypes(): Promise<ContentTypePublic[]> {
  try {
    return parseContentTypes(await apiFetch<unknown>('/content-types', { silentToast: true }))
  } catch (e) {
    console.warn('[content-types] 公开定义读取失败，文章页将不展示自定义字段', e)
    return []
  }
}

/** GET /api/admin/content-types —— 列表带 `posts_count`（删前提示"仍被 N 篇文章使用"的真值）。 */
export async function fetchAdminContentTypes(): Promise<AdminContentType[]> {
  const raw = await apiFetch<unknown>('/admin/content-types')
  const rows = Array.isArray(raw) ? raw : []
  return rows
    .map((row): AdminContentType | null => {
      const pub = _toPublic(row)
      if (!pub || typeof row !== 'object' || row === null) return null
      const r = row as Record<string, unknown>
      return { ...pub, id: Number(r.id) || 0, posts_count: Number(r.posts_count) || 0 }
    })
    .filter((t): t is AdminContentType => t !== null && t.id > 0)
}

export type ContentTypePayload = Omit<ContentTypePublic, 'fields'> & {
  fields: ContentFieldDef[]
}

/** POST /api/admin/content-types —— key 创建后不可变（PUT schema 里根本没有这个键）。 */
export async function createAdminContentType(payload: ContentTypePayload): Promise<AdminContentType> {
  const raw = await apiFetch<unknown>('/admin/content-types', { method: 'POST', body: payload })
  const pub = _toPublic(raw)
  const r = (raw ?? {}) as Record<string, unknown>
  return {
    ...(pub ?? { key: payload.key, name: payload.name, icon: null, description: null, fields: [] }),
    id: Number(r.id) || 0,
    posts_count: Number(r.posts_count) || 0
  }
}

/** PUT /api/admin/content-types/{key} —— 请求体禁止带 key（extra=forbid 会直接 422）。 */
export async function updateAdminContentType(
  key: string,
  payload: Omit<ContentTypePayload, 'key'>
): Promise<AdminContentType> {
  const raw = await apiFetch<unknown>(`/admin/content-types/${encodeURIComponent(key)}`, {
    method: 'PUT',
    body: payload
  })
  const pub = _toPublic(raw)
  const r = (raw ?? {}) as Record<string, unknown>
  return {
    ...(pub ?? { key, name: payload.name, icon: null, description: null, fields: [] }),
    id: Number(r.id) || 0,
    posts_count: Number(r.posts_count) || 0
  }
}

/**
 * DELETE /api/admin/content-types/{key}
 * 仍被文章引用时后端回 409（含 posts_count），apiFetch 会把 message toast 出来，
 * 这里不再重复包装——调用方只需 catch 后保持弹窗打开。
 */
export async function deleteAdminContentType(key: string): Promise<void> {
  await apiFetch(`/admin/content-types/${encodeURIComponent(key)}`, { method: 'DELETE' })
}

/** 按 key 找定义（后台编辑器与公开页共用；找不到返回 null = 内建 post 或已被删除）。 */
export function findContentType(
  types: readonly ContentTypePublic[],
  key: string | null | undefined
): ContentTypePublic | null {
  if (!key) return null
  return types.find(t => t.key === key) ?? null
}

/**
 * 从定义里挑出"要展示的键"：定义中存在 + 值非空。
 * `meta_fields` 里的额外键（历史脏数据 / 已删字段）一律不展示，但**不报错**——
 * 读侧宽容是这条链的红线（见 backend/models/content_type.py 的模块说明）。
 */
export function visibleMetaFields(
  type: ContentTypePublic | null,
  meta: Record<string, unknown> | null | undefined
): Array<{ field: ContentFieldDef, value: unknown }> {
  if (!type || !meta) return []
  const rows: Array<{ field: ContentFieldDef, value: unknown }> = []
  for (const field of type.fields) {
    const value = meta[field.key]
    if (value === undefined || value === null || value === '') continue
    if (Array.isArray(value) && value.length === 0) continue
    rows.push({ field, value })
  }
  return rows
}
