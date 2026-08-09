// API base从环境变量获取，siteConfig暂时用于兼容
// exactOptionalPropertyTypes: true — 不声明 lang 为可选属性，避免精确类型检查报错，
// 同时后续读取 siteConfig.lang 用 narrow 的方式（undefined-check 后读取）
const siteConfig: { site_url: string; lang?: string | undefined } = {
	site_url: "",
};

import { camelizeKeys, snakeizeKeys } from "../utils/camelize";

/**
 * SSR 环境下 Node.js 的 fetch 不支持相对路径（必须是完整 URL 带协议）。
 * - 服务端渲染/构建阶段：直接走后端地址（跳过 Astro/Vite 同源代理）
 * - 浏览器端：仍然用同源 "/api"，由 vite.server.proxy 代理到后端，免 CORS
 */
const SSR_BACKEND_BASE = (() => {
	const env = (import.meta as any).env?.ROSETTA_API_BASE;
	if (typeof env === "string" && env.trim().length > 0)
		return env.trim().replace(/\/$/, "");
	const internal =
		(globalThis as any).process?.env?.ROSETTA_API_BASE ??
		(globalThis as any).process?.env?.API_BASE_URL;
	if (typeof internal === "string" && internal.trim().length > 0)
		return internal.trim().replace(/\/$/, "");
	// 开发机 Windows 上 localhost 可能解析到 IPv6 [::1] 而后端只监听 127.0.0.1，
	// SSR 阶段直连后端时用 127.0.0.1 避免偶发 ECONNREFUSED
	// 注意：后端 API 都挂载在 /api 前缀下，所以这里要加上 /api
	return "http://127.0.0.1:8000/api";
})();

const IS_SSR = typeof (globalThis as any).window === "undefined";

/**
 * API 基础地址
 *
 * 规则:
 * 1. 优先使用环境变量 ROSETTA_API_BASE (显式配置，生产/部署用绝对 URL)
 * 2. 开发模式 + 浏览器端: 使用 "/api"（同源），走 astro.config.mjs vite.server.proxy
 *    → 自动代理到 http://localhost:8000，避免浏览器 CORS 预检失败
 * 3. SSR/Node.js 环境: 使用绝对 SSR_BACKEND_BASE，避免相对 URL 在 Node.js fetch 抛 ERR_INVALID_URL
 * 4. 生产构建 + 浏览器端: 保持 "/api"（同源），分域部署时通过 ROSETTA_API_BASE 指定
 */
export const API_BASE: string = IS_SSR
	? SSR_BACKEND_BASE
	: (() => {
			const env = (import.meta as any).env?.ROSETTA_API_BASE;
			if (typeof env === "string" && env.trim().length > 0) {
				return env.trim().replace(/\/$/, "");
			}
			return "/api";
		})();

const TOKEN_KEY = "rosetta_token";
const REFRESH_TOKEN_KEY = "rosetta_refresh_token";

let authToken: string | null = null;
let refreshToken: string | null = null;

const LANG_MAP_FRONTEND_TO_BACKEND: Record<string, string> = {
	zh_cn: "zh",
	"zh-cn": "zh",
	zh: "zh",
	zh_hans: "zh",
	zh_tw: "zh_Hant",
	"zh-tw": "zh_Hant",
	zh_hant: "zh_Hant",
	en: "en",
	en_us: "en",
	en_gb: "en",
	ja: "ja",
	ja_jp: "ja",
	jp: "ja",
};

export function getBackendLang(frontendLang: string): string {
	const key = frontendLang.toLowerCase().replace(/-/g, "_");
	return LANG_MAP_FRONTEND_TO_BACKEND[key] || "zh";
}

/**
 * SSR 请求上下文（可选）：在 Astro 页面 SSR 渲染阶段，由页面显式注入
 * `Astro.cookies.get("rosetta_lang")` 与 `Astro.request.headers.get("Accept-Language")`，
 * 让 SSR 直连后端时的 ?lang= 参数与浏览器请求（带 cookie / header）拿到一致的内容。
 *
 * 生命周期：单次 SSR 渲染过程中写入、构建完成后由 Astro GC，不会跨用户污染。
 */
type SSRRequestContext = {
	cookieRosettaLang?: string | null;
	acceptLanguage?: string | null;
};
let ssrCtx: SSRRequestContext | null = null;
export function setSSRRequestContext(ctx: SSRRequestContext | null): void {
	ssrCtx = ctx ?? null;
}

function readCookieLangRaw(): string | null {
	// 1) SSR：优先取注入的 cookie rosetta_lang（由 Astro.cookies 传入，最准确）
	if (ssrCtx?.cookieRosettaLang) return ssrCtx.cookieRosettaLang;
	// 2) 浏览器：从 document.cookie 读取
	if (typeof document !== "undefined") {
		try {
			const m = /(?:^|;\s*)rosetta_lang=([^;]+)/.exec(document.cookie || "");
			if (m && m[1]) return decodeURIComponent(m[1]);
		} catch (_e) { /* ignore */ }
	}
	return null;
}

function readHtmlDataLang(): string | null {
	if (typeof document !== "undefined") {
		const attr = document.documentElement.getAttribute("data-lang");
		if (attr) return attr;
	}
	return null;
}

function readAcceptLang(): string | null {
	if (ssrCtx?.acceptLanguage) return ssrCtx.acceptLanguage;
	return null;
}

export function getCurrentLang(): string {
	// 1. Cookie（用户持久化偏好）
	const cookie = readCookieLangRaw();
	if (cookie) {
		const mapped = getBackendLang(cookie);
		if (mapped) return mapped;
	}
	// 2. localStorage（LangSwitcher 会同步写，兼容老数据）
	try {
		if (typeof localStorage !== "undefined") {
			const saved = localStorage.getItem("lang");
			if (saved) {
				const mapped = getBackendLang(saved);
				if (mapped) return mapped;
			}
		}
	} catch {
		/* ignore */
	}
	// 3. html[data-lang]（SSR 注入的当前语言）
	const html = readHtmlDataLang();
	if (html) {
		const mapped = getBackendLang(html);
		if (mapped) return mapped;
	}
	// 4. Accept-Language（SSR 注入的请求头，或后端自己也会读，这里兜底）
	const accept = readAcceptLang();
	if (accept) {
		const first = accept.split(",")[0]?.trim()?.split(";")[0];
		if (first) {
			const mapped = getBackendLang(first);
			if (mapped) return mapped;
		}
	}
	// 5. siteConfig.lang（site-level 默认）
	try {
		if (siteConfig && typeof siteConfig.lang === "string") {
			return getBackendLang(siteConfig.lang);
		}
	} catch {
		/* ignore */
	}
	return "zh";
}

export function getCsrfToken(): string | null {
	try {
		if (typeof document !== "undefined") {
			const meta = document.querySelector('meta[name="csrf-token"]');
			return meta?.getAttribute("content") || null;
		}
	} catch {
		/* ignore */
	}
	return null;
}

// 模块加载时从 localStorage 恢复 token
try {
	if (typeof localStorage !== "undefined") {
		authToken = localStorage.getItem(TOKEN_KEY);
		refreshToken = localStorage.getItem(REFRESH_TOKEN_KEY);
	}
} catch {
	/* ignore */
}

export function setAuthToken(token: string | null) {
	authToken = token;
	try {
		if (typeof localStorage !== "undefined") {
			if (token) {
				localStorage.setItem(TOKEN_KEY, token);
			} else {
				localStorage.removeItem(TOKEN_KEY);
			}
		}
	} catch {
		/* ignore */
	}
}

export function setRefreshToken(token: string | null) {
	refreshToken = token;
	try {
		if (typeof localStorage !== "undefined") {
			if (token) {
				localStorage.setItem(REFRESH_TOKEN_KEY, token);
			} else {
				localStorage.removeItem(REFRESH_TOKEN_KEY);
			}
		}
	} catch {
		/* ignore */
	}
}

export function getAuthToken(): string | null {
	if (authToken) return authToken;
	try {
		if (typeof localStorage !== "undefined") {
			authToken = localStorage.getItem(TOKEN_KEY);
			return authToken;
		}
	} catch {
		/* ignore */
	}
	return null;
}

export function getRefreshToken(): string | null {
	if (refreshToken) return refreshToken;
	try {
		if (typeof localStorage !== "undefined") {
			refreshToken = localStorage.getItem(REFRESH_TOKEN_KEY);
			return refreshToken;
		}
	} catch {
		/* ignore */
	}
	return null;
}

export function clearAuth() {
	setAuthToken(null);
	setRefreshToken(null);
}

/**
 * 判断错误是否由"页面导航/组件销毁时浏览器主动取消 fetch"造成。
 * 这类 Abort 不是真实 Bug，调用端可选择静默吞掉，避免控制台噪音。
 */
export function isAbortedFetchError(e: any): boolean {
	if (!e) return false;
	return !!(e as any).__isAbortedFetch || e?.name === "AbortError";
}

export interface ApiResponse<T> {
	code: number;
	message: string;
	data: T;
}

export interface PaginatedResponse<T> {
	items: T[];
	total: number;
	page: number;
	page_size: number;
	total_pages: number;
}

function buildUrl(path: string, params?: Record<string, any>): string {
	let url = path.startsWith("http") ? path : `${API_BASE}${path}`;
	// Astro output: static + trailingSlash: "always" → 开发代理上不带尾斜杠的 API 请求
	// 会被 Astro 前端路由层当作前端页面处理，抛出前端 404（"Do you want to go to /xxx/? instead?"）。
	// 这里将所有"无文件扩展名"的路径规范化为以 / 结尾（在 query string 之前添加），
	// 确保 Vite 代理的 "/api" 路由能正确命中、FastAPI 路由也对末尾斜杠宽容。
	try {
		const dummyBase = url.startsWith("http") ? undefined : "http://127.0.0.1";
		const u = new URL(url, dummyBase);
		const pn = u.pathname;
		const lastSegment = pn.split("/").pop() ?? "";
		const hasExtension = lastSegment.includes(".");
		if (!pn.endsWith("/") && !hasExtension) {
			u.pathname = pn + "/";
		}
		url = url.startsWith("http") ? u.toString() : u.pathname + u.search + u.hash;
	} catch {
		/* URL parse 失败时保持原样（兜底，避免破坏请求） */
	}
	const qs = new URLSearchParams();
	let hasLang = false;
	const normParams = params ? snakeizeKeys(params) : undefined;
	if (normParams) {
		for (const [k, v] of Object.entries(normParams)) {
			if (v !== undefined && v !== null) {
				qs.append(k, String(v));
				if (k.toLowerCase() === "lang") hasLang = true;
			}
		}
	}
	if (!hasLang) {
		qs.append("lang", getCurrentLang());
	}
	const qsStr = qs.toString();
	if (qsStr) url += `${url.includes("?") ? "&" : "?"}${qsStr}`;
	return url;
}

export async function apiFetch<T>(
	path: string,
	options: RequestInit = {},
	params?: Record<string, any>,
): Promise<T> {
	// 允许 params._timeout 作为毫秒级超时；不进入 query string
	const _timeout: number | undefined =
		params &&
		typeof (params as any)._timeout === "number" &&
		(params as any)._timeout > 0
			? (params as any)._timeout
			: undefined;
	const qsParams: Record<string, any> | undefined = params
		? (Object.fromEntries(
				Object.entries(params).filter(([k]) => k !== "_timeout"),
			) as Record<string, any>)
		: undefined;
	const url = buildUrl(path, qsParams);

	const headerObj: Record<string, string> = {
		"Content-Type": "application/json",
	};
	if (options.headers) {
		if (typeof (options.headers as any).forEach === "function") {
			(options.headers as Headers).forEach((v, k) => {
				headerObj[k] = v;
			});
		} else if (Array.isArray(options.headers)) {
			// noUncheckedIndexedAccess + exactOptionalPropertyTypes:
			// 解构出来的 k/v 可能 undefined（非键元组时），需要过滤
			for (const kv of options.headers as string[][]) {
				const k = kv?.[0];
				const v = kv?.[1];
				if (typeof k === "string" && typeof v === "string") headerObj[k] = v;
			}
		} else {
			Object.assign(headerObj, options.headers);
		}
	}
	const headers = headerObj;

	const token = getAuthToken();
	if (token) {
		headers.Authorization = `Bearer ${token}`;
	}

	const csrfToken = getCsrfToken();
	if (csrfToken) {
		headers["X-CSRF-Token"] = csrfToken;
		if (typeof document !== "undefined") {
			document.cookie = `csrf_token=${csrfToken}; path=/; SameSite=Lax`;
		}
	}

	let body: any = options.body;
	if (body !== undefined && typeof body === "string") {
		try {
			const parsed = JSON.parse(body);
			body = JSON.stringify(snakeizeKeys(parsed));
		} catch {
			/* ignore */
		}
	}

	// 统一超时（AbortController，同时兼容浏览器 + Node 18+）
	let controller: AbortController | null = null;
	let timeoutId: any = null;
	const init: RequestInit = { ...options, headers, body };
	if (_timeout && typeof AbortController !== "undefined") {
		controller = new AbortController();
		init.signal = controller.signal;
		timeoutId = setTimeout(() => controller?.abort(), _timeout);
	}

	let res: Response;
	try {
		res = await fetch(url, init);
	} catch (err: any) {
		// fetch 层失败（DNS、CORS 预检、AbortSignal 超时等）—— res 永远不会被赋值，
		// 直接在这里规范化为 Error 抛出，避免后面读取 res.status 触发 undefined 错误。
		const isAbort =
			(err && (err.name === "AbortError" || err.name === "TimeoutError")) ||
			(err instanceof DOMException && err.name === "AbortError");

		// ============================================================
		// 特别处理：页面导航（Swup/整页刷新 / 组件销毁）导致浏览器主动 ABORT 请求。
		// 这类请求取消是"正常的生命周期事件"，不应该被当作错误抛给上层，
		// 否则会在控制台留下一堆 "net::ERR_ABORTED"、"请求超时" 等无意义噪音，
		// 并让调用者的 catch 里 console.error/console.warn 误以为出了 Bug。
		// 这里抛出一个带标记的 Error：上层用 isAbortedFetchError() 判断后可
		// 选择静默吞掉（例如 DashboardPanel、dynamic-config 等）。
		// ============================================================
		const isExplicitTimeout = !!_timeout; // 明确是应用层 _timeout 触发的 Abort
		const isNavigationAbort = isAbort && !isExplicitTimeout;

		const e = new Error(
			isAbort
				? isExplicitTimeout
					? "请求超时，请检查网络或稍后重试"
					: "请求已取消（页面导航或组件销毁）"
				: err?.message || "网络错误",
		);
		(e as any).name = isAbort ? "AbortError" : "NetworkError";
		(e as any).__isAbortedFetch = isNavigationAbort;
		throw e;
	} finally {
		if (timeoutId) clearTimeout(timeoutId);
	}

	if (res.status === 401) {
		clearAuth();
		if (
			typeof window !== "undefined" &&
			!window.location.pathname.includes("/login")
		) {
			window.location.href = "/login/";
		}
		throw new Error("登录已过期，请重新登录");
	}

	if (!res.ok) {
		let message = `HTTP ${res.status}`;
		try {
			const err = await res.json();
			const errNorm = camelizeKeys(err);
			if (errNorm?.detail) message = errNorm.detail;
			if (errNorm?.message) message = errNorm.message;
		} catch {
			/* ignore */
		}
		throw new Error(message);
	}

	if (res.status === 204) return null as T;

	try {
		const raw = await res.json();
		return camelizeKeys(raw) as T;
	} catch {
		return null as T;
	}
}

export async function apiGet<T>(path: string, params?: Record<string, any>) {
	return apiFetch<T>(path, { method: "GET" }, params);
}

export async function apiPost<T>(
	path: string,
	body?: any,
	params?: Record<string, any>,
) {
	return apiFetch<T>(
		path,
		{
			method: "POST",
			// exactOptionalPropertyTypes: true 模式下，RequestInit.body 不接受 undefined（仅接受 BodyInit | null）
			// 之前写 undefined 会导致 TS2379，改用 null 空 body 语义完全等价
			body: body !== undefined ? JSON.stringify(body) : null,
		},
		params,
	);
}

export async function apiPut<T>(
	path: string,
	body?: any,
	params?: Record<string, any>,
) {
	return apiFetch<T>(
		path,
		{
			method: "PUT",
			body: body !== undefined ? JSON.stringify(body) : null,
		},
		params,
	);
}

export async function apiDelete<T>(path: string, params?: Record<string, any>) {
	return apiFetch<T>(path, { method: "DELETE" }, params);
}

export async function apiPatch<T>(
	path: string,
	body?: any,
	params?: Record<string, any>,
) {
	return apiFetch<T>(
		path,
		{
			method: "PATCH",
			body: body !== undefined ? JSON.stringify(body) : null,
		},
		params,
	);
}

export async function apiUpload<T>(
	path: string,
	file: File,
	fieldName = "file",
	params?: Record<string, any>,
) {
	const formData = new FormData();
	formData.append(fieldName, file);
	const url = buildUrl(
		path.startsWith("http") ? path : `${API_BASE}${path}`,
		params,
	);
	const headers: Record<string, string> = {};
	const token = getAuthToken();
	if (token) headers.Authorization = `Bearer ${token}`;
	const csrfToken = getCsrfToken();
	if (csrfToken) {
		headers["X-CSRF-Token"] = csrfToken;
		if (typeof document !== "undefined") {
			document.cookie = `csrf_token=${csrfToken}; path=/; SameSite=Lax`;
		}
	}
	const res = await fetch(url, {
		method: "POST",
		headers,
		body: formData,
	});
	if (!res.ok) throw new Error(`HTTP ${res.status}`);
	return res.json() as Promise<T>;
}

type AxiosOpts = { headers?: Record<string, string> };
async function clientRequest(
	method: "GET" | "POST" | "PUT" | "PATCH" | "DELETE",
	rawPath: string,
	body?: any,
	opts?: AxiosOpts,
) {
	const path = rawPath.startsWith(API_BASE)
		? rawPath.slice(API_BASE.length)
		: rawPath;
	const url = buildUrl(path);
	const headerObj: Record<string, string> = {};
	const isFormData =
		typeof FormData !== "undefined" && body instanceof FormData;
	if (!isFormData) headerObj["Content-Type"] = "application/json";
	const token = getAuthToken();
	if (token) headerObj.Authorization = `Bearer ${token}`;
	const csrfToken = getCsrfToken();
	if (csrfToken) {
		headerObj["X-CSRF-Token"] = csrfToken;
		if (typeof document !== "undefined") {
			document.cookie = `csrf_token=${csrfToken}; path=/; SameSite=Lax`;
		}
	}
	if (opts?.headers) Object.assign(headerObj, opts.headers);
	const init: RequestInit = {
		method,
		headers: headerObj,
	};
	if (body !== undefined && method !== "GET") {
		if (isFormData) {
			init.body = body as any;
		} else {
			init.body = JSON.stringify(snakeizeKeys(body));
		}
	}
	const r = await fetch(url, init);
	if (r.status === 401) {
		clearAuth();
		if (
			typeof window !== "undefined" &&
			!window.location.pathname.includes("/login")
		) {
			window.location.href = "/login/";
		}
		throw new Error("登录已过期");
	}
	let data: any = null;
	try {
		const raw = await r.json();
		data = camelizeKeys(raw);
	} catch {
		try {
			data = await r.text();
		} catch {
			/* empty */
		}
	}
	if (!r.ok) {
		const msg =
			(typeof data === "object" && data?.detail) ||
			(typeof data === "object" && data?.message) ||
			`HTTP ${r.status}`;
		throw new Error(msg);
	}
	return {
		data,
		status: r.status,
		statusText: r.statusText,
		headers: r.headers,
	};
}

export const client = {
	get: (u: string, opts?: AxiosOpts) =>
		clientRequest("GET", u, undefined, opts),
	post: (u: string, body?: any, opts?: AxiosOpts) =>
		clientRequest("POST", u, body, opts),
	put: (u: string, body?: any, opts?: AxiosOpts) =>
		clientRequest("PUT", u, body, opts),
	patch: (u: string, body?: any, opts?: AxiosOpts) =>
		clientRequest("PATCH", u, body, opts),
	delete: (u: string, opts?: AxiosOpts) =>
		clientRequest("DELETE", u, undefined, opts),
};

// Admin 面板专用快捷引用（目前直接复用 client 实现；保留符号以便后续加鉴权/刷新/日志拦截）
export const adminApi = client;
export const blogApi = client;
export const userApi = client;
