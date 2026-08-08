import { setSSRRequestContext } from "@/api/client";

/**
 * Astro SSR 页面统一调用：在任何 await 后端 API fetch 之前调用一次，
 * 把 Astro.cookies / headers 里的语言偏好注入到 api/client.ts，
 * 让 SSR 直连后端的请求也带上与浏览器一致的 ?lang= 参数，
 * 保证文章/分类/标签等内容在 SSR 阶段就本地化（切语言刷新后立即看到目标语言内容）。
 *
 * 用法（放在 Astro 页面 frontmatter 顶部）：
 *   ---
 *   import { applyAstroLangContext } from "@/utils/ssrLangContext";
 *   applyAstroLangContext(Astro);
 *   const posts = await getSortedPosts();
 *   ---
 */
export function applyAstroLangContext(
	astro: {
		cookies?: {
			get: (key: string) => { value?: string } | undefined;
		};
		request?: {
			headers?: {
				get: (key: string) => string | null;
			};
		};
	},
): void {
	try {
		const cookie = astro.cookies?.get("rosetta_lang")?.value;
		const accept = astro.request?.headers?.get("accept-language");
		setSSRRequestContext({
			cookieRosettaLang: cookie ?? null,
			acceptLanguage: accept ?? null,
		});
	} catch (_e) {
		/* ignore — 拿不到上下文也不阻塞渲染，后端会用默认 zh 兜底 */
	}
}

/**
 * 清理 SSR 注入的语言上下文（可选，单次请求结束调用一次，
 * 主要防止在非 V8 单并发运行时（如 Node worker_threads）出现污染）。
 */
export function clearAstroLangContext(): void {
	try {
		setSSRRequestContext(null);
	} catch (_e) { /* ignore */ }
}
