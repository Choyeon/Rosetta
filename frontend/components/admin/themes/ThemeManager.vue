<script setup lang="ts">
import { ref, reactive, computed, onMounted, watch } from 'vue'
import { toast } from 'vue-sonner'
import { apiFetch } from '~~/composables/useApi'
import {
  bustThemeAssetCache,
  KNOWN_ROSETTA_THEMES,
  resolveThemeAssetPath
} from '~~/lib/rosetta-themes'
import {
  Search,
  RefreshCw,
  FolderSearch,
  UploadCloud,
  Trash2,
  Eye,
  SlidersHorizontal,
  AlertTriangle,
  Palette,
  Check,
  Sparkles,
  Play,
  ChevronRight,
  LayoutDashboard,
  CheckCircle2,
  BookOpen
} from '@lucide/vue'
import { Button } from '~~/components/ui/button'
import { Input } from '~~/components/ui/input'
import { Badge } from '~~/components/ui/badge'
import { Skeleton } from '~~/components/ui/skeleton'
import { Switch } from '~~/components/ui/switch'
import { Label } from '~~/components/ui/label'
import { Textarea } from '~~/components/ui/textarea'
import {
  Card,
  CardContent,
  CardTitle
} from '~~/components/ui/card'
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
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue
} from '~~/components/ui/select'

interface JsonSchemaNode {
  type?: string
  format?: string
  title?: string
  description?: string
  default?: unknown
  minimum?: number
  maximum?: number
  minLength?: number
  maxLength?: number
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  enum?: any[]
}

interface JsonSchema {
  properties?: Record<string, JsonSchemaNode>
  required?: string[]
}

interface Theme {
  id: number
  slug: string
  name: string
  version: string
  author: string | null
  description: string | null
  status: string
  is_active: boolean
  parent_theme: string | null
  screenshot_urls: string[]
  tags: string[]
  mods_schema?: JsonSchema | null
  mods?: Record<string, unknown> | null
  activated_at: string | null
  error_message: string | null
}

const { t: $_t } = useI18n()
const t = (k: string, fallback: string, values?: Record<string, unknown>) => {
  try {
    const v = values ? $_t(k, values) : $_t(k)
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

const themes = ref<Theme[]>([])
const loading = ref(true)
const search = ref('')
const activeFilter = ref<'all' | 'active' | 'available'>('all')
const perPage = ref(8)
const page = ref(1)
const customizerOpen = ref(false)
const confirmDeleteOpen = ref(false)
const currentTheme = ref<Theme | null>(null)
const modsForm = reactive<Record<string, unknown>>({})
const modsFormErrors = reactive<Record<string, string>>({})
const modsSaving = ref(false)

const frontendTheme = useFrontendTheme()

function castBySchema(value: unknown, node: JsonSchemaNode): unknown {
  const jtype = node.type
  if (value === null || value === undefined || value === '') {
    if (node.default !== undefined) return node.default
    if (jtype === 'string') return ''
    if (jtype === 'integer' || jtype === 'number') return node.default ?? null
    if (jtype === 'boolean') return false
    return null
  }
  if (jtype === 'integer') {
    const n = Number(value)
    return Number.isNaN(n) ? value : Math.trunc(n)
  }
  if (jtype === 'number') {
    const n = Number(value)
    return Number.isNaN(n) ? value : n
  }
  if (jtype === 'boolean') {
    if (typeof value === 'boolean') return value
    if (value === 'true') return true
    if (value === 'false') return false
    return !!value
  }
  return value
}

const totalInstalled = computed(() => themes.value.length)
const activeCount = computed(() => themes.value.filter(t => t.is_active).length)
const restCount = computed(() => themes.value.filter(t => !t.is_active).length)
const customizableCount = computed(() => themes.value.filter(t => !!t.mods_schema && Object.keys(t.mods_schema?.properties ?? {}).length > 0).length)
const errorCount = computed(() => themes.value.filter(t => t.status === 'error' || t.error_message).length)

const statusFilters: Array<{ key: typeof activeFilter.value, label: string, count: () => number }> = [
  { key: 'all', label: t('admin.themes.filter.all', '全部'), count: () => totalInstalled.value },
  { key: 'active', label: t('admin.themes.filter.active', '已激活'), count: () => activeCount.value },
  { key: 'available', label: t('admin.themes.filter.available', '可用'), count: () => restCount.value }
]

const filteredThemes = computed(() => {
  const q = search.value.trim().toLowerCase()
  return themes.value.filter((theme) => {
    if (activeFilter.value === 'active' && !theme.is_active) return false
    if (activeFilter.value === 'available' && theme.is_active) return false
    if (!q) return true
    if (theme.name.toLowerCase().includes(q)) return true
    if (theme.slug.toLowerCase().includes(q)) return true
    if (theme.tags && theme.tags.some(tg => tg.toLowerCase().includes(q))) return true
    if (theme.description && theme.description.toLowerCase().includes(q)) return true
    return false
  })
})

const totalCount = computed(() => filteredThemes.value.length)
const totalPages = computed(() => Math.max(1, Math.ceil(totalCount.value / perPage.value)))
watch(totalPages, (np) => {
  if (page.value > np) page.value = np
})

const paginatedThemes = computed(() => {
  const start = (page.value - 1) * perPage.value
  return filteredThemes.value.slice(start, start + perPage.value)
})

async function load() {
  try {
    const data = await $get<unknown>('/admin/themes')
    const obj = data as { data?: Theme[] } | Theme[]
    themes.value = (obj && typeof obj === 'object' && 'data' in obj ? (obj.data as Theme[]) : Array.isArray(obj) ? obj : null) ?? []
  } catch {
    themes.value = []
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
    const res = await $post<{
      message?: string
      data?: { added?: number, refreshed?: number, removed?: string[] }
    }>('/admin/themes/scan')
    const detail = res?.data
    if (detail) {
      // 老后端可能不回传 removed，兜底空数组，避免 TypeError 静默吞掉整个 toast。
      const removed = detail.removed ?? []
      toast.success(
        t('admin.themes.scanDoneDetail', '扫描完成：新增 {added}、刷新 {refreshed}、清理僵尸 {removed}', {
          added: detail.added ?? 0,
          refreshed: detail.refreshed ?? 0,
          removed: removed.length
        })
      )
      if (removed.length > 0) {
        toast.info(
          t('admin.themes.scanRemovedSlugs', '已移除磁盘上不存在主题的数据记录：{slugs}', {
            slugs: removed.join(', ')
          })
        )
      }
    } else {
      toast.success(t('admin.themes.scanDone', '扫描完成'))
    }
  } catch {
    /* handled */
  } finally {
    reload()
  }
}

async function activateTheme(theme: Theme) {
  try {
    await apiFetch(`/admin/themes/${theme.slug}/activate`, { method: 'PUT' })
    toast.success(t('admin.themes.activated', '主题已启用'))
    // 同步刷新前台主题状态，避免"后台切主题 → SPA 返回首页仍是旧主题"
    // （useFrontendTheme 有 loaded-latch，不强制重载不会重新拉 /api/themes/active）。
    try {
      await frontendTheme.reload()
    } catch {
      /* noop：后台上下文不消费主题视觉层，失败仅影响首页需硬刷新 */
    }
    reload()
  } catch {
    /* handled */
  }
}

function openCustomizer(theme: Theme) {
  currentTheme.value = theme
  const fresh: Record<string, unknown> = {}
  Object.assign(fresh, theme.mods ?? {})

  const props = theme.mods_schema?.properties
  if (props && typeof props === 'object') {
    for (const [key, node] of Object.entries(props)) {
      if (!node || typeof node !== 'object') continue
      const cur = fresh[key] !== undefined ? fresh[key] : (node.default ?? null)
      fresh[key] = castBySchema(cur, node as JsonSchemaNode)
    }
  }
  for (const k of Object.keys(modsForm)) {
    // eslint-disable-next-line @typescript-eslint/no-dynamic-delete
    delete modsForm[k]
  }
  for (const k of Object.keys(modsFormErrors)) {
    // eslint-disable-next-line @typescript-eslint/no-dynamic-delete
    delete modsFormErrors[k]
  }
  Object.assign(modsForm, fresh)
  customizerOpen.value = true
}

function _validateLocalForm(): boolean {
  for (const k of Object.keys(modsFormErrors)) {
    // eslint-disable-next-line @typescript-eslint/no-dynamic-delete
    delete modsFormErrors[k]
  }
  const props = currentTheme.value?.mods_schema?.properties
  if (!props) return true
  let ok = true
  for (const [key, node] of Object.entries(props)) {
    if (!node || typeof node !== 'object') continue
    const v = modsForm[key]
    const n = node as JsonSchemaNode
    if (Array.isArray(n.enum) && n.enum.length > 0) {
      if (v !== null && v !== undefined && v !== '' && !n.enum.includes(v)) {
        modsFormErrors[key] = `必须是 ${n.enum.map(x => String(x)).join(', ')} 之一`
        ok = false
      }
    }
    if (n.type === 'integer' || n.type === 'number') {
      if (v !== null && v !== undefined && v !== '') {
        const num = Number(v)
        if (Number.isNaN(num)) {
          modsFormErrors[key] = '必须是数字'
          ok = false
        } else {
          if (typeof n.minimum === 'number' && num < n.minimum) {
            modsFormErrors[key] = `不能小于 ${n.minimum}`
            ok = false
          }
          if (typeof n.maximum === 'number' && num > n.maximum) {
            modsFormErrors[key] = `不能大于 ${n.maximum}`
            ok = false
          }
        }
      }
    }
    if (n.type === 'string' && typeof v === 'string') {
      if (typeof n.minLength === 'number' && v.length < n.minLength) {
        modsFormErrors[key] = `长度至少 ${n.minLength}`
        ok = false
      }
      if (typeof n.maxLength === 'number' && v.length > n.maxLength) {
        modsFormErrors[key] = `长度至多 ${n.maxLength}`
        ok = false
      }
      if (n.format === 'color' && !/^#([0-9a-fA-F]{3}|[0-9a-fA-F]{4}|[0-9a-fA-F]{6}|[0-9a-fA-F]{8})$/.test(v)) {
        modsFormErrors[key] = '颜色格式必须为 #RGB / #RGBA / #RRGGBB / #RRGGBBAA'
        ok = false
      }
    }
  }
  return ok
}

async function saveMods() {
  if (!currentTheme.value) return
  if (!_validateLocalForm()) {
    toast.error(t('admin.themes.modsValidationFailed', '表单校验失败，请检查标红字段'))
    return
  }
  modsSaving.value = true
  try {
    const props = currentTheme.value.mods_schema?.properties
    const patch: Record<string, unknown> = {}
    for (const [k, v] of Object.entries(modsForm)) {
      const node = props?.[k]
      patch[k] = node ? castBySchema(v, node) : v
    }
    await $patch(`/admin/themes/${currentTheme.value.slug}/mods`, {
      mods: patch
    })
    toast.success(t('admin.themes.modsSaved', '主题自定义已保存'))
    customizerOpen.value = false
    if (currentTheme.value.is_active) {
      try {
        await frontendTheme.reload()
      } catch {
        /* noop */
      }
    }
    reload()
  } catch (err) {
    const msg = err && typeof err === 'object' && 'message' in err ? String((err as { message?: unknown }).message ?? '') : ''
    if (msg) toast.error(msg)
  } finally {
    modsSaving.value = false
  }
}

function confirmDelete(theme: Theme) {
  currentTheme.value = theme
  confirmDeleteOpen.value = true
}

async function doDelete() {
  if (!currentTheme.value) return
  try {
    await $delete(`/admin/themes/${currentTheme.value.slug}`)
    toast.success(t('admin.themes.deleted', '主题已删除'))
  } catch {
    /* handled */
  } finally {
    confirmDeleteOpen.value = false
    reload()
  }
}

function stubToast(msg: string) {
  toast.info(msg)
}

// ===== 预览：打开前台首页并附带 ?rosetta_theme_preview=<slug> =====
// useFrontendTheme.ensureLoaded() 读取该 query（仅限 KNOWN_ROSETTA_THEMES 白名单）
// 临时覆盖 active slug，不改动后端激活主题。新标签页打开，避免丢失后台上下文。
function previewTheme(theme: Theme) {
  if (!import.meta.client) return
  window.open(
    `/?rosetta_theme_preview=${encodeURIComponent(theme.slug)}`,
    '_blank',
    'noopener,noreferrer'
  )
}

// ===== 安装新主题：三来源（local / remote / upload）=====
const installOpen = ref(false)
const installSource = ref<'local' | 'remote' | 'upload'>('local')
const installBusy = ref(false)
const installLocalSlug = ref('')
const installRemoteUrl = ref('')
const installRemoteChecksum = ref('')
const installFile = ref<File | null>(null)
const installError = ref('')

function openInstall() {
  installSource.value = 'local'
  installLocalSlug.value = ''
  installRemoteUrl.value = ''
  installRemoteChecksum.value = ''
  installFile.value = null
  installError.value = ''
  installOpen.value = true
}

function onInstallSourceChange(v: unknown) {
  const s = String(v ?? 'local')
  installSource.value = s === 'remote' || s === 'upload' ? s : 'local'
  installError.value = ''
}

function onInstallFileChange(e: Event) {
  const input = e.target as HTMLInputElement
  installFile.value = input.files?.[0] ?? null
  installError.value = ''
}

async function submitInstall() {
  installError.value = ''
  installBusy.value = true
  try {
    if (installSource.value === 'local') {
      const slug = installLocalSlug.value.trim()
      if (!slug) {
        installError.value = t('admin.themes.installNeedSlug', '请填写主题 slug')
        return
      }
      await apiFetch('/admin/themes?source=local', { method: 'POST', body: { slug } })
    } else if (installSource.value === 'remote') {
      const url = installRemoteUrl.value.trim()
      if (!url) {
        installError.value = t('admin.themes.installNeedUrl', '请填写主题包 URL')
        return
      }
      const remote: Record<string, string> = { url }
      const cs = installRemoteChecksum.value.trim()
      if (cs) remote.checksum_sha256 = cs
      await apiFetch('/admin/themes?source=remote', { method: 'POST', body: { remote } })
    } else {
      if (!installFile.value) {
        installError.value = t('admin.themes.installNeedFile', '请选择 zip 文件')
        return
      }
      const fd = new FormData()
      fd.append('file', installFile.value)
      await apiFetch('/admin/themes?source=upload', { method: 'POST', body: fd })
    }
    toast.success(t('admin.themes.installDone', '主题安装成功'))
    installOpen.value = false
    reload()
  } catch (err) {
    const msg = err && typeof err === 'object' && 'message' in err
      ? String((err as { message?: unknown }).message ?? '')
      : ''
    installError.value = msg || t('admin.themes.installFailed', '安装失败')
  } finally {
    installBusy.value = false
  }
}

function openThemeDocs() {
  navigateTo('/admin/docs/theme-tutorial')
}

function themeScreenshot(theme: Theme): string {
  const first = theme.screenshot_urls?.[0]
  if (!first) return ''
  // 归一规则与前台 useFrontendTheme 共享单一来源；本地 /themes/** 是
  // immutable 强缓存，必须带 ?v=<version>，否则主题升级后卡片截图永远是旧的。
  return bustThemeAssetCache(resolveThemeAssetPath(theme.slug, first), theme.version)
}

// 内建主题随代码仓库分发：删除只会留下"磁盘还在、记录没了"的僵尸态，
// 下次 scan 又会被重新装回，白白丢失 mods 配置——UI 层直接禁止。
function isBuiltinTheme(theme: Theme): boolean {
  return KNOWN_ROSETTA_THEMES.has(theme.slug)
}

function formatDate(iso: string | null): string {
  if (!iso) return '—'
  try {
    const d = new Date(iso)
    return d.toLocaleDateString(undefined, { year: 'numeric', month: '2-digit', day: '2-digit' })
  } catch {
    return '—'
  }
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
          <div class="shrink-0 size-11 rounded-2xl bg-gradient-to-br from-purple-500/90 via-primary/80 to-accent/80 text-primary-foreground flex items-center justify-center shadow-pop relative overflow-hidden">
            <div class="absolute inset-0 bg-[radial-gradient(circle_at_30%_20%,hsl(var(--accent)/0.35),transparent_60%)]" />
            <Palette class="size-5 relative" />
          </div>
          <div class="flex flex-col gap-1 min-w-0">
            <h2 class="text-2xl font-semibold tracking-tight font-display">
              {{ t('admin.themes.title', '主题管理') }}
            </h2>
            <p class="text-sm text-muted-foreground">
              {{ t('admin.themes.desc', '切换与自定义 Rosetta 博客外观') }}
            </p>
          </div>
        </div>
        <div class="flex items-center gap-2 flex-wrap">
          <Button
            variant="outline"
            size="sm"
            class="text-primary hover:text-primary hover:bg-primary/5"
            @click="openThemeDocs"
          >
            <BookOpen data-icon="inline-start" />
            {{ t('admin.themes.docs', '主题文档') }}
          </Button>
          <Button
            variant="outline"
            size="sm"
            @click="reload"
          >
            <RefreshCw data-icon="inline-start" />
            {{ t('admin.actions.refresh', '刷新') }}
          </Button>
          <Button
            variant="outline"
            size="sm"
            @click="scan"
          >
            <FolderSearch data-icon="inline-start" />
            {{ t('admin.themes.scan', '扫描本地') }}
          </Button>
          <Button
            variant="default"
            size="sm"
            class="shadow-soft"
            @click="openInstall"
          >
            <UploadCloud data-icon="inline-start" />
            {{ t('admin.themes.install', '安装新主题') }}
          </Button>
        </div>
      </div>

      <!-- Stats cards -->
      <div class="grid grid-cols-2 md:grid-cols-4 gap-3">
        <Card class="overflow-hidden border-border/80 shadow-soft/60 relative">
          <div class="absolute -top-10 -right-10 size-28 rounded-full bg-primary/10 blur-2xl pointer-events-none" />
          <CardContent class="p-4 flex items-center justify-between gap-3 relative">
            <div class="min-w-0">
              <div class="text-xs uppercase tracking-[0.14em] text-muted-foreground">
                {{ t('admin.themes.stats.total', '主题总数') }}
              </div>
              <div class="mt-1 font-display text-2xl font-semibold tabular-nums">
                {{ totalInstalled }}
              </div>
            </div>
            <div class="size-10 rounded-xl bg-primary/10 text-primary flex items-center justify-center">
              <LayoutDashboard class="size-4.5" />
            </div>
          </CardContent>
        </Card>
        <Card class="overflow-hidden border-border/80 shadow-soft/60 relative">
          <div class="absolute -top-10 -right-10 size-28 rounded-full bg-success/10 blur-2xl pointer-events-none" />
          <CardContent class="p-4 flex items-center justify-between gap-3 relative">
            <div class="min-w-0">
              <div class="text-xs uppercase tracking-[0.14em] text-muted-foreground">
                {{ t('admin.themes.stats.active', '已激活') }}
              </div>
              <div class="mt-1 font-display text-2xl font-semibold tabular-nums text-success">
                {{ activeCount }}
              </div>
            </div>
            <div class="size-10 rounded-xl bg-success/10 text-success flex items-center justify-center">
              <CheckCircle2 class="size-4.5" />
            </div>
          </CardContent>
        </Card>
        <Card class="overflow-hidden border-border/80 shadow-soft/60 relative">
          <div class="absolute -top-10 -right-10 size-28 rounded-full bg-info/15 blur-2xl pointer-events-none" />
          <CardContent class="p-4 flex items-center justify-between gap-3 relative">
            <div class="min-w-0">
              <div class="text-xs uppercase tracking-[0.14em] text-muted-foreground">
                {{ t('admin.themes.stats.customizable', '可自定义') }}
              </div>
              <div class="mt-1 font-display text-2xl font-semibold tabular-nums">
                {{ customizableCount }}
              </div>
            </div>
            <div class="size-10 rounded-xl bg-info/10 text-info flex items-center justify-center">
              <SlidersHorizontal class="size-4.5" />
            </div>
          </CardContent>
        </Card>
        <Card class="overflow-hidden border-border/80 shadow-soft/60 relative">
          <div class="absolute -top-10 -right-10 size-28 rounded-full bg-warning/15 blur-2xl pointer-events-none" />
          <CardContent class="p-4 flex items-center justify-between gap-3 relative">
            <div class="min-w-0">
              <div class="text-xs uppercase tracking-[0.14em] text-muted-foreground">
                {{ t('admin.themes.stats.errors', '异常') }}
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

    <!-- ========= Toolbar: search + status pills ========= -->
    <Card class="shadow-soft/60 border-border/80 overflow-hidden">
      <CardContent class="p-4 flex flex-wrap items-center gap-3">
        <div class="relative w-full sm:max-w-sm">
          <Search class="absolute left-3 top-1/2 -translate-y-1/2 size-4 text-muted-foreground" />
          <Input
            v-model="search"
            type="search"
            class="rounded-xl pl-9"
            :placeholder="t('admin.themes.searchPlaceholder', '按名称或标签搜索...')"
            @input="page = 1"
          />
        </div>

        <div class="flex items-center gap-1.5 flex-wrap">
          <Badge
            v-for="f in statusFilters"
            :key="String(f.key)"
            :variant="activeFilter === f.key ? 'default' : 'outline'"
            class="cursor-pointer select-none rounded-full px-3 transition-all"
            :class="activeFilter === f.key ? 'shadow-soft/50' : 'hover:bg-accent'"
            @click="activeFilter = f.key; page = 1"
          >
            <span>{{ f.label }}</span>
            <span class="ml-1 tabular-nums opacity-70">{{ f.count() }}</span>
          </Badge>
        </div>
      </CardContent>

      <!-- Loading state -->
      <div
        v-if="loading"
        class="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-4 p-4"
      >
        <div
          v-for="n in Math.min(8, perPage)"
          :key="`sk-${n}`"
          class="flex flex-col gap-3 p-4 rounded-2xl border border-border/70 bg-card"
        >
          <Skeleton class="aspect-[16/10] rounded-xl" />
          <div class="flex flex-col gap-1.5">
            <Skeleton class="h-5 w-1/2 rounded-full" />
            <Skeleton class="h-3.5 w-1/3 rounded-full" />
          </div>
          <div class="flex gap-2 pt-1">
            <Skeleton class="h-8 flex-1 rounded-lg" />
            <Skeleton class="h-8 flex-1 rounded-lg" />
          </div>
        </div>
      </div>

      <!-- Empty state -->
      <div
        v-else-if="filteredThemes.length === 0"
        class="px-6 py-20 border-t border-border"
      >
        <div class="flex flex-col items-center justify-center gap-3 text-center">
          <div class="size-16 rounded-2xl bg-gradient-to-br from-purple-500/20 via-primary/15 to-accent/20 flex items-center justify-center relative overflow-hidden">
            <div class="absolute inset-0 bg-[radial-gradient(circle_at_30%_20%,hsl(var(--primary)/0.22),transparent_55%)]" />
            <Palette class="size-7 text-primary relative" />
          </div>
          <div class="flex flex-col gap-1">
            <h3 class="text-base font-semibold text-foreground">
              {{ search ? t('admin.themes.noSearchResult', '没有匹配的主题，换个关键词试试。') : t('admin.themes.emptyTitle', '暂无主题') }}
            </h3>
            <p class="text-sm text-muted-foreground max-w-sm">
              {{ search ? '' : t('admin.themes.emptyDesc', '点击「扫描本地」发现 themes 文件夹主题') }}
            </p>
          </div>
          <div class="flex items-center gap-2 pt-2">
            <Button
              v-if="search"
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
              <Sparkles data-icon="inline-start" />
              {{ t('admin.themes.scan', '扫描本地') }}
            </Button>
          </div>
        </div>
      </div>

      <!-- Grid -->
      <div
        v-else
        class="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-4 p-4"
      >
        <div
          v-for="(theme, idx) in paginatedThemes"
          :key="theme.slug"
          :class="[
            'relative group flex flex-col p-4 rounded-2xl border transition-all duration-300',
            theme.is_active
              ? 'border-primary/50 ring-2 ring-primary/20 bg-primary/[0.03] shadow-soft'
              : 'border-border/80 bg-card shadow-soft/40 hover:-translate-y-1 hover:border-primary/35 hover:shadow-pop'
          ]"
          :data-idx="idx"
        >
          <div class="relative flex flex-col gap-3 h-full">
            <!-- Screenshot tile -->
            <div class="aspect-[16/10] relative overflow-hidden rounded-xl bg-muted ring-1 ring-border/80 shadow-soft/40 group-hover:shadow-soft/80 transition-all">
              <template v-if="themeScreenshot(theme)">
                <img
                  :src="themeScreenshot(theme)"
                  :alt="theme.name"
                  loading="lazy"
                  class="size-full object-cover transition-transform duration-500 ease-out group-hover:scale-[1.06]"
                >
              </template>
              <div
                v-else
                class="size-full bg-[radial-gradient(circle_at_20%_15%,hsl(var(--primary)/0.25),hsl(var(--accent)/0.18)_40%,hsl(var(--muted))_80%)] flex items-center justify-center relative overflow-hidden"
              >
                <div
                  class="absolute inset-0 opacity-[0.35] mix-blend-overlay"
                  style="background-image: url('data:image/svg+xml,%3Csvg xmlns=%27http://www.w3.org/2000/svg%27 width=%27120%27 height=%27120%27 viewBox=%270 0 120 120%27%3E%3Cpath fill=%27none%27 stroke=%27white%27 stroke-opacity=%270.35%27 stroke-width=%271%27 d=%27M0 30h120M0 60h120M0 90h120M30 0v120M60 0v120M90 0v120%27/%3E%3C/svg%3E');"
                />
                <Palette class="size-10 text-foreground/50 relative" />
              </div>

              <!-- Top badges -->
              <div class="absolute top-2.5 left-2.5 flex gap-1.5 items-start">
                <Badge
                  v-if="theme.is_active"
                  variant="default"
                  class="rounded-full shadow-pop backdrop-blur bg-primary/90"
                >
                  <Check class="size-3 mr-1" />
                  {{ t('admin.themes.current', '当前主题') }}
                </Badge>
                <Badge
                  v-if="theme.status === 'error' || theme.error_message"
                  variant="destructive"
                  class="rounded-full"
                >
                  <AlertTriangle class="size-3 mr-1" />
                  {{ t('admin.themes.error', '错误') }}
                </Badge>
              </div>
              <div class="absolute top-2.5 right-2.5">
                <Badge
                  variant="outline"
                  class="rounded-full bg-background/80 backdrop-blur font-mono text-[11px]"
                >
                  v{{ theme.version }}
                </Badge>
              </div>

              <!-- Hover overlay: quick preview + customize -->
              <div class="absolute inset-0 bg-gradient-to-t from-black/80 via-black/30 to-transparent opacity-0 group-hover:opacity-100 transition-all duration-300 flex flex-col justify-end p-3 gap-2">
                <div class="flex items-center gap-1.5">
                  <Button
                    variant="default"
                    size="sm"
                    class="flex-1 rounded-xl shadow-soft bg-white/95 text-foreground hover:bg-white backdrop-blur"
                    @click="previewTheme(theme)"
                  >
                    <Eye data-icon="inline-start" />
                    {{ t('admin.themes.preview', '预览') }}
                  </Button>
                  <Button
                    v-if="theme.mods_schema"
                    variant="default"
                    size="sm"
                    class="flex-1 rounded-xl shadow-soft"
                    @click="openCustomizer(theme)"
                  >
                    <SlidersHorizontal data-icon="inline-start" />
                    {{ t('admin.themes.customize', '自定义') }}
                  </Button>
                </div>
              </div>
            </div>

            <!-- Meta content -->
            <div class="flex flex-col gap-2 flex-1">
              <div class="flex justify-between items-start gap-2">
                <div class="flex flex-col gap-0.5 min-w-0 flex-1">
                  <CardTitle class="truncate text-base leading-tight tracking-tight">
                    {{ theme.name }}
                  </CardTitle>
                  <div class="text-xs text-muted-foreground flex items-center gap-1 truncate">
                    <template v-if="theme.author">
                      <span>{{ t('common.by', '由') }} {{ theme.author }}</span>
                      <span class="opacity-40">·</span>
                    </template>
                    <span class="tabular-nums">
                      {{ t('admin.themes.activatedAt', '激活于') }} {{ formatDate(theme.activated_at) }}
                    </span>
                  </div>
                </div>
                <div class="flex flex-wrap gap-1 max-w-[140px] justify-end shrink-0">
                  <Badge
                    v-for="tag in theme.tags.slice(0, 2)"
                    :key="tag"
                    variant="outline"
                    class="text-[11px] truncate max-w-[92px] rounded-full"
                  >
                    {{ tag }}
                  </Badge>
                  <Badge
                    v-if="theme.tags.length > 2"
                    variant="outline"
                    class="text-[11px] rounded-full"
                  >
                    +{{ theme.tags.length - 2 }}
                  </Badge>
                </div>
              </div>

              <p class="text-sm text-muted-foreground line-clamp-2 leading-relaxed">
                {{ theme.description || t('admin.themes.noDesc', '该主题暂未提供描述信息。') }}
              </p>
            </div>

            <!-- Footer actions -->
            <div class="flex flex-col gap-2 pt-1">
              <div
                v-if="theme.error_message"
                class="rounded-xl border border-destructive/30 bg-destructive/5 p-2.5 text-xs text-destructive leading-snug"
                :title="theme.error_message"
              >
                <AlertTriangle class="size-3.5 inline mr-1.5 -translate-y-0.5" />
                <span class="line-clamp-2 align-middle">{{ theme.error_message }}</span>
              </div>

              <div class="flex items-stretch gap-2">
                <template v-if="theme.is_active">
                  <Button
                    variant="outline"
                    class="flex-1 rounded-xl"
                    disabled
                  >
                    <CheckCircle2
                      data-icon="inline-start"
                      class="mr-1 text-success"
                    />
                    {{ t('admin.themes.isActive', '已激活') }}
                  </Button>
                </template>
                <template v-else>
                  <Button
                    variant="default"
                    class="flex-1 rounded-xl shadow-soft/60"
                    @click="activateTheme(theme)"
                  >
                    <Play
                      data-icon="inline-start"
                      class="mr-1"
                    />
                    {{ t('admin.themes.activate', '启用') }}
                  </Button>
                </template>
                <Button
                  variant="outline"
                  class="rounded-xl px-3"
                  :disabled="!theme.mods_schema"
                  :title="theme.mods_schema ? t('admin.themes.customize', '自定义') : t('admin.themes.noCustomizeHint', '该主题无可自定义项')"
                  @click="openCustomizer(theme)"
                >
                  <SlidersHorizontal data-icon="inline-start" />
                </Button>
                <Button
                  variant="outline"
                  class="rounded-xl px-3 text-destructive hover:bg-destructive/10 hover:text-destructive hover:border-destructive/40"
                  :disabled="theme.is_active || isBuiltinTheme(theme)"
                  :title="theme.is_active
                    ? t('admin.themes.cannotDeleteActive', '当前激活的主题无法删除')
                    : isBuiltinTheme(theme)
                      ? t('admin.themes.cannotDeleteBuiltin', '内建主题不可删除')
                      : t('admin.themes.delete', '删除')"
                  @click="confirmDelete(theme)"
                >
                  <Trash2 data-icon="inline-start" />
                </Button>
              </div>

              <a
                v-if="theme.parent_theme"
                href="#"
                class="text-[11px] text-muted-foreground hover:text-foreground inline-flex items-center gap-1 truncate"
                @click.prevent="stubToast(t('admin.themes.parentHint', '父主题占位'))"
              >
                <span>
                  {{ t('admin.themes.childOf', '子主题：继承自 {name}', { name: theme.parent_theme }) }}
                </span>
                <ChevronRight class="size-3 opacity-60" />
              </a>
            </div>
          </div>
        </div>
      </div>

      <!-- Pagination bar（全站后台统一：AdminPagination） -->
      <div
        v-if="!loading && filteredThemes.length > 0"
        class="px-5 py-4 border-t border-border bg-muted/25"
      >
        <AdminPagination
          v-model:page="page"
          v-model:page-size="perPage"
          :total="totalCount"
          :page-size-options="[4, 8, 12]"
          unit="个主题"
        />
      </div>
    </Card>

    <!-- Customizer Dialog -->
    <Dialog v-model:open="customizerOpen">
      <DialogContent class="max-w-3xl">
        <DialogHeader>
          <DialogTitle class="flex items-center gap-2.5">
            <span class="size-9 rounded-xl bg-gradient-to-br from-purple-500/25 via-primary/20 to-accent/25 text-primary flex items-center justify-center relative overflow-hidden">
              <div class="absolute inset-0 bg-[radial-gradient(circle_at_30%_20%,hsl(var(--primary)/0.25),transparent_60%)]" />
              <SlidersHorizontal class="size-4.5 relative" />
            </span>
            <span class="font-display">
              {{ t('admin.themes.customizerTitle', '自定义主题：') }}{{ currentTheme?.name }}
            </span>
            <Badge
              v-if="currentTheme?.is_active"
              variant="default"
              class="ml-1 rounded-full"
            >
              <Check class="size-3 mr-1" />
              {{ t('admin.themes.current', '当前') }}
            </Badge>
          </DialogTitle>
          <DialogDescription>
            {{ t('admin.themes.customizerDesc', '实时调整主题外观；设置立即保存到站点。') }}
            <span
              v-if="currentTheme?.is_active"
              class="block text-xs text-primary mt-1"
            >
              · {{ t('admin.themes.customizerActiveHint', '您正在修改当前激活主题，保存后前端将立刻刷新。') }}
            </span>
          </DialogDescription>
        </DialogHeader>
        <div class="flex flex-col gap-3 max-h-[65vh] overflow-y-auto pr-1 -mr-1">
          <template v-if="currentTheme?.mods_schema?.properties">
            <div
              v-for="[key, schema] in Object.entries(currentTheme.mods_schema.properties)"
              :key="key"
              class="flex flex-col gap-2 rounded-xl border border-border/80 p-4 bg-muted/20"
            >
              <Label class="text-sm font-medium">
                {{ schema.title || key }}
                <span
                  v-if="schema.description"
                  class="block text-xs font-normal text-muted-foreground mt-0.5"
                >
                  {{ schema.description }}
                </span>
              </Label>
              <template v-if="schema.type === 'boolean'">
                <div class="flex items-center gap-2">
                  <Switch
                    :model-value="modsForm[key] === true"
                    @update:model-value="(v: boolean) => (modsForm[key] = v)"
                  />
                  <span class="text-xs text-muted-foreground">
                    {{ modsForm[key] ? t('admin.themes.modsOn', '启用') : t('admin.themes.modsOff', '关闭') }}
                  </span>
                </div>
              </template>
              <template v-else-if="schema.type === 'string' && schema.format === 'textarea'">
                <Textarea
                  :model-value="(modsForm[key] as string) ?? ''"
                  rows="4"
                  class="font-sans rounded-xl"
                  @update:model-value="(v: unknown) => (modsForm[key] = String(v ?? ''))"
                />
              </template>
              <template
                v-else-if="
                  Array.isArray(schema.enum) && schema.enum.length
                "
              >
                <Select
                  :model-value="(modsForm[key] !== undefined && modsForm[key] !== null ? String(modsForm[key]) : '')"
                  @update:model-value="(v: unknown) => {
                    const str = v === undefined || v === null ? '' : String(v)
                    if (schema.type === 'integer') {
                      modsForm[key] = str === '' ? (schema.default ?? null) : Math.trunc(Number(str))
                    }
                    else if (schema.type === 'number') {
                      modsForm[key] = str === '' ? (schema.default ?? null) : Number(str)
                    }
                    else if (typeof schema.type === 'boolean') {
                      modsForm[key] = str === 'true' ? true : str === 'false' ? false : str
                    }
                    else {
                      modsForm[key] = str === '' ? (schema.default ?? '') : str
                    }
                  }"
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
              <template v-else-if="schema.type === 'string' && schema.format === 'color'">
                <div class="flex items-center gap-2">
                  <Input
                    type="color"
                    class="w-14 h-9 p-1 rounded-xl cursor-pointer"
                    :model-value="(modsForm[key] as string) || (schema.default as string | number | undefined) || '#000000'"
                    @update:model-value="(v: unknown) => (modsForm[key] = String(v ?? ''))"
                  />
                  <Input
                    type="text"
                    spellcheck="false"
                    class="font-mono text-sm flex-1 rounded-xl"
                    placeholder="#RRGGBB"
                    :model-value="(modsForm[key] as string) ?? ''"
                    @update:model-value="(v: unknown) => (modsForm[key] = String(v ?? ''))"
                  />
                </div>
              </template>
              <template v-else-if="schema.type === 'string'">
                <Input
                  type="text"
                  class="rounded-xl"
                  :model-value="(modsForm[key] as string) ?? ''"
                  :placeholder="typeof schema.default === 'string' ? schema.default : ''"
                  @update:model-value="(v: unknown) => (modsForm[key] = String(v ?? ''))"
                />
              </template>
              <template v-else-if="schema.type === 'integer'">
                <Input
                  type="number"
                  step="1"
                  class="rounded-xl"
                  :min="typeof schema.minimum === 'number' ? schema.minimum : undefined"
                  :max="typeof schema.maximum === 'number' ? schema.maximum : undefined"
                  :model-value="
                    modsForm[key] === undefined || modsForm[key] === null || modsForm[key] === ''
                      ? ''
                      : String(Math.trunc(Number(modsForm[key])))
                  "
                  @update:model-value="(v: unknown) => {
                    const s = String(v ?? '')
                    modsForm[key] = s === '' ? (schema.default ?? null) : Math.trunc(Number(s))
                  }"
                />
              </template>
              <template v-else-if="schema.type === 'number'">
                <Input
                  type="number"
                  step="any"
                  class="rounded-xl"
                  :min="typeof schema.minimum === 'number' ? schema.minimum : undefined"
                  :max="typeof schema.maximum === 'number' ? schema.maximum : undefined"
                  :model-value="
                    modsForm[key] === undefined || modsForm[key] === null || modsForm[key] === ''
                      ? ''
                      : String(Number(modsForm[key]))
                  "
                  @update:model-value="(v: unknown) => {
                    const s = String(v ?? '')
                    modsForm[key] = s === '' ? (schema.default ?? null) : Number(s)
                  }"
                />
              </template>
              <template v-else>
                <Input
                  class="rounded-xl"
                  :model-value="modsForm[key] === null || modsForm[key] === undefined ? '' : String(modsForm[key])"
                  @update:model-value="(v: unknown) => (modsForm[key] = v)"
                />
              </template>
              <p
                v-if="modsFormErrors[key]"
                class="text-xs text-destructive flex items-center gap-1"
              >
                <AlertTriangle class="size-3.5" />
                {{ modsFormErrors[key] }}
              </p>
            </div>
          </template>
          <div
            v-else
            class="py-10 text-center text-sm text-muted-foreground rounded-xl border border-dashed border-border bg-muted/25"
          >
            {{ t('admin.themes.noMods', '该主题暂无可自定义项') }}
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
            :disabled="modsSaving"
            @click="saveMods"
          >
            <template v-if="modsSaving">
              <RefreshCw
                data-icon="inline-start"
                class="animate-spin"
              />
              {{ t('admin.actions.saving', '保存中…') }}
            </template>
            <template v-else>
              <Sparkles data-icon="inline-start" />
              {{ t('admin.actions.save', '保存') }}
            </template>
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
                {{ t('admin.themes.confirmDeleteTitle', '确认删除') }}
              </DialogTitle>
              <DialogDescription class="pt-1">
                {{
                  currentTheme
                    ? t(
                      'admin.themes.confirmDelete',
                      '即将删除主题「{name}」，删除后无法撤销，主题自定义与配置将一并移除。',
                      { name: currentTheme.name }
                    ).replace('{name}', currentTheme.name)
                    : ''
                }}
              </DialogDescription>
            </div>
          </div>
        </DialogHeader>
        <DialogFooter class="gap-2 sm:gap-0">
          <Button
            variant="outline"
            @click="confirmDeleteOpen = false"
          >
            {{ t('admin.actions.cancel', '取消') }}
          </Button>
          <Button
            variant="destructive"
            @click="doDelete"
          >
            <Trash2 data-icon="inline-start" />
            {{ t('admin.actions.delete', '删除') }}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>

    <!-- Install Dialog -->
    <Dialog v-model:open="installOpen">
      <DialogContent class="max-w-lg">
        <DialogHeader>
          <DialogTitle class="flex items-center gap-2.5 font-display">
            <span class="size-9 rounded-xl bg-primary/10 text-primary flex items-center justify-center">
              <UploadCloud class="size-4.5" />
            </span>
            {{ t('admin.themes.install', '安装新主题') }}
          </DialogTitle>
          <DialogDescription>
            {{ t('admin.themes.installDesc', '从本地目录、远程 URL 或上传 zip 包安装主题。') }}
          </DialogDescription>
        </DialogHeader>

        <div class="flex flex-col gap-4">
          <div class="flex flex-col gap-2">
            <Label class="text-sm font-medium">
              {{ t('admin.themes.installSource', '安装来源') }}
            </Label>
            <Select
              :model-value="installSource"
              @update:model-value="onInstallSourceChange"
            >
              <SelectTrigger class="rounded-xl">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="local">
                  {{ t('admin.themes.sourceLocal', '本地目录扫描') }}
                </SelectItem>
                <SelectItem value="remote">
                  {{ t('admin.themes.sourceRemote', '远程 URL 下载') }}
                </SelectItem>
                <SelectItem value="upload">
                  {{ t('admin.themes.sourceUpload', '上传 zip 包') }}
                </SelectItem>
              </SelectContent>
            </Select>
          </div>

          <div
            v-if="installSource === 'local'"
            class="flex flex-col gap-2"
          >
            <Label class="text-sm font-medium">
              {{ t('admin.themes.installSlug', '主题 slug') }}
            </Label>
            <Input
              v-model="installLocalSlug"
              class="rounded-xl font-mono text-sm"
              placeholder="astro-paper-inspired"
            />
            <p class="text-xs text-muted-foreground">
              {{ t('admin.themes.installLocalHint', '主题需已存在于服务器 themes/ 目录，可先点「扫描本地」。') }}
            </p>
          </div>

          <div
            v-else-if="installSource === 'remote'"
            class="flex flex-col gap-3"
          >
            <div class="flex flex-col gap-2">
              <Label class="text-sm font-medium">
                {{ t('admin.themes.installUrl', '主题包 URL') }}
              </Label>
              <Input
                v-model="installRemoteUrl"
                type="url"
                class="rounded-xl"
                placeholder="https://example.com/theme.zip"
              />
            </div>
            <div class="flex flex-col gap-2">
              <Label class="text-sm font-medium">
                {{ t('admin.themes.installChecksum', 'SHA256 校验和（可选）') }}
              </Label>
              <Input
                v-model="installRemoteChecksum"
                class="rounded-xl font-mono text-xs"
                :placeholder="t('admin.themes.installChecksumHint', '留空则跳过校验')"
              />
            </div>
          </div>

          <div
            v-else
            class="flex flex-col gap-2"
          >
            <Label class="text-sm font-medium">
              {{ t('admin.themes.installFile', 'zip 文件') }}
            </Label>
            <Input
              type="file"
              accept=".zip,application/zip"
              class="rounded-xl"
              @change="onInstallFileChange"
            />
          </div>

          <p
            v-if="installError"
            class="text-xs text-destructive flex items-center gap-1"
          >
            <AlertTriangle class="size-3.5 shrink-0" />
            {{ installError }}
          </p>
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
            :disabled="installBusy"
            @click="submitInstall"
          >
            <template v-if="installBusy">
              <RefreshCw
                data-icon="inline-start"
                class="animate-spin"
              />
              {{ t('admin.themes.installing', '安装中…') }}
            </template>
            <template v-else>
              <UploadCloud data-icon="inline-start" />
              {{ t('admin.themes.installAction', '安装') }}
            </template>
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  </div>
</template>
