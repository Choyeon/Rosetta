<!-- 性能监控页：24h 接口摘要、慢路径排行、近 7 天慢请求明细与性能表清理。
     契约：GET /admin/performance/slow 返回「裸数组」（无 success 信封）且字段为 endpoint/response_time_ms、
     仅支持 limit(≤100) 无分页，故本页绕过 useAdminManage 直接 apiFetch 并在页面侧归一化字段；
     清理保留天数校验失败以 throw 交给 DangerConfirmDialog 内联展示，而非 toast。 -->
<template>
  <div class="flex flex-col gap-5">
    <AdminPageHeader
      title="性能监控"
      description="实时观察接口响应、慢请求与性能数据存储情况"
      :icon="Gauge"
    >
      <template #actions>
        <Button
          variant="outline"
          class="rounded-xl"
          :disabled="anyLoading"
          @click="reloadAll"
        >
          <RefreshCw
            data-icon="inline-start"
            :class="anyLoading ? 'animate-spin' : ''"
          />
          刷新
        </Button>
      </template>
    </AdminPageHeader>

    <div class="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-5 gap-4">
      <StatCard
        :loading="summaryLoading"
        title="24h 请求总数"
        :icon="Activity"
        accent="info"
        :value="summary.total_requests_24h.toLocaleString('zh-CN')"
      />
      <StatCard
        :loading="summaryLoading"
        title="24h 错误率"
        :icon="AlertTriangle"
        accent="error"
        :value="`${(summary.error_rate_24h * 100).toFixed(2)}%`"
      />
      <StatCard
        :loading="summaryLoading"
        title="平均延迟"
        :icon="Timer"
        accent="primary"
        :value="`${summary.p50_ms} ms`"
      />
      <StatCard
        :loading="summaryLoading"
        title="P95 延迟"
        :icon="TimerReset"
        accent="warning"
        :value="`${summary.p95_ms} ms`"
      />
      <StatCard
        :loading="summaryLoading"
        title="P99 延迟"
        :icon="Zap"
        accent="error"
        :value="`${summary.p99_ms} ms`"
      />
    </div>

    <Alert
      v-if="summaryError"
      variant="destructive"
      class="rounded-xl"
    >
      <AlertTriangle class="size-4" />
      <AlertTitle>性能摘要获取失败</AlertTitle>
      <AlertDescription class="flex flex-wrap items-center justify-between gap-3">
        <span>{{ summaryError }}</span>
        <Button
          variant="outline"
          size="sm"
          class="rounded-lg shrink-0"
          :disabled="summaryLoading"
          @click="loadSummary"
        >
          <RotateCcw data-icon="inline-start" />
          重试
        </Button>
      </AlertDescription>
    </Alert>

    <Tabs
      v-model="activeTab"
      class="w-full"
    >
      <TabsList class="rounded-xl p-1 bg-muted/40">
        <TabsTrigger
          value="overview"
          class="rounded-lg data-[state=active]:text-white data-[state=active]:shadow-sm"
          :class="activeTab === 'overview' ? 'bg-primary text-primary-foreground' : ''"
        >
          <BarChart3
            class="size-4"
            data-icon="inline-start"
          />
          概览
        </TabsTrigger>
        <TabsTrigger
          value="slow"
          class="rounded-lg data-[state=active]:text-white data-[state=active]:shadow-sm"
          :class="activeTab === 'slow' ? 'bg-primary text-primary-foreground' : ''"
        >
          <Clock
            class="size-4"
            data-icon="inline-start"
          />
          慢请求明细
        </TabsTrigger>
        <TabsTrigger
          value="storage"
          class="rounded-lg data-[state=active]:text-white data-[state=active]:shadow-sm"
          :class="activeTab === 'storage' ? 'bg-primary text-primary-foreground' : ''"
        >
          <Database
            class="size-4"
            data-icon="inline-start"
          />
          存储与清理
        </TabsTrigger>
      </TabsList>

      <TabsContent
        value="overview"
        class="mt-6"
      >
        <AdminCard>
          <div class="flex flex-col gap-1.5 mb-4">
            <h3 class="text-base font-semibold">
              慢路径 Top 排名（近 24 小时）
            </h3>
            <p class="text-sm text-muted-foreground">
              按平均响应耗时排序的接口路径，建议优先优化红色与赭色条目
            </p>
          </div>
          <div class="p-0">
            <div
              v-if="summaryLoading"
              class="flex flex-col gap-3 p-5"
            >
              <Skeleton
                v-for="i in 6"
                :key="i"
                class="h-12 rounded-xl"
              />
            </div>
            <div
              v-else-if="!summary.top_slow_paths || summary.top_slow_paths.length === 0"
              class="p-12"
            >
              <Alert
                variant="info"
                class="rounded-xl max-w-lg mx-auto"
              >
                <Info class="size-4" />
                <AlertTitle>暂无慢路径数据</AlertTitle>
                <AlertDescription>
                  {{ summaryError ? '摘要接口不可用，请点击上方重试。' : '近 24 小时内没有平均耗时超过 200ms 的接口，或尚无监控数据。' }}
                </AlertDescription>
              </Alert>
            </div>
            <div
              v-else
              class="divide-y divide-border"
            >
              <div
                v-for="(p, idx) in summary.top_slow_paths"
                :key="p.path"
                class="flex items-center gap-4 px-5 py-3.5 hover:bg-muted/30 transition-colors"
              >
                <div
                  class="size-8 rounded-lg flex items-center justify-center font-bold text-xs shrink-0"
                  :class="idx < 3 ? 'bg-warning-muted text-warning-muted-foreground' : 'bg-muted text-muted-foreground'"
                >
                  #{{ idx + 1 }}
                </div>
                <div class="flex-1 min-w-0">
                  <div class="font-mono text-sm truncate">
                    {{ p.path }}
                  </div>
                  <div class="text-xs text-muted-foreground tabular-nums mt-0.5">
                    命中次数：{{ p.count.toLocaleString('zh-CN') }} 次
                  </div>
                </div>
                <div class="flex items-center gap-3 shrink-0">
                  <div class="w-40 h-2 rounded-full bg-muted overflow-hidden hidden sm:block">
                    <div
                      class="h-full rounded-full"
                      :style="{
                        width: `${Math.min(100, p.avg_ms / 5)}%`,
                        backgroundColor: p.avg_ms > 500
                          ? 'hsl(var(--destructive))'
                          : p.avg_ms > 200
                            ? 'hsl(var(--primary))'
                            : 'hsl(var(--success))'
                      }"
                    />
                  </div>
                  <div
                    class="font-semibold tabular-nums text-sm min-w-[72px] text-right"
                    :class="p.avg_ms > 500 ? 'text-error' : p.avg_ms > 200 ? 'text-warning' : 'text-success'"
                  >
                    {{ p.avg_ms }} ms
                  </div>
                </div>
              </div>
            </div>
          </div>
        </AdminCard>
      </TabsContent>

      <TabsContent
        value="slow"
        class="mt-6"
      >
        <AdminCard class="overflow-hidden">
          <div class="flex flex-wrap items-center justify-between gap-3 px-5 pt-5 pb-4">
            <div class="flex flex-col gap-1.5">
              <h3 class="text-base font-semibold">
                最近 7 天最慢请求
              </h3>
              <p class="text-sm text-muted-foreground">
                后端按耗时倒序返回 Top N 原始记录（非分页接口），调整数量即时重新拉取
              </p>
            </div>
            <div class="flex items-center gap-2">
              <Label
                for="slow-limit"
                class="text-sm whitespace-nowrap"
              >
                数量
              </Label>
              <Select
                v-model="slowLimit"
                @update:model-value="loadSlow"
              >
                <SelectTrigger
                  id="slow-limit"
                  class="w-24 rounded-xl"
                >
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem
                    v-for="n in slowLimitOptions"
                    :key="n"
                    :value="n"
                  >
                    {{ n }}
                  </SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>

          <div class="p-0">
            <div
              v-if="slowLoading"
              class="flex flex-col gap-3 p-6"
            >
              <Skeleton
                v-for="i in 6"
                :key="i"
                class="h-14 rounded-xl"
              />
            </div>
            <div
              v-else-if="slowError"
              class="p-12"
            >
              <Alert
                variant="destructive"
                class="rounded-xl max-w-lg mx-auto"
              >
                <AlertTriangle class="size-4" />
                <AlertTitle>慢请求获取失败</AlertTitle>
                <AlertDescription class="flex flex-wrap items-center justify-between gap-3">
                  <span>{{ slowError }}</span>
                  <Button
                    variant="outline"
                    size="sm"
                    class="rounded-lg shrink-0"
                    @click="loadSlow"
                  >
                    <RotateCcw data-icon="inline-start" />
                    重试
                  </Button>
                </AlertDescription>
              </Alert>
            </div>
            <div
              v-else
              class="overflow-x-auto"
            >
              <table class="w-full text-sm">
                <caption class="sr-only">
                  最近 7 天最慢请求列表
                </caption>
                <thead class="bg-muted/40 text-muted-foreground text-xs uppercase tracking-wide">
                  <tr>
                    <th class="text-left font-medium px-5 py-3">
                      方法
                    </th>
                    <th class="text-left font-medium px-5 py-3">
                      路径
                    </th>
                    <th class="text-right font-medium px-5 py-3">
                      耗时
                    </th>
                    <th class="text-right font-medium px-5 py-3">
                      状态码
                    </th>
                    <th class="text-left font-medium px-5 py-3">
                      IP
                    </th>
                    <th class="text-left font-medium px-5 py-3">
                      UA
                    </th>
                    <th class="text-right font-medium px-5 py-3">
                      时间
                    </th>
                  </tr>
                </thead>
                <tbody class="divide-y divide-border">
                  <tr
                    v-for="r in slowRows"
                    :key="r.id"
                    class="hover:bg-muted/30"
                  >
                    <td class="px-5 py-4">
                      <Badge
                        :class="methodClass(r.method)"
                        class="rounded-lg text-[11px] uppercase tracking-wide"
                      >
                        {{ r.method }}
                      </Badge>
                    </td>
                    <td class="px-5 py-4 font-mono text-xs max-w-[300px] truncate">
                      {{ r.path }}
                    </td>
                    <td
                      class="px-5 py-4 text-right tabular-nums font-semibold"
                      :class="r.duration_ms > 500 ? 'text-error' : r.duration_ms > 200 ? 'text-warning' : ''"
                    >
                      {{ r.duration_ms }} ms
                    </td>
                    <td class="px-5 py-4 text-right tabular-nums">
                      <span
                        :class="String(r.status_code).startsWith('5') ? 'text-error font-semibold' : String(r.status_code).startsWith('4') ? 'text-warning font-medium' : ''"
                      >
                        {{ r.status_code }}
                      </span>
                    </td>
                    <td class="px-5 py-4 text-xs text-muted-foreground tabular-nums whitespace-nowrap">
                      {{ r.ip || '-' }}
                    </td>
                    <td
                      class="px-5 py-4 text-xs text-muted-foreground max-w-[220px] truncate"
                      :title="r.user_agent ?? ''"
                    >
                      {{ r.user_agent || '-' }}
                    </td>
                    <td class="px-5 py-4 text-xs text-muted-foreground text-right tabular-nums whitespace-nowrap">
                      {{ formatAdminDateTime(r.created_at) }}
                    </td>
                  </tr>
                </tbody>
              </table>
            </div>
            <div
              v-if="!slowLoading && !slowError && slowRows.length === 0"
              class="p-12"
            >
              <Alert
                variant="info"
                class="rounded-xl max-w-lg mx-auto"
              >
                <Info class="size-4" />
                <AlertTitle>暂无慢请求记录</AlertTitle>
                <AlertDescription>最近 7 天内没有可展示的请求耗时记录。</AlertDescription>
              </Alert>
            </div>
          </div>
        </AdminCard>
      </TabsContent>

      <TabsContent
        value="storage"
        class="mt-6"
      >
        <AdminCard>
          <div
            v-if="storageLoading"
            class="flex flex-col gap-3 p-5"
          >
            <Skeleton class="h-10 w-1/3 rounded-xl" />
            <Skeleton class="h-40 rounded-xl" />
          </div>
          <div
            v-else-if="storageError"
            class="p-12"
          >
            <Alert
              variant="destructive"
              class="rounded-xl max-w-lg mx-auto"
            >
              <AlertTriangle class="size-4" />
              <AlertTitle>存储统计获取失败</AlertTitle>
              <AlertDescription class="flex flex-wrap items-center justify-between gap-3">
                <span>{{ storageError }}</span>
                <Button
                  variant="outline"
                  size="sm"
                  class="rounded-lg shrink-0"
                  @click="loadStorage"
                >
                  <RotateCcw data-icon="inline-start" />
                  重试
                </Button>
              </AlertDescription>
            </Alert>
          </div>
          <div
            v-else
            class="flex flex-col gap-6"
          >
            <div class="grid grid-cols-2 lg:grid-cols-4 gap-4">
              <div class="flex flex-col gap-1 rounded-xl border border-border bg-muted/30 p-4">
                <span class="text-xs text-muted-foreground uppercase tracking-wide">总记录数</span>
                <span class="text-xl font-bold tabular-nums">{{ storage.total_count.toLocaleString('zh-CN') }}</span>
              </div>
              <div class="flex flex-col gap-1 rounded-xl border border-border bg-muted/30 p-4">
                <span class="text-xs text-muted-foreground uppercase tracking-wide">最早记录</span>
                <span class="text-sm font-medium tabular-nums mt-1">{{ storage.earliest_record ? formatAdminDateTime(storage.earliest_record) : '-' }}</span>
              </div>
              <div class="flex flex-col gap-1 rounded-xl border border-border bg-muted/30 p-4">
                <span class="text-xs text-muted-foreground uppercase tracking-wide">最新记录</span>
                <span class="text-sm font-medium tabular-nums mt-1">{{ storage.latest_record ? formatAdminDateTime(storage.latest_record) : '-' }}</span>
              </div>
              <div class="flex flex-col gap-1 rounded-xl border border-border bg-muted/30 p-4">
                <span class="text-xs text-muted-foreground uppercase tracking-wide">统计时间</span>
                <span class="text-sm font-medium tabular-nums mt-1">{{ storage.queried_at ? formatAdminDateTime(storage.queried_at) : formatAdminDateTime(new Date().toISOString()) }}</span>
              </div>
            </div>

            <div>
              <div class="flex flex-col gap-1.5 mb-4">
                <h3 class="text-base font-semibold">
                  近 7 天每日请求量
                </h3>
                <p class="text-sm text-muted-foreground">
                  来自 /admin/performance/storage 的 daily_breakdown 真实数据，悬停查看当日平均耗时
                </p>
              </div>
              <div
                v-if="dailyBars.length === 0"
                class="p-8"
              >
                <Alert variant="info">
                  <Info class="size-4" />
                  <AlertTitle>暂无近 7 天数据</AlertTitle>
                  <AlertDescription>监控中间件写入记录后将在此展示每日趋势。</AlertDescription>
                </Alert>
              </div>
              <div
                v-else
                class="flex items-end gap-2 h-52 rounded-xl border border-border/60 bg-muted/20 p-4 pb-2"
              >
                <div
                  v-for="d in dailyBars"
                  :key="d.date"
                  class="flex-1 h-full flex flex-col items-center justify-end gap-1 group min-w-0"
                >
                  <span class="text-[10px] tabular-nums text-muted-foreground opacity-0 group-hover:opacity-100 transition-opacity">
                    {{ d.count.toLocaleString('zh-CN') }}
                  </span>
                  <div
                    class="w-full max-w-12 rounded-t-md bg-primary/60 group-hover:bg-primary transition-colors"
                    :style="{ height: `${d.heightPct}%` }"
                    :title="`${d.date} · ${d.count} 条 · 平均 ${d.avg_ms} ms`"
                  />
                  <span class="text-[10px] text-muted-foreground tabular-nums shrink-0">
                    {{ d.date.slice(5) }}
                  </span>
                </div>
              </div>
            </div>

            <div>
              <h3 class="text-base font-semibold mb-3">
                状态码分布
              </h3>
              <div
                v-if="statusGroups.length === 0"
                class="text-sm text-muted-foreground"
              >
                暂无数据
              </div>
              <div
                v-else
                class="flex flex-wrap gap-2"
              >
                <Badge
                  v-for="g in statusGroups"
                  :key="g.group"
                  :class="g.class"
                  class="rounded-lg text-xs tabular-nums border-transparent"
                >
                  {{ g.group }}：{{ g.count.toLocaleString('zh-CN') }}
                </Badge>
              </div>
            </div>

            <Separator />

            <div class="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
              <div class="flex flex-col gap-0.5">
                <h3 class="font-semibold flex items-center gap-2">
                  <Eraser class="size-4 text-destructive" />
                  清理历史监控数据
                </h3>
                <p class="text-sm text-muted-foreground">
                  删除保留期之外的性能记录，避免监控表无限增长（1–365 天）
                </p>
              </div>
              <div class="flex items-center gap-2 shrink-0">
                <Label
                  for="cleanup-days"
                  class="text-sm whitespace-nowrap"
                >
                  保留最近
                </Label>
                <Input
                  id="cleanup-days"
                  v-model.number="cleanupDays"
                  type="number"
                  min="1"
                  max="365"
                  class="w-24 rounded-xl"
                  :disabled="cleanupRunning"
                />
                <span class="text-sm text-muted-foreground">天</span>
                <Button
                  variant="destructive"
                  class="rounded-xl"
                  :disabled="cleanupRunning"
                  @click="cleanupOpen = true"
                >
                  <Trash2
                    v-if="!cleanupRunning"
                    data-icon="inline-start"
                  />
                  <Loader2
                    v-else
                    data-icon="inline-start"
                    class="animate-spin"
                  />
                  清理旧数据
                </Button>
              </div>
            </div>
          </div>
        </AdminCard>
      </TabsContent>
    </Tabs>

    <DangerConfirmDialog
      v-model:open="cleanupOpen"
      title="二次确认：清理性能监控数据"
      :description="`即将永久删除 ${cleanupDaysHint} 天之前的全部性能监控记录，此操作不可撤销。`"
      confirm-text="确认清理"
      confirm-phrase="清理数据"
      phrase-hint="请输入「清理数据」以确认"
      :on-confirm="runCleanup"
    />
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref, shallowRef } from 'vue'
import {
  fetchAdminPerformanceSummary,
  formatAdminDateTime,
  type AdminPerformanceSummary
} from '~~/composables/useAdminManage'
import { apiFetch } from '~~/composables/useApi'
import { extractApiErrorMessage } from '~~/lib/utils'
import { useToast } from '~~/composables/useToast'
import {
  Gauge, Activity, AlertTriangle, Timer, TimerReset, Zap, BarChart3, Clock,
  Database, Info, RotateCcw, RefreshCw, Eraser, Trash2, Loader2
} from '@lucide/vue'
import { Button } from '~~/components/ui/button'
import AdminCard from '~~/components/admin/AdminCard.vue'
import AdminPageHeader from '~~/components/admin/AdminPageHeader.vue'
import DangerConfirmDialog from '~~/components/admin/tools/DangerConfirmDialog.vue'
import StatCard from '~~/components/admin/StatCard.vue'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '~~/components/ui/tabs'
import { Badge } from '~~/components/ui/badge'
import { Skeleton } from '~~/components/ui/skeleton'
import { Separator } from '~~/components/ui/separator'
import { Input } from '~~/components/ui/input'
import { Label } from '~~/components/ui/label'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '~~/components/ui/select'
import { Alert, AlertTitle, AlertDescription } from '~~/components/ui/alert'

definePageMeta({ ssr: false, layout: 'admin' })

const toast = useToast()

const activeTab = ref('overview')
const summaryLoading = ref(true)
const summaryError = ref('')

const summary = reactive<AdminPerformanceSummary>({
  total_requests_24h: 0,
  error_rate_24h: 0,
  p50_ms: 0,
  p95_ms: 0,
  p99_ms: 0,
  top_slow_paths: []
})

// ---------- 慢请求明细 ----------
// 后端 GET /admin/performance/slow 返回「裸数组」，字段为 endpoint / response_time_ms，
// 且不支持 page/page_size 分页（仅 limit，上限 100，见后端 Query(ge=1, le=100)），
// 因此本页直接调 apiFetch 并在页面侧归一化字段；useAdminManage 中对应的
// fetchAdminSlowRequests（无映射/假分页/吞错）因无任何调用方已于 2026-09 删除。
interface RawSlowRecord {
  id: number
  endpoint?: string | null
  method?: string | null
  status_code?: number | null
  response_time_ms?: number | null
  user_agent?: string | null
  ip?: string | null
  created_at?: string | null
}

interface SlowRow {
  id: number
  path: string
  method: string
  duration_ms: number
  status_code: number
  user_agent: string | null
  ip: string | null
  created_at: string | null
}

const slowLoading = ref(true)
const slowError = ref('')
// reka-ui Select 以字符串为 value（与 AdminPagination 约定一致），发请求时再转数字
const slowLimit = ref('20')
const slowLimitOptions = ['20', '50', '100']
const slowRows = shallowRef<SlowRow[]>([])

function methodClass(m: string): string {
  const up = m.toUpperCase()
  if (up === 'GET') return 'bg-success-muted text-success-muted-foreground border-transparent'
  if (up === 'POST') return 'bg-warning-muted text-warning-muted-foreground border-transparent'
  if (up === 'PUT') return 'bg-info-muted text-info-muted-foreground border-transparent'
  if (up === 'DELETE') return 'bg-error-muted text-error-muted-foreground border-transparent'
  return 'bg-muted text-muted-foreground border-transparent'
}

async function loadSlow() {
  slowLoading.value = true
  slowError.value = ''
  try {
    const raw = await apiFetch<RawSlowRecord[]>('/admin/performance/slow', {
      query: { limit: Number(slowLimit.value) },
      silentToast: true
    })
    slowRows.value = (Array.isArray(raw) ? raw : []).map(r => ({
      id: Number(r.id),
      path: String(r.endpoint ?? ''),
      method: String(r.method ?? ''),
      duration_ms: Number(r.response_time_ms ?? 0),
      status_code: Number(r.status_code ?? 0),
      user_agent: r.user_agent ?? null,
      ip: r.ip ?? null,
      created_at: r.created_at ?? null
    }))
  } catch (err) {
    slowRows.value = []
    const e = err as { data?: unknown, message?: string }
    slowError.value = extractApiErrorMessage(e?.data, e?.message || '无法加载慢请求记录')
  } finally {
    slowLoading.value = false
  }
}

// ---------- 存储统计与清理 ----------
interface StorageStatusRow {
  status_code: number
  count: number
}

interface StorageDailyRow {
  date: string
  count: number
  avg_response_time_ms: number
}

interface StorageStats {
  total_count: number
  earliest_record: string | null
  latest_record: string | null
  status_breakdown: StorageStatusRow[]
  daily_breakdown: StorageDailyRow[]
  queried_at?: string | null
}

interface CleanupResult {
  success: boolean
  deleted_count: number
  cutoff_date: string
  remaining_count: number
}

const storageLoading = ref(true)
const storageError = ref('')
const storage = ref<StorageStats>({
  total_count: 0,
  earliest_record: null,
  latest_record: null,
  status_breakdown: [],
  daily_breakdown: []
})

const cleanupOpen = ref(false)
const cleanupRunning = ref(false)
const cleanupDays = ref(30)

const cleanupDaysHint = computed(() => {
  const d = clampDays(cleanupDays.value)
  return d == null ? '（天数无效）' : `${d}`
})

const dailyBars = computed(() => {
  const rows = storage.value.daily_breakdown ?? []
  const max = Math.max(...rows.map(r => r.count), 1)
  return rows.map(r => ({
    date: r.date,
    count: Number(r.count ?? 0),
    avg_ms: Number(r.avg_response_time_ms ?? 0),
    heightPct: Math.max(3, Math.round((Number(r.count ?? 0) / max) * 100))
  }))
})

const statusGroups = computed(() => {
  const agg: Record<string, number> = {}
  for (const row of storage.value.status_breakdown ?? []) {
    const g = `${String(row.status_code).charAt(0)}xx`
    agg[g] = (agg[g] ?? 0) + Number(row.count ?? 0)
  }
  const colorFor: Record<string, string> = {
    '2xx': 'bg-success-muted text-success-muted-foreground',
    '3xx': 'bg-info-muted text-info-muted-foreground',
    '4xx': 'bg-warning-muted text-warning-muted-foreground',
    '5xx': 'bg-error-muted text-error-muted-foreground'
  }
  return Object.entries(agg)
    .sort((a, b) => a[0].localeCompare(b[0]))
    .map(([group, count]) => ({ group, count, class: colorFor[group] ?? 'bg-muted text-muted-foreground' }))
})

function clampDays(v: unknown): number | null {
  const n = Number(v)
  if (!Number.isInteger(n) || n < 1 || n > 365) return null
  return n
}

async function loadSummary() {
  summaryLoading.value = true
  summaryError.value = ''
  try {
    const r = await fetchAdminPerformanceSummary()
    Object.assign(summary, r)
  } catch (err) {
    const e = err as { data?: unknown, message?: string }
    summaryError.value = extractApiErrorMessage(e?.data, e?.message || '无法加载性能摘要')
  } finally {
    summaryLoading.value = false
  }
}

async function loadStorage() {
  storageLoading.value = true
  storageError.value = ''
  try {
    const r = await apiFetch<StorageStats>('/admin/performance/storage', { silentToast: true })
    storage.value = r
  } catch (err) {
    const e = err as { data?: unknown, message?: string }
    storageError.value = extractApiErrorMessage(e?.data, e?.message || '无法加载存储统计')
  } finally {
    storageLoading.value = false
  }
}

/** 供 DangerConfirmDialog 调用：throw 则弹窗保持打开并内联展示错误 */
async function runCleanup() {
  const days = clampDays(cleanupDays.value)
  if (days == null) {
    throw new Error('保留天数需为 1–365 之间的整数')
  }
  cleanupRunning.value = true
  try {
    const r = await apiFetch<CleanupResult>('/admin/performance/cleanup', {
      method: 'DELETE',
      query: { days },
      silentToast: true
    })
    toast.success(`已删除 ${r?.deleted_count ?? 0} 条旧记录，剩余 ${r?.remaining_count ?? 0} 条`)
    await Promise.all([loadStorage(), loadSlow()])
  } finally {
    cleanupRunning.value = false
  }
}

const anyLoading = computed(() => summaryLoading.value || slowLoading.value || storageLoading.value)

async function reloadAll() {
  await Promise.all([loadSummary(), loadSlow(), loadStorage()])
}

onMounted(reloadAll)
</script>
