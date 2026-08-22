<template>
  <div class="container py-16 max-w-3xl mx-auto">
    <header class="mb-12">
      <div class="flex items-center gap-3 mb-4">
        <div class="inline-flex items-center justify-center size-12 rounded-xl bg-gradient-to-br from-slate-100 to-zinc-100 dark:from-slate-800 dark:to-zinc-800">
          <CalendarDays class="size-6 text-slate-600 dark:text-slate-300" />
        </div>
        <div>
          <h1 class="font-display text-3xl md:text-4xl font-bold tracking-tight">
            {{ t('archive.title') }}
          </h1>
          <p class="text-muted-foreground mt-1">
            {{ t('archive.desc') }}
          </p>
        </div>
      </div>
    </header>

    <div class="space-y-12">
      <section
        v-for="group in groupedByYear"
        :key="group.year"
        class="scroll-mt-24"
      >
        <div class="flex items-end justify-between mb-4">
          <h2 class="font-display text-2xl font-bold tracking-tight flex items-center gap-3">
            {{ group.year }}
            <Badge
              variant="secondary"
              class="text-xs font-medium"
            >
              {{ group.posts.length }} {{ t('archive.posts') }}
            </Badge>
          </h2>
        </div>
        <Separator />
        <ul class="mt-2">
          <li
            v-for="post in group.posts"
            :key="post.id"
            class="flex justify-between items-center py-3 border-b last:border-b-0 group/item"
          >
            <div class="flex items-center gap-3 min-w-0 flex-1">
              <Badge
                variant="outline"
                class="shrink-0 font-mono text-xs tabular-nums"
              >
                {{ formatMonthDay(getPublishedAt(post)) }}
              </Badge>
              <NuxtLink
                :to="`/posts/${post.slug}`"
                class="font-medium truncate group-hover/item:text-primary transition-colors"
              >
                {{ getPostTitle(post) }}
              </NuxtLink>
            </div>
            <div class="flex items-center gap-3 shrink-0 ml-3 text-xs text-muted-foreground">
              <span
                v-if="getCategoryName(post)"
                class="hidden sm:inline-flex items-center gap-1"
              >
                <FolderOpen class="size-3" />
                {{ getCategoryName(post) }}
              </span>
              <span class="inline-flex items-center gap-1 tabular-nums">
                <Eye class="size-3" />
                {{ getViews(post) }}
              </span>
            </div>
          </li>
        </ul>
      </section>
    </div>

    <div
      v-if="groupedByYear.length === 0"
      class="text-center py-20"
    >
      <div class="inline-flex items-center justify-center size-16 rounded-2xl bg-muted mb-4">
        <CalendarDays class="size-8 text-muted-foreground" />
      </div>
      <h3 class="font-display text-xl font-semibold">
        {{ t('archive.noPosts') }}
      </h3>
    </div>
  </div>
</template>

<script setup lang="ts">
import { Badge } from '~~/components/ui/badge'
import { Separator } from '~~/components/ui/separator'
import { useI18n } from 'vue-i18n'
import { CalendarDays, Eye, FolderOpen } from '@lucide/vue'

definePageMeta({ layout: 'default' })

const { t, locale } = useI18n()
const site = useSite()

// ===== SEO：基于 i18n + 站点设置 =====
const requestURL = useRequestURL()
const canonical = computed(() => requestURL.href)
useSeoMeta({
  title: () => String(t('archive.title') || '归档'),
  description: () => site.siteDescription.value,
  ogType: 'website',
  ogUrl: canonical,
  twitterCard: 'summary'
})
useHead({
  meta: [{ name: 'keywords', content: site.siteKeywords.value }],
  link: [{ rel: 'canonical', href: canonical }]
})

interface PostItem {
  id: number | string
  slug: string
  title?: string | Record<string, string>
  publishedAt?: string
  published_at?: string
  created_at?: string
  views?: number
  views_count?: number
  category?: { id: number | string, name?: string | Record<string, string>, slug: string }
}
interface ArchiveGroupItem {
  year: number
  month?: number
  count?: number
  posts?: PostItem[]
}

// ===== 真实接口：GET /api/blog/archive → [{year,month,count,posts:[...]}]
// 空数组作为 SSR/客户端统一兜底；绝不内置任何示例文章。
const { data: archiveData, pending: _pending } = await useAPI<ArchiveGroupItem[]>('/blog/archive', {
  query: { lang: locale.value, limit_per_month: 100 },
  key: 'archive:list:' + (locale.value || 'zh'),
  default: () => []
})

// 扁平化：后端返回已按年月分组，但需要兼容旧格式（单 posts 平铺）
const allPosts = computed<PostItem[]>(() => {
  const groups = (archiveData.value || []) as ArchiveGroupItem[]
  if (!Array.isArray(groups)) return []
  const result: PostItem[] = []
  for (const g of groups) {
    if (g && Array.isArray(g.posts)) {
      for (const p of g.posts) {
        // 归档接口里有 created_at；其他页面用 published_at / publishedAt
        const post = p as PostItem
        if (!post.publishedAt && !post.published_at && post.created_at) {
          post.published_at = post.created_at
        }
        result.push(post)
      }
    }
  }
  return result
})

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

const getPublishedAt = (post: PostItem): string =>
  post?.published_at || post?.publishedAt || post?.created_at || ''
const getPostTitle = (post: PostItem) => pickLocalized(post?.title)
const getCategoryName = (post: PostItem) => pickLocalized(post?.category?.name)
const getViews = (post: PostItem) => post?.views ?? post?.views_count ?? 0

const groupedByYear = computed(() => {
  const map = new Map<number, PostItem[]>()
  const sorted = [...allPosts.value].sort((a, b) => {
    const da = new Date(getPublishedAt(b)).getTime()
    const db = new Date(getPublishedAt(a)).getTime()
    return da - db
  })
  for (const post of sorted) {
    const t = new Date(getPublishedAt(post))
    const year = isNaN(t.getTime()) ? new Date().getFullYear() : t.getFullYear()
    if (!map.has(year)) map.set(year, [])
    map.get(year)!.push(post)
  }
  return Array.from(map.entries())
    .sort((a, b) => b[0] - a[0])
    .map(([year, posts]) => ({ year, posts }))
})

const formatMonthDay = (date: string) => {
  try {
    if (!date) return ''
    const d = new Date(date)
    if (isNaN(d.getTime())) return ''
    return d.toLocaleDateString(locale.value as string, {
      month: '2-digit',
      day: '2-digit'
    })
  } catch {
    return ''
  }
}
</script>
