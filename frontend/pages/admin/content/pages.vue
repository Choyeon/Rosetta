<!--
  独立页面（Page）管理列表：服务端分页 + CRUD 弹窗，请求走 useAdminManage wrapper 单源。
  硬契约：exclude_slugs=[about,guestbook] 不可移除——关于页正文的真源是站点设置
  basic.about_page_html（专用编辑入口 /admin/content/about）、留言板是固定路由页，
  混进列表会造成双编辑入口；后端 PageCreate/PageUpdate 是 extra=forbid，
  请求体只能带 slug/title/status/content 四键，多一个字段即 422；title/content 提交完整 i18n dict；
  slug 必填，校验用 CONTENT_SLUG_PATTERN（与后端同口径，允许中文）。
-->
<script setup lang="ts">
import { ref, reactive, watch, onMounted } from 'vue'
import { FileStack, Plus, Pencil, Trash2 } from '@lucide/vue'
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
import { Badge } from '~~/components/ui/badge'
import I18nTabsEditor from '~~/components/admin/I18nTabsEditor.vue'
import AdminRowActions from '~~/components/admin/AdminRowActions.vue'
import AdminFormField from '~~/components/admin/AdminFormField.vue'
import {
  EMPTY_I18N_DICT,
  getLocalizedStr,
  normalizeI18nDict,
  toI18nPayload,
  slugify,
  CONTENT_SLUG_PATTERN
} from '~~/composables/useAdminI18n'
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
  title: { ...EMPTY_I18N_DICT },
  status: 'draft' as 'draft' | 'published',
  content: { ...EMPTY_I18N_DICT }
})

const editingId = ref<number | null>(null)

/** slugify 结果与用户手填 slug 统一用 CONTENT_SLUG_PATTERN 校验（与后端同口径，允许中文） */
let slugManualEdit = false as boolean
watch(
  () => form.title,
  (val) => {
    if (!slugManualEdit && getLocalizedStr(val)) {
      const s = slugify(getLocalizedStr(val))
      form.slug = CONTENT_SLUG_PATTERN.test(s) ? s : ''
    }
  },
  { deep: true }
)

const columns: Column[] = [
  { key: 'slug', title: 'Slug', class: 'font-mono text-xs text-muted-foreground' },
  { key: 'title', title: '标题', class: 'font-medium' },
  { key: 'status', title: '状态', class: 'w-24' },
  { key: 'updated_at', title: '更新时间', class: 'w-44 text-xs text-muted-foreground' }
]

const loadData = async () => {
  loading.value = true
  try {
    const res = await fetchAdminPages({
      page: page.value,
      page_size: pageSize.value,
      // 关于页内容走 basic.about_page_html（专用编辑器 /admin/content/about）
      // 留言板是 pages/guestbook.vue 固定页面
      // 两者都不在"独立页面"管理列表中显示，避免混淆
      exclude_slugs: ['about', 'guestbook']
    })
    pages.value = res.items || []
    total.value = res.total || pages.value.length
    // 删除/筛选后当前页可能越界：夹回最后一页
    const maxPage = Math.max(1, Math.ceil((total.value ?? 0) / pageSize.value))
    if (page.value > maxPage && maxPage !== page.value) {
      page.value = maxPage
      return
    }
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
  form.title = { ...EMPTY_I18N_DICT }
  form.status = 'draft'
  form.content = { ...EMPTY_I18N_DICT }
  slugManualEdit = false
  dialogOpen.value = true
}

const openEdit = (p: AdminPage) => {
  dialogMode.value = 'edit'
  editingId.value = p.id
  form.slug = p.slug
  // 保留后端完整多语言 dict，避免保存时把其他语言内容抹掉
  form.title = normalizeI18nDict(p.title)
  form.status = p.status
  form.content = normalizeI18nDict(p.content)
  slugManualEdit = true
  dialogOpen.value = true
}

const save = async () => {
  if (!form.slug.trim()) {
    toast.error('请输入 slug')
    return
  }
  if (!CONTENT_SLUG_PATTERN.test(form.slug.trim())) {
    toast.error('Slug 只能包含小写字母、数字、下划线、中文和连字符（-）')
    return
  }
  const titlePayload = toI18nPayload(form.title)
  if (!titlePayload) {
    toast.error('请输入标题（至少一种语言）')
    return
  }
  saving.value = true
  try {
    // PageCreate/PageUpdate 为 extra=forbid：body 只能带 slug/title/status/content
    const payload: Record<string, unknown> = {
      slug: form.slug.trim(),
      title: titlePayload,
      status: form.status,
      content: toI18nPayload(form.content) ?? {}
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
  const id = pendingDeleteId.value
  if (id == null) return
  const resp = await deleteAdminPage(id)
  // 用后端提示语：删除现在是"移入回收站"而不是物理删除，写死「删除成功」会藏掉可恢复这件事
  toast.success(resp?.message || '删除成功')
  pendingDeleteId.value = null
  // 删掉当前页最后一条时回退一页（watch 会自动触发重新加载）
  if (pages.value.length <= 1 && page.value > 1) {
    page.value -= 1
  } else {
    await loadData()
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
    :icon="FileStack"
    description="独立页面用于创建关于、联系等非常规文章的页面。"
    :count="total"
  >
    <template #actions>
      <Button
        size="sm"
        class="shadow-sm"
        @click="openNew"
      >
        <Plus data-icon="inline-start" />
        新建页面
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
      <template #cell-updated_at="{ row }">
        {{ formatAdminDateTime((row as AdminPage).updated_at ?? (row as AdminPage).created_at) }}
      </template>
      <template #actions="{ row }">
        <AdminRowActions
          :actions="[
            { key: 'edit', label: '编辑页面', icon: Pencil, onClick: () => openEdit(row as AdminPage) },
            { key: 'delete', label: '删除页面', icon: Trash2, destructive: true, onClick: () => confirmDelete((row as AdminPage).id) }
          ]"
        />
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
      description="独立页面用于关于、隐私政策等静态内容，拥有独立 URL。"
      :icon="FileStack"
      :loading="saving"
      :submit-text="dialogMode === 'edit' ? '更新' : '保存'"
      @submit="save"
    >
      <div class="flex flex-col gap-5">
        <I18nTabsEditor
          v-model="form.title"
          kind="text"
          label="标题"
          required
          placeholder="页面标题"
          flat
        />
        <div class="grid grid-cols-1 gap-4 sm:grid-cols-2">
          <AdminFormField
            label="Slug"
            for="page-form-slug"
            required
            hint="页面地址为 /<slug>，例如 /about。"
          >
            <Input
              id="page-form-slug"
              v-model="form.slug"
              placeholder="about"
              class="h-10 rounded-[10px] font-mono text-sm"
              @input="slugManualEdit = true"
            />
          </AdminFormField>
          <AdminFormField
            label="状态"
            for="page-form-status"
          >
            <Select v-model="form.status">
              <SelectTrigger
                id="page-form-status"
                class="h-10 rounded-[10px]"
              >
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
          </AdminFormField>
        </div>
        <I18nTabsEditor
          v-model="form.content"
          kind="markdown"
          label="内容"
          placeholder="页面内容..."
          flat
        />
      </div>
    </AdminCrudDialog>

    <AdminConfirmDialog
      v-model:open="deleteDialogOpen"
      title="确认删除页面"
      description="删除后页面会移入回收站，30 天内可在「回收站」页恢复；到期后自动清除。"
      confirm-text="确认删除"
      :on-confirm="doDelete"
    />
  </AdminListPage>
</template>
