/**
 * i18n prefix_except_default 策略下的 URL 前缀保序中间件（客户端）。
 *
 * 可收录面上的链接已经全部迁到 localeHref()（composables/useLocaleLink.ts），
 * 本中间件只剩兜底职责：拦住那些仍然写死的裸 `to="/x"`（账号页、认证页、后台跳转
 * 等非爬虫面），把"目标路径没带前缀但当前语言非默认"重写成带前缀的等价 URL。
 *
 * 判定"当前语言"用 rosetta_lang cookie（由 LocaleSwitcher.vue / 页脚切换器写）——
 * i18n 的 detectBrowserLanguage 已整个关掉（见 nuxt.config.ts 的说明），cookie 是
 * 唯一跨页保序来源。
 *
 * ⚠️ 裸 `/` 不改写：那是默认语言（zh）首页，也是 hreflang 里 x-default 指的位置。
 * 在这里按 cookie 跳去 /en 会把中文首页的实拿内容与自指 canonical 判成两回事
 * （浏览器语言重定向的同一坑，只是换了执行方）。
 *
 * 已带前缀的目标路径（/en/posts/xxx、/ja/、/zh_Hant/admin 等）直接放行。
 * 静态资源、_nuxt、api、favicon 一律放行。
 */
const LOCALE_RE = /^\/(en|ja|zh_Hant)(?=\/|$)/
const SKIP_RE = /^\/(?:_nuxt|api|media|favicon|logo|assets|themes|@vite|@id|@fs|robots\.txt|sitemap|rss|sitemap\.xml|rss\.xml|site\.webmanifest|manifest|apple-touch-icon)/

export default defineNuxtRouteMiddleware((to) => {
  if (!import.meta.client) return
  if (to.path === '/') return
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
