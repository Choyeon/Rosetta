<!-- 翻译工具页：调后端同步翻译接口逐篇生成标题译文，供人工逐条复制，或经「写回标题」单条落库。
     契约：翻译端点本身只读；写回是显式逐行动作——先 GET /blog/posts/{id}/edit 拿完整多语言 title dict
     （公开口只回单语言字符串，直接 PUT 会抹掉其余语言），把新译文 merge 进 dict 后 PUT /blog/posts/{id}
     仅提交 { title }（PostUpdate exclude_unset，其余字段不动）；成败逐行内联展示。
     title 可能是 i18n dict 或旧纯文本，须经 titleText 归一否则译文源变 [object Object]；
     批量用 allSettled 单篇失败不阻断，且 apiFetch 已自动 toast 错误，页内 catch 不得二次提示（写回走 silentToast + 内联）。 -->
<template>
  <div class="flex flex-col gap-5">
    <AdminPageHeader
      title="翻译工具"
      description="使用后端同步接口逐篇翻译文章标题"
      :icon="Languages"
    />

    <div class="grid grid-cols-1 lg:grid-cols-3 gap-5">
      <AdminCard>
        <div class="flex flex-col gap-1.5 mb-4">
          <h3 class="text-base font-semibold">
            语言设置
          </h3>
          <p class="text-sm text-muted-foreground">
            选择源语言和目标翻译语言
          </p>
        </div>
        <div class="flex flex-col gap-4">
          <div class="flex flex-col gap-2">
            <Label
              for="tr-source-lang"
              class="text-sm font-medium"
            >源语言</Label>
            <Select
              v-model="form.sourceLang"
              class="rounded-xl"
            >
              <SelectTrigger id="tr-source-lang">
                <SelectValue placeholder="选择源语言" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem
                  v-for="lang in langOptions"
                  :key="lang.value"
                  :value="lang.value"
                >
                  {{ lang.label }}
                </SelectItem>
              </SelectContent>
            </Select>
          </div>
          <div class="flex flex-col gap-2">
            <Label class="text-sm font-medium">目标语言（可多选）</Label>
            <div class="flex flex-col gap-2 rounded-xl border border-border p-3 bg-muted/20">
              <label
                v-for="lang in langOptions"
                :key="lang.value"
                class="flex items-center gap-2 cursor-pointer p-2 rounded-lg hover:bg-muted transition-colors"
                :class="{ 'opacity-40 pointer-events-none': form.sourceLang === lang.value }"
              >
                <Checkbox
                  :model-value="form.targetLangs.includes(lang.value)"
                  :disabled="form.sourceLang === lang.value"
                  @update:model-value="toggleTarget(lang.value, $event)"
                />
                <span class="text-sm">{{ lang.label }}</span>
              </label>
            </div>
          </div>
        </div>
      </AdminCard>

      <AdminCard>
        <div class="flex flex-col gap-1.5 mb-4">
          <h3 class="text-base font-semibold">
            选择文章
          </h3>
          <p class="text-sm text-muted-foreground">
            从最近文章中选择单篇或多篇
          </p>
        </div>
        <div class="flex flex-col gap-4">
          <div class="flex flex-col gap-2">
            <Label
              for="tr-quick-post"
              class="text-sm font-medium"
            >单篇快速翻译</Label>
            <div class="flex gap-2">
              <Input
                id="tr-quick-post"
                v-model.number="quickPostId"
                type="number"
                placeholder="输入已加载的文章 ID"
                class="rounded-xl"
              />
              <Button
                variant="outline"
                class="rounded-xl shrink-0"
                :disabled="translatingQuick || !quickPostId || form.targetLangs.length === 0"
                @click="handleQuickTranslate"
              >
                <Loader2
                  v-if="translatingQuick"
                  data-icon="inline-start"
                  class="animate-spin"
                />
                <Zap
                  v-else
                  data-icon="inline-start"
                />
                立即翻译
              </Button>
            </div>
          </div>
          <Separator />
          <div class="relative">
            <Search class="size-4 absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground" />
            <Input
              v-model="postSearch"
              placeholder="按标题搜索..."
              class="rounded-xl pl-9"
            />
          </div>
          <div class="rounded-xl border border-border overflow-hidden bg-muted/10 max-h-56 overflow-y-auto">
            <div
              v-if="postsLoading"
              class="p-5 text-center text-sm text-muted-foreground"
            >
              正在加载文章...
            </div>
            <!-- 加载失败必须与"真的没有文章"区分开：旧实现 catch 后只剩空数组，
                 用户看到「暂无文章」，会误以为站点还没建内容，实际上是接口挂了。 -->
            <div
              v-else-if="postsError"
              class="p-5 flex flex-col items-center gap-2 text-center"
              role="alert"
            >
              <AlertTriangle class="size-5 text-warning" />
              <p class="text-sm font-medium text-foreground/90">
                文章列表加载失败
              </p>
              <p class="text-xs text-muted-foreground break-all">
                {{ postsError }}
              </p>
              <Button
                variant="outline"
                size="sm"
                class="rounded-lg"
                @click="loadPosts"
              >
                <RotateCcw data-icon="inline-start" />
                重试
              </Button>
            </div>
            <div
              v-else-if="filteredPosts.length === 0"
              class="p-5 text-center text-sm text-muted-foreground"
            >
              {{ postSearch ? '未找到匹配的文章' : '暂无文章' }}
            </div>
            <template v-else>
              <label
                v-for="post in filteredPosts"
                :key="post.id"
                class="flex items-start gap-2 p-3 hover:bg-muted transition-colors cursor-pointer border-b last:border-b-0 border-border/50"
              >
                <Checkbox
                  :model-value="form.postIds.includes(post.id)"
                  @update:model-value="togglePost(post.id, $event)"
                />
                <div class="flex-1 min-w-0">
                  <div class="font-medium truncate text-sm">{{ titleText(post.title) }}</div>
                  <div class="text-xs text-muted-foreground font-mono">#{{ post.id }}</div>
                </div>
              </label>
            </template>
          </div>
        </div>
      </AdminCard>

      <AdminCard>
        <div class="flex flex-col gap-1.5 mb-4">
          <h3 class="text-base font-semibold">
            开始翻译
          </h3>
          <p class="text-sm text-muted-foreground">
            按文章和目标语言逐项同步执行
          </p>
        </div>
        <div class="gap-4 h-full flex flex-col">
          <div class="flex flex-col gap-2 rounded-xl p-4 bg-muted/30 flex-1">
            <div class="flex items-center justify-between text-sm">
              <span class="text-muted-foreground">源语言</span><span class="font-medium">{{ labelOf(form.sourceLang) }}</span>
            </div>
            <div class="flex items-center justify-between text-sm">
              <span class="text-muted-foreground">目标语言</span><span class="font-medium">{{ form.targetLangs.length ? form.targetLangs.map(labelOf).join(' / ') : '未选' }}</span>
            </div>
            <div class="flex items-center justify-between text-sm">
              <span class="text-muted-foreground">文章数量</span><span class="font-medium">{{ form.postIds.length }} 篇</span>
            </div>
            <div class="flex items-center justify-between text-sm">
              <span class="text-muted-foreground">本次成功</span><span class="font-medium">{{ translatedCount }} 项</span>
            </div>
          </div>
          <Button
            :disabled="batchSubmitting || form.postIds.length === 0 || form.targetLangs.length === 0"
            class="text-white w-full shadow-sm bg-primary hover:bg-primary/90"
            @click="handleBatchTranslate"
          >
            <Loader2
              v-if="batchSubmitting"
              data-icon="inline-start"
              class="animate-spin"
            />
            <Send
              v-else
              data-icon="inline-start"
            />
            {{ batchSubmitting ? '正在翻译...' : '开始翻译' }}
          </Button>
        </div>
      </AdminCard>
    </div>

    <!-- ==================== 翻译结果 ==================== -->
    <AdminCard>
      <div class="flex flex-col gap-1.5 mb-4">
        <h3 class="flex items-center gap-2 text-base font-semibold">
          <ClipboardList class="size-5 text-primary" />
          翻译结果（{{ results.length }}）
        </h3>
        <p class="text-sm text-muted-foreground">
          后端返回的各语言译文，可逐条复制；不会自动写回文章——需要落库请点行内「写回标题」（仅合并该语言标题，其余语言不动）。
        </p>
      </div>
      <div
        v-if="results.length === 0"
        class="rounded-xl border border-dashed border-border p-8 text-center text-sm text-muted-foreground"
      >
        暂无翻译结果，先在上方选择文章并点击"开始翻译"。
      </div>
      <div
        v-else
        class="rounded-xl border border-border overflow-hidden"
      >
        <div class="max-h-96 overflow-y-auto divide-y divide-border/60">
          <div
            v-for="row in results"
            :key="row.key"
            class="px-4 py-3 flex items-start gap-3 hover:bg-muted/30"
          >
            <div class="w-44 shrink-0 min-w-0">
              <div
                class="text-sm font-medium truncate"
                :title="row.postTitle"
              >
                {{ row.postTitle }}
              </div>
              <div class="text-xs text-muted-foreground font-mono">
                #{{ row.postId }}
              </div>
            </div>
            <Badge
              variant="secondary"
              class="shrink-0 rounded-full text-xs"
            >
              {{ row.langLabel }}
            </Badge>
            <div class="flex-1 min-w-0 text-sm break-words">
              {{ row.text }}
            </div>
            <div class="shrink-0 flex flex-col items-end gap-1">
              <div class="flex items-center gap-1">
                <Button
                  variant="ghost"
                  size="icon-sm"
                  class="text-muted-foreground hover:text-foreground"
                  title="复制译文"
                  aria-label="复制译文"
                  @click="copyTranslation(row)"
                >
                  <Check
                    v-if="copiedKey === row.key"
                    class="text-success"
                  />
                  <Copy v-else />
                </Button>
                <Button
                  variant="outline"
                  size="sm"
                  class="rounded-lg"
                  :disabled="writebacks[row.key]?.state === 'saving'"
                  title="把该译文合并写回文章的对应语言标题"
                  @click="writeBackTitle(row)"
                >
                  <Loader2
                    v-if="writebacks[row.key]?.state === 'saving'"
                    data-icon="inline-start"
                    class="animate-spin"
                  />
                  <Save
                    v-else
                    data-icon="inline-start"
                  />
                  写回标题
                </Button>
              </div>
              <p
                v-if="writebacks[row.key]"
                class="max-w-48 text-right text-xs break-words"
                :class="writebacks[row.key]?.state === 'ok' ? 'text-success' : writebacks[row.key]?.state === 'error' ? 'text-destructive' : 'text-muted-foreground'"
                :role="writebacks[row.key]?.state === 'error' ? 'alert' : undefined"
              >
                {{ writebacks[row.key]?.message }}
              </p>
            </div>
          </div>
        </div>
      </div>
      <div
        v-if="results.length > 0"
        class="flex justify-end mt-3"
      >
        <Button
          variant="outline"
          size="sm"
          class="rounded-xl"
          @click="clearResults"
        >
          <Eraser
            data-icon="inline-start"
          />
          清空结果
        </Button>
      </div>
    </AdminCard>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { fetchRecentPosts, translateAdminText, type AdminPostListItem } from '~~/composables/useAdminManage'
import { apiFetch } from '~~/composables/useApi'
import { useToast } from '~~/composables/useToast'
import { ClipboardList, Copy, Check, Eraser, Languages, Loader2, Search, Send, Zap, AlertTriangle, RotateCcw, Save } from '@lucide/vue'
import { Button } from '~~/components/ui/button'
import AdminCard from '~~/components/admin/AdminCard.vue'
import { Badge } from '~~/components/ui/badge'
import { Checkbox } from '~~/components/ui/checkbox'
import { Input } from '~~/components/ui/input'
import { Label } from '~~/components/ui/label'
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue
} from '~~/components/ui/select'
import { Separator } from '~~/components/ui/separator'
import { extractApiErrorMessage } from '~~/lib/utils'

definePageMeta({ ssr: false, layout: 'admin' })

const toast = useToast()
/**
 * 语言选项单源镜像：frontend/i18n.config.ts 的 availableLocales（zh / zh_Hant / en / ja，
 * 站点固定四语、后端 backend/core/i18n.py 为语言唯一真源，不新增第五语）。
 * 展示名同时参考 backend/api/translate.py::LANG_NAMES，两处任一变更语言集合时这里必须同步。
 */
const langOptions = [
  { label: '简体中文 (zh)', value: 'zh' },
  { label: 'English (en)', value: 'en' },
  { label: '日本語 (ja)', value: 'ja' },
  { label: '繁體中文 (zh_Hant)', value: 'zh_Hant' }
]
const form = reactive({ sourceLang: 'zh', targetLangs: [] as string[], postIds: [] as number[] })
const quickPostId = ref<number>()
const postSearch = ref('')
const posts = shallowRef<AdminPostListItem[]>([])
const postsLoading = ref(false)
const postsError = ref('')
const translatingQuick = ref(false)
const batchSubmitting = ref(false)
const translatedCount = ref(0)

/** 翻译结果行：一次调用（文章 × 语言）一条 */
interface TranslateResultRow {
  key: string
  postId: number
  postTitle: string
  lang: string
  langLabel: string
  text: string
}
const results = ref<TranslateResultRow[]>([])
const copiedKey = ref<string | null>(null)
/** 逐行「写回标题」状态（键为 row.key）：saving/ok/error + 内联提示文案 */
type WritebackState = 'saving' | 'ok' | 'error'
const writebacks = ref<Record<string, { state: WritebackState, message: string }>>({})
let rowSeq = 0
/** 多语言文章的 title 可能是 {zh,en,ja,zh_Hant} 对象，直接 String() 会得到 [object Object] */
function titleText(title: unknown): string {
  // 译文工具要的是"这份内容长什么样"，与界面语言无关，所以固定按 zh 优先取。
  return pickLocalizedText(title, 'zh')
}
const filteredPosts = computed(() => {
  const keyword = postSearch.value.trim().toLowerCase()
  return keyword ? posts.value.filter(post => titleText(post.title).toLowerCase().includes(keyword) || String(post.id).includes(keyword)) : posts.value
})
function labelOf(code: string) {
  return langOptions.find(lang => lang.value === code)?.label ?? code
}
function toggleTarget(code: string, checked: boolean | 'indeterminate') {
  if (checked === true || checked === 'indeterminate') {
    if (!form.targetLangs.includes(code)) form.targetLangs.push(code)
  } else form.targetLangs = form.targetLangs.filter(item => item !== code)
}
function togglePost(id: number, checked: boolean | 'indeterminate') {
  if (checked === true || checked === 'indeterminate') {
    if (!form.postIds.includes(id)) form.postIds.push(id)
  } else form.postIds = form.postIds.filter(item => item !== id)
}
/**
 * 翻译单篇文章标题：调用后端拿到 {translations: {lang: text}} 后，
 * 逐语言写入结果列表（此前只数了个数量、结果被丢弃）。
 */
async function translatePost(post: AdminPostListItem) {
  const title = titleText(post.title)
  const result = await translateAdminText(title, form.sourceLang, form.targetLangs)
  const entries = Object.entries(result?.translations ?? {})
  for (const [lang, text] of entries) {
    results.value.unshift({
      key: `r${++rowSeq}`,
      postId: post.id,
      postTitle: title,
      lang,
      langLabel: labelOf(lang),
      text
    })
  }
  return entries.length
}
async function handleQuickTranslate() {
  const post = posts.value.find(item => item.id === quickPostId.value)
  if (!post || form.targetLangs.length === 0) return toast.warning('请选择真实文章并至少选择一个目标语言')
  translatingQuick.value = true
  try {
    const success = await translatePost(post)
    translatedCount.value += success
    toast.success(`已完成 ${success} 个语言翻译`)
    quickPostId.value = undefined
  } catch {
    // translateAdminText 内部的 apiFetch 已 toast，这里不再二次提示
  } finally {
    translatingQuick.value = false
  }
}
async function handleBatchTranslate() {
  if (!form.postIds.length || !form.targetLangs.length) return toast.warning('请选择文章和目标语言')
  batchSubmitting.value = true
  try {
    // 并行翻译：Promise.allSettled 保证单篇失败不阻断其他翻译
    const targets = form.postIds
      .map(id => posts.value.find(item => item.id === id))
      .filter((p): p is AdminPostListItem => !!p)
    const results_ = await Promise.allSettled(targets.map(post => translatePost(post)))
    const success = results_.reduce((acc, r) => acc + (r.status === 'fulfilled' ? r.value : 0), 0)
    translatedCount.value += success
    const failed = results_.filter(r => r.status === 'rejected').length
    if (failed === 0) toast.success(`翻译完成，成功 ${success} 项`)
    else toast.warning(`翻译完成，成功 ${success} 项，失败 ${failed} 篇`)
  } catch (error) {
    const msg = error instanceof Error ? error.message : '批量翻译失败'
    toast.error(msg)
  } finally {
    batchSubmitting.value = false
  }
}
async function copyTranslation(row: TranslateResultRow) {
  try {
    await navigator.clipboard.writeText(row.text)
    copiedKey.value = row.key
    window.setTimeout(() => {
      if (copiedKey.value === row.key) copiedKey.value = null
    }, 1500)
  } catch {
    toast.error('复制失败，请手动选择译文复制')
  }
}
function clearResults() {
  results.value = []
  writebacks.value = {}
}
/**
 * 「写回标题」：把这一行译文合并进该文章的 title i18n dict 并 PUT。
 * 必须先 GET /blog/posts/{id}/edit（staff 编辑口，返回完整 dict）——公开详情口回显的是
 * 按语言裁剪后的单值，直接 PUT 字符串会让后端把它当整份 title 覆写、其余语言整列蒸发。
 * PUT body 只带 { title }：PostUpdate 走 exclude_unset，status/content 等一概不动。
 * 失败不外抛（apiFetch 配 silentToast），状态与原因落在该行右侧内联展示，可再次点击重试。
 */
async function writeBackTitle(row: TranslateResultRow) {
  if (!row.text.trim()) return toast.warning('译文为空，无可写回内容')
  writebacks.value = { ...writebacks.value, [row.key]: { state: 'saving', message: '写回中…' } }
  try {
    const edit = await apiFetch<{ title?: Record<string, string> | string | null }>(
      `/blog/posts/${row.postId}/edit`,
      { silentToast: true }
    )
    // 旧行可能是纯文本 title：按 zh 归档，避免覆写时丢键
    const current = typeof edit?.title === 'string'
      ? { zh: edit.title }
      : { ...(edit?.title ?? {}) }
    const merged = { ...current, [row.lang]: row.text }
    await apiFetch(`/blog/posts/${row.postId}`, {
      method: 'PUT',
      body: { title: merged },
      silentToast: true
    })
    writebacks.value = { ...writebacks.value, [row.key]: { state: 'ok', message: `已写回 ${row.langLabel} 标题` } }
  } catch (e) {
    const err = e as { data?: unknown, message?: string }
    writebacks.value = {
      ...writebacks.value,
      [row.key]: { state: 'error', message: extractApiErrorMessage(err?.data, err?.message || '写回失败，可重试') }
    }
  }
}
/** 抽取成具名函数是为了让上面那个「重试」按钮能复用同一段加载逻辑 */
async function loadPosts() {
  postsLoading.value = true
  postsError.value = ''
  try {
    posts.value = await fetchRecentPosts(50)
  } catch (e) {
    // apiFetch 的统一 toast 负责全局提示；这里再补一条内联错误态，
    // 因为选择器本身是独立的失败界面，空列表会被误读成"没有文章"。
    posts.value = []
    const err = e as { data?: unknown, message?: string }
    postsError.value = extractApiErrorMessage(err?.data, err?.message || '加载文章列表失败')
  } finally {
    postsLoading.value = false
  }
}
onMounted(loadPosts)
</script>
