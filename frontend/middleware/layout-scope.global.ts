/**
 * layout-scope 全局路由中间件（最高保障层）：
 *
 * 前后台样式解耦的"第三层保险"（前两层：useFrontendTheme.clearThemeVisual + 布局 onMounted/watch）。
 *
 *   · /admin/*             → 确保 <html data-layout-scope="admin">，并清理 Rosetta 前端主题残留
 *   · /login /register /oobe → 确保 <html data-layout-scope="public-auth">，并清理主题残留
 *   · 其他所有路径          → 确保 <html data-layout-scope="frontend">
 *
 * 为什么需要 middleware：
 *   - login.vue 用 `layout: false`，不走 admin.vue / default.vue 的 onMounted / watch 钩子。
 *     若从激活 Minimal Paper 的首页按 login 按钮 SPA 跳转，data-theme 等属性会残留。
 *   - 硬刷新 admin/* 路由时，中间件比组件 onMounted 先跑，可以尽早（首渲染前）告诉 browser：
 *     这是 admin 上下文，不要尝试应用前台主题。
 *
 * 触发顺序（Nuxt 4）：
 *   middleware → page setup → layout setup → onMounted（组件）。
 *   所以这里只改 data-layout-scope，不做重的 DOM 操作；真正清理 <link>/<class>/<color>
 *   还是由布局的 onMounted 做。
 */
export default defineNuxtRouteMiddleware((to) => {
  if (!import.meta.client) return

  const path = to.path
  const root = document.documentElement

  let scope: 'admin' | 'frontend' | 'public-auth'
  if (path.startsWith('/admin')) {
    scope = 'admin'
  } else if (['/login', '/register', '/oobe'].includes(path) ||
             path.startsWith('/login/') || path.startsWith('/register/') || path.startsWith('/oobe/')) {
    scope = 'public-auth'
  } else {
    scope = 'frontend'
  }

  root.setAttribute('data-layout-scope', scope)

  // admin / public-auth 进入时，顺便调前端主题清理器（若 composable 已被激活）
  if (scope !== 'frontend') {
    // 延迟到 nextTick，避免在 middleware 阶段直接触发 composable 的首次初始化
    // （Nuxt 4 middleware 运行期不保证所有 composable 已可用）。
    queueMicrotask(() => {
      try {
        // 直接在 DOM 层做"轻量清理"：移除已知 Rosetta 主题属性。
        // 不使用 useFrontendTheme() 是因为 middleware 阶段可能在 setup() 之外调用 composable 会出错。
        for (const cls of Array.from(root.classList)) {
          if (cls.startsWith('theme-')) root.classList.remove(cls)
        }
        root.removeAttribute('data-rosetta-theme')
        const themes = new Set([
          'editorial-wp-style', 'astro-paper-inspired', 'minimal-brutalist',
          'typewriter-serif', 'market-style'
        ])
        const dt = root.getAttribute('data-theme')
        if (dt && themes.has(dt)) root.removeAttribute('data-theme')

        // 移除主题 <link>（所有 /themes/*/style.css 路径）
        document.querySelectorAll('link[rel="stylesheet"][href^="/themes/"]').forEach(
          el => el.remove()
        )
      } catch (_) {
        /* middleware 层绝不抛异常，失败了 layout 层仍会兜底清理 */
      }
    })
  }
})
