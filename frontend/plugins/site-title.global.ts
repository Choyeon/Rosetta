// 全局动态 titleTemplate：
//  1) 唯一权威来源（页面只负责写 `title: 单页标题`，不自己拼 "· 站点名"）
//  2) siteTitle / siteSubtitle 来自 useSite composable（后台 basic.site_name /
//     basic.subtitle 动态设置后，下次访问即生效，不用重配 nuxt.config）
//  3) 拼法：
//     - 空标题 / 标题与站点名相同：返回 "站点名 · 副标题" 或仅 "站点名"
//     - 其他情况：      "单页标题 · 站点名"
export default defineNuxtPlugin(async () => {
  if (import.meta.env.SSR) return
  const site = useSite()
  await site.ensureLoaded()
  useHead({
    titleTemplate: (title?: string) => site.withSuffix(title ?? '')
  })
})