/**
 * OOBE 全局路由中间件（对应 Astro src/middleware.ts）
 * 行为：
 *   - 后端 /api/oobe/status 返回 oobe_complete=false → 除 /oobe/** 外，所有页面 302 重定向到 /oobe
 *   - 已完成 OOBE → 如果访问 /oobe/** → 302 回首页
 *   - 带 10s 进程内缓存：避免每页请求都打后端（与 Astro 等价）
 *   - SSR + 客户端导航双端保护
 */
import { defineNuxtRouteMiddleware, navigateTo, useRequestFetch } from "#app";

const OOBE_PATH = "/oobe";
const EXACT_PREFIXES = [OOBE_PATH + "/", OOBE_PATH];

// 10 秒内存缓存（服务端进程级；客户端不使用此项，避免跨用户污染）
let cacheTsSsr = 0;
let cacheValSsr: boolean | null = null;
const CACHE_MS = 10 * 1000;

async function queryOobeCompleteSsr(runtime: ReturnType<typeof useRuntimeConfig>): Promise<boolean> {
  const now = Date.now();
  if (cacheValSsr !== null && now - cacheTsSsr < CACHE_MS) return cacheValSsr;
  const base = runtime.apiBaseUrlSsr || "http://127.0.0.1:8000";
  try {
    const r = await $fetch<{ oobe_complete?: boolean }>("/api/oobe/status", {
      baseURL: base,
      method: "GET",
      timeout: 1500,
      headers: { Accept: "application/json" },
    });
    const ok = !!r?.oobe_complete;
    cacheTsSsr = now;
    cacheValSsr = ok;
    return ok;
  } catch (_e) {
    // 后端未启动/超时：暂时按 complete 处理，让前端自行兜底（避免死循环跳 OOBE 页）
    cacheTsSsr = now;
    cacheValSsr = null;
    return true;
  }
}

export default defineNuxtRouteMiddleware(async (to) => {
  const pathname = to.path;
  // 静态资源/接口由 Nitro 处理，这里只拦截页面导航
  const staticExt = /\.(png|jpe?g|webp|gif|svg|css|js|mjs|woff2?|ttf|ico|map|avif|json|xml|txt)$/i;
  if (staticExt.test(pathname)) return;

  const isOobePage =
    pathname === OOBE_PATH ||
    pathname.startsWith(OOBE_PATH + "/");

  const runtime = useRuntimeConfig();
  let complete = true;

  if (import.meta.server) {
    // SSR：直接用后端绝对 URL 调用
    complete = await queryOobeCompleteSsr(runtime);
  } else if (import.meta.client) {
    // 客户端：调用同源 /api（由 Nitro 代理），走 useFetch 共享缓存避免重复请求
    try {
      const r = await useRequestFetch()("/api/oobe/status", { timeout: 1500 }).catch(() => null);
      complete = !!r?.oobe_complete;
    } catch (_) {
      complete = true; // 失败兜底
    }
  }

  if (!complete && !isOobePage) {
    return navigateTo(OOBE_PATH, { redirectCode: 302, replace: true });
  }
  if (complete && isOobePage) {
    return navigateTo("/", { redirectCode: 302, replace: true });
  }
});
