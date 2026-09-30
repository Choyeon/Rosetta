<!--
  评论/留言审核共用列表组件：isGuestbook prop 切换两套请求通道与文案；置顶/精华/回收站为留言专属，回复走文章评论接口故留言隐藏。
  契约：列表、分页、选择权全部由本组件持有（status prop 变化即重置页码并清空选择）；回收站移入/恢复没有单条 API，单条即长度为 1 的批量通道。
-->
<template>
  <div class="flex flex-col gap-4">
    <div class="flex flex-col sm:flex-row gap-3 sm:items-center sm:justify-between">
      <div class="relative flex-1 max-w-md">
        <Search class="absolute left-3 top-1/2 -translate-y-1/2 size-4 text-muted-foreground" />
        <Label
          for="comment-keyword"
          class="sr-only"
        >搜索{{ noun }}</Label>
        <Input
          id="comment-keyword"
          v-model="keyword"
          placeholder="搜索内容或作者..."
          class="pl-9"
          @keyup.enter="onSearch"
        />
      </div>
      <div class="flex items-center gap-2">
        <Button
          variant="ghost"
          size="sm"
          @click="onSearch"
        >
          <Search data-icon="inline-start" />
          搜索
        </Button>
      </div>
    </div>

    <div
      v-if="selectedIds.length > 0"
      class="flex flex-wrap items-center gap-2 p-3 rounded-xl border bg-muted/40"
    >
      <span class="text-sm text-muted-foreground">
        已选中 <span class="font-semibold text-foreground">{{ selectedIds.length }}</span> 条
      </span>
      <Separator
        orientation="vertical"
        class="h-5"
      />
      <Button
        v-if="!isTrashedView"
        size="sm"
        variant="outline"
        @click="openBatchConfirm('approve')"
      >
        <Check data-icon="inline-start" />
        通过
      </Button>
      <Button
        v-if="!isTrashedView"
        size="sm"
        variant="outline"
        @click="openBatchConfirm('reject')"
      >
        <X data-icon="inline-start" />
        拒绝
      </Button>
      <Button
        v-if="!isTrashedView"
        size="sm"
        variant="outline"
        @click="openBatchConfirm('spam')"
      >
        <Flag data-icon="inline-start" />
        标垃圾
      </Button>
      <Button
        v-if="isGuestbook && !isTrashedView"
        size="sm"
        variant="outline"
        @click="moveSelectionToTrash"
      >
        <Trash2 data-icon="inline-start" />
        移入回收站
      </Button>
      <Button
        size="sm"
        variant="destructive"
        @click="openBatchConfirm('delete')"
      >
        <Trash2 data-icon="inline-start" />
        {{ isTrashedView ? '彻底删除' : '删除' }}
      </Button>
      <Button
        size="sm"
        variant="ghost"
        @click="clearSelection"
      >
        取消选择
      </Button>
    </div>

    <div
      v-if="loading"
      class="flex flex-col gap-4"
    >
      <div
        v-for="i in 5"
        :key="i"
        class="flex flex-col gap-3 rounded-xl border p-4"
      >
        <div class="flex items-center gap-3">
          <Skeleton class="size-10 rounded-full" />
          <div class="flex flex-col gap-2 flex-1">
            <Skeleton class="h-4 w-32" />
            <Skeleton class="h-3 w-48" />
          </div>
        </div>
        <Skeleton class="h-16 w-full rounded-lg" />
      </div>
    </div>

    <div
      v-else-if="loadError"
      class="flex flex-col items-start gap-3 p-6"
    >
      <Alert variant="destructive">
        <AlertTitle>加载失败</AlertTitle>
        <AlertDescription>{{ loadErrorMsg || `${noun}列表请求未成功，请重试。` }}</AlertDescription>
      </Alert>
      <Button
        variant="outline"
        size="sm"
        @click="fetchData"
      >
        <RotateCcw data-icon="inline-start" />
        重试
      </Button>
    </div>

    <div
      v-else-if="!comments.length"
      class="py-16 text-center"
    >
      <Alert
        variant="info"
        class="max-w-md mx-auto"
      >
        <Info class="size-4" />
        <AlertTitle>暂无{{ noun }}</AlertTitle>
        <AlertDescription>当前筛选条件下没有{{ noun }}数据</AlertDescription>
      </Alert>
    </div>

    <div
      v-else
      class="flex flex-col gap-3"
    >
      <div
        v-for="comment in comments"
        :key="comment.id"
        :class="[
          'card-surface p-4',
          comment.parent_id ? 'ml-8' : ''
        ]"
      >
        <div class="flex items-start gap-3">
          <Checkbox
            :model-value="selectedIds.includes(comment.id)"
            class="mt-1"
            :aria-label="`选择${noun} #${comment.id}`"
            @update:model-value="toggleSelect(comment.id, $event)"
          />
          <UserAvatar
            :avatar="comment.resolved_avatar_url"
            :seed="comment.author_name"
            :name="comment.author_name"
            :title="comment.title || null"
            :size="40"
            :show-title="true"
          />

          <div class="flex-1 min-w-0">
            <div class="flex items-start justify-between gap-2">
              <div class="min-w-0">
                <div class="flex items-center gap-2 flex-wrap">
                  <span class="font-medium truncate">{{ comment.author_name }}</span>
                  <TitleBadge
                    v-if="comment.title"
                    :title="comment.title"
                    size="sm"
                  />
                  <span
                    v-if="comment.author_email"
                    class="text-xs text-muted-foreground truncate"
                  >
                    {{ comment.author_email }}
                  </span>
                  <span class="text-xs text-muted-foreground">
                    {{ formatAdminDateTime(comment.created_at) }}
                  </span>
                  <a
                    v-if="!isGuestbook && comment.post_ref"
                    :href="`/posts/${comment.post_ref.slug || ''}`"
                    target="_blank"
                    class="text-xs text-primary hover:underline truncate max-w-[200px]"
                  >
                    评论于：{{ comment.post_ref.title }}
                  </a>
                </div>
              </div>
              <div class="flex items-center gap-2 shrink-0">
                <Badge
                  v-if="isTrashedView"
                  variant="outline"
                  class="gap-1"
                >
                  <RotateCcw class="size-3" />已删除
                </Badge>
                <Badge
                  v-if="comment.is_pinned"
                  variant="outline"
                  class="gap-1"
                >
                  <Pin class="size-3" />置顶
                </Badge>
                <Badge
                  v-if="comment.is_featured"
                  variant="outline"
                  class="gap-1"
                >
                  <Sparkles class="size-3" />精华
                </Badge>
                <Badge :class="statusBadgeClass(comment.status)">
                  {{ statusText(comment.status) }}
                </Badge>
                <DropdownMenu>
                  <DropdownMenuTrigger as="template">
                    <Button
                      variant="ghost"
                      size="icon-sm"
                      :aria-label="`${noun}操作菜单`"
                    >
                      <MoreVertical data-icon="inline-start" />
                    </Button>
                  </DropdownMenuTrigger>
                  <DropdownMenuContent align="end">
                    <!-- 回收站条目只有两个合法去向：回来或彻底消失 -->
                    <template v-if="isTrashedView">
                      <DropdownMenuItem @click="moveToOrFromTrash(comment.id, 'restore')">
                        <RotateCcw data-icon="inline-start" />
                        恢复
                      </DropdownMenuItem>
                    </template>
                    <template v-else>
                      <DropdownMenuItem @click="updateStatus(comment.id, 'approved')">
                        <Check data-icon="inline-start" />
                        通过
                      </DropdownMenuItem>
                      <DropdownMenuItem @click="updateStatus(comment.id, 'rejected')">
                        <X data-icon="inline-start" />
                        拒绝
                      </DropdownMenuItem>
                      <DropdownMenuItem @click="updateStatus(comment.id, 'spam')">
                        <Flag data-icon="inline-start" />
                        标为垃圾
                      </DropdownMenuItem>
                    </template>
                    <!-- 置顶/精华是留言专属能力，评论模型没有对应列；回收站条目先恢复再排版 -->
                    <template v-if="isGuestbook && !isTrashedView">
                      <DropdownMenuItem @click="togglePinOrFeature(comment.id, 'pin')">
                        <Pin data-icon="inline-start" />
                        {{ comment.is_pinned ? '取消置顶' : '置顶' }}
                      </DropdownMenuItem>
                      <DropdownMenuItem @click="togglePinOrFeature(comment.id, 'feature')">
                        <Sparkles data-icon="inline-start" />
                        {{ comment.is_featured ? '取消精华' : '设为精华' }}
                      </DropdownMenuItem>
                    </template>
                    <DropdownMenuSeparator />
                    <DropdownMenuItem
                      v-if="isGuestbook && !isTrashedView"
                      @click="moveToOrFromTrash(comment.id, 'trash')"
                    >
                      <Trash2 data-icon="inline-start" />
                      移入回收站
                    </DropdownMenuItem>
                    <DropdownMenuItem
                      v-else-if="isTrashedView"
                      class="text-destructive focus:text-destructive"
                      @click="confirmDelete(comment)"
                    >
                      <Trash2 data-icon="inline-start" />
                      彻底删除
                    </DropdownMenuItem>
                    <DropdownMenuItem
                      v-else
                      class="text-destructive focus:text-destructive"
                      @click="confirmDelete(comment)"
                    >
                      <Trash2 data-icon="inline-start" />
                      删除
                    </DropdownMenuItem>
                  </DropdownMenuContent>
                </DropdownMenu>
              </div>
            </div>

            <p class="mt-2 text-foreground/90 leading-relaxed line-clamp-2 break-words">
              {{ comment.content }}
            </p>

            <div class="mt-3 flex items-center gap-4">
              <span class="inline-flex items-center gap-1.5 text-xs text-muted-foreground">
                <ThumbsUp class="size-3.5" />
                {{ comment.likes_count || 0 }}
              </span>
              <span class="inline-flex items-center gap-1.5 text-xs text-muted-foreground">
                <MessageCircle class="size-3.5" />
                {{ comment.reply_total || 0 }}
              </span>
              <!-- 留言不属于任何文章，无法走 /blog/posts/{id}/comments 回复接口，隐藏入口 -->
              <Button
                v-if="!isGuestbook"
                variant="ghost"
                size="sm"
                class="h-7 px-2"
                @click="toggleReply(comment.id)"
              >
                <Reply data-icon="inline-start" />
                <span class="text-xs">回复</span>
              </Button>
            </div>

            <div
              v-if="!isGuestbook && replyOpenId === comment.id"
              class="flex flex-col gap-3 mt-3 p-3 rounded-xl bg-muted/40 border border-border/50"
            >
              <Label
                :for="`reply-content-${comment.id}`"
                class="sr-only"
              >
                回复内容
              </Label>
              <Textarea
                :id="`reply-content-${comment.id}`"
                v-model="replyContent"
                rows="3"
                placeholder="输入回复内容..."
                class="resize-none"
              />
              <div class="flex justify-end gap-2">
                <Button
                  variant="ghost"
                  size="sm"
                  :disabled="replySubmitting"
                  @click="replyOpenId = null"
                >
                  取消
                </Button>
                <Button
                  size="sm"
                  :disabled="replySubmitting"
                  @click="submitReply(comment)"
                >
                  <Loader2
                    v-if="replySubmitting"
                    data-icon="inline-start"
                    class="animate-spin"
                  />
                  <Send
                    v-else
                    data-icon="inline-start"
                  />
                  发送回复
                </Button>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <div class="pt-4">
      <AdminPagination
        v-model:page="page"
        v-model:page-size="pageSize"
        :total="total"
        :page-size-options="[10, 20, 50, 100]"
        @update:page="onPageChange"
      />
    </div>

    <!-- 单条删除：统一走 DangerConfirmDialog，失败抛错保持弹窗打开 -->
    <DangerConfirmDialog
      v-model:open="deleteDialogOpen"
      :title="`确认删除${noun}`"
      confirm-text="确认删除"
      :confirm-phrase="`删除${noun}`"
      :phrase-hint="`请输入：删除${noun}`"
      :on-confirm="doDelete"
    >
      <template #description>
        将删除 <span class="font-medium text-destructive">{{ deleteTarget?.author_name || '该用户' }}</span>
        的{{ noun }}内容：{{ (deleteTarget?.content || '').slice(0, 60) }}…删除后无法恢复。
      </template>
    </DangerConfirmDialog>

    <!-- 批量操作：同为破坏性操作，走 DangerConfirmDialog -->
    <DangerConfirmDialog
      v-model:open="batchDialogOpen"
      :title="`批量${actionText(batchActionType)}（${selectedIds.length} 条）`"
      confirm-text="确认执行"
      :confirm-phrase="batchActionType === 'delete' ? `删除${noun}` : ''"
      :phrase-hint="batchActionType === 'delete' ? `请输入：删除${noun}` : ''"
      :on-confirm="doBatchAction"
    >
      <template #description>
        将对已选中的 <span class="font-medium">{{ selectedIds.length }}</span> 条{{ noun }}执行「{{ actionText(batchActionType) }}」，批量删除后无法恢复。
      </template>
    </DangerConfirmDialog>
  </div>
</template>

<script setup lang="ts">
/* eslint-disable */

import DangerConfirmDialog from '~~/components/admin/tools/DangerConfirmDialog.vue'
import UserAvatar from '~~/components/UserAvatar.vue'
import TitleBadge from '~~/components/TitleBadge.vue'
import { Button } from '~~/components/ui/button'
import { Input } from '~~/components/ui/input'
import { Textarea } from '~~/components/ui/textarea'
import { Badge } from '~~/components/ui/badge'
import { Checkbox } from '~~/components/ui/checkbox'
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuSeparator, DropdownMenuTrigger } from '~~/components/ui/dropdown-menu'
import { Skeleton } from '~~/components/ui/skeleton'
import { Alert, AlertDescription, AlertTitle } from '~~/components/ui/alert'
import { Separator } from '~~/components/ui/separator'
import { Label } from '~~/components/ui/label'
import {
  Search, Check, X, Trash2, MoreVertical, Flag, ThumbsUp, Loader2, RotateCcw,
  MessageCircle, Reply, Send, Info, Pin, Sparkles
} from '@lucide/vue'
import {
  fetchAdminComments,
  fetchAdminGuestbook,
  updateAdminCommentStatus,
  updateAdminGuestbookStatus,
  deleteAdminComment,
  deleteAdminGuestbook,
  toggleAdminGuestbookPin,
  toggleAdminGuestbookFeature,
  batchAdminComments,
  batchAdminGuestbook,
  replyToComment,
  formatAdminDateTime,
  type AdminCommentRow,
  type AdminCommentStatus,
  type AdminCommentStatusFilter,
  type CommentBatchActionType
} from '~~/composables/useAdminManage'

const props = defineProps<{
  status: AdminCommentStatusFilter
  isGuestbook?: boolean
}>()

/** 两套模型共用本组件：文案与请求通道都按 isGuestbook 切换。 */
const noun = computed(() => (props.isGuestbook ? '留言' : '评论'))
/** 回收站视图（仅留言板有软删除）：可执行的动作集与常规视图互斥。 */
const isTrashedView = computed(() => props.status === 'trashed')

const toast = useToast()

const loading = ref(false)
const loadError = ref(false)
const loadErrorMsg = ref('')
const comments = shallowRef<AdminCommentRow[]>([])
const keyword = ref('')
const page = ref(1)
const pageSize = ref(10)
const total = ref(0)
const selectedIds = ref<number[]>([])
const replyOpenId = ref<number | null>(null)
const replyContent = ref('')
const replySubmitting = ref(false)

// 单条删除
const deleteDialogOpen = ref(false)
const deleteTarget = ref<AdminCommentRow | null>(null)

// 批量操作确认
const batchDialogOpen = ref(false)
const batchActionType = ref<CommentBatchActionType>('approve')

const statusBadgeClass = (s: string): string => {
  switch (s) {
    case 'approved': return 'bg-success-muted text-success-muted-foreground hover:bg-success-muted'
    case 'pending': return 'bg-warning-muted text-warning-muted-foreground hover:bg-warning-muted'
    case 'rejected': return 'bg-destructive/10 text-destructive hover:bg-destructive/10'
    case 'spam': return 'bg-muted text-muted-foreground hover:bg-muted'
    default: return 'bg-muted text-muted-foreground'
  }
}

const statusText = (s: string): string => {
  switch (s) {
    case 'approved': return '已通过'
    case 'pending': return '待审核'
    case 'rejected': return '已拒绝'
    case 'spam': return '垃圾'
    default: return s
  }
}

async function fetchData() {
  loading.value = true
  loadError.value = false
  loadErrorMsg.value = ''
  try {
    // 删除后当前页可能越界：回退一页再取（循环而非递归，保证 loading 覆盖全程）
    for (;;) {
      const query = {
        page: page.value,
        page_size: pageSize.value,
        status: props.status,
        keyword: keyword.value.trim() || undefined
      }
      // 两条通道的行形状各自精确，共同基 AdminCommentRow 才是本组件的状态类型
      const res = props.isGuestbook
        ? await fetchAdminGuestbook(query)
        : await fetchAdminComments(query)
      const items = res.items ?? []
      total.value = res.total ?? 0
      if (items.length === 0 && total.value > 0 && page.value > 1) {
        page.value -= 1
        continue
      }
      comments.value = items
      break
    }
  } catch (err) {
    // apiFetch 已自动 toast，这里保留页面级错误态 + 重试入口
    comments.value = []
    total.value = 0
    loadError.value = true
    loadErrorMsg.value = err instanceof Error ? err.message : ''
  } finally {
    loading.value = false
  }
}

function onSearch() {
  page.value = 1
  selectedIds.value = []
  fetchData()
}

// 翻页/改每页条数后旧选择不再有效，必须清空避免跨页误批量操作
function onPageChange() {
  selectedIds.value = []
  fetchData()
}

function toggleSelect(id: number, checked: unknown) {
  const isChecked = checked === true
  if (isChecked) {
    if (!selectedIds.value.includes(id)) selectedIds.value.push(id)
  } else {
    selectedIds.value = selectedIds.value.filter(x => x !== id)
  }
}

function clearSelection() {
  selectedIds.value = []
}

async function updateStatus(id: number, status: AdminCommentStatus) {
  try {
    if (props.isGuestbook) await updateAdminGuestbookStatus(id, status)
    else await updateAdminCommentStatus(id, status)
    toast.success('状态更新成功')
    fetchData()
  } catch {
    // 失败提示由 apiFetch 统一弹出，避免双重 toast
  }
}

async function togglePinOrFeature(id: number, kind: 'pin' | 'feature') {
  try {
    const res = kind === 'pin'
      ? await toggleAdminGuestbookPin(id)
      : await toggleAdminGuestbookFeature(id)
    // 后端是 toggle，用回包的新状态措辞，不猜
    const on = kind === 'pin' ? Boolean(res?.is_pinned) : Boolean(res?.is_featured)
    if (kind === 'pin') toast.success(on ? '已置顶' : '已取消置顶')
    else toast.success(on ? '已设为精华' : '已取消精华')
    fetchData()
  } catch {
    /* apiFetch 已提示 */
  }
}

async function moveToOrFromTrash(id: number, direction: 'trash' | 'restore') {
  try {
    // 后端只开了批量通道，单条即长度为 1 的批量
    await batchAdminGuestbook([id], direction)
    toast.success(direction === 'trash' ? '已移入回收站' : '已恢复')
    selectedIds.value = selectedIds.value.filter(x => x !== id)
    fetchData()
  } catch {
    /* apiFetch 已提示 */
  }
}

async function moveSelectionToTrash() {
  const ids = [...selectedIds.value]
  if (ids.length === 0) return
  try {
    await batchAdminGuestbook(ids, 'trash')
    toast.success(`已移入回收站 ${ids.length} 条`)
    selectedIds.value = []
    fetchData()
  } catch {
    /* apiFetch 已提示 */
  }
}

function confirmDelete(comment: AdminCommentRow) {
  deleteTarget.value = comment
  deleteDialogOpen.value = true
}

async function doDelete() {
  const target = deleteTarget.value
  if (!target?.id) throw new Error(`未选择要删除的${noun.value}`)
  // 抛错时 DangerConfirmDialog 保持打开并内联显示错误；toast 由 apiFetch 统一处理
  if (props.isGuestbook) await deleteAdminGuestbook(target.id)
  else await deleteAdminComment(target.id)
  toast.success('删除成功')
  deleteTarget.value = null
  await fetchData()
}

function openBatchConfirm(action: CommentBatchActionType) {
  if (selectedIds.value.length === 0) return
  batchActionType.value = action
  batchDialogOpen.value = true
}

async function doBatchAction() {
  const ids = [...selectedIds.value]
  if (ids.length === 0) throw new Error(`未选择任何${noun.value}`)
  if (props.isGuestbook) await batchAdminGuestbook(ids, batchActionType.value)
  else await batchAdminComments(ids, batchActionType.value)
  toast.success(`批量操作成功：${actionText(batchActionType.value)} ${ids.length} 条`)
  selectedIds.value = []
  await fetchData()
}

function actionText(a: CommentBatchActionType): string {
  switch (a) {
    case 'approve': return '通过'
    case 'reject': return '拒绝'
    case 'spam': return '标记垃圾'
    case 'delete': return '删除'
  }
}

function toggleReply(id: number) {
  if (replyOpenId.value === id) {
    replyOpenId.value = null
    replyContent.value = ''
  } else {
    replyOpenId.value = id
    replyContent.value = ''
  }
}

async function submitReply(comment: AdminCommentRow) {
  if (replySubmitting.value) return
  if (!replyContent.value.trim()) {
    toast.warning('请输入回复内容')
    return
  }
  if (!comment.post_id) {
    toast.warning('该条目缺少所属文章，无法回复')
    return
  }
  replySubmitting.value = true
  try {
    await replyToComment(comment.post_id, comment.parent_id ?? comment.id, replyContent.value.trim())
    toast.success('回复成功')
    replyOpenId.value = null
    replyContent.value = ''
    fetchData()
  } catch {
    // 失败提示由 apiFetch 统一弹出，避免双重 toast
  } finally {
    replySubmitting.value = false
  }
}

watch(() => props.status, () => {
  page.value = 1
  selectedIds.value = []
  fetchData()
})

onMounted(fetchData)
</script>
