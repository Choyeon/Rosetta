<!--
  作者主页（作者归档）：GET /users/username/<username>（公开资料）
  + GET /blog/posts?author=<username>（该作者的已发布文章）。

  两条请求都用**固定 URL + query**，不存在"先拿到 id 再取列表"的依赖链：
  列表侧的作者过滤按用户名解析（后端 author 参数），所以 SSR 期可以并发取数，
  不需要 useAPI 支持空 URL。

  隐私口径由服务端负责：作者关掉 show_posts 后列表接口直接回空页，
  本页面因此绝不"猜测"内容是否存在——资料取不到（404 / 空对象）才由
  useContentStatus 回写真 404；列表为空只是"这位作者还没发文"。
-->
<template>
  <div class="container py-16">
    <header class="mb-12">
      <div class="mb-3 text-xs uppercase tracking-[0.16em] text-muted-foreground">
        <span>{{ t('authors.eyebrow', '作者主页') }}</span>
        <span> / </span>
        <span class="text-foreground">{{ displayName }}</span>
      </div>

      <div class="flex flex-wrap items-start justify-between gap-4">
        <div class="flex min-w-0 items-center gap-4">
          <UserAvatar
            :avatar="profile?.resolved_avatar_url || profile?.avatar || null"
            :seed="displayName"
            :name="displayName"
            :title="profile?.title ?? null"
            :size="72"
            :show-title="false"
          />
          <div class="min-w-0">
            <h1 class="font-display text-3xl md:text-4xl font-bold tracking-tight">
              {{ displayName }}
            </h1>
            <div
              v-if="profile?.title"
              class="mt-2 flex flex-wrap items-center gap-2"
            >
              <TitleBadge
                :title="profile.title"
                size="sm"
              />
            </div>
            <p
              v-if="bio"
              class="mt-3 max-w-2xl leading-relaxed text-muted-foreground"
            >
              {{ bio }}
            </p>
            <div
              v-if="profile?.website || profile?.github"
              class="mt-3 flex flex-wrap items-center gap-4 text-sm"
            >
              <a
                v-if="profile?.website"
                :href="profile.website"
                target="_blank"
                rel="noopener noreferrer"
                class="inline-flex items-center gap-1.5 text-muted-foreground transition-colors hover:text-primary"
              >
                <Globe class="size-3.5" />
                {{ t('authors.website', '网站') }}
              </a>
              <a
                v-if="profile?.github"
                :href="`https://github.com/${profile.github}`"
                target="_blank"
                rel="noopener noreferrer"
                class="inline-flex items-center gap-1.5 text-muted-foreground transition-colors hover:text-primary"
              >
                <ExternalLink class="size-3.5" />
                {{ t('authors.github', 'GitHub') }}
              </a>
            </div>
            <p
              v-if="joinedLabel"
              class="mt-2 text-xs text-muted-foreground"
            >
              {{ joinedLabel }}
            </p>
          </div>
        </div>

        <div class="inline-flex items-center gap-2 text-sm text-muted-foreground">
          <span class="inline-flex items-center justify-center rounded-full bg-muted px-3 py-1">
            {{ total }} {{ t('authors.posts', '篇文章') }}
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
    <template v-else-if="loadError">
      <div class="rounded-xl border border-destructive/30 bg-destructive/5 p-6 text-sm text-destructive">
        {{ t('admin.posts.loadFailed', '加载失败，请稍后重试。') }}
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
      <div class="py-20 text-center">
        <div class="mb-4 inline-flex size-16 items-center justify-center rounded-2xl bg-muted">
          <UserRound class="size-8 text-muted-foreground" />
        </div>
        <h3 class="font-display text-xl font-semibold">
          {{ t('authors.emptyTitle', '这位作者还没有公开文章') }}
        </h3>
        <p class="mt-1 text-muted-foreground">
          {{ t('posts.noPostsDesc', '作者正在努力创作，敬请期待。') }}
        </p>
      </div>
    </template>

    <div
      v-if="totalPages > 1"
      class="mt-12 flex justify-center"
    >
      <nav
        class="flex items-center gap-2"
        role="navigation"
        :aria-label="t('common.pagination', '分页导航')"
      >
        <Button
          variant="outline"
          size="icon"
          :disabled="currentPage <= 1"
          :aria-label="t('common.prevPage', '上一页')"
          @click="currentPage -= 1"
        >
          <ChevronLeft data-icon="inline-start" />
        </Button>
        <Button
          v-for="p in visiblePages"
          :key="p"
          :variant="p === currentPage ? 'default' : 'ghost'"
          size="icon"
          class="size-9 min-w-[2.25rem]"
          @click="currentPage = p"
        >
          {{ p }}
        </Button>
        <Button
          variant="outline"
          size="icon"
          :disabled="currentPage >= totalPages"
          :aria-label="t('common.nextPage', '下一页')"
          @click="currentPage += 1"
        >
          <ChevronRight data-icon="inline-end" />
        </Button>
      </nav>
    </div>
  </div>
</template>

<script setup lang="ts">
import { useAPI } from '~~/composables/useApi'
import { useContentStatus } from '~~/composables/useContentStatus'
import PostCard from '~~/components/PostCard.vue'
import PostSkeleton from '~~/components/PostSkeleton.vue'
import UserAvatar from '~~/components/UserAvatar.vue'
import TitleBadge from '~~/components/TitleBadge.vue'
import { Button } from '~~/components/ui/button'
import { ChevronLeft, ChevronRight, ExternalLink, Globe, UserRound } from '@lucide/vue'
import type { AdminUserTitle } from '~~/composables/useAdminManage'
import { useI18n } from 'vue-i18n'

definePageMeta({ layout: 'default' })

const { t, locale } = useI18n()
const route = useRoute()

const username = computed(() =>
  typeof route.params.username === 'string' ? route.params.username : ''
)
const currentPage = ref(1)
const pageSize = 9

const pickLocalized = (val: unknown): string => {
  if (val == null) return ''
  if (typeof val === 'string') return val
  if (typeof val === 'object') {
    const obj = val as Record<string, string>
    const key = (locale.value || Object.keys(obj)[0] || '') as string
    return obj[key] ?? obj[Object.keys(obj)[0] || ''] ?? ''
  }
  return String(val)
}

/** GET /users/username/{username} 的公开视图（后端已按隐私开关收窄字段） */
interface AuthorProfile {
  id?: number
  username?: string
  nickname?: string
  bio?: string
  avatar?: string | null
  resolved_avatar_url?: string | null
  website?: string | null
  github?: string | null
  title?: AdminUserTitle | null
  created_at?: string
}

interface AuthorPostRow {
  id: number | string
  slug: string
  title: string | Record<string, string>
  [key: string]: unknown
}

// 资料：用户名不存在 / 资料不公开时后端回 404/403，页面只用兜底 UI + 真状态码表达。
const { data: profile, error: profileError } = useAPI<AuthorProfile>(
  `/users/username/${username.value}`,
  { key: computed(() => `author:profile:${username.value}:${locale.value}`), default: () => ({}) }
)

// 列表：固定 URL + author query，与资料请求并发（无依赖链）。
const { data: postsRaw, pending, error: postsErr, refresh } = useAPI<{
  items?: AuthorPostRow[]
  total?: number
}>('/blog/posts', {
  query: computed(() => ({
    lang: locale.value,
    page: currentPage.value,
    page_size: pageSize,
    author: username.value || undefined
  })),
  key: computed(() => `author:posts:${username.value}:${locale.value}:${currentPage.value}`)
})

watch([currentPage, username, locale], () => {
  if (import.meta.client) refresh()
})

const displayName = computed(
  () => profile.value?.nickname || profile.value?.username
    || (pending.value ? '' : t('error.notFoundTitle'))
)
const bio = computed(() => pickLocalized(profile.value?.bio))
const joinedLabel = computed(() => {
  const raw = profile.value?.created_at
  if (!raw) return ''
  const d = new Date(raw)
  if (Number.isNaN(d.getTime())) return ''
  // 只取年份：Intl/toLocaleString 的格式化结果依赖运行端 ICU 数据，
  // 服务端与浏览器不一致就会在 hydration 那一刻打出文本差异（AGENTS §2.4）。
  return `${t('authors.joined', '加入于')} ${d.getUTCFullYear()}`
})

const posts = computed<AuthorPostRow[]>(
  () => Array.isArray(postsRaw.value?.items) ? postsRaw.value!.items! : []
)
const total = computed(() => postsRaw.value?.total ?? 0)
const loadError = computed(() => !!(profileError.value || postsErr.value))
// 资料缺失才是"这个作者不存在"；判定时点与口径见 composables/useContentStatus.ts。
useContentStatus(profileError, computed(() => !profile.value?.username))

const totalPages = computed(() => Math.max(1, Math.ceil(total.value / pageSize)))
const visiblePages = computed(() => {
  const pages: number[] = []
  const max = 5
  let start = Math.max(1, currentPage.value - Math.floor(max / 2))
  const end = Math.min(totalPages.value, start + max - 1)
  if (end - start + 1 < max) start = Math.max(1, end - max + 1)
  for (let i = start; i <= end; i++) pages.push(i)
  return pages
})

useSeo({
  title: computed(() =>
    displayName.value ? `${displayName.value} · ${t('authors.eyebrow', '作者主页')}` : t('authors.eyebrow', '作者主页')
  ),
  description: computed(() => bio.value),
  type: 'website'
})
useWebsiteJsonLd()
useBreadcrumbJsonLd([
  { name: t('nav.home', '首页') as string, url: '/' },
  { name: displayName.value || username.value, url: `/authors/${username.value}` }
])
</script>
