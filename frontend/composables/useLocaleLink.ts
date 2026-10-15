/**
 * useLocaleLink —— 把站内路径写成"当前语言下的真实 URL"。
 *
 * 为什么需要它：i18n 走 prefix_except_default（中文裸路径，英/日/繁挂 /en /ja /zh_Hant）。
 * 模板里直接写 `to="/posts/xxx"` 的链接，在带前缀的语言页面上仍然指向默认语言的 URL——
 * 访客会被客户端兜底中间件（middleware/locale-prefix.global.client.ts）再跳一次，
 * 但**爬虫读的是 SSR 里的 href**：英文页的整张链接图都指向中文版，
 * 语言变体只能靠 sitemap 与 hreflang 被发现，等于把站内权重往中文版倾斜。
 *
 * 单源口径与 SEO 侧一致（canonical / hreflang / JSON-LD 用的是同一个 applyLocalePrefix），
 * 也不走 @nuxtjs/i18n 的 localePath()：它按路由名解析，`/posts/{中文 slug}` 在 SSR 期
 * 产出过非字符串并把详情页打成整页 500（见 useSeo.ts 的 applyLocalePrefix 注释）。
 *
 * 后台页（/admin/**）与 OOBE 不要用它：那些路径不参与语言前缀。
 */
import { applyLocalePrefix } from './useSeo'

export function useLocaleLink() {
  const { locale } = useI18n()

  /**
   * 中性路径（或已带前缀的路径）→ 当前语言的真实 href。
   *
   * 外链与锚点原样透传：导航项、友情链接、首页 CTA 的 to 都可能来自后台配置
   * （https://example.com 或 #section），给它们挂语言前缀会产出
   * `/enhttps://example.com` 这种死链。语言前缀只属于站内绝对路径。
   */
  const localeHref = (path: string) => {
    const raw = path || ''
    if (!raw.startsWith('/') || /^\/\//.test(raw)) return raw
    return applyLocalePrefix(raw, locale.value)
  }

  return { localeHref }
}
