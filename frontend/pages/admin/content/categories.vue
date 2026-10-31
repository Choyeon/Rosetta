<!--
  后台分类管理页（SPA / layout=admin）：分类 CRUD，请求全部走 useAdminManage wrapper 单源。
  硬契约：name/description 以完整四语 dict {zh,en,ja,zh_Hant} 提交（后端 JSON 列依赖该形状）；
  slug 自动派生与手填校验共用 CONTENT_SLUG_PATTERN（镜像后端，允许 CJK）；留空时由后端按名称生成；
  is_active 是后端 GET /categories、sitemap 投递面与站点统计的真实强制点（关闭即从公开列表消失，
  但直接 URL 与文章上的分类链接保持可用），列表数据源因此必须带 ?all=true，否则停用是单向按钮；
  封面图（Category.cover_image）走"上传→站内 URL"，提交时始终带这个键：空串归 null 才是
  "清掉封面"，省略键在 PUT 的 exclude_unset 语义下等于"不改它"（清除按钮会点了没反应）；
  层级（Category.parent_id）同一条增量口径：下拉的"顶级分类"提交 null（不是省略键），
  候选必须排除自己与自己的全部后代——选中后代在后端是 400，让运营者撞那次 400 等于把
  环的判定推给服务端再靠 toast 解释；列表按"父在前、子缩进"的深度序渲染，且库里躺着悬空
  parent_id 或环时那些行一律按顶级落进列表（少一行就等于那条分类再也改不动）；
  失败提示由 apiFetch 统一 toast，页面 catch 内禁止二次弹错（双 toast 是回归）。
-->
<script setup lang="ts">
import { ref, reactive, watch, onMounted } from 'vue'
import { FolderTree, Plus, Pencil, Trash2, Image as ImageIcon, CornerDownRight } from '@lucide/vue'
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
import { useMediaUploadCover } from '~~/composables/useMedia'
import { buildCategoryTree, categoryDescendantIds } from '~~/lib/category-tree'
import { Button } from '~~/components/ui/button'
import { Input } from '~~/components/ui/input'
import AdminFormField from '~~/components/admin/AdminFormField.vue'
import { Badge } from '~~/components/ui/badge'
import { Label } from '~~/components/ui/label'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '~~/components/ui/select'
import { Switch } from '~~/components/ui/switch'
import I18nTabsEditor from '~~/components/admin/I18nTabsEditor.vue'
import AdminRowActions from '~~/components/admin/AdminRowActions.vue'
import { EMPTY_I18N_DICT, getLocalizedStr, normalizeI18nDict, slugify, CONTENT_SLUG_PATTERN, type I18nDict } from '~~/composables/useAdminI18n'
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
  cover_image: string
  parent_id: number | null
  is_active: boolean
}>({
  name: { ...EMPTY_I18N_DICT },
  slug: '',
  description: { ...EMPTY_I18N_DICT },
  color: '#94a3b8',
  icon: '',
  cover_image: '',
  parent_id: null,
  is_active: true
})

const coverInputRef = ref<HTMLInputElement | null>(null)
const coverUploading = ref(false)

/** slugify 结果与用户手填 slug 统一用 CONTENT_SLUG_PATTERN 校验（与后端同口径，允许中文） */
let slugManualEdit = false as boolean
watch(
  () => form.name,
  (val) => {
    const nameStr = getLocalizedStr(val)
    if (!slugManualEdit && nameStr) {
      const s = slugify(nameStr)
      form.slug = CONTENT_SLUG_PATTERN.test(s) ? s : ''
    }
  },
  { deep: true }
)

const columns: Column[] = [
  { key: 'id', title: 'ID', class: 'w-16 text-muted-foreground text-xs' },
  { key: 'name', title: '名称' },
  { key: 'slug', title: 'Slug', class: 'text-muted-foreground' },
  { key: 'description', title: '描述', class: 'max-w-[260px]' },
  { key: 'post_count', title: '文章数', align: 'center', class: 'w-20' },
  { key: 'is_active', title: '状态', align: 'center', class: 'w-24' }
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

/**
 * 列表按「父在前、子紧随并缩进」的深度序渲染。数据源仍是一条条真实的分类行
 * （`AdminDataTable` 的 `rowKey="id"` 与各插槽的 `row as AdminCategory` 都不变），
 * 缩进靠 id → depth 的映射查，不把 `{item, depth}` 包装塞进表格。
 * 悬空父级 / 自指 / 环上的行由 `buildCategoryTree` 兜成顶级行，一条都不会从列表里消失。
 */
const treeEntries = computed(() => buildCategoryTree(categories.value))
const categoryRows = computed(() => treeEntries.value.map(entry => entry.item))
const depthById = computed(() => {
  const map = new Map<string, number>()
  for (const entry of treeEntries.value) map.set(String(entry.item.id), entry.depth)
  return map
})
const indentOf = (cat: AdminCategory): number => depthById.value.get(String(cat.id)) ?? 0

/**
 * 父级候选排除自己与自己的全部后代：选中后代在后端是 400（会成环），
 * 而把环的判定留给服务端 + toast 等于让运营者反复猜"为什么改不动"。
 */
const parentOptions = computed(() => {
  const excluded = categoryDescendantIds(categories.value, editingId.value)
  const selfKey = editingId.value == null ? '' : String(editingId.value)
  return categories.value.filter((cat) => {
    const key = String(cat.id)
    return key !== selfKey && !excluded.has(key)
  })
})

/**
 * 父分类只认"候选里真实存在的项"：库里躺着悬空 parent_id（父级已删但缓存还是旧形状）时，
 * Select 认不出这个值，回填成它会让每次 PUT 都提交一个不存在的父级并撞 400。
 * 归成顶级是唯一安全解——显示与提交同口径，也正好是后端 SET NULL 想要的状态。
 */
const normalizeParentId = (raw: unknown): number | null => {
  const key = raw == null ? '' : String(raw)
  if (!key) return null
  const hit = parentOptions.value.find(cat => String(cat.id) === key)
  return hit ? Number(hit.id) : null
}

/**
 * 封面只走"上传→拿回站内 URL"，不提供手填地址的输入框：
 * 这个值最终会成为访客页面上 `<img src>` 的一部分，让自由文本进来就多一个注入面。
 */
const handleCoverUpload = async (e: Event) => {
  const input = e.target as HTMLInputElement
  const file = input.files?.[0]
  if (!file) return
  coverUploading.value = true
  try {
    const result = await useMediaUploadCover(file)
    if (result?.url) {
      form.cover_image = result.url
      toast.success('封面上传成功')
    } else {
      toast.error('封面上传失败')
    }
  } catch (err) {
    // 失败提示由 apiFetch 统一 toast，此处不重复弹错
    console.error('[categories] handleCoverUpload failed:', err)
  } finally {
    coverUploading.value = false
    input.value = ''
  }
}

const clearCover = () => {
  form.cover_image = ''
}

const resetForm = () => {
  form.name = { ...EMPTY_I18N_DICT }
  form.slug = ''
  form.description = { ...EMPTY_I18N_DICT }
  form.color = '#94a3b8'
  form.icon = ''
  form.cover_image = ''
  form.parent_id = null
  form.is_active = true
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
  // 先落 editingId：parentOptions 的「排除自己与后代」依赖它，回填必须按同一份候选判定
  editingId.value = cat.id
  form.name = normalizeI18nDict(cat.name)
  form.slug = cat.slug
  form.description = normalizeI18nDict(cat.description)
  form.color = cat.color || '#94a3b8'
  form.icon = cat.icon || ''
  // 必须回填：不回填则每次 PUT 把封面提交成空 → 已有封面被"改一次名字"抹掉
  form.cover_image = cat.cover_image || ''
  // 层级同样必须回填：不回填则 PUT 提交 null，子分类在"改一次名字"后被静默提到顶级
  form.parent_id = normalizeParentId(cat.parent_id)
  // 响应缓存可能还留着上线前写入的旧形状（没有这一项）；缺键按启用处理，
  // 否则编辑一次就把没动的分类判成停用。
  form.is_active = cat.is_active ?? true
  slugManualEdit = true
  dialogOpen.value = true
}

const save = async () => {
  if (!getLocalizedStr(form.name).trim()) {
    toast.error('请输入分类名称')
    return
  }
  if (form.slug && !CONTENT_SLUG_PATTERN.test(form.slug)) {
    toast.error('Slug 只能包含小写字母、数字、下划线、中文和连字符（-）')
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
      icon: form.icon || undefined,
      // 始终带上：空串会被 wrapper 归成 null（= 清掉封面），省略键则清不掉
      cover_image: form.cover_image,
      // 同样始终带上：null = 明确提到顶级，省略键在 exclude_unset 下清不掉父级
      parent_id: form.parent_id,
      is_active: form.is_active
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
    :icon="FolderTree"
    description="分类用于文章的主题组织，支持颜色与图标快速区分。"
    :count="categories.length"
  >
    <template #actions>
      <Button
        size="sm"
        class="shadow-sm"
        @click="openNew"
      >
        <Plus data-icon="inline-start" />
        新建分类
      </Button>
    </template>

    <AdminDataTable
      :columns="columns"
      :data="categoryRows"
      :loading="loading"
      row-key="id"
    >
      <template #cell-id="{ row }">
        #{{ row.id }}
      </template>
      <template #cell-name="{ row }">
        <div
          class="flex items-center gap-2"
          :style="{ marginLeft: `${indentOf(row as AdminCategory) * 1.25}rem` }"
        >
          <CornerDownRight
            v-if="indentOf(row as AdminCategory) > 0"
            class="size-3.5 shrink-0 text-muted-foreground/60"
          />
          <img
            v-if="(row as AdminCategory).cover_image"
            :src="(row as AdminCategory).cover_image!"
            alt=""
            class="size-8 shrink-0 rounded-[6px] object-cover"
            data-testid="category-row-cover"
          >
          <span
            class="size-3 rounded-full inline-block border border-white shadow-sm"
            :style="{ background: (row as AdminCategory).color || '#94a3b8' }"
          />
          <span class="font-medium">{{ getLocalizedStr((row as AdminCategory).name) }}</span>
          <Badge
            v-if="(row as AdminCategory).parent_id"
            variant="outline"
            class="rounded-[10px] font-normal text-xs"
          >
            子分类
          </Badge>
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
      <template #cell-is_active="{ row }">
        <Badge
          class="rounded-[10px] font-normal whitespace-nowrap"
          :class="(row as AdminCategory).is_active
            ? 'bg-success-muted text-success-muted-foreground'
            : 'bg-muted text-muted-foreground'"
        >
          {{ (row as AdminCategory).is_active ? '启用' : '停用' }}
        </Badge>
      </template>
      <template #actions="{ row }">
        <AdminRowActions
          :actions="[
            { key: 'edit', label: '编辑分类', icon: Pencil, onClick: () => openEdit(row as AdminCategory) },
            { key: 'delete', label: '删除分类', icon: Trash2, destructive: true, onClick: () => confirmDelete((row as AdminCategory).id) }
          ]"
        />
      </template>
    </AdminDataTable>

    <!-- 新建 / 编辑 Dialog -->
    <AdminCrudDialog
      v-model:open="dialogOpen"
      :title="dialogMode === 'edit' ? '编辑分类' : '新建分类'"
      description="分类会出现在前台导航与文章卡片上，名称与描述支持四语。"
      :icon="FolderTree"
      :loading="saving"
      :submit-text="editingId ? '更新' : '保存'"
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
          for="category-form-slug"
          hint="用于分类页地址 /categories/<slug>；留空时按名称自动生成。"
        >
          <Input
            id="category-form-slug"
            v-model="form.slug"
            placeholder="auto-generated-slug"
            class="h-10 rounded-[10px] font-mono text-sm"
            @input="slugManualEdit = true"
          />
        </AdminFormField>
        <I18nTabsEditor
          v-model="form.description"
          kind="textarea"
          label="描述"
          :rows="3"
          flat
        />
        <AdminFormField
          label="父分类"
          for="category-form-parent"
          hint="留空为顶级分类；子分类会出现在父分类落地页与后台列表的缩进层级里。"
        >
          <Select v-model="form.parent_id">
            <SelectTrigger
              id="category-form-parent"
              class="h-10 rounded-[10px]"
            >
              <SelectValue placeholder="无（顶级分类）" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem :value="null">
                无（顶级分类）
              </SelectItem>
              <SelectItem
                v-for="opt in parentOptions"
                :key="opt.id"
                :value="opt.id"
              >
                {{ getLocalizedStr(opt.name) || opt.slug }}
              </SelectItem>
            </SelectContent>
          </Select>
        </AdminFormField>
        <div class="grid grid-cols-1 gap-4 sm:grid-cols-2">
          <AdminFormField
            label="颜色"
            for="category-form-color"
          >
            <div class="flex gap-2">
              <input
                id="category-form-color"
                v-model="form.color"
                type="color"
                class="h-10 w-12 shrink-0 rounded-[10px] border border-input bg-background cursor-pointer"
              >
              <Input
                v-model="form.color"
                :aria-label="t('admin.categories.fColor')"
                class="h-10 flex-1 rounded-[10px] font-mono text-xs"
              />
            </div>
          </AdminFormField>
          <AdminFormField
            label="图标"
            for="category-form-icon"
            hint="heroicons:code-bracket 或 emoji"
          >
            <div class="flex gap-2">
              <div class="size-10 shrink-0 rounded-[10px] border border-border flex items-center justify-center bg-muted/30">
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
                class="h-10 flex-1 rounded-[10px] font-mono text-xs"
              />
            </div>
          </AdminFormField>
        </div>
        <AdminFormField
          label="封面图"
          hint="展示在分类页顶部横幅；不设则该区域整块不出现。"
        >
          <div class="flex flex-col gap-3">
            <button
              type="button"
              class="group relative w-full max-w-[320px] aspect-[16/9] overflow-hidden rounded-[12px] border border-dashed border-border bg-muted/30 transition-colors hover:border-primary/50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
              :aria-label="form.cover_image ? '更换封面图' : '上传封面图'"
              :disabled="coverUploading"
              @click="coverInputRef?.click()"
            >
              <img
                v-if="form.cover_image"
                :src="form.cover_image"
                alt="封面预览"
                class="size-full object-cover"
              >
              <span
                v-else
                class="absolute inset-0 flex flex-col items-center justify-center gap-1 text-xs text-muted-foreground"
              >
                <ImageIcon class="size-5 opacity-60" />
                点击上传封面
              </span>
              <span
                v-if="form.cover_image"
                class="absolute inset-0 flex items-center justify-center bg-black/45 text-xs font-medium text-white opacity-0 transition-opacity group-hover:opacity-100 group-focus-visible:opacity-100"
              >
                更换封面
              </span>
            </button>
            <div class="flex gap-2">
              <Button
                type="button"
                variant="outline"
                size="sm"
                class="h-9 rounded-[10px]"
                :disabled="coverUploading"
                @click="coverInputRef?.click()"
              >
                {{ coverUploading ? '上传中...' : (form.cover_image ? '更换封面' : '上传封面') }}
              </Button>
              <Button
                v-if="form.cover_image"
                type="button"
                variant="ghost"
                size="sm"
                class="h-9 rounded-[10px] text-destructive hover:text-destructive"
                @click="clearCover"
              >
                清除
              </Button>
            </div>
            <input
              ref="coverInputRef"
              type="file"
              accept="image/*"
              class="hidden"
              @change="handleCoverUpload"
            >
          </div>
        </AdminFormField>
        <div class="flex items-center justify-between gap-4 rounded-[12px] border border-border bg-muted/20 px-4 py-3">
          <div>
            <Label
              for="category-form-active"
              class="text-sm font-medium"
            >启用状态</Label>
            <div class="text-xs text-muted-foreground mt-0.5">
              关闭后分类不再出现在前台分类列表、导航与站点统计里；已发布文章上的分类链接仍然可用。
            </div>
          </div>
          <Switch
            id="category-form-active"
            v-model="form.is_active"
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
      :on-confirm="doDelete"
    />
  </AdminListPage>
</template>
