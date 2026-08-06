import {
	apiDelete,
	apiGet,
	apiPost,
	apiPut,
	type PaginatedResponse,
} from "./client";

export interface Page {
	id: number;
	slug: string;
	title: { [key: string]: string } | string;
	content: { [key: string]: string } | string;
	summary?: string;
	template?: string;
	order: number;
	status?: string;
	is_published?: boolean;
	allow_comments?: boolean;
	meta_title?: string;
	meta_description?: string;
	created_at: string;
	updated_at: string;
	published_at?: string;
	author?: { id: number; username: string; nickname?: string };
}

export interface PageCreate {
	slug: string;
	title: string;
	content: string;
	summary?: string;
	template?: string;
	order?: number;
	is_published?: boolean;
	allow_comments?: boolean;
	meta_title?: string;
	meta_description?: string;
}

export interface PageUpdate extends Partial<PageCreate> {}

export async function getPages(params?: { page?: number; page_size?: number }) {
	return apiGet<PaginatedResponse<Page>>("/pages", params);
}

export async function getPage(slug: string) {
	return apiGet<Page>(`/pages/${slug}`);
}

export async function getPageById(id: number) {
	return apiGet<Page>(`/pages/${id}`);
}

export async function createPage(data: PageCreate) {
	return apiPost<Page>("/pages", data);
}

export async function updatePage(id: number, data: PageUpdate) {
	return apiPut<Page>(`/pages/${id}`, data);
}

export async function deletePage(id: number) {
	return apiDelete(`/pages/${id}`);
}
