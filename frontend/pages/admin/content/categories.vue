<!--
  后台分类管理页（SPA / layout=admin）：分类 CRUD，请求全部走 useAdminManage wrapper 单源。
  硬契约：name/description 以完整四语 dict {zh,en,ja,zh_Hant} 提交（后端 JSON 列依赖该形状）；
  slug 自动派生仅在结果匹配后端 ^[a-z0-9-]+$ 时才填入，含中文则留空交给后端按名称生成；
  失败提示由 apiFetch 统一 toast，页面 catch 内禁止二次弹错（双 toast 是回归）。
-->
<script setup lang="ts">
import { ref, reactive, watch, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import {
  fetchAdminCategories,
  createAdminCategory,
  updateAdminCategory,
  deleteAdminCategory,
  type AdminCategory,
  type AdminTaxonomyPayload
} from '~~/composables/useAdminManage'
import { useToast } from '~~/composables/useToast'
import { Button } from '~~/components/ui/button'
import { Input } from '~~/components/ui/input'
import { Label } from '~~/components/ui/label'
import { Badge } from '~~/components/ui/badge'
import I18nTabsEditor from '~~/components/admin/I18nTabsEditor.vue'
import { getLocalizedStr, normalizeI18nDict, slugify, type I18nDict } from '~~/composables/useAdminI18n'
import type { AdminColumn as Column } from '~~/types/admin'

definePageMeta({ ssr: false, layout: 'admin' })

const { t } = useI18n()
const toast = useToast()

const categories = shallowRef<AdminCategory[]>([])
const loading = ref(false)
const saving = ref(false)
const editingId = ref<number | null>(null)

const dialogOpen = ref(false)
const dialogMode = ref<'new' | 'edit'>('new')

const form = reactive<{
  name: I18nDict
  slug: string
  description: I18nDict
  color: string
  icon: string
}>({
  name: { zh: '', en: '', ja: '', zh_Hant: '' },
  slug: '',
  description: { zh: '', en: '', ja: '', zh_Hant: '' },
  color: '#94a3b8',
  icon: ''
})

/** 后端 slug 校验 ^[a-z0-9-]+$；slugify 可能保留中文，仅当结果合法才自动填充，否则留空由后端按中文名生成 */
const SLUG_PATTERN = /^[a-z0-9-]+$/
let slugManualEdit = false as boolean
watch(
  () => form.name,
  (val) => {
    const nameStr = getLocalizedStr(val)
    if (!slugManualEdit && nameStr) {
      const s = slugify(nameStr)
      form.slug = SLUG_PATTERN.test(s) ? s : ''
    }
  },
  { deep: true }
)

const columns: Column[] = [
  { key: 'id', title: 'ID', class: 'w-16 text-muted-foreground text-xs' },
  { key: 'name', title: '名称' },
  { key: 'slug', title: 'Slug', class: 'text-muted-foreground' },
  { key: 'description', title: '描述', class: 'max-w-[260px]' },
  { key: 'post_count', title: '文章数', align: 'center', class: 'w-20' }
]

const loadData = async () => {
  loading.value = true
  try {
    categories.value = await fetchAdminCategories()
  } catch (err) {
    // 失败提示由 apiFetch 统一 toast，此处仅做状态兜底
    console.error('load categories error', err)
    categories.value = []
  } finally {
    loading.value = false
  }
}

const resetForm = () => {
  form.name = { zh: '', en: '', ja: '', zh_Hant: '' }
  form.slug = ''
  form.description = { zh: '', en: '', ja: '', zh_Hant: '' }
  form.color = '#94a3b8'
  form.icon = ''
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
  form.name = normalizeI18nDict(cat.name)
  form.slug = cat.slug
  form.description = normalizeI18nDict(cat.description)
  form.color = cat.color || '#94a3b8'
  form.icon = cat.icon || ''
  editingId.value = cat.id
  slugManualEdit = true
  dialogOpen.value = true
}

const save = async () => {
  if (!getLocalizedStr(form.name).trim()) {
    toast.error('请输入分类名称')
    return
  }
  if (form.slug && !SLUG_PATTERN.test(form.slug)) {
    toast.error('Slug 只能包含小写字母、数字和连字符（-）')
    return
  }
  if (form.color && !/^#[0-9a-fA-F]{6}$/.test(form.color)) {
    toast.error('颜色需为 6 位十六进制值，如 #3B82F6')
    return
  }
  saving.value = true
  try {
    const payload: AdminTaxonomyPayload = {
      name: form.name,
      slug: form.slug || undefined,
      description: form.description,
      color: form.color || undefined,
      icon: form.icon || undefined
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
  } catch (err) {
    // 失败提示由 apiFetch 统一 toast，此处不重复弹错
    console.error('save category error', err)
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
  const id = pendingDeleteId.value
  if (id == null) return
  // 异常一律外抛：AdminConfirmDialog 据此保持打开，错误提示由 apiFetch 统一 toast
  await deleteAdminCategory(id)
  toast.success('删除成功')
  pendingDeleteId.value = null
  if (editingId.value === id) resetForm()
  await loadData()
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
          <DynamicIcon
            v-if="(row as AdminCategory).icon"
            :icon="(row as AdminCategory).icon!"
            class="size-4 text-muted-foreground shrink-0"
          />
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
        <Badge variant="secondary">
          {{ (row as AdminCategory).post_count }}
        </Badge>
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
        <I18nTabsEditor
          v-model="form.name"
          kind="text"
          label="名称"
          required
        />
        <div>
          <Label
            for="category-form-slug"
            class="mb-1 block text-xs text-muted-foreground"
          >Slug</Label>
          <Input
            id="category-form-slug"
            v-model="form.slug"
            placeholder="自动生成，可修改"
            class="h-9 rounded-[10px]"
            @input="slugManualEdit = true"
          />
        </div>
        <I18nTabsEditor
          v-model="form.description"
          kind="textarea"
          label="描述"
          :rows="3"
        />
        <div class="grid grid-cols-2 gap-3">
          <div>
            <Label
              for="category-form-color"
              class="mb-1 block text-xs text-muted-foreground"
            >颜色</Label>
            <div class="flex gap-2">
              <input
                id="category-form-color"
                v-model="form.color"
                type="color"
                class="h-9 w-11 rounded-[10px] border border-input bg-background cursor-pointer"
              >
              <Input
                v-model="form.color"
                :aria-label="t('admin.categories.fColor')"
                class="h-9 rounded-[10px] flex-1 font-mono text-xs"
              />
            </div>
          </div>
          <div>
            <Label
              for="category-form-icon"
              class="mb-1 block text-xs text-muted-foreground"
            >图标</Label>
            <div class="flex gap-2">
              <div class="size-9 shrink-0 rounded-[10px] border border-border flex items-center justify-center bg-muted/30">
                <DynamicIcon
                  v-if="form.icon"
                  :icon="form.icon"
                  class="size-5 text-foreground"
                />
                <span
                  v-else
                  class="text-xs text-muted-foreground"
                >—</span>
              </div>
              <Input
                id="category-form-icon"
                v-model="form.icon"
                placeholder="heroicons:code-bracket 或 emoji"
                class="h-9 rounded-[10px] flex-1 font-mono text-xs"
              />
            </div>
          </div>
        </div>
      </div>
    </AdminCrudDialog>

    <!-- 删除确认 Dialog -->
    <AdminConfirmDialog
      v-model:open="deleteDialogOpen"
      title="确认删除分类"
      description="删除分类不会删除关联文章，但文章将变为未分类状态。此操作不可撤销。"
      confirm-text="确认删除"
      :on-confirm="doDelete"
    />
  </AdminListPage>
</template>
