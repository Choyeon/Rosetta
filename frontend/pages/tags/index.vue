<!--
  标签页：GET /blog/tags 的单一卡片网格（按文章数倒序）。
  上一版同时渲染「标签云 + 卡片网格」两份同一批链接，同屏重复且标题说法互相矛盾；
  现在只保留一份，用热度条表达相对收录量，字号阶梯（countToScale）随之删除。
  排序是纯函数（数量降序 → slug 字典序），掺入随机或时间相关因子会让 SSR 与客户端顺序不同。
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
      v-if="_tagsLoading && sortedTags.length === 0"
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
    <div
      v-else-if="sortedTags.length"
      class="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 gap-4"
    >
      <NuxtLink
        v-for="tag in sortedTags"
        :key="tag.id"
        v-memo="[tag.id, tag.slug, tag.color]"
        :to="localeHref(`/tags/${tag.slug}`)"
        class="no-underline group block rounded-xl focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-background"
      >
        <div class="card-surface lift-hover h-full rounded-xl p-4 flex flex-col gap-3">
          <div class="flex items-center justify-between gap-2">
            <TagBadge
              :color="tag.color"
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
import { Tags, RefreshCw } from '@lucide/vue'
import TagBadge from '~~/components/TagBadge.vue'
import { Button } from '~~/components/ui/button'
import { computed } from 'vue'

definePageMeta({ layout: 'default' })

const { t, locale } = useI18n()
const site = useSite()
const { localeHref } = useLocaleLink()

interface TagRow {
  id: number | string
  slug: string
  name?: string | Record<string, string>
  color?: string | null
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

/** 按文章数降序 → 按 slug 稳定排序 */
const sortedTags = computed<TagRow[]>(() => {
  return [...tags.value].sort((a, b) => {
    const d = tagPostsCount(b) - tagPostsCount(a)
    if (d !== 0) return d
    return String(a.slug).localeCompare(String(b.slug))
  })
})

/** 最热标签的文章数，作为热度条的 100% 分母（0 保护：没有文章时全部为 0）。 */
const maxPostsCount = computed<number>(() =>
  sortedTags.value.reduce((max, tag) => Math.max(max, tagPostsCount(tag)), 0)
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
