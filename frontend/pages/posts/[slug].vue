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

          <Skeleton
            v-if="loadingPost && !post"
            class="mt-4 h-12 w-3/4 rounded"
          />
          <h1
            v-else
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
            v-if="post"
            ref="articleEl"
            class="prose-shadcn prose-shadcn-dark mt-12 mx-auto max-w-none"
            v-html="renderedContent"
          />
          <Skeleton
            v-else-if="loadingPost"
            class="mt-12 h-[400px] w-full rounded-2xl"
          />
          <Alert
            v-else-if="loadError"
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

          <div
            v-if="normalizedTags.length"
            class="mt-12 flex flex-wrap gap-2"
          >
            <NuxtLink
              v-for="tag in normalizedTags"
              :key="tag.id"
              :to="`/posts?tag=${tag.slug}`"
            >
              <Badge
                variant="secondary"
                class="tag-colored cursor-pointer border-transparent hover:brightness-[0.98] transition-all"
                :style="{ '--tag-color': tag.color || '' }"
              >
                <Tag class="size-3 mr-1 opacity-70" />
                {{ tag.name }}
              </Badge>
            </NuxtLink>
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
import { Badge } from '~~/components/ui/badge'
import { Separator } from '~~/components/ui/separator'
import { Textarea } from '~~/components/ui/textarea'
import { Button } from '~~/components/ui/button'
import { Skeleton } from '~~/components/ui/skeleton'
import { Alert, AlertDescription, AlertTitle } from '~~/components/ui/alert'
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
  Tag,
  ShieldCheck,
  Send,
  Globe2,
  FileText,
  Hash,
  RefreshCw,
  List
} from '@lucide/vue'
import { watch, nextTick } from 'vue'
import { useReadingProgress, extractTOC, useTOCScrollSpy, estimateReadingStats } from '~~/composables/useReadingUX'
import type { TocItem } from '~~/composables/useReadingUX'

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

const slug = computed(() => route.params.slug as string)
const requestURL = useRequestURL()
const siteOrigin = computed(() => requestURL.origin)

// useFetch 的 URL/query 通过 computed 函数 / Ref 自动响应式，不再显式 watch。
// 关键点：避免 SSR 下 watch: [...] 让 useFetch 认为"只依赖 watch 触发"而跳过初始请求，
// 导致服务端不拉真实数据，页面 SSR 渲染成错误态。
const postSlug = computed(() =>
  typeof route.params.slug === 'string' ? route.params.slug : ''
)
const postFetchLocale = computed(() => locale.value || 'zh')
const postFetchKey = computed(
  () => `post:detail:${postSlug.value}:${postFetchLocale.value}`
)

const { data: postData, pending: loadingPost, error: fetchError } = useAPI<PostDetail>(
  () => `/blog/posts/${postSlug.value}`,
  {
    key: postFetchKey.value,
    query: {
      lang: postFetchLocale
    }
  }
)
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

const postTitle = computed(() => pickLocalized(post.value?.title))
const displayPostTitle = computed(() => {
  if (postTitle.value) return postTitle.value
  // Fallback: decode slug & strip trailing -<number> suffix for a clean human-readable title
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
const authorAvatar = computed(() => post.value?.author?.avatar || '')
const normalizedTags = computed(() => {
  const tags = post.value?.tags || []
  return tags.map(tag => ({
    id: tag.id,
    slug: tag.slug,
    name: pickLocalized(tag.name),
    color: (tag as { color?: string } | undefined)?.color || ''
  })).filter(tag => tag.id && tag.slug)
})

const seoTitle = computed(() => `${pickLocalized(post.value?.title) || displayPostTitle.value} · Rosetta`)
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

useSeoMeta({
  title: () => seoTitle.value,
  description: () => seoDescription.value,
  ogTitle: () => seoTitle.value,
  ogDescription: () => seoDescription.value,
  ogImage: () => absoluteCoverImage.value,
  ogType: 'article',
  articlePublishedTime: () => publishedAt.value,
  articleModifiedTime: () => updatedAt.value,
  articleAuthor: () => authorName.value ? [authorName.value] : [],
  articleTag: () => tagNames.value,
  twitterCard: 'summary_large_image',
  twitterTitle: () => seoTitle.value,
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

const mdRenderer = new Marked(
  {
    renderer: {
      html({ text }) {
        return escapeHtml(text)
      },
      code({ text, lang, escaped }) {
        if (escaped) return `<pre><code class="hljs">${escapeHtml(text)}</code></pre>`
        const rawLanguage = (lang || '').trim().toLowerCase()
        const cleaned = stripLeadingFenceFromCode(text, rawLanguage)
        const language = rawLanguage && hljs.getLanguage(rawLanguage) ? rawLanguage : ''
        let highlighted: string
        if (language) {
          try {
            highlighted = hljs.highlight(cleaned, { language, ignoreIllegals: true }).value
          } catch {
            highlighted = escapeHtml(cleaned)
          }
        } else {
          try {
            highlighted = hljs.highlightAuto(cleaned).value
          } catch {
            highlighted = escapeHtml(cleaned)
          }
        }
        const langClass = language ? ` language-${language}` : ''
        return `<pre><code class="hljs${langClass}">${highlighted}</code></pre>`
      }
    }
  },
  markedHighlight({
    langPrefix: 'hljs language-',
    highlight(code: string, lang: string) {
      const language = lang.trim().toLowerCase()
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
    return DOMPurify.sanitize(html)
  } catch (e) {
    console.error('Markdown parse error:', e)
    return import.meta.server ? escapeHtml(raw) : DOMPurify.sanitize(escapeHtml(raw))
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
})
onActivated(async () => {
  await loadCommentsForCurrentPost()
})
watch([slug, locale, () => post.value?.id], async () => {
  await loadCommentsForCurrentPost()
})

watch([() => post.value, renderedContent, loadingPost], async () => {
  if (loadingPost.value || !post.value) return
  if (!import.meta.client) return
  await nextTick()
  const el = document.querySelector('article.prose-shadcn')
  articleEl.value = el as HTMLElement | null
  tocItems.value = extractTOC(el as HTMLElement | null)
}, { immediate: true })

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
</script>
