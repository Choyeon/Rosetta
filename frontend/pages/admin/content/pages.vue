<script setup lang="ts">
import { ref, reactive, watch, onMounted } from 'vue'
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
import { Label } from '~~/components/ui/label'
import { Badge } from '~~/components/ui/badge'
import { Switch } from '~~/components/ui/switch'
import { Pin } from '@lucide/vue'
import MarkdownEditor from '~~/components/admin/MarkdownEditor.vue'
import { getLocalizedStr, slugify } from '~~/composables/useAdminI18n'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue
} from '~~/components/ui/select'
import type { AdminColumn as Column } from '~~/types/admin'

definePageMeta({ ssr: false, layout: 'admin' })

const toast = useToast()

const pages = shallowRef<AdminPage[]>([])
const loading = ref(false)
const total = ref(0)
const page = ref(1)
const pageSize = ref(20)

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

let slugManualEdit = false as boolean
watch(
  () => form.title,
  (val) => {
    if (!slugManualEdit && val) {
      form.slug = slugify(val)
    }
  }
)

const columns: Column[] = [
  { key: 'slug', title: 'Slug', class: 'font-mono text-xs text-muted-foreground' },
  { key: 'title', title: '标题', class: 'font-medium' },
  { key: 'status', title: '状态', class: 'w-24' },
  { key: 'is_pinned', title: '置顶', align: 'center', class: 'w-16' },
  { key: 'updated_at', title: '更新时间', class: 'w-44 text-xs text-muted-foreground' }
]

const loadData = async () => {
  loading.value = true
  try {
    const res = await fetchAdminPages({
      page: page.value,
      page_size: pageSize.value,
      // 关于页内容走站点设置 basic.about_page_html（直接 HTML 编辑）
      // 留言板是 pages/guestbook.vue 固定页面
      // 两者都不在"独立页面"管理列表中显示，避免混淆
      exclude_slugs: ['about', 'guestbook']
    })
    pages.value = res.items || []
    total.value = res.total || pages.value.length
  } catch {
    pages.value = []
    total.value = 0
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
  } catch {
    /* apiFetch 已统一 toast */
  } finally {
    saving.value = false
  }
}

function confirmDelete(id: number) {
  pendingDeleteId.value = id
  deleteDialogOpen.value = true
}

async function doDelete() {
  if (pendingDeleteId.value == null) return
  try {
    await deleteAdminPage(pendingDeleteId.value)
    toast.success('删除成功')
    deleteDialogOpen.value = false
    pendingDeleteId.value = null
    await loadData()
  } catch {
    /* apiFetch 已统一 toast */
  }
}

watch([page, pageSize], () => {
  loadData()
})

onMounted(() => {
  loadData()
})
</script>

<template>
  <AdminListPage
    title="独立页面"
    description="独立页面用于创建关于、联系等非常规文章的页面。"
    :count="total"
  >
    <template #actions>
      <Button
        class="rounded-[12px] h-10 px-5 shadow-sm"
        @click="openNew"
      >
        + 新建页面
      </Button>
    </template>

    <AdminDataTable
      :columns="columns"
      :data="pages"
      :loading="loading"
      row-key="id"
    >
      <template #cell-slug="{ row }">
        /{{ (row as AdminPage).slug }}
      </template>
      <template #cell-title="{ row }">
        <span
          class="block truncate"
          :title="getLocalizedStr((row as AdminPage).title)"
        >{{ getLocalizedStr((row as AdminPage).title) }}</span>
      </template>
      <template #cell-status="{ row }">
        <Badge
          class="rounded-[10px] font-normal"
          :class="(row as AdminPage).status === 'published'
            ? 'bg-success-muted text-success-muted-foreground'
            : 'bg-warning-muted text-warning-muted-foreground'"
        >
          {{ (row as AdminPage).status === 'published' ? '已发布' : '草稿' }}
        </Badge>
      </template>
      <template #cell-is_pinned="{ row }">
        <Pin
          v-if="(row as AdminPage).is_pinned"
          class="size-3.5 text-amber-500"
        />
      </template>
      <template #cell-updated_at="{ row }">
        {{ formatAdminDateTime((row as AdminPage).updated_at ?? (row as AdminPage).created_at) }}
      </template>
      <template #actions="{ row }">
        <Button
          variant="ghost"
          size="sm"
          class="h-8 rounded-[10px] text-xs px-3"
          @click="openEdit(row as AdminPage)"
        >
          编辑
        </Button>
        <Button
          variant="ghost"
          size="sm"
          class="h-8 rounded-[10px] text-xs px-3 text-destructive hover:text-destructive"
          @click="confirmDelete((row as AdminPage).id)"
        >
          删除
        </Button>
      </template>
    </AdminDataTable>

    <template #pagination>
      <AdminPagination
        v-model:page="page"
        v-model:page-size="pageSize"
        :total="total"
      />
    </template>

    <AdminCrudDialog
      v-model:open="dialogOpen"
      :title="dialogMode === 'edit' ? '编辑页面' : '新建页面'"
      :loading="saving"
      :submit-text="dialogMode === 'edit' ? '更新' : '保存'"
      @submit="save"
    >
      <div class="flex flex-col gap-4 max-h-[70vh] overflow-y-auto pr-1">
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
          <Label class="mb-1 block text-xs text-muted-foreground">内容</Label>
          <MarkdownEditor
            v-model="form.content"
            placeholder="页面内容..."
          />
        </div>
      </div>
    </AdminCrudDialog>

    <AdminConfirmDialog
      v-model:open="deleteDialogOpen"
      title="确认删除页面"
      description="此操作不可撤销，确定要删除这个页面吗？"
      confirm-text="确认删除"
      @confirm="doDelete"
    />
  </AdminListPage>
</template>
