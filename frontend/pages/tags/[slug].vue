<!--
  标签详情页：GET /blog/tags/slug/<slug> + GET /blog/posts?tag=<slug>，任一失败即整体进错误态。
  与 categories/[slug] 同一形态：详情 URL 与 lang 都是 setup 期快照，翻页只在客户端 refresh。
  分页只认列表响应的 total —— 详情里的 post_count 仅用于头部展示，不参与算页数，两者不一致时
  以 total 为准。
-->
<template>
  <div class="container py-16">
    <!-- 头部整块只在标签存在时渲染：不存在态下 tagName 回落成「页面不存在」，
         留着它就会与下面面板的 h1 并排成两个同名标题（线上 h1 数 = 2）。 -->
    <header
      v-if="!tagNotFound"
      class="mb-12"
    >
      <div class="inline-flex items-center gap-2 text-xs uppercase tracking-[0.16em] text-muted-foreground mb-3">
        <span class="size-1.5 rounded-full bg-cyan-500" />
        <NuxtLink
          :to="localeHref('/tags')"
          class="hover:text-foreground transition-colors"
        >{{ t('tags.title', '标签') }}</NuxtLink>
        <span>/</span>
      </div>
      <div class="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 class="font-display text-3xl md:text-4xl font-bold tracking-tight inline-flex items-center gap-3">
            <!-- 标题只出一份：徽章本身就是标题（胶囊里已经写着标签名）。
                 此前徽章与一个同名 span 并排，线上 h1 读出来是「Python Python」。 -->
            <TagBadge
              v-if="!tagNotFound"
              :color="tagColor"
              :label="tagName"
              size="md"
              show-icon
            />
            <span v-else>{{ tagName }}</span>
          </h1>
          <p
            v-if="tagDesc"
            class="text-muted-foreground mt-3 leading-relaxed max-w-2xl"
          >
            {{ tagDesc }}
          </p>
        </div>
        <div
          v-if="!tagNotFound"
          class="inline-flex items-center gap-2 text-sm text-muted-foreground"
        >
          <span class="inline-flex items-center justify-center px-3 py-1 rounded-full bg-muted tabular-nums">
            {{ postCount }} {{ t('tags.posts', '篇文章') }}
          </span>
        </div>
      </div>
    </header>

    <template v-if="pending && posts.length === 0">
      <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        <PostSkeleton
          v-for="i in 6"
          :key="i"
        />
      </div>
    </template>
    <!-- 标签不存在时只给一块面板：此前它会落进 loadError 分支（列表请求对不存在的标签
         照样成功、只是空，缺的是详情），访客看到的是「文章列表加载失败」——把一个
         不存在的 URL 说成临时故障。判据复用 tagNotFound（网络故障不算缺失，仍走下面的
         loadError，见 composables/useContentStatus.ts）。 -->
    <template v-else-if="tagNotFound">
      <div class="rounded-2xl border border-dashed border-border/70 bg-card/40 px-6 py-12 text-center">
        <div class="inline-flex items-center justify-center size-16 rounded-2xl bg-muted mb-4">
          <Tags class="size-8 text-muted-foreground" />
        </div>
        <h1 class="font-display text-xl font-semibold">
          {{ t('error.notFoundTitle') }}
        </h1>
        <p class="mt-2 text-sm text-muted-foreground">
          {{ t('error.notFoundDesc') }}
        </p>
        <div class="mt-6 flex flex-wrap items-center justify-center gap-3">
          <Button as-child>
            <NuxtLink :to="localeHref('/tags')">
              {{ t('tags.title') }}
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
    <template v-else-if="loadError">
      <div class="rounded-xl border border-destructive/30 bg-destructive/5 p-6 text-sm text-destructive">
        {{ t('error.loadFailed') }}
      </div>
    </template>
    <template v-else-if="posts.length > 0">
      <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        <PostCard
          v-for="p in posts"
          :key="p.id"
          :post="p"
        />
      </div>
    </template>
    <template v-else>
      <div class="text-center py-20">
        <div class="inline-flex items-center justify-center size-16 rounded-2xl bg-muted mb-4">
          <Tags class="size-8 text-muted-foreground" />
        </div>
        <h3 class="font-display text-xl font-semibold">
          {{ t('posts.noPosts', '这里还没有文章') }}
        </h3>
        <p class="text-muted-foreground mt-1">
          {{ t('posts.noPostsDesc', '作者正在努力创作，敬请期待。') }}
        </p>
      </div>
    </template>

    <div
      v-if="totalPages > 1"
      class="flex justify-center mt-12"
    >
      <!-- 与 /posts 同口径：分页必须是真实 <a href> 且当前页进 URL。纯 button + click
           等于第 2 页起的所有文章零入链，分享/刷新/后退也还原不出页码。 -->
      <nav
        class="flex items-center gap-2"
        role="navigation"
        aria-label="pagination"
      >
        <template v-if="currentPage <= 1">
          <Button
            variant="outline"
            size="icon"
            :aria-label="t('common.prevPage')"
            disabled
          >
            <ChevronLeft data-icon="inline-start" />
          </Button>
        </template>
        <a
          v-else
          :href="pageHref(currentPage - 1)"
          :aria-label="t('common.prevPage')"
          :class="pageLinkClass('outline')"
          @click.prevent="goToPage(currentPage - 1)"
        >
          <ChevronLeft data-icon="inline-start" />
        </a>
        <template
          v-for="p in visiblePages"
          :key="p"
        >
          <span
            v-if="p === currentPage"
            aria-current="page"
            :class="pageLinkClass('default')"
          >{{ p }}</span>
          <a
            v-else
            :href="pageHref(p)"
            :class="pageLinkClass('ghost')"
            @click.prevent="goToPage(p)"
          >{{ p }}</a>
        </template>
        <template v-if="currentPage >= totalPages">
          <Button
            variant="outline"
            size="icon"
            :aria-label="t('common.nextPage')"
            disabled
          >
            <ChevronRight data-icon="inline-start" />
          </Button>
        </template>
        <a
          v-else
          :href="pageHref(currentPage + 1)"
          :aria-label="t('common.nextPage')"
          :class="pageLinkClass('outline')"
          @click.prevent="goToPage(currentPage + 1)"
        >
          <ChevronRight data-icon="inline-start" />
        </a>
      </nav>
    </div>
  </div>
</template>

<script setup lang="ts">
import { useAPI } from '~~/composables/useApi'
import { isContentMissing, useContentStatus } from '~~/composables/useContentStatus'
import PostCard from '~~/components/PostCard.vue'
import TagBadge from '~~/components/TagBadge.vue'
import PostSkeleton from '~~/components/PostSkeleton.vue'
import { Button, buttonVariants } from '~~/components/ui/button'
import { pageWindow } from '~~/lib/pagination'
import { ChevronLeft, ChevronRight, Tags } from '@lucide/vue'
import { useI18n } from 'vue-i18n'

definePageMeta({ layout: 'default' })

const { t, locale } = useI18n()
const route = useRoute()
const { localeHref } = useLocaleLink()

const slug = computed(() => typeof route.params.slug === 'string' ? route.params.slug : '')
const currentPage = ref(Math.max(1, Number(route.query.page) || 1))
const site = useSite()
// 每页条数取后台「阅读体验」分组；未配置时沿用 9
const pageSize = computed(() => site.reading.value.posts_per_page)

const pickLocalized = (val: unknown): string => pickLocalizedText(val, locale.value)

interface TagDetail { id?: number | string, slug?: string, name?: unknown, description?: unknown, color?: string | null, post_count?: number, postsCount?: number, posts?: unknown[] }

interface TagPostRow {
  id: number | string
  slug: string
  title: string | Record<string, string>
  excerpt?: string | Record<string, string>
  cover_image?: string
  coverImage?: string
  category?: { id: number | string, name: string | Record<string, string>, slug: string, color?: string | null }
  tags?: Array<{ id: number | string, name: string | Record<string, string>, slug: string, color?: string | null }>
  author?: { id: number | string, name?: string, nickname?: string, username?: string, avatar?: string }
  created_at?: string
  published_at?: string
  publishedAt?: string
  updated_at?: string
  views?: number
  views_count?: number
  comments_count?: number
  commentsCount?: number
  likes_count?: number
  likesCount?: number
  is_pinned?: boolean
  [key: string]: unknown
}
// 静态键+静态查询：切语言/换标签 slug 都走「跳同页 URL → 重挂载 → 新参数重新请求」，
// 不手写 watch+refresh()（与 Nuxt key watcher 双发，第一发必被 abort）。
const { data: tagRaw, error: tagErr, status: tagStatus } = useAPI<TagDetail>(`/blog/tags/slug/${slug.value}`, {
  query: { lang: locale.value },
  key: `tag:detail:${slug.value}:${locale.value}`,
  default: () => ({} as TagDetail)
})

// query/key 都是 computed：翻页是页内状态（不重挂载），靠 Nuxt params/key watcher
// 自动重取；不再叠加手写 watch(refresh)（同一 URL 双发，第一发还被 abort）。
const { data: postsRaw, pending, error: postsErr } = useAPI<{ items?: TagPostRow[], total?: number }>('/blog/posts', {
  query: computed(() => ({
    lang: locale.value,
    page: currentPage.value,
    page_size: pageSize.value,
    tag: slug.value || undefined
  })),
  key: computed(() => `tag:posts:${slug.value}:${locale.value}:${currentPage.value}`)
})

// 同 categories：加载中留空，取不到标签时用 404 口径标题而不是人性化 slug。
// 详情请求还没落值时不判缺失，否则每个真实标签都会在加载期先闪一次"不存在"。
const tagDetailSettled = computed(() => tagStatus.value === 'success' || tagStatus.value === 'error')
const tagName = computed(() => pickLocalized(tagRaw.value?.name) || (tagDetailSettled.value ? t('error.notFoundTitle') : ''))
const tagColor = computed<string | null>(() => (tagRaw.value?.color ?? null) as string | null)
const tagDesc = computed(() => pickLocalized(tagRaw.value?.description))
const postCount = computed<number>(() => {
  const c = tagRaw.value as TagDetail | null | undefined
  if (c && typeof c.post_count === 'number') return c.post_count
  if (c && typeof c.postsCount === 'number') return c.postsCount
  if (c && Array.isArray(c.posts)) return c.posts.length
  return postsRaw.value?.total ?? 0
})
const posts = computed<TagPostRow[]>(() => Array.isArray(postsRaw.value?.items) ? postsRaw.value!.items! : [])
const total = computed(() => postsRaw.value?.total ?? 0)
const loadError = computed(() => !!(tagErr.value || postsErr.value))
// 标签不存在时让 SSR 响应带 404（兜底 UI 不变）；判定口径见 composables/useContentStatus.ts。
const tagMissing = computed(
  () => tagDetailSettled.value && !pickLocalized(tagRaw.value?.name)
)
// 404 / robots / canonical 同源判定，理由同分类页。
const tagNotFound = computed(() => isContentMissing(tagErr.value, tagMissing.value))
useContentStatus(tagErr, tagMissing)

const totalPages = computed(() => Math.max(1, Math.ceil(total.value / pageSize.value)))
const visiblePages = computed(() => pageWindow(currentPage.value, totalPages.value))

// 页码越界（?page=99 而标签只剩 3 页）拉回最后一页，别留一条点不动的空页码条。
watch([total, currentPage], () => {
  if (total.value > 0 && currentPage.value > totalPages.value) currentPage.value = totalPages.value
})

const pageHref = (page: number) =>
  `${applyLocalePrefix(`/tags/${slug.value}`, locale.value)}?page=${page}`
const pageLinkClass = (variant: 'default' | 'outline' | 'ghost') =>
  buttonVariants({ variant, size: 'icon' })

const router = useRouter()
function goToPage(page: number) {
  if (page < 1 || page > totalPages.value) return
  currentPage.value = page
  void router.replace({ query: page > 1 ? { page: String(page) } : {} })
  if (import.meta.client) window.scrollTo({ top: 0, behavior: 'smooth' })
}

// 浏览器前进/后退改的是地址栏，页内状态要跟着回读
watch(
  () => route.query.page,
  (raw) => {
    const next = Math.max(1, Number(raw) || 1)
    if (next !== currentPage.value) currentPage.value = next
  }
)

// 标题与 description 只由 useSeo 产出：再加一条裸 useHead 会让 <head> 出现第二条
// name="description"（unhead 按入队顺序合并，两份裁切长度不同），爬虫/分享卡片
// 只能碰运气挑一条。口径与 pages/[slug].vue 一致。
useSeo({
  title: computed(() => tagName.value ? `${tagName.value} · ${t('tags.title', '标签')}` : t('tags.title', '标签')),
  description: computed(() => tagDesc.value),
  noindex: tagNotFound,
  type: 'website'
})
useWebsiteJsonLd()
useBreadcrumbJsonLd([
  { name: t('nav.home', '首页') as string, url: '/' },
  { name: t('nav.tags', '标签') as string, url: '/tags' },
  { name: tagName.value || slug.value, url: `/tags/${slug.value}` }
])
</script>
