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
        class="h-full w-full object-cover transition-transform duration-[520ms] ease-out group-hover:scale-[1.035]"
        loading="lazy"
      >
    </NuxtLink>

    <div class="flex-1 min-w-0 p-4 sm:p-5 flex flex-col">
      <div class="flex items-center gap-2 flex-wrap mb-2">
        <Badge
          v-if="categoryName"
          variant="secondary"
          class="text-[11px] h-5 px-2"
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
          <span v-if="publishedAt" class="shrink-0">·</span>
          <CalendarDays v-if="publishedAt" class="size-3 shrink-0" />
          <span v-if="publishedAt" class="shrink-0 tabular-nums">{{ formatDate(publishedAt) }}</span>
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
        class="h-full w-full object-cover transition-transform duration-[600ms] ease-out group-hover:scale-[1.03]"
        loading="lazy"
      >
      <!-- subtle bottom vignette so text/tags still work when no content overlay -->
      <span class="pointer-events-none absolute inset-x-0 bottom-0 h-20 bg-gradient-to-t from-black/10 to-transparent opacity-70" />
    </NuxtLink>

    <header class="p-5 pb-0">
      <div class="flex items-center gap-2 flex-wrap">
        <Badge v-if="categoryName" variant="secondary">
          <FolderOpen class="size-3 mr-1" />
          {{ categoryName }}
        </Badge>
        <Badge v-if="isPinned" variant="default">
          {{ t('posts.pinned') }}
        </Badge>
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
          <AvatarImage v-if="authorAvatar" :src="authorAvatar" :alt="authorName" />
          <AvatarFallback>{{ authorName[0] || 'U' }}</AvatarFallback>
        </Avatar>
        <span class="font-medium text-foreground truncate">{{ authorName }}</span>
        <span v-if="publishedAt" class="shrink-0">·</span>
        <CalendarDays v-if="publishedAt" class="size-3.5 shrink-0" />
        <span v-if="publishedAt" class="shrink-0 tabular-nums">{{ formatDate(publishedAt) }}</span>
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

type PostCardVariant = 'default' | 'compact'

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
    }
    tags?: Array<{
      id: number | string
      name: string | Record<string, string>
      slug: string
    }>
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
const authorAvatar = computed(() => props.post.author?.avatar || '')
const categoryName = computed(() => {
  const c = props.post.category?.name
  return typeof c === 'string' ? c : (typeof c === 'object' && c ? (c[locale.value as string] || Object.values(c)[0]) : '')
})
const postTitle = computed(() => {
  const tt = props.post.title
  return typeof tt === 'string' ? tt : (typeof tt === 'object' && tt ? (tt[locale.value as string] || Object.values(tt)[0]) : '')
})
const postExcerpt = computed(() => {
  const e = props.post.excerpt
  if (!e) return ''
  return typeof e === 'string' ? e : (e[locale.value as string] || Object.values(e)[0])
})
const postSlug = computed(() => props.post.slug)

const formatDate = (date: string) => {
  try {
    if (!date) return ''
    const d = new Date(date)
    if (isNaN(d.getTime())) return ''
    return d.toLocaleDateString(locale.value as string, {
      year: 'numeric',
      month: 'short',
      day: 'numeric'
    })
  } catch {
    return ''
  }
}
</script>
