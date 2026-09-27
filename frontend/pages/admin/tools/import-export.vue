<!--
  导入导出页：文章数据的双向搬运——导出 ZIP（json/markdown 两通道）与上传导入（覆盖/跳过同 slug）。
  契约：草稿仅 /export/posts 在 scope≠published 且 include_drafts=true 时输出，markdown 导出固定只含已发布并忽略范围选择；
  skip_existing 查询参数只有 /import/posts 支持（markdown 通道不接收）；导入接口 HTTP 200 仍可能 success:false（业务失败），必须抛出走内联错误而非提示"导入完成"。
-->
<template>
  <div class="flex flex-col gap-5">
    <AdminPageHeader
      title="导入导出"
      description="跨平台文章数据迁移与备份"
      :icon="ArrowLeftRight"
    />

    <Tabs
      v-model="activeTab"
      class="w-full"
    >
      <TabsList class="rounded-xl p-1 bg-muted/40">
        <TabsTrigger
          value="export"
          class="rounded-lg data-[state=active]:text-primary-foreground data-[state=active]:shadow-sm"
          :class="activeTab === 'export' ? 'bg-primary text-primary-foreground' : ''"
        >
          <Upload class="size-4 mr-1.5" /> 导出
        </TabsTrigger>
        <TabsTrigger
          value="import"
          class="rounded-lg data-[state=active]:text-primary-foreground data-[state=active]:shadow-sm"
          :class="activeTab === 'import' ? 'bg-primary text-primary-foreground' : ''"
        >
          <Download class="size-4 mr-1.5" /> 导入
        </TabsTrigger>
      </TabsList>

      <TabsContent
        value="export"
        class="flex flex-col gap-5 mt-6"
      >
        <AdminCard>
          <div class="flex-col gap-0 flex-row items-center gap-3 flex">
            <div class="size-9 rounded-lg bg-warning-muted flex items-center justify-center text-warning-muted-foreground">
              <FileJson class="size-5" />
            </div>
            <div class="flex-1">
              <h3 class="text-base font-semibold">
                步骤 1 · 选择导出格式
              </h3>
              <p class="text-sm text-muted-foreground">
                兼容主流博客平台的格式标准
              </p>
            </div>
          </div>
          <div>
            <Label
              for="export-format"
              class="text-sm"
            >
              导出格式
            </Label>
            <Select
              v-model="exportForm.format"
              class="max-w-md"
            >
              <SelectTrigger
                id="export-format"
                class="rounded-xl mt-1.5"
              >
                <SelectValue placeholder="选择导出格式" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="json">
                  Rosetta 数据包（ZIP：posts/categories/tags JSON）
                </SelectItem>
                <SelectItem value="markdown">
                  Markdown 打包（ZIP：每篇一个 .md，含 frontmatter）
                </SelectItem>
              </SelectContent>
            </Select>
            <p class="text-xs text-muted-foreground mt-2">
              后端当前仅提供以上两种导出通道；WordPress / Halo / Typecho 等第三方格式暂无导入导出实现，故不再列出，避免生成错误命名的文件。
            </p>
          </div>
        </AdminCard>

        <AdminCard>
          <div class="flex-col gap-0 flex-row items-center gap-3 flex">
            <div class="size-9 rounded-lg bg-info-muted flex items-center justify-center text-info-muted-foreground">
              <Filter class="size-5" />
            </div>
            <div class="flex-1">
              <h3 class="text-base font-semibold">
                步骤 2 · 选择范围
              </h3>
              <p class="text-sm text-muted-foreground">
                筛选需要导出的文章范围
              </p>
            </div>
          </div>
          <div class="flex flex-col gap-4">
            <div class="flex flex-col gap-2">
              <Label class="text-sm">导出范围</Label>
              <div
                class="inline-flex rounded-xl border border-border p-1 bg-card self-start"
                role="group"
                aria-label="导出范围"
              >
                <button
                  v-for="s in scopes"
                  :key="s.key"
                  type="button"
                  class="px-3.5 py-1.5 rounded-lg text-sm font-medium transition-all"
                  :class="exportForm.scope === s.key
                    ? 'bg-primary text-primary-foreground shadow-sm'
                    : 'text-muted-foreground hover:bg-muted hover:text-foreground'"
                  @click="exportForm.scope = s.key"
                >
                  {{ s.label }}
                </button>
              </div>
              <p class="text-xs text-muted-foreground">
                后端仅在 <code class="font-mono">include_drafts=true</code> 且范围非 published 时输出草稿。
              </p>
            </div>
            <p
              v-if="exportForm.format === 'markdown'"
              class="text-xs text-muted-foreground"
            >
              Markdown 导出固定为「已发布」文章，且忽略下方范围选择。
            </p>
            <div class="grid md:grid-cols-1 gap-4">
              <div class="flex flex-col gap-2">
                <Label
                  for="export-from-date"
                  class="text-sm flex items-center gap-1.5"
                >
                  <CalendarDays class="size-3.5 text-primary" />
                  按创建日期范围筛选（选完开始会自动弹出结束）
                </Label>
                <div class="flex items-center gap-2 rounded-xl border border-border/60 bg-background/60 px-3 py-2.5">
                  <div class="relative group flex-1">
                    <input
                      id="export-from-date"
                      v-model="exportForm.fromDate"
                      type="date"
                      class="w-full h-9 rounded-lg border border-transparent bg-transparent px-2.5 text-sm text-foreground transition-colors hover:border-border focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus:bg-background"
                      :max="startMax"
                      placeholder="开始日期（含）"
                      @change="onFromChange"
                    >
                    <button
                      v-if="exportForm.fromDate"
                      type="button"
                      class="pointer-events-auto absolute right-1.5 top-1/2 -translate-y-1/2 opacity-0 group-hover:opacity-100 transition-opacity rounded-full p-0.5 hover:bg-muted text-muted-foreground hover:text-foreground"
                      aria-label="清除开始日期"
                      @click="exportForm.fromDate = ''"
                    >
                      <X class="size-3.5" />
                    </button>
                  </div>
                  <ChevronRight class="size-4 text-muted-foreground shrink-0" />
                  <div class="relative group flex-1">
                    <input
                      ref="exportToDateInputRef"
                      v-model="exportForm.toDate"
                      type="date"
                      class="w-full h-9 rounded-lg border border-transparent bg-transparent px-2.5 text-sm text-foreground transition-colors hover:border-border focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus:bg-background"
                      :min="endMin"
                      :max="endMax"
                      placeholder="结束日期（含）"
                      @change="onToChange"
                    >
                    <button
                      v-if="exportForm.toDate"
                      type="button"
                      class="pointer-events-auto absolute right-1.5 top-1/2 -translate-y-1/2 opacity-0 group-hover:opacity-100 transition-opacity rounded-full p-0.5 hover:bg-muted text-muted-foreground hover:text-foreground"
                      aria-label="清除结束日期"
                      @click="exportForm.toDate = ''"
                    >
                      <X class="size-3.5" />
                    </button>
                  </div>
                </div>
                <p
                  v-if="dateRangeHint"
                  class="text-xs text-muted-foreground flex items-center gap-1.5"
                >
                  <Info class="size-3.5 text-primary" />
                  {{ dateRangeHint }}
                </p>
              </div>
            </div>
          </div>
        </AdminCard>

        <AdminCard>
          <div class="flex-col gap-0 flex-row items-center gap-3 flex">
            <div class="size-9 rounded-lg bg-success-muted flex items-center justify-center text-success-muted-foreground">
              <Rocket class="size-5" />
            </div>
            <div class="flex-1">
              <h3 class="text-base font-semibold">
                步骤 3 · 生成导出文件
              </h3>
              <p class="text-sm text-muted-foreground">
                根据上述配置打包为可下载文件
              </p>
            </div>
          </div>
          <div class="flex flex-col gap-4">
            <div class="flex flex-col sm:flex-row sm:items-center gap-4">
              <Button
                :disabled="exporting"
                class="sm:w-auto w-full shadow-sm"
                @click="handleExport"
              >
                <Loader2
                  v-if="exporting"
                  data-icon="inline-start"
                  class="animate-spin"
                />
                <Package
                  v-else
                  data-icon="inline-start"
                />
                {{ exporting ? '正在生成...' : '生成导出文件' }}
              </Button>
              <p
                v-if="exporting"
                class="text-sm text-muted-foreground"
              >
                正在打包，文件较大时可能需要几秒...
              </p>
            </div>

            <Alert
              v-if="exportError"
              variant="destructive"
              class="rounded-xl"
            >
              <AlertTriangle class="size-4" />
              <AlertTitle>导出失败</AlertTitle>
              <AlertDescription class="flex flex-wrap items-center justify-between gap-3">
                <span>{{ exportError }}</span>
                <Button
                  variant="outline"
                  size="sm"
                  class="rounded-lg shrink-0"
                  :disabled="exporting"
                  @click="handleExport"
                >
                  <RotateCcw data-icon="inline-start" />
                  重试
                </Button>
              </AlertDescription>
            </Alert>

            <div
              v-if="downloadReady"
              class="p-5 rounded-xl border border-success/40 bg-success-muted/40"
            >
              <div class="flex items-start gap-3">
                <div class="size-11 rounded-xl bg-success text-success-foreground flex items-center justify-center shrink-0">
                  <Check class="size-5" />
                </div>
                <div class="flex-1 min-w-0">
                  <h3 class="font-semibold">
                    导出文件已生成
                  </h3>
                  <div class="mt-1 flex flex-wrap items-center gap-x-4 gap-y-1 text-sm text-muted-foreground">
                    <span>文件名：<span class="font-mono">{{ downloadReady.fileName }}</span></span>
                    <span>大小：{{ downloadReady.size }}</span>
                    <span>生成时间：{{ downloadReady.time }}</span>
                  </div>
                  <Button
                    variant="default"
                    size="sm"
                    class="mt-3 rounded-lg bg-success text-success-foreground hover:bg-success/90"
                    @click="doDownload"
                  >
                    <Download data-icon="inline-start" /> 立即下载
                  </Button>
                </div>
              </div>
            </div>
          </div>
        </AdminCard>
      </TabsContent>

      <TabsContent
        value="import"
        class="flex flex-col gap-5 mt-6"
      >
        <AdminCard>
          <div class="flex-col gap-0 flex-row items-center gap-3 flex">
            <div class="size-9 rounded-lg bg-primary-muted flex items-center justify-center text-primary-muted-foreground">
              <FileInput class="size-5" />
            </div>
            <div class="flex-1">
              <h3 class="text-base font-semibold">
                选择导入格式
              </h3>
              <p class="text-sm text-muted-foreground">
                后端支持 Rosetta 导出包（ZIP）与单篇 Markdown（.md，含 frontmatter）
              </p>
            </div>
          </div>
          <div>
            <Label
              for="import-format"
              class="text-sm"
            >
              导入格式
            </Label>
            <Select
              v-model="importForm.format"
              class="max-w-md"
            >
              <SelectTrigger
                id="import-format"
                class="rounded-xl mt-1.5"
              >
                <SelectValue placeholder="选择导入格式" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="json">
                  Rosetta 数据包 (.zip)
                </SelectItem>
                <SelectItem value="markdown">
                  单篇 Markdown (.md)
                </SelectItem>
              </SelectContent>
            </Select>
          </div>
        </AdminCard>

        <AdminCard>
          <div class="flex-col gap-0 flex-row items-center gap-3 flex">
            <div class="size-9 rounded-lg bg-warning-muted flex items-center justify-center text-warning-muted-foreground">
              <UploadCloud class="size-5" />
            </div>
            <div class="flex-1">
              <h3 class="text-base font-semibold">
                上传文件
              </h3>
              <p class="text-sm text-muted-foreground">
                拖入文件或点击选择，最大 256MB
              </p>
            </div>
          </div>
          <div>
            <div
              class="rounded-2xl border-2 border-dashed border-border hover:border-primary/50 bg-muted/20 hover:bg-muted/40 transition-all p-8 text-center cursor-pointer focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
              :class="{ 'border-primary bg-primary/5': dragging }"
              role="button"
              tabindex="0"
              aria-label="选择导入文件"
              @click="fileInputRef?.click()"
              @keydown.enter.prevent="fileInputRef?.click()"
              @keydown.space.prevent="fileInputRef?.click()"
              @dragover.prevent="dragging = true"
              @dragleave.prevent="dragging = false"
              @drop.prevent="handleDrop"
            >
              <input
                ref="fileInputRef"
                type="file"
                class="hidden"
                :accept="acceptForFormat"
                @change="handleFileSelect"
              >
              <div
                class="size-16 rounded-2xl mx-auto mb-4 flex items-center justify-center bg-primary text-primary-foreground"
              >
                <CloudUpload class="size-8" />
              </div>
              <div
                v-if="!importForm.file"
                class="flex flex-col gap-1"
              >
                <p class="font-semibold">
                  拖拽文件到此处，或点击选择文件
                </p>
                <p class="text-sm text-muted-foreground">
                  {{ acceptForFormat }}
                </p>
              </div>
              <div
                v-else
                class="flex flex-col gap-1"
              >
                <p class="font-semibold truncate">
                  {{ importForm.file.name }}
                </p>
                <p class="text-sm text-muted-foreground tabular-nums">
                  {{ formatSize(importForm.file.size) }}
                </p>
                <Button
                  variant="ghost"
                  size="sm"
                  class="mt-2 rounded-lg text-xs"
                  @click.stop="clearFile"
                >
                  <X data-icon="inline-start" /> 移除文件
                </Button>
              </div>
            </div>
          </div>
        </AdminCard>

        <AdminCard>
          <div class="flex-col gap-0 flex-row items-center gap-3 flex">
            <div class="size-9 rounded-lg bg-muted flex items-center justify-center text-muted-foreground">
              <Settings2 class="size-5" />
            </div>
            <div class="flex-1">
              <h3 class="text-base font-semibold">
                导入选项
              </h3>
              <p class="text-sm text-muted-foreground">
                控制导入时的行为模式
              </p>
            </div>
          </div>
          <div class="flex flex-col gap-3">
            <label
              class="flex items-start gap-3 cursor-pointer p-3 rounded-xl hover:bg-muted transition-colors border border-border"
              :class="importForm.opts.overwrite ? 'border-warning/60 bg-warning-muted/30' : ''"
            >
              <Checkbox
                :model-value="importForm.opts.overwrite"
                @update:model-value="importForm.opts.overwrite = !!$event"
              />
              <div class="flex flex-col gap-0.5">
                <div class="font-medium">
                  覆盖已有同 slug 文章
                </div>
                <div class="text-sm text-muted-foreground">
                  对应后端 <code class="font-mono">skip_existing=false</code>；不勾选时同名 slug 会被跳过。
                  <b
                    v-if="importForm.opts.overwrite"
                    class="text-warning"
                  >该操作会改写线上内容，需要输入确认短语。</b>
                </div>
              </div>
            </label>
            <p class="text-xs text-muted-foreground">
              「自动生成缩略图」「导入后存为草稿」等选项目前后端未实现，已移除以免产生无效请求。
            </p>
          </div>
        </AdminCard>

        <AdminCard>
          <div class="flex flex-col gap-5 pt-6">
            <div class="flex flex-col gap-2">
              <div class="flex items-center justify-between">
                <span class="font-medium">导入状态</span>
                <span class="text-sm text-muted-foreground tabular-nums">
                  {{ importing ? '处理中' : (importResult ? (importResult.ok ? '已完成' : '失败') : '待开始') }}
                </span>
              </div>
              <div
                class="h-2.5 rounded-full bg-muted overflow-hidden"
                role="progressbar"
                :aria-valuemin="0"
                :aria-valuemax="100"
                :aria-valuenow="importing ? undefined : (importResult?.ok ? 100 : 0)"
                :aria-label="importing ? '正在导入' : '导入进度'"
              >
                <div
                  v-if="importing"
                  class="h-full w-full origin-left animate-pulse rounded-full bg-primary"
                />
                <div
                  v-else
                  class="h-full rounded-full transition-all duration-500"
                  :style="{
                    width: importResult?.ok ? '100%' : '0%',
                    backgroundColor: importResult?.ok ? 'hsl(var(--success))' : 'hsl(var(--destructive))'
                  }"
                />
              </div>
            </div>
            <div class="flex flex-col sm:flex-row gap-3 sm:items-center sm:justify-between">
              <p
                v-if="!importForm.file"
                class="text-sm text-muted-foreground"
              >
                请先上传导入文件
              </p>
              <p
                v-else-if="importing"
                class="text-sm text-muted-foreground"
              >
                正在导入中，请勿关闭页面…
              </p>
              <p
                v-else-if="importError"
                class="text-sm text-destructive"
              >
                {{ importError }}
              </p>
              <p
                v-else
                class="text-sm text-muted-foreground"
              >
                准备就绪后点击下方按钮，确认后即可开始导入
              </p>
              <Button
                :disabled="importing || !importForm.file"
                class="sm:w-auto w-full shadow-sm"
                @click="importConfirmOpen = true"
              >
                <Loader2
                  v-if="importing"
                  data-icon="inline-start"
                  class="animate-spin"
                />
                <Play
                  v-else
                  data-icon="inline-start"
                />
                {{ importing ? '导入中...' : '开始导入' }}
              </Button>
            </div>

            <Alert
              v-if="importResult"
              :variant="importResult.ok ? 'success' : 'destructive'"
              class="rounded-xl"
            >
              <CheckCircle
                v-if="importResult.ok"
                class="size-4"
              />
              <AlertTriangle
                v-else
                class="size-4"
              />
              <AlertTitle>{{ importResult.ok ? '导入完成' : '导入未成功' }}</AlertTitle>
              <AlertDescription class="flex flex-col gap-1">
                <div>
                  成功导入 <b>{{ importResult.created }}</b> 篇
                  <span v-if="importResult.skipped > 0">，跳过 <b class="text-muted-foreground">{{ importResult.skipped }}</b> 篇</span>
                  <span v-if="importResult.failed > 0">，失败 <b class="text-destructive">{{ importResult.failed }}</b> 篇</span>
                </div>
                <p
                  v-if="importResult.message"
                  class="text-xs text-muted-foreground"
                >
                  {{ importResult.message }}
                </p>
                <ul
                  v-if="importResult.errors && importResult.errors.length"
                  class="flex flex-col gap-0.5 text-[11px] text-muted-foreground list-disc pl-4 mt-2"
                >
                  <li
                    v-for="(err, i) in importResult.errors.slice(0, 5)"
                    :key="`err-${i}-${err}`"
                  >
                    {{ err }}
                  </li>
                  <li
                    v-if="importResult.errors.length > 5"
                    class="italic opacity-70"
                  >
                    另有 {{ importResult.errors.length - 5 }} 条错误未展示…
                  </li>
                </ul>
              </AlertDescription>
            </Alert>
          </div>
        </AdminCard>
      </TabsContent>
    </Tabs>

    <DangerConfirmDialog
      v-model:open="importConfirmOpen"
      :title="importForm.opts.overwrite ? '危险：覆盖导入文章' : '确认导入文章'"
      :description="`将使用「${formatLabel}」通道导入 ${importForm.file?.name ?? '（未选择文件）'}（${importForm.opts.overwrite ? '同 slug 覆盖写入' : '跳过已存在 slug'}）。导入会直接写入线上文章数据且不可撤销，建议先做一次全站备份。`"
      confirm-text="确认导入"
      :confirm-phrase="importForm.opts.overwrite ? '覆盖导入' : ''"
      :on-confirm="runImport"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, watch, nextTick } from 'vue'
import { apiFetch } from '~~/composables/useApi'
import { extractApiErrorMessage } from '~~/lib/utils'
import { useToast } from '~~/composables/useToast'
import {
  ArrowLeftRight, Upload, Download, FileJson, FileInput, Filter, Rocket,
  Package, Check, CloudUpload, UploadCloud, Settings2, Play, X, Loader2,
  CheckCircle, ChevronRight, CalendarDays, Info, AlertTriangle, RotateCcw
} from '@lucide/vue'
import { Button } from '~~/components/ui/button'
import AdminCard from '~~/components/admin/AdminCard.vue'
import DangerConfirmDialog from '~~/components/admin/tools/DangerConfirmDialog.vue'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '~~/components/ui/tabs'
import { Label } from '~~/components/ui/label'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '~~/components/ui/select'
import { Checkbox } from '~~/components/ui/checkbox'
import { Alert, AlertTitle, AlertDescription } from '~~/components/ui/alert'

definePageMeta({ ssr: false, layout: 'admin' })

const toast = useToast()

const activeTab = ref('export')
/** 后端 /admin/export/posts 只认 scope=published|其它，草稿需显式 include_drafts=true */
const scopes = [
  { key: 'published', label: '仅已发布' },
  { key: 'all', label: '全部（含草稿）' }
] as const

/** 后端 ImportResult 原始结构 */
interface ImportResultResponse {
  success?: boolean
  message?: string
  created_count?: number
  skipped_count?: number
  error_count?: number
  errors?: string[]
}

const exporting = ref(false)
const exportError = ref('')
const downloadReady = ref<{ fileName: string, size: string, time: string, blob: Blob } | null>(null)

const exportToDateInputRef = ref<HTMLInputElement | null>(null)

const exportForm = reactive({
  format: 'json' as 'json' | 'markdown',
  scope: 'published' as 'all' | 'published',
  fromDate: '',
  toDate: ''
})

const todayStr = computed(() => {
  const d = new Date()
  const y = d.getFullYear()
  const m = String(d.getMonth() + 1).padStart(2, '0')
  const day = String(d.getDate()).padStart(2, '0')
  return `${y}-${m}-${day}`
})
const startMax = computed(() => exportForm.toDate || todayStr.value)
const endMin = computed(() => exportForm.fromDate || '')
const endMax = todayStr

const dateRangeHint = computed(() => {
  if (exportForm.fromDate && exportForm.toDate) {
    return `已选择范围：${exportForm.fromDate} ～ ${exportForm.toDate}（含边界）`
  }
  if (exportForm.fromDate) {
    return `已选开始日期：${exportForm.fromDate}，请选择结束日期（已自动弹出）`
  }
  return ''
})

watch(() => exportForm.fromDate, (val) => {
  if (!val) return
  if (exportForm.toDate && val > exportForm.toDate) {
    exportForm.toDate = val
  }
  nextTick(() => {
    if (!exportForm.toDate && exportToDateInputRef.value) {
      exportToDateInputRef.value.showPicker?.()
      exportToDateInputRef.value.focus()
    }
  })
})

function onFromChange() { /* watch 负责联动 */ }
function onToChange() {
  if (exportForm.toDate && exportForm.fromDate && exportForm.toDate < exportForm.fromDate) {
    exportForm.toDate = exportForm.fromDate
    toast.warning('结束日期不能早于开始日期，已自动调整。')
  }
}

const importing = ref(false)
const importConfirmOpen = ref(false)
const importError = ref('')
const importResult = ref<{
  ok: boolean
  created: number
  skipped: number
  failed: number
  message: string
  errors: string[]
} | null>(null)
const dragging = ref(false)
const fileInputRef = ref<HTMLInputElement | null>(null)

const importForm = reactive({
  format: 'json' as 'json' | 'markdown',
  file: null as File | null,
  opts: {
    overwrite: false
  }
})

const formatLabel = computed(() =>
  importForm.format === 'markdown' ? '/admin/import/markdown（单篇 .md）' : '/admin/import/posts（ZIP 数据包）'
)

const acceptForFormat = computed(() =>
  importForm.format === 'markdown' ? '.md,text/markdown' : '.zip,application/zip'
)

function formatSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  if (bytes < 1024 * 1024 * 1024) return `${(bytes / (1024 * 1024)).toFixed(2)} MB`
  return `${(bytes / (1024 * 1024 * 1024)).toFixed(2)} GB`
}

function handleFileSelect(e: Event) {
  const t = e.currentTarget as HTMLInputElement
  const f = t.files?.[0]
  if (f) acceptImportFile(f)
}

function handleDrop(e: DragEvent) {
  dragging.value = false
  const f = e.dataTransfer?.files?.[0]
  if (f) acceptImportFile(f)
}

/** 前端先按后端契约校验扩展名，避免必然 400 的上传 */
function acceptImportFile(f: File) {
  const okExt = importForm.format === 'markdown' ? /\.md$/i : /\.zip$/i
  if (!okExt.test(f.name)) {
    const want = importForm.format === 'markdown' ? '.md' : '.zip'
    toast.error(`当前导入通道只接受 ${want} 文件，已忽略「${f.name}」`)
    if (fileInputRef.value) fileInputRef.value.value = ''
    return
  }
  importResult.value = null
  importError.value = ''
  importForm.file = f
}

function clearFile() {
  importForm.file = null
  if (fileInputRef.value) fileInputRef.value.value = ''
}

async function handleExport() {
  exporting.value = true
  exportError.value = ''
  downloadReady.value = null
  try {
    const isMd = exportForm.format === 'markdown'
    const query: Record<string, string | boolean> = {}
    if (exportForm.fromDate) query.from = exportForm.fromDate
    if (exportForm.toDate) query.to = exportForm.toDate
    if (isMd) {
      query.lang = 'zh'
    } else {
      query.scope = exportForm.scope
      query.include_drafts = exportForm.scope === 'all'
    }
    const path = isMd ? '/admin/export/markdown' : '/admin/export/posts'
    const blob = await apiFetch<Blob>(path, {
      method: 'GET',
      responseType: 'blob',
      query,
      silentToast: true
    })
    if (!blob || blob.size === 0) {
      throw new Error('导出内容为空，请放宽筛选条件后重试')
    }
    const now = new Date()
    const pad = (n: number) => String(n).padStart(2, '0')
    const stamp = `${now.getFullYear()}${pad(now.getMonth() + 1)}${pad(now.getDate())}-${pad(now.getHours())}${pad(now.getMinutes())}`
    downloadReady.value = {
      // 两个导出通道都返回 ZIP，扩展名统一为 zip，避免误导下游平台
      fileName: `rosetta-export-${exportForm.format}-${stamp}.zip`,
      size: formatSize(blob.size),
      time: `${now.getFullYear()}-${pad(now.getMonth() + 1)}-${pad(now.getDate())} ${pad(now.getHours())}:${pad(now.getMinutes())}`,
      blob
    }
    toast.success('导出文件已生成')
  } catch (e) {
    const err = e as { data?: unknown, message?: string }
    exportError.value = extractApiErrorMessage(err?.data, err?.message || '导出失败')
  } finally {
    exporting.value = false
  }
}

function doDownload() {
  if (!downloadReady.value) return
  const url = URL.createObjectURL(downloadReady.value.blob)
  const a = document.createElement('a')
  a.href = url
  a.download = downloadReady.value.fileName
  document.body.appendChild(a)
  a.click()
  document.body.removeChild(a)
  setTimeout(() => URL.revokeObjectURL(url), 5000)
}

/**
 * 由 DangerConfirmDialog 的 onConfirm 调用：
 *   - 网络/HTTP 错误：apiFetch(silentToast) 抛出 → 弹窗内联展示，弹窗保持打开可重试
 *   - HTTP 200 + success:false（后端业务失败）：同样抛出，绝不提示"导入完成"
 */
async function runImport() {
  if (!importForm.file) {
    throw new Error('请先选择导入文件')
  }
  importing.value = true
  importError.value = ''
  importResult.value = null
  try {
    const isMd = importForm.format === 'markdown'
    const fd = new FormData()
    fd.append('file', importForm.file)
    const r = await apiFetch<ImportResultResponse>(
      isMd ? '/admin/import/markdown' : '/admin/import/posts',
      {
        method: 'POST',
        body: fd,
        // 仅 /import/posts 支持 skip_existing；markdown 通道后端不接收该参数
        query: isMd ? undefined : { skip_existing: !importForm.opts.overwrite },
        silentToast: true
      }
    )
    const created = Number(r?.created_count ?? 0) || 0
    const skipped = Number(r?.skipped_count ?? 0) || 0
    const failed = Number(r?.error_count ?? 0) || 0
    const ok = r?.success !== false
    importResult.value = {
      ok,
      created,
      skipped,
      failed,
      message: r?.message || (ok ? '导入完成' : '导入失败'),
      errors: Array.isArray(r?.errors) ? r.errors.filter(e => typeof e === 'string' && e) as string[] : []
    }
    if (!ok || (created === 0 && skipped === 0 && failed === 0)) {
      throw new Error(importResult.value.message || '导入未创建任何内容')
    }
    if (ok) {
      toast.success(importResult.value.message)
      clearFile()
    }
  } catch (e) {
    const err = e as { data?: unknown, message?: string }
    const msg = extractApiErrorMessage(err?.data, err?.message || '导入失败')
    importError.value = msg
    throw new Error(msg, { cause: e })
  } finally {
    importing.value = false
  }
}
</script>
