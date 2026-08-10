/**
 * /api/users/me — 当前用户资料（登录页成功后 / 后台每次刷新都调一次，写回 authStore.user/roles/permissions）
 */
import { proxyToBackend, camelizeKeys } from "@/server/utils/backend-api";

export default defineEventHandler(async (event) => {
  const raw = await proxyToBackend(event, { path: "/users" });
  return camelizeKeys(raw);
});
