/**
 * layout-scope 全局路由中间件（最高保障层）：
 *
 * 前后台样式解耦的"第三层保险"（前两层：useFrontendTheme.clearThemeVisual + 布局 onMounted/watch）。
 *
 *   · /admin/*             → 确保 <html data-layout-scope="admin">，并清理 Rosetta 前端主题残留
 *   · /login /register /oobe → 确保 <html data-layout-scope="public-auth">（主题视觉层
 *     允许保留在认证页：frontend 守卫的规则不命中；仅 admin 强制清理）
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
import { KNOWN_ROSETTA_THEMES } from '~~/lib/rosetta-themes'

export default defineNuxtRouteMiddleware((to) => {
  const path = to.path

  let scope: 'admin' | 'frontend' | 'public-auth'
  if (path.startsWith('/admin')) {
    scope = 'admin'
  } else if (
    ['/login', '/register', '/oobe'].includes(path)
    || path.startsWith('/login/')
    || path.startsWith('/register/')
    || path.startsWith('/oobe/')
  ) {
    scope = 'public-auth'
  } else {
    scope = 'frontend'
  }

  // ===== SSR 分支：通过 useHead({ htmlAttrs }) 写入首字节 scope 属性 =====
  // 主题 style.css 的选择器守卫是 [data-layout-scope="frontend"]，
  // 若 SSR 阶段不写入这个属性，首帧 HTML 到达浏览器后、Hydrate 完成前的窗口里，
  // 0 条主题 CSS 规则命中，首屏表现为"没有主题样式 / 默认主题不对"。
  if (import.meta.server) {
    useHead({
      htmlAttrs: {
        'data-layout-scope': scope
      }
    })
    // admin / public-auth 的 SSR 分支：同时把主题残留从 <head> 中排除。
    // SSR 端不会有 DOM 残留（每次请求都渲染全新 HTML），所以只需 useHead 不写 theme
    // 视觉层即可——这个清理由 useFrontendTheme.applyThemeVisual 的 SSR 守卫执行。
    return
  }

  if (!import.meta.client) return

  const root = document.documentElement
  root.setAttribute('data-layout-scope', scope)

  // 进入 admin 时清理主题残留属性/链接（composable 尚未保证可用的轻量 DOM 清理）。
  // 注意：public-auth（/login /register）自 2026-09 起【不再】清理——主题视觉层
  // 允许注入认证页（其样式靠 [data-layout-scope="frontend"] 守卫天然隔离，
  // 主题若需定制认证页必须显式书写 public-auth 守卫段落）。
  if (scope === 'admin') {
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
        const dt = root.getAttribute('data-theme')
        if (dt && KNOWN_ROSETTA_THEMES.has(dt)) root.removeAttribute('data-theme')

        // 移除主题 <link>（所有 /themes/*/style.css 路径）
        document.querySelectorAll('link[rel="stylesheet"][href^="/themes/"]').forEach(
          el => el.remove()
        )
      } catch {
        /* middleware 层绝不抛异常，失败了 layout 层仍会兜底清理 */
      }
    })
  }
})
