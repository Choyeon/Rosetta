<template>
  <div class="container py-16">
    <header class="mb-12 text-center max-w-2xl mx-auto">
      <div class="inline-flex items-center justify-center size-14 rounded-2xl bg-primary/10 mb-5">
        <Tags class="size-7 text-primary" />
      </div>
      <h1 class="font-display text-3xl md:text-4xl font-bold tracking-tight">
        {{ t('tags.title') }}
      </h1>
      <p class="text-muted-foreground mt-3 leading-relaxed">
        {{ t('tags.desc') }}
      </p>
    </header>

    <!-- 标签云：按文章数倒序，数量越多字号越大 -->
    <div
      v-if="_tagsLoading && sortedTags.length === 0"
      class="card-surface no-glow rounded-2xl p-8 mb-10"
    >
      <div class="flex flex-wrap items-center justify-center gap-3">
        <div
          v-for="i in 12"
          :key="i"
          class="h-8 rounded-full bg-muted animate-pulse"
          :style="{ width: `${40 + (i % 5) * 24}px` }"
        />
      </div>
    </div>

    <div
      v-else-if="tagsLoadError"
      class="rounded-xl border border-destructive/30 bg-destructive/5 p-6 text-sm text-destructive text-center mb-10"
    >
      {{ t('admin.posts.loadFailed') }}
    </div>

    <template v-else>
      <div class="card-surface no-glow rounded-2xl p-8 mb-10">
        <div class="flex flex-wrap items-center justify-center gap-3">
          <NuxtLink
            v-for="tag in sortedTags"
            :key="tag.id"
            v-memo="[tag.id, tag.slug, tag.color]"
            :to="`/tags/${tag.slug}`"
            class="no-underline"
            :style="cloudStyle(tag)"
          >
            <TagBadge
              :color="tag.color"
              :label="tagName(tag)"
              size="md"
              show-icon
            />
            <span class="ml-1 text-[11px] text-muted-foreground tabular-nums">
              {{ tagPostsCount(tag) }}
            </span>
          </NuxtLink>
          <div
            v-if="sortedTags.length === 0"
            class="text-center py-10 w-full text-muted-foreground"
          >
            {{ t('tags.noTags') }}
          </div>
        </div>
      </div>

      <!-- 网格视图（带颜色预览） -->
      <div class="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 gap-4">
        <NuxtLink
          v-for="tag in sortedTags"
          :key="tag.id"
          v-memo="[tag.id, tag.slug, tag.color]"
          :to="`/tags/${tag.slug}`"
          class="no-underline group block rounded-xl focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2"
        >
          <div class="card-surface glow-ring h-full rounded-xl p-4 transition-all duration-300 hover:shadow-soft hover:-translate-y-0.5">
            <div class="flex items-center justify-between mb-3">
              <TagBadge
                :color="tag.color"
                :label="tagName(tag)"
                size="md"
                show-icon
              />
              <span class="text-[11px] text-muted-foreground tabular-nums">
                {{ tagPostsCount(tag) }}
              </span>
            </div>
            <h3 class="font-medium text-sm leading-snug line-clamp-1 group-hover:underline underline-offset-4 text-foreground">
              {{ tagName(tag) }}
            </h3>
          </div>
        </NuxtLink>
      </div>
    </template>
  </div>
</template>

<script setup lang="ts">
import { Tags } from '@lucide/vue'
import TagBadge from '~~/components/TagBadge.vue'
import { watch, computed } from 'vue'

definePageMeta({ layout: 'default' })

const { t, locale } = useI18n()
const site = useSite()

// ===== SEO：基于 i18n + 站点设置 =====
useSeo({
  title: computed(() => String(t('nav.tags') || t('tags.title') || '标签')),
  description: computed(() => String(t('tags.desc') || '') || site.siteDescription.value),
  type: 'website'
})
useWebsiteJsonLd()
useBreadcrumbJsonLd([
  { name: t('nav.home') as string, url: '/' },
  { name: t('nav.tags') as string, url: '/tags' }
])

interface TagRow {
  id: number | string
  slug: string
  name?: string | Record<string, string>
  color?: string | null
  post_count?: number
  postsCount?: number
}

// SSR 与客户端首渲染统一为空数组（空 = 无标签占位，避免显示假数据）。
// 首屏渲染用 useSSR 友好的 useAPI，失败或空都保持空态，绝不回退到示例标签。
const { data: tagsData, pending: _tagsLoading, error: tagsLoadError, refresh: refreshTags } = useAPI<TagRow[]>('/blog/tags', {
  query: { lang: locale.value },
  key: computed(() => 'tags:list:' + (locale.value || 'zh')),
  default: () => []
})
watch(locale, () => void refreshTags())

const tags = computed<TagRow[]>(() => {
  const raw = tagsData.value
  if (!Array.isArray(raw)) return []
  return raw
})

const tagName = (tag: TagRow): string => {
  const v = tag.name
  if (v == null) return String(tag.slug)
  if (typeof v === 'string') return v
  const key = locale.value as string
  if (key && v[key]) return v[key]
  const first = Object.values(v as Record<string, string>)[0]
  return first || String(tag.slug)
}

const tagPostsCount = (tag: TagRow): number => {
  return tag.post_count ?? tag.postsCount ?? 0
}

/** 按文章数降序 → 按 slug 稳定排序 */
const sortedTags = computed<TagRow[]>(() => {
  return [...tags.value].sort((a, b) => {
    const d = tagPostsCount(b) - tagPostsCount(a)
    if (d !== 0) return d
    return String(a.slug).localeCompare(String(b.slug))
  })
})

/** 按文章数量给出标签云的不同字号（阶梯式，避免 Hydration 不一致）。 */
const countToScale = (n: number) => {
  if (n >= 40) return { size: '1.1rem', weight: '600' }
  if (n >= 25) return { size: '1rem', weight: '600' }
  if (n >= 15) return { size: '0.92rem', weight: '500' }
  if (n >= 7) return { size: '0.84rem', weight: '500' }
  return { size: '0.78rem', weight: '500' }
}

const cloudStyle = (tag: TagRow): Record<string, string> => {
  const scale = countToScale(tagPostsCount(tag))
  return { fontSize: scale.size, fontWeight: scale.weight }
}

// useAPI 已在顶层 await 进行 SSR 安全拉取；失败时自动回退空数组 default() => []，无示例标签残留。
</script>
