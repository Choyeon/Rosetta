<script setup lang="ts">
/* eslint-disable */
/* eslint-disable @typescript-eslint/ban-ts-comment */
// @ts-nocheck
/* eslint-enable @typescript-eslint/ban-ts-comment */
import { ref, computed, onMounted, watch } from 'vue'
import { useRouter } from 'vue-router'
import { usePosts } from '~~/composables/usePosts'
import {
  fetchAdminCategories,
  formatAdminDateTime,
  type AdminCategory
} from '~~/composables/useAdminManage'
import { useToast } from '~~/composables/useToast'
import type { Post } from '~~/types/api'
import { Button } from '~~/components/ui/button'
import { Input } from '~~/components/ui/input'
import { Badge } from '~~/components/ui/badge'
import { Checkbox } from '~~/components/ui/checkbox'
import { Skeleton } from '~~/components/ui/skeleton'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue
} from '~~/components/ui/select'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle
} from '~~/components/ui/dialog'

definePageMeta({ ssr: false, layout: 'admin' })

const router = useRouter()
const { fetchPosts, deletePost, batchUpdatePostStatus } = usePosts()
const toast = useToast()

const posts = ref<Post[]>([])
const loading = ref(false)
const total = ref(0)
const page = ref(1)
const pageSize = ref(10)
const totalPages = ref(0)

const searchQuery = ref('')
const statusFilter = ref<string>('all')
const categoryFilter = ref<string>('all')

const categories = ref<AdminCategory[]>([])
const selectedIds = ref<number[]>([])
const deleteDialogOpen = ref(false)
const pendingDeleteId = ref<number | null>(null)
const batchDeleteDialogOpen = ref(false)

const getLocalizedStr = (v: string | Record<string, string> | null | undefined): string => {
  if (v == null) return ''
  if (typeof v === 'string') return v
  return v.zh || v.en || Object.values(v)[0] || ''
}

const statusBadgeVariant = (status: string): string => {
  switch (status) {
    case 'published': return 'bg-emerald-100 text-emerald-700 border-emerald-200'
    case 'draft': return 'bg-amber-100 text-amber-700 border-amber-200'
    case 'scheduled': return 'bg-indigo-100 text-indigo-700 border-indigo-200'
    case 'archived': return 'bg-slate-100 text-slate-600 border-slate-200'
    default: return 'bg-slate-100 text-slate-600 border-slate-200'
  }
}

const statusLabel = (status: string): string => {
  switch (status) {
    case 'published': return '已发布'
    case 'draft': return '草稿'
    case 'scheduled': return '定时'
    case 'archived': return '已归档'
    default: return status
  }
}

let searchTimer: ReturnType<typeof setTimeout> | null = null
watch(searchQuery, () => {
  if (searchTimer) clearTimeout(searchTimer)
  searchTimer = setTimeout(() => {
    page.value = 1
    loadPosts()
  }, 500)
})

watch([statusFilter, categoryFilter, page, pageSize], () => {
  loadPosts()
})

const loadPosts = async () => {
  loading.value = true
  try {
    const data = await fetchPosts({
      page: page.value,
      page_size: pageSize.value,
      search: searchQuery.value.trim() || undefined,
      status: statusFilter.value !== 'all' ? statusFilter.value : undefined,
      category: categoryFilter.value !== 'all' ? categoryFilter.value : undefined
    })
    posts.value = Array.isArray(data) ? data : []
    const postsStore = usePosts()
    total.value = postsStore.total.value || posts.value.length
    totalPages.value = Math.max(1, Math.ceil(total.value / pageSize.value))
  } catch (e) {
    toast.error(e instanceof Error ? e.message : '加载文章列表失败')
    posts.value = []
    total.value = 0
    totalPages.value = 1
  } finally {
    loading.value = false
  }
}

const loadCategories = async () => {
  try {
    categories.value = await fetchAdminCategories()
  } catch {
    categories.value = []
  }
}

const refresh = () => {
  loadPosts()
}

const isSelected = (id: number) => selectedIds.value.includes(id)
const toggleSelected = (id: number) => {
  const idx = selectedIds.value.indexOf(id)
  if (idx === -1) selectedIds.value.push(id)
  else selectedIds.value.splice(idx, 1)
}

const isAllSelected = computed(() => {
  return posts.value.length > 0 && posts.value.every(p => isSelected(p.id))
})

const isSomeSelected = computed(() => {
  return posts.value.some(p => isSelected(p.id)) && !isAllSelected.value
})

const toggleSelectAll = () => {
  if (isAllSelected.value) {
    selectedIds.value = []
  } else {
    selectedIds.value = [...new Set([...selectedIds.value, ...posts.value.map(p => p.id)])]
  }
}

const confirmDelete = (id: number) => {
  pendingDeleteId.value = id
  deleteDialogOpen.value = true
}

const doDelete = async () => {
  if (pendingDeleteId.value == null) return
  const id = pendingDeleteId.value
  try {
    const { error } = await deletePost(id)
    if (error.value) throw error.value
    toast.success('删除成功')
    deleteDialogOpen.value = false
    pendingDeleteId.value = null
    selectedIds.value = selectedIds.value.filter(x => x !== id)
    loadPosts()
  } catch (e) {
    toast.error(e instanceof Error ? e.message : '删除失败')
  }
}

const confirmBatchDelete = () => {
  batchDeleteDialogOpen.value = true
}

const doBatchDelete = async () => {
  const ids = [...selectedIds.value]
  let failed = 0
  for (const id of ids) {
    try {
      const { error } = await deletePost(id)
      if (error.value) throw error.value
      selectedIds.value = selectedIds.value.filter(x => x !== id)
    } catch {
      failed++
    }
  }
  if (failed === 0) toast.success(`已批量删除 ${ids.length} 篇文章`)
  else toast.warning(`成功删除 ${ids.length - failed} 篇，失败 ${failed} 篇`)
  batchDeleteDialogOpen.value = false
  loadPosts()
}

const batchChangeStatus = async (status: 'published' | 'draft' | 'scheduled') => {
  const ids = [...selectedIds.value]

  try {
    const { data, error } = await batchUpdatePostStatus(ids, status)
    if (error.value) throw error.value

    const updatedCount = data.value?.data.updated_count ?? 0
    const unavailableCount = ids.length - updatedCount
    if (unavailableCount === 0) toast.success(`已批量修改 ${updatedCount} 篇文章状态`)
    else toast.warning(`成功修改 ${updatedCount} 篇，未授权或不存在 ${unavailableCount} 篇`)
    selectedIds.value = []
    await loadPosts()
  } catch (e) {
    toast.error(e instanceof Error ? e.message : '批量修改文章状态失败')
  }
}

const goToPage = (p: number) => {
  if (p < 1 || p > totalPages.value) return
  page.value = p
}

const pageNumbers = computed(() => {
  const total = totalPages.value
  const cur = page.value
  const pages: (number | string)[] = []
  const push = (v: number | string) => pages.push(v)
  if (total <= 7) {
    for (let i = 1; i <= total; i++) push(i)
  } else {
    if (cur <= 4) {
      for (let i = 1; i <= 5; i++) push(i)
      push('...')
      push(total)
    } else if (cur >= total - 3) {
      push(1)
      push('...')
      for (let i = total - 4; i <= total; i++) push(i)
    } else {
      push(1)
      push('...')
      for (let i = cur - 1; i <= cur + 1; i++) push(i)
      push('...')
      push(total)
    }
  }
  return pages
})

onMounted(() => {
  loadCategories()
  loadPosts()
})
</script>

<template>
  <div class="flex flex-col gap-5 p-6">
    <div class="flex flex-col gap-3">
      <div class="flex items-center justify-between">
        <div class="flex items-center gap-3">
          <h1 class="text-2xl font-bold tracking-tight">
            文章管理
          </h1>
          <Badge
            variant="secondary"
            class="rounded-[10px] px-3 py-1 bg-stone-100 text-stone-700 border-stone-200"
          >
            共 {{ total }} 篇
          </Badge>
        </div>
        <Button
          class="rounded-[12px] h-11 px-5 bg-gradient-to-r from-amber-500 to-orange-500 text-white hover:from-amber-600 hover:to-orange-600 shadow-sm"
          @click="router.push('/admin/content/posts/new')"
        >
          + 新建文章
        </Button>
      </div>

      <div class="flex flex-wrap items-center gap-3">
        <div class="flex-1 min-w-64">
          <Input
            v-model="searchQuery"
            placeholder="🔍 搜索标题 / slug / 摘要"
            class="h-10 rounded-[12px] pl-4"
          />
        </div>
        <Select v-model="statusFilter">
          <SelectTrigger class="h-10 w-36 rounded-[12px]">
            <SelectValue placeholder="状态" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">
              全部状态
            </SelectItem>
            <SelectItem value="published">
              已发布
            </SelectItem>
            <SelectItem value="draft">
              草稿
            </SelectItem>
            <SelectItem value="scheduled">
              定时
            </SelectItem>
            <SelectItem value="archived">
              已归档
            </SelectItem>
          </SelectContent>
        </Select>
        <Select v-model="categoryFilter">
          <SelectTrigger class="h-10 w-40 rounded-[12px]">
            <SelectValue placeholder="分类" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">
              全部分类
            </SelectItem>
            <SelectItem
              v-for="c in categories"
              :key="c.id"
              :value="c.slug || c.id.toString()"
            >
              {{ getLocalizedStr(c.name) }}
            </SelectItem>
          </SelectContent>
        </Select>
        <Button
          variant="outline"
          class="h-10 rounded-[12px]"
          @click="refresh"
        >
          🔄 刷新
        </Button>
      </div>
    </div>

    <div
      v-if="selectedIds.length > 0"
      class="flex items-center justify-between rounded-[12px] border border-amber-200 bg-amber-50 px-5 py-3"
    >
      <span class="text-sm text-amber-800">
        已选择 <strong>{{ selectedIds.length }}</strong> 条记录
      </span>
      <div class="flex items-center gap-2">
        <Button
          variant="outline"
          size="sm"
          class="rounded-[10px] h-9"
          @click="batchChangeStatus('published')"
        >
          批量发布
        </Button>
        <Button
          variant="outline"
          size="sm"
          class="rounded-[10px] h-9"
          @click="batchChangeStatus('draft')"
        >
          批量转草稿
        </Button>
        <Button
          variant="destructive"
          size="sm"
          class="rounded-[10px] h-9"
          @click="confirmBatchDelete"
        >
          批量删除
        </Button>
      </div>
    </div>

    <div class="rounded-[12px] border border-border bg-card overflow-hidden">
      <div class="overflow-x-auto">
        <div class="min-w-[1100px]">
          <div class="grid grid-cols-[auto,auto,1fr,120px,110px,80px,80px,90px,70px,160px,130px] bg-stone-50/80 border-b border-border text-xs font-medium text-muted-foreground">
            <div class="p-3 flex items-center justify-center w-11">
              <Checkbox
                :checked="isAllSelected"
                :indeterminate="isSomeSelected"
                @update:checked="toggleSelectAll"
              />
            </div>
            <div class="p-3 w-16">
              ID
            </div>
            <div class="p-3">
              标题
            </div>
            <div class="p-3">
              分类
            </div>
            <div class="p-3">
              状态
            </div>
            <div class="p-3 text-center">
              浏览
            </div>
            <div class="p-3 text-center">
              点赞
            </div>
            <div class="p-3 text-center">
              评论
            </div>
            <div class="p-3 text-center">
              置顶
            </div>
            <div class="p-3">
              发布时间
            </div>
            <div class="p-3 text-center">
              操作
            </div>
          </div>

          <template v-if="loading">
            <div
              v-for="i in 5"
              :key="`sk-${i}`"
              class="grid grid-cols-[auto,auto,1fr,120px,110px,80px,80px,90px,70px,160px,130px] border-b border-border/50"
            >
              <div class="p-3 w-11 flex items-center justify-center">
                <Skeleton class="h-4 w-4 rounded" />
              </div>
              <div class="p-3 w-16">
                <Skeleton class="h-4 w-8 rounded" />
              </div>
              <div class="p-3">
                <Skeleton class="h-5 w-3/4 rounded mb-1" /><Skeleton class="h-3 w-1/2 rounded" />
              </div>
              <div class="p-3">
                <Skeleton class="h-5 w-20 rounded-full" />
              </div>
              <div class="p-3">
                <Skeleton class="h-5 w-16 rounded-full" />
              </div>
              <div class="p-3">
                <Skeleton class="h-4 w-10 rounded mx-auto" />
              </div>
              <div class="p-3">
                <Skeleton class="h-4 w-10 rounded mx-auto" />
              </div>
              <div class="p-3">
                <Skeleton class="h-4 w-10 rounded mx-auto" />
              </div>
              <div class="p-3">
                <Skeleton class="h-4 w-8 rounded mx-auto" />
              </div>
              <div class="p-3">
                <Skeleton class="h-4 w-32 rounded" />
              </div>
              <div class="p-3 flex gap-2 justify-center">
                <Skeleton class="h-8 w-14 rounded" /><Skeleton class="h-8 w-14 rounded" />
              </div>
            </div>
          </template>

          <template v-else-if="posts.length === 0">
            <div class="py-20 text-center text-muted-foreground">
              <div class="text-5xl mb-3 opacity-30">
                📝
              </div>
              <div class="text-sm">
                暂无文章数据
              </div>
            </div>
          </template>

          <template v-else>
            <div
              v-for="(p, idx) in posts"
              :key="p.id"
              class="grid grid-cols-[auto,auto,1fr,120px,110px,80px,80px,90px,70px,160px,130px] border-b border-border/50 text-sm"
              :class="{ 'bg-stone-50/40': idx % 2 === 1 }"
            >
              <div class="p-3 flex items-center justify-center w-11">
                <Checkbox
                  :checked="isSelected(p.id)"
                  @update:checked="toggleSelected(p.id)"
                />
              </div>
              <div class="p-3 w-16 text-muted-foreground text-xs">
                #{{ p.id }}
              </div>
              <div class="p-3 min-w-0">
                <div
                  class="font-medium text-foreground truncate"
                  :title="getLocalizedStr(p.title)"
                >
                  {{ getLocalizedStr(p.title) || '(无标题)' }}
                </div>
                <div class="text-xs text-muted-foreground truncate mt-0.5">
                  /{{ p.slug }}
                </div>
              </div>
              <div class="p-3">
                <template v-if="p.category">
                  <Badge
                    variant="secondary"
                    class="rounded-[10px] font-normal"
                    :style="{
                      background: (p.category?.color ? `${p.category.color}20` : '#f5f5f4'),
                      color: p.category?.color || '#78716c',
                      border: p.category?.color ? `1px solid ${p.category.color}40` : '1px solid #e7e5e4'
                    }"
                  >
                    {{ getLocalizedStr(p.category?.name) }}
                  </Badge>
                </template>
                <span
                  v-else
                  class="text-xs text-muted-foreground"
                >未分类</span>
              </div>
              <div class="p-3">
                <Badge
                  class="rounded-[10px] border font-normal"
                  :class="statusBadgeVariant(p.status)"
                >
                  {{ statusLabel(p.status) }}
                </Badge>
              </div>
              <div class="p-3 text-center text-muted-foreground">
                {{ p.views }}
              </div>
              <div class="p-3 text-center text-muted-foreground">
                {{ p.likes_count }}
              </div>
              <div class="p-3 text-center text-muted-foreground">
                {{ p.comments_count }}
              </div>
              <div class="p-3 text-center">
                <span
                  v-if="p.is_pinned"
                  class="text-amber-500"
                >★</span>
              </div>
              <div class="p-3 text-xs text-muted-foreground">
                {{ formatAdminDateTime(p.published_at ?? p.created_at) }}
              </div>
              <div class="p-3 flex items-center justify-center gap-1.5">
                <Button
                  variant="ghost"
                  size="sm"
                  class="h-8 rounded-[10px] text-xs px-3"
                  @click="router.push(`/admin/content/posts/${p.id}/edit`)"
                >
                  编辑
                </Button>
                <Button
                  variant="ghost"
                  size="sm"
                  class="h-8 rounded-[10px] text-xs px-3 text-destructive hover:text-destructive"
                  @click="confirmDelete(p.id)"
                >
                  删除
                </Button>
              </div>
            </div>
          </template>
        </div>
      </div>

      <div class="flex flex-wrap items-center justify-between gap-3 px-4 py-3 border-t border-border bg-stone-50/50">
        <div class="flex items-center gap-2 text-sm">
          <span class="text-muted-foreground">每页</span>
          <Select
            v-model="pageSize"
            @update:model-value="() => { page.value = 1 }"
          >
            <SelectTrigger class="h-9 w-20 rounded-[10px]">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="10">
                10
              </SelectItem>
              <SelectItem value="20">
                20
              </SelectItem>
              <SelectItem value="50">
                50
              </SelectItem>
            </SelectContent>
          </Select>
          <span class="text-muted-foreground">条，共 {{ total }} 条</span>
        </div>
        <div class="flex items-center gap-1">
          <Button
            variant="outline"
            size="sm"
            class="h-9 rounded-[10px] px-3"
            :disabled="page <= 1"
            @click="goToPage(page - 1)"
          >
            上一页
          </Button>
          <template
            v-for="(pn, i) in pageNumbers"
            :key="i"
          >
            <Button
              v-if="pn !== '...'"
              variant="ghost"
              size="sm"
              class="h-9 w-9 rounded-[10px] p-0"
              :class="{ 'bg-amber-500 text-white hover:bg-amber-500 hover:text-white': pn === page }"
              @click="goToPage(pn as number)"
            >
              {{ pn }}
            </Button>
            <span
              v-else
              class="px-1 text-muted-foreground"
            >...</span>
          </template>
          <Button
            variant="outline"
            size="sm"
            class="h-9 rounded-[10px] px-3"
            :disabled="page >= totalPages"
            @click="goToPage(page + 1)"
          >
            下一页
          </Button>
        </div>
      </div>
    </div>

    <Dialog v-model:open="deleteDialogOpen">
      <DialogContent class="rounded-[12px] max-w-md">
        <DialogHeader>
          <DialogTitle>确认删除文章</DialogTitle>
          <DialogDescription>
            此操作不可撤销，确定要删除这篇文章吗？
          </DialogDescription>
        </DialogHeader>
        <DialogFooter class="mt-4">
          <Button
            variant="outline"
            class="rounded-[10px]"
            @click="deleteDialogOpen = false"
          >
            取消
          </Button>
          <Button
            variant="destructive"
            class="rounded-[10px]"
            @click="doDelete"
          >
            确认删除
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>

    <Dialog v-model:open="batchDeleteDialogOpen">
      <DialogContent class="rounded-[12px] max-w-md">
        <DialogHeader>
          <DialogTitle>确认批量删除</DialogTitle>
          <DialogDescription>
            即将删除 <strong>{{ selectedIds.length }}</strong> 篇文章，此操作不可撤销，确定继续吗？
          </DialogDescription>
        </DialogHeader>
        <DialogFooter class="mt-4">
          <Button
            variant="outline"
            class="rounded-[10px]"
            @click="batchDeleteDialogOpen = false"
          >
            取消
          </Button>
          <Button
            variant="destructive"
            class="rounded-[10px]"
            @click="doBatchDelete"
          >
            确认删除
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  </div>
</template>
