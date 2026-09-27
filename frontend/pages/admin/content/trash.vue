<!--
  回收站管理页：后端 /admin/trash 分页接口（裸分页对象），按资源类型筛选 + 恢复 / 永久删除 / 清空。
  契约：list 一次拉一页（page/page_size 由本组件驱动）；快照 title 可能是 i18n dict（文章）或纯文本（评论），
  展示前统一走 getLocalizedStr；永久删除与清空走 DangerConfirmDialog + silentToast（失败内联展示），
  恢复失败（如 slug 冲突 400）由 apiFetch 全局 toast 提示。
-->
<template>
  <div class="flex flex-col gap-5">
    <AdminPageHeader
      title="回收站"
      description="已删除的内容在此保留 30 天，可随时恢复或永久删除"
      :icon="ArchiveRestore"
    >
      <template #actions>
        <div class="inline-flex rounded-xl border border-border p-1 bg-card">
          <button
            v-for="f in typeFilters"
            :key="f.key"
            class="px-3 py-1.5 rounded-lg text-xs font-medium transition-all"
            :class="filter === f.key
              ? 'bg-primary text-primary-foreground shadow-sm'
              : 'text-muted-foreground hover:bg-muted hover:text-foreground'"
            @click="setFilter(f.key)"
          >
            {{ f.label }}
          </button>
        </div>
        <Button
          variant="outline"
          size="sm"
          class="rounded-xl text-error hover:text-error hover:bg-error-muted"
          :disabled="items.length === 0"
          @click="emptyConfirmOpen = true"
        >
          <Trash2 data-icon="inline-start" /> 清空回收站
        </Button>
      </template>
    </AdminPageHeader>

    <Alert
      v-if="!loading && loadError"
      variant="destructive"
      class="rounded-xl"
    >
      <AlertTriangle class="size-4" />
      <AlertTitle>回收站加载失败</AlertTitle>
      <AlertDescription class="flex flex-wrap items-center justify-between gap-3">
        <span>{{ loadError }}</span>
        <Button
          variant="outline"
          size="sm"
          class="rounded-lg shrink-0"
          @click="loadPage()"
        >
          <RotateCcw data-icon="inline-start" />
          重试
        </Button>
      </AlertDescription>
    </Alert>

    <div
      v-if="loading"
      class="flex flex-col gap-3"
    >
      <Skeleton
        v-for="i in 6"
        :key="i"
        class="h-24 rounded-2xl"
      />
    </div>

    <div
      v-else-if="items.length === 0 && !loadError"
      class="py-16"
    >
      <Alert
        variant="info"
        class="rounded-xl max-w-lg mx-auto"
      >
        <Info class="size-4" />
        <AlertTitle>{{ filter === 'all' ? '回收站是空的' : '当前筛选条件下无记录' }}</AlertTitle>
        <AlertDescription>{{ filter === 'all' ? '删除文章或评论后会在这里保留 30 天。' : '切换筛选条件查看其他类型的记录。' }}</AlertDescription>
      </Alert>
    </div>

    <div
      v-else
      class="flex flex-col gap-3"
    >
      <div
        v-for="entry in items"
        :key="entry.id"
        class="card-surface p-5 flex flex-col md:flex-row md:items-center gap-4"
      >
        <div class="flex-1 min-w-0">
          <div class="flex items-center gap-2 flex-wrap">
            <Badge
              variant="outline"
              class="text-[11px]"
              :class="typeClass(entry.resource_type)"
            >
              {{ typeLabel(entry.resource_type) }}
            </Badge>
            <h3
              class="font-semibold truncate max-w-full"
              :title="entryTitle(entry)"
            >
              {{ entryTitle(entry) }}
            </h3>
          </div>
          <p
            v-if="entrySummary(entry)"
            class="text-sm text-muted-foreground mt-1 line-clamp-2"
          >
            {{ entrySummary(entry) }}
          </p>
          <div class="flex items-center gap-4 mt-2 text-xs text-muted-foreground tabular-nums flex-wrap">
            <span>删除于 {{ formatAdminDate(entry.created_at) }}</span>
            <span v-if="entry.auto_delete_at">自动清除 {{ formatAdminDate(entry.auto_delete_at) }}</span>
            <span v-if="entry.deleted_by">操作人 {{ entry.deleted_by.nickname || entry.deleted_by.username }}</span>
          </div>
        </div>
        <div class="flex items-center gap-1 shrink-0">
          <Button
            variant="outline"
            size="sm"
            class="rounded-xl"
            :disabled="restoringId === entry.id"
            @click="handleRestore(entry)"
          >
            <Loader2
              v-if="restoringId === entry.id"
              data-icon="inline-start"
              class="animate-spin"
            />
            <RotateCcw
              v-else
              data-icon="inline-start"
            />
            恢复
          </Button>
          <Tooltip>
            <TooltipTrigger as-child>
              <Button
                variant="ghost"
                size="icon-sm"
                class="text-error hover:text-error hover:bg-error-muted"
                aria-label="永久删除"
                @click="deleteTarget = entry; confirmOpen = true"
              >
                <Trash2 />
              </Button>
            </TooltipTrigger>
            <TooltipContent>永久删除</TooltipContent>
          </Tooltip>
        </div>
      </div>

      <div
        v-if="totalPages > 1"
        class="flex items-center justify-between pt-1"
      >
        <div class="text-xs text-muted-foreground tabular-nums">
          共 {{ total }} 条 · 第 {{ page }} / {{ totalPages }} 页
        </div>
        <div class="flex items-center gap-1">
          <Button
            variant="outline"
            size="icon-sm"
            class="rounded-xl"
            :disabled="page <= 1"
            aria-label="上一页"
            @click="gotoPage(page - 1)"
          >
            <ChevronLeft />
          </Button>
          <Button
            variant="outline"
            size="icon-sm"
            class="rounded-xl"
            :disabled="page >= totalPages"
            aria-label="下一页"
            @click="gotoPage(page + 1)"
          >
            <ChevronRight />
          </Button>
        </div>
      </div>
    </div>

    <DangerConfirmDialog
      v-model:open="confirmOpen"
      title="确认永久删除？"
      :description="`「${deleteTarget ? entryTitle(deleteTarget) : ''}」将被彻底删除，无法恢复。`"
      confirm-text="永久删除"
      :on-confirm="confirmDelete"
    />
    <DangerConfirmDialog
      v-model:open="emptyConfirmOpen"
      title="确认清空回收站？"
      description="回收站内所有记录将被彻底删除，此操作无法撤销。"
      confirm-text="清空回收站"
      :on-confirm="confirmEmpty"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import {
  fetchAdminTrash,
  restoreAdminTrashItem,
  deleteAdminTrashItem,
  emptyAdminTrash,
  formatAdminDate,
  type AdminTrashEntry
} from '~~/composables/useAdminManage'
import { useToast } from '~~/composables/useToast'
import { extractApiErrorMessage } from '~~/lib/utils'
import {
  ArchiveRestore, Trash2, RotateCcw, Info, AlertTriangle, Loader2, ChevronLeft, ChevronRight
} from '@lucide/vue'
import { Button } from '~~/components/ui/button'
import { Skeleton } from '~~/components/ui/skeleton'
import { Badge } from '~~/components/ui/badge'
import { Alert, AlertTitle, AlertDescription } from '~~/components/ui/alert'
import { Tooltip, TooltipContent, TooltipTrigger } from '~~/components/ui/tooltip'
import DangerConfirmDialog from '~~/components/admin/tools/DangerConfirmDialog.vue'
import AdminPageHeader from '~~/components/admin/AdminPageHeader.vue'

definePageMeta({ ssr: false, layout: 'admin' })

const toast = useToast()

const typeFilters = [
  { key: 'all', label: '全部' },
  { key: 'post', label: '文章' },
  { key: 'comment', label: '评论' }
] as const

const loading = ref(true)
const loadError = ref('')
const items = ref<AdminTrashEntry[]>([])
const total = ref(0)
const totalPages = ref(0)
const page = ref(1)
const pageSize = 20
const filter = ref<(typeof typeFilters)[number]['key']>('all')

const restoringId = ref<number | null>(null)
const confirmOpen = ref(false)
const emptyConfirmOpen = ref(false)
const deleteTarget = ref<AdminTrashEntry | null>(null)

async function loadPage(targetPage = page.value) {
  loading.value = true
  loadError.value = ''
  try {
    const resp = await fetchAdminTrash({
      page: targetPage,
      page_size: pageSize,
      ...(filter.value === 'all' ? {} : { resource_type: filter.value })
    })
    items.value = resp.items ?? []
    total.value = resp.total ?? 0
    totalPages.value = resp.total_pages ?? 0
    page.value = resp.page ?? targetPage
  } catch (e) {
    // fetchAdminTrash 内部 apiFetch 已 toast；这里补充内联错误态 + 重试
    items.value = []
    const err = e as { data?: unknown, message?: string }
    loadError.value = extractApiErrorMessage(err?.data, err?.message || '加载回收站失败')
  } finally {
    loading.value = false
  }
}

function setFilter(key: typeof filter.value) {
  filter.value = key
  loadPage(1)
}

function gotoPage(p: number) {
  if (p < 1 || p > totalPages.value) return
  loadPage(p)
}

function typeLabel(t: string): string {
  return { post: '文章', comment: '评论', page: '页面' }[t] ?? t
}

function typeClass(t: string): string {
  if (t === 'post') return 'bg-primary/10 text-primary border-transparent'
  if (t === 'comment') return 'bg-warning-muted text-warning-muted-foreground border-transparent'
  return 'bg-muted text-muted-foreground border-transparent'
}

function getLocalizedStr(v: unknown): string {
  if (v == null) return ''
  if (typeof v === 'string') return v
  if (typeof v === 'object') {
    const dict = v as Record<string, string>
    return dict.zh || dict.en || Object.values(dict).find(x => typeof x === 'string' && x) || ''
  }
  return String(v)
}

function entryTitle(entry: AdminTrashEntry): string {
  const d = entry.resource_data
  const title = getLocalizedStr(d.title)
  if (title) return title
  if (entry.resource_type === 'comment') {
    const excerpt = getLocalizedStr(d.content).slice(0, 40)
    return excerpt ? `评论：${excerpt}…` : '评论'
  }
  return `${typeLabel(entry.resource_type)} #${entry.resource_id}`
}

function entrySummary(entry: AdminTrashEntry): string {
  const d = entry.resource_data
  if (entry.resource_type === 'comment') {
    return getLocalizedStr(d.content).slice(0, 120)
  }
  const excerpt = getLocalizedStr(d.excerpt) || getLocalizedStr(d.content).slice(0, 120)
  const slug = typeof d.slug === 'string' ? d.slug : ''
  return [excerpt, slug ? `/${slug}` : ''].filter(Boolean).join(' · ')
}

async function handleRestore(entry: AdminTrashEntry) {
  restoringId.value = entry.id
  try {
    await restoreAdminTrashItem(entry.id)
    toast.success('已恢复到原位置')
    await loadPage()
  } catch {
    // restore 失败（slug 冲突等）由 apiFetch 全局 toast 展示
  } finally {
    restoringId.value = null
  }
}

/**
 * DangerConfirmDialog 的 onConfirm：
 * throw 时弹窗保持打开并内联展示错误（请求走 silentToast 避免 toast 与内联双重提示）。
 */
async function confirmDelete() {
  const target = deleteTarget.value
  if (!target) return
  await deleteAdminTrashItem(target.id, { silentToast: true })
  toast.success('记录已永久删除')
  deleteTarget.value = null
  await loadPage()
}

async function confirmEmpty() {
  await emptyAdminTrash({ silentToast: true })
  toast.success('回收站已清空')
  await loadPage(1)
}

onMounted(() => loadPage(1))
</script>
