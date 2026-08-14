<template>
  <Card class="group overflow-hidden transition-all duration-300 hover:shadow-soft hover:-translate-y-0.5">
    <NuxtLink v-if="post.coverImage" :to="`/posts/${post.slug}`" class="block aspect-[16/9] overflow-hidden bg-muted">
      <img
        :src="post.coverImage"
        :alt="post.title"
        class="h-full w-full object-cover transition-transform duration-500 group-hover:scale-105"
        loading="lazy"
      />
    </NuxtLink>

    <CardHeader class="p-5 pb-0">
      <div class="flex items-center gap-2 flex-wrap">
        <Badge v-if="post.category" variant="secondary">
          <FolderOpen class="size-3 mr-1" />
          {{ post.category.name }}
        </Badge>
        <Badge v-if="isFeatured" variant="default" class="bg-gradient-to-r from-amber-500 to-orange-500 hover:from-amber-500 hover:to-orange-500">
          <Sparkles class="size-3 mr-1" />
          Featured
        </Badge>
      </div>
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
      </div>
      <div class="flex items-center gap-3 shrink-0">
        <span class="inline-flex items-center gap-1 tabular-nums">
          <Eye class="size-3.5" />
          {{ post.views ?? 0 }}
        </span>
        <span class="inline-flex items-center gap-1 tabular-nums">
          <MessageSquare class="size-3.5" />
          {{ post.commentsCount ?? 0 }}
        </span>
      </div>
    </CardFooter>
  </Card>
</template>

<script setup lang="ts">
import { Badge } from '~~/components/ui/badge'
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from '~~/components/ui/card'
import { Avatar, AvatarFallback, AvatarImage } from '~~/components/ui/avatar'
import { CalendarDays, Eye, MessageSquare, FolderOpen, Sparkles } from '@lucide/vue'
import { useI18n } from 'vue-i18n'
import { cn } from '~~/lib/utils'

interface Props {
  post: {
    id: number | string
    slug: string
    title: string
    excerpt?: string
    coverImage?: string
    category?: {
      id: number | string
      name: string
      slug: string
    }
    tags?: Array<{
      id: number | string
      name: string
      slug: string
    }>
    author?: {
      id: number | string
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
})

const { t, locale } = useI18n()

const formatDate = (date: string) => {
  try {
    return new Date(date).toLocaleDateString(locale.value as string, {
      year: 'numeric',
      month: 'short',
      day: 'numeric'
    })
  } catch {
    return date
  }
}
</script>
