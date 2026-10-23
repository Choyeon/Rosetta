<!--
  标签详情页：GET /blog/tags/slug/<slug> + GET /blog/posts?tag=<slug>，任一失败即整体进错误态。
  与 categories/[slug] 同一形态：详情 URL 与 lang 都是 setup 期快照，翻页只在客户端 refresh。
  分页只认列表响应的 total —— 详情里的 post_count 仅用于头部展示，不参与算页数，两者不一致时
  以 total 为准。
-->
<template>
  <div class="container py-16">
    <header class="mb-12">
      <div class="inline-flex items-center gap-2 text-xs uppercase tracking-[0.16em] text-muted-foreground mb-3">
        <span class="size-1.5 rounded-full bg-cyan-500" />
        <NuxtLink
          :to="localeHref('/tags')"
          class="hover:text-foreground transition-colors"
        >{{ t('tags.title', '标签') }}</NuxtLink>
        <span>/</span>
      </div>
      <div class="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 class="font-display text-3xl md:text-4xl font-bold tracking-tight inline-flex items-center gap-3">
            <TagBadge
              :color="tagColor"
              :label="tagName"
              size="md"
              show-icon
            />
            <span>{{ tagName }}</span>
          </h1>
          <p
            v-if="tagDesc"
            class="text-muted-foreground mt-3 leading-relaxed max-w-2xl"
          >
            {{ tagDesc }}
          </p>
        </div>
        <div class="inline-flex items-center gap-2 text-sm text-muted-foreground">
          <span class="inline-flex items-center justify-center px-3 py-1 rounded-full bg-muted tabular-nums">
            {{ postCount }} {{ t('tags.posts', '篇文章') }}
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
          <Tags class="size-8 text-muted-foreground" />
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
          :aria-label="t('common.prevPage')"
          :disabled="currentPage <= 1"
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
          :aria-label="t('common.nextPage')"
          :disabled="currentPage >= totalPages"
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
import TagBadge from '~~/components/TagBadge.vue'
import PostSkeleton from '~~/components/PostSkeleton.vue'
import { Button } from '~~/components/ui/button'
import { pageWindow } from '~~/lib/pagination'
import { ChevronLeft, ChevronRight, Tags } from '@lucide/vue'
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

interface TagDetail { id?: number | string, slug?: string, name?: unknown, description?: unknown, color?: string | null, post_count?: number, postsCount?: number, posts?: unknown[] }

interface TagPostRow {
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
// 静态键+静态查询：切语言/换标签 slug 都走「跳同页 URL → 重挂载 → 新参数重新请求」，
// 不手写 watch+refresh()（与 Nuxt key watcher 双发，第一发必被 abort）。
const { data: tagRaw, error: tagErr } = useAPI<TagDetail>(`/blog/tags/slug/${slug.value}`, {
  query: { lang: locale.value },
  key: `tag:detail:${slug.value}:${locale.value}`,
  default: () => ({} as TagDetail)
})

// query/key 都是 computed：翻页是页内状态（不重挂载），靠 Nuxt params/key watcher
// 自动重取；不再叠加手写 watch(refresh)（同一 URL 双发，第一发还被 abort）。
const { data: postsRaw, pending, error: postsErr } = useAPI<{ items?: TagPostRow[], total?: number }>('/blog/posts', {
  query: computed(() => ({
    lang: locale.value,
    page: currentPage.value,
    page_size: pageSize.value,
    tag: slug.value || undefined
  })),
  key: computed(() => `tag:posts:${slug.value}:${locale.value}:${currentPage.value}`)
})

// 同 categories：加载中留空，取不到标签时用 404 口径标题而不是人性化 slug。
const tagName = computed(() => pickLocalized(tagRaw.value?.name) || (pending.value ? '' : t('error.notFoundTitle')))
const tagColor = computed<string | null>(() => (tagRaw.value?.color ?? null) as string | null)
const tagDesc = computed(() => pickLocalized(tagRaw.value?.description))
const postCount = computed<number>(() => {
  const c = tagRaw.value as TagDetail | null | undefined
  if (c && typeof c.post_count === 'number') return c.post_count
  if (c && typeof c.postsCount === 'number') return c.postsCount
  if (c && Array.isArray(c.posts)) return c.posts.length
  return postsRaw.value?.total ?? 0
})
const posts = computed<TagPostRow[]>(() => Array.isArray(postsRaw.value?.items) ? postsRaw.value!.items! : [])
const total = computed(() => postsRaw.value?.total ?? 0)
const loadError = computed(() => !!(tagErr.value || postsErr.value))
// 标签不存在时让 SSR 响应带 404（兜底 UI 不变）；判定口径见 composables/useContentStatus.ts。
const tagMissing = computed(() => !pickLocalized(tagRaw.value?.name))
// 404 / robots / canonical 同源判定，理由同分类页。
const tagNotFound = computed(() => isContentMissing(tagErr.value, tagMissing.value))
useContentStatus(tagErr, tagMissing)

const totalPages = computed(() => Math.max(1, Math.ceil(total.value / pageSize.value)))
const visiblePages = computed(() => pageWindow(currentPage.value, totalPages.value))

useHead(() => ({
  title: tagName.value ? `${tagName.value} · ${t('tags.title', '标签')}` : t('tags.title', '标签'),
  meta: tagDesc.value ? [{ name: 'description', content: tagDesc.value }] : []
}))

useSeo({
  title: computed(() => tagName.value ? `${tagName.value} · ${t('tags.title', '标签')}` : t('tags.title', '标签')),
  description: computed(() => tagDesc.value),
  noindex: tagNotFound,
  type: 'website'
})
useWebsiteJsonLd()
useBreadcrumbJsonLd([
  { name: t('nav.home', '首页') as string, url: '/' },
  { name: t('nav.tags', '标签') as string, url: '/tags' },
  { name: tagName.value || slug.value, url: `/tags/${slug.value}` }
])
</script>
