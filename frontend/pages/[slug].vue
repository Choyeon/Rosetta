<!--
  独立页（顶级 catchall）：GET /pages/<slug> → marked 渲染 + isomorphic-dompurify 白名单清洗。
  污染 URL 自愈只折叠 %25 层、绝不整体 decode（过度解码会吞掉 %2D 造出死链）；slug 命中文章
  形态时 301/replace 跳 /posts/<slug>，因此新增顶级路由前必须确认不被这里的 catchall 抢占。
  跳走的那条不写状态码（redirectedAway），否则 301 会被 404 闸门覆盖成永久删除。
  sanitize 配置两端共用一份：SSR 直出的 HTML 与客户端重算结果要逐字节一致，否则水合错位。
  标题与 description 只由 useSeo 产出，裸 useHead 会让 <head> 里出现第二条 description。
-->
<template>
  <div class="container max-w-4xl mx-auto py-16">
    <template v-if="pending">
      <Skeleton class="aspect-[16/9] rounded-2xl mb-8" />
      <Skeleton class="h-12 w-3/4 rounded-xl mb-4" />
      <Skeleton class="h-6 w-2/4 rounded-lg mb-10" />
      <div class="flex flex-col gap-3">
        <Skeleton
          v-for="i in 10"
          :key="i"
          class="h-5 rounded"
        />
      </div>
    </template>
    <template v-else-if="pageNotFound">
      <!-- 顶级 catchall 接住每一条 /任意单段 URL，所以"打错网址"的第一印象就是这一屏。
           旧版是一条红色 alert + 一个按钮，既不像 404 也没有第二条出路；
           这里用统一的 404 版式（大号 404 / 标题 / 说明 / 双出口）。 -->
      <div class="flex flex-col items-center justify-center py-16 md:py-24 text-center">
        <div
          class="font-display text-6xl md:text-7xl font-black tracking-tighter text-muted-foreground/25 select-none"
          aria-hidden="true"
        >
          404
        </div>
        <h1 class="mt-3 font-display text-2xl md:text-3xl font-bold tracking-tight">
          {{ t('error.notFoundTitle') }}
        </h1>
        <p class="mt-3 max-w-md text-muted-foreground leading-relaxed">
          {{ t('pages.notFound') }}
        </p>
        <div class="mt-8 flex flex-wrap items-center justify-center gap-3">
          <NuxtLink
            :to="localeHref('/')"
            :class="buttonVariants()"
          >
            <ArrowLeft
              data-icon="inline-start"
              class="mr-2"
            />
            {{ t('pages.backHome') }}
          </NuxtLink>
          <NuxtLink
            :to="localeHref('/posts')"
            :class="buttonVariants({ variant: 'outline' })"
          >
            {{ t('posts.allPosts') }}
          </NuxtLink>
        </div>
      </div>
    </template>

    <!-- 请求失败：后端抖一下不能变成「页面不存在」，给一块可重试的错误面板 -->
    <div
      v-else-if="loadFailure"
      class="rounded-xl border border-destructive/30 bg-destructive/5 p-6 text-sm text-destructive"
    >
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
    <template v-else-if="page">
      <header class="mb-10">
        <div class="inline-flex items-center gap-2 text-xs uppercase tracking-[0.16em] text-muted-foreground mb-3">
          <span class="size-1.5 rounded-full bg-primary" />
          {{ t('pages.page', '页面') }}
        </div>
        <h1 class="font-display text-3xl md:text-5xl font-bold tracking-tight leading-tight">
          {{ title }}
        </h1>
        <div class="flex flex-wrap items-center gap-3 mt-6 text-sm text-muted-foreground">
          <span
            v-if="page.created_at || page.createdAt"
            class="inline-flex items-center gap-1.5"
          >
            <CalendarDays class="size-3.5" />
            {{ formatDate(page.created_at || page.createdAt || '') }}
          </span>
          <span v-if="page.updated_at || page.updatedAt">·</span>
          <span
            v-if="page.updated_at || page.updatedAt"
            class="inline-flex items-center gap-1.5"
          >
            <RefreshCw class="size-3.5" />
            {{ formatDate(page.updated_at || page.updatedAt || '') }}
          </span>
        </div>
      </header>
      <!-- eslint-disable-next-line vue/no-v-html -->
      <article
        class="prose-shadcn prose-shadcn-dark max-w-none"
        v-html="renderedContent"
      />
    </template>
  </div>
</template>

<script setup lang="ts">
import { Skeleton } from '~~/components/ui/skeleton'
import { Button, buttonVariants } from '~~/components/ui/button'
import { ArrowLeft, CalendarDays, RefreshCw } from '@lucide/vue'
import { isContentMissing, useContentStatus } from '~~/composables/useContentStatus'
import { Marked } from 'marked'
import DOMPurify from 'isomorphic-dompurify'
import { stripDuplicateTitleHeading } from '~~/lib/markdown'
import { useI18n } from 'vue-i18n'

definePageMeta({ layout: 'default' })

const { t, locale } = useI18n()
const { localeHref } = useLocaleLink()
const route = useRoute()

// 历史污染 URL（%25E6 式叠加编码）在客户端导航时不经过 Nitro 301 规范化中间件。
// vue-router 已解码一层，params 里可能仍残留 %E6 形态的转义序列。只解 %25 层
// （即 %25XX → %XX），不整体 decode——否则会多解一层把真实 slug 解坏（丢掉 %2D 连字符）。
const collapsePercent = (s: string): string => {
  let cur = s
  for (let i = 0; i < 4 && cur.includes('%25'); i++) {
    const next = cur.replace(/%25/gi, '%')
    if (next === cur) break
    cur = next
  }
  return cur
}

const slugRaw = computed(() => typeof route.params.slug === 'string' ? route.params.slug : '')
const slug = computed(() => collapsePercent(slugRaw.value))
// 逐级解码候选：原始 param → 解一层 %25 → 再解……覆盖多层污染 URL 的自愈查询。
// 末尾追加"连字符修复"形态：早期 url-normalize 中间件过度解码曾产出
// /post-1快速… 这类吞掉 %2D 的死链（post-N 与正文粘连），补回连字符再试一次。
const safeDecode = (s: string): string => {
  try {
    return decodeURIComponent(s)
  } catch {
    return ''
  }
}
const slugCandidates = computed(() => {
  const out: string[] = []
  let cur = slugRaw.value
  for (let i = 0; i < 4 && cur; i++) {
    if (!out.includes(cur)) out.push(cur)
    const decoded = safeDecode(cur)
    if (!decoded || decoded === cur) break
    cur = decoded
  }
  const hyphenRe = /^(post-\d+)(?=[\u4e00-\u9fff])/
  const repaired = out.map(s => s.replace(hyphenRe, '$1-')).find(s => !out.includes(s))
  if (repaired) out.push(repaired)
  return out
})

interface PageDetail {
  id?: number | string
  slug?: string
  title?: unknown
  content?: unknown
  created_at?: string
  createdAt?: string
  updated_at?: string
  updatedAt?: string
}

const pickLocalized = (val: unknown): string => pickLocalizedText(val, locale.value)

const runtimeConfig = useRuntimeConfig()
const unwrapResp = (r: unknown): PageDetail | null => {
  if (r && typeof r === 'object' && 'data' in r && r.data && typeof r.data === 'object') {
    return r.data as PageDetail
  }
  return (r as PageDetail | null) ?? null
}

const nuxtApp = useNuxtApp()
// 自愈 301 与 404 是互斥的两个出口：跳走的那条已经写好了重定向状态码，
// 不能再被下面的状态码闸门覆盖成 404（301 变 404 会把可恢复的死链做成永久删除）。
const redirectedAway = ref(false)
// 请求失败状态：0 = 没有失败。这里是**数据源**的失败，不是页面抛错——
// 页面里 throw createError 会被 contentNotFoundStatus.spec.ts 判成"又在页面里写状态码"，
// 而且渲染出的 error.vue 与响应码会脱节（见 AGENTS §2.3.2）。
const loadFailure = ref(0)
const { data: raw, pending, error, refresh } = useAsyncData<PageDetail | null>(
  computed(() => `page:slug:${slug.value}:${locale.value}`),
  async () => {
    const baseURL = import.meta.server ? runtimeConfig.apiBase : runtimeConfig.public.apiBase
    let primaryStatus = 0
    try {
      const resp = await $fetch(`/pages/${slug.value}`, { baseURL, query: { lang: locale.value } })
      return unwrapResp(resp)
    } catch (e) {
      // 记下主请求的失败形态：404 是"这条 URL 不存在"，其余（5xx / 断网）是"暂时读不到"。
      // 两者混为一谈的话，后端抖一下就把一个真实页面渲染成 404 并回 404 状态码。
      const err = e as { statusCode?: number, status?: number } | null
      primaryStatus = err?.statusCode ?? err?.status ?? 0
      // 404 自愈：顶级路径的 slug 可能其实是文章（如 /post-1-xxx 少了 /posts 前缀），
      // 命中文章则 301（SSR）/ replace（客户端）到真实详情页，避免误报"页面不存在"。
      // 污染 URL 可能叠加多层编码，逐级解码依次尝试。
      for (const cand of slugCandidates.value) {
        try {
          const p = await $fetch(`/blog/posts/${cand}`, { baseURL, query: { lang: locale.value } })
          const pd = unwrapResp(p)
          if (pd?.slug) {
            // handler 在异步上下文中执行，navigateTo 需显式恢复 Nuxt 上下文（NUXT_E1001）
            redirectedAway.value = true
            await nuxtApp.runWithContext(() => navigateTo(`/posts/${pd.slug}`, { redirectCode: 301, replace: true }))
            return null
          }
        } catch { /* 该候选不是文章，试下一个 */ }
      }
      if (primaryStatus !== 404) loadFailure.value = primaryStatus || 503
      return null
    }
  }
)
const retryLoad = () => {
  loadFailure.value = 0
  return refresh()
}

const page = computed<PageDetail | null>(() => {
  const r = raw.value as Record<string, unknown> | PageDetail | null
  if (r && typeof r === 'object' && 'data' in r && r.data && typeof r.data === 'object') {
    return r.data as PageDetail
  }
  return (r as PageDetail | null) ?? null
})
// 顶级 catchall 会接住每一条形如 /任意单段 的 URL：此前"独立页不存在"只渲染兜底 UI、
// 响应仍是 200（并且会被 swr 缓存固化），爬虫会把垃圾 URL 收进索引。
// 闸门口径与其余内容详情页一致（见 composables/useContentStatus.ts），
// 但跳走的那一条除外——它已经带着 301，不能再被改成 404。
const pageMissing = computed(() => !page.value && !redirectedAway.value && !loadFailure.value)
// 状态码 / robots / canonical 同源判定（404 却写 index,follow + 自指 canonical 是两份矛盾信号）
const pageNotFound = computed(() => isContentMissing(error.value, pageMissing.value))
useContentStatus(error, pageMissing)

// 加载中留空（只显站点名，不闪"页面不存在"）；确实取不到内容时用 404 口径标题，
// 不再把 slug 人性化成一个假装存在的页面名（响应侧已由 useContentStatus 回写 404）。
// 请求失败另外给「服务器开小差了」——标题与面板文案必须同口径，不能一个说不存在一个说稍后重试。
const title = computed(() => {
  const name = pickLocalized(page.value?.title)
  if (name) return name
  if (pending.value) return ''
  return loadFailure.value ? t('error.serverErrorTitle') : t('error.notFoundTitle')
})

const md = new Marked()
// isomorphic-dompurify 在 SSR 与客户端两端行为一致，避免 hydration mismatch
const SANITIZE_CONFIG = {
  ADD_TAGS: ['pre', 'code', 'span', 'kbd', 'mark', 'samp', 'var', 'img'],
  ADD_ATTR: ['class', 'src', 'alt', 'loading'],
  ALLOW_UNKNOWN_PROTOCOLS: false,
  WHOLE_DOCUMENT: false,
  FORBID_TAGS: ['script', 'iframe', 'object', 'embed', 'style', 'form', 'input', 'button'],
  FORBID_ATTR: ['onerror', 'onload', 'onclick', 'onmouseover', 'style'],
  IN_PLACE: true
} as const
const renderedContent = computed(() => {
  const rawContent = pickLocalized(page.value?.content)
  if (!rawContent) return ''
  // 模板已渲染页面标题的 h1；正文首行若是同名 `# 标题`，不剥就会在同一文档里出现两个 h1。
  const body = stripDuplicateTitleHeading(rawContent, pickLocalized(page.value?.title))
  try {
    const html = md.parse(body) as string
    return DOMPurify.sanitize(html, SANITIZE_CONFIG as unknown as Parameters<typeof DOMPurify.sanitize>[1])
  } catch (e) {
    console.warn('[pages/slug] markdown render failed', e)
    return ''
  }
})

// meta 描述必须是纯文本：renderedContent 是 sanitized HTML，
// 直接 slice 会把 <p> 等标签碎片喂给搜索引擎和社交卡片。
const metaDescription = computed(() =>
  renderedContent.value
    .replace(/<[^>]+>/g, ' ')
    .replace(/\s+/g, ' ')
    .trim()
    .slice(0, 180)
)

// 日期展示走 useI18nHelpers 的静态月表（口径同 pages/page/[slug].vue：SSR 页不得依赖
// Node/浏览器两侧 Intl 数据版本给出一致字符串，且详情页与列表卡片本就该是同一格式）。
const { formatDate } = useI18nHelpers()

// 标题与 description 由 useSeo 单源产出：这里再裸写一份 useHead 会在 <head> 里
// 留下第二条 name=description（unhead 按入队顺序合并，两份裁切长度不同）。
useSeo({
  title,
  description: metaDescription,
  noindex: pageNotFound,
  type: 'article'
})
useArticleJsonLd({
  slug,
  // 独立页的落地地址是 /<slug>（本页就是那条路由），不是 /posts/<slug>。
  // 缺内容时传空串 → useArticleJsonLd 不输出，404 页不会挂一份指向不存在 URL 的 Article。
  'path': computed(() => (pageNotFound.value ? '' : `/${slug.value}`)),
  title,
  'headline': title,
  'description': metaDescription,
  'publishedAt': computed(() => (page.value?.created_at || page.value?.createdAt || '') as string),
  'updatedAt': computed(() => (page.value?.updated_at || page.value?.updatedAt || '') as string),
  '@type': 'Article'
})
// 面包屑不再单独声明：useArticleJsonLd 的 @graph 里已内嵌同一条
// Home → 本篇 BreadcrumbList（独立页无分类），再调 useBreadcrumbJsonLd
// 等于给爬虫两套面包屑。
</script>
