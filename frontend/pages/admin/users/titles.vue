<!-- 头衔管理页：前台评论区展示的用户头衔 CRUD，名称/描述为完整 i18n dict（旧纯文本行经 normalizeI18nDict 兼容）。
     契约：color 为 NOT NULL 列——留空时必须整个 key 不发（POST 落后端默认色、PUT 保持原色），传 null 会被 422 拒；
     icon 只接受预设 ID/emoji，HTML/SVG 标记后端以 422 拒绝（头衔渲染于所有访客页，属存储型 XSS 防线）。 -->
<template>
  <div class="flex flex-col gap-5">
    <AdminPageHeader
      title="头衔管理"
      description="为用户配置展示在前台评论区的等级头衔"
      :icon="Award"
    >
      <template #actions>
        <Button
          size="sm"
          class="rounded-xl shadow-sm"
          @click="openCreate"
        >
          <Plus data-icon="inline-start" />
          新建头衔
        </Button>
      </template>
    </AdminPageHeader>

    <AdminCard>
      <div
        v-if="loading"
        class="flex flex-col gap-3 p-4"
      >
        <div
          v-for="i in 5"
          :key="i"
          class="h-12 rounded-lg"
        >
          <Skeleton class="h-full w-full rounded-lg" />
        </div>
      </div>

      <div
        v-else-if="loadError"
        class="flex flex-col items-start gap-3 p-6"
      >
        <Alert variant="destructive">
          <AlertTitle>加载头衔列表失败</AlertTitle>
          <AlertDescription>{{ loadErrorMsg || '请求未成功，请重试。' }}</AlertDescription>
        </Alert>
        <Button
          variant="outline"
          size="sm"
          @click="fetchData"
        >
          <RotateCcw data-icon="inline-start" />
          重试
        </Button>
      </div>

      <div
        v-else-if="!titles.length"
        class="p-16 text-center"
      >
        <Alert
          variant="info"
          class="max-w-md mx-auto"
        >
          <Info class="size-4" />
          <AlertTitle>暂无头衔</AlertTitle>
          <AlertDescription>点击右上角按钮创建第一个头衔</AlertDescription>
        </Alert>
      </div>

      <div
        v-else
        class="overflow-x-auto"
      >
        <table class="w-full text-sm">
          <caption class="sr-only">
            头衔列表：ID、名称、图标预览、描述与操作
          </caption>
          <thead>
            <tr class="border-b bg-muted/30">
              <th
                scope="col"
                class="text-left font-medium p-4 w-16"
              >
                ID
              </th>
              <th
                scope="col"
                class="text-left font-medium p-4"
              >
                名称
              </th>
              <th
                scope="col"
                class="text-left font-medium p-4 w-28"
              >
                图标预览
              </th>
              <th
                scope="col"
                class="text-left font-medium p-4"
              >
                描述
              </th>
              <th
                scope="col"
                class="text-right font-medium p-4 w-28"
              >
                操作
              </th>
            </tr>
          </thead>
          <tbody>
            <tr
              v-for="(t, i) in titles"
              :key="t.id"
              :class="i % 2 === 1 ? 'bg-muted/20' : ''"
            >
              <td class="p-4 text-muted-foreground tabular-nums">
                #{{ t.id }}
              </td>
              <td class="p-4">
                <div class="inline-flex items-center gap-2">
                  <span
                    class="size-2.5 rounded-full shrink-0"
                    :style="{ backgroundColor: t.color || '#94a3b8' }"
                  />
                  <span class="font-medium">{{ getLocalizedStr(t.name) }}</span>
                </div>
              </td>
              <td class="p-4">
                <TitleBadge
                  :title="t"
                  size="md"
                />
              </td>
              <td class="p-4 text-muted-foreground max-w-md break-words">
                {{ getLocalizedStr(t.description) || '—' }}
              </td>
              <td class="p-4 text-right">
                <div class="inline-flex items-center gap-1">
                  <Button
                    variant="ghost"
                    size="icon-sm"
                    aria-label="编辑头衔"
                    @click="openEdit(t)"
                  >
                    <Pencil data-icon="inline-start" />
                  </Button>
                  <Button
                    variant="ghost"
                    size="icon-sm"
                    class="text-destructive hover:text-destructive"
                    aria-label="删除头衔"
                    @click="confirmDelete(t)"
                  >
                    <Trash2 data-icon="inline-start" />
                  </Button>
                </div>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </AdminCard>

    <!-- 新建/编辑 对话框 -->
    <Dialog v-model:open="formDialogOpen">
      <DialogContent class="max-w-lg">
        <DialogHeader>
          <DialogTitle>{{ editingId ? '编辑头衔' : '新建头衔' }}</DialogTitle>
          <DialogDescription>
            头衔可授予用户，显示在用户名旁边
          </DialogDescription>
        </DialogHeader>
        <div class="flex flex-col gap-5 py-2">
          <!-- 名称 -->
          <I18nTabsEditor
            v-model="form.name"
            kind="text"
            label="名称"
            required
          />

          <!-- 颜色 + 图标预览 -->
          <div class="grid grid-cols-2 gap-4">
            <div class="flex flex-col gap-2">
              <Label for="title-color">颜色</Label>
              <div class="flex items-center gap-2">
                <input
                  v-model="form.color"
                  type="color"
                  aria-label="颜色选择器"
                  class="size-10 rounded-lg border cursor-pointer bg-transparent"
                >
                <Input
                  id="title-color"
                  v-model="form.color"
                  placeholder="#3b82f6"
                  class="font-mono text-sm"
                />
              </div>
              <p class="text-xs text-muted-foreground">
                十六进制色值（#rgb / #rrggbb 均可）；留空则用默认色，编辑时保持原色。
              </p>
            </div>
            <div class="flex flex-col gap-2">
              <span class="text-sm font-medium leading-none">预览</span>
              <div class="flex items-center h-10 rounded-lg border bg-muted/30 px-3">
                <TitleBadge
                  :title="previewTitle"
                  size="md"
                />
              </div>
            </div>
          </div>

          <!-- 图标选择：预设 SVG 网格 -->
          <div class="flex flex-col gap-2">
            <span class="text-sm font-medium leading-none">选择图标</span>
            <div class="rounded-lg border p-3 bg-muted/20">
              <div class="grid grid-cols-6 sm:grid-cols-8 gap-2">
                <button
                  v-for="p in presetIcons"
                  :key="p.id"
                  type="button"
                  :class="[
                    'relative size-10 rounded-lg border flex items-center justify-center transition-all',
                    form.icon === p.id
                      ? 'border-primary bg-primary/10 ring-2 ring-primary/30'
                      : 'border-border bg-card hover:bg-accent'
                  ]"
                  :title="p.name"
                  :aria-label="`选择图标 ${p.name}`"
                  @click="form.icon = p.id"
                >
                  <span
                    class="size-5"
                    :style="{ color: form.color }"
                  >
                    <TitleIconSvg
                      :icon="p.id"
                      :stroke-width="2"
                    />
                  </span>
                  <span
                    v-if="form.icon === p.id"
                    class="absolute -top-1 -right-1 size-4 rounded-full bg-primary text-primary-foreground text-[8px] flex items-center justify-center"
                  >✓</span>
                </button>
              </div>

              <!-- 自定义图标输入 -->
              <div class="flex flex-col gap-2 mt-3">
                <Label
                  for="title-icon-custom"
                  class="text-xs text-muted-foreground"
                >自定义（emoji / 预设 ID）</Label>
                <div class="flex gap-2">
                  <Input
                    id="title-icon-custom"
                    v-model="form.icon"
                    placeholder="选择预设或输入自定义，如 star / ⭐"
                    class="font-mono text-sm flex-1"
                  />
                </div>
                <p
                  class="text-[11px] text-muted-foreground"
                >
                  支持预设 ID（star、crown、trophy 等）与 emoji（⭐、🏆）。
                  不接受 HTML/SVG 标记——称号图标会渲染在所有访客页面上，贴入标记属存储型 XSS（后端以 422 拒绝）
                </p>
              </div>
            </div>
          </div>

          <!-- 描述 -->
          <I18nTabsEditor
            v-model="form.description"
            kind="textarea"
            label="描述"
            :rows="3"
          />
        </div>

        <DialogFooter>
          <Button
            variant="ghost"
            @click="formDialogOpen = false"
          >
            取消
          </Button>
          <Button
            :disabled="submitting"
            @click="submitForm"
          >
            <Loader2
              v-if="submitting"
              data-icon="inline-start"
              class="animate-spin"
            />
            {{ editingId ? '保存修改' : '创建头衔' }}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>

    <!-- 删除确认：统一走 DangerConfirmDialog -->
    <DangerConfirmDialog
      v-model:open="deleteDialogOpen"
      title="确认删除头衔"
      confirm-text="确认删除"
      confirm-phrase="删除头衔"
      phrase-hint="请输入：删除头衔"
      :on-confirm="doDelete"
    >
      <template #description>
        删除头衔 <span class="font-medium text-destructive">{{ deleteTargetName }}</span> 后无法恢复，已授予该头衔的用户将失去头衔显示。
      </template>
    </DangerConfirmDialog>
  </div>
</template>

<script setup lang="ts">
import AdminCard from '~~/components/admin/AdminCard.vue'
import DangerConfirmDialog from '~~/components/admin/tools/DangerConfirmDialog.vue'
import I18nTabsEditor from '~~/components/admin/I18nTabsEditor.vue'
import TitleBadge from '~~/components/TitleBadge.vue'
import { Button } from '~~/components/ui/button'
import { Input } from '~~/components/ui/input'
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from '~~/components/ui/dialog'
import { Skeleton } from '~~/components/ui/skeleton'
import { Alert, AlertDescription, AlertTitle } from '~~/components/ui/alert'
import { Label } from '~~/components/ui/label'
import { Plus, Pencil, Trash2, Info, Loader2, Award, RotateCcw } from '@lucide/vue'
import TitleIconSvg from '~~/components/TitleIconSvg.vue'
import {
  fetchAdminUserTitles,
  createAdminUserTitle,
  updateAdminUserTitle,
  deleteAdminUserTitle,
  type AdminUserTitle
} from '~~/composables/useAdminManage'
import { TITLE_PRESET_ICONS } from '~~/composables/titlePresets'
import { getLocalizedStr, normalizeI18nDict, type I18nDict } from '~~/composables/useAdminI18n'

definePageMeta({ ssr: false, layout: 'admin' })

const toast = useToast()
const presetIcons = TITLE_PRESET_ICONS

const loading = ref(false)
const submitting = ref(false)
const loadError = ref(false)
const loadErrorMsg = ref('')
const titles = shallowRef<AdminUserTitle[]>([])

const formDialogOpen = ref(false)
const editingId = ref<number | null>(null)
const form = reactive<{
  name: I18nDict
  color: string
  icon: string
  description: I18nDict
}>({
  name: { zh: '', en: '', ja: '', zh_Hant: '' },
  color: '#3b82f6',
  icon: '',
  description: { zh: '', en: '', ja: '', zh_Hant: '' }
})

const deleteDialogOpen = ref(false)
const deleteTarget = ref<AdminUserTitle | null>(null)
const deleteTargetName = computed(() =>
  deleteTarget.value ? getLocalizedStr(deleteTarget.value.name) || `#${deleteTarget.value.id}` : ''
)

const previewTitle = computed<AdminUserTitle>(() => ({
  id: 0,
  name: getLocalizedStr(form.name) || '头衔预览',
  color: form.color || '#3b82f6',
  icon: form.icon || 'star',
  description: getLocalizedStr(form.description)
}))

async function fetchData() {
  loading.value = true
  loadError.value = false
  loadErrorMsg.value = ''
  try {
    titles.value = await fetchAdminUserTitles()
  } catch (err) {
    // apiFetch 已自动 toast，这里只保留页面级错误态 + 重试入口
    console.error('fetch titles error', err)
    loadError.value = true
    loadErrorMsg.value = err instanceof Error ? err.message : ''
    titles.value = []
  } finally {
    loading.value = false
  }
}

function openCreate() {
  editingId.value = null
  Object.assign(form, {
    name: { zh: '', en: '', ja: '', zh_Hant: '' },
    color: '#3b82f6',
    icon: '',
    description: { zh: '', en: '', ja: '', zh_Hant: '' }
  })
  formDialogOpen.value = true
}

function openEdit(t: AdminUserTitle) {
  editingId.value = t.id ?? null
  form.name = normalizeI18nDict(t.name)
  form.color = t.color || '#3b82f6'
  form.icon = t.icon || ''
  form.description = normalizeI18nDict(t.description)
  formDialogOpen.value = true
}

async function submitForm() {
  if (!getLocalizedStr(form.name).trim()) {
    toast.warning('请填写名称')
    return
  }
  // 与后端 UserTitleCreate/Update 的 color 正则同规；先在前端拦下，
  // 免得取色器手输的 "reddish" 变成一条 422 校验错误 toast。
  const color = form.color.trim()
  if (color && !/^#(?:[0-9a-f]{3,4}|[0-9a-f]{6}|[0-9a-f]{8})$/i.test(color)) {
    toast.warning('颜色需为十六进制色值，例如 #3b82f6')
    return
  }
  submitting.value = true
  const payload = {
    name: form.name,
    // color 是 NOT NULL 列：留空时整个 key 都不发（POST 落后端默认色，PUT 保持原色）。
    // 传 null 会被后端以 422「称号颜色不能为空」拒绝——旧写法在这里会直接卡死保存。
    ...(color ? { color } : {}),
    icon: form.icon.trim() || null,
    description: form.description
  }
  try {
    if (editingId.value) {
      await updateAdminUserTitle(editingId.value, payload)
      toast.success('修改成功')
    } else {
      await createAdminUserTitle(payload)
      toast.success('创建成功')
    }
    formDialogOpen.value = false
    fetchData()
  } catch (err) {
    // 失败时保持弹窗打开；错误提示由 apiFetch 统一弹出，避免双重 toast
    console.error('submit title form error', err)
  } finally {
    submitting.value = false
  }
}

function confirmDelete(t: AdminUserTitle) {
  deleteTarget.value = t
  deleteDialogOpen.value = true
}

async function doDelete() {
  const target = deleteTarget.value
  if (!target?.id) throw new Error('未选择要删除的头衔')
  // 抛错时 DangerConfirmDialog 保持打开并内联显示错误；toast 由 apiFetch 统一处理
  await deleteAdminUserTitle(target.id)
  toast.success('删除成功')
  deleteTarget.value = null
  await fetchData()
}

onMounted(fetchData)
</script>
