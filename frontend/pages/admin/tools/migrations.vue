<!--
  数据库迁移页：Alembic 状态/一键 upgrade head + 跨库数据迁移任务（SQLite⇄PostgreSQL）发起、轮询与取消。
  契约：状态接口失败必须显式报错——把"取不到状态"降级成"已是最新版本"是危险误报；轮询要区分 job:null（无任务）与请求失败，后者连续 3 次才停止并露出重试；
  后端无 downgrade/单脚本应用端点；初始化错误横幅必须放在 v-if="job" 之外，否则首次使用（无任务）时永远不可见。
-->
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

    <AdminCard
      v-else-if="statusError"
    >
      <Alert
        variant="destructive"
        class="m-6 rounded-xl"
      >
        <AlertTriangle class="size-4" />
        <AlertTitle>无法读取 Alembic 迁移状态</AlertTitle>
        <AlertDescription class="flex flex-wrap items-center justify-between gap-3">
          <span>
            {{ statusError }} —— 为避免误判，页面不会把「取不到状态」显示成「已是最新版本」。
          </span>
          <Button
            variant="outline"
            size="sm"
            class="rounded-lg shrink-0"
            @click="loadStatus"
          >
            <RotateCcw data-icon="inline-start" />
            重试
          </Button>
        </AlertDescription>
      </Alert>
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
          <div class="flex flex-col gap-1.5 mb-4">
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
          <div class="flex flex-col gap-1.5 mb-4">
            <h3 class="flex items-center gap-2 text-base font-semibold">
              <PackageOpen class="size-5 text-warning" />
              待应用迁移（{{ status.pending?.length ?? 0 }}）
            </h3>
            <p class="text-sm text-muted-foreground">
              后端只提供一次性 upgrade 到 head，不支持单脚本应用或回滚；请使用下方「升级到最新版本」
            </p>
          </div>
          <div class="p-0">
            <ScrollArea class="max-h-80 rounded-b-2xl">
              <div
                v-if="!status.pending || status.pending.length === 0"
                class="p-8"
              >
                <div class="max-w-md mx-auto rounded-2xl border border-success/30 bg-success-muted/30 p-5 text-center">
                  <div class="size-14 rounded-2xl bg-success text-success-foreground mx-auto mb-3 flex items-center justify-center">
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
              <div class="size-10 rounded-xl bg-success text-success-foreground flex items-center justify-center shrink-0">
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
                一键运行所有待应用迁移，将 schema 升级至 <code class="px-1.5 py-0.5 bg-muted rounded">{{ status.latest_version || 'latest' }}</code>；后端未提供 downgrade 端点，升级前请确认已备份
              </p>
            </div>
            <Button
              :disabled="upgrading || status.is_latest"
              size="lg"
              class="sm:w-auto w-full rounded-2xl !px-8 shadow-md"
              @click="upgradeConfirmOpen = true"
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
                @click="jobCancelOpen = true"
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
                @click="jobConfirmOpen = true"
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
              <Label
                for="migration-source"
                class="text-sm font-medium"
              >
                源库连接串（source）
              </Label>
              <Input
                id="migration-source"
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
              <Label
                for="migration-target"
                class="text-sm font-medium"
              >
                目标库连接串（target）
              </Label>
              <Input
                id="migration-target"
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

          <!-- 初始化错误（预设/最近任务读取失败）：不能塞进 jobPollError，
               那块横幅在 v-if="job" 内部，首次使用（无任务）时永远不会显示 -->
          <div
            v-if="jobInitError"
            class="flex items-center justify-between gap-2 rounded-lg border border-destructive/40 bg-destructive/10 p-3"
            role="alert"
          >
            <span class="text-xs text-destructive">{{ jobInitError }}</span>
            <Button
              variant="outline"
              size="sm"
              class="rounded-lg shrink-0"
              @click="reloadJobSection"
            >
              <RotateCcw data-icon="inline-start" />
              重试
            </Button>
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
              v-if="jobPollError"
              class="flex flex-wrap items-center justify-between gap-2 rounded-lg border border-destructive/40 bg-destructive/10 p-3"
              role="alert"
            >
              <span class="text-xs text-destructive">{{ jobPollError }}</span>
              <Button
                variant="outline"
                size="sm"
                class="rounded-lg shrink-0"
                @click="resumeJobPolling"
              >
                <RotateCcw data-icon="inline-start" />
                继续轮询
              </Button>
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

    <DangerConfirmDialog
      v-model:open="upgradeConfirmOpen"
      title="确认执行 Alembic upgrade"
      :description="`将执行 alembic upgrade head，把数据库 schema 从 ${status.current_version || '未知版本'} 升级到 ${status.latest_version || 'latest'}（共 ${status.pending?.length ?? 0} 个待应用迁移）。后端未提供回滚端点，结构变更不可撤销，请先完成全站备份。`"
      confirm-text="执行升级"
      confirm-phrase="upgrade head"
      :on-confirm="runUpgrade"
    />

    <DangerConfirmDialog
      v-model:open="jobConfirmOpen"
      :title="jobForm.dry_run ? '确认发起试运行迁移' : '危险：确认发起跨库迁移'"
      :description="jobForm.dry_run
        ? '试运行只统计源表行数，不写入目标库。'
        : `该任务会向目标库 ${jobForm.target} 整库复制数据并在其中执行 alembic upgrade head，目标库中的同名数据可能被覆盖且不可撤销。`"
      confirm-text="发起任务"
      :confirm-phrase="jobForm.dry_run ? '' : '发起迁移'"
      :on-confirm="runJobStart"
    />

    <DangerConfirmDialog
      v-model:open="jobCancelOpen"
      title="确认取消迁移任务"
      description="取消后当前任务会中断，已写入目标库的数据不会自动回滚，需要重新发起或手工清理。"
      confirm-text="取消任务"
      cancel-text="继续运行"
      :on-confirm="runJobCancel"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted, onUnmounted } from 'vue'
import {
  formatAdminDateTime,
  fetchAdminMigrationStatus,
  upgradeAdminMigrations,
  fetchAdminMigrationPresets,
  fetchAdminMigrationJobStatus,
  startAdminMigrationJob,
  cancelAdminMigrationJob,
  type AdminMigrationStatus,
  type AdminMigrationJob,
  type AdminMigrationJobProgress,
  type AdminMigrationJobStatus
} from '~~/composables/useAdminManage'
import { extractApiErrorMessage } from '~~/lib/utils'
import { useToast } from '~~/composables/useToast'
import {
  Database, CheckCircle2, AlertTriangle, History, Check, PackageOpen,
  Clock, PartyPopper, Play, ArrowUpCircle, Loader2, Info, MoveRight, Ban,
  RotateCcw
} from '@lucide/vue'
import { Button } from '~~/components/ui/button'
import AdminCard from '~~/components/admin/AdminCard.vue'
import DangerConfirmDialog from '~~/components/admin/tools/DangerConfirmDialog.vue'
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

function errText(e: unknown, fallback: string): string {
  const err = e as { data?: unknown, message?: string }
  return extractApiErrorMessage(err?.data, err?.message || fallback)
}

const loading = ref(true)
const statusError = ref('')
const upgrading = ref(false)
const upgradeConfirmOpen = ref(false)
const jobConfirmOpen = ref(false)
const jobCancelOpen = ref(false)
const countdown = ref(10)
const upgradeResult = ref<{ message?: string } | null>(null)

const emptyStatus = (): AdminMigrationStatus => ({
  current_version: '',
  latest_version: '',
  is_latest: false,
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

/**
 * 状态读取走 useAdminManage 的 typed wrapper：
 * 该 wrapper 已改为「接口失败即 reject」，页面据此渲染显式错误态 + 重试，
 * 不会再出现后端宕机时误报"已是最新版本"的危险降级。
 */
async function loadStatus() {
  loading.value = true
  statusError.value = ''
  upgradeResult.value = null
  stopCountdown()
  countdown.value = 10
  try {
    status.value = await fetchAdminMigrationStatus({ silentToast: true })
  } catch (e) {
    status.value = emptyStatus()
    statusError.value = errText(e, '迁移状态接口不可用')
  } finally {
    loading.value = false
  }
}

/** DangerConfirmDialog 的 onConfirm：抛出即由弹窗内联展示并保留重试入口 */
async function runUpgrade() {
  upgrading.value = true
  upgradeResult.value = null
  try {
    const r = await upgradeAdminMigrations({ silentToast: true })
    upgradeResult.value = { message: r?.message }
    toast.success(r?.message || '数据库 Schema 已升级到最新版本')
    countdown.value = 10
    stopCountdown()
    countdownTimer = window.setInterval(() => {
      countdown.value--
      if (countdown.value <= 0) {
        stopCountdown()
        loadStatus()
      }
    }, 1000)
  } catch (e) {
    throw new Error(errText(e, '数据库 Schema 升级失败'), { cause: e })
  } finally {
    upgrading.value = false
  }
}

// ==================== 跨库数据迁移任务 ====================

const jobSubmitting = ref(false)
const job = ref<AdminMigrationJob | null>(null)
const presets = ref<Record<string, string>>({})
const jobForm = reactive({ source: '', target: '', dry_run: true, skip_schema: false })
const jobPollError = ref('')
const jobInitError = ref('')
let jobPollFailures = 0

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

/**
 * 轮询必须能区分「后端返回 job:null」与「请求失败」：
 * 之前用 silent 版，接口宕机时被当成任务结束，进度直接冻结且无任何提示。
 * 连续失败 3 次停止轮询并显式报错，提供手动重试。
 */
function startJobPolling() {
  stopJobPolling()
  jobPollTimer = window.setInterval(async () => {
    try {
      const latest = await fetchAdminMigrationJobStatus({ silentToast: true })
      jobPollFailures = 0
      jobPollError.value = ''
      if (latest) job.value = latest
      if (!latest || (latest.status !== 'running' && latest.status !== 'pending')) {
        stopJobPolling()
        if (latest?.status === 'done') toast.success('跨库迁移任务已完成')
        else if (latest?.status === 'error') toast.error('跨库迁移任务失败，请查看事件日志')
      }
    } catch (e) {
      jobPollFailures++
      jobPollError.value = `进度轮询失败（第 ${jobPollFailures} 次）：${errText(e, '任务状态接口不可用')}`
      if (jobPollFailures >= 3) {
        stopJobPolling()
        toast.error(jobPollError.value)
      }
    }
  }, 2000)
}

function resumeJobPolling() {
  jobPollFailures = 0
  jobPollError.value = ''
  startJobPolling()
}

async function loadPresets() {
  try {
    presets.value = await fetchAdminMigrationPresets({ silentToast: true })
  } catch (e) {
    // 连接串预设是辅助功能：不弹 toast，但要留下可重试的错误提示
    presets.value = {}
    jobInitError.value = `迁移连接预设读取失败：${errText(e, '接口不可用')}`
  }
}

async function loadLatestJob() {
  try {
    // 「没有历史任务」后端返回 job:null（不报错），走到 catch 就是网络/权限故障，
    // 必须显式露出，不能静默当成「无任务」。
    const latest = await fetchAdminMigrationJobStatus({ silentToast: true })
    jobInitError.value = ''
    if (latest) {
      job.value = latest
      if (latest.status === 'running' || latest.status === 'pending') startJobPolling()
    }
  } catch (e) {
    jobInitError.value = `最近任务状态读取失败：${errText(e, '接口不可用')}`
  }
}

/** 错误横幅上的「重试」：重跑本区块的两个读取请求 */
function reloadJobSection() {
  loadPresets()
  loadLatestJob()
}

/** DangerConfirmDialog 的 onConfirm（非试运行需输入确认短语） */
async function runJobStart() {
  const source = jobForm.source.trim()
  const target = jobForm.target.trim()
  if (!source || !target) {
    throw new Error('请填写源库与目标库连接串')
  }
  jobSubmitting.value = true
  try {
    job.value = await startAdminMigrationJob(
      { source, target, dry_run: jobForm.dry_run, skip_schema: jobForm.skip_schema },
      { silentToast: true }
    )
    jobPollFailures = 0
    jobPollError.value = ''
    toast.success('迁移任务已发起，正在后台执行')
    startJobPolling()
  } catch (e) {
    throw new Error(errText(e, '迁移任务发起失败'), { cause: e })
  } finally {
    jobSubmitting.value = false
  }
}

async function runJobCancel() {
  try {
    const latest = await cancelAdminMigrationJob({ silentToast: true })
    if (latest) job.value = latest
    stopJobPolling()
    jobPollError.value = ''
    toast.success('迁移任务已取消')
  } catch (e) {
    throw new Error(errText(e, '取消迁移任务失败'), { cause: e })
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
