<!--
  操作审计日志页：按操作类型/用户 ID/IP 关键词/资源类型/日期范围做服务端筛选 + 分页列表 + 行展开 details JSON。
  契约：筛选条件须点「应用筛选」才生效且必须把页码重置回 1（否则停留越界空页）；结果缩小时钳制回最后一页并只重试一次防循环；
  日期区间保证"结束不早于开始"，自动弹出结束选择器需等 DOM 同步（nextTick + showPicker）。
  导出（CSV/JSON）复用「类型/用户/日期」三项筛选打 /admin/logs/export（包装层只转发这四个条件，
  IP 关键词与资源类型不参与导出，触发时提示语必须如实说明），后端上限 1000 条。
  列表接口（advanced.py::list_operation_logs）另支持 resource_type 与 q（匹配 detail/error_code/ip），
  页内已接线为「IP/关键词」与「资源类型」两个输入；action 是自由字符串、后端无 distinct 枚举口，
  下拉只是常用值快捷方式——不在名单里的动作按原值渲染（actionLabel 回退原始 label、actionClass 回退中性灰）。
  清理旧日志走 DELETE /admin/logs/retention?days=N（days 限 1-3650）：它只删操作留痕，访问日志/性能指标由服务端
  LOG_RETENTION_DAYS 保留循环处理，文案不得写成"清理全部日志"；清理后必须重读列表，否则界面仍显示已删的行。
-->
<template>
  <div class="flex flex-col gap-5">
    <AdminPageHeader
      title="操作审计日志"
      description="管理员与登录用户的操作留痕"
      :icon="FileSearch"
    >
      <template #actions>
        <Button
          variant="outline"
          size="sm"
          class="rounded-xl"
          :disabled="exporting !== ''"
          @click="handleExport('csv')"
        >
          {{ exporting === 'csv' ? '导出中…' : '导出 CSV' }}
        </Button>
        <Button
          variant="outline"
          size="sm"
          class="rounded-xl"
          :disabled="exporting !== ''"
          @click="handleExport('json')"
        >
          {{ exporting === 'json' ? '导出中…' : '导出 JSON' }}
        </Button>
        <Label
          for="audit-cleanup-days"
          class="sr-only"
        >保留期限</Label>
        <Select v-model="cleanupDays">
          <SelectTrigger
            id="audit-cleanup-days"
            class="h-9 w-[7.5rem] rounded-xl"
          >
            <SelectValue placeholder="保留期限" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem
              v-for="d in cleanupDayOptions"
              :key="d"
              :value="d"
            >
              保留 {{ d }} 天
            </SelectItem>
          </SelectContent>
        </Select>
        <Button
          variant="outline"
          size="sm"
          class="rounded-xl"
          :disabled="exporting !== ''"
          @click="cleanupOpen = true"
        >
          清理旧日志
        </Button>
      </template>
    </AdminPageHeader>

    <AdminCard>
      <div class="pt-6 pb-4">
        <div class="grid md:grid-cols-2 xl:grid-cols-4 gap-4">
          <div class="flex flex-col gap-2">
            <Label
              for="audit-action-select"
              class="text-sm font-medium"
            >操作类型</Label>
            <Select
              v-model="filters.action"
              class="rounded-xl"
            >
              <SelectTrigger
                id="audit-action-select"
                class="rounded-xl"
              >
                <SelectValue placeholder="全部类型" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem
                  v-for="o in actionOptions"
                  :key="o.value"
                  :value="o.value"
                >
                  {{ o.label }}
                </SelectItem>
              </SelectContent>
            </Select>
          </div>
          <div class="flex flex-col gap-2">
            <Label
              for="audit-user-input"
              class="text-sm font-medium"
            >用户 ID 搜索</Label>
            <div class="relative">
              <Search class="size-4 absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground" />
              <Input
                id="audit-user-input"
                v-model.number="filters.userId"
                type="number"
                placeholder="留空=全部用户"
                class="rounded-xl pl-9"
              />
            </div>
          </div>
          <div class="flex flex-col gap-2">
            <Label
              for="audit-keyword-input"
              class="text-sm font-medium"
            >IP / 关键词</Label>
            <div class="relative">
              <Globe class="size-4 absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground" />
              <Input
                id="audit-keyword-input"
                v-model="filters.keyword"
                type="text"
                placeholder="匹配 IP / 详情 / 错误码"
                class="rounded-xl pl-9"
                @keyup.enter="applyFilters"
              />
            </div>
          </div>
          <div class="flex flex-col gap-2">
            <Label
              for="audit-resource-input"
              class="text-sm font-medium"
            >资源类型</Label>
            <div class="relative">
              <FileText class="size-4 absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground" />
              <Input
                id="audit-resource-input"
                v-model="filters.resourceType"
                type="text"
                placeholder="如 post / comment / user"
                class="rounded-xl pl-9"
                @keyup.enter="applyFilters"
              />
            </div>
          </div>
          <div class="flex flex-col gap-2 md:col-span-2 xl:col-span-2">
            <Label class="text-sm font-medium flex items-center gap-1.5">
              <CalendarDays class="size-3.5 text-primary" />
              日期范围
              <span class="text-xs text-muted-foreground font-normal ml-1">
                （选完开始会自动弹出结束，结束不能早于开始）
              </span>
            </Label>
            <div class="flex items-center gap-2 rounded-xl border border-border/60 bg-background/60 px-3 py-2">
              <div class="relative group flex-1">
                <input
                  v-model="filters.fromDate"
                  type="date"
                  aria-label="开始日期"
                  class="w-full h-9 rounded-lg border border-transparent bg-transparent px-2.5 text-sm text-foreground transition-colors hover:border-border focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus:bg-background"
                  :max="startMax"
                  placeholder="开始日期"
                  @change="onFromDateChange"
                >
                <button
                  v-if="filters.fromDate"
                  type="button"
                  class="pointer-events-auto absolute right-1.5 top-1/2 -translate-y-1/2 opacity-0 group-hover:opacity-100 transition-opacity rounded-full p-0.5 hover:bg-muted text-muted-foreground hover:text-foreground"
                  title="清除开始日期"
                  aria-label="清除开始日期"
                  @click="filters.fromDate = ''"
                >
                  <X class="size-3.5" />
                </button>
              </div>
              <ChevronRight class="size-4 text-muted-foreground shrink-0" />
              <div class="relative group flex-1">
                <input
                  ref="toDateInputRef"
                  v-model="filters.toDate"
                  type="date"
                  aria-label="结束日期"
                  class="w-full h-9 rounded-lg border border-transparent bg-transparent px-2.5 text-sm text-foreground transition-colors hover:border-border focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus:bg-background"
                  :min="endMin"
                  :max="endMax"
                  placeholder="结束日期"
                  @change="onToDateChange"
                >
                <button
                  v-if="filters.toDate"
                  type="button"
                  class="pointer-events-auto absolute right-1.5 top-1/2 -translate-y-1/2 opacity-0 group-hover:opacity-100 transition-opacity rounded-full p-0.5 hover:bg-muted text-muted-foreground hover:text-foreground"
                  title="清除结束日期"
                  aria-label="清除结束日期"
                  @click="filters.toDate = ''"
                >
                  <X class="size-3.5" />
                </button>
              </div>
              <div
                v-if="dateRangeError"
                class="shrink-0 pl-2"
              >
                <Tooltip>
                  <TooltipTrigger as-child>
                    <AlertTriangle class="size-4 text-warning shrink-0" />
                  </TooltipTrigger>
                  <TooltipContent class="text-xs">
                    {{ dateRangeError }}
                  </TooltipContent>
                </Tooltip>
              </div>
            </div>
          </div>
        </div>
        <div class="mt-4 flex items-center justify-between gap-2">
          <div
            v-if="appliedSummary"
            class="text-xs text-muted-foreground flex items-center gap-1.5"
          >
            <Filter class="size-3.5 text-primary" />
            <span>{{ appliedSummary }}</span>
          </div>
          <div class="ml-auto flex items-center gap-2">
            <Button
              variant="outline"
              class="rounded-xl"
              @click="resetFilters"
            >
              <RotateCcw
                data-icon="inline-start"
                class="mr-1.5"
              /> 重置
            </Button>
            <Button
              class="rounded-xl shadow-sm"
              :disabled="loading"
              @click="applyFilters"
            >
              <Filter
                data-icon="inline-start"
                class="mr-1.5"
              />
              应用筛选
            </Button>
          </div>
        </div>
      </div>
    </AdminCard>

    <AdminCard class="overflow-hidden">
      <div class="p-0">
        <div
          v-if="loading"
          class="flex flex-col gap-3 p-6"
        >
          <Skeleton
            v-for="i in 6"
            :key="i"
            class="h-16 rounded-xl"
          />
        </div>
        <div
          v-else-if="loadError"
          class="p-12"
        >
          <Alert
            variant="destructive"
            class="rounded-xl max-w-lg mx-auto"
          >
            <AlertTriangle class="size-4" />
            <AlertTitle>日志加载失败</AlertTitle>
            <AlertDescription class="flex flex-wrap items-center justify-between gap-3">
              <span>{{ loadError }}</span>
              <Button
                variant="outline"
                size="sm"
                class="rounded-lg shrink-0"
                @click="loadLogs()"
              >
                <RotateCcw data-icon="inline-start" />
                重试
              </Button>
            </AlertDescription>
          </Alert>
        </div>
        <div
          v-else
          class="divide-y divide-border"
        >
          <div
            v-for="log in logs"
            :key="log.id"
            class="px-5 py-4 hover:bg-muted/30 transition-colors cursor-pointer group"
            @click="toggleExpand(log.id)"
          >
            <div class="flex items-start gap-4">
              <div class="pt-1">
                <UserAvatar
                  :avatar="log.avatar"
                  :resolved-avatar-url="log.resolved_avatar_url"
                  :seed="`${log.username || 'user'}|${log.user_id ?? ''}`"
                  :name="log.username || `User #${log.user_id ?? '-'}`"
                  :size="36"
                  :show-title="false"
                  class="border border-border"
                />
              </div>
              <div class="flex-1 min-w-0">
                <div class="flex flex-wrap items-center gap-2">
                  <span class="font-semibold">{{ log.username ?? `用户 #${log.user_id ?? '-'}` }}</span>
                  <Badge
                    :class="actionClass(log.action)"
                    class="rounded-full text-[11px]"
                  >
                    {{ actionLabel(log.action) }}
                  </Badge>
                  <span class="text-xs text-muted-foreground tabular-nums">
                    ·
                    <span v-if="log.target_type">{{ log.target_type }}</span>
                    <span
                      v-if="log.target_id"
                      class="font-mono"
                    > #{{ log.target_id }}</span>
                  </span>
                </div>
                <div class="mt-1 flex flex-wrap items-center gap-x-4 gap-y-1 text-xs text-muted-foreground tabular-nums">
                  <span class="flex items-center gap-1">
                    <Clock class="size-3.5" />
                    {{ formatAdminDateTime(log.created_at) }}
                  </span>
                  <span
                    v-if="log.ip"
                    class="flex items-center gap-1"
                  >
                    <Globe class="size-3.5" /> {{ log.ip }}
                  </span>
                  <span
                    v-if="log.user_agent"
                    class="flex items-center gap-1 max-w-md truncate"
                    :title="log.user_agent"
                  >
                    <Monitor class="size-3.5" /> {{ log.user_agent }}
                  </span>
                </div>
              </div>
              <div class="flex items-center gap-1 shrink-0 pt-1">
                <Button
                  variant="ghost"
                  size="icon-sm"
                  class="opacity-0 group-hover:opacity-100 transition-opacity"
                  title="展开 / 收起详情"
                  :aria-label="expandedId === log.id ? '收起详情' : '展开详情'"
                  @click.stop="toggleExpand(log.id)"
                >
                  <ChevronDown
                    data-icon="inline-start"
                    class="transition-transform"
                    :class="{ 'rotate-180': expandedId === log.id }"
                  />
                </Button>
              </div>
            </div>
            <div
              v-if="expandedId === log.id"
              class="mt-4 rounded-xl border border-border bg-muted/30 p-4 overflow-x-auto"
            >
              <div class="flex items-center justify-between mb-2">
                <span class="text-xs font-semibold text-muted-foreground uppercase tracking-wide">详细详情 details（JSON）</span>
              </div>
              <pre class="text-xs font-mono leading-relaxed whitespace-pre-wrap break-all">
{{ log.details ? JSON.stringify(log.details, null, 2) : '（无附加数据）' }}
              </pre>
            </div>
          </div>
        </div>
        <div
          v-if="logs.length === 0 && !loading && !loadError"
          class="p-12"
        >
          <Alert
            variant="info"
            class="rounded-xl max-w-lg mx-auto"
          >
            <Info class="size-4" />
            <AlertTitle>暂无日志</AlertTitle>
            <AlertDescription>当前筛选条件下没有匹配的操作记录，尝试调整筛选条件或等待新操作。</AlertDescription>
          </Alert>
        </div>
        <div
          v-if="logs.length > 0"
          class="p-4 pt-0 mt-2"
        >
          <AdminPagination
            v-model:page="page"
            v-model:page-size="pageSize"
            :total="total"
            :page-size-options="[15, 30, 50, 100]"
            @update:page="loadLogs()"
          />
        </div>
      </div>
    </AdminCard>

    <DangerConfirmDialog
      v-model:open="cleanupOpen"
      title="清理历史操作日志"
      :description="cleanupDescription"
      confirm-text="确认清理"
      confirm-phrase="清理日志"
      :on-confirm="runCleanup"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted, watch, computed, nextTick } from 'vue'
import {
  fetchAdminAuditLogs,
  formatAdminDateTime,
  type AdminAuditLog,
  exportAdminAuditLogs,
  cleanupAdminAuditLogs,
  downloadBlob
} from '~~/composables/useAdminManage'
import { useToast } from '~~/composables/useToast'
import { extractApiErrorMessage } from '~~/lib/utils'
import { toYMD } from '~~/lib/datetime'
import {
  FileSearch, FileText, Search, Filter, RotateCcw, Clock, Globe, Monitor, Info,
  ChevronRight, ChevronDown, X, CalendarDays, AlertTriangle
} from '@lucide/vue'
import { Button } from '~~/components/ui/button'
import AdminCard from '~~/components/admin/AdminCard.vue'
import { Label } from '~~/components/ui/label'
import { Input } from '~~/components/ui/input'
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue
} from '~~/components/ui/select'
import { Skeleton } from '~~/components/ui/skeleton'
import { Badge } from '~~/components/ui/badge'
import { Alert, AlertTitle, AlertDescription } from '~~/components/ui/alert'
import {
  Tooltip, TooltipContent, TooltipTrigger
} from '~~/components/ui/tooltip'
import UserAvatar from '~~/components/UserAvatar.vue'
import DangerConfirmDialog from '~~/components/admin/tools/DangerConfirmDialog.vue'

definePageMeta({ ssr: false, layout: 'admin' })

const toast = useToast()

/**
 * 操作类型下拉是「常用值快捷方式」，不是枚举白名单：后端 action 是自由字符串
 * （advanced.py::OperationLogEntryOut，另有插件/webhook 自注册的动作），无 distinct 接口可查。
 * 不在名单里的动作照常渲染：actionLabel 未命中时回退原始字符串、actionClass 回退中性灰底，
 * 所以新动作不会出现空标签或碎样式；这里只列已在后端/插件里稳定出现的值。
 */
const actionOptions = [
  { label: '登录 login', value: 'login' },
  { label: '注册 register', value: 'register' },
  { label: '创建 create', value: 'create' },
  { label: '更新 update', value: 'update' },
  { label: '删除 delete', value: 'delete' },
  { label: '恢复 restore', value: 'restore' },
  { label: '彻底删除 permanent_delete', value: 'permanent_delete' },
  { label: '批量发布 batch_publish', value: 'batch_publish' },
  { label: '导出 export', value: 'export' },
  { label: '导入 import', value: 'import' },
  { label: '封禁 ban', value: 'ban' },
  { label: '解封 unban', value: 'unban' },
  { label: '设置 settings', value: 'settings' },
  { label: '迁移 migrate', value: 'migrate' },
  { label: '触发 trigger', value: 'trigger' }
]

function actionLabel(a: string): string {
  const find = actionOptions.find(o => o.value === a)
  if (find) return find.label.split(' ')[0] ?? a
  const map: Record<string, string> = {
    login: '登录', create: '创建', update: '更新', delete: '删除',
    export: '导出', import: '导入', ban: '封禁', unban: '解封',
    register: '注册', settings: '设置', trigger: '触发', migrate: '迁移'
  }
  return map[a] ?? a
}

function actionClass(a: string): string {
  const low = a.toLowerCase()
  if (['login', 'register'].includes(low)) return 'bg-info-muted text-info-muted-foreground border-transparent'
  if (['create', 'import', 'batch_publish'].includes(low)) return 'bg-success-muted text-success-muted-foreground border-transparent'
  if (['update', 'settings', 'export', 'trigger', 'migrate', 'restore'].includes(low)) return 'bg-warning-muted text-warning-muted-foreground border-transparent'
  if (['delete', 'ban', 'permanent_delete'].includes(low)) return 'bg-error-muted text-error-muted-foreground border-transparent'
  return 'bg-muted text-muted-foreground'
}

const loading = ref(true)
const loadError = ref('')
const logs = shallowRef<AdminAuditLog[]>([])
const page = ref(1)
const pageSize = ref(15)
const total = ref(0)
const expandedId = ref<number | null>(null)
/** 导出中标记：兼作按钮禁用与文案切换，避免连点起两个下载。 */
const exporting = ref<'' | 'csv' | 'json'>('')

/**
 * 手动清理：值必须是字符串（reka-ui Select 的 value 口径），调用时再转数字。
 * 后端 days 允许 1–3650，这里只给常用档位，避免管理员误填成"保留 1 天"而清空留痕。
 */
const cleanupDayOptions = ['7', '30', '90', '180', '365']
const cleanupDays = ref('90')
const cleanupOpen = ref(false)
const cleanupDescription = computed(() =>
  `将删除 ${cleanupDays.value} 天之前的操作日志记录，并保留最近 ${cleanupDays.value} 天的留痕。`
  + '此操作不可撤销：删掉之后无法再追溯那些动作是谁、从哪台设备做的。'
  + '访问日志与性能指标不在本接口范围内，由服务端保留策略定时处理。'
)

const toDateInputRef = ref<HTMLInputElement | null>(null)

const filters = reactive({
  action: '',
  userId: undefined as number | undefined,
  keyword: '',
  resourceType: '',
  fromDate: '',
  toDate: ''
})

const todayStr = computed(() => toYMD())
const startMax = computed(() => filters.toDate || todayStr.value)
const endMin = computed(() => filters.fromDate || '')
const endMax = todayStr

const dateRangeError = computed(() => {
  if (filters.fromDate && filters.toDate && filters.fromDate > filters.toDate) {
    return '结束日期不能早于开始日期，已自动修正为开始日期。'
  }
  return ''
})

const appliedSummary = computed(() => {
  const parts: string[] = []
  if (filters.action) {
    const o = actionOptions.find(x => x.value === filters.action)
    parts.push(`类型：${o?.label ?? filters.action}`)
  }
  if (filters.userId) parts.push(`用户 ID：${filters.userId}`)
  if (filters.keyword.trim()) parts.push(`IP/关键词：${filters.keyword.trim()}`)
  if (filters.resourceType.trim()) parts.push(`资源类型：${filters.resourceType.trim()}`)
  if (filters.fromDate || filters.toDate) {
    const s = filters.fromDate || '不限'
    const e = filters.toDate || '不限'
    parts.push(`日期：${s} 至 ${e}`)
  }
  return parts.length ? `当前筛选：${parts.join('，')}` : ''
})

watch(() => filters.fromDate, (val) => {
  if (!val) return
  if (filters.toDate && val > filters.toDate) {
    filters.toDate = val
  }
  nextTick(() => {
    if (!filters.toDate && toDateInputRef.value) {
      toDateInputRef.value.showPicker?.()
      toDateInputRef.value.focus()
    }
  })
})

function onFromDateChange(_e: Event) {
  // v-model 已完成同步，watch 负责联动 & 自动弹出
}

function onToDateChange(_e: Event) {
  if (filters.toDate && filters.fromDate && filters.toDate < filters.fromDate) {
    // 二次拦截：如果用户绕过 min 限制（例如通过键盘输入），自动拉平并 toast
    filters.toDate = filters.fromDate
    toast.warning('结束日期不能早于开始日期，已自动调整。')
  }
}

function toggleExpand(id: number) {
  expandedId.value = expandedId.value === id ? null : id
}

/**
 * 导出走 /admin/logs/export：把包装层支持的筛选（类型/用户/日期）原样带上（后端上限 1000 条）。
 * exportAdminAuditLogs 的 filters 形参不收录 q / resource_type（包装层不在本次改动范围，
 * 且它在内部逐键拼 query，页侧传了也到不了请求），因此这两个条件生效时提示语必须如实声明
 * "导出不含该条件"，否则用户会拿到一份与屏幕不一致的文件还以为同源。
 */
async function handleExport(format: 'csv' | 'json') {
  exporting.value = format
  try {
    const blob = await exportAdminAuditLogs(format, {
      action: filters.action,
      userId: filters.userId,
      fromDate: filters.fromDate,
      toDate: filters.toDate
    })
    downloadBlob(blob, `operation-logs-${todayStr.value}.${format}`)
    const narrow = filters.keyword.trim() || filters.resourceType.trim()
      ? '（注意：IP/关键词与资源类型条件不参与导出）'
      : ''
    toast.success(`已导出 ${format.toUpperCase()}（按当前可导出筛选，最多 1000 条）${narrow}`)
  } catch {
    // apiFetch 已把失败原因 toast 出来，这里只需解除按钮禁用
  } finally {
    exporting.value = ''
  }
}

/**
 * 由 DangerConfirmDialog 的 onConfirm 调用：请求失败时抛错 → 弹窗保持打开并内联展示，不会误报"已清理"。
 * 成功口径取接口返回的真实截止时间，且必须重读列表——记录已经在库里没了，界面上却还留着行。
 */
async function runCleanup() {
  const r = await cleanupAdminAuditLogs(Number(cleanupDays.value))
  const cutoff = formatAdminDateTime(r?.before)
  const deleted = r?.deleted_count ?? 0
  if (deleted > 0) {
    toast.success(`已清理 ${deleted} 条早于 ${cutoff} 的操作日志`)
  } else {
    toast.info(`保留期内没有需要清理的日志（截止时间 ${cutoff}）`)
  }
  page.value = 1
  await loadLogs()
}

function resetFilters() {
  filters.action = ''
  filters.userId = undefined
  filters.keyword = ''
  filters.resourceType = ''
  filters.fromDate = ''
  filters.toDate = ''
  page.value = 1
  loadLogs()
}

/** 应用筛选：条件变化后必须回到第 1 页，否则可能停留在越界空页 */
function applyFilters() {
  page.value = 1
  loadLogs()
}

async function loadLogs(retryOnClamp = true) {
  loading.value = true
  loadError.value = ''
  try {
    // q / resource_type 是后端 list_operation_logs 已支持的查询参数；
    // fetchAdminAuditLogs 会把 params 原样 spread 进 query，但包装层签名尚未收录这两个键
    // （useAdminManage 不在本次改动范围），这里用交集类型在页侧补齐，运行期即按后端口径转发。
    const params: Parameters<typeof fetchAdminAuditLogs>[0] & { q?: string, resource_type?: string } = {
      page: page.value,
      page_size: pageSize.value
    }
    if (filters.action) params.action = filters.action
    if (filters.userId) params.user_id = filters.userId
    if (filters.keyword.trim()) params.q = filters.keyword.trim()
    if (filters.resourceType.trim()) params.resource_type = filters.resourceType.trim()
    if (filters.fromDate) params.from = filters.fromDate
    if (filters.toDate) params.to = filters.toDate
    const r = await fetchAdminAuditLogs(params)
    logs.value = r?.items ?? []
    total.value = r?.total ?? 0
    // 结果集缩小时钳制回最后一页，避免停在越界空页（仅重试一次防循环）
    const maxPage = Math.max(1, Math.ceil(total.value / pageSize.value))
    if (retryOnClamp && logs.value.length === 0 && total.value > 0 && page.value > maxPage) {
      page.value = maxPage
      await loadLogs(false)
    }
  } catch (e) {
    logs.value = []
    // fetchAdminAuditLogs 内部的 apiFetch 已经 toast，这里只做内联错误态，避免双重提示
    const err = e as { data?: unknown, message?: string }
    loadError.value = extractApiErrorMessage(err?.data, err?.message || '加载日志失败')
  } finally {
    loading.value = false
  }
}

onMounted(loadLogs)
</script>
