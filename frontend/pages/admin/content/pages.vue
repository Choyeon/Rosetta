<script setup lang="ts">
/* eslint-disable */
/* eslint-disable @typescript-eslint/ban-ts-comment */
// @ts-nocheck
/* eslint-enable @typescript-eslint/ban-ts-comment */
import { ref, reactive, onMounted } from 'vue'
import {
  fetchAdminPages,
  createAdminPage,
  updateAdminPage,
  deleteAdminPage,
  formatAdminDateTime,
  type AdminPage
} from '~~/composables/useAdminManage'
import { useToast } from '~~/composables/useToast'
import { Button } from '~~/components/ui/button'
import { Input } from '~~/components/ui/input'
import { Textarea } from '~~/components/ui/textarea'
import { Label } from '~~/components/ui/label'
import { Badge } from '~~/components/ui/badge'
import { Switch } from '~~/components/ui/switch'
import { Skeleton } from '~~/components/ui/skeleton'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue
} from '~~/components/ui/select'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger
} from '~~/components/ui/dialog'

definePageMeta({ ssr: false, layout: 'admin' })

const toast = useToast()

const pages = ref<AdminPage[]>([])
const loading = ref(false)
const total = ref(0)
const page = ref(1)
const pageSize = ref(20)
const totalPages = ref(1)

const dialogOpen = ref(false)
const dialogMode = ref<'new' | 'edit'>('new')
const saving = ref(false)
const deleteDialogOpen = ref(false)
const pendingDeleteId = ref<number | null>(null)

const form = reactive({
  slug: '',
  title: '',
  status: 'draft' as 'draft' | 'published',
  is_pinned: false,
  content: ''
})

const editingId = ref<number | null>(null)

const getLocalizedStr = (v: string | Record<string, string> | null | undefined): string => {
  if (v == null) return ''
  if (typeof v === 'string') return v
  return v.zh || v.en || Object.values(v)[0] || ''
}

const slugify = (text: string): string => {
  let s = text.trim().toLowerCase()
  s = s.replace(/[\s]+/g, '-')
  s = s.replace(/[^\w\u4e00-\u9fa5-]/g, '')
  s = s.replace(/-+/g, '-').replace(/^-|-$/g, '')
  return s
}

let slugManualEdit = false
watch(
  () => form.title,
  (val) => {
    if (!slugManualEdit && val) {
      form.slug = slugify(val)
    }
  }
)

const statusBadgeVariant = (status: string): string => {
  switch (status) {
    case 'published': return 'bg-emerald-100 text-emerald-700 border-emerald-200'
    case 'draft': return 'bg-amber-100 text-amber-700 border-amber-200'
    default: return 'bg-slate-100 text-slate-600 border-slate-200'
  }
}

const statusLabel = (status: string): string => {
  return status === 'published' ? '已发布' : '草稿'
}

const loadData = async () => {
  loading.value = true
  try {
    const res = await fetchAdminPages({ page: page.value, page_size: pageSize.value })
    pages.value = res.items || []
    total.value = res.total || pages.value.length
    totalPages.value = res.total_pages || Math.max(1, Math.ceil(total.value / pageSize.value))
  } catch (e) {
    toast.error(e instanceof Error ? e.message : '加载页面列表失败')
    pages.value = []
    total.value = 0
    totalPages.value = 1
  } finally {
    loading.value = false
  }
}

const openNew = () => {
  dialogMode.value = 'new'
  editingId.value = null
  form.slug = ''
  form.title = ''
  form.status = 'draft'
  form.is_pinned = false
  form.content = ''
  slugManualEdit = false
  dialogOpen.value = true
}

const openEdit = (p: AdminPage) => {
  dialogMode.value = 'edit'
  editingId.value = p.id
  form.slug = p.slug
  form.title = getLocalizedStr(p.title)
  form.status = p.status
  form.is_pinned = p.is_pinned
  form.content = getLocalizedStr(p.content)
  slugManualEdit = true
  dialogOpen.value = true
}

const save = async () => {
  if (!form.slug.trim()) {
    toast.error('请输入 slug')
    return
  }
  if (!form.title.trim()) {
    toast.error('请输入标题')
    return
  }
  saving.value = true
  try {
    const payload: Record<string, unknown> = {
      slug: form.slug,
      title: { zh: form.title },
      status: form.status,
      is_pinned: form.is_pinned,
      content: { zh: form.content }
    }
    if (dialogMode.value === 'edit' && editingId.value) {
      await updateAdminPage(editingId.value, payload)
      toast.success('更新成功')
    } else {
      await createAdminPage(payload)
      toast.success('创建成功')
    }
    dialogOpen.value = false
    await loadData()
  } catch (e) {
    toast.error(e instanceof Error ? e.message : '保存失败')
  } finally {
    saving.value = false
  }
}

const confirmDelete = (id: number) => {
  pendingDeleteId.value = id
  deleteDialogOpen.value = true
}

const doDelete = async () => {
  if (pendingDeleteId.value == null) return
  try {
    await deleteAdminPage(pendingDeleteId.value)
    toast.success('删除成功')
    deleteDialogOpen.value = false
    pendingDeleteId.value = null
    await loadData()
  } catch (e) {
    toast.error(e instanceof Error ? e.message : '删除失败')
  }
}

const goToPage = (p: number) => {
  if (p < 1 || p > totalPages.value) return
  page.value = p
}

watch([page, pageSize], () => {
  loadData()
})

onMounted(() => {
  loadData()
})
</script>

<template>
  <div class="flex flex-col gap-5 p-6">
    <div class="flex items-center justify-between">
      <div class="flex items-center gap-3">
        <h1 class="text-2xl font-bold tracking-tight">
          独立页面
        </h1>
        <Badge
          variant="secondary"
          class="rounded-[10px] px-3 py-1 bg-stone-100 text-stone-700 border-stone-200"
        >
          共 {{ total }} 页
        </Badge>
      </div>
      <Dialog v-model:open="dialogOpen">
        <DialogTrigger as-child>
          <Button
            class="rounded-[12px] h-10 px-5 shadow-sm"
            @click="openNew"
          >
            + 新建页面
          </Button>
        </DialogTrigger>
        <DialogContent class="rounded-[12px] max-w-xl">
          <DialogHeader>
            <DialogTitle>{{ dialogMode === 'edit' ? '编辑页面' : '新建页面' }}</DialogTitle>
            <DialogDescription>
              独立页面用于创建关于、联系等非常规文章的页面。
            </DialogDescription>
          </DialogHeader>
          <div class="flex flex-col gap-4 py-4 max-h-[70vh] overflow-y-auto pr-1">
            <div class="grid grid-cols-2 gap-3">
              <div>
                <Label class="mb-1 block text-xs text-muted-foreground">
                  Slug <span class="text-destructive">*</span>
                </Label>
                <Input
                  v-model="form.slug"
                  placeholder="如 about, contact"
                  class="h-9 rounded-[10px]"
                  @input="slugManualEdit = true"
                />
              </div>
              <div>
                <Label class="mb-1 block text-xs text-muted-foreground">
                  标题 <span class="text-destructive">*</span>
                </Label>
                <Input
                  v-model="form.title"
                  placeholder="页面标题"
                  class="h-9 rounded-[10px]"
                />
              </div>
            </div>
            <div class="grid grid-cols-2 gap-3">
              <div>
                <Label class="mb-1 block text-xs text-muted-foreground">状态</Label>
                <Select v-model="form.status">
                  <SelectTrigger class="h-9 rounded-[10px]">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="draft">
                      草稿
                    </SelectItem>
                    <SelectItem value="published">
                      已发布
                    </SelectItem>
                  </SelectContent>
                </Select>
              </div>
              <div class="flex items-center justify-between rounded-[10px] border border-input px-3 py-2 bg-background">
                <span class="text-sm">置顶</span>
                <Switch v-model="form.is_pinned" />
              </div>
            </div>
            <div>
              <Label class="mb-1 block text-xs text-muted-foreground">
                内容
                <span class="opacity-60 ml-1">（未来将替换为 Markdown 编辑器）</span>
              </Label>
              <Textarea
                v-model="form.content"
                rows="8"
                placeholder="页面内容..."
                class="rounded-[10px] text-sm resize-y font-mono leading-relaxed"
              />
            </div>
          </div>
          <DialogFooter>
            <Button
              variant="outline"
              class="rounded-[10px]"
              @click="dialogOpen = false"
            >
              取消
            </Button>
            <Button
              class="rounded-[10px]"
              :disabled="saving"
              @click="save"
            >
              {{ saving ? '保存中...' : '保存' }}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>

    <div class="rounded-[12px] border border-border bg-card overflow-hidden">
      <div class="overflow-x-auto">
        <div class="min-w-[700px]">
          <div class="grid grid-cols-[1fr,1.5fr,110px,80px,180px,130px] bg-stone-50/80 border-b border-border text-xs font-medium text-muted-foreground">
            <div class="p-3">
              Slug
            </div>
            <div class="p-3">
              标题
            </div>
            <div class="p-3">
              状态
            </div>
            <div class="p-3 text-center">
              置顶
            </div>
            <div class="p-3">
              更新时间
            </div>
            <div class="p-3 text-center">
              操作
            </div>
          </div>

          <template v-if="loading">
            <div
              v-for="i in 5"
              :key="`sk-${i}`"
              class="grid grid-cols-[1fr,1.5fr,110px,80px,180px,130px] border-b border-border/50"
            >
              <div class="p-3">
                <Skeleton class="h-5 w-1/2 rounded" />
              </div>
              <div class="p-3">
                <Skeleton class="h-5 w-3/4 rounded" />
              </div>
              <div class="p-3">
                <Skeleton class="h-5 w-16 rounded-full" />
              </div>
              <div class="p-3">
                <Skeleton class="h-4 w-8 rounded mx-auto" />
              </div>
              <div class="p-3">
                <Skeleton class="h-4 w-32 rounded" />
              </div>
              <div class="p-3 flex gap-2 justify-center">
                <Skeleton class="h-8 w-14 rounded" /><Skeleton class="h-8 w-14 rounded" />
              </div>
            </div>
          </template>

          <template v-else-if="pages.length === 0">
            <div class="py-20 text-center text-muted-foreground">
              <div class="text-5xl mb-3 opacity-30">
                📄
              </div>
              <div class="text-sm">
                暂无独立页面
              </div>
            </div>
          </template>

          <template v-else>
            <div
              v-for="(p, idx) in pages"
              :key="p.id"
              class="grid grid-cols-[1fr,1.5fr,110px,80px,180px,130px] border-b border-border/50 text-sm"
              :class="{ 'bg-stone-50/40': idx % 2 === 1 }"
            >
              <div
                class="p-3 font-mono text-xs text-muted-foreground truncate"
                :title="p.slug"
              >
                /{{ p.slug }}
              </div>
              <div
                class="p-3 font-medium truncate"
                :title="getLocalizedStr(p.title)"
              >
                {{ getLocalizedStr(p.title) }}
              </div>
              <div class="p-3">
                <Badge
                  class="rounded-[10px] border font-normal"
                  :class="statusBadgeVariant(p.status)"
                >
                  {{ statusLabel(p.status) }}
                </Badge>
              </div>
              <div class="p-3 text-center">
                <span
                  v-if="p.is_pinned"
                  class="text-amber-500"
                >★</span>
              </div>
              <div class="p-3 text-xs text-muted-foreground">
                {{ formatAdminDateTime(p.updated_at ?? p.created_at) }}
              </div>
              <div class="p-3 flex items-center justify-center gap-1.5">
                <Button
                  variant="ghost"
                  size="sm"
                  class="h-8 rounded-[10px] text-xs px-3"
                  @click="openEdit(p)"
                >
                  编辑
                </Button>
                <Button
                  variant="ghost"
                  size="sm"
                  class="h-8 rounded-[10px] text-xs px-3 text-destructive hover:text-destructive"
                  @click="confirmDelete(p.id)"
                >
                  删除
                </Button>
              </div>
            </div>
          </template>
        </div>
      </div>

      <div class="flex items-center justify-end gap-1 px-4 py-3 border-t border-border bg-stone-50/50">
        <Button
          variant="outline"
          size="sm"
          class="h-9 rounded-[10px] px-3"
          :disabled="page <= 1"
          @click="goToPage(page - 1)"
        >
          上一页
        </Button>
        <span class="text-sm text-muted-foreground px-3">
          第 {{ page }} / {{ totalPages }} 页
        </span>
        <Button
          variant="outline"
          size="sm"
          class="h-9 rounded-[10px] px-3"
          :disabled="page >= totalPages"
          @click="goToPage(page + 1)"
        >
          下一页
        </Button>
      </div>
    </div>

    <Dialog v-model:open="deleteDialogOpen">
      <DialogContent class="rounded-[12px] max-w-md">
        <DialogHeader>
          <DialogTitle>确认删除页面</DialogTitle>
          <DialogDescription>
            此操作不可撤销，确定要删除这个页面吗？
          </DialogDescription>
        </DialogHeader>
        <DialogFooter class="mt-4">
          <Button
            variant="outline"
            class="rounded-[10px]"
            @click="deleteDialogOpen = false"
          >
            取消
          </Button>
          <Button
            variant="destructive"
            class="rounded-[10px]"
            @click="doDelete"
          >
            确认删除
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  </div>
</template>
