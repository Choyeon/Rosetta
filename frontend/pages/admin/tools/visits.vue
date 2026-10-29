<!--
  访客记录页：完整访问明细（真实来源 IP + UA 派生的系统/浏览器/设备 + Cookie 名称 + 语言 + 登录身份）
  与原「查看访问量」汇总同屏，是仪表盘 PV/UV 卡片「访客记录」入口的落地页。

  契约（缺任何一条都会让这页给出误导性的读数）：
  * `/monitoring/visits` 与 `/monitoring/visits/summary` 都**不套 {success,data} 信封**，直接取裸对象。
  * 一行记录是不是"真人"取决于两件事：`TRUSTED_PROXY_IPS` 有没有把 nginx 那台列为受信
    （决定 X-Forwarded-For 能不能采信，uvicorn 的 --proxy-headers 关掉时全靠它），以及
    采集口是否跳过了"受信对端 + 不带任何转发头"的本机服务直连。生产实测未跳时
    8.4 万条里 8.3 万条是 Nitro SSR 自己打 127.0.0.1:8000 取设置/主题/导航，
    这页看到的"访客"就是自家 SSR。所以页内按"当前这批记录是否全是回环"给显式告警。
  * os/browser/device/bot_name 是**读取时按当前规则现算**的标签（原始 UA 也随行返回供人工复核）；
    `is_bot` 是唯一落库的判定，历史行为 null 表示"未判定"，两档筛选都不含它 —— 显示要单独分一档。
  * `cookie_names` 只有名字，永远没有值（值是会话凭证，不落遥测、不上屏）。
  * `retention_days < days` 时窗口读数只是**下界**，必须与 `data_since` 一起标注，不能当全量。
  * 筛选条件点「应用筛选」才生效且必须把页码重置回 1（否则结果集变小后停在越界页码拿到空列表）。
-->
<template>
  <div class="flex flex-col gap-5">
    <AdminPageHeader
      title="访客记录"
      description="完整访问明细与访问量汇总（后端 /api/monitoring/visits）"
      :icon="Users"
    >
      <template #actions>
        <Button
          variant="outline"
          class="rounded-xl"
          @click="goMonitoring"
        >
          <Activity data-icon="inline-start" />
          系统监控
        </Button>
        <Button
          variant="outline"
          class="rounded-xl"
          :disabled="loading"
          @click="reloadAll"
        >
          <RefreshCw
            data-icon="inline-start"
            :class="loading ? 'animate-spin' : ''"
          />
          刷新
        </Button>
      </template>
    </AdminPageHeader>

    <Alert
      v-if="summaryError"
      variant="destructive"
      class="rounded-xl"
    >
      <AlertTriangle class="size-4" />
      <AlertTitle>访问量汇总获取失败</AlertTitle>
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

    <!-- 访问量：原「查看访问量」入口的内容搬到这里 -->
    <AdminCard>
      <div class="flex flex-col gap-1.5 mb-4">
        <h3 class="text-base font-semibold">
          访问量
        </h3>
        <p class="text-sm text-muted-foreground">
          今日 {{ fmt(summary?.today) }} · 昨日 {{ fmt(summary?.yesterday) }} ·
          独立 IP（今日）{{ fmt(summary?.unique_ips_today) }} ·
          环比 <span :class="growthTone">{{ fmtGrowth(summary?.growth) }}</span>
          <template v-if="summary?.data_since">
            · 数据始于 {{ shortDate(summary.data_since) }}
          </template>
        </p>
      </div>
      <div
        v-if="summaryLoading && !summary"
        class="grid grid-cols-2 md:grid-cols-4 gap-4"
      >
        <Skeleton
          v-for="i in 4"
          :key="i"
          class="h-20 rounded-xl"
        />
      </div>
      <div
        v-else
        class="flex flex-col gap-5"
      >
        <div class="grid grid-cols-2 md:grid-cols-4 gap-4">
          <div
            v-for="w in windows"
            :key="w.key"
            class="flex flex-col gap-1 rounded-xl border border-border bg-muted/30 p-4"
          >
            <span class="text-xs text-muted-foreground uppercase tracking-wide">{{ w.label }}</span>
            <span class="text-xl font-bold tabular-nums">{{ fmt(w.value) }}</span>
            <span
              v-if="w.truncated"
              class="text-[11px] text-warning"
            >
              仅保留 {{ summary?.retention_days }} 天日志，此为下界
            </span>
          </div>
        </div>
        <div
          v-if="summary?.trend?.length"
          class="flex items-end gap-2 h-32 rounded-xl border border-border/60 bg-muted/20 p-4 pb-2"
        >
          <div
            v-for="point in summary.trend"
            :key="point.date"
            class="flex-1 h-full flex flex-col items-center justify-end gap-1 group min-w-0"
          >
            <span class="text-[10px] tabular-nums text-muted-foreground opacity-0 group-hover:opacity-100 transition-opacity">
              {{ fmt(point.value) }}
            </span>
            <div
              class="w-full max-w-10 rounded-t-md bg-primary/60 group-hover:bg-primary transition-colors"
              :style="{ height: `${barHeight(point.value)}%` }"
              :title="`${point.date} · ${fmt(point.value)} 次访问`"
            />
            <span class="text-[10px] text-muted-foreground tabular-nums shrink-0">{{ point.date }}</span>
          </div>
        </div>
      </div>
    </AdminCard>

    <Alert
      v-if="loopbackOnly"
      variant="info"
      class="rounded-xl"
    >
      <Info class="size-4" />
      <AlertTitle>这批记录的来源 IP 全是回环地址</AlertTitle>
      <AlertDescription>
        整页读成 <code class="font-mono">127.0.0.1</code> 通常有两种成因：
        <strong>①本机服务直连被当成了访客</strong>——Nitro SSR 渲染时打
        <code class="font-mono">127.0.0.1:8000</code> 取设置/主题/导航，这类请求不带转发头，
        配好 <code class="font-mono">TRUSTED_PROXY_IPS</code> 后采集口会把它们整体跳过；
        <strong>②反代递来的 <code class="font-mono">X-Forwarded-For</code> 没被采信</strong>——后端只在直连对端属于
        <code class="font-mono">TRUSTED_PROXY_IPS</code> 时才读它。
        两种都由同一步解决：在生产 <code class="font-mono">.env</code> 里把反代所在地址加入
        <code class="font-mono">TRUSTED_PROXY_IPS</code>（例如 <code class="font-mono">127.0.0.1</code>）并重启后端；
        已有的历史行不会回填。
      </AlertDescription>
    </Alert>

    <AdminCard class="overflow-hidden">
      <div class="flex flex-wrap items-end gap-3 px-5 pt-5 pb-4">
        <div class="flex flex-col gap-1.5 flex-1 min-w-0">
          <h3 class="text-base font-semibold">
            访问明细
          </h3>
          <p class="text-sm text-muted-foreground">
            命中 {{ fmt(list?.total) }} 条 · 独立 IP {{ fmt(list?.unique_ips) }} ·
            机器流量 {{ fmt(list?.bot_total) }}
            <template v-if="list?.window_truncated">
              · 窗口被保留策略截短，当前为下界
            </template>
          </p>
        </div>
        <div class="flex flex-wrap items-end gap-2">
          <div class="flex flex-col gap-1">
            <Label
              for="visit-days"
              class="text-xs text-muted-foreground"
            >
              窗口
            </Label>
            <Select v-model="draftDays">
              <SelectTrigger
                id="visit-days"
                class="w-28 rounded-xl"
              >
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem
                  v-for="d in dayOptions"
                  :key="d"
                  :value="d"
                >
                  近 {{ d }} 天
                </SelectItem>
              </SelectContent>
            </Select>
          </div>
          <div class="flex flex-col gap-1">
            <Label
              for="visit-kind"
              class="text-xs text-muted-foreground"
            >
              流量类型
            </Label>
            <Select v-model="draftKind">
              <SelectTrigger
                id="visit-kind"
                class="w-32 rounded-xl"
              >
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem
                  v-for="k in kindOptions"
                  :key="k.value"
                  :value="k.value"
                >
                  {{ k.label }}
                </SelectItem>
              </SelectContent>
            </Select>
          </div>
          <div class="flex flex-col gap-1">
            <Label
              for="visit-ip"
              class="text-xs text-muted-foreground"
            >
              IP 包含
            </Label>
            <Input
              id="visit-ip"
              v-model="draftIp"
              class="w-40 rounded-xl font-mono text-xs"
              placeholder="203.0.113"
            />
          </div>
          <div class="flex flex-col gap-1">
            <Label
              for="visit-path"
              class="text-xs text-muted-foreground"
            >
              路径包含
            </Label>
            <Input
              id="visit-path"
              v-model="draftPath"
              class="w-40 rounded-xl font-mono text-xs"
              placeholder="/posts/"
            />
          </div>
          <div class="flex flex-col gap-1">
            <Label
              for="visit-status"
              class="text-xs text-muted-foreground"
            >
              状态码
            </Label>
            <Input
              id="visit-status"
              v-model="draftStatus"
              class="w-24 rounded-xl"
              type="number"
              placeholder="200"
            />
          </div>
          <Button
            class="rounded-xl"
            :disabled="loading"
            @click="applyFilters"
          >
            <Search data-icon="inline-start" />
            应用筛选
          </Button>
          <Button
            variant="ghost"
            class="rounded-xl"
            :disabled="loading"
            @click="resetFilters"
          >
            <RotateCcw data-icon="inline-start" />
            重置
          </Button>
        </div>
      </div>

      <div class="p-0">
        <div
          v-if="listError"
          class="p-12"
        >
          <Alert
            variant="destructive"
            class="rounded-xl max-w-lg mx-auto"
          >
            <AlertTriangle class="size-4" />
            <AlertTitle>访客记录获取失败</AlertTitle>
            <AlertDescription class="flex flex-wrap items-center justify-between gap-3">
              <span>{{ listError }}</span>
              <Button
                variant="outline"
                size="sm"
                class="rounded-lg shrink-0"
                :disabled="loading"
                @click="loadList"
              >
                <RotateCcw data-icon="inline-start" />
                重试
              </Button>
            </AlertDescription>
          </Alert>
        </div>
        <div
          v-else-if="!loading && rows.length === 0"
          class="p-12"
        >
          <Alert
            variant="info"
            class="rounded-xl max-w-lg mx-auto"
          >
            <Info class="size-4" />
            <AlertTitle>当前条件下没有访问记录</AlertTitle>
            <AlertDescription>
              访问日志由中间件写入内存队列、后台每 5 秒批量落库，刚产生的访问可能还在队列里；
              也可能窗口太短或筛选过严。
            </AlertDescription>
          </Alert>
        </div>
        <div
          v-else
          class="overflow-x-auto"
        >
          <AdminDataTable
            :columns="columns"
            :data="rows"
            :loading="loading"
            row-key="id"
          >
            <template #cell-when="{ row }">
              <span class="text-xs tabular-nums whitespace-nowrap">
                {{ formatAdminDateTime((row as VisitItem).created_at) }}
              </span>
            </template>
            <template #cell-path="{ row }">
              <div class="flex items-center gap-2 min-w-0">
                <Badge
                  :class="methodClass((row as VisitItem).method)"
                  class="rounded-lg text-[10px] uppercase tracking-wide border-transparent shrink-0"
                >
                  {{ (row as VisitItem).method }}
                </Badge>
                <span
                  class="font-mono text-xs block max-w-[320px] truncate"
                  :title="(row as VisitItem).path"
                >
                  {{ (row as VisitItem).path }}
                </span>
              </div>
            </template>
            <template #cell-ip="{ row }">
              <span
                class="text-xs tabular-nums font-mono"
                :class="(row as VisitItem).ip ? '' : 'text-muted-foreground'"
              >
                {{ (row as VisitItem).ip || '未记录' }}
              </span>
            </template>
            <template #cell-client="{ row }">
              <div class="flex flex-wrap items-center gap-1.5">
                <span
                  v-if="(row as VisitItem).is_bot"
                  class="flex items-center gap-1 text-xs text-muted-foreground"
                >
                  <Bot class="size-3.5" />
                  {{ (row as VisitItem).bot_name || '机器流量' }}
                </span>
                <template v-else>
                  <span class="flex items-center gap-1 text-xs">
                    <component
                      :is="deviceIcon((row as VisitItem).device)"
                      class="size-3.5 text-muted-foreground"
                    />
                    {{ osLabel(row as VisitItem) }}
                  </span>
                  <span class="text-xs text-muted-foreground">
                    {{ browserLabel(row as VisitItem) }}
                  </span>
                </template>
                <span
                  v-if="(row as VisitItem).is_bot === null"
                  class="text-[10px] text-muted-foreground"
                  title="该列上线前的历史行，未做机器人判定"
                >
                  未判定
                </span>
              </div>
            </template>
            <template #cell-visitor="{ row }">
              <span
                v-if="(row as VisitItem).username"
                class="flex items-center gap-1 text-xs"
              >
                <User class="size-3.5" />
                {{ (row as VisitItem).username }}
              </span>
              <span
                v-else-if="(row as VisitItem).user_id"
                class="text-xs text-muted-foreground font-mono"
              >
                id={{ (row as VisitItem).user_id }}
              </span>
              <span
                v-else
                class="text-xs text-muted-foreground"
              >
                匿名
              </span>
            </template>
            <template #cell-status_code="{ row }">
              <span
                class="tabular-nums text-xs font-medium"
                :class="statusClass((row as VisitItem).status_code)"
              >
                {{ (row as VisitItem).status_code }}
              </span>
            </template>
            <template #cell-duration="{ row }">
              <span class="tabular-nums text-xs">
                {{ (row as VisitItem).response_time_ms }} ms
              </span>
            </template>
            <template #actions="{ row }">
              <Button
                variant="ghost"
                size="icon-sm"
                title="查看这条记录的原始信息"
                aria-label="查看原始信息"
                @click="openDetail(row as VisitItem)"
              >
                <FileSearch data-icon="inline-start" />
              </Button>
            </template>
          </AdminDataTable>
        </div>

        <div
          v-if="rows.length > 0"
          class="p-4 pt-0 mt-2"
        >
          <AdminPagination
            v-model:page="page"
            v-model:page-size="pageSize"
            :total="list?.total ?? 0"
            :page-size-options="[20, 50, 100]"
            unit="条记录"
          />
        </div>
      </div>
    </AdminCard>

    <Dialog v-model:open="detailOpen">
      <DialogContent class="max-w-xl">
        <DialogHeader>
          <DialogTitle>原始访问信息</DialogTitle>
          <DialogDescription>
            系统/浏览器/设备是按当前规则现算的标签，下面是这条记录里真正存下来的字段。
          </DialogDescription>
        </DialogHeader>
        <div
          v-if="detail"
          class="flex flex-col gap-3 text-sm"
        >
          <div
            v-for="f in detailFields"
            :key="f.label"
            class="grid grid-cols-[110px_1fr] gap-3 items-start"
          >
            <span class="text-xs text-muted-foreground uppercase tracking-wide pt-0.5">{{ f.label }}</span>
            <span class="break-all font-mono text-xs leading-relaxed">{{ f.value }}</span>
          </div>
          <Separator />
          <p class="text-xs text-muted-foreground">
            Cookie 只记录名称，不记录值：值是会话凭证，不落遥测表也不上屏。
          </p>
        </div>
        <DialogFooter>
          <Button
            variant="outline"
            class="rounded-xl"
            @click="detailOpen = false"
          >
            关闭
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { apiFetch } from '~~/composables/useApi'
import { formatAdminDateTime } from '~~/composables/useAdminManage'
import { extractApiErrorMessage } from '~~/lib/utils'
import {
  Users, Activity, RefreshCw, RotateCcw, Search, Info, AlertTriangle,
  Monitor, Smartphone, Tablet, Bot, User, FileSearch
} from '@lucide/vue'
import { Button } from '~~/components/ui/button'
import AdminCard from '~~/components/admin/AdminCard.vue'
import AdminPageHeader from '~~/components/admin/AdminPageHeader.vue'
import AdminDataTable from '~~/components/admin/AdminDataTable.vue'
import AdminPagination from '~~/components/admin/AdminPagination.vue'
import { Badge } from '~~/components/ui/badge'
import { Skeleton } from '~~/components/ui/skeleton'
import { Separator } from '~~/components/ui/separator'
import { Input } from '~~/components/ui/input'
import { Label } from '~~/components/ui/label'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '~~/components/ui/select'
import { Alert, AlertDescription, AlertTitle } from '~~/components/ui/alert'
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from '~~/components/ui/dialog'
import type { AdminColumn as Column } from '~~/types/admin'

definePageMeta({ ssr: false, layout: 'admin' })

interface TrendPoint {
  date: string
  value: number
}

interface SummaryBody {
  total: number
  today: number
  yesterday: number
  week: number
  month: number
  unique_ips_today: number
  trend: TrendPoint[]
  growth: number
  retention_days: number
  data_since: string | null
}

interface VisitItem {
  id: number
  path: string
  method: string
  ip: string | null
  user_agent: string | null
  referer: string | null
  status_code: number
  response_time_ms: number
  created_at: string
  user_id: number | null
  username: string | null
  cookie_names: string | null
  accept_language: string | null
  is_bot: boolean | null
  os: string
  os_version: string
  browser: string
  browser_version: string
  device: string
  bot_name: string
}

interface ListBody {
  items: VisitItem[]
  total: number
  page: number
  page_size: number
  days: number
  unique_ips: number
  bot_total: number
  retention_days: number
  data_since: string | null
  window_truncated: boolean
}

// ── 访问量汇总 ──
const summary = ref<SummaryBody | null>(null)
const summaryLoading = ref(true)
const summaryError = ref('')

async function loadSummary() {
  summaryLoading.value = true
  summaryError.value = ''
  try {
    summary.value = await apiFetch<SummaryBody>('/monitoring/visits/summary', { silentToast: true })
  } catch (err) {
    const e = err as { data?: unknown, message?: string }
    summaryError.value = extractApiErrorMessage(e?.data, e?.message || '无法加载访问量')
  } finally {
    summaryLoading.value = false
  }
}

const windows = computed(() => {
  const s = summary.value
  const retention = s?.retention_days ?? 0
  // 保留窗口比统计窗口短 = 老数据已被删，这个读数只是下界
  const truncated = (days: number) => retention > 0 && retention < days
  return [
    { key: 'today', label: '今日', value: s?.today, truncated: false },
    { key: 'week', label: '近 7 天', value: s?.week, truncated: truncated(7) },
    { key: 'month', label: '近 30 天', value: s?.month, truncated: truncated(30) },
    { key: 'total', label: '累计', value: s?.total, truncated: false }
  ]
})

const trendMax = computed(() =>
  Math.max(1, ...(summary.value?.trend ?? []).map(p => Number(p.value) || 0))
)

function barHeight(value: number): number {
  return Math.max(3, Math.round((Number(value) || 0) / trendMax.value * 100))
}

const growthTone = computed(() => {
  const g = Number(summary.value?.growth ?? 0)
  if (g > 0.5) return 'text-success'
  if (g < -0.5) return 'text-error'
  return 'text-muted-foreground'
})

// ── 明细列表 ──
const dayOptions = ['1', '7', '30', '90']
const kindOptions = [
  { value: 'all', label: '全部流量' },
  { value: 'human', label: '仅真人' },
  { value: 'bot', label: '仅机器' }
]

const draftDays = ref('7')
const draftKind = ref('all')
const draftIp = ref('')
const draftPath = ref('')
const draftStatus = ref('')

const applied = ref({ days: '7', kind: 'all', ip: '', path: '', status: '' })

const rows = ref<VisitItem[]>([])
const list = ref<ListBody | null>(null)
const loading = ref(true)
const listError = ref('')
const page = ref(1)
const pageSize = ref(50)

const columns: Column[] = [
  { key: 'when', title: '时间' },
  { key: 'path', title: '路径' },
  { key: 'ip', title: '来源 IP' },
  { key: 'client', title: '客户端' },
  { key: 'visitor', title: '身份' },
  { key: 'status_code', title: '状态', align: 'right' },
  { key: 'duration', title: '耗时', align: 'right' }
]

async function loadList() {
  loading.value = true
  listError.value = ''
  const query: Record<string, string | number> = {
    days: Number(applied.value.days),
    kind: applied.value.kind,
    page: page.value,
    page_size: pageSize.value
  }
  if (applied.value.ip) query.ip = applied.value.ip
  if (applied.value.path) query.path = applied.value.path
  if (applied.value.status) query.status = Number(applied.value.status)
  try {
    const body = await apiFetch<ListBody>('/monitoring/visits', { query, silentToast: true })
    list.value = body
    rows.value = Array.isArray(body?.items) ? body.items : []
  } catch (err) {
    rows.value = []
    list.value = null
    const e = err as { data?: unknown, message?: string }
    listError.value = extractApiErrorMessage(e?.data, e?.message || '无法加载访客记录')
  } finally {
    loading.value = false
  }
}

function applyFilters() {
  applied.value = {
    days: draftDays.value,
    kind: draftKind.value,
    ip: draftIp.value.trim(),
    path: draftPath.value.trim(),
    status: draftStatus.value.trim()
  }
  // 结果集可能缩小，留在旧页码会拿到空列表
  page.value = 1
  loadList()
}

function resetFilters() {
  draftDays.value = '7'
  draftKind.value = 'all'
  draftIp.value = ''
  draftPath.value = ''
  draftStatus.value = ''
  applyFilters()
}

/** 当前这批记录是否全是回环地址（含未记录）——是就说明转发头没被采信 */
const loopbackOnly = computed(() => {
  if (rows.value.length === 0) return false
  return rows.value.every(r => !r.ip || /^(127\.|::1|localhost)/.test(r.ip))
})

const detailOpen = ref(false)
const detail = ref<VisitItem | null>(null)

function openDetail(row: VisitItem) {
  detail.value = row
  detailOpen.value = true
}

const detailFields = computed(() => {
  const d = detail.value
  if (!d) return []
  return [
    { label: '时间', value: formatAdminDateTime(d.created_at) },
    { label: '请求', value: `${d.method} ${d.path} → ${d.status_code} (${d.response_time_ms} ms)` },
    { label: '来源 IP', value: d.ip || '未记录' },
    { label: 'User-Agent', value: d.user_agent || '（空）' },
    { label: '判定', value: d.is_bot === null ? '未判定（历史行）' : d.is_bot ? `机器：${d.bot_name}` : '真人' },
    { label: '设备/系统', value: `${d.device} · ${osLabel(d)} · ${browserLabel(d)}` },
    { label: '来源页', value: d.referer || '（直接访问）' },
    { label: 'Cookie 名', value: d.cookie_names || '（无）' },
    { label: 'Accept-Language', value: d.accept_language || '（未发送）' },
    { label: '登录身份', value: d.username || (d.user_id ? `id=${d.user_id}` : '匿名') },
    { label: '记录 ID', value: String(d.id) }
  ]
})

function osLabel(row: VisitItem): string {
  return row.os_version ? `${row.os} ${row.os_version}` : row.os
}

function browserLabel(row: VisitItem): string {
  return row.browser_version ? `${row.browser} ${row.browser_version}` : row.browser
}

function deviceIcon(device: string) {
  if (device === 'mobile') return Smartphone
  if (device === 'tablet') return Tablet
  if (device === 'bot') return Bot
  return Monitor
}

function methodClass(m: string): string {
  const up = (m || '').toUpperCase()
  if (up === 'POST') return 'bg-warning-muted text-warning-muted-foreground'
  if (up === 'PUT') return 'bg-info-muted text-info-muted-foreground'
  if (up === 'DELETE') return 'bg-error-muted text-error-muted-foreground'
  return 'bg-success-muted text-success-muted-foreground'
}

function statusClass(code: number): string {
  if (code >= 500) return 'text-error'
  if (code >= 400) return 'text-warning'
  return 'text-muted-foreground'
}

function fmt(v: number | null | undefined): string {
  return Number(v ?? 0).toLocaleString('zh-CN')
}

function fmtGrowth(v: number | null | undefined): string {
  const g = Number(v ?? 0)
  return `${g >= 0 ? '+' : ''}${g.toFixed(1)}%`
}

function shortDate(iso: string | null | undefined): string {
  if (!iso) return '-'
  return iso.slice(0, 10)
}

watch([page, pageSize], () => {
  loadList()
})

async function reloadAll() {
  await Promise.all([loadSummary(), loadList()])
}

function goMonitoring() {
  navigateTo('/admin/tools/monitoring')
}

onMounted(reloadAll)
</script>
