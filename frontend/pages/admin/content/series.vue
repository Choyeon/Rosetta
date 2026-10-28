<!--
  系列管理页：卡片列表 + CRUD 弹窗（含封面上传与排序号）。
  硬契约：与分类/标签不同，PostSeriesCreate/Update 的 slug 为必填且后端不自动生成——
  前端用 CONTENT_SLUG_PATTERN 先拦（与后端同口径，允许中文）；请求体 extra=forbid，
  只能带 name/slug/description/cover_image/sort_order，i18n dict 要先经 toI18nPayload 滤掉空语言。
  is_active 是公开列表 GET /series、系列详情（停用即 404）与 sitemap 投递面的真实强制点，
  卡片底部的状态徽标直接打 PUT /admin/series/{id}/toggle（后端翻值并清前台页面缓存）。
-->
<script setup lang="ts">
import { ref, reactive, watch, onMounted } from 'vue'
import {
  fetchAdminSeries,
  createAdminSeries,
  updateAdminSeries,
  deleteAdminSeries,
  toggleAdminSeries,
  type AdminSeries
} from '~~/composables/useAdminManage'
import { useMediaUploadCover } from '~~/composables/useMedia'
import { useToast } from '~~/composables/useToast'
import { Button } from '~~/components/ui/button'
import { Input } from '~~/components/ui/input'
import AdminFormField from '~~/components/admin/AdminFormField.vue'
import { Badge } from '~~/components/ui/badge'
import { Skeleton } from '~~/components/ui/skeleton'
import I18nTabsEditor from '~~/components/admin/I18nTabsEditor.vue'
import AdminRowActions from '~~/components/admin/AdminRowActions.vue'
import { EMPTY_I18N_DICT, getLocalizedStr, normalizeI18nDict, toI18nPayload, slugify, CONTENT_SLUG_PATTERN } from '~~/composables/useAdminI18n'
import { BookOpen, ChevronDown, Layers, Plus, Pencil, Trash2, Image as ImageIcon } from '@lucide/vue'

definePageMeta({ ssr: false, layout: 'admin' })

const toast = useToast()

const seriesList = shallowRef<AdminSeries[]>([])
const loading = ref(false)
const expandedId = ref<number | null>(null)
const coverInputRef = ref<HTMLInputElement | null>(null)
const deleteDialogOpen = ref(false)
const pendingDeleteId = ref<number | null>(null)

const dialogOpen = ref(false)
const dialogMode = ref<'new' | 'edit'>('new')
const saving = ref(false)
const coverUploading = ref(false)

const form = reactive({
  name: { ...EMPTY_I18N_DICT } as Record<string, string>,
  slug: '',
  description: { ...EMPTY_I18N_DICT } as Record<string, string>,
  cover_image: '',
  sort_order: 0
})

const editingId = ref<number | null>(null)

/** 后端 PostSeriesCreate/Update 的 slug 必填（无后端自动生成），校验口径与 CONTENT_SLUG_PATTERN 一致 */
let slugManualEdit = false as boolean
watch(
  () => form.name,
  (val) => {
    const zhVal = String(val?.zh ?? '')
    if (!slugManualEdit && zhVal) {
      const s = slugify(zhVal)
      form.slug = CONTENT_SLUG_PATTERN.test(s) ? s : ''
    }
  },
  { deep: true }
)

const loadData = async () => {
  loading.value = true
  try {
    seriesList.value = await fetchAdminSeries()
  } catch (e) {
    // 失败提示由 apiFetch 统一 toast，此处仅做状态兜底
    console.error('[series] loadData failed:', e)
    seriesList.value = []
  } finally {
    loading.value = false
  }
}

const openNew = () => {
  dialogMode.value = 'new'
  editingId.value = null
  form.name = { ...EMPTY_I18N_DICT }
  form.slug = ''
  form.description = { ...EMPTY_I18N_DICT }
  form.cover_image = ''
  form.sort_order = 0
  slugManualEdit = false
  dialogOpen.value = true
}

const openEdit = (s: AdminSeries) => {
  dialogMode.value = 'edit'
  editingId.value = s.id
  form.name = normalizeI18nDict(s.name)
  form.slug = s.slug
  form.description = normalizeI18nDict(s.description)
  form.cover_image = s.cover_image || ''
  form.sort_order = s.sort_order ?? 0
  slugManualEdit = true
  dialogOpen.value = true
}

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
  } catch (e) {
    // 上传失败提示由 apiFetch 统一 toast，此处不重复弹错
    console.error('[series] handleCoverUpload failed:', e)
  } finally {
    coverUploading.value = false
    input.value = ''
  }
}

const clearCover = () => {
  form.cover_image = ''
}

const save = async () => {
  const namePayload = toI18nPayload(form.name)
  if (!namePayload) {
    toast.error('请输入系列标题（至少一种语言）')
    return
  }
  if (!form.slug.trim() || !CONTENT_SLUG_PATTERN.test(form.slug.trim())) {
    toast.error('请填写 Slug，仅允许小写字母、数字、下划线、中文和连字符（-）')
    return
  }
  saving.value = true
  try {
    // PostSeriesCreate/Update 为 extra=forbid：只带后端已知字段，空语言值过滤掉
    const descPayload = toI18nPayload(form.description)
    const payload: Record<string, unknown> = {
      name: namePayload,
      slug: form.slug.trim(),
      description: descPayload,
      cover_image: form.cover_image || undefined,
      sort_order: Number(form.sort_order) || 0
    }
    if (dialogMode.value === 'edit' && editingId.value) {
      await updateAdminSeries(editingId.value, payload)
      toast.success('更新成功')
    } else {
      await createAdminSeries(payload)
      toast.success('创建成功')
    }
    dialogOpen.value = false
    await loadData()
  } catch (e) {
    // 失败提示由 apiFetch 统一 toast，此处不重复弹错
    console.error('[series] save failed:', e)
  } finally {
    saving.value = false
  }
}

const toggleExpand = (id: number) => {
  expandedId.value = expandedId.value === id ? null : id
}

const togglingId = ref<number | null>(null)

/**
 * toggle 口翻的是后端那一行的当前值，不是"设成 X"——连点两次等于没点，
 * 所以在请求期间锁住这张卡片的入口，并用后端回读后的列表刷新状态（seriesList 是 shallowRef，
 * 就地改 s.is_active 不会重渲染）。
 */
async function toggleActive(s: AdminSeries) {
  if (togglingId.value !== null) return
  togglingId.value = s.id
  try {
    await toggleAdminSeries(s.id)
    toast.success(s.is_active ? '已停用，前台系列页与列表不再展示' : '已启用')
    await loadData()
  } catch (e) {
    // 失败提示由 apiFetch 统一 toast，此处不重复弹错
    console.error('[series] toggleActive failed:', e)
  } finally {
    togglingId.value = null
  }
}

function confirmDelete(id: number) {
  pendingDeleteId.value = id
  deleteDialogOpen.value = true
}

async function doDelete() {
  const id = pendingDeleteId.value
  if (id == null) return
  await deleteAdminSeries(id)
  toast.success('删除成功')
  pendingDeleteId.value = null
  if (expandedId.value === id) expandedId.value = null
  await loadData()
}

onMounted(() => {
  loadData()
})
</script>

<template>
  <AdminListPage
    title="系列管理"
    :icon="Layers"
    description="系列是一组相关文章的有序集合，方便读者按顺序阅读。"
    :count="seriesList.length"
  >
    <template #actions>
      <Button
        size="sm"
        class="shadow-sm"
        @click="openNew"
      >
        <Plus data-icon="inline-start" />
        新建系列
      </Button>
    </template>

    <div class="p-5">
      <template v-if="loading">
        <div class="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
          <Skeleton
            v-for="i in 6"
            :key="`sk-${i}`"
            class="h-60 rounded-[12px]"
          />
        </div>
      </template>

      <template v-else-if="seriesList.length === 0">
        <div class="card-surface py-24 text-center text-muted-foreground">
          <div class="mb-4 opacity-30 flex items-center justify-center">
            <BookOpen class="size-16" />
          </div>
          <div class="text-sm mb-2">
            暂无系列
          </div>
          <div class="text-xs opacity-70">
            创建一个系列来组织多篇相关文章
          </div>
        </div>
      </template>

      <template v-else>
        <div class="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
          <div
            v-for="s in seriesList"
            :key="s.id"
            class="card-surface overflow-hidden shadow-sm"
          >
            <div
              class="relative h-36 w-full overflow-hidden"
              @click="toggleExpand(s.id)"
            >
              <img
                v-if="s.cover_image"
                :src="s.cover_image"
                :alt="getLocalizedStr(s.name)"
                class="size-full object-cover cursor-pointer"
              >
              <div
                v-else
                class="size-full bg-primary/85 cursor-pointer"
              />
              <div class="absolute top-3 left-3 flex items-center gap-2">
                <Badge class="rounded-[10px] border border-white/30 bg-background/90 text-popover-foreground backdrop-blur-sm">
                  {{ s.posts_count }} 篇
                </Badge>
              </div>
              <div class="absolute top-3 right-3 text-white/90 opacity-80 hover:opacity-100 transition-opacity cursor-pointer">
                <ChevronDown
                  class="size-5 transition-transform"
                  :class="{ 'rotate-180': expandedId === s.id }"
                />
              </div>
            </div>
            <div class="p-4">
              <div class="flex items-start justify-between gap-2 mb-1.5">
                <h3
                  class="font-semibold text-base leading-snug line-clamp-1 cursor-pointer hover:text-primary transition-colors"
                  @click="toggleExpand(s.id)"
                >
                  {{ getLocalizedStr(s.name) }}
                </h3>
                <span class="text-xs text-muted-foreground shrink-0 mt-0.5">#{{ s.id }}</span>
              </div>
              <p class="text-sm text-muted-foreground line-clamp-2 min-h-[2.5rem] mb-3">
                {{ getLocalizedStr(s.description) || '暂无描述' }}
              </p>
              <div class="flex items-center justify-between gap-2">
                <div class="flex min-w-0 items-center gap-2">
                  <button
                    type="button"
                    class="inline-flex shrink-0 disabled:opacity-60"
                    :aria-label="s.is_active ? '点击停用该系列' : '点击启用该系列'"
                    :title="s.is_active ? '点击停用：前台系列列表与详情页不再展示' : '点击启用：恢复前台展示与爬虫投递'"
                    :disabled="togglingId !== null"
                    @click="toggleActive(s)"
                  >
                    <Badge :variant="s.is_active ? 'default' : 'outline'">
                      {{ s.is_active ? '启用中' : '已停用' }}
                    </Badge>
                  </button>
                  <span class="truncate text-xs text-muted-foreground">排序：{{ s.sort_order ?? 0 }}</span>
                </div>
                <div class="flex items-center gap-1">
                  <AdminRowActions
                    :actions="[
                      { key: 'edit', label: '编辑系列', icon: Pencil, onClick: () => openEdit(s) },
                      { key: 'delete', label: '删除系列', icon: Trash2, destructive: true, onClick: () => confirmDelete(s.id) }
                    ]"
                  />
                </div>
              </div>
            </div>

            <div
              v-if="expandedId === s.id"
              class="border-t border-border bg-muted/40 p-4"
            >
              <div class="flex items-center justify-between mb-3">
                <h4 class="text-sm font-medium">
                  系列内文章排序
                </h4>
                <span class="text-xs text-muted-foreground">（待后端 /series/{id}/posts 接口上线后启用）</span>
              </div>
              <div class="py-8 text-center text-xs text-muted-foreground">
                {{ s.posts_count > 0 ? `该系列共 ${s.posts_count} 篇文章，排序接口待提供` : '暂无关联文章' }}
              </div>
            </div>
          </div>
        </div>
      </template>
    </div>

    <AdminCrudDialog
      v-model:open="dialogOpen"
      :title="dialogMode === 'edit' ? '编辑系列' : '新建系列'"
      description="系列把同一主题的多篇文章按顺序组织成专题。"
      :icon="Layers"
      :loading="saving"
      :submit-text="dialogMode === 'edit' ? '更新' : '保存'"
      @submit="save"
    >
      <div class="flex flex-col gap-5">
        <I18nTabsEditor
          v-model="form.name"
          kind="text"
          label="标题"
          placeholder="系列标题"
          :required="true"
          flat
        />
        <AdminFormField
          label="Slug"
          for="series-form-slug"
          required
          hint="用于系列页地址 /series/<slug>；留空时按标题自动生成。"
        >
          <Input
            id="series-form-slug"
            v-model="form.slug"
            placeholder="series-slug"
            class="h-10 rounded-[10px] font-mono text-sm"
            @input="slugManualEdit = true"
          />
        </AdminFormField>
        <I18nTabsEditor
          v-model="form.description"
          kind="textarea"
          label="描述"
          placeholder="系列描述（可选）"
          :rows="3"
          flat
        />
        <AdminFormField
          label="封面图"
          hint="展示在系列列表与详情页顶部；不设则使用主题底色。"
        >
          <div class="flex flex-col gap-3">
            <button
              type="button"
              class="relative w-full aspect-[16/9] max-w-[320px] overflow-hidden rounded-[12px] border border-dashed border-border bg-muted/30 transition-colors hover:border-primary/50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring group"
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
        <AdminFormField
          label="排序号"
          for="series-form-sort-order"
          hint="数字越小越靠前。"
        >
          <Input
            id="series-form-sort-order"
            v-model.number="form.sort_order"
            type="number"
            class="h-10 w-32 rounded-[10px]"
          />
        </AdminFormField>
      </div>
    </AdminCrudDialog>

    <AdminConfirmDialog
      v-model:open="deleteDialogOpen"
      title="确认删除系列"
      description="删除系列不会删除其中的文章，但文章会失去系列关联。此操作不可撤销。"
      confirm-text="确认删除"
      :on-confirm="doDelete"
    />
  </AdminListPage>
</template>
