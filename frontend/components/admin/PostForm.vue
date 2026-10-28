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
  fetchAdminSeries,
  type AdminCategory,
  type AdminTag,
  type AdminSeries
} from '~~/composables/useAdminManage'
import { useMediaUploadCover } from '~~/composables/useMedia'
import { useToast } from '~~/composables/useToast'
import { EMPTY_I18N_DICT, getLocalizedStr, normalizeI18nDict, toI18nPayload, slugify } from '~~/composables/useAdminI18n'
import { toDateTimeLocal, fromDateTimeLocal } from '~~/lib/datetime'
import { estimateContentStats, slugSourceTitle, scheduledAtError } from '~~/lib/postEditor'
import { Button } from '~~/components/ui/button'
import { Input } from '~~/components/ui/input'
import { Label } from '~~/components/ui/label'
import AdminFormSection from './AdminFormSection.vue'
import AdminFormField from './AdminFormField.vue'
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
  Send,
  Eye,
  Type,
  FileText,
  Search,
  Shield,
  FolderTree
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
  title: { ...EMPTY_I18N_DICT } as Record<string, string>,
  slug: '',
  content: { ...EMPTY_I18N_DICT } as Record<string, string>,
  // 后端 PostBase/PostUpdate 的 pattern 只接受 draft|published|scheduled，
  // 历史遗留的 archived 状态不可再作为可写值出现。
  status: 'draft' as 'draft' | 'published' | 'scheduled',
  scheduled_at: '',
  is_pinned: false,
  allow_comments: true,
  visibility: 'public' as 'public' | 'password' | 'private',
  password: '',
  // 锁屏上给访客看的明文提示；后端只在真有密码哈希时回读它
  encryption_hint: '',
  category_id: null as number | null,
  tag_ids: [] as number[],
  // 系列章节：后端 PostEditResponse 已回填这两列，PUT 也必须始终带上，
  // 否则「改一次标题保存」就把文章踢出系列（系列页章节目录清空）。
  series_id: null as number | null,
  series_order: 0,
  // 来源：后端列 NOT NULL、默认「原创」，所以永远要发送（空值会让 PUT 把列写空，
  // 而列是 NOT NULL → 422）。原文链接反过来：空串在后端归成 None，正好是「清掉」。
  source: '原创',
  source_url: '',
  excerpt: { ...EMPTY_I18N_DICT } as Record<string, string>,
  cover_image: '',
  meta_title: { ...EMPTY_I18N_DICT } as Record<string, string>,
  meta_description: { ...EMPTY_I18N_DICT } as Record<string, string>,
  meta_keywords: { ...EMPTY_I18N_DICT } as Record<string, string>
})

const initialStateSnapshot = ref<string>('')
const categories = ref<AdminCategory[]>([])
const tags = ref<AdminTag[]>([])
const seriesList = ref<AdminSeries[]>([])
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

// 系列选择器里的中文标题：AdminSeries.name 实际是后端 title 的多语言 dict
const seriesOptions = computed(() =>
  seriesList.value.map(s => ({ id: s.id, label: getLocalizedStr(s.name) || s.slug }))
)

const slugSource = computed(() => slugSourceTitle(form.title))

const contentStats = computed(() => estimateContentStats(form.content.zh || ''))

/**
 * 主按钮文案跟随状态下发：状态是 draft 时 publishPost 实际保存的是草稿，
 * 按钮还写「发布文章」会让人以为点一下就直接上线。定时态同理。
 */
const primaryActionLabel = computed(() => {
  if (form.status === 'published') return '发布文章'
  if (form.status === 'scheduled') return '保存并定时'
  return '保存草稿'
})

const statusLabel = computed(() => {
  if (form.status === 'published') return '已发布'
  if (form.status === 'scheduled') return '定时发布'
  return '草稿'
})

const scheduledError = computed(() => scheduledAtError(form.status, fromDateTimeLocal(form.scheduled_at)))

/**
 * 原文链接只允许 http(s)：这个值会渲染成访客页面上的 `<a href>`，
 * `javascript:` / `data:` 伪协议写进去就等于在每篇文章下方埋一条可执行链接。
 * 后端 PostBase/PostUpdate 的严格档会拒（422），这里提前拦是为了让作者当场看到
 * 是哪一个字段错了，而不是一条整页保存失败的 toast。
 */
const sourceUrlError = computed(() => {
  const url = form.source_url.trim()
  if (!url || /^https?:\/\//i.test(url)) return ''
  return '原文链接必须以 http:// 或 https:// 开头'
})

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

const loadSeries = async () => {
  try {
    seriesList.value = await fetchAdminSeries()
  } catch {
    // apiFetch 已统一 toast 错误，不再二次弹
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
  // 提示必须回填：不回填则每次 PUT 把 encryption_hint 提交成空串，改一次标题就清掉提示
  form.encryption_hint = data.encryption_hint ?? ''
  form.category_id = data.category?.id ?? null
  form.tag_ids = data.tags ? data.tags.map(t => t.id) : []
  form.series_id = data.series_id ?? null
  form.series_order = data.series_order ?? 0
  // 必须回填：不回填则每次 PUT 把来源提交成「原创」，转载文章改一次标题就丢了出处
  form.source = data.source?.trim() || '原创'
  form.source_url = data.source_url ?? ''
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
    series_id: form.series_id ?? null,
    series_order: form.series_order || 0,
    // 来源始终发送且兜回默认值：列是 NOT NULL，空串会让后端 422，
    // 而"整个字段不出现"在 exclude_unset 语义下等于"不改它"，两者都不是作者想要的。
    source: form.source.trim() || '原创',
    // 空串归 null：与分类/封面同一套"显式清空"口径，省略键则清不掉旧出处
    source_url: form.source_url.trim() || null,
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
  // 提示与密码散列不同：空串是合法值（"我不要提示"），所以始终发送。
  // 离开密码态时发送空串把旧提示清掉——库里留一条永远不会展示的明文没有意义。
  payload.encryption_hint = form.visibility === 'password' ? form.encryption_hint.trim() : ''
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
  const srcErr = sourceUrlError.value
  if (srcErr) {
    toast.error(srcErr)
    return false
  }
  if (form.visibility === 'password' && !form.password.trim() && !initiallyPasswordProtected.value) {
    toast.error('请输入访问密码')
    return false
  }
  // 提示是锁屏上的明文，写成密码等于把门禁口令公开贴在门上
  if (
    form.visibility === 'password'
    && form.encryption_hint.trim()
    && form.encryption_hint.trim() === form.password.trim()
  ) {
    toast.error('密码提示不能写成密码本身')
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

// 保存后的收尾分两条路：草稿**留在编辑器里继续写**（把当前表单认作新的干净基线），
// 发布/定时才交还给外层页面跳列表。
// 旧行为是无条件 submitted=true + 立刻跳列表，两处毛病：
// 1) 存一次草稿就被踢出编辑器，接着写要重新点开、还会撞上"未保存"确认；
// 2) 若页面选择不跳（编辑态存草稿），submitted 已永久为真 → 之后的所有改动都不再
//    触发离开确认 / beforeunload / 卸载时写本地草稿，关标签页等于静默丢稿。
const settleAfterSave = (data: unknown) => {
  const status = (data as { status?: string } | null)?.status
  if (props.mode === 'edit' && status === 'draft') {
    initialStateSnapshot.value = JSON.stringify(form)
    try {
      localStorage.removeItem(draftLocalStorageKey.value)
    } catch {
      /* storage disabled */
    }
    return
  }
  markSubmitted()
}

const saveDraft = async () => {
  if (!validateBase()) return
  savingDraft.value = true
  try {
    const payload = buildPayload('draft')
    if (props.mode === 'new') {
      const data = await createPost(payload)
      toast.success('草稿保存成功')
      settleAfterSave(data)
      emits('submitSuccess', data, true)
    } else if (props.postId) {
      const data = await updatePost(props.postId, payload)
      toast.success('草稿保存成功')
      settleAfterSave(data)
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
      settleAfterSave(data)
      emits('submitSuccess', data, true)
    } else if (props.postId) {
      const data = await updatePost(props.postId, payload)
      settleAfterSave(data)
      emits('submitSuccess', data, false)
    }
  } catch {
    // apiFetch 已统一 toast 错误，不再二次弹
  } finally {
    submitting.value = false
  }
}

const openPreview = () => {
  if (!form.slug) {
    toast.warning('请先输入 slug 后再预览')
    return
  }
  // 预览打开的是**已保存到库里**的那一篇，且只有 published 能公开访问：
  // 草稿/定时走的是同一道可见性闸门（post_is_publicly_visible），新标签页只会看到 404。
  // 不提示的话作者以为是"编辑器没生效"，回头去改表单。
  if (form.status !== 'published') {
    toast.warning('预览打开的是已保存的公开页面；未发布的文章前台会显示 404，请先保存草稿再发布')
  }
  window.open(`/posts/${form.slug}`, '_blank')
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
  await Promise.all([loadCategories(), loadTags(), loadSeries()])

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
  <div class="flex flex-col gap-5">
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

    <!-- 常驻操作条：正文可能很长，保存/发布不能只沉在页面底部。
         top-16 让开 64px 的后台顶栏（AdminHeader 是 sticky top-0 z-40）。 -->
    <div class="sticky top-16 z-30 -mx-4 flex flex-wrap items-center justify-between gap-3 border-b border-border bg-background/90 px-4 py-2.5 backdrop-blur md:-mx-6 md:px-6">
      <div class="flex min-w-0 items-center gap-2.5">
        <span class="truncate text-sm font-medium">{{ form.title.zh || '未命名文章' }}</span>
        <Badge
          variant="secondary"
          class="shrink-0 rounded-[10px]"
        >
          {{ statusLabel }}
        </Badge>
        <span
          v-if="isDirty"
          class="inline-flex shrink-0 items-center gap-1.5 text-xs text-warning-muted-foreground"
        >
          <span class="size-1.5 rounded-full bg-warning" />
          有未保存的更改
        </span>
        <span
          v-else
          class="inline-flex shrink-0 items-center gap-1.5 text-xs text-muted-foreground"
        >
          <span class="size-1.5 rounded-full bg-success" />
          已同步
        </span>
      </div>
      <div class="flex shrink-0 items-center gap-2">
        <Button
          type="button"
          variant="ghost"
          size="sm"
          class="h-9 rounded-[10px]"
          @click="openPreview"
        >
          <Eye
            data-icon="inline-start"
            class="size-4"
          />
          预览
        </Button>
        <Button
          v-if="form.status !== 'draft'"
          type="button"
          variant="outline"
          size="sm"
          class="h-9 rounded-[10px]"
          :disabled="savingDraft || submitting"
          @click="saveDraft"
        >
          {{ savingDraft ? '保存中...' : '存为草稿' }}
        </Button>
        <Button
          type="button"
          size="sm"
          class="h-9 rounded-[10px]"
          :disabled="submitting || savingDraft"
          @click="publishPost"
        >
          {{ submitting ? '处理中...' : primaryActionLabel }}
        </Button>
      </div>
    </div>

    <div class="grid grid-cols-1 items-start gap-5 xl:grid-cols-[minmax(0,1fr)_360px]">
      <!-- ============================ 主编辑区 ============================ -->
      <div class="flex min-w-0 flex-col gap-4">
        <AdminFormSection
          title="标题与链接"
          description="简体中文为主语言，其余三种语言可切换填写。"
          :icon="Type"
        >
          <div class="flex flex-col gap-4">
            <I18nTabsEditor
              v-model="form.title"
              kind="text"
              label="标题"
              placeholder="输入文章标题"
              required
              flat
            />
            <AdminFormField
              label="Slug"
              for="post-form-slug"
              hint="文章地址为 /posts/<slug>；留空时会按标题自动生成。"
            >
              <div class="flex items-stretch gap-2">
                <span class="hidden sm:inline-flex items-center rounded-[10px] border border-border bg-muted/40 px-3 font-mono text-xs text-muted-foreground">
                  /posts/
                </span>
                <Input
                  id="post-form-slug"
                  v-model="form.slug"
                  placeholder="auto-generated-slug"
                  class="h-10 flex-1 rounded-[10px] font-mono text-sm"
                  @input="handleSlugInput"
                />
              </div>
            </AdminFormField>
          </div>
        </AdminFormSection>

        <AdminFormSection
          title="正文"
          description="支持 Markdown；可直接粘贴或拖拽图片上传。"
          :icon="FileText"
        >
          <template #actions>
            <span class="inline-flex items-center gap-1 rounded-full bg-muted/60 px-2.5 py-1 text-[11px] tabular-nums text-muted-foreground">
              {{ contentStats.words }} 字 · 约 {{ contentStats.minutes }} 分钟
            </span>
          </template>
          <I18nTabsEditor
            v-model="form.content"
            kind="markdown"
            label="正文"
            placeholder="开始撰写文章内容"
            required
            flat
          />
        </AdminFormSection>

        <AdminFormSection
          title="摘要与 SEO"
          description="摘要用于列表卡片与搜索结果；SEO 字段留空时回落到标题与摘要。"
          :icon="Search"
        >
          <div class="flex flex-col gap-5">
            <I18nTabsEditor
              v-model="form.excerpt"
              kind="textarea"
              label="摘要"
              :rows="3"
              placeholder="输入文章摘要，不填则自动截取前 180 字"
              flat
            />
            <div class="h-px bg-border" />
            <div class="flex flex-col gap-4">
              <I18nTabsEditor
                v-model="form.meta_title"
                kind="text"
                label="SEO 标题"
                placeholder="留空则使用文章标题"
                flat
              />
              <I18nTabsEditor
                v-model="form.meta_description"
                kind="text"
                label="SEO 描述"
                placeholder="留空则使用文章摘要"
                flat
              />
              <I18nTabsEditor
                v-model="form.meta_keywords"
                kind="text"
                label="SEO 关键词"
                placeholder="逗号分隔，例如：FastAPI, Python, 教程"
                flat
              />
            </div>
          </div>
        </AdminFormSection>
      </div>

      <!-- ============================ 右侧设置区 ============================ -->
      <aside class="flex flex-col gap-4">
        <AdminFormSection
          title="发布"
          description="决定文章的可见状态与发布时机。"
          :icon="Send"
        >
          <div class="flex flex-col gap-4">
            <AdminFormField
              label="状态"
              for="post-form-status"
              required
            >
              <Select v-model="form.status">
                <SelectTrigger
                  id="post-form-status"
                  class="h-10 rounded-[10px]"
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
            </AdminFormField>

            <AdminFormField
              v-if="form.status === 'scheduled'"
              label="定时时间"
              for="post-form-scheduled-at"
              required
              :error="scheduledError || undefined"
              hint="按你所在时区填写，提交时会自动换算为 UTC。"
            >
              <Input
                id="post-form-scheduled-at"
                v-model="form.scheduled_at"
                type="datetime-local"
                class="h-10 rounded-[10px] text-sm"
              />
            </AdminFormField>

            <div class="flex flex-col gap-2.5 rounded-[10px] border border-border/70 bg-muted/20 p-3">
              <div class="flex items-center justify-between gap-3">
                <Label
                  for="post-form-is-pinned"
                  class="text-sm"
                >置顶</Label>
                <Switch
                  id="post-form-is-pinned"
                  v-model="form.is_pinned"
                />
              </div>
              <div class="flex items-center justify-between gap-3">
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
        </AdminFormSection>

        <AdminFormSection
          title="可见性"
          description="控制谁可以阅读这篇文章。"
          :icon="Shield"
        >
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
            <Input
              v-if="form.visibility === 'password'"
              v-model="form.password"
              type="password"
              :aria-label="$_t('admin.editor.postPassword')"
              placeholder="访问密码"
              class="mt-2 h-10 rounded-[10px] text-sm"
            />
            <Input
              v-if="form.visibility === 'password'"
              v-model="form.encryption_hint"
              type="text"
              maxlength="200"
              :aria-label="$_t('admin.editor.postPasswordHint')"
              :placeholder="$_t('admin.editor.postPasswordHint')"
              class="mt-2 h-10 rounded-[10px] text-sm"
            />
          </div>
        </AdminFormSection>

        <AdminFormSection
          title="组织"
          description="分类、标签与系列决定文章的归档位置；来源标记这篇文章的出处。"
          :icon="FolderTree"
        >
          <div class="flex flex-col gap-4">
            <AdminFormField
              label="分类"
              for="post-form-category"
            >
              <Select
                :model-value="form.category_id?.toString() ?? '0'"
                @update:model-value="(v: string | undefined) => form.category_id = Number(v) || null"
              >
                <SelectTrigger
                  id="post-form-category"
                  class="h-10 rounded-[10px]"
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
                        :class="c.color ? '' : 'bg-muted-foreground/40'"
                        :style="c.color ? { background: c.color } : undefined"
                      />
                      {{ getLocalizedStr(c.name) }}
                    </div>
                  </SelectItem>
                </SelectContent>
              </Select>
            </AdminFormField>

            <div ref="tagComboboxRef">
              <AdminFormField label="标签">
                <div class="relative">
                  <div
                    class="min-h-10 px-2.5 py-1.5 rounded-[10px] border border-input bg-background flex flex-wrap gap-1.5 items-center cursor-text transition-colors"
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
                        :aria-label="`移除标签 ${getTagById(tagId) ? getLocalizedStr(getTagById(tagId)!.name) : tagId}`"
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
                      role="combobox"
                      aria-controls="post-form-tag-listbox"
                      :aria-expanded="tagComboboxOpen"
                      aria-autocomplete="list"
                      :aria-label="$_t('common.search')"
                      placeholder="搜索标签..."
                      @blur="onTagComboboxBlur"
                    >
                  </div>
                  <div
                    v-if="tagComboboxOpen"
                    id="post-form-tag-listbox"
                    role="listbox"
                    aria-label="标签候选"
                    :class="[
                      'absolute z-20 top-full mt-1 w-full max-h-56 overflow-y-auto rounded-[10px] border border-border bg-card shadow-lg p-1' // panel-exempt: 标签下拉浮层；card-surface 的 isolation:isolate + backdrop-filter 会打断它与输入框的层叠关系，浮层必须保持素面
                    ]"
                  >
                    <button
                      v-for="t in filteredTags"
                      :key="t.id"
                      type="button"
                      role="option"
                      :aria-selected="isTagSelected(t.id)"
                      class="w-full flex items-center justify-between px-2.5 py-2 rounded-md text-sm text-left cursor-pointer transition-colors hover:bg-accent"
                      :class="{ 'bg-accent/50': isTagSelected(t.id) }"
                      @mousedown.prevent="toggleTag(t.id)"
                    >
                      <div class="flex items-center gap-2">
                        <span
                          class="size-2 rounded-full inline-block"
                          :class="t.color ? '' : 'bg-muted-foreground/40'"
                          :style="t.color ? { background: t.color } : undefined"
                        />
                        {{ getLocalizedStr(t.name) }}
                        <span class="text-xs text-muted-foreground">({{ t.post_count }})</span>
                      </div>
                      <Check
                        v-if="isTagSelected(t.id)"
                        class="size-3.5 text-primary"
                      />
                    </button>
                    <div
                      v-if="filteredTags.length === 0"
                      class="px-2.5 py-3 text-sm text-muted-foreground text-center"
                    >
                      无匹配标签
                    </div>
                  </div>
                </div>
              </AdminFormField>
            </div>

            <div class="flex items-end gap-2">
              <div class="flex-1 min-w-0">
                <AdminFormField
                  label="系列"
                  for="post-form-series"
                >
                  <Select
                    :model-value="form.series_id?.toString() ?? '0'"
                    @update:model-value="(v: string | undefined) => form.series_id = Number(v) || null"
                  >
                    <SelectTrigger
                      id="post-form-series"
                      class="h-10 rounded-[10px]"
                    >
                      <SelectValue placeholder="无系列" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="0">
                        无系列
                      </SelectItem>
                      <SelectItem
                        v-for="s in seriesOptions"
                        :key="s.id"
                        :value="s.id.toString()"
                      >
                        {{ s.label }}
                      </SelectItem>
                    </SelectContent>
                  </Select>
                </AdminFormField>
              </div>
              <div
                v-if="form.series_id"
                class="w-24"
              >
                <AdminFormField
                  label="序号"
                  for="post-form-series-order"
                >
                  <Input
                    id="post-form-series-order"
                    v-model.number="form.series_order"
                    type="number"
                    min="0"
                    class="h-10 rounded-[10px] text-sm"
                  />
                </AdminFormField>
              </div>
            </div>

            <div class="flex items-start gap-2">
              <div class="w-40 shrink-0">
                <AdminFormField
                  label="来源"
                  for="post-form-source"
                  hint="默认「原创」；转载/翻译改成实际出处。"
                >
                  <Input
                    id="post-form-source"
                    v-model="form.source"
                    maxlength="50"
                    placeholder="原创"
                    class="h-10 rounded-[10px] text-sm"
                  />
                </AdminFormField>
              </div>
              <div class="flex-1 min-w-0">
                <AdminFormField
                  label="原文链接"
                  for="post-form-source-url"
                  :error="sourceUrlError || undefined"
                  hint="留空则文章页不显示出处链接；非原创内容建议填写，文章页会渲染成可点击的出站链接。"
                >
                  <Input
                    id="post-form-source-url"
                    v-model="form.source_url"
                    maxlength="500"
                    placeholder="https://example.com/original-post"
                    class="h-10 rounded-[10px] text-sm"
                  />
                </AdminFormField>
              </div>
            </div>
          </div>
        </AdminFormSection>

        <AdminFormSection
          title="封面图"
          description="列表卡片与分享卡使用该图片；不设则回落到站内占位封面。"
          :icon="ImageIcon"
        >
          <div class="flex flex-col gap-3">
            <button
              type="button"
              class="relative w-full aspect-[16/9] overflow-hidden rounded-[12px] border border-dashed border-border bg-muted/30 transition-colors hover:border-primary/50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring group"
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
                class="absolute inset-0 flex flex-col items-center justify-center gap-1.5 text-muted-foreground"
              >
                <ImageIcon class="size-6 opacity-60" />
                <span class="text-xs font-medium">{{ coverUploading ? '上传中...' : '点击上传封面' }}</span>
                <span class="text-[11px] opacity-70">建议 1200 × 800</span>
              </span>
              <span
                v-if="form.cover_image"
                class="absolute inset-0 flex items-center justify-center bg-black/45 text-xs font-medium text-white opacity-0 transition-opacity group-hover:opacity-100 group-focus-visible:opacity-100"
              >
                更换封面
              </span>
            </button>
            <div class="flex items-center gap-2">
              <Button
                type="button"
                variant="outline"
                size="sm"
                class="h-9 flex-1 rounded-[10px]"
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
                移除
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
        </AdminFormSection>
      </aside>
    </div>
  </div>
</template>
