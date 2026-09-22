<script setup lang="ts">
import { ref, reactive, computed, watch, onMounted, onBeforeUnmount, nextTick } from 'vue'
import type { Post, PostCreate } from '~~/types/api'
import I18nTabsEditor from './I18nTabsEditor.vue'
import { usePosts } from '~~/composables/usePosts'
import {
  fetchAdminCategories,
  fetchAdminTags,
  type AdminCategory,
  type AdminTag
} from '~~/composables/useAdminManage'
import { useMediaUploadCover } from '~~/composables/useMedia'
import { useToast } from '~~/composables/useToast'
import { getLocalizedStr, normalizeI18nDict, toI18nPayload, slugify } from '~~/composables/useAdminI18n'
import { Button } from '~~/components/ui/button'
import { Input } from '~~/components/ui/input'
import { Label } from '~~/components/ui/label'
import AdminCard from './AdminCard.vue'
import { Badge } from '~~/components/ui/badge'
import { Switch } from '~~/components/ui/switch'
import { Alert, AlertTitle, AlertDescription } from '~~/components/ui/alert'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue
} from '~~/components/ui/select'
import {
  Globe,
  Lock,
  EyeOff,
  Check,
  X,
  Image as ImageIcon,
  Save,
  Send,
  Eye
} from '@lucide/vue'

const props = defineProps<{
  mode: 'new' | 'edit'
  postId?: number
  initialData?: Post | null
}>()

const emits = defineEmits<{
  submitSuccess: [payload: unknown, isNew: boolean]
}>()

const toast = useToast()
const { createPost, updatePost } = usePosts()

const draftLocalStorageKey = computed(() =>
  `admin_post_draft_${props.mode}_${props.postId || 'new'}`
)

const form = reactive({
  title: { zh: '', en: '', ja: '', zh_Hant: '' } as Record<string, string>,
  slug: '',
  content: { zh: '', en: '', ja: '', zh_Hant: '' } as Record<string, string>,
  status: 'draft' as 'draft' | 'published' | 'scheduled' | 'archived',
  scheduled_at: '',
  is_pinned: false,
  allow_comments: true,
  visibility: 'public' as 'public' | 'password' | 'private',
  password: '',
  category_id: null as number | null,
  tag_ids: [] as number[],
  excerpt: { zh: '', en: '', ja: '', zh_Hant: '' } as Record<string, string>,
  cover_image: '',
  meta_title: { zh: '', en: '', ja: '', zh_Hant: '' } as Record<string, string>,
  meta_description: { zh: '', en: '', ja: '', zh_Hant: '' } as Record<string, string>,
  meta_keywords: { zh: '', en: '', ja: '', zh_Hant: '' } as Record<string, string>
})

const initialStateSnapshot = ref<string>('')
const categories = ref<AdminCategory[]>([])
const tags = ref<AdminTag[]>([])
const categoriesLoading = ref(false)
const tagsLoading = ref(false)
const submitting = ref(false)
const savingDraft = ref(false)
const coverUploading = ref(false)
const tagComboboxOpen = ref(false)
const tagSearchQuery = ref('')
const draftExists = ref(false)
const draftSavedAt = ref<string | null>(null)
const coverInputRef = ref<HTMLInputElement | null>(null)
const tagComboboxRef = ref<HTMLDivElement | null>(null)

const isDirty = computed(() => {
  return JSON.stringify(form) !== initialStateSnapshot.value
})

const filteredTags = computed(() => {
  const q = tagSearchQuery.value.trim().toLowerCase()
  if (!q) return tags.value
  return tags.value.filter(t =>
    getLocalizedStr(t.name).toLowerCase().includes(q)
  )
})

const visibilityOptions = [
  { value: 'public' as const, label: '公开', description: '所有人可见', icon: Globe },
  { value: 'password' as const, label: '密码保护', description: '需要密码才能查看', icon: Lock },
  { value: 'private' as const, label: '私密', description: '仅管理员可见', icon: EyeOff }
]

let slugManualEdit = false
watch(
  () => form.title.zh,
  (val) => {
    if (!slugManualEdit && val) {
      form.slug = slugify(val)
    }
  }
)

const handleSlugInput = () => {
  slugManualEdit = true
}

const loadCategories = async () => {
  categoriesLoading.value = true
  try {
    categories.value = await fetchAdminCategories()
  } catch (e) {
    toast.error(e instanceof Error ? e.message : '加载分类失败')
  } finally {
    categoriesLoading.value = false
  }
}

const loadTags = async () => {
  tagsLoading.value = true
  try {
    tags.value = await fetchAdminTags()
  } catch (e) {
    toast.error(e instanceof Error ? e.message : '加载标签失败')
  } finally {
    tagsLoading.value = false
  }
}

const applyInitialData = (data: Post) => {
  form.title = normalizeI18nDict(data.title)
  form.slug = data.slug
  form.content = normalizeI18nDict(data.content)
  form.status = data.status
  form.is_pinned = data.is_pinned
  form.allow_comments = data.allow_comments
  form.visibility = data.is_password_protected ? 'password' : 'public'
  form.category_id = data.category?.id ?? null
  form.tag_ids = data.tags ? data.tags.map(t => t.id) : []
  form.excerpt = normalizeI18nDict(data.excerpt)
  form.cover_image = data.cover_image || ''
  form.meta_title = normalizeI18nDict(data.meta_title)
  form.meta_description = normalizeI18nDict(data.meta_description)
  form.meta_keywords = normalizeI18nDict(data.meta_keywords)
  slugManualEdit = !!data.slug
  nextTick(() => {
    initialStateSnapshot.value = JSON.stringify(form)
  })
}

const saveDraftToLocalStorage = () => {
  try {
    const payload = {
      form: { ...form },
      savedAt: new Date().toISOString()
    }
    localStorage.setItem(draftLocalStorageKey.value, JSON.stringify(payload))
    draftSavedAt.value = payload.savedAt
  } catch (e) {
    console.warn('保存草稿失败', e)
  }
}

let draftDebounceTimer: ReturnType<typeof setTimeout> | null = null
watch(
  () => ({ ...form }),
  () => {
    if (draftDebounceTimer) clearTimeout(draftDebounceTimer)
    draftDebounceTimer = setTimeout(() => {
      saveDraftToLocalStorage()
    }, 8000)
  },
  { deep: true }
)

const checkExistingDraft = () => {
  try {
    const raw = localStorage.getItem(draftLocalStorageKey.value)
    if (raw) {
      const parsed = JSON.parse(raw)
      if (parsed?.form) {
        draftExists.value = true
        draftSavedAt.value = parsed.savedAt || null
      }
    }
  } catch (e) {
    console.warn('读取草稿失败', e)
  }
}

const restoreDraft = () => {
  try {
    const raw = localStorage.getItem(draftLocalStorageKey.value)
    if (raw) {
      const parsed = JSON.parse(raw)
      if (parsed?.form) {
        Object.assign(form, parsed.form)
        form.title = normalizeI18nDict(form.title)
        form.content = normalizeI18nDict(form.content)
        form.excerpt = normalizeI18nDict(form.excerpt)
        form.meta_title = normalizeI18nDict(form.meta_title)
        form.meta_description = normalizeI18nDict(form.meta_description)
        form.meta_keywords = normalizeI18nDict(form.meta_keywords)
        slugManualEdit = !!form.slug
        toast.success('草稿已恢复')
      }
    }
  } catch {
    toast.error('恢复草稿失败')
  }
  draftExists.value = false
}

const discardDraft = () => {
  try {
    localStorage.removeItem(draftLocalStorageKey.value)
  } catch (e) {
    console.warn('丢弃草稿失败', e)
  }
  draftExists.value = false
  toast.info('已丢弃草稿')
}

const isTagSelected = (id: number) => form.tag_ids.includes(id)

const toggleTag = (id: number) => {
  const idx = form.tag_ids.indexOf(id)
  if (idx === -1) {
    form.tag_ids.push(id)
  } else {
    form.tag_ids.splice(idx, 1)
  }
}

const removeTag = (id: number) => {
  const idx = form.tag_ids.indexOf(id)
  if (idx !== -1) form.tag_ids.splice(idx, 1)
}

const getTagById = (id: number): AdminTag | undefined => tags.value.find(t => t.id === id)

const handleCoverUpload = async (e: Event) => {
  const input = e.target as HTMLInputElement
  const file = input.files?.[0]
  if (!file) return
  coverUploading.value = true
  try {
    const res = await useMediaUploadCover(file)
    if (res?.url) {
      form.cover_image = res.url
      toast.success('封面上传成功')
    } else {
      toast.error('封面上传失败')
    }
  } catch (e) {
    toast.error(e instanceof Error ? e.message : '封面上传失败')
  } finally {
    coverUploading.value = false
    input.value = ''
  }
}

const clearCover = () => {
  form.cover_image = ''
}

const buildPayload = (overrideStatus?: string): PostCreate => {
  const payload: PostCreate = {
    title: (toI18nPayload(form.title) ?? { zh: form.title.zh }) as Record<string, string>,
    slug: form.slug,
    content: (toI18nPayload(form.content) ?? { zh: form.content.zh }) as Record<string, string>,
    status: (overrideStatus as PostCreate['status']) || form.status,
    is_pinned: form.is_pinned,
    allow_comments: form.allow_comments,
    category_id: form.category_id || undefined,
    tag_ids: form.tag_ids,
    excerpt: toI18nPayload(form.excerpt),
    cover_image: form.cover_image || undefined
  }
  if (form.status === 'scheduled' && form.scheduled_at) {
    payload.scheduled_at = form.scheduled_at
  }
  if (form.visibility === 'password' && form.password) {
    payload.password = form.password
  }
  payload.meta_title = toI18nPayload(form.meta_title)
  payload.meta_description = toI18nPayload(form.meta_description)
  payload.meta_keywords = toI18nPayload(form.meta_keywords)
  return payload
}

const validateBase = (): boolean => {
  if (!form.title.zh?.trim()) {
    toast.error('请输入文章标题（简体中文为主语言）')
    return false
  }
  if (!form.slug.trim()) {
    toast.error('请输入文章 slug')
    return false
  }
  if (!form.content.zh?.trim()) {
    toast.error('请输入文章内容（简体中文为主语言）')
    return false
  }
  if (form.status === 'scheduled' && !form.scheduled_at) {
    toast.error('请选择定时发布时间')
    return false
  }
  if (form.visibility === 'password' && !form.password.trim()) {
    toast.error('请输入访问密码')
    return false
  }
  return true
}

const saveDraft = async () => {
  if (!validateBase()) return
  savingDraft.value = true
  try {
    const payload = buildPayload('draft')
    if (props.mode === 'new') {
      const data = await createPost(payload)
      toast.success('草稿保存成功')
      emits('submitSuccess', data, true)
    } else if (props.postId) {
      const data = await updatePost(props.postId, payload)
      toast.success('草稿保存成功')
      emits('submitSuccess', data, false)
    }
  } catch (e) {
    toast.error(e instanceof Error ? e.message : '保存草稿失败')
  } finally {
    savingDraft.value = false
  }
}

const publishPost = async () => {
  if (!validateBase()) return
  submitting.value = true
  try {
    const publishStatus = form.status === 'archived' ? 'archived' : form.status
    const payload = buildPayload(publishStatus)
    if (props.mode === 'new') {
      const data = await createPost(payload)
      localStorage.removeItem(draftLocalStorageKey.value)
      emits('submitSuccess', data, true)
    } else if (props.postId) {
      const data = await updatePost(props.postId, payload)
      localStorage.removeItem(draftLocalStorageKey.value)
      emits('submitSuccess', data, false)
    }
  } catch (e) {
    toast.error(e instanceof Error ? e.message : '发布失败')
  } finally {
    submitting.value = false
  }
}

const openPreview = () => {
  if (form.slug) {
    window.open(`/posts/${form.slug}`, '_blank')
  } else {
    toast.warning('请先输入 slug 后再预览')
  }
}

const onKeyDown = (e: KeyboardEvent) => {
  if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 's') {
    e.preventDefault()
    saveDraft()
  }
}

const onBeforeUnload = (e: BeforeUnloadEvent) => {
  if (isDirty.value) {
    e.preventDefault()
    e.returnValue = '您有未保存的更改，确定要离开吗？'
    return e.returnValue
  }
}

const onTagComboboxBlur = () => {
  setTimeout(() => {
    tagComboboxOpen.value = false
    tagSearchQuery.value = ''
  }, 200)
}

const onClickOutsideTagCombobox = (e: MouseEvent) => {
  if (tagComboboxRef.value && !tagComboboxRef.value.contains(e.target as Node)) {
    tagComboboxOpen.value = false
    tagSearchQuery.value = ''
  }
}

watch(
  () => props.initialData,
  (val) => {
    if (val && !hasAppliedInitial.value) {
      applyInitialData(val)
      hasAppliedInitial.value = true
    }
  },
  { immediate: false }
)

const hasAppliedInitial = ref(false)

onMounted(async () => {
  document.addEventListener('keydown', onKeyDown)
  window.addEventListener('beforeunload', onBeforeUnload as EventListener)
  document.addEventListener('click', onClickOutsideTagCombobox)

  checkExistingDraft()
  await Promise.all([loadCategories(), loadTags()])

  if (props.initialData) {
    applyInitialData(props.initialData)
    hasAppliedInitial.value = true
  } else {
    initialStateSnapshot.value = JSON.stringify(form)
  }
})

onBeforeUnmount(() => {
  document.removeEventListener('keydown', onKeyDown)
  window.removeEventListener('beforeunload', onBeforeUnload as EventListener)
  document.removeEventListener('click', onClickOutsideTagCombobox)
  if (draftDebounceTimer) clearTimeout(draftDebounceTimer)
  saveDraftToLocalStorage()
})
</script>

<template>
  <div class="flex flex-col gap-4">
    <Alert
      v-if="draftExists"
      variant="warning"
      class="rounded-[12px]"
    >
      <AlertTitle class="font-semibold">
        发现未保存草稿
        <span
          v-if="draftSavedAt"
          class="text-sm font-normal opacity-70 ml-2"
        >
          {{ new Date(draftSavedAt).toLocaleString('zh-CN') }}
        </span>
      </AlertTitle>
      <AlertDescription class="mt-1">
        <div class="flex items-center gap-3">
          <span>是否恢复上次编辑的内容？</span>
          <Button
            variant="default"
            size="sm"
            class="rounded-[10px] h-8 text-xs"
            @click="restoreDraft"
          >
            恢复草稿
          </Button>
          <Button
            variant="ghost"
            size="sm"
            class="rounded-[10px] h-8 text-xs"
            @click="discardDraft"
          >
            丢弃
          </Button>
        </div>
      </AlertDescription>
    </Alert>

    <div class="flex flex-col gap-2">
      <I18nTabsEditor
        v-model="form.title"
        kind="text"
        label="标题"
        placeholder="输入文章标题"
        required
      />
      <Input
        v-model="form.slug"
        placeholder="slug（自动生成，可手动修改）"
        class="h-9 rounded-[10px] text-sm"
        @input="handleSlugInput"
      />
    </div>

    <div class="flex flex-col lg:flex-row gap-4">
      <div class="flex-1 lg:w-3/5 min-w-0">
        <I18nTabsEditor
          v-model="form.content"
          kind="markdown"
          label="正文"
          placeholder="开始撰写文章内容"
          required
        />
      </div>

      <div class="w-full lg:w-2/5">
        <div class="lg:sticky lg:top-4 lg:self-start flex flex-col gap-4 max-h-[calc(100vh-120px)] overflow-y-auto pr-1 scrollbar-thin">
          <AdminCard class="p-5 flex flex-col gap-4">
            <div>
              <Label class="mb-1.5 block text-sm font-medium">发布设置</Label>
              <div class="flex flex-col gap-3">
                <div>
                  <Label class="text-xs text-muted-foreground mb-1 block">状态 *</Label>
                  <Select v-model="form.status">
                    <SelectTrigger class="h-9 rounded-[10px]">
                      <SelectValue placeholder="选择状态" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="draft">
                        草稿
                      </SelectItem>
                      <SelectItem value="published">
                        已发布
                      </SelectItem>
                      <SelectItem value="scheduled">
                        定时发布
                      </SelectItem>
                      <SelectItem value="archived">
                        已归档
                      </SelectItem>
                    </SelectContent>
                  </Select>
                </div>
                <div v-if="form.status === 'scheduled'">
                  <Label class="text-xs text-muted-foreground mb-1 block">定时时间 *</Label>
                  <Input
                    v-model="form.scheduled_at"
                    type="datetime-local"
                    class="h-9 rounded-[10px] text-sm"
                  />
                </div>
                <div class="flex items-center justify-between">
                  <Label class="text-sm">置顶</Label>
                  <Switch v-model="form.is_pinned" />
                </div>
                <div class="flex items-center justify-between">
                  <Label class="text-sm">允许评论</Label>
                  <Switch v-model="form.allow_comments" />
                </div>
              </div>
            </div>

            <div class="h-px bg-border" />

            <div>
              <Label class="mb-2 block text-sm font-medium">可见性</Label>
              <div class="flex flex-col gap-1.5">
                <label
                  v-for="opt in visibilityOptions"
                  :key="opt.value"
                  class="flex items-start gap-3 rounded-[10px] border px-3 py-2.5 cursor-pointer transition-colors"
                  :class="form.visibility === opt.value
                    ? 'border-primary bg-primary/5'
                    : 'border-transparent hover:bg-muted/50'"
                >
                  <div class="mt-0.5">
                    <div
                      class="size-4 rounded-full border-2 flex items-center justify-center transition-colors"
                      :class="form.visibility === opt.value
                        ? 'border-primary'
                        : 'border-muted-foreground/40'"
                    >
                      <div
                        v-if="form.visibility === opt.value"
                        class="size-2 rounded-full bg-primary"
                      />
                    </div>
                    <input
                      v-model="form.visibility"
                      type="radio"
                      :value="opt.value"
                      class="sr-only"
                    >
                  </div>
                  <div class="flex-1 min-w-0">
                    <div class="flex items-center gap-1.5">
                      <component
                        :is="opt.icon"
                        class="size-3.5 text-muted-foreground"
                      />
                      <span class="text-sm font-medium">{{ opt.label }}</span>
                    </div>
                    <div class="text-xs text-muted-foreground mt-0.5">
                      {{ opt.description }}
                    </div>
                  </div>
                </label>
              </div>
              <div
                v-if="form.visibility === 'password'"
                class="mt-2"
              >
                <Input
                  v-model="form.password"
                  type="password"
                  placeholder="访问密码"
                  class="h-9 rounded-[10px] text-sm"
                />
              </div>
            </div>

            <div class="h-px bg-border" />

            <div>
              <Label class="text-xs text-muted-foreground mb-1 block">分类</Label>
              <Select
                :model-value="form.category_id?.toString() ?? ''"
                @update:model-value="(v: string | undefined) => form.category_id = v ? Number(v) : null"
              >
                <SelectTrigger class="h-9 rounded-[10px]">
                  <SelectValue :placeholder="categoriesLoading ? '加载中...' : '选择分类'" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="">
                    无分类
                  </SelectItem>
                  <SelectItem
                    v-for="c in categories"
                    :key="c.id"
                    :value="c.id.toString()"
                  >
                    <div class="flex items-center gap-2">
                      <span
                        class="size-2.5 rounded-full inline-block"
                        :style="{ background: c.color || '#94a3b8' }"
                      />
                      {{ getLocalizedStr(c.name) }}
                    </div>
                  </SelectItem>
                </SelectContent>
              </Select>
            </div>

            <div ref="tagComboboxRef">
              <Label class="text-xs text-muted-foreground mb-1 block">标签</Label>
              <div class="relative">
                <div
                  class="min-h-9 px-2.5 py-1.5 rounded-[10px] border border-input bg-background flex flex-wrap gap-1.5 items-center cursor-text transition-colors"
                  :class="tagComboboxOpen ? 'ring-2 ring-ring ring-offset-0' : ''"
                  @click="tagComboboxOpen = true"
                >
                  <template v-if="form.tag_ids.length === 0 && !tagSearchQuery">
                    <span class="text-sm text-muted-foreground px-1">
                      {{ tagsLoading ? '加载中...' : '点击添加标签...' }}
                    </span>
                  </template>
                  <Badge
                    v-for="tagId in form.tag_ids"
                    :key="tagId"
                    variant="secondary"
                    class="rounded-[10px] px-2 py-0.5 flex items-center gap-1"
                  >
                    {{ getTagById(tagId) ? getLocalizedStr(getTagById(tagId)!.name) : tagId }}
                    <button
                      type="button"
                      class="ml-0.5 rounded-full hover:bg-muted-foreground/20 p-0.5 transition-colors"
                      @click.stop="removeTag(tagId)"
                    >
                      <X class="size-3" />
                    </button>
                  </Badge>
                  <input
                    v-if="tagComboboxOpen"
                    v-model="tagSearchQuery"
                    type="text"
                    class="flex-1 min-w-20 bg-transparent outline-none text-sm px-1"
                    placeholder="搜索标签..."
                    @blur="onTagComboboxBlur"
                  >
                </div>
                <div
                  v-if="tagComboboxOpen"
                  class="absolute z-20 top-full mt-1 w-full max-h-56 overflow-y-auto rounded-[10px] border border-border bg-card shadow-lg p-1"
                >
                  <div
                    v-for="t in filteredTags"
                    :key="t.id"
                    class="flex items-center justify-between px-2.5 py-2 rounded-md text-sm cursor-pointer transition-colors hover:bg-accent"
                    :class="{ 'bg-accent/50': isTagSelected(t.id) }"
                    @mousedown.prevent="toggleTag(t.id)"
                  >
                    <div class="flex items-center gap-2">
                      <span
                        class="size-2 rounded-full inline-block"
                        :style="{ background: t.color || '#94a3b8' }"
                      />
                      {{ getLocalizedStr(t.name) }}
                      <span class="text-xs text-muted-foreground">({{ t.post_count }})</span>
                    </div>
                    <Check
                      v-if="isTagSelected(t.id)"
                      class="size-3.5 text-primary"
                    />
                  </div>
                  <div
                    v-if="filteredTags.length === 0"
                    class="px-2.5 py-3 text-sm text-muted-foreground text-center"
                  >
                    无匹配标签
                  </div>
                </div>
              </div>
            </div>

            <div>
              <Label class="text-xs text-muted-foreground mb-1 block">摘要</Label>
              <I18nTabsEditor
                v-model="form.excerpt"
                kind="textarea"
                :rows="3"
                placeholder="输入文章摘要，不填则自动截取前 180 字"
              />
            </div>
          </AdminCard>

          <AdminCard class="p-5 flex flex-col gap-4">
            <div>
              <Label class="mb-2 block text-sm font-medium">封面图</Label>
              <div class="flex items-start gap-3">
                <div
                  v-if="form.cover_image"
                  class="w-[160px] h-[90px] rounded-[10px] overflow-hidden border border-border bg-muted"
                >
                  <img
                    :src="form.cover_image"
                    alt="cover"
                    class="size-full object-cover"
                  >
                </div>
                <div
                  v-else
                  class="w-[160px] h-[90px] rounded-[10px] border border-dashed border-border bg-muted/30 flex items-center justify-center"
                >
                  <ImageIcon class="size-5 text-muted-foreground/50" />
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
          </AdminCard>

          <AdminCard class="p-5 flex flex-col gap-3">
            <Label class="text-sm font-medium">SEO 设置</Label>
            <I18nTabsEditor
              v-model="form.meta_title"
              kind="text"
              label="Meta Title"
              placeholder="SEO 标题"
            />
            <I18nTabsEditor
              v-model="form.meta_description"
              kind="text"
              label="Meta Description"
              placeholder="SEO 描述"
            />
            <I18nTabsEditor
              v-model="form.meta_keywords"
              kind="text"
              label="Meta Keywords"
              placeholder="SEO 关键词，逗号分隔"
            />
          </AdminCard>
        </div>
      </div>
    </div>

    <div class="flex items-center justify-between pt-2 border-t border-border">
      <Button
        type="button"
        variant="outline"
        class="rounded-[12px] h-11 px-6 gap-2"
        :disabled="savingDraft || submitting"
        @click="saveDraft"
      >
        <Save
          data-icon="inline-start"
          class="size-4"
        />
        {{ savingDraft ? '保存中...' : '保存草稿' }}
      </Button>
      <div class="flex items-center gap-2">
        <Button
          type="button"
          variant="ghost"
          class="rounded-[12px] h-11 px-5 gap-2"
          @click="openPreview"
        >
          <Eye
            data-icon="inline-start"
            class="size-4"
          />
          预览
        </Button>
        <Button
          type="button"
          class="rounded-[12px] h-11 px-7 gap-2"
          :disabled="submitting || savingDraft"
          @click="publishPost"
        >
          <Send
            data-icon="inline-start"
            class="size-4"
          />
          {{ submitting ? '发布中...' : '发布文章' }}
        </Button>
      </div>
    </div>
  </div>
</template>
