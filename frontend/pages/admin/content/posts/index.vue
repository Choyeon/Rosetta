<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import { useRouter } from 'vue-router'
import { usePosts } from '~~/composables/usePosts'
import {
  fetchAdminCategories,
  fetchAdminPostsPaged,
  formatAdminDateTime,
  type AdminCategory,
  type AdminPostListItem
} from '~~/composables/useAdminManage'
import { useToast } from '~~/composables/useToast'
import type { Post } from '~~/types/api'
import { Button } from '~~/components/ui/button'
import { Badge } from '~~/components/ui/badge'
import { RefreshCw, Plus, Pin } from '@lucide/vue'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue
} from '~~/components/ui/select'
import type { AdminColumn as Column } from '~~/types/admin'
import AdminFilterBar from '~~/components/admin/AdminFilterBar.vue'

definePageMeta({ ssr: false, layout: 'admin' })

const router = useRouter()
const { deletePost, batchUpdatePostStatus } = usePosts()
const toast = useToast()

const posts = ref<AdminPostListItem[]>([])
const loading = ref(false)
const total = ref(0)
const page = ref(1)
const pageSize = ref(10)

const searchQuery = ref('')
const statusFilter = ref<'all' | 'published' | 'draft' | 'scheduled' | 'archived'>('all')
const categoryFilter = ref<string>('all')
const createdStart = ref<string | null>(null)
const createdEnd = ref<string | null>(null)

const categories = ref<AdminCategory[]>([])
const selectedIds = ref<number[]>([])
const deleteDialogOpen = ref(false)
const pendingDeleteId = ref<number | null>(null)
const batchDeleteDialogOpen = ref(false)

const statusOptions = [
  { value: 'all' as const, label: '全部状态' },
  { value: 'published' as const, label: '已发布' },
  { value: 'draft' as const, label: '草稿' },
  { value: 'scheduled' as const, label: '定时' },
  { value: 'archived' as const, label: '已归档' }
]

const getLocalizedStr = (v: string | Record<string, string> | null | undefined): string => {
  if (v == null) return ''
  if (typeof v === 'string') return v
  return v.zh || v.en || Object.values(v)[0] || ''
}

const columns: Column[] = [
  { key: 'id', title: 'ID', class: 'w-16 text-muted-foreground text-xs' },
  { key: 'title', title: '标题' },
  { key: 'category', title: '分类', class: 'w-28' },
  { key: 'status', title: '状态', class: 'w-24' },
  { key: 'views', title: '浏览', align: 'center', class: 'w-20' },
  { key: 'likes_count', title: '点赞', align: 'center', class: 'w-20' },
  { key: 'comments_count', title: '评论', align: 'center', class: 'w-20' },
  { key: 'is_pinned', title: '置顶', align: 'center', class: 'w-16' },
  { key: 'published_at', title: '发布时间', class: 'w-44 text-xs text-muted-foreground' }
]

watch([page, pageSize], () => {
  loadPosts()
})

const loadPosts = async () => {
  loading.value = true
  try {
    const result = await fetchAdminPostsPaged<AdminPostListItem>({
      page: page.value,
      page_size: pageSize.value,
      search: searchQuery.value.trim() || undefined,
      status: statusFilter.value !== 'all' ? statusFilter.value : undefined,
      category: categoryFilter.value !== 'all' ? categoryFilter.value : undefined,
      created_start: createdStart.value,
      created_end: createdEnd.value
    })
    posts.value = result.items ?? []
    total.value = result.total ?? 0
  } catch {
    posts.value = []
    total.value = 0
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

const onSearch = () => {
  page.value = 1
  loadPosts()
}

const onReset = () => {
  categoryFilter.value = 'all'
  page.value = 1
  loadPosts()
}

const refresh = () => {
  loadPosts()
}

const isSelected = (id: number) => selectedIds.value.includes(id)
const _toggleSelected = (id: number) => {
  const idx = selectedIds.value.indexOf(id)
  if (idx === -1) selectedIds.value.push(id)
  else selectedIds.value.splice(idx, 1)
}

const isAllSelected = computed(() => {
  return posts.value.length > 0 && posts.value.every(p => isSelected(p.id))
})

const _isSomeSelected = computed(() => {
  return posts.value.some(p => isSelected(p.id)) && !isAllSelected.value
})

const _toggleSelectAll = () => {
  if (isAllSelected.value) {
    selectedIds.value = []
  } else {
    selectedIds.value = [...new Set([...selectedIds.value, ...posts.value.map(p => p.id)])]
  }
}

function confirmDelete(id: number) {
  pendingDeleteId.value = id
  deleteDialogOpen.value = true
}

async function doDelete() {
  if (pendingDeleteId.value == null) return
  const id = pendingDeleteId.value
  try {
    await deletePost(id)
    toast.success('删除成功')
    deleteDialogOpen.value = false
    pendingDeleteId.value = null
    selectedIds.value = selectedIds.value.filter(x => x !== id)
    loadPosts()
  } catch {
    /* apiFetch 已统一 toast */
  }
}

function confirmBatchDelete() {
  batchDeleteDialogOpen.value = true
}

async function doBatchDelete() {
  const ids = [...selectedIds.value]
  let failed = 0
  for (const id of ids) {
    try {
      await deletePost(id)
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
    const data = await batchUpdatePostStatus(ids, status)
    const updatedCount = data?.data?.updated_count ?? 0
    const unavailableCount = ids.length - updatedCount
    if (unavailableCount === 0) toast.success(`已批量修改 ${updatedCount} 篇文章状态`)
    else toast.warning(`成功修改 ${updatedCount} 篇，未授权或不存在 ${unavailableCount} 篇`)
    selectedIds.value = []
    await loadPosts()
  } catch {
    /* apiFetch 已统一 toast */
  }
}

onMounted(() => {
  loadCategories()
  loadPosts()
})
</script>

<template>
  <AdminListPage
    title="文章管理"
    description="管理博客文章，支持搜索、筛选、批量操作。"
    :count="total"
  >
    <template #actions>
      <Button
        class="rounded-[12px] h-11 px-5 shadow-sm gap-2"
        @click="router.push('/admin/content/posts/new')"
      >
        <Plus class="size-4.5" />
        <span>新建文章</span>
      </Button>
    </template>

    <template #toolbar>
      <div class="space-y-3">
        <AdminFilterBar
          v-model:keyword="searchQuery"
          v-model:status="statusFilter"
          v-model:created-start="createdStart"
          v-model:created-end="createdEnd"
          :status-options="statusOptions"
          search-placeholder="搜索标题 / slug / 摘要"
          :loading="loading"
          @search="onSearch"
          @reset="onReset"
        >
          <template #extraFilters>
            <Select v-model="categoryFilter">
              <SelectTrigger class="h-9 w-[160px] rounded-[10px]">
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
              size="sm"
              class="h-9 rounded-[10px]"
              @click="refresh"
            >
              <RefreshCw class="size-4 mr-1.5" />
              刷新
            </Button>
          </template>
        </AdminFilterBar>
      </div>
    </template>

    <div
      v-if="selectedIds.length > 0"
      class="flex items-center justify-between rounded-[12px] border border-primary/30 bg-primary/5 px-5 py-3"
    >
      <span class="text-sm text-primary/90">
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

    <AdminDataTable
      :columns="columns"
      :data="posts"
      :loading="loading"
      row-key="id"
      selectable
      :selected-ids="selectedIds"
      @update:selected-ids="(ids) => selectedIds = ids as number[]"
    >
      <template #cell-id="{ row }">
        #{{ (row as Post).id }}
      </template>
      <template #cell-title="{ row }">
        <div class="min-w-0">
          <div
            class="font-medium text-foreground truncate"
            :title="getLocalizedStr((row as Post).title)"
          >
            {{ getLocalizedStr((row as Post).title) || '(无标题)' }}
          </div>
          <div class="text-xs text-muted-foreground truncate mt-0.5">
            /{{ (row as Post).slug }}
          </div>
        </div>
      </template>
      <template #cell-category="{ row }">
        <template v-if="(row as Post).category">
          <Badge
            variant="secondary"
            class="rounded-[10px] font-normal"
            :style="{
              background: ((row as Post).category?.color ? `${(row as Post).category!.color}20` : '#f5f5f4'),
              color: (row as Post).category?.color || '#78716c',
              border: (row as Post).category?.color ? `1px solid ${(row as Post).category!.color}40` : '1px solid #e7e5e4'
            }"
          >
            {{ getLocalizedStr((row as Post).category?.name) }}
          </Badge>
        </template>
        <span
          v-else
          class="text-xs text-muted-foreground"
        >未分类</span>
      </template>
      <template #cell-status="{ row }">
        <Badge
          class="rounded-[10px] border font-normal"
          :class="{
            'bg-emerald-100 text-emerald-700 border-emerald-200': (row as Post).status === 'published',
            'bg-amber-100 text-amber-700 border-amber-200': (row as Post).status === 'draft',
            'bg-indigo-100 text-indigo-700 border-indigo-200': (row as Post).status === 'scheduled',
            'bg-slate-100 text-slate-600 border-slate-200': (row as Post).status === 'archived'
          }"
        >
          {{ { published: '已发布', draft: '草稿', scheduled: '定时', archived: '已归档' }[(row as Post).status] ?? (row as Post).status }}
        </Badge>
      </template>
      <template #cell-is_pinned="{ row }">
        <Pin
          v-if="(row as Post).is_pinned"
          class="size-3.5 text-amber-500"
        />
      </template>
      <template #cell-published_at="{ row }">
        {{ formatAdminDateTime((row as Post).published_at ?? (row as Post).created_at) }}
      </template>
      <template #actions="{ row }">
        <Button
          variant="ghost"
          size="sm"
          class="h-8 rounded-[10px] text-xs px-3"
          @click="router.push(`/admin/content/posts/${(row as Post).id}/edit`)"
        >
          编辑
        </Button>
        <Button
          variant="ghost"
          size="sm"
          class="h-8 rounded-[10px] text-xs px-3 text-destructive hover:text-destructive"
          @click="confirmDelete((row as Post).id)"
        >
          删除
        </Button>
      </template>
    </AdminDataTable>

    <template #pagination>
      <AdminPagination
        v-model:page="page"
        v-model:page-size="pageSize"
        :total="total"
      />
    </template>

    <AdminConfirmDialog
      v-model:open="deleteDialogOpen"
      title="确认删除文章"
      description="此操作不可撤销，确定要删除这篇文章吗？"
      confirm-text="确认删除"
      @confirm="doDelete"
    />

    <AdminConfirmDialog
      v-model:open="batchDeleteDialogOpen"
      title="确认批量删除"
      :description="`即将删除 ${selectedIds.length} 篇文章，此操作不可撤销，确定继续吗？`"
      confirm-text="确认删除"
      @confirm="doBatchDelete"
    />
  </AdminListPage>
</template>
