/**
 * 管理后台路由守卫：
 * - 仅拦截 /^\/admin/ 路由（客户端执行，SPA 模式）
 * - store 未初始化时先等待恢复登录态（幂等）
 * - 未登录 → 携带 redirect 参数跳转 /login
 * - 已登录但非管理员 → 跳转首页
 */
import { useAuthStore } from '~~/stores/auth'

export default defineNuxtRouteMiddleware(async (to) => {
  if (!import.meta.client) return
  if (!/^\/admin/.test(to.path)) return

  const authStore = useAuthStore()
  await authStore.initialize()

  if (!authStore.isAuthenticated) {
    return navigateTo(`/login?redirect=${encodeURIComponent(to.fullPath)}`, { replace: true })
  }

  if (!authStore.isAdmin) {
    return navigateTo('/', { replace: true })
  }
})
