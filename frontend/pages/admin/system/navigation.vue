<!--
  导航菜单管理页：全量列表 + 位置筛选 + 上下移排序 + 父子级选择 + Dialog CRUD。
  契约：交换 order 必须串行 PUT——并发两个局部更新若其一失败会留下重复 order，失败后不信任乐观状态而是 loadAll() 重同步；
  label 以完整 {zh,en,ja,zh_Hant} dict 提交（管理员名称必填校验只看 zh）；删除走 silentToast 由 DangerConfirmDialog 内联展示错误；
  location 与前台三个渲染面（顶栏 / 页脚 / 侧边栏抽屉）逐值对应，父级只能选同一位置的项——
  公开口每个渲染面只读自己那一档，跨位置的父子关系在那一面的查询里取不到父行。
  同位置的 parent_id 有真实执行者：移动抽屉 / 侧边栏抽屉 / 页脚按两档缩进渲染，
  顶栏把子项并进「更多」下拉并在宽屏平铺成真实 `<a>`（层级只到第 2 层，更深的后代并进同一个根）。
-->
<template>
  <div class="flex flex-col gap-5">
    <AdminPageHeader
      title="导航菜单管理"
      description="管理站点顶部 / 侧边的菜单项与排序"
      :icon="Menu"
    >
      <template #actions>
        <!-- 位置筛选走后端 location 参数（与公开口同一道 WHERE），不在前端滤：
             全量列表会随菜单增长变长，前端筛选等于每次都把所有行拉进来 -->
        <Select v-model="locationFilter">
          <SelectTrigger
            id="nav-location-filter"
            class="w-32 rounded-xl"
          >
            <SelectValue placeholder="位置" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">
              全部位置
            </SelectItem>
            <SelectItem
              v-for="loc in ADMIN_NAV_LOCATIONS"
              :key="loc"
              :value="loc"
            >
              {{ NAV_LOCATION_LABELS[loc] }}
            </SelectItem>
          </SelectContent>
        </Select>
        <Button
          size="sm"
          class="shadow-sm"
          @click="openCreate()"
        >
          <Plus data-icon="inline-start" /> 新建菜单项
        </Button>
      </template>
    </AdminPageHeader>

    <AdminCard>
      <div class="p-0">
        <Alert
          v-if="!loading && loadError"
          variant="destructive"
          class="rounded-xl m-5"
        >
          <AlertTriangle class="size-4" />
          <AlertTitle>导航列表加载失败</AlertTitle>
          <AlertDescription class="flex flex-wrap items-center justify-between gap-3">
            <span>{{ loadError }}</span>
            <Button
              variant="outline"
              size="sm"
              class="rounded-lg shrink-0"
              @click="loadAll"
            >
              <RotateCcw data-icon="inline-start" />
              重试
            </Button>
          </AlertDescription>
        </Alert>

        <div
          v-if="loading"
          class="flex flex-col gap-3 p-6"
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
            <AlertTitle>{{ locationFilterLabel ? `${locationFilterLabel}暂无菜单项` : '暂无菜单项' }}</AlertTitle>
            <AlertDescription>
              <template v-if="locationFilter === 'all'">
                点击右上角「新建菜单项」开始添加第一个导航。
              </template>
              <template v-else>
                {{ locationFilterLabel }}位置还没有菜单项，前台对应的是{{ locationConsumerHint }}点「新建菜单项」添加，或把已有项的位置改到这里。
              </template>
            </AlertDescription>
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
            :class="item.is_active ? '' : 'opacity-60'"
          >
            <div class="flex flex-col items-center gap-0.5 rounded-lg border border-border/50 bg-background/50 p-0.5">
              <button
                type="button"
                class="size-8 rounded-md inline-flex items-center justify-center text-muted-foreground hover:text-foreground hover:bg-muted disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
                :disabled="isFirst(item) || swapping"
                title="上移"
                aria-label="上移菜单项"
                @click="moveUp(item)"
              >
                <ChevronUp class="size-4" />
              </button>
              <button
                type="button"
                class="size-8 rounded-md inline-flex items-center justify-center text-muted-foreground hover:text-foreground hover:bg-muted disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
                :disabled="isLast(item) || swapping"
                title="下移"
                aria-label="下移菜单项"
                @click="moveDown(item)"
              >
                <ChevronDown class="size-4" />
              </button>
            </div>

            <div class="flex-1 min-w-0">
              <div class="flex items-center gap-2 flex-wrap">
                <span class="font-semibold">{{ extractZh(item.label ?? '') || '（未命名）' }}</span>
                <Badge
                  v-if="locationFilter === 'all'"
                  variant="outline"
                  class="text-xs"
                >
                  {{ NAV_LOCATION_LABELS[item.location] }}
                </Badge>
                <Badge
                  v-if="!item.is_active"
                  variant="secondary"
                  class="text-xs"
                >
                  已停用
                </Badge>
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
              <!-- 常驻操作：旧版 hover 才出现，触屏/键盘用户看不到编辑与删除 -->
              <AdminRowActions
                :actions="[
                  { key: 'edit', label: '编辑菜单项', icon: Pencil, onClick: () => openEdit(item) },
                  { key: 'delete', label: '删除菜单项', icon: Trash2, destructive: true, onClick: () => handleDelete(item) }
                ]"
              />
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
        <div class="flex flex-col gap-4 py-2">
          <I18nTabsEditor
            v-model="form.label"
            kind="text"
            label="显示名称"
            :required="true"
          />
          <div class="flex flex-col gap-2">
            <Label
              for="nav-url"
              class="text-sm font-medium"
            >链接 URL <span class="text-error">*</span></Label>
            <Input
              id="nav-url"
              v-model="form.url"
              placeholder="https:// 或 /posts 内部路由"
              class="rounded-xl"
            />
          </div>
          <div class="grid grid-cols-2 gap-4">
            <div class="flex flex-col gap-2">
              <Label
                for="nav-location"
                class="text-sm font-medium"
              >菜单位置</Label>
              <Select v-model="form.location">
                <SelectTrigger
                  id="nav-location"
                  class="rounded-xl"
                >
                  <SelectValue placeholder="选择位置" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem
                    v-for="loc in ADMIN_NAV_LOCATIONS"
                    :key="loc"
                    :value="loc"
                  >
                    {{ NAV_LOCATION_LABELS[loc] }}
                  </SelectItem>
                </SelectContent>
              </Select>
              <p class="text-xs text-muted-foreground">
                {{ locationConsumerHintOf(form.location) }}
              </p>
            </div>
            <div class="flex flex-col gap-2">
              <Label
                for="nav-active"
                class="text-sm font-medium"
              >前台显示</Label>
              <div class="flex items-center gap-2 pt-1.5">
                <Switch
                  id="nav-active"
                  v-model="form.is_active"
                />
                <span class="text-sm">{{ form.is_active ? '显示' : '隐藏（仅后台可见）' }}</span>
              </div>
            </div>
          </div>
          <div class="grid grid-cols-2 gap-4">
            <div class="flex flex-col gap-2">
              <Label
                for="nav-icon"
                class="text-sm font-medium"
              >图标（可选）</Label>
              <Input
                id="nav-icon"
                v-model="form.icon"
                placeholder="如 Home / Star"
                class="rounded-xl"
              />
            </div>
            <div class="flex flex-col gap-2">
              <Label
                for="nav-order"
                class="text-sm font-medium"
              >排序 order</Label>
              <Input
                id="nav-order"
                v-model.number="form.order"
                type="number"
                class="rounded-xl"
              />
            </div>
          </div>
          <div class="flex flex-col gap-2">
            <Label class="text-sm font-medium">打开方式</Label>
            <div class="flex items-center gap-4">
              <label class="inline-flex items-center gap-2 cursor-pointer">
                <input
                  v-model="form.target"
                  type="radio"
                  value="_self"
                  class="accent-[hsl(var(--primary))]"
                >
                <span class="text-sm">当前窗口</span>
              </label>
              <label class="inline-flex items-center gap-2 cursor-pointer">
                <input
                  v-model="form.target"
                  type="radio"
                  value="_blank"
                  class="accent-[hsl(var(--primary))]"
                >
                <span class="text-sm">新窗口</span>
              </label>
            </div>
          </div>
          <div class="flex flex-col gap-2">
            <Label
              for="nav-parent"
              class="text-sm font-medium"
            >父级菜单（可选，仅同位置可选）</Label>
            <Select v-model="form.parent_id">
              <SelectTrigger
                id="nav-parent"
                class="rounded-xl"
              >
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
              data-icon="inline-start"
              class="animate-spin"
            />
            <Save
              v-else
              data-icon="inline-start"
            />
            {{ editingId ? '保存修改' : '创建菜单' }}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>

    <DangerConfirmDialog
      v-model:open="confirmOpen"
      title="确认删除菜单项？"
      :description="`「${extractZh(deleteTarget?.label ?? '') || '未命名'}」将被永久删除，无法恢复；若有子菜单将一同解除关联。`"
      confirm-text="确认删除"
      :on-confirm="confirmDelete"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import {
  fetchAdminNavigations,
  createAdminNavigation,
  updateAdminNavigation,
  deleteAdminNavigation,
  ADMIN_NAV_LOCATIONS,
  NAV_LOCATION_LABELS,
  type AdminNavItem,
  type AdminNavLocation
} from '~~/composables/useAdminManage'
import { useToast } from '~~/composables/useToast'
import { extractApiErrorMessage } from '~~/lib/utils'
import {
  Menu, Plus, ChevronUp, ChevronDown, ExternalLink,
  Pencil, Trash2, Save, Loader2, Info, AlertTriangle, RotateCcw
} from '@lucide/vue'
import { Button } from '~~/components/ui/button'
import AdminCard from '~~/components/admin/AdminCard.vue'
import AdminRowActions from '~~/components/admin/AdminRowActions.vue'
import { Skeleton } from '~~/components/ui/skeleton'
import { Badge } from '~~/components/ui/badge'
import {
  Dialog, DialogContent, DialogDescription, DialogFooter,
  DialogHeader, DialogTitle
} from '~~/components/ui/dialog'
import { Label } from '~~/components/ui/label'
import { Input } from '~~/components/ui/input'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '~~/components/ui/select'
import { Switch } from '~~/components/ui/switch'
import { Alert, AlertTitle, AlertDescription } from '~~/components/ui/alert'
import I18nTabsEditor from '~~/components/admin/I18nTabsEditor.vue'
import DangerConfirmDialog from '~~/components/admin/tools/DangerConfirmDialog.vue'
import { EMPTY_I18N_DICT } from '~~/composables/useAdminI18n'

definePageMeta({ ssr: false, layout: 'admin' })

const toast = useToast()

const loading = ref(true)
const loadError = ref('')
const items = ref<AdminNavItem[]>([])
const dialogOpen = ref(false)
const confirmOpen = ref(false)
const submitting = ref(false)
const swapping = ref(false)
const editingId = ref<number | null>(null)
const deleteTarget = ref<AdminNavItem | null>(null)

/** 'all' = 不带 location 参数（后端回全量）；其余值直接进 GET /admin/navigations?location= */
const locationFilter = ref<AdminNavLocation | 'all'>('all')

/**
 * 每个位置对应的前台渲染面（唯一清单，与 components 侧一一对应）：
 * 顶栏/移动抽屉读 header，页脚「网站导航」读 footer，侧边栏抽屉读 sidebar。
 * 后台只列档位不说清"谁在渲染"，运营者就会把项存进没人读的位置。
 */
const LOCATION_CONSUMER_HINTS: Record<AdminNavLocation, string> = {
  header: '前台顶栏与移动端菜单抽屉读取这一档。',
  footer: '页脚「网站导航」一节读取这一档。',
  sidebar: '桌面侧边栏抽屉的「侧边栏」一节读取这一档。'
}
const locationConsumerHintOf = (loc: AdminNavLocation): string => LOCATION_CONSUMER_HINTS[loc]
const locationFilterLabel = computed(() =>
  locationFilter.value === 'all' ? '' : NAV_LOCATION_LABELS[locationFilter.value]
)
const locationConsumerHint = computed(() =>
  locationFilter.value === 'all' ? '' : locationConsumerHintOf(locationFilter.value)
)

const emptyForm = () => ({
  label: { ...EMPTY_I18N_DICT } as Record<string, string>,
  url: '',
  icon: '',
  target: '_self' as '_self' | '_blank',
  order: 0,
  parent_id: null as number | null,
  location: 'header' as AdminNavLocation,
  is_active: true
})
const form = ref(emptyForm())

const sortedItems = computed(() => [...items.value].sort((a, b) => a.order - b.order || a.id - b.id))

const parentOptions = computed(() =>
  sortedItems.value
    // 父级只能同位置且不能是自己：公开口每个渲染面只读一档，跨位置的父子关系
    // 在那一面的查询里根本取不到父行；把自己选成父级则是直接成环。
    .filter(i => editingId.value == null || i.id !== editingId.value)
    .filter(i => i.location === form.value.location)
    .map(i => ({ label: extractZh(i.label) || `#${i.id}`, value: i.id }))
)

// 换位置后原来的父级已不在候选里，不清掉会把一条"父级在别的位置"的关系留在库里
watch(() => form.value.location, () => {
  if (!parentOptions.value.some(opt => opt.value === form.value.parent_id)) {
    form.value.parent_id = null
  }
})

function extractZh(label: AdminNavItem['label']): string {
  if (typeof label === 'string') return label
  if (label && typeof label === 'object' && 'zh' in label) return (label as Record<string, string>).zh ?? ''
  if (label) return Object.values(label as Record<string, string>)[0] || ''
  return ''
}

function normalizeLabel(label: AdminNavItem['label']): Record<string, string> {
  const base = { ...EMPTY_I18N_DICT }
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
  if (swapping.value) return
  swapping.value = true
  const origA = a.order
  const origB = b.order
  try {
    // 串行 PUT：并发两个局部更新若其中一个失败会留下重复 order，
    // 失败时统一 loadAll() 从后端重新同步，不信任本地乐观状态
    await updateAdminNavigation(a.id, { order: origB })
    await updateAdminNavigation(b.id, { order: origA })
    a.order = origB
    b.order = origA
    toast.success('排序已更新')
  } catch (e) {
    // updateAdminNavigation 的 apiFetch 已 toast，这里只重同步列表
    console.error('[navigation] swapOrder failed:', e)
    await loadAll()
  } finally {
    swapping.value = false
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
  loadError.value = ''
  try {
    items.value = await fetchAdminNavigations(
      locationFilter.value === 'all' ? undefined : locationFilter.value
    )
  } catch (e) {
    // fetchAdminNavigations 内部 apiFetch 已 toast；这里补充内联错误态 + 重试
    items.value = []
    const err = e as { data?: unknown, message?: string }
    loadError.value = extractApiErrorMessage(err?.data, err?.message || '加载导航列表失败')
  } finally {
    loading.value = false
  }
}

watch(locationFilter, loadAll)

function openCreate() {
  editingId.value = null
  form.value = emptyForm()
  // 带位置筛选时新建，默认落进当前筛选的那一档，省一次「建完再改位置」
  if (locationFilter.value !== 'all') form.value.location = locationFilter.value
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
    parent_id: item.parent_id,
    location: item.location,
    is_active: item.is_active
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
    parent_id: form.value.parent_id,
    location: form.value.location,
    is_active: form.value.is_active
  }
  try {
    if (editingId.value) {
      await updateAdminNavigation(editingId.value, payload)
      toast.success('菜单项已更新')
    } else {
      await createAdminNavigation(payload)
      toast.success('菜单项已创建')
    }
    dialogOpen.value = false
    // 新建响应回的是后端原始行（title/target_blank 形态），且改过位置或显隐后
    // 未必还落在当前筛选里——统一 loadAll 拿标准化后的全量，不在本地拼。
    await loadAll()
  } catch (e) {
    // create/update 的 apiFetch 失败时已 toast 展示后端错误，不再二次提示
    console.error('[navigation] handleSubmit failed:', e)
  } finally {
    submitting.value = false
  }
}

function handleDelete(item: AdminNavItem) {
  deleteTarget.value = item
  confirmOpen.value = true
}

/**
 * DangerConfirmDialog 的 onConfirm：
 * throw 时弹窗保持打开并内联展示错误（请求走 silentToast 避免 toast 与内联双重提示）。
 */
async function confirmDelete() {
  const target = deleteTarget.value
  if (!target) return
  await deleteAdminNavigation(target.id, { silentToast: true })
  toast.success('菜单项已删除')
  deleteTarget.value = null
  await loadAll()
}

onMounted(loadAll)
</script>
