<!--
  文章管理列表页：服务端分页 + 关键字/状态/分类/日期筛选 + 批量发布/转草稿/置顶/删除。
  硬契约（都是踩过的坑，改前先读）：
  1. AdminDataTable 的选择是受控的——翻页、换筛选、删除、批量成功后必须由本页清空
     selectedIds，表格不会自动清。**翻页残留是最危险的一种**：第 1 页勾三篇、翻到第 2 页
     再点「批量删除」，删掉的是看不见的那三篇。
  2. 重载一律走 scheduleLoad()：**任何**"先置 page=1 再手动 loadPosts()"的写法都会发出
     两条相同请求（page 的 watch 是 pre-flush，下一轮微任务里还会再触发一次），
     慢的那个回来得晚就会覆盖快的结果。
  3. 两个批量接口信封不同：/blog/posts/batch-status 的 updated_count 在 {success,data} 双层里，
     /admin/posts/batch（删除与置顶走它，一次请求而非逐条 N 次往返）的 affected_count 是平铺的；
  4. 列表用 shallowRef 整替换，禁止改回 deep ref（大量 Post 对象的递归 Proxy 是白给的性能损耗）。
-->
<script setup lang="ts">
import { ref, shallowRef, onMounted, watch } from 'vue'
import { useRouter } from 'vue-router'
import { usePosts } from '~~/composables/usePosts'
import {
  fetchAdminCategories,
  fetchAdminPostsPaged,
  formatAdminDateTime,
  batchAdminPosts,
  type AdminCategory,
  type AdminPostListItem
} from '~~/composables/useAdminManage'
import { useToast } from '~~/composables/useToast'
import type { Post } from '~~/types/api'
import { Button } from '~~/components/ui/button'
import { Badge } from '~~/components/ui/badge'
import { Alert, AlertTitle, AlertDescription } from '~~/components/ui/alert'
import { RefreshCw, Plus, Pin, X } from '@lucide/vue'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue
} from '~~/components/ui/select'
import type { AdminColumn as Column } from '~~/types/admin'
import AdminFilterBar from '~~/components/admin/AdminFilterBar.vue'
import { getLocalizedStr } from '~~/composables/useAdminI18n'

definePageMeta({ ssr: false, layout: 'admin' })

const router = useRouter()
const { deletePost, batchUpdatePostStatus } = usePosts()
const toast = useToast()

// shallowRef：列表整赋值替换，避免 Vue 对 10+ 条 Post 对象深层 reactive 递归 Proxy
const posts = shallowRef<AdminPostListItem[]>([])
const loading = ref(false)
const total = ref(0)
const page = ref(1)
const pageSize = ref(10)

const searchQuery = ref('')
const statusFilter = ref<'all' | 'published' | 'draft' | 'scheduled'>('all')
const categoryFilter = ref<string>('all')
const createdStart = ref<string | null>(null)
const createdEnd = ref<string | null>(null)

const categories = shallowRef<AdminCategory[]>([])
const selectedIds = ref<number[]>([])
const deleteDialogOpen = ref(false)
const pendingDeleteId = ref<number | null>(null)
const batchDeleteDialogOpen = ref(false)
const batching = ref(false)
const loadError = ref<string | null>(null)

const statusOptions = [
  { value: 'all' as const, label: '全部状态' },
  { value: 'published' as const, label: '已发布' },
  { value: 'draft' as const, label: '草稿' },
  { value: 'scheduled' as const, label: '定时' }
]

const columns: Column[] = [
  { key: 'id', title: 'ID', class: 'w-16 text-muted-foreground text-xs' },
  { key: 'title', title: '标题' },
  { key: 'category', title: '分类', class: 'w-28' },
  { key: 'status', title: '状态', class: 'w-24' },
  { key: 'views', title: '浏览', align: 'center', class: 'w-20' },
  { key: 'likes_count', title: '点赞', align: 'center', class: 'w-20' },
  { key: 'comments_count', title: '评论', align: 'center', class: 'w-20' },
  { key: 'is_pinned', title: '置顶', align: 'center', class: 'w-16' },
  { key: 'published_at', title: '发布时间', class: 'w-44 text-xs text-muted-foreground' },
  { key: 'updated_at', title: '最后更新', class: 'w-44 text-xs text-muted-foreground' }
]

// 同一轮里可能有多个来源同时要求重载（筛选按钮 + page watch + 多个筛选 watch），
// 用宏任务合并成一次请求：setTimeout(0) 保证同步赋值与 pre-flush 的 watcher 都先跑完。
let loadTimer: ReturnType<typeof setTimeout> | null = null
function scheduleLoad() {
  if (loadTimer) clearTimeout(loadTimer)
  loadTimer = setTimeout(() => {
    loadTimer = null
    loadPosts()
  }, 0)
}

// 条件变化：清选择 + 回到第 1 页。不能既置 page=1 又直接调 loadPosts（见文件头契约 2）
function reload() {
  selectedIds.value = []
  if (page.value !== 1) page.value = 1
  scheduleLoad()
}

watch([page, pageSize], () => {
  scheduleLoad()
})

// 状态与日期跟分类保持一致：都是下拉/选值，选完就该生效，不该再要求点一次「搜索」。
// 关键字仍走按钮（用它防抖：每敲一个字打一次请求没必要）。
watch([statusFilter, createdStart, createdEnd], () => {
  reload()
})

const loadPosts = async () => {
  loading.value = true
  loadError.value = null
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
    // 删除/筛选后当前页可能越界：夹回最后一页（page 变化由 watch 触发重载）
    const maxPage = Math.max(1, Math.ceil(total.value / pageSize.value))
    if (posts.value.length === 0 && total.value > 0 && page.value > maxPage) {
      page.value = maxPage
      return
    }
  } catch (e) {
    posts.value = []
    total.value = 0
    // 不能静默：失败时表格是空的，而"筛选后没有结果"长得一模一样，
    // 管理员无法区分是查不到还是请求挂了。
    loadError.value = e instanceof Error ? e.message : '加载失败，请稍后重试'
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
  reload()
}

// 分类下拉在 FilterBar 插槽内，无法复用其搜索按钮语义：选中后立即刷新
watch(categoryFilter, () => {
  reload()
})

const onReset = () => {
  categoryFilter.value = 'all'
  reload()
}

const refresh = () => {
  scheduleLoad()
}

const clearSelection = () => {
  selectedIds.value = []
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
  } catch {
    // apiFetch 已统一 toast；对话框保持打开供重试（AdminConfirmDialog 的契约）
    return
  }
  toast.success('已移入回收站')
  pendingDeleteId.value = null
  selectedIds.value = selectedIds.value.filter(x => x !== id)
  scheduleLoad()
}

function confirmBatchDelete() {
  batchDeleteDialogOpen.value = true
}

async function doBatchDelete() {
  const ids = [...selectedIds.value]
  if (ids.length === 0) return
  batching.value = true
  try {
    // 一次请求替代逐条 DELETE：服务端在同一事务里入回收站并单层清缓存，
    // 部分失败不会留下"删了一半"的中间态。
    const resp = await batchAdminPosts('delete', ids)
    toast.success(`已删除 ${resp.affected_count ?? ids.length} 篇文章，回收站 30 天内可恢复`)
    selectedIds.value = []
    scheduleLoad()
  } catch {
    /* apiFetch 已统一 toast */
  } finally {
    batching.value = false
  }
}

const batchChangeStatus = async (status: 'published' | 'draft' | 'scheduled') => {
  const ids = [...selectedIds.value]
  batching.value = true
  try {
    const data = await batchUpdatePostStatus(ids, status)
    const updatedCount = data?.data?.updated_count ?? 0
    const unavailableCount = ids.length - updatedCount
    if (unavailableCount === 0) toast.success(`已批量修改 ${updatedCount} 篇文章状态`)
    else toast.warning(`成功修改 ${updatedCount} 篇，未授权或不存在 ${unavailableCount} 篇`)
    selectedIds.value = []
    scheduleLoad()
  } catch {
    /* apiFetch 已统一 toast */
  } finally {
    batching.value = false
  }
}

const batchPin = async (action: 'pin' | 'unpin') => {
  const ids = [...selectedIds.value]
  batching.value = true
  try {
    const resp = await batchAdminPosts(action, ids)
    const affected = resp.affected_count ?? 0
    if (affected === 0) toast.warning('所选文章已处于目标置顶状态，未做变更')
    else toast.success(`${action === 'pin' ? '已置顶' : '已取消置顶'} ${affected} 篇文章`)
    selectedIds.value = []
    scheduleLoad()
  } catch {
    /* apiFetch 已统一 toast */
  } finally {
    batching.value = false
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
        <Plus data-icon="inline-start" />
        <span>新建文章</span>
      </Button>
    </template>

    <template #toolbar>
      <div class="flex flex-col gap-3">
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
                <!-- 后端 list_posts 的 category 参数是 slug（`Category.slug == category`），
                     传 id 永远匹配不上，表现为"选了分类却一条都没有" -->
                <SelectItem
                  v-for="c in categories"
                  :key="c.id"
                  :value="c.slug"
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
              <RefreshCw data-icon="inline-start" />
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
        <span class="text-xs opacity-70 ml-1">（仅当前页）</span>
      </span>
      <div class="flex items-center gap-2 flex-wrap justify-end">
        <Button
          variant="ghost"
          size="sm"
          class="rounded-[10px] h-9 text-xs"
          :disabled="batching"
          @click="clearSelection"
        >
          <X data-icon="inline-start" />
          取消选择
        </Button>
        <Button
          variant="outline"
          size="sm"
          class="rounded-[10px] h-9"
          :disabled="batching"
          @click="batchChangeStatus('published')"
        >
          批量发布
        </Button>
        <Button
          variant="outline"
          size="sm"
          class="rounded-[10px] h-9"
          :disabled="batching"
          @click="batchChangeStatus('draft')"
        >
          批量转草稿
        </Button>
        <Button
          variant="outline"
          size="sm"
          class="rounded-[10px] h-9"
          :disabled="batching"
          @click="batchPin('pin')"
        >
          <Pin data-icon="inline-start" />
          批量置顶
        </Button>
        <Button
          variant="outline"
          size="sm"
          class="rounded-[10px] h-9"
          :disabled="batching"
          @click="batchPin('unpin')"
        >
          取消置顶
        </Button>
        <Button
          variant="destructive"
          size="sm"
          class="rounded-[10px] h-9"
          :disabled="batching"
          @click="confirmBatchDelete"
        >
          批量删除
        </Button>
      </div>
    </div>

    <Alert
      v-if="loadError"
      variant="destructive"
      class="rounded-[12px]"
    >
      <AlertTitle class="font-semibold">
        加载失败
      </AlertTitle>
      <AlertDescription class="mt-2 flex items-center gap-3">
        <span>{{ loadError }}</span>
        <Button
          variant="outline"
          size="sm"
          class="rounded-[10px]"
          @click="refresh"
        >
          <RefreshCw data-icon="inline-start" />
          重试
        </Button>
      </AlertDescription>
    </Alert>

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
          class="rounded-[10px] font-normal"
          :class="{
            'bg-success-muted text-success-muted-foreground': (row as Post).status === 'published',
            'bg-warning-muted text-warning-muted-foreground': (row as Post).status === 'draft',
            'bg-info-muted text-info-muted-foreground': (row as Post).status === 'scheduled',
            'bg-muted text-muted-foreground': (row as Post).status === 'archived'
          }"
        >
          {{ { published: '已发布', draft: '草稿', scheduled: '定时', archived: '已归档' }[(row as Post).status] ?? (row as Post).status }}
        </Badge>
      </template>
      <template #cell-is_pinned="{ row }">
        <Pin
          v-if="(row as Post).is_pinned"
          class="size-3.5 text-warning"
        />
      </template>
      <template #cell-published_at="{ row }">
        {{ formatAdminDateTime((row as Post).published_at ?? (row as Post).created_at) }}
      </template>
      <template #cell-updated_at="{ row }">
        {{ formatAdminDateTime((row as AdminPostListItem).updated_at) }}
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
          class="h-8 rounded-[10px] text-xs px-3"
          @click="router.push(`/admin/content/posts/${(row as Post).id}/revisions`)"
        >
          版本
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
      description="删除后将移入回收站，保留 30 天可恢复。确定要删除这篇文章吗？"
      confirm-text="确认删除"
      :on-confirm="doDelete"
    />

    <AdminConfirmDialog
      v-model:open="batchDeleteDialogOpen"
      title="确认批量删除"
      :description="`即将删除 ${selectedIds.length} 篇文章，移入回收站后 30 天内可恢复。`"
      confirm-text="确认删除"
      :on-confirm="doBatchDelete"
    />
  </AdminListPage>
</template>
