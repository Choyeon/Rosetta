import {
	apiDelete,
	apiGet,
	apiPost,
	apiPut,
	type PaginatedResponse,
} from "./client";

export interface Post {
	id: number;
	slug: string;
	title: string;
	summary: string;
	subtitle?: string | null;
	content: string;
	category?: { id: number; name: string; slug: string } | null;
	tags: { id: number; name: string; slug: string }[];
	cover_image?: string | null;
	author?: {
		id: number;
		username: string;
		nickname?: string;
		avatar?: string;
		bio?: string;
	} | null;
	views: number;
	likes: number;
	likes_count: number;
	comments_count: number;
	word_count: number;
	reading_time: number;
	status: "published" | "draft" | "scheduled";
	is_published: boolean;
	is_pinned: boolean;
	is_featured: boolean;
	password?: string | null;
	source?: string;
	source_url?: string;
	created_at: string;
	updated_at: string;
	published_at: string;
	allow_comments: boolean;
	is_password_protected?: boolean;
}

export interface PostListQuery {
	page?: number;
	page_size?: number;
	category?: string;
	tag?: string;
	search?: string;
	status?: "published" | "draft" | "scheduled" | "all";
	lang?: string;
}

// 前台API
export async function getPosts(params?: PostListQuery) {
	return apiGet<PaginatedResponse<Post>>("/blog/posts", params);
}

export async function getRecommendedPosts(params?: PostListQuery) {
	return apiGet<PaginatedResponse<Post>>("/blog/posts/recommended", params);
}

export async function getPostBySlug(slug: string, lang?: string) {
	return apiGet<Post>(`/blog/posts/${slug}`, { lang });
}

export async function getPostById(id: number, lang?: string) {
	return apiGet<Post>(`/blog/posts/id/${id}`, { lang });
}

export async function getPostForEdit(id: number) {
	return apiGet<Post>(`/blog/posts/${id}`);
}

export async function getSimilarPosts(
	postId: number,
	limit = 5,
	lang?: string,
) {
	return apiGet<Post[]>(`/blog/posts/${postId}/similar`, { limit, lang });
}

export async function likePost(postId: number) {
	return apiPost(`/blog/posts/${postId}/like`);
}

// 管理员API
export interface PostCreate {
	title: string;
	slug?: string;
	summary?: string;
	subtitle?: string;
	content: string;
	category_id?: number | null;
	tag_ids?: number[];
	cover_image?: string | null;
	status?: "draft" | "published" | "scheduled";
	is_pinned?: boolean;
	is_featured?: boolean;
	allow_comments?: boolean;
	password?: string | null;
	source?: string;
	source_url?: string;
	published_at?: string;
	lang?: string;
}

export interface PostUpdate extends Partial<PostCreate> {}

export async function createPost(data: PostCreate, lang?: string) {
	return apiPost<Post>("/blog/posts", data, { lang });
}

export async function updatePost(id: number, data: PostUpdate, lang?: string) {
	return apiPut<Post>(`/blog/posts/${id}`, data, { lang });
}

export async function deletePost(id: number) {
	return apiDelete(`/blog/posts/${id}`);
}

// 分类
export interface Category {
	id: number;
	name: string;
	slug: string;
	description?: string;
	icon?: string;
	color?: string;
	cover_image?: string;
	post_count: number;
	parent_id?: number | null;
	created_at: string;
}

export interface CategoryCreate {
	name: string;
	slug?: string;
	description?: string;
	icon?: string;
	color?: string;
	cover_image?: string;
	parent_id?: number | null;
	lang?: string;
}

export interface CategoryUpdate extends Partial<CategoryCreate> {}

export async function getCategories(lang?: string) {
	return apiGet<Category[]>("/blog/categories", { lang });
}

export async function getCategoryBySlug(slug: string, lang?: string) {
	return apiGet<Category>(`/blog/categories/slug/${slug}`, { lang });
}

export async function createCategory(data: CategoryCreate, lang?: string) {
	return apiPost<Category>("/blog/categories", data, { lang });
}

export async function updateCategory(
	id: number,
	data: CategoryUpdate,
	lang?: string,
) {
	return apiPut<Category>(`/blog/categories/${id}`, data, { lang });
}

export async function deleteCategory(id: number) {
	return apiDelete(`/blog/categories/${id}`);
}

// 标签
export interface Tag {
	id: number;
	name: string;
	slug: string;
	color?: string;
	icon?: string;
	is_active: boolean;
	post_count: number;
	created_at: string;
}

export interface TagCreate {
	name: string;
	slug?: string;
	color?: string;
	icon?: string;
	is_active?: boolean;
	lang?: string;
}

export interface TagUpdate extends Partial<TagCreate> {}

export async function getTags(lang?: string) {
	return apiGet<Tag[]>("/blog/tags", { lang });
}

export async function getTagBySlug(slug: string, lang?: string) {
	return apiGet<Tag>(`/blog/tags/slug/${slug}`, { lang });
}

export async function createTag(data: TagCreate, lang?: string) {
	return apiPost<Tag>("/blog/tags", data, { lang });
}

export async function updateTag(id: number, data: TagUpdate, lang?: string) {
	return apiPut<Tag>(`/blog/tags/${id}`, data, { lang });
}

export async function deleteTag(id: number) {
	return apiDelete(`/blog/tags/${id}`);
}

// 评论
export interface Comment {
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
	replies?: Comment[];
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

export interface CommentQuery {
	post_id?: number;
	page?: number;
	page_size?: number;
	parent_only?: boolean;
}

export async function getComments(postId: number) {
	return apiGet<Comment[]>(`/blog/posts/${postId}/comments`);
}

// 归档
export interface ArchiveMonthData {
	year: number;
	month: number;
	count: number;
	posts: Post[];
}

export interface ArchiveStats {
	total_posts: number;
	total_years: number;
	years: number[];
	year_stats: Record<string, number>;
}

export async function getArchive(limitPerMonth = 50, lang?: string) {
	return apiGet<ArchiveMonthData[]>("/blog/archive", {
		limit_per_month: limitPerMonth,
		lang,
	});
}

export async function getArchiveStats() {
	return apiGet<ArchiveStats>("/blog/archive/stats");
}

// 站点统计
export interface SiteStats {
	totalWords: number;
	totalPosts: number;
	totalCategories: number;
	totalTags: number;
}

export async function getSiteStats() {
	return apiGet<SiteStats>("/blog/site-stats");
}

export async function getArchiveByYear(year: number, lang?: string) {
	return apiGet<ArchiveMonthData[]>(`/blog/archive/${year}`, { lang });
}

export async function getArchiveByMonth(
	year: number,
	month: number,
	page = 1,
	page_size = 20,
	lang?: string,
) {
	return apiGet(`/blog/archive/${year}/${month}`, { page, page_size, lang });
}

// 我的内容
export async function getMyPosts(params?: {
	page?: number;
	page_size?: number;
	lang?: string;
}) {
	return apiGet<PaginatedResponse<Post>>("/blog/users/me/posts", params);
}

export async function getMyComments(params?: {
	page?: number;
	page_size?: number;
	lang?: string;
}) {
	return apiGet<PaginatedResponse<Comment>>("/blog/users/me/comments", params);
}

export async function getMyLikes(params?: {
	page?: number;
	page_size?: number;
	lang?: string;
}) {
	return apiGet<PaginatedResponse<Post>>("/blog/users/me/likes", params);
}

export async function getMyStats() {
	return apiGet<{ posts: number; comments: number; likes: number }>(
		"/blog/users/me/stats",
	);
}

export async function getMyHistory(params?: {
	page?: number;
	page_size?: number;
	lang?: string;
}) {
	return apiGet<PaginatedResponse<Post>>("/blog/users/me/history", params);
}

export async function clearMyHistory() {
	return apiDelete("/blog/users/me/history");
}
