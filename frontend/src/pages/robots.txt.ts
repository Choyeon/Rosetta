import type { APIRoute } from "astro";

/**
 * robots.txt —— 遵循 Astro API Routes 最佳实践：
 * 1. 永远返回一个明确的 Content-Type；
 * 2. 添加 X-Robots-Tag 头以强化行为；
 * 3. import.meta.env.SITE 未设置时不会抛错，给出兜底 URL。
 */
export const GET: APIRoute = () => {
	try {
		const site =
			(import.meta.env?.SITE as string | undefined) ||
			"https://firefly.cuteleaf.cn";
		const sitemapUrl = new URL("sitemap-index.xml", site).href;
		const robotsTxt = [
			"User-agent: *",
			"Allow: /",
			"Disallow: /_astro/",
			"Disallow: /admin/",
			"Disallow: /api/",
			"",
			`Sitemap: ${sitemapUrl}`,
		].join("\n");

		return new Response(robotsTxt, {
			headers: {
				"Content-Type": "text/plain; charset=utf-8",
				// 告诉搜索引擎，此响应的内容是标准的 robots 规则
				"X-Robots-Tag": "all",
				// 鼓励合理缓存（站点规则通常稳定），但不与 Cloudflare Workers 冲突
				"Cache-Control": "public, max-age=3600, s-maxage=86400",
			},
		});
	} catch (_e) {
		// 任何运行时错误都至少返回一个可解析的最小 robots.txt
		return new Response("User-agent: *\nAllow: /\n", {
			status: 200,
			headers: {
				"Content-Type": "text/plain; charset=utf-8",
				"Cache-Control": "no-store",
			},
		});
	}
};
