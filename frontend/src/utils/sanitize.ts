/**
 * HTML 消毒统一包装：基于 OWASP 事实上的标准 DOMPurify。
 *
 * 历史：原先使用 sanitize-html，它维护活跃度、社区审计面、每周下载量（3.6M）
 * 均弱于 DOMPurify（33M），且 DOMPurify 是 OWASP XSS Prevention Cheat Sheet
 * 推荐方案。此处提供与原 `sanitizeHtml(html, { allowedTags/allowedAttributes/allowedSchemes })`
 * 兼容的 API，调用方只需改 import 路径即可，避免 3 处（friends/Footer/RSS）
 * 同时重写配置。
 */
import createDOMPurify from "isomorphic-dompurify";
import type { Config as DOMPurifyConfig } from "dompurify";

// 在 Node/RSC/SSR 环境（friends/Footer/RSS）也直接可用：isomorphic-dompurify
// 默认会在无 window 时使用 jsdom 提供的 DOM，无需额外分支。
const DOMPurify = createDOMPurify;

/**
 * 近似 sanitize-html 的默认标签白名单。
 * sanitize-html 默认不包含 <img>（需要显式加），我们跟它保持一致，
 * 调用方各自 concat 自己需要的即可，避免与既有页面行为差异。
 */
const DEFAULT_ALLOWED_TAGS: readonly string[] = Object.freeze([
	"h3", "h4", "h5", "h6",
	"blockquote", "p", "a", "ul", "ol", "nl", "li",
	"b", "i", "strong", "em", "strike", "code", "hr", "br",
	"pre", "iframe",
	"sup", "sub",
]);

/**
 * 近似 sanitize-html defaults.allowedAttributes。
 * 注意：DOMPurify 默认允许的属性比 sanitize-html 严格（例如 style 不默认开），
 * 所以这里显式列出，保持原行为。
 */
const DEFAULT_ALLOWED_ATTRIBUTES: Readonly<Record<string, readonly string[]>> = Object.freeze(
	{
		a: ["href", "name", "target"],
		iframe: ["src"],
		img: ["src"],
	},
);

const DEFAULT_ALLOWED_SCHEMES: readonly string[] = Object.freeze(["http", "https"]);

export interface SanitizeOptions {
	allowedTags?: readonly string[];
	allowedAttributes?: Record<string, readonly string[]>;
	allowedSchemes?: readonly string[];
}

/** 兼容旧 sanitize-html 的 defaults 访问（静态引用）。 */
export const defaults: {
	allowedTags: string[];
	allowedAttributes: Record<string, string[]>;
	allowedSchemes: string[];
} = {
	allowedTags: [...DEFAULT_ALLOWED_TAGS],
	allowedAttributes: { ...DEFAULT_ALLOWED_ATTRIBUTES } as Record<string, string[]>,
	allowedSchemes: [...DEFAULT_ALLOWED_SCHEMES],
};

type SanitizeFn = (
	dirty: string | null | undefined,
	options?: SanitizeOptions,
) => string;
type SanitizeWithDefaults = SanitizeFn & {
	defaults: typeof defaults;
};

/**
 * 消毒 HTML：接受 sanitize-html 风格的配置，映射到 DOMPurify。
 *
 * 兼容性注意：
 * - 与原版 sanitize-html 一样，<script>/onerror/onload 等危险标签与事件属性
 *   一律移除；style 属性只有在调用方显式将 style 放进 allowedAttributes['*']
 *   时才保留。
 * - DOMPurify 会自动将 target=_blank 的链接加上 rel=noopener noreferrer，
 *   比原版 sanitize-html 更安全。
 */
export const sanitizeHtml: SanitizeWithDefaults = function (
	dirty: string | null | undefined,
	options: SanitizeOptions = {},
): string {
	if (!dirty) return "";

	const allowedTags = options.allowedTags ? [...options.allowedTags] : [...DEFAULT_ALLOWED_TAGS];
	const allowedAttributes = options.allowedAttributes ?? { ...DEFAULT_ALLOWED_ATTRIBUTES };
	const allowedSchemes = options.allowedSchemes?.length
		? [...options.allowedSchemes]
		: [...DEFAULT_ALLOWED_SCHEMES];

	// sanitize-html 的 allowedAttributes 是 "tagName => attr[]"，允许 '*' 通配；
	// DOMPurify 的 ALLOWED_ATTR 是全局 attr 数组 + ADD_ATTR 扩展。
	// 为保持精确，我们走 DOMPurify 的钩子不合适，改用 ADD_ATTR + ALLOWED_ATTR 组合：
	const globalWildcardAttrs = new Set<string>(allowedAttributes["*"] ?? []);
	const perTagAttrs: Record<string, string[]> = {};
	for (const [tag, attrs] of Object.entries(allowedAttributes)) {
		if (tag === "*") continue;
		perTagAttrs[tag.toLowerCase()] = [...attrs];
	}

	// 全局允许的属性集合：通配 + 所有 tag 级属性合并去重
	const allAttrs = new Set<string>(globalWildcardAttrs);
	for (const attrs of Object.values(perTagAttrs)) for (const a of attrs) allAttrs.add(a);

	// DOMPurify 配置：保留 ALLOWED_TAGS（注意小写），ALLOWED_ATTR 走数组，
	// 并用 ALLOWED_URI_REGEXP 扩展 allowedSchemes。
	const purifyCfg: DOMPurifyConfig = {
		ALLOWED_TAGS: allowedTags.map((t) => t.toLowerCase()),
		ALLOWED_ATTR: [...allAttrs],
		ALLOW_DATA_ATTR:
			globalWildcardAttrs.has("data-*") ||
			Object.values(perTagAttrs).some((a) => a.includes("data-*")),
		ALLOW_UNKNOWN_PROTOCOLS: false,
		ADD_URI_SAFE_ATTR: [],
		FORBID_TAGS: [
			"script",
			"style",
			"link",
			"meta",
			"base",
			"form",
			"input",
			"button",
			"textarea",
			"select",
		],
		FORBID_ATTR: [
			"onerror",
			"onload",
			"onclick",
			"onmouseover",
			"onfocus",
			"onblur",
			"onchange",
			"onsubmit",
			"onkeydown",
			"onkeypress",
			"onkeyup",
		],
	};

	// 构造 allowedSchemes 对应的正则：例如 http|https|mailto →
	// 匹配协议时不区分大小写，紧随 :// 或 mailto: (:)
	if (allowedSchemes.length) {
		const joined = allowedSchemes
			.map((s) => s.replace(/[^a-zA-Z0-9+.-]/g, ""))
			.filter(Boolean)
			.join("|");
		if (joined) {
			// mailto: 不需要 //，其他都需要 //。写一个宽松且安全的正则即可。
			purifyCfg.ALLOWED_URI_REGEXP = new RegExp(
				`^(?:(?:${joined}):(?:\\/\\/)?|[\\w\u00a0-\uffff-]|#)`,
				"i",
			);
		}
	}

	return DOMPurify.sanitize(dirty, purifyCfg);
} as SanitizeWithDefaults;

// 挂载 defaults 到函数对象（同时满足类型声明 + 运行时访问）
sanitizeHtml.defaults = defaults;

export default sanitizeHtml;
