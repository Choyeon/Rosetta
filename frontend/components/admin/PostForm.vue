<template>
  <div class="space-y-4">
    <!-- 草稿恢复横幅 -->
    <Alert
      v-if="draftBanner"
      class="border-primary/40"
    >
      <FileClock class="size-4" />
      <AlertTitle>{{ t('admin.editor.draftFound') }}</AlertTitle>
      <AlertDescription class="flex items-center gap-2">
        <span>{{ t('admin.editor.draftTime', { time: draftBanner }) }}</span>
        <Button
          size="sm"
          class="h-7"
          @click="restoreDraft"
        >
          {{ t('admin.editor.restoreDraft') }}
        </Button>
        <Button
          size="sm"
          variant="outline"
          class="h-7"
          @click="discardDraft"
        >
          {{ t('admin.editor.discardDraft') }}
        </Button>
      </AlertDescription>
    </Alert>

    <!-- 编辑页加载中 -->
    <div
      v-if="loading"
      class="space-y-4"
    >
      <Skeleton class="h-11 w-2/3" />
      <Skeleton class="h-9 w-1/3" />
      <Skeleton class="h-[420px] w-full" />
    </div>

    <!-- 404 -->
    <Alert
      v-else-if="notFound"
      variant="destructive"
    >
      <FileQuestion class="size-4" />
      <AlertTitle>{{ t('admin.editor.notFound') }}</AlertTitle>
      <AlertDescription>
        <Button
          :is="'NuxtLink'"
          as="component"
          to="/admin/posts"
          variant="outline"
          size="sm"
          class="mt-2"
        >
          {{ t('admin.editor.backToList') }}
        </Button>
      </AlertDescription>
    </Alert>

    <template v-else>
      <div class="grid gap-6 xl:grid-cols-[minmax(0,1fr)_360px]">
        <!-- 主编辑区 -->
        <div class="min-w-0 space-y-4">
          <div class="space-y-1.5">
            <Input
              v-model="form.title"
              :placeholder="t('admin.editor.titlePlaceholder')"
              class="h-12 border-0 bg-muted/40 px-4 text-lg font-semibold shadow-none focus-visible:ring-0 md:text-xl"
              :aria-label="t('admin.editor.title')"
            />
            <p
              v-if="titleError"
              class="px-4 text-xs text-destructive"
            >
              {{ titleError }}
            </p>
          </div>

          <div class="flex items-center gap-2 px-1">
            <span class="text-xs text-muted-foreground">/posts/</span>
            <Input
              v-model="form.slug"
              :placeholder="t('admin.editor.slugPlaceholder')"
              class="h-8 font-mono text-xs"
              :class="slugError ? 'border-destructive' : ''"
              @input="slugTouched = true"
            />
          </div>
          <p
            v-if="slugError"
            class="px-1 text-xs text-destructive"
          >
            {{ slugError }}
          </p>
          <p
            v-else
            class="px-1 text-xs text-muted-foreground"
          >
            {{ t('admin.editor.slugHint') }}
          </p>

          <MarkdownEditor
            v-model="form.content"
            :placeholder="t('admin.editor.contentPlaceholder')"
            :height="editorHeight"
            @save="doSave"
          />
        </div>

        <!-- 元数据面板 -->
        <div class="space-y-4">
          <Card>
            <CardHeader class="pb-3">
              <CardTitle class="text-base">
                {{ t('admin.editor.publishTitle') }}
              </CardTitle>
            </CardHeader>
            <CardContent class="space-y-4">
              <div class="space-y-1.5">
                <Label>{{ t('admin.editor.status') }}</Label>
                <Select v-model="form.status">
                  <SelectTrigger class="h-9">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="draft">
                      {{ t('admin.posts.status.draft') }}
                    </SelectItem>
                    <SelectItem value="published">
                      {{ t('admin.posts.status.published') }}
                    </SelectItem>
                    <SelectItem value="scheduled">
                      {{ t('admin.posts.status.scheduled') }}
                    </SelectItem>
                  </SelectContent>
                </Select>
              </div>

              <div
                v-if="form.status === 'scheduled'"
                class="space-y-1.5"
              >
                <Label>{{ t('admin.editor.scheduledAt') }}</Label>
                <Input
                  v-model="form.scheduledAt"
                  type="datetime-local"
                  class="h-9"
                />
              </div>
              <p
                v-else-if="publishedAtText"
                class="text-xs text-muted-foreground"
              >
                {{ t('admin.editor.publishedAt') }}: {{ publishedAtText }}
              </p>

              <div class="space-y-1.5">
                <Label>{{ t('admin.editor.visibility') }}</Label>
                <Select v-model="form.visibility">
                  <SelectTrigger class="h-9">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="public">
                      {{ t('admin.editor.visibilityPublic') }}
                    </SelectItem>
                    <SelectItem value="password">
                      {{ t('admin.editor.visibilityPassword') }}
                    </SelectItem>
                    <SelectItem value="private">
                      {{ t('admin.editor.visibilityPrivate') }}
                    </SelectItem>
                  </SelectContent>
                </Select>
              </div>

              <!-- 访问密码：新建直接输入；编辑显示已设置状态 + 修改/清除 -->
              <div
                v-if="form.visibility === 'password'"
                class="space-y-1.5"
              >
                <Label>{{ t('admin.editor.postPassword') }}</Label>
                <template v-if="!isEdit || passwordAction === 'set'">
                  <Input
                    v-model="form.password"
                    type="password"
                    autocomplete="new-password"
                    :placeholder="t('admin.editor.passwordPlaceholder')"
                    class="h-9"
                  />
                  <Button
                    v-if="isEdit && hasPassword"
                    size="sm"
                    variant="ghost"
                    class="h-7 px-2 text-xs"
                    @click="passwordAction = 'keep'"
                  >
                    {{ t('admin.editor.cancelEdit') }}
                  </Button>
                </template>
                <template v-else-if="passwordAction === 'keep' && hasPassword">
                  <div class="flex items-center gap-2">
                    <Badge variant="secondary">
                      <KeyRound class="mr-1 size-3" />{{ t('admin.editor.passwordSet') }}
                    </Badge>
                    <Button
                      size="sm"
                      variant="outline"
                      class="h-7"
                      @click="passwordAction = 'set'"
                    >
                      {{ t('admin.editor.changePassword') }}
                    </Button>
                    <Button
                      size="sm"
                      variant="outline"
                      class="h-7 text-destructive"
                      @click="passwordAction = 'clear'"
                    >
                      {{ t('admin.editor.clearPassword') }}
                    </Button>
                  </div>
                </template>
                <template v-else-if="passwordAction === 'clear'">
                  <div class="flex items-center gap-2">
                    <Badge
                      variant="outline"
                      class="text-destructive"
                    >
                      {{ t('admin.editor.passwordWillClear') }}
                    </Badge>
                    <Button
                      size="sm"
                      variant="ghost"
                      class="h-7"
                      @click="passwordAction = 'keep'"
                    >
                      {{ t('admin.editor.undo') }}
                    </Button>
                  </div>
                </template>
              </div>

              <Separator />

              <div class="flex items-center justify-between">
                <Badge
                  v-if="dirty"
                  variant="outline"
                  class="text-warning"
                >
                  {{ t('admin.editor.unsaved') }}
                </Badge>
                <span
                  v-else
                  class="text-xs text-muted-foreground"
                >{{ t('admin.editor.allSaved') }}</span>
                <Button
                  :disabled="saving || !!titleError || !!slugError"
                  @click="doSave"
                >
                  <Loader2
                    v-if="saving"
                    class="mr-2 size-4 animate-spin"
                  />
                  <Save
                    v-else
                    class="mr-2 size-4"
                  />
                  {{ saving ? t('admin.editor.saving') : t('admin.editor.save') }}
                </Button>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader class="pb-3">
              <CardTitle class="text-base">
                {{ t('admin.editor.metaTitle') }}
              </CardTitle>
            </CardHeader>
            <CardContent class="space-y-4">
              <div class="space-y-1.5">
                <Label>{{ t('admin.editor.category') }}</Label>
                <Select v-model="categoryIdStr">
                  <SelectTrigger class="h-9">
                    <SelectValue :placeholder="t('admin.editor.selectCategory')" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="none">
                      {{ t('admin.editor.noCategory') }}
                    </SelectItem>
                    <SelectItem
                      v-for="c in categories"
                      :key="c.id"
                      :value="String(c.id)"
                    >
                      {{ c.name }}
                    </SelectItem>
                  </SelectContent>
                </Select>
              </div>

              <div class="space-y-1.5">
                <Label>{{ t('admin.editor.tags') }}</Label>
                <Input
                  v-model="tagInput"
                  :placeholder="t('admin.editor.tagsPlaceholder')"
                  class="h-9"
                  list="admin-post-tags"
                />
                <datalist id="admin-post-tags">
                  <option
                    v-for="tg in allTags"
                    :key="tg.id"
                    :value="tg.name"
                  />
                </datalist>
                <p class="text-xs text-muted-foreground">
                  {{ t('admin.editor.tagsHint') }}
                </p>
              </div>

              <div class="space-y-1.5">
                <Label>{{ t('admin.editor.excerpt') }}</Label>
                <Textarea
                  v-model="form.excerpt"
                  :placeholder="t('admin.editor.excerptPlaceholder')"
                  rows="3"
                  class="text-sm"
                />
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader class="pb-3">
              <CardTitle class="text-base">
                {{ t('admin.editor.coverTitle') }}
              </CardTitle>
            </CardHeader>
            <CardContent class="space-y-3">
              <Input
                v-model="form.coverImage"
                :placeholder="t('admin.editor.coverPlaceholder')"
                class="h-9"
              />
              <div
                v-if="form.coverImage"
                class="relative overflow-hidden rounded-md border bg-muted"
              >
                <img
                  :src="form.coverImage"
                  :alt="t('admin.editor.coverAlt')"
                  class="h-32 w-full object-cover"
                  @error="coverBroken = true"
                  @load="coverBroken = false"
                >
                <p
                  v-if="coverBroken"
                  class="absolute inset-0 flex items-center justify-center text-xs text-muted-foreground"
                >
                  {{ t('admin.editor.coverBroken') }}
                </p>
              </div>
              <Button
                v-if="form.coverImage"
                size="sm"
                variant="outline"
                class="h-7"
                @click="form.coverImage = ''"
              >
                {{ t('admin.editor.clearCover') }}
              </Button>
            </CardContent>
          </Card>

          <Card>
            <CardHeader class="pb-3">
              <CardTitle class="text-base">
                {{ t('admin.editor.optionsTitle') }}
              </CardTitle>
            </CardHeader>
            <CardContent class="space-y-4">
              <div class="flex items-center justify-between">
                <Label
                  for="post-pinned"
                  class="cursor-pointer"
                >{{ t('admin.editor.pinned') }}</Label>
                <Switch
                  id="post-pinned"
                  :model-value="form.isPinned"
                  @update:model-value="(v: boolean) => form.isPinned = v"
                />
              </div>
              <div class="flex items-center justify-between">
                <Label
                  for="post-comments"
                  class="cursor-pointer"
                >{{ t('admin.editor.allowComments') }}</Label>
                <Switch
                  id="post-comments"
                  :model-value="form.allowComments"
                  @update:model-value="(v: boolean) => form.allowComments = v"
                />
              </div>
            </CardContent>
          </Card>
        </div>
      </div>
    </template>
  </div>
</template>

<script setup lang="ts">
import { Card, CardContent, CardHeader, CardTitle } from '~~/components/ui/card'
import { Button } from '~~/components/ui/button'
import { Input } from '~~/components/ui/input'
import { Textarea } from '~~/components/ui/textarea'
import { Label } from '~~/components/ui/label'
import { Badge } from '~~/components/ui/badge'
import { Switch } from '~~/components/ui/switch'
import { Separator } from '~~/components/ui/separator'
import { Skeleton } from '~~/components/ui/skeleton'
import { Alert, AlertDescription, AlertTitle } from '~~/components/ui/alert'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue
} from '~~/components/ui/select'
import { Save, Loader2, KeyRound, FileClock, FileQuestion } from '@lucide/vue'
import { apiFetch } from '~~/composables/useAPI'

/**
 * 文章新建 / 编辑共用表单。
 * - 新建：postId 为 null，POST /blog/posts
 * - 编辑：postId 存在，GET /blog/posts/{id} 加载（PostEditResponse，兼容本地化 string 形态），PUT /blog/posts/{id}
 */

const props = defineProps<{
  postId: number | null
}>()

const emit = defineEmits<{
  (e: 'loaded', payload: { title: string, slug: string }): void
}>()

const { t, locale } = useI18n()
const toast = useToast()

const isEdit = computed(() => props.postId != null)

type PostStatus = 'draft' | 'published' | 'scheduled'
type PostVisibility = 'public' | 'password' | 'private'
type PasswordAction = 'keep' | 'set' | 'clear'

interface PostFormState {
  title: string
  slug: string
  excerpt: string
  content: string
  coverImage: string
  status: PostStatus
  visibility: PostVisibility
  isPinned: boolean
  allowComments: boolean
  scheduledAt: string
  password: string
}

const emptyForm = (): PostFormState => ({
  title: '',
  slug: '',
  excerpt: '',
  content: '',
  coverImage: '',
  status: 'draft',
  visibility: 'public',
  isPinned: false,
  allowComments: true,
  scheduledAt: '',
  password: ''
})

const form = reactive<PostFormState>(emptyForm())
const categoryIdStr = ref('none')
const tagInput = ref('')
const slugTouched = ref(false)
const coverBroken = ref(false)

const loading = ref(false)
const notFound = ref(false)
const saving = ref(false)
const dirty = ref(false)
const hasPassword = ref(false)
const passwordAction = ref<PasswordAction>('keep')
const publishedAtText = ref('')

/** 服务端已存的多语言内容（保存时与当前语言合并，避免覆盖其他语言） */
const i18nDicts = reactive({
  title: {} as Record<string, string>,
  content: {} as Record<string, string>,
  excerpt: {} as Record<string, string>
})

interface CategoryOption { id: number, name: string, slug: string }
interface TagOption { id: number, name: string, slug: string }
const categories = ref<CategoryOption[]>([])
const allTags = ref<TagOption[]>([])

const editorHeight = computed(() => (import.meta.client && window.innerHeight < 900 ? 380 : 480))

/* ==================== 校验 ==================== */

const titleError = computed(() => (!form.title.trim() && dirty.value ? t('admin.editor.titleRequired') : ''))
const slugError = computed(() => {
  if (!slugTouched.value || !form.slug) return ''
  return /^[a-z0-9-]+$/.test(form.slug) ? '' : t('admin.editor.slugInvalid')
})

/* ==================== 快照 & 脏标记 ==================== */

/** 快照不含密码明文（草稿仅存入 localStorage，不落敏感值） */
function snapshot(): string {
  return JSON.stringify({
    title: form.title,
    slug: form.slug,
    excerpt: form.excerpt,
    content: form.content,
    coverImage: form.coverImage,
    status: form.status,
    visibility: form.visibility,
    isPinned: form.isPinned,
    allowComments: form.allowComments,
    scheduledAt: form.scheduledAt,
    categoryId: categoryIdStr.value,
    tags: tagInput.value,
    passwordAction: passwordAction.value
  })
}

function markClean() {
  baseline = snapshot()
  dirty.value = false
}

let baseline = snapshot()

watch(snapshot, (v) => {
  dirty.value = v !== baseline
  scheduleAutosave()
})

/* ==================== 本地草稿（debounce 8s） ==================== */

const draftKey = computed(() => `rosetta_admin_post_draft_${props.postId ?? 'new'}`)

let autosaveTimer: ReturnType<typeof setTimeout> | null = null

function scheduleAutosave() {
  if (!import.meta.client) return
  if (autosaveTimer) clearTimeout(autosaveTimer)
  autosaveTimer = setTimeout(() => {
    if (!dirty.value || saving.value || loading.value || notFound.value) return
    try {
      localStorage.setItem(draftKey.value, JSON.stringify({ savedAt: new Date().toISOString(), data: JSON.parse(snapshot()) }))
    } catch { /* localStorage 可能已满或被禁用 */ }
  }, 8000)
}

const draftBanner = ref('')

function findDraft(): { savedAt: string, data: Record<string, unknown> } | null {
  if (!import.meta.client) return null
  try {
    const raw = localStorage.getItem(draftKey.value)
    if (!raw) return null
    const parsed = JSON.parse(raw)
    if (!parsed?.data) return null
    return parsed
  } catch {
    return null
  }
}

function checkDraftAfterLoad() {
  const draft = findDraft()
  if (!draft) return
  if (JSON.stringify(draft.data) === baseline) {
    localStorage.removeItem(draftKey.value)
    return
  }
  draftBanner.value = new Date(draft.savedAt).toLocaleString()
}

function restoreDraft() {
  const draft = findDraft()
  if (draft) {
    const d = draft.data as Record<string, unknown>
    Object.assign(form, emptyForm(), {
      title: typeof d.title === 'string' ? d.title : '',
      slug: typeof d.slug === 'string' ? d.slug : '',
      excerpt: typeof d.excerpt === 'string' ? d.excerpt : '',
      content: typeof d.content === 'string' ? d.content : '',
      coverImage: typeof d.coverImage === 'string' ? d.coverImage : '',
      status: (['draft', 'published', 'scheduled'] as const).includes(d.status as PostStatus) ? d.status as PostStatus : 'draft',
      visibility: (['public', 'password', 'private'] as const).includes(d.visibility as PostVisibility) ? d.visibility as PostVisibility : 'public',
      isPinned: d.isPinned === true,
      allowComments: d.allowComments !== false,
      scheduledAt: typeof d.scheduledAt === 'string' ? d.scheduledAt : '',
      password: ''
    })
    categoryIdStr.value = typeof d.categoryId === 'string' ? d.categoryId : 'none'
    tagInput.value = typeof d.tags === 'string' ? d.tags : ''
    if (typeof d.passwordAction === 'string' && ['keep', 'set', 'clear'].includes(d.passwordAction)) {
      passwordAction.value = d.passwordAction as PasswordAction
    }
    if (form.slug) slugTouched.value = true
  }
  draftBanner.value = ''
}

function discardDraft() {
  if (import.meta.client) localStorage.removeItem(draftKey.value)
  draftBanner.value = ''
}

function clearDraft() {
  if (import.meta.client) localStorage.removeItem(draftKey.value)
  draftBanner.value = ''
}

/* ==================== 数据加载 ==================== */

/** 响应字段可能是多语言 dict（PostEditResponse）或当前语言 string（本地化响应），统一归一 */
function toI18nDict(v: unknown): Record<string, string> {
  if (v && typeof v === 'object' && !Array.isArray(v)) {
    return Object.fromEntries(Object.entries(v as Record<string, unknown>).filter(([, x]) => typeof x === 'string')) as Record<string, string>
  }
  if (typeof v === 'string') return { [locale.value]: v }
  return {}
}

function fromI18nDict(v: unknown): string {
  const dict = toI18nDict(v)
  return dict[locale.value] ?? dict.zh ?? Object.values(dict)[0] ?? ''
}

function toLocalDatetime(v: unknown): string {
  if (!v) return ''
  const d = new Date(String(v))
  if (Number.isNaN(d.getTime())) return ''
  const pad = (n: number) => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`
}

async function loadMeta() {
  try {
    const [cats, tags] = await Promise.all([
      apiFetch<CategoryOption[] | { data?: CategoryOption[] }>('/blog/categories'),
      apiFetch<TagOption[] | { data?: TagOption[] }>('/blog/tags')
    ])
    categories.value = (Array.isArray(cats) ? cats : cats?.data ?? []) as CategoryOption[]
    allTags.value = (Array.isArray(tags) ? tags : tags?.data ?? []) as TagOption[]
  } catch (e) {
    console.error('[PostForm] load categories/tags failed:', e)
  }
}

async function loadPost() {
  loading.value = true
  notFound.value = false
  try {
    const res = await apiFetch<Record<string, unknown>>(`/blog/posts/${props.postId}/edit`)
    i18nDicts.title = toI18nDict(res.title)
    i18nDicts.content = toI18nDict(res.content)
    i18nDicts.excerpt = toI18nDict(res.excerpt)

    form.title = fromI18nDict(res.title)
    form.content = fromI18nDict(res.content)
    form.excerpt = fromI18nDict(res.excerpt)
    form.slug = typeof res.slug === 'string' ? res.slug : ''
    form.coverImage = typeof res.cover_image === 'string' ? res.cover_image : ''
    form.status = (['draft', 'published', 'scheduled'] as const).includes(res.status as PostStatus) ? res.status as PostStatus : 'draft'
    form.visibility = (['public', 'password', 'private'] as const).includes(res.visibility as PostVisibility) ? res.visibility as PostVisibility : 'public'
    form.isPinned = res.is_pinned === true
    form.allowComments = res.allow_comments !== false
    form.scheduledAt = toLocalDatetime(res.scheduled_at)

    hasPassword.value = res.has_password === true || !!res.is_password_protected
    passwordAction.value = 'keep'

    const cat = res.category as { id?: number } | null | undefined
    categoryIdStr.value = cat && typeof cat.id === 'number' ? String(cat.id) : 'none'

    const tags = Array.isArray(res.tags) ? (res.tags as Array<{ id?: number }>) : []
    const knownIds = new Set(tags.map(x => x.id))
    const names = allTags.value.filter(tg => knownIds.has(tg.id)).map(tg => tg.name)
    tagInput.value = names.join(', ')

    publishedAtText.value = res.published_at ? new Date(String(res.published_at)).toLocaleString() : ''

    emit('loaded', { title: form.title, slug: form.slug })
    markClean()
    checkDraftAfterLoad()
  } catch (e) {
    const status = (e as { status?: number, statusCode?: number })?.status ?? (e as { statusCode?: number })?.statusCode ?? 0
    if (status === 404) {
      notFound.value = true
    } else {
      toast.error(t('admin.editor.loadFailed'))
      notFound.value = true
    }
  } finally {
    loading.value = false
  }
}

/* ==================== 标签解析（缺失时创建） ==================== */

function parseTagNames(): string[] {
  return tagInput.value
    .split(/[,，]/)
    .map(s => s.trim())
    .filter(Boolean)
}

async function resolveTagIds(names: string[]): Promise<number[]> {
  const ids: number[] = []
  for (const name of names) {
    const exist = allTags.value.find(tg => tg.name.toLowerCase() === name.toLowerCase())
    if (exist) {
      ids.push(exist.id)
      continue
    }
    try {
      const created = await apiFetch<TagOption>('/blog/tags', {
        method: 'POST',
        body: { name: { zh: name } }
      })
      if (created?.id) {
        allTags.value.push({ id: created.id, name: fromI18nDict(created.name) || name, slug: created.slug || '' })
        ids.push(created.id)
      }
    } catch (e) {
      console.error('[PostForm] create tag failed:', name, e)
    }
  }
  return ids
}

/* ==================== 保存 ==================== */

function buildPayload(tagIds: number[]): Record<string, unknown> {
  const lang = locale.value
  const payload: Record<string, unknown> = {
    title: { ...i18nDicts.title, [lang]: form.title.trim() },
    content: { ...i18nDicts.content, [lang]: form.content },
    excerpt: form.excerpt.trim() ? { ...i18nDicts.excerpt, [lang]: form.excerpt.trim() } : null,
    cover_image: form.coverImage.trim() || null,
    category_id: categoryIdStr.value !== 'none' ? Number(categoryIdStr.value) : null,
    tag_ids: tagIds,
    status: form.status,
    visibility: form.visibility,
    is_pinned: form.isPinned,
    allow_comments: form.allowComments,
    scheduled_at: form.status === 'scheduled' && form.scheduledAt ? new Date(form.scheduledAt).toISOString() : null
  }
  if (slugTouched.value && form.slug.trim()) {
    payload.slug = form.slug.trim()
  }
  // 密码：新建直接提交；编辑按 keep(省略)/set(新值)/clear(空串) 语义
  if (!isEdit.value) {
    if (form.password) payload.password = form.password
  } else if (passwordAction.value === 'set' && form.password) {
    payload.password = form.password
  } else if (passwordAction.value === 'clear') {
    payload.password = ''
  }
  return payload
}

async function doSave() {
  if (loading.value || saving.value || notFound.value) return
  if (!form.title.trim()) {
    dirty.value = true // 触发标题错误提示
    toast.error(t('admin.editor.titleRequired'))
    return
  }
  if (slugError.value) {
    toast.error(t('admin.editor.slugInvalid'))
    return
  }
  saving.value = true
  try {
    const tagIds = await resolveTagIds(parseTagNames())
    const payload = buildPayload(tagIds)
    if (isEdit.value) {
      await apiFetch(`/blog/posts/${props.postId}`, { method: 'PUT', body: payload })
      if (passwordAction.value === 'set') hasPassword.value = true
      if (passwordAction.value === 'clear') hasPassword.value = false
      passwordAction.value = 'keep'
      form.password = ''
      markClean()
      clearDraft()
      toast.success(t('admin.editor.saved'))
    } else {
      const created = await apiFetch<{ id?: number }>('/blog/posts', { method: 'POST', body: payload })
      markClean()
      clearDraft()
      toast.success(t('admin.editor.created'))
      if (created?.id) {
        await navigateTo(`/admin/posts/${created.id}/edit`, { replace: true })
      }
    }
  } catch (e) {
    console.error('[PostForm] save failed:', e)
    toast.error(t('admin.editor.saveFailed'))
  } finally {
    saving.value = false
  }
}

/* ==================== Ctrl+S / 离开保护 ==================== */

function onWindowKeydown(e: KeyboardEvent) {
  if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 's') {
    e.preventDefault()
    // 编辑器内部已 emit save，避免重复触发
    const target = e.target as HTMLElement | null
    if (target?.closest?.('[data-md-editor]')) return
    doSave()
  }
}

function onBeforeUnload(e: BeforeUnloadEvent) {
  if (dirty.value && !saving.value) {
    e.preventDefault()
    e.returnValue = ''
  }
}

onBeforeRouteLeave(() => {
  if (dirty.value && !saving.value) {
    if (!window.confirm(t('admin.editor.confirmLeave'))) return false
  }
  return true
})

/* ==================== 生命周期 ==================== */

onMounted(async () => {
  if (import.meta.client) {
    window.addEventListener('keydown', onWindowKeydown)
    window.addEventListener('beforeunload', onBeforeUnload)
  }
  await loadMeta()
  if (isEdit.value) {
    await loadPost()
  } else {
    markClean()
    checkDraftAfterLoad()
  }
})

onBeforeUnmount(() => {
  if (import.meta.client) {
    window.removeEventListener('keydown', onWindowKeydown)
    window.removeEventListener('beforeunload', onBeforeUnload)
  }
  if (autosaveTimer) clearTimeout(autosaveTimer)
})
</script>
