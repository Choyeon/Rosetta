import type { I18nString, PostListItemLocalized } from "./schema-contract";

export interface PostSeriesBase {
	title: I18nString;
	slug?: string | null;
	description?: I18nString | null;
	cover_image?: string | null;
	icon?: string | null;
	color?: string;
	is_active?: boolean;
	order?: number;
}

export type PostSeriesCreate = PostSeriesBase;

export interface PostSeriesUpdate {
	title?: I18nString | null;
	slug?: string | null;
	description?: I18nString | null;
	cover_image?: string | null;
	icon?: string | null;
	color?: string | null;
	is_active?: boolean | null;
	order?: number | null;
}

export interface PostSeriesResponse {
	id: number;
	title: I18nString;
	slug: string;
	description: I18nString | null;
	cover_image: string | null;
	icon: string | null;
	color: string;
	is_active: boolean;
	order: number;
	post_count: number;
	created_at: string;
	updated_at: string;
}

export interface PostSeriesWithPostsResponse extends PostSeriesResponse {
	posts: PostListItemLocalized[];
}
