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
    <!-- 该月没有文章（或页码越界）时只给一块面板：此前 h1「2026-07」与「共 0 篇文章」
         照常渲染，404 响应里读到的是一份"确实存在的空月份页"。判定沿用 monthNotFound
         （网络故障不算缺失，仍走下面的加载失败分支）。 -->
    <template v-if="monthNotFound">
      <div class="rounded-2xl border border-dashed border-border/70 bg-card/40 px-6 py-12 text-center">
        <div class="mb-4 inline-flex size-16 items-center justify-center rounded-2xl bg-muted">
          <CalendarDays class="size-8 text-muted-foreground" />
        </div>
        <h1 class="font-display text-xl font-semibold">
          {{ t('error.notFoundTitle') }}
        </h1>
        <p class="mt-2 text-sm text-muted-foreground">
          {{ t('error.notFoundDesc') }}
        </p>
        <div class="mt-6 flex flex-wrap items-center justify-center gap-3">
          <Button as-child>
            <NuxtLink :to="localeHref(`/archive/${year}`)">
              {{ t('archive.year', { year }) }}
            </NuxtLink>
          </Button>
          <Button
            variant="outline"
            as-child
          >
            <NuxtLink :to="localeHref('/')">
              {{ t('error.backHome') }}
            </NuxtLink>
          </Button>
        </div>
      </div>
    </template>

    <template v-else>
      <header class="mb-10">
        <NuxtLink
          :to="localeHref(`/archive/${year}`)"
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

      <!-- ===== 请求失败：网络故障 / 5xx 不能说成"该月没有文章" ===== -->
      <div
        v-else-if="error"
        class="rounded-xl border border-destructive/30 bg-destructive/5 p-6 text-sm text-destructive"
      >
        <div class="flex flex-col items-center gap-3 text-center">
          <span>{{ t('error.serverErrorDesc') }}</span>
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

      <div v-else>
        <Separator />
        <ul class="flex flex-col gap-3">
          <li
            v-for="post in posts"
            :key="post.id"
            class="flex flex-wrap items-baseline justify-between gap-x-4 gap-y-1 py-2"
          >
            <NuxtLink
              :to="localeHref(`/posts/${post.slug}`)"
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
            :to="localeHref(pageLink(page - 1))"
            class="inline-flex items-center gap-1 text-sm transition-colors hover:text-primary"
            :aria-label="`${t('archive.prevPage')} ${t('archive.posts')} ${page - 1}`"
          >
            <ChevronLeft class="size-4" />
            {{ t('archive.prevPage') }}
          </NuxtLink>
          <span class="text-sm text-muted-foreground tabular-nums">
            {{ page }} / {{ totalPages }}
          </span>
          <NuxtLink
            v-if="page < totalPages"
            :to="localeHref(pageLink(page + 1))"
            class="inline-flex items-center gap-1 text-sm transition-colors hover:text-primary"
            :aria-label="`${t('archive.nextPage')} ${t('archive.posts')} ${page + 1}`"
          >
            {{ t('archive.nextPage') }}
            <ChevronRight class="size-4" />
          </NuxtLink>
        </nav>
      </div>
    </template>
  </div>
</template>

<script setup lang="ts">
import { ArrowLeft, CalendarDays, ChevronLeft, ChevronRight, Eye, RefreshCw } from '@lucide/vue'
import { Button } from '~~/components/ui/button'
import { Separator } from '~~/components/ui/separator'
import Skeleton from '~~/components/ui/skeleton/Skeleton.vue'
import { useAPI } from '~~/composables/useApi'
import { isContentMissing, useContentStatus } from '~~/composables/useContentStatus'
import { toBcp47Locale } from '~~/composables/useSeo'
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
const { localeHref } = useLocaleLink()

// 参数合法性（年份 4 位 + 月份 1-12）已由中间件闸门保证，走到这里一定是规范化后的值。
const year = Number(route.params.year)
const month = Number(route.params.month)
const page = computed(() => {
  const raw = Number(route.query.page ?? 1)
  return Number.isFinite(raw) && raw >= 1 ? Math.floor(raw) : 1
})

const { data, pending, error, refresh } = useAPI<ArchiveMonthPage>(
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
  return pickLocalizedText(post.title, locale.value as string)
}
function categoryOf(post: ArchivePostItem): string {
  return pickLocalizedText(post.category?.name, locale.value as string)
}
function padMonth(value: number): string {
  return String(value).padStart(2, '0')
}
function pageLink(target: number): string {
  return `/archive/${year}/${padMonth(month)}${target > 1 ? `?page=${target}` : ''}`
}

// 必须先转 BCP-47：i18n 的 `zh_Hant` 不是合法标签，直接喂 Intl 会抛 RangeError，
// 而这段跑在 setup 里 → 整个 /zh_Hant/archive/<年>/<月> 渲染成 200 空壳。
const formatter = new Intl.DateTimeFormat(toBcp47Locale(locale.value), {
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
const monthMissing = computed(
  () => posts.value.length === 0 || page.value > (totalPages.value || 1)
)
useContentStatus(error, monthMissing)
// 状态码 / 标题 / robots / canonical / 兜底面板五处信号共用这一条判定。
// 加载中不算缺失：pending 时 posts 还是空的，直接判会把每个真实月份先渲染成 404 面板。
const monthNotFound = computed(
  () => !pending.value && isContentMissing(error.value, monthMissing.value)
)

// SEO 单源走 useSeo：本页曾只有一个裸 useHead title，四语版本既没有 canonical
// 也没有 hreflang，爬虫把它们当成三个互不相关的归档页。
// 缺失分支必须换标题：404 响应配一个"看起来正常"的归档标题，等于给搜索引擎
// 两份互相矛盾的信号（余下内容详情页都是这个口径）。
useSeo({
  title: computed(() =>
    monthNotFound.value
      ? (t('error.notFoundTitle') as string)
      : `${year}-${padMonth(month)} ${t('archive.title')}`
  ),
  description: computed(() => t('archive.statsTotal', { count: total.value }) as string),
  // 状态码 / 标题 / robots / canonical 同源判定（与上面的标题同一口径）
  noindex: monthNotFound,
  type: 'website'
})
useWebsiteJsonLd()
useBreadcrumbJsonLd([
  { name: t('nav.home') as string, url: '/' },
  { name: t('nav.archive') as string, url: '/archive' },
  { name: String(year), url: `/archive/${year}` },
  { name: `${year}-${padMonth(month)}`, url: `/archive/${year}/${padMonth(month)}` }
])
</script>
