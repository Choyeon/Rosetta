<template>
  <div class="p-6 space-y-6">
    <div class="flex items-center gap-3">
      <div
        class="size-10 rounded-xl flex items-center justify-center bg-primary text-primary-foreground"
      >
        <HardDrive class="size-5 text-white" />
      </div>
      <div>
        <h1 class="text-xl font-bold tracking-tight">
          缓存管理
        </h1>
        <p class="text-sm text-muted-foreground">
          查看缓存状态并执行按粒度的清退操作
        </p>
      </div>
    </div>

    <div class="grid grid-cols-2 gap-4 md:grid-cols-2 lg:grid-cols-4">
      <Card class="rounded-2xl">
        <CardContent class="p-5 space-y-3">
          <div class="flex items-center justify-between">
            <p class="text-xs text-muted-foreground font-medium uppercase tracking-wide">
              缓存后端
            </p>
            <div
              class="size-10 rounded-xl flex items-center justify-center shrink-0"
              :class="cacheStatus.backend === 'redis' ? 'bg-[#DC382D]/15 text-[#DC382D]' : 'bg-info-muted text-info-foreground'"
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
              {{ cacheStatus.backend || 'memory' }}
            </div>
            <div class="text-xs text-muted-foreground mt-0.5">
              {{ cacheStatus.backend === 'redis' ? '分布式 Redis 缓存' : '进程内 Memory 缓存' }}
            </div>
          </div>
        </CardContent>
      </Card>

      <Card class="rounded-2xl">
        <CardContent class="p-5 space-y-3">
          <div class="flex items-center justify-between">
            <p class="text-xs text-muted-foreground font-medium uppercase tracking-wide">
              Keys 数量
            </p>
            <div class="size-10 rounded-xl bg-primary-muted text-primary-foreground flex items-center justify-center shrink-0">
              <Layers class="size-5" />
            </div>
          </div>
          <div
            v-if="!statusLoading"
            class="text-2xl font-bold tabular-nums tracking-tight"
          >
            {{ (cacheStatus.keys ?? 0).toLocaleString('zh-CN') }}
          </div>
          <Skeleton
            v-else
            class="h-8 w-24 rounded-lg"
          />
        </CardContent>
      </Card>

      <Card class="rounded-2xl">
        <CardContent class="p-5 space-y-3">
          <div class="flex items-center justify-between">
            <p class="text-xs text-muted-foreground font-medium uppercase tracking-wide">
              内存占用
            </p>
            <div class="size-10 rounded-xl bg-warning-muted text-warning-foreground flex items-center justify-center shrink-0">
              <PieChart class="size-5" />
            </div>
          </div>
          <div
            v-if="!statusLoading"
            class="space-y-0.5"
          >
            <div class="text-2xl font-bold tabular-nums tracking-tight">
              {{ formatBytes(cacheStatus.memory_used_bytes) }}
            </div>
            <div class="text-xs text-muted-foreground">
              {{ cacheStatus.memory_used_bytes != null ? `${cacheStatus.memory_used_bytes.toLocaleString('zh-CN')} Bytes` : '未上报' }}
            </div>
          </div>
          <Skeleton
            v-else
            class="h-8 w-28 rounded-lg"
          />
        </CardContent>
      </Card>

      <Card class="rounded-2xl">
        <CardContent class="p-5 space-y-3">
          <div class="flex items-center justify-between">
            <p class="text-xs text-muted-foreground font-medium uppercase tracking-wide">
              命中率
            </p>
            <div
              class="size-10 rounded-xl flex items-center justify-center shrink-0"
              :class="hitRateWarning ? 'bg-warning-muted text-warning-foreground' : 'bg-success-muted text-success-foreground'"
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
            class="space-y-1"
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
                :class="hitRateWarning ? 'text-warning' : 'text-success'"
              >
                {{ hitPctFixed }}
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
        </CardContent>
      </Card>
    </div>

    <Card class="rounded-2xl">
      <CardHeader>
        <CardTitle class="flex items-center gap-2">
          <Shovel class="size-5" /> 缓存清退模式
        </CardTitle>
        <CardDescription>
          选择需要清退的缓存范围。除「全部」外，其他模式不会影响彼此的内容；清退后首次访问会变慢。
        </CardDescription>
      </CardHeader>
      <CardContent class="space-y-5">
        <div class="grid md:grid-cols-2 lg:grid-cols-3 gap-3">
          <label
            v-for="m in modes"
            :key="m.key"
            class="flex flex-col p-4 rounded-2xl border-2 transition-all cursor-pointer group"
            :class="flushMode === m.key
              ? 'border-[#0EA5E9] bg-[#0EA5E9]/5 shadow-soft'
              : 'border-border bg-card hover:border-[#0EA5E9]/40 hover:bg-muted/30'"
          >
            <div class="flex items-start gap-3">
              <input
                type="radio"
                class="accent-[#0EA5E9] mt-1"
                :checked="flushMode === m.key"
                @change="flushMode = m.key"
              >
              <div class="flex-1 min-w-0">
                <div class="flex items-center gap-2">
                  <component
                    :is="m.icon"
                    class="size-4"
                    :class="flushMode === m.key ? 'text-[#0EA5E9]' : 'text-muted-foreground'"
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
          <div class="space-y-0.5">
            <h3 class="font-semibold">
              即将执行：<span class="text-[#0EA5E9]">{{ currentModeMeta?.label }}</span>
            </h3>
            <p class="text-sm text-muted-foreground">
              {{ currentModeMeta?.scope }} · 确认后将立即清退
            </p>
          </div>
          <Button
            variant="outline"
            size="lg"
            :disabled="flushing"
            class="rounded-2xl !px-8 group border-2 border-[#0EA5E9]/50 text-[#0369A1] hover:bg-[#0EA5E9] hover:text-white hover:border-[#0EA5E9] transition-all"
            @click="confirmFlushOpen = true"
          >
            <Trash2
              v-if="!flushing"
              class="size-5 mr-2"
            />
            <Loader2
              v-else
              class="size-5 mr-2 animate-spin"
            />
            立即执行清退
          </Button>
        </div>
      </CardContent>
    </Card>

    <Dialog v-model:open="confirmFlushOpen">
      <DialogContent class="max-w-md rounded-2xl">
        <DialogHeader>
          <DialogTitle class="flex items-center gap-2">
            <AlertTriangle class="size-5 text-warning" />
            二次确认：缓存清退
          </DialogTitle>
          <DialogDescription>
            即将对 <b>{{ currentModeMeta?.label }}</b> 范围的缓存执行清退：
          </DialogDescription>
        </DialogHeader>
        <div class="rounded-xl p-4 border border-warning/40 bg-warning-muted/30 space-y-2">
          <p class="text-sm">
            <b>影响：</b>{{ currentModeMeta?.scope }}
          </p>
          <p class="text-sm text-muted-foreground">
            清退后首次访问会重新计算，响应速度会变慢；后续请求将恢复正常且带有新数据。
          </p>
        </div>
        <DialogFooter class="gap-2">
          <Button
            variant="outline"
            class="rounded-xl"
            :disabled="flushing"
            @click="confirmFlushOpen = false"
          >
            取消
          </Button>
          <Button
            variant="destructive"
            class="rounded-xl"
            :disabled="flushing"
            @click="handleFlush"
          >
            <Loader2
              v-if="flushing"
              class="size-4 animate-spin"
            />
            <Trash2
              v-else
              class="size-4"
            />
            确认清退
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
import { ref, computed, onMounted } from 'vue'
import {
  fetchAdminCacheStatus,
  flushAdminCache,
  type AdminCacheStatus,
  type AdminCacheFlushMode
} from '~~/composables/useAdminManage'
import { useToast } from '~~/composables/useToast'
import {
  HardDrive, Database, MemoryStick, Layers, PieChart, Target, TrendingDown,
  Shovel, AlertTriangle, Trash2, Loader2, Info,
  Boxes, BookOpen, FileText, Settings as SettingsIcon, Puzzle
} from '@lucide/vue'
import { Button } from '~~/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '~~/components/ui/card'
import { Skeleton } from '~~/components/ui/skeleton'
import { Separator } from '~~/components/ui/separator'
import {
  Dialog, DialogContent, DialogDescription, DialogFooter,
  DialogHeader, DialogTitle
} from '~~/components/ui/dialog'

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
const flushing = ref(false)
const confirmFlushOpen = ref(false)
const flushMode = ref<AdminCacheFlushMode>('all')

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
  try {
    const r = await fetchAdminCacheStatus()
    cacheStatus.value = r || emptyStatus()
  } catch (e) {
    toast.error(`接口未实现或调用失败: ${e instanceof Error ? e.message : 'fetchAdminCacheStatus'}`)
    cacheStatus.value = emptyStatus()
  } finally {
    statusLoading.value = false
  }
}

async function handleFlush() {
  flushing.value = true
  try {
    const r = await flushAdminCache(flushMode.value)
    confirmFlushOpen.value = false
    toast.success(r?.message || `已清退缓存：${currentModeMeta.value?.label}`)
    await loadStatus()
  } catch (e) {
    toast.error(`接口未实现或调用失败: ${e instanceof Error ? e.message : 'flushAdminCache'}`)
  } finally {
    flushing.value = false
  }
}

onMounted(loadStatus)
</script>
