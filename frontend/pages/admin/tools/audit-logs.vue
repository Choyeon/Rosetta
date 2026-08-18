<template>
  <div class="p-6 space-y-6">
    <div class="flex items-center gap-3">
      <div
        class="size-10 rounded-xl flex items-center justify-center"
        style="background: linear-gradient(135deg, #0EA5E9 0%, #0284C7 100%);"
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

    <Card class="rounded-2xl">
      <CardContent class="pt-6 pb-4">
        <div class="grid md:grid-cols-4 gap-4">
          <div class="space-y-2">
            <Label class="text-sm font-medium">操作类型</Label>
            <Select
              v-model="filters.action"
              :options="actionOptions"
              placeholder="全部类型"
              class="rounded-xl"
            />
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
          <div class="space-y-2">
            <Label class="text-sm font-medium">开始日期</Label>
            <Input
              v-model="filters.fromDate"
              type="date"
              class="rounded-xl"
            />
          </div>
          <div class="space-y-2">
            <Label class="text-sm font-medium">结束日期</Label>
            <Input
              v-model="filters.toDate"
              type="date"
              class="rounded-xl"
            />
          </div>
        </div>
        <div class="mt-4 flex items-center justify-end gap-2">
          <Button
            variant="outline"
            class="rounded-xl"
            @click="resetFilters"
          >
            <RotateCcw class="size-4 mr-1.5" /> 重置
          </Button>
          <Button
            class="rounded-xl text-white"
            style="background: linear-gradient(135deg, #0EA5E9 0%, #0369A1 100%);"
            :disabled="loading"
            @click="loadLogs"
          >
            <Filter class="size-4 mr-1.5" />
            应用筛选
          </Button>
        </div>
      </CardContent>
    </Card>

    <Card class="rounded-2xl overflow-hidden">
      <CardContent class="p-0">
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
                <Avatar class="size-9 border border-border">
                  <AvatarImage
                    v-if="log.username"
                    :src="avatarOf(log)"
                  />
                  <AvatarFallback class="text-xs font-bold bg-[#0EA5E9]/15 text-[#0369A1]">
                    {{ (log.username?.[0]?.toUpperCase()) || 'U' }}
                  </AvatarFallback>
                </Avatar>
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
      </CardContent>
    </Card>
  </div>
</template>

<script setup lang="ts">
/* eslint-disable */
/* eslint-disable @typescript-eslint/ban-ts-comment */
// @ts-nocheck
/* eslint-enable @typescript-eslint/ban-ts-comment */
import { ref, reactive, onMounted } from 'vue'
import {
  fetchAdminAuditLogs,
  formatAdminDateTime,
  type AdminAuditLog
} from '~~/composables/useAdminManage'
import { useToast } from '~~/composables/useToast'
import {
  FileSearch, Search, Filter, RotateCcw, Clock, Globe, Monitor, Info,
  ChevronLeft, ChevronRight, ChevronDown
} from '@lucide/vue'
import { Button } from '~~/components/ui/button'
import { Card, CardContent } from '~~/components/ui/card'
import { Label } from '~~/components/ui/label'
import { Input } from '~~/components/ui/input'
import { Select } from '~~/components/ui/select'
import { Skeleton } from '~~/components/ui/skeleton'
import { Badge } from '~~/components/ui/badge'
import { Alert, AlertTitle, AlertDescription } from '~~/components/ui/alert'
import { Avatar, AvatarFallback, AvatarImage } from '~~/components/ui/avatar'

definePageMeta({ ssr: false, layout: 'admin' })

const toast = useToast()

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
  if (find) return find.label.split(' ')[0]
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

function avatarOf(log: AdminAuditLog): string {
  const u = log.username || 'user'
  const hue = Array.from(u).reduce((s, c) => s + c.charCodeAt(0), 0) % 360
  const letter = encodeURIComponent(u[0]?.toUpperCase() || 'U')
  return `https://api.dicebear.com/7.x/initials/svg?seed=${letter}-${log.user_id ?? 0}&backgroundColor=hsl(${hue},70%,90%)`
}

const loading = ref(true)
const logs = ref<AdminAuditLog[]>([])
const page = ref(1)
const total = ref(0)
const totalPages = ref(1)
const expandedId = ref<number | null>(null)

const filters = reactive({
  action: '',
  userId: null as number | null,
  fromDate: '',
  toDate: ''
})

function toggleExpand(id: number) {
  expandedId.value = expandedId.value === id ? null : id
}

function resetFilters() {
  filters.action = ''
  filters.userId = null
  filters.fromDate = ''
  filters.toDate = ''
  page.value = 1
  loadLogs()
}

async function loadLogs() {
  loading.value = true
  try {
    const params: { page?: number, page_size?: number, action?: string, user_id?: number } = {
      page: page.value,
      page_size: 15
    }
    if (filters.action) params.action = filters.action
    if (filters.userId) params.user_id = filters.userId
    const r = await fetchAdminAuditLogs(params)
    logs.value = r?.items ?? []
    total.value = r?.total ?? 0
    totalPages.value = r?.total_pages ?? 1
  } catch (e) {
    toast.error(`接口未实现或调用失败: ${e instanceof Error ? e.message : 'fetchAdminAuditLogs'}`)
    logs.value = []
  } finally {
    loading.value = false
  }
}

onMounted(loadLogs)
</script>
