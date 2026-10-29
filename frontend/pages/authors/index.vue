<!--
  作者目录页（/authors）：GET /users/authors（公开只读），按公开文章数倒序分页。

  nuxt.config 的 `/authors` 已有一条 swr 600 规则（与 `/authors/**` 同档），但此前没有
  这个页面文件——裸 `/authors` 会落进顶级 catchall `pages/[slug].vue`，被当成一个不存在的
  独立页判 404。这里补上真实落地页，规则才不是死的。

  三条口径：
  1. 取数用 useAPI（SSR 期取数），不是 $fetch + onMounted —— 否则首屏白屏、爬虫拿不到内容。
  2. 卡片链接与分页链接都走 localeHref / applyLocalePrefix：SSR 的 href 是爬虫唯一能看到的
     站内链接图，不挂语言前缀等于把权重全推给默认语言版本（AGENTS §2.3.3）。
  3. 隐私由服务端负责（关公开资料 / 关文章列表 / 停用账号的人根本不在响应里），页面不做
     二次过滤——前端再筛一遍等于有两份口径，迟早分叉。
-->
<template>
  <div class="container py-16">
    <header class="mb-12 text-center max-w-2xl mx-auto">
      <div class="inline-flex items-center justify-center size-14 rounded-2xl bg-primary/10 mb-5">
        <Users class="size-7 text-primary" />
      </div>
      <h1 class="font-display text-3xl md:text-4xl font-bold tracking-tight">
        {{ t('authors.directoryTitle', '作者目录') }}
      </h1>
      <p class="text-muted-foreground mt-3 leading-relaxed">
        {{ t('authors.directoryDesc', '按公开文章数排列，点进去看这位作者写过的全部文章。') }}
      </p>
    </header>

    <div
      v-if="loading"
      class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6"
    >
      <div
        v-for="i in 6"
        :key="i"
        class="h-44 rounded-2xl border border-border/60 bg-card p-6"
      >
        <div class="flex items-center gap-3 mb-4">
          <Skeleton class="size-14 rounded-full" />
          <div class="flex flex-col gap-2 flex-1">
            <Skeleton class="h-4 w-1/2 rounded-full" />
            <Skeleton class="h-3 w-1/3 rounded-full" />
          </div>
        </div>
        <div class="flex flex-col gap-2">
          <Skeleton class="h-4 w-full rounded-full" />
          <Skeleton class="h-4 w-4/5 rounded-full" />
        </div>
      </div>
    </div>

    <div
      v-else-if="loadError"
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

    <template v-else-if="authors.length > 0">
      <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        <NuxtLink
          v-for="a in authors"
          :key="a.id"
          :to="localeHref(`/authors/${a.username}`)"
          class="block rounded-2xl focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2"
        >
          <Card class="h-full group transition-all hover:shadow-soft hover:-translate-y-0.5 duration-300">
            <CardHeader class="p-6 pb-4">
              <div class="flex items-start justify-between gap-3">
                <div class="flex min-w-0 items-center gap-3">
                  <UserAvatar
                    :resolved-avatar-url="a.resolved_avatar_url"
                    :avatar="a.avatar || null"
                    :seed="a.username"
                    :name="authorName(a)"
                    :title="a.title ?? null"
                    :size="56"
                    :show-title="false"
                  />
                  <div class="min-w-0">
                    <CardTitle class="font-display text-lg tracking-tight truncate group-hover:underline underline-offset-4">
                      {{ authorName(a) }}
                    </CardTitle>
                    <div
                      v-if="a.title"
                      class="mt-1.5"
                    >
                      <TitleBadge
                        :title="a.title"
                        size="sm"
                      />
                    </div>
                  </div>
                </div>
                <Badge variant="secondary">
                  {{ a.post_count }} {{ t('authors.posts', '篇文章') }}
                </Badge>
              </div>
              <CardDescription
                v-if="a.bio"
                class="mt-3 line-clamp-2 leading-relaxed min-h-[3rem]"
              >
                {{ a.bio }}
              </CardDescription>
            </CardHeader>
            <CardFooter class="p-6 pt-0 mt-2 flex items-center justify-between text-xs text-muted-foreground border-t">
              <span>
                {{ t('authors.recent', '最近更新') }}
                <template v-if="recentLabel(a)">
                  · {{ recentLabel(a) }}
                </template>
              </span>
              <ArrowRight class="size-4 transition-transform duration-300 group-hover:translate-x-1" />
            </CardFooter>
          </Card>
        </NuxtLink>
      </div>
    </template>

    <div
      v-else
      class="text-center py-20"
    >
      <div class="inline-flex items-center justify-center size-16 rounded-2xl bg-muted mb-4">
        <Users class="size-8 text-muted-foreground" />
      </div>
      <h3 class="font-display text-xl font-semibold">
        {{ t('authors.directoryEmpty', '还没有作者发布公开文章。') }}
      </h3>
    </div>

    <div
      v-if="totalPages > 1"
      class="mt-12 flex justify-center"
    >
      <nav
        class="flex items-center gap-2"
        role="navigation"
        :aria-label="t('common.pagination', '分页导航')"
      >
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
          :class="buttonVariants({ variant: 'outline', size: 'icon' })"
          :aria-label="t('common.prevPage', '上一页')"
        >
          <ChevronLeft data-icon="inline-start" />
        </a>

        <template
          v-for="p in visiblePages"
          :key="p"
        >
          <span
            v-if="p === currentPage"
            :class="buttonVariants({ variant: 'default', size: 'icon' })"
            aria-current="page"
          >{{ p }}</span>
          <a
            v-else
            :href="pageHref(p)"
            :class="buttonVariants({ variant: 'ghost', size: 'icon' })"
          >{{ p }}</a>
        </template>

        <template v-if="currentPage >= totalPages">
          <Button
            variant="outline"
            size="icon"
            disabled
            :aria-label="t('common.nextPage', '下一页')"
          >
            <ChevronRight data-icon="inline-end" />
          </Button>
        </template>
        <a
          v-else
          :href="pageHref(currentPage + 1)"
          :class="buttonVariants({ variant: 'outline', size: 'icon' })"
          :aria-label="t('common.nextPage', '下一页')"
        >
          <ChevronRight data-icon="inline-end" />
        </a>
      </nav>
    </div>
  </div>
</template>

<script setup lang="ts">
import { Card, CardDescription, CardFooter, CardHeader, CardTitle } from '~~/components/ui/card'
import { Badge } from '~~/components/ui/badge'
import { Button, buttonVariants } from '~~/components/ui/button'
import { Skeleton } from '~~/components/ui/skeleton'
import UserAvatar from '~~/components/UserAvatar.vue'
import TitleBadge from '~~/components/TitleBadge.vue'
import type { AdminUserTitle } from '~~/composables/useAdminManage'
import { ArrowRight, ChevronLeft, ChevronRight, RefreshCw, Users } from '@lucide/vue'
import { applyLocalePrefix } from '~~/composables/useSeo'
import { useAPI } from '~~/composables/useApi'
import { pageWindow } from '~~/lib/pagination'
import { useI18n } from 'vue-i18n'
import { computed } from 'vue'

definePageMeta({ layout: 'default' })

const { t, locale } = useI18n()
const route = useRoute()
const { localeHref } = useLocaleLink()

interface AuthorCard {
  id: number
  username: string
  nickname?: string | null
  avatar?: string | null
  resolved_avatar_url?: string | null
  title?: AdminUserTitle | null
  bio?: string | null
  post_count?: number
  last_published_at?: string | null
}

// 每页 12：3 列网格 × 4 行。目录不是文章流，条数跟博客「阅读体验」分组无关。
const PAGE_SIZE = 12

// ===== SEO：标题/描述走 i18n，canonical 由 useSeo 按路由派生（查询串白名单只有 page）=====
useSeo({
  title: computed(() => String(t('authors.directoryTitle', '作者目录'))),
  description: computed(() => String(t('authors.directoryDesc', '按公开文章数排列。'))),
  type: 'website'
})
useWebsiteJsonLd()
useBreadcrumbJsonLd([
  { name: t('nav.home') as string, url: '/' },
  { name: t('authors.directoryTitle', '作者目录') as string, url: '/authors' }
])

// 页码从 URL 读：分享链接 / 刷新 / 后退都能还原；非法值一律当第 1 页
const currentPage = computed(() => Math.max(1, Number(route.query.page) || 1))

const { data, pending, error: loadError, refresh } = useAPI<{
  items?: AuthorCard[]
  total?: number
  total_pages?: number
}>('/users/authors', {
  query: computed(() => ({ page: currentPage.value, page_size: PAGE_SIZE })),
  // 翻页是页内状态（不重挂载），key 带页码让 Nuxt 自动重取；不手写 watch+refresh
  key: computed(() => `authors:directory:${currentPage.value}`)
})

const authors = computed<AuthorCard[]>(() =>
  Array.isArray(data.value?.items) ? data.value!.items! : []
)
const total = computed(() => data.value?.total ?? 0)
const totalPages = computed(() => Math.max(1, Math.ceil(total.value / PAGE_SIZE)))
const loading = computed(() => pending.value && authors.value.length === 0)
const visiblePages = computed(() => pageWindow(currentPage.value, totalPages.value))

const authorName = (a: AuthorCard) => a.nickname?.trim() || a.username

/** 只取 UTC 年月日：Intl/toLocaleString 依赖运行端 ICU，两端不同就是 hydration 文本差异。 */
function recentLabel(a: AuthorCard): string {
  const raw = a.last_published_at
  if (!raw) return ''
  const d = new Date(raw)
  if (Number.isNaN(d.getTime())) return ''
  const mm = String(d.getUTCMonth() + 1).padStart(2, '0')
  const dd = String(d.getUTCDate()).padStart(2, '0')
  return `${d.getUTCFullYear()}-${mm}-${dd}`
}

const pageHref = (page: number) =>
  `${applyLocalePrefix('/authors', locale.value)}?page=${page}`

// 越界页码（?page=9999）对爬虫必须 301 回裸目录页：留 200 会被判 soft 404。
// 时点与 useContentStatus 同轨（app:rendered：数据已落值、状态码还改得动）；
// 响应头必须 no-store，否则 301 会被本页 swr 缓存进旧目标。
if (import.meta.server) {
  const ssrEvent = useRequestEvent()
  useNuxtApp().hooks.hookOnce('app:rendered', () => {
    if (
      ssrEvent
      && total.value > 0
      && currentPage.value > totalPages.value
    ) {
      ssrEvent.node.res.statusCode = 301
      ssrEvent.node.res.setHeader('location', applyLocalePrefix('/authors', locale.value))
      ssrEvent.node.res.setHeader('cache-control', 'no-store')
    }
  })
}
</script>
