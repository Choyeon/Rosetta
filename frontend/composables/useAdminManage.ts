/* eslint-disable @typescript-eslint/ban-ts-comment */
// @ts-nocheck
/* eslint-enable @typescript-eslint/ban-ts-comment */
/**
 * 后台管理页（仪表盘 / 评论 / 用户 / 分类·标签 / 站点设置）API 封装。
 * 全部基于 useAPI.ts 的 apiFetch（自动注入 Authorization 与 Accept-Language），
 * 不依赖 useAdmin.ts（其解包方式与当前后端格式不完全一致）。
 *
 * 路径规则：
 * - 后端 include_router 前缀在 backend/main.py 统一装配
 * - 前端 apiFetch 的相对路径（不带 /api 前缀）将自动拼接 useRuntimeConfig().public.apiBase
 */
import {
  apiFetch,
  silentApiFetch
} from '~~/composables/useApi'

// ========= 轻量级内存缓存（短 TTL） =========
// 用于用户编辑页、头衔选择等"同一轮交互内反复读取、数据基本不变"的场景。
// 避免进入页面时并行发起多条相同的 GET，给人"加载慢"的感知。
type CacheEntry<T> = { value: T, expiresAt: number }
const MEM_CACHE = new Map<string, CacheEntry<unknown>>()
const MEM_TTL_MS = 60 * 1000 // 1 分钟内不重复打后端

function cachedGet<T>(key: string, loader: () => Promise<T>, ttl = MEM_TTL_MS): Promise<T> {
  const now = Date.now()
  const cached = MEM_CACHE.get(key) as CacheEntry<T> | undefined
  if (cached && cached.expiresAt > now) return Promise.resolve(cached.value)
  const p = loader().then((v) => {
    MEM_CACHE.set(key, { value: v, expiresAt: Date.now() + ttl })
    return v
  })
  // 同时让并发请求共享同一个 Promise，避免重复请求
  MEM_CACHE.set(key, { value: p as unknown as T, expiresAt: Date.now() + Math.min(ttl, 10000) })
  return p
}

/** 清理某条缓存（写操作后调用，确保下次读拿到最新值） */
export function invalidateMemCache(keyPrefix?: string) {
  if (!keyPrefix) {
    MEM_CACHE.clear()
    return
  }
  for (const k of Array.from(MEM_CACHE.keys())) {
    if (k.startsWith(keyPrefix)) MEM_CACHE.delete(k)
  }
}

// ==================== 通用类型 ====================

/** 后端统一 { success, data, message } 包装 */
interface ApiEnvelope<T> {
  success: boolean
  data: T
  message?: string
}

/** 仅含 message 的操作结果（BaseResponse / 普通dict） */
export interface ApiMessage {
  success?: boolean
  message?: string
}

/** 后端分页结构（多数管理端点直接返回，不套 envelope） */
export interface AdminPaged<T> {
  items: T[]
  total: number
  page: number
  page_size: number
  total_pages: number
}

/** ISO 时间格式化为 YYYY-MM-DD（空值返回占位符） */
export function formatAdminDate(iso: string | null | undefined, placeholder = '-'): string {
  if (!iso) return placeholder
  const d = new Date(iso)
  if (Number.isNaN(d.getTime())) return placeholder
  const y = d.getFullYear()
  const m = String(d.getMonth() + 1).padStart(2, '0')
  const day = String(d.getDate()).padStart(2, '0')
  return `${y}-${m}-${day}`
}

/** ISO 时间格式化为 YYYY-MM-DD HH:mm */
export function formatAdminDateTime(iso: string | null | undefined, placeholder = '-'): string {
  if (!iso) return placeholder
  const d = new Date(iso)
  if (Number.isNaN(d.getTime())) return placeholder
  const hh = String(d.getHours()).padStart(2, '0')
  const mm = String(d.getMinutes()).padStart(2, '0')
  return `${formatAdminDate(iso, placeholder)} ${hh}:${mm}`
}

// ==================== 仪表盘 ====================

export type StatsRange = '7d' | '30d'

export interface DashboardSummary {
  total_posts: number
  total_drafts: number
  total_published: number
  total_comments: number
  total_pending_comments: number
  total_users: number
  total_views_today: number
  total_comments_today: number
}

export interface TimeseriesDataset {
  key: string
  values: number[]
}

export interface DashboardTimeseries {
  labels: string[]
  datasets: TimeseriesDataset[]
}

export interface TopArticle {
  id: number
  title: string
  views: number
  comments_count: number
}

export interface ActiveCommenter {
  name: string
  avatar: string | null
  comments_count: number
}

export interface SystemHealth {
  cpu_percent: number | null
  memory_percent: number | null
  db_rtt_ms: number | null
  cache_hit_percent: number | null
  health_score: number | null
}

export interface DashboardStats {
  timeseries: DashboardTimeseries
  top_articles: TopArticle[]
  active_commenters: ActiveCommenter[]
  system_health: SystemHealth
  summary: DashboardSummary
}

/** GET /api/admin/stats —— stats.router 挂在 /api/admin，@router.get("/stats") */
export function fetchDashboardStats(range: StatsRange = '7d'): Promise<DashboardStats> {
  return apiFetch<ApiEnvelope<DashboardStats>>('/admin/stats', {
    query: { range }
  }).then(res => res.data)
}

export interface AdminPostListItem {
  id: number
  title: string
  slug: string
  status: string
  views: number
  likes_count: number
  comments_count: number
  is_pinned: boolean
  created_at: string | null
  published_at: string | null
  category: { id: number, name: string, color?: string | null } | null
}

/**
 * 近期文章：并行请求已发布与草稿两个列表（GET /api/blog/posts?status=...，
 * 需 staff 登录态），按时间倒序合并取前 limit 篇。单个请求失败不影响另一路数据。
 */
export async function fetchRecentPosts(limit = 8): Promise<AdminPostListItem[]> {
  const [pub, draft] = await Promise.allSettled([
    apiFetch<AdminPaged<AdminPostListItem>>('/blog/posts', {
      query: { page: 1, page_size: limit, status: 'published' }
    }),
    apiFetch<AdminPaged<AdminPostListItem>>('/blog/posts', {
      query: { page: 1, page_size: Math.min(limit, 3), status: 'draft' }
    })
  ])
  const merged: AdminPostListItem[] = [
    ...(pub.status === 'fulfilled' ? pub.value.items : []),
    ...(draft.status === 'fulfilled' ? draft.value.items : [])
  ]
  const timeOf = (p: AdminPostListItem): number =>
    new Date(p.published_at ?? p.created_at ?? 0).getTime() || 0
  return merged.sort((a, b) => timeOf(b) - timeOf(a)).slice(0, limit)
}

export interface FetchAdminPostsParams {
  page?: number
  page_size?: number
  search?: string
  status?: 'all' | 'published' | 'draft' | 'scheduled' | 'archived'
  category?: string
  created_start?: string | null
  created_end?: string | null
}

export interface FetchAdminPostsResult<T> {
  items: T[]
  total: number
}

/**
 * 后台文章管理列表数据加载（基于 GET /api/blog/posts，需 staff 登录态）：
 * - status=具体值：服务端按该 status 过滤并分页
 * - status='all'：并行请求 4 种 status（published / draft / scheduled / archived），
 *   客户端合并去重、应用 search/category 过滤，再按时间倒序做本地分页。
 *   单个请求失败不阻断其他状态数据合并，避免整片列表为空。
 */
export async function fetchAdminPostsPaged<T extends AdminPostListItem>(
  params: FetchAdminPostsParams
): Promise<FetchAdminPostsResult<T>> {
  const page = Math.max(1, params.page ?? 1)
  const pageSize = Math.max(1, params.page_size ?? 10)
  const qSearch = params.search?.trim() || ''
  const qCategory = params.category && params.category !== 'all' ? params.category : undefined
  const qCreatedStart = params.created_start || undefined
  const qCreatedEnd = params.created_end || undefined

  const statuses: Array<'published' | 'draft' | 'scheduled' | 'archived'>
    = !params.status || params.status === 'all'
      ? ['published', 'draft', 'scheduled', 'archived']
      : [params.status as 'published' | 'draft' | 'scheduled' | 'archived']

  const commonQuery = {
    search: qSearch || undefined,
    category: qCategory,
    created_start: qCreatedStart,
    created_end: qCreatedEnd
  }

  // 特定单 status：直接走服务端分页，简单高效
  if (statuses.length === 1) {
    const paged = await apiFetch<AdminPaged<T>>('/blog/posts', {
      query: {
        page,
        page_size: pageSize,
        status: statuses[0],
        ...commonQuery
      }
    })
    return { items: paged.items ?? [], total: paged.total ?? 0 }
  }

  // status='all' 合并模式：每种 status 拉取足够大的一页，客户端统一处理
  // 注意：后端 list_posts 的 page_size 上限为 le=100（PaginatedResponse 同为 le=100），
  // 超过会 422。这里封顶 100，避免触发参数校验失败。
  const bigBatch = Math.min(100, Math.max(50, pageSize * 20))
  const results = await Promise.allSettled(
    statuses.map(s =>
      apiFetch<AdminPaged<T>>('/blog/posts', {
        query: {
          page: 1,
          page_size: bigBatch,
          status: s,
          ...commonQuery
        }
      })
    )
  )

  const seen = new Set<number>()
  const merged: T[] = []
  for (const r of results) {
    if (r.status !== 'fulfilled') continue
    for (const item of (r.value.items ?? []) as T[]) {
      if (seen.has(item.id)) continue
      seen.add(item.id)
      merged.push(item)
    }
  }

  const getLocalized = (v: string | Record<string, string> | null | undefined): string => {
    if (v == null) return ''
    if (typeof v === 'string') return v
    return Object.values(v)[0] || ''
  }

  // 客户端 search 兜底（服务端对非 published 的 search 可能不稳定）
  let filtered = merged
  if (qSearch) {
    const q = qSearch.toLowerCase()
    filtered = filtered.filter((p) => {
      const title = getLocalized(p.title as unknown as string | Record<string, string> | null | undefined).toLowerCase()
      const slug = String(p.slug ?? '').toLowerCase()
      return title.includes(q) || slug.includes(q)
    })
  }

  // 客户端日期范围兜底（合并模式下对多 status 结果再做一次本地校验）
  if (qCreatedStart || qCreatedEnd) {
    const startTs = qCreatedStart ? new Date(qCreatedStart + 'T00:00:00').getTime() : -Infinity
    const endTs = qCreatedEnd ? new Date(qCreatedEnd + 'T23:59:59.999').getTime() : Infinity
    filtered = filtered.filter((p) => {
      const t = new Date(p.created_at ?? p.published_at ?? 0).getTime() || 0
      return t >= startTs && t <= endTs
    })
  }

  // 时间倒序：优先 published_at，其次 created_at
  const timeOf = (p: T): number => new Date(p.published_at ?? p.created_at ?? 0).getTime() || 0
  filtered.sort((a, b) => timeOf(b) - timeOf(a))

  const total = filtered.length
  const start = (page - 1) * pageSize
  const items = filtered.slice(start, start + pageSize)
  return { items, total }
}

// ==================== 评论管理 ====================

export type AdminCommentStatus = 'approved' | 'pending' | 'rejected' | 'spam'
export type AdminCommentStatusFilter = AdminCommentStatus | 'all'

export interface AdminCommentPostRef {
  id: number
  slug: string | null
  title: string | null
}

export interface AdminComment {
  id: number
  post_id: number
  parent_id: number | null
  author_name: string
  resolved_avatar_url: string | null
  author_email: string | null
  content: string
  status: AdminCommentStatus | string
  active: boolean
  likes_count: number
  reply_total: number
  created_at: string | null
  post_ref: AdminCommentPostRef | null
  title?: { id?: number, name: string, icon?: string, color?: string } | null
}

export interface AdminCommentQuery {
  page?: number
  page_size?: number
  status?: AdminCommentStatusFilter
  keyword?: string
}

/** GET /api/admin/comments —— admin.router 挂在 /api/admin，@router.get("/comments") */
export function fetchAdminComments(params: AdminCommentQuery): Promise<AdminPaged<AdminComment>> {
  const query: Record<string, unknown> = {
    page: params.page ?? 1,
    page_size: params.page_size ?? 20
  }
  if (params.status && params.status !== 'all') query.status = params.status
  if (params.keyword && params.keyword.trim()) query.keyword = params.keyword.trim()
  return apiFetch<AdminPaged<AdminComment>>('/admin/comments', { query })
}

/** PATCH /api/admin/comments/{id} —— admin.router @router.patch("/comments/{comment_id}") */
export function updateAdminCommentStatus(
  commentId: number,
  status: AdminCommentStatus
): Promise<AdminComment> {
  return apiFetch<AdminComment>(`/admin/comments/${commentId}`, {
    method: 'PATCH',
    body: { status }
  })
}

/** DELETE /api/admin/comments/{id} —— admin.router @router.delete("/comments/{comment_id}") */
export function deleteAdminComment(commentId: number): Promise<ApiMessage> {
  return apiFetch<ApiMessage>(`/admin/comments/${commentId}`, { method: 'DELETE' })
}

export type CommentBatchActionType = 'approve' | 'reject' | 'spam' | 'delete'

/** POST /api/admin/comments/batch —— comments.router 挂在 /api，内部 @router.post("/admin/comments/batch") */
export function batchAdminComments(
  ids: number[],
  action: CommentBatchActionType
): Promise<ApiMessage> {
  return apiFetch<ApiMessage>('/admin/comments/batch', {
    method: 'POST',
    body: { ids: ids.slice(0, 100), action }
  })
}

export interface ReplyCommentResult {
  id: number
  content: string
  created_at: string | null
}

/**
 * POST /api/blog/posts/{postId}/comments —— blog.router 挂在 /api/blog，
 * 内部 @router.post("/posts/{post_id_or_slug}/comments")
 * 后端嵌套回复限制 1 层：目标一律为根评论（parent_id 为空时用自身 id）。
 */
export function replyToComment(
  postId: number,
  rootCommentId: number,
  content: string
): Promise<ReplyCommentResult> {
  return apiFetch<ReplyCommentResult>(`/blog/posts/${postId}/comments`, {
    method: 'POST',
    body: { content, parent_id: rootCommentId }
  })
}

// ==================== 用户管理 ====================

export interface AdminUserRow {
  id: number
  username: string
  email: string
  nickname: string | null
  avatar: string | null
  resolved_avatar_url: string | null
  is_active: boolean
  is_staff: boolean
  is_superuser: boolean
  role?: string | null
  is_banned: boolean
  created_at: string | null
  last_login: string | null
  posts_count: number
  comments_count: number
  title?: AdminUserTitle | null
  title_id?: number | null
}

/** RBAC 角色定义（应与后端 backend.core.rbac 保持一致） */
export const RBAC_ROLES = [
  { value: 'super_admin', label: '超级管理员' },
  { value: 'admin', label: '管理员' },
  { value: 'editor', label: '编辑' },
  { value: 'author', label: '作者' },
  { value: 'contributor', label: '投稿者' },
  { value: 'subscriber', label: '订阅者' }
] as const

export type RbacRoleValue = (typeof RBAC_ROLES)[number]['value']

export function rbacRoleLabel(role?: string | null): string {
  return RBAC_ROLES.find(r => r.value === role)?.label ?? '订阅者'
}

export interface AdminUserQuery {
  page?: number
  page_size?: number
  search?: string
  sort?: string
  order?: string
}

/** GET /api/users —— users.router 挂在 /api/users，@router.get("/") 分页列表 */
export function fetchAdminUsers(params: AdminUserQuery): Promise<AdminPaged<AdminUserRow>> {
  const query: Record<string, unknown> = {
    page: params.page ?? 1,
    page_size: params.page_size ?? 20
  }
  if (params.search && params.search.trim()) query.search = params.search.trim()
  if (params.sort) query.sort = params.sort
  if (params.order) query.order = params.order
  const qs = new URLSearchParams(query as Record<string, string>).toString()
  return cachedGet(
    `admin:users:list:${qs || 'default'}`,
    () => apiFetch<AdminPaged<AdminUserRow>>('/users', { query }),
    20 * 1000 // 用户列表短暂缓存，避免进入编辑页再回列表时重复拉
  )
}

export interface AdminUserPatchResult {
  id: number
  username: string
  email: string
  nickname: string | null
  avatar: string | null
  is_active: boolean
  is_staff: boolean
  is_superuser: boolean
  role?: string | null
  is_banned: boolean
}

export interface AdminUserFlags {
  is_staff?: boolean
  is_active?: boolean
  is_banned?: boolean
}

/** PATCH /api/admin/users/{id} —— admin.router @router.patch("/users/{user_id}") */
export function updateAdminUserFlags(
  userId: number,
  flags: AdminUserFlags
): Promise<AdminUserPatchResult> {
  invalidateMemCache(`admin:users:detail:${userId}`)
  invalidateMemCache('admin:users:list:')
  return apiFetch<AdminUserPatchResult>(`/admin/users/${userId}`, {
    method: 'PATCH',
    body: flags
  })
}

/** PATCH /api/admin/users/{id} 设置 RBAC 角色（后端 admin.router 已支持 role 字段） */
export function updateAdminUserRole(
  userId: number,
  role: string
): Promise<AdminUserPatchResult> {
  invalidateMemCache(`admin:users:detail:${userId}`)
  invalidateMemCache('admin:users:list:')
  return apiFetch<AdminUserPatchResult>(`/admin/users/${userId}`, {
    method: 'PATCH',
    body: { role }
  })
}

/** POST /api/admin/users/{id}/activate —— admin.router @router.post("/users/{user_id}/activate") */
export function activateAdminUser(userId: number): Promise<ApiMessage> {
  invalidateMemCache(`admin:users:detail:${userId}`)
  invalidateMemCache('admin:users:list:')
  return apiFetch<ApiMessage>(`/admin/users/${userId}/activate`, { method: 'POST' })
}

/** POST /api/admin/users/{id}/ban —— admin.router @router.post("/users/{user_id}/ban") */
export function banAdminUser(userId: number): Promise<ApiMessage> {
  invalidateMemCache(`admin:users:detail:${userId}`)
  invalidateMemCache('admin:users:list:')
  return apiFetch<ApiMessage>(`/admin/users/${userId}/ban`, { method: 'POST' })
}

/** POST /api/admin/users/{id}/unban —— admin.router @router.post("/users/{user_id}/unban") */
export function unbanAdminUser(userId: number): Promise<ApiMessage> {
  invalidateMemCache(`admin:users:detail:${userId}`)
  invalidateMemCache('admin:users:list:')
  return apiFetch<ApiMessage>(`/admin/users/${userId}/unban`, { method: 'POST' })
}

/** POST /api/admin/users/{id}/reset-password —— admin.router @router.post("/users/{user_id}/reset-password") */
export function resetAdminUserPassword(userId: number, newPassword: string): Promise<ApiMessage> {
  invalidateMemCache(`admin:users:detail:${userId}`)
  return apiFetch<ApiMessage>(`/admin/users/${userId}/reset-password`, {
    method: 'POST',
    body: { new_password: newPassword }
  })
}

/** DELETE /api/admin/users/{id} —— admin.router @router.delete("/users/{user_id}") */
export function deleteAdminUser(userId: number): Promise<ApiMessage> {
  invalidateMemCache(`admin:users:detail:${userId}`)
  invalidateMemCache('admin:users:list:')
  return apiFetch<ApiMessage>(`/admin/users/${userId}`, { method: 'DELETE' })
}

// ==================== 用户详情（编辑） ====================

/**
 * GET /api/admin/users/{id} —— admin.router 提供管理员详情端点
 * (admin.py admin_get_user → response_model=UserDetailResponse)，
 * 包含：bio / website / github / qq / avatar_source / resolved_avatar_url /
 *       posts_count / comments_count / is_banned / updated_at / title 等。
 */
export function fetchAdminUserDetail(id: number): Promise<AdminUserRow> {
  return cachedGet(
    `admin:users:detail:${id}`,
    () => apiFetch<AdminUserRow>(`/admin/users/${id}`),
    10 * 1000 // 短缓存：避免连续进入同一编辑页、或多组件同时读取时重复请求
  )
}

/**
 * PUT /api/admin/users/{id} —— 后端 admin.router 提供 PUT 全量更新（admin_update_user_full）。
 * 接受 AdminUserUpdateFull：nickname/email/website/github/qq/bio/avatar/title_id/
 * is_staff/is_superuser/is_active/is_banned/role/username。
 */
export function updateAdminUserDetail(id: number, payload: Record<string, unknown>): Promise<AdminUserRow> {
  invalidateMemCache(`admin:users:detail:${id}`)
  invalidateMemCache('admin:users:list:')
  return apiFetch<AdminUserRow>(`/admin/users/${id}`, { method: 'PUT', body: payload })
}

// ==================== 分类 / 标签管理 ====================

export interface AdminCategory {
  id: number
  name: string
  slug: string
  description: string | null
  icon: string | null
  color: string | null
  sort_order: number
  created_at: string | null
  post_count: number
}

export interface AdminTag {
  id: number
  name: string
  slug: string
  color: string | null
  icon: string | null
  is_active: boolean
  created_at: string | null
  post_count: number
}

/** 多语言值：后端以 dict {zh,en,ja,zh_Hant} 存储；前端可传纯 zh 字符串（兼容旧逻辑）或完整 dict */
export type I18nValue = string | Record<string, string>

export interface AdminTaxonomyPayload {
  /** 名称；后端为多语言 dict。可传 zh 字符串或完整 {zh,en,ja,zh_Hant} dict */
  name: I18nValue
  slug?: string
  description?: I18nValue
  icon?: string
  color?: string
  is_active?: boolean
  sort_order?: number
}

/** 把多语言字段规整为后端期望的 dict：收到 string 视为 zh，收到 dict 原样保留（不覆盖其他语言） */
function toI18nDict(v: I18nValue | undefined, fallback = ''): Record<string, string> | undefined {
  if (v == null) {
    return fallback ? { zh: fallback } : undefined
  }
  if (typeof v === 'string') {
    return v.trim() ? { zh: v.trim() } : (fallback ? { zh: fallback } : undefined)
  }
  // dict：过滤空值，全部为空则回退
  const out: Record<string, string> = {}
  for (const [k, val] of Object.entries(v)) {
    if (val && String(val).trim()) out[k] = String(val).trim()
  }
  return Object.keys(out).length > 0 ? out : (fallback ? { zh: fallback } : undefined)
}

/** 多语言字段包装：name/description 直接发 dict（兼容全语言），不再强制只用 zh 覆盖 */
function localizedBody(payload: AdminTaxonomyPayload): Record<string, unknown> {
  const body: Record<string, unknown> = {}
  const nameDict = toI18nDict(payload.name)
  if (nameDict) body.name = nameDict
  if (payload.slug && payload.slug.trim()) body.slug = payload.slug.trim()
  const descDict = toI18nDict(payload.description)
  if (descDict) body.description = descDict
  if (payload.icon && payload.icon.trim()) body.icon = payload.icon.trim()
  if (payload.color && payload.color.trim()) body.color = payload.color.trim()
  if (payload.is_active !== undefined) body.is_active = payload.is_active
  if (payload.sort_order !== undefined) body.sort_order = payload.sort_order
  return body
}

/** GET /api/blog/categories —— blog.router 挂在 /api/blog */
export function fetchAdminCategories(): Promise<AdminCategory[]> {
  return apiFetch<AdminCategory[]>('/blog/categories')
}

/** POST /api/blog/categories —— 创建分类 */
export function createAdminCategory(payload: AdminTaxonomyPayload): Promise<AdminCategory> {
  return apiFetch<AdminCategory>('/blog/categories', {
    method: 'POST',
    body: localizedBody(payload)
  })
}

/** PUT /api/blog/categories/{id} —— 更新分类 */
export function updateAdminCategory(
  categoryId: number,
  payload: AdminTaxonomyPayload
): Promise<AdminCategory> {
  return apiFetch<AdminCategory>(`/blog/categories/${categoryId}`, {
    method: 'PUT',
    body: localizedBody(payload)
  })
}

/** DELETE /api/blog/categories/{id} */
export function deleteAdminCategory(categoryId: number): Promise<ApiMessage> {
  return apiFetch<ApiMessage>(`/blog/categories/${categoryId}`, { method: 'DELETE' })
}

/** GET /api/blog/tags */
export function fetchAdminTags(): Promise<AdminTag[]> {
  return apiFetch<AdminTag[]>('/blog/tags')
}

/** POST /api/blog/tags */
export function createAdminTag(payload: AdminTaxonomyPayload): Promise<AdminTag> {
  return apiFetch<AdminTag>('/blog/tags', {
    method: 'POST',
    body: localizedBody(payload)
  })
}

/** PUT /api/blog/tags/{id} */
export function updateAdminTag(tagId: number, payload: AdminTaxonomyPayload): Promise<AdminTag> {
  return apiFetch<AdminTag>(`/blog/tags/${tagId}`, {
    method: 'PUT',
    body: localizedBody(payload)
  })
}

/** DELETE /api/blog/tags/{id} */
export function deleteAdminTag(tagId: number): Promise<ApiMessage> {
  return apiFetch<ApiMessage>(`/blog/tags/${tagId}`, { method: 'DELETE' })
}

// ==================== 站点设置 ====================

export type SettingsValue = string | number | boolean | null | Array<unknown> | Record<string, unknown>
export type SettingsGroupData = Record<string, SettingsValue>
export type AllSettingsGroups = Record<string, SettingsGroupData>

export interface AllSettingsResponse {
  groups: AllSettingsGroups
}

export interface SettingsGroupSaveResult {
  success: boolean
  group: string
  data: SettingsGroupData
  changed: string[]
}

/** GET /api/settings —— settings_groups.router 挂在 /api，@router.get("") */
export function fetchAllSettings(): Promise<AllSettingsGroups> {
  return apiFetch<AllSettingsResponse>('/settings').then(res => res.groups)
}

/** PATCH /api/settings/{group} —— settings_groups.router @router.patch("/{group}") */
export function saveSettingsGroup(
  group: string,
  payload: SettingsGroupData
): Promise<SettingsGroupSaveResult> {
  return apiFetch<SettingsGroupSaveResult>(`/settings/${group}`, {
    method: 'PATCH',
    body: payload
  })
}

/** 判断设置项是否为敏感值（只读展示） */
export function isSensitiveSettingKey(key: string): boolean {
  const k = key.toLowerCase()
  return k.includes('password') || k.includes('secret') || k.includes('token')
}

// ==================== 系列管理 ====================

export interface AdminSeries {
  id: number
  /** 前端内部统一用 name；后端字段实际叫 title，在 fetch 层做映射 */
  name: string | Record<string, string>
  slug: string
  description?: string | Record<string, string> | null
  cover_image?: string | null
  is_active?: boolean
  sort_order?: number
  /** 前端统一 posts_count；后端字段是 post_count，在 fetch 层做映射 */
  posts_count: number
  created_at: string | null
  updated_at?: string | null
}

/** 后端 PostSeriesResponse → 前端 AdminSeries 的字段翻译：title→name / post_count→posts_count */
function _toAdminSeries(raw: Record<string, unknown> | AdminSeries | null | undefined): AdminSeries {
  if (!raw) {
    return {
      id: 0,
      name: '',
      slug: '',
      description: '',
      cover_image: '',
      is_active: true,
      sort_order: 0,
      posts_count: 0,
      created_at: null,
      updated_at: null
    }
  }
  const r = raw as Record<string, unknown>
  return {
    id: Number(r.id) || 0,
    name:
      (r.name as AdminSeries['name'])
      ?? (r.title as AdminSeries['name'])
      ?? '',
    slug: String(r.slug ?? ''),
    description: (r.description as AdminSeries['description']) ?? null,
    cover_image: (r.cover_image as AdminSeries['cover_image']) ?? null,
    is_active: typeof r.is_active === 'boolean' ? r.is_active : true,
    sort_order: typeof r.sort_order === 'number' ? r.sort_order : 0,
    posts_count:
      Number(r.posts_count ?? r.post_count ?? 0),
    created_at: (r.created_at as string | null) ?? null,
    updated_at: (r.updated_at as string | null) ?? null
  }
}

/**
 * GET /api/admin/series —— post_series.router 挂在 /api，管理接口前缀 /admin/series
 * 公开接口是 /series；管理 CRUD 一律走 /admin/series
 *
 * 后端返回格式：直接是 list[PostSeriesResponse]（不包 {success,data,message} 信封），
 * 字段名用 title / post_count；这里翻译为前端 name / posts_count。
 */
export async function fetchAdminSeries(): Promise<AdminSeries[]> {
  const raw = await apiFetch<Record<string, unknown>[]>('/admin/series')
  return Array.isArray(raw) ? raw.map(r => _toAdminSeries(r)) : []
}

/** POST /api/admin/series —— 前端 name→后端 title；后端直接返回 PostSeriesResponse */
export async function createAdminSeries(payload: Record<string, unknown>): Promise<AdminSeries> {
  const body: Record<string, unknown> = { ...payload }
  if ('name' in body) {
    body.title = body.name
    delete body.name
  }
  const raw = await apiFetch<Record<string, unknown>>('/admin/series', {
    method: 'POST',
    body
  })
  return _toAdminSeries(raw)
}

/** PUT /api/admin/series/{id} —— 前端 name→后端 title；后端直接返回 PostSeriesResponse */
export async function updateAdminSeries(id: number, payload: Record<string, unknown>): Promise<AdminSeries> {
  const body: Record<string, unknown> = { ...payload }
  if ('name' in body) {
    body.title = body.name
    delete body.name
  }
  const raw = await apiFetch<Record<string, unknown>>(`/admin/series/${id}`, {
    method: 'PUT',
    body
  })
  return _toAdminSeries(raw)
}

/** DELETE /api/admin/series/{id} */
export function deleteAdminSeries(id: number): Promise<ApiMessage> {
  return apiFetch<ApiMessage>(`/admin/series/${id}`, { method: 'DELETE' })
}

// ==================== 独立页面 Page 管理 ====================

export interface AdminPage {
  id: number
  slug: string
  title: string | Record<string, string>
  content: string | Record<string, string>
  status: 'draft' | 'published'
  is_pinned: boolean
  created_at: string | null
  updated_at: string | null
}

/**
 * GET /api/pages —— core.router 挂在 /api，@router.get("/pages") 返回分页。
 * 支持 exclude_slugs：前端在拿到数据后过滤 about / guestbook 这两个"固定页面"，
 * 避免它们出现在"独立页面"管理列表里（关于页内容走站点设置，留言板是固定路由）。
 */
export async function fetchAdminPages(
  params: {
    page?: number
    page_size?: number
    status?: string
    exclude_slugs?: string[]
  } = {}
): Promise<AdminPaged<AdminPage>> {
  const { exclude_slugs, ...rest } = params
  const raw = await apiFetch<AdminPaged<AdminPage>>('/pages', {
    query: { page: 1, page_size: 20, ...rest }
  })
  if (exclude_slugs && exclude_slugs.length > 0 && Array.isArray(raw.items)) {
    const block = new Set(exclude_slugs.map(s => String(s).toLowerCase()))
    const filtered = raw.items.filter(p => !block.has(String(p.slug || '').toLowerCase()))
    const removed = raw.items.length - filtered.length
    return {
      ...raw,
      items: filtered,
      total: Math.max(0, (raw.total ?? raw.items.length) - removed),
      total_pages: Math.max(
        1,
        Math.ceil(
          Math.max(0, (raw.total ?? raw.items.length) - removed)
          / Math.max(1, raw.page_size ?? 20)
        )
      )
    }
  }
  return raw
}

/**
 * 后端 core.router 当前仅暴露 GET /pages 和 GET /pages/{slug}，未提供 POST/PUT/DELETE CRUD。
 * 以下三个接口静默降级，避免 404 toast 红条；等后端补齐后再删除这层降级。
 */
export function createAdminPage(payload: Record<string, unknown>): Promise<AdminPage> {
  return apiFetch<AdminPage>('/pages', { method: 'POST', body: payload })
}

export function updateAdminPage(id: number, payload: Record<string, unknown>): Promise<AdminPage> {
  return apiFetch<AdminPage>(`/pages/${id}`, { method: 'PUT', body: payload })
}

export function deleteAdminPage(id: number): Promise<ApiMessage> {
  return apiFetch<ApiMessage>(`/pages/${id}`, { method: 'DELETE' })
}

// ==================== 留言板（post_id = null 的评论） ====================

export function fetchAdminGuestbook(params: AdminCommentQuery): Promise<AdminPaged<AdminComment>> {
  const query: Record<string, unknown> = { page: params.page ?? 1, page_size: params.page_size ?? 20, guestbook: 1 }
  if (params.status && params.status !== 'all') query.status = params.status
  if (params.keyword && params.keyword.trim()) query.keyword = params.keyword.trim()
  return apiFetch<AdminPaged<AdminComment>>('/admin/comments', { query })
}

// ==================== 公告 ====================

export interface AdminAnnouncement {
  id: number
  type: 'info' | 'warning' | 'error' | 'success'
  title: string | Record<string, string>
  content?: string | Record<string, string>
  is_active: boolean
  is_dismissible: boolean
  sort_order: number
  created_at: string | null
}

/**
 * GET /api/admin/announcements —— announcement.router 挂在 /api，
 * 管理接口前缀 /admin/announcements；公开 GET /announcements 只返回活跃公告不分页。
 */
export function fetchAdminAnnouncements(params: { page?: number, page_size?: number } = {}): Promise<AdminPaged<AdminAnnouncement>> {
  // 后端 /admin/announcements 返回 list（非分页），前端包装成 AdminPaged 结构。
  return silentApiFetch<AdminAnnouncement[]>('/admin/announcements', {
    query: { page: 1, page_size: 20, ...params }
  }).then((list) => {
    const items = list ?? []
    return {
      items,
      total: items.length,
      page: params.page ?? 1,
      page_size: params.page_size ?? 20,
      total_pages: items.length > 0 ? 1 : 0
    }
  })
}

/** POST /api/admin/announcements */
export function createAdminAnnouncement(payload: Record<string, unknown>): Promise<AdminAnnouncement> {
  return apiFetch<Record<string, unknown>>('/admin/announcements', { method: 'POST', body: payload })
    .then(r => (r?.data as AdminAnnouncement) ?? (r as AdminAnnouncement))
}

/** PUT /api/admin/announcements/{id} */
export function updateAdminAnnouncement(id: number, payload: Record<string, unknown>): Promise<AdminAnnouncement> {
  return apiFetch<Record<string, unknown>>(`/admin/announcements/${id}`, { method: 'PUT', body: payload })
    .then(r => (r?.data as AdminAnnouncement) ?? (r as AdminAnnouncement))
}

/** DELETE /api/admin/announcements/{id} */
export function deleteAdminAnnouncement(id: number): Promise<ApiMessage> {
  return apiFetch<ApiMessage>(`/admin/announcements/${id}`, { method: 'DELETE' })
}

// ==================== 动态 / 说说 Activity ====================

export interface AdminActivity {
  id: number
  type: 'post' | 'card' | 'comment' | 'like' | 'status'
  title?: string | null
  content?: string | null
  link?: string | null
  author?: { id: number, username: string, nickname: string | null, avatar: string | null } | null
  reply_to?: string | null
  created_at: string | null
}

/**
 * GET /api/admin/activities —— activity.router 挂在 /api，管理接口前缀 /admin/activities
 * 公开 GET /activities 只返回已发布动态。
 */
export function fetchAdminActivities(params: { page?: number, page_size?: number, type?: string } = {}): Promise<AdminPaged<AdminActivity>> {
  return apiFetch<AdminPaged<AdminActivity>>('/admin/activities', { query: { page: 1, page_size: 20, ...params } })
}

/** POST /api/admin/activities */
export function createAdminActivity(payload: Record<string, unknown>): Promise<AdminActivity> {
  return apiFetch<Record<string, unknown>>('/admin/activities', { method: 'POST', body: payload })
    .then(r => (r?.data as AdminActivity) ?? (r as AdminActivity))
}

/** PUT /api/admin/activities/{id} */
export function updateAdminActivity(id: number, payload: Record<string, unknown>): Promise<AdminActivity> {
  return apiFetch<Record<string, unknown>>(`/admin/activities/${id}`, { method: 'PUT', body: payload })
    .then(r => (r?.data as AdminActivity) ?? (r as AdminActivity))
}

/** DELETE /api/admin/activities/{id} */
export function deleteAdminActivity(id: number): Promise<ApiMessage> {
  return apiFetch<ApiMessage>(`/admin/activities/${id}`, { method: 'DELETE' })
}

// ==================== 用户头衔 UserTitle ====================

export interface AdminUserTitle {
  id?: number
  name: string
  color?: string | null
  icon?: string | null
  description?: string | null
  created_at?: string | null
}

/**
 * GET /api/admin/titles —— title.router 挂在 /api/admin（无前缀），内部 @router.get("/titles")
 * = /api/admin/titles ✔
 */
export function fetchAdminUserTitles(): Promise<AdminUserTitle[]> {
  return cachedGet(
    'admin:titles:all',
    () => apiFetch<AdminUserTitle[]>('/admin/titles'),
    5 * 60 * 1000 // 头衔列表变化极少，缓存 5 分钟；写操作统一 invalidate
  )
}

export function createAdminUserTitle(payload: Record<string, unknown>): Promise<AdminUserTitle> {
  invalidateMemCache('admin:titles:')
  return apiFetch<AdminUserTitle>('/admin/titles', { method: 'POST', body: payload })
}

export function updateAdminUserTitle(id: number, payload: Record<string, unknown>): Promise<AdminUserTitle> {
  invalidateMemCache('admin:titles:')
  return apiFetch<AdminUserTitle>(`/admin/titles/${id}`, { method: 'PUT', body: payload })
}

export function deleteAdminUserTitle(id: number): Promise<ApiMessage> {
  invalidateMemCache('admin:titles:')
  return apiFetch<ApiMessage>(`/admin/titles/${id}`, { method: 'DELETE' })
}

/**
 * POST /api/admin/titles/assign —— title.router 内部 @router.post("/titles/assign")
 * = /api/admin/titles/assign
 */
export function assignAdminUserTitle(userId: number, titleId: number | null): Promise<ApiMessage> {
  if (titleId == null || titleId <= 0) {
    return Promise.resolve({ success: true, message: '已移除头衔' })
  }
  return apiFetch<ApiMessage>('/admin/titles/assign', { method: 'POST', body: { user_id: userId, title_id: titleId } })
}

// ==================== 媒体库 ====================

export interface AdminMediaItem {
  id: number
  filename: string
  url: string
  mime: string
  size_bytes: number
  category?: string | null
  uploaded_by?: { id: number, username: string } | null
  created_at: string | null
}

interface AdminMediaQuery {
  page?: number
  page_size?: number
  search?: string
  category?: string
  mime_prefix?: string
  file_type?: string
}

/**
 * GET /api/media/library —— media.router 挂在 /api/media，内部 @router.get("/library")
 * = /api/media/library ✔
 */
export function fetchAdminMediaLibrary(params: AdminMediaQuery = {}): Promise<AdminPaged<AdminMediaItem>> {
  const query: Record<string, unknown> = { page: 1, page_size: 20, ...params }
  // 后端参数名是 file_type 而非 mime_prefix；做一次兼容映射
  if (params.mime_prefix && !params.file_type) {
    query.file_type = params.mime_prefix
  }
  if (params.search) query.search = params.search
  return apiFetch<AdminPaged<AdminMediaItem>>('/media/library', { query })
}

/** DELETE /api/media/library/{id} —— media.router @router.delete("/library/{media_id}") */
export function deleteAdminMedia(id: number): Promise<ApiMessage> {
  return apiFetch<ApiMessage>(`/media/library/${id}`, { method: 'DELETE' })
}

/** DELETE /api/media/library/batch —— media.router @router.delete("/library/batch") */
export function deleteAdminMediaBatch(ids: number[]): Promise<ApiMessage> {
  return apiFetch<ApiMessage>('/media/library/batch', { method: 'DELETE', body: { ids } })
}

export interface AdminMediaStats {
  total_files: number
  total_size_bytes: number
  images: number
  videos: number
  documents: number
}

/** GET /api/media/library/stats —— media.router @router.get("/library/stats")，响应为 envelope */
export function fetchAdminMediaStats(): Promise<AdminMediaStats> {
  return apiFetch<ApiEnvelope<AdminMediaStats>>('/media/library/stats').then(r => r.data)
}

// ==================== 相册 Album ====================

export interface AdminAlbum {
  id: number
  title: string | Record<string, string>
  description?: string | Record<string, string> | null
  cover_url?: string | null
  is_public: boolean
  photos_count: number
  created_at: string | null
}

export interface AdminPhoto {
  id: number
  album_id: number
  title?: string | null
  thumbnail_url?: string | null
  original_url: string
  sort_order: number
  created_at: string | null
}

/**
 * GET /api/admin/gallery/albums —— gallery_admin_router 挂在 /api, prefix="/admin/gallery"
 * 公开接口在 /api/gallery/albums，管理 CRUD 一律走 /api/admin/gallery/*
 */
export function fetchAdminAlbums(params: { page?: number, page_size?: number } = {}): Promise<AdminPaged<AdminAlbum>> {
  return apiFetch<AdminPaged<Record<string, unknown>>>('/admin/gallery/albums', { query: { page: 1, page_size: 20, ...params } })
    .then(raw => ({ ...raw, items: (raw.items ?? []).map(mapAlbum) }))
}

/** POST /api/admin/gallery/albums */
export function createAdminAlbum(payload: Record<string, unknown>): Promise<AdminAlbum> {
  return apiFetch<Record<string, unknown>>('/admin/gallery/albums', { method: 'POST', body: albumBody(payload) }).then(mapAlbum)
}

/** PUT /api/admin/gallery/albums/{id} */
export function updateAdminAlbum(id: number, payload: Record<string, unknown>): Promise<AdminAlbum> {
  return apiFetch<Record<string, unknown>>(`/admin/gallery/albums/${id}`, { method: 'PUT', body: albumBody(payload) }).then(mapAlbum)
}

/** DELETE /api/admin/gallery/albums/{id} */
export function deleteAdminAlbum(id: number): Promise<ApiMessage> {
  return apiFetch<ApiMessage>(`/admin/gallery/albums/${id}`, { method: 'DELETE' })
}

/** GET /api/admin/gallery/albums/{albumId}/photos */
export function fetchAdminPhotos(albumId: number): Promise<AdminPaged<AdminPhoto>> {
  return apiFetch<AdminPaged<AdminPhoto>>(`/admin/gallery/albums/${albumId}/photos`)
}

export function createAdminPhoto(payload: Record<string, unknown>): Promise<AdminPhoto> {
  return apiFetch<AdminPhoto>('/admin/gallery/photos', { method: 'POST', body: payload })
}

export function updateAdminPhoto(id: number, payload: Record<string, unknown>): Promise<AdminPhoto> {
  return apiFetch<AdminPhoto>(`/admin/gallery/photos/${id}`, { method: 'PUT', body: payload })
}

/** DELETE /api/admin/gallery/photos/{id} —— gallery_admin_router */
export function deleteAdminPhoto(id: number): Promise<ApiMessage> {
  return apiFetch<ApiMessage>(`/admin/gallery/photos/${id}`, { method: 'DELETE' })
}

// ==================== 导航菜单 ====================

export interface AdminNavItem {
  id: number
  label: string | Record<string, string>
  url: string
  icon?: string | null
  order: number
  target: '_self' | '_blank'
  parent_id: number | null
}

/**
 * GET /api/admin/navigations —— core.router 挂在 /api，管理接口 @router.get("/admin/navigations")
 * 公开 GET /navigations 只返回激活项；管理端需要全量（包括非激活）走 /admin/navigations
 */
export async function fetchAdminNavigations(): Promise<AdminNavItem[]> {
  const list = await apiFetch<Array<Record<string, unknown>>>('/admin/navigations')
  if (!Array.isArray(list)) return []
  // 字段标准化：后端返回的是 NavigationResponse 结构（title/url/icon/parent_id/order/target_blank/is_active）
  return list.map((x: Record<string, unknown>, i: number) => {
    const label = x.title ?? x.label
    const localizedLabel = label !== null && typeof label === 'object'
      ? Object.fromEntries(
        Object.entries(label as Record<string, unknown>)
          .filter(([, value]) => typeof value === 'string')
      ) as Record<string, string>
      : null
    return {
      id: Number(x.id ?? (i + 1)),
      label: typeof label === 'string' ? label : (localizedLabel ?? `导航项 ${i + 1}`),
      url: String(x.url ?? x.link ?? ''),
      icon: typeof x.icon === 'string' ? x.icon : null,
      order: Number(x.order ?? x.sort_order ?? i) || i,
      target: (String(x.target ?? x.target_blank ?? '_self') === '_blank' ? '_blank' : '_self'),
      parent_id: Number(x.parent_id ?? null) || null
    }
  })
}

/** POST /api/navigations —— core.router @router.post("/navigations") */
function navigationBody(payload: Record<string, unknown>): Record<string, unknown> {
  const body: Record<string, unknown> = { ...payload }
  if ('label' in body) {
    body.title = body.label
    delete body.label
  }
  if ('target' in body) {
    body.target_blank = body.target === '_blank'
    delete body.target
  }
  return body
}

export function createAdminNavigation(payload: Record<string, unknown>): Promise<AdminNavItem> {
  return apiFetch<AdminNavItem>('/navigations', { method: 'POST', body: navigationBody(payload) })
}

export function updateAdminNavigation(id: number, payload: Record<string, unknown>): Promise<AdminNavItem> {
  return apiFetch<AdminNavItem>(`/navigations/${id}`, { method: 'PUT', body: navigationBody(payload) })
}

export function deleteAdminNavigation(id: number): Promise<ApiMessage> {
  return apiFetch<ApiMessage>(`/navigations/${id}`, { method: 'DELETE' })
}

// ==================== 友情链接 ====================

export interface AdminFriendLink {
  id: number
  name: string | Record<string, string>
  url: string
  logo?: string | null
  description?: string | Record<string, string> | null
  sort_order: number
  status: 'pending' | 'approved' | 'rejected'
  created_at: string | null
}

function friendLinkBody(payload: Record<string, unknown>): Record<string, unknown> {
  const body: Record<string, unknown> = { ...payload }
  if ('sort_order' in body) {
    body.order = body.sort_order
    delete body.sort_order
  }
  // 后端 Schema 支持 status 三态，同时 is_active 作为兼容字段也需要同步
  if ('status' in body && typeof body.status === 'string') {
    body.is_active = body.status === 'approved'
    // 保留 status 字段，不删除
  }
  delete body.bg_color
  return body
}

export function fetchAdminFriendLinks(): Promise<AdminFriendLink[]> {
  return apiFetch<Record<string, unknown>[]>('/friend-links?all=true').then(list => (list ?? []).map(mapFriendLink))
}

export function createAdminFriendLink(payload: Record<string, unknown>): Promise<AdminFriendLink> {
  return apiFetch<Record<string, unknown>>('/friend-links', { method: 'POST', body: friendLinkBody(payload) }).then(mapFriendLink)
}

export function updateAdminFriendLink(id: number, payload: Record<string, unknown>): Promise<AdminFriendLink> {
  return apiFetch<Record<string, unknown>>(`/friend-links/${id}`, { method: 'PUT', body: friendLinkBody(payload) }).then(mapFriendLink)
}

export function deleteAdminFriendLink(id: number): Promise<ApiMessage> {
  return apiFetch<ApiMessage>(`/friend-links/${id}`, { method: 'DELETE' })
}

// ==================== 响应形状适配（后端 → 前端约定） ====================
// 后端部分接口返回裸对象 / 裸列表 / {success, webhook|job} 等非标准信封，
// 这里统一映射为前端页面期望的形状，避免页面拿到 undefined / 字段错位。

function mapWebhook(raw: Record<string, unknown>): AdminWebhook {
  const r = raw as Record<string, unknown>
  return {
    id: Number(r.id) || 0,
    name: String(r.name ?? ''),
    url: String(r.url ?? ''),
    secret: (r.secret as string | null) ?? null,
    events: Array.isArray(r.events) ? (r.events as string[]) : [],
    active: typeof r.is_active === 'boolean' ? r.is_active : Boolean(r.active),
    provider: (r.provider as AdminWebhook['provider']) ?? 'generic',
    created_at: (r.created_at as string | null) ?? null,
    last_triggered_at: (r.last_triggered_at as string | null) ?? null
  }
}

function mapAlbum(raw: Record<string, unknown>): AdminAlbum {
  const r = raw as Record<string, unknown>
  return {
    id: Number(r.id) || 0,
    title: (r.title as AdminAlbum['title']) ?? '',
    description: (r.description as AdminAlbum['description']) ?? null,
    cover_url: (r.cover as string | null) ?? null,
    is_public: typeof r.is_published === 'boolean' ? r.is_published : true,
    photos_count: Number(r.photo_count ?? 0),
    created_at: (r.created_at as string | null) ?? null
  }
}

function albumBody(payload: Record<string, unknown>): Record<string, unknown> {
  const body: Record<string, unknown> = { ...payload }
  if ('cover_url' in body) {
    body.cover = body.cover_url
    delete body.cover_url
  }
  if ('is_public' in body) {
    body.is_published = body.is_public
    delete body.is_public
  }
  if (body.title && typeof body.title === 'object') {
    const t = body.title as Record<string, string>
    body.title = t.zh ?? Object.values(t)[0] ?? ''
  }
  if (body.description && typeof body.description === 'object') {
    const d = body.description as Record<string, string>
    body.description = d.zh ?? Object.values(d)[0] ?? null
  }
  return body
}

function mapFriendLink(raw: Record<string, unknown>): AdminFriendLink {
  const r = raw as Record<string, unknown>
  let name: AdminFriendLink['name'] = ''
  const nr = r.name
  if (typeof nr === 'string') name = nr
  else if (nr && typeof nr === 'object') {
    name = { ...(nr as Record<string, string>) }
  }
  let description: AdminFriendLink['description'] = null
  const dr = r.description
  if (typeof dr === 'string') description = dr
  else if (dr && typeof dr === 'object') {
    description = { ...(dr as Record<string, string>) }
  }
  // 优先使用后端返回的 status 字段（三态：pending/approved/rejected），
  // 兼容旧数据：若 status 缺失，则根据 is_active 推导 approved / pending。
  const rawStatus = typeof r.status === 'string' ? r.status : ''
  const isActive = typeof r.is_active === 'boolean' ? r.is_active : false
  const status: AdminFriendLink['status']
    = (rawStatus === 'approved' || rawStatus === 'pending' || rawStatus === 'rejected')
      ? rawStatus
      : (isActive ? 'approved' : 'pending')
  return {
    id: Number(r.id) || 0,
    name,
    url: String(r.url ?? ''),
    logo: (r.logo as string | null) ?? null,
    description,
    sort_order: Number(r.order ?? r.sort_order ?? 0),
    status,
    created_at: (r.created_at as string | null) ?? null
  }
}

// ==================== Webhook ====================

export interface AdminWebhook {
  id: number
  name: string
  url: string
  secret?: string | null
  events: string[]
  active: boolean
  provider: 'github' | 'generic' | 'feishu' | 'email'
  created_at: string | null
  last_triggered_at: string | null
}

/** GET /api/webhooks —— webhook.router 挂在 /api/webhooks，@router.get("") */
export function fetchAdminWebhooks(): Promise<AdminWebhook[]> {
  return apiFetch<AdminPaged<Record<string, unknown>>>('/webhooks').then(r => (r.items ?? []).map(mapWebhook))
}

/** POST /api/webhooks —— 后端返回 {success, message, webhook} */
export function createAdminWebhook(payload: Record<string, unknown>): Promise<AdminWebhook> {
  return apiFetch<{ success: boolean, webhook: Record<string, unknown> }>('/webhooks', { method: 'POST', body: payload })
    .then(r => mapWebhook(r.webhook))
}

/** PUT /api/webhooks/{id} —— 后端仅返回 {success, message}，无 webhook 体，返回 undefined 由页面刷新列表 */
export function updateAdminWebhook(id: number, payload: Record<string, unknown>): Promise<AdminWebhook | undefined> {
  return apiFetch<{ success: boolean, webhook?: Record<string, unknown>, message?: string }>(`/webhooks/${id}`, { method: 'PUT', body: payload })
    .then(r => (r.webhook ? mapWebhook(r.webhook) : undefined))
}

/** DELETE /api/webhooks/{id} */
export function deleteAdminWebhook(id: number): Promise<ApiMessage> {
  return apiFetch<ApiMessage>(`/webhooks/${id}`, { method: 'DELETE' })
}

/**
 * 触发测试：POST /api/webhooks/{id}/test —— webhook.router @router.post("/{webhook_id}/test")
 * 后端没有 trigger 端点，统一用 test 端点（发送示例 payload）。
 */
export function triggerAdminWebhook(id: number): Promise<ApiMessage> {
  return apiFetch<ApiMessage>(`/webhooks/${id}/test`, { method: 'POST' })
}

// ==================== 导入导出 ====================

export interface AdminExportInfo {
  job_id: string
  format: 'wordpress' | 'halo' | 'typecho' | 'markdown' | 'json'
  status: 'running' | 'done' | 'failed'
  download_url?: string | null
  created_at: string | null
}

/**
 * GET /api/admin/export/{posts|markdown} —— import_export.router 挂在 /api/admin：
 *   @router.get("/export/posts")      → JSON 格式（Rosetta 原生 JSON + categories + tags）
 *   @router.get("/export/markdown")   → Markdown ZIP
 * 后端没有 /import-export/* 路径，format=markdown → /admin/export/markdown，其它走 /admin/export/posts。
 */
export function exportAdminPosts(format: string, opts?: { from?: string, to?: string, scope?: string }): Promise<Blob> {
  const subPath = (format === 'markdown') ? 'markdown' : 'posts'
  const query: Record<string, string> = {}
  if (format !== 'markdown' && format !== 'json') query.format = format
  if (opts?.from) query.from = opts.from
  if (opts?.to) query.to = opts.to
  if (opts?.scope) query.scope = opts.scope
  return apiFetch<Blob>(`/admin/export/${subPath}`, {
    method: 'GET',
    responseType: 'blob',
    query: Object.keys(query).length ? query : undefined
  })
}

export interface AdminImportResult {
  success: boolean
  message: string
  created_count: number
  skipped_count: number
  error_count: number
  errors?: string[]
}

/**
 * POST /api/admin/import/{posts|markdown} —— import_export.router：
 *   @router.post("/import/posts")      → WordPress/Halo/Typecho/JSON 等（通过 format query 区分）
 *   @router.post("/import/markdown")   → Markdown ZIP
 * 统一传 multipart/form-data；后端通过 query.format 判断具体导入逻辑。
 */
export function importAdminPosts(format: string, file: File): Promise<AdminImportResult> {
  const subPath = (format === 'markdown') ? 'markdown' : 'posts'
  const fd = new FormData()
  fd.append('file', file)
  // 后端 import/posts 读 query.format 区分 wordpress/halo/typecho/json
  const query = (format !== 'markdown') ? { format } : undefined
  return apiFetch<AdminImportResult>(`/admin/import/${subPath}`, {
    method: 'POST',
    body: fd as unknown as Record<string, unknown>,
    query
  })
}

// ==================== SEO 工具 ====================

export interface AdminSeoScore {
  id: number
  slug: string
  title: string
  score: number
  suggestions: string[]
}

/**
 * GET /api/seo/sitemap-check —— 后端 seo.router 暂未提供（只有 config + sitemap.xml + robots.txt + schema/OG）
 * 静默降级返回占位，避免 404。
 */
export function fetchAdminSeoSitemapCheck(): Promise<{ ok: boolean, url_count: number, errors: string[] }> {
  return silentApiFetch<ApiEnvelope<{ ok: boolean, url_count: number, errors: string[] }>>('/seo/sitemap-check').then(r =>
    r?.data ?? { ok: false, url_count: 0, errors: ['后端暂未开放 sitemap 校验接口'] }
  )
}

/**
 * GET /api/seo/scores —— 后端暂未提供；静默降级。
 */
export function fetchAdminSeoScores(params: { page?: number, page_size?: number } = {}): Promise<AdminPaged<AdminSeoScore>> {
  return silentApiFetch<AdminPaged<AdminSeoScore>>('/seo/scores', { query: { page: 1, page_size: 20, ...params } }).then(r =>
    r ?? { items: [], total: 0, page: params.page ?? 1, page_size: params.page_size ?? 20, total_pages: 0 }
  )
}

/**
 * POST /api/seo/sitemap/generate —— seo.router 挂在 /api/seo，@router.post("/sitemap/generate")
 * 前端旧路径 /seo/sitemap/regenerate 不存在，已修正为 generate。
 */
export function regenerateAdminSitemap(): Promise<ApiMessage> {
  return apiFetch<ApiMessage>('/seo/sitemap/generate', { method: 'POST' })
}

// ==================== 翻译工具 ====================

export interface AdminTranslateResponse {
  translations: Record<string, string>
}

export function translateAdminText(
  text: string,
  sourceLang: string,
  targetLangs: string[]
): Promise<AdminTranslateResponse> {
  return apiFetch<AdminTranslateResponse>('/translate', {
    method: 'POST',
    body: { text, source_lang: sourceLang, target_langs: targetLangs }
  })
}

export interface AdminSlowRequest {
  id: number
  method: string
  path: string
  duration_ms: number
  status_code: number
  user_agent?: string | null
  created_at: string | null
}

export interface AdminPerformanceSummary {
  total_requests_24h: number
  error_rate_24h: number
  p50_ms: number
  p95_ms: number
  p99_ms: number
  top_slow_paths: Array<{ path: string, avg_ms: number, count: number }>
}

/**
 * GET /api/admin/performance/summary —— performance.router 挂在 /api/admin，
 * 内部 @router.get("/performance/summary") = /api/admin/performance/summary ✔
 */
export function fetchAdminPerformanceSummary(): Promise<AdminPerformanceSummary> {
  // 后端返回裸对象 { last_24h: {...}, last_7d: {...}, timestamp }，与页面期望的扁平结构不同，这里做映射。
  return apiFetch<Record<string, unknown>>('/admin/performance/summary').then((raw) => {
    const d = (raw?.last_24h ?? {}) as Record<string, unknown>
    const eps = Array.isArray(d.slow_endpoints) ? (d.slow_endpoints as Array<Record<string, unknown>>) : []
    return {
      total_requests_24h: Number(d.total_requests ?? 0),
      // 后端 error_rate 已是百分比数值（如 13.29），页面会再 ×100，故存为小数。
      error_rate_24h: Number(d.error_rate ?? 0) / 100,
      // 后端无 p50，用 avg 近似
      p50_ms: Number(d.avg_response_time_ms ?? 0),
      p95_ms: Number(d.p95_response_time_ms ?? 0),
      p99_ms: Number(d.p99_response_time_ms ?? 0),
      top_slow_paths: eps.map(e => ({
        path: String(e.endpoint ?? ''),
        count: Number(e.request_count ?? 0),
        avg_ms: Number(e.avg_response_time_ms ?? 0)
      }))
    }
  })
}

/** GET /api/admin/performance/slow —— performance.router @router.get("/performance/slow") */
export function fetchAdminSlowRequests(params: { page?: number, page_size?: number, limit?: number } = {}): Promise<AdminPaged<AdminSlowRequest>> {
  // 后端 /performance/slow 返回 list（非分页），包装成 AdminPaged。
  return silentApiFetch<AdminSlowRequest[]>('/admin/performance/slow', {
    query: { page: 1, page_size: 20, limit: 50, ...params }
  }).then((list) => {
    const items = Array.isArray(list) ? list : []
    return {
      items,
      total: items.length,
      page: params.page ?? 1,
      page_size: params.page_size ?? 20,
      total_pages: items.length > 0 ? 1 : 0
    }
  })
}

// ==================== 操作审计日志 ====================

export interface AdminAuditLog {
  id: number
  user_id: number | null
  username?: string | null
  action: string
  target_type?: string | null
  target_id?: string | null
  ip?: string | null
  user_agent?: string | null
  details?: Record<string, unknown> | null
  created_at: string | null
}

/**
 * GET /api/admin/logs
 * 注意：后端 advanced.py（prefix=/admin）与 admin_logs.py 都挂载了同名端点，实际命中 advanced.py，
 * 其返回结构是嵌套 user: {id, username, nickname}，并使用 resource_type / resource_id / ip_address / detail。
 * 这里做一次"字段归一化"，把两种可能的结构统一映射成 AdminAuditLog 的扁平字段，防止前端取值错位。
 */
export function fetchAdminAuditLogs(params: { page?: number, page_size?: number, action?: string, user_id?: number, from?: string, to?: string } = {}): Promise<AdminPaged<AdminAuditLog>> {
  return apiFetch<AdminPaged<Record<string, unknown>>>('/admin/logs', { query: { page: 1, page_size: 20, ...params } })
    .then((resp) => {
      const normalized = (resp?.items ?? []).map((raw: Record<string, unknown>) => {
        const userObj = (raw.user ?? null) as { id?: number, username?: string, nickname?: string } | null
        const uid = userObj?.id ?? (raw.user_id as number | null | undefined) ?? null
        const uname = userObj?.username ?? (raw.username as string | null | undefined) ?? (raw.user_name as string | null | undefined) ?? null
        return {
          id: raw.id as number,
          user_id: uid,
          username: uname,
          action: raw.action as string,
          target_type: (raw.target_type ?? raw.resource_type ?? null) as string | null,
          target_id: (raw.target_id ?? raw.resource_id ?? null) as string | number | null,
          ip: (raw.ip ?? raw.ip_address ?? null) as string | null,
          user_agent: (raw.user_agent ?? null) as string | null,
          details: (raw.details ?? raw.detail ?? null) as Record<string, unknown> | null,
          created_at: (raw.created_at ?? null) as string | null
        } satisfies AdminAuditLog
      })
      return { ...resp, items: normalized }
    })
}

// ==================== 数据库迁移 ====================

export interface AdminMigrationStatus {
  current_version: string
  latest_version: string
  is_latest: boolean
  pending: Array<{ version: string, message: string }>
  applied: Array<{ version: string, message: string, applied_at: string | null }>
}

/**
 * GET /api/admin/alembic/status —— 2026-08 新增后端端点，用于显示 Alembic schema 迁移的：
 *   current_version / latest_version / is_latest / applied / pending
 * 注意：/api/admin/migration/status 是"跨库数据迁移任务管理器"（Job）与本页面无关。
 * 失败时静默回退为 emptyStatus，保证界面可用。
 */
export function fetchAdminMigrationStatus(): Promise<AdminMigrationStatus> {
  return silentApiFetch<ApiEnvelope<AdminMigrationStatus> | AdminMigrationStatus>('/admin/alembic/status')
    .then((raw) => {
      const r = (raw && (raw as ApiEnvelope<AdminMigrationStatus>).data)
        ? (raw as ApiEnvelope<AdminMigrationStatus>).data
        : (raw as AdminMigrationStatus | null | undefined)
      if (!r) return emptyStatus()
      return {
        current_version: String(r.current_version ?? ''),
        latest_version: String(r.latest_version ?? ''),
        is_latest: Boolean(r.is_latest ?? true),
        pending: (Array.isArray(r.pending) ? r.pending : []) as AdminMigrationStatus['pending'],
        applied: (Array.isArray(r.applied) ? r.applied : []) as AdminMigrationStatus['applied']
      }
    })
    .catch(() => emptyStatus())
}

/**
 * Alembic 升级：后端 migration.router 是跨库数据迁移工具，不负责 Alembic schema 升级。
 * Schema 升级只能通过 `uv run python -m backend.migrations upgrade` 命令行执行。
 * 静默降级 + 给出明确提示，避免 404 toast。
 */
export function upgradeAdminMigrations(): Promise<ApiMessage> {
  return silentApiFetch<ApiMessage>('/admin/migration/upgrade', { method: 'POST' }).then(r =>
    r ?? { success: false, message: '数据库 Schema 升级请在服务器执行命令：uv run python -m backend.migrations upgrade' }
  )
}

// ==================== 缓存管理 ====================

export type AdminCacheFlushMode = 'all' | 'post_list' | 'post_detail' | 'settings' | 'fragments'

export interface AdminCacheStatus {
  backend: 'memory' | 'redis'
  keys: number
  memory_used_bytes?: number | null
  hit_rate?: number | null
}

/**
 * GET /api/admin/cache/status —— 2026-08 新增后端端点（admin_tools.router）。
 * 兼容统一响应格式 {success, data} 与直接裸对象两种包法。
 */
export function fetchAdminCacheStatus(): Promise<AdminCacheStatus> {
  return silentApiFetch<ApiEnvelope<AdminCacheStatus> | AdminCacheStatus>('/admin/cache/status').then((raw) => {
    const r = (raw && (raw as ApiEnvelope<AdminCacheStatus>).data)
      ? (raw as ApiEnvelope<AdminCacheStatus>).data
      : (raw as AdminCacheStatus | null | undefined)
    if (!r) return { backend: 'memory', keys: 0, memory_used_bytes: null, hit_rate: null }
    return {
      backend: r.backend === 'redis' ? 'redis' : 'memory',
      keys: Number(r.keys ?? 0),
      memory_used_bytes: r.memory_used_bytes ?? null,
      hit_rate: r.hit_rate ?? null
    } satisfies AdminCacheStatus
  })
}

export function flushAdminCache(mode: AdminCacheFlushMode): Promise<ApiMessage> {
  return apiFetch<ApiMessage>('/admin/cache/flush', { method: 'POST', body: { mode } }).then(r =>
    r ?? { success: true, message: '缓存已清退' }
  )
}

// ==================== 站内通知 Notifications ====================
// 接口路径: GET/POST /api/notifications/* （非 admin 前缀，按 recipient_id = 当前用户隔离）

export type NotificationLevel = 'info' | 'success' | 'warning' | 'error'

export interface AdminNotification {
  id: number
  level: NotificationLevel
  title: string
  message?: string | null
  verb?: string | null
  link?: string | null
  is_read: boolean
  actor?: { id: number, username: string, nickname?: string | null, avatar?: string | null } | null
  created_at: string | null
}

export interface NotificationsListResponse {
  items: AdminNotification[]
  total: number
  unread_count: number
  page: number
  page_size: number
  total_pages: number
}

export interface NotificationsStats {
  unread_count: number
  total_count: number
  read?: number
  type_distribution?: Record<string, number>
}

/**
 * GET /api/notifications —— notification.router 挂在 /api/notifications，@router.get("")
 * 裸 dict（非 ApiEnvelope）。降级：后端暂缺 / 权限不足时返回空列表，不抛错不 toast。
 */
export function fetchNotifications(params: {
  page?: number
  page_size?: number
  unread_only?: boolean
} = {}): Promise<NotificationsListResponse> {
  return silentApiFetch<NotificationsListResponse>('/notifications', {
    query: { page: 1, page_size: 10, unread_only: false, ...params }
  }).then(r => r ?? {
    items: [],
    total: 0,
    unread_count: 0,
    page: params.page ?? 1,
    page_size: params.page_size ?? 10,
    total_pages: 0
  })
}

/**
 * GET /api/notifications/stats —— notification.router @router.get("/stats")
 * 注意：后端返回裸 dict（无 success/data 包裹），404/5xx 时降级为 0 保证 badge 不误导。
 * 同时后端还有 @router.get("/unread-count")，这里使用 /stats 信息更全。
 */
export function fetchNotificationStats(): Promise<NotificationsStats> {
  return silentApiFetch<Record<string, unknown>>('/notifications/stats').then((r) => {
    const s = (r ?? {}) as Record<string, unknown>
    const num = (v: unknown, d = 0): number => (typeof v === 'number' ? v : Number(v ?? d)) || d
    return {
      // 后端返回 {total, unread, read}，页面读取 unread_count/total_count
      unread_count: num(s.unread_count ?? s.unread ?? 0),
      total_count: num(s.total_count ?? s.total ?? 0),
      read: num(s.read ?? 0),
      type_distribution: (s.type_distribution && typeof s.type_distribution === 'object'
        ? s.type_distribution
        : {}) as Record<string, number>
    }
  })
}

/** POST /api/notifications/{id}/read —— notification.router @router.post("/{notification_id}/read") */
export function markNotificationRead(id: number): Promise<void> {
  return silentApiFetch(`/notifications/${id}/read`, { method: 'POST' }).then(() => undefined)
}

/** POST /api/notifications/read-all —— @router.post("/read-all") */
export function markAllNotificationsRead(): Promise<void> {
  return silentApiFetch('/notifications/read-all', { method: 'POST' }).then(() => undefined)
}

/** DELETE /api/notifications —— @router.delete("") 清空所有通知 */
export function clearAllNotifications(): Promise<void> {
  return silentApiFetch('/notifications', { method: 'DELETE' }).then(() => undefined)
}

/** DELETE /api/notifications/{id} —— @router.delete("/{notification_id}") 删除单条 */
export function deleteNotification(id: number): Promise<void> {
  return silentApiFetch(`/notifications/${id}`, { method: 'DELETE' }).then(() => undefined)
}
