<template>
  <div class="container py-16">
    <header class="mb-12 text-center max-w-2xl mx-auto">
      <div class="inline-flex items-center justify-center size-14 rounded-2xl bg-gradient-to-br from-sky-100 to-cyan-100 dark:from-sky-900/30 dark:to-cyan-900/30 mb-5">
        <Tags class="size-7 text-cyan-600 dark:text-cyan-300" />
      </div>
      <h1 class="font-display text-3xl md:text-4xl font-bold tracking-tight">
        {{ t('tags.title') }}
      </h1>
      <p class="text-muted-foreground mt-3 leading-relaxed">
        {{ t('tags.desc') }}
      </p>
    </header>

    <!-- 标签云：按文章数倒序，数量越多字号越大 -->
    <div class="card-surface rounded-2xl p-8 mb-10">
      <div class="flex flex-wrap items-center justify-center gap-3">
        <NuxtLink
          v-for="tag in sortedTags"
          :key="tag.id"
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
        :to="`/tags/${tag.slug}`"
        class="no-underline group"
      >
        <div class="card-surface h-full rounded-xl p-4 transition-all duration-300 hover:shadow-soft hover:-translate-y-0.5">
          <div class="flex items-center justify-between mb-3">
            <div
              class="size-8 rounded-lg flex items-center justify-center"
              :style="{ background: tagChipBg(tag) }"
            >
              <Hash
                class="size-4"
                :style="{ color: tagTextColor(tag) }"
              />
            </div>
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
  </div>
</template>

<script setup lang="ts">
import { Tags, Hash } from '@lucide/vue'
import TagBadge from '~~/components/TagBadge.vue'

definePageMeta({ layout: 'default' })

const { t, locale } = useI18n()

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
const { data: tagsData, pending: _tagsLoading } = await useAPI<TagRow[]>('/blog/tags', {
  query: { lang: locale.value },
  key: 'tags:list:' + (locale.value || 'zh'),
  default: () => []
})

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

/** 将 hex 色值融合为柔和卡片顶色块（CSS color-mix）。 */
const tagChipBg = (tag: TagRow): string => {
  const hex = tag.color?.trim()
  if (!hex || !/^#?[0-9a-f]{6}$/i.test(hex)) return 'hsl(var(--muted))'
  const m = /^#?([a-f\d]{2})([a-f\d]{2})([a-f\d]{2})$/i.exec(hex)
  if (!m) return 'hsl(var(--muted))'
  const r = parseInt(m[1] ?? '00', 16) / 255
  const g = parseInt(m[2] ?? '00', 16) / 255
  const b = parseInt(m[3] ?? '00', 16) / 255
  const max = Math.max(r, g, b)
  const min = Math.min(r, g, b)
  let h = 0
  let s = 0
  const l = (max + min) / 2
  if (max !== min) {
    const d = max - min
    s = l > 0.5 ? d / (2 - max - min) : d / (max + min)
    switch (max) {
      case r: {
        h = (g - b) / d + (g < b ? 6 : 0)
        break
      }
      case g: {
        h = (b - r) / d + 2
        break
      }
      case b: {
        h = (r - g) / d + 4
        break
      }
      default: break
    }
    h *= 60
  }
  const hsl = `${h} ${s * 100}% ${l * 100}%`
  return `color-mix(in oklab, hsl(${hsl}) 30%, hsl(var(--muted)))`
}

/** 相对亮度选择前景色，确保彩色 icon 在卡片上可读。 */
function hexRelativeLuminance(hex: string): number {
  const m = /^#?([a-f\d]{2})([a-f\d]{2})([a-f\d]{2})$/i.exec(hex)
  if (!m) return 0.5
  const toLin = (v: number) => {
    return v <= 0.03928 ? v / 12.92 : ((v + 0.055) / 1.055) ** 2.4
  }
  const r = toLin(parseInt(m[1] ?? '00', 16) / 255)
  const g = toLin(parseInt(m[2] ?? '00', 16) / 255)
  const b = toLin(parseInt(m[3] ?? '00', 16) / 255)
  return 0.2126 * r + 0.7152 * g + 0.0722 * b
}

const tagTextColor = (tag: TagRow): string => {
  const col = tag.color?.trim()
  if (!col) return 'hsl(var(--foreground))'
  const lum = hexRelativeLuminance(col)
  return lum > 0.55 ? '#0f172a' : lum > 0.3 ? '#0f172a' : '#ffffff'
}

// useAPI 已在顶层 await 进行 SSR 安全拉取；失败时自动回退空数组 default() => []，无示例标签残留。
</script>
