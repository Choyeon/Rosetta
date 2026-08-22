<template>
  <div class="p-6 space-y-6">
    <div class="flex items-center gap-3">
      <div
        class="size-10 rounded-xl flex items-center justify-center bg-primary text-primary-foreground"
      >
        <Languages class="size-5 text-white" />
      </div>
      <div>
        <h1 class="text-xl font-bold tracking-tight">
          翻译工具
        </h1>
        <p class="text-sm text-muted-foreground">
          使用后端同步接口逐篇翻译文章标题
        </p>
      </div>
    </div>

    <div class="grid grid-cols-1 lg:grid-cols-3 gap-5">
      <Card class="rounded-2xl">
        <CardHeader>
          <CardTitle class="text-base">
            语言设置
          </CardTitle>
          <CardDescription>选择源语言和目标翻译语言</CardDescription>
        </CardHeader>
        <CardContent class="space-y-4">
          <div class="space-y-2">
            <Label class="text-sm font-medium">源语言</Label>
            <Select
              v-model="form.sourceLang"
              :options="langOptions"
              class="rounded-xl"
            />
          </div>
          <div class="space-y-2">
            <Label class="text-sm font-medium">目标语言（可多选）</Label>
            <div class="rounded-xl border border-border p-3 space-y-2 bg-muted/20">
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
        </CardContent>
      </Card>

      <Card class="rounded-2xl">
        <CardHeader>
          <CardTitle class="text-base">
            选择文章
          </CardTitle>
          <CardDescription>从最近文章中选择单篇或多篇</CardDescription>
        </CardHeader>
        <CardContent class="space-y-4">
          <div class="space-y-2">
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
                  class="size-4 animate-spin"
                />
                <Zap
                  v-else
                  class="size-4"
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
            <label
              v-for="post in filteredPosts"
              v-else
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
          </div>
        </CardContent>
      </Card>

      <Card class="rounded-2xl">
        <CardHeader>
          <CardTitle class="text-base">
            开始翻译
          </CardTitle>
          <CardDescription>按文章和目标语言逐项同步执行</CardDescription>
        </CardHeader>
        <CardContent class="space-y-4 h-full flex flex-col">
          <div class="rounded-xl p-4 space-y-2 bg-muted/30 flex-1">
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
              class="size-4 animate-spin"
            />
            <Send
              v-else
              class="size-4"
            />
            {{ batchSubmitting ? '正在翻译...' : '开始翻译' }}
          </Button>
        </CardContent>
      </Card>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { fetchRecentPosts, translateAdminText, type AdminPostListItem } from '~~/composables/useAdminManage'
import { useToast } from '~~/composables/useToast'
import { Languages, Loader2, Search, Send, Zap } from '@lucide/vue'
import { Button } from '~~/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '~~/components/ui/card'
import { Checkbox } from '~~/components/ui/checkbox'
import { Input } from '~~/components/ui/input'
import { Label } from '~~/components/ui/label'
import { Select } from '~~/components/ui/select'
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
const posts = ref<AdminPostListItem[]>([])
const postsLoading = ref(false)
const translatingQuick = ref(false)
const batchSubmitting = ref(false)
const translatedCount = ref(0)
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
async function translatePost(post: AdminPostListItem) {
  const result = await translateAdminText(String(post.title), form.sourceLang, form.targetLangs)
  return Object.keys(result.translations).length
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
    toast.error(error instanceof Error ? error.message : '翻译失败')
  } finally {
    translatingQuick.value = false
  }
}
async function handleBatchTranslate() {
  if (!form.postIds.length || !form.targetLangs.length) return toast.warning('请选择文章和目标语言')
  batchSubmitting.value = true
  let success = 0
  try {
    for (const id of form.postIds) {
      const post = posts.value.find(item => item.id === id)
      if (post) success += await translatePost(post)
    }
    translatedCount.value += success
    toast.success(`翻译完成，成功 ${success} 项`)
  } catch (error) {
    toast.error(error instanceof Error ? error.message : '翻译失败')
  } finally {
    batchSubmitting.value = false
  }
}
onMounted(async () => {
  postsLoading.value = true
  try {
    posts.value = await fetchRecentPosts(50)
  } catch (error) {
    toast.error(error instanceof Error ? error.message : '文章加载失败')
  } finally {
    postsLoading.value = false
  }
})
</script>
