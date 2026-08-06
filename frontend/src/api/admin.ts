import {
	apiDelete,
	apiGet,
	apiPatch,
	apiPost,
	apiPut,
	type PaginatedResponse,
} from "./client";
import type {
	AdminUserListParams,
	AdminUserUpdateFull,
	NavigationCreate,
	NavigationTreeNode,
	NavigationUpdate,
	UserDetailResponse,
} from "./schema-contract";

// ===== 用户管理（后台）=====
export interface AdminUserListItem extends UserDetailResponse {}

export async function getUsers(
	params: AdminUserListParams = {},
): Promise<PaginatedResponse<AdminUserListItem>> {
	return apiGet<PaginatedResponse<AdminUserListItem>>("/admin/users", params);
}

export async function getUser(id: number): Promise<UserDetailResponse> {
	return apiGet<UserDetailResponse>(`/admin/users/${id}`);
}

export async function updateUserFull(
	id: number,
	data: AdminUserUpdateFull,
): Promise<UserDetailResponse> {
	return apiPut<UserDetailResponse>(`/admin/users/${id}`, data);
}

export async function activateUser(id: number): Promise<UserDetailResponse> {
	return apiPatch<UserDetailResponse>(`/admin/users/${id}`, {
		is_active: true,
	});
}

export async function banUser(id: number): Promise<UserDetailResponse> {
	return apiPatch<UserDetailResponse>(`/admin/users/${id}`, {
		is_banned: true,
	});
}

export async function unbanUser(id: number): Promise<UserDetailResponse> {
	return apiPatch<UserDetailResponse>(`/admin/users/${id}`, {
		is_banned: false,
	});
}

export async function resetUserPassword(
	id: number,
	payload: { new_password: string },
): Promise<{ success: boolean; message?: string }> {
	return apiPost<{ success: boolean; message?: string }>(
		`/admin/users/${id}/reset-password`,
		payload,
	);
}

export async function deleteUser(id: number): Promise<{ success: boolean }> {
	return apiDelete<{ success: boolean }>(`/admin/users/${id}`);
}

// 导航管理
export interface Navigation {
	id: number;
	title: { [key: string]: string } | string;
	url: string;
	icon?: string | null;
	location: "header" | "footer" | "sidebar";
	order: number;
	is_active: boolean;
	target_blank: boolean;
	parent_id?: number | null;
	children?: Navigation[];
	created_at?: string;
}

export type { NavigationCreate, NavigationTreeNode, NavigationUpdate };

export async function getNavigations(location?: string) {
	return apiGet<Navigation[]>("/navigations", { location });
}

export async function getAdminNavigations(location?: string) {
	return apiGet<Navigation[]>("/admin/navigations", { location });
}

export async function createNavigation(data: NavigationCreate) {
	return apiPost<Navigation>("/navigations", data);
}

export async function updateNavigation(id: number, data: NavigationUpdate) {
	return apiPut<Navigation>(`/navigations/${id}`, data);
}

export async function deleteNavigation(id: number) {
	return apiDelete(`/navigations/${id}`);
}

export async function updateNavItem(
	id: number,
	data: NavigationUpdate,
): Promise<Navigation> {
	return apiPut<Navigation>(`/navigations/${id}`, data);
}

export async function reorderNav(
	orderedIds: number[],
	parentId: number | null = null,
	location?: "header" | "footer" | "sidebar",
) {
	return apiPatch<{ success: boolean; message?: string }>(
		"/navigations/reorder",
		{
			ids: orderedIds,
			parent_id: parentId,
			location,
		},
	);
}

// 友情链接
export interface FriendLink {
	id: number;
	name: string;
	url: string;
	logo?: string;
	description?: string;
	group?: string;
	order: number;
	is_active: boolean;
	created_at: string;
}

export interface FriendLinkCreate {
	name: string;
	url: string;
	logo?: string;
	description?: string;
	group?: string;
	order?: number;
	is_active?: boolean;
}

export interface FriendLinkUpdate extends Partial<FriendLinkCreate> {}

export async function getFriendLinks(all?: boolean) {
	return apiGet<FriendLink[]>("/friend-links", { all });
}

export async function createFriendLink(data: FriendLinkCreate) {
	return apiPost<FriendLink>("/friend-links", data);
}

export async function updateFriendLink(id: number, data: FriendLinkUpdate) {
	return apiPut<FriendLink>(`/friend-links/${id}`, data);
}

export async function deleteFriendLink(id: number) {
	return apiDelete(`/friend-links/${id}`);
}

// 评论管理（管理员）
export interface AdminComment {
	id: number;
	post_id: number;
	user?: {
		id: number;
		username: string;
		nickname?: string;
		avatar?: string;
	} | null;
	author_name?: string;
	author_email?: string;
	author_website?: string;
	content: string;
	parent_id?: number | null;
	replies?: AdminComment[];
	likes: number;
	is_approved: boolean;
	ip_address?: string;
	user_agent?: string;
	created_at: string;
	post?: { id: number; title: string; slug: string };
	qq?: string | null;
	github?: string | null;
	avatar_source?: "auto" | "custom" | "github" | "qq" | "gravatar";
	resolved_avatar_url?: string | null;
}

export type AdminCommentStatus =
	| "pending"
	| "approved"
	| "rejected"
	| "spam"
	| "all";

export interface GetAdminCommentsParams {
	page?: number;
	page_size?: number;
	post_id?: number;
	status?: AdminCommentStatus;
	keyword?: string;
}

export type CommentBatchAction =
	| "approve"
	| "reject"
	| "spam"
	| "restore"
	| "delete";

export async function getAdminComments(params: GetAdminCommentsParams = {}) {
	return apiGet<PaginatedResponse<AdminComment>>("/admin/comments", params);
}

export async function approveComment(id: number) {
	return apiPatch<AdminComment>(`/admin/comments/${id}`, {
		status: "approved",
		active: true,
	});
}

export async function rejectComment(id: number) {
	return apiPatch<AdminComment>(`/admin/comments/${id}`, {
		status: "rejected",
		active: false,
	});
}

export async function markCommentSpam(id: number) {
	return apiPatch<AdminComment>(`/admin/comments/${id}`, {
		status: "spam",
		active: false,
	});
}

export async function restoreComment(id: number) {
	return apiPatch<AdminComment>(`/admin/comments/${id}`, {
		status: "pending",
		active: true,
	});
}

export async function deleteComment(id: number) {
	return apiDelete(`/admin/comments/${id}`);
}

export async function batchAdminComments(
	action: CommentBatchAction,
	ids: number[],
) {
	return apiPost<{ processed_count: number; action: CommentBatchAction }>(
		"/admin/comments/batch",
		{ action, ids },
	);
}

// 动态/说说管理
export interface Dynamic {
	id: number;
	content: string;
	images?: string[];
	author?: {
		id: number;
		username: string;
		nickname: string;
		avatar?: string;
	} | null;
	likes: number;
	comments_count: number;
	is_pinned: boolean;
	visibility: "public" | "private" | "friends";
	created_at: string;
	updated_at: string;
}

export interface DynamicCreate {
	content: string;
	images?: string[];
	visibility?: "public" | "private" | "friends";
	is_pinned?: boolean;
}

export interface DynamicUpdate extends Partial<DynamicCreate> {}

export async function getDynamics(params?: {
	page?: number;
	page_size?: number;
}) {
	return apiGet<PaginatedResponse<Dynamic>>("/admin/activities", params);
}

export async function createDynamic(data: DynamicCreate) {
	return apiPost<Dynamic>("/admin/activities", data);
}

export async function updateDynamic(id: number, data: DynamicUpdate) {
	return apiPut<Dynamic>(`/admin/activities/${id}`, data);
}

export async function deleteDynamic(id: number) {
	return apiDelete(`/admin/activities/${id}`);
}

export async function likeDynamic(id: number) {
	return apiPost(`/activities/${id}/like`);
}

// 相册管理
export interface GalleryAlbum {
	id: number;
	title: string;
	description?: string;
	cover?: string;
	photos_count: number;
	created_at: string;
	is_public: boolean;
}

export interface GalleryPhoto {
	id: number;
	album_id: number;
	title?: string;
	description?: string;
	url: string;
	thumbnail?: string;
	order: number;
	shot_at?: string;
	location?: string;
	camera?: string;
	settings?: string;
	created_at: string;
}

export interface AlbumCreate {
	title: string;
	description?: string;
	cover?: string;
	is_public?: boolean;
}

export interface AlbumUpdate extends Partial<AlbumCreate> {}

export async function getAlbums() {
	return apiGet<GalleryAlbum[]>("/gallery/albums");
}

export async function getAlbum(id: number) {
	return apiGet<{ album: GalleryAlbum; photos: GalleryPhoto[] }>(
		`/gallery/albums/${id}`,
	);
}

export async function createAlbum(data: AlbumCreate) {
	return apiPost<GalleryAlbum>("/gallery/albums", data);
}

export async function updateAlbum(id: number, data: AlbumUpdate) {
	return apiPut<GalleryAlbum>(`/gallery/albums/${id}`, data);
}

export async function deleteAlbum(id: number) {
	return apiDelete(`/gallery/albums/${id}`);
}

export async function uploadPhoto(albumId: number, file: File, title?: string) {
	const formData = new FormData();
	formData.append("photo", file);
	if (title) formData.append("title", title);

	const { API_BASE, getAuthToken } = await import("./client");
	const url = `${API_BASE}/gallery/albums/${albumId}/photos`;
	const headers: Record<string, string> = {};
	const token = getAuthToken();
	if (token) headers.Authorization = `Bearer ${token}`;

	const res = await fetch(url, { method: "POST", headers, body: formData });
	if (!res.ok) throw new Error(`HTTP ${res.status}`);
	return res.json() as Promise<GalleryPhoto>;
}

export async function deletePhoto(id: number) {
	return apiDelete(`/gallery/photos/${id}`);
}

export async function updatePhoto(
	id: number,
	data: { title?: string; description?: string; order?: number },
) {
	return apiPut<GalleryPhoto>(`/gallery/photos/${id}`, data);
}

// 活动日志
export interface Activity {
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

export async function getActivities(params?: {
	page?: number;
	page_size?: number;
	actor_id?: number;
	action?: string;
}) {
	return apiGet<PaginatedResponse<Activity>>("/admin/activities", params);
}

// 公告管理
export interface Announcement {
	id: number;
	title: string;
	content: string;
	type: "info" | "warning" | "success" | "error";
	is_active: boolean;
	created_at: string;
	expires_at?: string;
}

export interface AnnouncementCreate {
	title: string;
	content: string;
	type?: "info" | "warning" | "success" | "error";
	is_active?: boolean;
	expires_at?: string;
}

export interface AnnouncementUpdate extends Partial<AnnouncementCreate> {}

export async function getAnnouncements() {
	// announcement.py prefix=/api，公开接口 /announcements（没有 core/ 前缀）
	return apiGet<Announcement[]>("/announcements");
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

export async function getNavItems(location?: string) {
	return getAdminNavigations(location);
}

export async function createNavItem(data: NavigationCreate) {
	// core.py:416 导航创建端点是 POST /navigations（没有 /admin 前缀，内部 CurrentStaff 鉴权）
	return apiPost<Navigation>("/navigations", data);
}

export async function deleteNavItem(id: number) {
	// core.py:472 导航删除端点是 DELETE /navigations/{id}（没有 /admin 前缀）
	return apiDelete(`/navigations/${id}`);
}

export async function getFriends(all?: boolean) {
	return getFriendLinks(all);
}

export async function createFriend(data: FriendLinkCreate) {
	return apiPost<FriendLink>("/friend-links", data);
}

export async function updateFriend(id: number, data: FriendLinkUpdate) {
	return apiPut<FriendLink>(`/friend-links/${id}`, data);
}

export async function deleteFriend(id: number) {
	return apiDelete(`/friend-links/${id}`);
}

// 轮播图 (Hero Slides)
export async function getBanners(activeOnly?: boolean) {
	const { getHeroSlides } = await import("./site");
	return getHeroSlides(activeOnly);
}

export async function createBanner(data: any) {
	const { createHeroSlide } = await import("./site");
	return createHeroSlide(data);
}

export async function deleteBanner(id: number) {
	const { deleteHeroSlide } = await import("./site");
	return deleteHeroSlide(id);
}

// 自定义页面管理
export interface CustomPage {
	id: number;
	title: string;
	slug: string;
	content: string;
	template?: string;
	summary?: string;
	is_published: boolean;
	allow_comments: boolean;
	created_at: string;
	updated_at: string;
}

export async function getPages() {
	// core.py:62 页面列表端点是 GET /pages（没有 /admin 前缀，带 CurrentUserOptional 权限过滤）
	return apiGet<CustomPage[]>("/pages");
}

export async function deletePage(id: number) {
	// core.py:182 页面删除端点是 DELETE /pages/{page_id}（没有 /admin 前缀）
	return apiDelete(`/pages/${id}`);
}

// 评论关系类型修正
export interface CommentWithRelations extends AdminComment {}

// 仪表盘统计
export interface DashboardStats {
	total_posts: number;
	total_comments: number;
	total_users: number;
	total_views: number;
	pending_comments: number;
	draft_posts: number;
	recent_posts: any[];
	recent_comments: any[];
	popular_posts: any[];
}

export async function getDashboardStats() {
	return apiGet<DashboardStats>("/admin/dashboard/stats");
}

// ========== Task 8: 仪表盘 Stats ==========
export interface AdminStatsResponse {
	timeseries: {
		labels: string[];
		datasets: { key: string; values: number[] }[];
	};
	top_articles: {
		id: number | string;
		title: string;
		views: number;
		comments_count: number;
	}[];
	active_commenters: {
		name: string;
		avatar: string | null;
		comments_count: number;
	}[];
	system_health: {
		cpu_percent: number | null;
		memory_percent: number | null;
		db_rtt_ms: number | null;
		cache_hit_percent: number | null;
		health_score: number | null;
	};
	summary: {
		total_posts: number;
		total_drafts: number;
		total_published: number;
		total_comments: number;
		total_pending_comments: number;
		total_users: number;
		total_views_today: number;
		total_comments_today: number;
	};
}

export async function getAdminStats(range: "7d" | "30d" = "7d") {
	return apiGet<AdminStatsResponse>("/admin/stats", { range });
}

// ========== Task 8: 17 组系统设置 ==========
export const SETTING_GROUPS = [
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
] as const;

export type SettingGroup = (typeof SETTING_GROUPS)[number];

export interface SettingsGroupResponse {
	group: SettingGroup;
	data: Record<string, any>;
}

export interface AllSettingsResponse {
	groups: Record<SettingGroup, Record<string, any>>;
}

export async function getAllSettings() {
	// settings_groups.py prefix=/api，空路径 GET /api
	return apiGet<AllSettingsResponse>("/");
}

export async function getSettingsGroup(group: SettingGroup) {
	return apiGet<SettingsGroupResponse>(`/${group}`);
}

export async function updateSettingsGroup(
	group: SettingGroup,
	payload: Record<string, any>,
) {
	return apiPatch<{
		success: boolean;
		group: SettingGroup;
		data: Record<string, any>;
		changed: string[];
	}>(`/${group}`, payload);
}

// ========== Task 8: 操作日志 ==========
export interface OperationLog {
	id: number;
	user_id: number | null;
	user_name: string | null;
	user_avatar: string | null;
	action: string;
	target_type: string | null;
	target_id: string | number | null;
	details: any | null;
	ip: string | null;
	user_agent: string | null;
	request_path: string | null;
	request_method: string | null;
	status: "success" | "failed";
	error_code: string | null;
	created_at: string | null;
}

export interface LogListParams {
	user_id?: number;
	action?: string;
	target_type?: string;
	from?: string;
	to?: string;
	q?: string;
	page?: number;
	page_size?: number;
}

export interface LogListResponse {
	items: OperationLog[];
	total: number;
	page: number;
	page_size: number;
	pages: number;
}

export async function listOperationLogs(params: LogListParams = {}) {
	return apiGet<LogListResponse>("/admin/logs", params);
}

export interface CleanupLogsResponse {
	deleted_count: number;
	before: string;
}

export async function cleanupOldLogs(days = 7) {
	return apiDelete<CleanupLogsResponse>("/admin/logs/retention", { days });
}
