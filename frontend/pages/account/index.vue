<!--
  个人中心 /account（SPA + no-store）：把后端自上线起一直"就绪、前端零消费"的 6 个
  /blog/users/me/* 端点接成 WordPress「我的账户」同款落地页 —— stats（文章/评论/获赞读数）、
  posts（我的文章，含草稿）、comments（我的评论）、likes（我的点赞，可取消）、
  history（阅读历史，可清空）。
  四条硬约束：
  1. ssr:false 写在 routeRules（不在页面里重复声明）：本页内容逐登录用户不同，而 auth store
     是 skipHydrate + localStorage，SSR 期根本没有 token；若走 SSR，未登录的 401 骨架会被渲染
     成"公共页面"，缓存头也就不能是公开 s-maxage。故与 /admin 同档：ssr:false + no-store, private。
  2. 登录闸门在命名中间件 auth-required（不进全局链），未登录带 ?redirect= 跳 /login；
     页面 setup 只管渲染，不做第二套状态判定（AGENTS.md §2.3.2 同源理由）。
  3. 一次只发「统计 + 当前 tab」两个请求：tab 与 page 都在 query 里，useAPI 的 url/key 随之
     变化，切 tab 不会把另外三档全量拉一遍。
  4. 日期格式化钉死 locale + timeZone：本仓两端时区不一致过，归档侧已按同口径修过一轮。
-->
<template>
  <div class="container py-16 max-w-3xl mx-auto">
    <header class="mb-10 flex flex-wrap items-center justify-between gap-x-6 gap-y-4">
      <div class="flex items-center gap-4 min-w-0">
        <UserAvatar
          :resolved-avatar-url="resolvedAvatarUrl"
          :avatar="rawAvatar"
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
      <TabsList class="grid w-full grid-cols-2 sm:grid-cols-4 mb-8">
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
  </div>
</template>

<script setup lang="ts">
import {
  CalendarClock,
  ChevronLeft,
  ChevronRight,
  Eye,
  FileText,
  Heart,
  MessageSquare,
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

type AccountTab = 'posts' | 'comments' | 'likes' | 'history'
const TAB_VALUES: AccountTab[] = ['posts', 'comments', 'likes', 'history']

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

// ===== 当前 tab 的列表：url 与 key 都随 tab/page 变化，切档才发新请求 =====
const {
  data: listData,
  pending,
  error: listError,
  refresh
} = useAPI<AccountList>(
  () => `/blog/users/me/${tab.value}`,
  {
    query: computed(() => ({ lang: locale.value, page: page.value, page_size: 10 })),
    key: computed(() => `account:list:${tab.value}:${locale.value}:${page.value}`)
  }
)

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

const formatter = new Intl.DateTimeFormat(locale.value, {
  year: 'numeric',
  month: 'short',
  day: 'numeric',
  timeZone: 'UTC'
})
function formatDate(value?: string | null): string {
  if (!value) return ''
  const date = new Date(value)
  return Number.isNaN(date.getTime()) ? '' : formatter.format(date)
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

useHead(() => ({ title: `${t('account.title')} · ${locale.value}` }))
</script>

<style scoped>
/* 复用归档骨架的排版令牌，本文件不引入新皮肤（主题样式零依赖）。 */
</style>
