import { loadRenderers } from "astro:container";
import { render } from "astro:content";
import { getContainerRenderer as getMDXRenderer } from "@astrojs/mdx/container-renderer";
import rss, { type RSSFeedItem } from "@astrojs/rss";
import I18nKey from "@i18n/i18nKey";
import { i18n } from "@i18n/translation";
import { getSortedPosts } from "@utils/content-utils";
import { formatDateI18nWithTime } from "@utils/date-utils";
import { url } from "@utils/url-utils";
import type { APIContext } from "astro";
import { experimental_AstroContainer as AstroContainer } from "astro/container";
import sanitizeHtml from "@/utils/sanitize";
// RSS生成在构建时，暂时用静态配置
import { siteConfig } from "@/config";

// 通过 astro.config.mjs 中 vite.define 注入的构建时全局常量，
// 避免 ../../package.json 这种跨 src 边界的相对路径在 SSR 运行时解析失败。
// 兜底使用 "2.0.0"，防止本地调试时 astro dev 未定义常量导致 ReferenceError。
declare const __ROSETTA_PKG_VERSION__: string | undefined;
const PKG_VERSION: string =
	(typeof __ROSETTA_PKG_VERSION__ !== "undefined" && __ROSETTA_PKG_VERSION__) ||
	"2.0.0";

function stripInvalidXmlChars(str: string): string {
	return str.replace(
		// biome-ignore lint/suspicious/noControlCharactersInRegex: https://www.w3.org/TR/xml/#charsets
		/[\x00-\x08\x0B\x0C\x0E-\x1F\x7F-\x9F\uFDD0-\uFDEF\uFFFE\uFFFF]/g,
		"",
	);
}

export async function GET(context: APIContext): Promise<Response> {
	const blog = await getSortedPosts();
	const renderers = await loadRenderers([getMDXRenderer()]);
	const container = await AstroContainer.create({ renderers });
	const feedItems: RSSFeedItem[] = [];
	// @astrojs/rss 会对 pubDate 调用 .toISOString()，若传入非法 Date 会抛
	// RangeError: Invalid time value，直接中断整个站点的生产构建。这里集中做一层
	// 规范化：所有 date-like 输入都转成 Date，非法值回退到 Unix 纪元（或当前时间）。
	function asValidDate(value: unknown, fallback = new Date(0)): Date {
		if (value instanceof Date && !Number.isNaN(value.getTime())) return value;
		if (typeof value === "number" || typeof value === "string") {
			const d = new Date(value as any);
			if (!Number.isNaN(d.getTime())) return d;
		}
		return fallback;
	}
	for (const post of blog) {
		const published = asValidDate(post.data?.published, new Date());
		if (post.data.password) {
			feedItems.push({
				title: post.data.title,
				pubDate: published,
				description: post.data.description || "",
				link: url(`/posts/${post.id}/`),
				content: i18n(I18nKey.passwordProtectedRss),
			});
			continue;
		}
		// render() 要求 PostEntry.data.draft 一定是 boolean（不能 undefined），
		// 以及 content.config.ts 中 schema 要求其他默认值字段都具备。这里临时合并一个带全默认值的 postIn 传入。
		const postForRender = {
			...post,
			data: {
				draft: false,
				...(post.data || {}),
			},
		} as const;
		const { Content } = await render(postForRender as any);
		const rawContent = await container.renderToString(Content);
		const cleanedContent = stripInvalidXmlChars(rawContent);
		feedItems.push({
			title: post.data.title,
			pubDate: published,
			description: post.data.description || "",
			link: url(`/posts/${post.id}/`),
			content: sanitizeHtml(cleanedContent, {
				allowedTags: sanitizeHtml.defaults.allowedTags.concat(["img"]),
			}),
		});
	}
	return rss({
		title: siteConfig.title,
		description: siteConfig.subtitle || "No description",
		site: context.site ?? "https://firefly.cuteleaf.cn",
		customData: `<templateTheme>Firefly</templateTheme>
		<templateThemeVersion>${PKG_VERSION}</templateThemeVersion>
		<templateThemeUrl>https://github.com/CuteLeaf/Firefly</templateThemeUrl>
		<lastBuildDate>${formatDateI18nWithTime(new Date())}</lastBuildDate>`,
		items: feedItems,
	});
}
