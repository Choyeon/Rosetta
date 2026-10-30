<!--
  评论举报队列（批次 #234）：消费 GET /admin/comments/reports + PATCH /admin/comments/reports/{id}。
  契约：
  - 裁决端点只改举报状态，**不下架评论**；确认违规后仍需在「全部评论」页把 status 置为拒绝/垃圾，
    所以本面板只提供「标记已处理 / 驳回 / 删除评论」，不伪装成一次点击就完成下架。
  - counts 由后端按全表算（不受筛选影响），筛选项角标直接读它；筛选/翻页后不重算，避免两套口径。
  - 删除评论走 DangerConfirmDialog + 后端 message（评论进回收站，不是物理删除）。
-->
<template>
  <div class="flex flex-col gap-4">
    <div class="flex flex-wrap items-center gap-2">
      <Button
        v-for="tab in STATUS_TABS"
        :key="tab.value"
        size="sm"
        :variant="status === tab.value ? 'default' : 'outline'"
        @click="changeStatus(tab.value)"
      >
        {{ tab.label }}
        <Badge
          variant="secondary"
          class="ml-1 tabular-nums"
        >
          {{ countOf(tab.value) }}
        </Badge>
      </Button>
    </div>

    <div
      v-if="loading"
      class="flex flex-col gap-3"
    >
      <div
        v-for="i in 4"
        :key="i"
        class="rounded-xl border p-4"
      >
        <Skeleton class="h-4 w-40" />
        <Skeleton class="mt-3 h-3 w-64" />
        <Skeleton class="mt-2 h-12 w-full rounded-lg" />
      </div>
    </div>

    <Alert
      v-else-if="loadError"
      variant="destructive"
    >
      <AlertTriangle data-icon="inline-start" />
      <AlertTitle>举报列表加载失败</AlertTitle>
      <AlertDescription class="flex flex-col items-start gap-2">
        <span>{{ loadErrorMsg || '请稍后重试' }}</span>
        <Button
          size="sm"
          variant="outline"
          @click="fetchData"
        >
          重试
        </Button>
      </AlertDescription>
    </Alert>

    <div
      v-else-if="reports.length === 0"
      class="flex flex-col items-center gap-2 rounded-xl border border-dashed py-14 text-muted-foreground"
    >
      <Inbox class="size-8" />
      <p class="text-sm">
        {{ status === 'open' ? '暂无待处理举报' : '这个状态下没有举报记录' }}
      </p>
    </div>

    <div
      v-else
      class="flex flex-col gap-3"
    >
      <div
        v-for="report in reports"
        :key="report.id"
        class="rounded-xl border p-4 flex flex-col gap-3"
      >
        <div class="flex flex-wrap items-center gap-2">
          <Badge :class="reasonClass(report.reason)">
            {{ reasonText(report.reason) }}
          </Badge>
          <Badge :class="statusClass(report.status)">
            {{ resolvedText(report.status) }}
          </Badge>
          <span class="text-xs text-muted-foreground">
            由 {{ report.reporter_name || '匿名访客' }}
            <template v-if="!report.reporter_name && report.reporter_ip">
              （{{ report.reporter_ip }}）
            </template>
            举报于 {{ formatAdminDateTime(report.created_at) }}
          </span>
        </div>

        <div class="flex flex-wrap items-center gap-2 text-sm">
          <span class="text-muted-foreground">被举报评论：</span>
          <a
            v-if="report.post_slug"
            :href="`/posts/${report.post_slug}`"
            target="_blank"
            rel="noopener"
            class="inline-flex items-center gap-1 font-medium text-primary hover:underline"
          >
            {{ report.post_title || report.post_slug }}
            <ExternalLink class="size-3.5" />
          </a>
          <span
            v-else
            class="font-medium text-muted-foreground"
          >文章已不可用</span>
          <span class="text-muted-foreground">· {{ report.comment_author }}</span>
        </div>

        <p class="rounded-lg bg-muted/40 px-3 py-2 text-sm leading-relaxed line-clamp-3 break-words">
          {{ report.comment_excerpt || '（原评论已删除）' }}
        </p>

        <p
          v-if="report.detail"
          class="text-sm text-muted-foreground"
        >
          补充说明：{{ report.detail }}
        </p>

        <div class="flex flex-wrap items-center gap-2">
          <Button
            v-if="report.status !== 'handled'"
            size="sm"
            :disabled="busyId === report.id"
            @click="resolve(report, 'handled')"
          >
            <Loader2
              v-if="busyId === report.id && busyAction === 'handled'"
              data-icon="inline-start"
              class="animate-spin"
            />
            <Check
              v-else
              data-icon="inline-start"
            />
            标记已处理
          </Button>
          <Button
            v-if="report.status !== 'dismissed'"
            size="sm"
            variant="outline"
            :disabled="busyId === report.id"
            @click="resolve(report, 'dismissed')"
          >
            <Loader2
              v-if="busyId === report.id && busyAction === 'dismissed'"
              data-icon="inline-start"
              class="animate-spin"
            />
            <X
              v-else
              data-icon="inline-start"
            />
            驳回
          </Button>
          <Button
            size="sm"
            variant="ghost"
            class="text-destructive hover:text-destructive"
            :disabled="busyId === report.id"
            @click="openDelete(report)"
          >
            <Trash2 data-icon="inline-start" />
            删除评论
          </Button>
          <span
            v-if="report.handled_by"
            class="ml-auto text-xs text-muted-foreground"
          >
            {{ report.handled_by }} 于 {{ formatAdminDateTime(report.handled_at) }} 裁决
          </span>
        </div>
      </div>

      <AdminPagination
        v-model:page="page"
        v-model:page-size="pageSize"
        :total="total"
        :page-size-options="[10, 20, 50]"
        @update:page="fetchData"
      />
    </div>

    <DangerConfirmDialog
      v-model:open="deleteDialogOpen"
      title="确认删除评论"
      confirm-text="确认删除"
      confirm-phrase="删除评论"
      phrase-hint="请输入：删除评论"
      :on-confirm="doDeleteComment"
    >
      <template #description>
        将删除 <span class="font-medium text-destructive">{{ deleteTarget?.comment_author }}</span>
        的评论：{{ (deleteTarget?.comment_excerpt || '').slice(0, 60) }}…
        评论会进入回收站（30 天内可恢复），举报记录随评论一并消失。
      </template>
    </DangerConfirmDialog>
  </div>
</template>

<script setup lang="ts">
import { Button } from '~~/components/ui/button'
import { Badge } from '~~/components/ui/badge'
import { Skeleton } from '~~/components/ui/skeleton'
import { Alert, AlertDescription, AlertTitle } from '~~/components/ui/alert'
import DangerConfirmDialog from '~~/components/admin/tools/DangerConfirmDialog.vue'
import AdminPagination from '~~/components/admin/AdminPagination.vue'
import { AlertTriangle, Check, ExternalLink, Inbox, Loader2, Trash2, X } from '@lucide/vue'
import {
  deleteAdminComment,
  fetchAdminCommentReports,
  formatAdminDateTime,
  resolveAdminCommentReport,
  type AdminCommentReportCounts,
  type AdminCommentReportFilter,
  type AdminCommentReportRow
} from '~~/composables/useAdminManage'

const STATUS_TABS: { value: AdminCommentReportFilter, label: string }[] = [
  { value: 'open', label: '待处理' },
  { value: 'handled', label: '已处理' },
  { value: 'dismissed', label: '已驳回' },
  { value: 'all', label: '全部' }
]

const toast = useToast()

const status = ref<AdminCommentReportFilter>('open')
const loading = ref(false)
const loadError = ref(false)
const loadErrorMsg = ref('')
const reports = shallowRef<AdminCommentReportRow[]>([])
const total = ref(0)
const page = ref(1)
const pageSize = ref(20)
const counts = ref<AdminCommentReportCounts | null>(null)
const busyId = ref<number | null>(null)
const busyAction = ref<'handled' | 'dismissed' | null>(null)

const deleteDialogOpen = ref(false)
const deleteTarget = ref<AdminCommentReportRow | null>(null)

const countOf = (value: AdminCommentReportFilter): number => {
  if (!counts.value) return 0
  return value === 'all' ? counts.value.total : counts.value[value]
}

const reasonText = (reason: string): string => {
  switch (reason) {
    case 'spam': return '垃圾广告'
    case 'abuse': return '辱骂攻击'
    case 'offtopic': return '与内容无关'
    default: return '其他原因'
  }
}

const reasonClass = (reason: string): string => {
  switch (reason) {
    case 'spam': return 'bg-muted text-muted-foreground hover:bg-muted'
    case 'abuse': return 'bg-destructive/10 text-destructive hover:bg-destructive/10'
    case 'offtopic': return 'bg-warning-muted text-warning-muted-foreground hover:bg-warning-muted'
    default: return 'bg-muted text-muted-foreground hover:bg-muted'
  }
}

const statusClass = (value: string): string => {
  switch (value) {
    case 'open': return 'bg-warning-muted text-warning-muted-foreground hover:bg-warning-muted'
    case 'handled': return 'bg-success-muted text-success-muted-foreground hover:bg-success-muted'
    case 'dismissed': return 'bg-muted text-muted-foreground hover:bg-muted'
    default: return 'bg-muted text-muted-foreground hover:bg-muted'
  }
}

const resolvedText = (value: string): string => {
  switch (value) {
    case 'open': return '待处理'
    case 'handled': return '已处理'
    case 'dismissed': return '已驳回'
    default: return value
  }
}

async function fetchData() {
  loading.value = true
  loadError.value = false
  loadErrorMsg.value = ''
  try {
    // 裁决/删除后当前页可能越界：回退一页再取
    for (;;) {
      const res = await fetchAdminCommentReports({
        status: status.value,
        page: page.value,
        page_size: pageSize.value
      })
      const items = res.items ?? []
      total.value = res.total ?? 0
      counts.value = res.counts ?? null
      if (items.length === 0 && total.value > 0 && page.value > 1) {
        page.value -= 1
        continue
      }
      reports.value = items
      break
    }
  } catch (err) {
    reports.value = []
    total.value = 0
    loadError.value = true
    loadErrorMsg.value = err instanceof Error ? err.message : ''
  } finally {
    loading.value = false
  }
}

function changeStatus(next: AdminCommentReportFilter) {
  if (status.value === next) return
  status.value = next
  page.value = 1
  fetchData()
}

async function resolve(report: AdminCommentReportRow, action: 'handled' | 'dismissed') {
  if (busyId.value !== null) return
  busyId.value = report.id
  busyAction.value = action
  try {
    await resolveAdminCommentReport(report.id, action)
    // 措辞取动作本身，不猜后端：裁决只改举报状态，评论仍在线
    toast.success(action === 'handled' ? '已标记为已处理' : '已驳回该举报')
    await fetchData()
  } catch {
    // apiFetch 已统一 toast
  } finally {
    busyId.value = null
    busyAction.value = null
  }
}

function openDelete(report: AdminCommentReportRow) {
  deleteTarget.value = report
  deleteDialogOpen.value = true
}

async function doDeleteComment() {
  const target = deleteTarget.value
  if (!target) throw new Error('未选择要删除的评论')
  // 提示语取后端 message（评论进回收站，留言板才是物理删除），不要写死
  const resp = await deleteAdminComment(target.comment_id)
  toast.success(resp?.message || '评论已删除')
  deleteTarget.value = null
  await fetchData()
}

onMounted(fetchData)
</script>
