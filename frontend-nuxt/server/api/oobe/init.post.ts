/**
 * /api/oobe/init — 提交首次配置（DB 初始化 + 超管）
 */
import { proxyToBackend, camelizeKeys } from "@/server/utils/backend-api";

export default defineEventHandler(async (event) => {
  const raw = await proxyToBackend(event, { path: "/oobe" });
  return camelizeKeys(raw);
});
