<!--
  单条评论行（含点赞、表情反应、回复入口与"本人可删"入口）。
  删除走 DELETE /api/comments/{id}（作者本人，服务端软删除进回收站）：入口由页面按
  canDelete 传入，本组件不碰认证态——游客行必须拿不到按钮，判据见 posts/[slug].vue 的 isOwn。
  后端 POST /comments/{id}/like 是纯计数 +1、无取消语义，故 isLiked 一旦置真就永久锁按钮；
  响应里 likes_count 位置不固定（信封层 / data 层都要探测）。点赞状态只存在本组件、不回写
  父列表，父页面 refresh 后本地点赞会丢；depth 仅是视觉缩进且封顶 2 级，不代表真实树深度。
  表情反应走 /comments/{id}/reactions 三条口（GET 统计 / POST 添加 / DELETE /{emoji} 取消）：
  计数与 reacted 一律以 GET 结果为真源，本地不猜；这条 GET 公开可读但对草稿/加密文章的
  评论回 404（闸门见 backend/api/comment_reactions.py），所以拉取失败只 toast、不锁面板。
-->
<template>
  <div
    class="card-surface flex gap-3 p-4"
    :class="depth >= 2 ? 'ps-6 sm:ps-12' : depth >= 1 ? 'ps-6' : ''"
  >
    <UserAvatar
      :avatar="comment.author?.avatar"
      :resolved-avatar-url="comment.author?.resolvedAvatarUrl"
      :seed="comment.author?.username || comment.author?.name"
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
          v-if="canReply"
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

        <!-- 删除入口只在"这一行是我的"时出现（isOwn 由页面用 raw.user_id 对当前登录 id 算，
             不看 author.id —— normalizeComment 的 author.id 有 `?? 评论 id` 兜底，
             游客行会撞上同号用户而被挂上按钮）。服务端仍会按归属判 404。 -->
        <Button
          v-if="canDelete"
          variant="ghost"
          size="sm"
          class="h-7 px-2 text-muted-foreground"
          :disabled="deleting"
          :aria-label="t('comment.delete')"
          @click="$emit('delete', comment.id)"
        >
          <Trash2
            data-icon="inline-start"
            class="mr-1 size-3.5"
          />
          <span class="text-xs">{{ deleting ? t('comment.deleting') : t('comment.delete') }}</span>
        </Button>

        <!-- 表情反应：已存在的计数先摊出来，面板点了才展开 -->
        <Button
          v-for="item in reactions"
          :key="`chip-${item.emoji}`"
          variant="ghost"
          size="sm"
          class="h-7 gap-1 px-2"
          :class="item.reacted ? 'border-primary/50 text-primary' : ''"
          :disabled="reactionBusy"
          :aria-pressed="item.reacted"
          @click="toggleReaction(item.emoji)"
        >
          <span class="text-xs leading-none">{{ item.emoji }}</span>
          <span class="text-xs tabular-nums">{{ item.count }}</span>
        </Button>

        <Button
          variant="ghost"
          size="sm"
          class="h-7 px-2"
          :disabled="reactionBusy"
          :aria-expanded="reactionPanel"
          :aria-label="t('comment.react')"
          @click="toggleReactionPanel"
        >
          <Smile
            data-icon="inline-start"
            class="size-3.5"
          />
        </Button>

        <!-- 举报入口：自己的评论不渲染（后端对 self-report 回 400 SELF_REPORT），
             成功一次后锁成「已举报」，重复点击不会得到新结果（后端按用户/IP 去重）。 -->
        <Button
          v-if="canReport"
          variant="ghost"
          size="sm"
          class="h-7 px-2 text-muted-foreground"
          :disabled="reported || reportBusy"
          :aria-expanded="reportPanel"
          :aria-label="reported ? t('comment.reported') : t('comment.report')"
          @click="reportPanel = !reportPanel"
        >
          <AlertTriangle
            data-icon="inline-start"
            class="mr-1 size-3.5"
          />
          <span class="text-xs">{{ reported ? t('comment.reported') : t('comment.report') }}</span>
        </Button>
      </div>

      <div
        v-if="reportPanel"
        class="mt-2 flex flex-col gap-2 rounded-lg border border-border/60 p-3"
      >
        <p class="text-xs text-muted-foreground">
          {{ t('comment.reportHint') }}
        </p>
        <div class="flex flex-wrap gap-1">
          <Button
            v-for="item in REPORT_REASONS"
            :key="`reason-${item.value}`"
            :variant="reportReason === item.value ? 'default' : 'outline'"
            size="sm"
            class="h-7 px-2"
            :disabled="reportBusy"
            :aria-pressed="reportReason === item.value"
            @click="reportReason = item.value"
          >
            {{ t(item.labelKey) }}
          </Button>
        </div>
        <Textarea
          v-model="reportDetail"
          rows="2"
          maxlength="500"
          class="resize-none text-sm"
          :placeholder="t('comment.reportDetailPlaceholder')"
        />
        <div class="flex justify-end gap-2">
          <Button
            variant="ghost"
            size="sm"
            :disabled="reportBusy"
            @click="reportPanel = false"
          >
            {{ t('common.cancel') }}
          </Button>
          <Button
            size="sm"
            :disabled="reportBusy"
            @click="submitReport"
          >
            <Loader2
              v-if="reportBusy"
              data-icon="inline-start"
              class="mr-1 size-3.5 animate-spin"
            />
            {{ t('comment.reportSubmit') }}
          </Button>
        </div>
      </div>

      <div
        v-if="reactionPanel"
        class="mt-2 flex flex-wrap gap-1"
      >
        <Button
          v-for="emoji in REACTION_EMOJIS"
          :key="`pick-${emoji}`"
          variant="outline"
          size="sm"
          class="h-7 px-2"
          :disabled="reactionBusy"
          :aria-label="emoji"
          @click="toggleReaction(emoji)"
        >
          {{ emoji }}
        </Button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import UserAvatar from '~~/components/UserAvatar.vue'
import TitleBadge from '~~/components/TitleBadge.vue'
import { Button } from '~~/components/ui/button'
import { Textarea } from '~~/components/ui/textarea'
import { AlertTriangle, Heart, Loader2, MessageSquare, Smile, Trash2 } from '~~/lib/lucide-svg-icons'
import { useI18n } from 'vue-i18n'
import {
  useComments,
  type CommentReactionSummary,
  type CommentReportReason
} from '~~/composables/useComments'
import { toBcp47Locale } from '~~/composables/useSeo'

interface Props {
  comment: {
    id: number | string
    author?: {
      id: number | string
      name: string
      avatar?: string
      email?: string
      /** 后端解析链产出的代理 URL，优先级高于 avatar */
      resolvedAvatarUrl?: string | null
      /** 稳定的头像配色种子（用户名） */
      username?: string | null
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
  /** 后台「评论 → 允许嵌套回复」关闭时收起回复按钮（写口此时会回 422 COMMENT_NESTING_DISABLED）。 */
  canReply?: boolean
  /** 仅这一行的作者本人可见的删除入口（页面用 raw.user_id 对登录 id 算，见上方注释）。 */
  canDelete?: boolean
  /** 举报入口：页面按"这条不是我的"传入（后端对 self-report 回 400 SELF_REPORT）。 */
  canReport?: boolean
  /** 删除请求进行中：锁住本行入口，避免重复提交（服务端删除非幂等，第二次会 404）。 */
  deleting?: boolean
}

const props = withDefaults(defineProps<Props>(), {
  depth: 0,
  canReply: true,
  canDelete: false,
  canReport: false,
  deleting: false
})

defineEmits<{
  reply: [commentId: number | string]
  delete: [commentId: number | string]
}>()

const { t, locale } = useI18n()
const {
  likeComment,
  loadCommentReactions,
  addCommentReaction,
  removeCommentReaction,
  reportComment
} = useComments()
const toast = useToast()

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

// 表情反应：后端没有批量统计口，逐条预取就是 N+1，所以只在第一次点开面板时拉一次；
// 每次 toggle 后以重拉为准（POST 幂等、DELETE 对已取消的回 404，本地增量算会漂）。
const REACTION_EMOJIS = ['👍', '❤️', '🎉', '😄', '😢', '😡']
const reactions = ref<CommentReactionSummary[]>([])
const reactionPanel = ref(false)
const reactionLoaded = ref(false)
const reactionBusy = ref(false)

async function reloadReactions() {
  const res = await loadCommentReactions(props.comment.id)
  reactions.value = res?.reactions ?? []
  reactionLoaded.value = true
}

async function toggleReactionPanel() {
  reactionPanel.value = !reactionPanel.value
  if (!reactionPanel.value || reactionLoaded.value || reactionBusy.value) return
  reactionBusy.value = true
  try {
    await reloadReactions()
  } catch {
    // apiFetch 已 toast，面板留着让用户能再点
  } finally {
    reactionBusy.value = false
  }
}

async function toggleReaction(emoji: string) {
  if (reactionBusy.value) return
  reactionBusy.value = true
  try {
    const hit = reactions.value.find(item => item.emoji === emoji)
    if (hit?.reacted) await removeCommentReaction(props.comment.id, emoji)
    else await addCommentReaction(props.comment.id, emoji)
    await reloadReactions()
  } catch {
    // 同上：失败态由 apiFetch 统一 toast，计数不本地猜
  } finally {
    reactionBusy.value = false
  }
}

// 举报：原因枚举与后端 Literal 逐个对齐（见 useComments::CommentReportReason）。
// 重复举报后端回 200 + duplicate=true 并带自己的 message，所以提示语优先用服务端那句，
// 不在组件里另写一套"你已经举报过了"的判断。
const REPORT_REASONS: { value: CommentReportReason, labelKey: string }[] = [
  { value: 'spam', labelKey: 'comment.reportSpam' },
  { value: 'abuse', labelKey: 'comment.reportAbuse' },
  { value: 'offtopic', labelKey: 'comment.reportOfftopic' },
  { value: 'other', labelKey: 'comment.reportOther' }
]
const reportPanel = ref(false)
const reportReason = ref<CommentReportReason>('spam')
const reportDetail = ref('')
const reportBusy = ref(false)
const reported = ref(false)

async function submitReport() {
  if (reportBusy.value) return
  reportBusy.value = true
  try {
    const res = await reportComment(props.comment.id, reportReason.value, reportDetail.value)
    reportPanel.value = false
    reportDetail.value = ''
    reported.value = true
    toast.success(res?.message || t('comment.reportThanks'))
  } catch {
    // apiFetch 已统一 toast；面板留着让用户改选原因后重试
  } finally {
    reportBusy.value = false
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

    return then.toLocaleDateString(toBcp47Locale(locale.value as string), {
      year: 'numeric',
      month: 'short',
      day: 'numeric'
    })
  } catch {
    return ''
  }
}
</script>
