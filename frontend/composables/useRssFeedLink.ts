/**
 * 分类/标签归档页的「本范围订阅源」`<link rel="alternate" type="application/rss+xml">`。
 *
 * 全站那条 RSS 链接由 `layouts/default.vue` 产出（`/rss.xml`）；这一条指向
 * `/rss.xml?category=<slug>` / `?tag=<slug>`，让阅读器与浏览器扩展能直接发现
 * 「这个分类本身可订阅」。后端 `/blog/rss` 的两个参数与前端这里的拼接是同一次
 * 契约的两端，口径由 `tests/unit/rssFeedDiscovery.spec.ts` 与
 * `tests/test_rss_taxonomy_feed.py` 分别钉住。
 *
 * 三条不输出的情形，缺一个就是给爬虫发假信号：
 * ① features.enable_rss 关掉（后端此时对 `/blog/rss` 直接 404，链接指向 404 空壳）；
 * ② 页面处于「分类不存在」态（此时页面自身 noindex，却又 advertise 一个该分类的源）；
 * ③ slug 还没取到（SSR 首帧）。
 *
 * `lang` 参数恒定带上：RSS 是单语言源（口径见 AGENTS.md §2.2.1 第 7 条），
 * 不带的话英文分类页的 feed 会按 Accept-Language/默认语言出中文标题，
 * 与页面语言互相矛盾。
 */
import { toValue, type MaybeRefOrGetter } from 'vue'

export function useRssFeedLink(opts: {
  kind: 'category' | 'tag'
  slug: MaybeRefOrGetter<string>
  label: MaybeRefOrGetter<string>
  active?: MaybeRefOrGetter<boolean>
}) {
  const site = useSite()
  const { locale } = useI18n()

  useHead(() => {
    const slug = toValue(opts.slug)
    if (!slug) return {}
    if (opts.active !== undefined && !toValue(opts.active)) return {}
    if (!site.features.value?.enable_rss) return {}
    const label = toValue(opts.label) || slug
    return {
      link: [
        {
          // rel 必须是字面量：unhead 按 rel 的具体值挑 link 变体（同 layouts/default.vue）
          rel: 'alternate',
          type: 'application/rss+xml',
          title: `${label} · RSS`,
          href: `/rss.xml?lang=${encodeURIComponent(locale.value)}&${opts.kind}=${encodeURIComponent(slug)}`
        }
      ]
    }
  })
}
