<template>
  <div class="container max-w-4xl mx-auto py-16">
    <template v-if="pending">
      <Skeleton class="aspect-[16/9] rounded-2xl mb-8" />
      <Skeleton class="h-12 w-3/4 rounded-xl mb-4" />
      <Skeleton class="h-6 w-2/4 rounded-lg mb-10" />
      <div class="space-y-3">
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
        <ArrowLeft class="size-4 mr-2" />
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
import { useAPI } from '~~/composables/useApi'
import { Marked } from 'marked'
import DOMPurify from 'dompurify'
import { useI18n } from 'vue-i18n'

definePageMeta({ layout: 'default' })

const { t, locale } = useI18n()
const route = useRoute()

const slug = computed(() => typeof route.params.slug === 'string' ? route.params.slug : '')

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

const { data: raw, pending, error } = await useAPI<PageDetail>(`/pages/${slug.value}`, {
  query: { lang: locale.value },
  key: computed(() => `page:slug:${slug.value}:${locale.value}`)
})

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
const renderedContent = computed(() => {
  const rawContent = pickLocalized(page.value?.content)
  if (!rawContent) return ''
  try {
    const html = md.parse(rawContent) as string
    // 非客户端环境 DOMPurify 不可用，直接跳过：返回原始 HTML，服务端渲染场景下由后端保证安全（内容通过后台创建）
    if (!import.meta.client) return html
    return DOMPurify.sanitize(html, {
      ADD_TAGS: ['pre', 'code', 'span', 'kbd', 'mark', 'samp', 'var', 'img'],
      ADD_ATTR: ['class', 'src', 'alt', 'loading'],
      ALLOW_UNKNOWN_PROTOCOLS: false,
      WHOLE_DOCUMENT: false,
      FORBID_TAGS: ['script', 'iframe', 'object', 'embed', 'style', 'form', 'input', 'button'],
      FORBID_ATTR: ['onerror', 'onload', 'onclick', 'onmouseover', 'style'],
      IN_PLACE: true
    })
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
</script>
