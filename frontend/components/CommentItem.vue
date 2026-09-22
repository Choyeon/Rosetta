<template>
  <div
    class="card-surface flex gap-3 p-4"
    :class="depth >= 2 ? 'ps-6 sm:ps-12' : depth >= 1 ? 'ps-6' : ''"
  >
    <UserAvatar
      :avatar="comment.author?.avatar"
      :seed="comment.author?.name"
      :name="comment.author?.name || 'Anonymous'"
      :title="comment.author?.title || null"
      :size="36"
      :show-title="true"
    />

    <div class="flex-1 min-w-0">
      <div class="flex items-start justify-between gap-2 mb-1">
        <div class="flex items-center gap-2 min-w-0">
          <span class="font-semibold text-sm truncate">{{ comment.author?.name || 'Anonymous' }}</span>
          <TitleBadge
            v-if="comment.author?.title"
            :title="comment.author?.title"
            size="sm"
          />
          <span class="text-xs text-muted-foreground shrink-0">{{ formatRelativeTime(comment.createdAt) }}</span>
        </div>
      </div>

      <p class="text-sm leading-relaxed mt-1 break-words whitespace-pre-wrap">
        {{ comment.content }}
      </p>

      <div class="flex items-center gap-1 mt-3">
        <Button
          variant="ghost"
          size="sm"
          class="h-7 px-2"
          :disabled="liking"
          :aria-pressed="isLiked"
          :aria-label="t('comment.like', '点赞')"
          @click="handleLike"
        >
          <Heart
            data-icon="inline-start"
            :class="`size-3.5 mr-1${isLiked ? ' fill-primary/30 text-primary' : ''}`"
          />
          <span class="text-xs tabular-nums">{{ displayLikesCount }}</span>
        </Button>
        <Button
          variant="ghost"
          size="sm"
          class="h-7 px-2"
          @click="$emit('reply', comment.id)"
        >
          <MessageSquare
            data-icon="inline-start"
            class="mr-1"
          />
          <span class="text-xs">{{ t('comment.reply') }}</span>
        </Button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import UserAvatar from '~~/components/UserAvatar.vue'
import TitleBadge from '~~/components/TitleBadge.vue'
import { Button } from '~~/components/ui/button'
import { Heart, MessageSquare } from '~~/lib/lucide-svg-icons'
import { useI18n } from 'vue-i18n'
import { useComments } from '~~/composables/useComments'

interface Props {
  comment: {
    id: number | string
    author?: {
      id: number | string
      name: string
      avatar?: string
      email?: string
      title?: {
        id?: number
        name: string
        icon?: string
        color?: string
      } | null
    }
    content: string
    createdAt: string
    parentId?: number | string | null
    likesCount?: number
  }
  /** 回复嵌套层级（0=根评论）。仅用于视觉缩进，最多 2 级。 */
  depth?: number
}

const props = withDefaults(defineProps<Props>(), {
  depth: 0
})

defineEmits<{
  reply: [commentId: number | string]
}>()

const { t, locale } = useI18n()
const { likeComment } = useComments()

// 点赞：真实调用 POST /api/comments/{id}/like（后端为纯计数 +1，无取消语义），
// 成功后以响应 likes_count 为准更新计数并锁定按钮，防止重复计数。
const isLiked = ref(false)
const liking = ref(false)
const serverLikesCount = ref<number | null>(null)
const displayLikesCount = computed(() => serverLikesCount.value ?? props.comment.likesCount ?? 0)

const handleLike = async () => {
  if (liking.value || isLiked.value) return
  liking.value = true
  try {
    const resp = await likeComment(props.comment.id)
    const r = (resp ?? {}) as Record<string, unknown>
    const rd = (r.data ?? {}) as Record<string, unknown>
    const count
      = (typeof r.likes_count === 'number' ? r.likes_count : undefined)
        ?? (typeof rd.likes_count === 'number' ? rd.likes_count : undefined)
    serverLikesCount.value = count ?? displayLikesCount.value + 1
    isLiked.value = true
  } catch {
    // apiFetch 已统一 toast（无 silentToast），此处仅终止本地 loading
  } finally {
    liking.value = false
  }
}

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
</script>
