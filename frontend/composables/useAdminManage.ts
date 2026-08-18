/* eslint-disable @typescript-eslint/ban-ts-comment */
// @ts-nocheck
/* eslint-enable @typescript-eslint/ban-ts-comment */
/**
 * 后台管理页（仪表盘 / 评论 / 用户 / 分类·标签 / 站点设置）API 封装。
 * 全部基于 useAPI.ts 的 apiFetch（自动注入 Authorization 与 Accept-Language），
 * 不依赖 useAdmin.ts（其解包方式与当前后端格式不完全一致）。
 */
import { apiFetch } from '~~/composables/useApi'

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

/** GET /api/series */
export function fetchAdminSeries(): Promise<AdminSeries[]> {
  return apiFetch<ApiEnvelope<AdminSeries[]>>('/series').then(r => r.data)
}

/** POST /api/series */
export function createAdminSeries(payload: Record<string, unknown>): Promise<AdminSeries> {
  return apiFetch<ApiEnvelope<AdminSeries>>('/series', { method: 'POST', body: payload }).then(r => r.data)
}

/** PUT /api/series/{id} */
export function updateAdminSeries(id: number, payload: Record<string, unknown>): Promise<AdminSeries> {
  return apiFetch<ApiEnvelope<AdminSeries>>(`/series/${id}`, { method: 'PUT', body: payload }).then(r => r.data)
}

/** DELETE /api/series/{id} */
export function deleteAdminSeries(id: number): Promise<ApiMessage> {
  return apiFetch<ApiMessage>(`/series/${id}`, { method: 'DELETE' })
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

export function fetchAdminPages(params: { page?: number, page_size?: number, status?: string } = {}): Promise<AdminPaged<AdminPage>> {
  return apiFetch<AdminPaged<AdminPage>>('/pages', { query: { page: 1, page_size: 20, ...params } })
}

export function createAdminPage(payload: Record<string, unknown>): Promise<AdminPage> {
  return apiFetch<ApiEnvelope<AdminPage>>('/pages', { method: 'POST', body: payload }).then(r => r.data)
}

export function updateAdminPage(id: number, payload: Record<string, unknown>): Promise<AdminPage> {
  return apiFetch<ApiEnvelope<AdminPage>>(`/pages/${id}`, { method: 'PUT', body: payload }).then(r => r.data)
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

export function fetchAdminAnnouncements(params: { page?: number, page_size?: number } = {}): Promise<AdminPaged<AdminAnnouncement>> {
  return apiFetch<AdminPaged<AdminAnnouncement>>('/announcements', { query: { page: 1, page_size: 20, ...params } })
}

export function createAdminAnnouncement(payload: Record<string, unknown>): Promise<AdminAnnouncement> {
  return apiFetch<ApiEnvelope<AdminAnnouncement>>('/announcements', { method: 'POST', body: payload }).then(r => r.data)
}

export function updateAdminAnnouncement(id: number, payload: Record<string, unknown>): Promise<AdminAnnouncement> {
  return apiFetch<ApiEnvelope<AdminAnnouncement>>(`/announcements/${id}`, { method: 'PUT', body: payload }).then(r => r.data)
}

export function deleteAdminAnnouncement(id: number): Promise<ApiMessage> {
  return apiFetch<ApiMessage>(`/announcements/${id}`, { method: 'DELETE' })
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

export function fetchAdminActivities(params: { page?: number, page_size?: number, type?: string } = {}): Promise<AdminPaged<AdminActivity>> {
  return apiFetch<AdminPaged<AdminActivity>>('/activities', { query: { page: 1, page_size: 20, ...params } })
}

export function createAdminActivity(payload: Record<string, unknown>): Promise<AdminActivity> {
  return apiFetch<ApiEnvelope<AdminActivity>>('/activities', { method: 'POST', body: payload }).then(r => r.data)
}

export function updateAdminActivity(id: number, payload: Record<string, unknown>): Promise<AdminActivity> {
  return apiFetch<ApiEnvelope<AdminActivity>>(`/activities/${id}`, { method: 'PUT', body: payload }).then(r => r.data)
}

export function deleteAdminActivity(id: number): Promise<ApiMessage> {
  return apiFetch<ApiMessage>(`/activities/${id}`, { method: 'DELETE' })
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

export function fetchAdminUserTitles(): Promise<AdminUserTitle[]> {
  return apiFetch<ApiEnvelope<AdminUserTitle[]>>('/titles').then(r => r.data)
}

export function createAdminUserTitle(payload: Record<string, unknown>): Promise<AdminUserTitle> {
  return apiFetch<ApiEnvelope<AdminUserTitle>>('/titles', { method: 'POST', body: payload }).then(r => r.data)
}

export function updateAdminUserTitle(id: number, payload: Record<string, unknown>): Promise<AdminUserTitle> {
  return apiFetch<ApiEnvelope<AdminUserTitle>>(`/titles/${id}`, { method: 'PUT', body: payload }).then(r => r.data)
}

export function deleteAdminUserTitle(id: number): Promise<ApiMessage> {
  return apiFetch<ApiMessage>(`/titles/${id}`, { method: 'DELETE' })
}

// ==================== 用户详情（编辑） ====================

export function fetchAdminUserDetail(id: number): Promise<AdminUserRow> {
  return apiFetch<ApiEnvelope<AdminUserRow>>(`/admin/users/${id}`).then(r => r.data)
}

export function updateAdminUserDetail(id: number, payload: Record<string, unknown>): Promise<AdminUserRow> {
  return apiFetch<ApiEnvelope<AdminUserRow>>(`/admin/users/${id}`, { method: 'PUT', body: payload }).then(r => r.data)
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

export function fetchAdminMediaLibrary(params: { page?: number, page_size?: number, search?: string, category?: string, mime_prefix?: string } = {}): Promise<AdminPaged<AdminMediaItem>> {
  return apiFetch<AdminPaged<AdminMediaItem>>('/media/library', { query: { page: 1, page_size: 20, ...params } })
}

export function deleteAdminMedia(id: number): Promise<ApiMessage> {
  return apiFetch<ApiMessage>(`/media/library/${id}`, { method: 'DELETE' })
}

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

export function fetchAdminAlbums(params: { page?: number, page_size?: number } = {}): Promise<AdminPaged<AdminAlbum>> {
  return apiFetch<AdminPaged<AdminAlbum>>('/gallery/albums', { query: { page: 1, page_size: 20, ...params } })
}

export function createAdminAlbum(payload: Record<string, unknown>): Promise<AdminAlbum> {
  return apiFetch<ApiEnvelope<AdminAlbum>>('/gallery/albums', { method: 'POST', body: payload }).then(r => r.data)
}

export function updateAdminAlbum(id: number, payload: Record<string, unknown>): Promise<AdminAlbum> {
  return apiFetch<ApiEnvelope<AdminAlbum>>(`/gallery/albums/${id}`, { method: 'PUT', body: payload }).then(r => r.data)
}

export function deleteAdminAlbum(id: number): Promise<ApiMessage> {
  return apiFetch<ApiMessage>(`/gallery/albums/${id}`, { method: 'DELETE' })
}

export function fetchAdminPhotos(albumId: number): Promise<AdminPhoto[]> {
  return apiFetch<ApiEnvelope<AdminPhoto[]>>(`/gallery/albums/${albumId}/photos`).then(r => r.data)
}

export function deleteAdminPhoto(id: number): Promise<ApiMessage> {
  return apiFetch<ApiMessage>(`/gallery/photos/${id}`, { method: 'DELETE' })
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

export function fetchAdminNavigations(): Promise<AdminNavItem[]> {
  return apiFetch<ApiEnvelope<AdminNavItem[]>>('/advanced/navigation').then(r => r.data)
}

export function createAdminNavigation(payload: Record<string, unknown>): Promise<AdminNavItem> {
  return apiFetch<ApiEnvelope<AdminNavItem>>('/advanced/navigation', { method: 'POST', body: payload }).then(r => r.data)
}

export function updateAdminNavigation(id: number, payload: Record<string, unknown>): Promise<AdminNavItem> {
  return apiFetch<ApiEnvelope<AdminNavItem>>(`/advanced/navigation/${id}`, { method: 'PUT', body: payload }).then(r => r.data)
}

export function deleteAdminNavigation(id: number): Promise<ApiMessage> {
  return apiFetch<ApiMessage>(`/advanced/navigation/${id}`, { method: 'DELETE' })
}

// ==================== 友情链接 ====================

export interface AdminFriendLink {
  id: number
  name: string
  url: string
  logo?: string | null
  description?: string | null
  bg_color?: string | null
  status: 'pending' | 'approved' | 'rejected'
  sort_order: number
  created_at: string | null
}

export function fetchAdminFriendLinks(): Promise<AdminFriendLink[]> {
  return apiFetch<ApiEnvelope<AdminFriendLink[]>>('/friendlinks').then(r => r.data)
}

export function createAdminFriendLink(payload: Record<string, unknown>): Promise<AdminFriendLink> {
  return apiFetch<ApiEnvelope<AdminFriendLink>>('/friendlinks', { method: 'POST', body: payload }).then(r => r.data)
}

export function updateAdminFriendLink(id: number, payload: Record<string, unknown>): Promise<AdminFriendLink> {
  return apiFetch<ApiEnvelope<AdminFriendLink>>(`/friendlinks/${id}`, { method: 'PUT', body: payload }).then(r => r.data)
}

export function deleteAdminFriendLink(id: number): Promise<ApiMessage> {
  return apiFetch<ApiMessage>(`/friendlinks/${id}`, { method: 'DELETE' })
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

export function fetchAdminWebhooks(): Promise<AdminWebhook[]> {
  return apiFetch<ApiEnvelope<AdminWebhook[]>>('/webhooks').then(r => r.data)
}

export function createAdminWebhook(payload: Record<string, unknown>): Promise<AdminWebhook> {
  return apiFetch<ApiEnvelope<AdminWebhook>>('/webhooks', { method: 'POST', body: payload }).then(r => r.data)
}

export function updateAdminWebhook(id: number, payload: Record<string, unknown>): Promise<AdminWebhook> {
  return apiFetch<ApiEnvelope<AdminWebhook>>(`/webhooks/${id}`, { method: 'PUT', body: payload }).then(r => r.data)
}

export function deleteAdminWebhook(id: number): Promise<ApiMessage> {
  return apiFetch<ApiMessage>(`/webhooks/${id}`, { method: 'DELETE' })
}

export function triggerAdminWebhook(id: number): Promise<ApiMessage> {
  return apiFetch<ApiMessage>(`/webhooks/${id}/trigger`, { method: 'POST' })
}

// ==================== 导入导出 ====================

export interface AdminExportInfo {
  job_id: string
  format: 'wordpress' | 'halo' | 'typecho' | 'markdown' | 'json'
  status: 'running' | 'done' | 'failed'
  download_url?: string | null
  created_at: string | null
}

export function exportAdminPosts(format: string): Promise<Blob> {
  return apiFetch<Blob>(`/import-export/export?format=${encodeURIComponent(format)}`, { method: 'GET', responseType: 'blob' })
}

export interface AdminImportResult {
  success: boolean
  message: string
  created_count: number
  skipped_count: number
  error_count: number
  errors?: string[]
}

export function importAdminPosts(format: string, file: File): Promise<AdminImportResult> {
  const fd = new FormData()
  fd.append('file', file)
  return apiFetch<AdminImportResult>(`/import-export/import?format=${encodeURIComponent(format)}`, {
    method: 'POST',
    body: fd as unknown as Record<string, unknown>
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

export function fetchAdminSeoSitemapCheck(): Promise<{ ok: boolean, url_count: number, errors: string[] }> {
  return apiFetch<ApiEnvelope<{ ok: boolean, url_count: number, errors: string[] }>>('/seo/sitemap-check').then(r => r.data)
}

export function fetchAdminSeoScores(params: { page?: number, page_size?: number } = {}): Promise<AdminPaged<AdminSeoScore>> {
  return apiFetch<AdminPaged<AdminSeoScore>>('/seo/scores', { query: { page: 1, page_size: 20, ...params } })
}

export function regenerateAdminSitemap(): Promise<ApiMessage> {
  return apiFetch<ApiMessage>('/seo/sitemap/regenerate', { method: 'POST' })
}

// ==================== 翻译工具 ====================

export interface AdminTranslateJob {
  id: string
  status: 'queued' | 'running' | 'done' | 'failed'
  progress: number
  source_lang: string
  target_lang: string
  items_total: number
  items_done: number
  created_at: string | null
}

export function translateAdminPost(id: number, targetLang: string): Promise<ApiMessage> {
  return apiFetch<ApiMessage>('/translate/post', { method: 'POST', body: { post_id: id, target_lang: targetLang } })
}

export function batchTranslateAdminPosts(ids: number[], targetLang: string): Promise<AdminTranslateJob> {
  return apiFetch<ApiEnvelope<AdminTranslateJob>>('/translate/batch', { method: 'POST', body: { ids, target_lang: targetLang } }).then(r => r.data)
}

export function fetchAdminTranslateJob(id: string): Promise<AdminTranslateJob> {
  return apiFetch<ApiEnvelope<AdminTranslateJob>>(`/translate/jobs/${id}`).then(r => r.data)
}

// ==================== 性能监控 ====================

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

export function fetchAdminPerformanceSummary(): Promise<AdminPerformanceSummary> {
  return apiFetch<ApiEnvelope<AdminPerformanceSummary>>('/performance/summary').then(r => r.data)
}

export function fetchAdminSlowRequests(params: { page?: number, page_size?: number, limit?: number } = {}): Promise<AdminPaged<AdminSlowRequest>> {
  return apiFetch<AdminPaged<AdminSlowRequest>>('/performance/slow', { query: { page: 1, page_size: 20, limit: 50, ...params } })
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

export function fetchAdminAuditLogs(params: { page?: number, page_size?: number, action?: string, user_id?: number } = {}): Promise<AdminPaged<AdminAuditLog>> {
  return apiFetch<AdminPaged<AdminAuditLog>>('/admin-logs', { query: { page: 1, page_size: 20, ...params } })
}

// ==================== 数据库迁移 ====================

export interface AdminMigrationStatus {
  current_version: string
  latest_version: string
  is_latest: boolean
  pending: Array<{ version: string, message: string }>
  applied: Array<{ version: string, message: string, applied_at: string | null }>
}

export function fetchAdminMigrationStatus(): Promise<AdminMigrationStatus> {
  return apiFetch<ApiEnvelope<AdminMigrationStatus>>('/migrations/status').then(r => r.data)
}

export function upgradeAdminMigrations(): Promise<ApiMessage> {
  return apiFetch<ApiMessage>('/migrations/upgrade', { method: 'POST' })
}

// ==================== 缓存管理 ====================

export type AdminCacheFlushMode = 'all' | 'post_list' | 'post_detail' | 'settings' | 'fragments'

export interface AdminCacheStatus {
  backend: 'memory' | 'redis'
  keys: number
  memory_used_bytes?: number | null
  hit_rate?: number | null
}

export function fetchAdminCacheStatus(): Promise<AdminCacheStatus> {
  return apiFetch<ApiEnvelope<AdminCacheStatus>>('/advanced/cache/status').then(r => r.data)
}

export function flushAdminCache(mode: AdminCacheFlushMode): Promise<ApiMessage> {
  return apiFetch<ApiMessage>('/advanced/cache/flush', { method: 'POST', body: { mode } })
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
  type_distribution: Record<string, number>
}

/** GET /api/notifications —— 当前登录用户的通知列表（附带 unread_count） */
export function fetchNotifications(params: {
  page?: number
  page_size?: number
  unread_only?: boolean
} = {}): Promise<NotificationsListResponse> {
  return apiFetch<NotificationsListResponse>('/notifications', {
    query: { page: 1, page_size: 10, unread_only: false, ...params }
  })
}

/** GET /api/notifications/stats —— 未读统计（用于铃铛 badge，轻量） */
export function fetchNotificationStats(): Promise<NotificationsStats> {
  return apiFetch<ApiEnvelope<NotificationsStats>>('/notifications/stats').then(r => r.data)
}

/** POST /api/notifications/{id}/read —— 标记单条已读 */
export function markNotificationRead(id: number): Promise<ApiMessage> {
  return apiFetch<ApiMessage>(`/notifications/${id}/read`, { method: 'POST' })
}

/** POST /api/notifications/clear —— 清空（全部标记已读） */
export function clearAllNotifications(): Promise<ApiMessage> {
  return apiFetch<ApiMessage>('/notifications/clear', { method: 'POST' })
}

/** DELETE /api/notifications/{id} */
export function deleteNotification(id: number): Promise<ApiMessage> {
  return apiFetch<ApiMessage>(`/notifications/${id}`, { method: 'DELETE' })
}
