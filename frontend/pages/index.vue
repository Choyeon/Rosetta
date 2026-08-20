<template>
  <div>
    <!-- ===== HERO: Bing Daily Wallpaper Section (pure wallpaper, no text) ===== -->
    <section
      class="relative min-h-[80vh] md:min-h-[86vh] overflow-hidden"
      :style="{
        backgroundImage: currentWallpaper ? `url(${currentWallpaper.fullUrl})` : undefined,
        backgroundSize: 'cover',
        backgroundPosition: 'center center',
        backgroundRepeat: 'no-repeat',
        backgroundAttachment: 'local'
      }"
    >
      <!-- Subtle depth overlays (no text → lighter gradients, just cinematic framing) -->
      <div class="absolute inset-0 bg-gradient-to-t from-black/65 via-black/5 to-transparent pointer-events-none" />
      <div class="absolute inset-0 bg-gradient-to-r from-black/35 via-black/5 to-black/10 pointer-events-none" />
      <div class="absolute inset-0 bg-gradient-to-b from-black/20 via-transparent to-transparent pointer-events-none" />

      <!-- Bottom HUD: 7-day switcher (left) + Photo meta + credit (right) -->
      <div class="absolute bottom-0 left-0 right-0 z-20">
        <div class="container relative pb-10 md:pb-12 flex flex-col sm:flex-row items-stretch sm:items-end justify-between gap-4">
          <!-- 7-day switcher → elegant per-day cards: gradient underlay + img overlay + center date -->
          <div
            class="rounded-2xl border border-white/15 bg-black/45 backdrop-blur-xl px-3 py-3 flex items-center gap-2 shadow-2xl shadow-black/40"
          >
            <div class="hidden sm:flex flex-col pr-2 pl-1 border-r border-white/10 justify-center">
              <span class="text-[10px] uppercase tracking-[0.14em] text-white/60">{{ t('home.wallpaper') }}</span>
              <span class="text-xs font-medium text-white/90">{{ t('home.recent7Days') }}</span>
            </div>
            <div class="flex items-center gap-2">
              <button
                v-for="day in recentDays"
                :key="day.index"
                type="button"
                class="group relative size-11 sm:size-14 rounded-lg overflow-hidden ring-1 ring-white/15 transition-all duration-200 shrink-0"
                :class="currentIdx === day.index
                  ? 'ring-2 ring-white/90 scale-105 shadow-[0_0_0_2px_rgba(255,255,255,0.1),0_8px_24px_-6px_rgba(0,0,0,0.6)]'
                  : 'hover:ring-white/60 hover:scale-[1.03] opacity-85 hover:opacity-100'"
                :aria-label="day.label"
                :title="day.title || day.label"
                @click="selectWallpaper(day.index)"
              >
                <div class="absolute inset-0 z-10 flex flex-col items-center justify-center text-white">
                  <span class="text-[15px] sm:text-[17px] font-bold leading-none tracking-tight drop-shadow-[0_1px_4px_rgba(0,0,0,0.5)]">
                    {{ day.dateCompact.main }}
                  </span>
                  <span class="text-[9px] sm:text-[10px] mt-1 leading-none tracking-[0.08em] opacity-90 drop-shadow-[0_1px_2px_rgba(0,0,0,0.45)]">
                    {{ day.dateCompact.sub }}
                  </span>
                </div>
                <!-- Thumbnail image → covers gradient when successfully loaded -->
                <img
                  v-if="day.thumbnail"
                  :src="day.thumbnail"
                  :alt="day.title || day.label"
                  class="absolute inset-0 w-full h-full object-cover transition-opacity duration-300 ease-out z-20"
                  loading="lazy"
                >
              </button>
            </div>
          </div>

          <!-- Photo credit (right) → no COPYRIGHT label prefix; show image title first, then credit -->
          <a
            v-if="currentWallpaper?.copyright || currentWallpaper?.title || currentWallpaper?.copyrightlink"
            :href="currentWallpaper.copyrightlink || '#'"
            target="_blank"
            rel="noreferrer noopener"
            class="rounded-2xl border border-white/15 bg-black/45 backdrop-blur-xl px-4 py-3 max-w-lg sm:text-right text-xs sm:text-sm text-white/85 hover:text-white transition-colors shadow-2xl shadow-black/40 hover:bg-black/60"
          >
            <div
              v-if="currentWallpaper.title"
              class="text-sm sm:text-base font-semibold text-white leading-snug mb-1"
            >
              {{ currentWallpaper.title }}
            </div>
            <span
              v-if="currentWallpaper.copyright"
              class="line-clamp-2 leading-snug text-white/75"
            >{{ currentWallpaper.copyright }}</span>
          </a>
        </div>
      </div>
    </section>

    <section class="container py-14 md:py-20">
      <div class="flex items-end justify-between mb-8 gap-6 flex-wrap">
        <div>
          <div class="flex items-center gap-2 text-xs uppercase tracking-[0.16em] text-muted-foreground">
            <span class="size-1.5 rounded-full bg-warning" />
            {{ t('posts.pinned') }}
          </div>
          <h2 class="mt-2 font-display text-2xl md:text-3xl font-bold tracking-tight">
            {{ t('posts.pinned') }}
          </h2>
        </div>
      </div>

      <div
        v-if="postsError"
        class="rounded-xl border border-destructive/30 bg-destructive/5 p-6 text-sm text-destructive"
      >
        {{ t('admin.posts.loadFailed') }}
      </div>
      <div
        v-else-if="postsPending && pinnedPosts.length === 0"
        class="grid grid-cols-1 lg:grid-cols-3 gap-6"
      >
        <Skeleton
          v-for="i in 3"
          :key="i"
          class="aspect-[16/10] rounded-2xl"
        />
      </div>
      <div
        v-else-if="pinnedPosts.length === 0"
        class="rounded-xl border bg-muted/30 p-6 text-sm text-muted-foreground"
      >
        {{ t('admin.posts.empty') }}
      </div>
      <div
        v-else
        class="grid grid-cols-1 lg:grid-cols-3 gap-6 items-start"
      >
        <PostCard
          v-for="post in pinnedPosts"
          :key="post.id"
          :post="post"
        />
      </div>
    </section>

    <!-- ===== LATEST + SIDEBAR ===== -->
    <section class="container pb-16">
      <div class="grid grid-cols-1 lg:grid-cols-3 gap-10">
        <div class="lg:col-span-2">
          <div class="flex items-end justify-between mb-6 gap-4 flex-wrap">
            <div>
              <div class="flex items-center gap-2 text-xs uppercase tracking-[0.16em] text-muted-foreground">
                <span class="size-1.5 rounded-full bg-primary" />
                {{ t('home.latestPosts') }}
              </div>
              <h2 class="mt-2 font-display text-2xl font-bold tracking-tight">
                {{ t('home.latestPosts') }}
              </h2>
            </div>
            <NuxtLink
              to="/posts"
              class="text-sm text-muted-foreground hover:text-foreground inline-flex items-center gap-1 transition-colors"
            >
              {{ t('home.viewAll') }}
              <ArrowRight class="size-3.5" />
            </NuxtLink>
          </div>

          <div class="flex flex-col gap-5">
            <div
              v-if="postsError"
              class="rounded-xl border border-destructive/30 bg-destructive/5 p-6 text-sm text-destructive"
            >
              {{ t('admin.posts.loadFailed') }}
            </div>
            <template v-else-if="postsPending && latestPosts.length === 0">
              <Skeleton
                v-for="i in 4"
                :key="i"
                class="h-[200px] rounded-2xl"
              />
            </template>
            <template v-else-if="latestPosts.length > 0">
              <PostCard
                v-for="post in latestPosts"
                :key="post.id"
                :post="post"
                variant="compact"
              />
            </template>
            <div
              v-else
              class="rounded-xl border bg-muted/30 p-6 text-sm text-muted-foreground"
            >
              {{ t('admin.posts.empty') }}
            </div>
          </div>
        </div>

        <!-- Sidebar -->
        <aside class="flex flex-col gap-6">
          <!-- Site stats -->
          <Card>
            <CardHeader>
              <CardTitle class="text-lg flex items-center gap-2">
                <BarChart3 class="size-4 text-primary" />
                {{ t('home.siteStats') }}
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div
                v-if="siteStatsError"
                class="text-sm text-destructive"
              >
                {{ t('admin.posts.loadFailed') }}
              </div>
              <div
                v-else-if="siteStatsPending"
                class="grid grid-cols-2 gap-3"
              >
                <Skeleton
                  v-for="i in 4"
                  :key="i"
                  class="h-24 rounded-xl"
                />
              </div>
              <div
                v-else-if="siteStats"
                class="grid grid-cols-2 gap-3"
              >
                <div class="rounded-xl bg-muted/50 p-4">
                  <div class="text-2xl font-bold font-display">
                    {{ siteStats.total_posts }}
                  </div>
                  <div class="text-xs text-muted-foreground mt-1">
                    {{ t('home.postsCount') }}
                  </div>
                </div>
                <div class="rounded-xl bg-muted/50 p-4">
                  <div class="text-2xl font-bold font-display">
                    {{ siteStats.total_categories }}
                  </div>
                  <div class="text-xs text-muted-foreground mt-1">
                    {{ t('home.categoriesCount') }}
                  </div>
                </div>
                <div class="rounded-xl bg-muted/50 p-4">
                  <div class="text-2xl font-bold font-display">
                    {{ siteStats.total_tags }}
                  </div>
                  <div class="text-xs text-muted-foreground mt-1">
                    {{ t('home.tagsCount') }}
                  </div>
                </div>
                <div class="rounded-xl bg-muted/50 p-4">
                  <div class="text-2xl font-bold font-display">
                    {{ siteStats.total_words }}
                  </div>
                  <div class="text-xs text-muted-foreground mt-1">
                    {{ t('post.words') }}
                  </div>
                </div>
              </div>
              <div
                v-else
                class="text-sm text-muted-foreground"
              >
                {{ t('common.noData') }}
              </div>
            </CardContent>
          </Card>

          <!-- Tech stack versions -->
          <Card>
            <CardHeader>
              <CardTitle class="text-lg flex items-center gap-2">
                <Server class="size-4 text-success" />
                {{ t('home.techStack') }}
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div class="space-y-2.5 text-sm">
                <template
                  v-for="(row, idx) in techRows"
                  :key="row.key"
                >
                  <div class="flex items-center justify-between gap-3">
                    <div class="flex items-center gap-2 min-w-0">
                      <span
                        class="shrink-0 size-2 rounded-full"
                        :class="row.color"
                      />
                      <span class="text-muted-foreground truncate">{{ row.label }}</span>
                    </div>
                    <code class="font-mono text-xs px-2 py-0.5 rounded-md bg-muted/70 text-foreground/90 truncate max-w-[55%] tabular-nums">
                      v{{ buildInfo[row.key] }}
                    </code>
                  </div>
                  <div
                    v-if="idx === 4 || idx === 6"
                    class="my-2 border-t border-border"
                  />
                </template>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle class="text-lg flex items-center gap-2">
                <FolderOpen class="size-4 text-warning" />
                {{ t('nav.categories') }}
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div
                v-if="categoriesError"
                class="text-sm text-destructive"
              >
                {{ t('admin.posts.loadFailed') }}
              </div>
              <div
                v-else-if="categoriesPending"
                class="flex flex-wrap gap-2"
              >
                <Skeleton
                  v-for="i in 4"
                  :key="i"
                  class="h-6 w-16 rounded-full"
                />
              </div>
              <div
                v-else-if="categories.length"
                class="flex flex-wrap gap-2"
              >
                <Badge
                  v-for="category in categories"
                  :key="category.id"
                  variant="secondary"
                  class="cursor-pointer hover:bg-secondary/80 transition-colors"
                  @click="navigateTo(`/posts?category=${category.slug}`)"
                >
                  {{ pickLocalized(category.name) }}
                </Badge>
              </div>
              <div
                v-else
                class="text-sm text-muted-foreground"
              >
                {{ t('common.noData') }}
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle class="text-lg flex items-center gap-2">
                <Tag class="size-4 text-success" />
                {{ t('home.tagCloud') }}
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div
                v-if="tagsError"
                class="text-sm text-destructive"
              >
                {{ t('admin.posts.loadFailed') }}
              </div>
              <div
                v-else-if="tagsPending"
                class="flex flex-wrap gap-1.5"
              >
                <Skeleton
                  v-for="i in 6"
                  :key="i"
                  class="h-6 w-14 rounded-full"
                />
              </div>
              <div
                v-else-if="tags.length"
                class="flex flex-wrap gap-1.5"
              >
                <Badge
                  v-for="tag in tags"
                  :key="tag.id"
                  variant="outline"
                  class="cursor-pointer hover:bg-accent transition-colors"
                  @click="navigateTo(`/posts?tag=${tag.slug}`)"
                >
                  #{{ pickLocalized(tag.name) }}
                </Badge>
              </div>
              <div
                v-else
                class="text-sm text-muted-foreground"
              >
                {{ t('common.noData') }}
              </div>
            </CardContent>
          </Card>
        </aside>
      </div>
    </section>

    <!-- ===== Newsletter / Guestbook CTA ===== -->
    <section class="container pb-24">
      <Card class="rounded-2xl border-0 bg-gradient-to-br from-slate-50 via-white to-indigo-50 dark:from-slate-900 dark:via-background dark:to-indigo-950/20 shadow-soft overflow-hidden">
        <CardContent class="p-10 md:p-14 text-center max-w-2xl mx-auto relative">
          <div class="absolute inset-0 bg-[radial-gradient(ellipse_at_center,rgba(99,102,241,0.08),transparent_70%)] pointer-events-none" />
          <div class="relative">
            <h2 class="font-display text-2xl md:text-3xl font-bold tracking-tight">
              {{ t('home.ctaTitle') }}
            </h2>
            <p class="text-muted-foreground mt-3 leading-relaxed">
              {{ t('home.ctaSubtitle') }}
            </p>
            <div class="mt-8 flex flex-col sm:flex-row gap-3 justify-center">
              <Button
                size="lg"
                @click="navigateTo('/guestbook')"
              >
                {{ t('home.goGuestbook') }}
              </Button>
              <Button
                size="lg"
                variant="outline"
                @click="navigateTo('/about')"
              >
                {{ t('home.goAbout') }}
              </Button>
            </div>
          </div>
        </CardContent>
      </Card>
    </section>
  </div>
</template>

<script setup lang="ts">
import { Card, CardContent, CardHeader, CardTitle } from '~~/components/ui/card'
import { Button } from '~~/components/ui/button'
import { Badge } from '~~/components/ui/badge'
import { Skeleton } from '~~/components/ui/skeleton'
import PostCard from '~~/components/PostCard.vue'
import type { Category, PaginatedResponse, Post, SiteStats, Tag as BlogTag } from '~~/types/api'
import { useAPI } from '~~/composables/useApi'
import { useBingWallpaper } from '~~/composables/useBingWallpaper'
import { useSiteVersions } from '~~/composables/useSiteVersions'
import { useI18n } from 'vue-i18n'
import { ArrowRight, BarChart3, FolderOpen, Server, Tag } from '@lucide/vue'

definePageMeta({ layout: 'default' })

const { t, locale } = useI18n()

// ===== 站点动态配置：<title>/hero/SEO/颜色都来自 settings（/api/settings + /api/config fallback）
const site = useSite()
await site.ensureLoaded()
const _heroTitle = computed(() => site.pickI18n(site.hero.value.title))
const _heroSubtitle = computed(() => site.pickI18n(site.hero.value.subtitle))
const _heroCaption = computed(() => site.pickI18n(site.hero.value.caption))
const _heroCtaText = computed(() => site.pickI18n(site.hero.value.cta_text))
const _heroCtaUrl = computed(() => String(site.hero.value.cta_url || '/posts'))

// ===== Tech versions =====
const { buildInfo } = useSiteVersions()

// Inline tech rows — no defineComponent() with runtime string-template,
// which breaks Vue runtime + Nuxt auto-injection on Windows.
interface TechRowItem { label: string, key: keyof typeof buildInfo.value, color: string }
const techRows: TechRowItem[] = [
  { label: 'Nuxt', key: 'nuxt', color: 'bg-emerald-500' },
  { label: 'Vue', key: 'vue', color: 'bg-teal-500' },
  { label: 'Vite', key: 'vite', color: 'bg-violet-500' },
  { label: 'Tailwind', key: 'tailwindcss', color: 'bg-sky-500' },
  { label: 'Pinia', key: 'pinia', color: 'bg-yellow-500' },
  { label: 'Node', key: 'node', color: 'bg-green-600' },
  { label: 'npm', key: 'npm', color: 'bg-red-500' },
  { label: 'Python', key: 'python', color: 'bg-blue-500' },
  { label: 'FastAPI', key: 'fastapi', color: 'bg-cyan-500' }
]

// ===== Bing wallpaper =====
const {
  currentImage,
  currentIdx,
  recentDays,
  selectDay: selectWallpaper,
  fetchWallpapers
} = useBingWallpaper()

const currentWallpaper = computed(() => currentImage.value)

onMounted(() => {
  fetchWallpapers()
})

// ===== i18n helpers =====
const pickLocalized = (val: string | Record<string, string> | null | undefined): string => {
  if (val == null) return ''
  if (typeof val === 'string') return val
  if (typeof val === 'object') {
    const localeKey = locale.value as string
    if (localeKey && val[localeKey]) return val[localeKey]
    const keys = Object.keys(val)
    const firstKey = keys.length > 0 ? keys[0]! : ''
    return firstKey ? (val[firstKey] || '') : ''
  }
  return String(val)
}

const { data: postsData, pending: postsPending, error: postsError } = await useAPI<PaginatedResponse<Post>>('/blog/posts', {
  query: { lang: locale.value, page: 1, page_size: 20 },
  key: 'home:posts:' + locale.value
})

const { data: categoriesData, pending: categoriesPending, error: categoriesError } = await useAPI<Category[]>('/blog/categories', {
  query: { lang: locale.value },
  key: 'home:categories:' + locale.value
})

const { data: tagsData, pending: tagsPending, error: tagsError } = await useAPI<BlogTag[]>('/blog/tags', {
  query: { lang: locale.value },
  key: 'home:tags:' + locale.value
})

const { data: siteStats, pending: siteStatsPending, error: siteStatsError } = await useAPI<SiteStats>('/blog/site-stats', {
  key: 'home:site-stats'
})

const posts = computed<Post[]>(() => postsData.value?.items ?? [])
const pinnedPosts = computed(() => posts.value.filter(post => post.is_pinned))
const latestPosts = computed(() => posts.value.filter(post => !post.is_pinned))
const categories = computed<Category[]>(() => categoriesData.value ?? [])
const tags = computed<BlogTag[]>(() => tagsData.value ?? [])

// ===== SEO =====
const requestURL = useRequestURL()
const canonical = computed(() => requestURL.href)
const origin = computed(() => requestURL.origin)

// 用 useSite 动态标题/描述，不再硬编码 "Rosetta · ..."
// titleTemplate（plugins/site-title.global.ts）会统一拼 "单页标题 · 站点名"；
// 首页是"无单页标题"情形，titleTemplate 会退化为 "站点名 · 副标题"。
const homeTitle = computed(() => site.siteSubtitle.value || '')
const siteDescription = computed(() => site.siteDescription.value)
const siteKeywords = computed(() => site.siteKeywords.value)
const siteTitle = computed(() => site.withSuffix())
const seoOgImage = computed(() => {
  const configured = site.seo.value.og_image
  if (configured) {
    const raw = String(configured)
    if (raw.startsWith('http')) return raw
    try {
      return new URL(raw, origin.value).href
    } catch {
      return raw
    }
  }
  const raw = posts.value[0]?.cover_image || '/favicon-32x32.png'
  if (raw.startsWith('http')) return raw
  try {
    return new URL(raw, origin.value).href
  } catch {
    return raw
  }
})

useSeoMeta({
  title: homeTitle,
  description: siteDescription,
  ogTitle: siteTitle,
  ogDescription: siteDescription,
  ogImage: seoOgImage,
  ogType: 'website',
  ogUrl: canonical,
  twitterCard: 'summary_large_image',
  twitterTitle: siteTitle,
  twitterDescription: siteDescription,
  twitterImage: seoOgImage
})
useHead({
  meta: [
    { name: 'keywords', content: siteKeywords }
  ],
  link: [
    { rel: 'canonical', href: canonical }
  ],
  script: [
    {
      type: 'application/ld+json',
      innerHTML: JSON.stringify({
        '@context': 'https://schema.org',
        '@type': 'WebSite',
        'name': site.siteTitle.value || 'Rosetta',
        'alternateName': site.siteSubtitle.value || undefined,
        'description': siteDescription.value || undefined,
        'keywords': siteKeywords.value || undefined,
        'url': origin.value
      })
    }
  ]
})
</script>
