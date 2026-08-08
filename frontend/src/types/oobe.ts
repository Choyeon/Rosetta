/**
 * Rosetta OOBE Type Definitions
 *
 * 与 backend/api/oobe.py + backend/core/oobe_constants.py 一一对应。
 * 修改后端 OOBE schema 后请同步更新此文件。
 *
 * 命名约定：
 *   后端 Pydantic class → 前端 interface
 *   后端 snake_case    → 前端 camelCase (由 apiFetch 自动转换)
 */

// ===== 通用 =====
export type Environment = "development" | "production";
export type DatabaseType = "sqlite" | "postgresql" | "postgres";
export type ThemeMode = "light" | "dark";
export type StepStatus = "idle" | "active" | "done" | "error";

// ===== 校验规则（与 backend/core/oobe_constants.py 对齐） =====
export const OOBE_USERNAME_MIN_LENGTH = 3;
export const OOBE_USERNAME_MAX_LENGTH = 20;
export const OOBE_USERNAME_PATTERN = /^[A-Za-z0-9_-]{3,20}$/;
export const OOBE_PASSWORD_MIN_LENGTH = 8;
export const OOBE_EMAIL_PATTERN = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

// ===== Feature Flags（与 backend/core/oobe_constants.py FEATURE_FLAGS 对齐） =====
export const OOBE_FEATURE_FLAGS: Record<string, string> = {
	enable_comments: "启用评论系统",
	enable_registration: "启用用户注册",
	enable_rss: "启用 RSS 订阅",
	enable_bing_wallpaper: "启用 Bing 每日壁纸",
	enable_pagefind_search: "启用 Pagefind 站内搜索",
	enable_encrypted_posts: "启用加密文章",
	enable_music_player: "启用音乐播放器",
	enable_pio: "启用看板娘 (Live2D)",
	enable_hero: "启用首页 Hero 区",
	enable_announcement: "启用公告栏",
	enable_friend_links: "启用友链页面",
	enable_sidebar_widgets: "启用侧边栏组件",
	enable_gallery: "启用相册",
	enable_bangumi: "启用追番页面",
	enable_anime: "启用动漫页面",
};

export const OOBE_FEATURE_DEFAULTS: Record<string, boolean> = {
	enable_comments: true,
	enable_registration: true,
	enable_rss: true,
	enable_bing_wallpaper: true,
	enable_pagefind_search: true,
	enable_encrypted_posts: false,
	enable_music_player: true,
	enable_pio: false,
	enable_hero: false,
	enable_announcement: true,
	enable_friend_links: true,
	enable_sidebar_widgets: true,
	enable_gallery: true,
	enable_bangumi: true,
	enable_anime: true,
};

export const OOBE_FEATURE_META: Record<string, { icon: string; desc: string }> =
	{
		enable_comments: {
			icon: "material-symbols:mode-comment-outline-rounded",
			desc: "与读者互动的留言板，支持审核与反垃圾",
		},
		enable_registration: {
			icon: "material-symbols:person-add-outline-rounded",
			desc: "允许访客自助注册账号（建议开启邮箱校验）",
		},
		enable_rss: {
			icon: "material-symbols:rss-feed-rounded",
			desc: "生成 /rss.xml、/atom.xml、/feed.json 三种订阅",
		},
		enable_bing_wallpaper: {
			icon: "material-symbols:image-outline-rounded",
			desc: "每日拉取 Bing 首页图作为 Banner 背景",
		},
		enable_pagefind_search: {
			icon: "material-symbols:search-rounded",
			desc: "离线全文搜索引擎，无需后端即可快速检索",
		},
		enable_encrypted_posts: {
			icon: "material-symbols:shield-lock-outline-rounded",
			desc: "输入密码才能阅读的加密文章",
		},
		enable_music_player: {
			icon: "material-symbols:music-note-rounded",
			desc: "右下角全局音乐播放器 (MetingJS)",
		},
		enable_pio: {
			icon: "material-symbols:smart-toy-rounded",
			desc: "Live2D 看板娘对话组件",
		},
		enable_hero: {
			icon: "material-symbols:photo-album-rounded",
			desc: "顶部大图 Hero 区域介绍站点",
		},
		enable_announcement: {
			icon: "material-symbols:campaign-rounded",
			desc: "站点公告滚动条，发布重要通知",
		},
		enable_friend_links: {
			icon: "material-symbols:diversity-3-rounded",
			desc: "/links 友情链接页与申请",
		},
		enable_sidebar_widgets: {
			icon: "material-symbols:dashboard-rounded",
			desc: "侧边栏组件（归档/分类/标签/最新评论等）",
		},
		enable_gallery: {
			icon: "material-symbols:gallery-thumbnail-rounded",
			desc: "/gallery 相册页面",
		},
		enable_bangumi: {
			icon: "material-symbols:movie-outline-rounded",
			desc: "/bangumi 追番展示页（对接 BGM.tv）",
		},
		enable_anime: {
			icon: "material-symbols:theaters-rounded",
			desc: "/anime 动漫收藏展示页",
		},
	};

// ===== 请求体 =====
/** 对应 backend/api/oobe.py CombinedInstallRequest */
export interface CombinedInstallRequest {
	databaseType: DatabaseType;
	dbHost: string;
	dbPort: number;
	dbName: string;
	dbUser: string;
	dbPassword: string;
	dbPath: string;
	redisEnabled: boolean;
	redisHost: string;
	redisPort: number;
	redisPassword: string;
	adminUsername: string;
	adminEmail: string;
	adminPassword: string;
	adminNickname: string;
	siteName: string;
	siteDescription: string;
	siteUrl: string;
	siteKeywords: string;
	siteAuthor: string;
	siteEmail: string;
	enableComments: boolean;
	enableRegistration: boolean;
	enableRss: boolean;
	enableBingWallpaper: boolean;
	enablePagefindSearch: boolean;
	enableEncryptedPosts: boolean;
	enableMusicPlayer: boolean;
	environment: Environment;
}

/** 对应 backend/api/oobe.py DatabaseConfigRequest */
export interface DatabaseConfigRequest {
	dbType: DatabaseType;
	dbHost: string;
	dbPort: number;
	dbName: string;
	dbUser: string;
	dbPassword: string;
	dbPath: string;
	redisHost: string;
	redisPort: number;
	redisPassword: string;
	redisEnabled: boolean;
}

/** 对应 backend/api/oobe.py SiteConfigRequest */
export interface SiteConfigRequest {
	siteName: string;
	siteTitle: string;
	siteDescription: string;
	siteKeywords: string;
	siteAuthor: string;
	siteEmail: string;
	siteUrl: string;
	githubUrl: string;
	xUrl: string;
	bilibiliUrl: string;
	footerText: string;
	enableComments: boolean;
	enableRegistration: boolean;
	enableRss: boolean;
	defaultCoverImage: string;
}

/** 对应 backend/api/oobe.py AdminAccountRequest */
export interface AdminAccountRequest {
	username: string;
	email: string;
	nickname: string;
	password: string;
}

// ===== 响应体 =====
/** 对应 backend/api/oobe.py get_oobe_status 响应 */
export interface OobeStatusResponse {
	success: boolean;
	oobeComplete: boolean;
	hasConfig: boolean;
	state: OobeState | null;
	config: Record<string, any> | null;
}

/** OOBE 状态快照 */
export interface OobeState {
	currentStep: number;
	totalSteps: number;
	environment: Environment;
	databaseConfig: Record<string, any>;
	siteConfig: Record<string, any>;
	adminConfig: Record<string, any>;
	completed: boolean;
	errors: string[];
}

/** 环境检测项 */
export interface EnvCheckItem {
	name: string;
	status: "pass" | "fail" | "info";
	value: string;
	detail?: string;
}

/** 安装步骤 */
export interface InstallStep {
	name: string;
	status: StepStatus;
}

/** 安装结果 */
export interface InstallResult {
	siteName: string;
	adminUsername: string;
	frontendUrl: string;
	adminUrl: string;
}

/** 安装进度事件（SSE） */
export interface InstallProgressEvent {
	type: "progress" | "done" | "error" | "connected";
	stepId?: string;
	message?: string;
	percent?: number;
	step?: number;
	progress?: number;
	timestamp?: string;
	success?: boolean;
	error?: string;
	sid?: string;
	frontendUrl?: string;
	adminUrl?: string;
}

/** 环境检测响应 */
export interface EnvCheckResponse {
	success: boolean;
	pythonVersion: { ok: boolean; value: string; error?: string };
	uvInstalled: { ok: boolean; value?: string; error?: string };
	uvVersion: { ok: boolean; value: string | null; error?: string };
	nodeVersion: { ok: boolean; value: string; error?: string };
	pnpmVersion: { ok: boolean; value: string; error?: string };
	databaseConnectivity: { ok: boolean; value?: string; error?: string };
	redisConnectivity: { ok: boolean; value?: string; error?: string };
	diskFreeGb: { ok: boolean; value: number; error?: string };
	memoryFreeMb: { ok: boolean; value: number; error?: string };
}

// ===== 前端 Draft 类型 =====
export interface OobeDraft {
	database: {
		dbType: DatabaseType;
		dbHost: string;
		dbPort: number;
		dbName: string;
		dbUser: string;
		dbPassword: string;
		redisEnable: boolean;
		redisHost: string;
		redisPort: number;
		redisPassword: string;
	};
	site: {
		siteName: string;
		siteUrl: string;
		siteDescription: string;
		siteKeywords: string;
		siteAuthor: string;
		siteEmail: string;
	};
	admin: {
		adminUsername: string;
		adminEmail: string;
		adminNickname: string;
		adminPassword: string;
		confirmAdminPassword: string;
	};
	features: Record<string, boolean>;
}
