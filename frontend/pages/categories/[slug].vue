<!--
  分类详情页：GET /blog/categories/slug/<slug>（元信息）+ GET /blog/posts?category=<slug>（列表）。
  详情请求的 URL 与 query 都是 setup 期一次性取值（只有 key 是 computed），换 slug 不会自动重取；
  列表 refresh 一律带 import.meta.client 守卫 —— SSR 阶段 useFetch 已取过数，服务端再 refresh
  等于重复请求。分类名取不到时兜底显示 slug，是刻意保留的可辨识占位而不是数据缺失。
  层级（Category.parent_id）从公开列表 `GET /blog/categories` 现算（与页脚同一把缓存键）：
  面包屑补全部祖先、页头下方挂直接子分类入口，JSON-LD 面包屑走 computed 跟着同一份祖先链走。
  祖先与子分类都只认"公开列表里真实存在的那几行"——父级被停用即整段收起，绝不链去一个
  访客读不到的分类页；取值算术单源在 lib/category-tree.ts（含环与悬空父级的兜底）。
-->
<template>
  <div class="container py-16">
    <!-- 分类封面：只在后台真给了图时出现，图坏了也整块撤掉。
         留一个空框（或 src=""）比没图更糟——它把首屏最贵的位置换成一处破图。 -->
    <div
      v-if="catCover && !coverBroken"
      class="mb-8 overflow-hidden rounded-[16px] border border-border/60"
      data-testid="category-cover"
    >
      <img
        :src="catCover"
        :alt="categoryName"
        class="block h-auto w-full aspect-[21/9] object-cover"
        width="1200"
        height="514"
        @error="coverBroken = true"
      >
    </div>
    <!-- 头部整块只在分类存在时渲染：不存在态下 categoryName 回落成「页面不存在」，
         留着它就会与下面面板的 h1 并排成两个同名标题（线上 h1 数 = 2）。 -->
    <header
      v-if="!catNotFound"
      class="mb-12"
    >
      <div class="inline-flex items-center gap-2 text-xs uppercase tracking-[0.16em] text-muted-foreground mb-3">
        <span class="size-1.5 rounded-full bg-warning" />
        <NuxtLink
          :to="localeHref('/categories')"
          class="hover:text-foreground transition-colors"
        >{{ t('categories.title', '分类') }}</NuxtLink>
        <!-- 祖先链按由远及近顺序补在中间，末尾那条 `/` 指向本页 h1（当前分类）。
             父级被停用时整条自然收起（公开列表取不到那一行），不会链去访客打不开的分类页。 -->
        <template
          v-for="ancestor in ancestorTrail"
          :key="ancestor.id"
        >
          <span>/</span>
          <NuxtLink
            :to="localeHref(`/categories/${ancestor.slug}`)"
            class="hover:text-foreground transition-colors"
          >{{ pickLocalized(ancestor.name) || ancestor.slug }}</NuxtLink>
        </template>
        <span>/</span>
      </div>
      <div class="flex flex-wrap items-end justify-between gap-4">
        <div class="flex items-center gap-3">
          <div
            v-if="catRaw?.icon"
            class="size-10 rounded-xl flex items-center justify-center shrink-0"
            :style="{ background: catRaw?.color ? `color-mix(in oklab, ${catRaw.color} 15%, transparent)` : undefined }"
            :class="!catRaw?.color ? 'bg-primary/10' : ''"
          >
            <DynamicIcon
              :icon="catRaw.icon"
              class="size-5"
              :class="catRaw?.color ? 'text-foreground' : 'text-primary'"
            />
          </div>
          <div>
            <h1 class="font-display text-3xl md:text-4xl font-bold tracking-tight">
              {{ categoryName }}
            </h1>
            <p
              v-if="categoryDesc"
              class="text-muted-foreground mt-3 leading-relaxed max-w-2xl"
            >
              {{ categoryDesc }}
            </p>
          </div>
        </div>
        <div
          v-if="!catNotFound"
          class="inline-flex items-center gap-2 text-sm text-muted-foreground"
        >
          <span class="inline-flex items-center justify-center px-3 py-1 rounded-full bg-muted">
            {{ postCount }} {{ t('categories.posts', '篇文章') }}
          </span>
        </div>
      </div>
    </header>

    <!-- 子分类入口：层级在前台不能只有"往上"没有"往下"。少了这一块，子分类页除了
         直接 URL 与后台列表就是零入链——爬虫发现不了这个页面，访客也走不到，
         运营者在后台建的第二层分类等于没建。 -->
    <div
      v-if="!catNotFound && childCategories.length > 0"
      class="mb-10"
      data-testid="category-children"
    >
      <div class="mb-3 text-xs uppercase tracking-[0.16em] text-muted-foreground">
        {{ t('categories.subcategories', '子分类') }}
      </div>
      <div class="flex flex-wrap gap-2">
        <NuxtLink
          v-for="child in childCategories"
          :key="child.id"
          :to="localeHref(`/categories/${child.slug}`)"
          class="inline-flex items-center gap-1.5 rounded-full border border-border/60 bg-card/60 px-3 py-1.5 text-sm text-muted-foreground transition-colors hover:border-primary/40 hover:text-foreground"
          data-testid="category-child-link"
        >
          <FolderOpen class="size-3.5 shrink-0" />
          <span>{{ pickLocalized(child.name) || child.slug }}</span>
          <span
            v-if="typeof child.post_count === 'number'"
            class="text-xs opacity-70"
          >{{ child.post_count }}</span>
        </NuxtLink>
      </div>
    </div>

    <template v-if="pending && posts.length === 0">
      <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        <PostSkeleton
          v-for="i in 6"
          :key="i"
        />
      </div>
    </template>
    <!-- 分类不存在时只给一块面板：此前它会落进 loadError 分支（列表请求对不存在的分类
         照样成功、只是空，缺的是详情），访客看到的是「文章列表加载失败」——把一个
         不存在的 URL 说成临时故障，刷新一百次也不会好。判据复用 catNotFound（网络故障
         不算缺失，仍走下面的 loadError，见 composables/useContentStatus.ts）。 -->
    <template v-else-if="catNotFound">
      <div class="rounded-2xl border border-dashed border-border/70 bg-card/40 px-6 py-12 text-center">
        <div class="inline-flex items-center justify-center size-16 rounded-2xl bg-muted mb-4">
          <FolderOpen class="size-8 text-muted-foreground" />
        </div>
        <h1 class="font-display text-xl font-semibold">
          {{ t('error.notFoundTitle') }}
        </h1>
        <p class="mt-2 text-sm text-muted-foreground">
          {{ t('error.notFoundDesc') }}
        </p>
        <div class="mt-6 flex flex-wrap items-center justify-center gap-3">
          <Button as-child>
            <NuxtLink :to="localeHref('/categories')">
              {{ t('categories.title') }}
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
          <FolderOpen class="size-8 text-muted-foreground" />
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
            disabled
            :aria-label="t('common.prevPage', '上一页')"
          >
            <ChevronLeft data-icon="inline-start" />
          </Button>
        </template>
        <a
          v-else
          :href="pageHref(currentPage - 1)"
          :aria-label="t('common.prevPage', '上一页')"
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
            disabled
            :aria-label="t('common.nextPage', '下一页')"
          >
            <ChevronRight data-icon="inline-start" />
          </Button>
        </template>
        <a
          v-else
          :href="pageHref(currentPage + 1)"
          :aria-label="t('common.nextPage', '下一页')"
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
import type { BreadcrumbItem } from '~~/composables/useSeo'
import { categoryAncestorPath, categoryChildren } from '~~/lib/category-tree'
import PostCard from '~~/components/PostCard.vue'
import PostSkeleton from '~~/components/PostSkeleton.vue'
import { Button, buttonVariants } from '~~/components/ui/button'
import { pageWindow } from '~~/lib/pagination'
import { ChevronLeft, ChevronRight, FolderOpen } from '@lucide/vue'
import { useI18n } from 'vue-i18n'

definePageMeta({ layout: 'default' })

const { t, locale } = useI18n()
const route = useRoute()
const { localeHref } = useLocaleLink()

const slug = computed(() => typeof route.params.slug === 'string' ? route.params.slug : '')
// 页码是 URL 状态：分享 ?page=3、刷新、浏览器后退都必须还原（口径见 /posts 文件头）。
const currentPage = ref(Math.max(1, Number(route.query.page) || 1))
// 快照 setup 期的页码：越界判定要认"访客请求的那一页"，而 currentPage 会被钳位 watch
// 拉回末页，事后就分不清 `?page=99` 与正常访问了。
const requestedPage = Math.max(1, Number(route.query.page) || 1)
const site = useSite()
// 每页条数取后台「阅读体验」分组；未配置时沿用 9
const pageSize = computed(() => site.reading.value.posts_per_page)

const pickLocalized = (val: unknown): string => pickLocalizedText(val, locale.value)

// 分类元信息：真实接口 slug 详情。失败不渲染示例内容。
interface CategoryDetail {
  id?: number | string
  slug?: string
  name?: unknown
  description?: unknown
  icon?: string
  color?: string
  /** 后台「分类 → 封面图」写入的站内 URL；null/空串都按"没有封面"处理 */
  cover_image?: string | null
  /** 父分类 ID；null/缺键都是顶级分类（旧缓存的载荷整键缺失） */
  parent_id?: number | string | null
  post_count?: number
  postsCount?: number
  posts?: unknown[]
}

/** `GET /blog/categories` 的行形态：祖先面包屑与子分类入口都从这份公开列表取。 */
interface CategoryListRow {
  id: number | string
  slug: string
  name?: unknown
  parent_id?: number | string | null
  post_count?: number
}

interface CategoryPostRow {
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
// 静态键+静态查询：切语言/换分类 slug 都走「跳同页 URL → 重挂载 → 新参数重新请求」，
// 不手写 watch+refresh()（与 Nuxt key watcher 双发，第一发必被 abort）。
const { data: catRaw, error: catError, status: catStatus } = useAPI<CategoryDetail>(`/blog/categories/slug/${slug.value}`, {
  query: { lang: locale.value },
  key: `category:detail:${slug.value}:${locale.value}`,
  default: () => ({} as CategoryDetail)
})

// 层级分类的公开面：祖先面包屑 + 子分类入口都从 `GET /blog/categories` 这一份列表算。
// 键与其它前台面（页脚 / 首页 / 列表页 / 目录页）共用 `blog:categories:<locale>`——
// 页脚常驻默认布局，所以这里按 key 去重后并不会多打一次后端。
// 列表只含启用的分类（后台 is_active 是公开列表的真实强制点），因此"父级被停用"时
// 面包屑自然收起到更早的启用祖先，而不是链去一个访客看不见的分类页。
const { data: catsListRaw } = useAPI<CategoryListRow[]>('/blog/categories', {
  query: { lang: locale.value },
  key: `blog:categories:${locale.value}`,
  default: () => []
})
const catList = computed<CategoryListRow[]>(() =>
  Array.isArray(catsListRaw.value) ? catsListRaw.value : []
)

// 父级按详情页自己的 parent_id 定位（不是"先在本页于列表里找到自身"）：
// 停用分类的直接 URL 仍然可用，那时它不在这份列表里，面包屑照样要显出它还启用的父级。
const parentCategory = computed<CategoryListRow | null>(() => {
  const pid = catRaw.value?.parent_id
  if (pid == null || pid === 0) return null
  return catList.value.find(row => String(row.id) === String(pid)) ?? null
})
/** 由远及近的祖先链（不含自身），父级本身排在最后。 */
const ancestorTrail = computed<CategoryListRow[]>(() => {
  const p = parentCategory.value
  if (!p) return []
  return [...categoryAncestorPath(catList.value, p.id), p]
})
/** 直接子分类：只在公开列表里的那些（停用的不该从子分类入口被带出来）。 */
const childCategories = computed<CategoryListRow[]>(() =>
  categoryChildren(catList.value, catRaw.value?.id)
)

// 分类文章：复用 /blog/posts?category=slug。失败回空数组，绝不造示例列表。
// query/key 都是 computed：翻页是页内状态（不同步 URL path，不重挂载），靠 Nuxt
// params/key watcher 自动重取；不再叠加手写 watch(refresh)（同一 URL 双发）。
const { data: postsRaw, pending, error: postsErr } = useAPI<{ items?: CategoryPostRow[], total?: number }>('/blog/posts', {
  query: computed(() => ({
    lang: locale.value,
    page: currentPage.value,
    page_size: pageSize.value,
    category: slug.value || undefined
  })),
  key: computed(() => `category:posts:${slug.value}:${locale.value}:${currentPage.value}`)
})

// 详情请求还没落值时不判缺失：默认的空对象会让每个真实分类在加载期先闪一次"不存在"。
const catDetailSettled = computed(() => catStatus.value === 'success' || catStatus.value === 'error')
// 加载中留空（只显站点名）；确实取不到分类时用 404 口径标题，
// 不再把 slug 人性化成假装存在的分类名（响应侧由 useContentStatus 回写 404）。
const categoryName = computed(() => pickLocalized(catRaw.value?.name) || (catDetailSettled.value ? t('error.notFoundTitle') : ''))
const categoryDesc = computed(() => pickLocalized(catRaw.value?.description))
// 封面口径：只有非空字符串才算"有封面"。后端 PUT 已把空串归成 null，这里再挡一层
// 是因为库里可能躺着归一之前写入的 `""`——它会变成一次 src="" 的图片请求（404 + 破图框）。
const catCover = computed(() => {
  const raw = (catRaw.value as CategoryDetail | null | undefined)?.cover_image
  return typeof raw === 'string' ? raw.trim() : ''
})
const coverBroken = ref(false)
const postCount = computed<number>(() => {
  const c = catRaw.value as CategoryDetail | null | undefined
  if (c && typeof c.post_count === 'number') return c.post_count
  if (c && typeof c.postsCount === 'number') return c.postsCount
  if (c && Array.isArray(c.posts)) return c.posts.length
  return postsRaw.value?.total ?? 0
})
const posts = computed<CategoryPostRow[]>(() => Array.isArray(postsRaw.value?.items) ? postsRaw.value!.items! : [])
const total = computed(() => postsRaw.value?.total ?? 0)
const loadError = computed(() => !!(catError.value || postsErr.value))
// 分类不存在时让 SSR 响应带 404（兜底 UI 不变）；判定口径见 composables/useContentStatus.ts。
const catMissing = computed(
  () => catDetailSettled.value && !pickLocalized(catRaw.value?.name)
)
// 404 与 robots/canonical 必须同源判定：状态码回了 404 却写着 `index, follow` +
// 自指 canonical，等于给搜索引擎两份互相矛盾的答复。
const catNotFound = computed(() => isContentMissing(catError.value, catMissing.value))
useContentStatus(catError, catMissing)

const totalPages = computed(() => Math.max(1, Math.ceil(total.value / pageSize.value)))
const visiblePages = computed(() => pageWindow(currentPage.value, totalPages.value))

// 页码越界（?page=99 而分类只剩 3 页）拉回最后一页：空列表加一条永远点不动的页码条
// 等于把用户困住，且 SSR 会把这个空态按本页 swr 缓存给后续访客。
watch([total, currentPage], () => {
  if (total.value > 0 && currentPage.value > totalPages.value) currentPage.value = totalPages.value
})

// 越界页码对爬虫必须 301 回裸分类页：200 空列表会被判 soft 404，自指 canonical 还等于
// 承认每个垃圾页码都是独立页面。时点与 useContentStatus 同轨（app:rendered：数据已落值、
// 状态码还改得动）；`no-store` 防 301 被本页 swr 缓存固化。
if (import.meta.server) {
  const ssrEvent = useRequestEvent()
  useNuxtApp().hooks.hookOnce('app:rendered', () => {
    if (ssrEvent && total.value > 0 && requestedPage > totalPages.value) {
      ssrEvent.node.res.statusCode = 301
      ssrEvent.node.res.setHeader('location', applyLocalePrefix(`/categories/${slug.value}`, locale.value))
      ssrEvent.node.res.setHeader('cache-control', 'no-store')
    }
  })
}

const pageHref = (page: number) =>
  `${applyLocalePrefix(`/categories/${slug.value}`, locale.value)}?page=${page}`
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

// 同 tags/[slug].vue：裸 useHead 会在 <head> 里制造第二条 description。
useSeo({
  title: computed(() => categoryName.value ? `${categoryName.value} · ${t('categories.title', '分类')}` : t('categories.title', '分类')),
  description: computed(() => categoryDesc.value),
  noindex: catNotFound,
  type: 'website'
})
useWebsiteJsonLd()
// 本分类的订阅源入口：阅读器/浏览器扩展在 SSR HTML 里读这条 link 就能只跟这个分类。
// active 用 catNotFound 的反面——不存在态页面自身 noindex，却又 advertise 一个该分类的源，
// 等于给爬虫两份互相矛盾的"这个分类存在"信号。
useRssFeedLink({
  kind: 'category',
  slug,
  label: computed(() => categoryName.value),
  active: computed(() => !catNotFound.value)
})
// 面包屑必须跟着层级走：子分类页只写「首页 / 分类 / 当前」等于把父级那一跳从结构化数据里
// 抹掉，爬虫读到的层级与页面上那行导航各说一套。
// 传 computed 而不是静态数组：详情请求在 setup 期还没落值，静态取会在 SSR 那一趟定死成"无父级"。
useBreadcrumbJsonLd(computed<BreadcrumbItem[]>(() => [
  { name: t('nav.home', '首页') as string, url: '/' },
  { name: t('nav.categories', '分类') as string, url: '/categories' },
  ...ancestorTrail.value.map(row => ({
    name: pickLocalized(row.name) || row.slug,
    url: `/categories/${row.slug}`
  })),
  { name: categoryName.value || slug.value, url: `/categories/${slug.value}` }
]))
</script>
