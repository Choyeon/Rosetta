<!--
  公告管理页：全量列表 + Dialog 创建/编辑 + 启用开关 + DangerConfirmDialog 删除。
  契约：后端 /admin/announcements 忽略分页参数返回全量（故本页刻意无分页器）；列表走 silentApiFetch 不自动 toast，错误态与提示必须由本页自行呈现；
  announcements 为 shallowRef——开关等单字段更新必须 map 整体替换行引用才会触发渲染；行内 title/content 可能是 i18n dict 或纯文本，需 displayField 兼容。
-->
<template>
  <div class="flex flex-col gap-5">
    <AdminPageHeader
      title="公告管理"
      description="全站公告的发布、启用与下线"
      :icon="Megaphone"
    >
      <template #actions>
        <Button
          size="sm"
          class="rounded-xl shadow-sm"
          @click="openCreate"
        >
          <Plus data-icon="inline-start" />
          新建公告
        </Button>
      </template>
    </AdminPageHeader>

    <AdminCard>
      <div class="p-0">
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

        <!-- silentApiFetch 不会自动 toast，错误状态必须在这一层呈现 -->
        <div
          v-else-if="loadError"
          class="flex flex-col items-start gap-3 p-6"
        >
          <Alert variant="destructive">
            <AlertTitle>加载公告列表失败</AlertTitle>
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
          v-else-if="!announcements.length"
          class="p-16 text-center"
        >
          <Alert
            variant="info"
            class="max-w-md mx-auto"
          >
            <Info class="size-4" />
            <AlertTitle>暂无公告</AlertTitle>
            <AlertDescription>点击右上角按钮创建第一条公告</AlertDescription>
          </Alert>
        </div>

        <div
          v-else
          class="overflow-x-auto"
        >
          <table class="w-full text-sm">
            <caption class="sr-only">
              公告列表：类型、标题、可关闭、启用、创建时间与操作
            </caption>
            <thead>
              <tr class="border-b bg-muted/30">
                <th
                  scope="col"
                  class="text-left font-medium p-4"
                >
                  类型
                </th>
                <th
                  scope="col"
                  class="text-left font-medium p-4"
                >
                  标题
                </th>
                <th
                  scope="col"
                  class="text-left font-medium p-4"
                >
                  可关闭
                </th>
                <th
                  scope="col"
                  class="text-left font-medium p-4"
                >
                  启用
                </th>
                <th
                  scope="col"
                  class="text-left font-medium p-4"
                >
                  创建时间
                </th>
                <th
                  scope="col"
                  class="text-right font-medium p-4"
                >
                  操作
                </th>
              </tr>
            </thead>
            <tbody>
              <tr
                v-for="(a, i) in announcements"
                :key="a.id"
                :class="i % 2 === 1 ? 'bg-muted/20' : ''"
              >
                <td class="p-4">
                  <Badge
                    :class="[typeBadgeClass(a.type), 'gap-1']"
                  >
                    <component
                      :is="typeIcon(a.type)"
                      class="size-3.5"
                    />
                    {{ typeText(a.type) }}
                  </Badge>
                </td>
                <td class="p-4 font-medium max-w-md break-words">
                  {{ displayField(a.title) }}
                </td>
                <td class="p-4">
                  <Check
                    v-if="a.is_dismissible"
                    class="size-4 text-success"
                    aria-label="允许用户关闭"
                  />
                  <span
                    v-else
                    class="text-muted-foreground"
                  >-</span>
                </td>
                <td class="p-4">
                  <Switch
                    :model-value="a.is_active"
                    :aria-label="`启用公告：${displayField(a.title)}`"
                    @update:model-value="toggleActive(a, $event)"
                  />
                </td>
                <td class="p-4 text-muted-foreground">
                  {{ formatAdminDateTime(a.created_at) }}
                </td>
                <td class="p-4 text-right">
                  <div class="inline-flex items-center gap-1">
                    <Button
                      variant="ghost"
                      size="icon-sm"
                      aria-label="编辑公告"
                      @click="openEdit(a)"
                    >
                      <Pencil data-icon="inline-start" />
                    </Button>
                    <Button
                      variant="ghost"
                      size="icon-sm"
                      class="text-destructive hover:text-destructive"
                      aria-label="删除公告"
                      @click="confirmDelete(a)"
                    >
                      <Trash2 data-icon="inline-start" />
                    </Button>
                  </div>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </AdminCard>

    <Dialog v-model:open="formDialogOpen">
      <DialogContent class="sm:max-w-lg">
        <DialogHeader>
          <DialogTitle>{{ editingId ? '编辑公告' : '新建公告' }}</DialogTitle>
          <DialogDescription>
            公告将展示在站点顶部，支持 Markdown 内容
          </DialogDescription>
        </DialogHeader>

        <div class="flex flex-col gap-4 py-2">
          <div class="flex flex-col gap-2">
            <span class="text-sm font-medium leading-none">公告类型</span>
            <div class="grid grid-cols-2 sm:grid-cols-4 gap-2">
              <button
                v-for="t in announcementTypes"
                :key="t.value"
                type="button"
                :aria-pressed="form.type === t.value"
                :class="[
                  'flex flex-col items-center justify-center gap-1 p-3 rounded-xl border transition-all',
                  form.type === t.value
                    ? 'border-primary bg-primary/5 ring-2 ring-primary/20'
                    : 'hover:bg-muted/40'
                ]"
                @click="form.type = t.value"
              >
                <component
                  :is="t.icon"
                  class="size-6"
                />
                <span class="text-xs">{{ t.label }}</span>
              </button>
            </div>
          </div>

          <div class="flex flex-col gap-2">
            <Label for="ann-title">标题 <span class="text-destructive">*</span></Label>
            <Input
              id="ann-title"
              v-model="form.title"
              placeholder="公告标题"
              maxlength="200"
            />
          </div>

          <div class="flex flex-col gap-2">
            <Label for="ann-content">内容（Markdown）<span class="text-destructive">*</span></Label>
            <Textarea
              id="ann-content"
              v-model="form.content_md"
              rows="6"
              placeholder="支持 Markdown 格式..."
              class="resize-none font-mono text-sm"
            />
          </div>

          <div class="grid grid-cols-2 gap-4">
            <div class="flex items-center justify-between rounded-xl border p-3">
              <div>
                <div class="text-sm font-medium">
                  可关闭
                </div>
                <div class="text-xs text-muted-foreground">
                  用户可手动关闭
                </div>
              </div>
              <Switch
                v-model="form.is_dismissible"
                aria-label="可关闭"
              />
            </div>
            <div class="flex items-center justify-between rounded-xl border p-3">
              <div>
                <div class="text-sm font-medium">
                  启用
                </div>
                <div class="text-xs text-muted-foreground">
                  是否立即生效
                </div>
              </div>
              <Switch
                v-model="form.active"
                aria-label="启用"
              />
            </div>
          </div>

          <p
            v-if="formError"
            class="text-sm text-destructive"
          >
            {{ formError }}
          </p>
        </div>

        <DialogFooter>
          <Button
            variant="ghost"
            :disabled="submitting"
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
            {{ editingId ? '保存修改' : '创建公告' }}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>

    <!-- 删除确认：统一走 DangerConfirmDialog -->
    <DangerConfirmDialog
      v-model:open="deleteDialogOpen"
      title="确认删除公告"
      confirm-text="确认删除"
      confirm-phrase="删除公告"
      phrase-hint="请输入：删除公告"
      :on-confirm="doDelete"
    >
      <template #description>
        将删除公告 <span class="font-medium text-destructive">{{ deleteTargetTitle || '未命名公告' }}</span>，删除后无法恢复。
      </template>
    </DangerConfirmDialog>
  </div>
</template>

<script setup lang="ts">
/* eslint-disable */

import AdminCard from '~~/components/admin/AdminCard.vue'
import DangerConfirmDialog from '~~/components/admin/tools/DangerConfirmDialog.vue'
import { Button } from '~~/components/ui/button'
import { Input } from '~~/components/ui/input'
import { Textarea } from '~~/components/ui/textarea'
import { Badge } from '~~/components/ui/badge'
import { Switch } from '~~/components/ui/switch'
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from '~~/components/ui/dialog'
import { Skeleton } from '~~/components/ui/skeleton'
import { Alert, AlertDescription, AlertTitle } from '~~/components/ui/alert'
import { Label } from '~~/components/ui/label'
import {
  Plus, Check, Pencil, Trash2, Info, Loader2, RotateCcw,
  AlertTriangle, XCircle, CheckCircle, Megaphone
} from '@lucide/vue'
import {
  fetchAdminAnnouncements,
  createAdminAnnouncement,
  updateAdminAnnouncement,
  deleteAdminAnnouncement,
  formatAdminDateTime,
  type AdminAnnouncement
} from '~~/composables/useAdminManage'

definePageMeta({ ssr: false, layout: 'admin' })

const toast = useToast()

type AnnType = 'info' | 'warning' | 'error' | 'success'

const announcementTypes = [
  { value: 'info' as AnnType, label: '信息', icon: Info },
  { value: 'warning' as AnnType, label: '警告', icon: AlertTriangle },
  { value: 'error' as AnnType, label: '错误', icon: XCircle },
  { value: 'success' as AnnType, label: '成功', icon: CheckCircle }
]

const loading = ref(false)
const submitting = ref(false)
const loadError = ref(false)
const loadErrorMsg = ref('')
const announcements = shallowRef<AdminAnnouncement[]>([])

const formDialogOpen = ref(false)
const editingId = ref<number | null>(null)
const formError = ref('')
const form = reactive({
  type: 'info' as AnnType,
  title: '',
  content_md: '',
  is_dismissible: true,
  active: true
})

const deleteDialogOpen = ref(false)
const deleteTarget = ref<AdminAnnouncement | null>(null)
const deleteTargetTitle = computed(() =>
  deleteTarget.value ? displayField(deleteTarget.value.title) : ''
)

function displayField(v: unknown): string {
  if (v == null) return ''
  if (typeof v === 'string') return v
  if (typeof v === 'object') {
    const obj = v as Record<string, unknown>
    return (obj.zh as string) || (obj.en as string) || Object.values(obj)[0] as string || ''
  }
  return String(v)
}

function typeBadgeClass(t: string): string {
  switch (t) {
    case 'info': return 'bg-info-muted text-info-muted-foreground hover:bg-info-muted'
    case 'warning': return 'bg-warning-muted text-warning-muted-foreground hover:bg-warning-muted'
    case 'error': return 'bg-error-muted text-error-muted-foreground hover:bg-error-muted'
    case 'success': return 'bg-success-muted text-success-muted-foreground hover:bg-success-muted'
    default: return 'bg-muted text-muted-foreground'
  }
}

function typeIcon(t: string) {
  switch (t) {
    case 'info': return Info
    case 'warning': return AlertTriangle
    case 'error': return XCircle
    case 'success': return CheckCircle
    default: return Megaphone
  }
}

function typeText(t: string): string {
  switch (t) {
    case 'info': return '信息'
    case 'warning': return '警告'
    case 'error': return '错误'
    case 'success': return '成功'
    default: return t
  }
}

async function fetchData() {
  loading.value = true
  loadError.value = false
  loadErrorMsg.value = ''
  try {
    // 后端 /admin/announcements 返回全量列表（忽略分页参数），因此不再展示分页器
    const res = await fetchAdminAnnouncements()
    announcements.value = res.items ?? []
  } catch (err) {
    // fetchAdminAnnouncements 走 silentApiFetch：不会自动 toast，需要页面自行提示
    console.error('fetch announcements error', err)
    announcements.value = []
    loadError.value = true
    loadErrorMsg.value = err instanceof Error ? err.message : ''
    toast.error('加载公告列表失败')
  } finally {
    loading.value = false
  }
}

function openCreate() {
  editingId.value = null
  formError.value = ''
  Object.assign(form, {
    type: 'info',
    title: '',
    content_md: '',
    is_dismissible: true,
    active: true
  })
  formDialogOpen.value = true
}

function openEdit(a: AdminAnnouncement) {
  editingId.value = a.id
  formError.value = ''
  Object.assign(form, {
    type: a.type,
    title: displayField(a.title),
    content_md: displayField(a.content),
    is_dismissible: a.is_dismissible,
    active: a.is_active
  })
  formDialogOpen.value = true
}

async function toggleActive(a: AdminAnnouncement, ev: unknown) {
  const checked = ev === true
  try {
    await updateAdminAnnouncement(a.id, { is_active: checked })
    toast.success('状态已更新')
    // announcements 是 shallowRef，直接改元素属性不会触发渲染：整体替换该行的引用
    announcements.value = announcements.value.map(x => (x.id === a.id ? { ...x, is_active: checked } : x))
  } catch {
    // 失败提示由 apiFetch 统一弹出，避免双重 toast；未做本地变更，开关自动保持原状态
  }
}

async function submitForm() {
  formError.value = ''
  if (!form.title.trim()) {
    formError.value = '请填写标题'
    return
  }
  // 后端 AnnouncementBase.content 为必填（min_length=1），空内容会直接 422
  if (!form.content_md.trim()) {
    formError.value = '请填写公告内容'
    return
  }
  submitting.value = true
  const payload: Record<string, unknown> = {
    type: form.type,
    title: form.title.trim(),
    content: form.content_md,
    is_dismissible: form.is_dismissible,
    is_active: form.active
  }
  try {
    if (editingId.value) {
      await updateAdminAnnouncement(editingId.value, payload)
      toast.success('修改成功')
    } else {
      await createAdminAnnouncement(payload)
      toast.success('创建成功')
    }
    formDialogOpen.value = false
    fetchData()
  } catch (err) {
    // apiFetch 已弹 toast；弹窗保持打开并保留输入，内联提示失败原因
    console.error('submit announcement error', err)
    formError.value = err instanceof Error ? err.message : (editingId.value ? '修改失败' : '创建失败')
  } finally {
    submitting.value = false
  }
}

function confirmDelete(a: AdminAnnouncement) {
  deleteTarget.value = a
  deleteDialogOpen.value = true
}

async function doDelete() {
  const target = deleteTarget.value
  if (!target?.id) throw new Error('未选择要删除的公告')
  // 抛错时 DangerConfirmDialog 保持打开并内联显示错误；toast 由 apiFetch 统一处理
  await deleteAdminAnnouncement(target.id)
  toast.success('删除成功')
  deleteTarget.value = null
  await fetchData()
}

onMounted(fetchData)
</script>
