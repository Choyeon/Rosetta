<!--
  热门榜单页：GET /blog/posts/hot，排名就是数组顺序（热度评分全在后端，前端不再二次计算）。
  后端当前返回裸数组，代码同时兼容 { items } 信封 —— 收紧成单一形状前先确认端点行为。
  本路由带 swr 60s 缓存，排名变动会滞后显示属预期，别为"立即生效"加客户端轮询；
  同步解构不加 await 是为避开 Suspense 水合 mismatch（全仓列表页同一约定）。
  榜单周期 chip 是真实 <a href>（走 localeHrefWith，缺省档不挂 ?rank=）：SSR 页把视图切换
  做成 <Button @click> 等于四个周期档在爬虫的链接图里不存在（批次 #127，AGENTS §2.3.3）。
-->
<template>
  <div class="container py-16">
    <header class="mb-10">
      <div class="flex items-center gap-3">
        <div class="inline-flex items-center justify-center size-11 rounded-2xl bg-gradient-to-br from-amber-400 to-orange-500 text-background shadow-sm">
          <Flame
            data-icon="inline-start"
            class="size-6"
          />
        </div>
        <div>
          <h1 class="font-display text-3xl md:text-4xl font-bold tracking-tight">
            {{ t('posts.hotTitle') || '热门榜单' }}
          </h1>
          <p class="text-muted-foreground mt-1">
            {{ t('posts.hotTitleDesc') || 'Hacker News 风格综合热度榜：评分、浏览、评论、新鲜度加权计算' }}
          </p>
        </div>
      </div>
    </header>

    <!-- 榜单口径切换：内容随选择整块替换，缺省档（综合榜）不挂查询键。
         必须是真实 <a href>（AGENTS §2.3.3 第 2 条）：这页是 SSR，做成 <Button @click>
         时 ?rank=day/week/month/all 在爬虫读到的 HTML 里一条都不存在。
         role 用 group 而不是 radiogroup：那套语义要求方向键切换，这里从未实现。 -->
    <div
      role="group"
      :aria-label="t('posts.rankAria')"
      class="flex flex-wrap gap-2 mb-8 -mt-2"
    >
      <a
        v-for="opt in rankOptions"
        :key="opt.value"
        :href="periodHref(opt.value)"
        :class="buttonVariants({ variant: period === opt.value ? 'default' : 'outline', size: 'sm' })"
        :aria-current="period === opt.value ? 'true' : undefined"
        @click.prevent="setPeriod(opt.value)"
      >
        {{ opt.label }}
      </a>
    </div>

    <template v-if="loading && posts.length === 0">
      <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        <PostSkeleton
          v-for="i in 6"
          :key="i"
        />
      </div>
    </template>
    <template v-else-if="loadError">
      <div class="rounded-xl border border-destructive/30 bg-destructive/5 p-6 text-sm text-destructive">
        <div class="flex flex-col items-center gap-3 text-center">
          <span>{{ t('error.loadFailed') }}</span>
          <Button
            variant="outline"
            size="sm"
            @click="refresh()"
          >
            <RefreshCw data-icon="inline-start" />
            {{ t('common.retry', '重试') }}
          </Button>
        </div>
      </div>
    </template>
    <template v-else-if="posts.length > 0">
      <ol class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        <li
          v-for="(post, idx) in posts"
          :key="post.id"
          v-memo="[post.id, post.updated_at, post.published_at]"
        >
          <div class="relative group">
            <div
              class="absolute -left-2 -top-3 z-10 size-8 rounded-full bg-card border border-border shadow flex items-center justify-center font-display text-sm font-bold"
              :class="{
                'text-amber-600 dark:text-amber-400': idx === 0,
                'text-muted-foreground': idx === 1,
                'text-orange-700 dark:text-orange-400': idx === 2
              }"
            >
              #{{ idx + 1 }}
            </div>
            <PostCard
              :post="post"
              class="pt-3"
            />
          </div>
        </li>
      </ol>
    </template>
    <template v-else>
      <div class="text-center py-20">
        <div class="inline-flex items-center justify-center size-16 rounded-2xl bg-muted mb-4">
          <TrendingUp class="size-8 text-muted-foreground" />
        </div>
        <h3 class="font-display text-xl font-semibold">
          {{ t('posts.noPosts') || '暂无文章' }}
        </h3>
        <p class="text-muted-foreground mt-1">
          {{ t('posts.noPostsDesc') || '尚无热度数据，欢迎回到文章列表浏览最新内容。' }}
        </p>
        <!-- 链接按钮走 buttonVariants + NuxtLink（Button 包 NuxtLink 会渲染出
             button 套 a 的嵌套可交互元素，键盘与点击行为都会错） -->
        <NuxtLink
          :to="localeHref('/posts')"
          :class="cn(buttonVariants({ variant: 'outline' }), 'mt-6')"
        >{{ t('nav.posts') || '全部文章' }}</NuxtLink>
      </div>
    </template>
  </div>
</template>

<script setup lang="ts">
import PostCard from '~~/components/PostCard.vue'
import PostSkeleton from '~~/components/PostSkeleton.vue'
import { Button, buttonVariants } from '~~/components/ui/button'
import { cn } from '~~/lib/utils'
import type { Post } from '~~/types/api'
import { useAPI } from '~~/composables/useApi'
import { useI18n } from 'vue-i18n'
import { Flame, RefreshCw, TrendingUp } from '@lucide/vue'
import { computed } from 'vue'

definePageMeta({ layout: 'default' })

const { t } = useI18n()
const site = useSite()
const route = useRoute()
const router = useRouter()
const { localeHref, localeHrefWith } = useLocaleLink()

// ===== SEO（useSeo composable）=====
const hotTitle = computed(() => t('posts.hotTitle') || '热门榜单')
const hotDescription = computed(
  () =>
    site.siteDescription.value
    || t('posts.hotTitleDesc')
    || '热门文章综合榜'
)
useSeo({
  title: hotTitle,
  description: hotDescription,
  type: 'website',
  url: '/posts/hot'
})
useBreadcrumbJsonLd([
  { name: String(t('nav.home') || '首页'), url: '/' },
  { name: String(t('nav.posts') || '文章'), url: '/posts' },
  { name: String(hotTitle.value || '热门'), url: '/posts/hot' }
])

// ===== SSR 友好同步解构 useAPI，无顶层 await（避免 async setup → Suspense
// 水合 Symbol(v-cmt) vs 真实 DIV → Hydration node mismatch）=====
const defaultLimit = 18

// ===== 榜单口径切换 =====
// hot 走 /blog/posts/hot（Hacker News 风格综合评分，新鲜度加权）；
// day/week/month/all 走 /ranking/posts（周期榜：近期浏览 + 点赞*5 + 评论*3，全站累计榜按总浏览）。
// 两个端点此前只有 hot 有前端消费者，/ranking/posts 是零调用死口。
const RANK_PERIODS = ['hot', 'day', 'week', 'month', 'all'] as const
type RankPeriod = (typeof RANK_PERIODS)[number]
const isRankPeriod = (v: unknown): v is RankPeriod =>
  (RANK_PERIODS as readonly string[]).includes(String(v))
// 周期是页内视图变体（canonical 白名单只有 page，见 §2.3.3 第 3 条），
// 但仍要进 URL：分享出去的"本周热榜"不能落回综合榜。
const period = ref<RankPeriod>(isRankPeriod(route.query.rank) ? route.query.rank : 'hot')

// 标签键写成字面量映射而不是 `posts.rank${Pascal}` 拼串：i18n 孤儿键守卫
// （tests/unit/i18nLocaleKeys.spec.ts）按"键名是否以字面量出现在源码里"判定消费点，
// 拼串会让这五个键看起来没人用，进而被当成垃圾删掉。
const RANK_LABEL_KEYS: Record<RankPeriod, string> = {
  hot: 'posts.rankHot',
  day: 'posts.rankDay',
  week: 'posts.rankWeek',
  month: 'posts.rankMonth',
  all: 'posts.rankAll'
}

const rankOptions = computed(() =>
  RANK_PERIODS.map(p => ({ value: p, label: String(t(RANK_LABEL_KEYS[p])) }))
)

// 周期 chip 是真实 <a href>（AGENTS §2.3.3 第 2 条）：这页 SSR 且带 swr 60，做成
// <Button @click> 时 ?rank=day/week/month/all 在爬虫读到的 HTML 里一条都不存在。
// 缺省档（hot）不挂查询键，与 setPeriod 写地址栏的口径一致。
const periodHref = (p: RankPeriod) =>
  localeHrefWith('/posts/hot', { rank: p === 'hot' ? '' : p })

const setPeriod = (next: RankPeriod) => {
  if (period.value === next) return
  period.value = next
  void router.replace({ query: next === 'hot' ? {} : { rank: next } })
}

interface RankingRow {
  id: number | string
  title: string | Record<string, string>
  slug: string
  cover_image?: string | null
  views?: number
  likes_count?: number
  comments_count?: number
  published_at?: string | null
  created_at?: string | null
  has_audio?: boolean
  has_video?: boolean
  has_embed?: boolean
}

const {
  data,
  pending: loading,
  error: loadError,
  refresh
} = useAPI<Post[] | { items?: Post[] } | { items?: RankingRow[] }>(
  () => (period.value === 'hot' ? '/blog/posts/hot' : '/ranking/posts'),
  {
    key: 'posts-hot-index',
    query: computed(() =>
      period.value === 'hot'
        ? { limit: defaultLimit }
        : { period: period.value, limit: defaultLimit }
    ),
    default: () => []
  }
)

// 后端 /blog/posts/hot 返回裸数组；同时兼容 { items } 信封结构。
// /ranking/posts 恒是 { period, items }，条目字段是榜单口径（无 excerpt/author），
// 补齐成 PostCard 认得的形状再交给同一套卡片渲染。
const posts = computed<Post[]>(() => {
  const d = data.value
  if (period.value === 'hot') {
    if (Array.isArray(d)) return d
    if (d && Array.isArray((d as { items?: Post[] }).items)) return (d as { items: Post[] }).items
    return []
  }
  const rows = (d as { items?: RankingRow[] } | null)?.items
  if (!Array.isArray(rows)) return []
  return rows.map(row => ({
    id: row.id,
    slug: row.slug,
    title: row.title,
    cover_image: row.cover_image ?? null,
    views: row.views ?? 0,
    likes_count: row.likes_count ?? 0,
    comments_count: row.comments_count ?? 0,
    published_at: row.published_at ?? row.created_at ?? null,
    created_at: row.created_at ?? null,
    // 存在性三位一起透传：榜单自带 60s 缓存，旧载荷没这三个键时按"没徽标"处理，
    // 但不能因为"这一族自己搭 dict"就永远不带（表现是只有综合榜亮）。
    has_audio: row.has_audio ?? false,
    has_video: row.has_video ?? false,
    has_embed: row.has_embed ?? false
  }) as unknown as Post)
})
</script>
