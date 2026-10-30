<!--
  分类列表页：GET /blog/categories 卡片网格，name/description 按四语 dict 取值，
  post_count 兼容 postsCount 两种命名。
  契约（2026-10 防双发改造后）：键与查询都是 setup 期静态字面量，切语言的刷新
  靠「切换器必然跳同页目标语言 URL → NuxtPage 按 path 重挂载本页 → setup 以新
  locale 重新请求」。不再写 watch(locale)+refresh()：旧写法里 key watcher 那一发
  用的仍是旧 locale 的静态查询参数，手写 refresh 又与它双发、第一发必被 abort，
  每切一次语言白送后端两次注定被丢弃的 /blog/categories 查询。
  排序（?sort=name，缺省按文章数倒序）是纯函数，条件落在地址栏：SSR 首屏与分享链接
  同一视图，改条件走 replace 不堆历史；名称比较走 lib/sortText（码位序，SSR/浏览器一致）。
-->
<template>
  <div class="container py-16">
    <header class="mb-12 text-center max-w-2xl mx-auto">
      <div class="inline-flex items-center justify-center size-14 rounded-2xl bg-primary/10 mb-5">
        <FolderOpen class="size-7 text-primary" />
      </div>
      <h1 class="font-display text-3xl md:text-4xl font-bold tracking-tight">
        {{ t('categories.title') }}
      </h1>
      <p class="text-muted-foreground mt-3 leading-relaxed">
        {{ t('categories.desc') }}
      </p>
    </header>

    <div
      v-if="_catsLoading && categories.length === 0"
      class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6"
    >
      <div
        v-for="i in 6"
        :key="i"
        class="h-48 rounded-2xl border border-border/60 bg-card p-6"
      >
        <!-- 分类卡骨架：与真实卡片同网点布局（图标方块 / 计数徽章 / 标题 / 两行摘要 / 元信息） -->
        <div class="flex items-start justify-between mb-4">
          <Skeleton class="size-12 rounded-xl" />
          <Skeleton class="w-12 h-6 rounded-full" />
        </div>
        <Skeleton class="h-5 w-2/3 rounded-full mb-3" />
        <div class="flex flex-col gap-2 mb-4">
          <Skeleton class="h-4 w-full rounded-full" />
          <Skeleton class="h-4 w-5/6 rounded-full" />
        </div>
        <div class="h-px bg-border/60 my-2" />
        <Skeleton class="h-4 w-1/2 rounded-full mt-3" />
      </div>
    </div>

    <div
      v-else-if="catsLoadError"
      class="rounded-xl border border-destructive/30 bg-destructive/5 p-6 text-sm text-destructive"
    >
      <div class="flex flex-col items-center gap-3 text-center">
        <span>{{ t('error.loadFailed') }}</span>
        <Button
          variant="outline"
          size="sm"
          @click="refresh()"
        >
          <RefreshCw data-icon="inline-start" />
          {{ t('error.retry') }}
        </Button>
      </div>
    </div>

    <div
      v-if="categories.length"
      class="mb-6 flex flex-wrap items-center justify-end gap-3"
    >
      <span class="text-xs text-muted-foreground tabular-nums">
        {{ t('categories.showingCount', { n: categories.length }) }}
      </span>
      <div
        role="radiogroup"
        :aria-label="t('posts.sortLabel')"
        class="flex gap-2"
      >
        <Button
          v-for="opt in sortOptions"
          :key="opt.value"
          :variant="sortMode === opt.value ? 'default' : 'outline'"
          size="sm"
          role="radio"
          :aria-checked="sortMode === opt.value"
          @click="setSort(opt.value)"
        >
          {{ opt.label }}
        </Button>
      </div>
    </div>

    <TransitionGroup
      v-if="categories.length"
      tag="div"
      class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6"
      name="list-item"
    >
      <NuxtLink
        v-for="cat in sortedCategories"
        :key="cat.id"
        v-memo="[cat.id, cat.slug, cat.post_count ?? cat.postsCount]"
        :to="localeHref(`/categories/${cat.slug}`)"
        class="block rounded-2xl focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2"
      >
        <Card class="h-full group transition-all hover:shadow-soft hover:-translate-y-0.5 duration-300 overflow-hidden">
          <CardHeader class="p-6 pb-4">
            <div class="flex items-start justify-between mb-4">
              <div
                class="size-12 rounded-xl flex items-center justify-center bg-primary/10 transition-transform duration-300 group-hover:scale-110"
                :style="cat.color ? { background: `color-mix(in oklab, ${cat.color} 15%, transparent)` } : undefined"
              >
                <DynamicIcon
                  v-if="cat.icon"
                  :icon="cat.icon"
                  class="size-6"
                  :class="cat.color ? 'text-foreground' : 'text-primary'"
                />
                <FolderOpen
                  v-else
                  class="size-6 text-primary"
                />
              </div>
              <Badge variant="secondary">
                {{ getPostsCount(cat) }} {{ t('categories.posts') }}
              </Badge>
            </div>
            <CardTitle class="font-display text-xl tracking-tight group-hover:underline underline-offset-4">
              {{ getCatName(cat) }}
            </CardTitle>
            <CardDescription class="mt-2 line-clamp-2 leading-relaxed min-h-[3rem]">
              {{ getCatDesc(cat) || t('categories.noDesc') }}
            </CardDescription>
          </CardHeader>
          <CardFooter class="p-6 pt-0 flex items-center justify-between text-sm text-muted-foreground border-t mt-2">
            <span>{{ t('categories.browsePosts') }}</span>
            <ArrowRight class="size-4 transition-transform duration-300 group-hover:translate-x-1" />
          </CardFooter>
        </Card>
      </NuxtLink>
    </TransitionGroup>

    <div
      v-if="categoriesEmpty"
      class="text-center py-20"
    >
      <div class="inline-flex items-center justify-center size-16 rounded-2xl bg-muted mb-4">
        <FolderOpen class="size-8 text-muted-foreground" />
      </div>
      <h3 class="font-display text-xl font-semibold">
        {{ t('categories.noCategories') }}
      </h3>
    </div>
  </div>
</template>

<script setup lang="ts">
import {
  Card,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle
} from '~~/components/ui/card'
import { Badge } from '~~/components/ui/badge'
import { Button } from '~~/components/ui/button'
import { useI18n } from 'vue-i18n'
import { FolderOpen, ArrowRight, RefreshCw } from '@lucide/vue'
import { compareText } from '~~/lib/sortText'
import { computed, ref, watch } from 'vue'

definePageMeta({ layout: 'default' })

const { t, locale } = useI18n()
const site = useSite()
const { localeHref } = useLocaleLink()
const route = useRoute()
const router = useRouter()

const pickLocalized = (val: unknown): string => pickLocalizedText(val, locale.value)
const getCatName = (c: { name?: string | Record<string, string> } | null | undefined) => pickLocalized(c?.name)
const getCatDesc = (c: { description?: string | Record<string, string> } | null | undefined) => pickLocalized(c?.description)
const getPostsCount = (c: { post_count?: number, postsCount?: number } | null | undefined) => c?.post_count ?? c?.postsCount ?? 0

interface CategoryRow {
  id: number | string
  slug: string
  name?: string | Record<string, string>
  description?: string | Record<string, string>
  icon?: string
  color?: string
  post_count?: number
  postsCount?: number
}

// 真实接口：GET /api/blog/categories。SSR + 客户端同源，失败时回退空数组，不显示示例分类。
// 键与 AppFooter 等共用 `blog:categories:<locale>`（Nuxt 按 key 去重，同页只发一条）；
// 静态键+静态查询：切语言走「跳同页 URL → 重挂载 → 新 locale 重新请求」，
// 不手写 watch(locale)+refresh()（与 Nuxt key watcher 双发，第一发必被 abort）。
const { data: catsData, pending: _catsLoading, error: catsLoadError, refresh } = useAPI<CategoryRow[]>('/blog/categories', {
  query: { lang: locale.value },
  key: `blog:categories:${locale.value}`,
  default: () => []
})

const categories = computed<CategoryRow[]>(() => {
  const raw = catsData.value
  if (!Array.isArray(raw)) return []
  return raw
})

// ===== 排序：状态落在地址栏（?sort=name），SSR 首屏与分享链接同口径 =====
// 默认按文章数倒序（接口返回的是 id 序，对读者没有意义）；改条件走 replace 不堆历史。
// 名称比较走 lib/sortText 的码位比较，不用 localeCompare（ICU 排序在 SSR/浏览器不一致）。
const sortMode = ref<'count' | 'name'>(route.query.sort === 'name' ? 'name' : 'count')

const setSort = (next: 'count' | 'name') => {
  if (sortMode.value === next) return
  sortMode.value = next
}

const sortOptions = computed(() => [
  { value: 'count' as const, label: String(t('categories.sortCount')) },
  { value: 'name' as const, label: String(t('categories.sortName')) }
])

watch(sortMode, (next) => {
  const query = next === 'count' ? {} : { sort: next }
  void router.replace({ query })
})

const sortedCategories = computed<CategoryRow[]>(() => {
  return [...categories.value].sort((a, b) => {
    if (sortMode.value === 'name') {
      const byName = compareText(getCatName(a), getCatName(b))
      if (byName !== 0) return byName
    }
    const d = getPostsCount(b) - getPostsCount(a)
    if (d !== 0) return d
    return compareText(String(a.slug), String(b.slug))
  })
})

// 空目录页 = 没有可索引内容（与 /sponsor 的 sponsorEmpty 同口径），后端 sitemap 同步跳过。
// 只在「确实取到空列表」时 noindex：加载中或请求失败仍保持可索引——一次网络故障不该把
// 有内容的目录页从索引里摘掉，而本页 3600s swr 会把判错的结果缓存一小时。
const categoriesEmpty = computed(
  () => !_catsLoading.value && !catsLoadError.value && categories.value.length === 0
)

// ===== SEO：基于 i18n + 站点设置 =====
useSeo({
  title: computed(() => String(t('nav.categories') || t('categories.title') || '分类')),
  description: computed(() => String(t('categories.desc') || '') || site.siteDescription.value),
  type: 'website',
  noindex: categoriesEmpty
})
useWebsiteJsonLd()
useBreadcrumbJsonLd([
  { name: t('nav.home') as string, url: '/' },
  { name: t('nav.categories') as string, url: '/categories' }
])
</script>
