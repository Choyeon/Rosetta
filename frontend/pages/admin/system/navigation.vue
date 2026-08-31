<template>
  <div class="p-6 space-y-6">
    <div class="flex items-center justify-between">
      <div class="flex items-center gap-3">
        <div
          class="size-10 rounded-xl flex items-center justify-center bg-primary text-primary-foreground"
        >
          <Menu class="size-5 text-white" />
        </div>
        <div>
          <h1 class="text-xl font-bold tracking-tight">
            导航菜单管理
          </h1>
          <p class="text-sm text-muted-foreground">
            管理站点顶部 / 侧边的菜单项与排序
          </p>
        </div>
      </div>
      <Button
        class="shadow-sm"
        @click="openCreate()"
      >
        <Plus class="size-4" /> 新建菜单项
      </Button>
    </div>

    <AdminCard>
      <div class="p-0">
        <div
          v-if="loading"
          class="p-6 space-y-3"
        >
          <Skeleton
            v-for="i in 5"
            :key="i"
            class="h-14 rounded-xl"
          />
        </div>

        <div
          v-else-if="items.length === 0"
          class="p-12"
        >
          <Alert
            variant="info"
            class="rounded-xl max-w-lg mx-auto"
          >
            <Info class="size-4" />
            <AlertTitle>暂无菜单项</AlertTitle>
            <AlertDescription>点击右上角「新建菜单项」开始添加第一个导航。</AlertDescription>
          </Alert>
        </div>

        <div
          v-else
          class="divide-y divide-border"
        >
          <div
            v-for="item in sortedItems"
            :key="item.id"
            class="flex items-center gap-3 px-5 py-4 hover:bg-muted/40 transition-colors group"
          >
            <div class="flex flex-col items-center gap-0.5">
              <button
                type="button"
                class="size-7 rounded-lg inline-flex items-center justify-center text-muted-foreground hover:text-foreground hover:bg-muted disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
                :disabled="isFirst(item)"
                title="上移"
                @click="moveUp(item)"
              >
                <ChevronUp class="size-4" />
              </button>
              <button
                type="button"
                class="size-7 rounded-lg inline-flex items-center justify-center text-muted-foreground hover:text-foreground hover:bg-muted disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
                :disabled="isLast(item)"
                title="下移"
                @click="moveDown(item)"
              >
                <ChevronDown class="size-4" />
              </button>
            </div>

            <div
              class="size-9 rounded-lg bg-muted/60 inline-flex items-center justify-center text-muted-foreground shrink-0"
              title="拖拽排序（此处使用上下按钮）"
            >
              <GripVertical class="size-4" />
            </div>

            <div class="flex-1 min-w-0">
              <div class="flex items-center gap-2 flex-wrap">
                <span class="font-semibold">{{ extractZh(item.label ?? '') || '（未命名）' }}</span>
                <Badge
                  v-if="item.parent_id"
                  variant="outline"
                  class="text-xs"
                >
                  二级菜单
                </Badge>
                <Badge
                  v-if="item.target === '_blank'"
                  variant="secondary"
                  class="text-xs"
                >
                  <ExternalLink class="size-3 mr-0.5" /> 新窗口
                </Badge>
              </div>
              <div class="flex items-center gap-2 mt-1 text-sm text-muted-foreground">
                <span class="truncate font-mono text-xs bg-muted/50 px-2 py-0.5 rounded">{{ item.url }}</span>
                <span
                  v-if="item.icon"
                  class="text-xs truncate"
                >· 图标: {{ item.icon }}</span>
              </div>
            </div>

            <div class="flex items-center gap-2 shrink-0">
              <div class="flex items-center gap-1.5 bg-muted/40 rounded-lg px-2.5 py-1">
                <span class="text-xs text-muted-foreground">排序</span>
                <span class="font-semibold tabular-nums text-sm">{{ item.order }}</span>
              </div>
              <div class="opacity-0 group-hover:opacity-100 transition-opacity flex items-center gap-1">
                <Button
                  variant="ghost"
                  size="icon-sm"
                  title="编辑"
                  @click="openEdit(item)"
                >
                  <Pencil class="size-4" />
                </Button>
                <Button
                  variant="ghost"
                  size="icon-sm"
                  class="text-error hover:text-error hover:bg-error-muted"
                  title="删除"
                  @click="handleDelete(item)"
                >
                  <Trash2 class="size-4" />
                </Button>
              </div>
            </div>
          </div>
        </div>
      </div>
    </AdminCard>

    <Dialog v-model:open="dialogOpen">
      <DialogContent class="max-w-xl rounded-2xl">
        <DialogHeader>
          <DialogTitle>{{ editingId ? '编辑菜单项' : '新建菜单项' }}</DialogTitle>
          <DialogDescription>
            填写导航菜单的显示名称、跳转链接与排序。
          </DialogDescription>
        </DialogHeader>
        <div class="space-y-4 py-2">
          <I18nTabsEditor
            v-model="form.label"
            kind="text"
            label="显示名称"
            :required="true"
          />
          <div class="space-y-2">
            <Label class="text-sm font-medium">链接 URL <span class="text-error">*</span></Label>
            <Input
              v-model="form.url"
              placeholder="https:// 或 /posts 内部路由"
              class="rounded-xl"
            />
          </div>
          <div class="grid grid-cols-2 gap-4">
            <div class="space-y-2">
              <Label class="text-sm font-medium">图标（可选）</Label>
              <Input
                v-model="form.icon"
                placeholder="如 Home / Star"
                class="rounded-xl"
              />
            </div>
            <div class="space-y-2">
              <Label class="text-sm font-medium">排序 order</Label>
              <Input
                v-model.number="form.order"
                type="number"
                class="rounded-xl"
              />
            </div>
          </div>
          <div class="space-y-2">
            <Label class="text-sm font-medium">打开方式</Label>
            <div class="flex items-center gap-4">
              <label class="inline-flex items-center gap-2 cursor-pointer">
                <input
                  v-model="form.target"
                  type="radio"
                  value="_self"
                  class="accent-[#0EA5E9]"
                >
                <span class="text-sm">当前窗口</span>
              </label>
              <label class="inline-flex items-center gap-2 cursor-pointer">
                <input
                  v-model="form.target"
                  type="radio"
                  value="_blank"
                  class="accent-[#0EA5E9]"
                >
                <span class="text-sm">新窗口</span>
              </label>
            </div>
          </div>
          <div class="space-y-2">
            <Label class="text-sm font-medium">父级菜单（可选，做二级菜单）</Label>
            <Select v-model="form.parent_id">
              <SelectTrigger class="rounded-xl">
                <SelectValue placeholder="无（一级菜单）" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem :value="null">
                  无（一级菜单）
                </SelectItem>
                <SelectItem
                  v-for="opt in parentOptions"
                  :key="opt.value"
                  :value="opt.value"
                >
                  {{ opt.label }}
                </SelectItem>
              </SelectContent>
            </Select>
          </div>
        </div>
        <DialogFooter>
          <Button
            variant="outline"
            class="rounded-xl"
            @click="dialogOpen = false"
          >
            取消
          </Button>
          <Button
            :disabled="submitting"
            class="rounded-xl shadow-sm"
            @click="handleSubmit"
          >
            <Loader2
              v-if="submitting"
              class="size-4 animate-spin"
            />
            <Save
              v-else
              class="size-4"
            />
            {{ editingId ? '保存修改' : '创建菜单' }}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>

    <Dialog v-model:open="confirmOpen">
      <DialogContent class="max-w-sm rounded-2xl">
        <DialogHeader>
          <DialogTitle>确认删除菜单项？</DialogTitle>
          <DialogDescription>删除后无法恢复，若有子菜单将一同解除关联。</DialogDescription>
        </DialogHeader>
        <DialogFooter class="gap-2">
          <Button
            variant="outline"
            class="rounded-xl"
            :disabled="deleting"
            @click="confirmOpen = false"
          >
            取消
          </Button>
          <Button
            variant="destructive"
            class="rounded-xl"
            :disabled="deleting"
            @click="confirmDelete"
          >
            <Loader2
              v-if="deleting"
              class="size-4 animate-spin"
            />
            <Trash2
              v-else
              class="size-4"
            />
            确认删除
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import {
  fetchAdminNavigations,
  createAdminNavigation,
  updateAdminNavigation,
  deleteAdminNavigation,
  type AdminNavItem
} from '~~/composables/useAdminManage'
import { useToast } from '~~/composables/useToast'
import {
  Menu, Plus, ChevronUp, ChevronDown, GripVertical, ExternalLink,
  Pencil, Trash2, Save, Loader2, Info
} from '@lucide/vue'
import { Button } from '~~/components/ui/button'
import AdminCard from '~~/components/admin/AdminCard.vue'
import { Skeleton } from '~~/components/ui/skeleton'
import { Badge } from '~~/components/ui/badge'
import {
  Dialog, DialogContent, DialogDescription, DialogFooter,
  DialogHeader, DialogTitle
} from '~~/components/ui/dialog'
import { Label } from '~~/components/ui/label'
import { Input } from '~~/components/ui/input'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '~~/components/ui/select'
import { Alert, AlertTitle, AlertDescription } from '~~/components/ui/alert'
import I18nTabsEditor from '~~/components/admin/I18nTabsEditor.vue'

definePageMeta({ ssr: false, layout: 'admin' })

const toast = useToast()

const loading = ref(true)
const items = ref<AdminNavItem[]>([])
const dialogOpen = ref(false)
const confirmOpen = ref(false)
const submitting = ref(false)
const deleting = ref(false)
const editingId = ref<number | null>(null)
const deleteTarget = ref<AdminNavItem | null>(null)

const emptyForm = () => ({
  label: { zh: '', en: '', ja: '', zh_Hant: '' } as Record<string, string>,
  url: '',
  icon: '',
  target: '_self' as '_self' | '_blank',
  order: 0,
  parent_id: null as number | null
})
const form = ref(emptyForm())

const sortedItems = computed(() => [...items.value].sort((a, b) => a.order - b.order || a.id - b.id))

const parentOptions = computed(() =>
  sortedItems.value
    .filter(i => editingId.value == null || i.id !== editingId.value)
    .map(i => ({ label: extractZh(i.label) || `#${i.id}`, value: i.id }))
)

function extractZh(label: AdminNavItem['label']): string {
  if (typeof label === 'string') return label
  if (label && typeof label === 'object' && 'zh' in label) return (label as Record<string, string>).zh ?? ''
  if (label) return Object.values(label as Record<string, string>)[0] || ''
  return ''
}

function normalizeLabel(label: AdminNavItem['label']): Record<string, string> {
  const base = { zh: '', en: '', ja: '', zh_Hant: '' }
  if (label == null) return base
  if (typeof label === 'string') {
    return { ...base, zh: label }
  }
  const obj = label as Record<string, string | null | undefined>
  return {
    zh: obj.zh ?? '',
    en: obj.en ?? '',
    ja: obj.ja ?? '',
    zh_Hant: obj.zh_Hant ?? ''
  }
}

function isFirst(item: AdminNavItem): boolean {
  const list = sortedItems.value
  return list.length === 0 || list[0]!.id === item.id
}

function isLast(item: AdminNavItem): boolean {
  const list = sortedItems.value
  return list.length === 0 || list[list.length - 1]!.id === item.id
}

async function swapOrder(a: AdminNavItem, b: AdminNavItem) {
  const origA = a.order
  const origB = b.order
  try {
    await Promise.all([
      updateAdminNavigation(a.id, { order: origB }),
      updateAdminNavigation(b.id, { order: origA })
    ])
    a.order = origB
    b.order = origA
    toast.success('排序已更新')
  } catch (e) {
    console.error('[navigation] swapOrder failed:', e)
    toast.error('更新排序失败')
  }
}

function moveUp(item: AdminNavItem) {
  const idx = sortedItems.value.findIndex(i => i.id === item.id)
  if (idx <= 0) return
  swapOrder(item, sortedItems.value[idx - 1]!)
}

function moveDown(item: AdminNavItem) {
  const idx = sortedItems.value.findIndex(i => i.id === item.id)
  if (idx < 0 || idx >= sortedItems.value.length - 1) return
  swapOrder(item, sortedItems.value[idx + 1]!)
}

async function loadAll() {
  loading.value = true
  try {
    items.value = await fetchAdminNavigations()
  } catch (e) {
    console.error('[navigation] loadAll failed:', e)
    toast.error('加载导航列表失败')
    items.value = []
  } finally {
    loading.value = false
  }
}

function openCreate() {
  editingId.value = null
  form.value = emptyForm()
  const max = items.value.reduce((m, i) => Math.max(m, i.order), -1)
  form.value.order = max + 1
  dialogOpen.value = true
}

function openEdit(item: AdminNavItem) {
  editingId.value = item.id
  form.value = {
    label: normalizeLabel(item.label),
    url: item.url,
    icon: item.icon ?? '',
    target: item.target || '_self',
    order: item.order,
    parent_id: item.parent_id
  }
  dialogOpen.value = true
}

async function handleSubmit() {
  if (!String(form.value.label.zh ?? '').trim() || !form.value.url.trim()) {
    toast.warning('请填写名称与 URL')
    return
  }
  submitting.value = true
  const payload = {
    label: form.value.label,
    url: form.value.url.trim(),
    icon: form.value.icon.trim() || null,
    target: form.value.target,
    order: Number(form.value.order) || 0,
    parent_id: form.value.parent_id
  }
  try {
    if (editingId.value) {
      await updateAdminNavigation(editingId.value, payload)
      toast.success('菜单项已更新')
    } else {
      const r = await createAdminNavigation(payload)
      items.value.push(r)
      toast.success('菜单项已创建')
    }
    dialogOpen.value = false
    await loadAll()
  } catch (e) {
    console.error('[navigation] handleSubmit failed:', e)
    toast.error(editingId.value ? '更新导航失败' : '创建导航失败')
  } finally {
    submitting.value = false
  }
}

function handleDelete(item: AdminNavItem) {
  deleteTarget.value = item
  confirmOpen.value = true
}

async function confirmDelete() {
  if (!deleteTarget.value) return
  deleting.value = true
  try {
    await deleteAdminNavigation(deleteTarget.value.id)
    items.value = items.value.filter(i => i.id !== deleteTarget.value!.id)
    toast.success('菜单项已删除')
    confirmOpen.value = false
  } catch (e) {
    console.error('[navigation] confirmDelete failed:', e)
    toast.error('删除导航失败')
  } finally {
    deleting.value = false
  }
}

onMounted(loadAll)
</script>
