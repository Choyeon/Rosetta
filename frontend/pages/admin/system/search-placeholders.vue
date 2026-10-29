<!--
  搜索占位符管理页：列表 + Dialog CRUD。

  这一族此前是**半接通**：模型 `SearchPlaceholder` 与公开读口 `GET /api/search-placeholders` 都在，
  前台 `/posts` 也真的在轮播这些文案，但全仓没有任何写口——运营者既看不到也管不了，
  表里永远只有"没有行"这一种状态（空则回退 i18n 的 posts.searchPlaceholder）。
  本页与后端 `/search-placeholders` 的 POST/PUT/DELETE + `/search-placeholders/all` 同批落地。

  两条口径：
  * text 是四语 dict，提交时保留完整形态（至少一种语言非空，后端 422 兜底）；不做语言解析，
    解析只发生在公开口——后台把单语字符串当 zh 重组会抹掉其余语言。
  * 停用（is_active=false）只是从公开口消失，不影响行本身；前台 SSR 页面缓存由后端
    写路径 purge，改完刷新即可见，无需手工清缓存。
-->
<template>
  <div class="flex flex-col gap-5">
    <AdminPageHeader
      title="搜索占位符"
      description="文章列表页搜索框轮播的提示文案；为空时回退站点默认文案"
      :icon="Search"
    >
      <template #actions>
        <Button
          size="sm"
          class="shadow-sm"
          @click="openCreate()"
        >
          <Plus data-icon="inline-start" /> 新建占位文本
        </Button>
      </template>
    </AdminPageHeader>

    <Alert
      v-if="!loading && loadError"
      variant="destructive"
      class="rounded-xl"
    >
      <AlertTriangle class="size-4" />
      <AlertTitle>占位符列表加载失败</AlertTitle>
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

    <Alert
      variant="info"
      class="rounded-xl"
    >
      <Info class="size-4" />
      <AlertTitle>前台如何消费</AlertTitle>
      <AlertDescription>
        「文章列表」页搜索框按请求语言随机轮播启用中的文案；某条语言没填时回退默认语言，
        四语全空的行不会显示，所以后端会直接拒绝这种写法。
      </AlertDescription>
    </Alert>

    <div
      v-if="loading"
      class="flex flex-col gap-3"
    >
      <Skeleton
        v-for="i in 4"
        :key="i"
        class="h-20 rounded-2xl"
      />
    </div>

    <div
      v-else-if="items.length === 0"
      class="py-16"
    >
      <Alert
        variant="info"
        class="rounded-xl max-w-lg mx-auto"
      >
        <Info class="size-4" />
        <AlertTitle>还没有占位文本</AlertTitle>
        <AlertDescription>点击右上方「新建占位文本」添加；未添加时前台使用默认提示语。</AlertDescription>
      </Alert>
    </div>

    <div
      v-else
      class="flex flex-col gap-3"
    >
      <div
        v-for="item in items"
        :key="item.id"
        class="card-surface lift-hover flex flex-col gap-3 p-4 sm:flex-row sm:items-center sm:justify-between"
      >
        <div class="flex min-w-0 flex-1 flex-col gap-1.5">
          <div class="flex min-w-0 items-center gap-2">
            <span
              class="truncate font-medium"
              :class="item.is_active ? '' : 'text-muted-foreground line-through'"
            >
              {{ previewOf(item) }}
            </span>
            <Badge
              :variant="item.is_active ? 'default' : 'secondary'"
              class="shrink-0 text-[11px]"
            >
              {{ item.is_active ? '启用中' : '已停用' }}
            </Badge>
          </div>
          <div class="flex flex-wrap items-center gap-1.5 text-xs text-muted-foreground">
            <Badge
              v-for="code in localeCodes"
              :key="code"
              variant="outline"
              class="text-[10px] !py-0 rounded-full"
              :class="(item.text[code] ?? '').trim() ? '' : 'opacity-40'"
              :title="(item.text[code] ?? '').trim() || '该语言未填写'"
            >
              {{ code }} {{ (item.text[code] ?? '').trim() ? '✓' : '—' }}
            </Badge>
            <span class="tabular-nums">排序 #{{ item.sort_order }}</span>
          </div>
        </div>

        <div class="flex shrink-0 items-center gap-2">
          <Tooltip>
            <TooltipTrigger as-child>
              <div class="flex items-center">
                <Switch
                  :model-value="item.is_active"
                  :aria-label="`切换「${previewOf(item)}」启用状态`"
                  @update:model-value="(v: boolean) => toggleActive(item, v)"
                />
              </div>
            </TooltipTrigger>
            <TooltipContent>{{ item.is_active ? '停用（前台不再轮播）' : '启用' }}</TooltipContent>
          </Tooltip>
          <Tooltip>
            <TooltipTrigger as-child>
              <Button
                variant="ghost"
                size="icon-sm"
                aria-label="编辑占位文本"
                @click="openEdit(item)"
              >
                <Pencil data-icon="inline-start" />
              </Button>
            </TooltipTrigger>
            <TooltipContent>编辑</TooltipContent>
          </Tooltip>
          <Tooltip>
            <TooltipTrigger as-child>
              <Button
                variant="ghost"
                size="icon-sm"
                class="text-destructive hover:text-destructive hover:bg-destructive-muted"
                aria-label="删除占位文本"
                @click="handleDelete(item)"
              >
                <Trash2 data-icon="inline-start" />
              </Button>
            </TooltipTrigger>
            <TooltipContent>删除</TooltipContent>
          </Tooltip>
        </div>
      </div>
    </div>

    <Dialog v-model:open="dialogOpen">
      <DialogContent class="max-w-xl rounded-2xl">
        <DialogHeader>
          <DialogTitle>{{ editingId ? '编辑占位文本' : '新建占位文本' }}</DialogTitle>
          <DialogDescription>建议写成不完整的短句，与访客要搜的主题相关。</DialogDescription>
        </DialogHeader>
        <div class="flex flex-col gap-4 py-2">
          <I18nTabsEditor
            v-model="form.text"
            kind="text"
            label="占位文本"
            placeholder="如：搜索你想看的文章…"
            :required="true"
            flat
          />
          <div class="grid grid-cols-2 gap-4">
            <div class="flex flex-col gap-2">
              <Label
                for="sp-order"
                class="text-sm font-medium"
              >{{ t('adminCommon.sortOrder') }}</Label>
              <Input
                id="sp-order"
                v-model.number="form.sort_order"
                type="number"
                min="0"
                class="rounded-xl"
              />
            </div>
            <div class="flex flex-col justify-end gap-2">
              <div class="flex items-center justify-between gap-3 rounded-[12px] border border-border bg-muted/20 px-4 py-2.5">
                <Label
                  for="sp-active"
                  class="text-sm font-medium"
                >启用</Label>
                <Switch
                  id="sp-active"
                  v-model="form.is_active"
                />
              </div>
            </div>
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
            class="rounded-xl"
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
            {{ editingId ? '保存修改' : '创建' }}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>

    <DangerConfirmDialog
      v-model:open="confirmOpen"
      title="确认删除占位文本？"
      :description="`「${previewOf(deleteTarget)}」将被永久删除，无法撤销。`"
      confirm-text="确认删除"
      :on-confirm="confirmDelete"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import {
  fetchAdminSearchPlaceholders,
  createAdminSearchPlaceholder,
  updateAdminSearchPlaceholder,
  deleteAdminSearchPlaceholder,
  type AdminSearchPlaceholder
} from '~~/composables/useAdminManage'
import { useToast } from '~~/composables/useToast'
import { extractApiErrorMessage } from '~~/lib/utils'
import { Search, Plus, Pencil, Trash2, Save, Loader2, Info, AlertTriangle, RotateCcw } from '@lucide/vue'
import { useI18n } from 'vue-i18n'
import { Button } from '~~/components/ui/button'
import { Skeleton } from '~~/components/ui/skeleton'
import { Badge } from '~~/components/ui/badge'
import {
  Dialog, DialogContent, DialogDescription, DialogFooter,
  DialogHeader, DialogTitle
} from '~~/components/ui/dialog'
import { Label } from '~~/components/ui/label'
import { Input } from '~~/components/ui/input'
import { Switch } from '~~/components/ui/switch'
import { Tooltip, TooltipContent, TooltipTrigger } from '~~/components/ui/tooltip'
import { Alert, AlertTitle, AlertDescription } from '~~/components/ui/alert'
import I18nTabsEditor from '~~/components/admin/I18nTabsEditor.vue'
import DangerConfirmDialog from '~~/components/admin/tools/DangerConfirmDialog.vue'
import AdminPageHeader from '~~/components/admin/AdminPageHeader.vue'
import { EMPTY_I18N_DICT } from '~~/composables/useAdminI18n'

definePageMeta({ ssr: false, layout: 'admin' })

const { t } = useI18n()
const toast = useToast()

const localeCodes = ['zh', 'en', 'ja', 'zh_Hant'] as const

const loading = ref(true)
const loadError = ref('')
const items = ref<AdminSearchPlaceholder[]>([])
const dialogOpen = ref(false)
const confirmOpen = ref(false)
const submitting = ref(false)
const editingId = ref<number | null>(null)
const deleteTarget = ref<AdminSearchPlaceholder | null>(null)

const emptyForm = () => ({
  text: { ...EMPTY_I18N_DICT } as Record<string, string>,
  sort_order: 0,
  is_active: true
})
const form = ref(emptyForm())

/** 列表预览：优先简体，其次其它语言；四语全空理论上不存在（后端拒收），留空兜底不崩。 */
function previewOf(item: AdminSearchPlaceholder | null): string {
  if (!item) return ''
  return item.text.zh || item.text.en || item.text.ja || item.text.zh_Hant || '（空文本）'
}

function normalizeI18nDict(v: Record<string, string> | string | null | undefined): Record<string, string> {
  const base = { ...EMPTY_I18N_DICT }
  if (v == null) return base
  if (typeof v === 'string') return { ...base, zh: v }
  return {
    zh: v.zh ?? '',
    en: v.en ?? '',
    ja: v.ja ?? '',
    zh_Hant: v.zh_Hant ?? ''
  }
}

async function loadAll() {
  loading.value = true
  loadError.value = ''
  try {
    items.value = await fetchAdminSearchPlaceholders()
  } catch (e) {
    // fetch 内部 apiFetch 已 toast；这里补内联错误态 + 重试，避免整页空白
    items.value = []
    const err = e as { data?: unknown, message?: string }
    loadError.value = extractApiErrorMessage(err?.data, err?.message || '加载占位符列表失败')
  } finally {
    loading.value = false
  }
}

function openCreate() {
  editingId.value = null
  form.value = emptyForm()
  const max = items.value.reduce((m, i) => Math.max(m, i.sort_order), -1)
  form.value.sort_order = max + 1
  dialogOpen.value = true
}

function openEdit(item: AdminSearchPlaceholder) {
  editingId.value = item.id
  form.value = {
    text: normalizeI18nDict(item.text),
    sort_order: item.sort_order,
    // 必须回填：不回填等于每次编辑都顺手把一条停用行重新启用
    is_active: item.is_active
  }
  dialogOpen.value = true
}

async function handleSubmit() {
  const hasText = localeCodes.some(code => String(form.value.text[code] ?? '').trim() !== '')
  if (!hasText) {
    toast.warning('请至少填写一种语言的提示文案')
    return
  }
  submitting.value = true
  const payload = {
    text: form.value.text,
    order: Math.max(0, Number(form.value.sort_order) || 0),
    is_active: form.value.is_active === true
  }
  try {
    if (editingId.value) {
      await updateAdminSearchPlaceholder(editingId.value, payload)
      toast.success('提示文案已更新')
    } else {
      await createAdminSearchPlaceholder(payload)
      toast.success('提示文案已创建')
    }
    dialogOpen.value = false
    await loadAll()
  } catch (e) {
    // apiFetch 失败已 toast；这里只留日志，不二次提示
    console.error('[search-placeholders] handleSubmit failed:', e)
  } finally {
    submitting.value = false
  }
}

/** 行内启停：本地先写入，失败回滚并提示（Switch 是受控的，不回滚会显示成"已切换"）。 */
async function toggleActive(item: AdminSearchPlaceholder, next: boolean) {
  const prev = item.is_active
  item.is_active = next
  try {
    await updateAdminSearchPlaceholder(item.id, { is_active: next })
    toast.success(next ? '已启用' : '已停用')
  } catch {
    item.is_active = prev
  }
}

function handleDelete(item: AdminSearchPlaceholder) {
  deleteTarget.value = item
  confirmOpen.value = true
}

async function confirmDelete() {
  const target = deleteTarget.value
  if (!target) return
  await deleteAdminSearchPlaceholder(target.id, { silentToast: true })
  toast.success('提示文案已删除')
  deleteTarget.value = null
  await loadAll()
}

onMounted(loadAll)
</script>
