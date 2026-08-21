<template>
  <div class="container py-16 max-w-5xl mx-auto">
    <div class="mb-10">
      <Breadcrumb class="mb-6">
        <BreadcrumbList>
          <BreadcrumbItem>
            <BreadcrumbLink as-child>
              <NuxtLink to="/">{{ t('series.home', '首页') }}</NuxtLink>
            </BreadcrumbLink>
          </BreadcrumbItem>
          <BreadcrumbSeparator />
          <BreadcrumbItem>
            <BreadcrumbLink as-child>
              <NuxtLink to="/series">{{ t('series.all', '系列') }}</NuxtLink>
            </BreadcrumbLink>
          </BreadcrumbItem>
          <BreadcrumbSeparator />
          <BreadcrumbItem>
            <BreadcrumbPage>{{ pickStr(series?.title) || pickStr(series?.name || '') || params.slug }}</BreadcrumbPage>
          </BreadcrumbItem>
        </BreadcrumbList>
      </Breadcrumb>

      <div
        v-if="pending && !series"
        class="space-y-4"
      >
        <Skeleton class="h-10 w-1/2" />
        <Skeleton class="h-4 w-full" />
        <Skeleton class="h-4 w-3/4" />
      </div>

      <template v-else-if="notFound || !series">
        <Alert variant="default">
          <AlertTitle class="flex items-center gap-2">
            <AlertCircle class="size-4" />
            {{ t('series.notFoundTitle', '系列不存在') }}
          </AlertTitle>
          <AlertDescription class="mt-3 flex items-center justify-between gap-4">
            <span>{{ t('series.notFoundDesc', '该系列可能尚未发布或已被移除。') }}</span>
            <Button
              size="sm"
              variant="default"
              @click="navigateTo('/series')"
            >
              {{ t('series.backToList', '返回系列列表') }}
            </Button>
          </AlertDescription>
        </Alert>
      </template>

      <template v-else>
        <header class="mb-10">
          <div
            v-if="pickStr(series?.cover_image)"
            class="rounded-2xl overflow-hidden aspect-[21/9] bg-muted mb-6"
          >
            <img
              :src="pickStr(series?.cover_image)"
              :alt="pickStr(series?.title) || pickStr(series?.name || '')"
              class="w-full h-full object-cover"
            >
          </div>
          <div class="flex items-center gap-3 mb-3">
            <Badge
              variant="secondary"
              class="text-xs font-medium"
            >
              {{ t('series.postsCount', { n: (series?.post_count ?? 0) }, { default: '{n} 篇文章' }) }}
            </Badge>
            <span
              v-if="series?.updated_at"
              class="text-xs text-muted-foreground"
            >
              {{ formatDate(series.updated_at) }}
            </span>
          </div>
          <h1 class="font-display text-3xl md:text-4xl font-bold tracking-tight">
            {{ pickStr(series?.title) || pickStr(series?.name || '') }}
          </h1>
          <p
            v-if="pickStr(series?.description)"
            class="text-muted-foreground mt-4 leading-relaxed"
          >
            {{ pickStr(series?.description) }}
          </p>
        </header>

        <Card>
          <CardHeader class="p-5 pb-3">
            <CardTitle class="font-display text-xl flex items-center gap-2">
              <ListOrdered class="size-5 text-primary" />
              {{ t('series.chapters', '系列目录') }}
            </CardTitle>
            <CardDescription class="text-sm">
              {{ t('series.chaptersHint', '按推荐顺序阅读，循序渐进。') }}
            </CardDescription>
          </CardHeader>
          <CardContent class="p-5 pt-0">
            <div
              v-if="postsList.length === 0"
              class="text-center py-10 text-muted-foreground text-sm"
            >
              {{ t('series.noPostsYet', '本系列暂无已发布文章。') }}
            </div>
            <ol
              v-else
              class="divide-y"
            >
              <li
                v-for="(p, idx) in postsList"
                :key="p.id"
              >
                <NuxtLink
                  :to="`/posts/${p.slug}`"
                  class="flex items-start gap-4 py-4 group transition-colors hover:bg-accent/40 rounded-lg px-3 -mx-3"
                >
                  <div class="shrink-0 w-10 h-10 rounded-lg bg-muted flex items-center justify-center font-display font-semibold text-muted-foreground group-hover:bg-primary group-hover:text-primary-foreground transition-colors">
                    {{ pad(idx + 1) }}
                  </div>
                  <div class="min-w-0 flex-1">
                    <div class="font-medium leading-snug truncate group-hover:text-primary transition-colors">
                      {{ pickStr(p.title) }}
                    </div>
                    <div class="flex items-center gap-3 mt-1.5 text-xs text-muted-foreground">
                      <span
                        v-if="p.published_at"
                        class="inline-flex items-center gap-1"
                      >
                        <CalendarDays class="size-3" />
                        {{ formatDate(p.published_at) }}
                      </span>
                      <span
                        v-if="typeof p.views === 'number'"
                        class="inline-flex items-center gap-1 tabular-nums"
                      >
                        <Eye class="size-3" />
                        {{ p.views }}
                      </span>
                    </div>
                  </div>
                  <ArrowUpRight class="size-4 text-muted-foreground/60 shrink-0 mt-2 group-hover:text-primary group-hover:-translate-y-0.5 group-hover:translate-x-0.5 transition-all" />
                </NuxtLink>
              </li>
            </ol>
          </CardContent>
        </Card>
      </template>
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
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '~~/components/ui/card'
import { Badge } from '~~/components/ui/badge'
import { Skeleton } from '~~/components/ui/skeleton'
import { Alert, AlertDescription, AlertTitle } from '~~/components/ui/alert'
import { Button } from '~~/components/ui/button'
import { AlertCircle, ArrowUpRight, CalendarDays, Eye, ListOrdered } from '@lucide/vue'
import { useI18n } from 'vue-i18n'

definePageMeta({ layout: 'default' })

const { t, locale } = useI18n()
const route = useRoute()
const params = route.params as { slug?: string }

interface SeriesPostRow {
  id: number | string
  slug: string
  title?: string | Record<string, string>
  cover_image?: string | null
  series_order?: number | null
  views?: number
  published_at?: string | null
}
interface SeriesDetail {
  id: number | string
  slug: string
  title?: string | Record<string, string>
  name?: string | Record<string, string>
  description?: string | Record<string, string>
  cover_image?: string | null
  sort_order?: number
  created_at?: string
  updated_at?: string
  post_count?: number
  posts?: SeriesPostRow[]
}

const pickStr = (v: string | Record<string, string> | null | undefined): string => {
  if (v == null) return ''
  if (typeof v === 'string') return v
  if (typeof v === 'object') {
    const l = locale.value as string
    if (l && v[l]) return v[l]
    const keys = Object.keys(v)
    const first = keys[0]
    return first ? (v[first] || '') : ''
  }
  return String(v)
}

const pad = (n: number) => n.toString().padStart(2, '0')
const formatDate = (v: string | null | undefined) => {
  if (!v) return ''
  try {
    const d = new Date(v)
    if (isNaN(d.getTime())) return ''
    return d.toLocaleDateString(locale.value as string, { year: 'numeric', month: '2-digit', day: '2-digit' })
  } catch { return '' }
}

// 真实接口：GET /api/series/{slug}。失败时回退 null，并显示 404 提示，不伪造内容。
const { data: detail, pending, error } = await useAPI<SeriesDetail | null>(`/series/${params.slug ?? ''}`, {
  key: 'series:detail:' + (params.slug ?? ''),
  default: () => null,
  server: false
})

const notFound = computed(() => !!error.value || (detail.value == null && !pending.value))
const series = computed<SeriesDetail | null>(() => detail.value ?? null)
const postsList = computed<SeriesPostRow[]>(() => {
  const items = series.value?.posts
  if (!Array.isArray(items)) return []
  return items
})
</script>
