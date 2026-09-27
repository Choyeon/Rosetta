<!--
  缓存管理页：展示服务端缓存后端/键数/内存/命中率，按粒度模式（all/post_list/post_detail/settings/fragments）执行清退。
  契约：GET /admin/cache/status 返回裸对象（无 success 信封）；hit_rate 可能是 0-1 小数或 0-100 百分数，须按 <=1 归一化否则命中率显示错量级；
  接口走 silentToast + 页内联错误态避免双重提示，「全部清退」在 DangerConfirmDialog 中要求输入短语二次确认。
-->
<template>
  <div class="flex flex-col gap-5">
    <AdminPageHeader
      title="缓存管理"
      description="查看缓存状态并执行按粒度的清退操作"
      :icon="HardDrive"
    />

    <Alert
      v-if="statusError"
      variant="destructive"
      class="rounded-xl"
    >
      <AlertTriangle class="size-4" />
      <AlertTitle>缓存状态获取失败</AlertTitle>
      <AlertDescription class="flex flex-wrap items-center justify-between gap-3">
        <span>{{ statusError }}</span>
        <Button
          variant="outline"
          size="sm"
          class="rounded-lg shrink-0"
          :disabled="statusLoading"
          @click="loadStatus"
        >
          <RotateCcw data-icon="inline-start" />
          重试
        </Button>
      </AlertDescription>
    </Alert>

    <div class="grid grid-cols-2 gap-4 md:grid-cols-2 lg:grid-cols-4">
      <AdminCard class="rounded-2xl">
        <div class="flex flex-col gap-3 p-5">
          <div class="flex items-center justify-between">
            <p class="text-xs text-muted-foreground font-medium uppercase tracking-wide">
              缓存后端
            </p>
            <div
              class="size-10 rounded-xl flex items-center justify-center shrink-0"
              :class="cacheStatus.backend === 'redis' ? 'bg-destructive/15 text-destructive' : 'bg-info-muted text-info-muted-foreground'"
            >
              <Database
                v-if="cacheStatus.backend === 'redis'"
                class="size-5"
              />
              <MemoryStick
                v-else
                class="size-5"
              />
            </div>
          </div>
          <div>
            <div class="text-2xl font-bold tracking-tight capitalize">
              {{ statusError ? '未知' : (cacheStatus.backend || 'memory') }}
            </div>
            <div class="text-xs text-muted-foreground mt-0.5">
              {{ statusError ? '状态接口不可用' : (cacheStatus.backend === 'redis' ? '分布式 Redis 缓存' : '进程内 Memory 缓存') }}
            </div>
          </div>
        </div>
      </AdminCard>

      <AdminCard class="rounded-2xl">
        <div class="flex flex-col gap-3 p-5">
          <div class="flex items-center justify-between">
            <p class="text-xs text-muted-foreground font-medium uppercase tracking-wide">
              Keys 数量
            </p>
            <div class="size-10 rounded-xl bg-primary-muted text-primary-muted-foreground flex items-center justify-center shrink-0">
              <Layers class="size-5" />
            </div>
          </div>
          <div
            v-if="!statusLoading"
            class="text-2xl font-bold tabular-nums tracking-tight"
          >
            {{ statusError ? '—' : (cacheStatus.keys ?? 0).toLocaleString('zh-CN') }}
          </div>
          <Skeleton
            v-else
            class="h-8 w-24 rounded-lg"
          />
        </div>
      </AdminCard>

      <AdminCard class="rounded-2xl">
        <div class="flex flex-col gap-3 p-5">
          <div class="flex items-center justify-between">
            <p class="text-xs text-muted-foreground font-medium uppercase tracking-wide">
              内存占用
            </p>
            <div class="size-10 rounded-xl bg-warning-muted text-warning-muted-foreground flex items-center justify-center shrink-0">
              <PieChart class="size-5" />
            </div>
          </div>
          <div
            v-if="!statusLoading"
            class="flex flex-col gap-0.5"
          >
            <div class="text-2xl font-bold tabular-nums tracking-tight">
              {{ statusError ? '—' : formatBytes(cacheStatus.memory_used_bytes) }}
            </div>
            <div class="text-xs text-muted-foreground">
              {{ statusError ? '状态接口不可用' : (cacheStatus.memory_used_bytes != null ? `${cacheStatus.memory_used_bytes.toLocaleString('zh-CN')} Bytes` : '未上报') }}
            </div>
          </div>
          <Skeleton
            v-else
            class="h-8 w-28 rounded-lg"
          />
        </div>
      </AdminCard>

      <AdminCard class="rounded-2xl">
        <div class="flex flex-col gap-3 p-5">
          <div class="flex items-center justify-between">
            <p class="text-xs text-muted-foreground font-medium uppercase tracking-wide">
              命中率
            </p>
            <div
              class="size-10 rounded-xl flex items-center justify-center shrink-0"
              :class="hitRateWarning ? 'bg-warning-muted text-warning-muted-foreground' : 'bg-success-muted text-success-muted-foreground'"
            >
              <Target
                v-if="!hitRateWarning"
                class="size-5"
              />
              <TrendingDown
                v-else
                class="size-5"
              />
            </div>
          </div>
          <div
            v-if="!statusLoading"
            class="flex flex-col gap-1"
          >
            <div class="flex items-center gap-2">
              <div class="flex-1 h-2 rounded-full bg-muted overflow-hidden">
                <div
                  class="h-full rounded-full transition-all"
                  :style="{
                    width: `${hitPct}%`,
                    backgroundColor: hitRateWarning
                      ? 'hsl(var(--primary))'
                      : 'hsl(var(--success))'
                  }"
                />
              </div>
              <span
                class="font-bold tabular-nums min-w-[52px] text-right"
                :class="statusError ? 'text-muted-foreground' : (hitRateWarning ? 'text-warning' : 'text-success')"
              >
                {{ statusError ? '—' : hitPctFixed }}
              </span>
            </div>
            <p
              v-if="hitRateWarning"
              class="text-xs text-warning"
            >
              <AlertTriangle class="size-3 inline mr-1" />
              命中率偏低（建议 ≥ 70%）
            </p>
            <p
              v-else-if="statusError || cacheStatus.hit_rate == null"
              class="text-xs text-muted-foreground"
            >
              后端未上报命中率
            </p>
            <p
              v-else
              class="text-xs text-muted-foreground"
            >
              健康范围
            </p>
          </div>
          <Skeleton
            v-else
            class="h-8 w-full rounded-lg"
          />
        </div>
      </AdminCard>
    </div>

    <AdminCard class="rounded-2xl">
      <div class="mb-4">
        <div class="flex items-center gap-2 mb-2">
          <Shovel class="size-5" />
          <span class="text-lg font-semibold">缓存清退模式</span>
        </div>
        <p class="text-sm text-muted-foreground">
          选择需要清退的缓存范围。除「全部」外，其他模式不会影响彼此的内容；清退后首次访问会变慢。
        </p>
      </div>
      <div class="flex flex-col gap-5">
        <div class="grid md:grid-cols-2 lg:grid-cols-3 gap-3">
          <label
            v-for="m in modes"
            :key="m.key"
            class="flex flex-col p-4 rounded-2xl border-2 transition-all cursor-pointer group"
            :class="flushMode === m.key
              ? 'border-primary bg-primary/5 shadow-soft'
              : 'border-border bg-card hover:border-primary/40 hover:bg-muted/30'"
          >
            <div class="flex items-start gap-3">
              <input
                type="radio"
                class="accent-[hsl(var(--primary))] mt-1"
                :checked="flushMode === m.key"
                @change="flushMode = m.key"
              >
              <div class="flex-1 min-w-0">
                <div class="flex items-center gap-2">
                  <component
                    :is="m.icon"
                    class="size-4"
                    :class="flushMode === m.key ? 'text-primary' : 'text-muted-foreground'"
                  />
                  <div class="font-semibold">{{ m.label }}</div>
                </div>
                <p class="text-sm text-muted-foreground mt-1.5 leading-relaxed">{{ m.desc }}</p>
                <div class="mt-2 inline-flex items-center gap-1 text-xs rounded-lg bg-muted/50 px-2 py-1 text-muted-foreground">
                  <Info class="size-3" />
                  影响：{{ m.scope }}
                </div>
              </div>
            </div>
          </label>
        </div>

        <Separator />

        <div class="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
          <div class="flex flex-col gap-0.5">
            <h3 class="font-semibold">
              即将执行：<span class="text-primary">{{ currentModeMeta?.label }}</span>
            </h3>
            <p class="text-sm text-muted-foreground">
              {{ currentModeMeta?.scope }} · 确认后将立即清退
            </p>
          </div>
          <Button
            variant="outline"
            size="lg"
            :disabled="flushing"
            class="rounded-2xl !px-8 group border-2 border-primary/50 text-primary hover:bg-primary hover:text-primary-foreground hover:border-primary transition-all"
            @click="confirmFlushOpen = true"
          >
            <Trash2
              v-if="!flushing"
              data-icon="inline-start"
            />
            <Loader2
              v-else
              data-icon="inline-start"
              class="animate-spin"
            />
            立即执行清退
          </Button>
        </div>
      </div>
    </AdminCard>

    <DangerConfirmDialog
      v-model:open="confirmFlushOpen"
      :title="`二次确认：${currentModeMeta?.label ?? ''}`"
      :description="`即将清退「${currentModeMeta?.label}」范围（${currentModeMeta?.scope}）。清退后首次访问会重新计算，响应速度会短暂变慢，且不可撤销。`"
      confirm-text="确认清退"
      :confirm-phrase="flushMode === 'all' ? '全部清退' : ''"
      :on-confirm="runFlush"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import type { AdminCacheStatus, AdminCacheFlushMode } from '~~/composables/useAdminManage'
import { apiFetch } from '~~/composables/useApi'
import { extractApiErrorMessage } from '~~/lib/utils'
import { useToast } from '~~/composables/useToast'
import {
  HardDrive, Database, MemoryStick, Layers, PieChart, Target, TrendingDown,
  Shovel, AlertTriangle, Trash2, Loader2, Info, RotateCcw,
  Boxes, BookOpen, FileText, Settings as SettingsIcon, Puzzle
} from '@lucide/vue'
import { Button } from '~~/components/ui/button'
import AdminCard from '~~/components/admin/AdminCard.vue'
import DangerConfirmDialog from '~~/components/admin/tools/DangerConfirmDialog.vue'
import { Skeleton } from '~~/components/ui/skeleton'
import { Separator } from '~~/components/ui/separator'
import { Alert, AlertTitle, AlertDescription } from '~~/components/ui/alert'

definePageMeta({ ssr: false, layout: 'admin' })

const toast = useToast()

const modes = [
  {
    key: 'all' as const,
    label: '全部清退',
    icon: Boxes,
    desc: '清空服务端所有缓存键，用于部署或大范围数据变更之后。',
    scope: '所有已缓存的页面、API、配置与片段'
  },
  {
    key: 'post_list' as const,
    label: '文章列表',
    icon: BookOpen,
    desc: '只清退文章列表类缓存（首页、归档、分类、标签等分页）。',
    scope: '/posts /categories /tags /archive /series 等列表 API'
  },
  {
    key: 'post_detail' as const,
    label: '文章详情',
    icon: FileText,
    desc: '清退每篇文章详情页渲染结果与 TOC/阅读时长等附属缓存。',
    scope: '/posts/{slug} 详情、Markdown 解析结果、相关推荐'
  },
  {
    key: 'settings' as const,
    label: '站点配置',
    icon: SettingsIcon,
    desc: '清退站点设置（17 组 settings）读取缓存，让修改立即生效。',
    scope: 'GET /api/settings 各组的内存/Redis 读缓存'
  },
  {
    key: 'fragments' as const,
    label: '页面片段',
    icon: Puzzle,
    desc: '清退页面渲染片段，如侧栏组件、页脚、Hero、公告等片段。',
    scope: 'Sidebar / Footer / Hero / Notice 等小部件输出'
  }
]

const statusLoading = ref(true)
const statusError = ref('')
const flushing = ref(false)
const confirmFlushOpen = ref(false)
const flushMode = ref<AdminCacheFlushMode>('all')

/** GET /admin/cache/status 返回裸对象（无 success 信封） */
interface CacheStatusResponse {
  backend?: string | null
  keys?: number | null
  memory_used_bytes?: number | null
  hit_rate?: number | null
}

interface CacheFlushResponse {
  mode?: string
  deleted_keys?: number
  message?: string
}

const emptyStatus = (): AdminCacheStatus => ({
  backend: 'memory',
  keys: 0,
  memory_used_bytes: null,
  hit_rate: null
})

const cacheStatus = ref<AdminCacheStatus>(emptyStatus())

const currentModeMeta = computed(() => modes.find(m => m.key === flushMode.value))

const hitPct = computed(() => {
  const r = cacheStatus.value.hit_rate
  if (r == null) return 0
  const p = r <= 1 ? r * 100 : r
  return Math.max(0, Math.min(100, p))
})

const hitPctFixed = computed(() => `${hitPct.value.toFixed(1)}%`)

const hitRateWarning = computed(() => cacheStatus.value.hit_rate != null && hitPct.value < 70)

function formatBytes(b: number | null | undefined): string {
  if (b == null) return '-'
  if (b < 1024) return `${b} B`
  if (b < 1024 * 1024) return `${(b / 1024).toFixed(1)} KB`
  if (b < 1024 * 1024 * 1024) return `${(b / (1024 * 1024)).toFixed(2)} MB`
  return `${(b / (1024 * 1024 * 1024)).toFixed(2)} GB`
}

async function loadStatus() {
  statusLoading.value = true
  statusError.value = ''
  try {
    // 状态接口失败时必须可见：silentToast 避免与页面内联错误重复提示
    const r = await apiFetch<CacheStatusResponse>('/admin/cache/status', { silentToast: true })
    cacheStatus.value = {
      backend: r?.backend === 'redis' ? 'redis' : 'memory',
      keys: Number(r?.keys ?? 0),
      memory_used_bytes: r?.memory_used_bytes ?? null,
      hit_rate: r?.hit_rate ?? null
    }
  } catch (err) {
    cacheStatus.value = emptyStatus()
    const e = err as { data?: unknown, message?: string }
    statusError.value = extractApiErrorMessage(e?.data, e?.message || '无法连接缓存状态接口')
  } finally {
    statusLoading.value = false
  }
}

/** 供 DangerConfirmDialog 调用：throw 则弹窗保持打开并内联展示错误 */
async function runFlush() {
  flushing.value = true
  try {
    const r = await apiFetch<CacheFlushResponse>('/admin/cache/flush', {
      method: 'POST',
      body: { mode: flushMode.value },
      silentToast: true
    })
    const keysHint = r?.deleted_keys != null ? `（${r.deleted_keys} 个键）` : ''
    toast.success(r?.message ?? `已清退缓存：${currentModeMeta.value?.label}${keysHint}`)
    await loadStatus()
  } finally {
    flushing.value = false
  }
}

onMounted(loadStatus)
</script>
