<!--
  标签页：GET /blog/tags 的单一卡片网格（默认按文章数倒序）。
  上一版同时渲染「标签云 + 卡片网格」两份同一批链接，同屏重复且标题说法互相矛盾；
  现在只保留一份，用热度条表达相对收录量，字号阶梯（countToScale）随之删除。
  排序与关键词过滤都是纯函数（不调接口、不掺随机/时间因子），条件落在 ?q= / ?sort= 上：
  SSR 首屏按 query 过滤（分享链接打开即是同一视图），改条件走 replace 不堆历史。
  关键词只看本地化名称与 slug，输入框是即时过滤（不是草稿态），因此不需要提交按钮。
  排序 chip 是真实 <a href>（走 localeHrefWith，带齐当前 ?q=）：SSR 页把视图切换做成
  <Button @click> 等于 ?sort=name 在爬虫的链接图里不存在（批次 #127，AGENTS §2.3.3）。
  name 缺失兜底 slug，post_count 兼容 postsCount 两种命名。
-->
<template>
  <div class="container py-16">
    <header class="mb-12 text-center max-w-2xl mx-auto">
      <div class="inline-flex items-center justify-center size-14 rounded-2xl bg-primary/10 mb-5">
        <Tags class="size-7 text-primary" />
      </div>
      <h1 class="font-display text-3xl md:text-4xl font-bold tracking-tight">
        {{ t('tags.title') }}
      </h1>
      <p class="text-muted-foreground mt-3 leading-relaxed">
        {{ t('tags.desc') }}
      </p>
    </header>

    <!-- 加载态：与结果同形状的骨架，避免"先出标签云再换成网格"的二次跳版 -->
    <div
      v-if="_tagsLoading && tags.length === 0"
      class="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 gap-4"
    >
      <Skeleton
        v-for="i in 10"
        :key="i"
        class="h-[104px] rounded-xl"
      />
    </div>

    <div
      v-else-if="tagsLoadError"
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

    <!-- 单一视图：上一版把同一批标签渲染了两遍（顶部标签云 + 下方卡片网格），
         同一屏里每个标签出现两次、链接也重复一次。这里只保留卡片网格，
         用数量条表达热度，信息量不减而重复消失。 -->
    <template v-else-if="tags.length">
      <!-- 工具栏：标签到几十条后网格不再是可扫的导航面，先给本地过滤 + 排序；
           过滤结果为空时保留工具栏（否则用户没有入口改回条件）。 -->
      <div class="mb-6 flex flex-col gap-3 sm:flex-row sm:items-center">
        <div class="relative flex-1">
          <Search
            class="pointer-events-none absolute start-3 top-1/2 -translate-y-1/2 size-4 text-muted-foreground"
            aria-hidden="true"
          />
          <Input
            v-model="filterQuery"
            :placeholder="t('tags.filterPlaceholder')"
            :aria-label="t('tags.filterPlaceholder')"
            class="ps-9 h-10"
          />
        </div>
        <div
          role="group"
          :aria-label="t('posts.sortLabel')"
          class="flex gap-2"
        >
          <a
            v-for="opt in sortOptions"
            :key="opt.value"
            :href="sortHref(opt.value)"
            :class="buttonVariants({ variant: sortMode === opt.value ? 'default' : 'outline', size: 'sm' })"
            :aria-current="sortMode === opt.value ? 'true' : undefined"
            @click.prevent="setSort(opt.value)"
          >
            {{ opt.label }}
          </a>
        </div>
      </div>

      <p
        v-if="visibleTags.length"
        class="mb-4 text-xs text-muted-foreground"
        aria-live="polite"
      >
        {{ t('tags.showingCount', { n: visibleTags.length }) }}
      </p>

      <div
        v-if="visibleTags.length"
        class="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 gap-4"
      >
        <NuxtLink
          v-for="tag in visibleTags"
          :key="tag.id"
          v-memo="[tag.id, tag.slug, tag.color, tag.icon]"
          :to="localeHref(`/tags/${tag.slug}`)"
          class="no-underline group block rounded-xl focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-background"
        >
          <div class="card-surface lift-hover h-full rounded-xl p-4 flex flex-col gap-3">
            <div class="flex items-center justify-between gap-2">
              <TagBadge
                :color="tag.color"
                :icon="tag.icon"
                :label="tagName(tag)"
                size="md"
                show-icon
              />
              <span class="text-xs text-muted-foreground tabular-nums shrink-0">
                {{ tagPostsCount(tag) }}
              </span>
            </div>
            <div class="mt-auto">
              <div
                class="h-1 w-full overflow-hidden rounded-full bg-muted"
                role="presentation"
              >
                <div
                  class="h-full rounded-full transition-[width] duration-[var(--motion-duration-slow)] ease-out"
                  :class="tag.color ? '' : 'bg-primary/70'"
                  :style="{ width: `${tagBarWidth(tag)}%`, backgroundColor: tag.color || undefined }"
                />
              </div>
              <span class="sr-only">{{ tagPostsCount(tag) }} {{ t('tags.posts') }}</span>
            </div>
          </div>
        </NuxtLink>
      </div>

      <div
        v-else
        class="text-center py-16"
      >
        <div class="inline-flex items-center justify-center size-16 rounded-2xl bg-muted mb-4">
          <Search class="size-8 text-muted-foreground" />
        </div>
        <h3 class="font-display text-xl font-semibold">
          {{ t('tags.noMatch') }}
        </h3>
        <p class="text-muted-foreground mt-2 text-sm">
          {{ t('tags.noMatchHint') }}
        </p>
        <Button
          variant="outline"
          size="sm"
          class="mt-5"
          @click="clearFilter"
        >
          {{ t('tags.clearFilter') }}
        </Button>
      </div>
    </template>

    <div
      v-else
      class="text-center py-20"
    >
      <div class="inline-flex items-center justify-center size-16 rounded-2xl bg-muted mb-4">
        <Tags class="size-8 text-muted-foreground" />
      </div>
      <h3 class="font-display text-xl font-semibold">
        {{ t('tags.noTags') }}
      </h3>
    </div>
  </div>
</template>

<script setup lang="ts">
import { Tags, RefreshCw, Search } from '@lucide/vue'
import TagBadge from '~~/components/TagBadge.vue'
import { Button, buttonVariants } from '~~/components/ui/button'
import { Input } from '~~/components/ui/input'
import { compareText } from '~~/lib/sortText'
import { computed, ref, watch } from 'vue'

definePageMeta({ layout: 'default' })

const { t, locale } = useI18n()
const site = useSite()
const { localeHref, localeHrefWith } = useLocaleLink()
const route = useRoute()
const router = useRouter()

interface TagRow {
  id: number | string
  slug: string
  name?: string | Record<string, string>
  color?: string | null
  icon?: string | null
  post_count?: number
  postsCount?: number
}

// SSR 与客户端首渲染统一为空数组（空 = 无标签占位，避免显示假数据）。
// 首屏渲染用 useSSR 友好的 useAPI，失败或空都保持空态，绝不回退到示例标签。
// 静态键+静态查询：切语言走「跳同页 URL → 重挂载 → 新 locale 重新请求」，
// 不手写 watch(locale)+refresh()（与 Nuxt key watcher 双发，第一发必被 abort）。
const { data: tagsData, pending: _tagsLoading, error: tagsLoadError, refresh } = useAPI<TagRow[]>('/blog/tags', {
  query: { lang: locale.value },
  key: `home:tags:${locale.value}`,
  default: () => []
})

const tags = computed<TagRow[]>(() => {
  const raw = tagsData.value
  if (!Array.isArray(raw)) return []
  return raw
})

// 空目录页 = 没有可索引内容（与 /sponsor 的 sponsorEmpty 同口径），后端 sitemap 同步跳过。
// 只在「确实取到空列表」时 noindex：加载中或请求失败仍保持可索引——一次网络故障不该把
// 有内容的目录页从索引里摘掉，而本页 3600s swr 会把判错的结果缓存一小时。
const tagsEmpty = computed(
  () => !_tagsLoading.value && !tagsLoadError.value && tags.value.length === 0
)

// ===== SEO：基于 i18n + 站点设置 =====
useSeo({
  title: computed(() => String(t('nav.tags') || t('tags.title') || '标签')),
  description: computed(() => String(t('tags.desc') || '') || site.siteDescription.value),
  type: 'website',
  noindex: tagsEmpty
})
useWebsiteJsonLd()
useBreadcrumbJsonLd([
  { name: t('nav.home') as string, url: '/' },
  { name: t('nav.tags') as string, url: '/tags' }
])

const tagName = (tag: TagRow): string => {
  const v = tag.name
  if (v == null) return String(tag.slug)
  if (typeof v === 'string') return v
  const key = locale.value as string
  if (key && v[key]) return v[key]
  const first = Object.values(v as Record<string, string>)[0]
  return first || String(tag.slug)
}

const tagPostsCount = (tag: TagRow): number => {
  return tag.post_count ?? tag.postsCount ?? 0
}

// ===== 过滤 / 排序：状态全在地址栏（?q= / ?sort=），SSR 首屏与分享链接同口径 =====
// 不调接口：标签总量是几十条，本地过滤即可；改条件走 replace，避免在历史里堆一串筛选态。
const filterQuery = ref(typeof route.query.q === 'string' ? route.query.q : '')
const sortMode = ref<'count' | 'name'>(route.query.sort === 'name' ? 'name' : 'count')

const setSort = (next: 'count' | 'name') => {
  if (sortMode.value === next) return
  sortMode.value = next
}

const sortOptions = computed(() => [
  { value: 'count' as const, label: String(t('tags.sortCount')) },
  { value: 'name' as const, label: String(t('tags.sortName')) }
])

// 排序 chip 是真实 <a href>，且必须带齐当前关键词（批次 #127）：只挂 sort 的 href 会让
// 「在 `q=foo` 的结果里换成按名称排」变成一次丢筛选的跳转——地址栏与 chip 用的是同一份条件。
const sortHref = (mode: 'count' | 'name') =>
  localeHrefWith('/tags', {
    q: filterQuery.value.trim(),
    sort: mode === 'count' ? '' : mode
  })

const syncUrl = () => {
  const query: Record<string, string> = {}
  const kw = filterQuery.value.trim()
  if (kw) query.q = kw
  if (sortMode.value !== 'count') query.sort = sortMode.value
  void router.replace({ query })
}

watch([filterQuery, sortMode], syncUrl)

const clearFilter = () => {
  filterQuery.value = ''
}

/**
 * 可见标签 = 关键词过滤（本地化名称或 slug，忽略大小写）+ 排序。
 * 排序是纯函数（数量降序 → slug 字典序；按名称时先比名称）。
 * 名称比较走 lib/sortText 的码位比较，不用 localeCompare（ICU 排序在 SSR/浏览器不一致）。
 */
const visibleTags = computed<TagRow[]>(() => {
  const kw = filterQuery.value.trim().toLowerCase()
  const list = kw
    ? tags.value.filter(tag =>
        tagName(tag).toLowerCase().includes(kw) || String(tag.slug).toLowerCase().includes(kw))
    : [...tags.value]
  return list.sort((a, b) => {
    if (sortMode.value === 'name') {
      const byName = compareText(tagName(a), tagName(b))
      if (byName !== 0) return byName
    }
    const d = tagPostsCount(b) - tagPostsCount(a)
    if (d !== 0) return d
    return compareText(String(a.slug), String(b.slug))
  })
})

/** 最热标签的文章数，作为热度条的 100% 分母（0 保护：没有文章时全部为 0）。
 *  分母取全量标签而非过滤后的集合：筛选时热度条宽度不该跟着跳。 */
const maxPostsCount = computed<number>(() =>
  tags.value.reduce((max, tag) => Math.max(max, tagPostsCount(tag)), 0)
)

/**
 * 热度条宽度：按最大计数等比缩放，最小保留 6%，
 * 让只有 1 篇文章的标签也有可见长度（0 宽会看起来像坏掉的进度条）。
 * 纯算术，SSR 与客户端对同一数据得到同一像素值。
 */
const tagBarWidth = (tag: TagRow): number => {
  const max = maxPostsCount.value
  if (max <= 0) return 0
  return Math.max(6, Math.round((tagPostsCount(tag) / max) * 100))
}

// useAPI 已在顶层 await 进行 SSR 安全拉取；失败时自动回退空数组 default() => []，无示例标签残留。
</script>
