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

function getProcessor(): any {
	if (processor) return processor;

	processor = unified()
		.use(remarkParse as any)
		.use(remarkPlugins as any)
		.use(remarkRehype as any, { allowDangerousHtml: true })
		.use(rehypePlugins as any)
		.use(rehypeStringify as any, { allowDangerousHtml: true });

	return processor;
}

export async function renderMarkdown(
	content: string,
): Promise<{ html: string; headings: any[]; frontmatter: any }> {
	try {
		const proc = getProcessor();
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
