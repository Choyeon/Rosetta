<!--
  前台页脚（默认主题完整版 / 极简主题瘦身版两副骨架）。
  站点数据不自行请求，直接读 layouts/default.vue 已 ensureLoaded 的 useSite() state，
  换挂载点时必须先保证该 state 已填充；管理员注入的 footer_custom_html 只有过
  sanitizeTrustedAdminHtml 白名单才允许 v-html。极简骨架判定唯一来源是
  lib/rosetta-themes 的 MINIMAL_THEME_SLUGS，禁止本地复制 slug 字面量。
-->
<script setup lang="ts">
import { Separator } from '~~/components/ui/separator'
import type { Category } from '~~/types/api'
import { useAPI } from '~~/composables/useApi'
import { useI18n } from 'vue-i18n'
import { MINIMAL_THEME_SLUGS } from '~~/lib/rosetta-themes'
import { flattenNavLinks, navRowsToLinks, withoutDuplicateTos, type NavLink, type NavApiRow } from '~~/lib/navigation'
import { applyLocalePrefix } from '~~/composables/useSeo'
import { sanitizeTrustedAdminHtml } from '~~/lib/sanitize'

const { t, locale, setLocale } = useI18n()
const { localeHref } = useLocaleLink()
const route = useRoute()

const currentYear = new Date().getFullYear()

// 极简主题（astro-paper-inspired）使用瘦身页脚：单列居中、无 logo/多列网格/分类栏，
// 仅保留自定义 HTML、导航链接行、语言切换与版权。slug 判定与首页保持一致。
const ft = useFrontendTheme()
const isMinimalTheme = computed<boolean>(() => MINIMAL_THEME_SLUGS.has(ft.slug.value || ''))

interface FooterLink {
  labelKey: string
  to?: string
  href?: string
  external?: boolean
}

// 分类键与首页 / posts 列表页 / categories 页共用同一把 `blog:categories:<locale>`：
// Nuxt 按 key 全局去重——同页页脚与正文只发一条 /blog/categories；
// 页脚常驻布局，跨前台页面导航也直接复用条目，不必每页重拉。
// 键与查询都是静态字面量：切语言靠 URL 变化 → 页面重挂载刷新，不手写 watch。
const { data: categories } = useAPI<Category[]>('/blog/categories', {
  query: { lang: locale.value },
  key: `blog:categories:${locale.value}`,
  default: () => []
})

const pickLocalized = (value: unknown): string => pickLocalizedText(value, locale.value)

const categoryLinks = computed<FooterLink[]>(() => {
  // 按本地化名称去重：mock/历史数据可能存在同名不同 slug 的重复分类，
  // 直接全量映射会让页脚出现重复入口。保留首次出现的分类。
  const seen = new Set<string>()
  const links: FooterLink[] = []
  for (const category of categories.value || []) {
    const label = pickLocalized(category.name)
    const key = label.trim().toLowerCase()
    if (!key || seen.has(key)) continue
    seen.add(key)
    links.push({
      labelKey: label,
      to: `/posts?category=${encodeURIComponent(category.slug)}`
    })
  }
  return links
})

/** 真实存在的前台页面（pages/* 路由），严禁引用不存在路径。 */
interface SiteLink extends FooterLink {
  /** 兜底文案（多语言）；当 i18n 尚未热更新或 key 丢失时直接显示，避免 SSR 出现 footer.home 裸 key。 */
  fallbacks: Record<string, string>
}
const FALLBACK_LOCALE = 'zh'
const localeLabelFallback = (key: string, fallbacks?: Record<string, string>): string => {
  const code = String(locale.value || FALLBACK_LOCALE)
  if (fallbacks && fallbacks[code]) return fallbacks[code]
  if (fallbacks && fallbacks[FALLBACK_LOCALE]) return fallbacks[FALLBACK_LOCALE]
  // 末尾兜底：从已有 common / nav 命名空间取近似值（对老环境友好）
  const compact = t(`nav.${key.split('.').pop() ?? ''}`, '')
  if (compact) return compact
  return t(key, '')
}
const siteLinks: SiteLink[] = [
  {
    labelKey: 'footer.home', to: '/',
    fallbacks: { zh: '首页', en: 'Home', ja: 'ホーム', zh_Hant: '首頁' }
  },
  {
    labelKey: 'footer.posts', to: '/posts',
    fallbacks: { zh: '文章', en: 'Posts', ja: '記事', zh_Hant: '文章' }
  },
  {
    labelKey: 'footer.categories', to: '/categories',
    fallbacks: { zh: '分类', en: 'Categories', ja: 'カテゴリ', zh_Hant: '分類' }
  },
  {
    labelKey: 'footer.tags', to: '/tags',
    fallbacks: { zh: '标签', en: 'Tags', ja: 'タグ', zh_Hant: '標籤' }
  },
  {
    labelKey: 'footer.archive', to: '/archive',
    fallbacks: { zh: '归档', en: 'Archive', ja: 'アーカイブ', zh_Hant: '封存' }
  },
  {
    labelKey: 'footer.about', to: '/about',
    fallbacks: { zh: '关于', en: 'About', ja: 'このサイトについて', zh_Hant: '關於' }
  },
  {
    labelKey: 'footer.gallery', to: '/gallery',
    fallbacks: { zh: '相册', en: 'Gallery', ja: 'ギャラリー', zh_Hant: '相簿' }
  },
  {
    labelKey: 'footer.guestbook', to: '/guestbook',
    fallbacks: { zh: '留言板', en: 'Guestbook', ja: 'ゲストブック', zh_Hant: '留言板' }
  },
  {
    labelKey: 'footer.activity', to: '/activity',
    fallbacks: { zh: '动态', en: 'Activity', ja: 'アクティビティ', zh_Hant: '動態' }
  },
  {
    labelKey: 'footer.friends', to: '/friends',
    fallbacks: { zh: '友链', en: 'Friends', ja: 'フレンド', zh_Hant: '友站連結' }
  },
  {
    labelKey: 'footer.authors', to: '/authors',
    fallbacks: { zh: '作者', en: 'Authors', ja: '著者', zh_Hant: '作者' }
  },
  {
    labelKey: 'footer.hot', to: '/posts/hot',
    fallbacks: { zh: '热门榜单', en: 'Hot Ranking', ja: 'ホットランキング', zh_Hant: '熱門榜單' }
  },
  {
    labelKey: 'footer.sponsor', to: '/sponsor',
    fallbacks: { zh: '捐助支持', en: 'Sponsor', ja: 'サポート', zh_Hant: '贊助支持' }
  }
]
/** 对每个 siteLink 先查 i18n，查不到走多语言兜底。 */
const siteLabel = (link: SiteLink) => {
  const fromI18n = t(link.labelKey, '')
  if (fromI18n && fromI18n !== link.labelKey) return fromI18n
  return localeLabelFallback(link.labelKey, link.fallbacks)
}

const sectionTitle = (key: string, fallbacks: Record<string, string>) => {
  const fromI18n = t(key, '')
  if (fromI18n && fromI18n !== key) return fromI18n
  return localeLabelFallback(key, fallbacks)
}

const resourceLinks: FooterLink[] = [
  { labelKey: 'footer.linkRSS', href: '/rss.xml' },
  { labelKey: 'footer.linkSitemap', href: '/sitemap.xml' }
]
const RESOURCE_FALLBACKS: Record<string, Record<string, string>> = {
  'footer.linkRSS': { zh: 'RSS 订阅', en: 'RSS Feed', ja: 'RSS', zh_Hant: 'RSS 訂閱' },
  'footer.linkSitemap': { zh: '网站地图', en: 'Sitemap', ja: 'サイトマップ', zh_Hant: '網站地圖' }
}
const SOCIAL_FALLBACKS: Record<string, Record<string, string>> = {
  'footer.socialGithub': { zh: 'GitHub', en: 'GitHub', ja: 'GitHub', zh_Hant: 'GitHub' },
  'footer.socialX': { zh: 'X (Twitter)', en: 'X', ja: 'X', zh_Hant: 'X' },
  'footer.socialBilibili': { zh: 'B 站', en: 'Bilibili', ja: 'ビリビリ', zh_Hant: 'B 站' },
  'footer.socialWeibo': { zh: '微博', en: 'Weibo', ja: '微博', zh_Hant: '微博' },
  'footer.socialZhihu': { zh: '知乎', en: 'Zhihu', ja: '知乎', zh_Hant: '知乎' },
  'footer.socialYoutube': { zh: 'YouTube', en: 'YouTube', ja: 'YouTube', zh_Hant: 'YouTube' },
  'footer.socialLinkedin': { zh: 'LinkedIn', en: 'LinkedIn', ja: 'LinkedIn', zh_Hant: 'LinkedIn' },
  'footer.socialTelegram': { zh: 'Telegram', en: 'Telegram', ja: 'Telegram', zh_Hant: 'Telegram' }
}
const resourceLabel = (labelKey: string) => sectionTitle(labelKey, RESOURCE_FALLBACKS[labelKey] ?? {})
const socialLabel = (labelKey: string) => sectionTitle(labelKey, SOCIAL_FALLBACKS[labelKey] ?? {})

// ===== 使用 useSite() 统一读取站点配置（数据来源：/api/config + /api/settings） =====
// 避免 footer 再单独请求 /api/config，保证站点名、版权、ICP、logo、社交链接等与
// AppHeader、页面 title 等位置使用完全一致的数据源与 fallback 行为。
interface SiteConfigLite {
  site_name: string
  site_author: string
  site_description: string
  site_logo: string
  footer_slogan: string
  powered_by_text: string
  copyright_text: string | null
  footer_custom_html: string
  icp_number: string
  police_icp_number: string
  github_url: string | null
  x_url: string | null
  bilibili_url: string | null
  weibo_url: string | null
  zhihu_url: string | null
  youtube_url: string | null
  linkedin_url: string | null
  telegram_url: string | null
}

// useSite 由 layouts/default.vue 提前 ensureLoaded()，这里 state 已填充完毕
const site = useSite()
/**
 * 捐助页在「未配置任何收款方式」时是 noindex 占位，页脚无条件挂入口等于把访客引向一张空白页。
 * 只在有真实收款方式时出现；判断用站点配置里同一份 donate 分组，不额外发请求。
 */
const visibleSiteLinks = computed(() =>
  siteLinks.filter(link => link.to !== '/sponsor' || site.donate.value.methods.length > 0)
)

// 管理员在「导航菜单」把项存到 location=footer 时，页脚是它唯一的渲染面。
// 后台给了三个位置而前台只认一个，等于另外两档是死档位（项存进去静默消失），
// 所以 header / footer / sidebar 三档各有一个消费方，URL 归一化共用 lib/navigation.ts。
// 与顶栏不同 key：两档数据集不同，共 key 会让其中一档拿到另一档的行。
const { data: footerNavRows } = useAPI<NavApiRow[]>('/navigations', {
  query: { location: 'footer' },
  key: `public:navigations:footer:${locale.value}`,
  default: () => []
})

/**
 * 页脚固定链接先占位：后台把「关于」又配成页脚菜单项时，同一列出现两条相同链接，
 * 比少一条更像 bug。父项因重复被摘掉时子项上提（整支子菜单不能跟着消失）。
 */
const footerNavLinks = computed<NavLink[]>(() =>
  withoutDuplicateTos(
    navRowsToLinks(
      footerNavRows.value,
      row => pickLocalized(row.label ?? row.title ?? row.name)
    ),
    new Set(visibleSiteLinks.value.map(l => l.to).filter((to): to is string => Boolean(to)))
  )
)
// features 分组关掉 RSS / Sitemap 后，页脚文字链与订阅图标必须一起消失：
// 留着就是指向 404 的入口，还会让爬虫以为站点有订阅源。
const visibleResourceLinks = computed(() => resourceLinks.filter((link) => {
  const f = site.features.value
  if (link.labelKey === 'footer.linkRSS') return f.enable_rss
  if (link.labelKey === 'footer.linkSitemap') return f.enable_sitemap
  return true
}))
const showRssIcon = computed(() => site.features.value.enable_rss)
const siteConfig = computed<SiteConfigLite>(() => {
  const publicCfg = (site.state.value.publicConfig || {}) as Record<string, unknown>
  const b = site.basic.value
  const f = site.footer.value

  const readStr = (key: string, fb = ''): string => {
    const v = publicCfg[key]
    if (v == null) return fb
    return String(v || fb)
  }
  const readNullable = (key: string): string | null => {
    const v = publicCfg[key]
    if (v == null || v === '') return null
    return String(v)
  }

  const siteName = b.site_name || readStr('site_name', 'Rosetta Blog')
  const siteDescription = b.description || readStr('site_description', 'Rosetta开源博客系统')
  // slogan 与 text 各有独立渲染位：slogan 是标语行，text 是 Powered by 那一行的覆写。
  // 此前写成 `f.slogan || f.text`，而两者都被 useSite 用副标题播种，
  // 于是 footer.text 这个输入框永远读不到——填了也白填。
  const footerSlogan = f.slogan || readStr('footer_slogan', siteDescription)
  const poweredByText = f.text || ''
  const copyrightText = (publicCfg.copyright_text as string | null) ?? null
  const footerCustomHtml = (publicCfg.footer_custom_html as string) || ''

  return {
    site_name: siteName,
    site_author: readStr('site_author', siteName),
    site_description: siteDescription,
    site_logo: b.logo || readStr('site_logo', '') || '/logo/rosetta-monochrome-icon.png',
    footer_slogan: footerSlogan,
    powered_by_text: poweredByText,
    copyright_text: copyrightText && String(copyrightText).trim() ? String(copyrightText) : null,
    footer_custom_html: footerCustomHtml,
    icp_number: b.icp_number || f.icp_number || readStr('icp_number', ''),
    // footer.police_icp_number：公安备案号此前只进库不渲染，备案号属于法定展示项，
    // 与"显示版权声明"开关无关（关掉版权行也照样显示）。
    police_icp_number: f.police_icp_number || readStr('police_icp_number', ''),
    github_url: readNullable('github_url'),
    x_url: readNullable('x_url'),
    bilibili_url: readNullable('bilibili_url'),
    weibo_url: readNullable('weibo_url'),
    zhihu_url: readNullable('zhihu_url'),
    youtube_url: readNullable('youtube_url'),
    linkedin_url: readNullable('linkedin_url'),
    telegram_url: readNullable('telegram_url')
  }
})

// footer_custom_html 是管理员有意书写的富 HTML，但仍带白名单 sanitize
// （禁 script/iframe/on*/javascript: URI，放行 class/style 内联排版）。
// isomorphic-dompurify SSR 与客户端同实现，首屏 HTML 即已洗过，两端字节一致。
const footerCustomHtml = computed(() => sanitizeTrustedAdminHtml(siteConfig.value.footer_custom_html))

const socialLinks = computed<FooterLink[]>(() => {
  // footer.show_social_links：后台关掉即整段不渲染（此前这个开关没有任何消费点）。
  if (site.footer.value.show_social_links === false) return []
  const cfg = siteConfig.value
  const list: FooterLink[] = []
  if (cfg.github_url) list.push({ labelKey: 'footer.socialGithub', href: cfg.github_url, external: true })
  if (cfg.x_url) list.push({ labelKey: 'footer.socialX', href: cfg.x_url, external: true })
  if (cfg.bilibili_url) list.push({ labelKey: 'footer.socialBilibili', href: cfg.bilibili_url, external: true })
  if (cfg.weibo_url) list.push({ labelKey: 'footer.socialWeibo', href: cfg.weibo_url, external: true })
  if (cfg.zhihu_url) list.push({ labelKey: 'footer.socialZhihu', href: cfg.zhihu_url, external: true })
  if (cfg.youtube_url) list.push({ labelKey: 'footer.socialYoutube', href: cfg.youtube_url, external: true })
  if (cfg.linkedin_url) list.push({ labelKey: 'footer.socialLinkedin', href: cfg.linkedin_url, external: true })
  if (cfg.telegram_url) list.push({ labelKey: 'footer.socialTelegram', href: cfg.telegram_url, external: true })
  return list
})

// 最终显示的版权文字：主题 footer_text（Customizer 入口） > 站点 settings.copyright_text > 默认格式
const copyrightLine = computed(() => {
  const themeCopyright = (site.footer.value && 'copyright' in site.footer.value)
    ? (site.footer.value as { copyright?: string }).copyright
    : null
  if (themeCopyright && String(themeCopyright).trim()) return String(themeCopyright).trim()
  if (siteConfig.value.copyright_text) return siteConfig.value.copyright_text
  const owner = siteConfig.value.site_author || siteConfig.value.site_name || 'Rosetta'
  return `© ${currentYear} ${owner} · ${t('footer.rightsReserved', 'All rights reserved.')}`
})

// appearance.show_copyright：后台"显示版权声明"开关（此前只进库，页脚始终渲染版权行）。
// ICP 备案号与它无关，关掉开关时仍然显示。
const showCopyright = computed(() => site.appearance.value.show_copyright !== false)

// appearance.show_powered_by：后台"显示 Powered by 标识"。此前整页没有这一行，
// 开关自然无人消费；现在是真渲染，关掉即消失（不留 visibility:hidden 的假开关）。
const showPoweredBy = computed(() => site.appearance.value.show_powered_by !== false)
// footer.text（后台"页脚 Powered by 文案"）非空时覆写内置四语文案。
const poweredByLine = computed(
  () => siteConfig.value.powered_by_text || t('footer.poweredBy', 'Powered by Rosetta')
)

const quickLocales = [
  { code: 'zh', label: '简体中文', flag: 'cn' },
  { code: 'en', label: 'English', flag: 'us' },
  { code: 'ja', label: '日本語', flag: 'jp' },
  { code: 'zh_Hant', label: '繁體中文', flag: 'tw' }
]

const handleSetLocale = async (code: string) => {
  if (code === locale.value) return
  await setLocale(code as 'zh' | 'en' | 'ja' | 'zh_Hant')
  if (!import.meta.client) return
  try {
    // 单一持久位：rosetta_lang 只给 locale-prefix.global.client.ts 做跨页保序
    // （接口语言一律由 URL 前缀决定：lang 参数 + Accept-Language，后端不再读这枚 cookie；
    // @nuxtjs/i18n 的语言检测已整个关掉）。
    document.cookie = `rosetta_lang=${code}; path=/; max-age=31536000; SameSite=Lax`
  } catch {
    /* ignore */
  }
  // 只 setLocale 不改 URL 的话，页面内容换了语言、地址栏却还是默认语言的路径，
  // 与 canonical/hreflang 判成的"这一页是中文版"直接冲突（顶部切换器同口径）。
  const next = applyLocalePrefix(route.fullPath, code)
  if (next && next !== route.fullPath) await navigateTo(next, { redirectCode: 302, replace: true })
}
</script>

<template>
  <footer
    v-if="!isMinimalTheme"
    class="border-t bg-muted/30"
  >
    <div class="container mx-auto py-12 md:py-16">
      <div class="grid grid-cols-1 gap-10 md:grid-cols-2 lg:grid-cols-12">
        <!-- Brand column -->
        <div class="lg:col-span-4">
          <NuxtLink
            :to="localeHref('/')"
            class="inline-flex items-center gap-2 font-display text-xl font-bold tracking-tight mb-4"
          >
            <img
              :src="siteConfig.site_logo"
              :alt="siteConfig.site_name"
              width="24"
              height="24"
              class="size-6 dark:contrast-0 dark:brightness-200 object-contain"
              loading="lazy"
              decoding="async"
              @error="(e: Event) => { (e.currentTarget as HTMLElement).style.display = 'none' }"
            >
            {{ siteConfig.site_name }}
          </NuxtLink>
          <p class="text-sm text-muted-foreground leading-relaxed mb-6 max-w-sm">
            {{ siteConfig.footer_slogan || siteConfig.site_description || t('footer.description', '穿越语言的边界 · Modern Blog System') }}
          </p>
          <!-- 管理员在站点设置 footer_custom_html 注入的自定义 HTML 片段（统计脚本、验证标签等）；已经过 lib/sanitize 白名单清洗 -->
          <!-- eslint-disable-next-line vue/no-v-html -->
          <div
            v-if="footerCustomHtml"
            class="mb-6 text-sm text-muted-foreground [&_a]:text-primary [&_a]:underline-offset-2"
            v-html="footerCustomHtml"
          />
          <!-- 社交链接：不使用 Button asChild 组合，避免 SSR 渲染 <a> 但客户端
               asChild slot 透传时序问题导致 undefined → Hydration mismatch。
               直接使用原生 <a> 并手写与 Button(ghost,icon) 相同的 class，SSR/客户端字节级一致。 -->
          <div class="flex items-center gap-2 mb-6">
            <a
              v-if="siteConfig.github_url"
              :href="siteConfig.github_url"
              target="_blank"
              rel="noreferrer"
              :aria-label="t('footer.githubLabel', 'GitHub')"
              class="inline-flex h-9 w-9 items-center justify-center rounded-md text-sm font-medium transition-colors hover:bg-accent hover:text-accent-foreground focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring disabled:pointer-events-none disabled:opacity-50 [&_svg]:pointer-events-none [&_svg]:size-4 [&_svg]:shrink-0"
            >
              <svg
                viewBox="0 0 24 24"
                fill="currentColor"
                aria-hidden="true"
              >
                <path d="M12 .587c-6.627 0-12 5.373-12 12 0 5.303 3.438 9.8 8.205 11.387.6.113.82-.258.82-.577 0-.285-.01-1.04-.015-2.04-3.338.724-4.042-1.61-4.042-1.61-.546-1.387-1.333-1.756-1.333-1.756-1.089-.745.083-.729.083-.729 1.205.084 1.839 1.237 1.839 1.237 1.07 1.834 2.807 1.304 3.492.997.108-.776.419-1.305.762-1.605-2.665-.305-5.467-1.334-5.467-5.931 0-1.311.469-2.381 1.236-3.221-.124-.303-.535-1.524.117-3.176 0 0 1.008-.322 3.301 1.23a11.507 11.507 0 013.003-.404c1.02.005 2.047.138 3.006.404 2.291-1.552 3.297-1.23 3.297-1.23.653 1.653.242 2.874.118 3.176.77.84 1.235 1.911 1.235 3.221 0 4.609-2.807 5.624-5.479 5.921.43.372.823 1.102.823 2.222 0 1.606-.015 2.896-.015 3.286 0 .315.217.695.825.577 4.765-1.589 8.199-6.086 8.199-11.386 0-6.627-5.373-12-12-12z" />
              </svg>
            </a>
            <a
              v-if="showRssIcon"
              href="/rss.xml"
              :aria-label="t('footer.rssLabel', 'RSS')"
              class="inline-flex h-9 w-9 items-center justify-center rounded-md text-sm font-medium transition-colors hover:bg-accent hover:text-accent-foreground focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring disabled:pointer-events-none disabled:opacity-50 [&_svg]:pointer-events-none [&_svg]:size-4 [&_svg]:shrink-0"
            >
              <svg
                viewBox="0 0 24 24"
                fill="currentColor"
                aria-hidden="true"
              >
                <path d="M5 3a1 1 0 00-1 1v2a15 15 0 0115 15h2a1 1 0 001-1A18 18 0 005 3zm0 6a1 1 0 00-1 1v2a9 9 0 019 9h2a1 1 0 001-1A12 12 0 005 9zm2.5 6a2.5 2.5 0 100 5 2.5 2.5 0 000-5z" />
              </svg>
            </a>
          </div>
        </div>

        <!-- Navigation (真实存在的页面) -->
        <div class="lg:col-span-3">
          <h4 class="font-bold uppercase tracking-wider text-xs text-muted-foreground mb-4">
            {{
              sectionTitle('footer.navigation', {
                zh: '网站导航',
                en: 'NAVIGATION',
                ja: 'ナビゲーション',
                zh_Hant: '網站導覽'
              })
            }}
          </h4>
          <ul class="flex flex-col gap-3">
            <li
              v-for="link in visibleSiteLinks"
              :key="link.to"
            >
              <NuxtLink
                :to="localeHref(link.to!)"
                class="text-sm text-muted-foreground hover:text-foreground transition-colors"
              >
                {{ siteLabel(link) }}
              </NuxtLink>
            </li>
            <!-- 后台配的位置=页脚的菜单项（location=footer）；父项在前、子项缩进一档，
                 子项在 SSR HTML 里是真实 <a>，爬虫读得到完整内链图。 -->
            <li
              v-for="link in flattenNavLinks(footerNavLinks)"
              :key="`nav-${link.to}`"
              :class="link.depth > 0 ? 'pl-3' : ''"
            >
              <NuxtLink
                :to="localeHref(link.to)"
                :target="link.target"
                :rel="link.target === '_blank' ? 'noopener noreferrer' : undefined"
                class="text-sm text-muted-foreground hover:text-foreground transition-colors"
              >
                {{ link.label }}
              </NuxtLink>
            </li>
          </ul>
        </div>

        <!-- Categories (真实后端分类接口) -->
        <div class="lg:col-span-2">
          <h4 class="font-bold uppercase tracking-wider text-xs text-muted-foreground mb-4">
            {{
              sectionTitle('footer.categories', {
                zh: '内容分类',
                en: 'CATEGORIES',
                ja: 'カテゴリ',
                zh_Hant: '內容分類'
              })
            }}
          </h4>
          <ul class="flex flex-col gap-3">
            <li
              v-for="link in categoryLinks"
              :key="link.to"
            >
              <NuxtLink
                :to="localeHref(link.to!)"
                class="text-sm text-muted-foreground hover:text-foreground transition-colors"
              >
                {{ link.labelKey }}
              </NuxtLink>
            </li>
            <li v-if="categoryLinks.length === 0">
              <span class="text-sm text-muted-foreground/60">
                {{ t('footer.noCategories', '暂无分类') }}
              </span>
            </li>
          </ul>
        </div>

        <!-- Resources + Socials -->
        <div class="lg:col-span-3">
          <h4 class="font-bold uppercase tracking-wider text-xs text-muted-foreground mb-4">
            {{
              sectionTitle('footer.resources', {
                zh: '快速导航',
                en: 'RESOURCES',
                ja: 'リソース',
                zh_Hant: '快速導覽'
              })
            }}
          </h4>
          <ul class="flex flex-col gap-3">
            <li
              v-for="link in visibleResourceLinks"
              :key="link.href"
            >
              <a
                :href="link.href"
                class="text-sm text-muted-foreground hover:text-foreground transition-colors"
              >
                {{ resourceLabel(link.labelKey) }}
              </a>
            </li>
            <li
              v-for="link in socialLinks"
              :key="link.href"
            >
              <a
                :href="link.href"
                target="_blank"
                rel="noreferrer"
                class="text-sm text-muted-foreground hover:text-foreground transition-colors"
              >
                {{ socialLabel(link.labelKey) }}
              </a>
            </li>
          </ul>
        </div>
      </div>

      <Separator class="my-10" />

      <div class="flex flex-col md:flex-row justify-between items-center gap-4">
        <div class="text-xs text-muted-foreground text-center md:text-left">
          <span v-if="siteConfig.icp_number">{{ siteConfig.icp_number }} · </span>
          <span v-if="siteConfig.police_icp_number">{{ siteConfig.police_icp_number }} · </span>
          <template v-if="showCopyright">
            {{ copyrightLine }}
          </template>
          <span
            v-if="showPoweredBy"
            class="block"
          >
            {{ poweredByLine }}
          </span>
        </div>
        <!-- Quick locale switch (with flags) -->
        <div class="flex items-center gap-2 flex-wrap">
          <button
            v-for="loc in quickLocales"
            :key="loc.code"
            type="button"
            class="group inline-flex items-center gap-1.5 rounded-md px-2 py-1 text-xs text-muted-foreground hover:text-foreground hover:bg-accent transition-colors"
            @click="handleSetLocale(loc.code)"
          >
            <span
              class="fi rounded-sm shrink-0"
              :class="`fi-${loc.flag}`"
              style="font-size: 14px; line-height: 1;"
              aria-hidden="true"
            />
            <span>{{ loc.label }}</span>
          </button>
        </div>
      </div>
    </div>
  </footer>

  <!-- ============ 极简主题瘦身页脚（astro-paper-inspired） ============ -->
  <footer
    v-else
    class="ap-footer-min border-t"
  >
    <div class="container mx-auto py-10 text-center">
      <!-- 管理员注入的自定义 HTML 片段（统计脚本、验证标签等）；已经过 lib/sanitize 白名单清洗 -->
      <!-- eslint-disable-next-line vue/no-v-html -->
      <div
        v-if="footerCustomHtml"
        class="mb-5 text-xs text-muted-foreground [&_a]:underline [&_a]:underline-offset-2"
        v-html="footerCustomHtml"
      />

      <!-- 导航链接行 -->
      <nav class="mb-5 flex flex-wrap items-center justify-center gap-x-4 gap-y-2">
        <NuxtLink
          v-for="link in visibleSiteLinks"
          :key="link.to"
          :to="localeHref(link.to!)"
          class="text-xs text-muted-foreground hover:text-foreground transition-colors"
        >
          {{ siteLabel(link) }}
        </NuxtLink>
        <!-- 极简骨架同样要渲染 location=footer：两副骨架少一副就是「换个主题菜单项消失」 -->
        <NuxtLink
          v-for="link in flattenNavLinks(footerNavLinks)"
          :key="`nav-${link.to}`"
          :to="localeHref(link.to)"
          :target="link.target"
          :rel="link.target === '_blank' ? 'noopener noreferrer' : undefined"
          :class="[
            'text-xs text-muted-foreground hover:text-foreground transition-colors',
            link.depth > 0 ? 'pl-2' : ''
          ]"
        >
          {{ link.label }}
        </NuxtLink>
      </nav>

      <!-- 语言切换 -->
      <div class="mb-4 flex flex-wrap items-center justify-center gap-x-3 gap-y-1">
        <button
          v-for="loc in quickLocales"
          :key="loc.code"
          type="button"
          class="inline-flex items-center gap-1.5 text-xs text-muted-foreground hover:text-foreground transition-colors"
          @click="handleSetLocale(loc.code)"
        >
          <span
            class="fi rounded-sm shrink-0"
            :class="`fi-${loc.flag}`"
            style="font-size: 13px; line-height: 1;"
            aria-hidden="true"
          />
          <span>{{ loc.label }}</span>
        </button>
      </div>

      <!-- 版权 -->
      <div class="text-xs text-muted-foreground">
        <span v-if="siteConfig.icp_number">{{ siteConfig.icp_number }} · </span>
        <span v-if="siteConfig.police_icp_number">{{ siteConfig.police_icp_number }} · </span>
        <template v-if="showCopyright">
          {{ copyrightLine }}
        </template>
        <span
          v-if="showPoweredBy"
          class="block"
        >
          {{ poweredByLine }}
        </span>
      </div>
    </div>
  </footer>
</template>
