<!--
  后台首页轮播管理（SPA / layout=admin）：GET/POST/PUT/DELETE /admin/hero/slides。
  首页横幅（pages/index.vue）的真实数据源：DB 有生效轮播时用它，没有则后端用近 30 天高热度文章兜底，
  所以"删光这里的行"不等于首页空白，而是回到热榜自动填充。
  硬契约：后端 HeroSlide* 为 extra=forbid 且 title/subtitle/cta_text 声明成 str，
  多语言字典必须 JSON.stringify 后提交（回显时解析），漏一步即 422。
  media_type 固定 image：首页只有背景图层，选 video/youtube 会存得进去却永远不渲染（静默失效）。
  start_time/end_time 不开放：生效时间窗由后端过滤，界面暂不排期，缺省 null＝长期生效。
-->
<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { MonitorPlay } from '@lucide/vue'
import {
  fetchAdminHeroSlides,
  createAdminHeroSlide,
  updateAdminHeroSlide,
  deleteAdminHeroSlide,
  toggleAdminHeroSlide,
  type AdminHeroSlide,
  type AdminHeroSlidePayload
} from '~~/composables/useAdminManage'
import { useToast } from '~~/composables/useToast'
import { useMediaUploadCover } from '~~/composables/useMedia'
import { Button } from '~~/components/ui/button'
import { Input } from '~~/components/ui/input'
import { Label } from '~~/components/ui/label'
import { Badge } from '~~/components/ui/badge'
import I18nTabsEditor from '~~/components/admin/I18nTabsEditor.vue'
import { getLocalizedStr, normalizeI18nDict, type I18nDict } from '~~/composables/useAdminI18n'
import type { AdminColumn as Column } from '~~/types/admin'

definePageMeta({ ssr: false, layout: 'admin' })

const toast = useToast()

const slides = shallowRef<AdminHeroSlide[]>([])
const loading = ref(false)
const saving = ref(false)
const uploading = ref(false)
const editingId = ref<number | null>(null)

const dialogOpen = ref(false)
const dialogMode = ref<'new' | 'edit'>('new')

const HEX_RE = /^#[0-9a-fA-F]{6}$/
const ALIGN_OPTIONS = [
  { value: 'left', label: '左对齐' },
  { value: 'center', label: '居中' },
  { value: 'right', label: '右对齐' }
] as const

const form = reactive<{
  title: I18nDict
  subtitle: I18nDict
  cta_text: I18nDict
  media_url: string
  cta_url: string
  overlay_color: string
  overlay_opacity: number
  text_align: 'left' | 'center' | 'right'
  sort_order: number
  is_active: boolean
}>({
  title: { zh: '', en: '', ja: '', zh_Hant: '' },
  subtitle: { zh: '', en: '', ja: '', zh_Hant: '' },
  cta_text: { zh: '', en: '', ja: '', zh_Hant: '' },
  media_url: '',
  cta_url: '',
  overlay_color: '#000000',
  overlay_opacity: 45,
  text_align: 'left',
  sort_order: 0,
  is_active: true
})

/** 后端存的是 JSON 字符串；非 JSON（历史脏数据/手填纯文本）原样当作当前语言文本回显 */
function toDict(raw: string | null): I18nDict {
  if (!raw) return { zh: '', en: '', ja: '', zh_Hant: '' }
  try {
    return normalizeI18nDict(JSON.parse(raw) as string | Record<string, string>)
  } catch {
    return normalizeI18nDict(raw)
  }
}

/** 四语全空时提交 null：留空串会被首页当成"有文案"从而顶掉兜底标题 */
function fromDict(dict: I18nDict): string | null {
  const values = normalizeI18nDict(dict)
  const hasText = Object.values(values).some(v => String(v ?? '').trim())
  return hasText ? JSON.stringify(values) : null
}

const columns: Column[] = [
  { key: 'preview', title: '预览', class: 'w-28' },
  { key: 'title', title: '标题' },
  { key: 'cta_url', title: '链接', class: 'max-w-[220px] text-muted-foreground' },
  { key: 'sort_order', title: '排序', align: 'center', class: 'w-20' },
  { key: 'is_active', title: '状态', align: 'center', class: 'w-24' }
]

async function loadData() {
  loading.value = true
  try {
    slides.value = await fetchAdminHeroSlides()
  } catch (err) {
    // 失败提示由 apiFetch 统一 toast，此处仅做状态兜底
    console.error('load hero slides error', err)
    slides.value = []
  } finally {
    loading.value = false
  }
}

function resetForm() {
  form.title = { zh: '', en: '', ja: '', zh_Hant: '' }
  form.subtitle = { zh: '', en: '', ja: '', zh_Hant: '' }
  form.cta_text = { zh: '', en: '', ja: '', zh_Hant: '' }
  form.media_url = ''
  form.cta_url = ''
  form.overlay_color = '#000000'
  form.overlay_opacity = 45
  form.text_align = 'left'
  form.sort_order = slides.value.length
  form.is_active = true
  editingId.value = null
}

function openNew() {
  dialogMode.value = 'new'
  resetForm()
  dialogOpen.value = true
}

function openEdit(slide: AdminHeroSlide) {
  dialogMode.value = 'edit'
  form.title = toDict(slide.title)
  form.subtitle = toDict(slide.subtitle)
  form.cta_text = toDict(slide.cta_text)
  form.media_url = slide.media_url
  form.cta_url = slide.cta_url ?? ''
  form.overlay_color = HEX_RE.test(slide.overlay_color ?? '') ? slide.overlay_color : '#000000'
  form.overlay_opacity = slide.overlay_opacity ?? 45
  form.text_align = slide.text_align ?? 'left'
  form.sort_order = slide.sort_order ?? 0
  form.is_active = slide.is_active
  editingId.value = slide.id
  dialogOpen.value = true
}

const fileInput = ref<HTMLInputElement | null>(null)

function pickImage() {
  fileInput.value?.click()
}

async function onImageChosen(event: Event) {
  const input = event.target as HTMLInputElement
  const file = input.files?.[0]
  input.value = ''
  if (!file) return
  uploading.value = true
  try {
    const result = await useMediaUploadCover(file)
    if (result?.url) form.media_url = result.url
  } catch (err) {
    // 失败提示由 apiFetch 统一 toast
    console.error('upload hero image error', err)
  } finally {
    uploading.value = false
  }
}

async function save() {
  if (!form.media_url.trim()) {
    toast.error('请上传或填写背景图片地址')
    return
  }
  if (!HEX_RE.test(form.overlay_color)) {
    toast.error('遮罩颜色需为 6 位十六进制值，如 #000000')
    return
  }
  const opacity = Number(form.overlay_opacity)
  if (!Number.isFinite(opacity) || opacity < 0 || opacity > 100) {
    toast.error('遮罩透明度需在 0–100 之间')
    return
  }
  const payload: AdminHeroSlidePayload = {
    title: fromDict(form.title),
    subtitle: fromDict(form.subtitle),
    cta_text: fromDict(form.cta_text),
    media_url: form.media_url.trim(),
    cta_url: form.cta_url.trim() || null,
    media_type: 'image',
    overlay_color: form.overlay_color,
    overlay_opacity: Math.round(opacity),
    text_align: form.text_align,
    sort_order: Number(form.sort_order) || 0,
    is_active: form.is_active
  }
  saving.value = true
  try {
    if (editingId.value) {
      await updateAdminHeroSlide(editingId.value, payload)
      toast.success('更新成功')
    } else {
      await createAdminHeroSlide(payload)
      toast.success('创建成功')
    }
    dialogOpen.value = false
    resetForm()
    await loadData()
  } catch (err) {
    // 失败提示由 apiFetch 统一 toast，此处不重复弹错
    console.error('save hero slide error', err)
  } finally {
    saving.value = false
  }
}

async function toggleActive(slide: AdminHeroSlide) {
  try {
    await toggleAdminHeroSlide(slide.id)
    toast.success(slide.is_active ? '已停用' : '已启用')
    await loadData()
  } catch (err) {
    console.error('toggle hero slide error', err)
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
  await deleteAdminHeroSlide(id)
  toast.success('删除成功')
  pendingDeleteId.value = null
  if (editingId.value === id) resetForm()
  await loadData()
}

onMounted(loadData)
</script>

<template>
  <AdminListPage
    title="首页轮播"
    :icon="MonitorPlay"
    description="首页横幅按排序值轮播这些幻灯片；一行都没有时自动改用近 30 天高热度文章。"
    :count="slides.length"
  >
    <template #actions>
      <Button
        class="rounded-[12px] h-10 px-5 shadow-sm"
        @click="openNew"
      >
        + 新建幻灯片
      </Button>
    </template>

    <AdminDataTable
      :columns="columns"
      :data="slides"
      :loading="loading"
      row-key="id"
    >
      <template #cell-preview="{ row }">
        <div class="size-16 rounded-lg overflow-hidden border border-border bg-muted/30 flex items-center justify-center">
          <img
            v-if="(row as AdminHeroSlide).media_url"
            :src="(row as AdminHeroSlide).media_url"
            :alt="getLocalizedStr(toDict((row as AdminHeroSlide).title)) || '幻灯片背景'"
            class="size-full object-cover"
            loading="lazy"
          >
          <span
            v-else
            class="text-xs text-muted-foreground"
          >无图</span>
        </div>
      </template>
      <template #cell-title="{ row }">
        <span class="font-medium">
          {{ getLocalizedStr(toDict((row as AdminHeroSlide).title)) || '（用站点标题）' }}
        </span>
      </template>
      <template #cell-cta_url="{ row }">
        <span
          class="text-xs block truncate"
          :title="(row as AdminHeroSlide).cta_url || ''"
        >{{ (row as AdminHeroSlide).cta_url || '-' }}</span>
      </template>
      <template #cell-sort_order="{ row }">
        <Badge variant="secondary">
          {{ (row as AdminHeroSlide).sort_order }}
        </Badge>
      </template>
      <template #cell-is_active="{ row }">
        <button
          type="button"
          class="inline-flex"
          :aria-label="(row as AdminHeroSlide).is_active ? '点击停用' : '点击启用'"
          @click="toggleActive(row as AdminHeroSlide)"
        >
          <Badge :variant="(row as AdminHeroSlide).is_active ? 'default' : 'outline'">
            {{ (row as AdminHeroSlide).is_active ? '启用中' : '已停用' }}
          </Badge>
        </button>
      </template>
      <template #actions="{ row }">
        <Button
          variant="ghost"
          size="sm"
          class="h-8 rounded-[10px] text-xs px-3"
          @click="openEdit(row as AdminHeroSlide)"
        >
          编辑
        </Button>
        <Button
          variant="ghost"
          size="sm"
          class="h-8 rounded-[10px] text-xs px-3 text-destructive hover:text-destructive"
          @click="confirmDelete((row as AdminHeroSlide).id)"
        >
          删除
        </Button>
      </template>
    </AdminDataTable>

    <AdminCrudDialog
      v-model:open="dialogOpen"
      :title="dialogMode === 'edit' ? '编辑幻灯片' : '新建幻灯片'"
      :loading="saving"
      :submit-text="editingId ? '更新' : '保存'"
      @submit="save"
    >
      <div class="flex flex-col gap-4">
        <div>
          <Label class="mb-1 block text-xs text-muted-foreground">背景图片</Label>
          <div class="flex items-start gap-3">
            <div class="size-24 shrink-0 rounded-lg overflow-hidden border border-border bg-muted/30 flex items-center justify-center">
              <img
                v-if="form.media_url"
                :src="form.media_url"
                alt="幻灯片背景预览"
                class="size-full object-cover"
              >
              <span
                v-else
                class="px-2 text-center text-xs text-muted-foreground"
              >未选择</span>
            </div>
            <div class="flex flex-1 flex-col gap-2">
              <Button
                type="button"
                variant="outline"
                size="sm"
                class="rounded-[10px] h-9 w-fit"
                :disabled="uploading"
                @click="pickImage"
              >
                {{ uploading ? '上传中...' : (form.media_url ? '更换图片' : '上传图片') }}
              </Button>
              <Input
                v-model="form.media_url"
                placeholder="也可直接粘贴图片 URL"
                class="h-9 rounded-[10px] font-mono text-xs"
              />
              <input
                ref="fileInput"
                type="file"
                accept="image/*"
                class="hidden"
                @change="onImageChosen"
              >
            </div>
          </div>
        </div>

        <I18nTabsEditor
          v-model="form.title"
          kind="text"
          label="主标题（留空则用站点标题）"
        />
        <I18nTabsEditor
          v-model="form.subtitle"
          kind="textarea"
          label="副标题 / 摘要"
          :rows="2"
        />
        <I18nTabsEditor
          v-model="form.cta_text"
          kind="text"
          label="按钮文案（留空则显示「阅读全文」）"
        />

        <div>
          <Label
            for="hero-form-cta"
            class="mb-1 block text-xs text-muted-foreground"
          >按钮链接（站内路径，语言前缀由前端自动补）</Label>
          <Input
            id="hero-form-cta"
            v-model="form.cta_url"
            placeholder="/posts/your-slug"
            class="h-9 rounded-[10px]"
          />
        </div>

        <div class="grid grid-cols-2 gap-3">
          <div>
            <Label
              for="hero-form-opacity"
              class="mb-1 block text-xs text-muted-foreground"
            >遮罩透明度 0–100</Label>
            <Input
              id="hero-form-opacity"
              v-model.number="form.overlay_opacity"
              type="number"
              min="0"
              max="100"
              class="h-9 rounded-[10px]"
            />
          </div>
          <div>
            <Label
              for="hero-form-sort"
              class="mb-1 block text-xs text-muted-foreground"
            >排序（小在前）</Label>
            <Input
              id="hero-form-sort"
              v-model.number="form.sort_order"
              type="number"
              min="0"
              class="h-9 rounded-[10px]"
            />
          </div>
        </div>

        <div>
          <Label class="mb-1 block text-xs text-muted-foreground">文字对齐</Label>
          <div class="flex gap-2">
            <Button
              v-for="opt in ALIGN_OPTIONS"
              :key="opt.value"
              type="button"
              size="sm"
              class="h-9 rounded-[10px]"
              :variant="form.text_align === opt.value ? 'default' : 'outline'"
              @click="form.text_align = opt.value"
            >
              {{ opt.label }}
            </Button>
          </div>
        </div>

        <div>
          <Label class="mb-1 block text-xs text-muted-foreground">遮罩颜色</Label>
          <div class="flex gap-2">
            <input
              v-model="form.overlay_color"
              type="color"
              aria-label="遮罩颜色选择器"
              class="h-9 w-11 rounded-[10px] border border-input bg-background cursor-pointer"
            >
            <Input
              v-model="form.overlay_color"
              aria-label="遮罩颜色十六进制值"
              class="h-9 rounded-[10px] flex-1 font-mono text-xs"
            />
          </div>
        </div>

        <label class="flex items-center gap-2 text-sm">
          <input
            v-model="form.is_active"
            type="checkbox"
            class="size-4 rounded border-input"
          >
          启用这张幻灯片
        </label>
      </div>
    </AdminCrudDialog>

    <AdminConfirmDialog
      v-model:open="deleteDialogOpen"
      title="确认删除幻灯片"
      description="删除后如果一张都不剩，首页横幅会自动改用近 30 天高热度文章。此操作不可撤销。"
      confirm-text="确认删除"
      :on-confirm="doDelete"
    />
  </AdminListPage>
</template>
