<template>
  <div class="container py-16">
    <header class="mb-12 text-center max-w-2xl mx-auto">
      <div class="inline-flex items-center justify-center size-14 rounded-2xl bg-primary/10 mb-5">
        <FolderOpen class="size-7 text-primary" />
      </div>
      <h1 class="font-display text-3xl md:text-4xl font-bold tracking-tight">
        {{ t('categories.title') }}
      </h1>
      <p class="text-muted-foreground mt-3 leading-relaxed">
        {{ t('categories.desc') }}
      </p>
    </header>

    <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
      <NuxtLink
        v-for="cat in categories"
        :key="cat.id"
        :to="`/categories/${cat.slug}`"
      >
        <Card class="h-full group transition-all hover:shadow-soft hover:-translate-y-0.5 duration-300 overflow-hidden">
          <CardHeader class="p-6 pb-4">
            <div class="flex items-start justify-between mb-4">
              <div
                class="size-12 rounded-xl flex items-center justify-center bg-primary/10 transition-transform duration-300 group-hover:scale-110"
              >
                <FolderOpen class="size-6 text-primary" />
              </div>
              <Badge variant="secondary">
                {{ getPostsCount(cat) }} {{ t('categories.posts') }}
              </Badge>
            </div>
            <CardTitle class="font-display text-xl tracking-tight group-hover:underline underline-offset-4">
              {{ getCatName(cat) }}
            </CardTitle>
            <CardDescription class="mt-2 line-clamp-2 leading-relaxed min-h-[3rem]">
              {{ getCatDesc(cat) || t('categories.noDesc') }}
            </CardDescription>
          </CardHeader>
          <CardFooter class="p-6 pt-0 flex items-center justify-between text-sm text-muted-foreground border-t mt-2">
            <span>{{ t('categories.browsePosts') }}</span>
            <ArrowRight class="size-4 transition-transform duration-300 group-hover:translate-x-1" />
          </CardFooter>
        </Card>
      </NuxtLink>
    </div>

    <div
      v-if="categories.length === 0"
      class="text-center py-20"
    >
      <div class="inline-flex items-center justify-center size-16 rounded-2xl bg-muted mb-4">
        <FolderOpen class="size-8 text-muted-foreground" />
      </div>
      <h3 class="font-display text-xl font-semibold">
        {{ t('categories.noCategories') }}
      </h3>
    </div>
  </div>
</template>

<script setup lang="ts">
import {
  Card,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle
} from '~~/components/ui/card'
import { Badge } from '~~/components/ui/badge'
import { useI18n } from 'vue-i18n'
import { FolderOpen, ArrowRight } from '@lucide/vue'
import { watch, computed } from 'vue'

definePageMeta({ layout: 'default' })

const { t, locale } = useI18n()

const pickLocalized = (val: string | Record<string, string> | null | undefined): string => {
  if (val == null) return ''
  if (typeof val === 'string') return val
  if (typeof val === 'object') {
    const localeKey = locale.value as string
    if (localeKey && val[localeKey]) return val[localeKey]
    const keys = Object.keys(val)
    const firstKey = keys.length > 0 ? keys[0]! : ''
    return firstKey ? (val[firstKey] || '') : ''
  }
  return String(val)
}
const getCatName = (c: { name?: string | Record<string, string> } | null | undefined) => pickLocalized(c?.name)
const getCatDesc = (c: { description?: string | Record<string, string> } | null | undefined) => pickLocalized(c?.description)
const getPostsCount = (c: { post_count?: number, postsCount?: number } | null | undefined) => c?.post_count ?? c?.postsCount ?? 0

interface CategoryRow {
  id: number | string
  slug: string
  name?: string | Record<string, string>
  description?: string | Record<string, string>
  post_count?: number
  postsCount?: number
}

// 真实接口：GET /api/blog/categories。SSR + 客户端同源，失败时回退空数组，不显示示例分类。
const { data: catsData, refresh: refreshCats } = await useAPI<CategoryRow[]>('/blog/categories', {
  query: { lang: locale.value },
  key: computed(() => 'categories:list:' + (locale.value || 'zh')),
  default: () => []
})
watch(locale, () => void refreshCats())

const categories = computed<CategoryRow[]>(() => {
  const raw = catsData.value
  if (!Array.isArray(raw)) return []
  return raw
})
</script>
