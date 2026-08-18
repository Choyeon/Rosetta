<template>
  <div class="space-y-4">
    <div class="flex flex-col sm:flex-row gap-3 sm:items-center sm:justify-between">
      <div class="relative flex-1 max-w-md">
        <Search class="absolute left-3 top-1/2 -translate-y-1/2 size-4 text-muted-foreground" />
        <Input
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
          <Search class="size-4 mr-2" />
          搜索
        </Button>
      </div>
    </div>

    <div
      v-if="selectedIds.length > 0"
      class="flex items-center gap-2 p-3 rounded-xl border bg-muted/40"
    >
      <span class="text-sm text-muted-foreground">
        已选中 <span class="font-semibold text-foreground">{{ selectedIds.length }}</span> 条
      </span>
      <Separator
        orientation="vertical"
        class="h-5"
      />
      <Button
        size="sm"
        variant="outline"
        @click="batchAction('approve')"
      >
        <Check class="size-3.5 mr-1.5" />
        通过
      </Button>
      <Button
        size="sm"
        variant="outline"
        @click="batchAction('reject')"
      >
        <X class="size-3.5 mr-1.5" />
        拒绝
      </Button>
      <Button
        size="sm"
        variant="outline"
        @click="batchAction('spam')"
      >
        <Trash2 class="size-3.5 mr-1.5" />
        标垃圾
      </Button>
      <Button
        size="sm"
        variant="destructive"
        @click="batchAction('delete')"
      >
        <Trash2 class="size-3.5 mr-1.5" />
        删除
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
      class="space-y-4"
    >
      <div
        v-for="i in 5"
        :key="i"
        class="rounded-xl border p-4 space-y-3"
      >
        <div class="flex items-center gap-3">
          <Skeleton class="size-10 rounded-full" />
          <div class="flex-1 space-y-2">
            <Skeleton class="h-4 w-32" />
            <Skeleton class="h-3 w-48" />
          </div>
        </div>
        <Skeleton class="h-16 w-full rounded-lg" />
      </div>
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
        <AlertTitle>暂无评论</AlertTitle>
        <AlertDescription>当前筛选条件下没有评论数据</AlertDescription>
      </Alert>
    </div>

    <div
      v-else
      class="space-y-3"
    >
      <div
        v-for="comment in comments"
        :key="comment.id"
        :class="[
          'rounded-xl border bg-card p-4 transition-all hover:shadow-sm',
          comment.parent_id ? 'ml-8 border-l-4 border-l-muted-foreground/20' : ''
        ]"
      >
        <div class="flex items-start gap-3">
          <Checkbox
            :model-value="selectedIds.includes(comment.id)"
            class="mt-1"
            @change="toggleSelect(comment.id, $event)"
          />
          <Avatar class="size-10 shrink-0">
            <AvatarImage
              :src="comment.resolved_avatar_url ?? ''"
              :alt="comment.author_name"
            />
            <AvatarFallback>{{ comment.author_name?.[0]?.toUpperCase() || 'U' }}</AvatarFallback>
          </Avatar>

          <div class="flex-1 min-w-0">
            <div class="flex items-start justify-between gap-2">
              <div class="min-w-0">
                <div class="flex items-center gap-2 flex-wrap">
                  <span class="font-medium truncate">{{ comment.author_name }}</span>
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
                <Badge :class="statusBadgeClass(comment.status)">
                  {{ statusText(comment.status) }}
                </Badge>
                <DropdownMenu>
                  <DropdownMenuTrigger as="template">
                    <Button
                      variant="ghost"
                      size="icon"
                      class="h-8 w-8"
                    >
                      <MoreVertical class="size-4" />
                    </Button>
                  </DropdownMenuTrigger>
                  <DropdownMenuContent align="end">
                    <DropdownMenuItem @click="updateStatus(comment.id, 'approved')">
                      <Check class="size-4 mr-2" />
                      通过
                    </DropdownMenuItem>
                    <DropdownMenuItem @click="updateStatus(comment.id, 'rejected')">
                      <X class="size-4 mr-2" />
                      拒绝
                    </DropdownMenuItem>
                    <DropdownMenuItem @click="updateStatus(comment.id, 'spam')">
                      <Flag class="size-4 mr-2" />
                      标为垃圾
                    </DropdownMenuItem>
                    <DropdownMenuSeparator />
                    <DropdownMenuItem
                      class="text-destructive focus:text-destructive"
                      @click="confirmDelete(comment.id)"
                    >
                      <Trash2 class="size-4 mr-2" />
                      删除
                    </DropdownMenuItem>
                  </DropdownMenuContent>
                </DropdownMenu>
              </div>
            </div>

            <p class="mt-2 text-foreground/90 leading-relaxed line-clamp-2">
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
              <Button
                variant="ghost"
                size="sm"
                class="h-7 px-2"
                @click="toggleReply(comment.id)"
              >
                <Reply class="size-3.5 mr-1" />
                <span class="text-xs">回复</span>
              </Button>
            </div>

            <div
              v-if="replyOpenId === comment.id"
              class="mt-3 p-3 rounded-xl bg-muted/40 border border-border/50 space-y-3"
            >
              <Textarea
                v-model="replyContent"
                rows="3"
                placeholder="输入回复内容..."
                class="resize-none"
              />
              <div class="flex justify-end gap-2">
                <Button
                  variant="ghost"
                  size="sm"
                  @click="replyOpenId = null"
                >
                  取消
                </Button>
                <Button
                  size="sm"
                  @click="submitReply(comment)"
                >
                  <Send class="size-3.5 mr-1.5" />
                  发送回复
                </Button>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <div
      v-if="totalPages > 1"
      class="pt-4"
    >
      <Pagination :items-per-page="pageSize ?? 10">
        <PaginationContent>
          <PaginationItem>
            <PaginationPrevious
              :disabled="page <= 1"
              @click="page > 1 && (page--, fetchData())"
            />
          </PaginationItem>
          <template
            v-for="p in visiblePages"
            :key="p"
          >
            <PaginationItem v-if="p !== '...'">
              <Button
                :variant="p === page ? 'default' : 'ghost'"
                size="icon"
                class="h-9 w-9"
                @click="page !== p && (page = p, fetchData())"
              >
                {{ p }}
              </Button>
            </PaginationItem>
            <PaginationItem v-else>
              <PaginationEllipsis :value="1" />
            </PaginationItem>
          </template>
          <PaginationItem>
            <PaginationNext
              :disabled="page >= totalPages"
              @click="page < totalPages && (page++, fetchData())"
            />
          </PaginationItem>
        </PaginationContent>
      </Pagination>
    </div>

    <Dialog v-model:open="deleteDialogOpen">
      <DialogContent>
        <DialogHeader>
          <DialogTitle>确认删除</DialogTitle>
          <DialogDescription>
            删除后该评论将无法恢复，确定继续吗？
          </DialogDescription>
        </DialogHeader>
        <DialogFooter>
          <Button
            variant="ghost"
            @click="deleteDialogOpen = false"
          >
            取消
          </Button>
          <Button
            variant="destructive"
            @click="doDelete"
          >
            确认删除
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  </div>
</template>

<script setup lang="ts">
/* eslint-disable */
/* eslint-disable @typescript-eslint/ban-ts-comment */
// @ts-nocheck
/* eslint-enable @typescript-eslint/ban-ts-comment */
import { Card, CardContent } from '~~/components/ui/card'
import { Button } from '~~/components/ui/button'
import { Input } from '~~/components/ui/input'
import { Textarea } from '~~/components/ui/textarea'
import { Avatar, AvatarFallback, AvatarImage } from '~~/components/ui/avatar'
import { Badge } from '~~/components/ui/badge'
import { Checkbox } from '~~/components/ui/checkbox'
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuLabel, DropdownMenuSeparator, DropdownMenuTrigger } from '~~/components/ui/dropdown-menu'
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from '~~/components/ui/dialog'
import { Pagination, PaginationContent, PaginationEllipsis, PaginationItem, PaginationNext, PaginationPrevious } from '~~/components/ui/pagination'
import { Skeleton } from '~~/components/ui/skeleton'
import { Alert, AlertDescription, AlertTitle } from '~~/components/ui/alert'
import { Separator } from '~~/components/ui/separator'
import {
  Search, Check, X, Trash2, MoreVertical, Flag, ThumbsUp,
  MessageCircle, Reply, Send, Info
} from '@lucide/vue'
import {
  fetchAdminComments,
  fetchAdminGuestbook,
  updateAdminCommentStatus,
  deleteAdminComment,
  batchAdminComments,
  replyToComment,
  formatAdminDateTime,
  type AdminComment,
  type AdminCommentStatus,
  type CommentBatchActionType
} from '~~/composables/useAdminManage'

const props = defineProps<{
  status: AdminCommentStatus | 'all'
  isGuestbook?: boolean
}>()

const toast = useToast()

const loading = ref(false)
const comments = ref<AdminComment[]>([])
const keyword = ref('')
const page = ref(1)
const pageSize = 10
const total = ref(0)
const selectedIds = ref<number[]>([])
const replyOpenId = ref<number | null>(null)
const replyContent = ref('')
const deleteDialogOpen = ref(false)
const deleteTargetId = ref<number | null>(null)

const totalPages = computed(() => Math.max(1, Math.ceil(total.value / pageSize)))

const visiblePages = computed(() => {
  const tp = totalPages.value
  const curr = page.value
  if (tp <= 7) return Array.from({ length: tp }, (_, i) => i + 1)
  const pages: (number | string)[] = []
  pages.push(1)
  if (curr > 3) pages.push('...')
  const start = Math.max(2, curr - 1)
  const end = Math.min(tp - 1, curr + 1)
  for (let i = start; i <= end; i++) pages.push(i)
  if (curr < tp - 2) pages.push('...')
  pages.push(tp)
  return pages
})

const statusBadgeClass = (s: string): string => {
  switch (s) {
    case 'approved': return 'bg-success-muted text-success-foreground hover:bg-success-muted'
    case 'pending': return 'bg-warning-muted text-warning-foreground hover:bg-warning-muted'
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

const fetchFn = computed(() => props.isGuestbook ? fetchAdminGuestbook : fetchAdminComments)

async function fetchData() {
  loading.value = true
  try {
    const res = await fetchFn.value({
      page: page.value,
      page_size: pageSize,
      status: props.status,
      keyword: keyword.value.trim() || undefined
    })
    comments.value = res.items ?? []
    total.value = res.total ?? 0
  } catch (err) {
    toast.error(err instanceof Error ? err.message : '加载评论失败')
    comments.value = []
    total.value = 0
  } finally {
    loading.value = false
  }
}

function onSearch() {
  page.value = 1
  selectedIds.value = []
  fetchData()
}

function toggleSelect(id: number, checked: unknown) {
  const isChecked = checked === true || (checked as { checked?: boolean })?.checked === true
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
    await updateAdminCommentStatus(id, status)
    toast.success('状态更新成功')
    fetchData()
  } catch (err) {
    toast.error(err instanceof Error ? err.message : '操作失败')
  }
}

function confirmDelete(id: number) {
  deleteTargetId.value = id
  deleteDialogOpen.value = true
}

async function doDelete() {
  if (deleteTargetId.value === null) return
  try {
    await deleteAdminComment(deleteTargetId.value)
    toast.success('删除成功')
    deleteDialogOpen.value = false
    deleteTargetId.value = null
    fetchData()
  } catch (err) {
    toast.error(err instanceof Error ? err.message : '删除失败')
  }
}

async function batchAction(action: CommentBatchActionType) {
  if (selectedIds.value.length === 0) return
  const ids = [...selectedIds.value]
  try {
    await batchAdminComments(ids, action)
    toast.success(`批量操作成功：${actionText(action)} ${ids.length} 条`)
    selectedIds.value = []
    fetchData()
  } catch (err) {
    toast.error(err instanceof Error ? err.message : '批量操作失败')
  }
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

async function submitReply(comment: AdminComment) {
  if (!replyContent.value.trim()) {
    toast.warning('请输入回复内容')
    return
  }
  try {
    await replyToComment(comment.post_id, comment.parent_id ?? comment.id, replyContent.value.trim())
    toast.success('回复成功')
    replyOpenId.value = null
    replyContent.value = ''
    fetchData()
  } catch (err) {
    toast.error(err instanceof Error ? err.message : '回复失败')
  }
}

watch(() => props.status, () => {
  page.value = 1
  selectedIds.value = []
  fetchData()
})

onMounted(fetchData)
</script>
