import qs from "qs";

/**
 * 规范化 URL 连接：a/b + /c + d/ →  a/b/c/d （单斜杠、无末尾斜线可选）。
 */
export function joinURL(...parts: string[]): string {
  const [head = "", ...rest] = parts.filter(p => typeof p === "string" && p.length > 0);
  const base = head.replace(/\/+$/, "");
  const tail = rest
    .map(p => p.replace(/^\/+|\/+$/g, ""))
    .filter(p => p.length > 0)
    .join("/");
  return tail ? `${base}/${tail}` : base;
}

/**
 * 在 URL 后追加 query 对象；支持嵌套、数组、去重。
 * 用 qs.stringify，兼容 qs.parse 回来的格式。
 */
export function withQuery<T extends Record<string, unknown>>(
  url: string,
  query: T,
  options: { removeFalsy?: boolean; arrayFormat?: "indices" | "brackets" | "repeat" | "comma" } = {}
): string {
  const { removeFalsy = false, arrayFormat = "indices" } = options;
  const [base, hashPart] = (url || "").split("#");
  const [pathname, existing] = base.split("?");
  const merged = {
    ...(existing ? qs.parse(existing, { ignoreQueryPrefix: true, depth: 5 }) : {}),
    ...(removeFalsy
      ? Object.fromEntries(Object.entries(query).filter(([, v]) => v !== undefined && v !== null && v !== ""))
      : query),
  };
  const queryStr = qs.stringify(merged, {
    arrayFormat,
    skipNulls: true,
    encode: true,
    addQueryPrefix: false,
    allowDots: false,
  });
  const hash = hashPart ? `#${hashPart}` : "";
  return queryStr ? `${pathname}?${queryStr}${hash}` : `${pathname}${hash}`;
}

/**
 * 去掉 URL 末尾斜杠（保留纯根 /）。
 */
export function withoutTrailingSlash(url: string): string {
  if (!url) return "/";
  const [base, hash] = url.split("#");
  const [path, query] = base.split("?");
  const clean = path.length > 1 ? path.replace(/\/+$/, "") : path;
  const q = query ? `?${query}` : "";
  const h = hash ? `#${hash}` : "";
  return `${clean}${q}${h}`;
}

/**
 * 判断是否站内跳转（相同 origin 或 path-only）。
 * 用来决定是走 navigateTo / <NuxtLink> 还是 <a target="_blank">。
 */
export function isInternal(url: string, currentOrigin = import.meta.client ? location.origin : ""): boolean {
  if (!url) return false;
  if (/^\s*(javascript:|data:|mailto:|tel:)/i.test(url)) return false;
  if (url.startsWith("/") || url.startsWith("#") || url.startsWith(".")) return true;
  try {
    const u = new URL(url, currentOrigin || "http://localhost");
    if (!currentOrigin) return false;
    return u.origin === currentOrigin;
  } catch {
    return false;
  }
}

/**
 * 以协议 :// 开头或协议相对 URL 即判定为绝对 URL。
 */
export function isAbsolute(url: string): boolean {
  return /^[a-z][a-z0-9+.-]*:\/\//i.test(url) || url.startsWith("//");
}

/**
 * 从 URL 的 query 中反解析出对象（支持嵌套数组），用 qs.parse。
 */
export function parseQuery<T = Record<string, unknown>>(
  search: string,
  options: { ignoreQueryPrefix?: boolean; depth?: number } = {}
): T {
  return qs.parse(search, { ignoreQueryPrefix: true, depth: options.depth ?? 5, ...options }) as T;
}

/**
 * 给 URL 附加 utm / 追踪参数但保留 origin hash 等信息，用于外部分享。
 */
export function buildShareUrl(
  url: string,
  params: { utmSource?: string; utmMedium?: string; utmCampaign?: string; ref?: string }
): string {
  const payload: Record<string, string> = {};
  if (params.utmSource) payload.utm_source = params.utmSource;
  if (params.utmMedium) payload.utm_medium = params.utmMedium;
  if (params.utmCampaign) payload.utm_campaign = params.utmCampaign;
  if (params.ref) payload.ref = params.ref;
  return withQuery(url, payload);
}
