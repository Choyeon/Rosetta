<template>
  <div class="flex gap-3 p-4 rounded-xl border bg-card">
    <Avatar class="size-9 shrink-0">
      <AvatarImage
        v-if="comment.author?.avatar"
        :src="comment.author.avatar"
        :alt="comment.author.name"
      />
      <AvatarFallback>{{ comment.author?.name?.[0] || 'U' }}</AvatarFallback>
    </Avatar>

    <div class="flex-1 min-w-0">
      <div class="flex items-start justify-between gap-2 mb-1">
        <div class="flex items-center gap-2 min-w-0">
          <span class="font-semibold text-sm truncate">{{ comment.author?.name || 'Anonymous' }}</span>
          <span class="text-xs text-muted-foreground shrink-0">{{ formatRelativeTime(comment.createdAt) }}</span>
        </div>
        <Button
          variant="ghost"
          size="sm"
          class="shrink-0 h-7 px-2"
          @click="$emit('reply', comment.id)"
        >
          <ArrowLeft class="size-3.5 mr-1 rotate-180" />
          <span class="text-xs">{{ t('comment.reply') }}</span>
        </Button>
      </div>

      <p class="text-sm leading-relaxed mt-1 break-words whitespace-pre-wrap">
        {{ comment.content }}
      </p>

      <div class="flex items-center gap-1 mt-3">
        <Button
          variant="ghost"
          size="sm"
          class="h-7 px-2"
          @click="handleLike"
        >
          <svg
            class="size-3.5 mr-1"
            :class="{ 'fill-error text-error': isLiked }"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            stroke-width="2"
            stroke-linecap="round"
            stroke-linejoin="round"
          >
            <path d="M19 14c1.49-1.46 3-3.21 3-5.5A5.5 5.5 0 0 0 16.5 3c-1.76 0-3 .5-4.5 2-1.5-1.5-2.74-2-4.5-2A5.5 5.5 0 0 0 2 8.5c0 2.3 1.5 4.05 3 5.5l7 7Z" />
          </svg>
          <span class="text-xs tabular-nums">{{ comment.likesCount ?? 0 }}</span>
        </Button>
        <Button
          variant="ghost"
          size="sm"
          class="h-7 px-2"
          @click="$emit('reply', comment.id)"
        >
          <MessageSquare class="size-3.5 mr-1" />
          <span class="text-xs">{{ t('comment.reply') }}</span>
        </Button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { Avatar, AvatarFallback, AvatarImage } from '~~/components/ui/avatar'
import { Button } from '~~/components/ui/button'
import { ArrowLeft, MessageSquare } from '@lucide/vue'
import { useI18n } from 'vue-i18n'

interface Props {
  comment: {
    id: number | string
    author?: {
      id: number | string
      name: string
      avatar?: string
      email?: string
    }
    content: string
    createdAt: string
    parentId?: number | string | null
    likesCount?: number
  }
  depth?: number
}

withDefaults(defineProps<Props>(), {
  depth: 0
})

defineEmits<{
  reply: [commentId: number | string]
}>()

const { t, locale } = useI18n()
const isLiked = ref(false)

const formatRelativeTime = (date: string) => {
  try {
    if (!date) return ''
    const now = new Date()
    const then = new Date(date)
    if (isNaN(then.getTime())) return ''
    const diffMs = now.getTime() - then.getTime()
    const diffSecs = Math.floor(diffMs / 1000)
    const diffMins = Math.floor(diffSecs / 60)
    const diffHours = Math.floor(diffMins / 60)
    const diffDays = Math.floor(diffHours / 24)

    if (diffSecs < 60) return t('comment.justNow')
    if (diffMins < 60) return `${diffMins}${t('comment.minutesAgo')}`
    if (diffHours < 24) return `${diffHours}${t('comment.hoursAgo')}`
    if (diffDays < 30) return `${diffDays}${t('comment.daysAgo')}`

    return then.toLocaleDateString(locale.value as string, {
      year: 'numeric',
      month: 'short',
      day: 'numeric'
    })
  } catch {
    return ''
  }
}

const handleLike = () => {
  isLiked.value = !isLiked.value
}
</script>
