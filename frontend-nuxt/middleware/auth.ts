// 管理后台用的 auth middleware（独立于 oobe.global 的全局限流）
// 用法：definePageMeta({ middleware: ["auth"] })
export default defineNuxtRouteMiddleware(async (to) => {
  const auth = useAuthStore();
  auth.init();
  if (!auth.isLogged) {
    return navigateTo({ path: "/login", query: { from: to.fullPath } }, { replace: true });
  }
  // 拉取 /api/users/me 确认 token 有效并同步 roles
  if (!auth.user) {
    try {
      const me: any = await apiGet("/api/users/me");
      const u = me?.data || me;
      if (u) auth.setAuth({ access_token: auth.accessToken || "", user: u });
    } catch {
      auth.logout();
      return navigateTo({ path: "/login", query: { from: to.fullPath } }, { replace: true });
    }
  }
  // admin 路由要求 admin 角色
  if (to.path.startsWith("/admin") && !auth.isAdmin) {
    return navigateTo("/403", { replace: true });
  }
});
