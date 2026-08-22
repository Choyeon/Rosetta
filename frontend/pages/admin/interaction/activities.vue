<template>
  <div class="space-y-6">
    <div class="flex items-center justify-between">
      <h1 class="text-2xl font-bold">
        动态/说说管理
      </h1>
      <Button
        class="rounded-xl shadow-sm"
        @click="openCreate"
      >
        <Plus class="size-4 mr-2" />
        发说说
      </Button>
    </div>

    <div class="flex flex-wrap items-center gap-2">
      <div
        v-for="opt in typeOptions"
        :key="opt.value"
        :class="[
          'inline-flex items-center gap-1.5 px-4 py-2 rounded-full text-sm border transition-all cursor-pointer',
          selectedType === opt.value
            ? 'bg-primary/10 border-primary text-primary'
            : 'bg-card hover:bg-muted/50'
        ]"
        @click="setType(opt.value)"
      >
        <span>{{ opt.icon }}</span>
        <span>{{ opt.label }}</span>
      </div>
    </div>

    <div
      v-if="loading"
      class="space-y-4"
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
        <div class="flex-1 space-y-3">
          <Skeleton class="h-4 w-40" />
          <Skeleton class="h-20 w-full rounded-xl" />
        </div>
      </div>
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
        <AlertDescription>当前筛选下没有动态数据，点击右上角发一条吧</AlertDescription>
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
              'size-10 rounded-full flex items-center justify-center text-lg border-2 border-background',
              typeBgClass(a.type)
            ]"
          >
            {{ typeIcon(a.type) }}
          </div>
        </div>

        <Card class="flex-1 min-w-0">
          <CardContent class="p-4">
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
                <Badge
                  variant="outline"
                  class="text-xs"
                >
                  {{ typeText(a.type) }}
                </Badge>
              </div>
              <div class="flex items-center gap-1 shrink-0">
                <Button
                  variant="ghost"
                  size="icon"
                  class="h-7 w-7"
                  @click="openEdit(a)"
                >
                  <Pencil class="size-3.5" />
                </Button>
                <Button
                  variant="ghost"
                  size="icon"
                  class="h-7 w-7 text-destructive hover:text-destructive"
                  @click="confirmDelete(a.id)"
                >
                  <Trash2 class="size-3.5" />
                </Button>
              </div>
            </div>

            <p
              v-if="displayField(a.title)"
              class="font-medium mb-1"
            >
              {{ displayField(a.title) }}
            </p>
            <p
              v-if="a.content"
              class="text-foreground/90 leading-relaxed whitespace-pre-wrap"
            >
              {{ a.content }}
            </p>

            <div
              v-if="a.link"
              class="mt-3"
            >
              <a
                :href="a.link"
                target="_blank"
                rel="noopener noreferrer"
                class="inline-flex items-center gap-1.5 text-sm text-primary hover:underline max-w-full truncate"
              >
                <ExternalLink class="size-3.5 shrink-0" />
                <span class="truncate">{{ a.link }}</span>
              </a>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>

    <div
      v-if="totalPages > 1"
      class="pt-4"
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
      <DialogContent>
        <DialogHeader>
          <DialogTitle>{{ editingId ? '编辑动态' : '发说说' }}</DialogTitle>
          <DialogDescription>
            {{ editingId ? '修改现有动态内容' : '发布一条新的说说/动态' }}
          </DialogDescription>
        </DialogHeader>

        <div class="space-y-4 py-2">
          <div
            v-if="editingId"
            class="space-y-2"
          >
            <Label>类型</Label>
            <Select v-model="form.type">
              <SelectTrigger>
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem
                  v-for="opt in typeOptions"
                  :key="opt.value"
                  :value="opt.value"
                >
                  {{ opt.icon }} {{ opt.label }}
                </SelectItem>
              </SelectContent>
            </Select>
          </div>

          <div class="space-y-2">
            <Label>内容</Label>
            <Textarea
              v-model="form.content"
              rows="4"
              placeholder="此刻的想法..."
              class="resize-none"
            />
          </div>

          <div class="space-y-2">
            <Label>链接（可选）</Label>
            <Input
              v-model="form.link"
              placeholder="https://..."
            />
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
            {{ editingId ? '保存修改' : '发布' }}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>

    <Dialog v-model:open="deleteDialogOpen">
      <DialogContent>
        <DialogHeader>
          <DialogTitle>确认删除</DialogTitle>
          <DialogDescription>删除后该动态将无法恢复，确定继续吗？</DialogDescription>
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
import { Card, CardContent } from '~~/components/ui/card'
import { Button } from '~~/components/ui/button'
import { Input } from '~~/components/ui/input'
import { Textarea } from '~~/components/ui/textarea'
import { Badge } from '~~/components/ui/badge'
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from '~~/components/ui/dialog'
import { Pagination, PaginationContent, PaginationEllipsis, PaginationItem, PaginationNext, PaginationPrevious } from '~~/components/ui/pagination'
import { Skeleton } from '~~/components/ui/skeleton'
import { Alert, AlertDescription, AlertTitle } from '~~/components/ui/alert'
import { Separator } from '~~/components/ui/separator'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '~~/components/ui/select'
import { Label } from '~~/components/ui/label'
import {
  Plus, Info, Pencil, Trash2, ExternalLink, Loader2
} from '@lucide/vue'
import {
  fetchAdminActivities,
  createAdminActivity,
  updateAdminActivity,
  deleteAdminActivity,
  formatAdminDateTime,
  type AdminActivity
} from '~~/composables/useAdminManage'

definePageMeta({ ssr: false, layout: 'admin' })

const toast = useToast()

const typeOptions = [
  { value: '', label: '全部', icon: '📋' },
  { value: 'post', label: '文章', icon: '📄' },
  { value: 'card', label: '卡片', icon: '🖼' },
  { value: 'comment', label: '评论', icon: '💬' },
  { value: 'like', label: '点赞', icon: '👍' },
  { value: 'status', label: '说说', icon: '💭' }
]

const loading = ref(false)
const submitting = ref(false)
const activities = ref<AdminActivity[]>([])
const selectedType = ref('')
const page = ref(1)
const pageSize = 20
const total = ref(0)

const formDialogOpen = ref(false)
const editingId = ref<number | null>(null)
const form = reactive({
  type: 'status' as AdminActivity['type'],
  content: '',
  link: ''
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

function typeIcon(t: string): string {
  switch (t) {
    case 'post': return '📄'
    case 'card': return '🖼'
    case 'comment': return '💬'
    case 'like': return '👍'
    case 'status': return '💭'
    default: return '💭'
  }
}

function typeText(t: string): string {
  switch (t) {
    case 'post': return '文章'
    case 'card': return '卡片'
    case 'comment': return '评论'
    case 'like': return '点赞'
    case 'status': return '说说'
    default: return t
  }
}

function typeBgClass(t: string): string {
  switch (t) {
    case 'post': return 'bg-info-muted text-info-foreground'
    case 'card': return 'bg-primary/10 text-primary'
    case 'comment': return 'bg-warning-muted text-warning-foreground'
    case 'like': return 'bg-error-muted text-error-foreground'
    case 'status': return 'bg-success-muted text-success-foreground'
    default: return 'bg-muted text-muted-foreground'
  }
}

function setType(v: string) {
  selectedType.value = v
  page.value = 1
  fetchData()
}

async function fetchData() {
  loading.value = true
  try {
    const res = await fetchAdminActivities({
      page: page.value,
      page_size: pageSize,
      type: selectedType.value || undefined
    })
    activities.value = res.items ?? []
    total.value = res.total ?? 0
  } catch (err) {
    toast.error(err instanceof Error ? err.message : '加载动态失败')
    activities.value = []
    total.value = 0
  } finally {
    loading.value = false
  }
}

function openCreate() {
  editingId.value = null
  Object.assign(form, { type: 'status', content: '', link: '' })
  formDialogOpen.value = true
}

function openEdit(a: AdminActivity) {
  editingId.value = a.id
  Object.assign(form, {
    type: a.type,
    content: a.content ?? '',
    link: a.link ?? ''
  })
  formDialogOpen.value = true
}

async function submitForm() {
  if (!form.content.trim()) {
    toast.warning('请输入内容')
    return
  }
  submitting.value = true
  try {
    if (editingId.value) {
      await updateAdminActivity(editingId.value, {
        type: form.type,
        content: form.content.trim(),
        link: form.link.trim() || null
      })
      toast.success('修改成功')
    } else {
      await createAdminActivity({
        type: 'status',
        content: form.content.trim(),
        link: form.link.trim() || null
      })
      toast.success('发布成功')
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
    await deleteAdminActivity(deleteTargetId.value)
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
