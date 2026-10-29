<!--
  系统监控页：`/api/monitoring/*` 八个只读端点在本仓的唯一消费方（此前八条全部零前端消费者，
  等于"后端有指标、后台看不到"）。三条实现口径：

  1. **分窗口不混读数**。`/performance` 取的是**进程内环形缓冲**（重启清零、无样本时连
     `sample_count` 键都不回），`/performance/summary` 取的是 `visit_logs`（跨重启的历史）。
     两者同屏但分别标注来源，否则"缓冲空 → 0ms"会被读成"全站很快"。
  2. **保留窗口截短的读数标成下界**。`visit_logs` 按 `LOG_RETENTION_DAYS` 自动清理，
     `retention_days < 窗口天数` 时 week/month 只是部分数据，用 `data_since` 说明起点。
  3. **`/database` 的 `database_url` 不上屏**。接口回的是掩码连接串，但掩码不等于可公开：
     渲染出来就会进截图与日志，本页只读 pool 与表行数。
  取数用 `Promise.all` + 逐段 try/catch：单个接口失败只影响自己那块，其余读数照常展示。
-->
<template>
  <div class="flex flex-col gap-5">
    <AdminPageHeader
      title="系统监控"
      description="健康检查、资源占用、访问量与性能指标（后端 /api/monitoring 八个只读接口）"
      :icon="Activity"
    >
      <template #actions>
        <Button
          variant="outline"
          size="sm"
          class="rounded-xl"
          :disabled="loading"
          @click="loadAll()"
        >
          <RefreshCw
            data-icon="inline-start"
            :class="loading ? 'animate-spin' : ''"
          />
          刷新全部
        </Button>
      </template>
    </AdminPageHeader>

    <Alert
      v-if="blockedBy"
      variant="destructive"
      class="rounded-xl"
    >
      <AlertTriangle class="size-4" />
      <AlertTitle>部分监控接口不可用</AlertTitle>
      <AlertDescription class="flex flex-wrap items-center justify-between gap-3">
        <span>{{ blockedBy }}</span>
        <Button
          variant="outline"
          size="sm"
          class="rounded-lg shrink-0"
          :disabled="loading"
          @click="loadAll()"
        >
          <RotateCcw data-icon="inline-start" />
          重试
        </Button>
      </AlertDescription>
    </Alert>

    <!-- 健康总览 -->
    <div class="grid grid-cols-1 gap-4 md:grid-cols-3">
      <AdminCard
        v-for="probe in healthProbes"
        :key="probe.name"
        class="rounded-2xl"
      >
        <div class="flex items-center justify-between gap-3 p-5">
          <div class="flex flex-col gap-1 min-w-0">
            <p class="text-xs text-muted-foreground font-medium uppercase tracking-wide">
              {{ probe.label }}
            </p>
            <p class="text-lg font-bold tracking-tight capitalize">
              {{ probe.status || '—' }}
            </p>
            <p class="text-xs text-muted-foreground truncate">
              {{ probe.detail }}
            </p>
          </div>
          <div
            class="size-10 rounded-xl flex items-center justify-center shrink-0"
            :class="probe.tone"
          >
            <component
              :is="probe.icon"
              class="size-5"
            />
          </div>
        </div>
      </AdminCard>
    </div>

    <!-- 资源占用 -->
    <div class="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-4">
      <StatCard
        title="CPU 占用"
        :value="`${round2(stats?.cpu?.percent)}%`"
        :hint="stats?.cpu?.count ? `${stats.cpu.count} 逻辑核 · psutil 采样` : 'psutil 不可用时恒为 0'"
        :icon="Cpu"
        accent="info"
        :loading="loading && !stats"
      />
      <StatCard
        title="常驻内存 RSS"
        :value="`${round2(stats?.memory?.rss_mb)} MB`"
        :hint="stats?.memory?.percent != null ? `占系统 ${stats.memory.percent}%` : '虚拟内存 ' + round2(stats?.memory?.vms_mb) + ' MB'"
        :icon="MemoryStick"
        accent="primary"
        :loading="loading && !stats"
      />
      <StatCard
        title="运行时长"
        :value="fmtUptime(stats?.uptime_seconds)"
        :hint="`统计截至 ${shortTime(stats?.timestamp)}`"
        :icon="Clock"
        accent="success"
        :loading="loading && !stats"
      />
      <StatCard
        title="缓存后端"
        :value="stats?.cache?.type ?? '—'"
        :hint="stats?.cache?.connected ? '连接正常' : '未连接'"
        :icon="Database"
        accent="warning"
        :loading="loading && !stats"
      />
    </div>

    <!-- 访问量 -->
    <AdminCard class="rounded-2xl">
      <div class="flex flex-col gap-4 p-5">
        <div class="flex items-center justify-between gap-3 flex-wrap">
          <div class="flex items-center gap-3 flex-wrap">
            <h3 class="font-semibold tracking-tight flex items-center gap-2">
              <BarChart3 class="size-4" />
              访问量
            </h3>
            <!-- 明细与 UA 解析在访客记录页（同一族接口，两个页面各取一段） -->
            <NuxtLink
              to="/admin/tools/visits"
              class="text-xs text-primary hover:underline"
            >
              完整访客记录 →
            </NuxtLink>
          </div>
          <p class="text-xs text-muted-foreground">
            今日 {{ fmtNumber(visits?.today) }} · 昨日 {{ fmtNumber(visits?.yesterday) }} ·
            独立 IP（今日）{{ fmtNumber(visits?.unique_ips_today) }} ·
            环比 <span :class="growthTone">{{ fmtGrowth(visits?.growth) }}</span>
          </p>
        </div>

        <div
          v-if="visits?.trend?.length"
          class="flex items-end gap-1.5 h-24"
        >
          <div
            v-for="point in visits.trend"
            :key="point.date"
            class="flex-1 flex flex-col items-center gap-1 min-w-0"
            :title="`${point.date}: ${point.value}`"
          >
            <div
              class="w-full rounded-t-md bg-primary/60"
              :style="{ height: barHeight(point.value) }"
            />
            <span class="text-[10px] text-muted-foreground w-full text-center truncate">
              {{ point.date }}
            </span>
          </div>
        </div>
        <Skeleton
          v-else-if="loading"
          class="h-24 w-full rounded-lg"
        />

        <div class="grid grid-cols-2 gap-3 md:grid-cols-4">
          <MetricCell
            v-for="w in visitWindows"
            :key="w.key"
            :label="w.label"
            :value="w.value"
            :note="w.truncated ? `仅保留 ${visits?.retention_days} 天日志，此为下界（数据始于 ${shortDate(visits?.data_since)}）` : ''"
          />
        </div>
      </div>
    </AdminCard>

    <!-- 性能：进程内缓冲 + 历史窗口两个口径 -->
    <div class="grid grid-cols-1 gap-4 lg:grid-cols-2">
      <AdminCard class="rounded-2xl">
        <div class="flex flex-col gap-4 p-5">
          <div class="flex items-center justify-between gap-3 flex-wrap">
            <h3 class="font-semibold tracking-tight flex items-center gap-2">
              <Timer class="size-4" />
              实时延迟（进程内环形缓冲）
            </h3>
            <div class="flex items-center gap-1">
              <Button
                v-for="p in PERIODS"
                :key="p"
                size="sm"
                variant="ghost"
                class="rounded-lg h-8 text-xs"
                :class="period === p ? 'bg-primary/10 text-primary' : ''"
                @click="setPeriod(p)"
              >
                {{ p }} 分钟
              </Button>
            </div>
          </div>

          <div class="grid grid-cols-2 gap-3 md:grid-cols-4">
            <MetricCell
              v-for="cell in latencyCells"
              :key="cell.label"
              :label="cell.label"
              :value="cell.value"
              unit="ms"
            />
          </div>
          <p class="text-xs text-muted-foreground">
            {{ perfBufferNote }}
          </p>
        </div>
      </AdminCard>

      <AdminCard class="rounded-2xl">
        <div class="flex flex-col gap-4 p-5">
          <h3 class="font-semibold tracking-tight flex items-center gap-2">
            <History class="size-4" />
            历史耗时（来自访问日志，跨重启）
          </h3>
          <div class="flex flex-col gap-2">
            <div
              v-for="row in historyRows"
              :key="row.label"
              class="grid grid-cols-5 gap-2 text-sm tabular-nums items-center"
            >
              <span class="text-muted-foreground text-xs">{{ row.label }}</span>
              <span>均值 {{ round2(row.avg) }} ms</span>
              <span>P95 {{ round2(row.p95) }} ms</span>
              <span>错误 {{ fmtNumber(row.errors) }}</span>
              <span :class="Number(row.error_rate) > 1 ? 'text-destructive' : ''">
                {{ round2(row.error_rate) }}%
              </span>
            </div>
          </div>
          <p class="text-xs text-muted-foreground">
            错误率分母＝窗口内全部请求（含 4xx 快速失败），分子＝状态码 ≥400；耗时样本上限 50000 条。
          </p>
        </div>
      </AdminCard>
    </div>

    <!-- 数据库连接池 -->
    <AdminCard class="rounded-2xl">
      <div class="flex flex-col gap-4 p-5">
        <h3 class="font-semibold tracking-tight flex items-center gap-2">
          <Server class="size-4" />
          数据库连接池与内容量
        </h3>
        <div class="grid grid-cols-2 gap-3 md:grid-cols-4">
          <MetricCell
            label="池大小"
            :value="dbStats?.pool?.size"
          />
          <MetricCell
            label="空闲连接"
            :value="dbStats?.pool?.checked_in"
          />
          <MetricCell
            label="占用连接"
            :value="dbStats?.pool?.checked_out"
          />
          <MetricCell
            label="溢出连接"
            :value="dbStats?.pool?.overflow"
          />
        </div>
        <div class="grid grid-cols-2 gap-3 md:grid-cols-5">
          <MetricCell
            label="用户"
            :value="stats?.database?.users_count"
          />
          <MetricCell
            label="文章总数"
            :value="stats?.database?.posts_count"
            :note="`已发布 ${fmtNumber(stats?.database?.published_posts_count)}`"
          />
          <MetricCell
            label="评论总数"
            :value="stats?.database?.comments_count"
            :note="`可见 ${fmtNumber(stats?.database?.active_comments_count)}`"
          />
          <MetricCell
            label="users 表行数"
            :value="dbStats?.table_sizes?.users"
          />
          <MetricCell
            label="posts 表行数"
            :value="dbStats?.table_sizes?.posts"
          />
        </div>
        <p class="text-[11px] text-muted-foreground">
          接口另回掩码后的连接串，本页刻意不展示——掩码不等于可公开。
        </p>
      </div>
    </AdminCard>

    <!-- 缓存指标 -->
    <AdminCard class="rounded-2xl">
      <div class="flex flex-col gap-4 p-5">
        <h3 class="font-semibold tracking-tight flex items-center gap-2">
          <Layers class="size-4" />
          缓存指标
          <span
            v-if="cacheStats && cacheStats.connected === false"
            class="text-xs font-normal text-destructive"
          >连接失败</span>
        </h3>
        <div class="grid grid-cols-2 gap-3 md:grid-cols-4">
          <MetricCell
            label="键总量"
            :value="cacheStats?.metrics?.total_keys"
          />
          <MetricCell
            label="命中率"
            :value="cacheStats?.metrics?.hit_rate"
            unit="%"
          />
          <MetricCell
            label="内存占用"
            :display="cacheStats?.metrics?.used_memory_human"
          />
          <MetricCell
            label="客户端数"
            :value="cacheStats?.metrics?.connected_clients"
          />
        </div>
        <p
          v-if="cacheStats?.error"
          class="text-xs text-destructive"
        >
          {{ cacheStats.error }}
        </p>
        <p
          v-else-if="cacheStats?.type === 'memory'"
          class="text-xs text-muted-foreground"
        >
          Memory 后端没有跨进程指标，以上为占位 0，不代表命中率真的是 0%。
        </p>
      </div>
    </AdminCard>

    <!-- 趋势 -->
    <AdminCard class="rounded-2xl">
      <div class="flex flex-col gap-4 p-5">
        <div class="flex items-center justify-between gap-3 flex-wrap">
          <h3 class="font-semibold tracking-tight flex items-center gap-2">
            <TrendingUp class="size-4" />
            新增趋势
          </h3>
          <div class="flex items-center gap-1">
            <Button
              v-for="d in TREND_DAYS"
              :key="d"
              size="sm"
              variant="ghost"
              class="rounded-lg h-8 text-xs"
              :class="trendDays === d ? 'bg-primary/10 text-primary' : ''"
              @click="setTrendDays(d)"
            >
              {{ d }} 天
            </Button>
          </div>
        </div>
        <div
          v-for="series in trendSeries"
          :key="series.name"
          class="flex items-center gap-3"
        >
          <span class="w-14 text-xs text-muted-foreground shrink-0">{{ series.label }}</span>
          <div class="flex-1 flex items-end gap-0.5 h-10">
            <div
              v-for="point in series.points"
              :key="point.date"
              class="flex-1 rounded-t bg-primary/40"
              :style="{ height: seriesHeight(point.count, series.max) }"
              :title="`${point.date}: ${point.count}`"
            />
          </div>
          <span class="w-16 text-xs tabular-nums text-right shrink-0">{{ fmtNumber(series.total) }}</span>
        </div>
      </div>
    </AdminCard>
  </div>
</template>

<script setup lang="ts">
import { apiFetch } from '~~/composables/useApi'
import { extractApiErrorMessage } from '~~/lib/utils'
import {
  Activity, AlertTriangle, BarChart3, Clock, Cpu, Database, HeartPulse, History,
  Layers, MemoryStick, RefreshCw, RotateCcw, Server, Timer, TrendingUp
} from '@lucide/vue'

definePageMeta({ ssr: false, layout: 'admin' })

/** 静默轮询间隔：与缓存管理页同口径——够快看到趋势，又不给日志表加压。 */
const POLL_MS = 30_000
const PERIODS = [5, 15, 60] as const
const TREND_DAYS = [7, 14, 30] as const

type DayCount = { date: string, count: number }
type Section<T> = { data: T | null, error: string }

/**
 * 八个端点各自的响应形状。类型必须写成具名 type 而不是内联在 `ref<...>` 里，
 * 因为下面的 `section<XxxShape>()` 要用同一个实参：不传实参时 `T` 推断成 `unknown`，
 * `x.data` 赋给 typed ref 就是 8 条 TS2322。
 */
type HealthShape = { status?: string, checks?: Record<string, { status?: string, error?: string, latency_ms?: number }> }
type StatsShape = {
  cpu?: { percent?: number, count?: number }
  memory?: { rss_mb?: number, vms_mb?: number, percent?: number }
  uptime_seconds?: number
  timestamp?: string
  cache?: { type?: string, connected?: boolean }
  database?: { users_count?: number, posts_count?: number, published_posts_count?: number, comments_count?: number, active_comments_count?: number }
}
type VisitsShape = {
  total?: number
  today?: number
  yesterday?: number
  week?: number
  month?: number
  unique_ips_today?: number
  growth?: number
  retention_days?: number
  data_since?: string | null
  trend?: { date: string, value: number }[]
}
type LatencyShape = {
  avg_latency?: number
  p50_latency?: number
  p95_latency?: number
  p99_latency?: number
  requests_per_minute?: number
  sample_count?: number
  error_count?: number
  window_requests?: number
  error_rate?: number
}
type PerfSummaryShape = Partial<Record<'last_24h' | 'last_7d', {
  avg_response_time_ms?: number
  p95_response_time_ms?: number
  error_count?: number
  error_rate?: number
}>>
type DbShape = { pool?: { size?: number, checked_in?: number, checked_out?: number, overflow?: number }, table_sizes?: Record<string, number> }
type CacheShape = {
  type?: string
  connected?: boolean
  error?: string
  metrics?: { total_keys?: number, hit_rate?: number, used_memory_human?: string, connected_clients?: number }
}
type TrendsShape = { posts?: DayCount[], comments?: DayCount[], users?: DayCount[], visits?: DayCount[] }

const loading = ref(false)
const blockedBy = ref('')
const period = ref<number>(15)
const trendDays = ref<number>(7)

const health = ref<null | HealthShape>(null)
const stats = ref<null | StatsShape>(null)
const visits = ref<null | VisitsShape>(null)
const latency = ref<null | LatencyShape>(null)
const perfSummary = ref<null | PerfSummaryShape>(null)
const dbStats = ref<null | DbShape>(null)
const cacheStats = ref<null | CacheShape>(null)
const trends = ref<null | TrendsShape>(null)

const healthProbes = computed(() => {
  const checks = health.value?.checks ?? {}
  const tone = (s?: string) =>
    s === 'healthy'
      ? 'bg-success-muted text-success-muted-foreground'
      : s === 'degraded'
        ? 'bg-warning-muted text-warning-muted-foreground'
        : 'bg-destructive/15 text-destructive'
  return [
    {
      name: 'overall',
      label: '整体健康',
      status: health.value?.status,
      detail: health.value ? '数据库 + 缓存真实探测' : '接口不可用',
      icon: HeartPulse,
      tone: tone(health.value?.status)
    },
    {
      name: 'database',
      label: '数据库',
      status: checks.database?.status,
      detail: checks.database?.error ?? 'SELECT 1 往返',
      icon: Database,
      tone: tone(checks.database?.status)
    },
    {
      name: 'cache',
      label: '缓存',
      status: checks.cache?.status,
      detail: checks.cache?.error ?? '写入再读回',
      icon: Layers,
      tone: tone(checks.cache?.status)
    }
  ]
})

const visitWindows = computed(() => {
  const retention = visits.value?.retention_days ?? null
  const truncated = (days: number) => retention !== null && retention < days
  return [
    { key: 'today', label: '今日', value: visits.value?.today, truncated: false },
    { key: 'week', label: '近 7 天', value: visits.value?.week, truncated: truncated(7) },
    { key: 'month', label: '近 30 天', value: visits.value?.month, truncated: truncated(30) },
    { key: 'total', label: '累计', value: visits.value?.total, truncated: false }
  ]
})

const growthTone = computed(() => {
  const g = Number(visits.value?.growth ?? 0)
  return g > 0 ? 'text-success' : g < 0 ? 'text-destructive' : 'text-muted-foreground'
})

const latencyCells = computed(() => [
  { label: '平均', value: latency.value?.avg_latency },
  { label: 'P50', value: latency.value?.p50_latency },
  { label: 'P95', value: latency.value?.p95_latency },
  { label: 'P99', value: latency.value?.p99_latency }
])

/** 环形缓冲为空时后端连 `sample_count` 键都不回——用键存在性区分"没样本"与"0ms"。 */
const perfBufferNote = computed(() => {
  if (!latency.value) return '延迟接口不可用'
  if (latency.value.sample_count === undefined) {
    return '窗口内进程没采到样本（环形缓冲不落盘、重启即清零），以上延迟读数不适用。'
  }
  return `样本 ${fmtNumber(latency.value.sample_count)} 条 · ${round2(latency.value.requests_per_minute)} 请求/分钟 · 错误率 ${round2(latency.value.error_rate)}%（错误率取自访问日志，与缓冲不同源）`
})

const historyRows = computed(() => {
  const h = perfSummary.value?.last_24h
  const d = perfSummary.value?.last_7d
  return [
    { label: '24 小时', avg: h?.avg_response_time_ms, p95: h?.p95_response_time_ms, errors: h?.error_count, error_rate: h?.error_rate },
    { label: '7 天', avg: d?.avg_response_time_ms, p95: d?.p95_response_time_ms, errors: d?.error_count, error_rate: d?.error_rate }
  ]
})

const trendSeries = computed(() => {
  const defs = [
    { name: 'posts', label: '文章', rows: trends.value?.posts ?? [] },
    { name: 'comments', label: '评论', rows: trends.value?.comments ?? [] },
    { name: 'users', label: '用户', rows: trends.value?.users ?? [] },
    { name: 'visits', label: '访问', rows: trends.value?.visits ?? [] }
  ]
  return defs.map(d => ({
    name: d.name,
    label: d.label,
    points: d.rows,
    total: d.rows.reduce((a, b) => a + (b.count ?? 0), 0),
    max: Math.max(1, ...d.rows.map(r => r.count ?? 0))
  }))
})

function seriesHeight(count: number, max: number) {
  return `${Math.max(2, Math.round(((count ?? 0) / max) * 100))}%`
}
const trendMax = computed(() => Math.max(1, ...(visits.value?.trend ?? []).map(t => t.value ?? 0)))
function barHeight(value: number) {
  return `${Math.max(2, Math.round(((value ?? 0) / trendMax.value) * 100))}%`
}

function fmtNumber(v: unknown) {
  if (v === null || v === undefined || v === '') return '—'
  const n = Number(v)
  return Number.isFinite(n) ? n.toLocaleString('zh-CN') : String(v)
}
function round2(v: unknown) {
  const n = Number(v)
  return Number.isFinite(n) ? Math.round(n * 100) / 100 : '—'
}
function fmtGrowth(v: unknown) {
  const n = Number(v)
  if (!Number.isFinite(n)) return '—'
  return `${n > 0 ? '+' : ''}${Math.round(n * 10) / 10}%`
}
function fmtUptime(seconds: unknown) {
  const n = Number(seconds)
  if (!Number.isFinite(n) || n <= 0) return '—'
  const d = Math.floor(n / 86400)
  const h = Math.floor((n % 86400) / 3600)
  const m = Math.floor((n % 3600) / 60)
  return d > 0 ? `${d} 天 ${h} 小时` : h > 0 ? `${h} 小时 ${m} 分` : `${m} 分`
}
function shortTime(iso?: string) {
  if (!iso) return '—'
  const d = new Date(iso)
  return Number.isNaN(d.getTime()) ? '—' : d.toLocaleTimeString('zh-CN', { hour12: false })
}
function shortDate(iso?: string | null) {
  if (!iso) return '—'
  const d = new Date(iso)
  return Number.isNaN(d.getTime()) ? '—' : d.toLocaleDateString('zh-CN')
}

/** 单段取数：失败只落到自己那一段的错误串，不把整页读数清空。 */
async function section<T>(path: string): Promise<Section<T>> {
  try {
    const data = await apiFetch<T>(path, { silentToast: true })
    return { data: (data ?? null) as T | null, error: '' }
  } catch (error) {
    return { data: null, error: extractApiErrorMessage(error, `${path} 获取失败`) }
  }
}

async function loadAll(silent = false) {
  if (!silent) loading.value = true
  const results = await Promise.all([
    section<HealthShape>('/monitoring/health'),
    section<StatsShape>('/monitoring/stats'),
    section<VisitsShape>('/monitoring/visits/summary'),
    section<LatencyShape>(`/monitoring/performance?period=${period.value}`),
    section<PerfSummaryShape>('/monitoring/performance/summary'),
    section<DbShape>('/monitoring/database'),
    section<CacheShape>('/monitoring/cache'),
    section<TrendsShape>(`/monitoring/trends?days=${trendDays.value}`)
  ])
  const [h, s, v, l, ps, db, cs, tr] = results

  if (!h.error) health.value = h.data
  if (!s.error) stats.value = s.data
  if (!v.error) visits.value = v.data
  if (!l.error) latency.value = l.data
  if (!ps.error) perfSummary.value = ps.data
  if (!db.error) dbStats.value = db.data
  if (!cs.error) cacheStats.value = cs.data
  if (!tr.error) trends.value = tr.data

  blockedBy.value = results.map(r => r.error).filter(Boolean).join('；')
  loading.value = false
}

async function setPeriod(p: number) {
  period.value = p
  await loadAll(true)
}
async function setTrendDays(d: number) {
  trendDays.value = d
  await loadAll(true)
}

let timer: ReturnType<typeof setInterval> | undefined
onMounted(() => {
  loadAll()
  timer = setInterval(() => {
    if (document.visibilityState === 'visible') loadAll(true)
  }, POLL_MS)
})
onUnmounted(() => {
  if (timer) clearInterval(timer)
})
</script>
