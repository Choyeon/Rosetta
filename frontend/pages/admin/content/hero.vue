<!--
  后台首页轮播管理（SPA / layout=admin）：GET/POST/PUT/DELETE /admin/hero/slides。
  首页横幅（pages/index.vue）的真实数据源：DB 有生效轮播时用它，没有则后端用近 30 天高热度文章兜底，
  所以"删光这里的行"不等于首页空白，而是回到热榜自动填充。
  硬契约：后端 HeroSlide* 为 extra=forbid 且 title/subtitle/cta_text 声明成 str，
  多语言字典必须 JSON.stringify 后提交（回显时解析），漏一步即 422。
  media_type 三档（image / video / youtube）都参与首页渲染，分档判定单源在 lib/hero-media.ts：
  image 铺背景图、video 播站内视频（CSP media-src 只有 'self'，外链写口即拒）、youtube 走
  privacy-enhanced 的 youtube-nocookie.com iframe（CSP frame-src 只放这一个域，后端
  security_middleware 与 deploy/nginx-site.conf 两处同改）。poster_url 是视频/嵌入的封面，
  也是缩略图与"iframe 被拦"时的静图回落。提交前的搭配校验在 heroMediaError（与后端同文案）。
  主次两个按钮都是"幻灯片自带优先、缺省回落到站点设置/查看全部"，所以两张框都留空也顶不掉现有观感。
  start_time/end_time 是生效时间窗：公开口 GET /hero/slides 按 `start <= now <= end` 过滤，
  两端留空＝长期生效；窗口倒挂（结束不晚于开始）由后端 422 拦住，因为那种行存得下去却永远不下发。
-->
<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { MonitorPlay, Plus, Pencil, Trash2, X } from '@lucide/vue'
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
import AdminRowActions from '~~/components/admin/AdminRowActions.vue'
import { EMPTY_I18N_DICT, getLocalizedStr, normalizeI18nDict, type I18nDict } from '~~/composables/useAdminI18n'
// 排期换算与"这条现在处于哪个阶段"的判据是跨域口径（公告、文章定时、这里的轮播同形），
// 实现在 lib/announcement + lib/datetime：后端两侧的过滤条件都是 `start <= now <= end`，
// 再抄一遍边界判断等于给自己制造"后台显示生效中、前台却不出现"的漂移空间。
import {
  announcementScheduleError,
  announcementStatus,
  fromDateTimeLocal,
  toDateTimeLocal,
  type AnnouncementStatus
} from '~~/lib/announcement'
import {
  heroMediaError,
  heroThumbUrl,
  type HeroMediaType
} from '~~/lib/hero-media'
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

// 文字色调管的是"这张底图是深底还是亮底"：浅色＝今天的白字＋黑色电影感压暗层；
// 深色＝亮底图（雪景/白墙/浅灰渐变）用的深字，同时撤掉那三层纯装饰黑渐变，
// 否则深字压在黑纱上等于两边都看不清。遮罩颜色/强度是另一回事，任何色调下都由运营者自己调。
const TONE_OPTIONS = [
  { value: 'light', label: '浅色文字' },
  { value: 'dark', label: '深色文字' }
] as const

// 标签写死中文与同文件其它控件一致（本页未接 i18n）。
const MEDIA_TYPE_OPTIONS = [
  { value: 'image', label: '图片' },
  { value: 'video', label: '站内视频' },
  { value: 'youtube', label: 'YouTube' }
] as const

const form = reactive<{
  title: I18nDict
  subtitle: I18nDict
  cta_text: I18nDict
  cta_url: string
  cta_secondary_text: I18nDict
  cta_secondary_url: string
  media_type: HeroMediaType
  media_url: string
  poster_url: string
  overlay_color: string
  overlay_opacity: number
  text_align: 'left' | 'center' | 'right'
  text_color: 'light' | 'dark'
  sort_order: number
  start_time: string
  end_time: string
  is_active: boolean
}>({
  title: { ...EMPTY_I18N_DICT },
  subtitle: { ...EMPTY_I18N_DICT },
  cta_text: { ...EMPTY_I18N_DICT },
  cta_url: '',
  cta_secondary_text: { ...EMPTY_I18N_DICT },
  cta_secondary_url: '',
  media_type: 'image',
  media_url: '',
  poster_url: '',
  overlay_color: '#000000',
  overlay_opacity: 45,
  text_align: 'left',
  text_color: 'light',
  sort_order: 0,
  start_time: '',
  end_time: '',
  is_active: true
})

// 后台列表的"为什么这条没在首页出现"：判据与公开口的过滤同形（见顶部注释）。
// 只服务于这一列的说明文字，前台显不显示由后端决定，前端不得拿它去过滤。
const SCHEDULE_LABEL: Record<AnnouncementStatus, string> = {
  active: '生效中',
  scheduled: '未到点',
  expired: '已结束',
  disabled: '已停用'
}

/** 后端存的是 JSON 字符串；非 JSON（历史脏数据/手填纯文本）原样当作当前语言文本回显 */
function toDict(raw: string | null): I18nDict {
  if (!raw) return { ...EMPTY_I18N_DICT }
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
  { key: 'schedule', title: '生效窗口', align: 'center', class: 'w-24' },
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
  form.title = { ...EMPTY_I18N_DICT }
  form.subtitle = { ...EMPTY_I18N_DICT }
  form.cta_text = { ...EMPTY_I18N_DICT }
  form.cta_url = ''
  form.cta_secondary_text = { ...EMPTY_I18N_DICT }
  form.cta_secondary_url = ''
  form.media_type = 'image'
  form.media_url = ''
  form.poster_url = ''
  form.overlay_color = '#000000'
  form.overlay_opacity = 45
  form.text_align = 'left'
  form.text_color = 'light'
  form.sort_order = slides.value.length
  form.start_time = ''
  form.end_time = ''
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
  form.cta_url = slide.cta_url ?? ''
  form.cta_secondary_text = toDict(slide.cta_secondary_text)
  form.cta_secondary_url = slide.cta_secondary_url ?? ''
  form.media_type = slide.media_type ?? 'image'
  form.media_url = slide.media_url
  form.poster_url = slide.poster_url ?? ''
  form.overlay_color = HEX_RE.test(slide.overlay_color ?? '') ? slide.overlay_color : '#000000'
  form.overlay_opacity = slide.overlay_opacity ?? 45
  form.text_align = slide.text_align ?? 'left'
  // 缺省必须是 light：库里历史行的 text_color 全是 'light'（列默认值），
  // 而首页今天的观感就是白字——判成别的值等于替所有既有幻灯片换一次皮肤。
  form.text_color = slide.text_color ?? 'light'
  form.sort_order = slide.sort_order ?? 0
  // 后端给的是带偏移的 ISO，datetime-local 输入框要本地墙钟字符串
  form.start_time = toDateTimeLocal(slide.start_time)
  form.end_time = toDateTimeLocal(slide.end_time)
  form.is_active = slide.is_active
  editingId.value = slide.id
  dialogOpen.value = true
}

const mediaFileInput = ref<HTMLInputElement | null>(null)
const posterFileInput = ref<HTMLInputElement | null>(null)
// 两个上传框共用一个隐藏 input 的处理函数，靠这里区分落点。
const uploadTarget = ref<'media' | 'poster'>('media')

function pickImage(target: 'media' | 'poster') {
  uploadTarget.value = target
  if (target === 'poster') posterFileInput.value?.click()
  else mediaFileInput.value?.click()
}

async function onImageChosen(event: Event) {
  const input = event.target as HTMLInputElement
  const file = input.files?.[0]
  input.value = ''
  if (!file) return
  uploading.value = true
  try {
    const result = await useMediaUploadCover(file)
    if (result?.url) {
      if (uploadTarget.value === 'poster') form.poster_url = result.url
      else form.media_url = result.url
    }
  } catch (err) {
    // 失败提示由 apiFetch 统一 toast
    console.error('upload hero image error', err)
  } finally {
    uploading.value = false
  }
}

// 预览与缩略图同源：图片用 media_url，视频/YouTube 用封面（YouTube 无封面时回落官方缩略图）。
const heroPreviewSrc = computed(() =>
  heroThumbUrl({ media_type: form.media_type, media_url: form.media_url, poster_url: form.poster_url })
)
const mediaUrlLabel = computed(() => {
  if (form.media_type === 'video') return '视频地址（站内路径，如 /media/xxx.mp4）'
  if (form.media_type === 'youtube') return 'YouTube 链接或视频 ID'
  return '背景图片'
})
const mediaUrlPlaceholder = computed(() => {
  if (form.media_type === 'video') return '/media/2026/01/hero.mp4'
  if (form.media_type === 'youtube') return 'https://www.youtube.com/watch?v=xxxxxxxxxxx'
  return '也可直接粘贴图片 URL'
})

async function save() {
  // 与后端 validate_media_pair 同文案：外链视频会被 CSP 拦成一片黑，
  // 解析不出 ID 的 YouTube 地址存进去就是一块空白 iframe——都在提交前说清楚。
  const mediaError = heroMediaError(form.media_type, form.media_url)
  if (mediaError) {
    toast.error(mediaError)
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
  // 倒挂窗口存得进库、公开口却永远不下发（后端同判据再拦一次，这里是让原因在提交前就看见）。
  const scheduleError = announcementScheduleError(form.start_time, form.end_time)
  if (scheduleError) {
    toast.error(scheduleError)
    return
  }
  const payload: AdminHeroSlidePayload = {
    title: fromDict(form.title),
    subtitle: fromDict(form.subtitle),
    cta_text: fromDict(form.cta_text),
    cta_url: form.cta_url.trim() || null,
    cta_secondary_text: fromDict(form.cta_secondary_text),
    cta_secondary_url: form.cta_secondary_url.trim() || null,
    media_url: form.media_url.trim(),
    media_type: form.media_type,
    // 图片档不带封面：切回 image 时显式清掉旧值，否则历史 poster 会顶掉背景图。
    poster_url: form.media_type === 'image' ? null : (form.poster_url.trim() || null),
    overlay_color: form.overlay_color,
    overlay_opacity: Math.round(opacity),
    text_align: form.text_align,
    text_color: form.text_color,
    sort_order: Number(form.sort_order) || 0,
    // 空串必须转成 null：后端只接受 datetime 或 null，传 '' 会被 Pydantic 判成非法 datetime 撞 422；
    // 而显式 null 在 exclude_unset 下会保留，正好表达"清除排期＝长期生效"。
    start_time: fromDateTimeLocal(form.start_time),
    end_time: fromDateTimeLocal(form.end_time),
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
        size="sm"
        class="shadow-sm"
        @click="openNew"
      >
        <Plus data-icon="inline-start" />
        新建幻灯片
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
            v-if="heroThumbUrl(row as AdminHeroSlide)"
            :src="heroThumbUrl(row as AdminHeroSlide) ?? ''"
            :alt="getLocalizedStr(toDict((row as AdminHeroSlide).title)) || '幻灯片背景'"
            class="size-full object-cover"
            loading="lazy"
          >
          <span
            v-else
            class="text-xs text-muted-foreground"
          >{{ (row as AdminHeroSlide).media_type === 'video' ? '无封面' : '无图' }}</span>
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
      <template #cell-schedule="{ row }">
        <Badge :variant="announcementStatus(row as AdminHeroSlide) === 'active' ? 'secondary' : 'outline'">
          {{ SCHEDULE_LABEL[announcementStatus(row as AdminHeroSlide)] }}
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
        <AdminRowActions
          :actions="[
            { key: 'edit', label: '编辑幻灯片', icon: Pencil, onClick: () => openEdit(row as AdminHeroSlide) },
            { key: 'delete', label: '删除幻灯片', icon: Trash2, destructive: true, onClick: () => confirmDelete((row as AdminHeroSlide).id) }
          ]"
        />
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
          <Label class="mb-1 block text-xs text-muted-foreground">媒体类型</Label>
          <div class="flex gap-2">
            <Button
              v-for="opt in MEDIA_TYPE_OPTIONS"
              :key="opt.value"
              type="button"
              size="sm"
              class="h-9 rounded-[10px]"
              :variant="form.media_type === opt.value ? 'default' : 'outline'"
              @click="form.media_type = opt.value"
            >
              {{ opt.label }}
            </Button>
          </div>
        </div>

        <div>
          <Label class="mb-1 block text-xs text-muted-foreground">{{ mediaUrlLabel }}</Label>
          <div class="flex items-start gap-3">
            <div class="size-24 shrink-0 rounded-lg overflow-hidden border border-border bg-muted/30 flex items-center justify-center">
              <img
                v-if="heroPreviewSrc"
                :src="heroPreviewSrc"
                alt="幻灯片媒体预览"
                class="size-full object-cover"
              >
              <span
                v-else
                class="px-2 text-center text-xs text-muted-foreground"
              >{{ form.media_type === 'video' ? '无封面' : '未选择' }}</span>
            </div>
            <div class="flex flex-1 flex-col gap-2">
              <Button
                v-if="form.media_type === 'image'"
                type="button"
                variant="outline"
                size="sm"
                class="rounded-[10px] h-9 w-fit"
                :disabled="uploading"
                @click="pickImage('media')"
              >
                {{ uploading ? '上传中...' : (form.media_url ? '更换图片' : '上传图片') }}
              </Button>
              <Input
                v-model="form.media_url"
                :placeholder="mediaUrlPlaceholder"
                class="h-9 rounded-[10px] font-mono text-xs"
              />
              <input
                ref="mediaFileInput"
                type="file"
                accept="image/*"
                class="hidden"
                @change="onImageChosen"
              >
            </div>
          </div>
        </div>

        <div v-if="form.media_type !== 'image'">
          <Label class="mb-1 block text-xs text-muted-foreground">封面图（可选）</Label>
          <div class="flex items-start gap-3">
            <div class="size-16 shrink-0 rounded-lg overflow-hidden border border-border bg-muted/30 flex items-center justify-center">
              <img
                v-if="form.poster_url"
                :src="form.poster_url"
                alt="封面预览"
                class="size-full object-cover"
              >
              <span
                v-else
                class="px-1 text-center text-xs text-muted-foreground"
              >无封面</span>
            </div>
            <div class="flex flex-1 flex-col gap-2">
              <Button
                type="button"
                variant="outline"
                size="sm"
                class="rounded-[10px] h-9 w-fit"
                :disabled="uploading"
                @click="pickImage('poster')"
              >
                {{ uploading ? '上传中...' : (form.poster_url ? '更换封面' : '上传封面') }}
              </Button>
              <Input
                v-model="form.poster_url"
                placeholder="也可直接粘贴图片 URL"
                class="h-9 rounded-[10px] font-mono text-xs"
              />
              <p class="text-xs text-muted-foreground">
                <template v-if="form.media_type === 'video'">
                  视频播放前与后台缩略图用这张；不填则缩略图只有序号。
                </template>
                <template v-else>
                  不填则自动使用 YouTube 官方缩略图。
                </template>
              </p>
              <input
                ref="posterFileInput"
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

        <I18nTabsEditor
          v-model="form.cta_secondary_text"
          kind="text"
          label="次按钮文案（留空则显示「查看全部」）"
        />

        <div>
          <Label
            for="hero-form-secondary-cta"
            class="mb-1 block text-xs text-muted-foreground"
          >次按钮链接（留空则跳 /posts）</Label>
          <Input
            id="hero-form-secondary-cta"
            v-model="form.cta_secondary_url"
            placeholder="/series/your-series"
            class="h-9 rounded-[10px]"
          />
        </div>

        <div class="grid grid-cols-2 gap-3">
          <div class="flex flex-col gap-2">
            <Label
              for="hero-form-start"
              class="text-xs text-muted-foreground"
            >
              生效开始（留空＝立即）
            </Label>
            <div class="flex gap-1">
              <Input
                id="hero-form-start"
                v-model="form.start_time"
                type="datetime-local"
              />
              <Button
                v-if="form.start_time"
                variant="ghost"
                size="icon-sm"
                title="清除开始时间"
                aria-label="清除开始时间"
                @click="form.start_time = ''"
              >
                <X data-icon="inline-start" />
              </Button>
            </div>
          </div>
          <div class="flex flex-col gap-2">
            <Label
              for="hero-form-end"
              class="text-xs text-muted-foreground"
            >
              生效结束（留空＝长期）
            </Label>
            <div class="flex gap-1">
              <Input
                id="hero-form-end"
                v-model="form.end_time"
                type="datetime-local"
              />
              <Button
                v-if="form.end_time"
                variant="ghost"
                size="icon-sm"
                title="清除结束时间"
                aria-label="清除结束时间"
                @click="form.end_time = ''"
              >
                <X data-icon="inline-start" />
              </Button>
            </div>
          </div>
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
          <Label class="mb-1 block text-xs text-muted-foreground">文字色调</Label>
          <div class="flex gap-2">
            <Button
              v-for="opt in TONE_OPTIONS"
              :key="opt.value"
              type="button"
              size="sm"
              class="h-9 rounded-[10px]"
              :variant="form.text_color === opt.value ? 'default' : 'outline'"
              @click="form.text_color = opt.value"
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
