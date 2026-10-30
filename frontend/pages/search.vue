<!--
  搜索页：以 route.query 为唯一真值（q / category / tag / sort / page 全部进 URL），
  结果可收藏/可分享，刷新/后退都能还原。
  本路由被 routeRules '/search/**' 精准反选为 ssr:false：首屏数据只在客户端拉取，
  改任何"可直出"假设前先查反选表。
  硬契约：
  1. 语言前缀必须走 applyLocalePrefix('/search', locale)：本页曾把裸路径写进 router.push，
     在 /en/search 上点搜索会把英文用户整站切回中文页（AGENTS §2.3.3 第 2 条）。
  2. sort 只回发白名单值（后端对未知值回退 latest），category/tag 原样透传。
  3. 检索词与筛选都为空时展示开始提示；仅筛选不为空时按该筛选浏览列表
     （此时计数改用「共 N 篇」，搜索口径的「与「」相关」在空关键词下会读成病句）。
-->
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
              <Search class="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 size-4 text-muted-foreground" />
              <Input
                v-model="keyword"
                :aria-label="t('common.search')"
                :placeholder="t('search.placeholder')"
                class="pl-9 h-10"
                @keyup.enter="runSearch"
              />
            </div>
            <Button
              variant="default"
              class="shrink-0"
              @click="runSearch"
            >
              <Search
                data-icon="inline-start"
                class="mr-2"
              />
              {{ t('search.submit') }}
            </Button>
          </div>

          <div class="mt-3 grid grid-cols-1 sm:grid-cols-3 gap-3">
            <Select
              v-model="selectedCategory"
              @update:model-value="handleFilter"
            >
              <SelectTrigger
                class="h-10"
                :aria-label="t('posts.selectCategory')"
              >
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

            <Select
              v-model="selectedTag"
              @update:model-value="handleFilter"
            >
              <SelectTrigger
                class="h-10"
                :aria-label="t('search.selectTag', '选择标签')"
              >
                <SelectValue :placeholder="t('search.selectTag', '选择标签')" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="__all">
                  {{ t('search.allTags', '全部标签') }}
                </SelectItem>
                <SelectItem
                  v-for="tag in tags"
                  :key="tag.id"
                  :value="tag.slug"
                >
                  {{ pickLocalized(tag.name) }}
                </SelectItem>
              </SelectContent>
            </Select>

            <Select
              v-model="sortBy"
              @update:model-value="handleFilter"
            >
              <SelectTrigger
                class="h-10"
                :aria-label="t('posts.sortLabel')"
              >
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
        </CardContent>
      </Card>

      <!-- 生效中的筛选做成可单独移除的 chip：三个下拉框里"当前选了什么"只有点开才看得见，
           用户想只去掉标签而保留分类时，此前只能把两个都清掉再重选。 -->
      <div
        v-if="hasFilter"
        class="mt-3 flex flex-wrap items-center gap-2"
      >
        <button
          v-for="chip in activeFilterChips"
          :key="chip.key"
          type="button"
          class="inline-flex items-center gap-1.5 rounded-full border border-border bg-muted/50 ps-3 pe-2 py-1 text-xs transition-colors hover:bg-muted"
          :aria-label="t('search.removeFilter', { name: chip.label })"
          @click="removeFilter(chip.key)"
        >
          <span class="text-muted-foreground">{{ chip.prefix }}</span>
          <span class="font-medium">{{ chip.label }}</span>
          <X class="size-3" />
        </button>
      </div>
    </header>

    <template v-if="!hasKeyword && !hasFilter">
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

        <!-- 最近搜索：本机 localStorage，只在客户端挂载后读取（首帧两端都是空列表）。 -->
        <div
          v-if="recentSearches.length > 0"
          class="mt-6 flex flex-wrap items-center justify-center gap-2"
        >
          <span class="text-xs text-muted-foreground">{{ t('search.recentTitle') }}</span>
          <button
            v-for="kw in recentSearches"
            :key="kw"
            type="button"
            class="rounded-full border border-border px-3 py-1 text-xs transition-colors hover:bg-muted"
            @click="applyRecent(kw)"
          >
            {{ kw }}
          </button>
          <button
            type="button"
            class="text-xs text-muted-foreground underline underline-offset-4 hover:text-foreground"
            @click="clearRecent"
          >
            {{ t('search.clearRecent') }}
          </button>
        </div>
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
      <div class="mb-6 flex flex-wrap items-center justify-between gap-2 text-muted-foreground">
        <p aria-live="polite">
          {{ hasKeyword
            ? t('search.resultCount', { count: total, keyword: keywordLabel })
            : t('posts.resultCount', { n: total }) }}
        </p>
        <button
          v-if="hasFilter"
          type="button"
          class="inline-flex items-center gap-1 rounded-md px-2 py-1 text-xs font-medium text-primary transition-colors hover:bg-primary/10"
          @click="clearFilters"
        >
          <X class="size-3.5" />
          {{ t('posts.clearFilters') }}
        </button>
      </div>
      <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        <PostCard
          v-for="post in posts"
          :key="post.id"
          :post="post"
          :highlight="keywordLabel"
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
          <!-- 分页用真实 <a href>：中键/新标签页能落到对应页码，点击仍走 SPA 翻页 -->
          <template v-if="currentPage <= 1">
            <Button
              variant="outline"
              size="icon"
              disabled
              :aria-label="t('common.prevPage', '上一页')"
            >
              <ChevronLeft data-icon="inline-start" />
            </Button>
          </template>
          <a
            v-else
            :href="pageHref(currentPage - 1)"
            :aria-label="t('common.prevPage', '上一页')"
            :class="pageLinkClass('outline')"
            @click.prevent="handlePageChange(currentPage - 1)"
          >
            <ChevronLeft data-icon="inline-start" />
          </a>
          <template
            v-for="page in visiblePages"
            :key="page"
          >
            <span
              v-if="page === currentPage"
              aria-current="page"
              :class="pageLinkClass('default')"
            >{{ page }}</span>
            <a
              v-else
              :href="pageHref(page)"
              :class="pageLinkClass('ghost')"
              @click.prevent="handlePageChange(page)"
            >{{ page }}</a>
          </template>
          <template v-if="currentPage >= totalPages">
            <Button
              variant="outline"
              size="icon"
              disabled
              :aria-label="t('common.nextPage', '下一页')"
            >
              <ChevronRight data-icon="inline-start" />
            </Button>
          </template>
          <a
            v-else
            :href="pageHref(currentPage + 1)"
            :aria-label="t('common.nextPage', '下一页')"
            :class="pageLinkClass('outline')"
            @click.prevent="handlePageChange(currentPage + 1)"
          >
            <ChevronRight data-icon="inline-start" />
          </a>
        </nav>
      </div>
    </template>

    <!-- 后端故障 ≠ 查无结果：两者都落到 v-else 时，用户会反复换关键词，
         而真实情况只是这一次检索请求失败了。 -->
    <template v-else-if="searchError">
      <div class="text-center py-20">
        <div class="inline-flex items-center justify-center size-16 rounded-2xl bg-muted mb-4">
          <SearchX class="size-8 text-muted-foreground" />
        </div>
        <h3 class="font-display text-xl font-semibold">
          {{ t('search.loadFailed') }}
        </h3>
        <Button
          variant="outline"
          class="mt-4"
          @click="refresh()"
        >
          {{ t('common.retry') }}
        </Button>
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
          {{ hasKeyword
            ? t('search.noResultsDesc', { keyword: keywordLabel })
            : t('posts.noMatchDesc') }}
        </p>
        <Button
          v-if="hasFilter"
          variant="outline"
          size="sm"
          class="mt-4"
          @click="clearFilters"
        >
          <X data-icon="inline-start" />
          {{ t('posts.clearFilters') }}
        </Button>
      </div>
    </template>
  </div>
</template>

<script setup lang="ts">
import { Card, CardContent } from '~~/components/ui/card'
import { Button, buttonVariants } from '~~/components/ui/button'
import { Input } from '~~/components/ui/input'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '~~/components/ui/select'
import PostCard from '~~/components/PostCard.vue'
import PostSkeleton from '~~/components/PostSkeleton.vue'
import type { Category, PaginatedResponse, Post, Tag } from '~~/types/api'
import { useAPI } from '~~/composables/useApi'
import { pageWindow } from '~~/lib/pagination'
import { useI18n } from 'vue-i18n'
import { Search, SearchX, ChevronLeft, ChevronRight, X } from '@lucide/vue'
import { ref, computed, watch, onMounted } from 'vue'

definePageMeta({ layout: 'default' })

const { t, locale } = useI18n()
const route = useRoute()
const router = useRouter()

const pickLocalized = (val: unknown): string => pickLocalizedText(val, locale.value)

const ALL = '__all'
const SORT_VALUES = ['latest', 'popular'] as const
type SortValue = (typeof SORT_VALUES)[number]

const sortFromUrl = (raw: unknown): SortValue =>
  SORT_VALUES.includes(raw as SortValue) ? (raw as SortValue) : 'latest'
const slugFromUrl = (raw: unknown): string => {
  const v = typeof raw === 'string' ? raw.trim() : ''
  return v === ALL ? '' : v
}

const keyword = ref<string>((route.query.q as string) || '')
const selectedCategory = ref(slugFromUrl(route.query.category))
const selectedTag = ref(slugFromUrl(route.query.tag))
const sortBy = ref<SortValue>(sortFromUrl(route.query.sort))
// 页码与检索词/筛选同样是 URL 状态：刷新/分享/后退必须还原当前页，而不是落回第一页。
const currentPage = ref(Math.max(1, Number(route.query.page) || 1))
const site = useSite()
// 每页条数取后台「阅读体验」分组；未配置时沿用 9
const pageSize = computed(() => site.reading.value.posts_per_page)

const hasKeyword = computed(() => !!(route.query.q as string | undefined)?.trim())
const hasFilter = computed(() => !!selectedCategory.value || !!selectedTag.value || sortBy.value !== 'latest')
const keywordLabel = computed(() => String(route.query.q || '').trim())

type FilterKey = 'category' | 'tag' | 'sort'

/** 生效中的筛选 chip：显示解析后的名称（slug 只在字典还没到时兜底），移除按钮逐个生效。 */
const activeFilterChips = computed<Array<{ key: FilterKey, prefix: string, label: string }>>(() => {
  const chips: Array<{ key: FilterKey, prefix: string, label: string }> = []
  if (selectedCategory.value) {
    const hit = (categories.value ?? []).find(c => c.slug === selectedCategory.value)
    chips.push({
      key: 'category',
      prefix: String(t('nav.categories')),
      label: hit ? pickLocalized(hit.name) : selectedCategory.value
    })
  }
  if (selectedTag.value) {
    const hit = tags.value.find(tg => tg.slug === selectedTag.value)
    chips.push({
      key: 'tag',
      prefix: String(t('nav.tags')),
      label: hit ? pickLocalized(hit.name) : selectedTag.value
    })
  }
  if (sortBy.value !== 'latest') {
    chips.push({
      key: 'sort',
      prefix: String(t('posts.sortLabel')),
      label: String(t('posts.sortPopular'))
    })
  }
  return chips
})

// 分类与首页/页脚/文章列表共用同一把缓存键，跨页不重复请求。
const { data: categories } = useAPI<Category[]>('/blog/categories', {
  query: { lang: locale.value },
  key: `blog:categories:${locale.value}`,
  default: () => []
})
const { data: tagsRaw } = useAPI<Tag[]>('/blog/tags', {
  query: { lang: locale.value },
  key: `home:tags:${locale.value}`,
  default: () => []
})
const tags = computed<Tag[]>(() => (Array.isArray(tagsRaw.value) ? tagsRaw.value.filter(t => t.is_active) : []))

// 以路由 query 作为检索与筛选的唯一真值来源：结果可分享、可后退。
const { data, pending, error: searchError, refresh } = useAPI<PaginatedResponse<Post>>('/blog/posts', {
  query: computed(() => ({
    lang: locale.value,
    page: currentPage.value,
    page_size: pageSize.value,
    search: keywordLabel.value || undefined,
    category: selectedCategory.value || undefined,
    tag: selectedTag.value || undefined,
    // 后端对未知取值回退 latest，这里同样只发白名单值
    sort: sortBy.value === 'popular' ? 'popular' : undefined
  })),
  key: computed(() =>
    `search:${keywordLabel.value}:${selectedCategory.value}:${selectedTag.value}:${sortBy.value}:${currentPage.value}`
  )
})

const posts = computed<Post[]>(() => data.value?.items || [])
const total = computed(() => data.value?.total || 0)
const totalPages = computed(() => Math.ceil(total.value / pageSize.value) || 1)

const visiblePages = computed(() => pageWindow(currentPage.value, totalPages.value))

// 地址栏查询串的唯一构造函数：关键词以「本次要提交的值」为准，不能只读 route.query.q ——
// 输入框是草稿态，只读 URL 会让「输入关键词 → 点搜索」第一次提交丢掉关键词（URL 纹丝不动）。
const buildUrlQuery = (rawKeyword: string): Record<string, string> => {
  const q: Record<string, string> = {}
  const kw = rawKeyword.trim()
  if (kw) q.q = kw
  if (selectedCategory.value) q.category = selectedCategory.value
  if (selectedTag.value) q.tag = selectedTag.value
  if (sortBy.value !== 'latest') q.sort = sortBy.value
  if (currentPage.value > 1) q.page = String(currentPage.value)
  return q
}

const urlQuery = computed<Record<string, string>>(() => buildUrlQuery(keywordLabel.value))

const searchPath = computed(() => applyLocalePrefix('/search', locale.value))

const syncUrl = (mode: 'push' | 'replace', keywordDraft?: string) => {
  const built = buildUrlQuery(keywordDraft ?? keywordLabel.value)
  const target = { path: searchPath.value, query: Object.keys(built).length > 0 ? built : {} }
  if (mode === 'push') void router.push(target)
  else void router.replace(target)
}

const runSearch = () => {
  // 输入框是草稿态：只有点搜索/回车才写进 URL；筛选保留，页码归 1。
  keyword.value = keyword.value.trim()
  currentPage.value = 1
  syncUrl('push', keyword.value)
  rememberSearch(keyword.value)
}

// ===== 最近搜索：只存在本机 localStorage，不上报、不同步 =====
// 首帧渲染必须是空列表（SSR 与 hydrate 两端一致），读取放在 onMounted。
const RECENT_SEARCH_KEY = 'rosetta:recent-searches'
const RECENT_SEARCH_LIMIT = 5
const recentSearches = ref<string[]>([])

const readRecentSearches = (): string[] => {
  try {
    const raw = localStorage.getItem(RECENT_SEARCH_KEY)
    const parsed: unknown = raw ? JSON.parse(raw) : []
    return Array.isArray(parsed)
      ? parsed.filter((s): s is string => typeof s === 'string' && s.trim().length > 0).slice(0, RECENT_SEARCH_LIMIT)
      : []
  } catch {
    return []
  }
}

const writeRecentSearches = (list: string[]) => {
  recentSearches.value = list
  try {
    localStorage.setItem(RECENT_SEARCH_KEY, JSON.stringify(list))
  } catch {
    // 隐私模式下 localStorage 可能直接抛错：记忆功能失效不该影响检索本身
  }
}

const rememberSearch = (raw: string) => {
  if (!import.meta.client) return
  const kw = raw.trim()
  if (!kw) return
  const rest = (recentSearches.value.length ? recentSearches.value : readRecentSearches())
    .filter(item => item !== kw)
  writeRecentSearches([kw, ...rest].slice(0, RECENT_SEARCH_LIMIT))
}

const applyRecent = (kw: string) => {
  keyword.value = kw
  runSearch()
}

const clearRecent = () => writeRecentSearches([])

onMounted(() => {
  if (!import.meta.client) return
  recentSearches.value = readRecentSearches()
})

const handleFilter = () => {
  // 改筛选时把输入框里的草稿一并提交：用户已经打了字再选分类，期望的是两者一起生效。
  currentPage.value = 1
  syncUrl('replace', keyword.value)
}

const handlePageChange = (page: number) => {
  if (page < 1 || page > totalPages.value) return
  // 不调 refresh()：currentPage 进 query/key 的 computed，Nuxt 的 key watcher
  // 已自动重取；再手写 refresh 等于同一 URL 双发，第一发还被 abort。
  currentPage.value = page
  // 用 replace 而非 push：翻页不该在历史里堆出一串同关键词的条目，
  // 但地址栏必须带上 page，否则分享出去的链接永远停在第一页。
  syncUrl('replace')
  if (import.meta.client) {
    window.scrollTo({ top: 0, behavior: 'smooth' })
  }
}

const clearFilters = () => {
  selectedCategory.value = ''
  selectedTag.value = ''
  sortBy.value = 'latest'
  currentPage.value = 1
  syncUrl('replace')
}

/** 只移除一个筛选位；关键词是输入框的内容，不属于筛选，一律不动。 */
const removeFilter = (key: FilterKey) => {
  if (key === 'category') selectedCategory.value = ''
  else if (key === 'tag') selectedTag.value = ''
  else sortBy.value = 'latest'
  currentPage.value = 1
  syncUrl('replace', keyword.value)
}

const pageHref = (page: number) => {
  const params = new URLSearchParams({ ...urlQuery.value, page: String(page) })
  return `${searchPath.value}?${params.toString()}`
}
const pageLinkClass = (variant: 'default' | 'outline' | 'ghost') =>
  buttonVariants({ variant, size: 'icon' })

// 越界页码（?page=99）拉回最后一页，避免停在"第 99 页，共 3 页"的空结果。
watch([total, currentPage], () => {
  if (total.value > 0 && currentPage.value > totalPages.value) currentPage.value = totalPages.value
})

// 浏览器前进/后退改的是地址栏，页内状态要跟着回读
watch(
  () => route.query,
  (q) => {
    keyword.value = (q.q as string) || ''
    selectedCategory.value = slugFromUrl(q.category)
    selectedTag.value = slugFromUrl(q.tag)
    sortBy.value = sortFromUrl(q.sort)
    currentPage.value = Math.max(1, Number(q.page) || 1)
  }
)

useSeo({
  title: computed(() => {
    const q = keywordLabel.value
    return q
      ? (t('search.resultCount', { count: total.value, keyword: q }) as string)
      : (t('search.title') as string || '搜索')
  }),
  description: computed(() => t('search.desc') as string),
  type: 'website',
  // 搜索结果不进索引：查询参数变体是薄内容页面，Google 官方口径就是 noindex
  noindex: true
})
useWebsiteJsonLd()
useBreadcrumbJsonLd([
  { name: t('nav.home', '首页') as string, url: '/' },
  { name: t('nav.search', '搜索') as string, url: '/search' }
])
</script>
