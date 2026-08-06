import {
	apiDelete,
	apiGet,
	apiPost,
	apiPut,
	clearAuth,
	setAuthToken,
	setRefreshToken,
} from "./client";

export interface User {
	id: number;
	username: string;
	email: string;
	nickname: string;
	avatar?: string | null;
	bio?: string | null;
	website?: string | null;
	github?: string | null;
	is_active: boolean;
	is_staff: boolean;
	is_superuser: boolean;
	role?: string;
	posts_count?: number;
	created_at: string;
	qq?: string | null;
	avatar_source?: "auto" | "custom" | "github" | "qq" | "gravatar";
	resolved_avatar_url?: string | null;
}

export interface LoginData {
	username: string;
	password: string;
}

export interface RegisterData {
	username: string;
	email: string;
	password: string;
	nickname?: string;
}

export interface AuthResponse {
	access_token: string;
	refresh_token: string;
	token_type: string;
	expires_in: number;
}

export async function login(data: LoginData) {
	// 注意：apiFetch 会通过 camelizeKeys() 将响应的 snake_case 转为 camelCase，
	// 所以后端返回的 { access_token, refresh_token } 实际访问时要用 accessToken / refreshToken
	const res = await apiPost<any>("/users/login", data);
	const access = res.access_token ?? res.accessToken;
	const refresh = res.refresh_token ?? res.refreshToken;
	if (access) setAuthToken(access);
	if (refresh) setRefreshToken(refresh);
	return res;
}

export async function register(data: RegisterData) {
	const res = await apiPost<any>("/users/register", data);
	const access = res.access_token ?? res.accessToken;
	const refresh = res.refresh_token ?? res.refreshToken;
	if (access) setAuthToken(access);
	if (refresh) setRefreshToken(refresh);
	return res;
}

export async function logout() {
	try {
		await apiPost("/users/logout");
	} catch {
		// ignore logout errors
	}
	clearAuth();
}

export async function getCurrentUser() {
	return apiGet<User>("/users/me");
}

export async function updateProfile(data: Partial<User>) {
	return apiPut<User>("/users/me", data);
}

export async function changePassword(data: {
	old_password: string;
	new_password: string;
}) {
	// 后端同时支持两条路径：优先用新版 /users/me/password
	// 同时兼容旧版 /users/me/change-password
	return apiPost("/users/me/change-password", data);
}

export async function getUsers(params?: Record<string, any>) {
	return apiGet<{ items: User[]; total: number }>("/admin/users", params);
}

export async function getUser(id: number) {
	return apiGet<User>(`/admin/users/${id}`);
}

export async function updateUser(id: number, data: Partial<User>) {
	return apiPut<User>(`/admin/users/${id}`, data);
}

export async function deleteUser(id: number) {
	return apiDelete(`/admin/users/${id}`);
}
