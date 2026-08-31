<script setup lang="ts">
import { ref, reactive, watch, onMounted } from 'vue'
import {
  fetchAdminSeries,
  createAdminSeries,
  updateAdminSeries,
  deleteAdminSeries,
  type AdminSeries
} from '~~/composables/useAdminManage'
import { useMediaUploadCover } from '~~/composables/useMedia'
import { useToast } from '~~/composables/useToast'
import { Button } from '~~/components/ui/button'
import { Input } from '~~/components/ui/input'
import { Label } from '~~/components/ui/label'
import { Badge } from '~~/components/ui/badge'
import { Skeleton } from '~~/components/ui/skeleton'
import I18nTabsEditor from '~~/components/admin/I18nTabsEditor.vue'
import { BookOpen, ChevronDown, Plus } from 'lucide-vue-next'

definePageMeta({ ssr: false, layout: 'admin' })

const toast = useToast()

const seriesList = ref<AdminSeries[]>([])
const loading = ref(false)
const expandedId = ref<number | null>(null)
const coverInputRef = ref<HTMLInputElement | null>(null)
const deleteDialogOpen = ref(false)
const pendingDeleteId = ref<number | null>(null)

const dialogOpen = ref(false)
const dialogMode = ref<'new' | 'edit'>('new')
const saving = ref(false)
const coverUploading = ref(false)

type I18nDict = Record<string, string>

const form = reactive({
  name: { zh: '', en: '', ja: '', zh_Hant: '' } as I18nDict,
  slug: '',
  description: { zh: '', en: '', ja: '', zh_Hant: '' } as I18nDict,
  cover_image: '',
  sort_order: 0
})

const editingId = ref<number | null>(null)

const getLocalizedStr = (v: string | Record<string, string> | null | undefined): string => {
  if (v == null) return ''
  if (typeof v === 'string') return v
  return v.zh || v.en || Object.values(v)[0] || ''
}

const normalizeI18nDict = (v: string | Record<string, string> | null | undefined): Record<string, string> => {
  const base = { zh: '', en: '', ja: '', zh_Hant: '' }
  if (v == null) return base
  if (typeof v === 'string') {
    return { ...base, zh: v }
  }
  return {
    zh: v.zh ?? '',
    en: v.en ?? '',
    ja: v.ja ?? '',
    zh_Hant: v.zh_Hant ?? ''
  }
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
    const zhVal = String(val?.zh ?? '')
    if (!slugManualEdit && zhVal) {
      form.slug = slugify(zhVal)
    }
  },
  { deep: true }
)

const loadData = async () => {
  loading.value = true
  try {
    seriesList.value = await fetchAdminSeries()
  } catch (e) {
    console.error('[series] loadData failed:', e)
    toast.error('加载系列列表失败')
    seriesList.value = []
  } finally {
    loading.value = false
  }
}

const openNew = () => {
  dialogMode.value = 'new'
  editingId.value = null
  form.name = { zh: '', en: '', ja: '', zh_Hant: '' }
  form.slug = ''
  form.description = { zh: '', en: '', ja: '', zh_Hant: '' }
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
    console.error('[series] handleCoverUpload failed:', e)
    toast.error('封面上传失败')
  } finally {
    coverUploading.value = false
    input.value = ''
  }
}

const clearCover = () => {
  form.cover_image = ''
}

const save = async () => {
  if (!String(form.name.zh ?? '').trim()) {
    toast.error('请输入系列标题')
    return
  }
  saving.value = true
  try {
    const descHasValue = String(form.description.zh ?? '') || String(form.description.en ?? '')
      || String(form.description.ja ?? '') || String(form.description.zh_Hant ?? '')
    const payload: Record<string, unknown> = {
      name: form.name,
      slug: form.slug || undefined,
      description: descHasValue ? form.description : undefined,
      cover_image: form.cover_image || undefined,
      sort_order: form.sort_order
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
    console.error('[series] save failed:', e)
    toast.error(editingId.value ? '更新系列失败' : '创建系列失败')
  } finally {
    saving.value = false
  }
}

const toggleExpand = (id: number) => {
  expandedId.value = expandedId.value === id ? null : id
}

function confirmDelete(id: number) {
  pendingDeleteId.value = id
  deleteDialogOpen.value = true
}

async function doDelete() {
  if (pendingDeleteId.value == null) return
  try {
    await deleteAdminSeries(pendingDeleteId.value)
    toast.success('删除成功')
    deleteDialogOpen.value = false
    pendingDeleteId.value = null
    if (expandedId.value === pendingDeleteId.value) expandedId.value = null
    await loadData()
  } catch (e) {
    console.error('[series] doDelete failed:', e)
    toast.error('删除系列失败')
  }
}

onMounted(() => {
  loadData()
})
</script>

<template>
  <AdminListPage
    title="系列管理"
    description="系列是一组相关文章的有序集合，方便读者按顺序阅读。"
    :count="seriesList.length"
  >
    <template #actions>
      <Button
        class="rounded-[12px] h-10 px-5 shadow-sm gap-2"
        @click="openNew"
      >
        <Plus class="size-4" />
        <span>新建系列</span>
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
        <div class="rounded-[12px] border border-border bg-card py-24 text-center text-muted-foreground">
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
            class="rounded-[12px] border border-border bg-card overflow-hidden shadow-sm"
          >
            <div
              class="relative h-36 w-full overflow-hidden"
              @click="toggleExpand(s.id)"
            >
              <img
                v-if="s.cover_image"
                :src="s.cover_image"
                :alt="getLocalizedStr(s.name)"
                class="w-full h-full object-cover cursor-pointer"
              >
              <div
                v-else
                class="w-full h-full bg-primary/85 cursor-pointer"
              />
              <div class="absolute top-3 left-3 flex items-center gap-2">
                <Badge class="rounded-[10px] border border-white/30 bg-white/90 text-stone-700 backdrop-blur-sm">
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
              <div class="flex items-center justify-between">
                <span class="text-xs text-muted-foreground">排序：{{ s.sort_order ?? 0 }}</span>
                <div class="flex items-center gap-1">
                  <Button
                    variant="ghost"
                    size="sm"
                    class="h-8 rounded-[10px] text-xs px-3"
                    @click="openEdit(s)"
                  >
                    编辑
                  </Button>
                  <Button
                    variant="ghost"
                    size="sm"
                    class="h-8 rounded-[10px] text-xs px-3 text-destructive hover:text-destructive"
                    @click="confirmDelete(s.id)"
                  >
                    删除
                  </Button>
                </div>
              </div>
            </div>

            <div
              v-if="expandedId === s.id"
              class="border-t border-border bg-stone-50/40 p-4"
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
      :loading="saving"
      :submit-text="dialogMode === 'edit' ? '更新' : '保存'"
      @submit="save"
    >
      <div class="flex flex-col gap-4">
        <I18nTabsEditor
          v-model="form.name"
          kind="text"
          label="标题"
          placeholder="系列标题"
          :required="true"
        />
        <div>
          <Label class="mb-1 block text-xs text-muted-foreground">Slug</Label>
          <Input
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
          placeholder="系列描述（可选）"
          :rows="3"
        />
        <div>
          <Label class="mb-1.5 block text-xs text-muted-foreground">封面图</Label>
          <div class="flex items-start gap-3">
            <div
              v-if="form.cover_image"
              class="w-[180px] h-[100px] rounded-[10px] overflow-hidden border border-border bg-muted"
            >
              <img
                :src="form.cover_image"
                alt="cover"
                class="w-full h-full object-cover"
              >
            </div>
            <div
              v-else
              class="w-[180px] h-[100px] rounded-[10px] border border-dashed border-border bg-muted flex items-center justify-center text-xs text-muted-foreground"
            >
              无封面
            </div>
            <div class="flex flex-col gap-2">
              <Button
                type="button"
                variant="outline"
                size="sm"
                class="rounded-[10px] h-9"
                :disabled="coverUploading"
                @click="coverInputRef?.click()"
              >
                {{ coverUploading ? '上传中...' : '上传封面' }}
              </Button>
              <Button
                v-if="form.cover_image"
                type="button"
                variant="ghost"
                size="sm"
                class="rounded-[10px] h-9 text-destructive hover:text-destructive"
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

    <AdminConfirmDialog
      v-model:open="deleteDialogOpen"
      title="确认删除系列"
      description="删除系列不会删除其中的文章，但文章会失去系列关联。此操作不可撤销。"
      confirm-text="确认删除"
      @confirm="doDelete"
    />
  </AdminListPage>
</template>
