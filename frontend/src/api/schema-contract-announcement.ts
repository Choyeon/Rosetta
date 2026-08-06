import type { I18nString } from "./schema-contract";

export type AnnouncementType = "info" | "success" | "warning" | "danger";

export interface AnnouncementBase {
	title: I18nString;
	content?: I18nString | null;
	type?: AnnouncementType;
	is_active?: boolean;
	is_sticky?: boolean;
	show_at?: string | null;
	expire_at?: string | null;
	target_audience?: "all" | "registered" | "staff" | string;
}

export type AnnouncementCreate = AnnouncementBase;

export interface AnnouncementUpdate {
	title?: I18nString | null;
	content?: I18nString | null;
	type?: AnnouncementType | null;
	is_active?: boolean | null;
	is_sticky?: boolean | null;
	show_at?: string | null;
	expire_at?: string | null;
	target_audience?: string | null;
}

export interface AnnouncementResponse {
	id: number;
	title: I18nString;
	content: I18nString | null;
	type: AnnouncementType;
	is_active: boolean;
	is_sticky: boolean;
	show_at: string | null;
	expire_at: string | null;
	target_audience: string;
	created_at: string;
	updated_at: string;
}
