/**
 * Rosetta API Schema Contract
 *
 * 与 backend/schemas/__init__.py 一一对应，修改后请同步更新。
 *
 * 命名约定：
 *   后端 class UserResponse(BaseModel)  →  前端 export interface UserResponse {}
 *
 * 类型约定：
 *   int               -> number
 *   float             -> number
 *   str               -> string
 *   bool              -> boolean
 *   datetime/DateTime -> string (ISO 8601)
 *   UUID              -> string
 *   EmailStr          -> string
 *   dict[str, Any]    -> Record<string, any>
 *   list[X]           -> X[]
 *   Optional[X]       -> X | null
 *   Enum 字面量       -> 'val1' | 'val2' 联合类型
 */

// ===== 通用工具类型 =====
export type I18nString = Record<string, string>;
export type LanguageCode = "zh" | "en" | "ja" | "zh_Hant" | string;
export type NeverGuard = (v: never) => never;
export const _assert_never: NeverGuard = (v) => v;

// ===== 基础响应模型 =====
export interface BaseResponse {
	success: boolean;
	message: string;
}

export interface PaginatedResponse<T> {
	items: T[];
	total: number;
	page: number;
	page_size: number;
	total_pages: number;
}

export interface TokenResponse {
	access_token: string;
	refresh_token: string;
	token_type: string;
	expires_in: number;
}

export interface LoginRequest {
	username: string;
	password: string;
}

export interface RegisterRequest {
	username: string;
	email: string;
	password: string;
	nickname?: string | null;
}

export interface LoginResponse extends TokenResponse {
	user: UserResponse;
}

// ===== 枚举类型 =====
export type PostStatus = "draft" | "published" | "scheduled";
export type PageStatus = "draft" | "published";
export type CommentStatus = "approved" | "pending" | "rejected" | "spam";
export type CommentBatchAction =
	| "approve"
	| "reject"
	| "spam"
	| "restore"
	| "delete";
export type GuestbookBatchAction =
	| "approve"
	| "reject"
	| "spam"
	| "pin"
	| "feature"
	| "trash"
	| "restore"
	| "delete";
export type NavigationLocation = "header" | "footer" | "sidebar";
export type NotificationLevel = "info" | "success" | "warning" | "error";
export type Visibility = "public" | "private" | "friends";
export type PollType = "single" | "multiple";

// ===== 用户相关模型 =====
export interface UserTitleResponse {
	id: number;
	name: string;
	color: string;
	icon: string | null;
	description: string | null;
}

export interface UserBase {
	username: string;
	email: string;
	nickname: string | null;
	bio: string | null;
	website: string | null;
	github: string | null;
}

export interface UserCreate extends UserBase {
	password: string;
}

export interface UserUpdate {
	nickname?: string | null;
	bio?: string | null;
	website?: string | null;
	github?: string | null;
	avatar?: string | null;
	cover_image?: string | null;
}

export interface AdminUserUpdate {
	is_staff?: boolean | null;
	is_banned?: boolean | null;
}

export interface UserResponse extends UserBase {
	id: number;
	avatar: string | null;
	cover_image: string | null;
	is_active: boolean;
	is_staff: boolean;
	is_superuser: boolean;
	title: UserTitleResponse | null;
	created_at: string;
	last_login: string | null;
}

export interface UserPreferenceResponse {
	public_profile: boolean;
	show_email: boolean;
	show_posts: boolean;
	show_comments: boolean;
	show_stats: boolean;
	theme: string;
}

export interface UserPreferenceUpdate {
	public_profile?: boolean | null;
	show_email?: boolean | null;
	show_posts?: boolean | null;
	show_comments?: boolean | null;
	show_stats?: boolean | null;
	theme?: string | null;
}

export interface PasswordChange {
	current_password: string;
	new_password: string;
}

export interface PasswordReset {
	new_password: string;
}

export interface AdminUserCreate {
	username: string;
	email: string;
	password: string;
	nickname?: string | null;
	bio?: string | null;
	website?: string | null;
	github?: string | null;
	is_staff?: boolean;
	is_active?: boolean;
}

export interface AdminUserUpdateFull {
	username?: string | null;
	email?: string | null;
	nickname?: string | null;
	bio?: string | null;
	website?: string | null;
	github?: string | null;
	qq?: string | null;
	avatar_source?:
		| "auto"
		| "custom"
		| "github"
		| "qq"
		| "gravatar"
		| "letter"
		| null;
	avatar?: string | null;
	cover_image?: string | null;
	is_staff?: boolean | null;
	is_active?: boolean | null;
	is_superuser?: boolean | null;
	is_banned?: boolean | null;
}

export interface UserDetailResponse extends UserResponse {
	bio: string | null;
	website: string | null;
	github: string | null;
	qq: string | null;
	avatar_source:
		| "auto"
		| "custom"
		| "github"
		| "qq"
		| "gravatar"
		| "letter"
		| null;
	resolved_avatar_url: string | null;
	posts_count: number;
	comments_count: number;
	is_banned: boolean;
	updated_at: string | null;
}

// ===== 后台：用户列表查询参数 =====
export interface AdminUserListParams {
	page?: number;
	page_size?: number;
	search?: string;
	is_staff?: boolean;
	is_active?: boolean;
	is_banned?: boolean;
	role?: "superuser" | "staff" | "subscriber";
}

// ===== 分类相关模型 =====
export interface CategoryBase {
	name: I18nString;
	slug?: string | null;
	description?: I18nString | null;
	icon?: string | null;
	color?: string;
}

export type CategoryCreate = CategoryBase;

export interface CategoryUpdate {
	name?: I18nString | null;
	slug?: string | null;
	description?: I18nString | null;
	icon?: string | null;
	color?: string | null;
	cover_image?: string | null;
}

export interface CategoryResponse {
	id: number;
	name: I18nString;
	slug: string;
	description: I18nString | null;
	icon: string | null;
	color: string;
	cover_image: string | null;
	created_at: string;
	post_count: number;
}

export interface CategoryLocalizedResponse {
	id: number;
	name: string;
	slug: string;
	description: string | null;
	icon: string | null;
	color: string;
	cover_image: string | null;
	created_at: string;
	post_count: number;
}

// ===== 标签相关模型 =====
export interface TagBase {
	name: I18nString;
	slug?: string | null;
	color?: string;
	icon?: string | null;
	is_active?: boolean;
}

export type TagCreate = TagBase;

export interface TagUpdate {
	name?: I18nString | null;
	slug?: string | null;
	color?: string | null;
	icon?: string | null;
	is_active?: boolean | null;
}

export interface TagResponse {
	id: number;
	name: I18nString;
	slug: string;
	color: string;
	icon: string | null;
	is_active: boolean;
	created_at: string;
	post_count: number;
}

export interface TagLocalizedResponse {
	id: number;
	name: string;
	slug: string;
	color: string;
	icon: string | null;
	is_active: boolean;
	created_at: string;
	post_count: number;
}

// ===== 文章相关模型 =====
export interface PostBase {
	title: I18nString;
	subtitle?: I18nString | null;
	slug?: string | null;
	source?: string;
	source_url?: string | null;
	content: I18nString;
	excerpt?: I18nString | null;
	cover_image?: string | null;
	category_id?: number | null;
	tag_ids?: number[];
	series_id?: number | null;
	series_order?: number;
	status?: PostStatus;
	scheduled_at?: string | null;
	password?: string | null;
	view_password?: string | null;
	encryption_enabled?: boolean;
	encryption_salt?: string | null;
	encryption_verifier?: string | null;
	encryption_algorithm?: string;
	encryption_hint?: string | null;
	is_pinned?: boolean;
	allow_comments?: boolean;
	meta_title?: I18nString | null;
	meta_description?: I18nString | null;
	meta_keywords?: I18nString | null;
}

export type PostCreate = PostBase;

export interface PostUpdate {
	title?: I18nString | null;
	subtitle?: I18nString | null;
	slug?: string | null;
	source?: string | null;
	source_url?: string | null;
	audio?: string | null;
	video?: string | null;
	video_url?: string | null;
	content?: I18nString | null;
	excerpt?: I18nString | null;
	cover_image?: string | null;
	category_id?: number | null;
	tag_ids?: number[] | null;
	series_id?: number | null;
	series_order?: number | null;
	status?: PostStatus | null;
	scheduled_at?: string | null;
	password?: string | null;
	view_password?: string | null;
	encryption_enabled?: boolean | null;
	encryption_salt?: string | null;
	encryption_verifier?: string | null;
	encryption_algorithm?: string | null;
	encryption_hint?: string | null;
	is_pinned?: boolean | null;
	allow_comments?: boolean | null;
	meta_title?: I18nString | null;
	meta_description?: I18nString | null;
	meta_keywords?: I18nString | null;
}

export interface PostResponse {
	id: number;
	title: I18nString;
	subtitle: I18nString | null;
	slug: string;
	source: string;
	source_url: string | null;
	audio: string | null;
	video: string | null;
	video_url: string | null;
	content: I18nString;
	excerpt: I18nString | null;
	cover_image: string | null;
	author: UserResponse;
	category: CategoryResponse | null;
	tags: TagResponse[];
	status: PostStatus;
	views: number;
	likes_count: number;
	is_pinned: boolean;
	allow_comments: boolean;
	comments_count: number;
	meta_title: I18nString | null;
	meta_description: I18nString | null;
	meta_keywords: I18nString | null;
	created_at: string;
	published_at: string | null;
	updated_at: string;
	reading_time: number;
}

export interface PostEditResponse {
	id: number;
	title: I18nString;
	subtitle: I18nString | null;
	slug: string;
	source: string;
	source_url: string | null;
	audio: string | null;
	video: string | null;
	video_url: string | null;
	content: I18nString;
	excerpt: I18nString | null;
	cover_image: string | null;
	status: PostStatus;
	visibility: Visibility;
	password: string | null;
	published_at: string | null;
	category: Record<string, any> | null;
	tags: Record<string, any>[];
	is_pinned: boolean;
	allow_comments: boolean;
	meta_description: I18nString | null;
	meta_title: I18nString | null;
	meta_keywords: I18nString | null;
	created_at: string;
	updated_at: string;
}

export interface PostLocalizedResponse {
	id: number;
	title: string;
	subtitle: string | null;
	slug: string;
	source: string;
	source_url: string | null;
	audio: string | null;
	video: string | null;
	video_url: string | null;
	content: string;
	excerpt: string | null;
	cover_image: string | null;
	author: UserResponse;
	category: CategoryLocalizedResponse | null;
	tags: TagLocalizedResponse[];
	status: PostStatus;
	visibility: Visibility;
	password: string | null;
	views: number;
	likes_count: number;
	is_pinned: boolean;
	allow_comments: boolean;
	comments_count: number;
	is_password_protected: boolean;
	meta_title: string | null;
	meta_description: string | null;
	meta_keywords: string | null;
	created_at: string;
	published_at: string | null;
	updated_at: string;
	reading_time: number;
}

export interface PostListItem {
	id: number;
	title: I18nString;
	subtitle: I18nString | null;
	slug: string;
	excerpt: I18nString | null;
	cover_image: string | null;
	author: UserResponse;
	category: CategoryResponse | null;
	tags: TagResponse[];
	status: PostStatus;
	views: number;
	likes_count: number;
	is_pinned: boolean;
	created_at: string;
	published_at: string | null;
	reading_time: number;
}

export interface PostListItemLocalized {
	id: number;
	title: string;
	subtitle: string | null;
	slug: string;
	excerpt: string | null;
	cover_image: string | null;
	author: UserResponse;
	category: CategoryLocalizedResponse | null;
	tags: TagLocalizedResponse[];
	status: PostStatus;
	views: number;
	likes_count: number;
	comments_count: number;
	is_pinned: boolean;
	created_at: string;
	published_at: string | null;
	reading_time: number;
}

// ===== 归档相关模型 =====
export interface ArchivePostItem {
	id: number;
	title: string;
	slug: string;
	created_at: string;
	category: CategoryLocalizedResponse | null;
	views: number;
}

export interface ArchiveMonthGroup {
	year: number;
	month: number;
	count: number;
	posts: ArchivePostItem[];
}

export interface ArchiveYearGroup {
	year: number;
	count: number;
	months: ArchiveMonthGroup[];
}

// ===== 评论相关模型 =====
export interface CommentBase {
	content: string;
	parent_id?: number | null;
	author_name?: string | null;
	author_email?: string | null;
	author_website?: string | null;
	hcaptcha_token?: string | null;
	qq?: string;
	github?: string;
	author_avatar_source?: "auto" | "custom" | "github" | "qq" | "gravatar";
}

export type CommentCreate = CommentBase;

export interface CommentResponse {
	id: number;
	post_id: number;
	user_id: number | null;
	parent_id: number | null;
	author_name: string;
	author_avatar: string;
	author_website: string | null;
	content: string;
	status: CommentStatus;
	is_pinned: boolean;
	likes_count: number;
	reply_total: number;
	created_at: string;
	replies: CommentResponse[];
	qq?: string | null;
	github?: string | null;
	avatar_source?: "auto" | "custom" | "github" | "qq" | "gravatar";
	resolved_avatar_url?: string | null;

	// ===== 评论管理视图扩展（后端 /admin/comments 列表独有）=====
	post_ref?: { id: number; slug?: string | null; title?: string | null } | null;
	parent_ref?: { id: number; nickname?: string | null } | null;
	user_ref?: {
		id: number;
		username: string;
		nickname: string | null;
		avatar: string | null;
	} | null;
}

export interface CommentPagedResponse {
	items: CommentResponse[];
	total: number;
	page: number;
	page_size: number;
	total_pages: number;
}

export type CommentAdminStatus =
	| "pending"
	| "approved"
	| "rejected"
	| "spam"
	| "all";

export interface AdminCommentListParams {
	page?: number;
	page_size?: number;
	status?: CommentAdminStatus;
	keyword?: string;
	post_id?: number;
}

// ===== 页面相关模型 =====
export interface PageBase {
	title: I18nString;
	slug: string;
	content: I18nString;
	status?: PageStatus;
}

export type PageCreate = PageBase;

export interface PageUpdate {
	title?: I18nString | null;
	slug?: string | null;
	content?: I18nString | null;
	status?: PageStatus | null;
}

export interface PageResponse {
	id: number;
	title: I18nString;
	slug: string;
	content: I18nString;
	status: PageStatus;
	created_at: string;
	updated_at: string;
}

export interface PageLocalizedResponse {
	id: number;
	title: string;
	slug: string;
	content: string;
	status: PageStatus;
	created_at: string;
	updated_at: string;
}

// ===== 导航相关模型 =====
export interface NavigationBase {
	title: I18nString;
	url: string;
	icon?: string | null;
	parent_id?: number | null;
	location?: NavigationLocation;
	order?: number;
	is_active?: boolean;
	target_blank?: boolean;
}

export type NavigationCreate = NavigationBase;

export interface NavigationUpdate {
	title?: I18nString | null;
	url?: string | null;
	icon?: string | null;
	parent_id?: number | null;
	location?: NavigationLocation | null;
	order?: number | null;
	is_active?: boolean | null;
	target_blank?: boolean | null;
}

export interface NavigationResponse {
	id: number;
	title: I18nString;
	url: string;
	icon: string | null;
	parent_id: number | null;
	location: NavigationLocation;
	order: number;
	is_active: boolean;
	target_blank: boolean;
	created_at: string;
}

export interface NavigationLocalizedResponse {
	id: number;
	title: string;
	url: string;
	location: NavigationLocation;
	order: number;
	is_active: boolean;
	target_blank: boolean;
	created_at: string;
}

export interface NavigationTreeNode extends NavigationResponse {
	children: NavigationTreeNode[];
}

// ===== 友情链接相关模型 =====
export interface FriendLinkBase {
	name: I18nString | string;
	url: string;
	description?: I18nString | string | null;
	logo?: string | null;
	order?: number;
	is_active?: boolean;
	target_blank?: boolean;
}

export type FriendLinkCreate = FriendLinkBase;

export interface FriendLinkUpdate {
	name?: I18nString | string | null;
	url?: string | null;
	description?: I18nString | string | null;
	logo?: string | null;
	order?: number | null;
	is_active?: boolean | null;
	target_blank?: boolean | null;
}

export interface FriendLinkResponse {
	id: number;
	name: I18nString;
	url: string;
	description: I18nString | null;
	logo: string | null;
	order: number;
	is_active: boolean;
	target_blank: boolean;
	created_at: string;
}

export interface FriendLinkLocalizedResponse {
	id: number;
	name: string;
	url: string;
	description: string | null;
	logo: string | null;
	order: number;
	is_active: boolean;
	target_blank: boolean;
	created_at: string;
}

// ===== 通知相关模型 =====
export interface NotificationResponse {
	id: number;
	title: I18nString;
	message: I18nString;
	level: NotificationLevel;
	link: string | null;
	is_read: boolean;
	created_at: string;
}

export interface NotificationLocalizedResponse {
	id: number;
	title: string;
	message: string;
	level: NotificationLevel;
	link: string | null;
	is_read: boolean;
	created_at: string;
}

// ===== 留言板相关模型 =====
export interface GuestbookEntryBase {
	content: string;
	author_name?: string | null;
	author_email?: string | null;
	author_website?: string | null;
	qq?: string;
	github?: string;
	author_avatar_source?: "auto" | "custom" | "github" | "qq" | "gravatar";
}

export type GuestbookEntryCreate = GuestbookEntryBase;

export interface GuestbookEntryResponse {
	id: number;
	user_id: number | null;
	author_name: string;
	author_avatar: string;
	author_website: string | null;
	content: string;
	status: CommentStatus;
	is_pinned: boolean;
	is_featured: boolean;
	likes_count: number;
	created_at: string;
	qq?: string | null;
	github?: string | null;
	avatar_source?: "auto" | "custom" | "github" | "qq" | "gravatar";
	resolved_avatar_url?: string | null;
}

export interface GuestbookEntryPagedResponse {
	items: GuestbookEntryResponse[];
	total: number;
	page: number;
	page_size: number;
	total_pages: number;
}

export interface GuestbookBatchActionRequest {
	ids: number[];
	action: GuestbookBatchAction;
}

// ===== 站点配置相关模型 =====
export interface StatsResponse {
	total_posts: number;
	total_pages: number;
	total_comments: number;
	total_guestbook: number;
	total_users: number;
	total_views: number;
	total_likes: number;
	total_categories: number;
	total_tags: number;
	total_dynamics: number;
	today_views: number;
	today_posts: number;
	today_comments: number;
	today_users: number;
}

export interface SiteConfigResponse {
	site_name: string;
	site_description: string;
	site_keywords: string;
	site_author: string;
	site_email: string;
	site_logo: string | null;
	site_favicon: string | null;
	site_icon: string | null;

	footer_text: string | null;
	footer_slogan: string | null;
	copyright_text: string | null;
	icp_number: string | null;
	police_icp_number: string | null;

	github_url: string | null;
	x_url: string | null;
	bilibili_url: string | null;
	weibo_url: string | null;
	zhihu_url: string | null;
	youtube_url: string | null;
	linkedin_url: string | null;
	telegram_url: string | null;

	contact_email: string | null;
	contact_qq: string | null;
	contact_wechat: string | null;

	enable_comments: boolean;
	enable_registration: boolean;
	enable_rss_feed: boolean;
	enable_search: boolean;
	enable_sitemap: boolean;
	enable_guestbook: boolean;
	enable_dark_mode: boolean;
	enable_reading_time: boolean;
	enable_word_count: boolean;
	enable_like_button: boolean;
	enable_share_buttons: boolean;
	enable_toc: boolean;

	pagination_page_size: number;
	pagination_max_page_size: number;

	code_theme: string;
	code_theme_dark: string;
	default_theme: string;
	primary_color: string;
	font_family: string | null;

	maintenance_mode: boolean;
	maintenance_message: string | null;
	maintenance_end_time: string | null;

	default_post_cover: string | null;
	default_avatar: string | null;
	default_category_cover: string | null;

	google_analytics_id: string | null;
	baidu_analytics_id: string | null;
	google_site_verification: string | null;
	baidu_site_verification: string | null;
	robots_txt: string | null;

	require_email_verification: boolean;
	allow_password_reset: boolean;
	session_timeout: number;
	max_login_attempts: number;
	login_lockout_duration: number;

	email_configured: boolean;
	email_from: string | null;
	email_from_name: string | null;

	max_upload_size: number;
	allowed_image_types: string;
	allowed_file_types: string;

	comment_require_approval: boolean;
	comment_allow_guest: boolean;
	comment_max_length: number;
	comment_antispam: boolean;

	custom_header_code: string | null;
	custom_footer_code: string | null;
	custom_css: string | null;
	custom_js: string | null;

	music_enabled: boolean;
	music_show_in_navbar: boolean;
	music_show_in_sidebar: boolean;
	music_mode: string;
	music_volume: number;
	music_play_mode: string;
	music_show_lyrics: boolean;
	music_meting_api: string;
	music_meting_server: string;
	music_meting_type: string;
	music_meting_id: string;

	wallpaper_mode: string;
	wallpaper_player_enable: boolean;
	wallpaper_desktop: string;
	wallpaper_mobile: string;
	wallpaper_video: string;
	wallpaper_use_bing: boolean;
	wallpaper_bing_days: number;
	wallpaper_dim_opacity: number;
	wallpaper_home_title: string;
	wallpaper_home_subtitle: string;
}

export interface SiteConfigUpdate extends Partial<SiteConfigResponse> {}

export type SettingGroup =
	| "basic"
	| "reading"
	| "comments"
	| "media"
	| "seo"
	| "email"
	| "cdn"
	| "cache"
	| "security"
	| "features"
	| "appearance"
	| "navigation"
	| "friendlinks"
	| "hero"
	| "notice"
	| "sidebar"
	| "footer";

export const SETTING_GROUPS: SettingGroup[] = [
	"basic",
	"reading",
	"comments",
	"media",
	"seo",
	"email",
	"cdn",
	"cache",
	"security",
	"features",
	"appearance",
	"navigation",
	"friendlinks",
	"hero",
	"notice",
	"sidebar",
	"footer",
];

export interface SiteSettingItem {
	key: string;
	label: string;
	description?: string | null;
	type: string;
	value: string | number | boolean | null;
	default?: string | number | boolean | null;
	options?: Array<Record<string, string>> | null;
	placeholder?: string | null;
	required?: boolean;
	min_value?: number | null;
	max_value?: number | null;
	pattern?: string | null;
}

export interface SiteSettingGroup {
	name: string;
	label: string;
	description?: string | null;
	icon?: string | null;
	settings: SiteSettingItem[];
}

export interface SettingsGroupsResponse {
	groups: Record<SettingGroup, Record<string, any>>;
	last_updated: string | null;
}

export interface SiteConfigFullResponse {
	groups: SiteSettingGroup[];
	last_updated?: string | null;
}

// ===== 投票相关模型 =====
export interface PollBase {
	title: string;
	description?: string | null;
	is_active?: boolean;
	allow_multiple?: boolean;
	show_results?: boolean;
}

export interface PollCreate extends PollBase {
	choices: string[];
}

export interface PollChoiceResponse {
	id: number;
	text: string;
	order: number;
	votes_count: number;
}

export interface PollResponse extends PollBase {
	id: number;
	choices: PollChoiceResponse[];
	total_votes: number;
	created_at: string;
}

export interface VoteCreate {
	choice_ids: number[];
}

// ===== 操作日志模型 =====
export type OperationAction =
	| "create"
	| "update"
	| "delete"
	| "login"
	| "logout"
	| "approve"
	| "reject"
	| "export"
	| "import"
	| "publish"
	| "unpublish"
	| string;

export interface OperationLogResponse {
	id: number;
	user_id: number | null;
	username: string | null;
	action: OperationAction;
	resource_type: string | null;
	resource_id: number | string | null;
	detail: Record<string, any> | null;
	ip_address: string | null;
	user_agent: string | null;
	status: "success" | "failed";
	error_message: string | null;
	created_at: string;
}

export interface OperationLogPagedResponse {
	items: OperationLogResponse[];
	total: number;
	page: number;
	page_size: number;
	total_pages: number;
}

// ===== OOBE 模型 =====
export interface OobeStatusResponse {
	installed: boolean;
	step: number;
	total_steps: number;
	has_admin: boolean;
	has_site_config: boolean;
	database_ok: boolean;
}

export interface OobeInitRequest {
	admin_username: string;
	admin_email: string;
	admin_password: string;
	site_name?: string;
	site_description?: string;
}

export interface HealthCheckResponse {
	status: "healthy" | "unhealthy" | "degraded";
	app_name: string;
	version: string;
	environment: string;
	database: "connected" | "disconnected";
	timestamp: string;
	checks?: Record<string, "pass" | "fail" | "warn">;
}

// ===== 从子模块再导出 =====
export type {
	ActivityBase,
	ActivityCreate,
	ActivityLocalizedResponse,
	ActivityResponse,
	ActivityType,
	ActivityUpdate,
} from "./schema-contract-activity";
export type {
	AnnouncementBase,
	AnnouncementCreate,
	AnnouncementResponse,
	AnnouncementType,
	AnnouncementUpdate,
} from "./schema-contract-announcement";
export type {
	CommentReactionCreate,
	CommentReactionResponse,
	CommentReactionType,
} from "./schema-contract-comment-reaction";
export type {
	HeroSlideBase,
	HeroSlideCreate,
	HeroSlideResponse,
	HeroSlideUpdate,
} from "./schema-contract-hero";
export type {
	PostSeriesBase,
	PostSeriesCreate,
	PostSeriesResponse,
	PostSeriesUpdate,
	PostSeriesWithPostsResponse,
} from "./schema-contract-post-series";

// ⚠️ 与 backend/schemas/__init__.py 一一对应，修改后请同步更新
