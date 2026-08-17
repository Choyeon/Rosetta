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
      <section v-for="group in groupedByYear" :key="group.year" class="scroll-mt-24">
        <div class="flex items-end justify-between mb-4">
          <h2 class="font-display text-2xl font-bold tracking-tight flex items-center gap-3">
            {{ group.year }}
            <Badge variant="secondary" class="text-xs font-medium">
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
              <Badge variant="outline" class="shrink-0 font-mono text-xs tabular-nums">
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
              <span v-if="getCategoryName(post)" class="hidden sm:inline-flex items-center gap-1">
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

    <div v-if="groupedByYear.length === 0" class="text-center py-20">
      <div class="inline-flex items-center justify-center size-16 rounded-2xl bg-muted mb-4">
        <CalendarDays class="size-8 text-muted-foreground" />
      </div>
      <h3 class="font-display text-xl font-semibold">{{ t('archive.noPosts') }}</h3>
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

interface PostItem {
  id: number | string
  slug: string
  title: string
  publishedAt: string
  views?: number
  category?: { id: number | string; name: string; slug: string }
}

const allPosts = ref<PostItem[]>([
  {
    id: 1,
    slug: 'post-1',
    title: '探索 Vue 3 组合式 API 的优雅设计模式',
    publishedAt: '2025-12-15T08:00:00Z',
    views: 2341,
    category: { id: 1, name: '前端开发', slug: 'frontend' }
  },
  {
    id: 2,
    slug: 'post-2',
    title: '构建高性能 Nuxt 应用的 10 个技巧',
    publishedAt: '2025-12-10T08:00:00Z',
    views: 1823,
    category: { id: 1, name: '前端开发', slug: 'frontend' }
  },
  {
    id: 3,
    slug: 'post-3',
    title: '现代 CSS 布局完全指南：从 Flex 到 Grid',
    publishedAt: '2025-11-28T08:00:00Z',
    views: 1567,
    category: { id: 3, name: 'CSS', slug: 'css' }
  },
  {
    id: 4,
    slug: 'post-4',
    title: 'TypeScript 类型体操进阶：条件类型与映射类型',
    publishedAt: '2025-11-15T08:00:00Z',
    views: 1289,
    category: { id: 4, name: 'TypeScript', slug: 'typescript' }
  },
  {
    id: 5,
    slug: 'post-5',
    title: 'Docker 容器化部署最佳实践',
    publishedAt: '2025-10-22T08:00:00Z',
    views: 987,
    category: { id: 6, name: '运维', slug: 'devops' }
  },
  {
    id: 6,
    slug: 'post-6',
    title: '微服务架构中的服务发现与负载均衡',
    publishedAt: '2025-10-08T08:00:00Z',
    views: 756,
    category: { id: 5, name: '架构', slug: 'architecture' }
  },
  {
    id: 7,
    slug: 'post-7',
    title: 'Tailwind CSS 自定义主题系统实战',
    publishedAt: '2025-09-20T08:00:00Z',
    views: 634,
    category: { id: 3, name: 'CSS', slug: 'css' }
  },
  {
    id: 8,
    slug: 'post-8',
    title: '状态管理新纪元：Pinia vs Vuex 深度对比',
    publishedAt: '2025-08-15T08:00:00Z',
    views: 512,
    category: { id: 5, name: '架构', slug: 'architecture' }
  },
  {
    id: 9,
    slug: 'post-9',
    title: 'Node.js 性能调优：从事件循环到内存管理',
    publishedAt: '2025-07-05T08:00:00Z',
    views: 428,
    category: { id: 2, name: '后端开发', slug: 'backend' }
  }
])

const pickLocalized = (val: any): string => {
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

const getPublishedAt = (post: any) =>
  post?.published_at || post?.publishedAt || post?.created_at || ''
const getPostTitle = (post: any) => pickLocalized(post?.title)
const getCategoryName = (post: any) => pickLocalized(post?.category?.name)
const getViews = (post: any) => post?.views ?? post?.views_count ?? 0

const groupedByYear = computed(() => {
  const map = new Map<number, any[]>()
  const sorted = [...allPosts.value].sort((a: any, b: any) => {
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
