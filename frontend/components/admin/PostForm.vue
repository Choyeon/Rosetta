<!--
  后台文章编辑表单（new / [id]/edit 两页共用）：i18n 标题/正文/SEO 字段 + 发布设置 + 本地草稿。
  硬契约（都是踩过的坑，改前先读）：
  1. buildPayload 的后端语义不可破坏——PUT 是 exclude_unset 增量更新，
     visibility 必须始终发送（否则"改回公开"永不落库）；password 为空时禁止发送该键
     （后端收到 password:'' 会清空已有密码哈希）。
  2. **要能被清掉的字段必须显式发送空值**。cover_image / category_id 写成 `|| undefined`
     会被 JSON.stringify 丢掉，后端 exclude_unset 就当这个键没出现过 —— 表现是
     「清除封面」「无分类」点了没反应。空字符串 / null 才是"清空"的语义。
  3. **scheduled_at 是本地墙钟，后端按 UTC 解释朴素时间**。回填必须用 toDateTimeLocal、
     提交必须用 fromDateTimeLocal，直接 slice(0,16) 会让东八区的作者排期偏 8 小时。
-->
<script setup lang="ts">
import { ref, reactive, computed, watch, onMounted, onBeforeUnmount, nextTick } from 'vue'
import { useI18n } from 'vue-i18n'
import { onBeforeRouteLeave } from 'vue-router'
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
import { toDateTimeLocal, fromDateTimeLocal } from '~~/lib/datetime'
import { estimateContentStats, slugSourceTitle, scheduledAtError } from '~~/lib/postEditor'
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

const { t: $_t } = useI18n()
const toast = useToast()
const { createPost, updatePost } = usePosts()

const draftLocalStorageKey = computed(() =>
  `admin_post_draft_${props.mode}_${props.postId || 'new'}`
)

const form = reactive({
  title: { zh: '', en: '', ja: '', zh_Hant: '' } as Record<string, string>,
  slug: '',
  content: { zh: '', en: '', ja: '', zh_Hant: '' } as Record<string, string>,
  // 后端 PostBase/PostUpdate 的 pattern 只接受 draft|published|scheduled，
  // 历史遗留的 archived 状态不可再作为可写值出现。
  status: 'draft' as 'draft' | 'published' | 'scheduled',
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

const slugSource = computed(() => slugSourceTitle(form.title))

const contentStats = computed(() => estimateContentStats(form.content.zh || ''))

const scheduledError = computed(() => scheduledAtError(form.status, fromDateTimeLocal(form.scheduled_at)))

let slugManualEdit = false
// 只盯 form.title.zh 时，作者先写英文（或繁体）标题就永远拿不到 slug，然后被
// "请输入 slug" 卡住。取"约定顺序里第一个非空的语言"，zh 仍是首选。
watch(slugSource, (val) => {
  if (!slugManualEdit && val) {
    form.slug = slugify(val)
  }
})

const handleSlugInput = () => {
  slugManualEdit = true
}

const loadCategories = async () => {
  categoriesLoading.value = true
  try {
    categories.value = await fetchAdminCategories()
  } catch {
    // apiFetch 已统一 toast 错误，不再二次弹
  } finally {
    categoriesLoading.value = false
  }
}

const loadTags = async () => {
  tagsLoading.value = true
  try {
    tags.value = await fetchAdminTags()
  } catch {
    // apiFetch 已统一 toast 错误，不再二次弹
  } finally {
    tagsLoading.value = false
  }
}

const applyInitialData = (data: Post) => {
  form.title = normalizeI18nDict(data.title)
  form.slug = data.slug
  form.content = normalizeI18nDict(data.content)
  form.status = data.status === 'archived' ? 'draft' : data.status
  // 定时文章必须回填计划时间：后端 GET 现已透传 scheduled_at，
  // 不回填则编辑一次就把 scheduled_at 提交为空、文章永远发不出去。
  // 走 toDateTimeLocal 而不是 slice(0,16)：库里存的是 UTC，datetime-local 要的是本地墙钟。
  form.scheduled_at = toDateTimeLocal(data.scheduled_at)
  form.is_pinned = data.is_pinned
  form.allow_comments = data.allow_comments
  // 优先读 staff 端点透传的 visibility（private 文章只靠 is_password_protected
  // 会被错误还原成 public，保存后把私密文章变公开）
  const vis = data.visibility
  form.visibility = vis === 'public' || vis === 'password' || vis === 'private'
    ? vis
    : (data.is_password_protected ? 'password' : 'public')
  initiallyPasswordProtected.value = form.visibility === 'password'
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
  } catch {
    // apiFetch 已统一 toast 错误，不再二次弹
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
    // 必发：后端 PUT 是 exclude_unset 增量语义，不发送 visibility 时
    // 「密码/私密 → 公开」的切换永远不会落库（表单显示公开、库里仍保护）
    visibility: form.visibility,
    is_pinned: form.is_pinned,
    allow_comments: form.allow_comments,
    // 显式 null 而不是省略：省略 = "这个键没出现过"，后端 exclude_unset 就不会动它，
    // 于是「无分类」「清除封面」点了没反应。null / '' 才是"我要清掉它"。
    category_id: form.category_id ?? null,
    tag_ids: form.tag_ids,
    excerpt: toI18nPayload(form.excerpt),
    cover_image: form.cover_image ?? ''
  }
  if (form.status === 'scheduled' && form.scheduled_at) {
    // datetime-local 的取值是本地墙钟，转成带偏移的 ISO 后端才能按 UTC 正确落库
    payload.scheduled_at = fromDateTimeLocal(form.scheduled_at) ?? undefined
  }
  // 空密码不发送：后端收到 password:'' 会清空已有哈希；编辑态哈希不可读，
  // 只有用户明确重新输入时才更新
  if (form.visibility === 'password' && form.password.trim()) {
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
  // 后端会把"不晚于现在"的定时文章直接降级成立即发布，作者以为排好了、实际已经发出去了。
  // 这个偏差只能在提交前拦，发出去之后再解释就晚了。
  const schedErr = scheduledError.value
  if (schedErr) {
    toast.error(schedErr)
    return false
  }
  if (form.visibility === 'password' && !form.password.trim() && !initiallyPasswordProtected.value) {
    toast.error('请输入访问密码')
    return false
  }
  return true
}

// 提交成功后统一收尾：清 localStorage 草稿、停掉 8s 自动保存定时器、放行路由守卫
const markSubmitted = () => {
  submitted.value = true
  if (draftDebounceTimer) {
    clearTimeout(draftDebounceTimer)
    draftDebounceTimer = null
  }
  try {
    localStorage.removeItem(draftLocalStorageKey.value)
  } catch {
    /* storage disabled */
  }
}

const saveDraft = async () => {
  if (!validateBase()) return
  savingDraft.value = true
  try {
    const payload = buildPayload('draft')
    if (props.mode === 'new') {
      const data = await createPost(payload)
      markSubmitted()
      toast.success('草稿保存成功')
      emits('submitSuccess', data, true)
    } else if (props.postId) {
      const data = await updatePost(props.postId, payload)
      markSubmitted()
      toast.success('草稿保存成功')
      emits('submitSuccess', data, false)
    }
  } catch {
    // apiFetch 已统一 toast 错误，不再二次弹（双 toast 是回归）
  } finally {
    savingDraft.value = false
  }
}

const publishPost = async () => {
  if (!validateBase()) return
  submitting.value = true
  try {
    const payload = buildPayload(form.status)
    if (props.mode === 'new') {
      const data = await createPost(payload)
      markSubmitted()
      emits('submitSuccess', data, true)
    } else if (props.postId) {
      const data = await updatePost(props.postId, payload)
      markSubmitted()
      emits('submitSuccess', data, false)
    }
  } catch {
    // apiFetch 已统一 toast 错误，不再二次弹
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
  if (!submitted.value && isDirty.value) {
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
// 提交成功后置位：跳过卸载时的本地草稿自动保存，并放行路由离开守卫
const submitted = ref(false)
// 编辑源文章本就是密码保护时，允许不重填密码直接保存（后端保留原哈希）
const initiallyPasswordProtected = ref(false)

onBeforeRouteLeave(async () => {
  if (submitted.value || !isDirty.value) return true
  return window.confirm('您有未保存的更改，确定要离开吗？')
})

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
  // 已提交成功后卸载不应再把草稿写回 localStorage
  if (!submitted.value) saveDraftToLocalStorage()
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
      <div class="flex-1 lg:w-3/5 min-w-0 flex flex-col gap-1.5">
        <I18nTabsEditor
          v-model="form.content"
          kind="markdown"
          label="正文"
          placeholder="开始撰写文章内容"
          required
        />
        <p class="text-xs text-muted-foreground px-1">
          约 {{ contentStats.words }} 字 · 预计阅读 {{ contentStats.minutes }} 分钟
          <span class="opacity-60">（按当前语言标签统计，仅作参考）</span>
        </p>
      </div>

      <div class="w-full lg:w-2/5">
        <div class="lg:sticky lg:top-4 lg:self-start flex flex-col gap-4 max-h-[calc(100vh-120px)] overflow-y-auto pr-1 scrollbar-thin">
          <AdminCard class="p-5 flex flex-col gap-4">
            <div>
              <Label class="mb-1.5 block text-sm font-medium">发布设置</Label>
              <div class="flex flex-col gap-3">
                <div>
                  <Label
                    for="post-form-status"
                    class="text-xs text-muted-foreground mb-1 block"
                  >状态 *</Label>
                  <Select v-model="form.status">
                    <SelectTrigger
                      id="post-form-status"
                      class="h-9 rounded-[10px]"
                    >
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
                    </SelectContent>
                  </Select>
                </div>
                <div v-if="form.status === 'scheduled'">
                  <Label
                    for="post-form-scheduled-at"
                    class="text-xs text-muted-foreground mb-1 block"
                  >定时时间 *</Label>
                  <Input
                    id="post-form-scheduled-at"
                    v-model="form.scheduled_at"
                    type="datetime-local"
                    class="h-9 rounded-[10px] text-sm"
                  />
                  <p
                    v-if="scheduledError"
                    class="text-xs text-destructive mt-1"
                  >
                    {{ scheduledError }}
                  </p>
                  <p
                    v-else
                    class="text-xs text-muted-foreground mt-1"
                  >
                    按你所在时区填写，提交时会自动换算为 UTC
                  </p>
                </div>
                <div class="flex items-center justify-between">
                  <Label
                    for="post-form-is-pinned"
                    class="text-sm"
                  >置顶</Label>
                  <Switch
                    id="post-form-is-pinned"
                    v-model="form.is_pinned"
                  />
                </div>
                <div class="flex items-center justify-between">
                  <Label
                    for="post-form-allow-comments"
                    class="text-sm"
                  >允许评论</Label>
                  <Switch
                    id="post-form-allow-comments"
                    v-model="form.allow_comments"
                  />
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
                  :aria-label="$_t('admin.editor.postPassword')"
                  placeholder="访问密码"
                  class="h-9 rounded-[10px] text-sm"
                />
              </div>
            </div>

            <div class="h-px bg-border" />

            <div>
              <Label
                for="post-form-category"
                class="text-xs text-muted-foreground mb-1 block"
              >分类</Label>
              <Select
                :model-value="form.category_id?.toString() ?? '0'"
                @update:model-value="(v: string | undefined) => form.category_id = Number(v) || null"
              >
                <SelectTrigger
                  id="post-form-category"
                  class="h-9 rounded-[10px]"
                >
                  <SelectValue :placeholder="categoriesLoading ? '加载中...' : '选择分类'" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="0">
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
                    :aria-label="$_t('common.search')"
                    placeholder="搜索标签..."
                    @blur="onTagComboboxBlur"
                  >
                </div>
                <div
                  v-if="tagComboboxOpen"
                  :class="[
                    'absolute z-20 top-full mt-1 w-full max-h-56 overflow-y-auto rounded-[10px] border border-border bg-card shadow-lg p-1' // panel-exempt: 标签下拉浮层；card-surface 的 isolation:isolate + backdrop-filter 会打断它与输入框的层叠关系，浮层必须保持素面
                  ]"
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
      <div class="flex items-center gap-3">
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
        <!-- 未保存状态必须可见：离开确认只在"真要离开"那一刻才出现，
             而作者更需要的是随时知道自己还有东西没存 -->
        <span
          v-if="isDirty"
          class="text-xs text-warning-muted-foreground"
        >有未保存的更改</span>
        <span
          v-else
          class="text-xs text-muted-foreground"
        >已同步</span>
      </div>
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
