/**
 * /api/oobe/status — 查询是否完成首次配置（给 middleware/oobe.global.ts 用）
 * 后端约定返回 { oobe_complete: boolean }
 */
import { proxyToBackend, camelizeKeys } from "@/server/utils/backend-api";

export default defineEventHandler(async (event) => {
  const raw = await proxyToBackend(event, { path: "/oobe" });
  const norm = camelizeKeys(raw);
  // 保证字段稳定：后端即使返回 oobeComplete 也转成 oobe_complete
  const complete = !!(norm?.oobeComplete ?? norm?.oobe_complete ?? norm?.data?.oobeComplete ?? norm?.data?.oobe_complete);
  return { oobe_complete: complete };
});
