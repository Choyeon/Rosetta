<template>
  <div class="space-y-6">
    <div class="flex flex-wrap items-start justify-between gap-3">
      <div>
        <h1 class="text-3xl font-bold tracking-tight font-display">
          {{ t('admin.dashboard.title') }}
        </h1>
        <p class="text-sm text-muted-foreground mt-1">
          {{ t('admin.dashboard.welcome', { name: userName }) }}
        </p>
      </div>
      <div class="flex flex-wrap items-center gap-2">
        <Button
          :is="'NuxtLink'"
          as="component"
          to="/admin/posts/new"
        >
          <Plus class="mr-2 size-4" />
          {{ t('admin.dashboard.newPost') }}
        </Button>
        <Button
          :is="'NuxtLink'"
          variant="outline"
          as="component"
          to="/admin/comments"
        >
          <MessageSquare class="mr-2 size-4" />
          {{ t('admin.dashboard.manageComments') }}
        </Button>
        <Button
          :is="'NuxtLink'"
          variant="outline"
          as="component"
          to="/admin/settings"
        >
          <Settings2 class="mr-2 size-4" />
          {{ t('admin.dashboard.siteSettings') }}
        </Button>
      </div>
    </div>

    <!-- 统计卡片 -->
    <div
      v-if="statsError"
      class="flex flex-col items-start gap-3"
    >
      <Alert variant="destructive">
        <AlertCircle class="size-4" />
        <AlertTitle>{{ t('admin.dashboard.loadFailed') }}</AlertTitle>
        <AlertDescription>{{ statsError }}</AlertDescription>
      </Alert>
      <Button
        variant="outline"
        size="sm"
        :disabled="loadingStats"
        @click="loadStats"
      >
        <RefreshCw
          class="mr-2 size-4"
          :class="{ 'animate-spin': loadingStats }"
        />
        {{ t('admin.dashboard.retry') }}
      </Button>
    </div>

    <div
      v-else-if="loadingStats && !stats"
      class="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-4"
    >
      <Card
        v-for="i in 8"
        :key="i"
      >
        <CardContent class="p-6 space-y-3">
          <Skeleton class="h-4 w-24" />
          <Skeleton class="h-9 w-20" />
        </CardContent>
      </Card>
    </div>

    <div
      v-else-if="stats"
      class="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-4"
    >
      <Card
        v-for="card in statCards"
        :key="card.label"
      >
        <CardContent class="p-6 space-y-1">
          <p class="text-sm text-muted-foreground">
            {{ card.label }}
          </p>
          <h2 class="font-display text-3xl font-bold">
            {{ card.value.toLocaleString() }}
          </h2>
        </CardContent>
      </Card>
    </div>

    <!-- 浏览趋势 -->
    <Card>
      <CardHeader class="flex flex-row items-center justify-between">
        <div>
          <CardTitle class="text-xl">
            {{ t('admin.dashboard.viewsTrend') }}
          </CardTitle>
          <CardDescription>{{ t('admin.dashboard.viewsTrendDesc') }}</CardDescription>
        </div>
        <Select
          v-model="statsRange"
          @update:model-value="loadStats"
        >
          <SelectTrigger class="w-32">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="7d">
              {{ t('admin.dashboard.trend7d') }}
            </SelectItem>
            <SelectItem value="30d">
              {{ t('admin.dashboard.trend30d') }}
            </SelectItem>
          </SelectContent>
        </Select>
      </CardHeader>
      <CardContent>
        <div
          v-if="loadingStats && !stats"
          class="space-y-3"
        >
          <Skeleton class="h-48 w-full" />
          <Skeleton class="h-4 w-2/3" />
        </div>
        <div v-else-if="trendBars.length > 0">
          <div class="overflow-x-auto">
            <div class="flex items-end gap-1.5 h-48 min-w-[32rem] px-1 pt-2">
              <div
                v-for="bar in trendBars"
                :key="bar.label"
                class="flex-1 min-w-4 rounded-t bg-primary/70 hover:bg-primary transition-colors relative group"
                :style="{ height: `${bar.heightPercent}%` }"
              >
                <div class="absolute -top-8 left-1/2 -translate-x-1/2 bg-foreground text-background text-xs px-2 py-1 rounded opacity-0 group-hover:opacity-100 transition-opacity whitespace-nowrap z-10">
                  {{ bar.label }}: {{ bar.value.toLocaleString() }}
                </div>
              </div>
            </div>
          </div>
          <div class="flex gap-1.5 mt-2 text-xs text-muted-foreground min-w-[32rem]">
            <div
              v-for="bar in trendBars"
              :key="`l-${bar.label}`"
              class="flex-1 min-w-4 text-center truncate"
            >
              {{ bar.shortLabel }}
            </div>
          </div>
        </div>
        <div
          v-else
          class="flex flex-col items-center justify-center py-12 text-muted-foreground"
        >
          <LineChart class="size-8 mb-2" />
          <p class="text-sm">
            {{ t('admin.dashboard.empty') }}
          </p>
        </div>
      </CardContent>
    </Card>

    <!-- 近期文章 -->
    <Card class="rounded-none border-0 shadow-none">
      <CardHeader class="flex flex-row items-center justify-between px-0">
        <div>
          <CardTitle class="text-xl">
            {{ t('admin.dashboard.recentPosts') }}
          </CardTitle>
          <CardDescription>{{ t('admin.dashboard.recentPostsDesc') }}</CardDescription>
        </div>
      </CardHeader>
      <CardContent class="px-0">
        <div
          v-if="loadingPosts && recentPosts.length === 0"
          class="space-y-3"
        >
          <Skeleton
            v-for="i in 5"
            :key="i"
            class="h-12 w-full"
          />
        </div>
        <template v-else-if="recentPosts.length > 0">
          <div class="overflow-x-auto">
            <table class="w-full text-sm">
              <thead>
                <tr class="border-b">
                  <th class="text-left font-medium text-muted-foreground p-3 pl-0">
                    {{ t('admin.dashboard.thTitle') }}
                  </th>
                  <th class="text-left font-medium text-muted-foreground p-3">
                    {{ t('admin.dashboard.thCategory') }}
                  </th>
                  <th class="text-left font-medium text-muted-foreground p-3">
                    {{ t('admin.dashboard.thStatus') }}
                  </th>
                  <th class="text-left font-medium text-muted-foreground p-3">
                    {{ t('admin.dashboard.thDate') }}
                  </th>
                  <th class="text-left font-medium text-muted-foreground p-3">
                    {{ t('admin.dashboard.thViews') }}
                  </th>
                  <th class="text-right font-medium text-muted-foreground p-3 pr-0">
                    {{ t('admin.dashboard.thActions') }}
                  </th>
                </tr>
              </thead>
              <tbody>
                <tr
                  v-for="post in recentPosts"
                  :key="post.id"
                  class="border-b last:border-0 transition-colors hover:bg-muted/50"
                >
                  <td class="p-3 pl-0">
                    <span class="font-medium">{{ post.title }}</span>
                  </td>
                  <td class="p-3">
                    <Badge
                      v-if="post.category"
                      variant="secondary"
                    >
                      {{ post.category.name }}
                    </Badge>
                    <span
                      v-else
                      class="text-muted-foreground"
                    >-</span>
                  </td>
                  <td class="p-3">
                    <Badge :class="statusBadgeClass(post.status)">
                      {{ postStatusLabel(post.status) }}
                    </Badge>
                  </td>
                  <td class="p-3 text-muted-foreground">
                    {{ formatAdminDate(post.published_at ?? post.created_at) }}
                  </td>
                  <td class="p-3">
                    <span class="flex items-center gap-1">
                      <Eye class="size-3" />
                      {{ post.views.toLocaleString() }}
                    </span>
                  </td>
                  <td class="p-3 pr-0 text-right">
                    <Button
                      :is="'NuxtLink'"
                      variant="ghost"
                      size="sm"
                      as="component"
                      :to="`/admin/posts/${post.id}/edit`"
                    >
                      <Pencil class="mr-2 size-4" />
                      {{ t('admin.dashboard.edit') }}
                    </Button>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </template>
        <Alert
          v-else
          class="mt-2"
        >
          <Activity class="size-4" />
          <AlertTitle>{{ t('admin.dashboard.noPosts') }}</AlertTitle>
          <AlertDescription>{{ t('admin.dashboard.noPostsDesc') }}</AlertDescription>
        </Alert>
      </CardContent>
    </Card>

    <!-- 热门文章 / 活跃评论者 / 系统健康 -->
    <div class="grid grid-cols-1 lg:grid-cols-3 gap-4">
      <Card>
        <CardHeader>
          <CardTitle class="text-base">
            {{ t('admin.dashboard.topArticles') }}
          </CardTitle>
          <CardDescription>{{ t('admin.dashboard.topArticlesDesc') }}</CardDescription>
        </CardHeader>
        <CardContent class="space-y-3">
          <div
            v-for="(a, i) in stats?.top_articles ?? []"
            :key="a.id"
            class="flex items-center justify-between gap-3 text-sm"
          >
            <div class="flex items-center gap-2 min-w-0">
              <span class="text-muted-foreground w-4">{{ i + 1 }}</span>
              <span class="truncate">{{ a.title }}</span>
            </div>
            <span class="flex items-center gap-1 text-muted-foreground shrink-0">
              <Eye class="size-3" />
              {{ a.views.toLocaleString() }}
            </span>
          </div>
          <p
            v-if="(stats?.top_articles ?? []).length === 0"
            class="text-sm text-muted-foreground"
          >
            {{ t('admin.dashboard.empty') }}
          </p>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle class="text-base">
            {{ t('admin.dashboard.activeCommenters') }}
          </CardTitle>
          <CardDescription>{{ t('admin.dashboard.activeCommentersDesc') }}</CardDescription>
        </CardHeader>
        <CardContent class="space-y-3">
          <div
            v-for="c in stats?.active_commenters ?? []"
            :key="c.name"
            class="flex items-center justify-between gap-3 text-sm"
          >
            <div class="flex items-center gap-2 min-w-0">
              <Avatar size="sm">
                <AvatarImage
                  v-if="c.avatar"
                  :src="c.avatar"
                  :alt="c.name"
                />
                <AvatarFallback>{{ c.name[0] }}</AvatarFallback>
              </Avatar>
              <span class="truncate">{{ c.name }}</span>
            </div>
            <span class="text-muted-foreground shrink-0">
              {{ t('admin.dashboard.commentsCount', { n: c.comments_count }) }}
            </span>
          </div>
          <p
            v-if="(stats?.active_commenters ?? []).length === 0"
            class="text-sm text-muted-foreground"
          >
            {{ t('admin.dashboard.empty') }}
          </p>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle class="text-base">
            {{ t('admin.dashboard.systemHealth') }}
          </CardTitle>
          <CardDescription>
            {{ t('admin.dashboard.healthScore') }}:
            <span class="font-medium text-foreground">{{ healthScore ?? '-' }}</span>
          </CardDescription>
        </CardHeader>
        <CardContent class="space-y-4">
          <div
            v-for="m in healthMetrics"
            :key="m.label"
            class="space-y-1.5"
          >
            <div class="flex justify-between text-sm">
              <span class="text-muted-foreground">{{ m.label }}</span>
              <span>{{ m.value }}</span>
            </div>
            <div
              v-if="m.percent !== null"
              class="h-1.5 rounded-full bg-muted overflow-hidden"
            >
              <div
                class="h-full rounded-full bg-primary"
                :style="{ width: `${m.percent}%` }"
              />
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  </div>
</template>

<script setup lang="ts">
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle
} from '~~/components/ui/card'
import { Button } from '~~/components/ui/button'
import { Badge } from '~~/components/ui/badge'
import { Skeleton } from '~~/components/ui/skeleton'
import { Avatar, AvatarFallback, AvatarImage } from '~~/components/ui/avatar'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '~~/components/ui/select'
import {
  Alert,
  AlertDescription,
  AlertTitle
} from '~~/components/ui/alert'
import {
  Plus,
  MessageSquare,
  Settings2,
  Pencil,
  Eye,
  Activity,
  RefreshCw,
  AlertCircle,
  LineChart
} from '@lucide/vue'
import { useAuthStore } from '~~/stores/auth'
import {
  fetchDashboardStats,
  fetchRecentPosts,
  formatAdminDate,
  type AdminPostListItem,
  type DashboardStats,
  type StatsRange
} from '~~/composables/useAdminManage'

definePageMeta({
  layout: 'admin'
})

const { t } = useI18n()
const authStore = useAuthStore()

const stats = ref<DashboardStats | null>(null)
const loadingStats = ref(false)
const statsError = ref('')
const statsRange = ref<StatsRange>('7d')

const recentPosts = ref<AdminPostListItem[]>([])
const loadingPosts = ref(false)

const userName = computed(() => {
  const u = authStore.user
  if (!u) return ''
  const name = (u as { name?: string, nickname?: string, username?: string }).name
    ?? (u as { nickname?: string }).nickname
    ?? (u as { username?: string }).username
    ?? ''
  return name ? `，${name}` : ''
})

const statCards = computed(() => {
  const s = stats.value?.summary
  if (!s) return []
  return [
    { label: t('admin.dashboard.stat.totalPosts'), value: s.total_posts },
    { label: t('admin.dashboard.stat.published'), value: s.total_published },
    { label: t('admin.dashboard.stat.drafts'), value: s.total_drafts },
    { label: t('admin.dashboard.stat.totalComments'), value: s.total_comments },
    { label: t('admin.dashboard.stat.pendingComments'), value: s.total_pending_comments },
    { label: t('admin.dashboard.stat.totalUsers'), value: s.total_users },
    { label: t('admin.dashboard.stat.viewsToday'), value: s.total_views_today },
    { label: t('admin.dashboard.stat.commentsToday'), value: s.total_comments_today }
  ]
})

interface TrendBar {
  label: string
  shortLabel: string
  value: number
  heightPercent: number
}

const trendBars = computed<TrendBar[]>(() => {
  const ts = stats.value?.timeseries
  if (!ts) return []
  const pv = ts.datasets.find(d => d.key === 'pv')
  const values = pv?.values ?? []
  const max = Math.max(...values, 0)
  if (max <= 0) return []
  return ts.labels.map((label, i) => {
    const value = values[i] ?? 0
    return {
      label,
      shortLabel: label.slice(5),
      value,
      heightPercent: Math.max(2, Math.round((value / max) * 100))
    }
  })
})

const healthScore = computed(() => stats.value?.system_health.health_score ?? null)

const healthMetrics = computed(() => {
  const h = stats.value?.system_health
  if (!h) return []
  return [
    {
      label: t('admin.dashboard.cpu'),
      value: h.cpu_percent === null ? '-' : `${h.cpu_percent}%`,
      percent: h.cpu_percent
    },
    {
      label: t('admin.dashboard.memory'),
      value: h.memory_percent === null ? '-' : `${h.memory_percent}%`,
      percent: h.memory_percent
    },
    {
      label: t('admin.dashboard.dbRtt'),
      value: h.db_rtt_ms === null ? '-' : `${h.db_rtt_ms} ${t('admin.dashboard.ms')}`,
      percent: null
    },
    {
      label: t('admin.dashboard.cacheHit'),
      value: h.cache_hit_percent === null ? '-' : `${h.cache_hit_percent}%`,
      percent: h.cache_hit_percent
    }
  ]
})

function postStatusLabel(status: string): string {
  const key = `admin.dashboard.status.${status}`
  const label = t(key)
  return label === key ? status : label
}

function statusBadgeClass(status: string): string {
  switch (status) {
    case 'published':
      return 'bg-success-muted text-success border-transparent'
    case 'draft':
      return 'bg-muted text-muted-foreground border-transparent'
    case 'scheduled':
      return 'bg-info-muted text-info border-transparent'
    default:
      return ''
  }
}

function extractErrorMessage(err: unknown): string {
  const e = err as { data?: { message?: string, detail?: unknown } }
  if (e?.data?.message) return e.data.message
  if (typeof e?.data?.detail === 'string') return e.data.detail
  return err instanceof Error ? err.message : String(err)
}

async function loadStats(): Promise<void> {
  loadingStats.value = true
  statsError.value = ''
  try {
    stats.value = await fetchDashboardStats(statsRange.value)
  } catch (err) {
    statsError.value = extractErrorMessage(err)
  } finally {
    loadingStats.value = false
  }
}

async function loadRecentPosts(): Promise<void> {
  loadingPosts.value = true
  try {
    recentPosts.value = await fetchRecentPosts(8)
  } catch {
    // apiFetch 已统一 toast；近期文章失败不影响仪表盘其余部分
    recentPosts.value = []
  } finally {
    loadingPosts.value = false
  }
}

onMounted(() => {
  loadStats()
  loadRecentPosts()
})
</script>
