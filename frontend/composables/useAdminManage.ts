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

/** 清理某条缓存（写操作后调用，确保下次读拿到最新值）。仅本模块内使用。 */
function invalidateMemCache(keyPrefix?: string) {
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
  /** 0-100；null = 一个指标都没实测到（未知），不是 0 分危急也不是 100 分健康 */
  health_score: number | null
  /** 后端算好的每轴健康分（0-100，越高越好），雷达/配色单源，避免前后端两套口径 */
  metric_scores?: Partial<Record<'cache' | 'cpu' | 'db' | 'memory', number | null>>
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
  /** 'all' 是后台专属的「全部状态」哨兵（blog.py::admin_all_statuses）；
   *  其余取值必须落在后端 schema 的 draft|published|scheduled 之内，
   *  archived 在后端不存在，列出只会得到一个永远为空的筛选 */
  status?: 'all' | 'published' | 'draft' | 'scheduled'
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
 * - status='all'（或不传）：后端直接返回全部状态，单次请求 + 服务端分页
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

  // 后端已支持 admin 传 status=all 返回全部状态，单次请求即可，无需 4 路并行
  const status = !params.status || params.status === 'all' ? 'all' : params.status

  const paged = await apiFetch<AdminPaged<T>>('/blog/posts', {
    query: {
      page,
      page_size: pageSize,
      status,
      search: qSearch || undefined,
      category: qCategory,
      created_start: qCreatedStart,
      created_end: qCreatedEnd
    }
  })
  return { items: paged.items ?? [], total: paged.total ?? 0 }
}

// ==================== 评论管理 ====================

export type AdminCommentStatus = 'approved' | 'pending' | 'rejected' | 'spam'
/** `trashed` 只有留言板端点识别（评论表无软删除列），列表组件按 tab 透传。 */
export type AdminCommentStatusFilter = AdminCommentStatus | 'all' | 'trashed'

export interface AdminCommentPostRef {
  id: number
  slug: string | null
  title: string | null
}

/**
 * 审核列表的共用行形状：评论（Comment）与留言（GuestbookEntry）两套后端模型
 * 在列表 UI 上消费同一组字段，评论专属字段（post/parent/reply）为可选。
 */
export interface AdminCommentRow {
  id: number
  author_name: string
  resolved_avatar_url: string | null
  author_email?: string | null
  content: string
  status: AdminCommentStatus | string
  likes_count: number
  reply_total?: number
  created_at: string | null
  title?: { id?: number, name: string, icon?: string, color?: string } | null
  post_id?: number | null
  parent_id?: number | null
  post_ref?: AdminCommentPostRef | null
  active?: boolean
  /** 留言专属：评论模型无对应列，故为可选。 */
  is_pinned?: boolean
  is_featured?: boolean
}

export interface AdminComment extends AdminCommentRow {
  post_id: number
  parent_id: number | null
  active: boolean
  reply_total: number
  post_ref: AdminCommentPostRef | null
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
  /** 仅 GET /admin/users/{id}（UserDetailResponse）返回，列表接口不含 */
  qq?: string | null
  avatar_source?: string | null
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
    () => apiFetch<AdminPaged<AdminUserRow>>('/users/', { query }),
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
 * 接受 AdminUserUpdateFull：username/email/nickname/bio/website/github/qq/avatar_source/
 * avatar/cover_image/role/is_staff/is_active/is_banned。
 * 该 schema 为 extra=forbid（2026-09 起真正生效），**多传一个字段就是 422 而不是被忽略**；
 * title_id 与 is_superuser 不在其列——头衔走 assign/remove 专用端点，超级管理员由 role 反推。
 */
export function updateAdminUserDetail(id: number, payload: Record<string, unknown>): Promise<AdminUserRow> {
  invalidateMemCache(`admin:users:detail:${id}`)
  invalidateMemCache('admin:users:list:')
  return apiFetch<AdminUserRow>(`/admin/users/${id}`, { method: 'PUT', body: payload })
}

// ==================== 分类 / 标签管理 ====================

export interface AdminCategory {
  id: number
  /** 后端 GET /blog/categories 返回 i18n 原始 dict（{zh,en,ja,zh_Hant}） */
  name: string | Record<string, string>
  slug: string
  description: string | Record<string, string> | null
  icon: string | null
  color: string | null
  created_at: string | null
  post_count: number
}

export interface AdminTag {
  id: number
  /** 同分类：后端返回多语言原始 dict */
  name: string | Record<string, string>
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
 * core.router 已提供完整页面 CRUD：POST /pages、PUT /pages/{id}、DELETE /pages/{id}
 * （均需 staff 登录；PageCreate/PageUpdate 为 extra=forbid，body 不得携带额外字段，
 * title/content 为 {zh,en,ja,zh_Hant} 多语言 dict，slug 必填、校验口径同 CONTENT_SLUG_PATTERN（允许中文）。
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

// ==================== 留言板（GuestbookEntry 独立模型） ====================

/**
 * 留言与评论是两套后端模型：前台 /guestbook 读写 GuestbookEntry 表，
 * 管理入口只能走 /admin/guestbook/*。
 * 历史缺陷：这里曾请求 `/admin/comments?guestbook=1`，而该 query 参数后端根本不存在
 * （FastAPI 直接丢弃未声明参数），结果是后台"留言板"列出的是文章评论，
 * 真实待审留言在后台永远不可见、不可审核。
 */
export interface AdminGuestbookEntry extends AdminCommentRow {
  user_id: number | null
  author_website?: string | null
  qq?: string | null
  github?: string | null
  avatar_source?: string | null
  is_pinned: boolean
  is_featured: boolean
}

export type GuestbookBatchAction
  = 'approve' | 'reject' | 'spam' | 'pin' | 'feature' | 'trash' | 'restore' | 'delete'

/** status 透传后端（含 all / trashed），不做前端二次过滤。 */
export function fetchAdminGuestbook(params: AdminCommentQuery): Promise<AdminPaged<AdminGuestbookEntry>> {
  const query: Record<string, unknown> = {
    page: params.page ?? 1,
    page_size: params.page_size ?? 20,
    status: params.status ?? 'all'
  }
  if (params.keyword && params.keyword.trim()) query.keyword = params.keyword.trim()
  return apiFetch<AdminPaged<AdminGuestbookEntry>>('/admin/guestbook', { query })
}

/** 审核是三个子动作 POST（/approve | /reject | /spam），不是 PATCH body。 */
export function updateAdminGuestbookStatus(
  entryId: number,
  status: AdminCommentStatus
): Promise<AdminGuestbookEntry> {
  const action = status === 'approved' ? 'approve' : status === 'rejected' ? 'reject' : 'spam'
  return apiFetch<AdminGuestbookEntry>(`/admin/guestbook/${entryId}/${action}`, { method: 'POST' })
}

/** 置顶 / 精华均为 toggle 语义，可安全重复调用。 */
export function toggleAdminGuestbookPin(entryId: number): Promise<AdminGuestbookEntry> {
  return apiFetch<AdminGuestbookEntry>(`/admin/guestbook/${entryId}/pin`, { method: 'POST' })
}

export function toggleAdminGuestbookFeature(entryId: number): Promise<AdminGuestbookEntry> {
  return apiFetch<AdminGuestbookEntry>(`/admin/guestbook/${entryId}/feature`, { method: 'POST' })
}

/** DELETE 为彻底删除（复用批量 delete 通道），非回收站软删除。 */
export function deleteAdminGuestbook(entryId: number): Promise<ApiMessage> {
  return apiFetch<ApiMessage>(`/admin/guestbook/${entryId}`, { method: 'DELETE' })
}

export function batchAdminGuestbook(
  ids: number[],
  action: GuestbookBatchAction
): Promise<ApiMessage> {
  return apiFetch<ApiMessage>('/admin/guestbook/batch', {
    method: 'POST',
    body: { ids: ids.slice(0, 100), action }
  })
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
    .then(r => ((r?.data ?? r) as unknown as AdminAnnouncement))
}

/** PUT /api/admin/announcements/{id} */
export function updateAdminAnnouncement(id: number, payload: Record<string, unknown>): Promise<AdminAnnouncement> {
  return apiFetch<Record<string, unknown>>(`/admin/announcements/${id}`, { method: 'PUT', body: payload })
    .then(r => ((r?.data ?? r) as unknown as AdminAnnouncement))
}

/** DELETE /api/admin/announcements/{id} */
export function deleteAdminAnnouncement(id: number): Promise<ApiMessage> {
  return apiFetch<ApiMessage>(`/admin/announcements/${id}`, { method: 'DELETE' })
}

// ==================== 动态 / 说说 Activity ====================

export interface AdminActivity {
  id: number
  /** 与后端 schemas/activity.py::ActivityType 及 Activity.type 列一致 */
  type: 'say' | 'article' | 'update' | 'notice' | 'link'
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
    .then(r => ((r?.data ?? r) as unknown as AdminActivity))
}

/** PUT /api/admin/activities/{id} */
export function updateAdminActivity(id: number, payload: Record<string, unknown>): Promise<AdminActivity> {
  return apiFetch<Record<string, unknown>>(`/admin/activities/${id}`, { method: 'PUT', body: payload })
    .then(r => ((r?.data ?? r) as unknown as AdminActivity))
}

/** DELETE /api/admin/activities/{id} */
export function deleteAdminActivity(id: number): Promise<ApiMessage> {
  return apiFetch<ApiMessage>(`/admin/activities/${id}`, { method: 'DELETE' })
}

// ==================== 用户头衔 UserTitle ====================

export interface AdminUserTitle {
  id?: number
  name: string | Record<string, string>
  color?: string | null
  icon?: string | null
  description?: string | Record<string, string> | null
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

/**
 * DELETE /api/admin/titles/{id} —— 后端返回 204 No Content（全库唯一一个 204 端点），
 * 因此这里不声明 `ApiMessage`：调用方拿到的是空响应体，任何 `.message` 读取都会 undefined。
 */
export async function deleteAdminUserTitle(id: number): Promise<void> {
  invalidateMemCache('admin:titles:')
  await apiFetch<unknown>(`/admin/titles/${id}`, { method: 'DELETE' })
}

/**
 * POST /api/admin/titles/assign —— title.router 内部 @router.post("/titles/assign")
 * = /api/admin/titles/assign
 * 只负责"赋予某个称号"；取消称号是另一个端点（见 removeAdminUserTitle），
 * 不要在这里用 titleId=null 走伪成功分支——旧实现正是那样返回了一条从未发出的"已移除头衔"。
 */
export function assignAdminUserTitle(userId: number, titleId: number): Promise<ApiMessage> {
  return apiFetch<ApiMessage>('/admin/titles/assign', { method: 'POST', body: { user_id: userId, title_id: titleId } })
}

/** DELETE /api/admin/users/{user_id}/title —— 移除用户称号，返回 { message, user_id }。 */
export function removeAdminUserTitle(userId: number): Promise<ApiMessage> {
  return apiFetch<ApiMessage>(`/admin/users/${userId}/title`, { method: 'DELETE' })
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
  // 后端 /media/library 只认 file_type（见 backend/api/media.py 的 Query 声明）。
  // mime_prefix 是历史别名：映射后必须从 query 里删掉，否则发出去一个后端会静默丢弃的参数，
  // 让人误以为筛选生效了。
  if (params.mime_prefix && !params.file_type) {
    query.file_type = params.mime_prefix
  }
  delete query.mime_prefix
  if (params.search) query.search = params.search
  return apiFetch<AdminPaged<AdminMediaItem>>('/media/library', { query })
}

/** DELETE /api/media/library/{id} —— media.router @router.delete("/library/{media_id}") */
export function deleteAdminMedia(id: number): Promise<ApiMessage> {
  return apiFetch<ApiMessage>(`/media/library/${id}`, { method: 'DELETE' })
}

/** DELETE /api/media/library/batch 的结果：三种条目必须分开上报，不能只看 deleted_count */
export interface AdminMediaBatchDeleteResult extends ApiMessage {
  deleted_count?: number
  /** 路径非法（越权文件）因而**保留数据库记录**的条目，需人工处理 */
  refused?: { id: number, reason: string }[]
  /** 请求里给出但库里不存在的 ID */
  missing_ids?: number[]
}

/** DELETE /api/media/library/batch —— media.router @router.delete("/library/batch") */
export function deleteAdminMediaBatch(ids: number[]): Promise<AdminMediaBatchDeleteResult> {
  return apiFetch<AdminMediaBatchDeleteResult>('/media/library/batch', {
    method: 'DELETE',
    body: { ids }
  })
}

export interface AdminMediaStats {
  total_files: number
  total_size_bytes: number
  images: number
  videos: number
  /** 后端 media.py 以 type_statistics["audio"] 单列音频计数，不与 videos 合并 */
  audios: number
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
  description?: string | null
  thumbnail_url?: string | null
  original_url: string
  url?: string
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

/**
 * GET /api/admin/gallery/albums/{albumId}/photos —— 后端 get_pagination 限制 page_size ≤ 100，
 * 且默认仅 12 条。这里逐页拉全（最多 20 页 = 2000 张，防御异常数据导致的死循环），
 * 保证相册详情页展示全部照片而不是被默认分页截断为 12 张。
 */
export async function fetchAdminPhotos(albumId: number): Promise<AdminPaged<AdminPhoto>> {
  const pageSize = 100
  const maxPages = 20
  const items: AdminPhoto[] = []
  let page = 1
  let total = 0
  let last: AdminPaged<AdminPhoto> | null = null
  while (page <= maxPages) {
    const resp = await apiFetch<AdminPaged<AdminPhoto>>(`/admin/gallery/albums/${albumId}/photos`, {
      query: { page, page_size: pageSize }
    })
    last = resp
    const batch = resp?.items ?? []
    items.push(...batch)
    total = Number(resp?.total ?? items.length)
    if (batch.length === 0) break
    if (items.length >= total) break
    page++
  }
  return {
    items,
    total: total || items.length,
    page: 1,
    page_size: pageSize,
    total_pages: last?.total_pages ?? 1
  }
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

/**
 * DELETE /api/admin/gallery/photos/batch —— 批量删除照片。
 *
 * deleted_count / missing_ids 用于判断是否"真的全删掉了"：
 * 请求里不存在的 ID 会列在 missing_ids，不会让请求失败。
 */
export interface AdminPhotoBatchDeleteResult extends ApiMessage {
  deleted_count?: number
  missing_ids?: number[]
}

export function deleteAdminPhotosBatch(ids: number[]): Promise<AdminPhotoBatchDeleteResult> {
  return apiFetch<AdminPhotoBatchDeleteResult>('/admin/gallery/photos/batch', {
    method: 'DELETE',
    body: { ids }
  })
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

export function deleteAdminNavigation(
  id: number,
  options: AdminToolRequestOptions = {}
): Promise<ApiMessage> {
  return apiFetch<ApiMessage>(`/navigations/${id}`, {
    method: 'DELETE',
    silentToast: options.silentToast ?? false
  })
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

export function deleteAdminFriendLink(
  id: number,
  options: AdminToolRequestOptions = {}
): Promise<ApiMessage> {
  return apiFetch<ApiMessage>(`/friend-links/${id}`, {
    method: 'DELETE',
    silentToast: options.silentToast ?? false
  })
}

// ==================== 响应形状适配（后端 → 前端约定） ====================
// 后端部分接口返回裸对象 / 裸列表 / {success, job} 等非标准信封，
// 这里统一映射为前端页面期望的形状，避免页面拿到 undefined / 字段错位。
// 已声明 response_model 的接口（如 /webhooks）不再需要 mapper：字段契约由
// Pydantic 在服务端保证，前端直接消费类型。

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
  /** 密钥只用于服务端出站签名，接口不再回显明文；页面用「是否已配置」提示 */
  has_secret: boolean
  events: string[]
  active: boolean
  provider: 'github' | 'generic' | 'feishu' | 'email'
  created_at: string | null
  updated_at: string | null
  last_triggered_at: string | null
}

export interface AdminWebhookPayload {
  name: string
  url: string
  /** undefined = 保持原密钥不变；'' = 清除密钥；非空 = 设为该值 */
  secret?: string | null
  events: string[]
  provider: AdminWebhook['provider']
  active: boolean
}

export interface AdminWebhookEvent {
  type: string
  description: string
}

/** GET /api/webhooks —— 服务端 WebhookListOut（items 已是 WebhookOut） */
export function fetchAdminWebhooks(): Promise<AdminWebhook[]> {
  return apiFetch<AdminPaged<AdminWebhook>>('/webhooks').then(r => r.items ?? [])
}

/**
 * GET /api/webhooks/events —— 可订阅事件的唯一清单。
 * 事件名必须来自这里：后端校验的就是 hooks 总线上的 do_action 名，
 * 前端自造一套 post_created 之类的写法会被 422 挡掉。
 */
export function fetchAdminWebhookEvents(): Promise<AdminWebhookEvent[]> {
  return apiFetch<{ events: AdminWebhookEvent[] }>('/webhooks/events').then(r => r.events ?? [])
}

/** POST /api/webhooks —— 返回创建后的完整对象（WebhookOut） */
export function createAdminWebhook(payload: AdminWebhookPayload): Promise<AdminWebhook> {
  return apiFetch<AdminWebhook>('/webhooks', { method: 'POST', body: payload })
}

/** PUT /api/webhooks/{id} —— 返回更新后的完整对象（WebhookOut） */
export function updateAdminWebhook(id: number, payload: Partial<AdminWebhookPayload>): Promise<AdminWebhook> {
  return apiFetch<AdminWebhook>(`/webhooks/${id}`, { method: 'PUT', body: payload })
}

/** DELETE /api/webhooks/{id} */
export function deleteAdminWebhook(id: number): Promise<ApiMessage> {
  return apiFetch<ApiMessage>(`/webhooks/${id}`, { method: 'DELETE' })
}

/**
 * 触发测试：POST /api/webhooks/{id}/test
 * 后端没有 trigger 端点，统一用 test（真实发送一次 test 事件并落投递记录）。
 * success=false 表示目标端点返回失败——HTTP 仍是 200，调用方必须看这个字段。
 */
export function triggerAdminWebhook(id: number): Promise<{ success: boolean, message: string, status_code: number | null }> {
  return apiFetch<{ success: boolean, message: string, status_code: number | null }>(`/webhooks/${id}/test`, { method: 'POST' })
}

/** 投递记录：后端 WebhookDeliveryOut */
export interface AdminWebhookDelivery {
  id: number
  event_type: string
  status_code: number | null
  error: string | null
  response_body: string | null
  delivered_at: string | null
  created_at: string | null
}

/** GET /api/webhooks/{id}/deliveries —— 投递记录（含响应片段） */
export function fetchAdminWebhookDeliveries(id: number): Promise<AdminWebhookDelivery[]> {
  return apiFetch<AdminPaged<AdminWebhookDelivery>>(`/webhooks/${id}/deliveries`).then(r => r.items ?? [])
}

/**
 * POST /api/webhooks/deliveries/{id}/retry —— 复发库内 payload 原文。
 * 目标端点失败时 HTTP 仍是 200，判成败看 success。
 */
export function retryAdminWebhookDelivery(deliveryId: number): Promise<{ success: boolean, message: string }> {
  return apiFetch<{ success: boolean, message: string }>(`/webhooks/deliveries/${deliveryId}/retry`, { method: 'POST' })
}

/**
 * POST /api/webhooks/{id}/regenerate-secret —— 轮换 HMAC 密钥。
 * 明文密钥只有这一个出口（WebhookOut 刻意不含 secret），旧密钥即刻失效，
 * 因此 UI 必须把新值展示一次并提示同步到接收方。
 */
export function regenerateAdminWebhookSecret(id: number): Promise<{ success: boolean, message: string, data: { secret: string } }> {
  return apiFetch<{ success: boolean, message: string, data: { secret: string } }>(`/webhooks/${id}/regenerate-secret`, { method: 'POST' })
}

/**
 * 导入导出的唯一实现放在 `pages/admin/tools/import-export.vue`：
 * 导出要拿 Blob + 进度、导入要 FormData + 结果统计，与这里的薄封装已有实质差异，
 * 保留两份只会让路径漂移（历史教训：/import-export/* 与 /admin/export/* 两套写法并存）。
 */

// ==================== SEO 工具 ====================

export interface AdminSeoScore {
  id: number
  slug: string
  title: string
  score: number
  suggestions: string[]
}

/** GET /api/seo/sitemap-check 的 data 载荷 */
export interface SitemapCheckResult {
  ok: boolean
  url_count: number
  errors: string[]
}

/**
 * GET /api/seo/sitemap-check —— seo.router @router.get("/sitemap-check")
 * 注意：这是**少数手工返回 { success, data } 包壳**的端点（见 backend/api/seo.py sitemap_check），
 * 与全局"裸对象"约定不同，因此这里显式解包 data。
 * 校验失败（后端 5xx / 权限）由调用方展示错误态，不再降级成"后端暂未开放"的假结果。
 */
export function fetchAdminSeoSitemapCheck(
  options: AdminToolRequestOptions = {}
): Promise<SitemapCheckResult> {
  return apiFetch<ApiEnvelope<SitemapCheckResult>>('/seo/sitemap-check', {
    silentToast: options.silentToast ?? true
  }).then((r) => {
    // 缺 data 不能当成"体检通过"：返回空 errors 会让界面绿掉，属假阳性
    if (!r?.data) throw new Error('Sitemap 校验接口未返回数据')
    return {
      ok: r.data.ok === true,
      url_count: Number(r.data.url_count ?? 0),
      errors: Array.isArray(r.data.errors) ? r.data.errors : []
    }
  })
}

/** GET /api/seo/scores —— seo.router @router.get("/scores")：裸分页对象（无 success 信封） */
export function fetchAdminSeoScores(
  params: { page?: number, page_size?: number } = {},
  options: AdminToolRequestOptions = {}
): Promise<AdminPaged<AdminSeoScore>> {
  const page = params.page ?? 1
  const pageSize = params.page_size ?? 20
  return apiFetch<Partial<AdminPaged<AdminSeoScore>>>('/seo/scores', {
    query: { page, page_size: pageSize, ...params },
    silentToast: options.silentToast ?? true
  }).then(r => ({
    items: Array.isArray(r?.items) ? r.items : [],
    total: Number(r?.total ?? 0) || 0,
    page: Number(r?.page ?? page),
    page_size: Number(r?.page_size ?? pageSize),
    total_pages: Number(r?.total_pages ?? 0) || 0
  }))
}

/** POST /api/seo/sitemap/generate —— 重新生成 sitemap.xml */
export function regenerateAdminSitemap(
  options: AdminToolRequestOptions = {}
): Promise<ApiMessage> {
  return apiFetch<ApiMessage>('/seo/sitemap/generate', {
    method: 'POST',
    silentToast: options.silentToast ?? true
  })
}

/**
 * 检索字段体检 —— GET /api/admin/tools/search-stats
 * 后端 response_model=SearchStatsResponse，裸对象无 { success, data } 包壳。
 * 口径是"内容完整度"（SQLite/PG 都走 LIKE 检索，没有全文索引可查）：
 * posts_without_* 同时兜住 SQL NULL、空串与 JSON null 三种"没有内容"形态。
 */
export interface AdminSearchRecommendation {
  type: 'excerpt' | 'slug' | 'tags'
  count: number
  message: string
}

export interface AdminSearchStats {
  total_posts: number
  total_categories: number
  posts_without_excerpt: number
  posts_without_slug: number
  posts_without_tags: number
  avg_slug_length: number
  avg_excerpt_length: number
  recommendations: AdminSearchRecommendation[]
}

export function fetchAdminSearchStats(
  options: AdminToolRequestOptions = {}
): Promise<AdminSearchStats> {
  return apiFetch<Partial<AdminSearchStats>>('/admin/tools/search-stats', {
    silentToast: options.silentToast ?? true
  }).then((r) => {
    // 缺字段一律归零而不是抛错：本接口是只读统计，部分缺失仍可展示
    const num = (v: unknown) => Number(v ?? 0) || 0
    return {
      total_posts: num(r?.total_posts),
      total_categories: num(r?.total_categories),
      posts_without_excerpt: num(r?.posts_without_excerpt),
      posts_without_slug: num(r?.posts_without_slug),
      posts_without_tags: num(r?.posts_without_tags),
      avg_slug_length: num(r?.avg_slug_length),
      avg_excerpt_length: num(r?.avg_excerpt_length),
      recommendations: Array.isArray(r?.recommendations) ? r.recommendations : []
    }
  })
}

/**
 * 补全检索字段 —— POST /api/admin/tools/optimize-search
 * slug 复用建文流程的 generate_slug（中文转拼音 + 唯一性校验），
 * 摘要按每种语言各自的正文生成，因此三个计数分开给。
 */
export interface AdminSearchOptimizeResult {
  success: boolean
  scanned_count: number
  slug_filled_count: number
  excerpt_filled_count: number
  message: string
}

export function runAdminSearchOptimize(
  options: AdminToolRequestOptions = {}
): Promise<AdminSearchOptimizeResult> {
  return apiFetch<Partial<AdminSearchOptimizeResult>>('/admin/tools/optimize-search', {
    method: 'POST',
    silentToast: options.silentToast ?? true
  }).then(r => ({
    success: r?.success === true,
    scanned_count: Number(r?.scanned_count ?? 0) || 0,
    slug_filled_count: Number(r?.slug_filled_count ?? 0) || 0,
    excerpt_filled_count: Number(r?.excerpt_filled_count ?? 0) || 0,
    message: typeof r?.message === 'string' ? r.message : ''
  }))
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

// ==================== 操作审计日志 ====================

export interface AdminAuditLog {
  id: number
  user_id: number | null
  username?: string | null
  action: string
  target_type?: string | null
  target_id?: string | number | null
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
 * 迁移工具的统一请求选项。
 * 这些接口的错误都由页面**内联**渲染（状态卡片旁的重试按钮、确认弹窗里的错误行），
 * 所以默认抑制全局 toast，避免同一错误弹两条。需要全局提示时传 `{ silentToast: false }`。
 */
export interface AdminToolRequestOptions {
  silentToast?: boolean
}

/** GET /api/admin/alembic/status 的返回结构（后端 response_model=AlembicStatusResponse，裸对象无包壳）。 */
export interface AdminAlembicUpgradeResult {
  success: boolean
  message: string
}

/**
 * GET /api/admin/alembic/status —— Alembic schema 版本状态：
 *   current_version / latest_version / is_latest / pending / applied
 * 注意：/api/admin/migration/status 是「跨库数据迁移任务管理器」（Job），
 * 与本处 Alembic schema 版本状态是两套接口（见下方 AdminMigrationJob* 系列）。
 *
 * 错误语义：接口失败一律 reject，由调用方渲染「状态不可用 + 重试」。
 * 早期版本走 silentApiFetch 并 catch 成 is_latest:true，后端宕机时界面会显示
 * "已是最新版本"——误导管理员跳过升级，属危险降级，已移除。
 */
export function fetchAdminMigrationStatus(
  options: AdminToolRequestOptions = {}
): Promise<AdminMigrationStatus> {
  return apiFetch<AdminMigrationStatus>('/admin/alembic/status', {
    silentToast: options.silentToast ?? true
  }).then(r => ({
    current_version: String(r?.current_version ?? ''),
    latest_version: String(r?.latest_version ?? ''),
    is_latest: Boolean(r?.is_latest ?? true),
    pending: (Array.isArray(r?.pending) ? r.pending : []) as AdminMigrationStatus['pending'],
    applied: (Array.isArray(r?.applied) ? r.applied : []) as AdminMigrationStatus['applied']
  }))
}

/**
 * POST /api/admin/alembic/upgrade（admin_tools.router）——
 * 服务端在 asyncio.to_thread 里执行 `alembic upgrade head`；
 * 失败后端返回 500，因此成功响应必为 success:true，调用方无需再判 success。
 */
export function upgradeAdminMigrations(
  options: AdminToolRequestOptions = {}
): Promise<AdminAlembicUpgradeResult> {
  return apiFetch<AdminAlembicUpgradeResult>('/admin/alembic/upgrade', {
    method: 'POST',
    silentToast: options.silentToast ?? true
  })
}

// -------------------- 跨库数据迁移任务（migration.router） --------------------
// 后端真实路径（migration.router prefix="/migration"，main.py 挂 /api/admin）：
//   POST /api/admin/migration/start    {source, target, dry_run, skip_schema} → {success, job}
//   GET  /api/admin/migration/status   → {success, job|null}（最新一次任务）
//   POST /api/admin/migration/cancel   → {success, job}
//   GET  /api/admin/migration/presets  → {success, presets: Record<string,string>}

export type AdminMigrationJobStatus = 'pending' | 'running' | 'done' | 'error' | 'cancelled'

export interface AdminMigrationJobProgress {
  stage?: string
  message?: string
  table?: string
  elapsed?: number
  tables_total?: number
  tables_done?: number
  rows_total?: number
  rows_done?: number
  warnings?: string[]
  errors?: string[]
  [key: string]: unknown
}

export interface AdminMigrationJob {
  job_id: string
  source: string
  target: string
  dry_run: boolean
  skip_schema: boolean
  created_by: string
  created_at: number
  started_at: number | null
  finished_at: number | null
  status: AdminMigrationJobStatus
  latest_progress: AdminMigrationJobProgress | null
  events_count: number
  events_tail: AdminMigrationJobProgress[]
  errors: string[]
  warnings: string[]
}

export interface AdminMigrationStartPayload {
  source: string
  target: string
  dry_run?: boolean
  skip_schema?: boolean
}

/** GET /api/admin/migration/presets —— 常用连接预设（当前库 / SQLite 默认路径等） */
export function fetchAdminMigrationPresets(
  options: AdminToolRequestOptions = {}
): Promise<Record<string, string>> {
  return apiFetch<{ success: boolean, presets?: Record<string, string> }>('/admin/migration/presets', {
    silentToast: options.silentToast ?? false
  })
    .then(r => (r?.presets && typeof r.presets === 'object' ? r.presets : {}))
}

/** POST /api/admin/migration/start —— 发起一次跨库迁移任务（全局同时仅允许一个 running） */
export function startAdminMigrationJob(
  payload: AdminMigrationStartPayload,
  options: AdminToolRequestOptions = {}
): Promise<AdminMigrationJob> {
  return apiFetch<{ success: boolean, job: AdminMigrationJob }>('/admin/migration/start', {
    method: 'POST',
    silentToast: options.silentToast ?? true,
    body: {
      source: payload.source,
      target: payload.target,
      dry_run: payload.dry_run ?? true,
      skip_schema: payload.skip_schema ?? false
    }
  }).then(r => r.job)
}

/**
 * GET /api/admin/migration/status —— 查询最新一次迁移任务。
 * 返回 `null` 表示「确实没有任务」；接口失败必须 reject，
 * 否则轮询会把后端宕机当成任务结束、进度条冻结且无任何提示。
 */
export function fetchAdminMigrationJobStatus(
  options: AdminToolRequestOptions = {}
): Promise<AdminMigrationJob | null> {
  return apiFetch<{ success: boolean, job?: AdminMigrationJob | null }>('/admin/migration/status', {
    silentToast: options.silentToast ?? true
  }).then(r => r?.job ?? null)
}

/** POST /api/admin/migration/cancel —— 取消当前运行中的迁移任务 */
export function cancelAdminMigrationJob(
  options: AdminToolRequestOptions = {}
): Promise<AdminMigrationJob> {
  return apiFetch<{ success: boolean, job: AdminMigrationJob }>('/admin/migration/cancel', {
    method: 'POST',
    silentToast: options.silentToast ?? true
  }).then(r => r.job)
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
 * GET /api/admin/cache/status 与 POST /api/admin/cache/flush 的唯一实现放在
 * `pages/admin/tools/cache.vue`（需要模式选择、批量 key 清退、逐条结果展示等页面态）。
 * 这里只保留 AdminCacheStatus / AdminCacheFlushMode 作为共享契约类型。
 */

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
 * 裸 dict（非 ApiEnvelope）。
 *
 * 失败一律 reject：把接口故障渲染成「暂时没有通知」是让管理员误判系统健康的假阴性。
 * 调用方负责展示错误态 + 重试；默认不弹全局 toast（面板内联展示）。
 */
export function fetchNotifications(params: {
  page?: number
  page_size?: number
  unread_only?: boolean
} = {}, options: AdminToolRequestOptions = {}): Promise<NotificationsListResponse> {
  const page = params.page ?? 1
  const pageSize = params.page_size ?? 10
  return apiFetch<Partial<NotificationsListResponse>>('/notifications', {
    query: { page, page_size: pageSize, unread_only: false, ...params },
    silentToast: options.silentToast ?? true
  }).then(r => ({
    items: Array.isArray(r?.items) ? r.items : [],
    total: Number(r?.total ?? 0) || 0,
    unread_count: Number(r?.unread_count ?? 0) || 0,
    page: Number(r?.page ?? page),
    page_size: Number(r?.page_size ?? pageSize),
    total_pages: Number(r?.total_pages ?? 0) || 0
  }))
}

/**
 * GET /api/notifications/stats —— notification.router @router.get("/stats")
 * 后端返回裸 dict（无 success/data 包裹）。字段名兼容 unread/total 与 unread_count/total_count。
 * 失败 reject，由调用方决定 badge 显示 0 还是错误态。
 */
export function fetchNotificationStats(
  options: AdminToolRequestOptions = {}
): Promise<NotificationsStats> {
  return apiFetch<Record<string, unknown>>('/notifications/stats', {
    silentToast: options.silentToast ?? true
  }).then((r) => {
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

/** POST /api/notifications/{id}/read —— 标记单条已读（失败 reject，调用方乐观回滚） */
export function markNotificationRead(id: number): Promise<void> {
  return apiFetch(`/notifications/${id}/read`, { method: 'POST', silentToast: true })
    .then(() => undefined)
}

/** POST /api/notifications/read-all —— @router.post("/read-all") */
export function markAllNotificationsRead(
  options: AdminToolRequestOptions = {}
): Promise<void> {
  return apiFetch('/notifications/read-all', {
    method: 'POST',
    silentToast: options.silentToast ?? false
  }).then(() => undefined)
}

/** DELETE /api/notifications —— @router.delete("") 清空所有通知（可 read_only=true 只清已读） */
export function clearAllNotifications(
  params: { read_only?: boolean } = {},
  options: AdminToolRequestOptions = {}
): Promise<ApiMessage> {
  return apiFetch<ApiMessage>('/notifications', {
    method: 'DELETE',
    query: { read_only: params.read_only ?? false },
    silentToast: options.silentToast ?? false
  })
}

/** DELETE /api/notifications/{id} —— @router.delete("/{notification_id}") 删除单条 */
export function deleteNotification(
  id: number,
  options: AdminToolRequestOptions = {}
): Promise<void> {
  return apiFetch(`/notifications/${id}`, {
    method: 'DELETE',
    silentToast: options.silentToast ?? false
  }).then(() => undefined)
}
