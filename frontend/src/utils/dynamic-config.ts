import { isAbortedFetchError } from "../api/client";
import { getSiteConfig } from "../api/site";
import { backgroundWallpaper as defaultWallpaperConfig } from "../config/backgroundWallpaper";
import { commentConfig as defaultCommentConfig } from "../config/commentConfig";
import { coverImageConfig as defaultCoverImageConfig } from "../config/coverImageConfig";
import { dynamicConfig as defaultDynamicPageConfig } from "../config/dynamicConfig";
import { sakuraConfig as defaultSakuraConfig } from "../config/effectsConfig";
import { friendsPageConfig as defaultFriendsPageConfig } from "../config/friendsConfig";
import { licenseConfig as defaultLicenseConfig } from "../config/licenseConfig";
import { mermaidConfig as defaultMermaidConfig } from "../config/mermaidConfig";
import { musicPlayerConfig as defaultMusicConfig } from "../config/musicConfig";
import { spineModelConfig as defaultPioSpineConfig } from "../config/pioConfig";
import { plantumlConfig as defaultPlantumlConfig } from "../config/plantumlConfig";
import { profileConfig as defaultProfileConfig } from "../config/profileConfig";
import { sidebarLayoutConfig } from "../config/sidebarConfig";
import { sponsorConfig as defaultSponsorPageConfig } from "../config/sponsorConfig";
import type { BackgroundWallpaperConfig } from "../types/backgroundWallpaper";
import type { MusicPlayerConfig } from "../types/musicConfig";
import type { ProfileConfig } from "../types/profileConfig";
import type { SidebarLayoutConfig } from "../types/sidebarConfig";
import type { SponsorMethod } from "../types/sponsorConfig";

export interface SidebarCardToggles {
	showProfile: boolean;
	showCategories: boolean;
	showTags: boolean;
	showRecentPosts: boolean;
	showRecentComments: boolean;
	showTagCloud: boolean;
	showSiteInfo: boolean;
	showMusic: boolean;
	showStatistics: boolean;
	showDynamics: boolean;
	widgetOrder: string[];
}

export interface SiteBasicInfo {
	siteUrl: string;
	siteStartDate: string;
	title: string;
	subtitle?: string;
	description: string;
	// 必须存在但可能为空字符串（strict 模式下 astro check 要读取不会报 18048）
	keywords: string | string[];
	author: string;
	primaryColor: string;
	// 页面级开关（被 Calendar / gallery / dynamic 等前台组件读取，因此提升到站点基础信息）
	// 设为必选 + 给 default 合并兜底，避免 ts(18048): 'siteConfig.pages' is possibly undefined
	pages: {
		friends: boolean;
		sponsor: boolean;
		guestbook: boolean;
		bangumi: boolean;
		gallery: boolean;
		anime: boolean;
		dynamic: boolean;
	};
	// 页面整体宽度（rem），Layout.astro 读取生成 CSS 变量
	pageWidth?: number;
	// 卡片样式配置，Layout.astro 读取生成 --card-border 等变量
	card?: {
		border: boolean;
		followTheme?: boolean;
	};
	// 多语言：前台通用组件读取，和 loadDynamicConfig 返回的本地 site.lang 保持一致
	lang: "en" | "zh_CN" | "zh_TW" | "ja" | string;
}

export interface FooterConfigData {
	customHtml: string;
	footerText: string;
	footerSlogan: string;
	copyrightText: string;
	icpNumber: string;
	policeIcpNumber: string;
	githubUrl: string;
	xUrl: string;
	bilibiliUrl: string;
	weiboUrl: string;
	zhihuUrl: string;
	youtubeUrl: string;
	linkedinUrl: string;
	telegramUrl: string;
}

export interface FriendsPageConfigData {
	title: string;
	description: string;
	showComment: boolean;
	showCustomContent: boolean;
}

export interface DynamicPageConfigData {
	title: string;
	description: string;
	itemsPerPage: number;
	showComment: boolean;
	apiUrl: string;
	profileUrl: string;
	memos: {
		enable: boolean;
		apiUrl: string;
		parent: string;
	};
}

export interface SponsorPageConfigData {
	title: string;
	description: string;
	usage: string;
	methods: SponsorMethod[];
	showSponsorsList: boolean;
	showComment: boolean;
	// 与 types/sponsorConfig.ts SponsorConfig 对齐：文章页底部打赏按钮开关
	showButtonInPost?: boolean;
}

// ========== 页面开关配置 ==========
export interface PagesConfigData {
	friends: boolean;
	sponsor: boolean;
	guestbook: boolean;
	bangumi: boolean;
	gallery: boolean;
	anime: boolean;
	dynamic: boolean;
}

// ========== 文章列表布局配置 ==========
export interface PostListLayoutConfigData {
	defaultMode: "list" | "grid";
	mobileDefaultMode: "list" | "grid";
	descriptionLines: number;
	showStatsIcons: boolean;
	tagsPosition: "meta" | "bottom";
}

// ========== 文章详情页配置 ==========
export interface PostDetailConfigData {
	showLastModified: boolean;
	outdatedThreshold: number;
	enableSharePoster: boolean;
	generateOgImages: boolean;
}

// ========== 封面图配置 ==========
export interface CoverImageConfigData {
	enableInPost: boolean;
	// 与 types/coverImageConfig.ts 对齐：封面叠加布局是可选项，后端未设置时走前端默认
	enableInPostOverlay?: boolean;
	showLoading?: boolean;
	randomCoverImage: {
		enable: boolean;
		apis: string[];
	};
}

// ========== 许可证配置 ==========
export interface LicenseConfigData {
	enable: boolean;
	name: string;
	url: string;
	// 与 types/licenseConfig.ts 对齐：icon 是可选项；不填时前端渲染通用 license 图标
	icon?: string;
}

// ========== 评论系统配置 ==========
export interface TwikooConfig {
	envId: string;
	lang: string;
	visitorCount: boolean;
	jsUrl: string;
	cssUrl: string;
}
export interface WalineConfig {
	serverURL: string;
	lang: string;
	emoji: string[];
	login: "enable" | "force" | "disable";
	visitorCount: boolean;
}
export interface ArtalkConfig {
	server: string;
	locale: string;
	visitorCount: boolean;
}
export interface GiscusConfig {
	repo: string;
	repoId: string;
	category: string;
	categoryId: string;
	mapping: string;
	strict: string;
	reactionsEnabled: string;
	emitMetadata: string;
	inputPosition: string;
	lang: string;
	loading: string;
}
export interface DisqusConfig {
	shortname: string;
}
export interface CommentConfigData {
	// 与 types/commentConfig.ts CommentConfig 对齐：新增 rosetta 后端内置评论类型
	type:
		| "none"
		| "twikoo"
		| "waline"
		| "giscus"
		| "disqus"
		| "artalk"
		| "rosetta";
	twikoo?: TwikooConfig;
	waline?: WalineConfig;
	artalk?: ArtalkConfig;
	giscus?: GiscusConfig;
	disqus?: DisqusConfig;
}

// ========== Bangumi配置 ==========
export interface BangumiConfigData {
	userId: string;
	mode: "static" | "dynamic";
	apiUrl: string;
	subjectBaseUrl: string;
	categoryOrder: string[];
	// 与 types/siteConfig.ts bangumi.categories 对齐：各分类显示开关
	categories?: {
		book?: boolean;
		anime?: boolean;
		music?: boolean;
		game?: boolean;
		real?: boolean;
	};
}

// ========== 追番配置 ==========
export interface AnimeConfigData {
	bilibili: { uid: string };
	tmdb: { apiKey: string; listId: string };
}

// ========== 分页配置 ==========
export interface PaginationConfigData {
	postsPerPage: number;
}

// ========== 图像优化配置 ==========
export interface ImageOptConfigData {
	formats: "avif" | "webp" | "both";
	quality: number;
	noReferrerDomains: string[];
}

// ========== 樱花特效配置 ==========
// 与 types/effectsConfig.ts SakuraConfig 对齐：补齐 limitTimes + speed，避免前端组件把 SakuraConfigData 当 SakuraConfig 用时报缺字段
export interface SakuraConfigData {
	enable: boolean;
	sakuraNum: number;
	limitTimes?: number; // -1 表示无限循环；后端没传时前端用默认值
	size: { min: number; max: number };
	opacity: { min: number; max: number };
	speed?: {
		horizontal: { min: number; max: number };
		vertical: { min: number; max: number };
		rotation: number;
		fadeSpeed: number;
	};
	zIndex: number;
}

// ========== 看板娘/Spine配置 ==========
export interface PioSpineConfigData {
	enable: boolean;
	model: { path: string; scale: number; x: number; y: number };
	position: { corner: string; offsetX: number; offsetY: number };
	size: { width: number; height: number };
	zIndex: number;
}

// ========== Mermaid配置 ==========
export interface MermaidConfigData {
	theme: string;
	securityLevel: string;
}

// ========== PlantUML配置 ==========
export interface PlantumlConfigData {
	serverUrl: string;
}

// ========== 主配置接口 ==========
export interface DynamicConfig {
	music: MusicPlayerConfig;
	wallpaper: BackgroundWallpaperConfig;
	profile: ProfileConfig;
	sidebar: SidebarCardToggles & {
		sidebarLayoutConfig: SidebarLayoutConfig;
	};
	site: SiteBasicInfo;
	footer: FooterConfigData;
	friendsPage: FriendsPageConfigData;
	dynamicPage: DynamicPageConfigData;
	sponsorPage: SponsorPageConfigData;
	pages: PagesConfigData;
	categoryBarEnabled: boolean;
	archiveFoldOldArticles: boolean;
	postListLayout: PostListLayoutConfigData;
	postDetail: PostDetailConfigData;
	coverImage: CoverImageConfigData;
	license: LicenseConfigData;
	comment: CommentConfigData;
	bangumi: BangumiConfigData;
	anime: AnimeConfigData;
	pagination: PaginationConfigData;
	imageOpt: ImageOptConfigData;
	sakura: SakuraConfigData;
	pioSpine: PioSpineConfigData;
	mermaid: MermaidConfigData;
	plantuml: PlantumlConfigData;
}

let cachedConfig: DynamicConfig | null = null;
let configPromise: Promise<DynamicConfig> | null = null;

function convertProfileConfig(apiConfig: any): ProfileConfig {
	let links = defaultProfileConfig.links;
	const rawLinks = apiConfig.author_links_json;
	if (typeof rawLinks === "string" && rawLinks.trim().length > 0) {
		try {
			const parsed = JSON.parse(rawLinks);
			if (Array.isArray(parsed) && parsed.length > 0) {
				links = parsed.map((l: any) => ({
					name: String(l.name ?? ""),
					icon: String(l.icon ?? ""),
					url: String(l.url ?? ""),
					showName: Boolean(l.showName ?? false),
				}));
			}
		} catch (e) {
			console.warn("[dynamic-config] Failed to parse author_links_json:", e);
		}
	} else if (Array.isArray(rawLinks) && rawLinks.length > 0) {
		links = rawLinks;
	}

	return {
		avatar: apiConfig.author_avatar || "",
		name: apiConfig.author_name || defaultProfileConfig.name,
		bio: apiConfig.author_bio || defaultProfileConfig.bio,
		links,
	};
}

function convertMusicConfig(apiConfig: any): MusicPlayerConfig {
	return {
		mode: apiConfig.music_mode || defaultMusicConfig.mode,
		volume: apiConfig.music_volume ?? defaultMusicConfig.volume,
		playMode: apiConfig.music_play_mode || defaultMusicConfig.playMode,
		showLyrics: apiConfig.music_show_lyrics ?? defaultMusicConfig.showLyrics,
		showInNavbar:
			apiConfig.music_show_in_navbar ?? defaultMusicConfig.showInNavbar,
		showInSidebar:
			apiConfig.music_show_in_sidebar ?? defaultMusicConfig.showInSidebar,
		meting: {
			api: apiConfig.music_meting_api || defaultMusicConfig.meting?.api,
			server:
				apiConfig.music_meting_server || defaultMusicConfig.meting?.server,
			type: apiConfig.music_meting_type || defaultMusicConfig.meting?.type,
			id: apiConfig.music_meting_id || defaultMusicConfig.meting?.id,
			fallbackApis: defaultMusicConfig.meting?.fallbackApis,
		},
		local: defaultMusicConfig.local,
	};
}

/**
 * 将 backend 返回的 sidebar 开关应用到 sidebarLayoutConfig 的各个组件 enable 上，
 * 返回新的 sidebarLayoutConfig 和原始显隐配置。
 */
function convertSidebarConfig(apiConfig: any): DynamicConfig["sidebar"] {
	const toggles: SidebarCardToggles = {
		showProfile: apiConfig.sidebar_show_profile ?? true,
		showCategories: apiConfig.sidebar_show_categories ?? true,
		showTags: apiConfig.sidebar_show_tags ?? true,
		showRecentPosts: apiConfig.sidebar_show_recent_posts ?? true,
		showRecentComments: apiConfig.sidebar_show_recent_comments ?? true,
		showTagCloud: apiConfig.sidebar_show_tag_cloud ?? true,
		showSiteInfo: apiConfig.sidebar_show_site_info ?? true,
		showMusic: apiConfig.sidebar_show_music ?? true,
		showStatistics: apiConfig.sidebar_show_statistics ?? true,
		showDynamics: apiConfig.sidebar_show_dynamics ?? true,
		widgetOrder:
			Array.isArray(apiConfig.sidebar_widget_order) &&
			apiConfig.sidebar_widget_order.length > 0
				? apiConfig.sidebar_widget_order
				: [
						"profile",
						"site_info",
						"statistics",
						"dynamics",
						"music",
						"categories",
						"tags",
						"recent_posts",
						"recent_comments",
					],
	};

	// 组件 type -> 对应开关的映射
	const typeToEnabled: Record<string, boolean> = {
		profile: toggles.showProfile,
		categories: toggles.showCategories,
		tags: toggles.showTags,
		recent_posts: toggles.showRecentPosts,
		recent_comments: toggles.showRecentComments,
		tag_cloud: toggles.showTagCloud,
		siteInfo: toggles.showSiteInfo,
		music: toggles.showMusic,
		stats: toggles.showStatistics,
		dynamic: toggles.showDynamics,
	};

	// 按 widget_order 对组件排序（匹配 type），但先保留 original positions
	const weightFor = (type: string): number => {
		const keyMap: Record<string, string> = {
			siteInfo: "site_info",
			stats: "statistics",
			dynamic: "dynamics",
			recent_posts: "recent_posts",
			recent_comments: "recent_comments",
			tag_cloud: "tag_cloud",
		};
		const k = keyMap[type] ?? type;
		const idx = toggles.widgetOrder.indexOf(k);
		return idx === -1 ? 9999 : idx;
	};

	const patchComponents = (arr: any[]) => {
		return arr
			.map((c) => {
				const enabled =
					typeToEnabled[c.type] === undefined
						? c.enable
						: typeToEnabled[c.type];
				return { ...c, enable: !!enabled };
			})
			.sort((a, b) => {
				// 先按 position 分组（top 在前），再按 widget_order 排序
				const posWeight = (p: string) => (p === "top" ? 0 : 1);
				const aPos = posWeight(a.position || "sticky");
				const bPos = posWeight(b.position || "sticky");
				if (aPos !== bPos) return aPos - bPos;
				return weightFor(a.type) - weightFor(b.type);
			});
	};

	const patchedSidebar: SidebarLayoutConfig = {
		...sidebarLayoutConfig,
		leftComponents: patchComponents(sidebarLayoutConfig.leftComponents),
		rightComponents: patchComponents(sidebarLayoutConfig.rightComponents),
		mobileBottomComponents: patchComponents(
			sidebarLayoutConfig.mobileBottomComponents,
		),
	};

	return {
		...toggles,
		sidebarLayoutConfig: patchedSidebar,
	};
}

/**
 * 从后端 /api/media/bing-wallpaper 获取今日 Bing 壁纸
 * 后端会优先返回 12h 缓存，Bing 不可用时自动 fallback 到最近一次成功结果。
 *
 * 输出兼容 convertWallpaperConfig 期望的「远程图片 URL 字符串」。
 * 如果后端返回空 url（极少见的 fallback），则回退到 bing.img.run / bing.biturl.top。
 *
 * Bing 官方 API 协议备忘：
 *   端点：https://www.bing.com/HPImageArchive.aspx?format=js&idx=0&n=1&mkt=zh-CN
 *   返回结构：{ images: [{ url, urlbase, copyright, title, startdate, ... }] }
 *   注意：url 是相对路径，例如 "/th?id=OHR.XXXX_1920x1080.jpg&rf=..."，必须拼接
 *         "https://www.bing.com" 前缀才是完整可访问的 CDN 地址。
 *   urlbase 是不带尺寸的 base，可自行拼 "_UHD.jpg"(4K) / "_1920x1080.jpg" 获取高清版本。
 */
async function resolveTodayBingWallpaperUrl(
	fallbackDays = 30,
): Promise<{ url: string; copyright: string; title: string }> {
	// ============== 工具：解析 Bing 官方数据 ==============
	function parseBingImage(first: any): {
		url: string;
		copyright: string;
		title: string;
	} {
		const copyright =
			typeof first?.copyright === "string" ? first.copyright : "";
		const title = typeof first?.title === "string" ? first.title : "";
		// Bing API 不会返回 full_url，只会返回相对 url 字段
		// 兼容本地后端可能自己拼好的 full_url 字段，避免重复前缀
		let rawUrl = "";
		if (typeof first?.full_url === "string" && first.full_url)
			rawUrl = first.full_url;
		else if (typeof first?.url === "string" && first.url) rawUrl = first.url;

		if (!rawUrl) return { url: "", copyright, title };

		// 已是完整 URL 直接用，否则补 bing 前缀
		if (/^https?:\/\//i.test(rawUrl)) return { url: rawUrl, copyright, title };
		const BING_CDN = "https://www.bing.com";
		if (rawUrl.startsWith("/"))
			return { url: `${BING_CDN}${rawUrl}`, copyright, title };
		return { url: `${BING_CDN}/${rawUrl}`, copyright, title };
	}

	// ============== 策略 1：本地后端代理 ==============
	try {
		// SSR/Node.js 环境下必须使用完整 URL（相对路径在 Node.js fetch 中无效）
		const IS_SSR = typeof (globalThis as any).window === "undefined";
		const ssrBackendBase =
			typeof (globalThis as any).process?.env?.ROSETTA_API_BASE === "string"
				? ((globalThis as any).process.env.ROSETTA_API_BASE as string).replace(
						/\/$/,
						"",
					)
				: "http://127.0.0.1:8000";
		const base = IS_SSR ? ssrBackendBase : "";
		const requestUrl = `${base}/api/media/bing-wallpaper?idx=0&n=1&mkt=zh-CN`;
		const r = await fetch(
			requestUrl,
			IS_SSR ? undefined : ({ credentials: "same-origin" } as any),
		);
		if (!r.ok) throw new Error(`bing-wallpaper http ${r.status}`);
		const data = await r.json();
		const first: any =
			Array.isArray(data?.images) && data.images.length > 0
				? data.images[0]
				: null;
		const parsed = parseBingImage(first);
		// 存储壁纸描述信息供前端使用
		if (!IS_SSR && typeof window !== "undefined") {
			(window as any).__bingWallpaperCopyright = parsed.copyright;
			(window as any).__bingWallpaperTitle = parsed.title;
		}
		if (parsed.url) return parsed;
	} catch (e) {
		if (isAbortedFetchError(e)) {
			// 页面切换时的正常取消，直接抛空字符串让上层用默认值
			return { url: "", copyright: "", title: "" };
		}
		console.warn(
			"[dynamic-config] /api/media/bing-wallpaper 解析失败，回退第三方 Bing 代理：",
			e,
		);
	}

	// ============== 策略 2：第三方 bing.biturl.top JSON API（带描述） ==============
	try {
		const fallbackUrl =
			"https://bing.biturl.top/?resolution=1920&format=json&index=0&mkt=zh-CN";
		const r = await fetch(fallbackUrl);
		if (r.ok) {
			const d = await r.json();
			const url = typeof d?.url === "string" ? d.url : "";
			const copyright = typeof d?.copyright === "string" ? d.copyright : "";
			const title =
				typeof d?.start_date === "string"
					? `Bing 每日壁纸 · ${d.start_date}`
					: "Bing 每日壁纸";
			if (url) {
				const IS_SSR = typeof (globalThis as any).window === "undefined";
				if (!IS_SSR && typeof window !== "undefined") {
					(window as any).__bingWallpaperCopyright = copyright;
					(window as any).__bingWallpaperTitle = title;
				}
				return { url, copyright, title };
			}
		}
	} catch (e) {
		console.warn(
			"[dynamic-config] bing.biturl.top 也失败，回退随机 day 图片占位：",
			e,
		);
	}

	// ============== 策略 3：兜底第三方 Bing 壁纸镜像（无描述） ==============
	const baseUrl = "https://bing.img.run";
	const randomDay = Math.floor(Math.random() * Math.min(fallbackDays, 30));
	return {
		url: `${baseUrl}/?day=${randomDay}`,
		copyright: "",
		title: "",
	};
}

function getBingWallpaperUrl(days = 30): string {
	const baseUrl = "https://bing.img.run";
	const randomDay = Math.floor(Math.random() * Math.min(days, 30));
	return `${baseUrl}/?day=${randomDay}`;
}

/**
 * 通过后端代理获取「指定 idx 偏移日」的 Bing 壁纸数据（带 title/copyright/full_url）。
 * idx 合法范围 [0, 7]，0=今日 1=昨日 ... 7=7 天前；超出会被后端自动 clamp。
 * 返回值：失败时回退第三方 bing.img.run 图片，其他字段留空（避免页面空白）。
 */
export async function fetchBingWallpaperByIndex(
	idx = 0,
	mkt = "zh-CN",
): Promise<{
	idx: number;
	url: string;
	copyright: string;
	title: string;
	startdate: string;
}> {
	const safeIdx = Math.max(0, Math.min(7, Number(idx) || 0));
	const fallback = {
		idx: safeIdx,
		url: getBingWallpaperUrl(30),
		copyright: "",
		title: "",
		startdate: "",
	};
	try {
		const IS_SSR = typeof (globalThis as any).window === "undefined";
		const ssrBackendBase =
			typeof (globalThis as any).process?.env?.ROSETTA_API_BASE === "string"
				? ((globalThis as any).process.env.ROSETTA_API_BASE as string).replace(
						/\/$/,
						"",
					)
				: "http://127.0.0.1:8000";
		const base = IS_SSR ? ssrBackendBase : "";
		const requestUrl = `${base}/api/media/bing-wallpaper?idx=${safeIdx}&n=1&mkt=${encodeURIComponent(mkt || "zh-CN")}`;
		const r = await fetch(
			requestUrl,
			IS_SSR ? undefined : ({ credentials: "same-origin" } as any),
		);
		if (!r.ok) throw new Error(`bing-wallpaper http ${r.status}`);
		const data = await r.json();
		const first =
			Array.isArray(data?.images) && data.images.length > 0
				? data.images[0]
				: null;
		if (!first) return fallback;
		const copyright =
			typeof first?.copyright === "string" ? first.copyright : "";
		const title = typeof first?.title === "string" ? first.title : "";
		const startdate =
			typeof first?.startdate === "string" ? first.startdate : "";
		let rawUrl = "";
		if (typeof first?.full_url === "string" && first.full_url)
			rawUrl = first.full_url;
		else if (typeof first?.url === "string" && first.url) rawUrl = first.url;
		let url = "";
		if (rawUrl) {
			if (/^https?:\/\//i.test(rawUrl)) url = rawUrl;
			else if (rawUrl.startsWith("/")) url = `https://www.bing.com${rawUrl}`;
			else url = `https://www.bing.com/${rawUrl}`;
		}
		if (!url) return fallback;
		return { idx: safeIdx, url, copyright, title, startdate };
	} catch (e) {
		if (isAbortedFetchError(e)) {
			return { ...fallback, url: "" };
		}
		console.warn(
			`[bing-wallpaper] idx=${safeIdx} fetch failed, fallback img.run:`,
			e,
		);
		return fallback;
	}
}

function convertWallpaperConfig(apiConfig: any): BackgroundWallpaperConfig {
	const useBing =
		apiConfig.wallpaper_use_bing === true ||
		apiConfig.wallpaper_use_bing === "true";
	// 默认未配置时，也展示 Bing 今日壁纸（保证首页 Banner 默认有高质量图）
	const forceBingAsDefault =
		useBing ||
		(!apiConfig.wallpaper_desktop &&
			!apiConfig.wallpaper_mobile &&
			!apiConfig.hero?.bg_image);
	const bingDays = apiConfig.wallpaper_bing_days ?? 30;

	let desktopSrc: any = apiConfig.wallpaper_desktop;
	let mobileSrc: any = apiConfig.wallpaper_mobile;
	const videoSrc = apiConfig.wallpaper_video;

	// 管理员已在 Hero 单独配置 bg_image 时，优先使用那一张
	const heroBgImage =
		apiConfig.hero &&
		typeof apiConfig.hero.bg_image === "string" &&
		apiConfig.hero.bg_image.trim()
			? apiConfig.hero.bg_image.trim()
			: "";

	if (!desktopSrc && heroBgImage) desktopSrc = heroBgImage;
	if (!mobileSrc && heroBgImage) mobileSrc = heroBgImage;

	if (forceBingAsDefault) {
		// 改为异步占位字符串：等真正渲染前，由调用方替换（见下方 patch 说明）
		// 但为了兼容现有结构（convertWallpaperConfig 是同步的），这里用一张立即可用的 URL。
		// 我们通过在 loadDynamicConfig 内先 resolve 一次再调用 convertWallpaperConfig 解决，
		// 此处保持兼容：若 _bingTodayUrl 已被写入则用它，否则用第三方 Bing 镜像作为 fallback。
		const bingUrl =
			typeof (apiConfig as any).__bingTodayUrl === "string" &&
			(apiConfig as any).__bingTodayUrl
				? (apiConfig as any).__bingTodayUrl
				: getBingWallpaperUrl(bingDays);
		if (!desktopSrc) desktopSrc = bingUrl;
		if (!mobileSrc) mobileSrc = bingUrl;
	}

	if (!desktopSrc) {
		desktopSrc = defaultWallpaperConfig.src;
	}

	let src: BackgroundWallpaperConfig["src"];
	if (typeof desktopSrc === "string" && desktopSrc) {
		src = {
			desktop: desktopSrc,
			mobile: mobileSrc || desktopSrc,
			playerUrl: videoSrc || (defaultWallpaperConfig.src as any).playerUrl,
		};
	} else {
		src = defaultWallpaperConfig.src;
	}

	const bingMeta = {
		title: (apiConfig as any).__bingTodayTitle || "",
		copyright: (apiConfig as any).__bingTodayCopyright || "",
	};

	// Bing 壁纸描述优先作为副标题（用户明确要求用 Bing 图片的描述）
	// 优先级：bingMeta.copyright → bingMeta.title → 后台配置 wallpaper_home_subtitle → 默认 subtitle
	const bingDesc =
		(bingMeta.copyright && String(bingMeta.copyright).trim()) ||
		(bingMeta.title && String(bingMeta.title).trim());
	let finalSubtitle: string | string[] | undefined;
	if (bingDesc) {
		finalSubtitle = bingDesc;
	} else if (apiConfig.wallpaper_home_subtitle) {
		const split = String(apiConfig.wallpaper_home_subtitle)
			.split("\n")
			.filter(Boolean);
		finalSubtitle = split.length > 0 ? split : undefined;
	} else {
		finalSubtitle = defaultWallpaperConfig.common?.homeText?.subtitle;
	}

	return {
		mode: apiConfig.wallpaper_mode || defaultWallpaperConfig.mode,
		playerEnable:
			apiConfig.wallpaper_player_enable ?? defaultWallpaperConfig.playerEnable,
		bingMeta: bingMeta.title || bingMeta.copyright ? bingMeta : undefined,
		src,
		common: {
			...defaultWallpaperConfig.common,
			dimOpacity:
				apiConfig.wallpaper_dim_opacity ??
				defaultWallpaperConfig.common?.dimOpacity,
			homeText: {
				...defaultWallpaperConfig.common?.homeText,
				enable: defaultWallpaperConfig.common?.homeText?.enable ?? false,
				title:
					apiConfig.wallpaper_home_title ||
					defaultWallpaperConfig.common?.homeText?.title,
				subtitle: finalSubtitle,
			},
		},
		banner: defaultWallpaperConfig.banner,
		overlay: defaultWallpaperConfig.overlay,
		fullscreen: defaultWallpaperConfig.fullscreen,
	};
}

function convertFooterConfig(apiConfig: any): FooterConfigData {
	return {
		customHtml: apiConfig.footer_custom_html || "",
		footerText: apiConfig.footer_text || "",
		footerSlogan: apiConfig.footer_slogan || "",
		copyrightText: apiConfig.copyright_text || "",
		icpNumber: apiConfig.icp_number || "",
		policeIcpNumber: apiConfig.police_icp_number || "",
		githubUrl: apiConfig.github_url || "",
		xUrl: apiConfig.x_url || "",
		bilibiliUrl: apiConfig.bilibili_url || "",
		weiboUrl: apiConfig.weibo_url || "",
		zhihuUrl: apiConfig.zhihu_url || "",
		youtubeUrl: apiConfig.youtube_url || "",
		linkedinUrl: apiConfig.linkedin_url || "",
		telegramUrl: apiConfig.telegram_url || "",
	};
}

function convertFriendsPageConfig(apiConfig: any): FriendsPageConfigData {
	return {
		title: apiConfig.friends_page_title || defaultFriendsPageConfig.title || "",
		description:
			apiConfig.friends_page_description ||
			defaultFriendsPageConfig.description ||
			"",
		showComment:
			typeof apiConfig.friends_page_show_comment === "boolean"
				? apiConfig.friends_page_show_comment
				: (defaultFriendsPageConfig.showComment ?? true),
		showCustomContent:
			typeof apiConfig.friends_page_show_custom_content === "boolean"
				? apiConfig.friends_page_show_custom_content
				: (defaultFriendsPageConfig.showCustomContent ?? true),
	};
}

function convertDynamicPageConfig(apiConfig: any): DynamicPageConfigData {
	const itemsPerPage =
		typeof apiConfig.dynamic_page_items_per_page === "number"
			? apiConfig.dynamic_page_items_per_page
			: (defaultDynamicPageConfig.itemsPerPage ?? 10);
	return {
		title: apiConfig.dynamic_page_title || defaultDynamicPageConfig.title || "",
		description:
			apiConfig.dynamic_page_description ||
			defaultDynamicPageConfig.description ||
			"",
		itemsPerPage: Math.max(1, itemsPerPage),
		showComment:
			typeof apiConfig.dynamic_page_show_comment === "boolean"
				? apiConfig.dynamic_page_show_comment
				: (defaultDynamicPageConfig.showComment ?? true),
		apiUrl: defaultDynamicPageConfig.apiUrl || "/api/activities",
		profileUrl: defaultDynamicPageConfig.profileUrl || "/about/",
		memos: {
			enable: defaultDynamicPageConfig.memos?.enable ?? false,
			apiUrl: defaultDynamicPageConfig.memos?.apiUrl || "",
			parent: defaultDynamicPageConfig.memos?.parent || "",
		},
	};
}

function convertSponsorPageConfig(apiConfig: any): SponsorPageConfigData {
	// 解析后端 sponsor_methods_json（JSON 字符串或数组）
	let methods: SponsorMethod[] = defaultSponsorPageConfig.methods || [];
	const rawMethods = apiConfig.sponsor_methods_json;
	if (typeof rawMethods === "string" && rawMethods.trim().length > 0) {
		try {
			const parsed = JSON.parse(rawMethods);
			if (Array.isArray(parsed) && parsed.length > 0) {
				methods = parsed.map((m: any) => ({
					name: String(m.name ?? ""),
					icon: String(m.icon ?? ""),
					qrCode: String(m.qrCode ?? ""),
					link: String(m.link ?? ""),
					description: String(m.description ?? ""),
					enabled:
						typeof m.enabled === "boolean"
							? m.enabled
							: m.enabled === undefined
								? true
								: Boolean(m.enabled),
				}));
			}
		} catch (e) {
			console.warn("[dynamic-config] Failed to parse sponsor_methods_json:", e);
		}
	} else if (Array.isArray(rawMethods) && rawMethods.length > 0) {
		methods = rawMethods;
	}

	return {
		title: apiConfig.sponsor_page_title || defaultSponsorPageConfig.title || "",
		description:
			apiConfig.sponsor_page_description ||
			defaultSponsorPageConfig.description ||
			"",
		usage: apiConfig.sponsor_page_usage || defaultSponsorPageConfig.usage || "",
		methods,
		showSponsorsList:
			typeof apiConfig.sponsor_show_sponsors_list === "boolean"
				? apiConfig.sponsor_show_sponsors_list
				: (defaultSponsorPageConfig.showSponsorsList ?? true),
		showComment:
			typeof apiConfig.sponsor_page_show_comment === "boolean"
				? apiConfig.sponsor_page_show_comment
				: (defaultSponsorPageConfig.showComment ?? true),
	};
}

// ========== 页面开关转换 ==========
function convertPagesConfig(apiConfig: any): PagesConfigData {
	return {
		friends:
			typeof apiConfig.page_friends_enabled === "boolean"
				? apiConfig.page_friends_enabled
				: true,
		sponsor:
			typeof apiConfig.page_sponsor_enabled === "boolean"
				? apiConfig.page_sponsor_enabled
				: true,
		guestbook:
			typeof apiConfig.page_guestbook_enabled === "boolean"
				? apiConfig.page_guestbook_enabled
				: true,
		bangumi:
			typeof apiConfig.page_bangumi_enabled === "boolean"
				? apiConfig.page_bangumi_enabled
				: true,
		gallery:
			typeof apiConfig.page_gallery_enabled === "boolean"
				? apiConfig.page_gallery_enabled
				: true,
		anime:
			typeof apiConfig.page_anime_enabled === "boolean"
				? apiConfig.page_anime_enabled
				: true,
		dynamic:
			typeof apiConfig.page_dynamic_enabled === "boolean"
				? apiConfig.page_dynamic_enabled
				: true,
	};
}

// ========== 封面图转换 ==========
function convertCoverImageConfig(apiConfig: any): CoverImageConfigData {
	let randomApis: string[] =
		defaultCoverImageConfig.randomCoverImage?.apis || [];
	const rawApis = apiConfig.cover_random_apis_json;
	if (typeof rawApis === "string" && rawApis.trim().length > 0) {
		try {
			const parsed = JSON.parse(rawApis);
			if (Array.isArray(parsed) && parsed.length > 0) {
				randomApis = parsed.map(String);
			}
		} catch (e) {
			console.warn(
				"[dynamic-config] Failed to parse cover_random_apis_json:",
				e,
			);
		}
	} else if (Array.isArray(rawApis) && rawApis.length > 0) {
		randomApis = rawApis.map(String);
	}

	return {
		enableInPost:
			typeof apiConfig.cover_enable_in_post === "boolean"
				? apiConfig.cover_enable_in_post
				: defaultCoverImageConfig.enableInPost,
		enableInPostOverlay:
			typeof apiConfig.cover_enable_overlay === "boolean"
				? apiConfig.cover_enable_overlay
				: defaultCoverImageConfig.enableInPostOverlay,
		showLoading:
			typeof apiConfig.cover_show_loading === "boolean"
				? apiConfig.cover_show_loading
				: defaultCoverImageConfig.showLoading,
		randomCoverImage: {
			enable:
				typeof apiConfig.cover_random_enable === "boolean"
					? apiConfig.cover_random_enable
					: (defaultCoverImageConfig.randomCoverImage?.enable ?? false),
			apis: randomApis,
		},
	};
}

// ========== 许可证转换 ==========
function convertLicenseConfig(apiConfig: any): LicenseConfigData {
	return {
		enable:
			typeof apiConfig.license_enable === "boolean"
				? apiConfig.license_enable
				: defaultLicenseConfig.enable,
		name: apiConfig.license_name || defaultLicenseConfig.name,
		url: apiConfig.license_url || defaultLicenseConfig.url,
		icon: apiConfig.license_icon || defaultLicenseConfig.icon,
	};
}

// ========== 评论系统转换 ==========
function convertCommentConfig(apiConfig: any): CommentConfigData {
	// Waline emoji
	let walineEmoji: string[] = defaultCommentConfig.waline?.emoji || [];
	const rawWalineEmoji = apiConfig.comment_waline_emoji_json;
	if (typeof rawWalineEmoji === "string" && rawWalineEmoji.trim().length > 0) {
		try {
			const parsed = JSON.parse(rawWalineEmoji);
			if (Array.isArray(parsed) && parsed.length > 0)
				walineEmoji = parsed.map(String);
		} catch (e) {
			console.warn(
				"[dynamic-config] Failed to parse comment_waline_emoji_json:",
				e,
			);
		}
	} else if (Array.isArray(rawWalineEmoji) && rawWalineEmoji.length > 0) {
		walineEmoji = rawWalineEmoji.map(String);
	}

	const type = (apiConfig.comment_system_type ||
		defaultCommentConfig.type) as CommentConfigData["type"];

	return {
		type: ["none", "twikoo", "waline", "giscus", "disqus", "artalk"].includes(
			type,
		)
			? type
			: "none",
		twikoo: {
			envId:
				apiConfig.comment_twikoo_env_id ||
				defaultCommentConfig.twikoo?.envId ||
				"",
			lang:
				apiConfig.comment_twikoo_lang ||
				defaultCommentConfig.twikoo?.lang ||
				"zh-CN",
			visitorCount:
				typeof apiConfig.comment_twikoo_visitor_count === "boolean"
					? apiConfig.comment_twikoo_visitor_count
					: (defaultCommentConfig.twikoo?.visitorCount ?? true),
			jsUrl:
				apiConfig.comment_twikoo_js_url ||
				defaultCommentConfig.twikoo?.jsUrl ||
				"",
			cssUrl:
				apiConfig.comment_twikoo_css_url ||
				defaultCommentConfig.twikoo?.cssUrl ||
				"",
		},
		waline: {
			serverURL:
				apiConfig.comment_waline_server_url ||
				defaultCommentConfig.waline?.serverURL ||
				"",
			lang:
				apiConfig.comment_waline_lang ||
				defaultCommentConfig.waline?.lang ||
				"zh-CN",
			emoji: walineEmoji,
			login:
				(apiConfig.comment_waline_login_mode as WalineConfig["login"]) ||
				defaultCommentConfig.waline?.login ||
				"enable",
			visitorCount:
				typeof apiConfig.comment_waline_visitor_count === "boolean"
					? apiConfig.comment_waline_visitor_count
					: (defaultCommentConfig.waline?.visitorCount ?? true),
		},
		artalk: {
			server:
				apiConfig.comment_artalk_server ||
				defaultCommentConfig.artalk?.server ||
				"",
			locale:
				apiConfig.comment_artalk_locale ||
				defaultCommentConfig.artalk?.locale ||
				"zh-CN",
			visitorCount:
				typeof apiConfig.comment_artalk_visitor_count === "boolean"
					? apiConfig.comment_artalk_visitor_count
					: (defaultCommentConfig.artalk?.visitorCount ?? true),
		},
		giscus: {
			repo:
				apiConfig.comment_giscus_repo ||
				defaultCommentConfig.giscus?.repo ||
				"",
			repoId:
				apiConfig.comment_giscus_repo_id ||
				defaultCommentConfig.giscus?.repoId ||
				"",
			category:
				apiConfig.comment_giscus_category ||
				defaultCommentConfig.giscus?.category ||
				"General",
			categoryId:
				apiConfig.comment_giscus_category_id ||
				defaultCommentConfig.giscus?.categoryId ||
				"",
			mapping:
				apiConfig.comment_giscus_mapping ||
				defaultCommentConfig.giscus?.mapping ||
				"title",
			strict:
				apiConfig.comment_giscus_strict ||
				defaultCommentConfig.giscus?.strict ||
				"0",
			reactionsEnabled:
				apiConfig.comment_giscus_reactions_enabled ||
				defaultCommentConfig.giscus?.reactionsEnabled ||
				"1",
			emitMetadata:
				apiConfig.comment_giscus_emit_metadata ||
				defaultCommentConfig.giscus?.emitMetadata ||
				"1",
			inputPosition:
				apiConfig.comment_giscus_input_position ||
				defaultCommentConfig.giscus?.inputPosition ||
				"top",
			lang:
				apiConfig.comment_giscus_lang ||
				defaultCommentConfig.giscus?.lang ||
				"zh-CN",
			loading:
				apiConfig.comment_giscus_loading ||
				defaultCommentConfig.giscus?.loading ||
				"lazy",
		},
		disqus: {
			shortname:
				apiConfig.comment_disqus_shortname ||
				defaultCommentConfig.disqus?.shortname ||
				"",
		},
	};
}

// ========== Bangumi转换 ==========
function convertBangumiConfig(apiConfig: any): BangumiConfigData {
	let categoryOrder: string[] = ["anime", "book", "music", "game"];
	const rawOrder = apiConfig.bangumi_category_order_json;
	if (typeof rawOrder === "string" && rawOrder.trim().length > 0) {
		try {
			const parsed = JSON.parse(rawOrder);
			if (Array.isArray(parsed) && parsed.length > 0)
				categoryOrder = parsed.map(String);
		} catch (e) {
			console.warn(
				"[dynamic-config] Failed to parse bangumi_category_order_json:",
				e,
			);
		}
	} else if (Array.isArray(rawOrder) && rawOrder.length > 0) {
		categoryOrder = rawOrder.map(String);
	}

	return {
		userId: apiConfig.bangumi_user_id || "",
		mode: apiConfig.bangumi_mode === "static" ? "static" : "dynamic",
		apiUrl: apiConfig.bangumi_api_url || "https://bgmapi.anibt.net",
		subjectBaseUrl:
			apiConfig.bangumi_subject_base_url || "https://bgmmi.anibt.net/subject/",
		categoryOrder,
	};
}

// ========== Anime追番转换 ==========
function convertAnimeConfig(apiConfig: any): AnimeConfigData {
	return {
		bilibili: { uid: apiConfig.anime_bilibili_uid || "" },
		tmdb: {
			apiKey: apiConfig.anime_tmdb_api_key || "",
			listId: apiConfig.anime_tmdb_list_id || "",
		},
	};
}

// ========== 图像优化转换 ==========
function convertImageOptConfig(apiConfig: any): ImageOptConfigData {
	let noReferrerDomains: string[] = ["*.hdslb.com", "*.bilibili.com"];
	const rawDomains = apiConfig.image_opt_no_referrer_json;
	if (typeof rawDomains === "string" && rawDomains.trim().length > 0) {
		try {
			const parsed = JSON.parse(rawDomains);
			if (Array.isArray(parsed) && parsed.length > 0)
				noReferrerDomains = parsed.map(String);
		} catch (e) {
			console.warn(
				"[dynamic-config] Failed to parse image_opt_no_referrer_json:",
				e,
			);
		}
	} else if (Array.isArray(rawDomains) && rawDomains.length > 0) {
		noReferrerDomains = rawDomains.map(String);
	}

	const fmt = apiConfig.image_opt_formats;
	return {
		formats: fmt === "avif" || fmt === "webp" || fmt === "both" ? fmt : "webp",
		quality:
			typeof apiConfig.image_opt_quality === "number"
				? Math.max(1, Math.min(100, apiConfig.image_opt_quality))
				: 85,
		noReferrerDomains,
	};
}

// ========== 樱花特效转换 ==========
function convertSakuraConfig(apiConfig: any): SakuraConfigData {
	return {
		enable:
			typeof apiConfig.sakura_enable === "boolean"
				? apiConfig.sakura_enable
				: defaultSakuraConfig.enable,
		sakuraNum:
			typeof apiConfig.sakura_count === "number"
				? apiConfig.sakura_count
				: defaultSakuraConfig.sakuraNum,
		size: {
			min:
				typeof apiConfig.sakura_min_scale === "number"
					? apiConfig.sakura_min_scale
					: (defaultSakuraConfig.size?.min ?? 0.5),
			max:
				typeof apiConfig.sakura_max_scale === "number"
					? apiConfig.sakura_max_scale
					: (defaultSakuraConfig.size?.max ?? 1.1),
		},
		opacity: {
			min:
				typeof apiConfig.sakura_min_opacity === "number"
					? apiConfig.sakura_min_opacity
					: (defaultSakuraConfig.opacity?.min ?? 0.3),
			max:
				typeof apiConfig.sakura_max_opacity === "number"
					? apiConfig.sakura_max_opacity
					: (defaultSakuraConfig.opacity?.max ?? 0.9),
		},
		zIndex:
			typeof apiConfig.sakura_z_index === "number"
				? apiConfig.sakura_z_index
				: (defaultSakuraConfig.zIndex ?? 100),
	};
}

// ========== Pio Spine转换 ==========
function convertPioSpineConfig(apiConfig: any): PioSpineConfigData {
	return {
		enable:
			typeof apiConfig.pio_spine_enable === "boolean"
				? apiConfig.pio_spine_enable
				: defaultPioSpineConfig.enable,
		model: {
			path:
				apiConfig.pio_spine_model_path ||
				(defaultPioSpineConfig.model as any)?.path ||
				"",
			scale:
				typeof apiConfig.pio_spine_scale === "number"
					? apiConfig.pio_spine_scale
					: ((defaultPioSpineConfig.model as any)?.scale ?? 1.0),
			x: 0,
			y: 0,
		},
		position: {
			corner:
				apiConfig.pio_spine_position_corner ||
				(defaultPioSpineConfig.position as any)?.corner ||
				"bottom-left",
			offsetX: 0,
			offsetY: 0,
		},
		size: {
			width:
				typeof apiConfig.pio_spine_width === "number"
					? apiConfig.pio_spine_width
					: ((defaultPioSpineConfig.size as any)?.width ?? 135),
			height:
				typeof apiConfig.pio_spine_height === "number"
					? apiConfig.pio_spine_height
					: ((defaultPioSpineConfig.size as any)?.height ?? 165),
		},
		zIndex:
			typeof apiConfig.pio_spine_z_index === "number"
				? apiConfig.pio_spine_z_index
				: ((defaultPioSpineConfig as any)?.zIndex ?? 1000),
	};
}

// ========== Mermaid转换 ==========
function convertMermaidConfig(apiConfig: any): MermaidConfigData {
	return {
		theme:
			apiConfig.mermaid_theme ||
			(defaultMermaidConfig as any)?.theme ||
			"default",
		securityLevel:
			apiConfig.mermaid_security_level ||
			(defaultMermaidConfig as any)?.securityLevel ||
			"strict",
	};
}

// ========== PlantUML转换 ==========
function convertPlantumlConfig(apiConfig: any): PlantumlConfigData {
	return {
		serverUrl:
			apiConfig.plantuml_server_url ||
			(defaultPlantumlConfig as any)?.serverUrl ||
			"https://www.plantuml.com/plantuml",
	};
}

export async function loadDynamicConfig(force = false): Promise<DynamicConfig> {
	if (cachedConfig && !force) {
		return cachedConfig;
	}

	if (configPromise && !force) {
		return configPromise;
	}

	configPromise = (async () => {
		try {
			const apiConfig = await getSiteConfig();

			// 优先尝试从后端代理拿今日 Bing 壁纸 URL（带 12h 缓存 + fallback）
			// 只要管理员没明确配置 wallpaper_desktop / mobile / hero.bg_image，
			// 就把这张 Bing 今日图作为首页默认 Banner。
			try {
				const hasExplicitBg =
					(typeof apiConfig.wallpaper_desktop === "string" &&
						!!apiConfig.wallpaper_desktop.trim()) ||
					(typeof apiConfig.wallpaper_mobile === "string" &&
						!!apiConfig.wallpaper_mobile.trim()) ||
					(typeof apiConfig.hero?.bg_image === "string" &&
						!!apiConfig.hero.bg_image.trim());
				const wantBing =
					apiConfig.wallpaper_use_bing === true ||
					apiConfig.wallpaper_use_bing === "true" ||
					!hasExplicitBg;
				if (wantBing) {
					const bingToday = await resolveTodayBingWallpaperUrl(
						typeof apiConfig.wallpaper_bing_days === "number"
							? apiConfig.wallpaper_bing_days
							: 30,
					);
					if (bingToday?.url) {
						(apiConfig as any).__bingTodayUrl = bingToday.url;
						(apiConfig as any).__bingTodayCopyright = bingToday.copyright;
						(apiConfig as any).__bingTodayTitle = bingToday.title;
						// 在 SSR 环境下也存储到全局（如果有 globalThis 对象）
						if (
							typeof (globalThis as any).__bingWallpaperCopyright ===
							"undefined"
						) {
							(globalThis as any).__bingWallpaperCopyright =
								bingToday.copyright;
							(globalThis as any).__bingWallpaperTitle = bingToday.title;
						}
					}
				}
			} catch (e) {
				console.warn("[dynamic-config] 解析 Bing 今日壁纸失败，使用默认：", e);
			}

			const pagesCfg = convertPagesConfig(apiConfig);
			const config: DynamicConfig = {
				music: convertMusicConfig(apiConfig),
				wallpaper: convertWallpaperConfig(apiConfig),
				profile: convertProfileConfig(apiConfig),
				sidebar: convertSidebarConfig(apiConfig),
				site: {
					siteUrl: apiConfig.site_url || "",
					siteStartDate: apiConfig.site_start_date || "2025-01-01",
					title: apiConfig.site_name || "ROSETTA",
					description: apiConfig.site_description || "",
					keywords: apiConfig.site_keywords || "",
					author: apiConfig.site_author || "",
					primaryColor: apiConfig.primary_color || "#3B82F6",
					// pages 合并到 site：Layout/页面组件大量读取 siteConfig.pages.*
					pages: pagesCfg,
					// pageWidth 和 card 合并到 site：Layout.astro 读取用于生成 CSS 变量
					pageWidth:
						typeof apiConfig.site_page_width === "number"
							? apiConfig.site_page_width
							: undefined,
					card:
						typeof apiConfig.card_border === "boolean" ||
						typeof apiConfig.card_follow_theme === "boolean"
							? {
									border: apiConfig.card_border ?? true,
									followTheme: apiConfig.card_follow_theme ?? false,
								}
							: undefined,
					// lang 默认浏览器zh-CN
					lang:
						typeof apiConfig.site_lang === "string"
							? apiConfig.site_lang
							: "zh_CN",
				},
				footer: convertFooterConfig(apiConfig),
				friendsPage: convertFriendsPageConfig(apiConfig),
				dynamicPage: convertDynamicPageConfig(apiConfig),
				sponsorPage: convertSponsorPageConfig(apiConfig),
				pages: convertPagesConfig(apiConfig),
				categoryBarEnabled:
					typeof apiConfig.category_bar_enabled === "boolean"
						? apiConfig.category_bar_enabled
						: true,
				archiveFoldOldArticles:
					typeof apiConfig.archive_fold_old_articles === "boolean"
						? apiConfig.archive_fold_old_articles
						: true,
				postListLayout: {
					defaultMode:
						apiConfig.post_list_default_mode === "grid" ? "grid" : "list",
					mobileDefaultMode:
						apiConfig.post_list_mobile_mode === "list" ? "list" : "grid",
					descriptionLines:
						typeof apiConfig.post_list_description_lines === "number"
							? Math.max(0, apiConfig.post_list_description_lines)
							: 2,
					showStatsIcons:
						typeof apiConfig.post_list_show_stats_icons === "boolean"
							? apiConfig.post_list_show_stats_icons
							: true,
					tagsPosition:
						apiConfig.post_list_tags_position === "meta" ? "meta" : "bottom",
				},
				postDetail: {
					showLastModified:
						typeof apiConfig.post_show_last_modified === "boolean"
							? apiConfig.post_show_last_modified
							: true,
					outdatedThreshold:
						typeof apiConfig.post_outdated_threshold_days === "number"
							? Math.max(1, apiConfig.post_outdated_threshold_days)
							: 30,
					enableSharePoster:
						typeof apiConfig.post_enable_share_poster === "boolean"
							? apiConfig.post_enable_share_poster
							: true,
					generateOgImages:
						typeof apiConfig.post_generate_og_images === "boolean"
							? apiConfig.post_generate_og_images
							: false,
				},
				coverImage: convertCoverImageConfig(apiConfig),
				license: convertLicenseConfig(apiConfig),
				comment: convertCommentConfig(apiConfig),
				bangumi: convertBangumiConfig(apiConfig),
				anime: convertAnimeConfig(apiConfig),
				pagination: {
					postsPerPage:
						typeof apiConfig.pagination_posts_per_page === "number"
							? Math.max(1, apiConfig.pagination_posts_per_page)
							: 10,
				},
				imageOpt: convertImageOptConfig(apiConfig),
				sakura: convertSakuraConfig(apiConfig),
				pioSpine: convertPioSpineConfig(apiConfig),
				mermaid: convertMermaidConfig(apiConfig),
				plantuml: convertPlantumlConfig(apiConfig),
			};
			cachedConfig = config;
			return config;
		} catch (e) {
			console.warn(
				"[dynamic-config] Failed to load config from API, using defaults:",
				e,
			);
			const fallbackSidebar = convertSidebarConfig({});
			const fallback: DynamicConfig = {
				music: defaultMusicConfig,
				wallpaper: defaultWallpaperConfig,
				profile: { ...defaultProfileConfig },
				sidebar: fallbackSidebar,
				site: {
					siteUrl: "",
					siteStartDate: "2025-01-01",
					title: "ROSETTA",
					description: "",
					keywords: "",
					author: "",
					primaryColor: "#3B82F6",
					// fallback 版本 pages 设为全 true
					pages: {
						friends: true,
						sponsor: true,
						guestbook: true,
						bangumi: true,
						gallery: true,
						anime: true,
						dynamic: true,
					},
					lang: "zh_CN",
				},
				footer: {
					customHtml: "",
					footerText: "",
					footerSlogan: "",
					copyrightText: "",
					icpNumber: "",
					policeIcpNumber: "",
					githubUrl: "",
					xUrl: "",
					bilibiliUrl: "",
					weiboUrl: "",
					zhihuUrl: "",
					youtubeUrl: "",
					linkedinUrl: "",
					telegramUrl: "",
				},
				friendsPage: {
					title: defaultFriendsPageConfig.title || "",
					description: defaultFriendsPageConfig.description || "",
					showComment: defaultFriendsPageConfig.showComment ?? true,
					showCustomContent: defaultFriendsPageConfig.showCustomContent ?? true,
				},
				dynamicPage: {
					title: defaultDynamicPageConfig.title || "",
					description: defaultDynamicPageConfig.description || "",
					itemsPerPage: defaultDynamicPageConfig.itemsPerPage ?? 10,
					showComment: defaultDynamicPageConfig.showComment ?? true,
					apiUrl: defaultDynamicPageConfig.apiUrl || "/api/activities",
					profileUrl: defaultDynamicPageConfig.profileUrl || "/about/",
					memos: {
						enable: defaultDynamicPageConfig.memos?.enable ?? false,
						apiUrl: defaultDynamicPageConfig.memos?.apiUrl || "",
						parent: defaultDynamicPageConfig.memos?.parent || "",
					},
				},
				sponsorPage: {
					title: defaultSponsorPageConfig.title || "",
					description: defaultSponsorPageConfig.description || "",
					usage: defaultSponsorPageConfig.usage || "",
					methods: defaultSponsorPageConfig.methods || [],
					showSponsorsList: defaultSponsorPageConfig.showSponsorsList ?? true,
					showComment: defaultSponsorPageConfig.showComment ?? true,
				},
				pages: {
					friends: true,
					sponsor: true,
					guestbook: true,
					bangumi: true,
					gallery: true,
					anime: true,
					dynamic: true,
				},
				categoryBarEnabled: true,
				archiveFoldOldArticles: true,
				postListLayout: {
					defaultMode: "list",
					mobileDefaultMode: "grid",
					descriptionLines: 2,
					showStatsIcons: true,
					tagsPosition: "bottom",
				},
				postDetail: {
					showLastModified: true,
					outdatedThreshold: 30,
					enableSharePoster: true,
					generateOgImages: false,
				},
				coverImage: defaultCoverImageConfig,
				license: defaultLicenseConfig,
				// defaultCommentConfig 来自 types/commentConfig.ts CommentConfig，其结构几乎完全兼容
				// 但缺少 "rosetta" 类型值 + 部分子类型的 strict 可选/必填精确类型不一致
				// 因为 DynamicConfig.comment: CommentConfigData；使用类型断言避免冗余定义
				comment: defaultCommentConfig as unknown as CommentConfigData,
				bangumi: {
					userId: "",
					mode: "dynamic",
					apiUrl: "https://bgmapi.anibt.net",
					subjectBaseUrl: "https://bgmmi.anibt.net/subject/",
					categoryOrder: ["anime", "book", "music", "game"],
				},
				anime: {
					bilibili: { uid: "" },
					tmdb: { apiKey: "", listId: "" },
				},
				pagination: { postsPerPage: 10 },
				imageOpt: {
					formats: "webp",
					quality: 85,
					noReferrerDomains: ["*.hdslb.com", "*.bilibili.com"],
				},
				sakura: defaultSakuraConfig,
				pioSpine: {
					enable: defaultPioSpineConfig.enable,
					model: {
						path: (defaultPioSpineConfig.model as any)?.path || "",
						scale: (defaultPioSpineConfig.model as any)?.scale ?? 1.0,
						x: 0,
						y: 0,
					},
					position: {
						corner:
							(defaultPioSpineConfig.position as any)?.corner || "bottom-left",
						offsetX: 0,
						offsetY: 0,
					},
					size: {
						width: (defaultPioSpineConfig.size as any)?.width ?? 135,
						height: (defaultPioSpineConfig.size as any)?.height ?? 165,
					},
					zIndex: (defaultPioSpineConfig as any)?.zIndex ?? 1000,
				},
				mermaid: {
					theme: (defaultMermaidConfig as any)?.theme || "default",
					securityLevel:
						(defaultMermaidConfig as any)?.securityLevel || "strict",
				},
				plantuml: {
					serverUrl:
						(defaultPlantumlConfig as any)?.serverUrl ||
						"https://www.plantuml.com/plantuml",
				},
			};
			cachedConfig = fallback;
			return fallback;
		}
	})();

	return configPromise;
}

export function getCachedConfig(): DynamicConfig | null {
	return cachedConfig;
}
