import { apiDelete, apiGet, apiPut, type PaginatedResponse } from "./client";

export interface User {
	id: number;
	username: string;
	email: string;
	nickname: string;
	avatar?: string | null;
	bio?: string | null;
	cover_image?: string | null;
	is_active: boolean;
	is_staff: boolean;
	is_superuser: boolean;
	created_at: string;
	last_login?: string | null;
	posts_count?: number;
	comments_count?: number;
	likes_count?: number;
	qq?: string | null;
	github?: string | null;
	avatar_source?: "auto" | "custom" | "github" | "qq" | "gravatar";
	resolved_avatar_url?: string | null;
}

export interface UserUpdate {
	email?: string;
	nickname?: string;
	bio?: string;
	avatar?: string | null;
	cover_image?: string | null;
	is_active?: boolean;
	is_staff?: boolean;
	is_superuser?: boolean;
	website?: string | null;
	github?: string | null;
	qq?: string | null;
	avatar_source?: "auto" | "custom" | "github" | "qq" | "gravatar";
}

export interface UserPreference {
	language: string;
	theme: "light" | "dark" | "system";
	code_theme_light: string;
	code_theme_dark: string;
	email_notification: boolean;
	comment_notification: boolean;
	like_notification: boolean;
}

export interface UserPreferenceUpdate extends Partial<UserPreference> {}

export interface PasswordChange {
	old_password: string;
	new_password: string;
}

// 当前用户
export async function getCurrentUser() {
	return apiGet<User>("/users/me");
}

export async function updateCurrentUser(data: UserUpdate) {
	return apiPut<User>("/users/me", data);
}

export async function changePassword(data: PasswordChange) {
	return apiPost("/users/me/change-password", data);
}

export async function updateAvatar(avatar: string) {
	return apiPut<User>("/users/me/avatar", undefined, { avatar });
}

export async function updateCover(cover_image: string) {
	return apiPut<User>("/users/me/cover", undefined, { cover_image });
}

export async function deleteAccount(password: string) {
	return apiDelete("/users/me", { password });
}

export async function getMyPreferences() {
	return apiGet<UserPreference>("/users/me/preferences");
}

export async function updateMyPreferences(data: UserPreferenceUpdate) {
	return apiPut<UserPreference>("/users/me/preferences", data);
}

// 用户管理（管理员）
export async function getUsers(params?: {
	page?: number;
	page_size?: number;
	search?: string;
}) {
	return apiGet<PaginatedResponse<User>>("/users/", params);
}

export async function getUser(userId: number) {
	return apiGet<User>(`/users/${userId}`);
}

export async function getUserByUsername(username: string) {
	return apiGet<User>(`/users/username/${username}`);
}

export async function getUserStats(userId: number) {
	return apiGet<{
		posts: number;
		comments: number;
		likes: number;
		views: number;
	}>(`/users/${userId}/stats`);
}

export async function getUserPosts(
	userId: number,
	params?: { page?: number; page_size?: number },
) {
	return apiGet<PaginatedResponse<any>>(`/users/${userId}/posts`, params);
}

export async function getUserComments(
	userId: number,
	params?: { page?: number; page_size?: number },
) {
	return apiGet<PaginatedResponse<any>>(`/users/${userId}/comments`, params);
}

// 需要导入apiPost（在文件末尾动态导入避免循环依赖问题）
import { apiPost } from "./client";
