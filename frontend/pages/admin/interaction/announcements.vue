<template>
  <div class="space-y-6">
    <div class="flex items-center justify-between">
      <h1 class="text-2xl font-bold">
        公告管理
      </h1>
      <Button
        class="rounded-xl shadow-sm"
        @click="openCreate"
      >
        <Plus class="size-4 mr-2" />
        新建公告
      </Button>
    </div>

    <Card>
      <CardContent class="p-0">
        <div
          v-if="loading"
          class="p-4 space-y-3"
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
            <thead>
              <tr class="border-b bg-muted/30">
                <th class="text-left font-medium p-4">
                  类型
                </th>
                <th class="text-left font-medium p-4">
                  标题
                </th>
                <th class="text-left font-medium p-4">
                  置顶
                </th>
                <th class="text-left font-medium p-4">
                  可关闭
                </th>
                <th class="text-left font-medium p-4">
                  粘性
                </th>
                <th class="text-left font-medium p-4">
                  启用
                </th>
                <th class="text-left font-medium p-4">
                  创建时间
                </th>
                <th class="text-right font-medium p-4">
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
                  <Badge :class="typeBadgeClass(a.type)">
                    {{ typeIcon(a.type) }} {{ typeText(a.type) }}
                  </Badge>
                </td>
                <td class="p-4 font-medium">
                  {{ displayField(a.title) }}
                </td>
                <td class="p-4">
                  <Pin
                    v-if="a.is_pinned"
                    class="size-4 text-warning"
                  />
                  <span
                    v-else
                    class="text-muted-foreground"
                  >-</span>
                </td>
                <td class="p-4">
                  <Check
                    v-if="a.is_dismissible"
                    class="size-4 text-success"
                  />
                  <span
                    v-else
                    class="text-muted-foreground"
                  >-</span>
                </td>
                <td class="p-4">
                  <Check
                    v-if="a.is_sticky"
                    class="size-4 text-success"
                  />
                  <span
                    v-else
                    class="text-muted-foreground"
                  >-</span>
                </td>
                <td class="p-4">
                  <Switch
                    :model-value="a.active"
                    @change="toggleActive(a, $event)"
                  />
                </td>
                <td class="p-4 text-muted-foreground">
                  {{ formatAdminDateTime(a.created_at) }}
                </td>
                <td class="p-4 text-right">
                  <div class="inline-flex items-center gap-1">
                    <Button
                      variant="ghost"
                      size="icon"
                      class="h-8 w-8"
                      @click="openEdit(a)"
                    >
                      <Pencil class="size-4" />
                    </Button>
                    <Button
                      variant="ghost"
                      size="icon"
                      class="h-8 w-8 text-destructive hover:text-destructive"
                      @click="confirmDelete(a.id)"
                    >
                      <Trash2 class="size-4" />
                    </Button>
                  </div>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </CardContent>
    </Card>

    <div
      v-if="totalPages > 1"
      class="pt-2"
    >
      <Pagination :items-per-page="pageSize ?? 10">
        <PaginationContent>
          <PaginationItem :value="1" />
          <PaginationPrevious
            :disabled="page <= 1"
            @click="page > 1 && (page--, fetchData())"
          />
          <template
            v-for="p in visiblePages"
            :key="p"
          >
            <PaginationItem v-if="p !== '...'">
              <Button
                :variant="p === page ? 'default' : 'ghost'"
                size="icon"
                class="h-9 w-9"
                @click="page !== p && (page = p, fetchData())"
              >
                {{ p }}
              </Button>
            </PaginationItem>
            <PaginationItem v-else>
              <PaginationEllipsis :value="1" />
            </PaginationItem>
          </template>
          <PaginationItem :value="1" />
          <PaginationNext
            :disabled="page >= totalPages"
            @click="page < totalPages && (page++, fetchData())"
          />
        </PaginationContent>
      </Pagination>
    </div>

    <Dialog v-model:open="formDialogOpen">
      <DialogContent class="sm:max-w-lg">
        <DialogHeader>
          <DialogTitle>{{ editingId ? '编辑公告' : '新建公告' }}</DialogTitle>
          <DialogDescription>
            公告将展示在站点顶部，支持 Markdown 内容
          </DialogDescription>
        </DialogHeader>

        <div class="space-y-4 py-2">
          <div class="space-y-2">
            <Label>公告类型</Label>
            <div class="grid grid-cols-4 gap-2">
              <button
                v-for="t in announcementTypes"
                :key="t.value"
                type="button"
                :class="[
                  'flex flex-col items-center justify-center gap-1 p-3 rounded-xl border transition-all',
                  form.type === t.value
                    ? 'border-primary bg-primary/5 ring-2 ring-primary/20'
                    : 'hover:bg-muted/40'
                ]"
                @click="form.type = t.value"
              >
                <span class="text-2xl">{{ t.icon }}</span>
                <span class="text-xs">{{ t.label }}</span>
              </button>
            </div>
          </div>

          <div class="space-y-2">
            <Label>标题 <span class="text-destructive">*</span></Label>
            <Input
              v-model="form.title"
              placeholder="公告标题"
            />
          </div>

          <div class="space-y-2">
            <Label>内容（Markdown）</Label>
            <Textarea
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
                  置顶
                </div>
                <div class="text-xs text-muted-foreground">
                  固定在最上方
                </div>
              </div>
              <Switch v-model="form.is_pinned" />
            </div>
            <div class="flex items-center justify-between rounded-xl border p-3">
              <div>
                <div class="text-sm font-medium">
                  可关闭
                </div>
                <div class="text-xs text-muted-foreground">
                  用户可手动关闭
                </div>
              </div>
              <Switch v-model="form.is_dismissible" />
            </div>
            <div class="flex items-center justify-between rounded-xl border p-3">
              <div>
                <div class="text-sm font-medium">
                  粘性
                </div>
                <div class="text-xs text-muted-foreground">
                  滚动时保持显示
                </div>
              </div>
              <Switch v-model="form.is_sticky" />
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
              <Switch v-model="form.active" />
            </div>
          </div>
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
              class="size-4 mr-2 animate-spin"
            />
            {{ editingId ? '保存修改' : '创建公告' }}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>

    <Dialog v-model:open="deleteDialogOpen">
      <DialogContent>
        <DialogHeader>
          <DialogTitle>确认删除</DialogTitle>
          <DialogDescription>删除后该公告将无法恢复，确定继续吗？</DialogDescription>
        </DialogHeader>
        <DialogFooter>
          <Button
            variant="ghost"
            @click="deleteDialogOpen = false"
          >
            取消
          </Button>
          <Button
            variant="destructive"
            @click="doDelete"
          >
            确认删除
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  </div>
</template>

<script setup lang="ts">
/* eslint-disable */
/* eslint-disable @typescript-eslint/ban-ts-comment */
// @ts-nocheck
/* eslint-enable @typescript-eslint/ban-ts-comment */
import { Card, CardContent } from '~~/components/ui/card'
import { Button } from '~~/components/ui/button'
import { Input } from '~~/components/ui/input'
import { Textarea } from '~~/components/ui/textarea'
import { Badge } from '~~/components/ui/badge'
import { Switch } from '~~/components/ui/switch'
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from '~~/components/ui/dialog'
import { Pagination, PaginationContent, PaginationEllipsis, PaginationItem, PaginationNext, PaginationPrevious } from '~~/components/ui/pagination'
import { Skeleton } from '~~/components/ui/skeleton'
import { Alert, AlertDescription, AlertTitle } from '~~/components/ui/alert'
import { Label } from '~~/components/ui/label'
import {
  Plus, Pin, Check, Pencil, Trash2, Info, Loader2
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
  { value: 'info' as AnnType, label: '信息', icon: 'ℹ️' },
  { value: 'warning' as AnnType, label: '警告', icon: '⚠️' },
  { value: 'error' as AnnType, label: '错误', icon: '❌' },
  { value: 'success' as AnnType, label: '成功', icon: '✅' }
]

const loading = ref(false)
const submitting = ref(false)
const announcements = ref<AdminAnnouncement[]>([])
const page = ref(1)
const pageSize = 20
const total = ref(0)

const formDialogOpen = ref(false)
const editingId = ref<number | null>(null)
const form = reactive({
  type: 'info' as AnnType,
  title: '',
  content_md: '',
  is_pinned: false,
  is_dismissible: true,
  is_sticky: false,
  active: true
})

const deleteDialogOpen = ref(false)
const deleteTargetId = ref<number | null>(null)

const totalPages = computed(() => Math.max(1, Math.ceil(total.value / pageSize)))

const visiblePages = computed(() => {
  const tp = totalPages.value
  const curr = page.value
  if (tp <= 7) return Array.from({ length: tp }, (_, i) => i + 1)
  const pages: (number | string)[] = [1]
  if (curr > 3) pages.push('...')
  for (let i = Math.max(2, curr - 1); i <= Math.min(tp - 1, curr + 1); i++) pages.push(i)
  if (curr < tp - 2) pages.push('...')
  pages.push(tp)
  return pages
})

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
    case 'info': return 'bg-info-muted text-info-foreground hover:bg-info-muted'
    case 'warning': return 'bg-warning-muted text-warning-foreground hover:bg-warning-muted'
    case 'error': return 'bg-error-muted text-error-foreground hover:bg-error-muted'
    case 'success': return 'bg-success-muted text-success-foreground hover:bg-success-muted'
    default: return 'bg-muted text-muted-foreground'
  }
}

function typeIcon(t: string): string {
  switch (t) {
    case 'info': return 'ℹ️'
    case 'warning': return '⚠️'
    case 'error': return '❌'
    case 'success': return '✅'
    default: return '📢'
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
  try {
    const res = await fetchAdminAnnouncements({ page: page.value, page_size: pageSize })
    announcements.value = res.items ?? []
    total.value = res.total ?? 0
  } catch (err) {
    toast.error(err instanceof Error ? err.message : '加载公告失败')
    announcements.value = []
    total.value = 0
  } finally {
    loading.value = false
  }
}

function openCreate() {
  editingId.value = null
  Object.assign(form, {
    type: 'info',
    title: '',
    content_md: '',
    is_pinned: false,
    is_dismissible: true,
    is_sticky: false,
    active: true
  })
  formDialogOpen.value = true
}

function openEdit(a: AdminAnnouncement) {
  editingId.value = a.id
  Object.assign(form, {
    type: a.type,
    title: displayField(a.title),
    content_md: displayField(a.content_md),
    is_pinned: a.is_pinned,
    is_dismissible: a.is_dismissible,
    is_sticky: a.is_sticky,
    active: a.active
  })
  formDialogOpen.value = true
}

async function toggleActive(a: AdminAnnouncement, ev: unknown) {
  const checked = ev === true || (ev as { checked?: boolean })?.checked === true
  try {
    await updateAdminAnnouncement(a.id, { active: checked })
    toast.success('状态已更新')
    a.active = checked
  } catch (err) {
    toast.error(err instanceof Error ? err.message : '更新失败')
  }
}

async function submitForm() {
  if (!form.title.trim()) {
    toast.warning('请填写标题')
    return
  }
  submitting.value = true
  const payload: Record<string, unknown> = {
    type: form.type,
    title: { zh: form.title.trim() },
    content_md: { zh: form.content_md },
    is_pinned: form.is_pinned,
    is_dismissible: form.is_dismissible,
    is_sticky: form.is_sticky,
    active: form.active
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
    toast.error(err instanceof Error ? err.message : '保存失败')
  } finally {
    submitting.value = false
  }
}

function confirmDelete(id: number) {
  deleteTargetId.value = id
  deleteDialogOpen.value = true
}

async function doDelete() {
  if (deleteTargetId.value === null) return
  try {
    await deleteAdminAnnouncement(deleteTargetId.value)
    toast.success('删除成功')
    deleteDialogOpen.value = false
    deleteTargetId.value = null
    fetchData()
  } catch (err) {
    toast.error(err instanceof Error ? err.message : '删除失败')
  }
}

onMounted(fetchData)
</script>
