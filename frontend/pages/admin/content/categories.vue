<script setup lang="ts">
/* eslint-disable */
/* eslint-disable @typescript-eslint/ban-ts-comment */
// @ts-nocheck
/* eslint-enable @typescript-eslint/ban-ts-comment */
import { ref, reactive, watch, onMounted } from 'vue'
import {
  fetchAdminCategories,
  createAdminCategory,
  updateAdminCategory,
  deleteAdminCategory,
  type AdminCategory
} from '~~/composables/useAdminManage'
import { useToast } from '~~/composables/useToast'
import { Button } from '~~/components/ui/button'
import { Input } from '~~/components/ui/input'
import { Textarea } from '~~/components/ui/textarea'
import { Label } from '~~/components/ui/label'
import { Card, CardContent, CardHeader, CardTitle } from '~~/components/ui/card'
import { Badge } from '~~/components/ui/badge'
import { Skeleton } from '~~/components/ui/skeleton'
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

const categories = ref<AdminCategory[]>([])
const loading = ref(false)
const saving = ref(false)
const editingId = ref<number | null>(null)
const deleteDialogOpen = ref(false)
const pendingDeleteId = ref<number | null>(null)

// 编辑/新建：使用 Dialog 弹窗，与标签管理保持一致的 UX
const dialogOpen = ref(false)
const dialogMode = ref<'new' | 'edit'>('new')

const form = reactive({
  name: '',
  slug: '',
  description: '',
  color: '#94a3b8',
  icon: '',
  sort_order: 0
})

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
  () => form.name,
  (val) => {
    if (!slugManualEdit && val) {
      form.slug = slugify(val)
    }
  }
)

const loadData = async () => {
  loading.value = true
  try {
    categories.value = await fetchAdminCategories()
  } catch (e) {
    toast.error(e instanceof Error ? e.message : '加载分类失败')
    categories.value = []
  } finally {
    loading.value = false
  }
}

const resetForm = () => {
  form.name = ''
  form.slug = ''
  form.description = ''
  form.color = '#94a3b8'
  form.icon = ''
  form.sort_order = 0
  editingId.value = null
  slugManualEdit = false
}

const openNew = () => {
  dialogMode.value = 'new'
  resetForm()
  dialogOpen.value = true
}

const openEdit = (cat: AdminCategory) => {
  dialogMode.value = 'edit'
  form.name = getLocalizedStr(cat.name)
  form.slug = cat.slug
  form.description = getLocalizedStr(cat.description)
  form.color = cat.color || '#94a3b8'
  form.icon = cat.icon || ''
  form.sort_order = (cat as unknown as { sort_order?: number }).sort_order ?? 0
  editingId.value = cat.id
  slugManualEdit = true
  dialogOpen.value = true
}

const save = async () => {
  if (!form.name.trim()) {
    toast.error('请输入分类名称')
    return
  }
  saving.value = true
  try {
    const payload = {
      name: form.name,
      slug: form.slug || undefined,
      description: form.description || undefined,
      color: form.color || undefined,
      icon: form.icon || undefined,
      sort_order: form.sort_order
    }
    if (editingId.value) {
      await updateAdminCategory(editingId.value, payload)
      toast.success('更新成功')
    } else {
      await createAdminCategory(payload)
      toast.success('创建成功')
    }
    resetForm()
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
    await deleteAdminCategory(pendingDeleteId.value)
    toast.success('删除成功')
    deleteDialogOpen.value = false
    pendingDeleteId.value = null
    if (editingId.value === pendingDeleteId.value) {
      resetForm()
    }
    await loadData()
  } catch (e) {
    toast.error(e instanceof Error ? e.message : '删除失败')
  }
}

onMounted(() => {
  loadData()
})
</script>

<template>
  <div class="flex flex-col gap-5 p-6">
    <!-- Header + 新建按钮 + 表单 Dialog -->
    <div class="flex flex-wrap items-center justify-between gap-3">
      <div class="flex items-center gap-3">
        <h1 class="text-2xl font-bold tracking-tight">
          分类管理
        </h1>
        <Badge
          variant="secondary"
          class="rounded-[10px] px-3 py-1 bg-stone-100 text-stone-700 border-stone-200"
        >
          共 {{ categories.length }} 个分类
        </Badge>
      </div>

      <Dialog v-model:open="dialogOpen">
        <DialogTrigger as-child>
          <Button
            class="rounded-[12px] h-10 px-5 shadow-sm"
            @click="openNew"
          >
            + 新建分类
          </Button>
        </DialogTrigger>
        <DialogContent class="rounded-[12px] max-w-lg">
          <DialogHeader>
            <DialogTitle>
              {{ dialogMode === 'edit' ? '编辑分类' : '新建分类' }}
            </DialogTitle>
            <DialogDescription>
              分类用于文章的主题组织，支持颜色与图标快速区分。
            </DialogDescription>
          </DialogHeader>
          <div class="flex flex-col gap-4 py-4">
            <div>
              <Label class="mb-1 block text-xs text-muted-foreground">
                名称 <span class="text-destructive">*</span>
              </Label>
              <Input
                v-model="form.name"
                placeholder="分类名称"
                class="h-9 rounded-[10px]"
              />
            </div>
            <div>
              <Label class="mb-1 block text-xs text-muted-foreground">Slug</Label>
              <Input
                v-model="form.slug"
                placeholder="自动生成，可修改"
                class="h-9 rounded-[10px]"
                @input="slugManualEdit = true"
              />
            </div>
            <div>
              <Label class="mb-1 block text-xs text-muted-foreground">描述</Label>
              <Textarea
                v-model="form.description"
                rows="3"
                placeholder="分类描述（可选）"
                class="rounded-[10px] text-sm resize-y"
              />
            </div>
            <div class="grid grid-cols-2 gap-3">
              <div>
                <Label class="mb-1 block text-xs text-muted-foreground">颜色</Label>
                <div class="flex gap-2">
                  <input
                    v-model="form.color"
                    type="color"
                    class="h-9 w-11 rounded-[10px] border border-input bg-background cursor-pointer"
                  >
                  <Input
                    v-model="form.color"
                    class="h-9 rounded-[10px] flex-1 font-mono text-xs"
                  />
                </div>
              </div>
              <div>
                <Label class="mb-1 block text-xs text-muted-foreground">图标</Label>
                <Input
                  v-model="form.icon"
                  placeholder="emoji 或 icon"
                  class="h-9 rounded-[10px]"
                />
              </div>
            </div>
            <div>
              <Label class="mb-1 block text-xs text-muted-foreground">排序号</Label>
              <Input
                v-model.number="form.sort_order"
                type="number"
                class="h-9 rounded-[10px]"
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
              class="rounded-[10px] shadow-sm"
              :disabled="saving"
              @click="save"
            >
              {{ saving ? '保存中...' : (editingId ? '更新' : '保存') }}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>

    <!-- 分类列表：全宽显示（不再有右侧常驻表单列） -->
    <div class="rounded-[12px] border border-border bg-card overflow-hidden">
      <div class="overflow-x-auto">
        <div class="min-w-[700px]">
          <div class="grid grid-cols-[auto,1.2fr,1fr,1.4fr,90px,80px,130px] bg-stone-50/80 border-b border-border text-xs font-medium text-muted-foreground">
            <div class="p-3 w-16">
              ID
            </div>
            <div class="p-3">
              名称
            </div>
            <div class="p-3">
              Slug
            </div>
            <div class="p-3">
              描述
            </div>
            <div class="p-3 text-center">
              文章数
            </div>
            <div class="p-3 text-center">
              排序
            </div>
            <div class="p-3 text-center">
              操作
            </div>
          </div>

          <template v-if="loading">
            <div
              v-for="i in 5"
              :key="`sk-${i}`"
              class="grid grid-cols-[auto,1.2fr,1fr,1.4fr,90px,80px,130px] border-b border-border/50"
            >
              <div class="p-3 w-16">
                <Skeleton class="h-4 w-8 rounded" />
              </div>
              <div class="p-3">
                <Skeleton class="h-5 w-3/4 rounded" />
              </div>
              <div class="p-3">
                <Skeleton class="h-5 w-2/3 rounded" />
              </div>
              <div class="p-3">
                <Skeleton class="h-5 w-full rounded" />
              </div>
              <div class="p-3">
                <Skeleton class="h-4 w-10 rounded mx-auto" />
              </div>
              <div class="p-3">
                <Skeleton class="h-4 w-10 rounded mx-auto" />
              </div>
              <div class="p-3 flex gap-2 justify-center">
                <Skeleton class="h-8 w-14 rounded" /><Skeleton class="h-8 w-14 rounded" />
              </div>
            </div>
          </template>

          <template v-else-if="categories.length === 0">
            <div class="py-20 text-center text-muted-foreground">
              <div class="text-5xl mb-3 opacity-30">
                📁
              </div>
              <div class="text-sm">
                暂无分类，点击右上角「新建分类」创建第一个吧
              </div>
            </div>
          </template>

          <template v-else>
            <div
              v-for="(c, idx) in categories"
              :key="c.id"
              class="grid grid-cols-[auto,1.2fr,1fr,1.4fr,90px,80px,130px] border-b border-border/50 text-sm"
              :class="{ 'bg-stone-50/40': idx % 2 === 1 }"
            >
              <div class="p-3 w-16 text-muted-foreground text-xs">
                #{{ c.id }}
              </div>
              <div class="p-3">
                <div class="flex items-center gap-2">
                  <span
                    class="w-3 h-3 rounded-full inline-block border border-white shadow-sm"
                    :style="{ background: c.color || '#94a3b8' }"
                  />
                  <span class="font-medium">{{ getLocalizedStr(c.name) }}</span>
                  <span
                    v-if="c.icon"
                    class="text-muted-foreground"
                  >{{ c.icon }}</span>
                </div>
              </div>
              <div class="p-3 text-muted-foreground truncate">
                {{ c.slug }}
              </div>
              <div
                class="p-3 text-muted-foreground text-xs truncate"
                :title="getLocalizedStr(c.description)"
              >
                {{ getLocalizedStr(c.description) || '-' }}
              </div>
              <div class="p-3 text-center">
                <Badge
                  variant="secondary"
                  class="rounded-[10px]"
                >
                  {{ c.post_count }}
                </Badge>
              </div>
              <div class="p-3 text-center text-muted-foreground text-xs">
                {{ (c as any).sort_order ?? 0 }}
              </div>
              <div class="p-3 flex items-center justify-center gap-1.5">
                <Button
                  variant="ghost"
                  size="sm"
                  class="h-8 rounded-[10px] text-xs px-3"
                  @click="openEdit(c)"
                >
                  编辑
                </Button>
                <Button
                  variant="ghost"
                  size="sm"
                  class="h-8 rounded-[10px] text-xs px-3 text-destructive hover:text-destructive"
                  @click="confirmDelete(c.id)"
                >
                  删除
                </Button>
              </div>
            </div>
          </template>
        </div>
      </div>
    </div>

    <!-- 删除确认 Dialog -->
    <Dialog v-model:open="deleteDialogOpen">
      <DialogContent class="rounded-[12px] max-w-md">
        <DialogHeader>
          <DialogTitle>确认删除分类</DialogTitle>
          <DialogDescription>
            删除分类不会删除关联文章，但文章将变为未分类状态。此操作不可撤销。
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
