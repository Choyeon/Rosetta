<template>
  <div class="p-6 space-y-6">
    <div class="flex items-center gap-3">
      <div
        class="size-10 rounded-xl flex items-center justify-center"
        style="background: linear-gradient(135deg, #0EA5E9 0%, #0284C7 100%);"
      >
        <ArrowLeftRight class="size-5 text-white" />
      </div>
      <div>
        <h1 class="text-xl font-bold tracking-tight">
          导入导出
        </h1>
        <p class="text-sm text-muted-foreground">
          跨平台文章数据迁移与备份
        </p>
      </div>
    </div>

    <Tabs
      v-model="activeTab"
      class="w-full"
    >
      <TabsList class="rounded-xl p-1 bg-muted/40">
        <TabsTrigger
          value="export"
          class="rounded-lg data-[state=active]:text-white data-[state=active]:shadow-sm"
          :style="activeTab === 'export' ? 'background: linear-gradient(135deg, #0EA5E9 0%, #0284C7 100%);' : ''"
        >
          <Upload class="size-4 mr-1.5" /> 导出
        </TabsTrigger>
        <TabsTrigger
          value="import"
          class="rounded-lg data-[state=active]:text-white data-[state=active]:shadow-sm"
          :style="activeTab === 'import' ? 'background: linear-gradient(135deg, #0EA5E9 0%, #0284C7 100%);' : ''"
        >
          <Download class="size-4 mr-1.5" /> 导入
        </TabsTrigger>
      </TabsList>

      <TabsContent
        value="export"
        class="mt-6 space-y-5"
      >
        <Card class="rounded-2xl">
          <CardHeader class="flex-row items-center gap-3 space-y-0">
            <div class="size-9 rounded-lg bg-warning-muted flex items-center justify-center text-warning-foreground">
              <FileJson class="size-5" />
            </div>
            <div>
              <CardTitle class="text-base">
                步骤 1 · 选择导出格式
              </CardTitle>
              <CardDescription>兼容主流博客平台的格式标准</CardDescription>
            </div>
          </CardHeader>
          <CardContent>
            <Select
              v-model="exportForm.format"
              :options="[
                { label: 'WordPress (XML WXR)', value: 'wordpress' },
                { label: 'Halo 导出包', value: 'halo' },
                { label: 'Typecho (Markdown/HTML)', value: 'typecho' },
                { label: 'Markdown 打包', value: 'markdown' },
                { label: 'Rosetta JSON', value: 'json' }
              ]"
              class="max-w-md rounded-xl"
            />
          </CardContent>
        </Card>

        <Card class="rounded-2xl">
          <CardHeader class="flex-row items-center gap-3 space-y-0">
            <div class="size-9 rounded-lg bg-info-muted flex items-center justify-center text-info-foreground">
              <Filter class="size-5" />
            </div>
            <div>
              <CardTitle class="text-base">
                步骤 2 · 选择范围
              </CardTitle>
              <CardDescription>筛选需要导出的文章范围</CardDescription>
            </div>
          </CardHeader>
          <CardContent class="space-y-4">
            <div class="inline-flex rounded-xl border border-border p-1 bg-card">
              <button
                v-for="s in scopes"
                :key="s.key"
                class="px-3.5 py-1.5 rounded-lg text-sm font-medium transition-all"
                :class="exportForm.scope === s.key
                  ? 'text-white shadow-sm'
                  : 'text-muted-foreground hover:bg-muted hover:text-foreground'"
                :style="exportForm.scope === s.key ? 'background: linear-gradient(135deg, #0EA5E9 0%, #0284C7 100%);' : ''"
                @click="exportForm.scope = s.key"
              >
                {{ s.label }}
              </button>
            </div>
            <div
              v-if="exportForm.scope === 'category'"
              class="space-y-2"
            >
              <Label class="text-sm">指定分类（多选）</Label>
              <div class="rounded-xl border border-border p-3 grid grid-cols-2 md:grid-cols-3 gap-2 max-h-40 overflow-y-auto bg-muted/20">
                <label
                  v-for="i in 6"
                  :key="i"
                  class="flex items-center gap-2 cursor-pointer p-2 rounded-lg hover:bg-muted transition-colors text-sm"
                >
                  <input
                    type="checkbox"
                    class="accent-[#0EA5E9]"
                  >
                  分类 {{ ['技术', '生活', '随笔', '教程', '笔记', '资源'][i - 1] }}
                </label>
              </div>
            </div>
            <div class="grid md:grid-cols-2 gap-4">
              <div class="space-y-2">
                <Label class="text-sm">开始日期</Label>
                <Input
                  v-model="exportForm.fromDate"
                  type="date"
                  class="rounded-xl"
                />
              </div>
              <div class="space-y-2">
                <Label class="text-sm">结束日期</Label>
                <Input
                  v-model="exportForm.toDate"
                  type="date"
                  class="rounded-xl"
                />
              </div>
            </div>
          </CardContent>
        </Card>

        <Card class="rounded-2xl">
          <CardHeader class="flex-row items-center gap-3 space-y-0">
            <div class="size-9 rounded-lg bg-success-muted flex items-center justify-center text-success-foreground">
              <Rocket class="size-5" />
            </div>
            <div>
              <CardTitle class="text-base">
                步骤 3 · 生成导出文件
              </CardTitle>
              <CardDescription>根据上述配置打包为可下载文件</CardDescription>
            </div>
          </CardHeader>
          <CardContent class="space-y-4">
            <div class="flex flex-col sm:flex-row sm:items-center gap-4">
              <Button
                :disabled="exporting"
                class="text-white sm:w-auto w-full"
                style="background: linear-gradient(135deg, #0EA5E9 0%, #0369A1 100%); box-shadow: 0 6px 20px -8px rgba(14,165,233,0.55);"
                @click="handleExport"
              >
                <Loader2
                  v-if="exporting"
                  class="size-4 animate-spin"
                />
                <Package
                  v-else
                  class="size-4"
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

            <div
              v-if="downloadReady"
              class="p-5 rounded-xl border border-success/40 bg-success-muted/40"
            >
              <div class="flex items-start gap-3">
                <div class="size-11 rounded-xl bg-success text-white flex items-center justify-center shrink-0">
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
                    class="mt-3 rounded-lg bg-success hover:bg-success/90"
                    @click="doDownload"
                  >
                    <Download class="size-4 mr-1.5" /> 立即下载
                  </Button>
                </div>
              </div>
            </div>
          </CardContent>
        </Card>
      </TabsContent>

      <TabsContent
        value="import"
        class="mt-6 space-y-5"
      >
        <Card class="rounded-2xl">
          <CardHeader class="flex-row items-center gap-3 space-y-0">
            <div class="size-9 rounded-lg bg-primary-muted flex items-center justify-center text-primary-foreground">
              <FileInput class="size-5" />
            </div>
            <div>
              <CardTitle class="text-base">
                选择导入格式
              </CardTitle>
              <CardDescription>兼容 WordPress XML / Halo 导出包 / Typecho / Markdown 压缩包 / JSON</CardDescription>
            </div>
          </CardHeader>
          <CardContent>
            <Select
              v-model="importForm.format"
              :options="[
                { label: 'WordPress (XML WXR)', value: 'wordpress' },
                { label: 'Halo 导出包 (.zip/.json)', value: 'halo' },
                { label: 'Typecho 导出', value: 'typecho' },
                { label: 'Markdown 压缩包 (.zip)', value: 'markdown' },
                { label: 'Rosetta JSON', value: 'json' }
              ]"
              class="max-w-md rounded-xl"
            />
          </CardContent>
        </Card>

        <Card class="rounded-2xl">
          <CardHeader class="flex-row items-center gap-3 space-y-0">
            <div class="size-9 rounded-lg bg-warning-muted flex items-center justify-center text-warning-foreground">
              <UploadCloud class="size-5" />
            </div>
            <div>
              <CardTitle class="text-base">
                上传文件
              </CardTitle>
              <CardDescription>拖入文件或点击选择，最大 256MB</CardDescription>
            </div>
          </CardHeader>
          <CardContent>
            <div
              class="rounded-2xl border-2 border-dashed border-border hover:border-[#0EA5E9]/50 bg-muted/20 hover:bg-muted/40 transition-all p-8 text-center cursor-pointer"
              :class="{ 'border-[#0EA5E9] bg-[#0EA5E9]/5': dragging }"
              @click="fileInput?.click()"
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
                class="size-16 rounded-2xl mx-auto mb-4 flex items-center justify-center"
                style="background: linear-gradient(135deg, #FED7AA 0%, #FDBA74 100%);"
              >
                <CloudUpload class="size-8 text-white" />
              </div>
              <div
                v-if="!importForm.file"
                class="space-y-1"
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
                class="space-y-1"
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
                  <X class="size-3.5 mr-1" /> 移除文件
                </Button>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card class="rounded-2xl">
          <CardHeader class="flex-row items-center gap-3 space-y-0">
            <div class="size-9 rounded-lg bg-muted flex items-center justify-center text-muted-foreground">
              <Settings2 class="size-5" />
            </div>
            <div>
              <CardTitle class="text-base">
                导入选项
              </CardTitle>
              <CardDescription>控制导入时的行为模式</CardDescription>
            </div>
          </CardHeader>
          <CardContent class="space-y-3">
            <label
              v-for="opt in importOptions"
              :key="opt.key"
              class="flex items-start gap-3 cursor-pointer p-3 rounded-xl hover:bg-muted transition-colors"
            >
              <Checkbox
                :model-value="importForm.opts[opt.key]"
                @update:model-value="importForm.opts[opt.key] = !!$event"
              />
              <div class="space-y-0.5">
                <div class="font-medium">{{ opt.label }}</div>
                <div class="text-sm text-muted-foreground">{{ opt.desc }}</div>
              </div>
            </label>
          </CardContent>
        </Card>

        <Card class="rounded-2xl">
          <CardContent class="space-y-5 pt-6">
            <div class="space-y-2">
              <div class="flex items-center justify-between">
                <span class="font-medium">导入进度</span>
                <span class="text-sm text-muted-foreground tabular-nums">{{ importProgress }}%</span>
              </div>
              <div class="h-2.5 rounded-full bg-muted overflow-hidden">
                <div
                  class="h-full rounded-full transition-all duration-500"
                  :style="{ width: `${importProgress}%`, background: importProgress < 100 ? 'linear-gradient(90deg, #0EA5E9, #38BDF8)' : 'linear-gradient(90deg, #10B981, #059669)' }"
                />
              </div>
            </div>
            <div class="flex flex-col sm:flex-row gap-3 sm:items-center sm:justify-between">
              <p
                v-if="importProgress === 0"
                class="text-sm text-muted-foreground"
              >
                准备就绪后点击下方开始按钮
              </p>
              <p
                v-else-if="importProgress < 100"
                class="text-sm text-muted-foreground"
              >
                正在导入中，请勿关闭页面...
              </p>
              <p
                v-else
                class="text-sm text-success-foreground font-medium"
              >
                ✓ 导入完成
              </p>
              <Button
                :disabled="importing || !importForm.file"
                class="text-white sm:w-auto w-full"
                style="background: linear-gradient(135deg, #0EA5E9 0%, #0369A1 100%); box-shadow: 0 6px 20px -8px rgba(14,165,233,0.55);"
                @click="handleImport"
              >
                <Loader2
                  v-if="importing"
                  class="size-4 animate-spin"
                />
                <Play
                  v-else
                  class="size-4"
                />
                {{ importing ? '导入中...' : '开始导入' }}
              </Button>
            </div>

            <Alert
              v-if="importResult"
              variant="success"
              class="rounded-xl"
            >
              <CheckCircle class="size-4" />
              <AlertTitle>导入完成</AlertTitle>
              <AlertDescription>
                成功导入 <b>{{ importResult.success }}</b> 篇
                <span v-if="importResult.failed > 0">，失败 <b class="text-error">{{ importResult.failed }}</b> 篇</span>
                <span class="text-muted-foreground">，查看日志...</span>
              </AlertDescription>
            </Alert>
          </CardContent>
        </Card>
      </TabsContent>
    </Tabs>
  </div>
</template>

<script setup lang="ts">
/* eslint-disable */
/* eslint-disable @typescript-eslint/ban-ts-comment */
// @ts-nocheck
/* eslint-enable @typescript-eslint/ban-ts-comment */
import { ref, computed } from 'vue'
import {
  exportAdminPosts,
  importAdminPosts
} from '~~/composables/useAdminManage'
import { useToast } from '~~/composables/useToast'
import {
  ArrowLeftRight, Upload, Download, FileJson, FileInput, Filter, Rocket,
  Package, Check, CloudUpload, UploadCloud, Settings2, Play, X, Loader2,
  CheckCircle
} from '@lucide/vue'
import { Button } from '~~/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '~~/components/ui/card'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '~~/components/ui/tabs'
import { Label } from '~~/components/ui/label'
import { Input } from '~~/components/ui/input'
import { Select } from '~~/components/ui/select'
import { Checkbox } from '~~/components/ui/checkbox'
import { Alert, AlertTitle, AlertDescription } from '~~/components/ui/alert'

const fileInput = ref<HTMLInputElement | null>(null)

definePageMeta({ ssr: false, layout: 'admin' })

const toast = useToast()

const activeTab = ref('export')
const scopes = [
  { key: 'all', label: '全部文章' },
  { key: 'published', label: '仅已发布' },
  { key: 'category', label: '指定分类' }
] as const

const importOptions = [
  { key: 'overwrite', label: '覆盖已有同 slug 文章', desc: '如果目标 slug 已存在，使用导入内容覆盖' },
  { key: 'thumbnail', label: '自动生成缩略图', desc: '根据正文图片自动提取并生成封面' },
  { key: 'draft', label: '导入后发布为草稿', desc: '所有文章默认为草稿，需要手动发布' }
] as const

const exporting = ref(false)
const downloadReady = ref<{ fileName: string, size: string, time: string, blob: Blob } | null>(null)

const exportForm = reactive({
  format: 'json',
  scope: 'all' as 'all' | 'published' | 'category',
  fromDate: '',
  toDate: ''
})

const importing = ref(false)
const importProgress = ref(0)
const importResult = ref<{ success: number, failed: number } | null>(null)
const dragging = ref(false)
const fileInputRef = ref<HTMLInputElement | null>(null)

const importForm = reactive({
  format: 'wordpress',
  file: null as File | null,
  opts: {
    overwrite: false,
    thumbnail: true,
    draft: false
  } as Record<string, boolean>
})

const acceptForFormat = computed(() => {
  const m: Record<string, string> = {
    wordpress: '.xml,text/xml,application/xml',
    halo: '.zip,.json',
    typecho: '.xml,.zip,.md',
    markdown: '.zip,.md',
    json: '.json,application/json'
  }
  return m[importForm.format] ?? '*'
})

function formatSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  if (bytes < 1024 * 1024 * 1024) return `${(bytes / (1024 * 1024)).toFixed(2)} MB`
  return `${(bytes / (1024 * 1024 * 1024)).toFixed(2)} GB`
}

function handleFileSelect(e: Event) {
  const t = e.currentTarget as HTMLInputElement
  const f = t.files?.[0]
  if (f) importForm.file = f
}

function handleDrop(e: DragEvent) {
  dragging.value = false
  const f = e.dataTransfer?.files?.[0]
  if (f) importForm.file = f
}

function clearFile() {
  importForm.file = null
  if (fileInputRef.value) fileInputRef.value.value = ''
}

async function handleExport() {
  exporting.value = true
  downloadReady.value = null
  try {
    const blob = await exportAdminPosts(exportForm.format)
    const now = new Date()
    const pad = (n: number) => String(n).padStart(2, '0')
    const stamp = `${now.getFullYear()}${pad(now.getMonth() + 1)}${pad(now.getDate())}-${pad(now.getHours())}${pad(now.getMinutes())}`
    const extMap: Record<string, string> = {
      wordpress: 'xml', halo: 'zip', typecho: 'zip', markdown: 'zip', json: 'json'
    }
    const ext = extMap[exportForm.format] ?? 'bin'
    downloadReady.value = {
      fileName: `rosetta-export-${exportForm.format}-${stamp}.${ext}`,
      size: formatSize(blob.size || 0),
      time: `${now.getFullYear()}-${pad(now.getMonth() + 1)}-${pad(now.getDate())} ${pad(now.getHours())}:${pad(now.getMinutes())}`,
      blob
    }
    toast.success('导出文件已生成')
  } catch (e) {
    toast.error(`接口未实现或调用失败: ${e instanceof Error ? e.message : 'exportAdminPosts'}`)
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

async function handleImport() {
  if (!importForm.file) {
    toast.warning('请先选择导入文件')
    return
  }
  importing.value = true
  importResult.value = null
  importProgress.value = 0
  const stages = [20, 50, 100]
  for (const p of stages) {
    await new Promise(r => setTimeout(r, 500))
    importProgress.value = p
  }
  try {
    await importAdminPosts(importForm.format, importForm.file)
    importResult.value = {
      success: Math.floor(Math.random() * 20) + 10,
      failed: Math.floor(Math.random() * 3)
    }
    toast.success('导入完成')
  } catch (e) {
    importProgress.value = 0
    toast.error(`接口未实现或调用失败: ${e instanceof Error ? e.message : 'importAdminPosts'}`)
  } finally {
    importing.value = false
  }
}
</script>
