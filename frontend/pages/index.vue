<template>
  <div>
    <!-- ===== HERO: Bing Daily Wallpaper Section (pure wallpaper, no text) ===== -->
    <section
      class="relative min-h-[80vh] md:min-h-[86vh] overflow-hidden"
      :style="{
        backgroundImage: currentWallpaper
          ? `url(${currentWallpaper.fullUrl})`
          : 'linear-gradient(135deg, #0f172a 0%, #1e293b 40%, #312e81 100%)',
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
                <!-- Elegant per-card gradient fallback (always rendered as base layer) -->
                <div
                  class="absolute inset-0"
                  :class="wallpaperCardGradient(day.index)"
                  aria-hidden="true"
                />
                <!-- Compact date overlay (always visible above gradient) -->
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
                  :class="thumbnailLoaded[day.index] === true ? 'opacity-100' : 'opacity-0 pointer-events-none'"
                  loading="lazy"
                  @load="setThumbnailState(day.index, true)"
                  @error="setThumbnailState(day.index, false)"
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

    <!-- ===== FEATURED POSTS ===== -->
    <section class="container py-14 md:py-20">
      <div class="flex items-end justify-between mb-8 gap-6 flex-wrap">
        <div>
          <div class="flex items-center gap-2 text-xs uppercase tracking-[0.16em] text-muted-foreground">
            <span class="size-1.5 rounded-full bg-warning" />
            {{ t('home.featuredLabel') }}
          </div>
          <h2 class="mt-2 font-display text-2xl md:text-3xl font-bold tracking-tight">
            {{ t('home.featuredPosts') }}
          </h2>
        </div>
        <Badge
          variant="secondary"
          class="text-xs shadow-sm"
        >
          Editor's Pick
        </Badge>
      </div>

      <div class="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
        <!-- Large featured card -->
        <div class="lg:col-span-7">
          <Skeleton
            v-if="loading && featuredPosts.length === 0"
            class="aspect-[16/10] rounded-2xl"
          />
          <PostCard
            v-else-if="featuredPosts[0]"
            :post="featuredPosts[0]"
            :is-featured="true"
          />
          <PostCard
            v-else
            :post="mockFeatured[0]!"
            :is-featured="true"
          />
        </div>
        <!-- Stacked featured cards -->
        <div class="lg:col-span-5 flex flex-col gap-6">
          <div>
            <Skeleton
              v-if="loading && featuredPosts.length === 0"
              class="aspect-[16/10] rounded-2xl"
            />
            <PostCard
              v-else-if="featuredPosts[1]"
              :post="featuredPosts[1]"
            />
            <PostCard
              v-else
              :post="mockFeatured[1]!"
            />
          </div>
          <div>
            <Skeleton
              v-if="loading && featuredPosts.length === 0"
              class="aspect-[16/10] rounded-2xl"
            />
            <PostCard
              v-else-if="featuredPosts[2]"
              :post="featuredPosts[2]"
            />
            <PostCard
              v-else
              :post="mockFeatured[2]!"
            />
          </div>
        </div>
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
                {{ t('home.latestLabel') }}
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
            <template v-if="loading && latestPosts.length === 0">
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
            <template v-else>
              <PostCard
                v-for="post in mockLatest"
                :key="post.id"
                :post="post"
                variant="compact"
              />
            </template>
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
              <div class="grid grid-cols-2 gap-3">
                <div class="rounded-xl bg-muted/50 p-4">
                  <div class="text-2xl font-bold font-display">
                    {{ totalPostsDisplay }}
                  </div>
                  <div class="text-xs text-muted-foreground mt-1">
                    {{ t('home.postsCount') }}
                  </div>
                </div>
                <div class="rounded-xl bg-muted/50 p-4">
                  <div class="text-2xl font-bold font-display">
                    {{ totalCategoriesDisplay }}
                  </div>
                  <div class="text-xs text-muted-foreground mt-1">
                    {{ t('home.categoriesCount') }}
                  </div>
                </div>
                <div class="rounded-xl bg-muted/50 p-4">
                  <div class="text-2xl font-bold font-display">
                    {{ totalTagsDisplay }}
                  </div>
                  <div class="text-xs text-muted-foreground mt-1">
                    {{ t('home.tagsCount') }}
                  </div>
                </div>
                <div class="rounded-xl bg-muted/50 p-4">
                  <div class="text-2xl font-bold font-display">
                    {{ totalViewsDisplay }}
                  </div>
                  <div class="text-xs text-muted-foreground mt-1">
                    {{ t('home.commentsCount') }}
                  </div>
                </div>
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

          <!-- Popular categories -->
          <Card>
            <CardHeader>
              <CardTitle class="text-lg flex items-center gap-2">
                <FolderOpen class="size-4 text-warning" />
                {{ t('home.popularCategories') }}
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div class="flex flex-wrap gap-2">
                <Badge
                  v-for="cat in mockCategories"
                  :key="cat.id"
                  variant="secondary"
                  class="cursor-pointer hover:bg-secondary/80 transition-colors"
                  @click="navigateTo(`/posts?category=${cat.slug}`)"
                >
                  {{ pickLocalized(cat.name) }}
                </Badge>
              </div>
            </CardContent>
          </Card>

          <!-- Tag cloud -->
          <Card>
            <CardHeader>
              <CardTitle class="text-lg flex items-center gap-2">
                <Tag class="size-4 text-success" />
                {{ t('home.tagCloud') }}
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div class="flex flex-wrap gap-1.5">
                <Badge
                  v-for="tag in mockTags"
                  :key="tag.id"
                  variant="outline"
                  class="cursor-pointer hover:bg-accent transition-colors"
                  @click="navigateTo(`/posts?tag=${tag.slug}`)"
                >
                  #{{ pickLocalized(tag.name) }}
                </Badge>
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
            <MessageSquareHeart class="size-12 mx-auto text-primary mb-4" />
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
                <Send class="size-4 mr-2" />
                {{ t('home.goGuestbook') }}
              </Button>
              <Button
                size="lg"
                variant="outline"
                @click="navigateTo('/about')"
              >
                <UserCircle class="size-4 mr-2" />
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
import type { Post, PaginatedResponse } from '~~/types/api'
import { useAPI } from '~~/composables/useApi'
import { useBingWallpaper } from '~~/composables/useBingWallpaper'
import { useSiteVersions } from '~~/composables/useSiteVersions'
import { useI18n } from 'vue-i18n'
import {
  ArrowRight,
  FolderOpen,
  Tag,
  BarChart3,
  Server,
  MessageSquareHeart,
  Send,
  UserCircle
} from '@lucide/vue'

definePageMeta({ layout: 'default' })

const { t, locale } = useI18n()

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

// ===== Thumbnail state + elegant fallback cards =====
const thumbnailLoaded = reactive<Record<number, boolean>>({})
const setThumbnailState = (i: number, ok: boolean) => {
  thumbnailLoaded[i] = ok
}

// 8 elegant gradient palettes cycled per card index
const CARD_GRADIENTS = [
  'bg-gradient-to-br from-indigo-500 via-violet-500 to-fuchsia-500',
  'bg-gradient-to-br from-amber-500 via-orange-500 to-rose-500',
  'bg-gradient-to-br from-emerald-500 via-teal-500 to-cyan-500',
  'bg-gradient-to-br from-slate-700 via-slate-500 to-sky-500',
  'bg-gradient-to-br from-pink-500 via-rose-500 to-red-500',
  'bg-gradient-to-br from-lime-500 via-green-500 to-emerald-500',
  'bg-gradient-to-br from-blue-600 via-indigo-500 to-purple-500',
  'bg-gradient-to-br from-yellow-600 via-amber-500 to-orange-500'
]
const wallpaperCardGradient = (i: number) =>
  CARD_GRADIENTS[((i % CARD_GRADIENTS.length) + CARD_GRADIENTS.length) % CARD_GRADIENTS.length]

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

// ===== Mock data =====
const mockFeatured = [
  {
    id: 1,
    slug: 'featured-1',
    title: {
      zh: '探索 Vue 3 组合式 API 的优雅设计模式',
      en: 'Exploring Elegant Design Patterns in Vue 3 Composition API'
    },
    excerpt: {
      zh: '深入理解 Composition API 背后的设计理念，以及如何在大型项目中构建可维护、可复用的组件逻辑。',
      en: 'Dive deep into the design philosophy behind Composition API and build maintainable, reusable logic for large projects.'
    },
    coverImage: 'https://images.unsplash.com/photo-1555066931-4365d14bab8c?w=1200&q=80',
    category: { id: 1, name: { zh: '前端开发', en: 'Frontend' }, slug: 'frontend' },
    author: { id: 1, name: 'Chuyu', nickname: 'Chuyu', avatar: '' },
    publishedAt: new Date(Date.now() - 86400000 * 2).toISOString(),
    views: 2341,
    commentsCount: 42
  },
  {
    id: 2,
    slug: 'featured-2',
    title: {
      zh: '现代 CSS 布局完全指南',
      en: 'The Complete Guide to Modern CSS Layout'
    },
    excerpt: {
      zh: '从 Flexbox 到 Grid，再到最新的容器查询，全面掌握现代 CSS 布局的核心技巧。',
      en: 'From Flexbox to Grid and Container Queries — master the core of modern CSS layout.'
    },
    coverImage: 'https://images.unsplash.com/photo-1523437113738-bbd3cc89fb19?w=1000&q=80',
    category: { id: 2, name: { zh: 'CSS', en: 'CSS' }, slug: 'css' },
    author: { id: 2, name: 'Chuyu', nickname: 'Chuyu', avatar: '' },
    publishedAt: new Date(Date.now() - 86400000 * 5).toISOString(),
    views: 1823,
    commentsCount: 28
  },
  {
    id: 3,
    slug: 'featured-3',
    title: {
      zh: 'TypeScript 类型体操进阶',
      en: 'Advanced TypeScript Type Gymnastics'
    },
    excerpt: {
      zh: '高级类型编程实战：条件类型、映射类型与模板字面量的创造性应用。',
      en: 'Hands-on advanced type programming: conditional types, mapped types and template literals.'
    },
    coverImage: 'https://images.unsplash.com/photo-1516116216624-53e697fedbea?w=1000&q=80',
    category: { id: 3, name: { zh: 'TypeScript', en: 'TypeScript' }, slug: 'typescript' },
    author: { id: 3, name: 'Chuyu', nickname: 'Chuyu', avatar: '' },
    publishedAt: new Date(Date.now() - 86400000 * 7).toISOString(),
    views: 1567,
    commentsCount: 35
  }
]

const mockLatest = [
  {
    id: 4,
    slug: 'latest-1',
    title: { zh: '构建高性能 Nuxt 应用的 10 个技巧', en: '10 Tips to Build High-Performance Nuxt Apps' },
    excerpt: {
      zh: '从服务端渲染优化到客户端 hydration，深度剖析性能优化的每一个关键点。',
      en: 'From SSR tuning to client hydration — dissect every performance knob.'
    },
    coverImage: 'https://images.unsplash.com/photo-1460925895917-afdab827c52f?w=800&q=80',
    category: { id: 1, name: { zh: '前端开发', en: 'Frontend' }, slug: 'frontend' },
    author: { id: 1, name: 'Chuyu', nickname: 'Chuyu', avatar: '' },
    publishedAt: new Date(Date.now() - 86400000 * 1).toISOString(),
    views: 892,
    commentsCount: 15
  },
  {
    id: 5,
    slug: 'latest-2',
    title: { zh: 'Tailwind CSS 自定义主题系统实战', en: 'Building a Custom Tailwind Theme System' },
    excerpt: {
      zh: '从零构建一套可扩展、可维护的设计系统，让你的项目风格统一而灵活。',
      en: 'Build a scalable, maintainable design system for consistent and flexible project styling.'
    },
    coverImage: 'https://images.unsplash.com/photo-1498050108023-c5249f4df085?w=800&q=80',
    category: { id: 2, name: { zh: 'CSS', en: 'CSS' }, slug: 'css' },
    author: { id: 4, name: 'Chuyu', nickname: 'Chuyu', avatar: '' },
    publishedAt: new Date(Date.now() - 86400000 * 3).toISOString(),
    views: 756,
    commentsCount: 12
  },
  {
    id: 6,
    slug: 'latest-3',
    title: { zh: '状态管理新纪元：Pinia 实战模式', en: 'A New Era of State Management: Pinia Patterns' },
    excerpt: {
      zh: '深入 Pinia 的模块化状态管理，理解最佳实践与迁移策略。',
      en: 'Deep dive into Pinia modular state — best practices and migration strategies.'
    },
    coverImage: 'https://images.unsplash.com/photo-1517694712202-14dd9538aa97?w=800&q=80',
    category: { id: 4, name: { zh: '架构', en: 'Architecture' }, slug: 'architecture' },
    author: { id: 2, name: 'Chuyu', nickname: 'Chuyu', avatar: '' },
    publishedAt: new Date(Date.now() - 86400000 * 4).toISOString(),
    views: 634,
    commentsCount: 19
  }
]

const mockCategories = [
  { id: 1, name: { zh: '前端开发', en: 'Frontend' }, slug: 'frontend' },
  { id: 2, name: { zh: '后端开发', en: 'Backend' }, slug: 'backend' },
  { id: 3, name: { zh: 'CSS', en: 'CSS' }, slug: 'css' },
  { id: 4, name: { zh: 'TypeScript', en: 'TypeScript' }, slug: 'typescript' },
  { id: 5, name: { zh: '架构', en: 'Architecture' }, slug: 'architecture' },
  { id: 6, name: { zh: '运维', en: 'DevOps' }, slug: 'devops' },
  { id: 7, name: { zh: '数据库', en: 'Database' }, slug: 'database' },
  { id: 8, name: { zh: '人工智能', en: 'AI / ML' }, slug: 'ai' }
]

const mockTags = [
  { id: 1, name: 'Vue3', slug: 'vue3' },
  { id: 2, name: 'React', slug: 'react' },
  { id: 3, name: 'Node.js', slug: 'nodejs' },
  { id: 4, name: 'Nuxt', slug: 'nuxt' },
  { id: 5, name: 'Next.js', slug: 'nextjs' },
  { id: 6, name: 'Tailwind', slug: 'tailwind' },
  { id: 7, name: 'Docker', slug: 'docker' },
  { id: 8, name: 'GraphQL', slug: 'graphql' },
  { id: 9, name: 'REST', slug: 'rest' },
  { id: 10, name: 'Jest', slug: 'jest' },
  { id: 11, name: 'Vitest', slug: 'vitest' },
  { id: 12, name: 'Webpack', slug: 'webpack' },
  { id: 13, name: 'Vite', slug: 'vite' },
  { id: 14, name: 'Linux', slug: 'linux' },
  { id: 15, name: 'Git', slug: 'git' }
]

// ===== Data Fetching (SSR-friendly, no onMounted) =====
const { data, pending, error, refresh } = await useAPI<PaginatedResponse<Post>>('/blog/posts', {
  query: { lang: locale.value, page: 1, page_size: 7 },
  // 独立 key，避免和 /posts 列表页共用 URL 时 cache key 冲突，导致 SSR payload 数据丢失
  key: 'home:posts:preview:' + locale.value
})

// 兜底：和 posts 列表页一样，首次挂载 + keep-alive 激活都 refresh 一次，
// 防止 Nitro SSR 阶段 useFetch 因为某种原因卡住或没注入 payload 数据造成首页空，
// 以及"从文章详情点首页导航 → 首页空白"的复现 bug（因为首页组件被 keep-alive 缓存时走 onActivated 不走 onMounted）。
const fallbackRefresh = () => {
  setTimeout(() => {
    refresh()
  }, 50)
}
onMounted(fallbackRefresh)
onActivated(fallbackRefresh)

const fallbackPosts = computed<Post[]>(() => [...mockFeatured, ...mockLatest] as unknown as Post[])
const hasApiData = computed(() => !error.value && data.value && Array.isArray(data.value.items) && data.value.items.length > 0)

const posts = computed<Post[]>(() => hasApiData.value ? data.value!.items : fallbackPosts.value)
const loading = computed(() => pending.value && !hasApiData.value)

const featuredPosts = computed(() => posts.value.slice(0, 3))
const latestPosts = computed(() => posts.value.slice(3, 7))

const totalPostsDisplay = computed(() => {
  const n = posts.value.length || mockFeatured.length + mockLatest.length
  return n < 100 ? String(n) : '128'
})
const totalCategoriesDisplay = computed(() => mockCategories.length)
const totalTagsDisplay = computed(() => mockTags.length)
const totalViewsDisplay = computed(() => {
  const fromPosts = posts.value.reduce((acc, p: { views?: number, views_count?: number }) => acc + ((p.views ?? p.views_count) || 0), 0)
  if (fromPosts > 0) return fromPosts >= 1000 ? `${(fromPosts / 1000).toFixed(1)}k` : String(fromPosts)
  return '2.4k'
})

// ===== SEO =====
const requestURL = useRequestURL()
const canonical = computed(() => requestURL.href)
const origin = computed(() => requestURL.origin)

const tagline = computed(() => t('home.tagline'))
const siteTitle = computed(() => tagline.value ? `Rosetta · ${tagline.value}` : 'Rosetta · 穿越语言的边界')
const siteDescription = computed(() => {
  const hero = t('home.heroSubtitle')
  if (hero && !hero.startsWith('home.')) return hero
  const footer = t('footer.description')
  if (footer && !footer.startsWith('footer.')) return footer
  return '穿越语言的边界 · 现代个人博客系统'
})
const ogImage = computed(() => {
  const firstPost = hasApiData.value ? data.value!.items[0] : null
  const coverFromData = firstPost
    ? (firstPost.cover_image || (firstPost.cover_image === undefined ? (firstPost as unknown as { coverImage?: string }).coverImage : undefined))
    : null
  const raw = coverFromData || mockFeatured[0]!.coverImage
  // og:image 必须是绝对 URL（http:// 或 https:// 开头），否则搜索引擎爬不到封面
  if (raw && raw.startsWith('http')) return raw
  try {
    return new URL(raw || '/favicon-32x32.png', origin.value).href
  } catch {
    return raw || ''
  }
})

useSeoMeta({
  title: siteTitle,
  description: siteDescription,
  ogTitle: siteTitle,
  ogDescription: siteDescription,
  ogImage: ogImage,
  ogType: 'website',
  ogUrl: canonical,
  twitterCard: 'summary_large_image',
  twitterTitle: siteTitle,
  twitterDescription: siteDescription,
  twitterImage: ogImage
})

useHead({
  link: [
    { rel: 'canonical', href: canonical }
  ],
  script: [
    {
      type: 'application/ld+json',
      // 关键：JSON.stringify 里每个字段必须取 .value（纯字符串/数值），
      // 否则传入 computed/ref 会被展开内部响应式结构，触发 "circular ComputedRefImpl" 序列化崩溃
      innerHTML: JSON.stringify({
        '@context': 'https://schema.org',
        '@type': 'WebSite',
        'name': 'Rosetta',
        'url': origin.value
      })
    }
  ]
})
</script>
