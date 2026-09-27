<!--
  单月归档页 /archive/<year>/<month>（SSR）：GET /blog/archive/{year}/{month} 的分页落地页。
  与上两级归档的分工：/archive 是全量总览、/archive/<year> 是年份落地页，本页补上 WordPress
  date archive 的最细一级（月），后端端点自上线起一直是"后端就绪、前端零消费"的死路由。
  四条硬约束：
  1. 参数闸门在 middleware/archive-year.ts（页面内 throw createError 仍是 HTTP 200，
     配合 /archive/** 的 swr 会把 200 空壳缓存成可复用页面——见该中间件注释）；
  2. 目录式父子：本页与同级 pages/archive/[year]/index.vue 并存，若把父页写成
     pages/archive/[year].vue，子路由会静默渲染父组件（父页没有 NuxtPage outlet）；
  3. 日期格式化钉死 locale + timeZone：两端时区不一致时分组结果不同，swr 会固化服务端那一份；
  4. 空月份走真 404（复用 composables/useContentStatus），WordPress 的 no-such-date 口径。
-->
<template>
  <div class="container py-16 max-w-3xl mx-auto">
    <header class="mb-10">
      <NuxtLink
        :to="`/archive/${year}`"
        class="inline-flex items-center gap-1 text-sm text-muted-foreground transition-colors hover:text-foreground"
      >
        <ArrowLeft class="size-4" />
        {{ t('archive.year', { year }) }}
      </NuxtLink>
      <h1 class="mt-4 font-display text-3xl md:text-4xl font-bold tracking-tight tabular-nums">
        {{ year }}-{{ padMonth(month) }}
      </h1>
      <p class="mt-1 text-sm text-muted-foreground tabular-nums">
        {{ t('archive.statsTotal', { count: total }) }}
      </p>
    </header>

    <!-- ===== 加载骨架屏：与 /archive、/archive/<year> 同构 ===== -->
    <div
      v-if="pending"
      class="flex flex-col gap-3"
    >
      <Separator />
      <div
        v-for="r in 6"
        :key="r"
        class="py-2"
      >
        <Skeleton class="h-5 w-4/5 rounded-md" />
      </div>
    </div>

    <!-- ===== 该月无文章（正常路径已由中间件+useContentStatus 判 404） ===== -->
    <div
      v-else-if="posts.length === 0"
      class="py-20 text-center"
    >
      <div class="mb-4 inline-flex size-16 items-center justify-center rounded-2xl bg-muted">
        <CalendarDays class="size-8 text-muted-foreground" />
      </div>
      <h2 class="font-display text-xl font-semibold">
        {{ t('archive.noPosts') }}
      </h2>
    </div>

    <div v-else>
      <Separator />
      <ul class="flex flex-col gap-3">
        <li
          v-for="post in posts"
          :key="post.id"
          class="flex flex-wrap items-baseline justify-between gap-x-4 gap-y-1 py-2"
        >
          <NuxtLink
            :to="`/posts/${post.slug}`"
            class="text-base transition-colors hover:text-primary"
          >
            {{ titleOf(post) }}
          </NuxtLink>
          <span class="flex items-center gap-3 text-sm text-muted-foreground tabular-nums">
            <span>{{ formatDate(post.published_at || post.created_at) }}</span>
            <span
              v-if="categoryOf(post)"
              class="hidden sm:inline"
            >{{ categoryOf(post) }}</span>
            <span class="inline-flex items-center gap-1">
              <Eye class="size-3.5" />
              {{ post.views ?? 0 }}
            </span>
          </span>
        </li>
      </ul>

      <!-- ===== 分页：后端按 page/page_size 返回 total_pages，越界页由 useContentStatus 判 404 ===== -->
      <nav
        v-if="totalPages > 1"
        class="mt-10 flex items-center justify-between gap-3"
        :aria-label="t('archive.posts')"
      >
        <NuxtLink
          v-if="page > 1"
          :to="pageLink(page - 1)"
          class="inline-flex items-center gap-1 text-sm transition-colors hover:text-primary"
          :aria-label="`${t('archive.posts')} ${page - 1}`"
        >
          ←
        </NuxtLink>
        <span class="text-sm text-muted-foreground tabular-nums">
          {{ page }} / {{ totalPages }}
        </span>
        <NuxtLink
          v-if="page < totalPages"
          :to="pageLink(page + 1)"
          class="inline-flex items-center gap-1 text-sm transition-colors hover:text-primary"
          :aria-label="`${t('archive.posts')} ${page + 1}`"
        >
          →
        </NuxtLink>
      </nav>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ArrowLeft, CalendarDays, Eye } from '@lucide/vue'
import { Separator } from '~~/components/ui/separator'
import Skeleton from '~~/components/ui/skeleton/Skeleton.vue'
import { useAPI } from '~~/composables/useApi'
import { useContentStatus } from '~~/composables/useContentStatus'
import { useI18n } from 'vue-i18n'

/** GET /blog/archive/{year}/{month} 的响应（与后端 ArchiveMonthPage 同构） */
interface ArchivePostItem {
  id: number | string
  slug: string
  title?: string | Record<string, string>
  created_at?: string | null
  published_at?: string | null
  views?: number
  category?: { name?: string | Record<string, string> }
}
interface ArchiveMonthPage {
  year: number
  month: number
  count: number
  page: number
  page_size: number
  total_pages: number
  posts: ArchivePostItem[]
}

definePageMeta({ layout: 'default', middleware: 'archive-year' })

const { t, locale } = useI18n()
const route = useRoute()

// 参数合法性（年份 4 位 + 月份 1-12）已由中间件闸门保证，走到这里一定是规范化后的值。
const year = Number(route.params.year)
const month = Number(route.params.month)
const page = computed(() => {
  const raw = Number(route.query.page ?? 1)
  return Number.isFinite(raw) && raw >= 1 ? Math.floor(raw) : 1
})

const { data, pending, error } = useAPI<ArchiveMonthPage>(
  `/blog/archive/${year}/${month}`,
  {
    query: computed(() => ({ lang: locale.value, page: page.value, page_size: 20 })),
    key: computed(() => `archive:month:${year}:${month}:${locale.value}:${page.value}`)
  }
)

const posts = computed<ArchivePostItem[]>(() => data.value?.posts ?? [])
const total = computed(() => data.value?.count ?? 0)
const totalPages = computed(() => data.value?.total_pages ?? 0)

// 服务端已按 lang 本地化，这里只兜 dict 残留与字符串两种形态。
function titleOf(post: ArchivePostItem): string {
  const title = post.title as string | Record<string, string> | undefined
  return typeof title === 'string' ? title : (title?.[locale.value] ?? Object.values(title ?? {})[0] ?? '')
}
function categoryOf(post: ArchivePostItem): string {
  const name = post.category?.name as string | Record<string, string> | undefined
  if (!name) return ''
  return typeof name === 'string' ? name : (name[locale.value] ?? '')
}
function padMonth(value: number): string {
  return String(value).padStart(2, '0')
}
function pageLink(target: number): string {
  return `/archive/${year}/${padMonth(month)}${target > 1 ? `?page=${target}` : ''}`
}

const formatter = new Intl.DateTimeFormat(locale.value, {
  year: 'numeric',
  month: 'short',
  day: 'numeric',
  timeZone: 'UTC'
})
function formatDate(value?: string | null): string {
  if (!value) return ''
  const date = new Date(value)
  return Number.isNaN(date.getTime()) ? '' : formatter.format(date)
}

// 空月份 / 越界页 = 真 404（不改网络故障与 5xx 的状态码，判据见 useContentStatus）。
useContentStatus(
  error,
  computed(() => posts.value.length === 0 || page.value > (totalPages.value || 1))
)

useHead(() => ({ title: `${year}-${padMonth(month)} · ${t('archive.title')}` }))
</script>
