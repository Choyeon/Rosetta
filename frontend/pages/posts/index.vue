<template>
  <div class="container py-16">
    <header class="mb-10">
      <h1 class="font-display text-3xl md:text-4xl font-bold tracking-tight">
        {{ t('posts.allPosts') }}
      </h1>
      <p class="text-muted-foreground mt-2">
        {{ t('posts.allPostsDesc') }}
      </p>

      <Card class="mt-8">
        <CardContent class="p-4">
          <div class="flex flex-col md:flex-row gap-3">
            <div class="flex-1 relative">
              <Search class="absolute left-3 top-1/2 -translate-y-1/2 size-4 text-muted-foreground" />
              <Input
                v-model="searchInput"
                :placeholder="t('posts.searchPlaceholder')"
                class="pl-9 h-10"
                @keyup.enter="handleSearch"
              />
            </div>
            <div class="md:w-56">
              <Select
                v-model="selectedCategory"
                @update:model-value="handleFilter"
              >
                <SelectTrigger class="h-10">
                  <SelectValue :placeholder="t('posts.selectCategory')" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="__all">
                    {{ t('posts.allCategories') }}
                  </SelectItem>
                  <SelectItem
                    v-for="cat in categories"
                    :key="cat.id"
                    :value="cat.slug"
                  >
                    {{ pickLocalized(cat.name) }}
                  </SelectItem>
                </SelectContent>
              </Select>
            </div>
            <Button
              variant="default"
              @click="handleSearch"
            >
              <Filter class="size-4 mr-2" />
              {{ t('posts.filter') }}
            </Button>
          </div>
        </CardContent>
      </Card>
    </header>

    <template v-if="loading && posts.length === 0">
      <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        <Skeleton
          v-for="i in 6"
          :key="i"
          class="aspect-[4/5] rounded-2xl"
        />
      </div>
    </template>
    <template v-else-if="posts.length > 0">
      <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        <PostCard
          v-for="post in posts"
          :key="post.id"
          :post="post"
        />
      </div>
    </template>
    <template v-else>
      <div class="text-center py-20">
        <div class="inline-flex items-center justify-center size-16 rounded-2xl bg-muted mb-4">
          <Search class="size-8 text-muted-foreground" />
        </div>
        <h3 class="font-display text-xl font-semibold">
          {{ t('posts.noPosts') }}
        </h3>
        <p class="text-muted-foreground mt-1">
          {{ t('posts.noPostsDesc') }}
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
  </div>
</template>

<script setup lang="ts">
import { Card, CardContent } from '~~/components/ui/card'
import { Button } from '~~/components/ui/button'
import { Input } from '~~/components/ui/input'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '~~/components/ui/select'
import { Skeleton } from '~~/components/ui/skeleton'
import PostCard from '~~/components/PostCard.vue'
import type { Category, Post, PaginatedResponse } from '~~/types/api'
import { useAPI } from '~~/composables/useApi'
import { useI18n } from 'vue-i18n'
import { Search, Filter, ChevronLeft, ChevronRight } from '@lucide/vue'

definePageMeta({ layout: 'default' })

const { t, locale } = useI18n()

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

const searchInput = ref('')
const searchQuery = ref('')
const selectedCategory = ref('')
const currentPage = ref(1)
const pageSize = 9

const { data: categories } = await useAPI<Category[]>('/blog/categories', {
  query: { lang: locale.value },
  key: `posts:categories:${locale.value}`,
  default: () => []
})

// TEMP 临时用 plain object（非 computed）测试 SSR payload 是否正常注入
// 注意：Nuxt useFetch 在 SSR 下 query 如果传 computed/ref ，可能不被序列化为 payload.data key
//      导致客户端 hydration 拿到 undefined，不会自动重试。
const { data, pending, refresh } = await useAPI<PaginatedResponse<Post>>('/blog/posts', {
  // 不用 computed 直接传值，确保 SSR 端能生成正确的 cache key 并写入 payload
  query: computed(() => ({
    lang: locale.value,
    page: currentPage.value,
    page_size: pageSize,
    category: (selectedCategory.value && selectedCategory.value !== '__all') ? selectedCategory.value : undefined,
    search: searchQuery.value || undefined
  })),
  key: 'posts:list'
})

// 手动监听搜索/分类/语言/分页变化并刷新（仅客户端触发）。
watch([currentPage, searchQuery, selectedCategory, locale], () => {
  if (import.meta.client) {
    refresh()
  }
})

const posts = computed<Post[]>(() => data.value?.items || [])
const total = computed(() => data.value?.total || 0)
const loading = computed(() => pending.value && posts.value.length === 0)

const totalPages = computed(() => Math.ceil(total.value / pageSize) || 1)

const visiblePages = computed(() => {
  const pages: number[] = []
  const max = 5
  let start = Math.max(1, currentPage.value - Math.floor(max / 2))
  const end = Math.min(totalPages.value, start + max - 1)
  if (end - start + 1 < max) {
    start = Math.max(1, end - max + 1)
  }
  for (let i = start; i <= end; i++) {
    pages.push(i)
  }
  return pages
})

const handleSearch = () => {
  searchQuery.value = searchInput.value.trim()
  currentPage.value = 1
}

const handleFilter = () => {
  currentPage.value = 1
}

const handlePageChange = (page: number) => {
  if (page < 1 || page > totalPages.value) return
  currentPage.value = page
  if (import.meta.client) {
    window.scrollTo({ top: 0, behavior: 'smooth' })
  }
}

// ===== SEO =====
const requestURL = useRequestURL()
const origin = computed(() => requestURL.origin)
const canonical = computed(() => `${origin.value}/posts?page=${currentPage.value}`)

useSeoMeta({
  title: () => t('posts.allPosts'),
  description: () => t('posts.allPostsDesc'),
  ogType: 'website',
  ogUrl: canonical,
  twitterCard: 'summary'
})

useHead({
  link: [
    { rel: 'canonical', href: canonical }
  ]
})
</script>
