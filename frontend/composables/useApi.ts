/**
 * 通用 $api composable — 对应 Astro frontend/src/api/client.ts 全家桶：
 *   - apiGet / apiPost / apiPut / apiPatch / apiDelete / apiUpload
 *   - 支持 params camelCase → snake_case（使用自定义 snakeizeKeys/camelizeKeys）
 *   - SSR：runtimeConfig.apiBaseUrlSsr 直连后端（不走相对 URL）
 *   - 浏览器：useRuntimeConfig().public.apiBaseUrl 为空 → 同源 /api（Nitro 代理）
 *   - 401 自动清空 Auth Store + 跳 /login
 *   - 统一超时（params._timeout）
 */
import { useAuthStore } from "@stores/auth";

// ===================== 工具：camelCase ↔ snake_case =====================
const SNAKE_RE = /([A-Z]+)/g;
function snakeizeKey(k: string): string {
  if (!k) return k;
  return k.replace(SNAKE_RE, (_, g1: string) =>
    g1.length === 1 ? `_${g1.toLowerCase()}` : `_${g1.toLowerCase()}`
  ).replace(/^_/, "");
}
const CAMEL_RE = /_([a-z0-9])/g;
function camelizeKey(k: string): string {
  if (!k) return k;
  return k.replace(CAMEL_RE, (_m, g1: string) => g1.toUpperCase());
}
export function snakeizeKeys<T = any>(obj: T): any {
  if (obj == null) return obj;
  if (Array.isArray(obj)) return obj.map(snakeizeKeys);
  if (typeof obj !== "object") return obj;
  const out: Record<string, any> = {};
  for (const k of Object.keys(obj as any)) {
    out[snakeizeKey(k)] = snakeizeKeys((obj as any)[k]);
  }
  return out;
}
export function camelizeKeys<T = any>(obj: T): any {
  if (obj == null) return obj;
  if (Array.isArray(obj)) return obj.map(camelizeKeys);
  if (typeof obj !== "object") return obj;
  const out: Record<string, any> = {};
  for (const k of Object.keys(obj as any)) {
    out[camelizeKey(k)] = camelizeKeys((obj as any)[k]);
  }
  return out;
}

// ===================== 语言映射 =====================
const LANG_MAP: Record<string, string> = {
  zh_cn: "zh", "zh-cn": "zh", zh: "zh", zh_hans: "zh",
  zh_tw: "zh_Hant", "zh-tw": "zh_Hant", zh_hant: "zh_Hant",
  en: "en", en_us: "en", en_gb: "en",
  ja: "ja", ja_jp: "ja", jp: "ja",
};
export function getBackendLang(frontendLang: string): string {
  const k = frontendLang.toLowerCase().replace(/-/g, "_");
  return LANG_MAP[k] || "zh";
}
function readCurrentLang(): string {
  if (import.meta.client) {
    try {
      const m = /(?:^|;\s*)rosetta_lang=([^;]+)/.exec(document.cookie || "");
      if (m?.[1]) return getBackendLang(decodeURIComponent(m[1]));
      const saved = localStorage.getItem("lang");
      if (saved) return getBackendLang(saved);
    } catch {
      /* ignore */
    }
    const attr = document.documentElement.getAttribute("data-lang");
    if (attr) return getBackendLang(attr);
  } else {
    const c = useCookie<string | undefined>("rosetta_lang", { default: () => undefined });
    if (c.value) return getBackendLang(c.value);
  }
  return "zh";
}

// ===================== URL 构造 + 尾斜杠规范化 =====================
function buildUrl(
  path: string,
  params?: Record<string, any> | undefined
): { url: string; timeoutMs?: number } {
  const runtime = useRuntimeConfig();
  const isSsr = import.meta.server;

  let base: string;
  if (isSsr) {
    base = (runtime as any).apiBaseUrlSsr || "http://127.0.0.1:8000";
    if (!base.endsWith("/api")) base += "/api";
  } else {
    base = (runtime.public as any).apiBaseUrl?.trim() || "";
    // 空 base → 使用同源 /api（Nitro 代理）
    if (base && !base.endsWith("/api") && !base.endsWith("/api/")) {
      base = base.replace(/\/$/, "") + "/api";
    }
    if (!base) base = "/api";
  }

  let url = path.startsWith("http") ? path : `${base.replace(/\/$/, "")}/${path.replace(/^\//, "")}`;

  // _timeout 独立处理（不进 query string）
  let timeoutMs: number | undefined;
  const safeParams: Record<string, any> = {};
  if (params) {
    for (const [k, v] of Object.entries(params)) {
      if (k === "_timeout") {
        if (typeof v === "number" && v > 0) timeoutMs = v;
        continue;
      }
      if (v !== undefined && v !== null) safeParams[k] = v;
    }
  }
  const norm = snakeizeKeys(safeParams);

  // URL 规范化：无扩展名的 API 路径补尾斜杠
  try {
    const dummyBase = url.startsWith("http") ? undefined : "http://127.0.0.1";
    const u = new URL(url, dummyBase);
    const pn = u.pathname;
    const last = pn.split("/").pop() ?? "";
    const hasExt = last.includes(".");
    if (!pn.endsWith("/") && !hasExt) u.pathname = pn + "/";
    url = url.startsWith("http") ? u.toString() : u.pathname + u.search + u.hash;
  } catch {
    /* 失败保持原样 */
  }

  const qs = new URLSearchParams();
  let hasLang = false;
  if (norm) {
    for (const [k, v] of Object.entries(norm)) {
      qs.append(k, String(v));
      if (k.toLowerCase() === "lang") hasLang = true;
    }
  }
  if (!hasLang) qs.append("lang", readCurrentLang());
  const qsStr = qs.toString();
  if (qsStr) url += `${url.includes("?") ? "&" : "?"}${qsStr}`;

  return { url, timeoutMs };
}

// ===================== 核心请求 =====================
export interface ApiResponse<T> {
  code: number;
  message: string;
  data: T;
}
export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  pageSize: number;
  totalPages: number;
}

export function isAbortedFetchError(e: any): boolean {
  if (!e) return false;
  return !!(e as any).__isAbortedFetch || e?.name === "AbortError";
}

/**
 * 统一请求封装（使用 $fetch from ofetch / Nuxt）
 * 与 Astro client.apiFetch 保持等价语义：
 *   - body → snakeizeKeys
 *   - 响应 JSON → camelizeKeys
 *   - 401 → 自动登出 + 跳转登录
 */
export async function apiFetch<T>(
  path: string,
  options: Omit<Parameters<typeof $fetch<T>>[1], "body"> & { body?: any } = {},
  params?: Record<string, any>
): Promise<T> {
  const { url, timeoutMs } = buildUrl(path, params);
  const auth = useAuthStore();
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(options.headers || {}),
  };
  if (auth.accessToken) headers.Authorization = `Bearer ${auth.accessToken}`;
  if (auth.csrfToken) {
    headers["X-CSRF-Token"] = auth.csrfToken;
    if (import.meta.client) {
      document.cookie = `csrf_token=${encodeURIComponent(auth.csrfToken)}; path=/; SameSite=Lax`;
    }
  }

  let body: any = options.body;
  if (body !== undefined && typeof body !== "string") {
    try {
      body = JSON.stringify(snakeizeKeys(body));
    } catch {
      body = JSON.stringify(body);
    }
  } else if (typeof body === "string") {
    try {
      const parsed = JSON.parse(body);
      body = JSON.stringify(snakeizeKeys(parsed));
    } catch {
      /* 非 JSON 原样 */
    }
  }

  try {
    const raw = await $fetch<any>(url, {
      ...options,
      headers,
      body: body as any,
      timeout: timeoutMs ?? 30_000,
      credentials: "include",
    });
    return camelizeKeys(raw) as T;
  } catch (err: any) {
    const isAbort =
      err?.name === "AbortError" ||
      err?.cause?.name === "AbortError" ||
      /cancel|abort/i.test(err?.message || "");

    const status = err?.response?.status ?? err?.status ?? 0;
    if (status === 401) {
      auth.logout();
      if (import.meta.client && !window.location.pathname.includes("/login")) {
        await navigateTo("/login", { replace: true });
      }
      throw new Error("登录已过期，请重新登录");
    }

    // 规范化为 Error：优先取后端 message/detail
    let message = err?.message || `HTTP ${status || "Error"}`;
    try {
      const data = err?.response?._data ?? err?.data;
      const norm = camelizeKeys(data);
      if (norm?.detail) message = norm.detail;
      if (norm?.message) message = norm.message;
    } catch {
      /* ignore */
    }
    const e = new Error(message);
    (e as any).name = isAbort ? "AbortError" : err?.name || "FetchError";
    (e as any).__isAbortedFetch = isAbort && !timeoutMs;
    (e as any).status = status;
    throw e;
  }
}

export function apiGet<T>(path: string, params?: Record<string, any>) {
  return apiFetch<T>(path, { method: "GET" }, params);
}
export function apiPost<T>(
  path: string,
  body?: any,
  params?: Record<string, any>
) {
  return apiFetch<T>(path, { method: "POST", body }, params);
}
export function apiPut<T>(
  path: string,
  body?: any,
  params?: Record<string, any>
) {
  return apiFetch<T>(path, { method: "PUT", body }, params);
}
export function apiPatch<T>(
  path: string,
  body?: any,
  params?: Record<string, any>
) {
  return apiFetch<T>(path, { method: "PATCH", body }, params);
}
export function apiDelete<T>(path: string, params?: Record<string, any>) {
  return apiFetch<T>(path, { method: "DELETE" }, params);
}

/** 文件上传（multipart/form-data）—— 不做 snakeize body，保持 File 原样 */
export async function apiUpload<T>(
  path: string,
  file: File,
  fieldName = "file",
  params?: Record<string, any>
): Promise<T> {
  const { url, timeoutMs } = buildUrl(path, params);
  const auth = useAuthStore();

  const fd = new FormData();
  fd.append(fieldName, file);
  const headers: Record<string, string> = {};
  if (auth.accessToken) headers.Authorization = `Bearer ${auth.accessToken}`;
  if (auth.csrfToken) {
    headers["X-CSRF-Token"] = auth.csrfToken;
    if (import.meta.client) {
      document.cookie = `csrf_token=${encodeURIComponent(auth.csrfToken)}; path=/; SameSite=Lax`;
    }
  }
  try {
    const raw = await $fetch<any>(url, {
      method: "POST",
      headers,
      body: fd,
      timeout: timeoutMs ?? 120_000,
      credentials: "include",
    });
    return camelizeKeys(raw) as T;
  } catch (err: any) {
    const message = err?.message || "上传失败";
    throw new Error(message);
  }
}

// =============================================================
// 兼容 Astro 原 api/* client.* 结构（旧代码迁移时无需改符号）
// =============================================================
async function clientRequest(
  method: "GET" | "POST" | "PUT" | "PATCH" | "DELETE",
  rawPath: string,
  body?: any,
  opts?: { headers?: Record<string, string> }
) {
  const res = await apiFetch<any>(
    rawPath,
    {
      method,
      body,
      headers: opts?.headers,
    }
  );
  return {
    data: res,
    status: 200,
    statusText: "OK",
    headers: new Headers(),
  };
}
export const client = {
  get: (u: string, opts?: { headers?: Record<string, string> }) =>
    clientRequest("GET", u, undefined, opts),
  post: (u: string, body?: any, opts?: { headers?: Record<string, string> }) =>
    clientRequest("POST", u, body, opts),
  put: (u: string, body?: any, opts?: { headers?: Record<string, string> }) =>
    clientRequest("PUT", u, body, opts),
  patch: (u: string, body?: any, opts?: { headers?: Record<string, string> }) =>
    clientRequest("PATCH", u, body, opts),
  delete: (u: string, opts?: { headers?: Record<string, string> }) =>
    clientRequest("DELETE", u, undefined, opts),
};
export const adminApi = client;
export const blogApi = client;
export const userApi = client;
