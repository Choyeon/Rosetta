<template>
  <div class="flex flex-col gap-5">
    <AdminPageHeader
      title="翻译工具"
      description="使用后端同步接口逐篇翻译文章标题"
      :icon="Languages"
    />

    <div class="grid grid-cols-1 lg:grid-cols-3 gap-5">
      <AdminCard>
        <div class="flex flex-col gap-1 .5 mb-4">
          <h3 class="text-base font-semibold">
            语言设置
          </h3>
          <p class="text-sm text-muted-foreground">
            选择源语言和目标翻译语言
          </p>
        </div>
        <div class="flex flex-col gap-4">
          <div class="flex flex-col gap-2">
            <Label class="text-sm font-medium">源语言</Label>
            <Select
              v-model="form.sourceLang"
              class="rounded-xl"
            >
              <SelectTrigger>
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
        <div class="flex flex-col gap-1 .5 mb-4">
          <h3 class="text-base font-semibold">
            选择文章
          </h3>
          <p class="text-sm text-muted-foreground">
            从最近文章中选择单篇或多篇
          </p>
        </div>
        <div class="flex flex-col gap-4">
          <div class="flex flex-col gap-2">
            <Label class="text-sm font-medium">单篇快速翻译</Label>
            <div class="flex gap-2">
              <Input
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
                  <div class="font-medium truncate text-sm">{{ post.title }}</div>
                  <div class="text-xs text-muted-foreground font-mono">#{{ post.id }}</div>
                </div>
              </label>
            </template>
          </div>
        </div>
      </AdminCard>

      <AdminCard>
        <div class="flex flex-col gap-1 .5 mb-4">
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
          后端返回的各语言译文，可逐条复制；仅生成结果，不会自动写回文章。
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
            <Button
              variant="ghost"
              size="icon-sm"
              class="shrink-0 text-muted-foreground hover:text-foreground"
              title="复制译文"
              @click="copyTranslation(row)"
            >
              <Check
                v-if="copiedKey === row.key"
                class="text-success"
              />
              <Copy v-else />
            </Button>
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
          @click="results = []"
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
import { useToast } from '~~/composables/useToast'
import { ClipboardList, Copy, Check, Eraser, Languages, Loader2, Search, Send, Zap } from '@lucide/vue'
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

definePageMeta({ ssr: false, layout: 'admin' })

const toast = useToast()
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
let rowSeq = 0
const filteredPosts = computed(() => {
  const keyword = postSearch.value.trim().toLowerCase()
  return keyword ? posts.value.filter(post => String(post.title).toLowerCase().includes(keyword) || String(post.id).includes(keyword)) : posts.value
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
  const result = await translateAdminText(String(post.title), form.sourceLang, form.targetLangs)
  const entries = Object.entries(result?.translations ?? {})
  for (const [lang, text] of entries) {
    results.value.unshift({
      key: `r${++rowSeq}`,
      postId: post.id,
      postTitle: String(post.title),
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
  } catch (error) {
    const msg = error instanceof Error ? error.message : '翻译失败'
    toast.error(msg)
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
onMounted(async () => {
  postsLoading.value = true
  try {
    posts.value = await fetchRecentPosts(50)
  } catch {
    // 文章列表加载失败时保持空列表
  } finally {
    postsLoading.value = false
  }
})
</script>
