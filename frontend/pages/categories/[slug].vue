<!--
  分类详情页：GET /blog/categories/slug/<slug>（元信息）+ GET /blog/posts?category=<slug>（列表）。
  详情请求的 URL 与 query 都是 setup 期一次性取值（只有 key 是 computed），换 slug 不会自动重取；
  列表 refresh 一律带 import.meta.client 守卫 —— SSR 阶段 useFetch 已取过数，服务端再 refresh
  等于重复请求。分类名取不到时兜底显示 slug，是刻意保留的可辨识占位而不是数据缺失。
-->
<template>
  <div class="container py-16">
    <header class="mb-12">
      <div class="inline-flex items-center gap-2 text-xs uppercase tracking-[0.16em] text-muted-foreground mb-3">
        <span class="size-1.5 rounded-full bg-warning" />
        <NuxtLink
          :to="localeHref('/categories')"
          class="hover:text-foreground transition-colors"
        >{{ t('categories.title', '分类') }}</NuxtLink>
        <span>/</span>
      </div>
      <div class="flex flex-wrap items-end justify-between gap-4">
        <div class="flex items-center gap-3">
          <div
            v-if="catRaw?.icon"
            class="size-10 rounded-xl flex items-center justify-center shrink-0"
            :style="{ background: catRaw?.color ? `color-mix(in oklab, ${catRaw.color} 15%, transparent)` : undefined }"
            :class="!catRaw?.color ? 'bg-primary/10' : ''"
          >
            <DynamicIcon
              :icon="catRaw.icon"
              class="size-5"
              :class="catRaw?.color ? 'text-foreground' : 'text-primary'"
            />
          </div>
          <div>
            <h1 class="font-display text-3xl md:text-4xl font-bold tracking-tight">
              {{ categoryName }}
            </h1>
            <p
              v-if="categoryDesc"
              class="text-muted-foreground mt-3 leading-relaxed max-w-2xl"
            >
              {{ categoryDesc }}
            </p>
          </div>
        </div>
        <div class="inline-flex items-center gap-2 text-sm text-muted-foreground">
          <span class="inline-flex items-center justify-center px-3 py-1 rounded-full bg-muted">
            {{ postCount }} {{ t('categories.posts', '篇文章') }}
          </span>
        </div>
      </div>
    </header>

    <template v-if="pending && posts.length === 0">
      <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        <PostSkeleton
          v-for="i in 6"
          :key="i"
        />
      </div>
    </template>
    <template v-else-if="loadError">
      <div class="rounded-xl border border-destructive/30 bg-destructive/5 p-6 text-sm text-destructive">
        {{ t('admin.posts.loadFailed', '加载失败，请稍后重试。') }}
      </div>
    </template>
    <template v-else-if="posts.length > 0">
      <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        <PostCard
          v-for="p in posts"
          :key="p.id"
          :post="p"
        />
      </div>
    </template>
    <template v-else>
      <div class="text-center py-20">
        <div class="inline-flex items-center justify-center size-16 rounded-2xl bg-muted mb-4">
          <FolderOpen class="size-8 text-muted-foreground" />
        </div>
        <h3 class="font-display text-xl font-semibold">
          {{ t('posts.noPosts', '这里还没有文章') }}
        </h3>
        <p class="text-muted-foreground mt-1">
          {{ t('posts.noPostsDesc', '作者正在努力创作，敬请期待。') }}
        </p>
      </div>
    </template>

    <div
      v-if="totalPages > 1"
      class="flex justify-center mt-12"
    >
      <nav
        class="flex items-center gap-2"
        role="navigation"
        aria-label="pagination"
      >
        <Button
          variant="outline"
          size="icon"
          :disabled="currentPage <= 1"
          :aria-label="t('common.prevPage', '上一页')"
          @click="currentPage -= 1"
        >
          <ChevronLeft data-icon="inline-start" />
        </Button>
        <Button
          v-for="p in visiblePages"
          :key="p"
          :variant="p === currentPage ? 'default' : 'ghost'"
          size="icon"
          class="size-9 min-w-[2.25rem]"
          @click="currentPage = p"
        >
          {{ p }}
        </Button>
        <Button
          variant="outline"
          size="icon"
          :disabled="currentPage >= totalPages"
          :aria-label="t('common.nextPage', '下一页')"
          @click="currentPage += 1"
        >
          <ChevronRight data-icon="inline-start" />
        </Button>
      </nav>
    </div>
  </div>
</template>

<script setup lang="ts">
import { useAPI } from '~~/composables/useApi'
import { isContentMissing, useContentStatus } from '~~/composables/useContentStatus'
import PostCard from '~~/components/PostCard.vue'
import PostSkeleton from '~~/components/PostSkeleton.vue'
import { Button } from '~~/components/ui/button'
import { pageWindow } from '~~/lib/pagination'
import { ChevronLeft, ChevronRight, FolderOpen } from '@lucide/vue'
import { useI18n } from 'vue-i18n'

definePageMeta({ layout: 'default' })

const { t, locale } = useI18n()
const route = useRoute()
const { localeHref } = useLocaleLink()

const slug = computed(() => typeof route.params.slug === 'string' ? route.params.slug : '')
const currentPage = ref(1)
const site = useSite()
// 每页条数取后台「阅读体验」分组；未配置时沿用 9
const pageSize = computed(() => site.reading.value.posts_per_page)

const pickLocalized = (val: unknown): string => pickLocalizedText(val, locale.value)

// 分类元信息：真实接口 slug 详情。失败不渲染示例内容。
interface CategoryDetail {
  id?: number | string
  slug?: string
  name?: unknown
  description?: unknown
  icon?: string
  color?: string
  post_count?: number
  postsCount?: number
  posts?: unknown[]
}

interface CategoryPostRow {
  id: number | string
  slug: string
  title: string | Record<string, string>
  excerpt?: string | Record<string, string>
  cover_image?: string
  coverImage?: string
  category?: { id: number | string, name: string | Record<string, string>, slug: string, color?: string | null }
  tags?: Array<{ id: number | string, name: string | Record<string, string>, slug: string, color?: string | null }>
  author?: { id: number | string, name?: string, nickname?: string, username?: string, avatar?: string }
  created_at?: string
  published_at?: string
  publishedAt?: string
  updated_at?: string
  views?: number
  views_count?: number
  comments_count?: number
  commentsCount?: number
  likes_count?: number
  likesCount?: number
  is_pinned?: boolean
  [key: string]: unknown
}
// 静态键+静态查询：切语言/换分类 slug 都走「跳同页 URL → 重挂载 → 新参数重新请求」，
// 不手写 watch+refresh()（与 Nuxt key watcher 双发，第一发必被 abort）。
const { data: catRaw, error: catError } = useAPI<CategoryDetail>(`/blog/categories/slug/${slug.value}`, {
  query: { lang: locale.value },
  key: `category:detail:${slug.value}:${locale.value}`,
  default: () => ({} as CategoryDetail)
})

// 分类文章：复用 /blog/posts?category=slug。失败回空数组，绝不造示例列表。
// query/key 都是 computed：翻页是页内状态（不同步 URL path，不重挂载），靠 Nuxt
// params/key watcher 自动重取；不再叠加手写 watch(refresh)（同一 URL 双发）。
const { data: postsRaw, pending, error: postsErr } = useAPI<{ items?: CategoryPostRow[], total?: number }>('/blog/posts', {
  query: computed(() => ({
    lang: locale.value,
    page: currentPage.value,
    page_size: pageSize.value,
    category: slug.value || undefined
  })),
  key: computed(() => `category:posts:${slug.value}:${locale.value}:${currentPage.value}`)
})

// 加载中留空（只显站点名）；确实取不到分类时用 404 口径标题，
// 不再把 slug 人性化成假装存在的分类名（响应侧由 useContentStatus 回写 404）。
const categoryName = computed(() => pickLocalized(catRaw.value?.name) || (pending.value ? '' : t('error.notFoundTitle')))
const categoryDesc = computed(() => pickLocalized(catRaw.value?.description))
const postCount = computed<number>(() => {
  const c = catRaw.value as CategoryDetail | null | undefined
  if (c && typeof c.post_count === 'number') return c.post_count
  if (c && typeof c.postsCount === 'number') return c.postsCount
  if (c && Array.isArray(c.posts)) return c.posts.length
  return postsRaw.value?.total ?? 0
})
const posts = computed<CategoryPostRow[]>(() => Array.isArray(postsRaw.value?.items) ? postsRaw.value!.items! : [])
const total = computed(() => postsRaw.value?.total ?? 0)
const loadError = computed(() => !!(catError.value || postsErr.value))
// 分类不存在时让 SSR 响应带 404（兜底 UI 不变）；判定口径见 composables/useContentStatus.ts。
const catMissing = computed(() => !pickLocalized(catRaw.value?.name))
// 404 与 robots/canonical 必须同源判定：状态码回了 404 却写着 `index, follow` +
// 自指 canonical，等于给搜索引擎两份互相矛盾的答复。
const catNotFound = computed(() => isContentMissing(catError.value, catMissing.value))
useContentStatus(catError, catMissing)

const totalPages = computed(() => Math.max(1, Math.ceil(total.value / pageSize.value)))
const visiblePages = computed(() => pageWindow(currentPage.value, totalPages.value))

useHead(() => ({
  title: categoryName.value ? `${categoryName.value} · ${t('categories.title', '分类')}` : t('categories.title', '分类'),
  meta: categoryDesc.value ? [{ name: 'description', content: categoryDesc.value }] : []
}))

useSeo({
  title: computed(() => categoryName.value ? `${categoryName.value} · ${t('categories.title', '分类')}` : t('categories.title', '分类')),
  description: computed(() => categoryDesc.value),
  noindex: catNotFound,
  type: 'website'
})
useWebsiteJsonLd()
useBreadcrumbJsonLd([
  { name: t('nav.home', '首页') as string, url: '/' },
  { name: t('nav.categories', '分类') as string, url: '/categories' },
  { name: categoryName.value || slug.value, url: `/categories/${slug.value}` }
])
</script>
