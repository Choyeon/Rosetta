export interface HeroSlideBase {
	title: string;
	subtitle?: string | null;
	description?: string | null;
	image?: string | null;
	background_image?: string | null;
	cta_text?: string | null;
	cta_url?: string | null;
	gradient?: string | null;
	order?: number;
	is_active?: boolean;
	target_blank?: boolean;
}

export type HeroSlideCreate = HeroSlideBase;

export interface HeroSlideUpdate {
	title?: string | null;
	subtitle?: string | null;
	description?: string | null;
	image?: string | null;
	background_image?: string | null;
	cta_text?: string | null;
	cta_url?: string | null;
	gradient?: string | null;
	order?: number | null;
	is_active?: boolean | null;
	target_blank?: boolean | null;
}

export interface HeroSlideResponse {
	id: number;
	title: string;
	subtitle: string | null;
	description: string | null;
	image: string | null;
	background_image: string | null;
	cta_text: string | null;
	cta_url: string | null;
	gradient: string | null;
	order: number;
	is_active: boolean;
	target_blank: boolean;
	created_at: string;
	updated_at: string;
}
