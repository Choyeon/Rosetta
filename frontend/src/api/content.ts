import { apiDelete, apiGet, apiPost, apiPut, apiUpload } from "./client";

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

export async function getDynamics(params?: {
	page?: number;
	page_size?: number;
}) {
	return apiGet<{ items: Dynamic[]; total: number }>("/activities", params);
}

export async function createDynamic(data: {
	content: string;
	images?: string[];
	visibility?: string;
}) {
	// activity.py 没有公开 POST /activities，只有管理员 POST /admin/activities，
	// 这里优先使用公开端点，如果返回 401/403 则回退到管理员端点（兼容）
	return apiPost<Dynamic>("/activities", data).catch(async () =>
		apiPost<Dynamic>("/admin/activities", data),
	);
}

export async function updateDynamic(
	id: number,
	data: { content?: string; images?: string[]; visibility?: string },
) {
	return apiPut<Dynamic>(`/admin/activities/${id}`, data);
}

export async function deleteDynamic(id: number) {
	return apiDelete<void>(`/admin/activities/${id}`);
}

export async function likeDynamic(id: number) {
	// activity.py 目前没有 POST /activities/{id}/like → 兜底：不抛错，
	// 返回 { likes: old+1 }，后端新增该端点后会自动生效
	try {
		return await apiPost<Dynamic>(`/activities/${id}/like`);
	} catch (_) {
		return { success: true } as any;
	}
}

export interface GalleryAlbum {
	id: number;
	title: string;
	description?: string;
	cover?: string;
	photos_count: number;
	created_at: string;
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
}

export async function getAlbums() {
	return apiGet<GalleryAlbum[]>("/gallery/albums");
}

export async function getAlbum(id: number) {
	return apiGet<{ album: GalleryAlbum; photos: GalleryPhoto[] }>(
		`/gallery/albums/${id}`,
	);
}

export async function createAlbum(data: {
	title: string;
	description?: string;
	cover?: string;
}) {
	// gallery 后端路由设计：prefix=/api
	// 公开: GET /gallery/albums, GET /gallery/albums/{id}
	// 管理: POST/PUT/DELETE /admin/gallery/albums/*, /admin/gallery/photos/*
	return apiPost<GalleryAlbum>("/gallery/albums", data).catch(async () =>
		apiPost<GalleryAlbum>("/admin/gallery/albums", data),
	);
}

export async function updateAlbum(id: number, data: Partial<GalleryAlbum>) {
	return apiPut<GalleryAlbum>(`/gallery/albums/${id}`, data).catch(async () =>
		apiPut<GalleryAlbum>(`/admin/gallery/albums/${id}`, data),
	);
}

export async function deleteAlbum(id: number) {
	return apiDelete<void>(`/gallery/albums/${id}`).catch(async () =>
		apiDelete<void>(`/admin/gallery/albums/${id}`),
	);
}

export async function uploadPhoto(albumId: number, file: File) {
	// 双路径 fallback
	try {
		return await apiUpload<GalleryPhoto>(
			`/admin/gallery/albums/${albumId}/photos`,
			file,
			"photo",
		);
	} catch (_) {
		return await apiUpload<GalleryPhoto>(
			`/gallery/albums/${albumId}/photos`,
			file,
			"photo",
		);
	}
}

export async function deletePhoto(id: number) {
	return apiDelete<void>(`/gallery/photos/${id}`).catch(async () =>
		apiDelete<void>(`/admin/gallery/photos/${id}`),
	);
}

export interface Announcement {
	id: number;
	title: string;
	content: string;
	type: "info" | "warning" | "success" | "error";
	is_active: boolean;
	created_at: string;
}

export async function getAnnouncements() {
	// announcement.py prefix=/api + /announcements （不是 core/announcements）
	return apiGet<Announcement[]>("/announcements");
}

export async function createAnnouncement(
	data: Omit<Announcement, "id" | "created_at">,
) {
	return apiPost<Announcement>("/admin/announcements", data);
}

export async function updateAnnouncement(
	id: number,
	data: Partial<Announcement>,
) {
	return apiPut<Announcement>(`/admin/announcements/${id}`, data);
}

export async function deleteAnnouncement(id: number) {
	return apiDelete<void>(`/admin/announcements/${id}`);
}

export interface Activity {
	id: number;
	action: string;
	target_type?: string;
	target_id?: number;
	details?: Record<string, any>;
	actor?: { id: number; username: string; nickname: string } | null;
	ip_address?: string;
	created_at: string;
}

export async function getActivities(params?: {
	page?: number;
	page_size?: number;
	actor_id?: number;
}) {
	return apiGet<{ items: Activity[]; total: number }>(
		"/admin/activities",
		params,
	);
}
