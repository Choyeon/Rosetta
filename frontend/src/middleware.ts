// =============================================================
// Astro SSR Middleware：在任意页面渲染**之前**执行
// 用途：
//   1. OOBE 未完成 → 自动 302 到 /oobe/
//      （为什么不在 Layout.astro 里做？因为 Layout 是子组件，
//       此时 response stream 已经开启，Astro.redirect 会触发
//       ResponseSentError，结果页面只会渲染 <script src="/@vite/client"/>）
//   2. OOBE 已完成 → 如果访问 /oobe[/]，302 到首页，避免误访问
// =============================================================
import { defineMiddleware } from "astro:middleware";

const SSR_API_BASE =
	import.meta.env.API_BASE_URL_SSR ||
	import.meta.env.API_BASE_URL ||
	"http://127.0.0.1:8000";
const OOBE_PATH = "/oobe/";
const OOBE_PATH_ALT = "/oobe";
// 带 10 秒内存缓存：同一请求同一进程 10 秒内不用再去问后端，
// 避免每个静态资源/page 请求都打一次 /api/oobe/status。
let cacheTs = 0;
let cacheVal: boolean | null = null;
const CACHE_MS = 10 * 1000;

async function queryOobeComplete(): Promise<boolean> {
	const now = Date.now();
	if (cacheVal !== null && now - cacheTs < CACHE_MS) return cacheVal;
	try {
		const resp = await fetch(`${SSR_API_BASE}/api/oobe/status`, {
			method: "GET",
			headers: { Accept: "application/json" },
			// node 18+: AbortSignal.timeout 存在，给短超时避免 SSR 卡壳
			signal: (globalThis as any).AbortSignal?.timeout?.(1500) as
				| AbortSignal
				| undefined,
		} as any);
		let result = false;
		if (resp.ok) {
			try {
				const json: any = await resp.json();
				result = !!json?.oobe_complete;
			} catch (_) { /* ignore parse */ }
		}
		cacheTs = now;
		cacheVal = result;
		return result;
	} catch (_) {
		// 后端没启动 → 不做跳转，留给前端 JS 兜底
		// （否则会误跳导致 oobe 页本身也拿不到后端接口）
		cacheTs = now;
		cacheVal = null;
		return true; // 暂时当作 complete，跳过 SSR 跳转
	}
}

export const onRequest = defineMiddleware(async (context, next) => {
	const pathname = context.url.pathname;
	// 静态资源 / api 路由 不处理：只处理 .html / 无扩展的页面请求
	if (
		pathname.startsWith("/_astro/") ||
		pathname.startsWith("/@") ||
		pathname.startsWith("/node_modules/") ||
		/\/[^/]+\.[a-zA-Z0-9]{1,8}$/.test(pathname) && !/\/(index|oobe)$/i.test(pathname.replace(/^.*\//, ""))
	) {
		// 但 /api/allPostMeta.json 这类 .json 不走 here（由 Astro pages 路由决定）
		if (/\.(png|jpe?g|webp|gif|svg|css|js|ts|mjs|cjs|woff2?|ttf|ico|map)$/i.test(pathname)) {
			return next();
		}
	}

	const isOobePage =
		pathname === OOBE_PATH ||
		pathname === OOBE_PATH_ALT ||
		pathname.startsWith(OOBE_PATH);

	const oobeComplete = await queryOobeComplete();

	if (!oobeComplete && !isOobePage) {
		return context.redirect(OOBE_PATH, 302);
	}
	if (oobeComplete && isOobePage) {
		// OOBE 已经完成了，再访问 /oobe 没意义 → 回首页
		return context.redirect("/", 302);
	}
	return next();
});
