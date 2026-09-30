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
 * is_active / is_staff / is_superuser、role、last_login 等私密与提权字段。
 * 需要完整账号资料（后台、个人中心）时用 `User`。
 */
export interface PublicUser {
  id: number
  username: string
  nickname?: string
  avatar?: string
  bio?: string
  website?: string
  github?: string
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
  subtitle?: string | Record<string, string>
  slug: string
  content: string | Record<string, string>
  excerpt?: string | Record<string, string>
  cover_image?: string
  /** 公开作者卡片；后台需要完整账号资料时用 useAuthStore().user。 */
  author?: PublicUser
  category?: Category
  tags: Tag[]
  status: 'draft' | 'published' | 'archived' | 'scheduled'
  /** 仅 status=scheduled 时有值；库内为 UTC，编辑表单按 UTC 字面值回填。 */
  scheduled_at?: string
  views: number
  likes_count: number
  comments_count: number
  is_pinned: boolean
  allow_comments: boolean
  is_password_protected?: boolean
  visibility?: 'public' | 'password' | 'private'
  meta_title?: string | Record<string, string>
  meta_description?: string | Record<string, string>
  meta_keywords?: string | Record<string, string>
  created_at: string
  published_at?: string
  updated_at?: string
  reading_time: number
}

export interface PostCreate {
  title: string | Record<string, string>
  subtitle?: string | Record<string, string>
  slug?: string
  content: string | Record<string, string>
  excerpt?: string | Record<string, string>
  cover_image?: string
  // 后端 PostBase/PostUpdate 的 category_id 是 `int | None`：显式 null 表示"取消分类"，
  // 而省略该键在 exclude_unset 语义下等于"不动它"。类型必须允许 null，否则"无分类"
  // 这个操作在类型层面就写不出来。
  category_id?: number | null
  tag_ids?: number[]
  status?: 'draft' | 'published' | 'scheduled'
  visibility?: 'public' | 'password' | 'private'
  scheduled_at?: string
  password?: string
  is_pinned?: boolean
  allow_comments?: boolean
  meta_title?: string | Record<string, string>
  meta_description?: string | Record<string, string>
  meta_keywords?: string | Record<string, string>
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
  enable_music_player?: boolean
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
