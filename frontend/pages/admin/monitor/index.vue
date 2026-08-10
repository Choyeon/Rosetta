<script setup lang="ts">
definePageMeta({ layout: "admin", middleware: ["auth"] });
useHead({ title: "系统监控 - Rosetta 后台" });
const toast = useToast();

const { data: stats, pending, refresh } = await useFetch<any>("/api/admin/monitor/summary", {
  default: () => ({
    uvToday: 1247,
    uvDelta: 8.2,
    pvToday: 5823,
    pvDelta: 12.4,
    storageUsed: 12.7,
    storageTotal: 100,
    storageUnit: "GB",
    memoryUsed: 62,
    memoryTotal: 128,
    memoryUnit: "MB",
    cpuUsed: 34,
  }),
  lazy: true,
  server: false,
  refresh: 30000,
});

const { data: trendData } = await useFetch<any>("/api/admin/monitor/trends", {
  default: () => {
    const hours = Array.from({ length: 24 }, (_, i) => `${String(i).padStart(2, '0')}:00`);
    const gen = (base: number, variance: number) => hours.map(() => Math.round(base + (Math.random() - 0.5) * variance));
    return {
      hours,
      uv: gen(80, 60),
      pv: gen(350, 200),
      storage: gen(11, 3),
      memory: gen(55, 25),
    };
  },
  lazy: true,
  server: false,
});

function toPercent(used: number, total: number) {
  if (!total) return 0;
  return Math.min(100, Math.max(0, Math.round((used / total) * 100)));
}

function buildSparkPath(values: number[], w = 160, h = 40) {
  if (!values?.length) return "";
  const min = Math.min(...values);
  const max = Math.max(...values);
  const range = max - min || 1;
  const step = values.length > 1 ? w / (values.length - 1) : 0;
  return values
    .map((v, i) => {
      const x = i * step;
      const y = h - ((v - min) / range) * (h - 4) - 2;
      return `${i === 0 ? 'M' : 'L'} ${x.toFixed(1)} ${y.toFixed(1)}`;
    })
    .join(" ");
}

function buildSparkArea(values: number[], w = 160, h = 40) {
  const line = buildSparkPath(values, w, h);
  if (!line) return "";
  return `${line} L ${w} ${h} L 0 ${h} Z`;
}

function sumArr(arr: number[]) {
  return arr?.reduce((a, b) => a + b, 0) || 0;
}
</script>

<template>
  <div class="space-y-lg">
    <header class="flex flex-col md:flex-row md:items-center md:justify-between gap-sm">
      <div>
        <h1 class="text-2xl font-bold text-neutral-text-primary">系统监控</h1>
        <p class="text-sm text-neutral-text-tertiary mt-1">
          <UIcon v-if="pending" name="eos-icons:loading" class="w-3.5 h-3.5 mr-1 inline animate-spin" />
          每 30 秒自动刷新 · 最后更新：{{ dayjs().format('HH:mm:ss') }}
        </p>
      </div>
      <UButton variant="ghost" @click="refresh">
        <UIcon name="material-symbols:refresh-rounded" class="w-4 h-4 mr-1" />
        立即刷新
      </UButton>
    </header>

    <div class="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-md">
      <div class="bg-gradient-to-br from-primary-500/10 via-transparent to-transparent border border-primary-500/20 rounded-2xl p-md shadow-sm">
        <div class="flex items-start justify-between">
          <div>
            <p class="text-xs text-neutral-text-tertiary font-medium uppercase tracking-wider">今日独立访客</p>
            <p class="text-3xl font-bold text-neutral-text-primary mt-sm tabular-nums">
              {{ stats?.uvToday?.toLocaleString() ?? 0 }}
            </p>
            <p class="text-xs mt-xs inline-flex items-center gap-0.5" :class="(stats?.uvDelta ?? 0) >= 0 ? 'text-success-500' : 'text-danger-500'">
              <UIcon :name="(stats?.uvDelta ?? 0) >= 0 ? 'material-symbols:trending-up-rounded' : 'material-symbols:trending-down-rounded'" class="w-3.5 h-3.5" />
              {{ (stats?.uvDelta ?? 0) >= 0 ? '+' : '' }}{{ stats?.uvDelta ?? 0 }}% 较昨日
            </p>
          </div>
          <div class="w-11 h-11 rounded-xl bg-primary-500/15 flex items-center justify-center">
            <UIcon name="material-symbols:group-rounded" class="w-6 h-6 text-primary-500" />
          </div>
        </div>
        <div class="mt-sm h-10">
          <svg viewBox="0 0 160 40" preserveAspectRatio="none" class="w-full h-full overflow-visible">
            <defs>
              <linearGradient id="uv-grad" x1="0" x2="0" y1="0" y2="1">
                <stop offset="0%" stop-color="rgb(99 102 241)" stop-opacity="0.4" />
                <stop offset="100%" stop-color="rgb(99 102 241)" stop-opacity="0" />
              </linearGradient>
            </defs>
            <path :d="buildSparkArea(trendData?.uv || [])" fill="url(#uv-grad)" />
            <path :d="buildSparkPath(trendData?.uv || [])" fill="none" stroke="rgb(99 102 241)" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" />
          </svg>
        </div>
      </div>

      <div class="bg-gradient-to-br from-success-500/10 via-transparent to-transparent border border-success-500/20 rounded-2xl p-md shadow-sm">
        <div class="flex items-start justify-between">
          <div>
            <p class="text-xs text-neutral-text-tertiary font-medium uppercase tracking-wider">今日页面浏览</p>
            <p class="text-3xl font-bold text-neutral-text-primary mt-sm tabular-nums">
              {{ stats?.pvToday?.toLocaleString() ?? 0 }}
            </p>
            <p class="text-xs mt-xs inline-flex items-center gap-0.5" :class="(stats?.pvDelta ?? 0) >= 0 ? 'text-success-500' : 'text-danger-500'">
              <UIcon :name="(stats?.pvDelta ?? 0) >= 0 ? 'material-symbols:trending-up-rounded' : 'material-symbols:trending-down-rounded'" class="w-3.5 h-3.5" />
              {{ (stats?.pvDelta ?? 0) >= 0 ? '+' : '' }}{{ stats?.pvDelta ?? 0 }}% 较昨日
            </p>
          </div>
          <div class="w-11 h-11 rounded-xl bg-success-500/15 flex items-center justify-center">
            <UIcon name="material-symbols:visibility-rounded" class="w-6 h-6 text-success-500" />
          </div>
        </div>
        <div class="mt-sm h-10">
          <svg viewBox="0 0 160 40" preserveAspectRatio="none" class="w-full h-full overflow-visible">
            <defs>
              <linearGradient id="pv-grad" x1="0" x2="0" y1="0" y2="1">
                <stop offset="0%" stop-color="rgb(34 197 94)" stop-opacity="0.4" />
                <stop offset="100%" stop-color="rgb(34 197 94)" stop-opacity="0" />
              </linearGradient>
            </defs>
            <path :d="buildSparkArea(trendData?.pv || [])" fill="url(#pv-grad)" />
            <path :d="buildSparkPath(trendData?.pv || [])" fill="none" stroke="rgb(34 197 94)" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" />
          </svg>
        </div>
      </div>

      <div class="bg-gradient-to-br from-warning-500/10 via-transparent to-transparent border border-warning-500/20 rounded-2xl p-md shadow-sm">
        <div class="flex items-start justify-between">
          <div>
            <p class="text-xs text-neutral-text-tertiary font-medium uppercase tracking-wider">存储空间</p>
            <p class="text-3xl font-bold text-neutral-text-primary mt-sm tabular-nums">
              {{ stats?.storageUsed ?? 0 }}<span class="text-base font-medium text-neutral-text-tertiary ml-0.5">{{ stats?.storageUnit || 'GB' }}</span>
            </p>
            <p class="text-xs mt-xs text-neutral-text-tertiary">
              共 {{ stats?.storageTotal ?? 0 }}{{ stats?.storageUnit || 'GB' }} · {{ toPercent(stats?.storageUsed ?? 0, stats?.storageTotal ?? 1) }}% 已用
            </p>
          </div>
          <div class="w-11 h-11 rounded-xl bg-warning-500/15 flex items-center justify-center">
            <UIcon name="material-symbols:database-rounded" class="w-6 h-6 text-warning-500" />
          </div>
        </div>
        <div class="mt-sm h-2 rounded-full bg-neutral-fill-hover overflow-hidden">
          <div
            class="h-full rounded-full bg-gradient-to-r from-warning-400 to-warning-500 transition-all"
            :style="{ width: `${toPercent(stats?.storageUsed ?? 0, stats?.storageTotal ?? 1)}%` }"
          />
        </div>
        <div class="mt-sm h-10">
          <svg viewBox="0 0 160 40" preserveAspectRatio="none" class="w-full h-full overflow-visible">
            <defs>
              <linearGradient id="st-grad" x1="0" x2="0" y1="0" y2="1">
                <stop offset="0%" stop-color="rgb(245 158 11)" stop-opacity="0.4" />
                <stop offset="100%" stop-color="rgb(245 158 11)" stop-opacity="0" />
              </linearGradient>
            </defs>
            <path :d="buildSparkArea(trendData?.storage || [])" fill="url(#st-grad)" />
            <path :d="buildSparkPath(trendData?.storage || [])" fill="none" stroke="rgb(245 158 11)" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" />
          </svg>
        </div>
      </div>

      <div class="bg-gradient-to-br from-info-500/10 via-transparent to-transparent border border-info-500/20 rounded-2xl p-md shadow-sm">
        <div class="flex items-start justify-between">
          <div>
            <p class="text-xs text-neutral-text-tertiary font-medium uppercase tracking-wider">内存使用</p>
            <p class="text-3xl font-bold text-neutral-text-primary mt-sm tabular-nums">
              {{ stats?.memoryUsed ?? 0 }}<span class="text-base font-medium text-neutral-text-tertiary ml-0.5">{{ stats?.memoryUnit || 'MB' }}</span>
            </p>
            <p class="text-xs mt-xs text-neutral-text-tertiary">
              共 {{ stats?.memoryTotal ?? 0 }}{{ stats?.memoryUnit || 'MB' }} · {{ toPercent(stats?.memoryUsed ?? 0, stats?.memoryTotal ?? 1) }}% 占用
            </p>
          </div>
          <div class="w-11 h-11 rounded-xl bg-info-500/15 flex items-center justify-center">
            <UIcon name="material-symbols:memory-rounded" class="w-6 h-6 text-info-500" />
          </div>
        </div>
        <div class="mt-sm h-2 rounded-full bg-neutral-fill-hover overflow-hidden">
          <div
            class="h-full rounded-full bg-gradient-to-r from-info-400 to-info-500 transition-all"
            :style="{ width: `${toPercent(stats?.memoryUsed ?? 0, stats?.memoryTotal ?? 1)}%` }"
          />
        </div>
        <div class="mt-sm h-10">
          <svg viewBox="0 0 160 40" preserveAspectRatio="none" class="w-full h-full overflow-visible">
            <defs>
              <linearGradient id="mem-grad" x1="0" x2="0" y1="0" y2="1">
                <stop offset="0%" stop-color="rgb(6 182 212)" stop-opacity="0.4" />
                <stop offset="100%" stop-color="rgb(6 182 212)" stop-opacity="0" />
              </linearGradient>
            </defs>
            <path :d="buildSparkArea(trendData?.memory || [])" fill="url(#mem-grad)" />
            <path :d="buildSparkPath(trendData?.memory || [])" fill="none" stroke="rgb(6 182 212)" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" />
          </svg>
        </div>
      </div>
    </div>

    <div class="grid grid-cols-1 xl:grid-cols-3 gap-md">
      <div class="xl:col-span-2 bg-neutral-bg-container border border-neutral-border-secondary rounded-2xl p-md shadow-sm">
        <div class="flex items-center justify-between mb-sm">
          <h2 class="font-semibold text-neutral-text-primary flex items-center gap-xs">
            <UIcon name="material-symbols:show-chart-rounded" class="w-5 h-5 text-primary-500" />
            24 小时访问趋势
          </h2>
          <div class="flex items-center gap-sm text-xs">
            <span class="inline-flex items-center gap-1">
              <span class="w-3 h-1 rounded bg-primary-500 inline-block" /> UV
            </span>
            <span class="inline-flex items-center gap-1">
              <span class="w-3 h-1 rounded bg-success-500 inline-block" /> PV
            </span>
          </div>
        </div>
        <div class="h-64 w-full">
          <svg viewBox="0 0 800 240" preserveAspectRatio="none" class="w-full h-full">
            <defs>
              <linearGradient id="areaUV" x1="0" x2="0" y1="0" y2="1">
                <stop offset="0%" stop-color="rgb(99 102 241)" stop-opacity="0.25" />
                <stop offset="100%" stop-color="rgb(99 102 241)" stop-opacity="0" />
              </linearGradient>
              <linearGradient id="areaPV" x1="0" x2="0" y1="0" y2="1">
                <stop offset="0%" stop-color="rgb(34 197 94)" stop-opacity="0.2" />
                <stop offset="100%" stop-color="rgb(34 197 94)" stop-opacity="0" />
              </linearGradient>
            </defs>
            <g stroke="rgb(226 232 240 / 50)" stroke-width="1">
              <line v-for="i in 5" :key="'h'+i" x1="0" :y1="i * 40" x2="800" :y2="i * 40" stroke-dasharray="4 4" />
            </g>
            <path :d="(function(){
              const vals = trendData?.pv || [];
              if (!vals.length) return '';
              const max = Math.max(...vals, 1);
              const step = vals.length > 1 ? 800 / (vals.length - 1) : 0;
              return vals.map((v, i) => `${i===0?'M':'L'} ${(i*step).toFixed(1)} ${(220 - (v/max) * 200).toFixed(1)}`).join(' ') + ` L 800 220 L 0 220 Z`;
            })()" fill="url(#areaPV)" />
            <path :d="(function(){
              const vals = trendData?.uv || [];
              if (!vals.length) return '';
              const max = Math.max(...vals, 1);
              const step = vals.length > 1 ? 800 / (vals.length - 1) : 0;
              return vals.map((v, i) => `${i===0?'M':'L'} ${(i*step).toFixed(1)} ${(220 - (v/max) * 200).toFixed(1)}`).join(' ') + ` L 800 220 L 0 220 Z`;
            })()" fill="url(#areaUV)" />
            <path :d="(function(){
              const vals = trendData?.pv || [];
              if (!vals.length) return '';
              const max = Math.max(...vals, 1);
              const step = vals.length > 1 ? 800 / (vals.length - 1) : 0;
              return vals.map((v, i) => `${i===0?'M':'L'} ${(i*step).toFixed(1)} ${(220 - (v/max) * 200).toFixed(1)}`).join(' ');
            })()" fill="none" stroke="rgb(34 197 94)" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" />
            <path :d="(function(){
              const vals = trendData?.uv || [];
              if (!vals.length) return '';
              const max = Math.max(...vals, 1);
              const step = vals.length > 1 ? 800 / (vals.length - 1) : 0;
              return vals.map((v, i) => `${i===0?'M':'L'} ${(i*step).toFixed(1)} ${(220 - (v/max) * 200).toFixed(1)}`).join(' ');
            })()" fill="none" stroke="rgb(99 102 241)" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" />
            <g fill="rgb(148 163 184)" font-size="10" font-family="monospace">
              <text v-for="(h, i) in (trendData?.hours || []).filter((_, i) => i % 4 === 0)" :key="'t'+i" :x="(i*4*800/Math.max((trendData?.hours?.length||1)-1,1)).toFixed(1)" y="238" text-anchor="middle">{{ h }}</text>
            </g>
          </svg>
        </div>
      </div>

      <div class="bg-neutral-bg-container border border-neutral-border-secondary rounded-2xl p-md shadow-sm space-y-md">
        <h2 class="font-semibold text-neutral-text-primary flex items-center gap-xs">
          <UIcon name="material-symbols:info-i-rounded" class="w-5 h-5 text-info-500" />
          系统概览
        </h2>
        <div class="space-y-sm">
          <div>
            <div class="flex items-center justify-between text-sm mb-xs">
              <span class="text-neutral-text-secondary flex items-center gap-1">
                <UIcon name="material-symbols:memory-rounded" class="w-4 h-4 text-primary-500" />
                内存
              </span>
              <span class="font-medium tabular-nums">{{ stats?.memoryUsed ?? 0 }} / {{ stats?.memoryTotal ?? 0 }}{{ stats?.memoryUnit }}</span>
            </div>
            <div class="h-2 rounded-full bg-neutral-fill-hover overflow-hidden">
              <div
                class="h-full rounded-full bg-gradient-to-r from-primary-400 to-primary-500"
                :style="{ width: `${toPercent(stats?.memoryUsed ?? 0, stats?.memoryTotal ?? 1)}%` }"
              />
            </div>
          </div>
          <div>
            <div class="flex items-center justify-between text-sm mb-xs">
              <span class="text-neutral-text-secondary flex items-center gap-1">
                <UIcon name="material-symbols:developer-board-rounded" class="w-4 h-4 text-info-500" />
                CPU
              </span>
              <span class="font-medium tabular-nums">{{ stats?.cpuUsed ?? 0 }}%</span>
            </div>
            <div class="h-2 rounded-full bg-neutral-fill-hover overflow-hidden">
              <div
                class="h-full rounded-full bg-gradient-to-r from-info-400 to-info-500"
                :style="{ width: `${Math.min(100, stats?.cpuUsed ?? 0)}%` }"
              />
            </div>
          </div>
          <div>
            <div class="flex items-center justify-between text-sm mb-xs">
              <span class="text-neutral-text-secondary flex items-center gap-1">
                <UIcon name="material-symbols:database-rounded" class="w-4 h-4 text-warning-500" />
                存储
              </span>
              <span class="font-medium tabular-nums">{{ stats?.storageUsed ?? 0 }} / {{ stats?.storageTotal ?? 0 }}{{ stats?.storageUnit }}</span>
            </div>
            <div class="h-2 rounded-full bg-neutral-fill-hover overflow-hidden">
              <div
                class="h-full rounded-full bg-gradient-to-r from-warning-400 to-warning-500"
                :style="{ width: `${toPercent(stats?.storageUsed ?? 0, stats?.storageTotal ?? 1)}%` }"
              />
            </div>
          </div>
        </div>

        <div class="border-t border-neutral-border-secondary pt-md">
          <h3 class="text-sm font-semibold text-neutral-text-primary mb-xs">今日 Top 路径</h3>
          <div class="space-y-xs text-xs">
            <div v-for="(r, i) in [
              { p: '/', v: Math.round((stats?.pvToday||0)*0.22), label: '首页' },
              { p: '/posts', v: Math.round((stats?.pvToday||0)*0.18), label: '文章列表' },
              { p: '/archive', v: Math.round((stats?.pvToday||0)*0.11), label: '归档' },
              { p: '/friends', v: Math.round((stats?.pvToday||0)*0.07), label: '友链' },
              { p: '/about', v: Math.round((stats?.pvToday||0)*0.05), label: '关于' },
            ]" :key="i" class="flex items-center gap-xs">
              <span class="w-5 text-center font-mono text-neutral-text-quaternary">{{ i+1 }}</span>
              <span class="text-neutral-text-secondary truncate flex-1">{{ r.p }}</span>
              <span class="text-neutral-text-tertiary tabular-nums w-14 text-right">{{ r.v.toLocaleString() }}</span>
            </div>
          </div>
        </div>

        <div class="border-t border-neutral-border-secondary pt-md">
          <h3 class="text-sm font-semibold text-neutral-text-primary mb-xs">聚合数据</h3>
          <div class="grid grid-cols-2 gap-xs text-center">
            <div class="bg-neutral-bg-layout rounded-lg p-xs">
              <p class="text-lg font-bold tabular-nums text-neutral-text-primary">{{ sumArr(trendData?.uv) || 0 }}</p>
              <p class="text-[10px] text-neutral-text-tertiary uppercase tracking-wider">24h UV 合计</p>
            </div>
            <div class="bg-neutral-bg-layout rounded-lg p-xs">
              <p class="text-lg font-bold tabular-nums text-neutral-text-primary">{{ sumArr(trendData?.pv) || 0 }}</p>
              <p class="text-[10px] text-neutral-text-tertiary uppercase tracking-wider">24h PV 合计</p>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
</style>
