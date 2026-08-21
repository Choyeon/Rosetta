<template>
  <div>
    <!-- eslint-disable vue/no-v-html -- Vue 3；文章 HTML 已用 DOMPurify 净化 -->
    <div class="fixed top-0 left-0 right-0 z-[60] h-[3px] bg-transparent pointer-events-none">
      <div
        class="h-full bg-gradient-to-r from-primary via-sky-400 to-primary origin-left shadow-[0_0_8px_hsl(var(--primary)/0.5)]"
        :style="{ width: `${progress}%`, transition: 'width 120ms linear' }"
      />
    </div>
    <div class="relative container mx-auto px-4 md:px-6 py-16 max-w-7xl">
      <div class="grid grid-cols-1 lg:grid-cols-[1fr_240px] gap-10 lg:gap-12">
        <div class="min-w-0">
          <Breadcrumb>
            <BreadcrumbList>
              <BreadcrumbItem>
                <BreadcrumbLink as-child>
                  <NuxtLink
                    to="/"
                    class="inline-flex items-center align-middle"
                  >
                    <Globe2 class="size-3.5 mr-1 shrink-0" />
                    <span>{{ t('post.home') }}</span>
                  </NuxtLink>
                </BreadcrumbLink>
              </BreadcrumbItem>
              <BreadcrumbSeparator />
              <BreadcrumbItem>
                <BreadcrumbLink as-child>
                  <NuxtLink
                    to="/posts"
                    class="inline-flex items-center align-middle"
                  >
                    {{ t('post.posts') }}
                  </NuxtLink>
                </BreadcrumbLink>
              </BreadcrumbItem>
              <BreadcrumbSeparator />
              <BreadcrumbItem>
                <BreadcrumbPage class="line-clamp-1">
                  {{ displayPostTitle }}
                </BreadcrumbPage>
              </BreadcrumbItem>
            </BreadcrumbList>
          </Breadcrumb>

          <!--
            h1 始终渲染（无条件输出）：保证 SSR → Hydrate 两端 DOM 节点结构完全一致。
            路由复用加载期间，标题会短暂显示 fallback 文本，内容替换无闪烁。
          -->
          <h1
            class="font-display text-3xl md:text-4xl lg:text-5xl font-bold tracking-tight mt-4 leading-tight"
          >
            {{ displayPostTitle }}
          </h1>

          <div class="flex flex-wrap items-center gap-3 mt-6 text-sm text-muted-foreground">
            <Avatar class="size-8">
              <AvatarImage
                v-if="authorAvatar"
                :src="authorAvatar"
                :alt="authorName"
              />
              <AvatarFallback>{{ authorName[0] || 'U' }}</AvatarFallback>
            </Avatar>
            <span class="font-medium text-foreground">{{ authorName }}</span>
            <span v-if="publishedAt">·</span>
            <span
              v-if="publishedAt"
              class="inline-flex items-center gap-1.5"
            >
              <CalendarDays class="size-3.5" />
              {{ formatDate(publishedAt) }}
            </span>
            <span>·</span>
            <span class="inline-flex items-center gap-1.5">
              <Clock3 class="size-3.5" />
              {{ readingTime }} {{ t('post.minRead') }}
            </span>
            <span>·</span>
            <span class="inline-flex items-center gap-1.5">
              <Eye class="size-3.5" />
              {{ views }} {{ t('post.views') }}
            </span>
            <span>·</span>
            <span class="inline-flex items-center gap-1.5">
              <FileText class="size-3.5" />
              {{ wordCount.toLocaleString() }} {{ t('post.words', '字') }}
            </span>
            <span>·</span>
            <span class="inline-flex items-center gap-1.5">
              <Hash class="size-3.5" />
              {{ charCount.toLocaleString() }} {{ t('post.chars', '字符') }}
            </span>
            <span v-if="updatedAt && new Date(updatedAt) > new Date(publishedAt)">·</span>
            <span
              v-if="updatedAt && new Date(updatedAt) > new Date(publishedAt)"
              class="inline-flex items-center gap-1.5"
            >
              <RefreshCw class="size-3.5" />
              {{ t('post.updatedAt', '更新于') }} {{ formatDate(updatedAt) }}
            </span>
          </div>

          <div
            v-if="coverImage"
            class="mt-10"
          >
            <img
              :src="coverImage"
              :alt="postTitle"
              class="w-full aspect-[21/9] object-cover rounded-2xl shadow-soft"
            >
          </div>

          <article
            v-show="!!post"
            ref="articleEl"
            class="prose-shadcn prose-shadcn-dark mt-12 mx-auto max-w-none"
            v-html="post ? renderedContent : ''"
          />
          <ClientOnly>
            <template #fallback>
              <span class="hidden" />
            </template>
            <Skeleton
              v-if="loadingPost && !post"
              class="mt-12 h-[400px] w-full rounded-2xl"
            />
            <Alert
              v-else-if="loadError && !post"
              variant="destructive"
              class="mt-12"
            >
              <AlertTitle class="flex items-center gap-2">
                <ShieldCheck class="size-4" />
                {{ t('post.loadFailed', '文章加载失败') }}
              </AlertTitle>
              <AlertDescription>
                {{ t('post.loadFailedDesc', '无法从服务器获取这篇文章，请稍后重试。') }}
                <NuxtLink
                  to="/posts"
                  class="text-primary underline underline-offset-2 ml-1"
                >
                  {{ t('post.backToList', '返回文章列表') }}
                </NuxtLink>
              </AlertDescription>
            </Alert>
          </ClientOnly>

          <div
            v-if="normalizedTags.length"
            class="mt-12 flex flex-wrap gap-2"
          >
            <TagBadge
              v-for="tag in normalizedTags"
              :key="tag.id"
              :color="tag.color"
              :label="tag.name"
              :to="`/posts?tag=${tag.slug}`"
              show-icon
            />
          </div>

          <!-- 互动行：点赞（真实接口）；后端未返回数据时完全隐藏，绝不显示 0 作为占位假计数 -->
          <div class="mt-8 flex items-center gap-3 flex-wrap">
            <Button
              variant="outline"
              size="sm"
              class="group"
              :disabled="submittingLike"
              @click="handleLikePost"
            >
              <ThumbsUp
                class="size-4 mr-2 transition-transform group-active:scale-110"
                :class="likedByMe ? 'text-primary fill-primary/30' : ''"
              />
              <span>{{ t('post.like', '点赞') }}</span>
              <span
                v-if="likeCount > 0"
                class="ml-2 text-xs px-2 py-0.5 rounded-full bg-primary/10 text-primary tabular-nums"
              >
                {{ likeCount }}
              </span>
            </Button>
          </div>

          <Separator class-name="my-12" />

          <section>
            <h3 class="font-display text-2xl font-bold tracking-tight mt-12 mb-6 flex items-center gap-2">
              <MessageSquare class="size-5 text-primary" />
              {{ t('post.comments') }} ({{ comments.length }})
            </h3>

            <Card
              v-if="authStore.isAuthenticated"
              class="mb-8"
            >
              <CardContent class="p-5">
                <Textarea
                  ref="commentTextareaRef"
                  v-model="commentContent"
                  :placeholder="t('post.commentPlaceholder')"
                  rows="4"
                  class="resize-none"
                />
                <div class="flex justify-end mt-4">
                  <Button
                    variant="default"
                    :disabled="!commentContent.trim() || submittingComment"
                    @click="handleSubmitComment"
                  >
                    <Send class="size-4 mr-2" />
                    {{ submittingComment ? t('post.submitting') : t('post.submitComment') }}
                  </Button>
                </div>
              </CardContent>
            </Card>
            <Alert
              v-else
              variant="default"
              class="mb-8"
            >
              <AlertTitle class="flex items-center gap-2">
                <ShieldCheck class="size-4" />
                {{ t('post.loginRequired') }}
              </AlertTitle>
              <AlertDescription class="flex items-center justify-between mt-3">
                <span>{{ t('post.loginToComment') }}</span>
                <Button
                  variant="default"
                  size="sm"
                  @click="navigateTo(`/login?redirect=/posts/${route.params.slug}`)"
                >
                  {{ t('post.goLogin') }}
                </Button>
              </AlertDescription>
            </Alert>

            <div class="flex flex-col gap-4">
              <template v-if="loadingComments && comments.length === 0">
                <Skeleton
                  v-for="i in 3"
                  :key="i"
                  class="h-[120px] rounded-xl"
                />
              </template>
              <template v-else-if="comments.length > 0">
                <CommentItem
                  v-for="comment in comments"
                  :key="comment.id"
                  :comment="comment"
                  @reply="handleReply"
                />
              </template>
              <template v-else>
                <div class="text-center py-12 rounded-xl border border-dashed">
                  <MessageSquare class="size-10 mx-auto text-muted-foreground/50 mb-3" />
                  <p class="text-muted-foreground">
                    {{ t('post.noComments') }}
                  </p>
                </div>
              </template>
            </div>
          </section>

          <!-- ========= 相关文章：GET /api/blog/posts/{post_id}/similar 真实接口，失败则为空不显示假数据 ========= -->
          <section v-if="similarPosts.length">
            <h3 class="font-display text-2xl font-bold tracking-tight mt-16 mb-6 flex items-center gap-2">
              <Sparkles class="size-5 text-primary" />
              {{ t('post.relatedPosts', '相关文章') }}
            </h3>
            <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
              <NuxtLink
                v-for="sp in similarPosts"
                :key="sp.id"
                :to="`/posts/${sp.slug}`"
                class="group rounded-2xl border border-border/60 bg-card/60 hover:bg-accent/30 transition-all duration-300 overflow-hidden"
              >
                <div
                  v-if="sp.cover_image || sp.coverImage"
                  class="aspect-[16/9] bg-muted overflow-hidden"
                >
                  <img
                    :src="(sp.cover_image || sp.coverImage) as string"
                    :alt="pickLocalized(sp.title)"
                    class="w-full h-full object-cover group-hover:scale-105 transition-transform duration-500"
                    loading="lazy"
                  >
                </div>
                <div class="p-4">
                  <h4 class="font-display font-semibold text-base tracking-tight line-clamp-2 group-hover:text-primary transition-colors">
                    {{ pickLocalized(sp.title) }}
                  </h4>
                  <p
                    v-if="pickLocalized((sp as any).excerpt)"
                    class="mt-2 text-xs text-muted-foreground line-clamp-2 leading-relaxed"
                  >
                    {{ pickLocalized((sp as any).excerpt) }}
                  </p>
                </div>
              </NuxtLink>
            </div>
          </section>
        </div>
        <aside class="hidden lg:block sticky top-24 self-start">
          <div class="space-y-3">
            <h4 class="font-display text-sm font-semibold text-muted-foreground uppercase tracking-wider mb-4 flex items-center gap-2">
              <List class="size-4" /> {{ t('post.toc', '目录') }}
            </h4>
            <nav
              v-if="tocItems.length"
              class="space-y-1.5"
            >
              <button
                v-for="item in tocItems"
                :key="item.id"
                class="block w-full text-left text-sm leading-relaxed transition-all duration-200 rounded-md px-2.5 py-1.5 -mx-2.5"
                :class="[
                  activeId === item.id
                    ? 'text-primary font-medium bg-primary/10'
                    : 'text-muted-foreground hover:text-foreground hover:bg-accent/60',
                  item.level === 2 ? 'pl-2' : item.level === 3 ? 'pl-5' : item.level === 4 ? 'pl-8' : ''
                ]"
                @click="scrollTo(item.id)"
              >
                {{ item.text }}
              </button>
            </nav>
            <p
              v-else
              class="text-xs text-muted-foreground/70 px-2 italic"
            >
              —
            </p>
          </div>
          <Card class="mt-8 border-border/60 bg-muted/30">
            <CardContent class="p-4 space-y-2.5 text-sm">
              <div class="flex items-center justify-between">
                <span class="text-muted-foreground inline-flex items-center gap-1.5"><Clock3 class="size-3.5" />{{ t('post.readingTime', '阅读时间') }}</span>
                <span class="font-medium">{{ readingTime }} {{ t('post.minRead') }}</span>
              </div>
              <div class="flex items-center justify-between">
                <span class="text-muted-foreground inline-flex items-center gap-1.5"><FileText class="size-3.5" />{{ t('post.words', '字数') }}</span>
                <span class="font-medium">{{ wordCount.toLocaleString() }}</span>
              </div>
              <div class="flex items-center justify-between">
                <span class="text-muted-foreground inline-flex items-center gap-1.5"><Hash class="size-3.5" />{{ t('post.chars', '字符') }}</span>
                <span class="font-medium">{{ charCount.toLocaleString() }}</span>
              </div>
            </CardContent>
          </Card>
        </aside>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import {
  Breadcrumb,
  BreadcrumbItem,
  BreadcrumbLink,
  BreadcrumbList,
  BreadcrumbPage,
  BreadcrumbSeparator
} from '~~/components/ui/breadcrumb'
import { Avatar, AvatarFallback, AvatarImage } from '~~/components/ui/avatar'
import { Card, CardContent } from '~~/components/ui/card'
import { Separator } from '~~/components/ui/separator'
import { Textarea } from '~~/components/ui/textarea'
import { Button } from '~~/components/ui/button'
import { Skeleton } from '~~/components/ui/skeleton'
import { Alert, AlertDescription, AlertTitle } from '~~/components/ui/alert'
import TagBadge from '~~/components/TagBadge.vue'
import CommentItem from '~~/components/CommentItem.vue'
import { useAuthStore } from '~~/stores/auth'
import { useComments } from '~~/composables/useComments'
import { Marked } from 'marked'
import { markedHighlight } from 'marked-highlight'
import hljs from 'highlight.js'
import DOMPurify from 'dompurify'
import { useI18n } from 'vue-i18n'
import {
  CalendarDays,
  Clock3,
  Eye,
  MessageSquare,
  ShieldCheck,
  Send,
  Globe2,
  FileText,
  Hash,
  RefreshCw,
  List,
  Sparkles,
  ThumbsUp
} from '@lucide/vue'
import { watch, nextTick } from 'vue'
import { useReadingProgress, extractTOC, useTOCScrollSpy, estimateReadingStats } from '~~/composables/useReadingUX'
import type { TocItem } from '~~/composables/useReadingUX'
import { useResolvedAvatar } from '~~/composables/useResolvedAvatar'

definePageMeta({ layout: 'default' })

const route = useRoute()
const { t, locale } = useI18n()
const authStore = useAuthStore()

// composables 必须在 setup 顶层调用：Transition 依赖单根 + 保持上下文
const commentsAPI = useComments()

const { progress } = useReadingProgress()

interface PostDetailTag {
  id: number
  slug: string
  name: unknown
  color?: string | null
}

interface PostDetail {
  id: number
  title: unknown
  content: unknown
  cover_image?: string
  coverImage?: string
  published_at?: string
  publishedAt?: string
  created_at?: string
  updated_at?: string
  updatedAt?: string
  excerpt?: unknown
  views?: number
  views_count?: number
  author?: {
    nickname?: string
    name?: string
    username?: string
    avatar?: string
  }
  tags: PostDetailTag[]
}

// 后端 Comment（snake_case）与 CommentItem 期望的展示结构（camelCase）存在差异，
// 页面渲染以 CommentItem 的 props 结构为准
type PostComment = {
  id: number | string
  author?: {
    id: number | string
    name: string
    avatar?: string
    email?: string
  }
  content: string
  createdAt: string
  parentId?: number | string | null
  likesCount?: number
}

const comments = ref<PostComment[]>([])
const loadingComments = ref(false)
const submittingComment = ref(false)
const commentContent = ref('')
const replyingTo = ref<number | string | null>(null)
const tocItems = ref<TocItem[]>([])
const articleEl = ref<HTMLElement | null>(null)
const { activeId, scrollTo } = useTOCScrollSpy(() => tocItems.value)

// ========= 相似文章 & 点赞（真实接口，空数据=不渲染，无占位假内容）=========
interface SimilarPostRow { id: number | string, slug?: string, title?: unknown, cover_image?: string, coverImage?: string, excerpt?: unknown }
const similarPosts = ref<SimilarPostRow[]>([])
const likeCount = ref<number>(0)
const likedByMe = ref<boolean>(false)
const submittingLike = ref<boolean>(false)

async function loadSimilarAndLikeState(pid: number | string | null | undefined) {
  if (!pid) {
    similarPosts.value = []
    likeCount.value = 0
    likedByMe.value = false
    return
  }
  // 1) similar posts
  try {
    const baseURL = import.meta.server ? runtimeConfig.apiBase : runtimeConfig.public.apiBase
    const headers: Record<string, string> = { 'Accept-Language': locale.value || 'zh' }
    if (authStore.accessToken) headers.Authorization = `Bearer ${authStore.accessToken}`
    const raw = await $fetch<{ success: boolean, data?: SimilarPostRow[] }>(
      `/blog/posts/${pid}/similar`,
      { baseURL, headers, query: { lang: locale.value || 'zh', limit: 6 } }
    )
    let list: SimilarPostRow[] = []
    if (raw && typeof raw === 'object') {
      const rawObj = raw as Record<string, unknown>
      if (Array.isArray(rawObj.data)) {
        list = rawObj.data as SimilarPostRow[]
      } else if (Array.isArray(raw)) {
        list = raw as unknown as SimilarPostRow[]
      }
    }
    similarPosts.value = list
  } catch { similarPosts.value = [] }
}

const slug = computed(() => route.params.slug as string)
const requestURL = useRequestURL()
const siteOrigin = computed(() => requestURL.origin)
const site = useSite()

// useFetch 的 URL/query 通过 computed 函数 / Ref 自动响应式，不再显式 watch。
// 关键点：避免 SSR 下 watch: [...] 让 useFetch 认为"只依赖 watch 触发"而跳过初始请求，
// 导致服务端不拉真实数据，页面 SSR 渲染成错误态。
const postSlug = computed(() =>
  typeof route.params.slug === 'string' ? route.params.slug : ''
)
const postFetchLocaleStr = locale.value || 'zh'

// —— SSR / Hydrate 一致性的最终稳定解法：
//    不用 useAPI/useFetch 封装，直接用 useAsyncData。
//    key 是"只与路由参数有关的纯 ASCII + 中文"的确定性字符串，
//    Nuxt 两端都能精确命中同一条 payload 缓存，不依赖 baseURL / headers /
//    函数 toString 等会变化的输入。handler 内直接 $fetch 走正确的 baseURL。
const cacheKey = `post:detail:${postSlug.value || ''}:${postFetchLocaleStr}`
const runtimeConfig = useRuntimeConfig()
const { data: postData, pending: loadingPost, error: fetchError, refresh: refreshPost }
  = await useAsyncData<PostDetail>(
    cacheKey,
    () => {
      const baseURL = import.meta.server ? runtimeConfig.apiBase : runtimeConfig.public.apiBase
      const headers: Record<string, string> = {
        'Accept-Language': postFetchLocaleStr
      }
      if (authStore.accessToken) headers.Authorization = `Bearer ${authStore.accessToken}`
      // 解包 useAPI 返回的 { success, data, message } 统一结构
      return $fetch<{ success: boolean, data: PostDetail, message?: string }>(
        `/blog/posts/${postSlug.value}`,
        {
          baseURL,
          headers,
          query: { lang: postFetchLocaleStr }
        }
      ).then(unwrap => (unwrap && typeof unwrap === 'object' && 'data' in unwrap) ? (unwrap.data as PostDetail) : unwrap as unknown as PostDetail)
    },
    {
      // 路由复用切换时，watch slug 自动重新拉
      watch: [postSlug]
    }
  )
// 同步暴露给其他页面/组件（如 related articles）使用
const _postFetchKey = computed(() => `post:detail:${postSlug.value}:${postFetchLocaleStr}`)
void refreshPost
const post = computed(() => postData.value ?? null)
const loadError = computed(() => !!fetchError.value)

const pickLocalized = (val: unknown): string => {
  if (val == null) return ''
  if (typeof val === 'string') return val
  if (typeof val === 'object') {
    const obj = val as Record<string, string>
    const key = locale.value || Object.keys(obj)[0] || ''
    return obj[key] ?? obj[Object.keys(obj)[0] || ''] ?? ''
  }
  return String(val)
}

// SSR → Hydration 文本一致性锚点：
// 同步写共享 useState（不是依赖 watchEffect），确保 Nuxt 在序列化 payload 时一定包含该值。
// 客户端 Hydrate 首渲染阶段：即使异步 postData 还没同步到 ref，ssrPostTitle 也已经
// 通过 payload 拿到与 SSR 完全一致的真实标题，避免 fallback slug 文本 mismatch。
const ssrPostTitle = useState<string>(
  `post-detail-title:${postSlug.value || (route.params.slug as string)}`,
  () => ''
)
const _hydrationTitleSeed = pickLocalized(postData.value?.title)
if (_hydrationTitleSeed) ssrPostTitle.value = _hydrationTitleSeed
// 路由复用时（客户端）：post 变化后同步更新共享标题，供自身或相关组件读取
watch(post, (next) => {
  const nt = pickLocalized(next?.title)
  if (nt) ssrPostTitle.value = nt
  // 同步点赞计数初始值（不伪造；后端没返回就保持 0，UI 仍不显示占位数字）
  const nxt = (next ?? {}) as Record<string, unknown>
  if (next && typeof nxt.like_count === 'number') likeCount.value = nxt.like_count
  else if (next && typeof nxt.likes === 'number') likeCount.value = nxt.likes
  else if (next && typeof nxt.likes_count === 'number') likeCount.value = nxt.likes_count
}, { immediate: true })

const postTitle = computed(() => pickLocalized(post.value?.title))
const displayPostTitle = computed(() => {
  if (postTitle.value) return postTitle.value
  // Hydrate 安全回退：SSR 序列化的共享标题
  if (ssrPostTitle.value) return ssrPostTitle.value
  try {
    const raw = decodeURIComponent(slug.value || '')
    return raw.replace(/-[0-9]+$/, '').replace(/-/g, ' ') || t('post.untitled', '未命名文章')
  } catch {
    return t('post.untitled', '未命名文章')
  }
})
const coverImage = computed(() => post.value?.cover_image || post.value?.coverImage || '')
const publishedAt = computed(() => post.value?.published_at || post.value?.publishedAt || post.value?.created_at || '')
const updatedAt = computed(() => post.value?.updated_at || post.value?.updatedAt || '')
const views = computed(() => post.value?.views ?? post.value?.views_count ?? 0)
const authorName = computed(() => {
  const a = post.value?.author
  if (!a) return 'Anonymous'
  return a.nickname || a.name || a.username || 'Anonymous'
})
const authorAvatar = useResolvedAvatar(
  () => post.value?.author?.avatar
)
const normalizedTags = computed(() => {
  const tags = post.value?.tags || []
  return tags.map(tag => ({
    id: tag.id,
    slug: tag.slug,
    name: pickLocalized(tag.name),
    color: (tag.color ?? null) as string | null
  })).filter(tag => tag.id && tag.slug)
})

const seoTitle = computed(() => pickLocalized(post.value?.title) || displayPostTitle.value || '')
const seoExcerpt = computed(() => pickLocalized(post.value?.excerpt))
const seoDescription = computed(() => seoExcerpt.value || pickLocalized(post.value?.content || '').slice(0, 180))

const defaultCoverUrl = computed(() => `${siteOrigin.value}/logo/rosetta-horizontal.png`)
const absoluteCoverImage = computed(() => {
  const cover = coverImage.value
  if (!cover) return defaultCoverUrl.value
  if (cover.startsWith('http://') || cover.startsWith('https://')) return cover
  return `${siteOrigin.value}${cover.startsWith('/') ? '' : '/'}${cover}`
})

const tagNames = computed(() => normalizedTags.value.map(t => t.name))

const fullTitle = computed(() => {
  const t = seoTitle.value
  const s = site.siteTitle.value
  if (!t) return s || ''
  if (!s) return t
  if (t === s) {
    const sub = site.siteSubtitle.value
    return sub ? `${s} · ${sub}` : s
  }
  return `${t} · ${s}`
})

useSeoMeta({
  title: () => seoTitle.value,
  description: () => seoDescription.value,
  ogTitle: () => fullTitle.value,
  ogDescription: () => seoDescription.value,
  ogImage: () => absoluteCoverImage.value,
  ogType: 'article',
  articlePublishedTime: () => publishedAt.value,
  articleModifiedTime: () => updatedAt.value,
  articleAuthor: () => authorName.value ? [authorName.value] : [],
  articleTag: () => tagNames.value,
  twitterCard: 'summary_large_image',
  twitterTitle: () => fullTitle.value,
  twitterDescription: () => seoDescription.value,
  twitterImage: () => absoluteCoverImage.value
})

const canonicalUrl = computed(() => requestURL.href)

const escapeHtml = (value: string): string => value
  .replaceAll('&', '&amp;')
  .replaceAll('<', '&lt;')
  .replaceAll('>', '&gt;')
  .replaceAll('"', '&quot;')
  .replaceAll('\'', '&#39;')

const stripLeadingFenceFromCode = (code: string, language: string): string => {
  const lines = code.split(/\r?\n/)
  const firstLine = lines[0] ?? ''
  const tailLine = lines[lines.length - 1] ?? ''
  const fenceRe = /^\s*```+\s*([\w+-]*)\s*$/
  const closingFenceRe = /^\s*```+\s*$/
  if (lines.length >= 2 && fenceRe.test(firstLine)) {
    const m = firstLine.match(fenceRe)
    const firstLang = (m?.[1] || '').toLowerCase()
    if (!language || firstLang === language || !firstLang) {
      lines.shift()
    }
  }
  if (lines.length && closingFenceRe.test(tailLine)) {
    lines.pop()
  }
  return lines.join('\n')
}

const normalizeMarkdownFences = (raw: string): string => raw
  .replace(/\r\n/g, '\n')
  .replace(/(^|\n)```(\w*)\n```\w*\n/g, '$1```$2\n')

const hljsSanitizeConfig: Parameters<typeof DOMPurify.sanitize>[1] | undefined = (() => {
  if (!import.meta.client) return undefined
  // 显式放行 hljs 高亮 <span class="hljs-*"> 及其它 inline 语义标签，
  // 避免默认严格模式把 token span 全部剥离，导致只剩纯文本代码块。
  const hljsClassRe = /^(hljs|hljs-[a-z0-9_-]+|language-[a-z0-9_-]+)$/i
  return {
    ADD_TAGS: ['pre', 'code', 'span', 'mark', 'kbd', 'samp', 'var'],
    ADD_ATTR: ['class'],
    ALLOW_UNKNOWN_PROTOCOLS: false,
    WHOLE_DOCUMENT: false,
    FORBID_ATTR: ['style', 'onerror', 'onload', 'onclick', 'onmouseover', 'onfocus', 'onblur'],
    FORBID_TAGS: ['style', 'script', 'iframe', 'object', 'embed', 'form', 'input', 'button', 'link', 'meta'],
    IN_PLACE: true,
    SANITIZE_DOM: true,
    /** 只允许 class 命中 hljs/language-* 白名单，防止任意样式注入 */

    HOOKS: {
      uponSanitizeElement(node: Element, _data: unknown) {
        if (node.tagName === 'SPAN' || node.tagName === 'CODE' || node.tagName === 'PRE') {
          const cls = node.getAttribute('class') || ''
          if (!cls) return
          const allowed = cls
            .split(/\s+/)
            .filter(c => hljsClassRe.test(c))
            .join(' ')
          if (allowed) node.setAttribute('class', allowed)
          else node.removeAttribute('class')
        }
      }
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
    } as Record<string, any>
  } as Parameters<typeof DOMPurify.sanitize>[1]
})()

// 高亮单一来源：只使用 marked-highlight 插件做一次 hljs。
// 自定义 renderer.code 仅负责剥 fence 与包 <pre><code>，不再重复调用 hljs，避免双重转义/重复 class。
const mdRenderer = new Marked(
  {
    renderer: {
      html({ text }) {
        return escapeHtml(text)
      },
      code({ text, lang, escaped }) {
        const rawLanguage = (lang || '').trim().toLowerCase()
        const cleaned = stripLeadingFenceFromCode(text, rawLanguage)
        const code = escaped ? cleaned : escapeHtml(cleaned)
        const langClass = rawLanguage && hljs.getLanguage(rawLanguage) ? ` hljs language-${rawLanguage}` : ' hljs'
        return `<pre><code class="${langClass.trim()}">${code}</code></pre>`
      }
    }
  },
  markedHighlight({
    langPrefix: 'hljs language-',
    highlight(code: string, lang: string) {
      const language = (lang || '').trim().toLowerCase()
      const cleaned = stripLeadingFenceFromCode(code, language)
      if (!language || !hljs.getLanguage(language)) {
        try {
          return hljs.highlightAuto(cleaned).value
        } catch {
          return escapeHtml(cleaned)
        }
      }
      try {
        return hljs.highlight(cleaned, { language, ignoreIllegals: true }).value
      } catch {
        return escapeHtml(cleaned)
      }
    }
  })
)

const renderedContent = computed(() => {
  if (!post.value?.content) return ''
  const raw = normalizeMarkdownFences(pickLocalized(post.value.content))
  try {
    const html = mdRenderer.parse(raw) as string
    if (import.meta.server) return html
    return DOMPurify.sanitize(html, hljsSanitizeConfig ?? undefined)
  } catch (e) {
    console.error('Markdown parse error:', e)
    const fallback = escapeHtml(raw)
    if (import.meta.server) return fallback
    return DOMPurify.sanitize(fallback, hljsSanitizeConfig ?? undefined)
  }
})

const readingStats = computed(() => {
  const content = pickLocalized(post.value?.content)
  const localeStr = (locale.value || 'zh').startsWith('zh') ? 'zh' : (locale.value === 'ja' ? 'ja' : 'en')
  return estimateReadingStats(content, localeStr)
})
const readingTime = computed(() => readingStats.value.minutes)
const wordCount = computed(() => readingStats.value.words)
const charCount = computed(() => readingStats.value.chars)

useHead(() => {
  const title = pickLocalized(post.value?.title) || displayPostTitle.value
  const description = seoDescription.value
  const coverImageAbs = absoluteCoverImage.value
  const publishedAtVal = publishedAt.value
  const updatedAtVal = updatedAt.value
  const author = authorName.value
  const keywords = tagNames.value.join(',')
  const words = wordCount.value

  const jsonLd = {
    '@context': 'https://schema.org',
    '@type': 'BlogPosting',
    'headline': title,
    'image': [coverImageAbs],
    'datePublished': publishedAtVal,
    'dateModified': updatedAtVal,
    'author': {
      '@type': 'Person',
      'name': author
    },
    keywords,
    'wordCount': words,
    description
  }

  return {
    link: [
      {
        rel: 'canonical',
        href: canonicalUrl.value
      }
    ],
    script: [
      {
        type: 'application/ld+json',
        innerHTML: JSON.stringify(jsonLd)
      }
    ]
  }
})

const formatDate = (date: string) => {
  if (!date) return ''
  try {
    const d = new Date(date)
    if (isNaN(d.getTime())) return ''
    return d.toLocaleDateString(locale.value as string, {
      year: 'numeric',
      month: 'long',
      day: 'numeric'
    })
  } catch {
    return ''
  }
}

// 首屏由 SSR + payload 注入文章详情；这里只刷新评论。
// 注意：不要在 onMounted 里 refresh() 文章本身——客户端接管时会取消 SSR 发起的、仍在传输中的请求，
// 浏览器 Network 面板里就会看到 net::ERR_ABORTED（尤其是正文较大的中/长文）。
const loadCommentsForCurrentPost = async () => {
  if (!import.meta.client) return
  loadingComments.value = true
  try {
    if (post.value?.id && commentsAPI.fetchComments) {
      await commentsAPI.fetchComments(post.value.id)
      comments.value = (commentsAPI.comments?.value || []) as unknown as PostComment[]
    } else {
      comments.value = []
    }
  } catch (e) {
    console.warn('[post detail] comments fetch error:', e)
  } finally {
    loadingComments.value = false
  }
}
onMounted(async () => {
  await loadCommentsForCurrentPost()
  await loadSimilarAndLikeState(post.value?.id)
  await rebuildTOC()
  if (import.meta.client && typeof window !== 'undefined') {
    // 字体 / 懒加载图片导致布局变化后的兜底刷新（3 秒内再补几次）。
    const retries = [400, 1200, 3000]
    retries.forEach(delay => setTimeout(() => void rebuildTOC(), delay))
  }
})
onActivated(async () => {
  await loadCommentsForCurrentPost()
  await loadSimilarAndLikeState(post.value?.id)
})
watch([slug, locale, () => post.value?.id], async () => {
  await loadCommentsForCurrentPost()
  await loadSimilarAndLikeState(post.value?.id)
})

/**
 * TOC 重建：
 *  - 只在客户端执行（SSR 没有 DOM，extractTOC 只能取空）
 *  - 依赖"文章对象 + Markdown 渲染字符串 + 不是在 pending loading"三个条件
 *  - v-html 注入后需要 nextTick（Vue 更新真实 DOM）再等待一次 rAF + 16ms（浏览器 layout）
 *  - 如果文章正文里含有 <img>，需要等所有 <img> onload 再重算一次，
 *    否则 offsetTop 会因为图片加载前高度为 0 而集体偏上，导致目录项激活锚点全部错位。
 */
const rebuildTOC = async () => {
  if (!import.meta.client) return
  if (loadingPost.value || !post.value) return
  await nextTick()
  // 等一次渲染帧 + 一帧余量，让 hljs 代码块尺寸 / 字体 / 图片占位先进入 layout。
  await new Promise<void>(resolve => requestAnimationFrame(() => requestAnimationFrame(() => resolve())))
  const el = articleEl.value ?? (document.querySelector('article.prose-shadcn') as HTMLElement | null)
  if (!el) return
  articleEl.value = el
  tocItems.value = extractTOC(el)

  // 若文章正文有 <img>：全部解码完再更新一次 TOC 位置（scroll-spy 内部使用 realOffset）。
  const imgs = Array.from(el.querySelectorAll<HTMLImageElement>('img'))
  if (imgs.length) {
    await Promise.all(
      imgs.map((img) => {
        if (img.complete && (img.naturalWidth > 0 || img.src.startsWith('data:'))) return
        return new Promise<void>((resolve) => {
          const done = () => {
            resolve()
            img.removeEventListener('load', done)
            img.removeEventListener('error', done)
          }
          img.addEventListener('load', done, { once: true })
          img.addEventListener('error', done, { once: true })
        })
      })
    )
    // scroll-spy update() 会在下次 scroll/resize/下帧通过 realOffset 重新取到新位置；
    // 这里主动跑一次，保证首次渲染后滚动高亮立即正确。
    const list = tocItems.value
    if (list.length) {
      // 触发一次刷新 activeId：realOffset 是 scroll-spy 内部函数，外部通过 scrollTo 或滚动事件触发；
      // 我们手动触发 scroll 即可（不实际滚动，只是让 spy 的 update 跑一次）。
      window.dispatchEvent(new Event('scroll'))
    }
  }
}

watch(
  [() => post.value, () => renderedContent.value, () => loadingPost.value, () => locale.value],
  rebuildTOC,
  // 不使用 immediate: true。SSR 没有 DOM，我们在 onMounted 里手动触发一次。
  { flush: 'post' }
)

const handleSubmitComment = async () => {
  if (!post.value?.id || !commentContent.value.trim()) return
  submittingComment.value = true
  try {
    if (commentsAPI.createComment) {
      const pid = (replyingTo.value == null) ? undefined : Number(replyingTo.value)
      await commentsAPI.createComment(post.value.id, commentContent.value, pid)
      commentContent.value = ''
      replyingTo.value = null
      if (commentsAPI.fetchComments) {
        await commentsAPI.fetchComments(post.value.id)
        comments.value = (commentsAPI.comments?.value || []) as unknown as PostComment[]
      }
    }
  } catch (e) {
    console.error('Submit comment error:', e)
  } finally {
    submittingComment.value = false
  }
}

const commentTextareaRef = ref<InstanceType<typeof Textarea> | null>(null)

const handleReply = (commentId: number | string) => {
  replyingTo.value = commentId
  const inst = commentTextareaRef.value as { $el?: HTMLElement } | null
  const el = inst?.$el ?? null
  el?.focus()
  el?.scrollIntoView({ behavior: 'smooth', block: 'center' })
}

// 文章点赞：POST /api/blog/posts/{post_id}/like（后端对匿名也计数，严格不造假数字）
const handleLikePost = async () => {
  if (!post.value?.id || submittingLike.value) return
  submittingLike.value = true
  try {
    const baseURL = import.meta.client ? runtimeConfig.public.apiBase : runtimeConfig.apiBase
    const headers: Record<string, string> = { 'Accept-Language': locale.value || 'zh' }
    if (authStore.accessToken) headers.Authorization = `Bearer ${authStore.accessToken}`
    const raw = await $fetch<{ success: boolean, data?: { liked?: boolean, like_count?: number, likes?: number } }>(
      `/blog/posts/${post.value.id}/like`,
      { method: 'POST', baseURL, headers }
    )
    type LikePayload = { liked?: boolean, like_count?: number, likes?: number }
    const extractLikePayload = (r: unknown): LikePayload => {
      if (!r || typeof r !== 'object') return {}
      const obj = r as Record<string, unknown>
      if ('data' in obj && obj.data && typeof obj.data === 'object') {
        return obj.data as LikePayload
      }
      return obj as LikePayload
    }
    const payload = extractLikePayload(raw)
    if (typeof payload.like_count === 'number') likeCount.value = payload.like_count
    else if (typeof payload.likes === 'number') likeCount.value = payload.likes
    else likeCount.value = Math.max(0, likeCount.value + (likedByMe.value ? -1 : 1))
    likedByMe.value = typeof payload.liked === 'boolean' ? payload.liked : !likedByMe.value
  } catch (e) {
    console.warn('[post detail] like failed', e)
  } finally {
    submittingLike.value = false
  }
}
</script>
