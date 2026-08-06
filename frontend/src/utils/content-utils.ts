import type { Category as ApiCategory, Tag as ApiTag, Post } from "@api/blog";
import {
	getCategories as apiGetCategories,
	getPosts as apiGetPosts,
	getSimilarPosts as apiGetSimilarPosts,
	getTags as apiGetTags,
} from "@api/blog";
import { getCategoryUrl } from "@utils/url-utils";

// 兼容 Firefly 原有 CollectionEntry<"posts"> 的 data 结构
type PostData = {
	title: string;
	summary?: string;
	description?: string;
	published: Date;
	modified?: Date;
	updated?: Date;
	tags: string[];
	category?: string | null;
	categorySlug?: string | null;
	cover?: {
		src: string;
		alt?: string;
	};
	image?: string;
	author?: string;
	pinned?: boolean;
	draft?: boolean;
	featured?: boolean;
	password?: string | null;
	passwordHint?: string;
	nextSlug?: string;
	nextTitle?: string;
	prevSlug?: string;
	prevTitle?: string;
	readingTime?: number;
	words?: number;
	views?: number;
	likes?: number;
	commentsCount?: number;
	lang?: string;
	sourceLink?: string;
	licenseName?: string;
	licenseUrl?: string;
	comment?: string;
};

type PostEntry = {
	id: string;
	slug: string;
	body: string;
	data: PostData;
	collection: "posts";
};

function convertApiPost(apiPost: any): PostEntry {
	const tags: any[] = apiPost.tags || [];
	// 日期兜底：published_at 或 created_at 为空字符串/非法字符串时，new Date("")
	// 会得到 Invalid Date，后续调用 .toISOString() / .getTime() 会直接抛
	// RangeError: Invalid time value，导致 RSS / sitemap / 构建期遍历失败。
	// 这里集中规范为「有效 Date」，无效时退化到当前时间（保证构建链路不断）。
	const nowFallback = new Date();
	function toValidDate(value: unknown): Date | undefined {
		if (value == null || value === "") return undefined;
		const d = new Date(value as any);
		if (!Number.isNaN(d.getTime())) return d;
		return undefined;
	}
	const publishedDate =
		toValidDate(apiPost.published_at) ??
		toValidDate(apiPost.created_at) ??
		nowFallback;
	const updatedDate =
		toValidDate(apiPost.updated_at) ??
		toValidDate(apiPost.modified_at) ??
		undefined;
	const postId =
		apiPost.id != null
			? String(apiPost.id)
			: `post-${Math.random().toString(36).slice(2, 8)}`;
	// slug 兜底：后端允许 slug=null，但前端大量逻辑依赖 slug 非空构造 URL，
	// 若缺失直接回退到 id 字符串，避免 posts/index 等模板构造链接时 undefined。
	const slug =
		apiPost.slug != null && String(apiPost.slug).trim().length > 0
			? String(apiPost.slug)
			: postId;
	const titleValue =
		apiPost.title != null && String(apiPost.title).trim().length > 0
			? String(apiPost.title)
			: `Untitled Post ${postId}`;
	const summaryValue = apiPost.summary || apiPost.excerpt || "";
	return {
		id: postId,
		slug,
		body: apiPost.content || "",
		collection: "posts",
		data: {
			title: titleValue,
			summary: summaryValue,
			description: summaryValue || titleValue,
			published: publishedDate,
			modified: updatedDate,
			updated: updatedDate,
			tags:
				tags
					.map((t: any) => (typeof t === "string" ? t : t?.name))
					.filter(Boolean) || [],
			category: apiPost.category?.name || null,
			categorySlug:
				apiPost.category?.slug ||
				(apiPost.category?.name
					? encodeURIComponent(apiPost.category.name)
					: null),
			cover: apiPost.cover_image
				? { src: apiPost.cover_image, alt: titleValue }
				: undefined,
			image: apiPost.cover_image || "",
			author: apiPost.author?.nickname || apiPost.author?.username || undefined,
			pinned: apiPost.is_pinned,
			draft:
				apiPost.is_published !== undefined
					? !apiPost.is_published
					: apiPost.status !== "published",
			featured: apiPost.is_featured,
			password: apiPost.password,
			passwordHint: apiPost.password_hint || "",
			readingTime: apiPost.reading_time,
			words: apiPost.word_count,
			views: apiPost.views,
			likes: apiPost.likes ?? apiPost.likes_count,
			commentsCount: apiPost.comments_count,
		},
	};
}

// ===== 缓存层：避免同一次 SSR 渲染中重复请求 =====
const CACHE_TTL_MS = 30_000;
const cache = new Map<string, { value: any; expires: number }>();

function cacheGet<T>(key: string): T | null {
	const entry = cache.get(key);
	if (!entry) return null;
	if (Date.now() > entry.expires) {
		cache.delete(key);
		return null;
	}
	return entry.value as T;
}

function cacheSet(key: string, value: any, ttl = CACHE_TTL_MS) {
	cache.set(key, { value, expires: Date.now() + ttl });
}

async function cachedApiCall<T>(
	cacheKey: string,
	fn: () => Promise<T>,
	ttl = CACHE_TTL_MS,
): Promise<T> {
	const cached = cacheGet<T>(cacheKey);
	if (cached !== null) return cached;
	const result = await fn();
	// 不缓存空数组 / 空字符串 / null / undefined：
	// 这类结果通常是后端短暂不可达或初次启动未就绪的兜底，
	// 如果被缓存 30s，会让用户看到整页空白卡片。
	const isEmpty =
		result == null ||
		(Array.isArray(result) && result.length === 0) ||
		(typeof result === "string" && result.length === 0);
	if (!isEmpty) cacheSet(cacheKey, result, ttl);
	return result;
}

async function getRawSortedPosts(): Promise<PostEntry[]> {
	return cachedApiCall("posts:sorted", async () => {
		try {
			const allPosts: Post[] = [];
			let page = 1;
			const pageSize = 100;

			while (true) {
				const result = await apiGetPosts({
					page,
					page_size: pageSize,
					status: "published",
				});
				const items = result?.items || [];
				allPosts.push(...items);
				if (
					!result ||
					items.length < pageSize ||
					page >= (result?.total_pages || 1)
				)
					break;
				page++;
			}

			const posts = allPosts.map(convertApiPost);
			posts.sort((a, b) => {
				if (a.data.pinned && !b.data.pinned) return -1;
				if (!a.data.pinned && b.data.pinned) return 1;
				return b.data.published.getTime() - a.data.published.getTime();
			});
			return posts;
		} catch (e) {
			console.warn(
				"[content-utils] Failed to fetch posts from API, fallback to empty:",
				e,
			);
			return [];
		}
	});
}

export async function getSortedPosts(): Promise<PostEntry[]> {
	const sorted = await getRawSortedPosts();

	for (let i = 1; i < sorted.length; i++) {
		sorted[i].data.nextSlug = sorted[i - 1].slug;
		sorted[i].data.nextTitle = sorted[i - 1].data.title;
	}
	for (let i = 0; i < sorted.length - 1; i++) {
		sorted[i].data.prevSlug = sorted[i + 1].slug;
		sorted[i].data.prevTitle = sorted[i + 1].data.title;
	}

	return sorted;
}

export type PostForList = {
	id: string;
	slug: string;
	data: PostData;
};

export async function getSortedPostsList(): Promise<PostForList[]> {
	const sorted = await getRawSortedPosts();
	return sorted.map((p) => ({ id: p.slug, slug: p.slug, data: p.data }));
}

export type Tag = {
	name: string;
	slug?: string;
	color?: string;
	icon?: string | null;
	count: number;
};

export async function getTagList(): Promise<Tag[]> {
	return cachedApiCall("tags:list", async () => {
		try {
			const tags = await apiGetTags();
			return (tags || [])
				.map((t: ApiTag) => ({
					name: t.name,
					slug: t.slug,
					color: t.color,
					icon: t.icon ?? null,
					count:
						(t as unknown as { post_count?: number; postCount?: number })
							.post_count ??
						(t as unknown as { post_count?: number; postCount?: number })
							.postCount ??
						0,
				}))
				.sort((a, b) =>
					a.name.toLowerCase().localeCompare(b.name.toLowerCase()),
				);
		} catch (e) {
			console.warn("[content-utils] Failed to fetch tags:", e);
			return [];
		}
	});
}

export type Category = {
	name: string;
	slug?: string;
	color?: string;
	icon?: string | null;
	count: number;
	url: string;
};

export async function getCategoryList(): Promise<Category[]> {
	return cachedApiCall("categories:list", async () => {
		try {
			const cats = await apiGetCategories();
			return (cats || [])
				.map((c: ApiCategory) => ({
					name: c.name,
					slug: c.slug,
					color: c.color,
					icon: c.icon ?? null,
					count:
						(c as unknown as { post_count?: number; postCount?: number })
							.post_count ??
						(c as unknown as { post_count?: number; postCount?: number })
							.postCount ??
						0,
					// 使用 name 生成 URL，与 PostMeta / posts/index 保持一致
					// 这样 ?category= 参数就是 name，与 data-category 中的值匹配
					url: getCategoryUrl(c.name),
				}))
				.sort(
					(a, b) =>
						b.count - a.count ||
						a.name.toLowerCase().localeCompare(b.name.toLowerCase()),
				);
		} catch (e) {
			console.warn("[content-utils] Failed to fetch categories:", e);
			return [];
		}
	});
}

function tokenizeTitle(title: string): Set<string> {
	const tokens = new Set<string>();
	const segmenter = new Intl.Segmenter("zh", { granularity: "word" });
	for (const { segment, isWordLike } of segmenter.segment(title)) {
		if (!isWordLike) continue;
		tokens.add(segment.toLowerCase());
	}
	return tokens;
}

function jaccardSimilarity(a: Set<string>, b: Set<string>): number {
	if (a.size === 0 && b.size === 0) return 0;
	let intersection = 0;
	for (const item of a) {
		if (b.has(item)) intersection++;
	}
	const union = a.size + b.size - intersection;
	return union === 0 ? 0 : intersection / union;
}

export async function getRelatedPosts(
	currentPost: PostEntry,
	maxCount = 5,
): Promise<PostForList[]> {
	try {
		const postId = Number(currentPost.id);
		if (!Number.isNaN(postId) && postId > 0) {
			const related = await apiGetSimilarPosts(postId, maxCount);
			if (related && related.length > 0) {
				return related.map((p: Post) => ({
					id: p.slug,
					slug: p.slug,
					data: convertApiPost(p).data,
				}));
			}
		}

		const all = await getRawSortedPosts();
		const currentTokens = tokenizeTitle(currentPost.data.title);
		const currentCategory = currentPost.data.category;

		const scored = all
			.filter((p) => p.slug !== currentPost.slug)
			.map((p) => {
				let score = 0;
				const titleTokens = tokenizeTitle(p.data.title);
				score += jaccardSimilarity(currentTokens, titleTokens) * 0.6;
				if (currentCategory && p.data.category === currentCategory)
					score += 0.3;
				const daysDiff =
					Math.abs(
						p.data.published.getTime() - currentPost.data.published.getTime(),
					) / 86400000;
				score += Math.max(0, 1 - daysDiff / 365) * 0.1;
				return { post: p, score };
			})
			.sort((a, b) => b.score - a.score)
			.slice(0, maxCount);

		return scored.map((s) => ({
			id: s.post.slug,
			slug: s.post.slug,
			data: s.post.data,
		}));
	} catch (e) {
		console.warn("[content-utils] Failed to fetch related posts:", e);
		return [];
	}
}

export type { PostEntry as CollectionEntryPost };
