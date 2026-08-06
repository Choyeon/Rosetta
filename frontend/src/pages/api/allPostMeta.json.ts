import { getSortedPosts } from "@/utils/content-utils";

const JSON_HEADERS: Record<string, string> = {
	"Content-Type": "application/json; charset=utf-8",
	// 由于后台发布了新文章，缓存不宜过长；CDN 可在 60s 内短暂复用：
	"Cache-Control":
		"public, max-age=60, s-maxage=300, stale-while-revalidate=600",
	// 当 rosetta_lang cookie 变更时，缓存应失效（实际此端点不依赖 cookie，但为一致性保留）
	Vary: "Accept-Encoding, Accept, Cookie",
	// 允许内嵌第三方页面在后台调用
	"Access-Control-Allow-Origin": "*",
	"Access-Control-Allow-Methods": "GET, OPTIONS",
	"X-Content-Type-Options": "nosniff",
};

export async function GET(): Promise<Response> {
	try {
		const posts = await getSortedPosts();

		const allPostsData = posts
			.map((post) => {
				const published = post.data?.published;
				return {
					id: post.slug || post.id,
					slug: post.slug || post.id,
					title: post.data?.title ?? "",
					description:
						(post.data as any)?.summary || post.data?.description || "",
					published:
						published instanceof Date
							? published.getTime()
							: new Date(0).getTime(),
					category: post.data?.category || "",
					password: !!post.data?.password,
				};
			})
			.sort((a, b) => b.published - a.published);

		return new Response(JSON.stringify(allPostsData), {
			headers: JSON_HEADERS,
		});
	} catch (e) {
		console.error("[allPostMeta] Failed:", e);
		return new Response(JSON.stringify([]), {
			status: 500,
			headers: {
				...JSON_HEADERS,
				"Cache-Control": "no-store",
			},
		});
	}
}
