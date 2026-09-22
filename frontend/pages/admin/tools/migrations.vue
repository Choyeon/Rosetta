<template>
  <div class="flex flex-col gap-5">
    <AdminPageHeader
      title="数据库迁移"
      description="管理 Alembic 版本升级，保持 schema 最新"
      :icon="Database"
    />

    <AdminCard
      v-if="loading"
    >
      <div class="flex flex-col gap-4 p-6">
        <Skeleton class="h-32 rounded-2xl" />
        <Skeleton class="h-40 rounded-2xl" />
        <Skeleton class="h-40 rounded-2xl" />
      </div>
    </AdminCard>

    <template v-else>
      <div class="grid md:grid-cols-3 gap-4">
        <div class="flex flex-col gap-1 rounded-2xl border border-border p-5 bg-card">
          <p class="text-xs text-muted-foreground uppercase tracking-wide">
            当前版本
          </p>
          <p
            class="font-mono font-bold text-2xl tabular-nums truncate"
            :title="status.current_version"
          >
            {{ status.current_version || '未初始化' }}
          </p>
        </div>
        <div class="flex flex-col gap-1 rounded-2xl border border-border p-5 bg-card">
          <p class="text-xs text-muted-foreground uppercase tracking-wide">
            最新版本
          </p>
          <p
            class="font-mono font-bold text-2xl tabular-nums truncate"
            :title="status.latest_version"
          >
            {{ status.latest_version || '-' }}
          </p>
        </div>
        <div class="flex flex-col gap-2 rounded-2xl border border-border p-5 bg-card">
          <p class="text-xs text-muted-foreground uppercase tracking-wide">
            版本状态
          </p>
          <Badge
            :variant="status.is_latest ? 'default' : 'secondary'"
            :class="status.is_latest ? 'bg-success-muted text-success-muted-foreground border-transparent text-sm !py-1 !px-3' : 'bg-warning-muted text-warning-muted-foreground border-transparent text-sm !py-1 !px-3'"
            class="rounded-full"
          >
            <CheckCircle2
              v-if="status.is_latest"
              class="size-4 mr-1"
            />
            <AlertTriangle
              v-else
              class="size-4 mr-1"
            />
            {{ status.is_latest ? '已是最新版本' : '存在待应用迁移' }}
          </Badge>
        </div>
      </div>

      <div class="grid md:grid-cols-2 gap-5">
        <AdminCard>
          <div class="flex flex-col gap-1 .5 mb-4">
            <h3 class="flex items-center gap-2 text-base font-semibold">
              <History class="size-5 text-success" />
              已应用迁移（{{ status.applied?.length ?? 0 }}）
            </h3>
            <p class="text-sm text-muted-foreground">
              历史上已成功执行的迁移脚本
            </p>
          </div>
          <div class="p-0">
            <ScrollArea class="max-h-80 rounded-b-2xl">
              <div
                v-if="!status.applied || status.applied.length === 0"
                class="p-8"
              >
                <Alert
                  variant="info"
                  class="rounded-xl"
                >
                  <Info class="size-4" />
                  <AlertTitle>暂无已应用迁移</AlertTitle>
                  <AlertDescription>尚未记录任何已应用的迁移版本。</AlertDescription>
                </Alert>
              </div>
              <div
                v-else
                class="divide-y divide-border"
              >
                <div
                  v-for="m in status.applied"
                  :key="m.version"
                  class="px-5 py-3 flex items-start gap-3 hover:bg-muted/30"
                >
                  <div class="size-8 rounded-lg bg-success-muted text-success-muted-foreground flex items-center justify-center shrink-0 mt-0.5">
                    <Check class="size-4" />
                  </div>
                  <div class="flex-1 min-w-0">
                    <div class="font-mono text-sm font-semibold truncate">
                      {{ m.version }}
                    </div>
                    <div class="text-sm text-muted-foreground">
                      {{ m.message || '（无描述）' }}
                    </div>
                    <div class="text-xs text-muted-foreground tabular-nums mt-0.5">
                      {{ formatAdminDateTime(m.applied_at) }}
                    </div>
                  </div>
                </div>
              </div>
            </ScrollArea>
          </div>
        </AdminCard>

        <AdminCard>
          <div class="flex flex-col gap-1 .5 mb-4">
            <h3 class="flex items-center gap-2 text-base font-semibold">
              <PackageOpen class="size-5 text-warning" />
              待应用迁移（{{ status.pending?.length ?? 0 }}）
            </h3>
            <p class="text-sm text-muted-foreground">
              点击右侧按钮可立即执行单个迁移
            </p>
          </div>
          <div class="p-0">
            <ScrollArea class="max-h-80 rounded-b-2xl">
              <div
                v-if="!status.pending || status.pending.length === 0"
                class="p-8"
              >
                <div class="max-w-md mx-auto rounded-2xl border border-success/30 bg-success-muted/30 p-5 text-center">
                  <div class="size-14 rounded-2xl bg-success text-white mx-auto mb-3 flex items-center justify-center">
                    <PartyPopper class="size-7" />
                  </div>
                  <h3 class="font-semibold text-success">
                    好消息，数据库是最新的！
                  </h3>
                  <p class="text-sm text-muted-foreground mt-1">
                    当前没有需要应用的迁移脚本。
                  </p>
                </div>
              </div>
              <div
                v-else
                class="divide-y divide-border"
              >
                <div
                  v-for="m in status.pending"
                  :key="m.version"
                  class="px-5 py-3 flex items-start gap-3 hover:bg-muted/30"
                >
                  <div class="size-8 rounded-lg bg-warning-muted text-warning-muted-foreground flex items-center justify-center shrink-0 mt-0.5">
                    <Clock class="size-4" />
                  </div>
                  <div class="flex-1 min-w-0">
                    <div class="font-mono text-sm font-semibold truncate">
                      {{ m.version }}
                    </div>
                    <div class="text-sm text-muted-foreground">
                      {{ m.message || '（无描述）' }}
                    </div>
                  </div>
                  <Button
                    variant="outline"
                    size="sm"
                    class="rounded-lg shrink-0 mt-0.5"
                    :disabled="upgrading"
                    @click="handleUpgrade"
                  >
                    <Play
                      data-icon="inline-start"
                      class="mr-1"
                    /> 应用
                  </Button>
                </div>
              </div>
            </ScrollArea>
          </div>
        </AdminCard>
      </div>

      <AdminCard>
        <div class="flex flex-col gap-5 pt-6">
          <div
            v-if="upgradeResult"
            class="rounded-xl border border-success/40 bg-success-muted/40 p-5"
          >
            <div class="flex items-start gap-3">
              <div class="size-10 rounded-xl bg-success text-white flex items-center justify-center shrink-0">
                <CheckCircle2 class="size-5" />
              </div>
              <div class="flex-1 min-w-0">
                <h3 class="font-semibold">
                  升级成功！
                </h3>
                <p class="text-sm text-muted-foreground mt-0.5">
                  {{ upgradeResult.message || '数据库已升级到最新版本。' }}
                </p>
                <p class="text-xs text-muted-foreground mt-1">
                  页面将在 <b class="tabular-nums">{{ countdown }}</b> 秒后自动刷新。
                </p>
              </div>
            </div>
          </div>

          <div class="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
            <div>
              <h3 class="font-semibold text-lg">
                升级到最新版本（upgrade）
              </h3>
              <p class="text-sm text-muted-foreground">
                一键运行所有待应用迁移，将 schema 升级至 <code class="px-1.5 py-0.5 bg-muted rounded">{{ status.latest_version || 'latest' }}</code>
              </p>
            </div>
            <Button
              :disabled="upgrading || status.is_latest"
              size="lg"
              class="sm:w-auto w-full rounded-2xl !px-8 shadow-md"
              @click="handleUpgrade"
            >
              <Loader2
                v-if="upgrading"
                data-icon="inline-start"
                class="animate-spin"
              />
              <ArrowUpCircle
                v-else
                data-icon="inline-start"
              />
              {{ upgrading ? '正在执行迁移...' : `升级到最新版本` }}
            </Button>
          </div>
        </div>
      </AdminCard>

      <!-- ==================== 跨库数据迁移任务 ==================== -->
      <AdminCard>
        <div class="flex flex-col gap-5 pt-6">
          <div class="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
            <div>
              <h3 class="flex items-center gap-2 font-semibold text-lg">
                <MoveRight class="size-5 text-primary" />
                跨库数据迁移（SQLite ⇄ PostgreSQL）
              </h3>
              <p class="text-sm text-muted-foreground">
                后台异步复制整库数据并在目标库执行 alembic upgrade head，支持试运行与取消。
              </p>
            </div>
            <div class="flex items-center gap-2 shrink-0">
              <Button
                v-if="jobRunning"
                variant="outline"
                size="sm"
                class="rounded-xl"
                @click="handleJobCancel"
              >
                <Ban
                  data-icon="inline-start"
                />
                取消任务
              </Button>
              <Button
                size="sm"
                class="rounded-xl"
                :disabled="jobSubmitting || jobRunning || !jobForm.source.trim() || !jobForm.target.trim()"
                @click="handleJobStart"
              >
                <Loader2
                  v-if="jobSubmitting"
                  data-icon="inline-start"
                  class="animate-spin"
                />
                <Play
                  v-else
                  data-icon="inline-start"
                />
                {{ jobRunning ? '迁移运行中...' : '发起迁移' }}
              </Button>
            </div>
          </div>

          <div class="grid md:grid-cols-2 gap-4">
            <div class="flex flex-col gap-2">
              <Label class="text-sm font-medium">源库连接串（source）</Label>
              <Input
                v-model="jobForm.source"
                placeholder="sqlite+aiosqlite:///./rosetta.db"
                class="rounded-xl font-mono text-xs"
                :disabled="jobRunning"
              />
              <div class="flex flex-wrap gap-2">
                <Button
                  v-for="opt in presetOptions"
                  :key="`src-${opt.key}`"
                  variant="outline"
                  size="sm"
                  class="rounded-lg text-xs h-7"
                  :disabled="jobRunning"
                  @click="jobForm.source = opt.value"
                >
                  {{ opt.label }}
                </Button>
              </div>
            </div>
            <div class="flex flex-col gap-2">
              <Label class="text-sm font-medium">目标库连接串（target）</Label>
              <Input
                v-model="jobForm.target"
                placeholder="postgresql+asyncpg://user:pass@localhost:5432/rosetta"
                class="rounded-xl font-mono text-xs"
                :disabled="jobRunning"
              />
              <div class="flex flex-wrap gap-2">
                <Button
                  v-for="opt in presetOptions"
                  :key="`dst-${opt.key}`"
                  variant="outline"
                  size="sm"
                  class="rounded-lg text-xs h-7"
                  :disabled="jobRunning"
                  @click="jobForm.target = opt.value"
                >
                  {{ opt.label }}
                </Button>
              </div>
            </div>
          </div>

          <div class="flex flex-wrap items-center gap-x-6 gap-y-3">
            <label class="flex items-center gap-2 cursor-pointer">
              <Switch
                v-model="jobForm.dry_run"
                :disabled="jobRunning"
              />
              <span class="text-sm">试运行（dry-run，只统计源表行数不写入）</span>
            </label>
            <label class="flex items-center gap-2 cursor-pointer">
              <Switch
                v-model="jobForm.skip_schema"
                :disabled="jobRunning"
              />
              <span class="text-sm">跳过 schema 阶段（不在目标库执行 upgrade head）</span>
            </label>
          </div>

          <!-- 任务进度 -->
          <div
            v-if="job"
            class="rounded-xl border border-border bg-muted/20 p-4 flex flex-col gap-3"
          >
            <div class="flex flex-wrap items-center justify-between gap-2">
              <div class="flex items-center gap-2">
                <span class="text-sm font-semibold">
                  任务 {{ job.job_id.slice(0, 8) }}
                </span>
                <Badge
                  :class="jobStatusClass(job.status)"
                  class="rounded-full border-transparent text-xs !px-2.5"
                >
                  {{ jobStatusLabel(job.status) }}
                </Badge>
              </div>
              <span class="text-xs text-muted-foreground font-mono">
                {{ job.source }} → {{ job.target }}
              </span>
            </div>

            <div class="flex flex-col gap-1.5">
              <div class="flex items-center justify-between text-xs text-muted-foreground">
                <span>{{ jobProgressText }}</span>
                <span class="tabular-nums">{{ jobPercent }}%</span>
              </div>
              <Progress
                :value="jobPercent"
                class="h-2"
              />
            </div>

            <div
              v-if="job.errors.length || job.warnings.length"
              class="flex items-center gap-3 text-xs"
            >
              <span
                v-if="job.errors.length"
                class="text-error font-medium"
              >错误 {{ job.errors.length }}</span>
              <span
                v-if="job.warnings.length"
                class="text-warning font-medium"
              >警告 {{ job.warnings.length }}</span>
            </div>

            <ScrollArea class="max-h-44 rounded-lg border border-border/60 bg-background">
              <ul class="divide-y divide-border/50">
                <li
                  v-for="(ev, i) in jobEventsDesc"
                  :key="i"
                  class="px-3 py-1.5 text-xs font-mono flex items-start gap-2"
                >
                  <span class="shrink-0 uppercase text-muted-foreground/80 w-16">{{ ev.stage ?? '-' }}</span>
                  <span
                    v-if="ev.table"
                    class="shrink-0 text-primary/80"
                  >{{ ev.table }}</span>
                  <span class="text-muted-foreground break-all">{{ ev.message || '' }}</span>
                </li>
                <li
                  v-if="jobEventsDesc.length === 0"
                  class="px-3 py-3 text-xs text-muted-foreground"
                >
                  暂无进度事件。
                </li>
              </ul>
            </ScrollArea>
          </div>
        </div>
      </AdminCard>
    </template>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted, onUnmounted } from 'vue'
import {
  fetchAdminMigrationStatus,
  upgradeAdminMigrations,
  formatAdminDateTime,
  fetchAdminMigrationPresets,
  startAdminMigrationJob,
  fetchAdminMigrationJobStatus,
  cancelAdminMigrationJob,
  type AdminMigrationStatus,
  type AdminMigrationJob,
  type AdminMigrationJobProgress,
  type AdminMigrationJobStatus
} from '~~/composables/useAdminManage'
import { useToast } from '~~/composables/useToast'
import {
  Database, CheckCircle2, AlertTriangle, History, Check, PackageOpen,
  Clock, PartyPopper, Play, ArrowUpCircle, Loader2, Info, MoveRight, Ban
} from '@lucide/vue'
import { Button } from '~~/components/ui/button'
import AdminCard from '~~/components/admin/AdminCard.vue'
import { Badge } from '~~/components/ui/badge'
import { Skeleton } from '~~/components/ui/skeleton'
import { ScrollArea } from '~~/components/ui/scroll-area'
import { Alert, AlertTitle, AlertDescription } from '~~/components/ui/alert'
import { Input } from '~~/components/ui/input'
import { Label } from '~~/components/ui/label'
import { Switch } from '~~/components/ui/switch'
import { Progress } from '~~/components/ui/progress'

definePageMeta({ ssr: false, layout: 'admin' })

const toast = useToast()

const loading = ref(true)
const upgrading = ref(false)
const countdown = ref(10)
const upgradeResult = ref<{ message?: string } | null>(null)

const emptyStatus = (): AdminMigrationStatus => ({
  current_version: '',
  latest_version: '',
  is_latest: true,
  pending: [],
  applied: []
})

const status = ref<AdminMigrationStatus>(emptyStatus())

let countdownTimer: number | null = null

function stopCountdown() {
  if (countdownTimer) {
    clearInterval(countdownTimer)
    countdownTimer = null
  }
}

async function loadStatus() {
  loading.value = true
  upgradeResult.value = null
  stopCountdown()
  countdown.value = 10
  try {
    const r = await fetchAdminMigrationStatus()
    status.value = r || emptyStatus()
  } catch {
    status.value = emptyStatus()
  } finally {
    loading.value = false
  }
}

async function handleUpgrade() {
  upgrading.value = true
  upgradeResult.value = null
  try {
    const r = await upgradeAdminMigrations()
    if (r?.success === false) {
      throw new Error(r.message || '数据库 Schema 升级失败')
    }
    upgradeResult.value = { message: r?.message }
    toast.success(r?.message || '数据库 Schema 已升级到最新版本')
    countdown.value = 10
    countdownTimer = window.setInterval(() => {
      countdown.value--
      if (countdown.value <= 0) {
        stopCountdown()
        loadStatus()
      }
    }, 1000)
  } catch {
    // 错误已由 apiFetch 统一 toast，此处不再双报（"静默失败"是 bug 的反面是双报）
  } finally {
    upgrading.value = false
  }
}

// ==================== 跨库数据迁移任务 ====================

const jobSubmitting = ref(false)
const job = ref<AdminMigrationJob | null>(null)
const presets = ref<Record<string, string>>({})
const jobForm = reactive({ source: '', target: '', dry_run: true, skip_schema: false })

let jobPollTimer: number | null = null

const jobRunning = computed(() => job.value?.status === 'running' || job.value?.status === 'pending')

const presetOptions = computed(() => [
  { key: 'current_database', label: '当前数据库', value: presets.value.current_database ?? '' },
  { key: 'sqlite_default', label: 'SQLite 默认', value: presets.value.sqlite_default ?? '' }
].filter(opt => opt.value))

const jobEventsDesc = computed<AdminMigrationJobProgress[]>(() =>
  (job.value?.events_tail ?? []).slice(-30).reverse()
)

const jobPercent = computed(() => {
  const p = job.value?.latest_progress
  if (!p) return jobRunning.value ? 3 : 100
  const totalTables = Number(p.tables_total ?? 0)
  if (!totalTables) return jobRunning.value ? 3 : 100
  return Math.min(100, Math.round((Number(p.tables_done ?? 0) / totalTables) * 100))
})

const jobProgressText = computed(() => {
  const p = job.value?.latest_progress
  if (!p) return '等待进度…'
  const parts: string[] = []
  if (p.stage) parts.push(`阶段 ${p.stage}`)
  if (p.tables_total) parts.push(`表 ${p.tables_done ?? 0}/${p.tables_total}`)
  if (p.rows_total) parts.push(`行 ${p.rows_done ?? 0}/${p.rows_total}`)
  if (p.message) parts.push(String(p.message))
  return parts.join(' · ') || '运行中…'
})

function jobStatusLabel(s: AdminMigrationJobStatus) {
  return {
    pending: '排队中',
    running: '运行中',
    done: '已完成',
    error: '失败',
    cancelled: '已取消'
  }[s] ?? s
}

function jobStatusClass(s: AdminMigrationJobStatus) {
  if (s === 'done') return 'bg-success-muted text-success-muted-foreground'
  if (s === 'error') return 'bg-error-muted text-error-muted-foreground'
  if (s === 'cancelled') return 'bg-warning-muted text-warning-muted-foreground'
  if (s === 'running') return 'bg-info-muted text-info-muted-foreground'
  return 'bg-muted text-muted-foreground'
}

function stopJobPolling() {
  if (jobPollTimer) {
    clearInterval(jobPollTimer)
    jobPollTimer = null
  }
}

function startJobPolling() {
  stopJobPolling()
  jobPollTimer = window.setInterval(async () => {
    const latest = await fetchAdminMigrationJobStatus(true)
    if (latest) job.value = latest
    if (!latest || (latest.status !== 'running' && latest.status !== 'pending')) {
      stopJobPolling()
      if (latest?.status === 'done') toast.success('跨库迁移任务已完成')
      else if (latest?.status === 'error') toast.error('跨库迁移任务失败，请查看事件日志')
    }
  }, 2000)
}

async function loadPresets() {
  try {
    presets.value = await fetchAdminMigrationPresets()
  } catch {
    presets.value = {}
  }
}

async function loadLatestJob() {
  try {
    const latest = await fetchAdminMigrationJobStatus(true)
    if (latest) {
      job.value = latest
      if (latest.status === 'running' || latest.status === 'pending') startJobPolling()
    }
  } catch {
    // 无历史任务时静默
  }
}

async function handleJobStart() {
  if (!jobForm.source.trim() || !jobForm.target.trim()) {
    toast.warning('请填写源库与目标库连接串')
    return
  }
  jobSubmitting.value = true
  try {
    job.value = await startAdminMigrationJob({
      source: jobForm.source.trim(),
      target: jobForm.target.trim(),
      dry_run: jobForm.dry_run,
      skip_schema: jobForm.skip_schema
    })
    toast.success('迁移任务已发起，正在后台执行')
    startJobPolling()
  } catch {
    // 错误已由 apiFetch 统一 toast
  } finally {
    jobSubmitting.value = false
  }
}

async function handleJobCancel() {
  try {
    job.value = await cancelAdminMigrationJob()
    stopJobPolling()
    toast.success('迁移任务已取消')
  } catch {
    // 错误已由 apiFetch 统一 toast
  }
}

onMounted(() => {
  loadStatus()
  loadPresets()
  loadLatestJob()
})

onUnmounted(() => {
  stopCountdown()
  stopJobPolling()
})
</script>
