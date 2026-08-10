/**
 * /api/auth/login — 登录：接收 username + password → 写入 access/refresh 双 cookie
 * 前端 client：Pinia useAuthStore().setAuth() 也会写 localStorage + Cookie 双重；
 * 这里服务端的作用是保证服务端跳转（302）场景也能种 Cookie（SSR 首屏登录态）。
 */
import { proxyToBackend, clearAuthCookies } from "@/server/utils/backend-api";
import { camelizeKeys } from "@/server/utils/backend-api";

interface LoginBody { username?: string; password?: string; remember?: boolean; email?: string }

export default defineEventHandler(async (event) => {
  // 登出残留（强制清）
  try {
    const body = await readBody<LoginBody>(event);
    if (!body) throw new Error("empty body");
  } catch {
    /* fallback */
  }

  const backend: any = await proxyToBackend(event, { path: "/auth" });
  const payload = camelizeKeys(backend);
  const at: string | undefined = payload?.accessToken || payload?.access_token || payload?.data?.accessToken || payload?.data?.access_token;
  const rt: string | undefined = payload?.refreshToken || payload?.refresh_token || payload?.data?.refreshToken || payload?.data?.refresh_token;
  const opts7 = { path: "/", httpOnly: false, sameSite: "lax" as const, maxAge: 60 * 60 * 24 * 7 };
  const opts14 = { ...opts7, maxAge: 60 * 60 * 24 * 14 };
  if (at) setCookie(event, "rosetta_token", at, opts7); else clearAuthCookies(event);
  if (rt) setCookie(event, "rosetta_refresh_token", rt, opts14);
  return payload;
});
