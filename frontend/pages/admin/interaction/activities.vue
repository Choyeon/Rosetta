<!--
  动态/说说管理页：时间线样式列表 + Dialog 创建/编辑 + DangerConfirmDialog 删除。
  契约：后端 Activity 创建/更新为 extra=forbid，只能发 content（必填 i18n dict）/type/is_published（title/link 字段已不存在）；type 枚举须与 backend/schemas/activity.py 严格同步；
  行内 content 可能是 dict 或旧纯文本，展示/回填/提交必须经 getLocalizedStr/normalizeI18nDict/toI18nPayload 兼容处理。
-->
<template>
  <div class="flex flex-col gap-5">
    <AdminPageHeader
      title="动态/说说管理"
      description="发布与管理站点时间线上的短动态"
      :icon="Activity"
    >
      <template #actions>
        <Button
          size="sm"
          class="rounded-xl shadow-sm"
          @click="openCreate"
        >
          <Plus data-icon="inline-start" />
          发说说
        </Button>
      </template>
    </AdminPageHeader>

    <div
      v-if="loading"
      class="flex flex-col gap-4"
    >
      <div
        v-for="i in 4"
        :key="i"
        class="flex gap-4"
      >
        <div class="relative">
          <Skeleton class="size-10 rounded-full" />
          <div
            v-if="i < 4"
            class="absolute left-1/2 top-10 w-px h-16 bg-border -translate-x-1/2"
          />
        </div>
        <div class="flex flex-col gap-3 flex-1">
          <Skeleton class="h-4 w-40" />
          <Skeleton class="h-20 w-full rounded-xl" />
        </div>
      </div>
    </div>

    <div
      v-else-if="loadError"
      class="flex flex-col items-start gap-3 p-6 card-surface"
    >
      <Alert variant="destructive">
        <AlertTitle>加载动态列表失败</AlertTitle>
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
      v-else-if="!activities.length"
      class="py-16 text-center"
    >
      <Alert
        variant="info"
        class="max-w-md mx-auto"
      >
        <Info class="size-4" />
        <AlertTitle>暂无动态</AlertTitle>
        <AlertDescription>还没有任何动态数据，点击右上角发一条吧</AlertDescription>
      </Alert>
    </div>

    <div
      v-else
      class="relative pl-6"
    >
      <div class="absolute left-[19px] top-2 bottom-2 w-px bg-border" />

      <div
        v-for="a in activities"
        :key="a.id"
        class="relative flex gap-4 pb-8"
      >
        <div class="relative z-10 shrink-0">
          <div
            :class="[
              'size-10 rounded-full flex items-center justify-center border-2 border-background',
              typeBgClass(a.type)
            ]"
          >
            <component
              :is="typeIcon(a.type)"
              class="size-4"
            />
          </div>
        </div>

        <AdminCard class="flex-1 min-w-0">
          <div class="p-4">
            <div class="flex items-start justify-between gap-3 mb-2">
              <div class="flex items-center gap-2 flex-wrap min-w-0">
                <span class="font-medium">{{ a.author?.nickname || a.author?.username || '系统' }}</span>
                <Separator
                  orientation="vertical"
                  class="h-4"
                />
                <span class="text-xs text-muted-foreground">
                  {{ formatAdminDateTime(a.created_at) }}
                </span>
                <Badge variant="outline">
                  {{ typeText(a.type) }}
                </Badge>
                <Badge
                  v-if="!a.is_published"
                  variant="secondary"
                >
                  未发布
                </Badge>
              </div>
              <div class="flex items-center gap-1 shrink-0">
                <Button
                  variant="ghost"
                  size="icon-sm"
                  aria-label="编辑动态"
                  @click="openEdit(a)"
                >
                  <Pencil data-icon="inline-start" />
                </Button>
                <Button
                  variant="ghost"
                  size="icon-sm"
                  class="text-destructive hover:text-destructive"
                  aria-label="删除动态"
                  @click="confirmDelete(a)"
                >
                  <Trash2 data-icon="inline-start" />
                </Button>
              </div>
            </div>

            <p class="text-foreground/90 leading-relaxed whitespace-pre-wrap break-words">
              {{ displayField(a.content) }}
            </p>
          </div>
        </AdminCard>
      </div>
    </div>

    <div class="pt-4">
      <AdminPagination
        v-model:page="page"
        v-model:page-size="pageSize"
        :total="total"
        :page-size-options="[10, 20, 50, 100]"
        @update:page="fetchData"
      />
    </div>

    <Dialog v-model:open="formDialogOpen">
      <DialogContent>
        <DialogHeader>
          <DialogTitle>{{ editingId ? '编辑动态' : '发说说' }}</DialogTitle>
          <DialogDescription>
            {{ editingId ? '修改现有动态内容' : '发布一条新的说说/动态' }}
          </DialogDescription>
        </DialogHeader>

        <div class="flex flex-col gap-4 py-2">
          <div class="flex flex-col gap-2">
            <Label for="activity-type">类型</Label>
            <!-- 后端 ActivityType 枚举：say / article / update / notice / link -->
            <Select v-model="form.type">
              <SelectTrigger id="activity-type">
                <SelectValue placeholder="选择类型" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem
                  v-for="opt in typeOptions"
                  :key="opt.value"
                  :value="opt.value"
                >
                  {{ opt.label }}
                </SelectItem>
              </SelectContent>
            </Select>
          </div>

          <!-- 后端要求 content 为多语言 dict（extra=forbid，不再支持 title/link 字段） -->
          <I18nTabsEditor
            v-model="form.content"
            kind="textarea"
            :rows="4"
            label="内容"
            placeholder="此刻的想法..."
            required
          />

          <div class="flex items-center justify-between rounded-xl border p-3">
            <div>
              <div class="text-sm font-medium">
                发布到时间线
              </div>
              <div class="text-xs text-muted-foreground">
                关闭则仅自己可见
              </div>
            </div>
            <Switch
              v-model="form.published"
              aria-label="发布到时间线"
            />
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
            {{ editingId ? '保存修改' : '发布' }}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>

    <!-- 删除确认：统一走 DangerConfirmDialog -->
    <DangerConfirmDialog
      v-model:open="deleteDialogOpen"
      title="确认删除动态"
      confirm-text="确认删除"
      confirm-phrase="删除动态"
      phrase-hint="请输入：删除动态"
      :on-confirm="doDelete"
    >
      <template #description>
        将删除动态内容：{{ (displayField(deleteTarget?.content) || '').slice(0, 60) }}…删除后无法恢复。
      </template>
    </DangerConfirmDialog>
  </div>
</template>

<script setup lang="ts">
/* eslint-disable */

import AdminCard from '~~/components/admin/AdminCard.vue'
import DangerConfirmDialog from '~~/components/admin/tools/DangerConfirmDialog.vue'
import I18nTabsEditor from '~~/components/admin/I18nTabsEditor.vue'
import { Button } from '~~/components/ui/button'
import { Badge } from '~~/components/ui/badge'
import { Switch } from '~~/components/ui/switch'
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from '~~/components/ui/dialog'
import { Skeleton } from '~~/components/ui/skeleton'
import { Alert, AlertDescription, AlertTitle } from '~~/components/ui/alert'
import { Separator } from '~~/components/ui/separator'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '~~/components/ui/select'
import { Label } from '~~/components/ui/label'
import {
  Plus, Info, Pencil, Trash2, Loader2, RotateCcw, Activity,
  MessageSquareQuote, FileText, RefreshCw, Bell, Link as LinkIcon
} from '@lucide/vue'
import {
  fetchAdminActivities,
  createAdminActivity,
  updateAdminActivity,
  deleteAdminActivity,
  formatAdminDateTime
} from '~~/composables/useAdminManage'
import {
  getLocalizedStr,
  normalizeI18nDict,
  toI18nPayload,
  type I18nDict
} from '~~/composables/useAdminI18n'

definePageMeta({ ssr: false, layout: 'admin' })

const toast = useToast()

// 与 backend/schemas/activity.py 的 ActivityType 严格一致
type ActType = 'say' | 'article' | 'update' | 'notice' | 'link'

// 后端 ActivityResponse：content 为 i18n dict，无 title/link 字段
interface ActivityRow {
  id: number
  content: string | Record<string, string> | null
  type: ActType | string
  author?: { username?: string, nickname?: string | null } | null
  is_published: boolean
  created_at: string | null
}

const typeOptions: { value: ActType, label: string }[] = [
  { value: 'say', label: '说说' },
  { value: 'article', label: '文章' },
  { value: 'update', label: '更新' },
  { value: 'notice', label: '通知' },
  { value: 'link', label: '链接' }
]

const loading = ref(false)
const submitting = ref(false)
const loadError = ref(false)
const loadErrorMsg = ref('')
const activities = shallowRef<ActivityRow[]>([])
const page = ref(1)
const pageSize = ref(20)
const total = ref(0)

const formDialogOpen = ref(false)
const editingId = ref<number | null>(null)
const formError = ref('')
const form = reactive({
  type: 'say' as ActType,
  content: { zh: '', en: '', ja: '', zh_Hant: '' } as I18nDict,
  published: true
})

const deleteDialogOpen = ref(false)
const deleteTarget = ref<ActivityRow | null>(null)

function displayField(v: unknown): string {
  return getLocalizedStr(v as string | Record<string, string> | null | undefined)
}

function typeIcon(t: string) {
  switch (t) {
    case 'say': return MessageSquareQuote
    case 'article': return FileText
    case 'update': return RefreshCw
    case 'notice': return Bell
    case 'link': return LinkIcon
    default: return MessageSquareQuote
  }
}

function typeText(t: string): string {
  switch (t) {
    case 'say': return '说说'
    case 'article': return '文章'
    case 'update': return '更新'
    case 'notice': return '通知'
    case 'link': return '链接'
    default: return t
  }
}

function typeBgClass(t: string): string {
  switch (t) {
    case 'say': return 'bg-success-muted text-success-muted-foreground'
    case 'article': return 'bg-info-muted text-info-muted-foreground'
    case 'update': return 'bg-primary/10 text-primary'
    case 'notice': return 'bg-warning-muted text-warning-muted-foreground'
    case 'link': return 'bg-error-muted text-error-muted-foreground'
    default: return 'bg-muted text-muted-foreground'
  }
}

async function fetchData() {
  loading.value = true
  loadError.value = false
  loadErrorMsg.value = ''
  try {
    // 删除后当前页可能越界：回退一页再取（循环而非递归，保证 loading 覆盖全程）
    for (;;) {
      const res = await fetchAdminActivities({ page: page.value, page_size: pageSize.value })
      const items = (res.items ?? []) as unknown as ActivityRow[]
      total.value = res.total ?? 0
      if (items.length === 0 && total.value > 0 && page.value > 1) {
        page.value -= 1
        continue
      }
      activities.value = items
      break
    }
  } catch (err) {
    // apiFetch 已自动 toast，这里保留页面级错误态 + 重试入口
    console.error('fetch activities error', err)
    activities.value = []
    total.value = 0
    loadError.value = true
    loadErrorMsg.value = err instanceof Error ? err.message : ''
  } finally {
    loading.value = false
  }
}

function openCreate() {
  editingId.value = null
  formError.value = ''
  Object.assign(form, {
    type: 'say' as ActType,
    content: { zh: '', en: '', ja: '', zh_Hant: '' },
    published: true
  })
  formDialogOpen.value = true
}

function openEdit(a: ActivityRow) {
  editingId.value = a.id
  formError.value = ''
  Object.assign(form, {
    type: (typeOptions.some(o => o.value === a.type) ? a.type : 'say') as ActType,
    content: normalizeI18nDict(a.content),
    published: a.is_published
  })
  formDialogOpen.value = true
}

async function submitForm() {
  formError.value = ''
  // 后端 ActivityBase.content 为必填 i18n dict，且 extra=forbid：只允许 content/type/is_published
  const contentPayload = toI18nPayload(form.content as Record<string, string>)
  if (!contentPayload) {
    formError.value = '请填写内容（至少一种语言）'
    return
  }
  submitting.value = true
  const payload: Record<string, unknown> = {
    content: contentPayload,
    type: form.type,
    is_published: form.published
  }
  try {
    if (editingId.value) {
      await updateAdminActivity(editingId.value, payload)
      toast.success('修改成功')
    } else {
      await createAdminActivity(payload)
      toast.success('发布成功')
    }
    formDialogOpen.value = false
    fetchData()
  } catch (err) {
    // apiFetch 已弹 toast；弹窗保持打开并保留输入，内联提示失败原因
    console.error('submit activity error', err)
    formError.value = err instanceof Error ? err.message : (editingId.value ? '修改失败' : '发布失败')
  } finally {
    submitting.value = false
  }
}

function confirmDelete(a: ActivityRow) {
  deleteTarget.value = a
  deleteDialogOpen.value = true
}

async function doDelete() {
  const target = deleteTarget.value
  if (!target?.id) throw new Error('未选择要删除的动态')
  // 抛错时 DangerConfirmDialog 保持打开并内联显示错误；toast 由 apiFetch 统一处理
  await deleteAdminActivity(target.id)
  toast.success('删除成功')
  deleteTarget.value = null
  await fetchData()
}

onMounted(fetchData)
</script>
