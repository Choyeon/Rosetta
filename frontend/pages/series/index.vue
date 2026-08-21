<template>
  <div class="container py-16">
    <header class="mb-12 text-center max-w-2xl mx-auto">
      <div class="inline-flex items-center justify-center size-14 rounded-2xl bg-gradient-to-br from-indigo-100 to-sky-100 dark:from-indigo-900/30 dark:to-sky-900/30 mb-5">
        <BookOpen class="size-7 text-indigo-600 dark:text-indigo-300" />
      </div>
      <h1 class="font-display text-3xl md:text-4xl font-bold tracking-tight">
        {{ t('series.title', '系列文章') }}
      </h1>
      <p class="text-muted-foreground mt-3 leading-relaxed">
        {{ t('series.desc', '按主题深度组织的系列专题，循序渐进地学习某一技术方向。') }}
      </p>
    </header>

    <div
      v-if="pending && seriesList.length === 0"
      class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6"
    >
      <div
        v-for="i in 3"
        :key="i"
        class="rounded-2xl overflow-hidden"
      >
        <Skeleton class="aspect-[16/9] w-full" />
        <div class="p-5 space-y-3 mt-2">
          <Skeleton class="h-5 w-2/3" />
          <Skeleton class="h-4 w-full" />
          <Skeleton class="h-4 w-4/5" />
        </div>
      </div>
    </div>

    <div
      v-else-if="seriesList.length === 0"
      class="text-center py-20"
    >
      <div class="inline-flex items-center justify-center size-16 rounded-2xl bg-muted mb-4">
        <BookOpen class="size-8 text-muted-foreground" />
      </div>
      <h3 class="font-display text-xl font-semibold">
        {{ t('series.noSeries', '暂无系列') }}
      </h3>
      <p class="text-muted-foreground mt-2 text-sm">
        {{ t('series.noSeriesHint', '作者尚未组织专题系列，敬请期待。') }}
      </p>
    </div>

    <div
      v-else
      class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6"
    >
      <NuxtLink
        v-for="s in seriesList"
        :key="s.id"
        :to="`/series/${s.slug}`"
        class="no-underline group"
      >
        <Card class="h-full overflow-hidden group transition-all duration-300 hover:shadow-soft hover:-translate-y-0.5">
          <div class="aspect-[16/9] w-full bg-muted overflow-hidden relative">
            <img
              v-if="pickStr(s.cover_image)"
              :src="pickStr(s.cover_image)"
              :alt="pickStr(s.title) || pickStr(s.name || '')"
              class="w-full h-full object-cover transition-transform duration-500 group-hover:scale-[1.03]"
              loading="lazy"
            >
            <div
              v-else
              class="w-full h-full flex items-center justify-center bg-gradient-to-br from-sky-500/20 via-cyan-500/10 to-transparent"
            >
              <BookOpen class="size-10 text-primary/40" />
            </div>
            <div class="absolute top-3 left-3">
              <Badge
                variant="secondary"
                class="text-[11px] font-medium backdrop-blur"
              >
                {{ s.post_count ?? 0 }} {{ t('series.posts', '篇') }}
              </Badge>
            </div>
          </div>
          <CardHeader class="p-5 pb-3">
            <CardTitle class="font-display text-xl tracking-tight group-hover:underline underline-offset-4 line-clamp-2">
              {{ pickStr(s.title) || pickStr(s.name || '') || '—' }}
            </CardTitle>
            <CardDescription class="mt-2 leading-relaxed line-clamp-3 min-h-[4.5rem] text-sm">
              {{ pickStr(s.description) || t('series.noDesc', '暂无描述') }}
            </CardDescription>
          </CardHeader>
          <CardFooter class="p-5 pt-0 flex items-center justify-between text-sm text-muted-foreground border-t mt-2">
            <span>{{ t('series.viewAll', '查看全部') }}</span>
            <ArrowRight class="size-4 transition-transform duration-300 group-hover:translate-x-1" />
          </CardFooter>
        </Card>
      </NuxtLink>
    </div>
  </div>
</template>

<script setup lang="ts">
import { BookOpen, ArrowRight } from '@lucide/vue'
import {
  Card,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle
} from '~~/components/ui/card'
import { Badge } from '~~/components/ui/badge'
import { Skeleton } from '~~/components/ui/skeleton'
import { useI18n } from 'vue-i18n'

definePageMeta({ layout: 'default' })

const { t, locale } = useI18n()

interface SeriesRow {
  id: number | string
  slug: string
  title?: string | Record<string, string>
  name?: string | Record<string, string>
  description?: string | Record<string, string>
  cover_image?: string | null
  post_count?: number
  sort_order?: number
  created_at?: string
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

// 真实接口：GET /api/series。失败或空时回退空数组，绝不显示示例系列。
const { data: seriesData, pending } = await useAPI<SeriesRow[]>('/series', {
  key: 'series:list:' + (locale.value || 'zh'),
  default: () => []
})

const seriesList = computed<SeriesRow[]>(() => {
  const raw = seriesData.value
  if (!Array.isArray(raw)) return []
  return raw
})
</script>
