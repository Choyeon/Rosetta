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
import { fetchAdminContentTypes, type AdminContentType } from '~~/composables/useContentTypes'
import type { Post } from '~~/types/api'
import { Button } from '~~/components/ui/button'
import { Badge } from '~~/components/ui/badge'
import { Alert, AlertTitle, AlertDescription } from '~~/components/ui/alert'
import { RefreshCw, Plus, Pin, X, Pencil, History, Trash2 } from '@lucide/vue'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue
} from '~~/components/ui/select'
import type { AdminColumn as Column } from '~~/types/admin'
import AdminFilterBar from '~~/components/admin/AdminFilterBar.vue'
import AdminRowActions from '~~/components/admin/AdminRowActions.vue'
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
const typeFilter = ref<string>('all')
const createdStart = ref<string | null>(null)
const createdEnd = ref<string | null>(null)

const categories = shallowRef<AdminCategory[]>([])
const contentTypes = shallowRef<AdminContentType[]>([])
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
  // ID 与点赞从独立列下移：ID 并入标题行（#21 · /slug），点赞在列表里没有操作入口，
  // 两者占掉的 120px 正好是「操作」列被挤出视口的原因。列宽改为固定值 + table-fixed，
  // 日期与状态才不会被 auto 布局压成三行。
  { key: 'title', title: '标题' },
  { key: 'category', title: '分类', class: 'w-20' },
  { key: 'status', title: '状态', class: 'w-20' },
  { key: 'views', title: '浏览', align: 'center', class: 'w-16' },
  { key: 'comments_count', title: '评论', align: 'center', class: 'w-16' },
  { key: 'is_pinned', title: '置顶', align: 'center', class: 'w-12' },
  { key: 'published_at', title: '发布时间', class: 'w-32 text-xs text-muted-foreground' },
  { key: 'updated_at', title: '最后更新', class: 'w-32 text-xs text-muted-foreground' }
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
      post_type: typeFilter.value !== 'all' ? typeFilter.value : undefined,
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

// 内容类型定义同时喂两处：筛选下拉的选项，和行上那个"这条是什么类型"的徽标名。
// 取不到就当没有自定义类型（下拉整块不显示），标准文章的徽标本来也不显示。
const loadContentTypes = async () => {
  try {
    contentTypes.value = await fetchAdminContentTypes()
  } catch {
    contentTypes.value = []
  }
}

/** 行内类型徽标的文案：自定义类型用定义里的显示名，内置 post 不显示徽标。 */
const typeName = (key?: string | null): string => {
  if (!key || key === 'post') return ''
  return contentTypes.value.find(t => t.key === key)?.name ?? key
}

const onSearch = () => {
  reload()
}

// 分类/类型下拉在 FilterBar 插槽内，无法复用其搜索按钮语义：选中后立即刷新
watch([categoryFilter, typeFilter], () => {
  reload()
})

const onReset = () => {
  categoryFilter.value = 'all'
  typeFilter.value = 'all'
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
  loadContentTypes()
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
        size="sm"
        class="shadow-sm"
        @click="router.push('/admin/content/posts/new')"
      >
        <Plus data-icon="inline-start" />
        新建文章
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
            <!-- 列表默认口径是「不传 post_type = 全部类型」，自定义类型因此会和标准文章混在一起；
                 这一列下拉给的就是"只看某一种"。没有定义时整块不显示（选项永远只有两项＝白占位置）。 -->
            <Select
              v-if="contentTypes.length > 0"
              v-model="typeFilter"
            >
              <SelectTrigger class="h-9 w-[160px] rounded-[10px]">
                <SelectValue placeholder="内容类型" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">
                  全部类型
                </SelectItem>
                <SelectItem value="post">
                  标准文章
                </SelectItem>
                <SelectItem
                  v-for="ct in contentTypes"
                  :key="ct.key"
                  :value="ct.key"
                >
                  {{ ct.name }}
                </SelectItem>
              </SelectContent>
            </Select>
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
      class="flex flex-col gap-3 rounded-[12px] border border-primary/30 bg-primary/5 px-5 py-3 sm:flex-row sm:items-center sm:justify-between"
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
      table-class="table-fixed"
      :selected-ids="selectedIds"
      @update:selected-ids="(ids) => selectedIds = ids as number[]"
    >
      <template #cell-title="{ row }">
        <div class="min-w-0">
          <div
            class="font-medium text-foreground truncate"
            :title="getLocalizedStr((row as Post).title)"
          >
            {{ getLocalizedStr((row as Post).title) || '(无标题)' }}
          </div>
          <div class="text-xs text-muted-foreground truncate mt-0.5">
            <span class="tabular-nums text-muted-foreground/70">#{{ (row as Post).id }}</span>
            <span class="mx-1 text-muted-foreground/40">·</span>
            <span>/{{ (row as Post).slug }}</span>
            <!-- 自定义类型才挂徽标（内置 post 是多数，逐个显示等于噪音）：
                 列表已按"全部类型"混排，没有这一位就看不出某行为什么带着扩展字段。 -->
            <span
              v-if="typeName((row as Post).post_type)"
              class="ml-2 rounded-[8px] bg-info-muted px-1.5 py-0.5 text-info-muted-foreground"
            >{{ typeName((row as Post).post_type) }}</span>
          </div>
        </div>
      </template>
      <template #cell-category="{ row }">
        <template v-if="(row as Post).category">
          <Badge
            variant="secondary"
            class="rounded-[10px] font-normal whitespace-nowrap"
            :style="{
              background: ((row as Post).category?.color ? `${(row as Post).category!.color}20` : 'hsl(var(--muted))'),
              color: (row as Post).category?.color || 'hsl(var(--muted-foreground))',
              border: (row as Post).category?.color ? `1px solid ${(row as Post).category!.color}40` : '1px solid hsl(var(--border))'
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
        <div class="flex flex-col items-start gap-1">
          <Badge
            class="rounded-[10px] font-normal whitespace-nowrap"
            :class="{
              'bg-success-muted text-success-muted-foreground': (row as Post).status === 'published',
              'bg-warning-muted text-warning-muted-foreground': (row as Post).status === 'draft',
              'bg-info-muted text-info-muted-foreground': (row as Post).status === 'scheduled',
              'bg-muted text-muted-foreground': (row as Post).status === 'archived'
            }"
          >
            {{ { published: '已发布', draft: '草稿', scheduled: '定时', archived: '已归档' }[(row as Post).status] ?? (row as Post).status }}
          </Badge>
          <!-- 状态与可见性是两条正交的轴：「已发布 + 私密」是合法组合（作者自己留着看的成文），
               合成一个徽标就看不出这层。公开读口已把私密文章整条滤掉，后台必须有标记位，
               否则管理员只有逐篇打开编辑器才知道哪篇没对外发布。 -->
          <Badge
            v-if="(row as Post).visibility === 'private'"
            variant="secondary"
            class="rounded-[10px] font-normal whitespace-nowrap bg-warning-muted text-warning-muted-foreground"
            title="私密：不进列表、RSS、sitemap、搜索与热榜，只有作者与管理员能打开"
          >
            私密
          </Badge>
          <Badge
            v-else-if="(row as Post).visibility === 'password'"
            variant="secondary"
            class="rounded-[10px] font-normal whitespace-nowrap bg-info-muted text-info-muted-foreground"
            title="密码保护：列表与订阅源能看到摘要，正文需要访问密码"
          >
            密码
          </Badge>
        </div>
      </template>
      <template #cell-is_pinned="{ row }">
        <Pin
          v-if="(row as Post).is_pinned"
          class="size-3.5 text-warning"
          aria-label="已置顶"
        />
        <span
          v-else
          class="text-muted-foreground/40"
          aria-hidden="true"
        >—</span>
      </template>
      <template #cell-published_at="{ row }">
        <span
          class="whitespace-nowrap tabular-nums"
          :title="formatAdminDateTime((row as Post).published_at ?? (row as Post).created_at)"
        >{{ formatAdminDateTime((row as Post).published_at ?? (row as Post).created_at) }}</span>
      </template>
      <template #cell-updated_at="{ row }">
        <span
          class="whitespace-nowrap tabular-nums"
          :title="formatAdminDateTime((row as AdminPostListItem).updated_at)"
        >{{ formatAdminDateTime((row as AdminPostListItem).updated_at) }}</span>
      </template>
      <template #actions="{ row }">
        <AdminRowActions
          :actions="[
            { key: 'edit', label: '编辑文章', icon: Pencil, onClick: () => router.push(`/admin/content/posts/${(row as Post).id}/edit`) },
            { key: 'revisions', label: '版本历史', icon: History, onClick: () => router.push(`/admin/content/posts/${(row as Post).id}/revisions`) },
            { key: 'delete', label: '删除文章', icon: Trash2, destructive: true, onClick: () => confirmDelete((row as Post).id) }
          ]"
        />
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
