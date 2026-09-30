<!--
  公告管理页：全量列表 + Dialog 创建/编辑 + 启用开关 + DangerConfirmDialog 删除。

  契约与取舍：
  · 后端 /admin/announcements 有意忽略分页参数返回全量（故本页刻意无分页器）；列表走
    silentApiFetch 不自动 toast，错误态必须由本页自行呈现。
  · announcements 是 shallowRef——开关等单字段更新必须 map 整体替换行引用才会触发渲染。
  · title/content 恒为明文字符串（不是 i18n dict），删掉旧的 displayField 兼容分支。
  · 排期（start_time / end_time）与排序（sort_order）后端一直支持，但此前 UI 上完全不可达：
    不填表单就只能在数据库里改。这里补齐，并给出"这条为什么没在展示"的状态列。
  · 状态判定走 lib/announcement.ts::announcementStatus——**只用于后台展示**，
    前台横幅的显隐由服务端按 is_active + 时间窗过滤，前端不重复判定（口径会漂）。
  · 改动公告后后端会清 Nitro 的前台页面 SWR 缓存，因此不需要在前端做任何缓存处理。
-->
<template>
  <div class="flex flex-col gap-5">
    <AdminPageHeader
      title="公告管理"
      description="全站公告的发布、排期与下线"
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
            class="h-14"
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
              公告列表：状态、类型、标题与内容、展示时段、排序、可关闭、启用与操作
            </caption>
            <thead>
              <tr class="border-b bg-muted/30">
                <th
                  scope="col"
                  class="text-left font-medium p-4 whitespace-nowrap"
                >
                  状态
                </th>
                <th
                  scope="col"
                  class="text-left font-medium p-4 whitespace-nowrap"
                >
                  类型
                </th>
                <th
                  scope="col"
                  class="text-left font-medium p-4"
                >
                  标题与内容
                </th>
                <th
                  scope="col"
                  class="text-left font-medium p-4 whitespace-nowrap"
                >
                  展示时段
                </th>
                <th
                  scope="col"
                  class="text-left font-medium p-4 whitespace-nowrap"
                >
                  排序
                </th>
                <th
                  scope="col"
                  class="text-left font-medium p-4 whitespace-nowrap"
                >
                  可关闭
                </th>
                <th
                  scope="col"
                  class="text-left font-medium p-4 whitespace-nowrap"
                >
                  启用
                </th>
                <th
                  scope="col"
                  class="text-right font-medium p-4 whitespace-nowrap"
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
                    :class="[statusBadgeClass(statusOf(a)), 'gap-1']"
                    :title="statusHint(statusOf(a))"
                  >
                    <component
                      :is="statusIcon(statusOf(a))"
                      class="size-3.5"
                    />
                    {{ statusText(statusOf(a)) }}
                  </Badge>
                </td>
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
                <td class="p-4 max-w-md">
                  <div class="font-medium break-words">
                    {{ a.title }}
                  </div>
                  <div
                    v-if="a.content"
                    class="mt-0.5 text-xs text-muted-foreground break-words line-clamp-2"
                  >
                    {{ a.content }}
                  </div>
                </td>
                <td class="p-4 text-muted-foreground whitespace-nowrap">
                  {{ scheduleText(a) }}
                </td>
                <td class="p-4 text-muted-foreground tabular-nums">
                  {{ a.sort_order }}
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
                    :aria-label="`启用公告：${a.title}`"
                    @update:model-value="toggleActive(a, $event)"
                  />
                </td>
                <td class="p-4 text-right">
                  <div class="inline-flex items-center gap-1">
                    <Button
                      variant="ghost"
                      size="icon-sm"
                      :aria-label="`编辑公告：${a.title}`"
                      @click="openEdit(a)"
                    >
                      <Pencil data-icon="inline-start" />
                    </Button>
                    <Button
                      variant="ghost"
                      size="icon-sm"
                      class="text-destructive hover:text-destructive"
                      :aria-label="`删除公告：${a.title}`"
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
      <DialogContent class="sm:max-w-2xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>{{ editingId ? '编辑公告' : '新建公告' }}</DialogTitle>
          <DialogDescription>
            公告展示在站点顶部；支持 Markdown 正文（横幅按纯文本降级渲染）与定时上下线
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
            <div class="flex items-center justify-between">
              <Label for="ann-content">正文（Markdown）<span class="text-destructive">*</span></Label>
              <span
                class="text-xs tabular-nums"
                :class="contentOverflow ? 'text-destructive' : 'text-muted-foreground'"
              >{{ form.content.length }} / {{ ANNOUNCEMENT_CONTENT_MAX }}</span>
            </div>
            <Textarea
              id="ann-content"
              v-model="form.content"
              rows="5"
              :maxlength="ANNOUNCEMENT_CONTENT_MAX"
              placeholder="支持 Markdown 格式..."
              class="resize-none font-mono text-sm"
            />
          </div>

          <div class="grid grid-cols-1 sm:grid-cols-3 gap-4">
            <div class="flex flex-col gap-2">
              <Label
                for="ann-sort"
                class="text-xs text-muted-foreground"
              >排序权重（越小越靠前）</Label>
              <Input
                id="ann-sort"
                v-model.number="form.sort_order"
                type="number"
                min="0"
                step="1"
              />
            </div>
            <div class="flex flex-col gap-2">
              <Label
                for="ann-start"
                class="text-xs text-muted-foreground"
              >开始时间（留空＝立即）</Label>
              <div class="flex gap-1">
                <Input
                  id="ann-start"
                  v-model="form.start_time"
                  type="datetime-local"
                />
                <Button
                  v-if="form.start_time"
                  variant="ghost"
                  size="icon-sm"
                  aria-label="清除开始时间"
                  @click="form.start_time = ''"
                >
                  <X data-icon="inline-start" />
                </Button>
              </div>
            </div>
            <div class="flex flex-col gap-2">
              <Label
                for="ann-end"
                class="text-xs text-muted-foreground"
              >结束时间（留空＝长期）</Label>
              <div class="flex gap-1">
                <Input
                  id="ann-end"
                  v-model="form.end_time"
                  type="datetime-local"
                />
                <Button
                  v-if="form.end_time"
                  variant="ghost"
                  size="icon-sm"
                  aria-label="清除结束时间"
                  @click="form.end_time = ''"
                >
                  <X data-icon="inline-start" />
                </Button>
              </div>
            </div>
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
                  关闭后前台不再展示
                </div>
              </div>
              <Switch
                v-model="form.is_active"
                aria-label="启用"
              />
            </div>
          </div>

          <div class="flex flex-col gap-2">
            <span class="text-xs text-muted-foreground">前台效果预览</span>
            <div
              v-if="previewTitle || previewContent"
              class="px-4 py-2.5 text-sm rounded-md"
              :class="announcementVariantClass(form.type)"
            >
              <div class="flex items-start gap-3">
                <Bell class="size-4 shrink-0 mt-0.5 opacity-80" />
                <div class="min-w-0 flex-1 flex flex-wrap items-baseline gap-x-3 gap-y-1">
                  <strong
                    v-if="previewTitle"
                    class="font-medium"
                  >{{ previewTitle }}</strong>
                  <span
                    v-if="previewContent && previewContent !== previewTitle"
                    class="opacity-90"
                  >{{ previewContent }}</span>
                </div>
              </div>
            </div>
            <p
              v-else
              class="text-xs text-muted-foreground"
            >
              填写标题或正文后显示预览
            </p>
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
import { computed, onMounted, reactive, ref, shallowRef } from 'vue'
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
  Plus, Check, Pencil, Trash2, Info, Loader2, RotateCcw, X, Bell,
  AlertTriangle, XCircle, CheckCircle, Megaphone,
  Clock, CircleSlash, CalendarClock
} from '@lucide/vue'
import {
  fetchAdminAnnouncements,
  createAdminAnnouncement,
  updateAdminAnnouncement,
  deleteAdminAnnouncement,
  formatAdminDateTime,
  type AdminAnnouncement
} from '~~/composables/useAdminManage'
import { announcementVariantClass, stripInlineMarkdown } from '~~/composables/useAnnouncementBar'
import {
  ANNOUNCEMENT_CONTENT_MAX,
  announcementScheduleError,
  announcementStatus,
  fromDateTimeLocal,
  toDateTimeLocal,
  type AnnouncementStatus
} from '~~/lib/announcement'

definePageMeta({ ssr: false, layout: 'admin' })

const toast = useToast()

type AnnType = AdminAnnouncement['type']

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
  content: '',
  sort_order: 0,
  start_time: '',
  end_time: '',
  is_dismissible: true,
  is_active: true
})

const deleteDialogOpen = ref(false)
const deleteTarget = ref<AdminAnnouncement | null>(null)
const deleteTargetTitle = computed(() => deleteTarget.value?.title ?? '')

const contentOverflow = computed(() => form.content.length > ANNOUNCEMENT_CONTENT_MAX)
const previewTitle = computed(() => stripInlineMarkdown(form.title))
const previewContent = computed(() => stripInlineMarkdown(form.content))

function statusOf(a: AdminAnnouncement): AnnouncementStatus {
  return announcementStatus(a)
}

function statusText(s: AnnouncementStatus): string {
  switch (s) {
    case 'active': return '展示中'
    case 'scheduled': return '待开始'
    case 'expired': return '已结束'
    case 'disabled': return '已停用'
    default: return s
  }
}

/** hover 提示写清"为什么没在展示"，省得管理员去翻后端过滤条件。 */
function statusHint(s: AnnouncementStatus): string {
  switch (s) {
    case 'active': return '已启用且当前时间在生效窗口内，前台正在展示'
    case 'scheduled': return '开始时间未到，到点后自动展示'
    case 'expired': return '结束时间已过，前台不再展示'
    case 'disabled': return '未启用，前台不展示'
    default: return ''
  }
}

function statusBadgeClass(s: AnnouncementStatus): string {
  switch (s) {
    case 'active': return 'bg-success-muted text-success-muted-foreground hover:bg-success-muted'
    case 'scheduled': return 'bg-info-muted text-info-muted-foreground hover:bg-info-muted'
    case 'expired': return 'bg-warning-muted text-warning-muted-foreground hover:bg-warning-muted'
    case 'disabled': return 'bg-muted text-muted-foreground'
    default: return 'bg-muted text-muted-foreground'
  }
}

function statusIcon(s: AnnouncementStatus) {
  switch (s) {
    case 'active': return CheckCircle
    case 'scheduled': return CalendarClock
    case 'expired': return Clock
    case 'disabled': return CircleSlash
    default: return Megaphone
  }
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

function scheduleText(a: AdminAnnouncement): string {
  const start = a.start_time ? formatAdminDateTime(a.start_time, '') : ''
  const end = a.end_time ? formatAdminDateTime(a.end_time, '') : ''
  if (start && end) return `${start} ~ ${end}`
  if (start) return `${start} 起`
  if (end) return `至 ${end}`
  return '长期有效'
}

async function fetchData() {
  loading.value = true
  loadError.value = false
  loadErrorMsg.value = ''
  try {
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

function resetForm(a?: AdminAnnouncement) {
  Object.assign(form, {
    type: a?.type ?? 'info',
    title: a?.title ?? '',
    content: a?.content ?? '',
    sort_order: a?.sort_order ?? 0,
    // 后端给的是带偏移的 ISO，datetime-local 输入框要本地墙钟字符串
    start_time: toDateTimeLocal(a?.start_time),
    end_time: toDateTimeLocal(a?.end_time),
    is_dismissible: a?.is_dismissible ?? true,
    is_active: a?.is_active ?? true
  })
}

function openCreate() {
  editingId.value = null
  formError.value = ''
  resetForm()
  formDialogOpen.value = true
}

function openEdit(a: AdminAnnouncement) {
  editingId.value = a.id
  formError.value = ''
  resetForm(a)
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
  // 后端 AnnouncementBase.content 为必填且上限 ANNOUNCEMENT_CONTENT_MAX，空内容 / 超长都会 422
  if (!form.content.trim()) {
    formError.value = '请填写公告内容'
    return
  }
  const scheduleError = announcementScheduleError(form.start_time, form.end_time)
  if (scheduleError) {
    formError.value = scheduleError
    return
  }

  submitting.value = true
  const payload: Record<string, unknown> = {
    type: form.type,
    title: form.title.trim(),
    content: form.content,
    sort_order: Number.isFinite(form.sort_order) ? Math.max(0, Math.trunc(form.sort_order)) : 0,
    // 空串必须转成 null：后端只接受 datetime 或 null，传 '' 会被判成非法 datetime
    start_time: fromDateTimeLocal(form.start_time),
    end_time: fromDateTimeLocal(form.end_time),
    is_dismissible: form.is_dismissible,
    is_active: form.is_active
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
    await fetchData()
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
