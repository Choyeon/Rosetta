<!--
  作者主页（作者归档）：GET /users/username/<username>（公开资料）
  + GET /blog/posts?author=<username>（该作者的已发布文章）。

  两条请求都用**固定 URL + query**，不存在"先拿到 id 再取列表"的依赖链：
  列表侧的作者过滤按用户名解析（后端 author 参数），所以 SSR 期可以并发取数，
  不需要 useAPI 支持空 URL。

  隐私口径由服务端负责：作者关掉 show_posts 后列表接口直接回空页，关掉 public_profile 后
  资料接口直接回 404。本页面因此绝不"猜测"内容是否存在——isContentMissing 判定为真
  （404 / 取不到资料）才同时换上「不存在」文案并由 useContentStatus 回写真 404；
  列表为空只是"这位作者还没发文"。
-->
<template>
  <div class="container py-16">
    <header
      v-if="!notFound"
      class="mb-12"
    >
      <!-- 作者封面（User.cover_image，账户设置页可上传）：取不到资料时自然不渲染，
           装饰图 alt 留空——作者名已在下方 h1，重复一遍只会让读屏器多念一次。 -->
      <div
        v-if="coverImage"
        class="mb-6 overflow-hidden rounded-xl border"
      >
        <img
          :src="coverImage"
          alt=""
          width="1200"
          height="800"
          class="h-32 w-full object-cover md:h-44"
        >
      </div>
      <div class="mb-3 text-xs uppercase tracking-[0.16em] text-muted-foreground">
        <span>{{ t('authors.eyebrow', '作者主页') }}</span>
        <span> / </span>
        <span class="text-foreground">{{ displayName }}</span>
      </div>

      <div class="flex flex-wrap items-start justify-between gap-4">
        <div class="flex min-w-0 items-center gap-4">
          <UserAvatar
            :resolved-avatar-url="profile?.resolved_avatar_url"
            :avatar="profile?.avatar || null"
            :seed="profile?.username || displayName"
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
            <!-- 发私信：入口放在作者主页而非主导航。/account/messages 是登录态私有页，
                 未登录点过去只会得到一次跳转；本人主页也不需要给自己发私信。
                 ClientOnly 是必需的：SSR 期 auth store 走 skipHydrate（拿不到 token），
                 服务端渲染成「无链接」、客户端渲染成「有链接」，不包就是节点级 hydration mismatch。 -->
            <ClientOnly>
              <div
                v-if="canMessage"
                class="mt-3 flex flex-wrap items-center gap-4 text-sm"
              >
                <NuxtLink
                  :to="messageHref"
                  class="inline-flex items-center gap-1.5 text-muted-foreground transition-colors hover:text-primary"
                >
                  <MessageSquare class="size-3.5" />
                  {{ t('messages.fromProfile') }}
                </NuxtLink>
              </div>
            </ClientOnly>
            <p
              v-if="joinedLabel"
              class="mt-2 text-xs text-muted-foreground"
            >
              {{ joinedLabel }}
            </p>
          </div>
        </div>

        <div class="flex flex-wrap items-center gap-2 text-sm text-muted-foreground">
          <span class="inline-flex items-center justify-center rounded-full bg-muted px-3 py-1">
            {{ total }} {{ t('authors.posts', '篇文章') }}
          </span>
          <!-- 目录页入口挂在这里而不是主导航：作者主页是"从一篇文章认识一个人"的终点，
               往下逛的自然去处是"还有哪些人在写"；主导航再加一条会挤掉内容页的位置。 -->
          <NuxtLink
            :to="localeHref('/authors')"
            class="inline-flex items-center justify-center rounded-full border border-border/60 px-3 py-1 transition-colors hover:text-primary hover:border-primary/40"
          >
            {{ t('authors.browseAll', '浏览全部作者') }}
          </NuxtLink>
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
    <template v-else-if="notFound">
      <div class="py-20 text-center">
        <div class="mb-4 inline-flex size-16 items-center justify-center rounded-2xl bg-muted">
          <UserRound class="size-8 text-muted-foreground" />
        </div>
        <h1 class="font-display text-xl font-semibold">
          {{ t('authors.notFoundTitle', '这位作者不存在') }}
        </h1>
        <p class="mt-1 text-muted-foreground">
          {{ t('authors.notFoundDesc', '该主页可能从未存在，或作者已关闭了公开资料。') }}
        </p>
      </div>
    </template>
    <template v-else-if="loadError">
      <div class="rounded-xl border border-destructive/30 bg-destructive/5 p-6 text-sm text-destructive">
        <div class="flex flex-col items-center gap-3 text-center">
          <span>{{ t('error.serverErrorDesc') }}</span>
          <Button
            variant="outline"
            size="sm"
            @click="retryLoad()"
          >
            <RefreshCw data-icon="inline-start" />
            {{ t('error.retry') }}
          </Button>
        </div>
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
        aria-label="pagination"
      >
        <!-- 与 /posts、/activity、/authors 目录同款：翻页是真实 <a href>（SSR HTML 里的
             href 是无 JS 访客与爬虫唯一的链接图），click 仍走 handlePageChange 保留 SPA 行为。 -->
        <template v-if="currentPage <= 1">
          <Button
            variant="outline"
            size="icon"
            class="size-9 min-w-[2.25rem]"
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
          @click.prevent="handlePageChange(currentPage - 1)"
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
            @click.prevent="handlePageChange(p)"
          >{{ p }}</a>
        </template>
        <template v-if="currentPage >= totalPages">
          <Button
            variant="outline"
            size="icon"
            class="size-9 min-w-[2.25rem]"
            disabled
            :aria-label="t('common.nextPage', '下一页')"
          >
            <ChevronRight data-icon="inline-end" />
          </Button>
        </template>
        <a
          v-else
          :href="pageHref(currentPage + 1)"
          :aria-label="t('common.nextPage', '下一页')"
          :class="pageLinkClass('outline')"
          @click.prevent="handlePageChange(currentPage + 1)"
        >
          <ChevronRight data-icon="inline-end" />
        </a>
      </nav>
    </div>
  </div>
</template>

<script setup lang="ts">
import { useAPI } from '~~/composables/useApi'
import { isContentMissing, useContentStatus } from '~~/composables/useContentStatus'
import PostCard from '~~/components/PostCard.vue'
import PostSkeleton from '~~/components/PostSkeleton.vue'
import UserAvatar from '~~/components/UserAvatar.vue'
import TitleBadge from '~~/components/TitleBadge.vue'
import { Button, buttonVariants } from '~~/components/ui/button'
import { ChevronLeft, ChevronRight, ExternalLink, Globe, MessageSquare, RefreshCw, UserRound } from '@lucide/vue'
import type { AdminUserTitle } from '~~/composables/useAdminManage'
import { useAuthStore } from '~~/stores/auth'
import { pageWindow } from '~~/lib/pagination'
import { useI18n } from 'vue-i18n'

definePageMeta({ layout: 'default' })

const { t, locale } = useI18n()
const route = useRoute()
const authStore = useAuthStore()

const username = computed(() =>
  typeof route.params.username === 'string' ? route.params.username : ''
)
const router = useRouter()
// 页码从 URL 读：作者主页的「第 N 页」是可分享的，站内一度只有页内状态——
// 刷新/后退回到第 1 页、爬虫也只拿得到第一页的链接。
const requestedPage = Math.max(1, Number(route.query.page) || 1)
const currentPage = ref(requestedPage)
const site = useSite()
const { localeHref } = useLocaleLink()
// 每页条数取后台「阅读体验」分组；未配置时沿用 9
const pageSize = computed(() => site.reading.value.posts_per_page)

const pickLocalized = (val: unknown): string => pickLocalizedText(val, locale.value)

/** GET /users/username/{username} 的公开视图（后端已按隐私开关收窄字段） */
interface AuthorProfile {
  id?: number
  username?: string
  nickname?: string
  bio?: string
  avatar?: string | null
  cover_image?: string | null
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

// 资料：用户名不存在、或作者关了「公开资料」时后端统一回 404（不存在口径，防枚举）。
// 静态键：切语言/换作者都走「跳同页 URL → 重挂载 → 新参数重新请求」，
// 不手写 watch+refresh()（与 Nuxt key watcher 双发，第一发必被 abort）。
const { data: profile, error: profileError, refresh: refreshProfile } = useAPI<AuthorProfile>(
  `/users/username/${username.value}`,
  { key: `author:profile:${username.value}:${locale.value}`, default: () => ({}) }
)

// 列表：固定 URL + author query，与资料请求并发（无依赖链）。
// query/key 都是 computed：翻页是页内状态（不重挂载），靠 Nuxt params/key watcher
// 自动重取；不再叠加手写 watch(refresh)（同一 URL 双发，第一发还被 abort）。
const { data: postsRaw, pending, error: postsErr, refresh: refreshPosts } = useAPI<{
  items?: AuthorPostRow[]
  total?: number
}>('/blog/posts', {
  query: computed(() => ({
    lang: locale.value,
    page: currentPage.value,
    page_size: pageSize.value,
    author: username.value || undefined
  })),
  key: computed(() => `author:posts:${username.value}:${locale.value}:${currentPage.value}`)
})

const displayName = computed(
  () => profile.value?.nickname || profile.value?.username
    || (pending.value ? '' : t('authors.notFoundTitle'))
)
const bio = computed(() => pickLocalized(profile.value?.bio))
const coverImage = computed(() => profile.value?.cover_image?.trim() || '')
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
// 失败态的重试必须同时重取两个端点：资料挂掉时列表往往是好的，
// 只刷一个会让另一半永远停在失败态。
const retryLoad = () => Promise.all([refreshProfile(), refreshPosts()])
// 资料缺失才是"这个作者不存在"；判定时点与口径见 composables/useContentStatus.ts。
const profileMissing = computed(() => !profile.value?.username)

// 发私信入口：只对「已登录 + 拿到对端 id + 不是本人」三者同时成立时出现。
// 中性路径带 ?to= 查询串，applyLocalePrefix 会把查询留在末尾（/en/account/messages?to=7）。
const canMessage = computed(() =>
  Boolean(authStore.accessToken)
  && Boolean(profile.value?.id)
  && profile.value?.id !== authStore.user?.id
)
const messageHref = computed(() =>
  applyLocalePrefix(`/account/messages?to=${profile.value?.id ?? 0}`, locale.value)
)
useContentStatus(profileError, profileMissing)
// 页面分支与 HTTP 状态码共用同一个判定：不公开的资料后端也回 404，
// 所以这里必须走"不存在"文案，不能落到"加载失败，请重试"——那等于对用户说
// 刷新一下就能看到，而真实状态码已经告诉爬虫这个 URL 没了。
const notFound = computed(() => isContentMissing(profileError.value, profileMissing.value))

const totalPages = computed(() => Math.max(1, Math.ceil(total.value / pageSize.value)))
const visiblePages = computed(() => pageWindow(currentPage.value, totalPages.value))
// 用户名按路由参数原样拼：作者主页的 canonical 另由 useSeo 收敛到库里的大小写。
const pageHref = (page: number) =>
  `${applyLocalePrefix(`/authors/${username.value}`, locale.value)}?page=${page}`
const pageLinkClass = (variant: 'default' | 'outline' | 'ghost') =>
  buttonVariants({ variant, size: 'icon' })

const handlePageChange = (page: number) => {
  if (page < 1 || page > totalPages.value) return
  currentPage.value = page
  if (import.meta.client) {
    router.replace({ query: page > 1 ? { page: String(page) } : {} })
    window.scrollTo({ top: 0, behavior: 'smooth' })
  }
}

// 越界页码拉回末页（分享链接里的文章被删光后的旧页码），别停在空列表。
watch([total, currentPage], () => {
  if (total.value === 0) return
  if (currentPage.value > totalPages.value) currentPage.value = totalPages.value
})

// 浏览器前进/后退改的是地址栏，页内状态要跟着回读。
watch(() => route.query.page, (raw) => {
  const next = Math.max(1, Number(raw) || 1)
  if (next !== currentPage.value) currentPage.value = next
})

// 越界页码对爬虫必须 301 回裸作者页：200 空列表会被判 soft 404，自指 canonical 还等于
// 承认每个垃圾页码都是独立页面。时点与 useContentStatus 同轨（app:rendered：数据已落值、
// 状态码还改得动）；`no-store` 防 301 被本页 swr 缓存固化。
if (import.meta.server) {
  const ssrEvent = useRequestEvent()
  useNuxtApp().hooks.hookOnce('app:rendered', () => {
    if (ssrEvent && total.value > 0 && requestedPage > totalPages.value) {
      ssrEvent.node.res.statusCode = 301
      ssrEvent.node.res.setHeader('location', applyLocalePrefix(`/authors/${username.value}`, locale.value))
      ssrEvent.node.res.setHeader('cache-control', 'no-store')
    }
  })
}

useSeo({
  // 不存在的作者不能拿用户名拼标题（任务 85 的同一口径：404 页标题不得由 slug 伪造）
  title: computed(() => {
    if (notFound.value) return t('authors.notFoundTitle')
    return displayName.value
      ? `${displayName.value} · ${t('authors.eyebrow', '作者主页')}`
      : t('authors.eyebrow', '作者主页')
  }),
  description: computed(() => bio.value),
  // 404 与 robots/canonical 同源：不存在的作者页不得声明 index,follow 或自指 canonical
  noindex: notFound,
  // 后端按用户名查人是**不区分大小写**的（/authors/choyeon、/authors/CHOYEON 都是同一份内容，
  // 线上 curl 实测三个变体全部 200）。canonical 若按请求路径自指，任意拼写都会变成一条
  // 自指且可索引的重复页面；钉到库里那一份用户名，所有大小写变体才收敛成一个 URL。
  // 资料没到手（含 404/失败）时传空串 = 沿用按路由派生的口径，noindex 已抑制 canonical。
  url: computed(() => (profile.value?.username ? `/authors/${profile.value.username}` : '')),
  type: 'website'
})
useWebsiteJsonLd()
useBreadcrumbJsonLd([
  { name: t('nav.home', '首页') as string, url: '/' },
  { name: displayName.value || username.value, url: `/authors/${username.value}` }
])
</script>
