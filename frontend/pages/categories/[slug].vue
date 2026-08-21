<template>
  <div class="container py-16">
    <header class="mb-12">
      <div class="inline-flex items-center gap-2 text-xs uppercase tracking-[0.16em] text-muted-foreground mb-3">
        <span class="size-1.5 rounded-full bg-warning" />
        <NuxtLink
          to="/categories"
          class="hover:text-foreground transition-colors"
        >{{ t('categories.title', '分类') }}</NuxtLink>
        <span>/</span>
      </div>
      <div class="flex flex-wrap items-end justify-between gap-4">
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
        <div class="inline-flex items-center gap-2 text-sm text-muted-foreground">
          <span class="inline-flex items-center justify-center px-3 py-1 rounded-full bg-muted">
            {{ postCount }} {{ t('categories.posts', '篇文章') }}
          </span>
        </div>
      </div>
    </header>

    <template v-if="pending && posts.length === 0">
      <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        <Skeleton
          v-for="i in 6"
          :key="i"
          class="aspect-[4/5] rounded-2xl"
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
          aria-label="prev"
          @click="currentPage -= 1"
        >
          <ChevronLeft class="h-4 w-4" />
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
          aria-label="next"
          @click="currentPage += 1"
        >
          <ChevronRight class="h-4 w-4" />
        </Button>
      </nav>
    </div>
  </div>
</template>

<script setup lang="ts">
import { useAPI } from '~~/composables/useApi'
import PostCard from '~~/components/PostCard.vue'
import { Skeleton } from '~~/components/ui/skeleton'
import { Button } from '~~/components/ui/button'
import { ChevronLeft, ChevronRight, FolderOpen } from '@lucide/vue'
import { useI18n } from 'vue-i18n'

definePageMeta({ layout: 'default' })

const { t, locale } = useI18n()
const route = useRoute()

const slug = computed(() => typeof route.params.slug === 'string' ? route.params.slug : '')
const currentPage = ref(1)
const pageSize = 9

const pickLocalized = (val: unknown): string => {
  if (val == null) return ''
  if (typeof val === 'string') return val
  if (typeof val === 'object') {
    const obj = val as Record<string, string>
    const key = (locale.value || Object.keys(obj)[0] || '') as string
    return obj[key] ?? obj[Object.keys(obj)[0] || ''] ?? ''
  }
  return String(val)
}

// 分类元信息：真实接口 slug 详情。失败不渲染示例内容。
interface CategoryDetail {
  id?: number | string
  slug?: string
  name?: unknown
  description?: unknown
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
const { data: catRaw, error: catError } = await useAPI<CategoryDetail>(`/blog/categories/slug/${slug.value}`, {
  query: { lang: locale.value },
  key: computed(() => `category:detail:${slug.value}:${locale.value}`),
  default: () => ({} as CategoryDetail)
})

// 分类文章：复用 /blog/posts?category=slug。失败回空数组，绝不造示例列表。
const { data: postsRaw, pending, error: postsErr, refresh } = await useAPI<{ items?: CategoryPostRow[], total?: number }>('/blog/posts', {
  query: computed(() => ({
    lang: locale.value,
    page: currentPage.value,
    page_size: pageSize,
    category: slug.value || undefined
  })),
  key: computed(() => `category:posts:${slug.value}:${locale.value}:${currentPage.value}`)
})

watch([currentPage, slug, locale], () => {
  if (import.meta.client) refresh()
})

const categoryName = computed(() => pickLocalized(catRaw.value?.name) || slug.value || '')
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

const totalPages = computed(() => Math.max(1, Math.ceil(total.value / pageSize)))
const visiblePages = computed(() => {
  const pages: number[] = []
  const max = 5
  let start = Math.max(1, currentPage.value - Math.floor(max / 2))
  const end = Math.min(totalPages.value, start + max - 1)
  if (end - start + 1 < max) start = Math.max(1, end - max + 1)
  for (let i = start; i <= end; i++) pages.push(i)
  return pages
})

useHead(() => ({
  title: categoryName.value ? `${categoryName.value} · ${t('categories.title', '分类')}` : t('categories.title', '分类'),
  meta: categoryDesc.value ? [{ name: 'description', content: categoryDesc.value }] : []
}))
</script>
