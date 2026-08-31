<template>
  <div class="p-6 space-y-6">
    <div class="flex items-center gap-3">
      <div
        class="size-10 rounded-xl flex items-center justify-center bg-primary text-primary-foreground"
      >
        <FileSearch class="size-5 text-white" />
      </div>
      <div>
        <h1 class="text-xl font-bold tracking-tight">
          操作审计日志
        </h1>
        <p class="text-sm text-muted-foreground">
          管理员与登录用户的操作留痕
        </p>
      </div>
    </div>

    <AdminCard>
      <div class="pt-6 pb-4">
        <div class="grid md:grid-cols-2 xl:grid-cols-4 gap-4">
          <div class="space-y-2">
            <Label class="text-sm font-medium">操作类型</Label>
            <Select
              v-model="filters.action"
              class="rounded-xl"
            >
              <SelectTrigger class="rounded-xl">
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
          <div class="space-y-2">
            <Label class="text-sm font-medium">用户 ID 搜索</Label>
            <div class="relative">
              <Search class="size-4 absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground" />
              <Input
                v-model.number="filters.userId"
                type="number"
                placeholder="留空=全部用户"
                class="rounded-xl pl-9"
              />
            </div>
          </div>
          <div class="space-y-2 md:col-span-2 xl:col-span-2">
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
              <RotateCcw class="size-4 mr-1.5" /> 重置
            </Button>
            <Button
              class="rounded-xl shadow-sm"
              :disabled="loading"
              @click="loadLogs"
            >
              <Filter class="size-4 mr-1.5" />
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
          class="p-6 space-y-3"
        >
          <Skeleton
            v-for="i in 6"
            :key="i"
            class="h-16 rounded-xl"
          />
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
                  @click.stop="toggleExpand(log.id)"
                >
                  <ChevronDown
                    class="size-4 transition-transform"
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
          v-if="logs.length === 0 && !loading"
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
          <div class="flex items-center justify-between text-xs text-muted-foreground">
            <span>第 {{ page }} / {{ Math.max(1, totalPages) }} 页，共 {{ total }} 条</span>
            <div class="flex gap-1">
              <Button
                variant="outline"
                size="icon-sm"
                class="rounded-lg"
                :disabled="page <= 1"
                @click="page--; loadLogs()"
              >
                <ChevronLeft class="size-4" />
              </Button>
              <Button
                variant="outline"
                size="icon-sm"
                class="rounded-lg"
                :disabled="page >= totalPages"
                @click="page++; loadLogs()"
              >
                <ChevronRight class="size-4" />
              </Button>
            </div>
          </div>
        </div>
      </div>
    </AdminCard>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted, watch, computed, nextTick } from 'vue'
import {
  fetchAdminAuditLogs,
  formatAdminDateTime,
  type AdminAuditLog
} from '~~/composables/useAdminManage'
import { useToast } from '~~/composables/useToast'
import {
  FileSearch, Search, Filter, RotateCcw, Clock, Globe, Monitor, Info,
  ChevronLeft, ChevronRight, ChevronDown, X, CalendarDays, AlertTriangle
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

definePageMeta({ ssr: false, layout: 'admin' })

const _toast = useToast()

const actionOptions = [
  { label: '登录 login', value: 'login' },
  { label: '创建 create', value: 'create' },
  { label: '更新 update', value: 'update' },
  { label: '删除 delete', value: 'delete' },
  { label: '导出 export', value: 'export' },
  { label: '导入 import', value: 'import' },
  { label: '封禁 ban', value: 'ban' },
  { label: '设置 settings', value: 'settings' }
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
  if (['login', 'register'].includes(low)) return 'bg-info-muted text-info-foreground border-transparent'
  if (['create', 'import'].includes(low)) return 'bg-success-muted text-success-foreground border-transparent'
  if (['update', 'settings', 'export', 'trigger', 'migrate'].includes(low)) return 'bg-warning-muted text-warning-foreground border-transparent'
  if (['delete', 'ban'].includes(low)) return 'bg-error-muted text-error-foreground border-transparent'
  return 'bg-muted text-muted-foreground'
}

const loading = ref(true)
const logs = ref<AdminAuditLog[]>([])
const page = ref(1)
const total = ref(0)
const totalPages = ref(1)
const expandedId = ref<number | null>(null)

const toDateInputRef = ref<HTMLInputElement | null>(null)

const filters = reactive({
  action: '',
  userId: undefined as number | undefined,
  fromDate: '',
  toDate: ''
})

const todayStr = computed(() => {
  const d = new Date()
  const y = d.getFullYear()
  const m = String(d.getMonth() + 1).padStart(2, '0')
  const day = String(d.getDate()).padStart(2, '0')
  return `${y}-${m}-${day}`
})
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
    _toast.warning('结束日期不能早于开始日期，已自动调整。')
  }
}

function toggleExpand(id: number) {
  expandedId.value = expandedId.value === id ? null : id
}

function resetFilters() {
  filters.action = ''
  filters.userId = undefined
  filters.fromDate = ''
  filters.toDate = ''
  page.value = 1
  loadLogs()
}

async function loadLogs() {
  loading.value = true
  try {
    const params: Parameters<typeof fetchAdminAuditLogs>[0] = {
      page: page.value,
      page_size: 15
    }
    if (filters.action) params.action = filters.action
    if (filters.userId) params.user_id = filters.userId
    if (filters.fromDate) params.from = filters.fromDate
    if (filters.toDate) params.to = filters.toDate
    const r = await fetchAdminAuditLogs(params)
    logs.value = r?.items ?? []
    total.value = r?.total ?? 0
    totalPages.value = r?.total_pages ?? 1
  } catch (e) {
    logs.value = []
    const msg = e instanceof Error ? e.message : '加载日志失败'
    _toast.error(msg)
  } finally {
    loading.value = false
  }
}

onMounted(loadLogs)
</script>
