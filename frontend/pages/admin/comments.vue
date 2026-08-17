<template>
  <div class="space-y-6">
    <div>
      <h1 class="text-3xl font-bold tracking-tight font-display">
        {{ t('admin.comments.title') }}
      </h1>
      <p class="text-sm text-muted-foreground mt-1">
        {{ t('admin.comments.desc') }}
      </p>
    </div>

    <!-- 状态筛选 + 搜索 -->
    <div class="flex flex-col lg:flex-row lg:items-center justify-between gap-3">
      <Tabs
        v-model="statusFilter"
        @update:model-value="onFilterChange"
      >
        <TabsList>
          <TabsTrigger value="all">
            {{ t('admin.comments.tabAll') }}
          </TabsTrigger>
          <TabsTrigger value="pending">
            {{ t('admin.comments.tabPending') }}
          </TabsTrigger>
          <TabsTrigger value="approved">
            {{ t('admin.comments.tabApproved') }}
          </TabsTrigger>
          <TabsTrigger value="rejected">
            {{ t('admin.comments.tabRejected') }}
          </TabsTrigger>
          <TabsTrigger value="spam">
            {{ t('admin.comments.tabSpam') }}
          </TabsTrigger>
        </TabsList>
      </Tabs>
      <div class="flex items-center gap-2 w-full lg:w-80">
        <div class="relative flex-1">
          <Search class="absolute left-3 top-1/2 -translate-y-1/2 size-4 text-muted-foreground" />
          <Input
            v-model="keyword"
            :placeholder="t('admin.comments.searchPlaceholder')"
            class="pl-9"
            @keyup.enter="onFilterChange"
          />
        </div>
        <Button
          variant="secondary"
          @click="onFilterChange"
        >
          {{ t('admin.comments.search') }}
        </Button>
      </div>
    </div>

    <!-- 批量操作条 -->
    <div
      v-if="selectedIds.length > 0"
      class="flex flex-wrap items-center gap-2 rounded-lg border bg-muted/40 px-4 py-2.5"
    >
      <span class="text-sm font-medium">{{ t('admin.comments.selected', { n: selectedIds.length }) }}</span>
      <div class="ml-auto flex flex-wrap items-center gap-2">
        <Button
          size="sm"
          variant="outline"
          :disabled="actionLoading"
          @click="onBatch('approve')"
        >
          <Check class="mr-1 size-4" />
          {{ t('admin.comments.batchApprove') }}
        </Button>
        <Button
          size="sm"
          variant="outline"
          :disabled="actionLoading"
          @click="onBatch('reject')"
        >
          <X class="mr-1 size-4" />
          {{ t('admin.comments.batchReject') }}
        </Button>
        <Button
          size="sm"
          variant="outline"
          :disabled="actionLoading"
          @click="onBatch('spam')"
        >
          <Ban class="mr-1 size-4" />
          {{ t('admin.comments.batchSpam') }}
        </Button>
        <Button
          size="sm"
          variant="destructive"
          :disabled="actionLoading"
          @click="batchDeleteOpen = true"
        >
          <Trash2 class="mr-1 size-4" />
          {{ t('admin.comments.batchDelete') }}
        </Button>
      </div>
    </div>

    <!-- 错误重试 -->
    <div
      v-if="loadError"
      class="flex flex-col items-start gap-3"
    >
      <Alert variant="destructive">
        <AlertCircle class="size-4" />
        <AlertTitle>{{ t('admin.comments.loadFailed') }}</AlertTitle>
        <AlertDescription>{{ loadError }}</AlertDescription>
      </Alert>
      <Button
        variant="outline"
        size="sm"
        :disabled="loading"
        @click="load"
      >
        <RefreshCw
          class="mr-2 size-4"
          :class="{ 'animate-spin': loading }"
        />
        {{ t('admin.comments.retry') }}
      </Button>
    </div>

    <Card v-else>
      <CardContent class="p-0">
        <div
          v-if="loading && comments.length === 0"
          class="p-4 space-y-3"
        >
          <Skeleton
            v-for="i in 6"
            :key="i"
            class="h-14 w-full"
          />
        </div>

        <div
          v-else-if="comments.length > 0"
          class="overflow-x-auto"
        >
          <table class="w-full text-sm">
            <thead>
              <tr class="border-b">
                <th class="w-10 p-3">
                  <Checkbox
                    :checked="allChecked"
                    @update:checked="toggleSelectAll"
                  />
                </th>
                <th class="text-left font-medium text-muted-foreground p-3">
                  {{ t('admin.comments.thAuthor') }}
                </th>
                <th class="text-left font-medium text-muted-foreground p-3">
                  {{ t('admin.comments.thContent') }}
                </th>
                <th class="text-left font-medium text-muted-foreground p-3">
                  {{ t('admin.comments.thPost') }}
                </th>
                <th class="text-left font-medium text-muted-foreground p-3">
                  {{ t('admin.comments.thStatus') }}
                </th>
                <th class="text-left font-medium text-muted-foreground p-3">
                  {{ t('admin.comments.thTime') }}
                </th>
                <th class="text-right font-medium text-muted-foreground p-3">
                  {{ t('admin.comments.thActions') }}
                </th>
              </tr>
            </thead>
            <tbody>
              <template
                v-for="c in comments"
                :key="c.id"
              >
                <tr class="border-b last:border-0 transition-colors hover:bg-muted/50 align-top">
                  <td class="p-3">
                    <Checkbox
                      :checked="selectedIds.includes(c.id)"
                      @update:checked="(v: boolean) => toggleSelect(c.id, v)"
                    />
                  </td>
                  <td class="p-3">
                    <div class="flex items-center gap-2">
                      <Avatar size="sm">
                        <AvatarImage
                          v-if="c.resolved_avatar_url"
                          :src="c.resolved_avatar_url"
                          :alt="c.author_name"
                        />
                        <AvatarFallback>{{ c.author_name[0] }}</AvatarFallback>
                      </Avatar>
                      <div class="min-w-0">
                        <p class="font-medium truncate">
                          {{ c.author_name }}
                        </p>
                        <p
                          v-if="c.author_email"
                          class="text-xs text-muted-foreground truncate"
                        >
                          {{ c.author_email }}
                        </p>
                      </div>
                    </div>
                  </td>
                  <td class="p-3 max-w-64">
                    <button
                      type="button"
                      class="text-left hover:text-primary transition-colors"
                      @click="viewing = c"
                    >
                      <span class="line-clamp-2 break-all">{{ excerpt(c.content, 80) }}</span>
                    </button>
                  </td>
                  <td class="p-3">
                    <NuxtLink
                      v-if="c.post_ref?.slug"
                      :to="`/posts/${c.post_ref.slug}`"
                      target="_blank"
                      class="hover:text-primary"
                    >
                      {{ c.post_ref.title || `#${c.post_id}` }}
                    </NuxtLink>
                    <span
                      v-else
                      class="text-muted-foreground"
                    >-</span>
                  </td>
                  <td class="p-3">
                    <Badge :class="statusBadgeClass(c.status)">
                      {{ statusLabel(c.status) }}
                    </Badge>
                  </td>
                  <td class="p-3 text-muted-foreground whitespace-nowrap">
                    {{ formatAdminDateTime(c.created_at) }}
                  </td>
                  <td class="p-3 text-right whitespace-nowrap">
                    <div class="flex items-center justify-end gap-1">
                      <Button
                        v-if="c.status !== 'approved'"
                        variant="ghost"
                        size="sm"
                        :disabled="actionLoading"
                        @click="onSetStatus(c, 'approved')"
                      >
                        <Check class="size-4" />
                      </Button>
                      <Button
                        v-if="c.status !== 'rejected'"
                        variant="ghost"
                        size="sm"
                        :disabled="actionLoading"
                        @click="onSetStatus(c, 'rejected')"
                      >
                        <X class="size-4" />
                      </Button>
                      <Button
                        v-if="c.status !== 'spam'"
                        variant="ghost"
                        size="sm"
                        :disabled="actionLoading"
                        @click="onSetStatus(c, 'spam')"
                      >
                        <Ban class="size-4" />
                      </Button>
                      <Button
                        variant="ghost"
                        size="sm"
                        :disabled="actionLoading"
                        @click="toggleReply(c)"
                      >
                        <Reply class="size-4" />
                      </Button>
                      <Button
                        variant="ghost"
                        size="sm"
                        class="text-destructive hover:text-destructive"
                        :disabled="actionLoading"
                        @click="pendingDelete = c"
                      >
                        <Trash2 class="size-4" />
                      </Button>
                    </div>
                  </td>
                </tr>
                <tr
                  v-if="replyTargetId === c.id"
                  class="border-b last:border-0 bg-muted/30"
                >
                  <td
                    :colspan="7"
                    class="p-3"
                  >
                    <div class="flex flex-col gap-2 sm:flex-row sm:items-start">
                      <Textarea
                        v-model="replyContent"
                        rows="2"
                        :placeholder="t('admin.comments.replyPlaceholder')"
                        class="flex-1"
                      />
                      <div class="flex gap-2">
                        <Button
                          size="sm"
                          :disabled="replySubmitting || !replyContent.trim()"
                          @click="submitReply(c)"
                        >
                          {{ t('admin.comments.replySubmit') }}
                        </Button>
                        <Button
                          size="sm"
                          variant="ghost"
                          @click="closeReply"
                        >
                          {{ t('admin.comments.cancel') }}
                        </Button>
                      </div>
                    </div>
                  </td>
                </tr>
              </template>
            </tbody>
          </table>
        </div>

        <div
          v-else
          class="flex flex-col items-center justify-center py-16 text-muted-foreground"
        >
          <MessageSquare class="size-8 mb-2" />
          <p class="text-sm">
            {{ t('admin.comments.empty') }}
          </p>
        </div>
      </CardContent>
    </Card>

    <!-- 分页 -->
    <div
      v-if="totalPages > 1"
      class="flex justify-center"
    >
      <Pagination
        v-slot="{ page }"
        :page="currentPage"
        :total="total"
        :items-per-page="pageSize"
        :sibling-count="1"
        show-edges
        @update:page="onPageChange"
      >
        <PaginationContent v-slot="{ items }">
          <PaginationPrevious />
          <template
            v-for="(item, index) in items"
            :key="index"
          >
            <PaginationListItem
              v-if="item.type === 'page'"
              :value="item.value"
              :is-active="item.value === page"
            >
              {{ item.value }}
            </PaginationListItem>
            <PaginationEllipsis v-else />
          </template>
          <PaginationNext />
        </PaginationContent>
      </Pagination>
    </div>

    <!-- 全文查看 Dialog -->
    <Dialog
      :open="viewing !== null"
      @update:open="(v: boolean) => { if (!v) viewing = null }"
    >
      <DialogContent class="max-w-xl">
        <DialogHeader>
          <DialogTitle>{{ viewing?.author_name }}</DialogTitle>
          <DialogDescription>
            {{ viewing?.post_ref?.title ?? '' }} · {{ formatAdminDateTime(viewing?.created_at) }}
          </DialogDescription>
        </DialogHeader>
        <div class="max-h-96 overflow-y-auto whitespace-pre-wrap break-words text-sm">
          {{ viewing?.content }}
        </div>
      </DialogContent>
    </Dialog>

    <!-- 单条删除确认 -->
    <Dialog
      :open="pendingDelete !== null"
      @update:open="(v: boolean) => { if (!v) pendingDelete = null }"
    >
      <DialogContent>
        <DialogHeader>
          <DialogTitle>{{ t('admin.comments.deleteTitle') }}</DialogTitle>
          <DialogDescription>{{ t('admin.comments.deleteDesc') }}</DialogDescription>
        </DialogHeader>
        <div class="rounded-md bg-muted/50 p-3 text-sm whitespace-pre-wrap break-words line-clamp-4">
          {{ pendingDelete?.content }}
        </div>
        <DialogFooter>
          <Button
            variant="outline"
            @click="pendingDelete = null"
          >
            {{ t('admin.comments.cancel') }}
          </Button>
          <Button
            variant="destructive"
            :disabled="actionLoading"
            @click="confirmDelete"
          >
            {{ t('admin.comments.confirmDelete') }}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>

    <!-- 批量删除确认 -->
    <Dialog v-model:open="batchDeleteOpen">
      <DialogContent>
        <DialogHeader>
          <DialogTitle>{{ t('admin.comments.batchDeleteTitle') }}</DialogTitle>
          <DialogDescription>
            {{ t('admin.comments.batchDeleteDesc', { n: selectedIds.length }) }}
          </DialogDescription>
        </DialogHeader>
        <DialogFooter>
          <Button
            variant="outline"
            @click="batchDeleteOpen = false"
          >
            {{ t('admin.comments.cancel') }}
          </Button>
          <Button
            variant="destructive"
            :disabled="actionLoading"
            @click="confirmBatchDelete"
          >
            {{ t('admin.comments.confirmDelete') }}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  </div>
</template>

<script setup lang="ts">
import { Card, CardContent } from '~~/components/ui/card'
import { Button } from '~~/components/ui/button'
import { Badge } from '~~/components/ui/badge'
import { Skeleton } from '~~/components/ui/skeleton'
import { Input } from '~~/components/ui/input'
import { Textarea } from '~~/components/ui/textarea'
import { Checkbox } from '~~/components/ui/checkbox'
import { Avatar, AvatarFallback, AvatarImage } from '~~/components/ui/avatar'
import { Tabs, TabsList, TabsTrigger } from '~~/components/ui/tabs'
import {
  Pagination,
  PaginationContent,
  PaginationEllipsis,
  PaginationListItem,
  PaginationNext,
  PaginationPrevious
} from '~~/components/ui/pagination'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle
} from '~~/components/ui/dialog'
import {
  Alert,
  AlertDescription,
  AlertTitle
} from '~~/components/ui/alert'
import {
  Search,
  Check,
  X,
  Ban,
  Trash2,
  Reply,
  RefreshCw,
  AlertCircle,
  MessageSquare
} from '@lucide/vue'
import {
  batchAdminComments,
  deleteAdminComment,
  fetchAdminComments,
  formatAdminDateTime,
  replyToComment,
  updateAdminCommentStatus,
  type AdminComment,
  type AdminCommentStatus,
  type AdminCommentStatusFilter,
  type CommentBatchActionType
} from '~~/composables/useAdminManage'

definePageMeta({
  layout: 'admin'
})

const { t } = useI18n()
const toast = useToast()

const statusFilter = ref<AdminCommentStatusFilter>('all')
const keyword = ref('')
const currentPage = ref(1)
const pageSize = 20

const comments = ref<AdminComment[]>([])
const total = ref(0)
const totalPages = ref(0)
const loading = ref(false)
const loadError = ref('')
const actionLoading = ref(false)

const selectedIds = ref<number[]>([])
const viewing = ref<AdminComment | null>(null)
const pendingDelete = ref<AdminComment | null>(null)
const batchDeleteOpen = ref(false)

const replyTargetId = ref<number | null>(null)
const replyContent = ref('')
const replySubmitting = ref(false)

const allChecked = computed(
  () => comments.value.length > 0 && comments.value.every(c => selectedIds.value.includes(c.id))
)

function toggleSelect(id: number, checked: boolean): void {
  if (checked) {
    selectedIds.value = [...selectedIds.value, id]
  } else {
    selectedIds.value = selectedIds.value.filter(i => i !== id)
  }
}

function toggleSelectAll(checked: boolean): void {
  selectedIds.value = checked ? comments.value.map(c => c.id) : []
}

function excerpt(content: string, max: number): string {
  return content.length > max ? `${content.slice(0, max)}…` : content
}

function statusLabel(status: AdminCommentStatus | string): string {
  const key = `admin.comments.status.${status}`
  const label = t(key)
  return label === key ? status : label
}

function statusBadgeClass(status: AdminCommentStatus | string): string {
  switch (status) {
    case 'approved':
      return 'bg-success-muted text-success border-transparent'
    case 'pending':
      return 'bg-warning-muted text-warning border-transparent'
    case 'rejected':
      return 'bg-error-muted text-error border-transparent'
    case 'spam':
      return 'bg-muted text-muted-foreground border-transparent'
    default:
      return ''
  }
}

async function load(): Promise<void> {
  loading.value = true
  loadError.value = ''
  try {
    const res = await fetchAdminComments({
      page: currentPage.value,
      page_size: pageSize,
      status: statusFilter.value,
      keyword: keyword.value
    })
    comments.value = res.items
    total.value = res.total
    totalPages.value = res.total_pages
    selectedIds.value = []
  } catch (err) {
    const e = err as { data?: { message?: string, detail?: unknown } }
    loadError.value = e?.data?.message
      ?? (typeof e?.data?.detail === 'string' ? e.data.detail : '')
      || (err instanceof Error ? err.message : String(err))
  } finally {
    loading.value = false
  }
}

function onFilterChange(): void {
  currentPage.value = 1
  load()
}

function onPageChange(p: number): void {
  currentPage.value = p
  load()
}

async function onSetStatus(c: AdminComment, status: AdminCommentStatus): Promise<void> {
  actionLoading.value = true
  try {
    await updateAdminCommentStatus(c.id, status)
    toast.success(t('admin.comments.toast.statusUpdated'))
    await load()
  } catch {
    // apiFetch 已 toast 错误详情
  } finally {
    actionLoading.value = false
  }
}

async function confirmDelete(): Promise<void> {
  if (!pendingDelete.value) return
  actionLoading.value = true
  try {
    const res = await deleteAdminComment(pendingDelete.value.id)
    toast.success(res.message ?? t('admin.comments.toast.deleted'))
    pendingDelete.value = null
    await load()
  } catch {
    // ignore（apiFetch 已提示）
  } finally {
    actionLoading.value = false
  }
}

async function onBatch(action: CommentBatchActionType): Promise<void> {
  if (selectedIds.value.length === 0) return
  if (selectedIds.value.length > 100) {
    toast.warning(t('admin.comments.toast.tooMany'))
    return
  }
  actionLoading.value = true
  try {
    const res = await batchAdminComments(selectedIds.value, action)
    toast.success(res.message ?? t('admin.comments.toast.batchDone'))
    await load()
  } catch {
    // ignore
  } finally {
    actionLoading.value = false
  }
}

async function confirmBatchDelete(): Promise<void> {
  batchDeleteOpen.value = false
  await onBatch('delete')
}

function toggleReply(c: AdminComment): void {
  if (replyTargetId.value === c.id) {
    closeReply()
    return
  }
  replyTargetId.value = c.id
  replyContent.value = ''
}

function closeReply(): void {
  replyTargetId.value = null
  replyContent.value = ''
}

async function submitReply(c: AdminComment): Promise<void> {
  const content = replyContent.value.trim()
  if (!content) return
  replySubmitting.value = true
  try {
    await replyToComment(c.post_id, c.parent_id ?? c.id, content)
    toast.success(t('admin.comments.toast.replied'))
    closeReply()
  } catch {
    // ignore
  } finally {
    replySubmitting.value = false
  }
}

onMounted(() => {
  load()
})
</script>
