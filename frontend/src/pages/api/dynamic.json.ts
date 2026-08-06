import type { APIContext } from "astro";
import { getDynamics } from "@/api/content";

function resolveContent(content: unknown, preferLang: string): string {
	if (typeof content === "string") return content || "";
	if (typeof content === "object" && content !== null) {
		const obj = content as Record<string, unknown>;
		const langKey = preferLang === "zh_Hant" ? "zh_Hant" : preferLang;
		const pick = (k: string): string | undefined => {
			const v = obj[k];
			return typeof v === "string" ? v : undefined;
		};
		const firstNonEmptyString = (): string => {
			for (const v of Object.values(obj)) {
				if (typeof v === "string" && v.length > 0) return v;
			}
			return "";
		};
		return (
			pick(langKey) ||
			pick("zh") ||
			pick("en") ||
			pick("ja") ||
			firstNonEmptyString() ||
			""
		);
	}
	return "";
}

const JSON_HEADERS: Record<string, string> = {
	"Content-Type": "application/json; charset=utf-8",
	// 动态列表内容刷新较频繁，保守设置缓存
	"Cache-Control":
		"public, max-age=30, s-maxage=120, stale-while-revalidate=300",
	Vary: "Accept-Encoding, Accept, Cookie",
	"Access-Control-Allow-Origin": "*",
	"Access-Control-Allow-Methods": "GET, OPTIONS",
	"X-Content-Type-Options": "nosniff",
};

export async function GET({ request }: APIContext): Promise<Response> {
	try {
		// 从请求 Cookie / 头推断偏好语言
		let preferLang = "zh";
		const cookie = request.headers.get("cookie") || "";
		const match = cookie.match(/rosetta_lang=([^;]+)/);
		if (match) {
			const raw = decodeURIComponent(match[1]).toLowerCase();
			if (raw.includes("hant") || raw.includes("tw") || raw.includes("hk")) {
				preferLang = "zh_Hant";
			} else if (raw.startsWith("en")) preferLang = "en";
			else if (raw.startsWith("ja")) preferLang = "ja";
		}

		const result = (await getDynamics({ page_size: 50 })) as unknown;
		const items =
			(result && typeof result === "object" && "items" in result
				? (result as { items?: unknown[] }).items
				: undefined) || [];
		const dynamics = (Array.isArray(items) ? items : []) as unknown[];

		const data = dynamics.map((d) => {
			const row =
				typeof d === "object" && d !== null
					? (d as Record<string, unknown>)
					: {};
			const createdAt = row.created_at;
			const html = resolveContent(row.content, preferLang);
			return {
				id: String(row.id ?? ""),
				published:
					createdAt instanceof Date
						? createdAt.getTime()
						: typeof createdAt === "string" || typeof createdAt === "number"
							? new Date(createdAt as any).getTime()
							: 0,
				html,
				images: Array.isArray(row.images) ? (row.images as string[]) : [],
				searchText: html,
				pinned: typeof row.is_pinned === "boolean" ? row.is_pinned : false,
				location: typeof row.location === "string" ? row.location : "",
			};
		});

		return new Response(JSON.stringify(data), {
			headers: JSON_HEADERS,
		});
	} catch (e) {
		console.warn(
			"[dynamic.json] Failed to fetch from API, returning empty:",
			e,
		);
		return new Response(JSON.stringify([]), {
			status: 500,
			headers: {
				...JSON_HEADERS,
				"Cache-Control": "no-store",
			},
		});
	}
}
