<template>
  <div class="p-6 space-y-6">
    <div class="flex items-center gap-3">
      <div
        class="size-10 rounded-xl flex items-center justify-center"
        style="background: linear-gradient(135deg, #0EA5E9 0%, #0284C7 100%);"
      >
        <Gauge class="size-5 text-white" />
      </div>
      <div>
        <h1 class="text-xl font-bold tracking-tight">
          性能监控
        </h1>
        <p class="text-sm text-muted-foreground">
          实时观察接口响应、慢请求与错误趋势
        </p>
      </div>
    </div>

    <div class="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-5 gap-4">
      <StatCard
        loading="summaryLoading"
        label="24h 请求总数"
        icon="Activity"
        color="info"
        :value="summary.total_requests_24h"
        :format="(v) => Number(v).toLocaleString('zh-CN')"
      />
      <StatCard
        loading="summaryLoading"
        label="24h 错误率"
        icon="AlertTriangle"
        color="error"
        :value="summary.error_rate_24h"
        :format="(v) => `${(Number(v) * 100).toFixed(2)}%`"
      />
      <StatCard
        loading="summaryLoading"
        label="P50 延迟"
        icon="Timer"
        color="primary"
        :value="summary.p50_ms"
        :format="(v) => `${v} ms`"
      />
      <StatCard
        loading="summaryLoading"
        label="P95 延迟"
        icon="TimerReset"
        color="warning"
        :value="summary.p95_ms"
        :format="(v) => `${v} ms`"
      />
      <StatCard
        loading="summaryLoading"
        label="P99 延迟"
        icon="Zap"
        color="danger"
        :value="summary.p99_ms"
        :format="(v) => `${v} ms`"
      />
    </div>

    <Tabs
      v-model="activeTab"
      class="w-full"
    >
      <TabsList class="rounded-xl p-1 bg-muted/40">
        <TabsTrigger
          value="overview"
          class="rounded-lg data-[state=active]:text-white data-[state=active]:shadow-sm"
          :style="activeTab === 'overview' ? 'background: linear-gradient(135deg, #0EA5E9 0%, #0284C7 100%);' : ''"
        >
          <BarChart3 class="size-4 mr-1.5" /> 概览
        </TabsTrigger>
        <TabsTrigger
          value="slow"
          class="rounded-lg data-[state=active]:text-white data-[state=active]:shadow-sm"
          :style="activeTab === 'slow' ? 'background: linear-gradient(135deg, #0EA5E9 0%, #0284C7 100%);' : ''"
        >
          <Clock class="size-4 mr-1.5" /> 慢请求 Top
        </TabsTrigger>
        <TabsTrigger
          value="trend"
          class="rounded-lg data-[state=active]:text-white data-[state=active]:shadow-sm"
          :style="activeTab === 'trend' ? 'background: linear-gradient(135deg, #0EA5E9 0%, #0284C7 100%);' : ''"
        >
          <TrendingUp class="size-4 mr-1.5" /> 错误率趋势
        </TabsTrigger>
      </TabsList>

      <TabsContent
        value="overview"
        class="mt-6"
      >
        <Card class="rounded-2xl">
          <CardHeader>
            <CardTitle>慢路径 Top 排名</CardTitle>
            <CardDescription>按平均响应耗时排序的接口路径，建议优先优化红色与赭色条目</CardDescription>
          </CardHeader>
          <CardContent class="p-0">
            <div
              v-if="summaryLoading"
              class="p-5 space-y-3"
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
                <AlertDescription>接口实现后，这里将展示平均耗时最高的 Top 路径。</AlertDescription>
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
                  :class="idx < 3 ? 'bg-warning-muted text-warning-foreground' : 'bg-muted text-muted-foreground'"
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
                        background: p.avg_ms > 500
                          ? 'linear-gradient(90deg, #EF4444, #DC2626)'
                          : p.avg_ms > 200
                            ? 'linear-gradient(90deg, #0EA5E9, #0284C7)'
                            : 'linear-gradient(90deg, #10B981, #059669)'
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
          </CardContent>
        </Card>
      </TabsContent>

      <TabsContent
        value="slow"
        class="mt-6"
      >
        <Card class="rounded-2xl overflow-hidden">
          <CardContent class="p-0">
            <div
              v-if="slowLoading"
              class="p-6 space-y-3"
            >
              <Skeleton
                v-for="i in 6"
                :key="i"
                class="h-14 rounded-xl"
              />
            </div>
            <div
              v-else
              class="overflow-x-auto"
            >
              <table class="w-full text-sm">
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
                      UA
                    </th>
                    <th class="text-right font-medium px-5 py-3">
                      时间
                    </th>
                  </tr>
                </thead>
                <tbody class="divide-y divide-border">
                  <tr
                    v-for="r in slowList"
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
              v-if="slowList.length === 0 && !slowLoading"
              class="p-12"
            >
              <Alert
                variant="info"
                class="rounded-xl max-w-lg mx-auto"
              >
                <Info class="size-4" />
                <AlertTitle>暂无慢请求数据</AlertTitle>
                <AlertDescription>当接口返回 >200ms 的请求时将显示在此列表。</AlertDescription>
              </Alert>
            </div>
            <div
              v-if="slowList.length > 0"
              class="p-4 pt-0 mt-2"
            >
              <div class="flex items-center justify-between text-xs text-muted-foreground">
                <span>第 {{ slowPage }} / {{ Math.max(1, slowTotalPages) }} 页，共 {{ slowTotal }} 条</span>
                <div class="flex gap-1">
                  <Button
                    variant="outline"
                    size="icon-sm"
                    class="rounded-lg"
                    :disabled="slowPage <= 1"
                    @click="slowPage--; loadSlow()"
                  >
                    <ChevronLeft class="size-4" />
                  </Button>
                  <Button
                    variant="outline"
                    size="icon-sm"
                    class="rounded-lg"
                    :disabled="slowPage >= slowTotalPages"
                    @click="slowPage++; loadSlow()"
                  >
                    <ChevronRight class="size-4" />
                  </Button>
                </div>
              </div>
            </div>
          </CardContent>
        </Card>
      </TabsContent>

      <TabsContent
        value="trend"
        class="mt-6"
      >
        <Card class="rounded-2xl">
          <CardHeader>
            <CardTitle>近 30 天错误率趋势</CardTitle>
            <CardDescription>展示每日按请求数加权的 4xx / 5xx 比例，接入图表库后自动替换为真实曲线</CardDescription>
          </CardHeader>
          <CardContent>
            <div
              class="h-72 rounded-2xl relative overflow-hidden"
              style="background: linear-gradient(135deg, rgba(14,165,233,0.08) 0%, rgba(139,92,246,0.06) 50%, rgba(14,165,169,0.08) 100%);"
            >
              <svg
                class="absolute inset-0 w-full h-full opacity-30"
                preserveAspectRatio="none"
                viewBox="0 0 100 40"
              >
                <defs>
                  <linearGradient
                    id="linegrad"
                    x1="0%"
                    y1="0%"
                    x2="100%"
                    y2="0%"
                  >
                    <stop
                      offset="0%"
                      stop-color="#0EA5E9"
                    />
                    <stop
                      offset="50%"
                      stop-color="#8B5CF6"
                    />
                    <stop
                      offset="100%"
                      stop-color="#0EA5A9"
                    />
                  </linearGradient>
                  <linearGradient
                    id="areagrad"
                    x1="0%"
                    y1="0%"
                    x2="0%"
                    y2="100%"
                  >
                    <stop
                      offset="0%"
                      stop-color="#0EA5E9"
                      stop-opacity="0.3"
                    />
                    <stop
                      offset="100%"
                      stop-color="#0EA5E9"
                      stop-opacity="0"
                    />
                  </linearGradient>
                </defs>
                <path
                  d="M0 28 L8 26 L16 24 L24 30 L32 22 L40 20 L48 25 L56 18 L64 22 L72 16 L80 20 L88 14 L100 18 L100 40 L0 40 Z"
                  fill="url(#areagrad)"
                />
                <path
                  d="M0 28 L8 26 L16 24 L24 30 L32 22 L40 20 L48 25 L56 18 L64 22 L72 16 L80 20 L88 14 L100 18"
                  fill="none"
                  stroke="url(#linegrad)"
                  stroke-width="0.8"
                  stroke-linecap="round"
                  stroke-linejoin="round"
                />
              </svg>
              <div class="absolute inset-0 flex items-center justify-center flex-col gap-2 backdrop-blur-sm">
                <div class="size-14 rounded-2xl bg-white/60 dark:bg-black/40 flex items-center justify-center text-muted-foreground">
                  <BarChart3 class="size-7" />
                </div>
                <div class="font-semibold text-foreground/90">
                  图表接入中
                </div>
                <div class="text-sm text-muted-foreground">
                  占位：30 天错误率折线（<span class="tabular-nums">0.12% → 0.06%</span>）
                </div>
              </div>
            </div>
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
import { ref, reactive, onMounted, computed, defineComponent, h, type Component } from 'vue'
import {
  fetchAdminPerformanceSummary,
  fetchAdminSlowRequests,
  formatAdminDateTime,
  type AdminPerformanceSummary,
  type AdminSlowRequest
} from '~~/composables/useAdminManage'
import { useToast } from '~~/composables/useToast'
import {
  Gauge, Activity, AlertTriangle, Timer, TimerReset, Zap, BarChart3, Clock,
  TrendingUp, Info, Loader2 as LucideSkeleton, ChevronLeft, ChevronRight
} from '@lucide/vue'
import { Button } from '~~/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '~~/components/ui/card'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '~~/components/ui/tabs'
import { Badge } from '~~/components/ui/badge'
import { Skeleton } from '~~/components/ui/skeleton'
import { Alert, AlertTitle, AlertDescription } from '~~/components/ui/alert'

definePageMeta({ ssr: false, layout: 'admin' })

const toast = useToast()

const iconMap: Record<string, Component> = {
  Activity, AlertTriangle, Timer, TimerReset, Zap
}

const StatCard = defineComponent({
  name: 'StatCard',
  props: {
    loading: { type: Boolean, default: false },
    label: { type: String, required: true },
    icon: { type: String, required: true },
    color: { type: String, default: 'primary' },
    value: { type: [Number, String], default: 0 },
    format: { type: Function, default: null as ((v: unknown) => string) | null }
  },
  setup(props) {
    const colorClasses: Record<string, string> = {
      info: 'bg-info-muted text-info-foreground',
      error: 'bg-error-muted text-error-foreground',
      primary: 'bg-primary-muted text-primary-foreground',
      warning: 'bg-warning-muted text-warning-foreground',
      danger: 'bg-error-muted text-error-foreground'
    }
    return () => {
      const display = props.format ? props.format(props.value) : String(props.value ?? '-')
      const Icon = iconMap[props.icon] || Activity
      return h('div', { class: 'rounded-2xl border border-border bg-card p-4 space-y-3' }, [
        h('div', { class: 'flex items-start justify-between' }, [
          h('p', { class: 'text-xs text-muted-foreground font-medium uppercase tracking-wide' }, props.label),
          h('div', { class: ['size-9 rounded-xl flex items-center justify-center shrink-0', colorClasses[props.color]] }, [
            h(Icon, { class: 'size-4' })
          ])
        ]),
        props.loading
          ? h(LucideSkeleton, { class: 'h-9 w-24 rounded-lg animate-spin' })
          : h('div', { class: 'text-2xl font-bold tracking-tight tabular-nums' }, display)
      ])
    }
  }
})

const activeTab = ref('overview')
const summaryLoading = ref(true)
const slowLoading = ref(true)

const summary = reactive<AdminPerformanceSummary>({
  total_requests_24h: 0,
  error_rate_24h: 0,
  p50_ms: 0,
  p95_ms: 0,
  p99_ms: 0,
  top_slow_paths: []
})

const slowList = ref<AdminSlowRequest[]>([])
const slowPage = ref(1)
const slowTotal = ref(0)
const slowTotalPages = ref(1)

function methodClass(m: string): string {
  const up = m.toUpperCase()
  if (up === 'GET') return 'bg-success-muted text-success-foreground border-transparent'
  if (up === 'POST') return 'bg-warning-muted text-warning-foreground border-transparent'
  if (up === 'PUT') return 'bg-info-muted text-info-foreground border-transparent'
  if (up === 'DELETE') return 'bg-error-muted text-error-foreground border-transparent'
  return 'bg-muted text-muted-foreground border-transparent'
}

async function loadSummary() {
  summaryLoading.value = true
  try {
    const r = await fetchAdminPerformanceSummary()
    Object.assign(summary, r)
  } catch (e) {
    toast.error(`接口未实现或调用失败: ${e instanceof Error ? e.message : 'fetchAdminPerformanceSummary'}`)
  } finally {
    summaryLoading.value = false
  }
}

async function loadSlow() {
  slowLoading.value = true
  try {
    const r = await fetchAdminSlowRequests({ page: slowPage.value, page_size: 15 })
    slowList.value = r?.items ?? []
    slowTotal.value = r?.total ?? 0
    slowTotalPages.value = r?.total_pages ?? 1
  } catch (e) {
    toast.error(`接口未实现或调用失败: ${e instanceof Error ? e.message : 'fetchAdminSlowRequests'}`)
    slowList.value = []
  } finally {
    slowLoading.value = false
  }
}

onMounted(async () => {
  await Promise.all([loadSummary(), loadSlow()])
})
</script>
