<!--
  个人中心 /account（SPA + no-store）：把后端自上线起一直"就绪、前端零消费"的
  /blog/users/me/* 与 /favorites* 端点接成 WordPress「我的账户」同款落地页 ——
  stats（文章/评论/获赞读数）、posts（我的文章，含草稿）、comments（我的评论）、
  likes（我的点赞，可取消）、favorites（我的收藏：收藏夹筛选、移动、备注、取消）、
  history（阅读历史，可清空）。
  四条硬约束：
  1. ssr:false 写在 routeRules（不在页面里重复声明）：本页内容逐登录用户不同，而 auth store
     是 skipHydrate + localStorage，SSR 期根本没有 token；若走 SSR，未登录的 401 骨架会被渲染
     成"公共页面"，缓存头也就不能是公开 s-maxage。故与 /admin 同档：ssr:false + no-store, private。
  2. 登录闸门在命名中间件 auth-required（不进全局链），未登录带 ?redirect= 跳 /login；
     页面 setup 只管渲染，不做第二套状态判定（AGENTS.md §2.3.2 同源理由）。
  3. 一次只发「统计 + 当前 tab + 收藏夹名册」三个请求：tab、page 与收藏档位用的都是响应式
     url/key，切 tab 不会把另外几档全量拉一遍；名册只有三条消费点（筛选条、移动菜单、管理弹窗），
     一次拉全量比按档位重复拉更省。
  4. 日期格式化钉死 locale + timeZone：本仓两端时区不一致过，归档侧已按同口径修过一轮。
-->
<template>
  <div class="container py-16 max-w-3xl mx-auto">
    <!-- 用户封面：与作者主页同一份数据（User.cover_image），只在设过封面时占位；
         头像与名字已在下方 header 里，这里按装饰图处理（alt 留空），不做第二处可读文本。 -->
    <div
      v-if="coverImage"
      class="mb-6 overflow-hidden rounded-xl border"
    >
      <img
        :src="coverImage"
        alt=""
        class="h-32 w-full object-cover"
      >
    </div>
    <header class="mb-10 flex flex-wrap items-center justify-between gap-x-6 gap-y-4">
      <div class="flex items-center gap-4 min-w-0">
        <UserAvatar
          :resolved-avatar-url="resolvedAvatarUrl"
          :avatar="rawAvatar"
          :seed="accountSeed"
          :name="displayName"
          :size="56"
        />
        <div class="min-w-0">
          <h1 class="font-display text-2xl md:text-3xl font-bold tracking-tight truncate">
            {{ t('account.title') }}
          </h1>
          <p class="mt-1 text-sm text-muted-foreground truncate">
            {{ displayName }}
          </p>
        </div>
      </div>
      <p class="text-xs uppercase tracking-wider text-muted-foreground">
        {{ t('account.desc') }}
      </p>
      <!-- 账户设置（资料/隐私/改密）入口放在本页而非顶栏下拉：/account 本身就只有登录态可达，
           再往用户菜单里塞第三项只是把同一批链接摊成两处维护。 -->
      <Button
        variant="outline"
        size="sm"
        @click="navigateTo('/account/settings')"
      >
        <Settings data-icon="inline-start" />
        {{ t('account.settingsTitle') }}
      </Button>
    </header>

    <!-- ===== 读数卡：GET /users/me/stats（后端信封 {success,data,message}，与列表端点不同构） ===== -->
    <div class="mb-10 grid grid-cols-3 gap-3">
      <div
        v-for="metric in metrics"
        :key="metric.key"
        class="card-surface rounded-xl px-4 py-3"
      >
        <div class="flex items-center gap-2 text-xs text-muted-foreground">
          <component
            :is="metric.icon"
            class="size-3.5"
          />
          {{ metric.label }}
        </div>
        <div class="mt-1 font-display text-2xl font-bold tabular-nums">
          {{ metric.value }}
        </div>
      </div>
    </div>

    <Tabs
      :model-value="tab"
      class="w-full"
      @update:model-value="onTabChange"
    >
      <TabsList class="grid w-full grid-cols-2 sm:grid-cols-5 mb-8">
        <TabsTrigger
          v-for="item in tabItems"
          :key="item.value"
          :value="item.value"
          class="data-[state=active]:shadow-none"
        >
          <component
            :is="item.icon"
            class="size-4"
          />
          {{ item.label }}
        </TabsTrigger>
      </TabsList>

      <TabsContent
        v-for="item in tabItems"
        :key="item.value"
        :value="item.value"
      >
        <!-- 阅读历史额外一条工具栏：清空（唯一写路径，二次确认后才发 DELETE） -->
        <div
          v-if="item.value === 'history' && historyRows.length > 0"
          class="mb-4 flex items-center justify-between gap-3"
        >
          <span class="text-sm text-muted-foreground tabular-nums">
            {{ t('account.statsTotal', { count: total }) }}
          </span>
          <Button
            variant="outline"
            size="sm"
            @click="clearDialogOpen = true"
          >
            <Trash2 data-icon="inline-start" />
            {{ t('account.clearHistory') }}
          </Button>
        </div>

        <!-- ===== 加载骨架 ===== -->
        <div
          v-if="pending"
          class="flex flex-col gap-3"
        >
          <Separator />
          <div
            v-for="r in 5"
            :key="r"
            class="py-2"
          >
            <Skeleton class="h-5 w-4/5 rounded-md" />
          </div>
        </div>

        <!-- ===== 请求失败（401 已由 useAPI 跳登录，这里只露其余状态） ===== -->
        <div
          v-else-if="listError"
          class="py-16 text-center"
          role="alert"
        >
          <h2 class="font-display text-lg font-semibold">
            {{ t('account.loadFailed') }}
          </h2>
          <Button
            class="mt-4"
            variant="outline"
            size="sm"
            @click="reload"
          >
            <RotateCcw data-icon="inline-start" />
            {{ t('account.retry') }}
          </Button>
        </div>

        <!-- ===== 空档（正常路径：新用户四条列表都可能是空） ===== -->
        <div
          v-else-if="rows.length === 0"
          class="py-16 text-center"
        >
          <div class="mb-4 inline-flex size-16 items-center justify-center rounded-2xl bg-muted">
            <component
              :is="item.icon"
              class="size-8 text-muted-foreground"
            />
          </div>
          <h2 class="font-display text-xl font-semibold">
            {{ emptyLabel(item.value) }}
          </h2>
        </div>

        <!-- ===== 我的文章 / 我的点赞：同构（都是文章行） ===== -->
        <div v-else-if="item.value === 'posts' || item.value === 'likes'">
          <Separator />
          <ul class="flex flex-col gap-3">
            <li
              v-for="post in postRows"
              :key="String(post.id)"
              class="flex flex-wrap items-baseline justify-between gap-x-4 gap-y-1 py-2"
            >
              <NuxtLink
                :to="`/posts/${post.slug}`"
                class="text-base transition-colors hover:text-primary"
              >
                {{ post.title }}
              </NuxtLink>
              <span class="flex items-center gap-3 text-sm text-muted-foreground tabular-nums">
                <span>{{ formatDate(post.published_at || post.created_at) }}</span>
                <Badge
                  v-if="item.value === 'posts'"
                  :variant="post.status === 'published' ? 'secondary' : 'outline'"
                  :class="post.status === 'published' ? 'bg-success-muted text-success-muted-foreground' : 'bg-warning-muted text-warning-muted-foreground'"
                >
                  {{ statusLabel(post.status) }}
                </Badge>
                <span
                  v-if="item.value === 'likes'"
                  class="inline-flex items-center gap-1"
                >
                  <Heart class="size-3.5" />
                  {{ post.likes_count ?? 0 }}
                </span>
                <span class="inline-flex items-center gap-1">
                  <Eye class="size-3.5" />
                  {{ post.views ?? 0 }}
                </span>
                <Button
                  v-if="item.value === 'likes'"
                  variant="ghost"
                  size="sm"
                  :disabled="pendingLikeId !== null"
                  @click="unlike(post)"
                >
                  {{ t('account.unlike') }}
                </Button>
              </span>
            </li>
          </ul>
        </div>

        <!-- ===== 我的评论 ===== -->
        <div v-else-if="item.value === 'comments'">
          <Separator />
          <ul class="flex flex-col gap-4">
            <li
              v-for="comment in commentRows"
              :key="String(comment.id)"
              class="py-2"
            >
              <div class="flex flex-wrap items-center justify-between gap-x-3 gap-y-1">
                <NuxtLink
                  v-if="comment.post_slug"
                  :to="`/posts/${comment.post_slug}`"
                  class="text-sm font-medium transition-colors hover:text-primary"
                >
                  {{ comment.post_title || t('account.deletedPost') }}
                </NuxtLink>
                <span
                  v-else
                  class="text-sm text-muted-foreground"
                >{{ t('account.deletedPost') }}</span>
                <span class="flex items-center gap-3 text-xs text-muted-foreground tabular-nums">
                  <span>{{ formatDate(comment.created_at) }}</span>
                  <Badge
                    :variant="comment.active ? 'secondary' : 'outline'"
                    :class="comment.active ? 'bg-success-muted text-success-muted-foreground' : 'bg-warning-muted text-warning-muted-foreground'"
                  >
                    {{ comment.active ? t('account.commentApproved') : t('account.commentPending') }}
                  </Badge>
                </span>
              </div>
              <p class="mt-1.5 text-sm text-muted-foreground leading-relaxed">
                {{ comment.content }}
              </p>
            </li>
          </ul>
        </div>

        <!-- ===== 我的收藏：后端 /api/favorites 全家（列表/取消/收藏夹/备注）的落地面 ===== -->
        <div v-else-if="item.value === 'favorites'">
          <!-- 收藏夹筛选条：全部 + 每个收藏夹（带篇数）。folder 写进 query，与 tab/page 同机制。 -->
          <div class="mb-4 flex flex-wrap items-center gap-2">
            <Button
              variant="outline"
              size="sm"
              :class="folderFilter === null ? 'border-primary text-primary' : ''"
              @click="selectFolder(null)"
            >
              {{ t('account.folderAll') }}
              <span class="ml-1.5 text-xs tabular-nums text-muted-foreground">{{ foldersTotal }}</span>
            </Button>
            <Button
              v-for="folder in folders"
              :key="`chip-${folder.id}`"
              variant="outline"
              size="sm"
              :class="folderFilter === folder.id ? 'border-primary text-primary' : ''"
              @click="selectFolder(folder.id)"
            >
              {{ folder.name }}
              <span class="ml-1.5 text-xs tabular-nums text-muted-foreground">{{ folder.count ?? 0 }}</span>
            </Button>
            <Button
              variant="ghost"
              size="sm"
              @click="folderDialogOpen = true"
            >
              <FolderOpen data-icon="inline-start" />
              {{ t('account.manageFolders') }}
            </Button>
          </div>

          <Separator />
          <ul class="flex flex-col gap-4">
            <li
              v-for="row in favoriteRows"
              :key="String(row.id)"
              class="py-2"
            >
              <div class="flex flex-wrap items-center justify-between gap-x-3 gap-y-1">
                <NuxtLink
                  v-if="row.post"
                  :to="`/posts/${row.post.slug}`"
                  class="text-base transition-colors hover:text-primary"
                >
                  {{ resolveLocalized(row.post.title) }}
                </NuxtLink>
                <span
                  v-else
                  class="text-sm text-muted-foreground"
                >{{ t('account.deletedPost') }}</span>
                <span class="flex items-center gap-3 text-xs text-muted-foreground tabular-nums">
                  <span>{{ formatDate(row.created_at) }}</span>
                  <span
                    v-if="row.post?.views != null"
                    class="inline-flex items-center gap-1"
                  >
                    <Eye class="size-3.5" />
                    {{ row.post.views }}
                  </span>
                </span>
              </div>

              <p
                v-if="row.note"
                class="mt-1.5 text-sm text-muted-foreground leading-relaxed"
              >
                {{ row.note }}
              </p>

              <div class="mt-2 flex flex-wrap items-center gap-2">
                <Select
                  :model-value="String(row.folder_id ?? 'none')"
                  :disabled="busyFavoriteId !== null || !row.post"
                  @update:model-value="(v: unknown) => moveToFolder(row, v)"
                >
                  <SelectTrigger
                    class="h-8 w-40"
                    :aria-label="t('account.moveFolder')"
                  >
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="none">
                      {{ t('account.folderNone') }}
                    </SelectItem>
                    <SelectItem
                      v-for="folder in folders"
                      :key="`move-${folder.id}`"
                      :value="String(folder.id)"
                    >
                      {{ folder.name }}
                    </SelectItem>
                  </SelectContent>
                </Select>
                <Button
                  variant="outline"
                  size="sm"
                  :disabled="busyFavoriteId !== null || !row.post"
                  @click="openNoteDialog(row)"
                >
                  <Pencil data-icon="inline-start" />
                  {{ t('account.editNote') }}
                </Button>
                <!-- 文章已删/不可见的收藏行没有 post id，按文章取消的口拿不到它；
                     这类行必须能按收藏行 ID 删掉，否则用户永远清不掉一条"已删除的文章"。 -->
                <Button
                  variant="ghost"
                  size="sm"
                  :disabled="busyFavoriteId !== null"
                  @click="unfavorite(row)"
                >
                  <Trash2 data-icon="inline-start" />
                  {{ t('account.unfavorite') }}
                </Button>
              </div>
            </li>
          </ul>
        </div>

        <!-- ===== 阅读历史（后端在无对应文章时跳过该行，故行数可能少于 page_size） ===== -->
        <div v-else>
          <Separator />
          <ul class="flex flex-col gap-3">
            <li
              v-for="history in historyRows"
              :key="String(history.id)"
              class="flex flex-wrap items-baseline justify-between gap-x-4 gap-y-1 py-2"
            >
              <NuxtLink
                :to="`/posts/${history.post?.slug}`"
                class="text-base transition-colors hover:text-primary"
              >
                {{ history.post?.title }}
              </NuxtLink>
              <span class="flex items-center gap-3 text-sm text-muted-foreground tabular-nums">
                <span>{{ t('account.viewedAt', { time: formatDate(history.viewed_at) }) }}</span>
                <span class="inline-flex items-center gap-1">
                  <Eye class="size-3.5" />
                  {{ history.post?.views ?? 0 }}
                </span>
              </span>
            </li>
          </ul>
        </div>

        <!-- ===== 分页：越界页只回空列表，这里不判 404（私有页，状态码无 SEO 意义） ===== -->
        <nav
          v-if="totalPages > 1"
          class="mt-10 flex items-center justify-between gap-3"
          :aria-label="t(`account.tab${cap(tab)}`)"
        >
          <Button
            v-if="page > 1"
            variant="outline"
            size="sm"
            @click="goPage(page - 1)"
          >
            <ChevronLeft data-icon="inline-start" />
            {{ t('account.prevPage') }}
          </Button>
          <span
            v-else
            aria-hidden="true"
          />
          <span class="text-sm text-muted-foreground tabular-nums">
            {{ page }} / {{ totalPages }}
          </span>
          <Button
            v-if="page < totalPages"
            variant="outline"
            size="sm"
            @click="goPage(page + 1)"
          >
            {{ t('account.nextPage') }}
            <ChevronRight data-icon="inline-end" />
          </Button>
          <span
            v-else
            aria-hidden="true"
          />
        </nav>
      </TabsContent>
    </Tabs>

    <!-- ===== 清空阅读历史二次确认（不可撤销，必须显式确认） ===== -->
    <AlertDialog
      :open="clearDialogOpen"
      @update:open="(v: boolean) => { clearDialogOpen = v }"
    >
      <AlertDialogContent>
        <AlertDialogHeader>
          <AlertDialogTitle class="flex items-center gap-2">
            <Trash2
              data-icon="inline-start"
              class="size-5 text-amber-500"
            />
            {{ t('account.clearHistoryTitle') }}
          </AlertDialogTitle>
          <AlertDialogDescription>
            {{ t('account.clearHistoryBody', { count: total }) }}
          </AlertDialogDescription>
        </AlertDialogHeader>
        <AlertDialogFooter>
          <AlertDialogCancel>
            {{ t('common.cancel') }}
          </AlertDialogCancel>
          <AlertDialogAction
            variant="destructive"
            @click="clearHistory"
          >
            {{ t('account.clearHistory') }}
          </AlertDialogAction>
        </AlertDialogFooter>
      </AlertDialogContent>
    </AlertDialog>

    <!-- ===== 收藏夹管理：新建 + 改名 + 删除（删除只把收藏移回未归类，不删收藏本身） ===== -->
    <Dialog
      :open="folderDialogOpen"
      @update:open="(v: boolean) => { folderDialogOpen = v }"
    >
      <DialogContent class="max-w-md">
        <DialogHeader>
          <DialogTitle>{{ t('account.manageFolders') }}</DialogTitle>
          <DialogDescription>{{ t('account.manageFoldersHint') }}</DialogDescription>
        </DialogHeader>
        <ul class="flex flex-col gap-3">
          <li
            v-for="folder in folders"
            :key="`mgr-${folder.id}`"
            class="flex items-center gap-2"
          >
            <Input
              v-model="folderDrafts[folder.id]"
              :placeholder="folder.name"
              class="h-9"
              :aria-label="folder.name"
            />
            <Button
              variant="outline"
              size="sm"
              :disabled="busyFolderId !== null || !canRename(folder)"
              @click="renameFolder(folder)"
            >
              {{ t('common.save') }}
            </Button>
            <Button
              variant="ghost"
              size="sm"
              :disabled="busyFolderId !== null"
              @click="removeFolder(folder)"
            >
              <Trash2 data-icon="inline-start" />
              {{ t('common.delete') }}
            </Button>
          </li>
          <li
            v-if="folders.length === 0"
            class="text-sm text-muted-foreground"
          >
            {{ t('account.noFolders') }}
          </li>
        </ul>
        <div class="flex items-center gap-2 border-t pt-3">
          <Input
            v-model="newFolderName"
            class="h-9"
            :placeholder="t('account.newFolderPlaceholder')"
            :aria-label="t('account.newFolderPlaceholder')"
          />
          <Button
            size="sm"
            :disabled="busyFolderId !== null || !newFolderName.trim()"
            @click="createFolder"
          >
            {{ t('account.addFolder') }}
          </Button>
        </div>
      </DialogContent>
    </Dialog>

    <!-- ===== 单条收藏的备注（PATCH /favorites/post/{id}/note，留空即清空） ===== -->
    <Dialog
      :open="noteDialogOpen"
      @update:open="(v: boolean) => { noteDialogOpen = v }"
    >
      <DialogContent class="max-w-md">
        <DialogHeader>
          <DialogTitle>{{ t('account.noteTitle') }}</DialogTitle>
          <DialogDescription>{{ t('account.noteHint') }}</DialogDescription>
        </DialogHeader>
        <Input
          v-model="noteDraft"
          :aria-label="t('account.noteTitle')"
          :placeholder="t('account.notePlaceholder')"
        />
        <div class="flex justify-end gap-2">
          <Button
            variant="outline"
            size="sm"
            @click="noteDialogOpen = false"
          >
            {{ t('common.cancel') }}
          </Button>
          <Button
            size="sm"
            :disabled="busyFavoriteId !== null"
            @click="saveNote"
          >
            {{ t('common.save') }}
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  </div>
</template>

<script setup lang="ts">
import {
  Bookmark,
  CalendarClock,
  ChevronLeft,
  ChevronRight,
  Eye,
  FileText,
  FolderOpen,
  Heart,
  MessageSquare,
  Pencil,
  RotateCcw,
  Settings,
  Sparkles,
  ThumbsUp,
  Trash2
} from '@lucide/vue'
import { Badge } from '~~/components/ui/badge'
import { Button } from '~~/components/ui/button'
import { Separator } from '~~/components/ui/separator'
import Skeleton from '~~/components/ui/skeleton/Skeleton.vue'
import { Input } from '~~/components/ui/input'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle
} from '~~/components/ui/dialog'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue
} from '~~/components/ui/select'
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle
} from '~~/components/ui/alert-dialog'
import {
  Tabs,
  TabsContent,
  TabsList,
  TabsTrigger
} from '~~/components/ui/tabs'
import UserAvatar from '~~/components/UserAvatar.vue'
import { apiFetch, useAPI } from '~~/composables/useApi'
import { useFavorites, type FavoriteRow } from '~~/composables/useFavorites'
import { useI18nHelpers } from '~~/composables/useI18nHelpers'
import { useToast } from '~~/composables/useToast'
import { useAuthStore } from '~~/stores/auth'
import { useI18n } from 'vue-i18n'

/** GET /blog/users/me/stats 的信封（唯一带 data 包装的读数端点） */
interface AccountStats {
  success?: boolean
  data?: { posts: number, comments: number, likes: number } | null
}
/** 文章行：/users/me/posts 与 /users/me/likes 共用（后者多 likes_count / comments_count） */
interface AccountPostRow {
  id: number | string
  slug: string
  title?: string
  status?: string
  views?: number
  likes_count?: number
  comments_count?: number
  published_at?: string | null
  created_at?: string | null
}
interface AccountCommentRow {
  id: number | string
  content?: string
  post_slug?: string | null
  post_title?: string | null
  active?: boolean
  created_at?: string | null
}
interface AccountHistoryRow {
  id: number | string
  viewed_at?: string | null
  post?: AccountPostRow | null
}
interface AccountList {
  items: unknown[]
  total: number
  page: number
  page_size: number
  total_pages: number
}

type AccountTab = 'posts' | 'comments' | 'likes' | 'favorites' | 'history'
const TAB_VALUES: AccountTab[] = ['posts', 'comments', 'likes', 'favorites', 'history']

// ssr:false 由 routeRules 精准反选（与 /admin 同档），页面不重复声明，避免两处口径漂移。
definePageMeta({ layout: 'default', middleware: 'auth-required' })

const { t, locale } = useI18n()
const route = useRoute()
const router = useRouter()
const toast = useToast()
const authStore = useAuthStore()

const displayName = computed(() => {
  const u = authStore.user as Record<string, unknown> | null
  const name = (u?.display_name ?? u?.nickname ?? u?.username) as string | undefined
  return typeof name === 'string' ? name : ''
})
const resolvedAvatarUrl = computed(() => {
  const u = authStore.user as Record<string, unknown> | null
  return (u?.resolved_avatar_url as string) || ''
})
const rawAvatar = computed(() => {
  const u = authStore.user as Record<string, unknown> | null
  return (u?.avatar as string) || ''
})
// 头像配色种子必须用稳定的 username：昵称可改，改了会让默认头像换色。
const accountSeed = computed(() => {
  const u = authStore.user as Record<string, unknown> | null
  return (u?.username as string) || displayName.value || ''
})
const coverImage = computed(() => {
  const u = authStore.user as Record<string, unknown> | null
  return String(u?.cover_image ?? '')
})

const tab = computed<AccountTab>(() => {
  const raw = String(route.query.tab ?? '') as AccountTab
  return TAB_VALUES.includes(raw) ? raw : 'posts'
})
const page = computed(() => {
  const raw = Number(route.query.page ?? 1)
  return Number.isFinite(raw) && raw >= 1 ? Math.floor(raw) : 1
})

const tabItems = computed(() => [
  { value: 'posts' as const, label: t('account.tabPosts'), icon: FileText },
  { value: 'comments' as const, label: t('account.tabComments'), icon: MessageSquare },
  { value: 'likes' as const, label: t('account.tabLikes'), icon: ThumbsUp },
  { value: 'favorites' as const, label: t('account.tabFavorites'), icon: Bookmark },
  { value: 'history' as const, label: t('account.tabHistory'), icon: CalendarClock }
])

// ===== 统计读数：信封端点，取 data 内层 =====
const { data: statsData } = useAPI<AccountStats>(
  '/blog/users/me/stats',
  {
    query: computed(() => ({ lang: locale.value })),
    key: computed(() => `account:stats:${locale.value}`)
  }
)

const metrics = computed(() => {
  const s = statsData.value?.data
  return [
    { key: 'posts', label: t('account.statPosts'), value: s?.posts ?? 0, icon: FileText },
    { key: 'comments', label: t('account.statComments'), value: s?.comments ?? 0, icon: MessageSquare },
    { key: 'likes', label: t('account.statLikes'), value: s?.likes ?? 0, icon: Sparkles }
  ]
})

// ===== 当前 tab 的列表：url/key 都随档位变化，切档才发新请求 =====
// 收藏档位走另一个端点族（/favorites，带 folder_id 筛选），其余档位走 /blog/users/me/{tab}。
const favoritesAPI = useFavorites()
const { resolveLocalized } = useI18nHelpers()

const folderFilter = computed(() => {
  const raw = Number(route.query.folder ?? 0)
  return Number.isFinite(raw) && raw > 0 ? Math.floor(raw) : null
})

const listUrl = computed(() =>
  tab.value === 'favorites' ? '/favorites' : `/blog/users/me/${tab.value}`
)
const listQuery = computed(() =>
  tab.value === 'favorites'
    ? { folder_id: folderFilter.value ?? undefined, page: page.value, page_size: 10 }
    : { lang: locale.value, page: page.value, page_size: 10 }
)
const listKey = computed(() =>
  tab.value === 'favorites'
    ? `account:favorites:${folderFilter.value ?? 'all'}:${page.value}`
    : `account:list:${tab.value}:${locale.value}:${page.value}`
)
const {
  data: listData,
  pending,
  error: listError,
  refresh
} = useAPI<AccountList>(() => listUrl.value, {
  query: listQuery,
  key: listKey
})

const rows = computed(() => listData.value?.items ?? [])
const total = computed(() => listData.value?.total ?? 0)
const totalPages = computed(() => listData.value?.total_pages ?? 0)
const postRows = computed<AccountPostRow[]>(() =>
  tab.value === 'posts' || tab.value === 'likes' ? (rows.value as AccountPostRow[]) : []
)
const commentRows = computed<AccountCommentRow[]>(() =>
  tab.value === 'comments' ? (rows.value as AccountCommentRow[]) : []
)
const historyRows = computed<AccountHistoryRow[]>(() =>
  tab.value === 'history' ? (rows.value as AccountHistoryRow[]) : []
)
const favoriteRows = computed<FavoriteRow[]>(() =>
  tab.value === 'favorites' ? (rows.value as FavoriteRow[]) : []
)

// ===== 收藏夹：一次拉全量（列表短、用于筛选条 + 移动菜单 + 管理弹窗三处） =====
const { data: foldersData, refresh: refreshFolders } = favoritesAPI.getFavoriteFolders()
const folders = computed(() => foldersData.value?.items ?? [])
const foldersTotal = computed(() => folders.value.reduce((sum, f) => sum + (f.count ?? 0), 0))
/** 每个收藏夹的改名草稿；键是 folder.id，初始为空表示"未改"。 */
const folderDrafts = ref<Record<number, string>>({})
const newFolderName = ref('')
const folderDialogOpen = ref(false)
const busyFolderId = ref<number | null>(null)

const noteDialogOpen = ref(false)
const noteTarget = ref<FavoriteRow | null>(null)
const noteDraft = ref('')
const busyFavoriteId = ref<number | null>(null)

function selectFolder(id: number | null) {
  const merged: Record<string, string> = { ...route.query as Record<string, string> }
  if (id === null) delete merged.folder
  else merged.folder = String(id)
  // 换收藏夹必须回第 1 页；page=1 是默认态，用 delete 而不是写 '1'（与 writeQuery 同口径）。
  delete merged.page
  void router.push({ path: route.path, query: merged })
}

async function unfavorite(row: FavoriteRow) {
  if (busyFavoriteId.value !== null) return
  const postId = Number(row.post?.id)
  // 没有 post id 的孤儿行（文章已删/不可见）按收藏行 ID 删；by-post 对它无参可用。
  const favoriteId = Number(row.id)
  if (!postId && !favoriteId) return
  busyFavoriteId.value = row.id
  try {
    // 按文章取消（DELETE /favorites/post/{id}）而不是按收藏行 ID：后端语义是
    // "这篇不再收藏"，会清掉该 (user, post) 的全部行；按行 ID 删会让历史重复行留下。
    if (postId) await favoritesAPI.removeFavoriteByPost(postId)
    else await favoritesAPI.removeFavoriteById(favoriteId)
    toast.success(t('account.unfavorited'))
    await Promise.all([refresh(), refreshFolders()])
  } catch {
    // apiFetch 已 toast
  } finally {
    busyFavoriteId.value = null
  }
}

async function moveToFolder(row: FavoriteRow, value: unknown) {
  const postId = Number(row.post?.id)
  if (!postId) return
  const folderId = value === 'none' || value == null ? null : Number(value)
  if (folderId === (row.folder_id ?? null)) return
  busyFavoriteId.value = row.id
  try {
    await favoritesAPI.moveFavoriteByPost(postId, folderId)
    toast.success(t('account.moved'))
    await Promise.all([refresh(), refreshFolders()])
  } catch {
    /* 同上 */
  } finally {
    busyFavoriteId.value = null
  }
}

function openNoteDialog(row: FavoriteRow) {
  noteTarget.value = row
  noteDraft.value = row.note ?? ''
  noteDialogOpen.value = true
}

async function saveNote() {
  const row = noteTarget.value
  const postId = Number(row?.post?.id)
  if (!row || !postId) return
  busyFavoriteId.value = row.id
  try {
    // 空串 → null：后端 PATCH 的 note=null 才是"清空备注"，传 '' 会在列表里留一条空备注。
    await favoritesAPI.setFavoriteNote(postId, noteDraft.value.trim() || null)
    toast.success(t('account.noteSaved'))
    noteDialogOpen.value = false
    await refresh()
  } catch {
    /* 同上 */
  } finally {
    busyFavoriteId.value = null
  }
}

async function createFolder() {
  const name = newFolderName.value.trim()
  if (!name || busyFolderId.value !== null) return
  busyFolderId.value = 0
  try {
    await favoritesAPI.createFolder(name)
    newFolderName.value = ''
    toast.success(t('account.folderCreated'))
    await refreshFolders()
  } catch {
    /* 同上 */
  } finally {
    busyFolderId.value = null
  }
}

/** 改名按钮的唯一可用口径：草稿非空且与现名不同 —— 否则点击必然是静默 no-op */
function canRename(folder: { id: number, name: string }): boolean {
  const next = (folderDrafts.value[folder.id] ?? '').trim()
  return Boolean(next) && next !== folder.name
}

async function renameFolder(folder: { id: number, name: string }) {
  const next = (folderDrafts.value[folder.id] ?? '').trim()
  if (!next || next === folder.name || busyFolderId.value !== null) return
  busyFolderId.value = folder.id
  try {
    await favoritesAPI.updateFolder(folder.id, { name: next })
    folderDrafts.value = { ...folderDrafts.value, [folder.id]: '' }
    toast.success(t('account.folderRenamed'))
    await Promise.all([refreshFolders(), refresh()])
  } catch {
    /* 同上 */
  } finally {
    busyFolderId.value = null
  }
}

async function removeFolder(folder: { id: number, name: string }) {
  if (busyFolderId.value !== null) return
  busyFolderId.value = folder.id
  try {
    await favoritesAPI.deleteFolder(folder.id)
    toast.success(t('account.folderDeleted'))
    // 收藏夹没了还留在筛选条件里 = 一片空白页；删完把筛选复位到"全部"。
    if (folderFilter.value === folder.id) selectFolder(null)
    await Promise.all([refreshFolders(), refresh()])
  } catch {
    /* 同上 */
  } finally {
    busyFolderId.value = null
  }
}

function cap(value: string): string {
  return value.charAt(0).toUpperCase() + value.slice(1)
}
function emptyLabel(value: AccountTab): string {
  return t(`account.empty${cap(value)}`)
}
function statusLabel(status?: string): string {
  if (status === 'published') return t('account.statusPublished')
  if (status === 'draft') return t('account.statusDraft')
  if (status === 'pending') return t('account.statusPending')
  return status ?? ''
}

// computed：本页是 SPA（ssr:false），切语言不会重跑 setup。写成一次性 const 会让
// 日期永远停在"首次进入这一页时的语言"格式，而同一页的标题与状态文案都会跟着变。
const formatter = computed(() =>
  new Intl.DateTimeFormat(locale.value, {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
    timeZone: 'UTC'
  })
)
function formatDate(value?: string | null): string {
  if (!value) return ''
  const date = new Date(value)
  return Number.isNaN(date.getTime()) ? '' : formatter.value.format(date)
}

/** tab / page 都写进 query：可分享、浏览器前进后退可用，刷新不丢档 */
function writeQuery(next: Record<string, string>) {
  const merged: Record<string, string | undefined> = { ...route.query as Record<string, string>, ...next }
  if (merged.page === '1') delete merged.page
  if (Object.keys(merged).length === 0) return router.push({ path: route.path })
  return router.push({ path: route.path, query: merged })
}
function onTabChange(value: string | number) {
  const next = String(value) as AccountTab
  if (next === tab.value) return
  void writeQuery({ tab: next, page: '1' })
}
function goPage(value: number) {
  void writeQuery({ page: String(value) })
}

async function reload() {
  await refresh()
}

// 取消点赞复用点赞开关（POST /posts/{id}/like 是 toggle），不新造后端语义。
const pendingLikeId = ref<string | null>(null)
async function unlike(post: AccountPostRow) {
  const id = String(post.id)
  if (pendingLikeId.value !== null) return
  pendingLikeId.value = id
  try {
    await apiFetch(`/blog/posts/${id}/like`, { method: 'POST' })
    toast.success(t('account.unliked'))
    await refresh()
  } catch {
    // apiFetch 已按统一失败信封 toast，这里只吞 rejection 防未处理异常
  } finally {
    pendingLikeId.value = null
  }
}

const clearDialogOpen = ref(false)
async function clearHistory() {
  clearDialogOpen.value = false
  try {
    await apiFetch('/blog/users/me/history', { method: 'DELETE' })
    toast.success(t('account.historyCleared'))
    await refresh()
  } catch {
    // 同上：失败提示由 apiFetch 统一负责
  }
}

useHead(() => ({ title: t('account.title') }))
// 个人中心是逐登录用户内容，robots.txt 的 Disallow 不足以挡住收录（见 login.vue 同口径）。
useNoindexPage()
</script>

<style scoped>
/* 复用归档骨架的排版令牌，本文件不引入新皮肤（主题样式零依赖）。 */
</style>
