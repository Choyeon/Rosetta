/**
 * 后台管理页（仪表盘 / 评论 / 用户 / 分类·标签 / 站点设置）API 封装。
 * 全部基于 useAPI.ts 的 apiFetch（自动注入 Authorization 与 Accept-Language），
 * 不依赖 useAdmin.ts（其解包方式与当前后端格式不完全一致）。
 */
import { apiFetch } from '~~/composables/useAPI'

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

/** GET /api/admin/stats?range=7d|30d —— 返回 { success, data, message } 包装，需解包 data */
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
}

export interface AdminCommentQuery {
  page?: number
  page_size?: number
  status?: AdminCommentStatusFilter
  keyword?: string
}

/** GET /api/admin/comments —— 直接返回 { items, total, page, page_size, total_pages } */
export function fetchAdminComments(params: AdminCommentQuery): Promise<AdminPaged<AdminComment>> {
  const query: Record<string, unknown> = {
    page: params.page ?? 1,
    page_size: params.page_size ?? 20
  }
  if (params.status && params.status !== 'all') query.status = params.status
  if (params.keyword && params.keyword.trim()) query.keyword = params.keyword.trim()
  return apiFetch<AdminPaged<AdminComment>>('/admin/comments', { query })
}

/** PATCH /api/admin/comments/{id} —— 更新评论状态（status 与 active 后端自动同步） */
export function updateAdminCommentStatus(
  commentId: number,
  status: AdminCommentStatus
): Promise<AdminComment> {
  return apiFetch<AdminComment>(`/admin/comments/${commentId}`, {
    method: 'PATCH',
    body: { status }
  })
}

/** DELETE /api/admin/comments/{id} */
export function deleteAdminComment(commentId: number): Promise<ApiMessage> {
  return apiFetch<ApiMessage>(`/admin/comments/${commentId}`, { method: 'DELETE' })
}

export type CommentBatchActionType = 'approve' | 'reject' | 'spam' | 'delete'

/** POST /api/admin/comments/batch —— 批量操作（ids 后端限制 1~100 条） */
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
 * POST /api/posts/{postId}/comments —— 以当前登录管理员身份回复评论。
 * 后端嵌套回复限制 1 层：目标一律为根评论（parent_id 为空时用自身 id）。
 */
export function replyToComment(
  postId: number,
  rootCommentId: number,
  content: string
): Promise<ReplyCommentResult> {
  return apiFetch<ReplyCommentResult>(`/posts/${postId}/comments`, {
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
  is_banned: boolean
  created_at: string | null
  last_login: string | null
  posts_count: number
  comments_count: number
}

export interface AdminUserQuery {
  page?: number
  page_size?: number
  search?: string
}

/** GET /api/admin/users —— 直接返回分页结构（需超级管理员权限） */
export function fetchAdminUsers(params: AdminUserQuery): Promise<AdminPaged<AdminUserRow>> {
  const query: Record<string, unknown> = {
    page: params.page ?? 1,
    page_size: params.page_size ?? 20
  }
  if (params.search && params.search.trim()) query.search = params.search.trim()
  return apiFetch<AdminPaged<AdminUserRow>>('/admin/users', { query })
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
  is_banned: boolean
}

export interface AdminUserFlags {
  is_staff?: boolean
  is_active?: boolean
  is_banned?: boolean
}

/** PATCH /api/admin/users/{id} —— 更新用户标志位（角色 staff / 激活 / 封禁） */
export function updateAdminUserFlags(
  userId: number,
  flags: AdminUserFlags
): Promise<AdminUserPatchResult> {
  return apiFetch<AdminUserPatchResult>(`/admin/users/${userId}`, {
    method: 'PATCH',
    body: flags
  })
}

/** POST /api/admin/users/{id}/activate —— 激活（同时解封） */
export function activateAdminUser(userId: number): Promise<ApiMessage> {
  return apiFetch<ApiMessage>(`/admin/users/${userId}/activate`, { method: 'POST' })
}

/** POST /api/admin/users/{id}/ban —— 封禁（禁用） */
export function banAdminUser(userId: number): Promise<ApiMessage> {
  return apiFetch<ApiMessage>(`/admin/users/${userId}/ban`, { method: 'POST' })
}

/** POST /api/admin/users/{id}/unban —— 解封 */
export function unbanAdminUser(userId: number): Promise<ApiMessage> {
  return apiFetch<ApiMessage>(`/admin/users/${userId}/unban`, { method: 'POST' })
}

/** POST /api/admin/users/{id}/reset-password —— 重置密码（至少8位，含大小写与数字） */
export function resetAdminUserPassword(userId: number, newPassword: string): Promise<ApiMessage> {
  return apiFetch<ApiMessage>(`/admin/users/${userId}/reset-password`, {
    method: 'POST',
    body: { new_password: newPassword }
  })
}

/** DELETE /api/admin/users/{id} —— 删除用户（软删除，评论等引用被置空） */
export function deleteAdminUser(userId: number): Promise<ApiMessage> {
  return apiFetch<ApiMessage>(`/admin/users/${userId}`, { method: 'DELETE' })
}

// ==================== 分类 / 标签管理 ====================

export interface AdminCategory {
  id: number
  name: string
  slug: string
  description: string | null
  icon: string | null
  color: string | null
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

export interface AdminTaxonomyPayload {
  /** 名称；后端为多语言 dict，这里以 zh 为主语言发送 */
  name: string
  slug?: string
  description?: string
  icon?: string
  color?: string
  is_active?: boolean
}

/** 多语言字段包装：{ zh: name } */
function localizedBody(payload: AdminTaxonomyPayload): Record<string, unknown> {
  const body: Record<string, unknown> = { name: { zh: payload.name } }
  if (payload.slug && payload.slug.trim()) body.slug = payload.slug.trim()
  if (payload.description && payload.description.trim()) {
    body.description = { zh: payload.description.trim() }
  }
  if (payload.icon && payload.icon.trim()) body.icon = payload.icon.trim()
  if (payload.color && payload.color.trim()) body.color = payload.color.trim()
  if (payload.is_active !== undefined) body.is_active = payload.is_active
  return body
}

/** GET /api/blog/categories —— 分类列表（含已发布文章数，本地化名称） */
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

/** DELETE /api/blog/categories/{id} —— 删除分类（有文章关联时以后端报错为准） */
export function deleteAdminCategory(categoryId: number): Promise<ApiMessage> {
  return apiFetch<ApiMessage>(`/blog/categories/${categoryId}`, { method: 'DELETE' })
}

/** GET /api/blog/tags —— 标签列表（含文章数与启用状态） */
export function fetchAdminTags(): Promise<AdminTag[]> {
  return apiFetch<AdminTag[]>('/blog/tags')
}

/** POST /api/blog/tags —— 创建标签 */
export function createAdminTag(payload: AdminTaxonomyPayload): Promise<AdminTag> {
  return apiFetch<AdminTag>('/blog/tags', {
    method: 'POST',
    body: localizedBody(payload)
  })
}

/** PUT /api/blog/tags/{id} —— 更新标签 */
export function updateAdminTag(tagId: number, payload: AdminTaxonomyPayload): Promise<AdminTag> {
  return apiFetch<AdminTag>(`/blog/tags/${tagId}`, {
    method: 'PUT',
    body: localizedBody(payload)
  })
}

/** DELETE /api/blog/tags/{id} —— 删除标签 */
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

/** GET /api/settings —— 返回 { groups: { groupKey: {...} } }（全部 17 组） */
export function fetchAllSettings(): Promise<AllSettingsGroups> {
  return apiFetch<AllSettingsResponse>('/settings').then(res => res.groups)
}

/** PATCH /api/settings/{group} —— 保存单个设置组 */
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
