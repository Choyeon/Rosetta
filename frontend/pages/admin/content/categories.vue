<script setup lang="ts">
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
import { Badge } from '~~/components/ui/badge'
import type { AdminColumn as Column } from '~~/types/admin'

definePageMeta({ ssr: false, layout: 'admin' })

const toast = useToast()

const categories = ref<AdminCategory[]>([])
const loading = ref(false)
const saving = ref(false)
const editingId = ref<number | null>(null)

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
  s = s.replace(/[^\w一-龥-]/g, '')
  s = s.replace(/-+/g, '-').replace(/^-|-$/g, '')
  return s
}

let slugManualEdit = false as boolean
watch(
  () => form.name,
  (val) => {
    if (!slugManualEdit && val) {
      form.slug = slugify(val)
    }
  }
)

const columns: Column[] = [
  { key: 'id', title: 'ID', class: 'w-16 text-muted-foreground text-xs' },
  { key: 'name', title: '名称' },
  { key: 'slug', title: 'Slug', class: 'text-muted-foreground' },
  { key: 'description', title: '描述', class: 'max-w-[260px]' },
  { key: 'post_count', title: '文章数', align: 'center', class: 'w-20' },
  { key: 'sort_order', title: '排序', align: 'center', class: 'w-16' }
]

const loadData = async () => {
  loading.value = true
  try {
    categories.value = await fetchAdminCategories()
  } catch {
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
  } catch {
    /* apiFetch 已统一 toast */
  } finally {
    saving.value = false
  }
}

const deleteDialogOpen = ref(false)
const pendingDeleteId = ref<number | null>(null)

function confirmDelete(id: number) {
  pendingDeleteId.value = id
  deleteDialogOpen.value = true
}

async function doDelete() {
  if (pendingDeleteId.value == null) return
  try {
    await deleteAdminCategory(pendingDeleteId.value)
    toast.success('删除成功')
    deleteDialogOpen.value = false
    pendingDeleteId.value = null
    if (editingId.value === pendingDeleteId.value) resetForm()
    await loadData()
  } catch {
    /* apiFetch 已统一 toast */
  }
}

onMounted(() => {
  loadData()
})
</script>

<template>
  <AdminListPage
    title="分类管理"
    description="分类用于文章的主题组织，支持颜色与图标快速区分。"
    :count="categories.length"
  >
    <template #actions>
      <Button
        class="rounded-[12px] h-10 px-5 shadow-sm"
        @click="openNew"
      >
        + 新建分类
      </Button>
    </template>

    <AdminDataTable
      :columns="columns"
      :data="categories"
      :loading="loading"
      row-key="id"
    >
      <template #cell-id="{ row }">
        #{{ row.id }}
      </template>
      <template #cell-name="{ row }">
        <div class="flex items-center gap-2">
          <span
            class="size-3 rounded-full inline-block border border-white shadow-sm"
            :style="{ background: (row as AdminCategory).color || '#94a3b8' }"
          />
          <span class="font-medium">{{ getLocalizedStr((row as AdminCategory).name) }}</span>
          <span
            v-if="(row as AdminCategory).icon"
            class="text-muted-foreground"
          >{{ (row as AdminCategory).icon }}</span>
        </div>
      </template>
      <template #cell-description="{ row }">
        <span
          class="text-muted-foreground text-xs block truncate"
          :title="getLocalizedStr((row as AdminCategory).description)"
        >
          {{ getLocalizedStr((row as AdminCategory).description) || '-' }}
        </span>
      </template>
      <template #cell-post_count="{ row }">
        <Badge variant="secondary">{{ (row as AdminCategory).post_count }}</Badge>
      </template>
      <template #cell-sort_order="{ row }">
        <span class="text-muted-foreground text-xs">{{ (row as AdminCategory).sort_order ?? 0 }}</span>
      </template>
      <template #actions="{ row }">
        <Button
          variant="ghost"
          size="sm"
          class="h-8 rounded-[10px] text-xs px-3"
          @click="openEdit(row as AdminCategory)"
        >
          编辑
        </Button>
        <Button
          variant="ghost"
          size="sm"
          class="h-8 rounded-[10px] text-xs px-3 text-destructive hover:text-destructive"
          @click="confirmDelete((row as AdminCategory).id)"
        >
          删除
        </Button>
      </template>
    </AdminDataTable>

    <!-- 新建 / 编辑 Dialog -->
    <AdminCrudDialog
      v-model:open="dialogOpen"
      :title="dialogMode === 'edit' ? '编辑分类' : '新建分类'"
      :loading="saving"
      :submit-text="editingId ? '更新' : '保存'"
      @submit="save"
    >
      <div class="flex flex-col gap-4">
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
    </AdminCrudDialog>

    <!-- 删除确认 Dialog -->
    <AdminConfirmDialog
      v-model:open="deleteDialogOpen"
      title="确认删除分类"
      description="删除分类不会删除关联文章，但文章将变为未分类状态。此操作不可撤销。"
      confirm-text="确认删除"
      @confirm="doDelete"
    />
  </AdminListPage>
</template>
