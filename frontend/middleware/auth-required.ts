/**
 * 登录页路由闸门（仅挂在需要登录态的页面，不进全局链）。
 *
 * 为什么单独建一个而不是复用 admin.global：后者把「非管理员踢回首页」和
 * `/^\/admin/` 判定绑在一起，普通注册用户进 /account 会被自己的角色判定赶回家。
 * 这里只回答一个问题——登录了吗。
 *
 * 与 AGENTS.md §2.3.2 同源的理由：状态闸门放中间件，页面 setup 只管渲染。
 * /account 是 ssr:false（见 nuxt.config routeRules），所以 SSR 分支直接 return，
 * 服务端不会替一个没有 token 的请求去跑登录判定。
 */
import { useAuthStore } from '~~/stores/auth'

export default defineNuxtRouteMiddleware(async (to) => {
  if (!import.meta.client) return

  const authStore = useAuthStore()
  // store 只在客户端从 localStorage 回填；未初始化时先恢复，否则 isAuthenticated 恒 false
  // 会把已登录用户踢去 /login（admin.global 同序）。
  await authStore.initialize()

  if (!authStore.isAuthenticated) {
    return navigateTo(`/login?redirect=${encodeURIComponent(to.fullPath)}`, { replace: true })
  }
})
