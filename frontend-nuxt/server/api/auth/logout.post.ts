/**
 * /api/auth/logout — 服务端清 Cookie；前端 authStore.logout() 会同步清 localStorage
 */
import { clearAuthCookies, proxyToBackend } from "@/server/utils/backend-api";

export default defineEventHandler(async (event) => {
  clearAuthCookies(event);
  try {
    await proxyToBackend(event, { path: "/auth" });
  } catch {
    /* 后端登出失败不影响前端 */
  }
  return { code: 0, message: "ok", data: null };
});
