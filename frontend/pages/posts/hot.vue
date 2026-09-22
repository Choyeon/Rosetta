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

    <template v-if="loading && posts.length === 0">
      <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        <PostSkeleton
          v-for="i in 6"
          :key="i"
        />
      </div>
    </template>
    <template v-else-if="loadError">
      <div class="rounded-xl border border-destructive/30 bg-destructive/5 p-6 text-sm text-destructive text-center">
        {{ t('admin.posts.loadFailed') || '加载失败' }}
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
                'text-slate-500': idx === 1,
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
        <Button
          as="child"
          variant="outline"
          class="mt-6"
        >
          <NuxtLink to="/posts">{{ t('nav.posts') || '全部文章' }}</NuxtLink>
        </Button>
      </div>
    </template>
  </div>
</template>

<script setup lang="ts">
import PostCard from '~~/components/PostCard.vue'
import PostSkeleton from '~~/components/PostSkeleton.vue'
import { Button } from '~~/components/ui/button'
import type { Post } from '~~/types/api'
import { useAPI } from '~~/composables/useApi'
import { useI18n } from 'vue-i18n'
import { Flame, TrendingUp } from '@lucide/vue'
import { computed } from 'vue'

definePageMeta({ layout: 'default' })

const { t, locale } = useI18n()
const site = useSite()

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

// ===== SSR 友好同步解构 useAPI，无顶层 await（避免 async setup → Suspense
// 水合 Symbol(v-cmt) vs 真实 DIV → Hydration node mismatch）=====
const defaultLimit = 18
const {
  data,
  pending: loading,
  error: loadError
} = useAPI<Post[] | { items?: Post[] }>('/blog/posts/hot', {
  key: 'posts-hot-index',
  query: { limit: defaultLimit },
  default: () => []
})

// 后端 /blog/posts/hot 返回裸数组；同时兼容 { items } 信封结构
const posts = computed<Post[]>(() => {
  const d = data.value
  if (Array.isArray(d)) return d
  if (d && Array.isArray(d.items)) return d.items
  return []
})

// 避免 unused local lint 警告
void pickLocalized
</script>
