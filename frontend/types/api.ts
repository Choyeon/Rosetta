// API Response Types
export interface BaseResponse {
  success: boolean
  message: string
  data?: unknown
}

export interface PaginatedResponse<T = unknown> {
  items: T[]
  total: number
  page: number
  page_size: number
  total_pages: number
}

// User Types
export interface User {
  id: number
  username: string
  email: string
  nickname?: string
  avatar?: string
  bio?: string
  website?: string
  github?: string
  qq?: string
  cover_image?: string
  is_active: boolean
  is_staff: boolean
  is_superuser: boolean
  title?: UserTitle
  created_at: string
  last_login?: string
}

/**
 * 公开作者卡片 —— 对应后端 `PublicUserResponse`。
 * 文章 / 相册 / 动态等公开资源的 author 字段用这个类型，**不含** email、qq、
 * is_active / is_staff / is_superuser、role、last_login 等私密与提权字段，
 * 也**不含** website / github：这两个社交链接受 `UserPreference.show_social_links`
 * 管，而这张卡片挂在每一篇匿名可读的文章上、还进响应缓存，留着就是给那个开关留旁路。
 * 社交链接只在作者主页资料（`User`）上出现。
 * 需要完整账号资料（后台、个人中心）时用 `User`。
 */
export interface PublicUser {
  id: number
  username: string
  nickname?: string
  avatar?: string
  bio?: string
  cover_image?: string
  avatar_source?: string
  resolved_avatar_url?: string
  title?: UserTitle
  created_at: string
}

export interface UserTitle {
  id: number
  name: string | Record<string, string>
  color: string
  icon?: string
}

export interface TokenResponse {
  access_token: string
  refresh_token: string
  token_type: string
  expires_in: number
}

// Post Types
export interface Post {
  id: number
  title: string | Record<string, string>
  /** 多语言副标题；后台编辑表单可写，文章页在主标题下作为导语展示。 */
  subtitle?: string | Record<string, string> | null
  slug: string
  /** 来源（默认「原创」）；文章页只在非默认值或有原文链接时展示。 */
  source?: string
  /** 原文出处；后端严格档只收 http(s)，渲染侧仍要再判一次 scheme。 */
  source_url?: string | null
  /** 站内音视频（后端第四档只收 `/...` 路径，外链会被 CSP media-src 拦掉）。 */
  audio?: string | null
  video?: string | null
  /** YouTube 嵌入地址；渲染侧只允许用解析出的 11 位 ID 拼 iframe src。 */
  video_url?: string | null
  content: string | Record<string, string>
  /** null = 库里没有摘要（清空后的行就是 JSON null），回落口径在读侧处理。 */
  excerpt?: string | Record<string, string> | null
  cover_image?: string
  /** 公开作者卡片；后台需要完整账号资料时用 useAuthStore().user。 */
  author?: PublicUser
  category?: Category
  tags: Tag[]
  /** 所属系列（章节容器）：编辑器回填后 PUT 必须原样带上，否则一次普通编辑就把文章踢出系列 */
  series_id?: number | null
  series_order?: number | null
  status: 'draft' | 'published' | 'archived' | 'scheduled'
  /** 仅 status=scheduled 时有值；库内为 UTC，编辑表单按 UTC 字面值回填。 */
  scheduled_at?: string
  views: number
  likes_count: number
  comments_count: number
  is_pinned: boolean
  allow_comments: boolean
  is_password_protected?: boolean
  /** 密码提示：仅当文章真有访问密码时后端才输出，闸门页在锁屏上展示。 */
  encryption_hint?: string | null
  visibility?: 'public' | 'password' | 'private'
  meta_title?: string | Record<string, string> | null
  meta_description?: string | Record<string, string> | null
  meta_keywords?: string | Record<string, string> | null
  /** 内容类型 key（默认 post）；公开详情与 /edit 都会回显，前台据此查 /api/content-types 定义。 */
  post_type?: string
  /** 自定义内容类型的字段值；定义之外的历史键读侧不做校验，渲染侧只展示定义内且非空的值。 */
  meta_fields?: Record<string, unknown> | null
  created_at: string
  published_at?: string
  updated_at?: string
  reading_time: number
  /** 列表项的媒体存在性三位（批次 #120）：只带"有没有"，地址仍只有详情口回。 */
  has_audio?: boolean
  has_video?: boolean
  has_embed?: boolean
}

export interface PostCreate {
  title: string | Record<string, string>
  /** null = 清掉副标题；省略等于"不动它"（后端 PUT 是 exclude_unset 增量语义）。 */
  subtitle?: string | Record<string, string> | null
  slug?: string
  source?: string
  /** 显式 null = 清掉原文链接（后端 PUT 是 exclude_unset 增量语义）。 */
  source_url?: string | null
  /** 音视频三列同一条「清空要显式发送」口径：null = 清掉，省略 = 不动它。 */
  audio?: string | null
  video?: string | null
  video_url?: string | null
  content: string | Record<string, string>
  /** null = 清掉摘要；省略等于"不动它"（后端 PUT 是 exclude_unset 增量语义）。 */
  excerpt?: string | Record<string, string> | null
  cover_image?: string
  // 后端 PostBase/PostUpdate 的 category_id 是 `int | None`：显式 null 表示"取消分类"，
  // 而省略该键在 exclude_unset 语义下等于"不动它"。类型必须允许 null，否则"无分类"
  // 这个操作在类型层面就写不出来。
  category_id?: number | null
  tag_ids?: number[]
  series_id?: number | null
  series_order?: number
  status?: 'draft' | 'published' | 'scheduled'
  visibility?: 'public' | 'password' | 'private'
  scheduled_at?: string
  password?: string
  /** 密码提示（可选，最长 200）；明文出现在锁屏上，不要写成密码本身。 */
  encryption_hint?: string
  is_pinned?: boolean
  allow_comments?: boolean
  meta_title?: string | Record<string, string> | null
  meta_description?: string | Record<string, string> | null
  meta_keywords?: string | Record<string, string> | null
  /** 内容类型 key；编辑器始终发送（默认 post），换类型时要连同 meta_fields 一起提交。 */
  post_type?: string
  /** null = 清空自定义字段；省略等于"不动它"（后端 PUT 是 exclude_unset 增量语义）。 */
  meta_fields?: Record<string, unknown> | null
}

// Category Types
export interface Category {
  id: number
  name: string | Record<string, string>
  slug: string
  description?: string | Record<string, string>
  icon?: string
  color?: string
  cover_image?: string
  created_at: string
  post_count?: number
}

// Tag Types
export interface Tag {
  id: number
  name: string | Record<string, string>
  slug: string
  color?: string
  icon?: string
  is_active: boolean
  created_at: string
  post_count?: number
}

// Comment Types
export interface Comment {
  id: number
  post_id: number
  user: User
  parent_id?: number
  content: string
  active: boolean
  created_at: string
  replies?: Comment[]
}

// Navigation Types
export interface Navigation {
  id: number
  title: string | Record<string, string>
  url: string
  icon?: string
  parent_id?: number
  location: 'header' | 'footer' | 'sidebar'
  order: number
  is_active: boolean
  target_blank: boolean
}

// Friend Link Types
export interface FriendLink {
  id: number
  name: string
  url: string
  description?: string
  logo?: string
  order: number
  is_active: boolean
  target_blank: boolean
}

/**
 * `POST /friend-links/apply` 的回执（后端 `FriendLinkApplyReceipt` 同构）。
 *
 * `duplicate=true` 时接口回的是 **200** 且没有新建行（库里已有同地址的 pending/approved），
 * 前端据此把文案切成「已经提交过了」，不必为冲突另写一个错误分支。
 */
export interface FriendLinkApplyReceipt {
  id: number
  status: 'pending' | 'approved'
  duplicate: boolean
  message: string
}

// Page Types
export interface Page {
  id: number
  title: string | Record<string, string>
  slug: string
  content: string | Record<string, string>
  status: 'draft' | 'published'
  created_at: string
  updated_at?: string
}

// OOBE Types
export interface OOBEStatus {
  oobe_complete: boolean
  has_config: boolean
  state?: unknown
  config?: unknown
}

export interface OOBEInstallRequest {
  database_type: 'sqlite' | 'postgresql'
  db_host?: string
  db_port?: number
  db_name?: string
  db_user?: string
  db_password?: string
  db_path?: string
  redis_enabled?: boolean
  redis_host?: string
  redis_port?: number
  redis_password?: string
  admin_username: string
  admin_email: string
  admin_password: string
  admin_nickname?: string
  admin_bio?: string
  admin_qq?: string
  admin_github?: string
  admin_website?: string
  admin_avatar_source?: string
  site_name: string
  site_description: string
  site_url: string
  site_keywords?: string
  site_author?: string
  site_email?: string
  enable_comments?: boolean
  enable_registration?: boolean
  enable_rss?: boolean
  enable_bing_wallpaper?: boolean
  environment?: 'development' | 'production'
}

// Stats Types
export interface SiteStats {
  total_words: number
  total_posts: number
  total_categories: number
  total_tags: number
}

// Media Item Types
export interface MediaItem {
  id: number
  user?: User
  title?: string
  description?: string
  alt_text?: string
  filename: string
  original_name?: string
  url: string
  thumbnail_url?: string
  category: 'image' | 'video' | 'audio' | 'document' | 'other'
  mime_type: string
  size: number
  width?: number
  height?: number
  duration?: number
  storage: 'local' | 's3' | 'oss' | 'cos' | 'other'
  metadata?: Record<string, unknown>
  is_active: boolean
  created_at: string
  updated_at?: string
}

// 站内通知目前没有共享类型：后台通知面板按需内联声明形状。

// Media Library 相关的行/查询类型见 ~~/types/media-library 与 useAdminManage.ts 的 AdminMediaItem。

export interface AdminUserCreate {
  username: string
  email: string
  password: string
  nickname?: string
  is_staff?: boolean
  is_superuser?: boolean
  is_active?: boolean
}
