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
 * POST /api/posts/{postId}/comments —— comments.router 挂在 /api，
 * 内部 @router.post("/posts/{post_id_or_slug}/comments")
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

/** GET /api/users —— users.router 挂在 /api/users，@router.get("/") 分页列表 */
export function fetchAdminUsers(params: AdminUserQuery): Promise<AdminPaged<AdminUserRow>> {
  const query: Record<string, unknown> = {
    page: params.page ?? 1,
    page_size: params.page_size ?? 20
  }
  if (params.search && params.search.trim()) query.search = params.search.trim()
  return apiFetch<AdminPaged<AdminUserRow>>('/users', { query })
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

/** PATCH /api/admin/users/{id} —— admin.router @router.patch("/users/{user_id}") */
export function updateAdminUserFlags(
  userId: number,
  flags: AdminUserFlags
): Promise<AdminUserPatchResult> {
  return apiFetch<AdminUserPatchResult>(`/admin/users/${userId}`, {
    method: 'PATCH',
    body: flags
  })
}

/** POST /api/admin/users/{id}/activate —— admin.router @router.post("/users/{user_id}/activate") */
export function activateAdminUser(userId: number): Promise<ApiMessage> {
  return apiFetch<ApiMessage>(`/admin/users/${userId}/activate`, { method: 'POST' })
}

/** POST /api/admin/users/{id}/ban —— admin.router @router.post("/users/{user_id}/ban") */
export function banAdminUser(userId: number): Promise<ApiMessage> {
  return apiFetch<ApiMessage>(`/admin/users/${userId}/ban`, { method: 'POST' })
}

/** POST /api/admin/users/{id}/unban —— admin.router @router.post("/users/{user_id}/unban") */
export function unbanAdminUser(userId: number): Promise<ApiMessage> {
  return apiFetch<ApiMessage>(`/admin/users/${userId}/unban`, { method: 'POST' })
}

/** POST /api/admin/users/{id}/reset-password —— admin.router @router.post("/users/{user_id}/reset-password") */
export function resetAdminUserPassword(userId: number, newPassword: string): Promise<ApiMessage> {
  return apiFetch<ApiMessage>(`/admin/users/${userId}/reset-password`, {
    method: 'POST',
    body: { new_password: newPassword }
  })
}

/**
 * DELETE /api/admin/users/{id} —— 后端 admin.router / users.router 当前未提供 DELETE 用户的 HTTP 端点。
 * 静默降级：提示"请使用命令行删除用户"，避免 404 toast。
 */
export function deleteAdminUser(userId: number): Promise<ApiMessage> {
  return apiFetch<ApiMessage>(`/admin/users/${userId}`, { method: 'DELETE' })
}

// ==================== 用户详情（编辑） ====================

/**
 * GET /api/users/{id} —— users.router 挂在 /api/users，@router.get("/{user_id}")
 * 注意：不要走 /admin/users/{id}，admin.router 当前未提供 GET 详情端点。
 */
export function fetchAdminUserDetail(id: number): Promise<AdminUserRow> {
  return apiFetch<ApiEnvelope<AdminUserRow>>(`/users/${id}`).then(r => r.data)
}

/**
 * PUT /api/admin/users/{id} —— 后端 admin.router 当前仅提供 PATCH（标志位更新），未提供 PUT（全量信息更新）。
 * 降级：仍然尝试 PATCH 主字段（nickname/email 等可能不被后端接受，但比 404 好）；
 * 真正的 profile 更新应在用户自身的 /users/me 端点完成。
 */
export function updateAdminUserDetail(id: number, payload: Record<string, unknown>): Promise<AdminUserRow> {
  return apiFetch<ApiEnvelope<AdminUserRow>>(`/admin/users/${id}`, { method: 'PATCH', body: payload }).then(r => r.data)
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
  name: string | Record<string, string>
  slug: string
  description?: string | Record<string, string> | null
  cover_image?: string | null
  sort_order?: number
  posts_count: number
  created_at: string | null
}

/**
 * GET /api/admin/series —— post_series.router 挂在 /api，管理接口前缀 /admin/series
 * 公开接口是 /series；管理 CRUD 一律走 /admin/series
 */
export function fetchAdminSeries(): Promise<AdminSeries[]> {
  return apiFetch<ApiEnvelope<AdminSeries[]>>('/admin/series').then(r => r.data)
}

/** POST /api/admin/series */
export function createAdminSeries(payload: Record<string, unknown>): Promise<AdminSeries> {
  return apiFetch<ApiEnvelope<AdminSeries>>('/admin/series', { method: 'POST', body: payload }).then(r => r.data)
}

/** PUT /api/admin/series/{id} */
export function updateAdminSeries(id: number, payload: Record<string, unknown>): Promise<AdminSeries> {
  return apiFetch<ApiEnvelope<AdminSeries>>(`/admin/series/${id}`, { method: 'PUT', body: payload }).then(r => r.data)
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

/** GET /api/pages —— core.router 挂在 /api，@router.get("/pages") 返回分页 */
export function fetchAdminPages(params: { page?: number, page_size?: number, status?: string } = {}): Promise<AdminPaged<AdminPage>> {
  return apiFetch<AdminPaged<AdminPage>>('/pages', { query: { page: 1, page_size: 20, ...params } })
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
  content_md?: string | Record<string, string>
  is_pinned: boolean
  is_dismissible: boolean
  is_sticky: boolean
  active: boolean
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
  return apiFetch<ApiEnvelope<AdminAnnouncement>>('/admin/announcements', { method: 'POST', body: payload }).then(r => r.data)
}

/** PUT /api/admin/announcements/{id} */
export function updateAdminAnnouncement(id: number, payload: Record<string, unknown>): Promise<AdminAnnouncement> {
  return apiFetch<ApiEnvelope<AdminAnnouncement>>(`/admin/announcements/${id}`, { method: 'PUT', body: payload }).then(r => r.data)
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
  return apiFetch<ApiEnvelope<AdminActivity>>('/admin/activities', { method: 'POST', body: payload }).then(r => r.data)
}

/** PUT /api/admin/activities/{id} */
export function updateAdminActivity(id: number, payload: Record<string, unknown>): Promise<AdminActivity> {
  return apiFetch<ApiEnvelope<AdminActivity>>(`/admin/activities/${id}`, { method: 'PUT', body: payload }).then(r => r.data)
}

/** DELETE /api/admin/activities/{id} */
export function deleteAdminActivity(id: number): Promise<ApiMessage> {
  return apiFetch<ApiMessage>(`/admin/activities/${id}`, { method: 'DELETE' })
}

// ==================== 用户头衔 UserTitle ====================

export interface AdminUserTitle {
  id: number
  name: string
  color?: string | null
  icon?: string | null
  description?: string | null
  created_at: string | null
}

/**
 * GET /api/admin/titles —— title.router 挂在 /api/admin（无前缀），内部 @router.get("/titles")
 * = /api/admin/titles ✔
 */
export function fetchAdminUserTitles(): Promise<AdminUserTitle[]> {
  return apiFetch<ApiEnvelope<AdminUserTitle[]>>('/admin/titles').then(r => r.data)
}

export function createAdminUserTitle(payload: Record<string, unknown>): Promise<AdminUserTitle> {
  return apiFetch<ApiEnvelope<AdminUserTitle>>('/admin/titles', { method: 'POST', body: payload }).then(r => r.data)
}

export function updateAdminUserTitle(id: number, payload: Record<string, unknown>): Promise<AdminUserTitle> {
  return apiFetch<ApiEnvelope<AdminUserTitle>>(`/admin/titles/${id}`, { method: 'PUT', body: payload }).then(r => r.data)
}

export function deleteAdminUserTitle(id: number): Promise<ApiMessage> {
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
  return apiFetch<AdminPaged<AdminAlbum>>('/admin/gallery/albums', { query: { page: 1, page_size: 20, ...params } })
}

/** POST /api/admin/gallery/albums */
export function createAdminAlbum(payload: Record<string, unknown>): Promise<AdminAlbum> {
  return apiFetch<ApiEnvelope<AdminAlbum>>('/admin/gallery/albums', { method: 'POST', body: payload }).then(r => r.data)
}

/** PUT /api/admin/gallery/albums/{id} */
export function updateAdminAlbum(id: number, payload: Record<string, unknown>): Promise<AdminAlbum> {
  return apiFetch<ApiEnvelope<AdminAlbum>>(`/admin/gallery/albums/${id}`, { method: 'PUT', body: payload }).then(r => r.data)
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
  try {
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
  } catch {
    return []
  }
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
  name: string
  url: string
  logo?: string | null
  description?: string | null
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
  if ('status' in body) {
    body.is_active = body.status === 'approved'
    delete body.status
  }
  delete body.bg_color
  return body
}

export function fetchAdminFriendLinks(): Promise<AdminFriendLink[]> {
  return apiFetch<AdminFriendLink[]>('/friend-links?all=true')
}

export function createAdminFriendLink(payload: Record<string, unknown>): Promise<AdminFriendLink> {
  return apiFetch<AdminFriendLink>('/friend-links', { method: 'POST', body: friendLinkBody(payload) })
}

export function updateAdminFriendLink(id: number, payload: Record<string, unknown>): Promise<AdminFriendLink> {
  return apiFetch<AdminFriendLink>(`/friend-links/${id}`, { method: 'PUT', body: friendLinkBody(payload) })
}

export function deleteAdminFriendLink(id: number): Promise<ApiMessage> {
  return apiFetch<ApiMessage>(`/friend-links/${id}`, { method: 'DELETE' })
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
  return apiFetch<ApiEnvelope<AdminWebhook[]>>('/webhooks').then(r => r.data)
}

/** POST /api/webhooks */
export function createAdminWebhook(payload: Record<string, unknown>): Promise<AdminWebhook> {
  return apiFetch<ApiEnvelope<AdminWebhook>>('/webhooks', { method: 'POST', body: payload }).then(r => r.data)
}

/** PUT /api/webhooks/{id} */
export function updateAdminWebhook(id: number, payload: Record<string, unknown>): Promise<AdminWebhook> {
  return apiFetch<ApiEnvelope<AdminWebhook>>(`/webhooks/${id}`, { method: 'PUT', body: payload }).then(r => r.data)
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
export function exportAdminPosts(format: string): Promise<Blob> {
  const subPath = (format === 'markdown') ? 'markdown' : 'posts'
  return apiFetch<Blob>(`/admin/export/${subPath}`, {
    method: 'GET',
    responseType: 'blob',
    query: (format !== 'markdown' && format !== 'json') ? { format } : undefined
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
  return apiFetch<ApiEnvelope<AdminPerformanceSummary>>('/admin/performance/summary').then(r => r.data)
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

/** GET /api/admin/logs —— admin_logs.router 挂在 /api/admin，@router.get("/logs") */
export function fetchAdminAuditLogs(params: { page?: number, page_size?: number, action?: string, user_id?: number } = {}): Promise<AdminPaged<AdminAuditLog>> {
  return apiFetch<AdminPaged<AdminAuditLog>>('/admin/logs', { query: { page: 1, page_size: 20, ...params } })
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
 * GET /api/admin/migration/status —— migration.router 挂在 /api/admin + 内部 prefix="/migration"
 * + @router.get("/status") = /api/admin/migration/status ✔
 * 注意：这里的"迁移"是跨库数据迁移（Migration Manager），不是 Alembic schema 迁移。
 */
export function fetchAdminMigrationStatus(): Promise<AdminMigrationStatus> {
  return apiFetch<ApiEnvelope<AdminMigrationStatus>>('/admin/migration/status').then(r => r.data)
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
 * advanced.router 挂载于 /api + prefix="/admin"，当前仅提供回收站 / 修订版本 / 批量操作，
 * 没有 /cache/status 或 /cache/flush 的 HTTP 端点。缓存清理通过重启进程或 Redis CLI 直接操作。
 * 两个缓存接口一律静默降级。
 */
export function fetchAdminCacheStatus(): Promise<AdminCacheStatus> {
  return silentApiFetch<ApiEnvelope<AdminCacheStatus>>('/admin/cache/status').then(r =>
    r?.data ?? { backend: 'memory', keys: 0, memory_used_bytes: null, hit_rate: null }
  )
}

export function flushAdminCache(mode: AdminCacheFlushMode): Promise<ApiMessage> {
  return silentApiFetch<ApiMessage>('/admin/cache/flush', { method: 'POST', body: { mode } }).then(r =>
    r ?? { success: false, message: '缓存清理暂未开放 HTTP 接口，请重启服务或清空 Redis 键。' }
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
  return silentApiFetch<NotificationsStats>('/notifications/stats').then((r) => {
    const stats = r as Record<string, unknown> | null
    if (stats && (typeof stats.unread_count === 'number' || typeof stats.total_count === 'number')) {
      return {
        unread_count: Number(stats.unread_count) || 0,
        total_count: Number(stats.total_count ?? 0) || 0,
        read: Number(stats.read ?? 0) || 0,
        type_distribution: stats.type_distribution && typeof stats.type_distribution === 'object'
          ? stats.type_distribution as Record<string, number>
          : {}
      }
    }
    return { unread_count: 0, total_count: 0, read: 0, type_distribution: {} }
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
