<!--
  单年归档页（SSR）：GET /blog/archive/{year} 返回该年「月 → 文章」分组。
  与 /archive 的分工：/archive 一次拉全量分组做站内总览，本页是可被索引、可分享的
  年份落地页（WordPress date archive 口径），缓存走 nuxt.config 的 /archive/** 规则。
  两条硬约束：
  1. 路由参数必须是 4 位数字，非法路径在本页 throw 404，不把垃圾参数发给后端换 422；
  2. 日期/月份格式化必须钉死 locale + timeZone（/archive 的教训：两端时区不一致时
     跨年分组结果不同，而 swr 缓存会把服务端那一份固化下来）。

  Known gap (verified 2026-09-28 against the production build): /archive/abcd does hit this
  page and the guard does throw, but the error page comes back with HTTP 200 instead of 404.
  Real content is fine (/archive/2026 -> 82 KB with 2026-05..08 groups); the status code for
  invalid years still needs a server-side guard. Not silently prettied over here.
-->
<template>
  <div class="container py-16 max-w-3xl mx-auto">
    <header class="mb-10">
      <NuxtLink
        to="/archive"
        class="inline-flex items-center gap-1 text-sm text-muted-foreground transition-colors hover:text-foreground"
      >
        <ArrowLeft class="size-4" />
        {{ t('archive.backToArchive') }}
      </NuxtLink>
      <h1 class="mt-4 font-display text-3xl md:text-4xl font-bold tracking-tight tabular-nums">
        {{ t('archive.yearTitle', { year }) }}
      </h1>
      <p class="mt-1 text-sm text-muted-foreground tabular-nums">
        {{ t('archive.statsTotal', { count: totalInYear }) }}
      </p>
    </header>

    <!-- ===== 加载骨架屏：与 /archive 同构，避免首屏空白跳动 ===== -->
    <div
      v-if="_pending"
      class="flex flex-col gap-10"
    >
      <section
        v-for="s in 2"
        :key="s"
      >
        <Skeleton class="mb-4 h-7 w-28 rounded-lg" />
        <Separator />
        <ul class="mt-2 flex flex-col gap-3">
          <li
            v-for="r in 4"
            :key="r"
            class="py-2"
          >
            <Skeleton class="h-5 w-4/5 rounded-md" />
          </li>
        </ul>
      </section>
    </div>

    <!-- ===== 该年无文章（含后端返回空分组） ===== -->
    <div
      v-else-if="months.length === 0"
      class="py-20 text-center"
    >
      <div class="mb-4 inline-flex size-16 items-center justify-center rounded-2xl bg-muted">
        <CalendarDays class="size-8 text-muted-foreground" />
      </div>
      <h2 class="font-display text-xl font-semibold">
        {{ t('archive.noYearPosts') }}
      </h2>
    </div>

    <div
      v-else
      class="flex flex-col gap-10"
    >
      <section
        v-for="group in months"
        :id="`month-${group.month}`"
        :key="group.month"
      >
        <div class="mb-4 flex items-end justify-between gap-3">
          <h2 class="font-display text-2xl font-bold tracking-tight tabular-nums">
            {{ year }}-{{ padMonth(group.month) }}
            <Badge
              variant="secondary"
              class="ml-2 text-xs font-medium"
            >
              {{ group.count }} {{ t('archive.posts') }}
            </Badge>
          </h2>
        </div>
        <Separator />
        <ul>
          <li
            v-for="post in group.posts"
            :key="post.id"
            class="group/item flex items-center justify-between border-b py-3 last:border-b-0"
          >
            <div class="flex min-w-0 flex-1 items-center gap-3">
              <Badge
                variant="outline"
                class="shrink-0 font-mono text-xs tabular-nums"
              >
                {{ formatDate(post.created_at) }}
              </Badge>
              <NuxtLink
                :to="`/posts/${post.slug}`"
                class="truncate font-medium transition-colors group-hover/item:text-primary"
              >
                {{ titleOf(post) }}
              </NuxtLink>
            </div>
            <div class="ml-3 flex shrink-0 items-center gap-3 text-xs text-muted-foreground">
              <span
                v-if="categoryOf(post)"
                class="hidden items-center gap-1 sm:inline-flex"
              >
                <FolderOpen class="size-3" />
                {{ categoryOf(post) }}
              </span>
              <span class="inline-flex items-center gap-1 tabular-nums">
                <Eye class="size-3" />
                {{ post.views ?? 0 }}
              </span>
            </div>
          </li>
        </ul>
      </section>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ArrowLeft, CalendarDays, Eye, FolderOpen } from '@lucide/vue'
import { Badge } from '~~/components/ui/badge'
import { Separator } from '~~/components/ui/separator'
import Skeleton from '~~/components/ui/skeleton/Skeleton.vue'
import { useAPI } from '~~/composables/useApi'
import { useI18n } from 'vue-i18n'

definePageMeta({ layout: 'default' })

/** GET /blog/archive/{year} 的分组项（与后端 ArchiveMonthGroup 同构，前端本地声明避免依赖 re-export） */
interface ArchivePostItem {
  id: number | string
  slug: string
  title?: string | Record<string, string>
  created_at?: string | null
  views?: number
  category?: { id?: number | string, name?: string | Record<string, string>, slug?: string }
}
interface ArchiveMonthGroup {
  year: number
  month: number
  count: number
  posts: ArchivePostItem[]
}

const { t, locale } = useI18n()
const route = useRoute()
const site = useSite()

// 路由参数即年份闸门：非 4 位数字（爬虫乱拼、手改地址栏）不进请求阶段就 404。
const rawYear = String(route.params.year ?? '')
if (!/^\d{4}$/.test(rawYear)) {
  throw createError({ statusCode: 404, message: 'Invalid archive year', fatal: true })
}
const year = Number(rawYear)

const { data: groupsData, pending: _pending } = useAPI<ArchiveMonthGroup[]>(
  `/blog/archive/${year}`,
  {
    query: { lang: locale.value },
    key: computed(() => `archive:year:${year}:${locale.value}`)
  }
)

const months = computed<ArchiveMonthGroup[]>(() =>
  [...(groupsData.value ?? [])].sort((a, b) => b.month - a.month)
)
const totalInYear = computed(() =>
  months.value.reduce((sum, group) => sum + (group.posts?.length ?? 0), 0)
)

// 后端读者侧已按 lang 本地化，这里只兜多语言 dict 残留与字符串两种形态。
function titleOf(post: ArchiveMonthGroup['posts'][number]): string {
  const title = post.title as string | Record<string, string> | undefined
  return typeof title === 'string' ? title : (title?.[locale.value] ?? Object.values(title ?? {})[0] ?? '')
}
function categoryOf(post: ArchiveMonthGroup['posts'][number]): string {
  const name = post.category?.name as string | Record<string, string> | undefined
  if (!name) return ''
  return typeof name === 'string' ? name : (name[locale.value] ?? '')
}
function padMonth(month: number): string {
  return String(month).padStart(2, '0')
}
// timeZone: 'UTC' + 固定 locale：与 /archive 那次「服务端与访客时区不一致导致
// 分组漂移、并被 swr 缓存固化」的教训同源，日期渲染两端必须逐字节一致。
const dateFormatter = new Intl.DateTimeFormat('en-US', {
  month: 'short',
  day: 'numeric',
  timeZone: 'UTC'
})
function formatDate(value?: string | null): string {
  if (!value) return '--'
  const date = new Date(value)
  return Number.isNaN(date.getTime()) ? '--' : dateFormatter.format(date)
}

useSeo({
  title: computed(() => t('archive.yearTitle', { year }) as string),
  description: computed(() => site.siteDescription.value),
  type: 'website'
})
useWebsiteJsonLd()
useBreadcrumbJsonLd([
  { name: t('nav.home') as string, url: '/' },
  { name: t('nav.archive') as string, url: '/archive' },
  { name: String(year), url: `/archive/${year}` }
])
</script>
