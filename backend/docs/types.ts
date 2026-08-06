/**
 * Rosetta API TypeScript 类型定义
 * 
 * 供前端直接导入使用
 * 
 * 使用方法：
 * import type { Post, User, PaginatedResponse } from '@/types/api'
 */

// ==================== 基础类型 ====================

export interface BaseResponse {
  success: boolean
  message: string
}

export interface PaginatedResponse<T> {
  items: T[]
  total: number
  page: number
  page_size: number
  total_pages: number
}

export interface TokenResponse {
  access_token: string
  refresh_token: string
  token_type: string
  expires_in: number
}

export interface ErrorResponse {
  success: false
  message: string
  error_code: number | string
  errors?: Array<{
    field: string
    message: string
    type: string
  }>
  retry_after?: number
}

// ==================== 多语言类型 ====================

export type I18nString = Record<string, string>

export type LanguageCode = 'zh' | 'en' | 'ja' | 'zh_Hant'

// ==================== 用户相关类型 ====================

export interface UserTitle {
  id: number
  name: string
  color: string
  icon: string | null
  description: string | null
}

export interface User {
  id: number
  username: string
  email: string
  nickname: string | null
  avatar: string | null
  cover_image: string | null
  bio: string | null
  website: string | null
  github: string | null
  is_active: boolean
  is_staff: boolean
  is_superuser: boolean
  title: UserTitle | null
  created_at: string
  last_login: string | null
}

export interface UserPreference {
  public_profile: boolean
  theme: 'light' | 'dark' | 'system'
}

export interface UserCreate {
  username: string
  email: string
  password: string
  nickname?: string
  bio?: string
  website?: string
  github?: string
}

export interface UserUpdate {
  nickname?: string
  bio?: string
  website?: string
  github?: string
  avatar?: string
  cover_image?: string
}

export interface UserPreferenceUpdate {
  public_profile?: boolean
  theme?: string
}

export interface LoginRequest {
  username: string
  password: string
}

// ==================== 用户管理相关类型 ====================

export interface PasswordChange {
  current_password: string
  new_password: string
}

export interface PasswordReset {
  new_password: string
}

export interface AdminUserCreate {
  username: string
  email: string
  password: string
  nickname?: string
  bio?: string
  website?: string
  github?: string
  is_staff?: boolean
  is_active?: boolean
}

export interface AdminUserUpdate {
  username?: string
  email?: string
  nickname?: string
  bio?: string
  website?: string
  github?: string
  avatar?: string
  cover_image?: string
  is_staff?: boolean
  is_active?: boolean
  is_banned?: boolean
}

export interface UserDetail {
  id: number
  username: string
  email: string
  nickname: string | null
  avatar: string | null
  cover_image: string | null
  bio: string | null
  website: string | null
  github: string | null
  is_active: boolean
  is_staff: boolean
  is_superuser: boolean
  is_banned: boolean
  title: UserTitle | null
  created_at: string
  updated_at: string | null
  last_login: string | null
}

// ==================== 分类相关类型 ====================

export interface Category {
  id: number
  name: I18nString
  slug: string
  description: I18nString | null
  icon: string | null
  color: string
  cover_image: string | null
  created_at: string
  post_count: number
}

export interface CategoryLocalized {
  id: number
  name: string
  slug: string
  description: string | null
  icon: string | null
  color: string
  cover_image: string | null
  created_at: string
  post_count: number
}

export interface CategoryCreate {
  name: I18nString
  slug?: string
  description?: I18nString
  icon?: string
  color?: string
}

export interface CategoryUpdate {
  name?: I18nString
  slug?: string
  description?: I18nString
  icon?: string
  color?: string
  cover_image?: string
}

// ==================== 标签相关类型 ====================

export interface Tag {
  id: number
  name: I18nString
  slug: string
  color: string
  icon: string | null
  is_active: boolean
  created_at: string
  post_count: number
}

export interface TagLocalized {
  id: number
  name: string
  slug: string
  color: string
  icon: string | null
  is_active: boolean
  created_at: string
  post_count: number
}

export interface TagCreate {
  name: I18nString
  slug?: string
  color?: string
  icon?: string
  is_active?: boolean
}

export interface TagUpdate {
  name?: I18nString
  slug?: string
  color?: string
  icon?: string
  is_active?: boolean
}

// ==================== 文章相关类型 ====================

export interface PostAuthor {
  id: number
  username: string
  nickname: string | null
  avatar: string | null
  email: string
  bio: string | null
  website: string | null
  github: string | null
  cover_image: string | null
  is_active: boolean
  is_staff: boolean
  is_superuser: boolean
  title: UserTitle | null
  created_at: string
  last_login: string | null
}

export interface Post {
  id: number
  title: I18nString
  subtitle: I18nString | null
  slug: string
  source: string
  source_url: string | null
  audio: string | null
  video: string | null
  video_url: string | null
  content: I18nString
  excerpt: I18nString | null
  cover_image: string | null
  author: User
  category: Category | null
  tags: Tag[]
  status: 'draft' | 'published'
  views: number
  likes_count: number
  is_pinned: boolean
  allow_comments: boolean
  comments_count: number
  meta_title: I18nString | null
  meta_description: I18nString | null
  meta_keywords: I18nString | null
  created_at: string
  published_at: string | null
  updated_at: string
  reading_time: number
}

export interface PostLocalized {
  id: number
  title: string
  subtitle: string | null
  slug: string
  source: string
  source_url: string | null
  audio: string | null
  video: string | null
  video_url: string | null
  content: string
  excerpt: string | null
  cover_image: string | null
  author: PostAuthor
  category: CategoryLocalized | null
  tags: TagLocalized[]
  status: 'draft' | 'published'
  views: number
  likes_count: number
  is_pinned: boolean
  allow_comments: boolean
  comments_count: number
  is_password_protected: boolean
  meta_title: string | null
  meta_description: string | null
  meta_keywords: string | null
  created_at: string
  published_at: string | null
  updated_at: string
  reading_time: number
}

export interface PostListItem {
  id: number
  title: I18nString
  subtitle: I18nString | null
  slug: string
  excerpt: I18nString | null
  cover_image: string | null
  author: User
  category: Category | null
  tags: Tag[]
  status: string
  views: number
  likes_count: number
  is_pinned: boolean
  created_at: string
  published_at: string | null
  reading_time: number
}

export interface PostListItemLocalized {
  id: number
  title: string
  subtitle: string | null
  slug: string
  excerpt: string | null
  cover_image: string | null
  author: PostAuthor
  category: CategoryLocalized | null
  tags: TagLocalized[]
  status: string
  views: number
  likes_count: number
  comments_count: number
  is_pinned: boolean
  created_at: string
  published_at: string | null
  reading_time: number
}

export interface PostCreate {
  title: I18nString
  subtitle?: I18nString
  slug?: string
  source?: string
  source_url?: string
  content: I18nString
  excerpt?: I18nString
  cover_image?: string
  category_id?: number
  tag_ids?: number[]
  status?: 'draft' | 'published'
  password?: string
  is_pinned?: boolean
  allow_comments?: boolean
  meta_title?: I18nString
  meta_description?: I18nString
  meta_keywords?: I18nString
}

export interface PostUpdate {
  title?: I18nString
  subtitle?: I18nString
  slug?: string
  source?: string
  source_url?: string
  audio?: string
  video?: string
  video_url?: string
  content?: I18nString
  excerpt?: I18nString
  cover_image?: string
  category_id?: number
  tag_ids?: number[]
  status?: 'draft' | 'published'
  password?: string | null
  is_pinned?: boolean
  allow_comments?: boolean
  meta_title?: I18nString
  meta_description?: I18nString
  meta_keywords?: I18nString
}

// ==================== 归档相关类型 ====================

export interface ArchivePostItem {
  id: number
  title: string
  slug: string
  created_at: string
  category: {
    id: number
    name: string
    color: string
  } | null
  views: number
}

export interface ArchiveMonthGroup {
  year: number
  month: number
  count: number
  posts: ArchivePostItem[]
}

export interface ArchiveStats {
  total_posts: number
  total_years: number
  years: number[]
  year_stats: Record<number, number>
}

export interface ArchiveMonthResponse {
  year: number
  month: number
  count: number
  page: number
  page_size: number
  total_pages: number
  posts: ArchivePostItem[]
}

// ==================== 评论相关类型 ====================

export interface Comment {
  id: number
  post_id: number
  user: User
  parent_id: number | null
  content: string
  active: boolean
  created_at: string
  replies: Comment[]
}

export interface CommentCreate {
  content: string
  parent_id?: number
}

// ==================== 页面相关类型 ====================

export interface Page {
  id: number
  title: I18nString
  slug: string
  content: I18nString
  status: 'draft' | 'published'
  created_at: string
  updated_at: string
}

export interface PageCreate {
  title: I18nString
  slug: string
  content: I18nString
  status?: 'draft' | 'published'
}

export interface PageUpdate {
  title?: I18nString
  slug?: string
  content?: I18nString
  status?: 'draft' | 'published'
}

// ==================== 导航相关类型 ====================

export interface Navigation {
  id: number
  title: I18nString
  url: string
  location: 'header' | 'footer' | 'sidebar'
  order: number
  is_active: boolean
  target_blank: boolean
  created_at: string
}

export interface NavigationCreate {
  title: I18nString
  url: string
  location?: 'header' | 'footer' | 'sidebar'
  order?: number
  is_active?: boolean
  target_blank?: boolean
}

// ==================== 友链相关类型 ====================

export interface FriendLink {
  id: number
  name: I18nString
  url: string
  description: I18nString | null
  logo: string | null
  order: number
  is_active: boolean
  target_blank: boolean
  created_at: string
}

export interface FriendLinkCreate {
  name: I18nString | string
  url: string
  description?: I18nString | string
  logo?: string
  order?: number
  is_active?: boolean
  target_blank?: boolean
}

export interface FriendLinkUpdate {
  name?: I18nString | string
  url?: string
  description?: I18nString | string
  logo?: string
  order?: number
  is_active?: boolean
  target_blank?: boolean
}

// ==================== 站点配置相关类型 ====================

export interface SiteConfig {
  // 基础信息
  site_name: string
  site_description: string
  site_keywords: string
  site_author: string
  site_email: string
  site_logo: string | null
  site_favicon: string | null
  site_icon: string | null
  // 页脚设置
  footer_text: string | null
  footer_slogan: string | null
  copyright_text: string | null
  icp_number: string | null
  police_icp_number: string | null
  // 社交媒体链接
  github_url: string | null
  x_url: string | null
  bilibili_url: string | null
  weibo_url: string | null
  zhihu_url: string | null
  youtube_url: string | null
  linkedin_url: string | null
  telegram_url: string | null
  // 联系方式
  contact_email: string | null
  contact_qq: string | null
  contact_wechat: string | null
  // 功能开关
  enable_comments: boolean
  enable_registration: boolean
  enable_rss_feed: boolean
  enable_search: boolean
  enable_sitemap: boolean
  enable_guestbook: boolean
  enable_dark_mode: boolean
  enable_reading_time: boolean
  enable_word_count: boolean
  enable_like_button: boolean
  enable_share_buttons: boolean
  enable_toc: boolean
  // 分页设置
  pagination_page_size: number
  pagination_max_page_size: number
  // 外观设置
  code_theme: string
  code_theme_dark: string
  default_theme: string
  primary_color: string
  font_family: string | null
  // 维护模式
  maintenance_mode: boolean
  maintenance_message: string | null
  maintenance_end_time: string | null
  // 默认图片
  default_post_cover: string | null
  default_avatar: string | null
  default_category_cover: string | null
  // SEO 设置
  google_analytics_id: string | null
  baidu_analytics_id: string | null
  google_site_verification: string | null
  baidu_site_verification: string | null
  robots_txt: string | null
  // 安全设置
  require_email_verification: boolean
  allow_password_reset: boolean
  session_timeout: number
  max_login_attempts: number
  login_lockout_duration: number
  // 邮件设置
  email_configured: boolean
  email_from: string | null
  email_from_name: string | null
  // 文件上传设置
  max_upload_size: number
  allowed_image_types: string
  allowed_file_types: string
  // 评论设置
  comment_require_approval: boolean
  comment_allow_guest: boolean
  comment_max_length: number
  comment_antispam: boolean
  // 自定义代码
  custom_header_code: string | null
  custom_footer_code: string | null
  custom_css: string | null
  custom_js: string | null
}

export interface SiteConfigUpdate {
  // 基础信息
  site_name?: string
  site_description?: string
  site_keywords?: string
  site_author?: string
  site_email?: string
  site_logo?: string
  site_favicon?: string
  site_icon?: string
  // 页脚设置
  footer_text?: string
  footer_slogan?: string
  copyright_text?: string
  icp_number?: string
  police_icp_number?: string
  // 社交媒体链接
  github_url?: string
  x_url?: string
  bilibili_url?: string
  weibo_url?: string
  zhihu_url?: string
  youtube_url?: string
  linkedin_url?: string
  telegram_url?: string
  // 联系方式
  contact_email?: string
  contact_qq?: string
  contact_wechat?: string
  // 功能开关
  enable_comments?: boolean
  enable_registration?: boolean
  enable_rss_feed?: boolean
  enable_search?: boolean
  enable_sitemap?: boolean
  enable_guestbook?: boolean
  enable_dark_mode?: boolean
  enable_reading_time?: boolean
  enable_word_count?: boolean
  enable_like_button?: boolean
  enable_share_buttons?: boolean
  enable_toc?: boolean
  // 分页设置
  pagination_page_size?: number
  pagination_max_page_size?: number
  // 外观设置
  code_theme?: string
  code_theme_dark?: string
  default_theme?: string
  primary_color?: string
  font_family?: string
  // 维护模式
  maintenance_mode?: boolean
  maintenance_message?: string
  maintenance_end_time?: string
  // 默认图片
  default_post_cover?: string
  default_avatar?: string
  default_category_cover?: string
  // SEO 设置
  google_analytics_id?: string
  baidu_analytics_id?: string
  google_site_verification?: string
  baidu_site_verification?: string
  robots_txt?: string
  // 安全设置
  require_email_verification?: boolean
  allow_password_reset?: boolean
  session_timeout?: number
  max_login_attempts?: number
  login_lockout_duration?: number
  // 文件上传设置
  max_upload_size?: number
  allowed_image_types?: string
  allowed_file_types?: string
  // 评论设置
  comment_require_approval?: boolean
  comment_allow_guest?: boolean
  comment_max_length?: number
  comment_antispam?: boolean
  // 自定义代码
  custom_header_code?: string
  custom_footer_code?: string
  custom_css?: string
  custom_js?: string
}

export interface SiteSettingItem {
  key: string
  label: string
  description?: string
  type: 'text' | 'textarea' | 'switch' | 'select' | 'number' | 'color' | 'image' | 'url' | 'email' | 'datetime'
  value: string | number | boolean | null
  default?: string | number | boolean | null
  options?: Array<{ value: string; label: string }>
  placeholder?: string
  required?: boolean
  min_value?: number
  max_value?: number
  pattern?: string
}

export interface SiteSettingGroup {
  name: string
  label: string
  description?: string
  icon?: string
  settings: SiteSettingItem[]
}

export interface SiteConfigFullResponse {
  groups: SiteSettingGroup[]
  last_updated?: string
}

// ==================== 媒体相关类型 ====================

export interface ImageUploadResponse {
  url: string
  filename: string
  width: number
  height: number
  size: number
}

export interface ImageResponse {
  url: string
  filename: string
  width: number
  height: number
}

// ==================== 翻译相关类型 ====================

export interface TranslateRequest {
  text: string
  source_lang?: string
  target_langs?: string[]
}

export interface TranslateResponse {
  translations: Record<string, string>
}

// ==================== 后台管理相关类型 ====================

export interface AdminStats {
  posts: number
  views: number
  comments: number
  users: number
}

export interface ViewTrend {
  date: string
  views: number
}

export interface CategoryStat {
  name: string
  count: number
}

export interface AdminUserUpdate {
  is_staff?: boolean
  is_active?: boolean
  is_banned?: boolean
}

// ==================== 健康检查相关类型 ====================

export interface HealthCheckResponse {
  status: 'healthy' | 'unhealthy'
  app_name: string
  version: string
  environment: string
  database: 'connected' | 'disconnected'
}

// ==================== API 查询参数类型 ====================

export interface PaginationParams {
  page?: number
  page_size?: number
}

export interface PostListParams extends PaginationParams {
  category?: string
  tag?: string
  search?: string
  status?: string
  lang?: LanguageCode
}

export interface UserListParams extends PaginationParams {
  search?: string
}

export interface NavigationListParams {
  location?: 'header' | 'footer' | 'sidebar'
}

export interface FriendLinkListParams {
  all?: boolean
}

export interface TranslateParams {
  lang?: LanguageCode
}
