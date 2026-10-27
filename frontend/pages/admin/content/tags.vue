<!--
  标签管理页：标签墙 + 客户端搜索过滤 + CRUD 弹窗（颜色/图标/启用开关）。
  硬契约：fetchAdminTags 一次拉全量、搜索是纯客户端过滤（slug 校验与分类同套
  CONTENT_SLUG_PATTERN——允许中文，留空时由后端按名称生成）；name 提交完整四语 dict；
  图标以文本插值渲染（{{ t.icon }}），禁止改回 v-html——短字符串落库脏数据换个消费点就中招。
-->
<script setup lang="ts">
import { ref, reactive, watch, computed, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import {
  fetchAdminTags,
  createAdminTag,
  updateAdminTag,
  deleteAdminTag,
  type AdminTag,
  type AdminTaxonomyPayload
} from '~~/composables/useAdminManage'
import { useToast } from '~~/composables/useToast'
import { Button } from '~~/components/ui/button'
import { Input } from '~~/components/ui/input'
import { Label } from '~~/components/ui/label'
import { Switch } from '~~/components/ui/switch'
import I18nTabsEditor from '~~/components/admin/I18nTabsEditor.vue'
import AdminFormField from '~~/components/admin/AdminFormField.vue'
import AdminRowActions from '~~/components/admin/AdminRowActions.vue'
import { EMPTY_I18N_DICT, getLocalizedStr, normalizeI18nDict, slugify, CONTENT_SLUG_PATTERN, type I18nDict } from '~~/composables/useAdminI18n'
import type { AdminColumn as Column } from '~~/types/admin'
import { Search, Plus, Pencil, Trash2, Tag, Tags } from '@lucide/vue'

definePageMeta({ ssr: false, layout: 'admin' })

const { t: $_t } = useI18n()
const toast = useToast()

const tags = shallowRef<AdminTag[]>([])
const loading = ref(false)
const searchQuery = ref('')
const dialogOpen = ref(false)
const dialogMode = ref<'new' | 'edit'>('new')
const saving = ref(false)

const deleteDialogOpen = ref(false)
const pendingDeleteId = ref<number | null>(null)

const form = reactive<{
  name: I18nDict
  slug: string
  color: string
  icon: string
  is_active: boolean
}>({
  name: { ...EMPTY_I18N_DICT },
  slug: '',
  color: '#0EA5E9',
  icon: '',
  is_active: true
})

const editingId = ref<number | null>(null)

/** slugify 结果与用户手填 slug 统一用 CONTENT_SLUG_PATTERN 校验（与后端同口径，允许中文） */
let slugManualEdit = false as boolean
watch(
  () => form.name,
  (val) => {
    const nameZh = getLocalizedStr(val)
    if (!slugManualEdit && nameZh) {
      const s = slugify(nameZh)
      form.slug = CONTENT_SLUG_PATTERN.test(s) ? s : ''
    }
  },
  { deep: true }
)

const filteredTags = computed(() => {
  const q = searchQuery.value.trim().toLowerCase()
  if (!q) return tags.value
  return tags.value.filter(t =>
    getLocalizedStr(t.name).toLowerCase().includes(q)
    || t.slug.toLowerCase().includes(q)
  )
})

/** 标签没配颜色时回落到主题主色，避免写死十六进制在换调色板后不跟随 */
const tagColor = (t: AdminTag) => t.color || 'hsl(var(--primary))'

const columns: Column[] = [
  { key: 'name', title: '名称' },
  { key: 'slug', title: 'Slug', class: 'w-56 text-muted-foreground font-mono text-xs' },
  { key: 'post_count', title: '文章数', align: 'center', class: 'w-24' },
  { key: 'is_active', title: '状态', align: 'center', class: 'w-24' }
]

const loadData = async () => {
  loading.value = true
  try {
    tags.value = await fetchAdminTags()
  } catch (err) {
    // 失败提示由 apiFetch 统一 toast，此处仅做状态兜底
    console.error('load tags error', err)
    tags.value = []
  } finally {
    loading.value = false
  }
}

const openNew = () => {
  dialogMode.value = 'new'
  editingId.value = null
  form.name = { ...EMPTY_I18N_DICT }
  form.slug = ''
  form.color = '#0EA5E9'
  form.icon = ''
  form.is_active = true
  slugManualEdit = false
  dialogOpen.value = true
}

const openEdit = (t: AdminTag) => {
  dialogMode.value = 'edit'
  editingId.value = t.id
  form.name = normalizeI18nDict(t.name)
  form.slug = t.slug
  form.color = t.color || '#0EA5E9'
  form.icon = t.icon || ''
  form.is_active = t.is_active
  slugManualEdit = true
  dialogOpen.value = true
}

const save = async () => {
  if (!getLocalizedStr(form.name).trim()) {
    toast.error('请输入标签名称')
    return
  }
  if (form.slug && !CONTENT_SLUG_PATTERN.test(form.slug)) {
    toast.error('Slug 只能包含小写字母、数字、下划线、中文和连字符（-）')
    return
  }
  if (form.color && !/^#[0-9a-fA-F]{6}$/.test(form.color)) {
    toast.error('颜色需为 6 位十六进制值，如 #0EA5E9')
    return
  }
  saving.value = true
  try {
    const payload: AdminTaxonomyPayload = {
      name: form.name,
      slug: form.slug || undefined,
      color: form.color || undefined,
      icon: form.icon || undefined,
      is_active: form.is_active
    }
    if (dialogMode.value === 'edit' && editingId.value) {
      await updateAdminTag(editingId.value, payload)
      toast.success('更新成功')
    } else {
      await createAdminTag(payload)
      toast.success('创建成功')
    }
    dialogOpen.value = false
    await loadData()
  } catch (err) {
    // 失败提示由 apiFetch 统一 toast，此处不重复弹错
    console.error('save tag error', err)
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
  await deleteAdminTag(id)
  toast.success('删除成功')
  pendingDeleteId.value = null
  if (editingId.value === id && !dialogOpen.value) {
    editingId.value = null
  }
  await loadData()
}

onMounted(() => {
  loadData()
})
</script>

<template>
  <AdminListPage
    title="标签管理"
    :icon="Tags"
    description="标签可用于文章的快速分类与搜索聚合。"
    :count="tags.length"
  >
    <template #actions>
      <Button
        size="sm"
        class="shadow-sm"
        @click="openNew"
      >
        <Plus data-icon="inline-start" />
        新建标签
      </Button>
    </template>

    <template #toolbar>
      <div class="relative max-w-sm">
        <Search class="absolute left-3 top-1/2 -translate-y-1/2 size-4 text-muted-foreground pointer-events-none" />
        <Input
          v-model="searchQuery"
          :aria-label="$_t('common.search')"
          placeholder="搜索标签名称或 slug..."
          class="h-10 rounded-[12px] pl-9"
        />
      </div>
    </template>

    <AdminDataTable
      :columns="columns"
      :data="filteredTags"
      :loading="loading"
      row-key="id"
    >
      <template #cell-name="{ row }">
        <div class="flex min-w-0 items-center gap-2">
          <span
            class="size-2.5 shrink-0 rounded-full"
            :style="{ background: tagColor(row as AdminTag) }"
          />
          <span class="truncate font-medium">{{ getLocalizedStr((row as AdminTag).name) }}</span>
          <span
            v-if="(row as AdminTag).icon"
            class="shrink-0 text-xs"
          >{{ (row as AdminTag).icon }}</span>
        </div>
      </template>
      <template #cell-slug="{ row }">
        <code class="text-xs text-muted-foreground">/{{ (row as AdminTag).slug }}</code>
      </template>
      <template #cell-post_count="{ row }">
        <Badge variant="secondary">
          {{ (row as AdminTag).post_count }}
        </Badge>
      </template>
      <template #cell-is_active="{ row }">
        <Badge
          class="rounded-[10px] font-normal whitespace-nowrap"
          :class="(row as AdminTag).is_active
            ? 'bg-success-muted text-success-muted-foreground'
            : 'bg-muted text-muted-foreground'"
        >
          {{ (row as AdminTag).is_active ? '启用' : '停用' }}
        </Badge>
      </template>
      <template #actions="{ row }">
        <AdminRowActions
          :actions="[
            { key: 'edit', label: '编辑标签', icon: Pencil, onClick: () => openEdit(row as AdminTag) },
            { key: 'delete', label: '删除标签', icon: Trash2, destructive: true, onClick: () => confirmDelete((row as AdminTag).id) }
          ]"
        />
      </template>
      <template #empty>
        <div class="flex flex-col items-center justify-center gap-2 text-muted-foreground">
          <Tag class="size-8" />
          <span class="text-sm">{{ searchQuery ? '无匹配的标签' : '暂无标签，点击右上角「新建标签」创建吧' }}</span>
        </div>
      </template>
    </AdminDataTable>

    <AdminCrudDialog
      v-model:open="dialogOpen"
      :title="dialogMode === 'edit' ? '编辑标签' : '新建标签'"
      description="标签用于跨分类聚合，颜色会显示在文章卡片的标签胶囊上。"
      :icon="Tags"
      :loading="saving"
      :submit-text="dialogMode === 'edit' ? '更新' : '保存'"
      @submit="save"
    >
      <div class="flex flex-col gap-5">
        <I18nTabsEditor
          v-model="form.name"
          kind="text"
          label="名称"
          required
          flat
        />
        <AdminFormField
          label="Slug"
          for="tag-form-slug"
          hint="用于标签页地址 /tags/<slug>；留空时按名称自动生成。"
        >
          <Input
            id="tag-form-slug"
            v-model="form.slug"
            placeholder="auto-generated-slug"
            class="h-10 rounded-[10px] font-mono text-sm"
            @input="slugManualEdit = true"
          />
        </AdminFormField>
        <div class="grid grid-cols-1 gap-4 sm:grid-cols-2">
          <AdminFormField
            label="颜色"
            for="tag-form-color"
          >
            <div class="flex gap-2">
              <input
                id="tag-form-color"
                v-model="form.color"
                type="color"
                class="h-10 w-12 shrink-0 rounded-[10px] border border-input bg-background cursor-pointer"
              >
              <Input
                v-model="form.color"
                :aria-label="$_t('admin.categories.fColor')"
                class="h-10 flex-1 rounded-[10px] font-mono text-xs"
              />
            </div>
          </AdminFormField>
          <AdminFormField
            label="图标"
            for="tag-form-icon"
            hint="支持 emoji 或图标名。"
          >
            <Input
              id="tag-form-icon"
              v-model="form.icon"
              placeholder="emoji 或 icon"
              class="h-10 rounded-[10px]"
            />
          </AdminFormField>
        </div>
        <div class="flex items-center justify-between gap-4 rounded-[12px] border border-border bg-muted/20 px-4 py-3">
          <div>
            <Label
              for="tag-form-active"
              class="text-sm font-medium"
            >启用状态</Label>
            <div class="text-xs text-muted-foreground mt-0.5">
              关闭后标签不再显示在前台
            </div>
          </div>
          <Switch
            id="tag-form-active"
            v-model="form.is_active"
          />
        </div>
      </div>
    </AdminCrudDialog>

    <AdminConfirmDialog
      v-model:open="deleteDialogOpen"
      title="确认删除标签"
      description="删除标签不会删除关联文章，只是解除文章与该标签的关联。此操作不可撤销。"
      confirm-text="确认删除"
      :on-confirm="doDelete"
    />
  </AdminListPage>
</template>
