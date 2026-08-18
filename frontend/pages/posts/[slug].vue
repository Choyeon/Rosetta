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
              variant="outline"
              class="cursor-pointer hover:bg-accent transition-colors"
            >
              <Tag class="size-3 mr-1" />
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
import { usePosts } from '~~/composables/usePosts'
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

const mockPost = ref<PostDetail | null>(null)

const { data: postData, pending: loadingPost, error: fetchError, refresh } = useAPI<PostDetail>(
  `/blog/posts/${slug.value}`,
  {
    key: 'post:detail:' + locale.value + ':' + (typeof route.params.slug === 'string' ? route.params.slug : ''),
    query: {
      lang: locale.value
    }
  }
)

const post = computed(() => postData.value ?? mockPost.value ?? null)
const loadError = computed(() => !!fetchError.value && !mockPost.value)

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
    name: pickLocalized(tag.name)
  })).filter(tag => tag.id && tag.slug)
})

const seoTitle = computed(() => `${pickLocalized(post.value?.title) || displayPostTitle.value} · Rosetta`)
const seoExcerpt = computed(() => pickLocalized((post.value as any)?.excerpt))
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

/**
 * Markdown renderer with mature highlight.js syntax highlighting.
 * - Uses highlight.js as the tokenizer (190+ built-in languages)
 * - `langPrefix: 'hljs language-'` ensures `language-<lang>` class is set on <code>
 *   so highlight.js CSS selectors match regardless of the token palette.
 * - Unknown / missing languages fall back to plaintext (no crash).
 */
const mdRenderer = new Marked(
  markedHighlight({
    langPrefix: 'hljs language-',
    highlight(code: string, lang: string) {
      try {
        const language = hljs.getLanguage(lang) ? lang : 'plaintext'
        return hljs.highlight(code, { language, ignoreIllegals: true }).value
      } catch {
        return code
      }
    }
  })
)

const renderedContent = computed(() => {
  if (!post.value?.content) return ''
  const raw = pickLocalized(post.value.content)
  try {
    const html = mdRenderer.parse(raw) as string
    // DOMPurify 依赖浏览器 DOM；SSR 时直接返回 marked 输出的 HTML，
    // 这样搜索引擎能在 SSR 的 HTML 里抓到正文结构，不至于浪费 SSR 开启的好处。
    // 客户端（浏览器）阶段用 DOMPurify 再净化一遍，避免 XSS。
    if (import.meta.server) return html
    return DOMPurify.sanitize(html)
  } catch (e) {
    console.error('Markdown parse error:', e)
    if (import.meta.server) return raw
    return DOMPurify.sanitize(raw)
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
    headline: title,
    image: [coverImageAbs],
    datePublished: publishedAtVal,
    dateModified: updatedAtVal,
    author: {
      '@type': 'Person',
      name: author
    },
    keywords,
    wordCount: words,
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

// 兜底：首次挂载 + keep-alive 激活都 refresh 一次文章主体 + 评论
// 防止 SSR 阶段 useFetch Promise pending 卡住、或"从详情 A → 列表 → 详情 B（组件复用不重 mount）
// → 内容仍是 A"这类因为 keep-alive 导致的旧数据残留。
let didFirstMount = false
const fallbackDetailRefresh = async () => {
  if (!import.meta.client) return
  try {
    await refresh()
  } catch (e) {
    console.warn('[post detail] forced refresh failed:', e)
  }
  loadingComments.value = true
  try {
    if (post.value?.id) {
      if (commentsAPI.fetchComments) {
        await commentsAPI.fetchComments(post.value.id)
        comments.value = (commentsAPI.comments?.value || []) as unknown as PostComment[]
      }
    }
  } catch (e) {
    console.warn('[post detail] comments fetch error:', e)
  } finally {
    loadingComments.value = false
  }
}
onMounted(async () => {
  didFirstMount = true
  await fallbackDetailRefresh()
})
onActivated(async () => {
  await fallbackDetailRefresh()
})

watch([() => post.value, renderedContent, loadingPost], async () => {
  if (loadingPost.value || !post.value) return
  if (!import.meta.client) return
  await nextTick()
  const el = document.querySelector('article.prose-shadcn')
  articleEl.value = el as HTMLElement | null
  tocItems.value = extractTOC(el as HTMLElement | null)
}, { immediate: true })

// =====================================================
// Fallback: build a complete, rich mock post object
// so content renders even when the FastAPI backend is down
// =====================================================
const buildMockDetailPost = (postSlug: string, fallbackTitle: string) => {
  const coverImages = [
    'https://images.unsplash.com/photo-1555066931-4365d14bab8c?w=1600&q=80',
    'https://images.unsplash.com/photo-1517694712202-14dd9538aa97?w=1600&q=80',
    'https://images.unsplash.com/photo-1498050108023-c5249f4df085?w=1600&q=80',
    'https://images.unsplash.com/photo-1542831371-29b0f74f9713?w=1600&q=80',
    'https://images.unsplash.com/photo-1504639725590-34d0984388bd?w=1600&q=80'
  ]
  const hash = [...(postSlug || 'a')].reduce((s, c) => s + c.charCodeAt(0), 0)
  const cover = coverImages[hash % coverImages.length]
  const viewsMock = 480 + (hash % 1800)
  const d = new Date()
  d.setDate(d.getDate() - (hash % 30))
  const publishedStr = d.toISOString()

  const titleZh = fallbackTitle || '只是如此浏览那些'
  const titleEn = titleZh

  const markdown = `# ${titleZh}

> 这是一篇**离线演示文章**：当前后端服务未连接，以下内容由本地 Mock 数据生成，用于演示排版、组件和样式效果。
> 等 FastAPI 服务运行在 \`localhost:8000\` 后，数据将自动替换为真实内容。

## 为什么这篇文章依然可见？

即便后端接口暂时离线，前端依然提供完整的 Markdown 文章内容，确保读者**无论如何都能看到排版渲染效果**而不是面对空白页。这种策略很适合开发阶段、或在弱网环境下提供 Fallback 体验。

---

## 核心实现要点

一个健壮的文章详情页，通常要考虑以下 6 点：

1. **面包屑（Breadcrumb）**：首页 → 文章列表 → 当前文章，且图标与文字严格对齐
2. **数据加载态**：\`loadingPost\` 控制骨架屏（Skeleton）出现与消失
3. **离线 Fallback**：接口失败时从本地 Mock 数据填充，不让整页空白
4. **Markdown 渲染**：使用 \`marked\` 解析器，配套 \`prose-shadcn\` 样式体系
5. **多语言字段**：title/excerpt/content 支持 \`{ zh, en }\` 结构自动按 locale 取值
6. **评论系统**：未登录显示登录引导；登录后可提交；加载中显示骨架

### 代码片段示例

下面是一段典型的 \`useFetch\` + 错误回退逻辑：

\`\`\`typescript
const { data, error } = await useFetch<PostDetail>(
  () => \`/api/blog/posts/\${slug.value}?lang=\${locale.value}\`
)

if (error.value || !data.value) {
  post.value = buildMockDetailPost(slug.value, displayTitle.value)
} else {
  post.value = data.value
}
\`\`\`

---

## 渲染效果展示

### 代码块语法高亮

\`\`\`python
# Python 后端 FastAPI 路由示例
from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session
from . import schemas, crud, deps

app = FastAPI(title="Rosetta Blog API")

@app.get("/api/blog/posts/{slug}", response_model=schemas.PostOut)
def get_post(slug: str, db: Session = Depends(deps.get_db)):
    post = crud.post.get_by_slug(db, slug=slug)
    if not post:
        raise HTTPException(404, "Post not found")
    crud.post.incr_views(db, post.id)
    return post
\`\`\`

### 引用块

> “简单是可靠的先决条件。” —— Edsger W. Dijkstra
>
> 每删除一行冗余代码，都是在为未来的自己减少一份维护成本。

### 表格

| 组件模块 | 技术栈 / 依赖 | 作用 |
|---|---|---|
| 首页 Hero | Bing Daily API + Unsplash Fallback | 每日壁纸、最近 7 天切换、图片版权卡片 |
| 文章卡片 | PostCard.vue (default/compact) | 精选 / 最新 / 分类 / 搜索结果统一复用 |
| 主题切换 | ThemeToggle.vue + clip-path | 从点击位置扩散的暗/亮模式动画 |
| 语言切换 | flag-icons CDN + LocaleSwitcher | 🇨🇳🇺🇸🇯🇵🇹🇼 四国旗图标、cookie 持久化 |
| 调色盘 | ThemePaletteSwitcher.vue + View Transitions API | 多套品牌主题色，扩散切换动画 |

### 有序列表（写作工作流）

1. 平时用 Obsidian 本地积累卡片笔记
2. 每周挑选 3~5 张卡片进行结构化展开
3. 补全代码示例、图示、引用来源
4. 过一遍 Lighthouse + 断网 Mock 自检
5. 发布并同步 RSS、邮件订阅

### 无序列表（前端依赖清单）

- Nuxt 4 · Vue 3 · TypeScript
- Tailwind CSS 3 · shadcn/ui · Radix Vue
- Pinia 2 · @vueuse/core · vee-validate 4
- marked · lucide-vue-next · vue-sonner

---

## 主题色切换（彩蛋）

右上角导航栏里除了明暗切换，还多了一个**调色盘图标**。点击可以切换 6 套品牌配色：

- 靛青 Indigo（默认）
- 翡翠 Emerald
- 琥珀 Amber
- 玫瑰 Rose
- 紫罗兰 Violet
- 天青 Sky

实现方式基于掘金文章《来实现一下 element-plus 中的主题切换动画》，采用 **View Transitions API**，从点击位置用圆形裁切扩散，与暗/亮模式的切换动画同规格。

---

## 结语

> 写博客这件事，本质上是把脑子里那些模糊的想法，**强制**变成一段可被他人阅读的结构化文字。
>
> 在这个过程中，你会惊讶地发现：原来自己对很多概念的理解，其实还停留在“好像会了”的阶段。

祝阅读愉快。🚀
`

  return {
    id: 9000 + (hash % 1000),
    slug: postSlug,
    title: { zh: titleZh, en: titleEn },
    excerpt: {
      zh: '后端离线场景下的前端 Fallback 演示文章，展示 Markdown 排版、代码块、表格、引用等完整渲染效果。',
      en: 'A demo article rendered from local mocks when the API backend is unavailable.'
    },
    cover_image: cover,
    category: {
      id: 1,
      slug: 'frontend',
      name: { zh: '前端开发', en: 'Frontend' }
    },
    tags: [
      { id: 1, slug: 'nuxt', name: { zh: 'Nuxt', en: 'Nuxt' } },
      { id: 2, slug: 'vue', name: { zh: 'Vue 3', en: 'Vue 3' } },
      { id: 3, slug: 'markdown', name: { zh: 'Markdown', en: 'Markdown' } },
      { id: 4, slug: 'offline-first', name: { zh: '离线优先', en: 'Offline First' } }
    ],
    author: {
      id: 1,
      name: 'Choyeon',
      nickname: 'Choyeon',
      username: 'choyeon',
      avatar: 'https://images.unsplash.com/photo-1535713875002-d1d0cf377fde?w=200&q=80'
    },
    published_at: publishedStr,
    created_at: publishedStr,
    updated_at: publishedStr,
    views: viewsMock,
    views_count: viewsMock,
    comments_count: 3,
    likes_count: 12 + (hash % 80),
    content: { zh: markdown, en: markdown }
  }
}

watch([fetchError, postData], () => {
  if (import.meta.client && fetchError.value && !postData.value) {
    if (import.meta.dev) {
      mockPost.value = buildMockDetailPost(slug.value, displayPostTitle.value)
    }
  }
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

<style>
.prose-shadcn {
  color: hsl(var(--foreground));
  line-height: 1.75;
  font-size: 1rem;
}
.prose-shadcn p {
  margin: 1.2em 0;
}
.prose-shadcn h1,
.prose-shadcn h2,
.prose-shadcn h3,
.prose-shadcn h4 {
  font-family: inherit;
  font-weight: 700;
  letter-spacing: -0.02em;
  line-height: 1.2;
  margin-top: 2em;
  margin-bottom: 0.8em;
}
.prose-shadcn h2 { font-size: 1.6rem; }
.prose-shadcn h3 { font-size: 1.3rem; }
.prose-shadcn h4 { font-size: 1.1rem; }
.prose-shadcn a {
  color: hsl(var(--primary));
  text-decoration: underline;
  text-underline-offset: 3px;
}
.prose-shadcn a:hover {
  opacity: 0.8;
}
.prose-shadcn ul,
.prose-shadcn ol {
  margin: 1.2em 0;
  padding-left: 1.5em;
}
.prose-shadcn li {
  margin: 0.4em 0;
}
.prose-shadcn ul li::marker {
  color: hsl(var(--primary));
}
.prose-shadcn blockquote {
  border-left: 4px solid hsl(var(--primary) / 0.4);
  padding-left: 1.2em;
  margin: 1.5em 0;
  color: hsl(var(--muted-foreground));
  font-style: italic;
}
.prose-shadcn code {
  background: hsl(var(--muted));
  padding: 0.2em 0.45em;
  border-radius: 0.35em;
  font-size: 0.9em;
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
}
.prose-shadcn pre {
  background: hsl(var(--muted));
  padding: 1.2em 1.4em;
  border-radius: 0.75em;
  overflow-x: auto;
  margin: 1.5em 0;
}
.prose-shadcn pre code {
  background: transparent;
  padding: 0;
  font-size: 0.9em;
}
.prose-shadcn img {
  border-radius: 0.75em;
  margin: 1.5em 0;
  max-width: 100%;
}
.prose-shadcn hr {
  border: none;
  border-top: 1px solid hsl(var(--border));
  margin: 2em 0;
}
.prose-shadcn table {
  width: 100%;
  border-collapse: collapse;
  margin: 1.5em 0;
  font-size: 0.95em;
}
.prose-shadcn th,
.prose-shadcn td {
  padding: 0.75em 1em;
  border-bottom: 1px solid hsl(var(--border));
  text-align: left;
}
.prose-shadcn th {
  background: hsl(var(--muted));
  font-weight: 600;
}
</style>
