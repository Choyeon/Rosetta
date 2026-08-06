import type { I18nString } from "./schema-contract";

export type ActivityType =
	| "post_create"
	| "post_update"
	| "post_publish"
	| "comment_create"
	| "guestbook_create"
	| "user_register"
	| "user_login"
	| "like"
	| "dynamic_create"
	| string;

export interface ActivityBase {
	type: ActivityType;
	user_id?: number | null;
	target_type?: string | null;
	target_id?: number | string | null;
	title: I18nString | string;
	content?: I18nString | string | null;
	metadata?: Record<string, any> | null;
	is_public?: boolean;
}

export type ActivityCreate = ActivityBase;

export interface ActivityUpdate {
	type?: ActivityType | null;
	title?: I18nString | string | null;
	content?: I18nString | string | null;
	metadata?: Record<string, any> | null;
	is_public?: boolean | null;
}

export interface ActivityResponse {
	id: number;
	type: ActivityType;
	user_id: number | null;
	target_type: string | null;
	target_id: number | string | null;
	title: I18nString;
	content: I18nString | null;
	metadata: Record<string, any> | null;
	is_public: boolean;
	created_at: string;
	updated_at: string;
}

export interface ActivityLocalizedResponse {
	id: number;
	type: ActivityType;
	user_id: number | null;
	target_type: string | null;
	target_id: number | string | null;
	title: string;
	content: string | null;
	metadata: Record<string, any> | null;
	is_public: boolean;
	created_at: string;
	updated_at: string;
}
