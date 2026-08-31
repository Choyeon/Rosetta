<template>
  <div class="container py-16">
    <header class="mb-10">
      <h1 class="font-display text-3xl md:text-4xl font-bold tracking-tight">
        {{ t('search.title') }}
      </h1>
      <p class="text-muted-foreground mt-2">
        {{ t('search.desc') }}
      </p>

      <Card class="mt-8">
        <CardContent class="p-4">
          <div class="flex flex-col md:flex-row gap-3">
            <div class="flex-1 relative">
              <Search class="absolute left-3 top-1/2 -translate-y-1/2 size-4 text-muted-foreground" />
              <Input
                v-model="keyword"
                :placeholder="t('search.placeholder')"
                class="pl-9 h-10"
                @keyup.enter="runSearch"
              />
            </div>
            <Button
              variant="default"
              @click="runSearch"
            >
              <Search class="size-4 mr-2" />
              {{ t('search.submit') }}
            </Button>
          </div>
        </CardContent>
      </Card>
    </header>

    <template v-if="!route.query.q">
      <div class="text-center py-20">
        <div class="inline-flex items-center justify-center size-16 rounded-2xl bg-muted mb-4">
          <Search class="size-8 text-muted-foreground" />
        </div>
        <h3 class="font-display text-xl font-semibold">
          {{ t('search.startPrompt') }}
        </h3>
        <p class="text-muted-foreground mt-1">
          {{ t('search.startDesc') }}
        </p>
      </div>
    </template>

    <template v-else-if="pending && posts.length === 0">
      <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        <PostSkeleton
          v-for="i in 6"
          :key="i"
        />
      </div>
    </template>

    <template v-else-if="posts.length > 0">
      <p class="text-muted-foreground mb-6">
        {{ t('search.resultCount', { count: total, keyword: String(route.query.q) }) }}
      </p>
      <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        <PostCard
          v-for="post in posts"
          :key="post.id"
          :post="post"
        />
      </div>

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
            aria-label="Go to previous page"
            @click="handlePageChange(currentPage - 1)"
          >
            <ChevronLeft class="h-4 w-4" />
          </Button>
          <Button
            v-for="page in visiblePages"
            :key="page"
            :variant="page === currentPage ? 'default' : 'ghost'"
            size="icon"
            class="size-9 min-w-[2.25rem]"
            @click="handlePageChange(page)"
          >
            {{ page }}
          </Button>
          <Button
            variant="outline"
            size="icon"
            :disabled="currentPage >= totalPages"
            aria-label="Go to next page"
            @click="handlePageChange(currentPage + 1)"
          >
            <ChevronRight class="h-4 w-4" />
          </Button>
        </nav>
      </div>
    </template>

    <template v-else>
      <div class="text-center py-20">
        <div class="inline-flex items-center justify-center size-16 rounded-2xl bg-muted mb-4">
          <SearchX class="size-8 text-muted-foreground" />
        </div>
        <h3 class="font-display text-xl font-semibold">
          {{ t('search.noResults') }}
        </h3>
        <p class="text-muted-foreground mt-1">
          {{ t('search.noResultsDesc', { keyword: String(route.query.q) }) }}
        </p>
      </div>
    </template>
  </div>
</template>

<script setup lang="ts">
import { Card, CardContent } from '~~/components/ui/card'
import { Button } from '~~/components/ui/button'
import { Input } from '~~/components/ui/input'
import PostCard from '~~/components/PostCard.vue'
import PostSkeleton from '~~/components/PostSkeleton.vue'
import type { Post, PaginatedResponse } from '~~/types/api'
import { useAPI } from '~~/composables/useApi'
import { useI18n } from 'vue-i18n'
import { Search, SearchX, ChevronLeft, ChevronRight } from '@lucide/vue'
import { ref, computed, watch } from 'vue'

definePageMeta({ layout: 'default' })

const { t, locale } = useI18n()
const route = useRoute()
const router = useRouter()

const keyword = ref<string>((route.query.q as string) || '')
const currentPage = ref(1)
const pageSize = 9

// 以路由 query.q 作为检索词的唯一真值来源：SSR 可渲染、结果可分享。
const { data, pending, refresh } = await useAPI<PaginatedResponse<Post>>('/blog/posts', {
  query: computed(() => ({
    lang: locale.value,
    page: currentPage.value,
    page_size: pageSize,
    search: (route.query.q as string) || undefined
  })),
  key: computed(() => `search:${route.query.q || ''}:${currentPage.value}`)
})

const posts = computed<Post[]>(() => data.value?.items || [])
const total = computed(() => data.value?.total || 0)
const totalPages = computed(() => Math.ceil(total.value / pageSize) || 1)

const visiblePages = computed(() => {
  const pages: number[] = []
  const max = 5
  let start = Math.max(1, currentPage.value - Math.floor(max / 2))
  const end = Math.min(totalPages.value, start + max - 1)
  if (end - start + 1 < max) {
    start = Math.max(1, end - max + 1)
  }
  for (let i = start; i <= end; i++) pages.push(i)
  return pages
})

const runSearch = () => {
  const q = keyword.value.trim()
  currentPage.value = 1
  // 通过路由跳转触发新的 SSR 友好检索（可被收藏/分享）
  router.push({ path: '/search', query: q ? { q } : {} })
}

const handlePageChange = (page: number) => {
  if (page < 1 || page > totalPages.value) return
  currentPage.value = page
  if (import.meta.client) {
    window.scrollTo({ top: 0, behavior: 'smooth' })
    refresh()
  }
}

// 路由 q 变化时（含浏览器前进/后退）同步输入框
watch(
  () => route.query.q,
  (q) => {
    keyword.value = (q as string) || ''
    currentPage.value = 1
  }
)

useSeo({
  title: computed(() => {
    const q = (route.query.q as string) || ''
    return q
      ? (t('search.resultCount', { count: total.value, keyword: q }) as string)
      : (t('search.title') as string || '搜索')
  }),
  description: computed(() => t('search.desc') as string),
  type: 'website'
})
useWebsiteJsonLd()
useBreadcrumbJsonLd([
  { name: t('nav.home', '首页') as string, url: '/' },
  { name: t('nav.search', '搜索') as string, url: '/search' }
])
</script>
