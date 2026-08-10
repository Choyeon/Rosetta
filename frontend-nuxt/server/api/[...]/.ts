/**
 * 通用 catch-all API 代理：
 *   浏览器 / Nuxt $fetch → /api/<任意路径> → FastAPI http://127.0.0.1:8000/api/v1/<任意路径>
 * 所有方法（GET/POST/PUT/PATCH/DELETE/OPTIONS）都走这里。
 * 更具体的 server/api/auth/*.ts / oobe/*.ts / media/*.ts 由于路由更具体，匹配优先级高于 catch-all，会覆盖此 handler。
 */
import { proxyToBackend } from "@/server/utils/backend-api";
// 注：Nitro 内部 server/utils 无需别名也能被自动引入，这里别名在 tsconfig 配置 @/* -> frontend-nuxt/*

export default defineEventHandler(async (event) => {
  return await proxyToBackend(event);
});
