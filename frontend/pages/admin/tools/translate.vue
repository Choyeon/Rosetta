<template>
  <div class="p-6 space-y-6">
    <div class="flex items-center justify-between">
      <div class="flex items-center gap-3">
        <div
          class="size-10 rounded-xl flex items-center justify-center"
          style="background: linear-gradient(135deg, #0EA5E9 0%, #0284C7 100%);"
        >
          <Languages class="size-5 text-white" />
        </div>
        <div>
          <h1 class="text-xl font-bold tracking-tight">
            翻译工具
          </h1>
          <p class="text-sm text-muted-foreground">
            批量或单篇把文章翻译为其他语言版本
          </p>
        </div>
      </div>
      <Button
        variant="outline"
        class="rounded-xl"
        :disabled="!latestJob"
        @click="refreshJob"
      >
        <RefreshCw
          class="size-4 mr-1.5"
          :class="{ 'animate-spin': refreshingJob }"
        />
        刷新任务状态
      </Button>
    </div>

    <div class="grid grid-cols-1 lg:grid-cols-3 gap-5">
      <Card class="rounded-2xl">
        <CardHeader>
          <div class="inline-flex items-center justify-center size-8 rounded-lg bg-warning-muted text-warning-foreground mb-1">
            <span class="text-sm font-bold">1</span>
          </div>
          <CardTitle class="text-base">
            语言设置
          </CardTitle>
          <CardDescription>选择源语言和目标翻译语言</CardDescription>
        </CardHeader>
        <CardContent class="space-y-4">
          <div class="space-y-2">
            <Label class="text-sm font-medium">源语言</Label>
            <Select
              v-model="form.sourceLang"
              :options="langOptions"
              class="rounded-xl"
            />
          </div>
          <div class="space-y-2">
            <Label class="text-sm font-medium">目标语言（可多选）</Label>
            <div class="rounded-xl border border-border p-3 space-y-2 bg-muted/20">
              <label
                v-for="lang in langOptions"
                :key="lang.value"
                class="flex items-center gap-2 cursor-pointer p-2 rounded-lg hover:bg-muted transition-colors"
                :class="{ 'opacity-40 pointer-events-none': form.sourceLang === lang.value }"
              >
                <Checkbox
                  :model-value="form.targetLangs.includes(lang.value)"
                  :disabled="form.sourceLang === lang.value"
                  @update:model-value="toggleTarget(lang.value, $event)"
                />
                <span class="text-sm">{{ lang.label }}</span>
              </label>
            </div>
            <p class="text-xs text-muted-foreground">
              已选 {{ form.targetLangs.length }} 个目标语言
            </p>
          </div>
        </CardContent>
      </Card>

      <Card class="rounded-2xl">
        <CardHeader>
          <div class="inline-flex items-center justify-center size-8 rounded-lg bg-info-muted text-info-foreground mb-1">
            <span class="text-sm font-bold">2</span>
          </div>
          <CardTitle class="text-base">
            选择文章
          </CardTitle>
          <CardDescription>通过列表勾选或直接输入 post_id</CardDescription>
        </CardHeader>
        <CardContent class="space-y-4">
          <div class="space-y-2">
            <Label class="text-sm font-medium">单篇快速翻译</Label>
            <div class="flex gap-2">
              <Input
                v-model.number="quickPostId"
                type="number"
                placeholder="输入文章 ID"
                class="rounded-xl"
              />
              <Button
                variant="outline"
                class="rounded-xl shrink-0"
                :disabled="translatingQuick || !quickPostId || form.targetLangs.length === 0"
                @click="handleQuickTranslate"
              >
                <Loader2
                  v-if="translatingQuick"
                  class="size-4 animate-spin"
                />
                <Zap
                  v-else
                  class="size-4"
                />
                立即翻译
              </Button>
            </div>
          </div>
          <Separator />
          <div class="space-y-2">
            <Label class="text-sm font-medium">搜索文章（批量多选）</Label>
            <div class="relative">
              <Search class="size-4 absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground" />
              <Input
                v-model="postSearch"
                placeholder="按标题搜索..."
                class="rounded-xl pl-9"
              />
            </div>
          </div>
          <div class="rounded-xl border border-border overflow-hidden bg-muted/10 max-h-56 overflow-y-auto">
            <div
              v-if="fakePosts.length === 0"
              class="p-5 text-center text-sm text-muted-foreground"
            >
              {{ postSearch ? '未找到匹配的文章' : '暂无数据，可直接用上方 post_id 输入' }}
            </div>
            <label
              v-for="p in fakePosts"
              :key="p.id"
              class="flex items-start gap-2 p-3 hover:bg-muted transition-colors cursor-pointer border-b last:border-b-0 border-border/50"
            >
              <Checkbox
                :model-value="form.postIds.includes(p.id)"
                @update:model-value="togglePost(p.id, $event)"
              />
              <div class="flex-1 min-w-0">
                <div class="font-medium truncate text-sm">{{ p.title }}</div>
                <div class="text-xs text-muted-foreground font-mono">#{{ p.id }}</div>
              </div>
            </label>
          </div>
          <div class="flex items-center justify-between text-xs text-muted-foreground">
            <span>已选 {{ form.postIds.length }} 篇文章</span>
            <button
              v-if="form.postIds.length > 0"
              class="text-[#0EA5E9] hover:underline"
              @click="form.postIds = []"
            >
              清空
            </button>
          </div>
        </CardContent>
      </Card>

      <Card class="rounded-2xl">
        <CardHeader>
          <div class="inline-flex items-center justify-center size-8 rounded-lg bg-success-muted text-success-foreground mb-1">
            <span class="text-sm font-bold">3</span>
          </div>
          <CardTitle class="text-base">
            开始翻译
          </CardTitle>
          <CardDescription>确认配置后批量提交翻译任务</CardDescription>
        </CardHeader>
        <CardContent class="space-y-4 h-full flex flex-col">
          <div class="rounded-xl p-4 space-y-2 bg-muted/30 flex-1">
            <div class="flex items-center justify-between text-sm">
              <span class="text-muted-foreground">源语言</span>
              <span class="font-medium">{{ labelOf(form.sourceLang) }}</span>
            </div>
            <div class="flex items-center justify-between text-sm">
              <span class="text-muted-foreground">目标语言</span>
              <span class="font-medium">
                {{ form.targetLangs.length ? form.targetLangs.map(labelOf).join(' / ') : '未选' }}
              </span>
            </div>
            <div class="flex items-center justify-between text-sm">
              <span class="text-muted-foreground">文章数量</span>
              <span class="font-medium tabular-nums">{{ form.postIds.length }} 篇</span>
            </div>
            <div class="flex items-center justify-between text-sm">
              <span class="text-muted-foreground">预计任务数</span>
              <span class="font-medium tabular-nums text-[#0EA5E9]">{{ form.postIds.length * form.targetLangs.length }} 次</span>
            </div>
          </div>
          <Button
            :disabled="batchSubmitting || form.postIds.length === 0 || form.targetLangs.length === 0"
            class="text-white w-full"
            style="background: linear-gradient(135deg, #0EA5E9 0%, #0369A1 100%); box-shadow: 0 6px 20px -8px rgba(14,165,233,0.55);"
            @click="handleBatchTranslate"
          >
            <Loader2
              v-if="batchSubmitting"
              class="size-4 animate-spin"
            />
            <Send
              v-else
              class="size-4"
            />
            {{ batchSubmitting ? '正在提交任务...' : '开始翻译' }}
          </Button>
          <p
            v-if="form.postIds.length === 0 || form.targetLangs.length === 0"
            class="text-xs text-muted-foreground text-center"
          >
            请先选择目标语言和至少一篇文章
          </p>
        </CardContent>
      </Card>
    </div>

    <Card class="rounded-2xl">
      <CardHeader class="flex-row items-center justify-between space-y-0">
        <div class="flex items-center gap-3">
          <div class="size-9 rounded-lg bg-muted flex items-center justify-center text-muted-foreground">
            <ListTodo class="size-5" />
          </div>
          <div>
            <CardTitle class="text-base">
              最近翻译任务
            </CardTitle>
            <CardDescription>最近一次的批量或单篇翻译进度，可点击手动刷新</CardDescription>
          </div>
        </div>
      </CardHeader>
      <CardContent>
        <div
          v-if="!latestJob"
          class="py-10"
        >
          <Alert
            variant="info"
            class="rounded-xl max-w-xl mx-auto"
          >
            <Info class="size-4" />
            <AlertTitle>暂无进行中的任务</AlertTitle>
            <AlertDescription>提交翻译任务后，这里会显示实时进度。</AlertDescription>
          </Alert>
        </div>

        <div
          v-else
          class="rounded-2xl border border-border p-5 bg-muted/20"
        >
          <div class="flex flex-wrap items-start justify-between gap-3">
            <div class="space-y-1">
              <div class="flex items-center gap-2 flex-wrap">
                <span class="font-semibold">任务 #{{ latestJob.id.slice(0, 8) }}...</span>
                <Badge
                  :variant="jobBadgeVariant(latestJob.status)"
                  :class="jobBadgeClass(latestJob.status)"
                  class="rounded-full text-[11px]"
                >
                  {{ jobStatusLabel(latestJob.status) }}
                </Badge>
              </div>
              <div class="text-xs text-muted-foreground tabular-nums">
                {{ labelOf(latestJob.source_lang) }} → {{ labelOf(latestJob.target_lang) }} · 创建于 {{ formatAdminDateTime(latestJob.created_at) }}
              </div>
            </div>
            <div class="text-right text-xs text-muted-foreground tabular-nums space-y-0.5">
              <div>进度：{{ latestJob.items_done }} / {{ latestJob.items_total }}</div>
              <div>{{ latestJob.progress.toFixed(0) }}%</div>
            </div>
          </div>
          <div class="mt-4">
            <div class="h-3 rounded-full bg-muted overflow-hidden">
              <div
                class="h-full rounded-full transition-all duration-700 relative overflow-hidden"
                :class="[
                  latestJob.status === 'failed' ? 'bg-error' : '',
                  latestJob.status === 'done' ? '!bg-gradient-to-r !from-[#10B981] !to-[#059669]' : '',
                  (latestJob.status === 'running' || latestJob.status === 'queued') ? '!bg-gradient-to-r !from-[#0EA5E9] !to-[#38BDF8]' : ''
                ]"
              >
                <div
                  v-if="latestJob.status === 'running'"
                  class="absolute inset-0 animate-progress-stripe opacity-40"
                  style="background-image: linear-gradient(45deg, rgba(255,255,255,0.25) 25%, transparent 25%, transparent 50%, rgba(255,255,255,0.25) 50%, rgba(255,255,255,0.25) 75%, transparent 75%, transparent); background-size: 20px 20px;"
                />
              </div>
            </div>
            <div
              :style="{ width: `${latestJob.progress}%` }"
            />
          </div>
        </div>
      </CardContent>
    </Card>
  </div>
</template>

<script setup lang="ts">
/* eslint-disable */
/* eslint-disable @typescript-eslint/ban-ts-comment */
// @ts-nocheck
/* eslint-enable @typescript-eslint/ban-ts-comment */
import { ref, reactive, computed, onMounted, onUnmounted } from 'vue'
import {
  translateAdminPost,
  batchTranslateAdminPosts,
  fetchAdminTranslateJob,
  formatAdminDateTime,
  type AdminTranslateJob
} from '~~/composables/useAdminManage'
import { useToast } from '~~/composables/useToast'
import {
  Languages, RefreshCw, Search, Zap, Send, ListTodo, Loader2, Info
} from '@lucide/vue'
import { Button } from '~~/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '~~/components/ui/card'
import { Label } from '~~/components/ui/label'
import { Input } from '~~/components/ui/input'
import { Select } from '~~/components/ui/select'
import { Checkbox } from '~~/components/ui/checkbox'
import { Separator } from '~~/components/ui/separator'
import { Badge } from '~~/components/ui/badge'
import { Alert, AlertTitle, AlertDescription } from '~~/components/ui/alert'
import type { BadgeVariants } from '~~/components/ui/badge'

definePageMeta({ ssr: false, layout: 'admin' })

const toast = useToast()

const langOptions = [
  { label: '简体中文 (zh)', value: 'zh' },
  { label: 'English (en)', value: 'en' },
  { label: '日本語 (ja)', value: 'ja' },
  { label: '繁體中文 (zh_Hant)', value: 'zh_Hant' }
]

function labelOf(code: string): string {
  return langOptions.find(l => l.value === code)?.label ?? code
}

function jobStatusLabel(s: string): string {
  return { queued: '排队中', running: '执行中', done: '已完成', failed: '失败' }[s] ?? s
}
function jobBadgeVariant(s: string): BadgeVariants['variant'] {
  if (s === 'done') return 'default'
  if (s === 'failed') return 'destructive'
  if (s === 'running') return 'secondary'
  return 'outline'
}
function jobBadgeClass(s: string): string {
  if (s === 'done') return 'bg-success-muted text-success-foreground border-transparent'
  if (s === 'running') return 'bg-warning-muted text-warning-foreground border-transparent'
  return ''
}

const form = reactive({
  sourceLang: 'zh',
  targetLangs: [] as string[],
  postIds: [] as number[]
})
const quickPostId = ref<number | null>(null)
const postSearch = ref('')
const translatingQuick = ref(false)
const batchSubmitting = ref(false)
const refreshingJob = ref(false)
const latestJob = ref<AdminTranslateJob | null>(null)

const fakePosts = computed(() => {
  const all = [
    { id: 101, title: 'Rosetta 博客系统入门指南' },
    { id: 102, title: '基于 FastAPI 的高性能后端实践' },
    { id: 103, title: 'Vue 3 + Nuxt 4 前端工程化记录' },
    { id: 104, title: '从零搭建 SEO 友好的博客架构' },
    { id: 105, title: 'Markdown 编辑器选型与集成笔记' }
  ]
  const kw = postSearch.value.trim().toLowerCase()
  if (!kw) return all
  return all.filter(p => p.title.toLowerCase().includes(kw) || String(p.id).includes(kw))
})

function toggleTarget(code: string, checked: boolean | 'indeterminate') {
  const on = checked === true || checked === 'indeterminate'
  if (on) {
    if (!form.targetLangs.includes(code)) form.targetLangs.push(code)
  } else {
    form.targetLangs = form.targetLangs.filter(x => x !== code)
  }
}

function togglePost(id: number, checked: boolean | 'indeterminate') {
  const on = checked === true || checked === 'indeterminate'
  if (on) {
    if (!form.postIds.includes(id)) form.postIds.push(id)
  } else {
    form.postIds = form.postIds.filter(x => x !== id)
  }
}

async function handleQuickTranslate() {
  if (!quickPostId.value || form.targetLangs.length === 0) {
    toast.warning('请填写 post_id 并至少选择一个目标语言')
    return
  }
  translatingQuick.value = true
  try {
    const targets = [...form.targetLangs]
    for (const t of targets) {
      await translateAdminPost(quickPostId.value, t)
    }
    toast.success(`已提交 #${quickPostId.value} 到 ${targets.length} 种语言的翻译任务`)
    quickPostId.value = null
  } catch (e) {
    toast.error(`接口未实现或调用失败: ${e instanceof Error ? e.message : 'translateAdminPost'}`)
  } finally {
    translatingQuick.value = false
  }
}

async function handleBatchTranslate() {
  if (form.postIds.length === 0 || form.targetLangs.length === 0) {
    toast.warning('请选择文章和目标语言')
    return
  }
  batchSubmitting.value = true
  try {
    const target = form.targetLangs[0]
    const job = await batchTranslateAdminPosts(form.postIds, target)
    latestJob.value = job
    toast.success(`已创建批量翻译任务：${job.id.slice(0, 8)}...`)
    startPolling(job.id)
  } catch (e) {
    toast.error(`接口未实现或调用失败: ${e instanceof Error ? e.message : 'batchTranslateAdminPosts'}`)
  } finally {
    batchSubmitting.value = false
  }
}

let pollTimer: number | null = null

function startPolling(jobId: string) {
  stopPolling()
  pollTimer = window.setInterval(async () => {
    try {
      const job = await fetchAdminTranslateJob(jobId)
      latestJob.value = job
      if (job.status === 'done' || job.status === 'failed') stopPolling()
    } catch { /* ignore */ }
  }, 10000)
}

function stopPolling() {
  if (pollTimer) { clearInterval(pollTimer); pollTimer = null }
}

async function refreshJob() {
  if (!latestJob.value) return
  refreshingJob.value = true
  try {
    latestJob.value = await fetchAdminTranslateJob(latestJob.value.id)
  } catch (e) {
    toast.error(`接口未实现或调用失败: ${e instanceof Error ? e.message : 'fetchAdminTranslateJob'}`)
  } finally {
    refreshingJob.value = false
  }
}

onMounted(() => { /* manual refresh only */ })
onUnmounted(stopPolling)
</script>
