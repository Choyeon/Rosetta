/**
 * /api/auth/refresh — 拿 refresh_token → 换一对新 token（如果后端支持）
 */
import { proxyToBackend, clearAuthCookies, camelizeKeys } from "@/server/utils/backend-api";

export default defineEventHandler(async (event) => {
  const rt = parseCookies(event)["rosetta_refresh_token"];
  if (!rt) {
    setResponseStatus(event, 400);
    return { code: 400, message: "missing refresh token", data: null };
  }
  const backend: any = await proxyToBackend(event, { path: "/auth" });
  const payload = camelizeKeys(backend);
  const at: string | undefined = payload?.accessToken || payload?.access_token || payload?.data?.accessToken || payload?.data?.access_token;
  const newRt: string | undefined = payload?.refreshToken || payload?.refresh_token || payload?.data?.refreshToken || payload?.data?.refresh_token;
  const opts7 = { path: "/", httpOnly: false, sameSite: "lax" as const, maxAge: 60 * 60 * 24 * 7 };
  const opts14 = { ...opts7, maxAge: 60 * 60 * 24 * 14 };
  if (at) setCookie(event, "rosetta_token", at, opts7); else clearAuthCookies(event);
  if (newRt) setCookie(event, "rosetta_refresh_token", newRt, opts14);
  return payload;
});
