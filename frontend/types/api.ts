// API Response Types
export interface BaseResponse {
  success: boolean
  message: string
  data?: any
}

export interface PaginatedResponse<T = any> {
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

export interface UserTitle {
  id: number
  name: string
  color: string
  icon?: string
}

export interface UserPreference {
  id: number
  user_id: number
  public_profile: boolean
  show_email: boolean
  show_posts: boolean
  show_comments: boolean
  show_stats: boolean
  notification_comment: boolean
  notification_like: boolean
  notification_follow: boolean
  theme: string
  language: string
  posts_per_page: number
}

// Auth Types
export interface LoginRequest {
  username: string
  password: string
}

export interface RegisterRequest {
  username: string
  email: string
  password: string
  nickname?: string
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
  author?: User
  category?: Category
  tags: Tag[]
  status: 'draft' | 'published' | 'archived' | 'scheduled'
  views: number
  likes_count: number
  comments_count: number
  is_pinned: boolean
  allow_comments: boolean
  is_password_protected?: boolean
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
  category_id?: number
  tag_ids?: number[]
  status?: 'draft' | 'published' | 'archived' | 'scheduled'
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

export interface CommentCreate {
  content: string
  parent_id?: number
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

// Site Config Types
export interface SiteConfig {
  site_name: string
  site_description: string
  site_keywords: string
  site_author: string
  site_email: string
  site_logo?: string
  site_favicon?: string
  site_icon?: string
  footer_text?: string
  enable_comments: boolean
  enable_registration: boolean
  enable_rss_feed: boolean
  pagination_page_size: number
  code_theme: string
  music_enabled: boolean
  music_show_in_navbar: boolean
  music_show_in_sidebar: boolean
  music_mode: string
  music_volume: number
  music_meting_api?: string
  music_meting_server?: string
  music_meting_type?: string
  music_meting_id?: string
  wallpaper_mode: string
  wallpaper_player_enable: boolean
  wallpaper_desktop?: string
  wallpaper_mobile?: string
  wallpaper_video?: string
  wallpaper_use_bing: boolean
  wallpaper_bing_days: number
  wallpaper_dim_opacity: number
  wallpaper_home_title?: string
  wallpaper_home_subtitle?: string
  author_name?: string
  author_bio?: string
  author_avatar?: string
  author_links_json?: string
  // Sidebar settings
  sidebar_show_profile: boolean
  sidebar_show_categories: boolean
  sidebar_show_tags: boolean
  sidebar_show_recent_posts: boolean
  sidebar_show_music: boolean
  sidebar_show_statistics: boolean
  sidebar_widget_order: string[]
}

// OOBE Types
export interface OOBEStatus {
  oobe_complete: boolean
  has_config: boolean
  state?: any
  config?: any
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

// Archive Types
export interface ArchiveMonth {
  year: number
  month: number
  count: number
  posts: ArchivePost[]
}

export interface ArchivePost {
  id: number
  title: string
  slug: string
  created_at: string
  category?: {
    id: number
    name: string
    color: string
  }
  views: number
}

// Stats Types
export interface SiteStats {
  total_words: number
  total_posts: number
  total_categories: number
  total_tags: number
}

// Guestbook Types
export interface GuestbookEntry {
  id: number
  user?: User
  nickname?: string
  email?: string
  website?: string
  content: string
  parent_id?: number
  replies?: GuestbookEntry[]
  likes_count: number
  is_pinned: boolean
  is_featured: boolean
  is_approved: boolean
  is_spam: boolean
  ip?: string
  user_agent?: string
  created_at: string
  updated_at?: string
}

// Gallery Types
export interface GalleryItem {
  id: number
  gallery_id: number
  title?: string
  description?: string
  url: string
  thumbnail?: string
  mime_type?: string
  size?: number
  width?: number
  height?: number
  order: number
  is_active: boolean
  created_at: string
  updated_at?: string
}

export interface Gallery {
  id: number
  title: string | Record<string, string>
  slug: string
  description?: string | Record<string, string>
  cover_image?: string
  author?: User
  items_count: number
  views: number
  is_public: boolean
  is_active: boolean
  items?: GalleryItem[]
  created_at: string
  updated_at?: string
  published_at?: string
}

// Activity Types
export interface Activity {
  id: number
  user?: User
  type: 'post' | 'comment' | 'like' | 'follow' | 'custom'
  content?: string
  target_type?: string
  target_id?: number
  target_title?: string
  target_url?: string
  metadata?: Record<string, any>
  likes_count: number
  comments_count: number
  is_public: boolean
  created_at: string
  updated_at?: string
}

// Admin Stats Types
export interface AdminStats {
  total_posts: number
  total_comments: number
  total_users: number
  total_views: number
  today_posts: number
  today_comments: number
  today_users: number
  today_views: number
  pending_comments: number
  pending_guestbook: number
}

export interface ViewTrend {
  date: string
  count: number
}

export interface CategoryStat {
  id: number
  name: string
  slug: string
  color?: string
  post_count: number
  view_count?: number
  percentage?: number
}

// Sponsor Types
export interface Sponsor {
  id: number
  name: string
  avatar?: string
  message?: string
  amount: number
  currency: string
  method?: string
  is_anonymous: boolean
  is_public: boolean
  created_at: string
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
  metadata?: Record<string, any>
  is_active: boolean
  created_at: string
  updated_at?: string
}

// Notification Types
export interface Notification {
  id: number
  user: User
  type: 'comment' | 'like' | 'follow' | 'system' | 'mention'
  title: string
  content?: string
  target_type?: string
  target_id?: number
  target_url?: string
  sender?: User
  metadata?: Record<string, any>
  is_read: boolean
  created_at: string
  read_at?: string
}

// Page Setting Types
export interface PageSetting {
  id: number
  key: string
  value: any
  type: 'string' | 'number' | 'boolean' | 'json'
  group: string
  description?: string
  updated_at: string
}

// Announcement Types
export interface Announcement {
  id: number
  title: string | Record<string, string>
  content: string | Record<string, string>
  type: 'info' | 'warning' | 'success' | 'danger'
  level: 'normal' | 'important' | 'urgent'
  is_active: boolean
  is_pinned: boolean
  start_at?: string
  end_at?: string
  show_location: 'all' | 'home' | 'admin' | 'posts'
  author?: User
  views: number
  created_at: string
  updated_at?: string
}

// Hero Carousel Types
export interface HeroCarouselItem {
  id: number
  title?: string | Record<string, string>
  subtitle?: string | Record<string, string>
  description?: string | Record<string, string>
  image: string
  mobile_image?: string
  link_url?: string
  link_text?: string | Record<string, string>
  target_blank: boolean
  order: number
  is_active: boolean
  start_at?: string
  end_at?: string
  button_style?: string
  overlay_opacity?: number
  text_color?: string
  created_at: string
  updated_at?: string
}

// Post Series Types
export interface PostSeries {
  id: number
  title: string | Record<string, string>
  slug: string
  description?: string | Record<string, string>
  cover_image?: string
  author?: User
  posts_count: number
  views: number
  is_active: boolean
  posts?: Post[]
  created_at: string
  updated_at?: string
  published_at?: string
}

// Ranking Types
export interface RankingItem {
  id: number
  rank: number
  title: string
  slug: string
  category?: Category
  cover_image?: string
  views: number
  likes_count: number
  comments_count: number
  score: number
  trend: 'up' | 'down' | 'same' | 'new'
  trend_change?: number
  period: 'daily' | 'weekly' | 'monthly' | 'all'
  type: 'post' | 'comment' | 'user' | 'tag' | 'category'
  created_at?: string
}

// Admin User Types
export interface AdminUserListParams {
  page?: number
  pageSize?: number
  page_size?: number
  search?: string
  role?: string
  isActive?: boolean
  is_active?: boolean
}

export interface AdminUserCreate {
  username: string
  email: string
  password: string
  nickname?: string
  is_staff?: boolean
  is_superuser?: boolean
  is_active?: boolean
}

export interface AdminUserUpdate {
  username?: string
  email?: string
  nickname?: string
  bio?: string
  website?: string
  github?: string
  qq?: string
  avatar?: string
  cover_image?: string
  is_staff?: boolean
  is_superuser?: boolean
  is_active?: boolean
}

export interface ResetPasswordRequest {
  new_password: string
}

// Admin Comment Types
export interface AdminCommentListParams {
  page?: number
  pageSize?: number
  page_size?: number
  status?: 'all' | 'active' | 'pending' | 'spam' | 'rejected'
}

export interface CommentBatchAction {
  ids: number[]
  action: 'approve' | 'reject' | 'spam' | 'delete'
}

// Admin Tools Types
export interface MockDataConfig {
  users?: number
  posts?: number
  comments?: number
  categories?: number
  tags?: number
}

export interface UnusedImage {
  id: number
  url: string
  path: string
  size: number
  created_at: string
}

// Backup Types
export interface BackupInfo {
  last_backup_at?: string
  backup_count: number
  total_size: number
  backups: BackupItem[]
}

export interface BackupItem {
  id: string
  name: string
  size: number
  created_at: string
  type: 'full' | 'partial'
}

export interface RestoreRequest {
  backup_id: string
  confirm?: boolean
}

// Media Library Params Types
export interface MediaLibraryParams {
  page?: number
  pageSize?: number
  page_size?: number
  search?: string
  category?: string
  type?: 'image' | 'video' | 'audio' | 'file'
}

export interface MediaUpdate {
  name?: string
  category?: string
}

export interface MediaStats {
  total: number
  images: number
  videos: number
  audios: number
  files: number
  total_size: number
}

export interface BingWallpaperItem {
  url: string
  title: string
  copyright: string
  date: string
  hsh: string
}

export interface MediaAvatarOptions {
  username?: string
  email?: string
  size?: number
  default?: string
}
