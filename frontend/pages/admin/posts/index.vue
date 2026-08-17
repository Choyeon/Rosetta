<template>
  <div>
    <div class="flex items-start justify-between gap-4">
      <div>
        <h1 class="text-2xl font-bold tracking-tight font-display">
          {{ t('admin.posts.title') }}
        </h1>
        <p class="text-sm text-muted-foreground mt-1">
          {{ t('admin.posts.desc', { total: total }) }}
        </p>
      </div>
      <Button
        :is="'NuxtLink'"
        as="component"
        to="/admin/posts/new"
      >
        <Plus class="mr-2 size-4" />
        {{ t('admin.posts.createNew') }}
      </Button>
    </div>

    <!-- 筛选栏 -->
    <div class="mt-6 flex flex-wrap items-center gap-2">
      <div class="relative w-full sm:w-64">
        <Search class="absolute left-2.5 top-1/2 size-4 -translate-y-1/2 text-muted-foreground" />
        <Input
          v-model="searchInput"
          :placeholder="t('admin.posts.searchPlaceholder')"
          class="h-9 pl-8"
          @keydown.enter.prevent="applySearchNow"
        />
      </div>

      <Select v-model="statusFilter">
        <SelectTrigger class="h-9 w-32">
          <SelectValue />
        </SelectTrigger>
        <SelectContent>
          <SelectItem value="published">
            {{ t('admin.posts.status.published') }}
          </SelectItem>
          <SelectItem value="draft">
            {{ t('admin.posts.status.draft') }}
          </SelectItem>
          <SelectItem value="scheduled">
            {{ t('admin.posts.status.scheduled') }}
          </SelectItem>
        </SelectContent>
      </Select>

      <Select v-model="categoryFilter">
        <SelectTrigger class="h-9 w-40">
          <SelectValue :placeholder="t('admin.posts.allCategories')" />
        </SelectTrigger>
        <SelectContent>
          <SelectItem value="all">
            {{ t('admin.posts.allCategories') }}
          </SelectItem>
          <SelectItem
            v-for="c in categories"
            :key="c.id"
            :value="c.slug"
          >
            {{ c.name }}
          </SelectItem>
        </SelectContent>
      </Select>
    </div>

    <!-- 列表 -->
    <Card class="mt-4 rounded-lg">
      <CardContent class="p-0">
        <!-- 加载骨架 -->
        <div
          v-if="loading"
          class="space-y-3 p-4"
        >
          <div
            v-for="i in 6"
            :key="i"
            class="flex items-center gap-4"
          >
            <Skeleton class="h-5 flex-1" />
            <Skeleton class="h-5 w-16" />
            <Skeleton class="h-5 w-14" />
            <Skeleton class="h-5 w-24" />
          </div>
        </div>

        <!-- 错误 -->
        <div
          v-else-if="loadError"
          class="flex flex-col items-center gap-3 p-10 text-center"
        >
          <CloudOff class="size-8 text-muted-foreground" />
          <p class="text-sm text-muted-foreground">
            {{ t('admin.posts.loadFailed') }}
          </p>
          <Button
            size="sm"
            variant="outline"
            @click="fetchList"
          >
            <RotateCcw class="mr-2 size-4" />
            {{ t('admin.posts.retry') }}
          </Button>
        </div>

        <!-- 空状态 -->
        <div
          v-else-if="posts.length === 0"
          class="flex flex-col items-center gap-3 p-10 text-center"
        >
          <FileText class="size-8 text-muted-foreground" />
          <p class="text-sm text-muted-foreground">
            {{ t('admin.posts.empty') }}
          </p>
          <Button
            :is="'NuxtLink'"
            as="component"
            to="/admin/posts/new"
            size="sm"
          >
            <Plus class="mr-2 size-4" />
            {{ t('admin.posts.createNew') }}
          </Button>
        </div>

        <div
          v-else
          class="overflow-x-auto"
        >
          <table class="w-full text-sm">
            <thead>
              <tr class="border-b">
                <th class="p-3 pl-4 text-left font-medium text-muted-foreground">
                  {{ t('admin.posts.col.title') }}
                </th>
                <th class="p-3 text-left font-medium text-muted-foreground">
                  {{ t('admin.posts.col.category') }}
                </th>
                <th class="p-3 text-left font-medium text-muted-foreground">
                  {{ t('admin.posts.col.status') }}
                </th>
                <th class="p-3 text-left font-medium text-muted-foreground">
                  {{ t('admin.posts.col.views') }}
                </th>
                <th class="p-3 text-left font-medium text-muted-foreground">
                  {{ t('admin.posts.col.comments') }}
                </th>
                <th class="p-3 text-left font-medium text-muted-foreground">
                  {{ t('admin.posts.col.time') }}
                </th>
                <th class="p-3 pr-4 text-right font-medium text-muted-foreground">
                  {{ t('admin.posts.col.actions') }}
                </th>
              </tr>
            </thead>
            <tbody>
              <tr
                v-for="post in posts"
                :key="post.id"
                class="border-b transition-colors last:border-0 hover:bg-muted/50"
              >
                <td class="max-w-[320px] p-3 pl-4">
                  <NuxtLink
                    :to="`/admin/posts/${post.id}/edit`"
                    class="flex items-center gap-1.5 font-medium hover:text-primary"
                  >
                    <Pin
                      v-if="post.is_pinned"
                      class="size-3.5 shrink-0 text-primary"
                    />
                    <span class="truncate">{{ post.title }}</span>
                  </NuxtLink>
                  <p class="truncate text-xs text-muted-foreground">
                    {{ post.slug }}
                  </p>
                </td>
                <td class="p-3">
                  <Badge
                    v-if="post.category"
                    variant="secondary"
                    class="max-w-[120px] truncate"
                  >
                    {{ post.category.name }}
                  </Badge>
                  <span
                    v-else
                    class="text-muted-foreground"
                  >—</span>
                </td>
                <td class="p-3">
                  <Badge :variant="statusVariant(post.status)">
                    {{ statusLabel(post.status) }}
                  </Badge>
                </td>
                <td class="p-3">
                  <span class="flex items-center gap-1 text-muted-foreground">
                    <Eye class="size-3.5" />
                    {{ post.views }}
                  </span>
                </td>
                <td class="p-3">
                  <span class="flex items-center gap-1 text-muted-foreground">
                    <MessageSquare class="size-3.5" />
                    {{ post.comments_count ?? 0 }}
                  </span>
                </td>
                <td class="p-3 whitespace-nowrap text-muted-foreground">
                  {{ formatTime(post.published_at || post.created_at) }}
                </td>
                <td class="p-3 pr-4 text-right">
                  <DropdownMenu>
                    <DropdownMenuTrigger as-child>
                      <Button
                        variant="ghost"
                        size="icon-sm"
                        class="size-8"
                      >
                        <MoreHorizontal class="size-4" />
                      </Button>
                    </DropdownMenuTrigger>
                    <DropdownMenuContent
                      align="end"
                      class="w-40"
                    >
                      <DropdownMenuItem as-child>
                        <NuxtLink
                          :to="`/admin/posts/${post.id}/edit`"
                          class="flex items-center"
                        >
                          <Pencil class="mr-2 size-4" />
                          {{ t('admin.posts.actions.edit') }}
                        </NuxtLink>
                      </DropdownMenuItem>
                      <DropdownMenuItem as-child>
                        <NuxtLink
                          :to="`/posts/${post.slug}`"
                          target="_blank"
                          class="flex items-center"
                        >
                          <Eye class="mr-2 size-4" />
                          {{ t('admin.posts.actions.preview') }}
                        </NuxtLink>
                      </DropdownMenuItem>
                      <DropdownMenuItem
                        :disabled="togglingId === post.id"
                        @click="togglePublish(post)"
                      >
                        <Loader2
                          v-if="togglingId === post.id"
                          class="mr-2 size-4 animate-spin"
                        />
                        <ArrowUpCircle
                          v-else-if="post.status !== 'published'"
                          class="mr-2 size-4"
                        />
                        <ArrowDownCircle
                          v-else
                          class="mr-2 size-4"
                        />
                        {{ post.status === 'published' ? t('admin.posts.actions.unpublish') : t('admin.posts.actions.publish') }}
                      </DropdownMenuItem>
                      <DropdownMenuSeparator />
                      <DropdownMenuItem
                        class="text-destructive focus:text-destructive"
                        @click="openDelete(post)"
                      >
                        <Trash2 class="mr-2 size-4" />
                        {{ t('admin.posts.actions.delete') }}
                      </DropdownMenuItem>
                    </DropdownMenuContent>
                  </DropdownMenu>
                </td>
              </tr>
            </tbody>
          </table>
        </div>

        <!-- 分页 -->
        <div
          v-if="!loading && !loadError && totalPages > 1"
          class="flex items-center justify-between gap-2 border-t p-3"
        >
          <span class="text-xs text-muted-foreground">{{ t('admin.posts.pageOf', { page: page, total: totalPages }) }}</span>
          <Pagination
            :page="page"
            :total="total"
            :items-per-page="pageSize"
            :sibling-count="1"
            :show-edges="totalPages > 7"
            @update:page="changePage"
          >
            <PaginationContent v-slot="{ items }">
              <PaginationPrevious />
              <template
                v-for="(item, index) in items"
                :key="index"
              >
                <PaginationItem
                  v-if="item.type === 'page'"
                  :value="item.value"
                  :is-active="item.value === page"
                >
                  {{ item.value }}
                </PaginationItem>
                <PaginationEllipsis
                  v-else
                  :index="index"
                />
              </template>
              <PaginationNext />
            </PaginationContent>
          </Pagination>
        </div>
      </CardContent>
    </Card>

    <!-- 删除确认 -->
    <Dialog
      :open="!!deleteTarget"
      @update:open="v => { if (!v) deleteTarget = null }"
    >
      <DialogContent class="sm:max-w-md">
        <DialogHeader>
          <DialogTitle>{{ t('admin.posts.deleteTitle') }}</DialogTitle>
          <DialogDescription>
            {{ t('admin.posts.deleteDesc', { title: deleteTarget?.title ?? '' }) }}
          </DialogDescription>
        </DialogHeader>
        <DialogFooter>
          <Button
            variant="outline"
            :disabled="deleting"
            @click="deleteTarget = null"
          >
            {{ t('admin.posts.cancel') }}
          </Button>
          <Button
            variant="destructive"
            :disabled="deleting"
            @click="confirmDelete"
          >
            <Loader2
              v-if="deleting"
              class="mr-2 size-4 animate-spin"
            />
            {{ t('admin.posts.actions.delete') }}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  </div>
</template>

<script setup lang="ts">
import { Card, CardContent } from '~~/components/ui/card'
import { Button } from '~~/components/ui/button'
import { Input } from '~~/components/ui/input'
import { Badge } from '~~/components/ui/badge'
import { Skeleton } from '~~/components/ui/skeleton'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue
} from '~~/components/ui/select'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger
} from '~~/components/ui/dropdown-menu'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle
} from '~~/components/ui/dialog'
import {
  Pagination,
  PaginationContent,
  PaginationEllipsis,
  PaginationItem,
  PaginationNext,
  PaginationPrevious
} from '~~/components/ui/pagination'
import {
  Plus,
  Search,
  Eye,
  MessageSquare,
  MoreHorizontal,
  Pencil,
  Trash2,
  Pin,
  CloudOff,
  FileText,
  RotateCcw,
  ArrowUpCircle,
  ArrowDownCircle,
  Loader2
} from '@lucide/vue'
import { apiFetch } from '~~/composables/useAPI'

definePageMeta({
  layout: 'admin'
})

const { t, locale } = useI18n()
const toast = useToast()

interface PostListItem {
  id: number
  title: string
  slug: string
  status: string
  views: number
  comments_count?: number
  is_pinned?: boolean
  category?: { id: number, name: string, slug: string, color?: string } | null
  published_at?: string | null
  created_at?: string | null
}

interface CategoryOption { id: number, name: string, slug: string }

const posts = ref<PostListItem[]>([])
const categories = ref<CategoryOption[]>([])
const loading = ref(false)
const loadError = ref(false)
const total = ref(0)
const totalPages = ref(0)
const page = ref(1)
const pageSize = 15

const searchInput = ref('')
const appliedSearch = ref('')
const statusFilter = ref('published')
const categoryFilter = ref('all')

const deleteTarget = ref<PostListItem | null>(null)
const deleting = ref(false)
const togglingId = ref<number | null>(null)

let searchTimer: ReturnType<typeof setTimeout> | null = null
watch(searchInput, (v) => {
  if (searchTimer) clearTimeout(searchTimer)
  searchTimer = setTimeout(() => {
    appliedSearch.value = v.trim()
    page.value = 1
  }, 400)
})

function applySearchNow() {
  if (searchTimer) clearTimeout(searchTimer)
  appliedSearch.value = searchInput.value.trim()
  page.value = 1
}

function changePage(p: number) {
  if (p === page.value) return
  page.value = p
  fetchList()
}

async function fetchList() {
  loading.value = true
  loadError.value = false
  try {
    const query: Record<string, unknown> = {
      page: page.value,
      page_size: pageSize,
      lang: locale.value,
      status: statusFilter.value
    }
    if (categoryFilter.value !== 'all') query.category = categoryFilter.value
    if (appliedSearch.value) query.search = appliedSearch.value

    // 管理员视角：带 status 的 /blog/posts 返回对应状态的全部文章（含草稿）
    const res = await apiFetch<{ items?: PostListItem[], total?: number, total_pages?: number } & Record<string, unknown>>(
      '/blog/posts',
      { query }
    )
    posts.value = res?.items ?? []
    total.value = res?.total ?? 0
    totalPages.value = res?.total_pages ?? 0
  } catch (e) {
    console.error('[admin/posts] fetch list failed:', e)
    loadError.value = true
  } finally {
    loading.value = false
  }
}

async function fetchCategories() {
  try {
    const res = await apiFetch<CategoryOption[] | { data?: CategoryOption[] }>('/blog/categories')
    categories.value = Array.isArray(res) ? res : (res?.data ?? [])
  } catch (e) {
    console.error('[admin/posts] fetch categories failed:', e)
  }
}

watch([appliedSearch, statusFilter, categoryFilter], () => {
  page.value = 1
  fetchList()
})

watch(locale, () => {
  fetchList()
})

async function togglePublish(post: PostListItem) {
  if (togglingId.value) return
  togglingId.value = post.id
  const next = post.status === 'published' ? 'draft' : 'published'
  try {
    await apiFetch(`/blog/posts/${post.id}`, { method: 'PUT', body: { status: next } })
    toast.success(next === 'published' ? t('admin.posts.publishedToast') : t('admin.posts.unpublishedToast'))
    await fetchList()
  } catch (e) {
    console.error('[admin/posts] toggle publish failed:', e)
  } finally {
    togglingId.value = null
  }
}

function openDelete(post: PostListItem) {
  deleteTarget.value = post
}

async function confirmDelete() {
  if (!deleteTarget.value) return
  deleting.value = true
  try {
    await apiFetch(`/blog/posts/${deleteTarget.value.id}`, { method: 'DELETE' })
    toast.success(t('admin.posts.deletedToast'))
    deleteTarget.value = null
    // 当前页删空后回退一页
    if (posts.value.length === 1 && page.value > 1) page.value -= 1
    else await fetchList()
  } catch (e) {
    console.error('[admin/posts] delete failed:', e)
  } finally {
    deleting.value = false
  }
}

function statusVariant(status: string): 'default' | 'secondary' | 'outline' {
  switch (status) {
    case 'published': return 'secondary'
    case 'scheduled': return 'default'
    default: return 'outline'
  }
}

function statusLabel(status: string): string {
  switch (status) {
    case 'published': return t('admin.posts.status.published')
    case 'draft': return t('admin.posts.status.draft')
    case 'scheduled': return t('admin.posts.status.scheduled')
    default: return status
  }
}

function formatTime(v?: string | null): string {
  if (!v) return '—'
  const d = new Date(v)
  if (Number.isNaN(d.getTime())) return '—'
  return d.toLocaleDateString()
}

onMounted(() => {
  fetchCategories()
  fetchList()
})
</script>
