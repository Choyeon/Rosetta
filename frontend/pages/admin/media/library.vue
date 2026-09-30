<!--
  媒体资源库页：网格/列表双视图 + 服务端分页筛选 + XHR 进度上传队列 + 预览编辑与单删/批删。
  契约：批删回包分三种结果必须分别播报（deleted_count / refused=被内容引用或路径非法被服务端保留，reason 由服务端给 / missing_ids），只报"已删除"会误导管理员；
  selectedIds 每次拉取都要重新与当前页结果求交，防批量操作连带删除不可见的旧选中项；响应带序号防乱序写回，分页组件双 emit 需微任务合并成单次请求。
-->
<template>
  <div class="flex flex-col gap-5">
    <AdminPageHeader
      title="媒体资源库"
      description="统一查看与管理上传的图片、视频与文档"
      :icon="Files"
    />

    <div class="grid grid-cols-2 md:grid-cols-4 gap-4">
      <AdminCard class="overflow-hidden">
        <div class="p-4">
          <div class="flex items-center justify-between">
            <div>
              <p class="text-xs text-muted-foreground">
                总文件数
              </p>
              <p class="text-2xl font-bold mt-1">
                {{ stats.total_files || 0 }}
              </p>
            </div>
            <div class="size-10 rounded-xl bg-primary/10 flex items-center justify-center">
              <Files class="size-5 text-primary" />
            </div>
          </div>
        </div>
      </AdminCard>
      <AdminCard class="overflow-hidden">
        <div class="p-4">
          <div class="flex items-center justify-between">
            <div>
              <p class="text-xs text-muted-foreground">
                总大小
              </p>
              <p class="text-2xl font-bold mt-1">
                {{ formatSize(stats.total_size_bytes || 0) }}
              </p>
            </div>
            <div class="size-10 rounded-xl bg-warning-muted flex items-center justify-center">
              <HardDrive class="size-5 text-warning-muted-foreground" />
            </div>
          </div>
        </div>
      </AdminCard>
      <AdminCard class="overflow-hidden">
        <div class="p-4">
          <div class="flex items-center justify-between">
            <div>
              <p class="text-xs text-muted-foreground">
                图片
              </p>
              <p class="text-2xl font-bold mt-1">
                {{ stats.images || 0 }}
              </p>
            </div>
            <div class="size-10 rounded-xl bg-success-muted flex items-center justify-center">
              <ImageIcon class="size-5 text-success-muted-foreground" />
            </div>
          </div>
        </div>
      </AdminCard>
      <AdminCard class="overflow-hidden">
        <div class="p-4">
          <div class="flex items-center justify-between">
            <div>
              <p class="text-xs text-muted-foreground">
                视频/音频/文档
              </p>
              <p class="text-2xl font-bold mt-1">
                {{ stats.videos + stats.audios + stats.documents }}
              </p>
            </div>
            <div class="size-10 rounded-xl bg-info-muted flex items-center justify-center">
              <FileText class="size-5 text-info-muted-foreground" />
            </div>
          </div>
        </div>
      </AdminCard>
    </div>

    <div class="flex flex-col sm:flex-row gap-3 items-stretch sm:items-center justify-between">
      <div class="flex flex-col sm:flex-row gap-3 items-stretch sm:items-center flex-1">
        <div class="relative flex-1 max-w-sm">
          <Search class="absolute left-3 top-1/2 -translate-y-1/2 size-4 text-muted-foreground" />
          <Input
            v-model="searchQuery"
            placeholder="搜索文件名..."
            aria-label="搜索文件名"
            class="pl-9"
            @keyup.enter="applyFilter"
          />
        </div>
        <Select
          :model-value="mimeFilter"
          @update:model-value="onMimeFilterChange"
        >
          <SelectTrigger
            class="w-[140px]"
            aria-label="按文件类型筛选"
          >
            <SelectValue placeholder="文件类型" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">
              全部
            </SelectItem>
            <SelectItem value="image">
              图片
            </SelectItem>
            <SelectItem value="video">
              视频
            </SelectItem>
            <!-- 后端 file_type 白名单是 image/video/audio/document 四类； -->
            <!-- 此前 UI 漏了 audio，管理员无法单独筛出音频文件 -->
            <SelectItem value="audio">
              音频
            </SelectItem>
            <SelectItem value="document">
              文档
            </SelectItem>
          </SelectContent>
        </Select>
      </div>
      <div class="flex items-center gap-2">
        <div class="flex items-center rounded-lg border p-0.5">
          <Button
            :variant="viewMode === 'grid' ? 'secondary' : 'ghost'"
            size="icon-sm"
            class="size-8"
            title="网格视图"
            aria-label="网格视图"
            @click="setViewMode('grid')"
          >
            <LayoutGrid data-icon="inline-start" />
          </Button>
          <Button
            :variant="viewMode === 'list' ? 'secondary' : 'ghost'"
            size="icon-sm"
            class="size-8"
            title="列表视图"
            aria-label="列表视图"
            @click="setViewMode('list')"
          >
            <List data-icon="inline-start" />
          </Button>
        </div>
        <Button
          v-if="selectedIds.length > 0"
          variant="destructive"
          size="sm"
          @click="confirmBatchDelete"
        >
          <Trash2 data-icon="inline-start" />
          批量删除 ({{ selectedIds.length }})
        </Button>
        <Button
          variant="outline"
          size="sm"
          :disabled="uploading"
          @click="triggerUpload"
        >
          <Loader2
            v-if="uploading"
            data-icon="inline-start"
            class="animate-spin"
          />
          <Upload
            v-else
            data-icon="inline-start"
          />
          批量上传文件
        </Button>
        <input
          ref="uploadInputRef"
          type="file"
          multiple
          class="hidden"
          :accept="uploadAccept"
          @change="onFilesUpload"
        >
      </div>
    </div>

    <MediaUploadQueue
      :items="uploadQueue"
      class="pb-2"
      @remove="removeUploadItem"
      @clear-finished="clearUploadFinished"
    />

    <div
      v-if="loading"
      :class="viewMode === 'grid'
        ? 'grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-6 gap-4'
        : 'flex flex-col card-surface overflow-hidden'"
    >
      <template v-if="viewMode === 'grid'">
        <div
          v-for="i in 12"
          :key="i"
          class="flex flex-col gap-2"
        >
          <Skeleton class="aspect-square w-full rounded-xl" />
          <Skeleton class="h-3 w-full rounded" />
          <Skeleton class="h-3 w-1/2 rounded" />
        </div>
      </template>
      <template v-else>
        <div
          v-for="i in 10"
          :key="i"
          class="flex items-center gap-3 px-3 py-2 border-b last:border-b-0"
        >
          <Skeleton class="size-10 rounded-md shrink-0" />
          <Skeleton class="h-3 flex-1 rounded" />
          <Skeleton class="h-3 w-16 rounded" />
          <Skeleton class="h-3 w-20 rounded" />
        </div>
      </template>
    </div>

    <div
      v-else-if="loadError"
      class="py-16 text-center"
    >
      <Alert
        variant="destructive"
        class="max-w-md mx-auto"
      >
        <AlertCircle class="size-4" />
        <AlertTitle>加载失败</AlertTitle>
        <AlertDescription>媒体资源库加载失败，请检查网络或稍后重试</AlertDescription>
        <Button
          variant="outline"
          size="sm"
          class="mt-3"
          @click="requestFetch"
        >
          <RefreshCw data-icon="inline-start" />
          重试
        </Button>
      </Alert>
    </div>

    <div
      v-else-if="!mediaItems.length"
      class="py-16 text-center"
    >
      <Alert
        variant="info"
        class="max-w-md mx-auto"
      >
        <Info class="size-4" />
        <AlertTitle v-if="hasActiveFilter">
          无匹配结果
        </AlertTitle>
        <AlertDescription v-if="hasActiveFilter">
          当前筛选条件下没有文件，可调整关键词或文件类型后重新搜索
        </AlertDescription>
        <template v-else>
          <AlertTitle>暂无文件</AlertTitle>
          <AlertDescription>暂无文件，上传您的第一个文件吧</AlertDescription>
        </template>
      </Alert>
    </div>

    <div
      v-else-if="viewMode === 'grid'"
      class="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-6 gap-4"
    >
      <div
        v-for="m in mediaItems"
        :key="m.id"
        :class="[
          'group relative rounded-xl border bg-card overflow-hidden shadow-sm transition-shadow hover:shadow-md cursor-pointer' // panel-exempt: 媒体库缩略图瓦片，内容由图片铺满，card-surface 的渐变玻璃面/内发光无从体现
        ]"
        role="button"
        tabindex="0"
        :aria-label="`预览文件 ${m.filename}`"
        @click="openPreview(m)"
        @keydown="onCardKeydown($event, m)"
      >
        <div class="aspect-square bg-muted relative overflow-hidden">
          <template v-if="isImage(m.mime)">
            <img
              :src="m.url"
              :alt="m.filename"
              class="size-full object-cover"
              loading="lazy"
            >
          </template>
          <template v-else>
            <div class="size-full flex items-center justify-center">
              <component
                :is="mimeIcon(m.mime)"
                class="size-12 text-muted-foreground"
              />
            </div>
          </template>

          <div class="absolute top-2 right-2 opacity-0 group-hover:opacity-100 focus-within:opacity-100 transition-opacity flex items-center gap-1">
            <Button
              variant="destructive"
              size="icon"
              class="h-7 w-7 backdrop-blur-sm"
              title="删除文件"
              :aria-label="`删除文件 ${m.filename}`"
              @click.stop="confirmDelete(m.id)"
            >
              <Trash2 data-icon="inline-start" />
            </Button>
          </div>

          <div
            class="absolute bottom-2 right-2"
            @click.stop
          >
            <div
              :class="[
                'size-5 rounded flex items-center justify-center border transition-all',
                selectedIds.includes(m.id)
                  ? 'bg-primary border-primary text-primary-foreground'
                  : 'bg-background/80 backdrop-blur-sm opacity-0 group-hover:opacity-100 focus-within:opacity-100'
              ]"
            >
              <Checkbox
                :model-value="selectedIds.includes(m.id)"
                class="size-4 data-[state=checked]:bg-primary data-[state=checked]:border-primary"
                :aria-label="`选择文件 ${m.filename}`"
                @update:model-value="(v: unknown) => toggleSelect(m.id, v)"
              />
            </div>
          </div>
        </div>
        <div class="flex flex-col gap-1 p-2">
          <p
            class="text-xs font-medium truncate"
            :title="m.filename"
          >
            {{ m.filename }}
          </p>
          <p class="text-xs text-muted-foreground">
            {{ formatSize(m.size_bytes) }}
          </p>
        </div>
      </div>
    </div>

    <div
      v-else
      class="flex flex-col card-surface overflow-hidden"
    >
      <div
        v-for="m in mediaItems"
        :key="m.id"
        class="group flex items-center gap-3 px-3 py-2 border-b last:border-b-0 transition-colors hover:bg-muted/50 cursor-pointer"
        role="button"
        tabindex="0"
        :aria-label="`预览文件 ${m.filename}`"
        @click="openPreview(m)"
        @keydown="onCardKeydown($event, m)"
      >
        <button
          type="button"
          class="shrink-0 rounded border p-0.5 flex items-center justify-center transition-colors"
          :class="selectedIds.includes(m.id)
            ? 'bg-primary border-primary text-primary-foreground'
            : 'bg-background border-input'"
          :aria-label="selectedIds.includes(m.id) ? '取消选择' : '选择'"
          @click.stop="toggleSelectRow(m.id)"
        >
          <Check
            v-if="selectedIds.includes(m.id)"
            class="size-3"
          />
          <span
            v-else
            class="size-3"
          />
        </button>
        <div class="size-10 shrink-0 rounded-md overflow-hidden bg-muted flex items-center justify-center">
          <img
            v-if="isImage(m.mime)"
            :src="m.url"
            :alt="m.filename"
            class="size-full object-cover"
            loading="lazy"
          >
          <component
            :is="mimeIcon(m.mime)"
            v-else
            class="size-5 text-muted-foreground"
          />
        </div>
        <p
          class="min-w-0 flex-1 truncate text-sm font-medium"
          :title="m.filename"
        >
          {{ m.filename }}
        </p>
        <Badge
          variant="secondary"
          class="shrink-0"
        >
          {{ typeLabel(m) }}
        </Badge>
        <span class="hidden sm:block w-20 shrink-0 text-right text-xs tabular-nums text-muted-foreground">
          {{ formatSize(m.size_bytes) }}
        </span>
        <span class="hidden md:block w-24 shrink-0 text-xs text-muted-foreground">
          {{ shortDate(m.created_at) }}
        </span>
        <Button
          variant="destructive"
          size="icon-sm"
          class="size-8 shrink-0 opacity-0 group-hover:opacity-100 focus-within:opacity-100 transition-opacity"
          title="删除"
          :aria-label="`删除文件 ${m.filename}`"
          @click.stop="confirmDelete(m.id)"
        >
          <Trash2 data-icon="inline-start" />
        </Button>
      </div>
    </div>

    <div
      v-if="!loading && !loadError && total > 0"
      class="pt-2"
    >
      <AdminPagination
        v-model:page="page"
        v-model:page-size="pageSize"
        :total="total"
        :page-size-options="[10, 20, 50, 100]"
        unit="个"
        @update:page="onPageChange"
        @update:page-size="onPageSizeChange"
      />
    </div>

    <AdminConfirmDialog
      v-model:open="deleteDialogOpen"
      title="确认删除"
      description="删除后该文件将无法恢复，确定继续吗？"
      confirm-text="确认删除"
      :on-confirm="doDelete"
    />

    <AdminConfirmDialog
      v-model:open="batchDeleteDialogOpen"
      title="确认批量删除"
      confirm-text="确认删除"
      :on-confirm="doBatchDelete"
    >
      <template #description>
        将删除选中的 <span class="font-medium text-destructive">{{ selectedIds.length }}</span> 个文件，此操作无法恢复。
      </template>
    </AdminConfirmDialog>
    <MediaPreviewDialog
      v-model:open="previewOpen"
      :media="previewItem"
      @updated="onMediaUpdated"
    />
  </div>
</template>

<script setup lang="ts">
import AdminCard from '~~/components/admin/AdminCard.vue'
import { Button } from '~~/components/ui/button'
import { Input } from '~~/components/ui/input'
import { Skeleton } from '~~/components/ui/skeleton'
import { Alert, AlertDescription, AlertTitle } from '~~/components/ui/alert'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '~~/components/ui/select'
import { Checkbox } from '~~/components/ui/checkbox'
import { Badge } from '~~/components/ui/badge'
import MediaUploadQueue from '~~/components/admin/media/MediaUploadQueue.vue'
import MediaPreviewDialog from '~~/components/admin/media/MediaPreviewDialog.vue'
import {
  Search, Upload, Trash2, Info, Loader2, Files, HardDrive,
  Image as ImageIcon, FileText, FileVideo, FileIcon as FileDoc, FileArchive,
  LayoutGrid, List, RefreshCw, AlertCircle, Check
} from '@lucide/vue'
import {
  fetchAdminMediaLibrary,
  deleteAdminMedia,
  deleteAdminMediaBatch,
  fetchAdminMediaStats,
  type AdminMediaStats
} from '~~/composables/useAdminManage'
import { useUploadProgress, validateUploadFiles, ALLOWED_UPLOAD_EXTENSIONS } from '~~/composables/useUploadProgress'
import type { MediaLibraryItem } from '~~/types/media-library'

definePageMeta({ ssr: false, layout: 'admin' })

const toast = useToast()

const loading = ref(false)
const loadError = ref(false)
const mediaItems = shallowRef<MediaLibraryItem[]>([])
const stats = ref<AdminMediaStats>({
  total_files: 0,
  total_size_bytes: 0,
  images: 0,
  videos: 0,
  audios: 0,
  documents: 0
})
const searchQuery = ref('')
const mimeFilter = ref('all')
const page = ref(1)
// 必须与 AdminPagination 的 page-size-options 之一对应，否则「每页」下拉无匹配项
const pageSize = ref(20)
const total = ref(0)
const selectedIds = ref<number[]>([])

const uploadInputRef = ref<HTMLInputElement | null>(null)
/** 与 validateUploadFiles / 后端 allowed_types 同一份白名单，避免选择器里挑到必然被拒的文件 */
const uploadAccept = ALLOWED_UPLOAD_EXTENSIONS.map(ext => `.${ext}`).join(',')

const deleteDialogOpen = ref(false)
const deleteTargetId = ref<number | null>(null)
const batchDeleteDialogOpen = ref(false)

// ---- 视图切换（grid / list）----
const VIEW_MODE_STORAGE_KEY = 'rosetta-admin-media-view-mode'
type MediaViewMode = 'grid' | 'list'
const viewMode = ref<MediaViewMode>('grid')

function setViewMode(mode: MediaViewMode) {
  viewMode.value = mode
  if (import.meta.client) {
    try {
      localStorage.setItem(VIEW_MODE_STORAGE_KEY, mode)
    } catch { /* storage disabled */ }
  }
}

function restoreViewMode() {
  try {
    const saved = localStorage.getItem(VIEW_MODE_STORAGE_KEY)
    if (saved === 'grid' || saved === 'list') viewMode.value = saved
  } catch { /* storage disabled */ }
}

// ---- 上传进度队列 ----
const {
  queue: uploadQueue,
  uploading,
  startUploads,
  removeItem: removeUploadItem,
  clearFinished: clearUploadFinished
} = useUploadProgress()

// ---- 预览对话框 ----
const previewOpen = ref(false)
const previewItem = ref<MediaLibraryItem | null>(null)

function openPreview(m: MediaLibraryItem) {
  previewItem.value = m
  previewOpen.value = true
}

/**
 * 卡片是 div[role=button]，Enter/Space 需手动补键激活；
 * 只响应焦点落在卡片本身的按键，避免子级 Checkbox/Delete 按钮冒泡误触发预览。
 */
function onCardKeydown(ev: KeyboardEvent, m: MediaLibraryItem) {
  if (ev.target !== ev.currentTarget) return
  if (ev.key === 'Enter' || ev.key === ' ') {
    ev.preventDefault()
    openPreview(m)
  }
}

/** PUT 保存成功后同步列表中对应项的元数据。 */
function onMediaUpdated(payload: { id: number, title: string, alt_text: string, description: string }) {
  const patch = (list: MediaLibraryItem[]) => list.map(x =>
    x.id === payload.id
      ? { ...x, title: payload.title, alt_text: payload.alt_text, description: payload.description }
      : x
  )
  mediaItems.value = patch(mediaItems.value)
  if (previewItem.value && previewItem.value.id === payload.id) {
    previewItem.value = { ...previewItem.value, ...payload }
  }
}

function typeLabel(m: MediaLibraryItem): string {
  const mime = m.mime || ''
  if (mime.startsWith('image/')) return '图片'
  if (mime.startsWith('video/')) return '视频'
  if (mime.startsWith('audio/')) return '音频'
  if (m.file_type) return m.file_type
  if (mime.startsWith('text/') || mime.includes('pdf') || mime.includes('word') || mime.includes('document')) return '文档'
  return mime || '其他'
}

function shortDate(raw: string | null | undefined): string {
  if (!raw) return '—'
  const d = new Date(raw)
  if (Number.isNaN(d.getTime())) return raw
  return d.toLocaleDateString()
}

function formatSize(bytes: number): string {
  if (!bytes || bytes <= 0) return '0 B'
  const kb = bytes / 1024
  if (kb < 1024) return `${kb.toFixed(1)} KB`
  const mb = kb / 1024
  if (mb < 1024) return `${mb.toFixed(1)} MB`
  return `${(mb / 1024).toFixed(2)} GB`
}

function isImage(mime?: string | null): boolean {
  return mime?.startsWith('image/') ?? false
}

function mimeIcon(mime?: string | null): unknown {
  if (!mime) return FileText
  if (mime.startsWith('video/')) return FileVideo
  if (mime.includes('pdf') || mime.includes('word') || mime.includes('document') || mime.startsWith('text/')) return FileDoc
  if (mime.includes('zip') || mime.includes('rar') || mime.includes('tar') || mime.includes('archive')) return FileArchive
  return FileText
}

/**
 * 「文件类型」下拉的值其实是后端 ``file_type``（image / video / audio / document），
 * 不是 MIME 前缀——历史上这里叫 mimePrefix，改名后变量名与语义才对得上。
 * 'all' 是「全部」选项的哨兵值：reka-ui 的 SelectItem 禁止空串 value。
 */
function fileTypeFilter(): string | undefined {
  const allowed = new Set(['image', 'video', 'audio', 'document'])
  return allowed.has(mimeFilter.value) ? mimeFilter.value : undefined
}

/** 区分「筛选无结果」与「库内确实没有文件」，避免给出误导性的上传引导 */
const hasActiveFilter = computed(() =>
  searchQuery.value.trim() !== '' || mimeFilter.value !== 'all'
)

/**
 * 并发筛选/翻页时响应可能乱序到达：每次请求取一个序号，
 * 只有最新一次请求的结果才允许写回状态，否则旧响应会覆盖新结果。
 */
let fetchSeq = 0

async function fetchData() {
  const seq = ++fetchSeq
  loading.value = true
  loadError.value = false
  try {
    const [itemsRes, statsRes] = await Promise.allSettled([
      fetchAdminMediaLibrary({
        page: page.value,
        page_size: pageSize.value,
        search: searchQuery.value.trim() || undefined,
        mime_prefix: fileTypeFilter()
      }),
      fetchAdminMediaStats()
    ])
    if (seq !== fetchSeq) return
    if (itemsRes.status === 'fulfilled') {
      mediaItems.value = itemsRes.value.items ?? []
      total.value = itemsRes.value.total ?? 0
      // 删除/筛选后当前页可能越界：夹回最后一页并重查一次
      const maxPage = Math.max(1, Math.ceil(total.value / pageSize.value))
      if (mediaItems.value.length === 0 && total.value > 0 && page.value > maxPage) {
        page.value = maxPage
        return fetchData()
      }
      // 翻页/筛选/删除后本页条目已换一批：清掉不在当前结果里的选中项，
      // 否则批量删除会连带删掉用户看不见的旧选中文件
      const visibleIds = new Set(mediaItems.value.map(x => x.id))
      selectedIds.value = selectedIds.value.filter(id => visibleIds.has(id))
    } else {
      loadError.value = true
      mediaItems.value = []
      total.value = 0
    }
    if (statsRes.status === 'fulfilled') {
      stats.value = statsRes.value
    }
  } catch (e) {
    if (seq !== fetchSeq) return
    // apiFetch 已统一 toast，页面另有 loadError Alert 展示，不重复弹错
    console.error('[media-library] fetchData failed:', e)
    loadError.value = true
    mediaItems.value = []
    total.value = 0
  } finally {
    if (seq === fetchSeq) loading.value = false
  }
}

/** 搜索/筛选变化统一入口：清空选中、回到第 1 页再查询 */
function applyFilter() {
  selectedIds.value = []
  page.value = 1
  requestFetch()
}

function onMimeFilterChange(value: unknown) {
  mimeFilter.value = typeof value === 'string' ? value : 'all'
  applyFilter()
}

// AdminPagination 一次交互可能同时 emit page 与 page-size（且重复 emit），
// 合并到同一个微任务里，避免一次点击打出两遍相同请求。
let fetchQueued = false
function requestFetch() {
  if (fetchQueued) return
  fetchQueued = true
  queueMicrotask(() => {
    fetchQueued = false
    void fetchData()
  })
}

function onPageChange() {
  requestFetch()
}

function onPageSizeChange() {
  selectedIds.value = []
  requestFetch()
}

function triggerUpload() {
  uploadInputRef.value?.click()
}

async function onFilesUpload(ev: Event) {
  const target = ev.target as HTMLInputElement
  const files = Array.from(target.files ?? [])
  if (target) target.value = ''
  if (!files.length) return

  // 客户端预校验：≤20MB + 扩展名白名单，被拒绝的文件逐个 toast 原因
  const { accepted, rejected } = validateUploadFiles(files)
  for (const r of rejected) {
    toast.error(`${r.name}：${r.reason}`)
  }
  if (!accepted.length) return

  // 队列 + XHR 进度上传（最多 4 路并发），全部结束后汇总
  const { success, failed, aborted } = await startUploads(accepted)
  const finished = success + failed + aborted
  const skipped = accepted.length - finished

  if (success > 0) {
    const parts = [`成功 ${success}`]
    if (failed) parts.push(`失败 ${failed}`)
    if (aborted) parts.push(`已取消 ${aborted}`)
    if (skipped > 0) parts.push(`未发送 ${skipped}`)
    toast.success(`上传完成：${parts.join(' / ')}`)
    requestFetch()
  } else if (failed > 0 || aborted > 0) {
    toast.error(`文件上传失败（${failed} 个）、已取消（${aborted} 个），详见上传任务列表`)
  }
}

function toggleSelect(id: number, checked: unknown) {
  const isChecked = checked === true || (checked as { checked?: boolean })?.checked === true
  if (isChecked) {
    if (!selectedIds.value.includes(id)) selectedIds.value.push(id)
  } else {
    selectedIds.value = selectedIds.value.filter(x => x !== id)
  }
}

/** 列表视图的行选择：直接翻转选中态。 */
function toggleSelectRow(id: number) {
  if (selectedIds.value.includes(id)) {
    selectedIds.value = selectedIds.value.filter(x => x !== id)
  } else {
    selectedIds.value = [...selectedIds.value, id]
  }
}

function confirmDelete(id: number) {
  deleteTargetId.value = id
  deleteDialogOpen.value = true
}

async function doDelete() {
  // 先把 id 取出来：deleteTargetId 在成功后会被置 null，
  // 若先置 null 再 filter（`x !== null`）等于没删，selectedIds 会残留已删除项。
  const id = deleteTargetId.value
  if (id === null) return
  await deleteAdminMedia(id)
  toast.success('删除成功')
  selectedIds.value = selectedIds.value.filter(x => x !== id)
  deleteTargetId.value = null
  requestFetch()
}

function confirmBatchDelete() {
  if (selectedIds.value.length === 0) return
  batchDeleteDialogOpen.value = true
}

async function doBatchDelete() {
  const ids = [...selectedIds.value]
  if (ids.length === 0) return
  const res = await deleteAdminMediaBatch(ids)
  selectedIds.value = []
  // 后端逐条汇报三种结果：真删掉的、路径非法被保留的、库里本来没有的。
  // 只报"已删除 N 个"会让管理员以为剩下的文件也一起没了。
  const { deleted_count: deleted, refused = [], missing_ids: missing = [] } = res
  const n = typeof deleted === 'number' ? deleted : ids.length
  const notes: string[] = []
  if (refused.length > 0) {
    // reason 是服务端口径（被内容引用 / 路径非法），按原因分组播报，前端不再写死一种
    const byReason = new Map<string, number>()
    for (const r of refused)
      byReason.set(r.reason, (byReason.get(r.reason) ?? 0) + 1)
    const detail = [...byReason].map(([reason, count]) => `${count} 个（${reason}）`).join('，')
    notes.push(`${refused.length} 个已保留未删除：${detail}`)
  }
  if (missing.length > 0) notes.push(`${missing.length} 个记录已不存在`)
  if (notes.length > 0)
    toast.warning(`已删除 ${n} 个文件，${notes.join('，')}`)
  else toast.success(`批量删除成功：${ids.length} 个文件`)

  // 整批删完后当前页可能越界：回退到有效页再查
  const remaining = Math.max(0, total.value - n)
  const maxPage = Math.max(1, Math.ceil(remaining / pageSize.value))
  if (page.value > maxPage) page.value = maxPage
  requestFetch()
}

onMounted(() => {
  restoreViewMode()
  fetchData()
})
</script>
