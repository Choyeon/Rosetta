<template>
<<<<<<< Updated upstream
  <Card class="group overflow-hidden transition-all duration-300 hover:shadow-soft hover:-translate-y-0.5">
    <NuxtLink v-if="post.coverImage" :to="`/posts/${post.slug}`" class="block aspect-[16/9] overflow-hidden bg-muted">
      <img
        :src="post.coverImage"
        :alt="post.title"
=======
  <!-- COMPACT variant: horizontal list style (image on left, content on right) -->
  <article
    v-if="variant === 'compact'"
    :class="cn(
      'group rounded-2xl border bg-card text-card-foreground shadow-sm transition-all duration-300 hover:shadow-md hover:-translate-y-0.5 overflow-hidden flex gap-0'
    )"
  >
    <NuxtLink
      v-if="coverImage"
      :to="`/posts/${postSlug}`"
      class="block shrink-0 w-[120px] sm:w-[168px] md:w-[180px] aspect-[4/3] sm:aspect-auto sm:h-auto sm:min-h-full overflow-hidden bg-muted"
    >
      <img
        :src="coverImage"
        :alt="postTitle"
>>>>>>> Stashed changes
        class="h-full w-full object-cover transition-transform duration-500 group-hover:scale-105"
        loading="lazy"
      />
    </NuxtLink>

<<<<<<< Updated upstream
    <CardHeader class="p-5 pb-0">
      <div class="flex items-center gap-2 flex-wrap">
        <Badge v-if="post.category" variant="secondary">
          <FolderOpen class="size-3 mr-1" />
          {{ post.category.name }}
=======
    <div class="flex-1 min-w-0 p-4 sm:p-5 flex flex-col">
      <div class="flex items-center gap-2 flex-wrap mb-2">
        <Badge v-if="categoryName" variant="secondary" class="text-[11px] h-5 px-2">
          <FolderOpen class="size-3 mr-1" />
          {{ categoryName }}
        </Badge>
        <Badge v-if="isFeatured" variant="default" class="bg-gradient-to-r from-amber-500 to-orange-500 hover:from-amber-500 hover:to-orange-500 text-[11px] h-5 px-2">
          <Sparkles class="size-3 mr-1" />
          Featured
        </Badge>
      </div>

      <CardTitle class="font-display text-base sm:text-lg leading-snug line-clamp-2 group-hover:underline underline-offset-4 decoration-border">
        <NuxtLink :to="`/posts/${postSlug}`">{{ postTitle }}</NuxtLink>
      </CardTitle>

      <CardDescription class="line-clamp-2 text-muted-foreground leading-relaxed mt-2 text-sm">
        {{ postExcerpt || t('post.noExcerpt') }}
      </CardDescription>

      <div class="mt-auto pt-3 flex items-center justify-between text-xs text-muted-foreground gap-3">
        <div class="flex items-center gap-2 min-w-0">
          <Avatar class="size-5">
            <AvatarImage v-if="authorAvatar" :src="authorAvatar" :alt="authorName" />
            <AvatarFallback class="text-[10px]">{{ authorName[0] || 'U' }}</AvatarFallback>
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

  <!-- DEFAULT / FEATURED variant: vertical card style -->
  <Card
    v-else
    :class="cn(
      'group overflow-hidden transition-all duration-300 hover:shadow-soft hover:-translate-y-0.5',
      isFeatured && 'md:rounded-3xl'
    )"
  >
    <NuxtLink v-if="coverImage" :to="`/posts/${postSlug}`" class="block overflow-hidden bg-muted"
      :class="isFeatured ? 'aspect-[16/10]' : 'aspect-[16/9]'"
    >
      <img
        :src="coverImage"
        :alt="postTitle"
        class="h-full w-full object-cover transition-transform duration-500 group-hover:scale-105"
        loading="lazy"
      />
    </NuxtLink>

    <CardHeader :class="isFeatured ? 'p-6 sm:p-7 pb-0' : 'p-5 pb-0'">
      <div class="flex items-center gap-2 flex-wrap">
        <Badge v-if="categoryName" variant="secondary">
          <FolderOpen class="size-3 mr-1" />
          {{ categoryName }}
>>>>>>> Stashed changes
        </Badge>
        <Badge v-if="isFeatured" variant="default" class="bg-gradient-to-r from-amber-500 to-orange-500 hover:from-amber-500 hover:to-orange-500">
          <Sparkles class="size-3 mr-1" />
          Featured
        </Badge>
      </div>
<<<<<<< Updated upstream
      <CardTitle class="mt-2 font-display text-xl leading-snug line-clamp-2 group-hover:underline underline-offset-4 decoration-border">
        <NuxtLink :to="`/posts/${post.slug}`">{{ post.title }}</NuxtLink>
      </CardTitle>
    </CardHeader>

    <CardContent class="p-5 pb-4">
      <CardDescription class="line-clamp-3 text-muted-foreground leading-relaxed">
        {{ post.excerpt || t('post.noExcerpt') }}
      </CardDescription>
    </CardContent>

    <CardFooter class="p-5 pt-0 flex items-center justify-between border-t pt-4 mt-2 text-xs text-muted-foreground gap-3">
      <div class="flex items-center gap-2 min-w-0">
        <Avatar class="size-6">
          <AvatarImage v-if="post.author?.avatar" :src="post.author.avatar" :alt="post.author.name" />
          <AvatarFallback>{{ post.author?.name?.[0] || 'U' }}</AvatarFallback>
        </Avatar>
        <span class="font-medium text-foreground truncate">{{ post.author?.name || 'Anonymous' }}</span>
        <span class="shrink-0">·</span>
        <CalendarDays class="size-3.5 shrink-0" />
        <span class="shrink-0 tabular-nums">{{ formatDate(post.publishedAt) }}</span>
=======
      <CardTitle :class="[
        'mt-2 font-display leading-snug line-clamp-2 group-hover:underline underline-offset-4 decoration-border',
        isFeatured ? 'text-2xl sm:text-3xl md:text-4xl' : 'text-xl'
      ]">
        <NuxtLink :to="`/posts/${postSlug}`">{{ postTitle }}</NuxtLink>
      </CardTitle>
    </CardHeader>

    <CardContent :class="isFeatured ? 'p-6 sm:p-7 pb-4' : 'p-5 pb-4'">
      <CardDescription :class="['text-muted-foreground leading-relaxed', isFeatured ? 'line-clamp-3 md:line-clamp-4 text-base md:text-lg' : 'line-clamp-3']">
        {{ postExcerpt || t('post.noExcerpt') }}
      </CardDescription>
    </CardContent>

    <CardFooter
      :class="[
        'flex items-center justify-between border-t mt-2 text-xs text-muted-foreground gap-3',
        isFeatured ? 'p-6 sm:p-7 pt-4' : 'p-5 pt-0'
      ]"
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
>>>>>>> Stashed changes
      </div>
      <div class="flex items-center gap-3 shrink-0">
        <span class="inline-flex items-center gap-1 tabular-nums">
          <Eye class="size-3.5" />
<<<<<<< Updated upstream
          {{ post.views ?? 0 }}
        </span>
        <span class="inline-flex items-center gap-1 tabular-nums">
          <MessageSquare class="size-3.5" />
          {{ post.commentsCount ?? 0 }}
=======
          {{ views }}
        </span>
        <span class="inline-flex items-center gap-1 tabular-nums">
          <MessageSquare class="size-3.5" />
          {{ commentsCount }}
>>>>>>> Stashed changes
        </span>
      </div>
    </CardFooter>
  </Card>
</template>

<script setup lang="ts">
<<<<<<< Updated upstream
=======
import { computed } from 'vue'
>>>>>>> Stashed changes
import { Badge } from '~~/components/ui/badge'
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from '~~/components/ui/card'
import { Avatar, AvatarFallback, AvatarImage } from '~~/components/ui/avatar'
import { CalendarDays, Eye, MessageSquare, FolderOpen, Sparkles } from '@lucide/vue'
import { useI18n } from 'vue-i18n'
import { cn } from '~~/lib/utils'

<<<<<<< Updated upstream
=======
type PostCardVariant = 'default' | 'compact'

>>>>>>> Stashed changes
interface Props {
  post: {
    id: number | string
    slug: string
<<<<<<< Updated upstream
    title: string
    excerpt?: string
    coverImage?: string
    category?: {
      id: number | string
      name: string
=======
    title: string | Record<string, string>
    excerpt?: string | Record<string, string>
    cover_image?: string
    coverImage?: string
    category?: {
      id: number | string
      name: string | Record<string, string>
>>>>>>> Stashed changes
      slug: string
    }
    tags?: Array<{
      id: number | string
<<<<<<< Updated upstream
      name: string
=======
      name: string | Record<string, string>
>>>>>>> Stashed changes
      slug: string
    }>
    author?: {
      id: number | string
<<<<<<< Updated upstream
      name: string
      avatar?: string
      username?: string
    }
    publishedAt: string
    views?: number
    commentsCount?: number
  }
  isFeatured?: boolean
}

const props = withDefaults(defineProps<Props>(), {
  isFeatured: false
=======
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
  }
  isFeatured?: boolean
  variant?: PostCardVariant
}

const props = withDefaults(defineProps<Props>(), {
  isFeatured: false,
  variant: 'default'
>>>>>>> Stashed changes
})

const { t, locale } = useI18n()

<<<<<<< Updated upstream
const formatDate = (date: string) => {
  try {
    return new Date(date).toLocaleDateString(locale.value as string, {
=======
// 兼容 snake_case / camelCase 字段（后端 API 与 mock 数据混用场景）
const coverImage = computed(() => props.post.cover_image || props.post.coverImage || '')
const publishedAt = computed(() => props.post.published_at || props.post.publishedAt || props.post.created_at || '')
const views = computed(() => props.post.views ?? props.post.views_count ?? 0)
const commentsCount = computed(() => props.post.comments_count ?? props.post.commentsCount ?? 0)
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
>>>>>>> Stashed changes
      year: 'numeric',
      month: 'short',
      day: 'numeric'
    })
  } catch {
<<<<<<< Updated upstream
    return date
=======
    return ''
>>>>>>> Stashed changes
  }
}
</script>
