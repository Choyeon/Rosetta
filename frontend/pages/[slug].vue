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
    <template v-else-if="loadError || !page">
      <div class="rounded-xl border border-destructive/30 bg-destructive/5 p-6 text-sm text-destructive mb-8">
        {{ t('pages.notFound', '无法加载该页面，可能已被删除或尚未发布。') }}
      </div>
      <Button
        variant="outline"
        @click="navigateTo('/')"
      >
        <ArrowLeft
          data-icon="inline-start"
          class="mr-2"
        />
        {{ t('pages.backHome', '返回首页') }}
      </Button>
    </template>
    <template v-else>
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
import { Button } from '~~/components/ui/button'
import { ArrowLeft, CalendarDays, RefreshCw } from '@lucide/vue'
import { Marked } from 'marked'
import DOMPurify from 'isomorphic-dompurify'
import { useI18n } from 'vue-i18n'

definePageMeta({ layout: 'default' })

const { t, locale } = useI18n()
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

const runtimeConfig = useRuntimeConfig()
const unwrapResp = (r: unknown): PageDetail | null => {
  if (r && typeof r === 'object' && 'data' in r && r.data && typeof r.data === 'object') {
    return r.data as PageDetail
  }
  return (r as PageDetail | null) ?? null
}

const nuxtApp = useNuxtApp()
const { data: raw, pending, error } = useAsyncData<PageDetail | null>(
  computed(() => `page:slug:${slug.value}:${locale.value}`),
  async () => {
    const baseURL = import.meta.server ? runtimeConfig.apiBase : runtimeConfig.public.apiBase
    try {
      const resp = await $fetch(`/pages/${slug.value}`, { baseURL, query: { lang: locale.value } })
      return unwrapResp(resp)
    } catch {
      // 404 自愈：顶级路径的 slug 可能其实是文章（如 /post-1-xxx 少了 /posts 前缀），
      // 命中文章则 301（SSR）/ replace（客户端）到真实详情页，避免误报"页面不存在"。
      // 污染 URL 可能叠加多层编码，逐级解码依次尝试。
      for (const cand of slugCandidates.value) {
        try {
          const p = await $fetch(`/blog/posts/${cand}`, { baseURL, query: { lang: locale.value } })
          const pd = unwrapResp(p)
          if (pd?.slug) {
            // handler 在异步上下文中执行，navigateTo 需显式恢复 Nuxt 上下文（NUXT_E1001）
            await nuxtApp.runWithContext(() => navigateTo(`/posts/${pd.slug}`, { redirectCode: 301, replace: true }))
            return null
          }
        } catch { /* 该候选不是文章，试下一个 */ }
      }
      return null
    }
  }
)

const page = computed<PageDetail | null>(() => {
  const r = raw.value as Record<string, unknown> | PageDetail | null
  if (r && typeof r === 'object' && 'data' in r && r.data && typeof r.data === 'object') {
    return r.data as PageDetail
  }
  return (r as PageDetail | null) ?? null
})
const loadError = computed(() => !!error.value || !page.value)

const title = computed(() => pickLocalized(page.value?.title) || slug.value)

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
  try {
    const html = md.parse(rawContent) as string
    return DOMPurify.sanitize(html, SANITIZE_CONFIG as unknown as Parameters<typeof DOMPurify.sanitize>[1])
  } catch (e) {
    console.warn('[pages/slug] markdown render failed', e)
    return ''
  }
})

const formatDate = (iso: string) => {
  if (!iso) return ''
  try {
    const d = new Date(iso)
    if (isNaN(d.getTime())) return ''
    return d.toLocaleDateString(locale.value as string, { year: 'numeric', month: 'long', day: 'numeric' })
  } catch { return '' }
}

useHead(() => ({
  title: title.value,
  meta: [{ name: 'description', content: renderedContent.value.slice(0, 180) }]
}))

useSeo({
  title,
  description: computed(() => renderedContent.value.slice(0, 180)),
  type: 'article'
})
useArticleJsonLd({
  slug,
  title,
  'headline': title,
  'description': computed(() => renderedContent.value.slice(0, 180)),
  'publishedAt': computed(() => (page.value?.created_at || page.value?.createdAt || '') as string),
  'updatedAt': computed(() => (page.value?.updated_at || page.value?.updatedAt || '') as string),
  '@type': 'Article'
})
useBreadcrumbJsonLd([
  { name: t('nav.home', '首页') as string, url: '/' },
  { name: title.value || slug.value, url: `/${slug.value}` }
])
</script>
