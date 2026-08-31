<script setup lang="ts">
import { ref, reactive, computed, onMounted } from 'vue'
import { toast } from 'vue-sonner'
import { apiFetch } from '~~/composables/useApi'
import {
  Search,
  RefreshCw,
  FolderSearch,
  UploadCloud,
  Trash2,
  Cog,
  ArrowUpCircle,
  ChevronDown,
  Check,
  AlertTriangle,
  Puzzle,
  X,
  Sparkles,
  Download
} from '@lucide/vue'
import { Button } from '~~/components/ui/button'
import { Input } from '~~/components/ui/input'
import { Badge } from '~~/components/ui/badge'
import { Checkbox } from '~~/components/ui/checkbox'
import { Switch } from '~~/components/ui/switch'
import { Label } from '~~/components/ui/label'
import { Textarea } from '~~/components/ui/textarea'
import Table from '~~/components/ui/table/Table.vue'
import TableHeader from '~~/components/ui/table/TableHeader.vue'
import TableBody from '~~/components/ui/table/TableBody.vue'
import TableHead from '~~/components/ui/table/TableHead.vue'
import TableRow from '~~/components/ui/table/TableRow.vue'
import TableCell from '~~/components/ui/table/TableCell.vue'
import { Card, CardContent } from '~~/components/ui/card'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogClose
} from '~~/components/ui/dialog'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuGroup,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger
} from '~~/components/ui/dropdown-menu'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue
} from '~~/components/ui/select'
import TableSkeleton from '~~/components/admin/TableSkeleton.vue'

interface JsonSchemaNode {
  type?: string
  format?: string
  title?: string
  description?: string
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  enum?: any[]
}

interface JsonSchema {
  properties?: Record<string, JsonSchemaNode>
}

interface Plugin {
  id: number
  slug: string
  name: string
  version: string
  author: string | null
  description: string | null
  status: 'inactive' | 'active' | 'error' | 'installed'
  settings_schema?: JsonSchema | null
  settings?: Record<string, unknown> | null
  update_available: boolean
  installed_at: string | null
  activated_at: string | null
  error_message: string | null
}

interface BulkResponse {
  success?: number
  total?: number
}

const { t: $_t } = useI18n()
const t = (k: string, fallback: string) => {
  try {
    const v = $_t(k)
    return v && v !== k ? v : fallback
  } catch {
    return fallback
  }
}

function $get<T>(url: string, opts?: Record<string, unknown>) {
  return apiFetch<T>(url, { method: 'GET', ...opts })
}
function $post<T>(url: string, body?: unknown, opts?: Record<string, unknown>) {
  return apiFetch<T>(url, { method: 'POST', body, ...opts })
}
function $patch<T>(url: string, body?: unknown, opts?: Record<string, unknown>) {
  return apiFetch<T>(url, { method: 'PATCH', body, ...opts })
}
function $delete<T>(url: string, opts?: Record<string, unknown>) {
  return apiFetch<T>(url, { method: 'DELETE', ...opts })
}

const plugins = ref<Plugin[]>([])
const loading = ref(true)
const search = ref('')
const statusFilter = ref<'all' | 'active' | 'inactive' | 'error'>('all')
const selected = ref<Set<string>>(new Set())
const perPage = ref(20)
const page = ref(1)

const settingsOpen = ref(false)
const confirmDeleteOpen = ref(false)
const currentPlugin = ref<Plugin | null>(null)
const settingsForm = reactive<Record<string, unknown>>({})

const totalInstalled = computed(() => plugins.value.length)
const activeCount = computed(() => plugins.value.filter(p => p.status === 'active').length)
const inactiveCount = computed(() => plugins.value.filter(p => p.status === 'inactive' || p.status === 'installed').length)
const errorCount = computed(() => plugins.value.filter(p => p.status === 'error').length)
const updatableCount = computed(() => plugins.value.filter(p => p.update_available).length)

const filtered = computed(() => {
  const q = search.value.trim().toLowerCase()
  return plugins.value.filter((p) => {
    if (statusFilter.value === 'active' && p.status !== 'active') return false
    if (statusFilter.value === 'inactive' && !(p.status === 'inactive' || p.status === 'installed')) return false
    if (statusFilter.value === 'error' && p.status !== 'error') return false
    if (!q) return true
    if (p.name.toLowerCase().includes(q)) return true
    if (p.slug.toLowerCase().includes(q)) return true
    if (p.description && p.description.toLowerCase().includes(q)) return true
    return false
  })
})

const totalCount = computed(() => filtered.value.length)
const totalPages = computed(() => Math.max(1, Math.ceil(totalCount.value / perPage.value)))

const paginated = computed(() => {
  const start = (page.value - 1) * perPage.value
  return filtered.value.slice(start, start + perPage.value)
})

const allSelected = computed({
  get: () => paginated.value.length > 0 && paginated.value.every(r => selected.value.has(r.slug)),
  set: (v: boolean) => {
    if (v) {
      paginated.value.forEach(r => selected.value.add(r.slug))
    } else {
      paginated.value.forEach(r => selected.value.delete(r.slug))
    }
    selected.value = new Set(selected.value)
  }
})

const statusLabel = (s: Plugin['status']) => {
  switch (s) {
    case 'active': return t('admin.plugins.status.active', '已启用')
    case 'inactive': return t('admin.plugins.status.inactive', '已禁用')
    case 'error': return t('admin.plugins.status.error', '异常')
    case 'installed': return t('admin.plugins.status.installed', '已安装')
    default: return s
  }
}
const statusVariant = (s: Plugin['status']) => {
  if (s === 'active') return 'success'
  if (s === 'error') return 'destructive'
  return 'outline'
}

function toggleSel(slug: string, checked: boolean) {
  if (checked) selected.value.add(slug)
  else selected.value.delete(slug)
  selected.value = new Set(selected.value)
}

async function load() {
  try {
    const data = await $get<unknown>('/admin/plugins')
    const obj = data as { data?: Plugin[] } | Plugin[]
    plugins.value = (obj && typeof obj === 'object' && 'data' in obj ? (obj.data as Plugin[]) : Array.isArray(obj) ? obj : null) ?? []
  } catch {
    plugins.value = []
  } finally {
    loading.value = false
  }
}

function reload() {
  loading.value = true
  load()
}

async function scan() {
  try {
    await $post('/admin/plugins/scan')
    toast.success(t('admin.plugins.scanDone', '扫描完成'))
  } catch {
    /* toast handled by apiFetch */
  } finally {
    reload()
  }
}

async function onToggleStatus(row: Plugin, val: boolean) {
  try {
    await $patch(`/admin/plugins/${row.slug}/status`, { enabled: val })
    toast.success(val ? t('admin.plugins.activated', '已启用') : t('admin.plugins.deactivated', '已禁用'))
  } catch {
    /* handled */
  } finally {
    reload()
  }
}

function openSettings(row: Plugin) {
  currentPlugin.value = row
  const fresh: Record<string, unknown> = {}
  Object.assign(fresh, row.settings ?? {})
  for (const k of Object.keys(settingsForm)) {
    // eslint-disable-next-line @typescript-eslint/no-dynamic-delete
    delete settingsForm[k]
  }
  Object.assign(settingsForm, fresh)
  settingsOpen.value = true
}

async function saveSettings() {
  if (!currentPlugin.value) return
  try {
    await $patch(`/admin/plugins/${currentPlugin.value.slug}/settings`, {
      slug: currentPlugin.value.slug,
      settings: { ...settingsForm }
    })
    toast.success(t('admin.plugins.settingsSaved', '设置已保存'))
    settingsOpen.value = false
    reload()
  } catch {
    /* handled */
  }
}

function confirmDelete(row: Plugin) {
  currentPlugin.value = row
  confirmDeleteOpen.value = true
}

function confirmDeleteBulk() {
  currentPlugin.value = null
  confirmDeleteOpen.value = true
}

async function doDelete() {
  try {
    if (currentPlugin.value) {
      await $delete(`/admin/plugins/${currentPlugin.value.slug}`)
      toast.success(t('admin.plugins.deleted', '插件已删除'))
    } else if (selected.value.size > 0) {
      await $post('/admin/plugins/_bulk', { action: 'delete', slugs: [...selected.value] })
      toast.success(t('admin.plugins.bulkDeleted', '批量删除完成'))
      selected.value.clear()
    }
  } catch {
    /* handled */
  } finally {
    confirmDeleteOpen.value = false
    reload()
  }
}

async function bulkAction(action: string) {
  if (selected.value.size === 0) return
  try {
    const data = await $post<BulkResponse>('/admin/plugins/_bulk', { action, slugs: [...selected.value] })
    const succ = data?.success ?? 0
    const tot = data?.total ?? selected.value.size
    const labels: Record<string, string> = {
      activate: t('admin.plugins.bulkActivate', '批量启用'),
      deactivate: t('admin.plugins.bulkDeactivate', '批量禁用'),
      upgrade: t('admin.plugins.bulkUpgrade', '批量升级')
    }
    toast.success(`${labels[action] ?? action}完成: ${succ}/${tot}`)
    selected.value.clear()
    reload()
  } catch {
    /* handled */
  }
}

function stubToast(msg: string) {
  toast.info(msg)
}

const statusFilters: Array<{ key: typeof statusFilter.value, label: () => string, count: () => number }> = [
  { key: 'all', label: () => t('admin.plugins.filter.all', '全部'), count: () => totalInstalled.value },
  { key: 'active', label: () => t('admin.plugins.status.active', '已启用'), count: () => activeCount.value },
  { key: 'inactive', label: () => t('admin.plugins.filter.inactive', '未启用'), count: () => inactiveCount.value },
  { key: 'error', label: () => t('admin.plugins.status.error', '异常'), count: () => errorCount.value }
]

function gotoPage(n: number) {
  const tgt = Math.min(Math.max(1, n), totalPages.value)
  page.value = tgt
}

onMounted(() => {
  load()
})
</script>

<template>
  <div class="flex flex-col gap-5">
    <!-- ========= Header + Stats strip ========= -->
    <div class="flex flex-col gap-4">
      <div class="flex flex-wrap items-start justify-between gap-4">
        <div class="flex items-start gap-3">
          <div class="shrink-0 size-11 rounded-2xl bg-gradient-to-br from-primary/90 to-accent/80 text-primary-foreground flex items-center justify-center shadow-pop">
            <Puzzle class="size-5" />
          </div>
          <div class="flex flex-col gap-1 min-w-0">
            <h2 class="text-2xl font-semibold tracking-tight font-display">
              {{ t('admin.plugins.title', '插件管理') }}
            </h2>
            <p class="text-sm text-muted-foreground">
              {{ t('admin.plugins.desc', '安装、启用、配置并升级你的 Rosetta 插件') }}
            </p>
          </div>
        </div>
        <div class="flex items-center gap-2 flex-wrap">
          <Button
            variant="outline"
            size="sm"
            @click="reload"
          >
            <RefreshCw class="size-4" />
            {{ t('admin.actions.refresh', '刷新') }}
          </Button>
          <Button
            variant="outline"
            size="sm"
            @click="scan"
          >
            <FolderSearch class="size-4" />
            {{ t('admin.plugins.scan', '扫描本地') }}
          </Button>
          <Button
            variant="default"
            size="sm"
            class="shadow-soft"
            @click="stubToast(t('admin.plugins.installHint', '请通过后端或 CLI 安装新插件'))"
          >
            <UploadCloud class="size-4" />
            {{ t('admin.plugins.install', '安装新插件') }}
          </Button>
        </div>
      </div>

      <!-- Stats cards -->
      <div class="grid grid-cols-2 md:grid-cols-4 xl:grid-cols-5 gap-3">
        <Card class="overflow-hidden border-border/80 shadow-soft/60 relative">
          <div class="absolute -top-10 -right-10 size-28 rounded-full bg-primary/10 blur-2xl pointer-events-none" />
          <CardContent class="p-4 flex items-center justify-between gap-3 relative">
            <div class="min-w-0">
              <div class="text-xs uppercase tracking-[0.14em] text-muted-foreground">
                {{ t('admin.plugins.stats.installed', '已安装') }}
              </div>
              <div class="mt-1 font-display text-2xl font-semibold tabular-nums">
                {{ totalInstalled }}
              </div>
            </div>
            <div class="size-10 rounded-xl bg-primary/10 text-primary flex items-center justify-center">
              <Puzzle class="size-4.5" />
            </div>
          </CardContent>
        </Card>
        <Card class="overflow-hidden border-border/80 shadow-soft/60 relative">
          <div class="absolute -top-10 -right-10 size-28 rounded-full bg-success/10 blur-2xl pointer-events-none" />
          <CardContent class="p-4 flex items-center justify-between gap-3 relative">
            <div class="min-w-0">
              <div class="text-xs uppercase tracking-[0.14em] text-muted-foreground">
                {{ t('admin.plugins.stats.active', '已启用') }}
              </div>
              <div class="mt-1 font-display text-2xl font-semibold tabular-nums text-success">
                +{{ activeCount }}
              </div>
            </div>
            <div class="size-10 rounded-xl bg-success/10 text-success flex items-center justify-center">
              <Check class="size-4.5" />
            </div>
          </CardContent>
        </Card>
        <Card class="overflow-hidden border-border/80 shadow-soft/60 relative">
          <div class="absolute -top-10 -right-10 size-28 rounded-full bg-muted/50 blur-2xl pointer-events-none" />
          <CardContent class="p-4 flex items-center justify-between gap-3 relative">
            <div class="min-w-0">
              <div class="text-xs uppercase tracking-[0.14em] text-muted-foreground">
                {{ t('admin.plugins.stats.inactive', '未启用') }}
              </div>
              <div class="mt-1 font-display text-2xl font-semibold tabular-nums text-muted-foreground">
                {{ inactiveCount }}
              </div>
            </div>
            <div class="size-10 rounded-xl bg-muted/70 text-muted-foreground flex items-center justify-center">
              <X class="size-4.5" />
            </div>
          </CardContent>
        </Card>
        <Card class="overflow-hidden border-border/80 shadow-soft/60 relative">
          <div class="absolute -top-10 -right-10 size-28 rounded-full bg-info/15 blur-2xl pointer-events-none" />
          <CardContent class="p-4 flex items-center justify-between gap-3 relative">
            <div class="min-w-0">
              <div class="text-xs uppercase tracking-[0.14em] text-muted-foreground">
                {{ t('admin.plugins.stats.updates', '可升级') }}
              </div>
              <div class="mt-1 font-display text-2xl font-semibold tabular-nums">
                {{ updatableCount }}
              </div>
            </div>
            <div class="size-10 rounded-xl bg-info/10 text-info flex items-center justify-center">
              <ArrowUpCircle class="size-4.5" />
            </div>
          </CardContent>
        </Card>
        <Card class="overflow-hidden border-border/80 shadow-soft/60 relative col-span-2 md:col-span-1">
          <div class="absolute -top-10 -right-10 size-28 rounded-full bg-warning/15 blur-2xl pointer-events-none" />
          <CardContent class="p-4 flex items-center justify-between gap-3 relative">
            <div class="min-w-0">
              <div class="text-xs uppercase tracking-[0.14em] text-muted-foreground">
                {{ t('admin.plugins.stats.errors', '异常') }}
              </div>
              <div
                class="mt-1 font-display text-2xl font-semibold tabular-nums"
                :class="errorCount ? 'text-destructive' : 'text-muted-foreground'"
              >
                {{ errorCount }}
              </div>
            </div>
            <div
              class="size-10 rounded-xl flex items-center justify-center"
              :class="errorCount ? 'bg-destructive/10 text-destructive' : 'bg-muted/70 text-muted-foreground'"
            >
              <AlertTriangle class="size-4.5" />
            </div>
          </CardContent>
        </Card>
      </div>
    </div>

    <!-- ========= Toolbar: search + status pills + bulk actions ========= -->
    <Card class="shadow-soft/60 border-border/80 overflow-hidden">
      <CardContent class="p-4 flex flex-wrap items-center gap-3">
        <div class="relative w-full sm:max-w-sm">
          <Search class="absolute left-3 top-1/2 -translate-y-1/2 size-4 text-muted-foreground" />
          <Input
            v-model="search"
            type="search"
            class="rounded-xl pl-9"
            :placeholder="t('admin.plugins.searchPlaceholder', '搜索插件名 / 描述...')"
          />
        </div>

        <div class="flex items-center gap-1.5 flex-wrap">
          <Badge
            v-for="f in statusFilters"
            :key="String(f.key)"
            :variant="statusFilter === f.key ? 'default' : 'outline'"
            class="cursor-pointer select-none rounded-full px-3 transition-all"
            :class="statusFilter === f.key ? 'shadow-soft/50' : 'hover:bg-accent'"
            @click="statusFilter = f.key; page = 1"
          >
            <span>{{ f.label() }}</span>
            <span class="ml-1 tabular-nums opacity-70">{{ f.count() }}</span>
          </Badge>
        </div>

        <div class="ml-auto flex items-center gap-2 flex-wrap">
          <Badge
            v-if="selected.size > 0"
            variant="outline"
            class="rounded-full border-primary/30 bg-primary/5"
          >
            <Check class="size-3 mr-1 text-primary" />
            {{ t('admin.plugins.selected', '已选') }} {{ selected.size }}
          </Badge>
          <DropdownMenu>
            <DropdownMenuTrigger as-child>
              <Button
                variant="outline"
                size="sm"
                class="rounded-xl"
                :disabled="selected.size === 0"
              >
                {{ t('admin.plugins.bulkActions', '批量操作') }}
                <ChevronDown class="size-4" />
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent
              align="end"
              class="w-44"
            >
              <DropdownMenuGroup>
                <DropdownMenuItem @click="bulkAction('activate')">
                  <Check class="size-4 text-success" />
                  {{ t('admin.plugins.bulkActivate', '批量启用') }}
                </DropdownMenuItem>
                <DropdownMenuItem @click="bulkAction('deactivate')">
                  <X class="size-4 text-muted-foreground" />
                  {{ t('admin.plugins.bulkDeactivate', '批量禁用') }}
                </DropdownMenuItem>
                <DropdownMenuItem @click="bulkAction('upgrade')">
                  <ArrowUpCircle class="size-4 text-info" />
                  {{ t('admin.plugins.bulkUpgrade', '批量升级') }}
                </DropdownMenuItem>
                <DropdownMenuSeparator />
                <DropdownMenuItem
                  class="text-destructive focus:text-destructive"
                  @click="confirmDeleteBulk"
                >
                  <Trash2 class="size-4" />
                  {{ t('admin.plugins.bulkDelete', '批量删除') }}
                </DropdownMenuItem>
              </DropdownMenuGroup>
            </DropdownMenuContent>
          </DropdownMenu>
        </div>
      </CardContent>

      <!-- Loading state -->
      <TableSkeleton
        v-if="loading"
        :rows="8"
        :cols="4"
        class="border-0 rounded-none"
      />

      <!-- Empty state -->
      <div
        v-else-if="filtered.length === 0"
        class="px-6 py-20"
      >
        <div class="flex flex-col items-center justify-center gap-3 text-center">
          <div class="size-16 rounded-2xl bg-gradient-to-br from-muted via-muted to-background flex items-center justify-center relative overflow-hidden">
            <div class="absolute inset-0 bg-[radial-gradient(circle_at_30%_20%,hsl(var(--primary)/0.18),transparent_55%)]" />
            <Puzzle class="size-7 text-muted-foreground relative" />
          </div>
          <div class="flex flex-col gap-1">
            <h3 class="text-base font-semibold text-foreground">
              {{ t('admin.plugins.emptyTitle', '暂无插件') }}
            </h3>
            <p class="text-sm text-muted-foreground max-w-sm">
              {{ search ? t('admin.plugins.noSearchResult', '没有匹配的插件，换个关键词试试。') : t('admin.plugins.emptyDesc', '点击「扫描本地」以发现 plugins 文件夹中的插件') }}
            </p>
          </div>
          <div class="flex items-center gap-2 pt-2">
            <Button
              size="sm"
              variant="outline"
              @click="search = ''"
            >
              {{ t('admin.actions.clear', '清除筛选') }}
            </Button>
            <Button
              size="sm"
              @click="scan"
            >
              <Sparkles class="size-4" />
              {{ t('admin.plugins.scan', '扫描本地') }}
            </Button>
          </div>
        </div>
      </div>

      <!-- Data table -->
      <template v-else>
        <div class="overflow-hidden">
          <Table>
            <TableHeader class="bg-muted/40 [&_tr]:hover:bg-transparent sticky top-0 z-10 backdrop-blur">
              <TableRow class="hover:bg-transparent border-0">
                <TableHead class="w-12 pl-6">
                  <Checkbox
                    v-model="allSelected"
                    :aria-label="t('admin.plugins.selectAll', '全选当前页')"
                  />
                </TableHead>
                <TableHead>
                  {{ t('admin.plugins.col.plugin', '插件') }}
                </TableHead>
                <TableHead class="w-44">
                  {{ t('admin.plugins.col.status', '状态') }}
                </TableHead>
                <TableHead class="w-[11rem] text-right pr-6">
                  {{ t('admin.plugins.col.actions', '操作') }}
                </TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              <TableRow
                v-for="row in paginated"
                :key="row.slug"
                :data-state="selected.has(row.slug) ? 'selected' : undefined"
                class="group align-top transition-colors"
              >
                <TableCell class="pl-6 align-top pt-5">
                  <Checkbox
                    :model-value="selected.has(row.slug)"
                    :aria-label="`选择 ${row.name}`"
                    @update:model-value="(c: boolean | 'indeterminate') => toggleSel(row.slug, c === true)"
                    @click.stop
                  />
                </TableCell>
                <TableCell class="py-5 pr-4">
                  <div class="flex gap-4 items-start min-w-0">
                    <!-- Icon tile -->
                    <div
                      class="shrink-0 size-12 rounded-2xl border border-border/80 bg-background flex items-center justify-center shadow-sm relative overflow-hidden"
                      :class="{
                        'bg-gradient-to-br from-success/15 to-success/5 border-success/30': row.status === 'active',
                        'bg-gradient-to-br from-destructive/15 to-destructive/5 border-destructive/30': row.status === 'error'
                      }"
                    >
                      <div class="absolute inset-0 bg-[radial-gradient(circle_at_20%_0%,hsl(var(--primary)/0.18),transparent_60%)]" />
                      <Puzzle
                        class="size-5 relative"
                        :class="
                          row.status === 'active'
                            ? 'text-success'
                            : row.status === 'error'
                              ? 'text-destructive'
                              : 'text-foreground/70'
                        "
                      />
                    </div>

                    <div class="flex flex-col gap-1.5 min-w-0 flex-1">
                      <div class="flex items-center gap-2 flex-wrap">
                        <h3 class="font-semibold text-base leading-tight tracking-tight truncate">
                          {{ row.name }}
                        </h3>
                        <Badge
                          variant="outline"
                          class="font-mono text-[11px] rounded-full"
                        >
                          <span class="opacity-60 mr-1">v</span>{{ row.version }}
                        </Badge>
                        <span
                          v-if="row.author"
                          class="text-xs text-muted-foreground truncate"
                        >
                          · {{ t('common.by', '由') }} {{ row.author }}
                        </span>
                      </div>
                      <p class="text-sm text-muted-foreground line-clamp-2 leading-relaxed">
                        {{ row.description || t('admin.plugins.noDesc', '该插件暂未提供描述信息。') }}
                      </p>
                      <div class="flex gap-1.5 flex-wrap pt-0.5">
                        <Badge
                          v-if="row.update_available"
                          variant="destructive"
                          class="text-[11px] rounded-full px-2.5"
                        >
                          <ArrowUpCircle class="size-3 mr-1" />
                          {{ t('admin.plugins.updateAvailable', '可升级') }}
                        </Badge>
                        <Badge
                          variant="secondary"
                          class="text-[11px] rounded-full px-2.5 max-w-[240px]"
                        >
                          <span class="truncate opacity-80 mr-1">slug</span>
                          <span class="truncate font-mono">{{ row.slug }}</span>
                        </Badge>
                      </div>
                    </div>
                  </div>
                </TableCell>
                <TableCell class="py-5">
                  <div class="flex flex-col gap-2.5 items-start">
                    <div class="flex items-center gap-2.5">
                      <Switch
                        :checked="row.status === 'active'"
                        :disabled="row.status === 'error'"
                        @update:checked="(next: boolean) => onToggleStatus(row, next)"
                      />
                      <Badge
                        :variant="statusVariant(row.status)"
                        class="rounded-full text-xs px-2.5"
                      >
                        <span
                          class="mr-1.5 size-1.5 rounded-full inline-block"
                          :class="
                            row.status === 'active'
                              ? 'bg-success animate-pulse'
                              : row.status === 'error'
                                ? 'bg-destructive animate-pulse'
                                : 'bg-muted-foreground/60'
                          "
                        />
                        {{ statusLabel(row.status) }}
                      </Badge>
                    </div>
                    <div
                      v-if="row.error_message"
                      class="max-w-xs rounded-lg border border-destructive/30 bg-destructive/5 p-2.5 text-xs text-destructive leading-snug"
                      :title="row.error_message"
                    >
                      <AlertTriangle class="size-3.5 inline mr-1.5 -translate-y-0.5" />
                      <span class="line-clamp-2 align-middle">{{ row.error_message }}</span>
                    </div>
                  </div>
                </TableCell>
                <TableCell class="py-5 pr-6">
                  <div class="flex items-center gap-1.5 justify-end">
                    <Button
                      variant="ghost"
                      size="icon"
                      class="rounded-xl text-muted-foreground hover:text-foreground hover:bg-accent"
                      :title="t('admin.plugins.settings', '设置')"
                      :disabled="!row.settings_schema"
                      @click="openSettings(row)"
                    >
                      <Cog class="size-4" />
                    </Button>
                    <Button
                      variant="ghost"
                      size="icon"
                      class="rounded-xl text-info hover:text-info/90 hover:bg-info/10 disabled:opacity-50"
                      :title="t('admin.plugins.upgrade', '升级')"
                      :disabled="!row.update_available"
                      @click="bulkAction('upgrade')"
                    >
                      <Download class="size-4" />
                    </Button>
                    <Button
                      variant="ghost"
                      size="icon"
                      class="rounded-xl text-destructive hover:text-destructive hover:bg-destructive/10"
                      :title="t('admin.plugins.delete', '删除')"
                      @click="confirmDelete(row)"
                    >
                      <Trash2 class="size-4" />
                    </Button>
                  </div>
                </TableCell>
              </TableRow>
            </TableBody>
          </Table>
        </div>

        <!-- Pagination bar -->
        <div class="flex flex-wrap items-center justify-between gap-3 px-6 py-4 border-t border-border bg-muted/25">
          <div class="flex items-center gap-3 flex-wrap">
            <span class="text-xs uppercase tracking-[0.12em] text-muted-foreground">
              {{ t('admin.plugins.perPage', '每页显示') }}
            </span>
            <div class="inline-flex rounded-xl border border-input overflow-hidden bg-background shadow-sm">
              <Button
                v-for="n in [10, 20, 50]"
                :key="n"
                size="sm"
                :variant="perPage === n ? 'default' : 'ghost'"
                class="rounded-none border-0 h-8 px-3"
                @click="perPage = n; page = 1"
              >
                {{ n }}
              </Button>
            </div>
            <span class="text-xs text-muted-foreground tabular-nums">
              {{ totalCount }} {{ t('admin.plugins.itemsUnit', '项') }} · {{ t('admin.pagination.page', '第') }} {{ page }} / {{ totalPages }} {{ t('admin.pagination.pageSuffix', '页') }}
            </span>
          </div>
          <div class="flex items-center justify-end gap-2">
            <Button
              variant="outline"
              size="sm"
              class="rounded-xl"
              :disabled="page <= 1"
              @click="gotoPage(page - 1)"
            >
              {{ t('admin.pagination.prev', '上一页') }}
            </Button>
            <template v-if="totalPages <= 7">
              <Button
                v-for="n in totalPages"
                :key="n"
                size="sm"
                :variant="page === n ? 'default' : 'ghost'"
                class="rounded-xl w-9 px-0 tabular-nums"
                @click="gotoPage(n)"
              >
                {{ n }}
              </Button>
            </template>
            <template v-else>
              <Button
                size="sm"
                variant="ghost"
                class="rounded-xl w-9 px-0 tabular-nums"
                @click="gotoPage(1)"
              >
                1
              </Button>
              <span
                v-if="page > 3"
                class="text-muted-foreground px-1"
              >…</span>
              <Button
                v-for="n in [page - 1, page, page + 1].filter(x => x > 1 && x < totalPages)"
                :key="n"
                size="sm"
                :variant="page === n ? 'default' : 'ghost'"
                class="rounded-xl w-9 px-0 tabular-nums"
                @click="gotoPage(n)"
              >
                {{ n }}
              </Button>
              <span
                v-if="page < totalPages - 2"
                class="text-muted-foreground px-1"
              >…</span>
              <Button
                size="sm"
                variant="ghost"
                class="rounded-xl w-9 px-0 tabular-nums"
                @click="gotoPage(totalPages)"
              >
                {{ totalPages }}
              </Button>
            </template>
            <Button
              variant="outline"
              size="sm"
              class="rounded-xl"
              :disabled="page * perPage >= totalCount"
              @click="gotoPage(page + 1)"
            >
              {{ t('admin.pagination.next', '下一页') }}
            </Button>
          </div>
        </div>
      </template>
    </Card>

    <!-- Settings Dialog -->
    <Dialog v-model:open="settingsOpen">
      <DialogContent class="max-w-2xl">
        <DialogHeader>
          <DialogTitle class="flex items-center gap-2.5">
            <span class="size-9 rounded-xl bg-primary/10 text-primary flex items-center justify-center">
              <Cog class="size-4.5" />
            </span>
            <span class="font-display">
              {{ t('admin.plugins.settingsTitle', '插件设置：') }}{{ currentPlugin?.name }}
            </span>
          </DialogTitle>
          <DialogDescription>
            {{ t('admin.plugins.settingsDesc', '启用或配置插件功能；修改后立即生效。') }}
          </DialogDescription>
        </DialogHeader>
        <div class="flex flex-col gap-4 max-h-[60vh] overflow-y-auto pr-1">
          <template v-if="currentPlugin?.settings_schema?.properties">
            <div
              v-for="[key, schema] in Object.entries(currentPlugin.settings_schema.properties)"
              :key="key"
              class="flex flex-col gap-2 rounded-xl border border-border/80 p-4 bg-muted/20"
            >
              <Label class="text-sm font-medium">
                {{ schema.title || key }}
                <span
                  v-if="schema.description"
                  class="block text-xs font-normal text-muted-foreground mt-1"
                >
                  {{ schema.description }}
                </span>
              </Label>
              <template v-if="schema.type === 'boolean'">
                <Switch
                  :checked="settingsForm[key] === true"
                  @update:model-value="(v: boolean) => (settingsForm[key] = v)"
                />
              </template>
              <template v-else-if="schema.type === 'string' && schema.format === 'textarea'">
                <Textarea
                  :model-value="(settingsForm[key] as string) ?? ''"
                  rows="4"
                  class="font-sans"
                  @update:model-value="(v: unknown) => (settingsForm[key] = String(v ?? ''))"
                />
              </template>
              <template
                v-else-if="
                  schema.type === 'string'
                    && Array.isArray(schema.enum)
                    && schema.enum.length
                "
              >
                <Select
                  :model-value="(settingsForm[key] as string) ?? ''"
                  @update:model-value="(v: unknown) => (settingsForm[key] = String(v ?? ''))"
                >
                  <SelectTrigger class="rounded-xl">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem
                      v-for="opt in schema.enum"
                      :key="String(opt)"
                      :value="String(opt)"
                    >
                      {{ String(opt) }}
                    </SelectItem>
                  </SelectContent>
                </Select>
              </template>
              <template v-else-if="schema.type === 'string'">
                <Input
                  :type="schema.format === 'color' ? 'color' : 'text'"
                  class="rounded-xl"
                  :model-value="(settingsForm[key] as string) ?? ''"
                  @update:model-value="(v: unknown) => (settingsForm[key] = String(v ?? ''))"
                />
              </template>
              <template v-else-if="schema.type === 'integer' || schema.type === 'number'">
                <Input
                  type="number"
                  class="rounded-xl"
                  :model-value="settingsForm[key] === undefined || settingsForm[key] === null ? '' : String(settingsForm[key])"
                  @update:model-value="(v: unknown) => {
                    const s = String(v ?? '');
                    settingsForm[key] = s === '' ? '' : Number(s);
                  }"
                />
              </template>
            </div>
          </template>
          <div
            v-else
            class="py-10 text-center text-sm text-muted-foreground rounded-xl border border-dashed border-border bg-muted/25"
          >
            {{ t('admin.plugins.noSettings', '该插件暂无可配置项') }}
          </div>
        </div>
        <DialogFooter class="gap-2 sm:gap-0">
          <DialogClose as-child>
            <Button variant="ghost">
              {{ t('admin.actions.cancel', '取消') }}
            </Button>
          </DialogClose>
          <Button
            variant="default"
            class="shadow-soft"
            @click="saveSettings"
          >
            {{ t('admin.actions.save', '保存') }}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>

    <!-- Confirm Delete Dialog -->
    <Dialog v-model:open="confirmDeleteOpen">
      <DialogContent class="max-w-md">
        <DialogHeader>
          <div class="flex items-center gap-3">
            <div class="size-11 shrink-0 rounded-2xl bg-destructive/10 flex items-center justify-center">
              <AlertTriangle class="size-5 text-destructive" />
            </div>
            <div class="flex flex-col gap-0.5">
              <DialogTitle class="font-display">
                {{ t('admin.plugins.confirmDeleteTitle', '确认删除') }}
              </DialogTitle>
              <DialogDescription class="pt-1">
                {{
                  currentPlugin
                    ? t(
                      'admin.plugins.confirmDeleteOne',
                      '即将删除插件「{name}」，删除后无法撤销，插件数据与设置将一并移除。'
                    ).replace('{name}', currentPlugin.name)
                    : t(
                      'admin.plugins.confirmDeleteBulk',
                      '即将删除选中的 {n} 个插件，删除后无法撤销，插件数据与设置将一并移除。'
                    ).replace('{n}', String(selected.size))
                }}
              </DialogDescription>
            </div>
          </div>
        </DialogHeader>
        <DialogFooter class="gap-2 sm:gap-0 pt-2">
          <DialogClose as-child>
            <Button variant="outline">
              {{ t('admin.actions.cancel', '取消') }}
            </Button>
          </DialogClose>
          <Button
            variant="destructive"
            class="shadow-soft"
            @click="doDelete"
          >
            <Trash2 class="size-4" />
            {{ t('admin.actions.delete', '删除') }}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  </div>
</template>
