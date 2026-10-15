/**
 * i18n prefix_except_default 策略下的 URL 前缀保序中间件（客户端）。
 *
 * 项目内 40+ 页面仍写 <NuxtLink to="/posts/xxx">，切换语言后点击会掉回默认语言
 * 路径（zh）——本中间件在客户端导航里拦截这种"目标路径没带前缀但当前语言非默认"
 * 的情况，重写到带前缀的等价 URL。
 *
 * 判定"当前语言"用 rosetta_lang cookie（由 LocaleSwitcher.vue 与 SSR 期
 * detectBrowserLanguage 双写）而不是 i18n 内部 locale——后者在 middleware 首帧
 * 未必完成注入，容易在冷启动时读到默认 zh。
 *
 * 已带前缀的目标路径（/en/posts/xxx、/ja/、/zh_Hant/admin 等）直接放行。
 * 静态资源、_nuxt、api、favicon 一律放行。
 *
 * ⚠️ 长期方案：把 40+ 页面的 <NuxtLink to="/x"> 迁到 <NuxtLinkLocale to="/x">
 * 后就可以移除本中间件；当前先以最小侵入保证语言切换的连续性可用。
 */
const LOCALE_RE = /^\/(en|ja|zh_Hant)(?=\/|$)/
const SKIP_RE = /^\/(?:_nuxt|api|media|favicon|logo|assets|themes|@vite|@id|@fs|robots\.txt|sitemap|rss|sitemap\.xml|rss\.xml|site\.webmanifest|manifest|apple-touch-icon)/

export default defineNuxtRouteMiddleware((to) => {
  if (!import.meta.client) return
  if (SKIP_RE.test(to.path)) return

  // 从 cookie 读当前语言；无 cookie 或非默认且未在 URL 前缀里 → 需要重写
  const raw = document.cookie.match(/(?:^|;\s*)rosetta_lang=([^;]+)/)?.[1]
  const cookieLocale = raw ? decodeURIComponent(raw) : null
  if (!cookieLocale || cookieLocale === 'zh') return

  // 目标已经带前缀（无论是否与 cookie 一致）→ 交给 i18n 处理，不重复改写
  if (LOCALE_RE.test(to.path)) return

  // 目标是无前缀路径 → 挂 cookie 语言前缀
  const next = `/${cookieLocale}${to.fullPath === '/' ? '' : to.fullPath}`
  return navigateTo(next, { redirectCode: 302, replace: true })
})
