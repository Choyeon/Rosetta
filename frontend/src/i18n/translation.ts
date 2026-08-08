import { derived, type Readable, writable } from "svelte/store";
import { siteConfig } from "../config";
import I18nKey from "./i18nKey";
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

/**
 * 把「前端 Lang code / 后端 cookie 值 / data-lang 属性」统一归一成前端 Lang 枚举。
 * 当输入非法时，用 fallback（默认 zh_CN）兜底，避免 setLang() 直接 return 导致
 * 语言状态分裂。
 */
export function normalizeLangOrFallback(
	raw: Lang | string | undefined | null,
	fallback: Lang = "zh_CN",
): Lang {
	if (!raw) return fallback;
	if (typeof raw !== "string") return fallback;
	if (raw === "zh_CN" || raw === "zh_TW" || raw === "en" || raw === "ja") return raw;
	const lower = raw.toLowerCase().replace(/-/g, "_");
	if (lower === "zh" || lower === "zh_cn" || lower === "zh_hans" || lower === "zh_sg")
		return "zh_CN";
	if (
		lower === "zh_hant" ||
		lower === "zh_tw" ||
		lower === "zh_hk" ||
		lower === "zh_mo"
	)
		return "zh_TW";
	if (lower.startsWith("en")) return "en";
	if (lower.startsWith("ja")) return "ja";
	return fallback;
}

/**
 * i18n 文案与后端（以及 data-i18n-titles 属性）的 4 语言 key 映射：
 * zh / zh_CN / zh-Hans         → 简体中文
 * zh_Hant / zh_TW / zh-Hant-TW → 繁體中文
 * en / en_US                   → English
 * ja / ja_JP                   → 日本語
 *
 * getDisplayTitle() 优先匹配精确 key，其次匹配变体前缀，最后回退到 zh。
 * 所有 SSR 阶段输出的导航项 i18n_titles 字典统一使用这 4 个 key。
 */
export const CANONICAL_I18N_TITLE_KEYS = {
	zh: "zh",
	zh_Hant: "zh_Hant",
	en: "en",
	ja: "ja",
} as const;

export type CanonicalI18nTitles = Partial<
	Record<(typeof CANONICAL_I18N_TITLE_KEYS)[keyof typeof CANONICAL_I18N_TITLE_KEYS], string>
>;

/**
 * 把 i18n Key（posts / social / mine / home / ...）构造成 SSR 用的 i18n_titles 字典。
 * 这样即使后端导航接口失败（降级到 navBarConfig 静态配置），
 * 下拉菜单和顶栏依然可以渲染完整的 data-i18n-titles 属性，
 * 保证语言切换 + Swup 跳页后导航文字动态生效。
 */
export function buildI18nTitlesForKey(key: I18nKey): CanonicalI18nTitles {
	return {
		zh: zh_CN[key] || key,
		zh_Hant: zh_TW[key] || key,
		en: en[key] || key,
		ja: ja[key] || key,
	};
}

/**
 * 前端「当前用户语言」转换为「后端 / data-i18n-titles 语言 key」
 * zh_CN → zh，zh_TW → zh_Hant，en → en，ja → ja
 */
export function toBackendLang(frontLang: Lang | string): string {
	switch (frontLang) {
		case "zh_CN":
		case "zh":
		case "zh-Hans":
		case "zh-CN":
			return "zh";
		case "zh_TW":
		case "zh_Hant":
		case "zh-Hant":
		case "zh-TW":
			return "zh_Hant";
		case "en":
		case "en_US":
			return "en";
		case "ja":
		case "ja_JP":
			return "ja";
		default:
			return "zh";
	}
}

/**
 * 从后端 / SSR 的 data-i18n-titles 中匹配到对应语言的展示文案。
 *
 * langHint 来源：
 *  - rosetta-lang-change 事件的 detail.backendLang
 *  - <html data-lang=""> / localStorage.lang → 转成 toBackendLang()
 *  - 后端写死的 navBarConfig.i18n_titles 对象 key
 *
 * 回退顺序：精确命中 → 前缀命中（zh_Hant_TW → zh_Hant；zh_CN → zh；en_US → en）→ zh → 取第一个非空值。
 */
export function getDisplayTitle(
	titles: Record<string, string> | string | undefined | null,
	langHint: Lang | string,
): string {
	if (!titles) return "";
	if (typeof titles === "string") return titles;

	const direct = toBackendLang(langHint);
	if (titles[direct]) return titles[direct];

	// 前缀兜底（zh_CN / zh-Hans 统一匹配到 zh；zh_Hant_TW 匹配到 zh_Hant；en-US 匹配到 en）
	const keys = Object.keys(titles);
	const lowerHint = String(langHint || "").toLowerCase().replace(/-|_/g, "");
	for (const k of keys) {
		const normK = k.toLowerCase().replace(/-|_/g, "");
		if (normK === lowerHint) return titles[k];
	}
	if (lowerHint.startsWith("zhhant")) {
		const hit = keys.find(
			(k) => k.toLowerCase().includes("hant") || /zh[-_ ]?tw/i.test(k),
		);
		if (hit && titles[hit]) return titles[hit];
	}
	if (lowerHint.startsWith("zh")) {
		const hit = keys.find(
			(k) => k === "zh" || /zh[-_ ]?cn/i.test(k) || k === "zh_CN",
		);
		if (hit && titles[hit]) return titles[hit];
	}
	if (lowerHint.startsWith("en")) {
		const hit = keys.find((k) => k === "en" || /^en/i.test(k));
		if (hit && titles[hit]) return titles[hit];
	}
	if (lowerHint.startsWith("ja")) {
		const hit = keys.find((k) => k === "ja" || /^ja/i.test(k));
		if (hit && titles[hit]) return titles[hit];
	}

	// 再退 zh 或第一个值
	if (titles.zh) return titles.zh;
	const first = keys.find((k) => titles[k]);
	return first ? titles[first] : "";
}

/**
 * 通过 data-i18n-aria-key / data-i18n-text-key / data-i18n-alt-key /
 * data-i18n-title-key 在 SSR 组件上声明要替换的 i18n Key，
 * 客户端 applyI18nTitlesAnywhere() 统一用这个翻译，避免各种属性写死英文。
 *
 * 节点属性：
 *  - data-i18n-text-key = "displaySettings | search | ..."   → 同步 textContent + aria-label（若有）
 *  - data-i18n-aria-key = "..."                              → 只同步 aria-label（比如纯图标按钮）
 *  - data-i18n-alt-key = "..."                               → 只同步 alt（比如图片替代文本）
 *  - data-i18n-title-key = "..."                             → 只同步 title（悬停提示）
 *  - data-i18n-titles = "{ \"zh\":\"...\", ... }"            → 导航多语言字典（和历史机制保持兼容）
 */
export function applyI18nTitlesAnywhere(langHint?: Lang | string) {
	if (typeof document === "undefined") return;
	const safeHint =
		langHint ||
		(typeof localStorage !== "undefined"
			? (localStorage.getItem("lang") as Lang | null)
			: null) ||
		document.documentElement.getAttribute("data-lang") ||
		siteConfig.lang ||
		"zh_CN";

	const titlesNodes = document.querySelectorAll<HTMLElement>(
		".i18n-nav-title[data-i18n-titles], [data-i18n-titles]",
	);
	titlesNodes.forEach((el) => {
		const raw = el.getAttribute("data-i18n-titles");
		if (!raw) return;
		try {
			const decoded = raw
				.replace(/&quot;/g, '"')
				.replace(/&#39;/g, "'")
				.replace(/&amp;/g, "&")
				.replace(/&lt;/g, "<")
				.replace(/&gt;/g, ">");
			const titles = JSON.parse(decoded) as Record<string, string> | string;
			const text = getDisplayTitle(titles, safeHint);
			if (text) {
				el.textContent = text;
				if (el.hasAttribute("aria-label")) {
					el.setAttribute("aria-label", text);
				}
			}
		} catch (_e) {
			/* ignore invalid JSON */
		}
	});

	type AttrSpec =
		| "data-i18n-text-key"
		| "data-i18n-aria-key"
		| "data-i18n-alt-key"
		| "data-i18n-title-key";
	const applyNodeI18nKey = (attr: AttrSpec) => {
		document.querySelectorAll<HTMLElement>(`[${attr}]`).forEach((el) => {
			const raw = el.getAttribute(attr) as I18nKey | null;
			if (!raw) return;
			const text = i18n(raw);
			if (!text) return;
			if (attr === "data-i18n-text-key") {
				el.textContent = text;
				if (el.hasAttribute("aria-label")) el.setAttribute("aria-label", text);
			} else if (attr === "data-i18n-aria-key") {
				el.setAttribute("aria-label", text);
			} else if (attr === "data-i18n-alt-key") {
				el.setAttribute("alt", text);
			} else if (attr === "data-i18n-title-key") {
				el.setAttribute("title", text);
			}
		});
	};
	applyNodeI18nKey("data-i18n-text-key");
	applyNodeI18nKey("data-i18n-aria-key");
	applyNodeI18nKey("data-i18n-alt-key");
	applyNodeI18nKey("data-i18n-title-key");

	// WidgetLayout 展开/收起按钮：data-i18n-more-key / data-i18n-less-key 声明 i18n key，
	// 切语言后更新 data-show-more / data-show-less、toggle-text、title、aria-label 四个展示位，
	// 保证按钮脚本（读 data-show-more / data-show-less）下次切换时用的是新语言文案。
	const expandBtns = document.querySelectorAll<HTMLElement>(
		"widget-layout .expand-btn button[data-i18n-more-key]",
	);
	expandBtns.forEach((btn) => {
		const moreKey = btn.getAttribute("data-i18n-more-key") as I18nKey | null;
		const lessKey = btn.getAttribute("data-i18n-less-key") as I18nKey | null;
		const moreText = moreKey ? i18n(moreKey) : "";
		const lessText = lessKey ? i18n(lessKey) : "";
		if (moreText) btn.setAttribute("data-show-more", moreText);
		if (lessText) btn.setAttribute("data-show-less", lessText);
		const expanded = btn.getAttribute("data-expanded") === "true";
		const label = expanded ? lessText || moreText : moreText || lessText;
		if (label) {
			btn.setAttribute("title", label);
			btn.setAttribute("aria-label", label);
			const text = btn.querySelector<HTMLElement>(".toggle-text");
			if (text) text.textContent = label;
		}
	});

	// 音乐播放器：切语言后覆盖 cfg.i18n（保证后续 play/pause 脚本取到新语言文案）
	// 并单独刷新播放按钮的 title/aria-label（根据当前是否正在播放决定用 play 还是 pause 文案）。
	const musicWidgets = document.querySelectorAll<
		HTMLElement & { __musicCfg?: { i18n: Record<string, string> } }
	>(".music-player-widget");
	musicWidgets.forEach((widget) => {
		const cfg = widget.__musicCfg;
		if (cfg && cfg.i18n) {
			cfg.i18n.noPlaying = i18n(I18nKey.musicNoPlaying) || cfg.i18n.noPlaying;
			cfg.i18n.lyrics = i18n(I18nKey.musicLyrics) || cfg.i18n.lyrics;
			cfg.i18n.noLyrics = i18n(I18nKey.musicNoLyrics) || cfg.i18n.noLyrics;
			cfg.i18n.loadingLyrics =
				i18n(I18nKey.musicLoadingLyrics) || cfg.i18n.loadingLyrics;
			cfg.i18n.failedLyrics =
				i18n(I18nKey.musicFailedLyrics) || cfg.i18n.failedLyrics;
			cfg.i18n.noSongs = i18n(I18nKey.musicNoSongs) || cfg.i18n.noSongs;
			cfg.i18n.error = i18n(I18nKey.musicError) || cfg.i18n.error;
			cfg.i18n.play = i18n(I18nKey.musicPlay) || cfg.i18n.play;
			cfg.i18n.pause = i18n(I18nKey.musicPause) || cfg.i18n.pause;
			cfg.i18n.noCover = i18n(I18nKey.musicNoCover) || cfg.i18n.noCover;
			cfg.i18n.music = i18n(I18nKey.music) || cfg.i18n.music;
		}
		// 刷新播放按钮 title / aria-label
		const playBtn = widget.querySelector<HTMLElement>(".btn-play");
		if (playBtn) {
			const isPlaying =
				playBtn.querySelector(".icon-pause") &&
				!playBtn.querySelector(".icon-pause")?.classList.contains("hidden");
			const playText = i18n(I18nKey.musicPlay);
			const pauseText = i18n(I18nKey.musicPause);
			const label = isPlaying ? pauseText || playText : playText || pauseText;
			if (label) {
				playBtn.setAttribute("title", label);
				playBtn.setAttribute("aria-label", label);
			}
		}
	});

	// 背景视频播放按钮：SSR 声明 data-i18n-text-key-play / data-i18n-text-key-pause，
	// 语言切换 / Swup 导航后同步刷新 data-i18n-play / data-i18n-pause / aria-label 三个属性，
	// 保证 Navbar 里的 bg-player-state-change 监听器（读属性）取到目标语言的最新文案。
	const bgBtns = document.querySelectorAll<HTMLElement>(
		"#bg-player-toggle[data-i18n-text-key-play], [data-i18n-text-key-play]",
	);
	bgBtns.forEach((btn) => {
		const playKey = btn.getAttribute("data-i18n-text-key-play") as I18nKey | null;
		const pauseKey = btn.getAttribute("data-i18n-text-key-pause") as I18nKey | null;
		const playText = playKey ? i18n(playKey) : "";
		const pauseText = pauseKey ? i18n(pauseKey) : "";
		if (playText) btn.setAttribute("data-i18n-play", playText);
		if (pauseText) btn.setAttribute("data-i18n-pause", pauseText);
		// aria-label 用当前是否在播放决定 → 默认播放（未播放）→ playText
		const isPlaying = document.documentElement.hasAttribute("data-bg-video-playing");
		const label = isPlaying
			? pauseText || playText
			: playText || pauseText;
		if (label) btn.setAttribute("aria-label", label);
	});

	// 站点信息折叠按钮：把新语言的展开/收起文案覆写到 data 属性上，并刷新按钮可见文本。
	document
		.querySelectorAll<HTMLElement>("site-info-collapse[data-i18n-expand-key][data-i18n-collapse-key]")
		.forEach((el) => {
			const expandKey = el.getAttribute("data-i18n-expand-key") as I18nKey | null;
			const collapseKey = el.getAttribute("data-i18n-collapse-key") as I18nKey | null;
			const expandText = expandKey ? i18n(expandKey) : "";
			const collapseText = collapseKey ? i18n(collapseKey) : "";
			if (expandText) el.setAttribute("data-expand-text", expandText);
			if (collapseText) el.setAttribute("data-collapse-text", collapseText);
			// site-info-collapse 自定义元素会把按钮文案存在 DOM 属性并在点击时读取；
			// 这里直接尝试刷新按钮 text，保证切语言后按钮可见文本立刻变化。
			const btn = el.querySelector<HTMLElement>(":scope > button");
			if (btn) {
				const isCollapsed =
					el.getAttribute("data-collapsed") === "true" ||
					el.querySelector<HTMLElement>(":scope > .site-info-detail")?.classList.contains("collapsed");
				const label = isCollapsed
					? expandText || collapseText
					: collapseText || expandText;
				if (label) btn.textContent = label;
			}
		});

	// 站点统计动态后缀（单位：天/日/days 等）：
	// value 在 data-stat-id 节点显示数字，suffix 只显示单位文字（避免 200 "200 日" 双数字 bug）。
	// 所以这里只把模板里 "{days}" 占位符去掉，只保留纯单位 + 前后留白。
	document.querySelectorAll<HTMLElement>("[data-i18n-days-suffix]").forEach((el) => {
		const attr = el.getAttribute("data-i18n-days-suffix");
		if (!attr) return;
		const template = i18n(attr as I18nKey);
		if (!template) return;
		// 从前面的 data-stat-id 数字节点取当前 days 值（用于判断是否是非数字的 today 文本态）
		const suffixId = el.getAttribute("data-stat-suffix");
		let countVal: number = 0;
		const statEl = suffixId
			? document.querySelector<HTMLElement>(`[data-stat-id="${suffixId}"]`)
			: null;
		if (statEl?.textContent) {
			const parsed = Number(String(statEl.textContent).replace(/[^\d.-]/g, ""));
			if (!Number.isNaN(parsed)) countVal = parsed;
			else countVal = NaN;
		}
		// 非数字内容（last-update 的"今日/今天/Today"等文本态）：隐藏 suffix，并把 statEl 文本重写成当前语言
		if (Number.isNaN(countVal)) {
			el.style.display = "none";
			const todayKey = statEl?.getAttribute("data-stat-today-key") as I18nKey | null;
			if (statEl && todayKey) {
				const todayLabel = i18n(todayKey);
				if (todayLabel) statEl.textContent = todayLabel;
			}
			return;
		}
		el.style.display = "";
		// 与 SSR 阶段 suffix 生成逻辑对齐：只把模板中的 "{days}" 占位符移除，保留其余字符（含空格）
		// 这样对于 "{days} 日" / "{days} 天前" / "{days} days" 都能得到正确的带前导空格的纯单位文本，
		// 与前面 data-stat-id 的数字拼接后不会再出现「200  200 日」双数字 bug。
		el.textContent = template.replace("{days}", "");
	});

	// 归档面板：切语言后覆写元素上的 __i18nStrings（保证后续筛选/重渲染取新语言文案），
	// 并且立刻刷新已渲染的"X 篇文章 / X 篇文章"label。
	document
		.querySelectorAll<
			HTMLElement & {
				__i18nStrings?: Record<string, string>;
			}
		>("archive-panel[data-i18n-keyset='archivePanel']")
		.forEach((panel) => {
			const newStrings = {
				categories: i18n(I18nKey.categories) || "Categories",
				tags: i18n(I18nKey.tags) || "Tags",
				uncategorized: i18n(I18nKey.uncategorized) || "Uncategorized",
				postCount: i18n(I18nKey.postCount) || "post",
				postsCount: i18n(I18nKey.postsCount) || "posts",
			};
			panel.__i18nStrings = newStrings;
			panel
				.querySelectorAll<HTMLElement>(".archive-year-count-label")
				.forEach((labelEl) => {
					const key = labelEl.getAttribute("data-i18n-postcount-key");
					const text =
						key === "postCount"
							? newStrings.postCount
							: key === "postsCount"
								? newStrings.postsCount
								: "";
					if (text) labelEl.textContent = text;
				});
			// 刷新归档年份展开/收起按钮的 aria-label（切换到新语言文案 + 保留年份数字）
			const expandText = i18n(I18nKey.expand) || "Expand";
			const collapseText = i18n(I18nKey.collapse) || "Collapse";
			panel
				.querySelectorAll<HTMLElement>(
					"button.archive-year-toggle[data-i18n-expand-key][data-i18n-collapse-key]",
				)
				.forEach((btn) => {
					const year = btn.getAttribute("data-year-value") || "";
					const expanded = btn.getAttribute("aria-expanded") === "true";
					const label = expanded
						? `${collapseText} ${year}`.trim()
						: `${expandText} ${year}`.trim();
					if (label) btn.setAttribute("aria-label", label);
				});
		});

	// 日历：切语言后重写月份/年份标题。
	// 注：Calendar.astro 的 <script is:inline define:vars> 是 SSR 一次性注入字面量，
	// 切语言后 monthNames / yearText / currentLang 不会同步，这里直接根据 DOM 里已渲染的
	// 「数字年份 + 月份文本」重新构造显示内容，并按中英日语序调整。
	const calNav = document.getElementById("current-month-display") as HTMLElement | null;
	if (calNav && calNav.textContent) {
		// 从原文本里提取 year (四位数)
		const yearMatch = /\b(\d{4})\b/.exec(calNav.textContent);
		const year = yearMatch ? Number(yearMatch[1]) : new Date().getFullYear();
		// 按「月份名字」匹配：先判断当前语言的月份顺序，再构造
		const months = [
			I18nKey.calendarJanuary,
			I18nKey.calendarFebruary,
			I18nKey.calendarMarch,
			I18nKey.calendarApril,
			I18nKey.calendarMay,
			I18nKey.calendarJune,
			I18nKey.calendarJuly,
			I18nKey.calendarAugust,
			I18nKey.calendarSeptember,
			I18nKey.calendarOctober,
			I18nKey.calendarNovember,
			I18nKey.calendarDecember,
		];
		const monthNamesArr = months.map((k) => i18n(k) || "");
		const monthMap: Record<string, number> = {};
		monthNamesArr.forEach((m, idx) => {
			if (m) monthMap[m.toLowerCase()] = idx;
		});
		// 查找原文里是否包含某个月份名
		let monthIdx = -1;
		const lowered = calNav.textContent.toLowerCase();
		for (const m of Object.keys(monthMap)) {
			if (lowered.includes(m)) {
				monthIdx = monthMap[m];
				break;
			}
		}
		if (monthIdx < 0) monthIdx = new Date().getMonth();

		const lang = getCurrentLang();
		const yearTxt = i18n(I18nKey.year) || "年";
		const monthTxt = monthNamesArr[monthIdx] || "";
		if (lang.startsWith("zh") || lang.startsWith("ja")) {
			calNav.textContent = `${year}${yearTxt}${monthTxt}`;
		} else {
			calNav.textContent = `${monthTxt} ${year}`;
		}
	}
}

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
	// 后端写入 cookie 的值 → zh / zh_Hant；这里再映射回前端 Lang code。
	zh: zh_CN,
	zh_hant: zh_TW,
	zh_Hant: zh_TW,
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
	const safe = normalizeLangOrFallback(lang, "zh_CN");
	currentLang.set(safe);
	if (typeof localStorage !== "undefined") {
		localStorage.setItem("lang", safe);
	}
	// 写入 cookie（path=/ 同源可用）以便 SSR 阶段通过 Vite 代理头传递给后端
	if (typeof document !== "undefined") {
		document.documentElement.setAttribute("data-lang", safe);
		const htmlLang = safe.replace("_", "-");
		document.documentElement.setAttribute("lang", htmlLang);
		// 后端对应的映射：zh_CN→zh, zh_TW→zh_Hant, en→en, ja→ja
		const backendLang =
			safe === "zh_TW" ? "zh_Hant" : safe === "zh_CN" ? "zh" : safe;
		const expires = new Date(
			Date.now() + 365 * 24 * 60 * 60 * 1000,
		).toUTCString();
		document.cookie = `rosetta_lang=${encodeURIComponent(backendLang)}; path=/; expires=${expires}; SameSite=Lax`;

		// 提前把「页面即将重载」写到全局 window 标志，保证：
		//  1) rosetta-lang-change 派发期间各组件才会把 unloadingSoon 置位（没问题）
		//  2) 派发之后的 ~30ms 窗口里，任何被 Swup 新插入 DOM 才初始化 / 才 onMount 的
		//     Svelte 组件（DynamicSidebar、DynamicFeed）也能提前检测到，不会发新请求，
		//     从而彻底消除 DevTools 中「net::ERR_ABORTED /api/activities?...」的红色网络日志。
		//  标志在 beforeunload / pagehide 时也同样被设置，双重保险。
		const w = window as Window & { __rosettaUnloadingSoon?: boolean };
		w.__rosettaUnloadingSoon = true;

		// 派发全局事件，通知 SSR 渲染的组件（导航、页脚等）同步切换客户端文字
		// detail.willReload = true 代表 LangSwitcher 会在 ~30ms 后调用
		// window.location.replace() 触发整页重载；收到该信号的组件应：
		//   1) 立即 abort 所有进行中的 fetch/XHR
		//   2) 取消任何已排期的 debounce/setTimeout I/O
		//   3) 不再发新请求，避免浏览器把被卸载打断的请求记为 ERR_ABORTED
		try {
			const evt = new CustomEvent("rosetta-lang-change", {
				detail: { lang: safe, backendLang, willReload: true },
				bubbles: true,
			});
			window.dispatchEvent(evt);
		} catch (_e) {
			// 旧浏览器兼容失败静默
		}
	}
}

// 暴露给 Navbar / Footer 等 Swup 外脚本调用（例如 content:replace 后），
// 统一同步 html 属性 + cookie + rosetta-lang-change，避免 Navbar 里自行
// 维护一份「只写属性不发事件」的实现导致语言状态分裂。
if (typeof window !== "undefined") {
	(window as Window & {
		__rosettaSetLang?: (lang: Lang | string) => void;
		__rosettaRawI18n?: (key: string) => string;
	}).__rosettaSetLang = (l) => {
		setLang(normalizeLangOrFallback(l, "zh_CN"));
	};
	// 给 is:inline 脚本（SiteStats.astro / MainGridLayout.resetBannerState 等）
	// 读取当前语言的 i18n 文案（纯 key→字符串，不带 vars；找不到时返回空串由调用方兜底）
	(window as Window & {
		__rosettaSetLang?: (lang: Lang | string) => void;
		__rosettaRawI18n?: (key: string) => string;
	}).__rosettaRawI18n = (key: string) => {
		try {
			return i18n(key as I18nKey) || "";
		} catch (_e) {
			return "";
		}
	};
}

export const t: Readable<Translation> = derived(currentLang, ($lang) =>
	getTranslation($lang),
);

// Swup 就绪后：SPA 导航切换到新页面 → 非容器区（Navbar / Footer / 设置面板）的
// SSR 渲染文案必须同步应用 i18n（包含 data-i18n-titles / data-i18n-text-key /
// data-i18n-aria-key 三种声明方式）。
// 为避免执行顺序问题（translation.js 在 swup.js 之前加载），这里在 DOMContentLoaded
// 再绑定钩子 + 立即对初始文档执行一次应用，确保首屏文字正确。
if (typeof window !== "undefined" && typeof document !== "undefined") {
	const bind = () => {
		const w = window as Window & {
			swup?: {
				hooks?: {
					on: (
						evt: string,
						handler: () => void,
					) => void;
				};
			};
		};
		// 先应用一次当前文档（首屏 SSR 渲染完立即生效，不用等用户切换语言）
		applyI18nTitlesAnywhere();
		// swup 已实例化：直接挂钩子
		if (w.swup && w.swup.hooks && typeof w.swup.hooks.on === "function") {
			w.swup.hooks.on("content:replace", () =>
				applyI18nTitlesAnywhere(),
			);
			w.swup.hooks.on("page:view", () =>
				applyI18nTitlesAnywhere(),
			);
		} else {
			// 延迟绑定：swup 稍后才初始化（@swup/astro 会派发 "swup:enable"）
			window.addEventListener(
				"swup:enable",
				() => {
					if (w.swup && w.swup.hooks && typeof w.swup.hooks.on === "function") {
						w.swup.hooks.on("content:replace", () =>
							applyI18nTitlesAnywhere(),
						);
						w.swup.hooks.on("page:view", () =>
							applyI18nTitlesAnywhere(),
						);
					}
				},
				{ once: true },
			);
		}
	};
	if (document.readyState === "loading") {
		document.addEventListener("DOMContentLoaded", bind, { once: true });
	} else {
		bind();
	}
	// 语言切换事件：全局只需要一个，因为 applyI18nTitlesAnywhere 会遍历整个文档
	window.addEventListener(
		"rosetta-lang-change",
		(e) => {
			const ce = e as CustomEvent<{ lang?: string; backendLang?: string }>;
			const hint = ce.detail?.backendLang || ce.detail?.lang;
			applyI18nTitlesAnywhere(hint);
		},
		false,
	);
}

/**
 * 运行时「当前有效语言」读取的统一入口：
 *  优先级：cookie rosetta_lang（SSR 写 / setLang 写）→ localStorage.lang（旧版本）
 *        → html[data-lang]（documentElement）→ siteConfig.lang（默认值）。
 *
 *  SSR 下调用时可传 Astro 全局对象，会优先从 Astro.cookies / Astro.request 的 Cookie 头
 *  读取 rosetta_lang，这样 frontmatter 中 t() 翻译的 WidgetLayout name、按钮 aria-label
 *  就不会落回默认 zh_CN，刷新页面时 SSR 文案与目标语言一致。
 */
export function readEffectiveLangHintRaw(
	astro?: {
		cookies?: { get: (k: string) => { value?: string } | undefined };
		request?: { headers?: { get?: (k: string) => string | null } };
	},
): string | null {
	// SSR：优先走 Astro.cookies（get 返回形如 { value }）
	if (astro) {
		try {
			const cookieVal = astro.cookies?.get?.("rosetta_lang");
			if (cookieVal && typeof cookieVal === "object" && "value" in cookieVal) {
				const v = (cookieVal as { value?: string }).value;
				if (v) return v;
			}
		} catch (_e) { /* ignore */ }
		try {
			const cookieHeader = astro.request?.headers?.get?.("Cookie")
				|| astro.request?.headers?.get?.("cookie");
			if (cookieHeader) {
				const m = /(?:^|;\s*)rosetta_lang=([^;]+)/.exec(cookieHeader);
				if (m && m[1]) {
					try { return decodeURIComponent(m[1]); } catch (_e) { /* ignore */ }
				}
			}
		} catch (_e) { /* ignore */ }
	}
	if (typeof document !== "undefined") {
		const m = /(?:^|;\s*)rosetta_lang=([^;]+)/.exec(document.cookie || "");
		if (m && m[1]) {
			try {
				const decoded = decodeURIComponent(m[1]);
				if (decoded) return decoded;
			} catch (_e) {
				/* ignore */
			}
		}
	}
	if (typeof localStorage !== "undefined") {
		const fromLs = localStorage.getItem("lang");
		if (fromLs) return fromLs;
	}
	if (typeof document !== "undefined") {
		const attr = document.documentElement.getAttribute("data-lang");
		if (attr) return attr;
	}
	return null;
}

export function getCurrentLang(): Lang {
	const raw = readEffectiveLangHintRaw();
	if (!raw) return normalizeLangOrFallback(siteConfig.lang || "zh_CN", "zh_CN");
	return normalizeLangOrFallback(raw, "zh_CN");
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

/**
 * 用指定的 langHint 翻译 i18n Key（SSR/Astro 组件调用时推荐）。
 *
 * 使用场景：
 *  Astro 服务器端组件（比如 Navbar.astro）能通过 Astro.cookies.get("rosetta_lang")
 *  读到用户真实偏好语言，如果直接调用 i18n(key)，会命中 siteConfig.lang（默认 zh_CN），
 *  导致服务端渲染的 aria-label / 文本永远是中文，然后客户端 applyI18nTitlesAnywhere
 *  执行后再「闪切」到目标语言，体验差。
 *
 *  在 Astro 组件里调用：
 *    const ssrLang = (Astro.cookies.get("rosetta_lang")?.value ?? siteConfig.lang) as Lang;
 *    const label = i18nFor(I18nKey.displaySettings, ssrLang);
 */
export function i18nFor(
	key: I18nKey,
	langHint: Lang | string | undefined | null,
	vars?: Record<string, string | number>,
): string {
	const safe = normalizeLangOrFallback(langHint, siteConfig.lang as Lang | undefined);
	const trans = getTranslation(safe);
	let value = trans[key];
	if (!value && safe !== "zh_CN") {
		const zh = zh_CN[key];
		if (zh) value = zh;
	}
	if (!value) value = defaultTranslation[key];
	if (vars && value) {
		Object.keys(vars).forEach((k) => {
			value = value!.replace(new RegExp(`\\{${k}\\}`, "g"), String(vars[k]));
		});
	}
	return value || key;
}

if (typeof document !== "undefined") {
	const initialLang = getInitialLang();
	document.documentElement.setAttribute("data-lang", initialLang);
	document.documentElement.setAttribute("lang", initialLang.replace("_", "-"));
}
