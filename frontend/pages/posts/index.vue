<!--
  文章列表页：GET /blog/posts（分页 / 分类 / 关键词 / 排序）+ /search-placeholders 占位词轮播。
  硬契约（都是踩过的坑，改前先读）：
  1. canonical 在 setup 同步阶段用 useRequestURL().origin 拼好：await 之后再调 useHead 会被
     Nuxt 忽略（NUXT_E1001），SEO 静默失效。
  2. 列表 useFetch 的 key 固定为 'posts:list'（不用动态 key）。Nuxt 在 SSR 下对 computed query
     生成的 key 不一定能写进 payload，客户端 hydration 会拿到 undefined 且不会自动重试。
     重新请求由那个 import.meta.client 守卫的 watch 集中触发 —— SSR 首屏由 useFetch 自动完成。
  3. canonical 的查询串必须与 URL 同步函数产出完全一致：页面从不把状态写进地址栏却声明
     /posts?page=N 的话，等于把规范地址指向一个不存在的 URL。
-->
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
              <Search class="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 size-4 text-muted-foreground" />
              <Input
                v-model="searchInput"
                :placeholder="searchPlaceholder"
                :aria-label="t('common.search') || '搜索'"
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
            <div class="md:w-44">
              <Select
                v-model="sortBy"
                @update:model-value="handleFilter"
              >
                <SelectTrigger
                  class="h-10"
                  :aria-label="t('posts.sortLabel')"
                >
                  <List class="mr-2 size-4 shrink-0 text-muted-foreground" />
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="latest">
                    {{ t('posts.sortLatest') }}
                  </SelectItem>
                  <SelectItem value="popular">
                    {{ t('posts.sortPopular') }}
                  </SelectItem>
                </SelectContent>
              </Select>
            </div>
            <Button
              variant="default"
              class="shrink-0"
              @click="handleSearch"
            >
              <Filter
                data-icon="inline-start"
                class="mr-2"
              />
              {{ t('posts.filter') }}
            </Button>
          </div>
        </CardContent>
      </Card>
    </header>

    <template v-if="loading && posts.length === 0">
      <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        <PostSkeleton
          v-for="i in 6"
          :key="i"
        />
      </div>
    </template>
    <template v-else-if="loadError">
      <div class="rounded-xl border border-destructive/30 bg-destructive/5 p-6 text-sm text-destructive">
        <div class="flex flex-col items-center gap-3 text-center">
          <span>{{ t('admin.posts.loadFailed') }}</span>
          <Button
            variant="outline"
            size="sm"
            @click="retry"
          >
            <RefreshCw data-icon="inline-start" />
            {{ t('common.retry', '重试') }}
          </Button>
        </div>
      </div>
    </template>
    <template v-else-if="posts.length > 0">
      <!-- 翻页/换筛选时旧数据仍在（useFetch 的 data 不清空），只加 dim + aria-busy，
           不切骨架屏：整块闪成骨架再回来，比"停一下再换"更难读 -->
      <div
        :class="busy ? 'opacity-60 transition-opacity' : 'transition-opacity'"
        :aria-busy="busy"
      >
        <TransitionGroup
          tag="div"
          class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6"
          name="list-item"
        >
          <PostCard
            v-for="post in posts"
            :key="post.id"
            v-memo="[post.id, post.updated_at, post.published_at]"
            :post="post"
          />
        </TransitionGroup>
      </div>
    </template>
    <template v-else>
      <div class="text-center py-20">
        <div class="inline-flex items-center justify-center size-16 rounded-2xl bg-muted mb-4">
          <Search class="size-8 text-muted-foreground" />
        </div>
        <h3 class="font-display text-xl font-semibold">
          {{ hasActiveFilter ? t('posts.noMatch') : t('posts.noPosts') }}
        </h3>
        <p class="text-muted-foreground mt-1">
          {{ hasActiveFilter ? t('posts.noMatchDesc') : t('posts.noPostsDesc') }}
        </p>
        <Button
          v-if="hasActiveFilter"
          variant="outline"
          size="sm"
          class="mt-4"
          @click="clearFilters"
        >
          <X
            data-icon="inline-start"
            class="size-4"
          />
          {{ t('posts.clearFilters') }}
        </Button>
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
          :disabled="currentPage <= 1 || busy"
          :aria-label="t('common.prevPage', '上一页')"
          @click="handlePageChange(currentPage - 1)"
        >
          <ChevronLeft data-icon="inline-start" />
        </Button>
        <Button
          v-for="page in visiblePages"
          :key="page"
          :variant="page === currentPage ? 'default' : 'ghost'"
          size="icon"
          class="size-9 min-w-[2.25rem]"
          :disabled="busy"
          @click="handlePageChange(page)"
        >
          {{ page }}
        </Button>
        <Button
          variant="outline"
          size="icon"
          :disabled="currentPage >= totalPages || busy"
          :aria-label="t('common.nextPage', '下一页')"
          @click="handlePageChange(currentPage + 1)"
        >
          <ChevronRight data-icon="inline-start" />
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
import PostCard from '~~/components/PostCard.vue'
import PostSkeleton from '~~/components/PostSkeleton.vue'
import type { Category, Post, PaginatedResponse } from '~~/types/api'
import { useAPI } from '~~/composables/useApi'
import { useI18n } from 'vue-i18n'
import { Search, Filter, ChevronLeft, ChevronRight, List, X, RefreshCw } from '~~/lib/lucide-svg-icons'
import { watch, computed, onMounted, onBeforeUnmount, getCurrentInstance } from 'vue'

definePageMeta({ layout: 'default' })

const { t, locale } = useI18n()
const site = useSite()
const route = useRoute()
const router = useRouter()

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

// ===== SEO（useSeo composable）=====
const listTitle = computed(() => t('nav.posts'))
const listDescription = computed(
  () =>
    site.siteDescription.value
    || t('posts.allPosts')
    || '浏览全部文章')
useSeo({
  title: listTitle,
  description: listDescription,
  type: 'website',
  url: '/posts'
})
useBreadcrumbJsonLd([
  { name: String(t('nav.home') || '首页'), url: '/' },
  { name: String(t('nav.posts') || listTitle.value || '文章'), url: '/posts' }
])

const ALL_CATEGORIES = '__all'
const pageSize = 9

// ===== 初始状态从 URL 读：分享链接 / 刷新 / 浏览器后退都要能还原 =====
// 只接受白名单取值，避免 ?sort=<垃圾> 之类被直接透传到接口。
const searchInput = ref((route.query.search as string) || '')
const searchQuery = ref((route.query.search as string) || '')
const selectedCategory = ref((route.query.category as string) || '')
const sortBy = ref<'latest' | 'popular'>(route.query.sort === 'popular' ? 'popular' : 'latest')
const currentPage = ref(Math.max(1, Number(route.query.page) || 1))

const hasActiveFilter = computed(
  () => searchQuery.value !== '' || (selectedCategory.value !== '' && selectedCategory.value !== ALL_CATEGORIES)
)

// ===== 同步阶段注册 SEO：canonical（await 之后注册触发 NUXT_E1001 → 失效）=====
const requestURL = useRequestURL()
const origin = computed(() => requestURL.origin)

// canonical 必须与 syncUrl 产出逐字一致：声明的规范地址和实际地址差一个字符，
// 搜索引擎就会当成两个 URL，分页页还会被判成重复内容。
const canonicalQuery = computed(() => {
  const q: Record<string, string> = {}
  if (currentPage.value > 1) q.page = String(currentPage.value)
  if (selectedCategory.value && selectedCategory.value !== ALL_CATEGORIES) {
    q.category = selectedCategory.value
  }
  if (searchQuery.value) q.search = searchQuery.value
  if (sortBy.value !== 'latest') q.sort = sortBy.value
  return q
})
const canonical = computed(() => {
  const qs = new URLSearchParams(canonicalQuery.value).toString()
  return `${origin.value}${route.path}${qs ? `?${qs}` : ''}`
})

useHead(() => ({
  link: [
    { rel: 'canonical', href: canonical.value }
  ]
}))

const { data: categories } = useAPI<Category[]>('/blog/categories', {
  query: { lang: locale.value },
  key: computed(() => `posts:categories:${locale.value}`),
  default: () => []
})

// ===== 搜索占位符：真实接口 /api/search-placeholders。空则回退 i18n key，绝不编造示例提示词 =====
const { data: placeholdersRaw } = useAPI<string[]>('/search-placeholders', {
  key: 'posts:search-placeholders',
  default: () => []
})
const searchPlaceholderIdx = ref(0)
const searchPlaceholderList = computed<string[]>(() => {
  const raw = placeholdersRaw.value
  return Array.isArray(raw) ? raw.filter(s => typeof s === 'string' && s.length > 0) : []
})
const searchPlaceholder = computed<string>(() => {
  if (searchPlaceholderList.value.length > 0) {
    return searchPlaceholderList.value[searchPlaceholderIdx.value % searchPlaceholderList.value.length] || ''
  }
  return t('posts.searchPlaceholder') as string
})
onMounted(() => {
  if (!import.meta.client) return
  const list = searchPlaceholderList.value
  if (list.length <= 1) return
  const t = setInterval(() => {
    searchPlaceholderIdx.value = (searchPlaceholderIdx.value + 1) % list.length
  }, 4200)
  const vm = getCurrentInstance()
  if (vm) onBeforeUnmount(() => clearInterval(t))
})

const { data, pending, error: loadError, refresh } = useAPI<PaginatedResponse<Post>>('/blog/posts', {
  query: computed(() => ({
    lang: locale.value,
    page: currentPage.value,
    page_size: pageSize,
    category: (selectedCategory.value && selectedCategory.value !== ALL_CATEGORIES) ? selectedCategory.value : undefined,
    search: searchQuery.value || undefined,
    // 后端对未知取值回退 latest，这里同样只发白名单值
    sort: sortBy.value === 'popular' ? 'popular' : undefined
  })),
  key: 'posts:list'
})

const posts = computed<Post[]>(() => data.value?.items || [])
const total = computed(() => data.value?.total || 0)
const totalPages = computed(() => Math.ceil(total.value / pageSize) || 1)
const loading = computed(() => pending.value && posts.value.length === 0)
// 翻页/换筛选时 data 仍是上一批：没有 busy 的话界面完全静止，用户会以为点击没生效
const busy = computed(() => pending.value)

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

// 分享链接上的页码可能已经越界（比如文章删了一大批）：拉回来再请求，
// 否则用户拿到的是一个"第 7 页，共 3 页"的空列表且无从自救。
watch([total, currentPage], () => {
  if (total.value === 0) return
  if (currentPage.value > totalPages.value) currentPage.value = totalPages.value
})

function syncUrl() {
  if (!import.meta.client) return
  const q = canonicalQuery.value
  router.replace({ query: Object.keys(q).length > 0 ? q : {} })
}

// 手动监听搜索/分类/排序/语言/分页变化并刷新（仅客户端触发）。
// 分类列表不跟着刷：分类不随这些条件变化，跟着刷只是每次多打一个请求。
watch([currentPage, searchQuery, selectedCategory, sortBy, locale], () => {
  if (import.meta.client) {
    refresh()
  }
})

const handleSearch = () => {
  searchQuery.value = searchInput.value.trim()
  currentPage.value = 1
  syncUrl()
}

const handleFilter = () => {
  currentPage.value = 1
  syncUrl()
}

const handlePageChange = (page: number) => {
  if (page < 1 || page > totalPages.value) return
  currentPage.value = page
  syncUrl()
  if (import.meta.client) {
    window.scrollTo({ top: 0, behavior: 'smooth' })
  }
}

const clearFilters = () => {
  searchInput.value = ''
  searchQuery.value = ''
  selectedCategory.value = ''
  currentPage.value = 1
  syncUrl()
}

const retry = () => {
  refresh()
}
</script>
