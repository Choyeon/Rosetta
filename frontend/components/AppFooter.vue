<script setup lang="ts">
import { Button } from '~~/components/ui/button'
import { Separator } from '~~/components/ui/separator'
import type { Category } from '~~/types/api'
import { useAPI } from '~~/composables/useApi'
import { useI18n } from 'vue-i18n'

const { t, locale, setLocale } = useI18n()

const currentYear = new Date().getFullYear()

interface FooterLink {
  labelKey: string
  to?: string
  href?: string
  external?: boolean
}

const { data: categories } = await useAPI<Category[]>('/blog/categories', {
  query: { lang: locale.value },
  key: `footer:categories:${locale.value}`,
  default: () => []
})

const pickLocalized = (value: string | Record<string, string>): string => {
  if (typeof value === 'string') return value
  return value[locale.value] || value.zh || Object.values(value)[0] || ''
}

const categoryLinks = computed<FooterLink[]>(() => (categories.value || []).map(category => ({
  labelKey: pickLocalized(category.name),
  to: `/posts?category=${encodeURIComponent(category.slug)}`
})))

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
  copyright_text: string | null
  footer_custom_html: string
  icp_number: string
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
  const footerSlogan = f.slogan || f.text || readStr('footer_slogan', siteDescription)
  const copyrightText = (publicCfg.copyright_text as string | null) ?? null
  const footerCustomHtml = (publicCfg.footer_custom_html as string) || ''

  return {
    site_name: siteName,
    site_author: readStr('site_author', siteName),
    site_description: siteDescription,
    site_logo: b.logo || readStr('site_logo', '') || '/logo/rosetta-monochrome-icon.png',
    footer_slogan: footerSlogan,
    copyright_text: copyrightText && String(copyrightText).trim() ? String(copyrightText) : null,
    footer_custom_html: footerCustomHtml,
    icp_number: b.icp_number || f.icp_number || readStr('icp_number', ''),
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

const socialLinks = computed<FooterLink[]>(() => {
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

// 最终显示的版权文字：站点设置 copyright_text 优先 → 否则生成默认格式
const copyrightLine = computed(() => {
  if (siteConfig.value.copyright_text) return siteConfig.value.copyright_text
  const owner = siteConfig.value.site_author || siteConfig.value.site_name || 'Rosetta'
  return `© ${currentYear} ${owner} · ${t('footer.rightsReserved', 'All rights reserved.')}`
})

const quickLocales = [
  { code: 'zh', label: '简体中文', flag: 'cn' },
  { code: 'en', label: 'English', flag: 'us' },
  { code: 'ja', label: '日本語', flag: 'jp' },
  { code: 'zh_Hant', label: '繁體中文', flag: 'tw' }
]

const handleSetLocale = async (code: string) => {
  await setLocale(code as 'zh' | 'en' | 'ja' | 'zh_Hant')
  try {
    if (import.meta.client) {
      document.cookie = `i18n_redirected=${code}; path=/; max-age=31536000; SameSite=Lax`
    }
  } catch {
    /* ignore */
  }
}
</script>

<template>
  <footer class="border-t bg-muted/30">
    <div class="container mx-auto py-12 md:py-16">
      <div class="grid grid-cols-1 gap-10 md:grid-cols-2 lg:grid-cols-12">
        <!-- Brand column -->
        <div class="lg:col-span-4">
          <NuxtLink
            to="/"
            class="inline-flex items-center gap-2 font-display text-xl font-bold tracking-tight mb-4"
          >
            <img
              :src="siteConfig.site_logo"
              :alt="siteConfig.site_name"
              class="size-6 h-6 w-6 dark:contrast-0 dark:brightness-200 object-contain"
              loading="lazy"
              @error="(e: any) => { e.currentTarget.style.display = 'none' }"
            >
            {{ siteConfig.site_name }}
          </NuxtLink>
          <p class="text-sm text-muted-foreground leading-relaxed mb-6 max-w-sm">
            {{ siteConfig.footer_slogan || siteConfig.site_description || t('footer.description', '穿越语言的边界 · Modern Blog System') }}
          </p>
          <!-- 管理员在站点设置 footer_custom_html 注入的自定义 HTML 片段（统计脚本、验证标签等） -->
          <div
            v-if="siteConfig.footer_custom_html"
            class="mb-6 text-sm text-muted-foreground [&_a]:text-primary [&_a]:underline-offset-2"
            v-html="siteConfig.footer_custom_html"
          />
          <div class="flex items-center gap-2 mb-6">
            <Button
              v-if="siteConfig.github_url"
              variant="ghost"
              size="icon"
              as-child
            >
              <a
                :href="siteConfig.github_url"
                target="_blank"
                rel="noreferrer"
                :aria-label="t('footer.githubLabel', 'GitHub')"
              >
                <svg
                  viewBox="0 0 24 24"
                  class="h-4 w-4"
                  fill="currentColor"
                  aria-hidden="true"
                >
                  <path d="M12 .587c-6.627 0-12 5.373-12 12 0 5.303 3.438 9.8 8.205 11.387.6.113.82-.258.82-.577 0-.285-.01-1.04-.015-2.04-3.338.724-4.042-1.61-4.042-1.61-.546-1.387-1.333-1.756-1.333-1.756-1.089-.745.083-.729.083-.729 1.205.084 1.839 1.237 1.839 1.237 1.07 1.834 2.807 1.304 3.492.997.108-.776.419-1.305.762-1.605-2.665-.305-5.467-1.334-5.467-5.931 0-1.311.469-2.381 1.236-3.221-.124-.303-.535-1.524.117-3.176 0 0 1.008-.322 3.301 1.23a11.507 11.507 0 013.003-.404c1.02.005 2.047.138 3.006.404 2.291-1.552 3.297-1.23 3.297-1.23.653 1.653.242 2.874.118 3.176.77.84 1.235 1.911 1.235 3.221 0 4.609-2.807 5.624-5.479 5.921.43.372.823 1.102.823 2.222 0 1.606-.015 2.896-.015 3.286 0 .315.217.695.825.577 4.765-1.589 8.199-6.086 8.199-11.386 0-6.627-5.373-12-12-12z" />
                </svg>
              </a>
            </Button>
            <Button
              variant="ghost"
              size="icon"
              as-child
            >
              <a
                href="/rss.xml"
                :aria-label="t('footer.rssLabel', 'RSS')"
              >
                <svg
                  viewBox="0 0 24 24"
                  class="h-4 w-4"
                  fill="currentColor"
                  aria-hidden="true"
                >
                  <path d="M5 3a1 1 0 00-1 1v2a15 15 0 0115 15h2a1 1 0 001-1A18 18 0 005 3zm0 6a1 1 0 00-1 1v2a9 9 0 019 9h2a1 1 0 001-1A12 12 0 005 9zm2.5 6a2.5 2.5 0 100 5 2.5 2.5 0 000-5z" />
                </svg>
              </a>
            </Button>
          </div>
          <p class="text-xs text-muted-foreground">
            {{ copyrightLine }}
          </p>
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
          <ul class="space-y-3">
            <li
              v-for="link in siteLinks"
              :key="link.to"
            >
              <NuxtLink
                :to="link.to!"
                class="text-sm text-muted-foreground hover:text-foreground transition-colors"
              >
                {{ siteLabel(link) }}
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
          <ul class="space-y-3">
            <li
              v-for="link in categoryLinks"
              :key="link.to"
            >
              <NuxtLink
                :to="link.to!"
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
          <ul class="space-y-3">
            <li
              v-for="link in resourceLinks"
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
          © {{ currentYear }} {{ siteConfig.site_author || siteConfig.site_name }}
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
</template>
