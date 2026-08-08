import {
	type NavBarConfig,
	type NavBarLink,
	type NavBarSearchConfig,
	NavBarSearchMethod,
} from "../types/navBarConfig";
import type { CanonicalI18nTitles } from "../i18n/translation";
import Key from "../i18n/i18nKey";
import { zh_CN } from "../i18n/languages/zh_CN";
import { zh_TW } from "../i18n/languages/zh_TW";
import { en } from "../i18n/languages/en";
import { ja } from "../i18n/languages/ja";
import type I18nKey from "../i18n/i18nKey";

/**
 * 构造导航项的 4 语言 i18n_titles 字典（纯字面量构造，避免模块顶层触发跨模块函数调用）。
 *  - i18n Key：按 key 直接从四种语言表中取值
 *  - 字面量对象：直接把 zh / zh_Hant / en / ja 写入
 *
 *  注意：这里不使用 translation.ts 里的 buildI18nTitlesForKey，
 *  避免 navBarConfig 模块顶层触发 translation.ts 的 import，
 *  导致 Vite SSR 的 TDZ（Cannot access '__vite_ssr_import_*__' before initialization）。
 */
const makeTitles = (
	spec: I18nKey | { zh: string; zh_Hant: string; en: string; ja: string },
): CanonicalI18nTitles => {
	if (typeof spec === "string") {
		const k = spec;
		return {
			zh: (zh_CN as Record<string, string>)[k] || k,
			zh_Hant: (zh_TW as Record<string, string>)[k] || k,
			en: (en as Record<string, string>)[k] || k,
			ja: (ja as Record<string, string>)[k] || k,
		};
	}
	return {
		zh: spec.zh,
		zh_Hant: spec.zh_Hant,
		en: spec.en,
		ja: spec.ja,
	};
};

// ============================================================================
// 导航栏配置 - 根据顺序动态生成导航栏链接
// NavBar Configuration - Dynamically generate navigation bar links based on order
// ============================================================================
const getDynamicNavBarConfig = (): NavBarConfig => {
	// 基础导航栏链接
	const links: NavBarLink[] = [];

	// 主页
	links.push(LinkPresets.Home);

	// 文章及其子菜单
	links.push({
		name: zh_CN[Key.posts],
		url: "#",
		icon: "material-symbols:article",
		i18n_titles: makeTitles(Key.posts),
		children: [
			// 归档
			LinkPresets.Archive,

			// 分类
			LinkPresets.Categories,

			// 标签
			LinkPresets.Tags,
		],
	});

	//社交及其子菜单
	links.push({
		name: zh_CN[Key.social],
		url: "#",
		icon: "material-symbols:group",
		i18n_titles: makeTitles(Key.social),
		children: [
			// 友链
			LinkPresets.Friends,

			// 留言
			LinkPresets.Guestbook,
		],
	});

	// 我的及其子菜单
	links.push({
		name: zh_CN[Key.mine],
		url: "#",
		icon: "material-symbols:person",
		i18n_titles: makeTitles(Key.mine),
		children: [
			// 动态
			LinkPresets.Dynamic,

			// 相册
			LinkPresets.Gallery,

			// 后台管理
			LinkPresets.Admin,
		],
	});

	// 关于及其子菜单
	links.push({
		name: zh_CN[Key.about],
		url: "#",
		icon: "material-symbols:info",
		i18n_titles: makeTitles(Key.about),
		children: [
			// 打赏
			LinkPresets.Sponsor,

			// 关于页面
			LinkPresets.About,
		],
	});

	return { links } as NavBarConfig;
};

// 导航搜索配置
export const navBarSearchConfig: NavBarSearchConfig = {
	method: NavBarSearchMethod.PageFind,
};

// ============================================================================
// 链接预设 - 可自由自定义导航栏链接的名称、图标和URL
// Link Presets - Allows free customization of the name, icon, and URL of navigation bar links
// ============================================================================
export const LinkPresets: Record<string, NavBarLink> = {
	Home: {
		name: zh_CN[Key.home],
		url: "/",
		icon: "material-symbols:home",
		i18n_titles: makeTitles(Key.home),
	},
	Dynamic: {
		name: zh_CN[Key.dynamic],
		url: "/dynamic/",
		icon: "material-symbols:forum-rounded",
		pageKey: "dynamic",
		i18n_titles: makeTitles(Key.dynamic),
	},
	Archive: {
		name: zh_CN[Key.archive],
		url: "/archive/",
		icon: "material-symbols:archive",
		i18n_titles: makeTitles(Key.archive),
	},
	Categories: {
		name: zh_CN[Key.categories],
		url: "/categories/",
		icon: "material-symbols:folder-open-rounded",
		i18n_titles: makeTitles(Key.categories),
	},
	Tags: {
		name: zh_CN[Key.tags],
		url: "/tags/",
		icon: "material-symbols:tag-rounded",
		i18n_titles: makeTitles(Key.tags),
	},
	Friends: {
		name: "友链",
		url: "/friends/",
		icon: "material-symbols:link-2-rounded",
		pageKey: "friends",
		i18n_titles: makeTitles({
			zh: "友链",
			zh_Hant: "友鏈",
			en: "Friends",
			ja: "フレンド",
		}),
	},
	Sponsor: {
		name: zh_CN[Key.sponsor] ?? "打赏",
		url: "/sponsor/",
		icon: "material-symbols:favorite",
		pageKey: "sponsor",
		i18n_titles: makeTitles({
			zh: "打赏",
			zh_Hant: "贊助",
			en: "Sponsor",
			ja: "スポンサー",
		}),
	},
	Guestbook: {
		name: "留言",
		url: "/guestbook/",
		icon: "material-symbols:chat",
		pageKey: "guestbook",
		i18n_titles: makeTitles({
			zh: "留言",
			zh_Hant: "留言",
			en: "Guestbook",
			ja: "メッセージ",
		}),
	},
	About: {
		name: zh_CN[Key.about],
		url: "/about/",
		icon: "material-symbols:person",
		i18n_titles: makeTitles(Key.about),
	},
	Bangumi: {
		name: "番组计划",
		url: "/bangumi/",
		icon: "material-symbols:movie",
		pageKey: "bangumi",
		i18n_titles: makeTitles({
			zh: "番组计划",
			zh_Hant: "番組計劃",
			en: "Bangumi",
			ja: "番組計画",
		}),
	},
	Gallery: {
		name: "相册",
		url: "/gallery/",
		icon: "material-symbols:photo-library",
		pageKey: "gallery",
		i18n_titles: makeTitles({
			zh: "相册",
			zh_Hant: "相簿",
			en: "Gallery",
			ja: "ギャラリー",
		}),
	},
	Anime: {
		name: "追番",
		url: "/anime/",
		icon: "material-symbols:live-tv",
		pageKey: "anime",
		i18n_titles: makeTitles({
			zh: "追番",
			zh_Hant: "追番",
			en: "Anime",
			ja: "アニメ",
		}),
	},
	Admin: {
		name: "后台管理",
		url: "/admin/",
		icon: "material-symbols:dashboard",
		i18n_titles: makeTitles({
			zh: "后台管理",
			zh_Hant: "後台管理",
			en: "Admin",
			ja: "管理画面",
		}),
	},
};

export const navBarConfig: NavBarConfig = getDynamicNavBarConfig();
