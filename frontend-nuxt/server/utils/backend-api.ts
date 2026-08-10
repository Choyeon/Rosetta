/**
 * Nitro 后端代理工具 — 统一将浏览器端 /api/** 或 SSR $fetch("/api/**")
 * 转发到真实 FastAPI 后端 http://127.0.0.1:8000/api/v1 (或配置 API_BASE_URL)
 *
 * 能力：
 *  - 从 rosetta_token cookie 读取 Bearer access_token
 *  - 注入 Authorization / X-CSRF-Token / Accept-Language
 *  - 401 响应 → 自动清除 rosetta_token / rosetta_refresh_token cookie
 *  - 响应 snake_case body → camelize（等价 useApi.ts 的客户端转换）
 *  - 请求 query camelCase → snakeize
 */
import type { H3Event } from "h3";

// ===================== camel/snake 工具（与 composables/useApi.ts 等价，但 node 端不重 import） =====================
const SNAKE_RE = /([A-Z]+)/g;
const CAMEL_RE = /_([a-z0-9])/g;
function snakeKey(k: string) {
  return k.replace(SNAKE_RE, (_m: string, g1: string) =>
    g1.length === 1 ? `_${g1.toLowerCase()}` : `_${g1.toLowerCase()}`
  ).replace(/^_/, "");
}
function camelKey(k: string) {
  return k.replace(CAMEL_RE, (_m: string, g1: string) => g1.toUpperCase());
}
export function snakeizeKeys<T>(obj: T): any {
  if (obj == null) return obj;
  if (Array.isArray(obj)) return obj.map(snakeizeKeys);
  if (typeof obj !== "object") return obj;
  const out: Record<string, any> = {};
  for (const k of Object.keys(obj as any)) out[snakeKey(k)] = snakeizeKeys((obj as any)[k]);
  return out;
}
export function camelizeKeys<T>(obj: T): any {
  if (obj == null) return obj;
  if (Array.isArray(obj)) return obj.map(camelizeKeys);
  if (typeof obj !== "object") return obj;
  const out: Record<string, any> = {};
  for (const k of Object.keys(obj as any)) out[camelKey(k)] = camelizeKeys((obj as any)[k]);
  return out;
}

// ===================== 基础 URL =====================
export function backendBase(): string {
  const runtime = useRuntimeConfig();
  const raw = (runtime as any).apiBaseUrlSsr || (runtime as any).API_BASE_URL || "http://127.0.0.1:8000";
  // 规范化：追加 /api/v1 如果不存在
  let base = raw.replace(/\/$/, "");
  if (!/\/api(\/v1)?$/.test(base)) base += "/api/v1";
  return base;
}

// ===================== 语言（cookie：rosetta_lang） =====================
function readLangCookie(e: H3Event) {
  return parseCookies(e)["rosetta_lang"] || "zh";
}
const LANG_MAP: Record<string, string> = {
  zh_cn: "zh", zh: "zh", zh_hans: "zh",
  zh_tw: "zh_Hant", zh_hant: "zh_Hant",
  en: "en", en_us: "en",
  ja: "ja", ja_jp: "ja",
};
function backendLang(lang: string) {
  return LANG_MAP[lang.toLowerCase().replace(/-/g, "_")] || "zh";
}

// ===================== Cookie 清理（401 自动登出） =====================
export function clearAuthCookies(e: H3Event) {
  const opts = { path: "/", httpOnly: false, sameSite: "lax" as const };
  deleteCookie(e, "rosetta_token", opts);
  deleteCookie(e, "rosetta_refresh_token", opts);
  deleteCookie(e, "csrf_token", opts);
}

// ===================== 核心：后端代理 fetch =====================
export interface ProxyOptions {
  /** 附加到后端路径前的子段；默认空。例："/v1" 已在 backendBase 里加了 */
  path?: string;
  /** 禁用 snakeize/camelize（上传/原始响应） */
  rawBody?: boolean;
  rawResponse?: boolean;
  timeoutMs?: number;
}

export async function proxyToBackend(
  event: H3Event,
  opts: ProxyOptions = {}
) {
  const base = backendBase();
  // 1) 路径：event.path 去掉 /api 前缀
  let incomingPath = event.path.replace(/^\/api/, "") || "/";
  incomingPath = opts.path ? opts.path + incomingPath : incomingPath;

  // 2) Query：从 getQuery 读取 + snakeize + lang 注入
  const q = getQuery(event);
  const snakeQ: Record<string, any> = snakeizeKeys(q);
  const hasLang = Object.keys(snakeQ).some(k => k.toLowerCase() === "lang");
  if (!hasLang) snakeQ.lang = backendLang(readLangCookie(event));
  const search = new URLSearchParams();
  for (const [k, v] of Object.entries(snakeQ)) {
    if (Array.isArray(v)) (v as any[]).forEach(x => search.append(k, String(x)));
    else if (v !== undefined && v !== null) search.append(k, String(v));
  }
  const qs = search.toString();

  // 3) 路径补尾斜杠 + 拼接 query
  if (!incomingPath.startsWith("/")) incomingPath = "/" + incomingPath;
  const hasExt = /\.[a-z0-9]{1,8}$/i.test(incomingPath.split("/").pop() || "");
  if (!incomingPath.endsWith("/") && !hasExt) incomingPath += "/";
  const backendUrl = `${base}${incomingPath}${qs ? "?" + qs : ""}`;

  // 4) Headers
  const hdrs: Record<string, string> = {
    Accept: "application/json",
    "Accept-Language": backendLang(readLangCookie(event)),
  };
  // X-Forwarded-* 真实 IP
  try {
    const fwd = getRequestHeader(event, "x-forwarded-for");
    const realIp = getRequestHeader(event, "x-real-ip");
    const ua = getRequestHeader(event, "user-agent");
    const ref = getRequestHeader(event, "referer");
    if (fwd) hdrs["X-Forwarded-For"] = fwd;
    if (realIp) hdrs["X-Real-IP"] = realIp;
    if (ua) hdrs["User-Agent"] = ua;
    if (ref) hdrs.Referer = ref;
  } catch { /* ignore */ }
  // Authorization Bearer
  const access = parseCookies(event)["rosetta_token"];
  if (access) hdrs.Authorization = `Bearer ${access}`;
  const csrf = parseCookies(event)["csrf_token"];
  if (csrf) hdrs["X-CSRF-Token"] = csrf;
  const contentT = getRequestHeader(event, "content-type");
  if (contentT) hdrs["Content-Type"] = contentT;

  // 5) Body
  let body: any;
  if (!["GET", "HEAD", "OPTIONS"].includes(event.method)) {
    try {
      const raw = await readRawBody(event, false);
      if (raw) {
        if (opts.rawBody) {
          body = raw;
        } else if (/^multipart\/form-data/i.test(contentT || "")) {
          body = raw; // 上传文件不做 snake
        } else if (typeof raw === "string" && raw.length) {
          try {
            const parsed = JSON.parse(raw);
            body = JSON.stringify(snakeizeKeys(parsed));
            hdrs["Content-Type"] = "application/json";
          } catch {
            body = raw; // 非 JSON 原样
          }
        } else {
          body = raw;
        }
      }
    } catch {
      /* empty body */
    }
  }

  // 6) Fetch
  try {
    const resp = await $fetch.raw(backendUrl, {
      method: event.method,
      headers: hdrs,
      body,
      timeout: opts.timeoutMs ?? 30_000,
      redirect: "manual",
      credentials: "omit",
    });
    // 401 → 清 cookie
    if (resp.status === 401) clearAuthCookies(event);
    // 设置响应头（content-type 等）
    for (const [k, v] of Object.entries(resp.headers)) {
      const key = k.toLowerCase();
      if (["content-type", "cache-control", "x-total-count", "x-page", "x-page-size"].includes(key)) {
        setResponseHeader(event, k, v as string);
      }
    }
    setResponseStatus(event, resp.status, resp.statusText);
    if (opts.rawResponse) return resp._data ?? null;
    return camelizeKeys(resp._data);
  } catch (err: any) {
    const status = err?.response?.status ?? err?.status ?? 500;
    if (status === 401) clearAuthCookies(event);
    const data = err?.response?._data ?? err?.data;
    // 错误信息规范化
    let message = err?.message || `Backend ${status}`;
    try {
      const n = camelizeKeys(data);
      if (n?.detail) message = n.detail;
      if (n?.message) message = n.message;
    } catch { /* ignore */ }
    setResponseStatus(event, status >= 100 && status < 600 ? status : 500);
    return { code: status, message, data: null };
  }
}
