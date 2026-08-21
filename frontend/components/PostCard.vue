<template>
  <article
    v-if="variant === 'compact'"
    class="card-surface lift-hover group overflow-hidden flex gap-0 text-card-foreground"
  >
    <NuxtLink
      v-if="coverImage"
      :to="`/posts/${postSlug}`"
      class="block shrink-0 w-[120px] sm:w-[168px] md:w-[180px] aspect-[4/3] sm:aspect-auto sm:h-auto sm:min-h-full overflow-hidden bg-muted"
    >
      <img
        :src="coverImage"
        :alt="postTitle"
        class="h-full w-full object-cover transition-transform transition-duration-[520ms] ease-out group-hover:scale-[1.035]"
        loading="lazy"
      >
    </NuxtLink>

    <div class="flex-1 min-w-0 p-4 sm:p-5 flex flex-col">
      <div class="flex items-center gap-2 flex-wrap mb-2">
        <Badge
          v-if="categoryName"
          variant="secondary"
          class="text-[11px] h-5 px-2"
          :style="categoryBadgeStyle"
        >
          <FolderOpen class="size-3 mr-1" />
          {{ categoryName }}
        </Badge>
        <Badge
          v-if="isPinned"
          variant="default"
          class="text-[11px] h-5 px-2"
        >
          {{ t('posts.pinned') }}
        </Badge>
        <!-- 紧凑卡片：一行 Tag 上限 4 个（防止挤压正文） -->
        <TagBadge
          v-for="tag in compactTags"
          :key="tag.id"
          :color="tag.color"
          :label="tag.name"
          :to="`/posts?tag=${tag.slug}`"
          size="sm"
        />
      </div>

      <h2 class="font-display text-base sm:text-lg leading-snug line-clamp-2 group-hover:underline underline-offset-4 decoration-border">
        <NuxtLink :to="`/posts/${postSlug}`">{{ postTitle }}</NuxtLink>
      </h2>

      <p class="line-clamp-2 text-muted-foreground leading-relaxed mt-2 text-sm">
        {{ postExcerpt || t('post.noExcerpt') }}
      </p>

      <div class="mt-auto pt-3 flex items-center justify-between text-xs text-muted-foreground gap-3">
        <div class="flex items-center gap-2 min-w-0">
          <Avatar class="size-5">
            <AvatarImage
              v-if="authorAvatar"
              :src="authorAvatar"
              :alt="authorName"
            />
            <AvatarFallback class="text-[10px]">
              {{ authorName[0] || 'U' }}
            </AvatarFallback>
          </Avatar>
          <span class="font-medium text-foreground truncate">{{ authorName }}</span>
          <span
            v-if="publishedAt"
            class="shrink-0"
          >·</span>
          <CalendarDays
            v-if="publishedAt"
            class="size-3 shrink-0"
          />
          <span
            v-if="publishedAt"
            class="shrink-0 tabular-nums"
          >{{ formatDate(publishedAt) }}</span>
        </div>
        <div class="flex items-center gap-3 shrink-0">
          <span class="inline-flex items-center gap-1 tabular-nums">
            <Eye class="size-3.5" />
            {{ views }}
          </span>
          <span class="inline-flex items-center gap-1 tabular-nums">
            <MessageSquare class="size-3.5" />
            {{ commentsCount }}
          </span>
        </div>
      </div>
    </div>
  </article>

  <article
    v-else
    class="card-surface lift-hover group overflow-hidden text-card-foreground"
  >
    <NuxtLink
      v-if="coverImage"
      :to="`/posts/${postSlug}`"
      class="block aspect-[16/9] overflow-hidden bg-muted relative"
    >
      <img
        :src="coverImage"
        :alt="postTitle"
        class="h-full w-full object-cover transition-transform transition-duration-[600ms] ease-out group-hover:scale-[1.03]"
        loading="lazy"
      >
      <!-- subtle bottom vignette so text/tags still work when no content overlay -->
      <span class="pointer-events-none absolute inset-x-0 bottom-0 h-20 bg-gradient-to-t from-black/10 to-transparent opacity-70" />
    </NuxtLink>

    <header class="p-5 pb-0">
      <div class="flex items-center gap-2 flex-wrap">
        <Badge
          v-if="categoryName"
          variant="secondary"
          :style="categoryBadgeStyle"
        >
          <FolderOpen class="size-3 mr-1" />
          {{ categoryName }}
        </Badge>
        <Badge
          v-if="isPinned"
          variant="default"
        >
          {{ t('posts.pinned') }}
        </Badge>
        <!-- 默认卡片：分类、置顶之后显示 Tag，完整渲染 -->
        <TagBadge
          v-for="tag in normalizedTags"
          :key="tag.id"
          :color="tag.color"
          :label="tag.name"
          :to="`/posts?tag=${tag.slug}`"
        />
      </div>
      <h2 class="mt-2 font-display leading-snug line-clamp-2 group-hover:underline underline-offset-4 decoration-border text-xl">
        <NuxtLink :to="`/posts/${postSlug}`">{{ postTitle }}</NuxtLink>
      </h2>
    </header>

    <div class="p-5 pt-3">
      <p class="text-muted-foreground leading-relaxed line-clamp-3">
        {{ postExcerpt || t('post.noExcerpt') }}
      </p>
    </div>

    <footer
      class="flex items-center justify-between mt-2 text-xs text-muted-foreground gap-3 p-5 pt-0"
      style="border-top:1px solid color-mix(in oklab, hsl(var(--foreground)) 6%, transparent)"
    >
      <div class="flex items-center gap-2 min-w-0">
        <Avatar class="size-6">
          <AvatarImage
            v-if="authorAvatar"
            :src="authorAvatar"
            :alt="authorName"
          />
          <AvatarFallback>{{ authorName[0] || 'U' }}</AvatarFallback>
        </Avatar>
        <span class="font-medium text-foreground truncate">{{ authorName }}</span>
        <span
          v-if="publishedAt"
          class="shrink-0"
        >·</span>
        <CalendarDays
          v-if="publishedAt"
          class="size-3.5 shrink-0"
        />
        <span
          v-if="publishedAt"
          class="shrink-0 tabular-nums"
        >{{ formatDate(publishedAt) }}</span>
      </div>
      <div class="flex items-center gap-3 shrink-0">
        <span class="inline-flex items-center gap-1 tabular-nums">
          <Eye class="size-3.5" />
          {{ views }}
        </span>
        <span class="inline-flex items-center gap-1 tabular-nums">
          <MessageSquare class="size-3.5" />
          {{ commentsCount }}
        </span>
      </div>
    </footer>
  </article>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { Badge } from '~~/components/ui/badge'
import { Avatar, AvatarFallback, AvatarImage } from '~~/components/ui/avatar'
import { CalendarDays, Eye, MessageSquare, FolderOpen } from '@lucide/vue'
import { useI18n } from 'vue-i18n'
import TagBadge from '~~/components/TagBadge.vue'
import { useResolvedAvatar } from '~~/composables/useResolvedAvatar'

type PostCardVariant = 'default' | 'compact'

interface TagLike {
  id: number | string
  name: string | Record<string, string>
  slug: string
  color?: string | null
}

interface Props {
  post: {
    id: number | string
    slug: string
    title: string | Record<string, string>
    excerpt?: string | Record<string, string>
    cover_image?: string
    coverImage?: string
    category?: {
      id: number | string
      name: string | Record<string, string>
      slug: string
      color?: string | null
    }
    tags?: TagLike[]
    author?: {
      id: number | string
      name?: string
      nickname?: string
      username?: string
      avatar?: string
    }
    created_at?: string
    published_at?: string
    publishedAt?: string
    updated_at?: string
    views?: number
    views_count?: number
    comments_count?: number
    commentsCount?: number
    likes_count?: number
    likesCount?: number
    is_pinned?: boolean
  }
  variant?: PostCardVariant
}

const props = withDefaults(defineProps<Props>(), {
  variant: 'default'
})

const { t, locale } = useI18n()

const coverImage = computed(() => props.post.cover_image || props.post.coverImage || '')
const publishedAt = computed(() => props.post.published_at || props.post.publishedAt || props.post.created_at || '')
const views = computed(() => props.post.views ?? props.post.views_count ?? 0)
const commentsCount = computed(() => props.post.comments_count ?? props.post.commentsCount ?? 0)
const isPinned = computed(() => props.post.is_pinned === true)
const authorName = computed(() => {
  const a = props.post.author
  return a?.nickname || a?.name || a?.username || 'Anonymous'
})
const authorAvatar = useResolvedAvatar(
  () => props.post.author?.avatar,
  () => props.post.author?.avatar
)

function resolveLocalized(
  value: string | Record<string, string> | undefined,
  fallback = ''
): string {
  if (!value) return fallback
  if (typeof value === 'string') return value
  const v = value as Record<string, string>
  return (v[locale.value as string] ?? Object.values(v)[0] ?? fallback) as string
}

const categoryName = computed(() => resolveLocalized(props.post.category?.name))
const categoryColor = computed(() => props.post.category?.color ?? null)

/**
 * 将 hex (#RRGGBB) 颜色转换为 HSL 空格三元组（如 "181 84% 36%"）。
 * 用于直接拼到 hsl(...) 颜色函数中，参与 color-mix 计算。
 */
function hexToHslTriple(hex: string): string | null {
  const m = /^#?([a-f\d]{2})([a-f\d]{2})([a-f\d]{2})$/i.exec(String(hex).trim())
  if (!m) return null
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
      case r:
        h = (g - b) / d + (g < b ? 6 : 0)
        break
      case g:
        h = (b - r) / d + 2
        break
      case b:
        h = (r - g) / d + 4
        break
    }
    h *= 60
  }
  return `${h} ${s * 100}% ${l * 100}%`
}

/** 分类 Badge：当后端返回了 category.color 时，融合成柔和底色。 */
const categoryBadgeStyle = computed<Record<string, string> | undefined>(() => {
  if (!categoryColor.value) return undefined
  const triple = hexToHslTriple(categoryColor.value)
  if (!triple) return undefined
  return {
    background: `color-mix(in oklab, hsl(${triple}) 18%, hsl(var(--secondary)))`,
    border: `1px solid color-mix(in oklab, hsl(${triple}) 30%, transparent)`,
    color: 'hsl(var(--secondary-foreground))'
  }
})

const postTitle = computed(() => resolveLocalized(props.post.title))
const postExcerpt = computed(() => resolveLocalized(props.post.excerpt))
const postSlug = computed(() => props.post.slug)

/** 把 tags 解析为"i18n aware + 已解析 color"的扁平数组。 */
const normalizedTags = computed<Array<{ id: number | string, slug: string, name: string, color: string | null }>>(() => {
  if (!props.post.tags?.length) return []
  return props.post.tags.map(t => ({
    id: t.id,
    slug: t.slug,
    name: resolveLocalized(t.name),
    color: t.color ?? null
  })).filter(t => t.name.trim().length > 0)
})

/** 紧凑卡片：最多 4 个 Tag，避免挤占正文空间。 */
const compactTags = computed(() => normalizedTags.value.slice(0, 4))

/**
 * SSR-safe 日期格式化（PostCard）。
 *
 * —— 为什么不用 toLocaleDateString？ ——
 * Node SSR 的 Intl 实现（在没有 full-icu 的情况下）会把 zh/ja 等 locale 回退到 en-US，
 * 生成类似 "Aug 20, 2025" 的字符串，而浏览器端按中文 locale 生成 "2025年8月20日"。
 * 服务端 HTML 文本与客户端首次渲染文本不一致 → Vue Hydration mismatch。
 *
 * 这里用静态月份名表 + 模板拼接，保证 SSR 与浏览器两端输出字节级一致。
 */
const POSTCARD_MONTHS: Record<string, string[]> = {
  zh: ['1月', '2月', '3月', '4月', '5月', '6月', '7月', '8月', '9月', '10月', '11月', '12月'],
  zh_Hant: ['1月', '2月', '3月', '4月', '5月', '6月', '7月', '8月', '9月', '10月', '11月', '12月'],
  en: ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'],
  ja: ['1月', '2月', '3月', '4月', '5月', '6月', '7月', '8月', '9月', '10月', '11月', '12月']
}

const formatDate = (date: string) => {
  try {
    if (!date) return ''
    const d = new Date(date)
    if (isNaN(d.getTime())) return ''
    const loc = locale.value as string
    const months = (POSTCARD_MONTHS[loc] || POSTCARD_MONTHS.en || []) as string[]
    const y = d.getFullYear()
    const m = months[d.getMonth()] ?? ''
    const day = d.getDate()
    switch (loc) {
      case 'zh':
      case 'zh_Hant':
      case 'ja':
        return `${y}年${m}${day}日`
      case 'en':
      default:
        return `${m} ${day}, ${y}`
    }
  } catch {
    return ''
  }
}
</script>
