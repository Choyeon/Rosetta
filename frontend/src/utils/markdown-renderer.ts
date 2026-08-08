import katex from "katex";
import rehypeStringify from "rehype-stringify";
import remarkParse from "remark-parse";
import remarkRehype from "remark-rehype";
import { unified } from "unified";
import "katex/dist/contrib/mhchem.mjs";
import rehypeAutolinkHeadings from "rehype-autolink-headings";
import rehypeCallouts from "rehype-callouts";
import rehypeCodeGroup from "rehype-code-group";
import rehypeComponents from "rehype-components";
import rehypeKatex from "rehype-katex";
import rehypeSlug from "rehype-slug";
import remarkAdmonitionToBlockquoteCallout from "remark-admonition-to-blockquote-callout";
import remarkDirective from "remark-directive";
import remarkGfm from "remark-gfm";
import remarkMath from "remark-math";
import remarkSectionize from "remark-sectionize";
import { loadDynamicConfig } from "./dynamic-config";

let cachedMdCfg: any = null;
export const getMarkdownConfigs = async () => {
	if (cachedMdCfg) return cachedMdCfg;
	const cfg = await loadDynamicConfig();
	cachedMdCfg = {
		mermaidConfig: cfg.mermaid,
		plantumlConfig: cfg.plantuml,
		siteConfig: { title: cfg.site.title },
	};
	return cachedMdCfg;
};

// 默认回退值用于同步场景
import { plantumlConfig } from "../config";

const siteConfig = {
	title: "ROSETTA",
	site_url: "",
	post: {
		rehypeCallouts: {
			enablePythonMarkdownAdmonitions: true,
			theme: "default" as const,
		},
	},
	imageOptimization: { noReferrerDomains: [] },
};

import { GithubCardComponent } from "../plugins/rehype-component-github-card.mjs";
import { rehypeDiagramPanZoom } from "../plugins/rehype-diagram-panzoom.mjs";
import rehypeEmailProtection from "../plugins/rehype-email-protection.mjs";
import rehypeExternalLinks from "../plugins/rehype-external-links.mjs";
import rehypeFigure from "../plugins/rehype-figure.mjs";
import rehypeImageReferrerPolicy from "../plugins/rehype-image-referrerpolicy.mjs";
import { rehypePlantuml } from "../plugins/rehype-plantuml.mjs";
import { parseDirectiveNode } from "../plugins/remark-directive-rehype.js";
import { remarkExcerpt } from "../plugins/remark-excerpt.js";
import { remarkImageGrid } from "../plugins/remark-image-grid.js";
import { remarkMermaid } from "../plugins/remark-mermaid.js";
import { remarkPlantuml } from "../plugins/remark-plantuml.js";
// BUG#5 FIX: 客户端（MarkdownEditor 预览）不使用 remarkReadingTime，
// 因为 reading-time 包依赖 Node.js 的 util.inherits，在浏览器端会导致 hydration 错误。
// 注意：astro.config.mjs 中 SSG/SSR 构建使用独立的 remarkReadingTime 导入，不受影响。
//
// BUG#6 FIX: 客户端不使用 remarkWikiLink / rehypeMermaid，
// 因为这些插件在模块顶层静态 import 了 node:fs / node:path / node:url，
// 在浏览器端加载模块时就会报 "Module 'node:fs' has been externalized" 错误。
// 注意：astro.config.mjs 中 SSG/SSR 构建使用独立的 remarkWikiLink / rehypeMermaid 导入，不受影响。

export const remarkPlugins = [
	remarkGfm,
	...(siteConfig.post.rehypeCallouts.enablePythonMarkdownAdmonitions !== false
		? [remarkAdmonitionToBlockquoteCallout]
		: []),
	remarkMath,
	remarkImageGrid,
	remarkExcerpt,
	remarkDirective,
	remarkSectionize,
	parseDirectiveNode,
	remarkMermaid,
	[remarkPlantuml, plantumlConfig],
] as any[];

export const rehypePlugins = [
	[rehypeKatex, { katex }],
	[rehypeCallouts, { theme: siteConfig.post.rehypeCallouts.theme }],
	rehypeSlug,
	rehypeCodeGroup,
	rehypePlantuml,
	rehypeDiagramPanZoom,
	rehypeFigure,
	[
		rehypeImageReferrerPolicy,
		{ domains: siteConfig.imageOptimization?.noReferrerDomains || [] },
	],
	[rehypeExternalLinks, { siteUrl: siteConfig.site_url }],
	[rehypeEmailProtection, { method: "base64" }],
	[
		rehypeComponents,
		{
			components: {
				github: GithubCardComponent,
			},
		},
	],
	[
		rehypeAutolinkHeadings,
		{
			behavior: "append",
			properties: {
				className: ["anchor"],
			},
			content: {
				type: "element",
				tagName: "span",
				properties: {
					className: ["anchor-icon"],
					"data-pagefind-ignore": true,
				},
				children: [
					{
						type: "text",
						value: "#",
					},
				],
			},
		},
	],
] as any[];

let processor: any = null;
let processorBuilding: Promise<any> | null = null;

/**
 * 构建 unified processor（根据 SSR / 客户端环境动态加载插件）
 * - SSR 模式（服务端渲染 / [...slug].astro 中 await renderMarkdown(...) 调用场景）：
 *   追加 rehype-expressive-code 成熟代码高亮（复制按钮、行号、折叠、双主题、语言徽标）
 * - 客户端模式（MarkdownEditor 实时预览等浏览器环境）：
 *   保持轻量 rehype 管线，避免打包 Shiki/Oniguruma WASM 巨大体积
 */
async function getProcessor(): Promise<any> {
	if (processor) return processor;
	if (processorBuilding) return processorBuilding;

	processorBuilding = (async () => {
		const base = unified()
			.use(remarkParse as any)
			.use(remarkPlugins as any)
			.use(remarkRehype as any, { allowDangerousHtml: true })
			.use(rehypePlugins as any);

		// ---------- SSR-only: Expressive Code 成熟代码高亮 ----------
		// 1. 仅 SSR 环境启用（浏览器端 build 时会把 import.meta.env.SSR 替换为 false，
		//    配合 Vite 的 dead-code elimination，客户端 bundle 中不会包含
		//    rehype-expressive-code / oniguruma 这种重型依赖。
		// 2. import.meta.env?.SSR 在 Astro Vite 环境为 true / false，其它环境
		//    （比如纯 Node 单元测试）回退到 typeof process 判断。
		const isSSREnv: boolean =
			(typeof (import.meta as any)?.env?.SSR === "boolean"
				? (import.meta as any).env.SSR
				: typeof process !== "undefined" &&
				  !!(process as any).versions?.node &&
				  typeof window === "undefined");

		if (isSSREnv) {
			try {
				// ---------- 先拿配置 ----------
				let ecCfg: any = null;
				try {
					const cfgMod = await import("../config");
					ecCfg = cfgMod.expressiveCodeConfig;
				} catch (e: any) {
					throw new Error("config import: " + (e as Error).message);
				}
				const expressiveCodeConfig = ecCfg;

				// ---------- 分步 import，便于定位哪一个具体包缺失 ----------
				let ecCore: any;
				try { ecCore = await import("rehype-expressive-code"); }
				catch (e: any) { throw new Error("rehype-expressive-code: " + (e as Error).message); }
				let collapsibleSec: any;
				try { collapsibleSec = await import("@expressive-code/plugin-collapsible-sections"); }
				catch (e: any) { throw new Error("plugin-collapsible-sections: " + (e as Error).message); }
				let lineNums: any;
				try { lineNums = await import("@expressive-code/plugin-line-numbers"); }
				catch (e: any) { throw new Error("plugin-line-numbers: " + (e as Error).message); }

				let langBadgeFn: any = null;
				if (expressiveCodeConfig?.pluginLanguageBadge?.enable === true) {
					try {
						const lb = await import("expressive-code-language-badge");
						langBadgeFn = (lb as any)?.pluginLanguageBadge ?? (lb as any)?.default;
					} catch (e: any) {
						console.warn("[markdown-renderer] pluginLanguageBadge load failed:", e?.message);
					}
				}
				let langLogoFn: any = null;
				if (expressiveCodeConfig?.pluginLanguageLogo?.enable === true) {
					try {
						const ll = await import("ec-lang-logo");
						langLogoFn = (ll as any)?.pluginLanguageLogo ?? (ll as any)?.default;
					} catch (e: any) {
						console.warn("[markdown-renderer] pluginLanguageLogo load failed:", e?.message);
					}
				}
				let collapsibleFn: any = null;
				if (expressiveCodeConfig?.pluginCollapsible?.enable === true) {
					try {
						const cc = await import("expressive-code-collapsible");
						collapsibleFn = (cc as any)?.pluginCollapsible ?? (cc as any)?.default;
					} catch (e: any) {
						console.warn("[markdown-renderer] pluginCollapsible load failed:", e?.message);
					}
				}

				let i18nFn: any = null;
				try {
					const iMod = await import("../i18n/translation");
					i18nFn = iMod?.i18n ?? iMod;
				} catch {}
				let KeyMod: any = null;
				try {
					const k = await import("../i18n/i18nKey");
					KeyMod = k.default ?? k;
				} catch {}

				const pluginsArr: any[] = [];
				const K: any = KeyMod || {};
				const defI18n = (key: string, fallback: string): string => {
					if (typeof i18nFn === "function" && key && typeof key === "string") {
						try {
							const got = i18nFn(key);
							if (typeof got === "string" && got) return got;
						} catch {}
					}
					return fallback;
				};

				// pluginLanguageBadge 配置
				if (expressiveCodeConfig?.pluginLanguageBadge?.enable === true && typeof langBadgeFn === "function") {
					try {
						const v = langBadgeFn();
						if (v) pluginsArr.push(v);
					} catch (e: any) {
						console.warn("[markdown-renderer] pluginLanguageBadge init failed:", e?.message);
					}
				}
				// pluginLanguageLogo 配置
				if (expressiveCodeConfig?.pluginLanguageLogo?.enable === true && typeof langLogoFn === "function") {
					try {
						const args = {
							color: expressiveCodeConfig.pluginLanguageLogo.color ?? "mono",
							excludedLangs: expressiveCodeConfig.pluginLanguageLogo.excludedLangs ?? [],
						};
						const v = langLogoFn(args);
						if (v) pluginsArr.push(v);
					} catch (e: any) {
						console.warn("[markdown-renderer] pluginLanguageLogo init failed:", e?.message);
					}
				}
				const sec = (collapsibleSec as any)?.pluginCollapsibleSections ?? (collapsibleSec as any)?.default?.pluginCollapsibleSections ?? collapsibleSec;
				const ln = (lineNums as any)?.pluginLineNumbers ?? (lineNums as any)?.default?.pluginLineNumbers ?? lineNums;
				if (typeof sec === "function") { const v = sec(); if (v) pluginsArr.push(v); }
				if (typeof ln === "function") { const v = ln(); if (v) pluginsArr.push(v); }
				// pluginCollapsible（超过 N 行自动折叠）
				if (expressiveCodeConfig?.pluginCollapsible?.enable === true && typeof collapsibleFn === "function") {
					try {
						const showMore = defI18n(K.codeCollapsibleShowMore, "展开");
						const showLess = defI18n(K.codeCollapsibleShowLess, "收起");
						const expanded = defI18n(K.codeCollapsibleExpanded, "代码块已展开");
						const collapsed = defI18n(K.codeCollapsibleCollapsed, "代码块已折叠");
						const args = {
							lineThreshold: expressiveCodeConfig.pluginCollapsible.lineThreshold || 15,
							previewLines: expressiveCodeConfig.pluginCollapsible.previewLines || 8,
							defaultCollapsed: expressiveCodeConfig.pluginCollapsible.defaultCollapsed ?? true,
							expandButtonText: showMore,
							collapseButtonText: showLess,
							expandedAnnouncement: expanded,
							collapsedAnnouncement: collapsed,
						};
						const v = collapsibleFn(args);
						if (v) pluginsArr.push(v);
					} catch (e: any) {
						console.warn("[markdown-renderer] pluginCollapsible init failed:", e?.message);
					}
				}

				const rehypeExpressiveCode = ecCore.default ?? ecCore;
				// eslint-disable-next-line no-console
				if (typeof console?.debug === "function") {
					console.debug("[markdown-renderer] SSR EC plugins loaded:", pluginsArr.flat().filter(Boolean).map(p => typeof p === "object" && p ? (p.name || "plugin@" + (Object.keys(p).slice(0,3).join(","))) : typeof p));
				}
				base.use(rehypeExpressiveCode as any, {
					themes: [
						expressiveCodeConfig.darkTheme,
						expressiveCodeConfig.lightTheme,
					],
					useDarkModeMediaQuery: false,
					// 与站点 <html data-theme="one-light/one-dark-pro"> 完全同步
					themeCssSelector: (theme: any) => `[data-theme='${theme.name}']`,
					plugins: pluginsArr.flat().filter(Boolean),
					defaultProps: {
						wrap: false,
						overridesByLang: {
							shellsession: {
								showLineNumbers: false,
							},
						},
					},
					styleOverrides: {
						borderRadius: "0.75rem",
						codeFontSize: "0.875rem",
						codeFontFamily:
							"var(--font-jetbrains-mono), ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, 'Liberation Mono', 'Courier New', monospace",
						codeLineHeight: "1.5rem",
						frames: {},
						textMarkers: {
							delHue: 0,
							insHue: 180,
							markHue: 250,
						},
						languageBadge: {
							fontSize: "0.75rem",
							fontWeight: "bold",
							borderRadius: "0.25rem",
							opacity: "1",
							borderWidth: "0px",
							borderColor: "transparent",
						},
					},
					frames: {
						showCopyToClipboardButton: true,
					},
				} as any);
			} catch (e) {
				console.warn(
					"[markdown-renderer] Failed to load Expressive Code for SSR, fallback to plain code blocks:",
					e,
				);
			}
		}

		// 最后：stringify
		base.use(rehypeStringify as any, { allowDangerousHtml: true });
		processor = base;
		return base;
	})();

	return processorBuilding;
}

export async function renderMarkdown(
	content: string,
): Promise<{ html: string; headings: any[]; frontmatter: any }> {
	try {
		const proc = await getProcessor();
		const result = await proc.process(content);
		return {
			html: String(result),
			headings: (result.data as any)?.headings || [],
			frontmatter: (result.data as any)?.frontmatter || {},
		};
	} catch (e) {
		console.warn("[markdown-renderer] Failed to render markdown:", e);
		return {
			html: `<pre>${content}</pre>`,
			headings: [],
			frontmatter: {},
		};
	}
}
