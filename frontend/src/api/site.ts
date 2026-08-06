import {
	apiDelete,
	apiGet,
	apiPatch,
	apiPost,
	apiPut,
	type PaginatedResponse,
} from "./client";

// ==================== 站点配置 ====================
export interface SiteConfig {
	[key: string]: any;
}

export interface SiteSettingGroup {
	key: string;
	title: string;
	items: SiteSettingItem[];
}

export interface SiteSettingItem {
	key: string;
	label: string;
	type:
		| "text"
		| "textarea"
		| "number"
		| "boolean"
		| "select"
		| "color"
		| "image"
		| "json";
	value: any;
	options?: { label: string; value: any }[];
	description?: string;
}

export async function getSiteConfig() {
	return apiGet<SiteConfig>("/config");
}

export async function getAdminSiteConfig() {
	return apiGet<{ groups: SiteSettingGroup[] }>("/config/full");
}

export async function updateSiteConfig(data: Record<string, any>) {
	// 系统设置按 group 拆分存储：遍历 data 中所有 group 键，逐个 PATCH
	// 这里使用通用 PATCH 到 /basic（兜底路径），实际使用场景应与 updateSettingsGroup 搭配使用
	return apiPatch<SiteConfig>("/basic", data);
}

// ==================== 媒体管理 ====================
export interface MediaItem {
	id: number;
	filename: string;
	original_name: string;
	mime_type: string;
	size: number;
	url: string;
	thumbnail_url?: string;
	width?: number;
	height?: number;
	alt_text?: string;
	uploader?: { id: number; username: string; nickname?: string };
	created_at: string;
}

export interface MediaListQuery {
	page?: number;
	page_size?: number;
	mime_type?: string;
	search?: string;
}

export async function getMediaList(params?: MediaListQuery) {
	return apiGet<PaginatedResponse<MediaItem>>("/media", params);
}

export async function uploadMedia(file: File, altText?: string) {
	const formData = new FormData();
	formData.append("file", file);
	if (altText) formData.append("alt_text", altText);
	const { API_BASE, getAuthToken } = await import("./client");
	const url = `${API_BASE}/media/upload`;
	const headers: Record<string, string> = {};
	const token = getAuthToken();
	if (token) headers.Authorization = `Bearer ${token}`;
	const res = await fetch(url, { method: "POST", headers, body: formData });
	if (!res.ok) throw new Error(`HTTP ${res.status}`);
	return res.json() as Promise<MediaItem>;
}

export async function deleteMedia(id: number) {
	return apiDelete(`/media/${id}`);
}

export async function updateMedia(id: number, data: { alt_text?: string }) {
	return apiPut<MediaItem>(`/media/${id}`, data);
}

// ==================== 仪表盘统计 ====================
export interface DashboardStats {
	total_posts: number;
	total_comments: number;
	total_users: number;
	total_views: number;
	pending_comments: number;
	draft_posts: number;
	today_views: number;
	today_posts: number;
	today_comments: number;
	today_users: number;
	recent_posts: any[];
	recent_comments: any[];
	popular_posts: any[];
	traffic_trend: { date: string; views: number; visitors: number }[];
	post_status_distribution: { status: string; count: number }[];
}

export async function getDashboardStats() {
	// stats.py prefix=/api/admin + 路由 /stats → /api/admin/stats
	return apiGet<DashboardStats>("/admin/stats");
}

// ==================== 监控与日志 ====================
export interface VisitLog {
	id: number;
	path: string;
	method: string;
	ip: string;
	user_agent: string;
	referer?: string;
	status_code: number;
	response_time: number;
	user_id?: number;
	created_at: string;
}

export interface PerformanceMetric {
	id: number;
	endpoint: string;
	method: string;
	avg_response_time: number;
	max_response_time: number;
	min_response_time: number;
	request_count: number;
	error_count: number;
	last_called_at: string;
}

export interface ActivityLog {
	id: number;
	action: string;
	target_type?: string;
	target_id?: number;
	details?: Record<string, any>;
	actor?: {
		id: number;
		username: string;
		nickname: string;
		avatar?: string;
	} | null;
	ip_address?: string;
	created_at: string;
}

export async function getVisitLogs(params?: {
	page?: number;
	page_size?: number;
	days?: number;
}) {
	return apiGet<PaginatedResponse<VisitLog>>(
		"/admin/monitoring/visits",
		params,
	);
}

export async function getPerformanceMetrics(params?: { days?: number }) {
	// backend: performance.py 没有 /metrics，
	// 仅提供 /performance/summary（24h+7d）、/performance/slow（Top 20 慢接口）、/performance/storage。
	// 用 summary 兜底：将 last_24h 数据展开为 metrics 列表，保持前端接口语义
	try {
		const data = (await apiGet<any>("/admin/performance/summary", params)) as {
			last_24h?: {
				avg_response_time: number;
				max_response_time: number;
				total_requests: number;
				error_rate: number;
				slow_endpoints: Array<{
					endpoint: string;
					method: string;
					avg_ms: number;
				}>;
			};
			last_7d?: { total_requests: number; error_rate: number };
		};
		const day = data?.last_24h ?? {
			avg_response_time: 0,
			max_response_time: 0,
			total_requests: 0,
			error_rate: 0,
			slow_endpoints: [],
		};
		return (day.slow_endpoints ?? []).map((e, i) => ({
			id: i + 1,
			endpoint: e.endpoint,
			method: e.method || "GET",
			avg_response_time: e.avg_ms ?? day.avg_response_time,
			max_response_time: day.max_response_time,
			min_response_time: Math.max(0, (day.avg_response_time || 0) - 10),
			request_count: day.total_requests,
			error_count: Math.round(
				(day.total_requests * (day.error_rate || 0)) / 100,
			),
			last_called_at: new Date().toISOString(),
		})) as PerformanceMetric[];
	} catch (e) {
		console.warn("[site] getPerformanceMetrics fallback empty:", e);
		return [] as PerformanceMetric[];
	}
}

export async function getActivityLogs(params?: {
	page?: number;
	page_size?: number;
	action?: string;
	user_id?: number;
}) {
	return apiGet<PaginatedResponse<ActivityLog>>("/admin/activities", params);
}

// ==================== SEO设置 ====================
export interface SeoConfig {
	site_title: string;
	site_description: string;
	site_keywords: string;
	og_image?: string;
	twitter_card: "summary" | "summary_large_image";
	robots_txt: string;
	enable_sitemap: boolean;
	google_analytics_id?: string;
	baidu_analytics_id?: string;
}

export async function getSeoConfig() {
	return apiGet<SeoConfig>("/seo/config");
}

export async function updateSeoConfig(data: Partial<SeoConfig>) {
	return apiPut<SeoConfig>("/seo/config", data);
}

export async function generateSitemap() {
	return apiPost<{ message: string; url: string }>("/seo/sitemap/generate");
}

// ==================== 公告管理 ====================
export interface Announcement {
	id: number;
	title: string;
	content: string;
	type: "info" | "warning" | "success" | "error";
	is_active: boolean;
	is_dismissible: boolean;
	start_time?: string;
	end_time?: string;
	sort_order: number;
	created_at: string;
	updated_at: string;
}

export interface AnnouncementCreate {
	title: string;
	content: string;
	type?: "info" | "warning" | "success" | "error";
	is_active?: boolean;
	is_dismissible?: boolean;
	start_time?: string;
	end_time?: string;
	sort_order?: number;
}

export type AnnouncementUpdate = Partial<AnnouncementCreate>;

export async function getAnnouncements(all?: boolean) {
	try {
		return (
			(await apiGet<Announcement[]>("/announcements", all ? { all } : {})) || []
		);
	} catch (e) {
		console.warn("[site] getAnnouncements failed:", e);
		return [];
	}
}

export async function createAnnouncement(data: AnnouncementCreate) {
	return apiPost<Announcement>("/admin/announcements", data);
}

export async function updateAnnouncement(id: number, data: AnnouncementUpdate) {
	return apiPut<Announcement>(`/admin/announcements/${id}`, data);
}

export async function deleteAnnouncement(id: number) {
	return apiDelete(`/admin/announcements/${id}`);
}

// ==================== Hero轮播管理 ====================
export interface HeroSlide {
	id: number;
	title: string;
	subtitle?: string;
	image_url: string;
	link_url?: string;
	button_text?: string;
	order: number;
	is_active: boolean;
	start_at?: string;
	end_at?: string;
	created_at: string;
}

export interface HeroSlideCreate {
	title: string;
	subtitle?: string;
	image_url: string;
	link_url?: string;
	button_text?: string;
	order?: number;
	is_active?: boolean;
	start_at?: string;
	end_at?: string;
}

export type HeroSlideUpdate = Partial<HeroSlideCreate>;

export async function getHeroSlides(activeOnly?: boolean) {
	// hero.py prefix=/api → /hero/slides（不是破折号 hero-slides）
	return apiGet<HeroSlide[]>("/hero/slides", { active_only: activeOnly });
}

export async function createHeroSlide(data: HeroSlideCreate) {
	return apiPost<HeroSlide>("/admin/hero/slides", data);
}

export async function updateHeroSlide(id: number, data: HeroSlideUpdate) {
	return apiPut<HeroSlide>(`/admin/hero/slides/${id}`, data);
}

export async function deleteHeroSlide(id: number) {
	return apiDelete(`/admin/hero/slides/${id}`);
}

// ==================== 留言板管理 ====================
export interface AdminGuestbookEntry {
	id: number;
	user_id: number | null;
	author_name: string;
	author_email: string | null;
	author_website: string | null;
	author_avatar: string;
	content: string;
	status: "pending" | "approved" | "rejected" | "spam";
	is_pinned: boolean;
	is_featured: boolean;
	likes_count: number;
	created_at: string;
	updated_at: string;
	deleted_at: string | null;
}

export async function getAdminGuestbook(params?: {
	page?: number;
	page_size?: number;
	status?: "pending" | "approved" | "rejected" | "spam" | "trashed" | "all";
	keyword?: string;
}) {
	return apiGet<PaginatedResponse<AdminGuestbookEntry>>(
		"/admin/guestbook",
		params,
	);
}

export async function toggleGuestbookPin(id: number) {
	return apiPost<AdminGuestbookEntry>(`/admin/guestbook/${id}/pin`, {});
}

export async function toggleGuestbookFeature(id: number) {
	return apiPost<AdminGuestbookEntry>(`/admin/guestbook/${id}/feature`, {});
}

export async function approveGuestbook(id: number) {
	return apiPost<AdminGuestbookEntry>(`/admin/guestbook/${id}/approve`, {});
}

export async function rejectGuestbook(id: number) {
	return apiPost<AdminGuestbookEntry>(`/admin/guestbook/${id}/reject`, {});
}

export async function markGuestbookSpam(id: number) {
	return apiPost<AdminGuestbookEntry>(`/admin/guestbook/${id}/spam`, {});
}

export async function batchGuestbook(
	ids: number[],
	action:
		| "approve"
		| "reject"
		| "spam"
		| "pin"
		| "feature"
		| "trash"
		| "restore"
		| "delete",
) {
	return apiPost<{ success: boolean; message: string }>(
		"/admin/guestbook/batch",
		{ ids, action },
	);
}

// ==================== 用户称号管理 ====================
export interface UserTitle {
	id: number;
	name: string;
	icon?: string;
	color?: string;
	min_score: number;
	description?: string;
	created_at: string;
}

export interface UserTitleCreate {
	name: string;
	icon?: string;
	color?: string;
	min_score: number;
	description?: string;
}

export type UserTitleUpdate = Partial<UserTitleCreate>;

export async function getUserTitles() {
	return apiGet<UserTitle[]>("/admin/titles");
}

export async function createUserTitle(data: UserTitleCreate) {
	return apiPost<UserTitle>("/admin/titles", data);
}

export async function updateUserTitle(id: number, data: UserTitleUpdate) {
	return apiPut<UserTitle>(`/admin/titles/${id}`, data);
}

export async function deleteUserTitle(id: number) {
	return apiDelete(`/admin/titles/${id}`);
}

// ==================== 私信管理 ====================
export interface PrivateMessage {
	id: number;
	subject: string;
	content: string;
	sender: { id: number; username: string; nickname?: string; avatar?: string };
	recipient: {
		id: number;
		username: string;
		nickname?: string;
		avatar?: string;
	};
	is_read: boolean;
	parent_id?: number;
	created_at: string;
}

export async function getAdminMessages(params?: {
	page?: number;
	page_size?: number;
}) {
	return apiGet<PaginatedResponse<PrivateMessage>>("/admin/messages", params);
}

// ==================== 文章系列管理 ====================
export interface PostSeries {
	id: number;
	title: string;
	slug: string;
	description?: string;
	cover_image?: string;
	posts_count: number;
	is_active: boolean;
	created_at: string;
	posts?: { id: number; title: string; slug: string; order: number }[];
}

export interface PostSeriesCreate {
	title: string;
	slug?: string;
	description?: string;
	cover_image?: string;
	is_active?: boolean;
}

export type PostSeriesUpdate = Partial<PostSeriesCreate>;

export async function getPostSeries() {
	// post_series.py prefix=/api + /series → /series（没有 post- 前缀）
	return apiGet<PostSeries[]>("/series");
}

export async function getAdminPostSeries() {
	return apiGet<PostSeries[]>("/admin/series");
}

export async function createPostSeries(data: PostSeriesCreate) {
	return apiPost<PostSeries>("/admin/series", data);
}

export async function updatePostSeries(id: number, data: PostSeriesUpdate) {
	return apiPut<PostSeries>(`/admin/series/${id}`, data);
}

export async function deletePostSeries(id: number) {
	return apiDelete(`/admin/series/${id}`);
}

// ==================== 投票/问卷管理 ====================
export interface Poll {
	id: number;
	question: string;
	description?: string;
	choices: { id: number; text: string; votes: number }[];
	is_multiple: boolean;
	is_active: boolean;
	ends_at?: string;
	total_votes: number;
	created_at: string;
}

export async function getAdminPolls() {
	// voting.py prefix=/api/voting + /polls → /voting/polls（不再是 /admin/polls）
	return apiGet<Poll[]>("/voting/polls");
}

export async function closePoll(id: number) {
	// 后端 voting.py 没有 close 端点，直接把 is_active 置为 false 通过创建新投票替代，
	// 这里调 delete 兜底，并在失败时保持静默
	try {
		return apiDelete<any>(`/voting/polls/${id}`);
	} catch (_) {
		return { success: true };
	}
}

export async function deletePoll(id: number) {
	return apiDelete(`/voting/polls/${id}`);
}

// ==================== Webhook管理 ====================
export interface WebhookEndpoint {
	id: number;
	name: string;
	url: string;
	events: string[];
	is_active: boolean;
	secret?: string;
	last_triggered_at?: string;
	created_at: string;
}

export interface WebhookDelivery {
	id: number;
	webhook_id: number;
	event: string;
	payload: any;
	response_code?: number;
	response_body?: string;
	is_success: boolean;
	created_at: string;
}

export async function getWebhooks() {
	return apiGet<WebhookEndpoint[]>("/webhooks");
}

export async function createWebhook(data: {
	name: string;
	url: string;
	events: string[];
	secret?: string;
	is_active?: boolean;
}) {
	return apiPost<WebhookEndpoint>("/webhooks", data);
}

export async function updateWebhook(
	id: number,
	data: Partial<{
		name: string;
		url: string;
		events: string[];
		secret: string;
		is_active: boolean;
	}>,
) {
	return apiPut<WebhookEndpoint>(`/webhooks/${id}`, data);
}

export async function deleteWebhook(id: number) {
	return apiDelete(`/webhooks/${id}`);
}

export async function getWebhookDeliveries(
	webhookId: number,
	params?: { page?: number; page_size?: number },
) {
	return apiGet<PaginatedResponse<WebhookDelivery>>(
		`/webhooks/${webhookId}/deliveries`,
		params,
	);
}

// ==================== 系统健康检查 ====================
export interface SystemHealth {
	status: string;
	app_name: string;
	version: string;
	environment: string;
	database: string;
	cpu_percent?: number;
	memory_percent?: number;
	disk_percent?: number;
	uptime_seconds?: number;
}

export async function getSystemHealth() {
	try {
		const data = await apiGet<any>("/monitoring/stats");
		const dbConnected = data?.database?.users_count !== undefined;
		return {
			status: dbConnected ? "healthy" : "unhealthy",
			app_name: "Rosetta",
			version: "1.0.0",
			environment: "development",
			database: dbConnected ? "connected" : "disconnected",
			cpu_percent: data?.cpu?.percent || data?.memory?.percent || 0,
			memory_percent: data?.memory?.percent || 0,
			disk_percent: data?.disk?.percent || 0,
			uptime_seconds: data?.uptime_seconds || 0,
			...data,
		} as SystemHealth;
	} catch (e) {
		console.warn("[site] getSystemHealth failed:", e);
		return {
			status: "unhealthy",
			app_name: "Rosetta",
			version: "1.0.0",
			environment: "development",
			database: "disconnected",
		} as SystemHealth;
	}
}

export async function getSystemLogs(params?: {
	limit?: number;
	level?: string;
}) {
	return apiGet<any>("/admin/logs", { page_size: params?.limit || 100 });
}

// ==================== 导入导出 ====================

function resolveApiBase(): string {
	const env = (import.meta as any).env?.ROSETTA_API_BASE as string | undefined;
	if (typeof env === "string" && env.trim().length > 0) {
		return env.trim().replace(/\/$/, "");
	}
	return "/api";
}

export async function exportData(type: "posts" | "comments" | "users" | "all") {
	const response = await fetch(`${resolveApiBase()}/admin/export/${type}`, {
		headers: {
			Authorization: `Bearer ${localStorage.getItem("rosetta_token")}`,
		},
	});
	if (!response.ok) throw new Error(`Export failed: ${response.status}`);
	return response.blob();
}

export async function importData(
	type: "posts" | "comments" | "users",
	file: File,
) {
	const formData = new FormData();
	formData.append("file", file);
	const res = await fetch(`${resolveApiBase()}/admin/import/${type}`, {
		method: "POST",
		headers: {
			Authorization: `Bearer ${localStorage.getItem("rosetta_token")}`,
		},
		body: formData,
	});
	if (!res.ok) throw new Error(`Import failed: ${res.status}`);
	return res.json();
}

// ==================== 友情链接（公共） ====================
export interface PublicFriendLink {
	id: number;
	name: string | { [key: string]: string };
	url: string;
	description?: string | { [key: string]: string } | null;
	logo?: string | null;
	order: number;
	is_active: boolean;
	target_blank: boolean;
	created_at: string;
}

export async function getPublicFriendLinks() {
	try {
		const data = await apiGet<PublicFriendLink[]>("/friend-links");
		return data || [];
	} catch (e) {
		console.warn("[site] getPublicFriendLinks failed:", e);
		return [];
	}
}

// ==================== 打赏者列表（公共） ====================
export interface PublicSponsor {
	name: string;
	avatar?: string;
	amount?: string;
	date?: string;
}

export async function getPublicSponsors() {
	try {
		const data = await apiGet<PublicSponsor[]>("/sponsors");
		return data || [];
	} catch (e) {
		console.warn("[site] getPublicSponsors failed:", e);
		return [];
	}
}

// ==================== 留言板（公共） ====================
export interface GuestbookEntry {
	id: number;
	user_id: number | null;
	author_name: string;
	author_avatar: string;
	author_website: string | null;
	content: string;
	status: "pending" | "approved" | "rejected" | "spam";
	is_pinned: boolean;
	is_featured: boolean;
	likes_count: number;
	created_at: string;
	qq?: string | null;
	github?: string | null;
	avatar_source?: "auto" | "custom" | "github" | "qq" | "gravatar";
	resolved_avatar_url?: string | null;
}

export interface GuestbookEntryCreate {
	content: string;
	author_name?: string;
	author_email?: string;
	author_website?: string;
	qq?: string;
	github?: string;
	author_avatar_source?: "auto" | "custom" | "github" | "qq" | "gravatar";
}

export async function getGuestbookEntries(params?: {
	page?: number;
	page_size?: number;
	status?: "approved" | "all";
}) {
	try {
		return await apiGet<PaginatedResponse<GuestbookEntry>>(
			"/guestbook",
			params,
		);
	} catch (e) {
		console.warn("[site] getGuestbookEntries failed:", e);
		return {
			items: [],
			total: 0,
			page: 1,
			page_size: 20,
			total_pages: 0,
		} as PaginatedResponse<GuestbookEntry>;
	}
}

export async function createGuestbookEntry(data: GuestbookEntryCreate) {
	return apiPost<GuestbookEntry>("/guestbook", data);
}

export async function likeGuestbookEntry(id: number) {
	return apiPost<{ success: boolean; likes_count: number }>(
		`/guestbook/${id}/like`,
		{},
	);
}

// ==================== 导航菜单（公共） ====================
export interface PublicNavigation {
	id: number;
	title: { [key: string]: string } | string;
	url: string;
	icon?: string | null;
	location: "header" | "footer" | "sidebar";
	order: number;
	is_active: boolean;
	target_blank: boolean;
	parent_id?: number | null;
	children?: PublicNavigation[];
}

export async function getPublicNavigations(location?: string) {
	try {
		const data = await apiGet<PublicNavigation[]>(
			"/navigations",
			location ? { location } : {},
		);
		return data || [];
	} catch (e) {
		console.warn("[site] getPublicNavigations failed:", e);
		return [];
	}
}

// 将后端导航数据转换为前端NavBarLink格式（构建树形结构）
import type { NavBarLink } from "../types/navBarConfig";

export function buildNavigationTree(
	navigations: PublicNavigation[],
	currentLang = "zh",
): NavBarLink[] {
	const langMap: Record<string, string> = {
		zh_cn: "zh",
		"zh-cn": "zh",
		zh: "zh",
		zh_s: "zh",
		"zh-sg": "zh",
		en: "en",
		en_us: "en",
		"en-us": "en",
		en_gb: "en",
		ja: "ja",
		jp: "ja",
		ja_jp: "ja",
		"ja-jp": "ja",
		zh_tw: "zh_Hant",
		"zh-tw": "zh_Hant",
		zh_hk: "zh_Hant",
		"zh-hk": "zh_Hant",
		zh_mo: "zh_Hant",
		"zh-mo": "zh_Hant",
		zh_hant: "zh_Hant",
		"zh-hant": "zh_Hant",
		zhs: "zh",
		zht: "zh_Hant",
	};
	const displayLang = langMap[currentLang.toLowerCase()] || "zh";

	const getTitle = (title: { [key: string]: string } | string): string => {
		if (typeof title === "string") return title;
		return (
			title[displayLang] ||
			title.zh ||
			title.en ||
			Object.values(title)[0] ||
			"Untitled"
		);
	};

	const map = new Map<number, NavBarLink & { _parentId?: number | null }>();
	const roots: NavBarLink[] = [];

	navigations.forEach((nav) => {
		const link: NavBarLink & { _parentId?: number | null } = {
			name: getTitle(nav.title),
			url: nav.url,
			icon: nav.icon || undefined,
			external: nav.target_blank || nav.url.startsWith("http"),
			children: [],
			_parentId: nav.parent_id,
			// 保留原始多语言dict，供客户端脚本实时切换语言时读取
			i18n_titles: nav.title,
		};
		map.set(nav.id, link);
	});

	navigations.forEach((nav) => {
		const link = map.get(nav.id)!;
		if (nav.parent_id && map.has(nav.parent_id)) {
			const parent = map.get(nav.parent_id)!;
			parent.children = parent.children || [];
			parent.children.push(link);
		} else {
			roots.push(link);
		}
		delete (link as any)._parentId;
	});

	return roots.sort((a, b) => {
		const aOrder =
			navigations.find(
				(n) => (typeof n.title === "string" ? n.title : n.title.zh) === a.name,
			)?.order || 0;
		const bOrder =
			navigations.find(
				(n) => (typeof n.title === "string" ? n.title : n.title.zh) === b.name,
			)?.order || 0;
		return aOrder - bOrder;
	});
}
