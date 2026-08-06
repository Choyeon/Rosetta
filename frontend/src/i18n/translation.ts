import { derived, type Readable, writable } from "svelte/store";
import { siteConfig } from "../config";
import type I18nKey from "./i18nKey";
import { en } from "./languages/en";
import { ja } from "./languages/ja";
import { zh_CN } from "./languages/zh_CN";
import { zh_TW } from "./languages/zh_TW";

export type Lang = "en" | "ja" | "zh_CN" | "zh_TW";

export const SUPPORTED_LANGS: {
	code: Lang;
	label: string;
	nativeLabel: string;
}[] = [
	{ code: "zh_CN", label: "Chinese (Simplified)", nativeLabel: "简体中文" },
	{ code: "zh_TW", label: "Chinese (Traditional)", nativeLabel: "繁體中文" },
	{ code: "en", label: "English", nativeLabel: "English" },
	{ code: "ja", label: "Japanese", nativeLabel: "日本語" },
];

export type Translation = {
	[K in I18nKey]: string;
};

const defaultTranslation = en;

const map: { [key: string]: Translation } = {
	en: en,
	en_us: en,
	en_gb: en,
	en_au: en,
	zh_cn: zh_CN,
	zh_CN: zh_CN,
	zh_tw: zh_TW,
	zh_TW: zh_TW,
	ja: ja,
	ja_jp: ja,
};

export function getTranslation(lang: string): Translation {
	return map[lang] || map[lang.toLowerCase()] || defaultTranslation;
}

export function detectBrowserLang(): Lang {
	if (typeof navigator === "undefined") return "zh_CN";
	// userLanguage 是 IE 老属性，现代 TS Navigator 类型中不存在，断言兜底
	const userLang = navigator as Navigator & { userLanguage?: string };
	const browserLang = (
		navigator.language ||
		userLang.userLanguage ||
		"zh-CN"
	).toLowerCase();
	if (browserLang.startsWith("zh")) {
		if (
			browserLang === "zh-tw" ||
			browserLang === "zh-hk" ||
			browserLang === "zh-mo"
		) {
			return "zh_TW";
		}
		return "zh_CN";
	}
	if (browserLang.startsWith("ja")) return "ja";
	if (browserLang.startsWith("en")) return "en";
	return "zh_CN";
}

function getInitialLang(): Lang {
	if (typeof localStorage !== "undefined") {
		const savedLang = localStorage.getItem("lang");
		if (savedLang && map[savedLang]) {
			return savedLang as Lang;
		}
	}
	const detected = detectBrowserLang();
	if (typeof localStorage !== "undefined") {
		localStorage.setItem("lang", detected);
	}
	return detected;
}

export const currentLang = writable<Lang>(getInitialLang());

export function setLang(lang: Lang) {
	if (!map[lang]) return;
	currentLang.set(lang);
	if (typeof localStorage !== "undefined") {
		localStorage.setItem("lang", lang);
	}
	// 写入 cookie（path=/ 同源可用）以便 SSR 阶段通过 Vite 代理头传递给后端
	if (typeof document !== "undefined") {
		document.documentElement.setAttribute("data-lang", lang);
		const htmlLang = lang.replace("_", "-");
		document.documentElement.setAttribute("lang", htmlLang);
		// 后端对应的映射：zh_CN→zh, zh_TW→zh_Hant, en→en, ja→ja
		const backendLang =
			lang === "zh_TW" ? "zh_Hant" : lang === "zh_CN" ? "zh" : lang;
		const expires = new Date(
			Date.now() + 365 * 24 * 60 * 60 * 1000,
		).toUTCString();
		document.cookie = `rosetta_lang=${encodeURIComponent(backendLang)}; path=/; expires=${expires}; SameSite=Lax`;

		// 派发全局事件，通知 SSR 渲染的组件（导航、页脚等）同步切换客户端文字
		try {
			const evt = new CustomEvent("rosetta-lang-change", {
				detail: { lang, backendLang },
				bubbles: true,
			});
			window.dispatchEvent(evt);
		} catch (_e) {
			// 旧浏览器兼容失败静默
		}
	}
}

export const t: Readable<Translation> = derived(currentLang, ($lang) =>
	getTranslation($lang),
);

export function getCurrentLang(): string {
	let lang: Lang = siteConfig.lang || "zh_CN";
	if (typeof localStorage !== "undefined") {
		const savedLang = localStorage.getItem("lang");
		if (savedLang) {
			lang = savedLang as Lang;
		}
	}
	return lang;
}

export function i18n(
	key: I18nKey,
	vars?: Record<string, string | number>,
): string {
	const lang = getCurrentLang();
	const currentLangTrans = getTranslation(lang);
	let value = currentLangTrans[key];

	if (!value && lang.toLowerCase() !== "zh_cn" && lang !== "zh_CN") {
		const chineseValue = zh_CN[key];
		if (chineseValue) {
			value = chineseValue;
		}
	}

	if (!value) {
		value = defaultTranslation[key];
	}

	if (vars && value) {
		Object.keys(vars).forEach((k) => {
			value = value.replace(new RegExp(`\\{${k}\\}`, "g"), String(vars[k]));
		});
	}

	return value || key;
}

if (typeof document !== "undefined") {
	const initialLang = getInitialLang();
	document.documentElement.setAttribute("data-lang", initialLang);
	document.documentElement.setAttribute("lang", initialLang.replace("_", "-"));
}
