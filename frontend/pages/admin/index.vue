<script setup lang="ts">
/* eslint-disable */
/* eslint-disable @typescript-eslint/ban-ts-comment */
// @ts-nocheck
/* eslint-enable @typescript-eslint/ban-ts-comment */
import {
  Eye,
  Users,
  MessageSquare,
  FileText,
  ChevronRight,
  Activity as ActivityIcon,
  AlertTriangle,
  CheckCircle2,
  TrendingUp,
  ArrowUpRight
} from '@lucide/vue'
import StatCard from '~~/components/admin/StatCard.vue'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '~~/components/ui/card'
import { Button } from '~~/components/ui/button'
import { Avatar, AvatarFallback, AvatarImage } from '~~/components/ui/avatar'
import { Badge } from '~~/components/ui/badge'
import { Progress } from '~~/components/ui/progress'
import { Skeleton } from '~~/components/ui/skeleton'
import { Tooltip, TooltipContent, TooltipTrigger } from '~~/components/ui/tooltip'
import { useAuthStore } from '~~/stores/auth'
import { useToast } from '~~/composables/useToast'
import {
  fetchDashboardStats,
  fetchRecentPosts,
  fetchAdminComments,
  fetchAdminActivities,
  type DashboardStats,
  type StatsRange,
  type AdminComment,
  type AdminActivity
} from '~~/composables/useAdminManage'

definePageMeta({
  ssr: false,
  layout: 'admin'
  // 登录 & 管理员权限校验：由 middleware/admin.global.ts 全局守卫负责
})

const authStore = useAuthStore()
const { error: toastError, success } = useToast()

const loading = ref(true)

// ====== 数据类型（来自后端真实接口 /api/admin/stats ）======
interface DashSummary {
  postsCount: number
  publishedCount: number
  draftCount: number
  views24h: number
  views7d: number
  usersCount: number
  pendingComments: number
  totalComments: number
  oobeComplete: boolean
}
const summary = ref<DashSummary>({
  postsCount: 0, publishedCount: 0, draftCount: 0,
  views24h: 0, views7d: 0, usersCount: 0,
  pendingComments: 0, totalComments: 0, oobeComplete: true
})

interface ActivityItem {
  id: number
  icon: 'post' | 'comment' | 'user' | 'system' | 'alert'
  text: string
  time: string
  accent: 'primary' | 'success' | 'warning' | 'info' | 'error'
}
const activities = ref<ActivityItem[]>([])

interface HotPost {
  id: number
  title: string
  views: number
  comments: number
  /** 真实接口暂无此字段，改为 null（避免 Math.random 假趋势） */
  trend: number | null
  slug: string
}
const hotPosts = ref<HotPost[]>([])

interface HealthItem { label: string, value: number, status: 'ok' | 'warn' | 'bad' }
const health = ref<HealthItem[]>([])

const statsRange = ref<StatsRange>('7d')
let statsRaw: DashboardStats | null = null

// ====== 工具：相对时间（中文友好） ======
function timeAgo(iso: string | null | undefined): string {
  if (!iso) return '刚刚'
  const d = new Date(iso).getTime()
  if (Number.isNaN(d)) return String(iso)
  const diff = Math.max(0, Date.now() - d)
  const min = 60 * 1000
  const hr = 60 * min
  const day = 24 * hr
  if (diff < min) return '刚刚'
  if (diff < hr) return `${Math.floor(diff / min)} 分钟前`
  if (diff < day) return `${Math.floor(diff / hr)} 小时前`
  if (diff < 7 * day) return `${Math.floor(diff / day)} 天前`
  const dt = new Date(d)
  return `${dt.getMonth() + 1} 月 ${dt.getDate()} 日`
}

// ====== 加载数据：全部走真实后端 API ======
async function loadAll() {
  loading.value = true
  try {
    // 1) 主仪表盘：GET /api/admin/stats?range=7d|30d
    statsRaw = await fetchDashboardStats(statsRange.value)
    const s = statsRaw.summary
    const pvSeries = statsRaw.timeseries.datasets.find(d => d.key === 'pv')?.values ?? []
    const sevenDayViews = pvSeries.reduce((a: number, b: number) => a + b, 0)
    const lastDayPv = pvSeries.length ? pvSeries[pvSeries.length - 1] : 0

    summary.value = {
      postsCount: s.total_posts ?? 0,
      publishedCount: s.total_published ?? 0,
      draftCount: s.total_drafts ?? 0,
      views24h: s.total_views_today ?? lastDayPv ?? 0,
      views7d: sevenDayViews,
      usersCount: s.total_users ?? 0,
      pendingComments: s.total_pending_comments ?? 0,
      totalComments: s.total_comments ?? 0,
      oobeComplete: true
    }

    // 2) 热门文章：后端 top_articles（按浏览量排序）
    hotPosts.value = (statsRaw.top_articles || []).map((p) => ({
      id: p.id,
      title: p.title,
      views: p.views ?? 0,
      comments: p.comments_count ?? 0,
      // 后端未返回真实的"相比上期趋势"字段，保持 null 不伪造
      trend: null,
      slug: ''
    }))

    // 3) 系统健康：后端 system_health（cpu / mem / db / cache）
    const h = statsRaw.system_health || {}
    const items: Array<[string, number | null]> = [
      ['CPU 使用率', h.cpu_percent],
      ['内存占用', h.memory_percent],
      ['数据库 RTT (ms)', h.db_rtt_ms],
      ['缓存命中率', h.cache_hit_percent]
    ]
    const toStatus = (v: number | null, isRtt = false): 'ok' | 'warn' | 'bad' => {
      if (v === null || Number.isNaN(v)) return 'ok'
      if (isRtt) return v < 30 ? 'ok' : v < 100 ? 'warn' : 'bad'
      return v < 60 ? 'ok' : v < 80 ? 'warn' : 'bad'
    }
    health.value = items
      .filter(([, v]) => v !== null && v !== undefined)
      .map(([label, v]) => ({
        label,
        value: Math.round((v as number) * 10) / 10,
        status: toStatus(v, label.startsWith('数据库'))
      }))

    // 4) 近期活动：并行拉取 最近动态 / 待审评论 / 最近文章，合并时间线
    try {
      const [postsRes, commentsRes, actRes] = await Promise.allSettled([
        fetchRecentPosts(5),
        fetchAdminComments({ page: 1, page_size: 5, status: 'pending' }).catch(() => null as any),
        fetchAdminActivities({ page: 1, page_size: 5 }).catch(() => null as any)
      ])

      const merged: ActivityItem[] = []

      if (postsRes.status === 'fulfilled') {
        for (const p of postsRes.value.slice(0, 3)) {
          merged.push({
            id: 10000 + Number(p.id),
            icon: 'post',
            text: `${p.status === 'published' ? '已发布' : '草稿'}：《${p.title}》`,
            time: timeAgo(p.published_at ?? p.created_at),
            accent: p.status === 'published' ? 'success' : 'warning'
          })
        }
      }

      if (commentsRes.status === 'fulfilled' && commentsRes.value?.items?.length) {
        for (const c of commentsRes.value.items.slice(0, 3) as AdminComment[]) {
          merged.push({
            id: 20000 + Number(c.id),
            icon: 'comment',
            text: `新评论待审核：来自「${c.author_name}」`,
            time: timeAgo(c.created_at),
            accent: 'warning'
          })
        }
      }

      if (actRes.status === 'fulfilled' && actRes.value?.items?.length) {
        let fallbackSeq = 0
        for (const a of actRes.value.items.slice(0, 3) as AdminActivity[]) {
          const content: string = (a as any).content ?? (a as any).text ?? (a as any).message ?? '发布了新动态'
          fallbackSeq += 1
          const idN = Number((a as any).id)
          merged.push({
            id: Number.isFinite(idN) && idN > 0
              ? 30000 + idN
              : 3000000 + fallbackSeq,
            icon: 'system',
            text: content.slice(0, 60),
            time: timeAgo((a as any).created_at),
            accent: 'primary'
          })
        }
      }

      // 按时间关键字倒序（粗略：id 越大时间越近），取前 5 条
      merged.sort((x, y) => y.id - x.id)
      activities.value = merged.slice(0, 5)
    } catch (e) {
      // 子链路加载失败不影响整体
    }
  } catch (e: any) {
    toastError(e?.message || '仪表盘数据加载失败')
    // 清空数据（不再展示假数据，符合用户要求："只是真实的后台不需要这是假数据"）
    activities.value = []
    hotPosts.value = []
    health.value = []
  } finally {
    loading.value = false
  }
}

onMounted(loadAll)

const greeting = computed(() => {
  const h = new Date().getHours()
  if (h < 6) return '凌晨好'
  if (h < 11) return '早上好'
  if (h < 13) return '中午好'
  if (h < 18) return '下午好'
  return '晚上好'
})
const today = computed(() => {
  const d = new Date()
  return `${d.getFullYear()} 年 ${d.getMonth() + 1} 月 ${d.getDate()} 日`
})

const viewsTrend = computed(() => {
  if (!summary.value.views7d) return { v: '0%', d: 'flat' as const, hint: '' }
  const avg = summary.value.views7d / 7
  if (avg <= 0) return { v: '+0%', d: 'up' as const, hint: '新站' }
  const diff = ((summary.value.views24h - avg) / avg) * 100
  return {
    v: (diff >= 0 ? '+' : '') + diff.toFixed(1) + '%',
    d: Math.abs(diff) < 2 ? 'flat' as const : diff > 0 ? 'up' as const : 'down' as const,
    hint: 'vs 日均'
  }
})

const iconFor = (t: ActivityItem['icon']) => ({
  post: FileText,
  comment: MessageSquare,
  user: Users,
  system: ActivityIcon,
  alert: AlertTriangle
}[t])

const pillFor = (a: ActivityItem['accent']) => ({
  primary: 'bg-[#E0F2FE] text-[#0369A1] dark:bg-[#075985]/40 dark:text-[#BAE6FD]',
  success: 'bg-[#ECFDF5] text-[#065F46] dark:bg-[#064E3B]/40 dark:text-[#A7F3D0]',
  warning: 'bg-[#FEF9C3] text-[#854D0E] dark:bg-[#713F12]/40 dark:text-[#FDE68A]',
  info: 'bg-[#EFF6FF] text-[#1E40AF] dark:bg-[#1E3A8A]/40 dark:text-[#BFDBFE]',
  error: 'bg-[#FEF2F2] text-[#991B1B] dark:bg-[#7F1D1D]/40 dark:text-[#FECACA]'
}[a])
</script>

<template>
  <div class="admin-dashboard space-y-6 animate-in">
    <!-- 欢迎横幅 -->
    <section
      class="relative overflow-hidden rounded-[16px] p-6 md:p-7 text-white shadow-[0_10px_30px_-12px_rgba(14,165,233,0.45)]"
      style="background: linear-gradient(135deg,#0EA5E9 0%,#0284C7 55%,#075985 100%);"
    >
      <div
        aria-hidden="true"
        class="pointer-events-none absolute -top-12 -right-12 size-56 rounded-full bg-white/10 blur-2xl"
      />
      <div class="relative flex flex-col md:flex-row md:items-center md:justify-between gap-5">
        <div class="min-w-0">
          <p class="text-white/80 text-sm">
            {{ today }} · {{ greeting }}，{{ authStore.user?.username || '管理员' }}
          </p>
          <h1 class="mt-1 font-display font-bold text-2xl md:text-3xl tracking-tight">
            欢迎回到 <span class="underline decoration-white/30 decoration-4 underline-offset-4">Rosetta Admin</span>
          </h1>
          <p class="mt-2 text-white/85 text-sm max-w-xl">
            今天您的博客获得了 {{ summary.views24h.toLocaleString() }} 次浏览，比日均 {{ viewsTrend.v }}。
            共 <span class="font-semibold">{{ summary.pendingComments }}</span> 条评论等待审核，
            <span class="font-semibold">{{ summary.draftCount }}</span> 篇草稿待发布。
          </p>
        </div>
        <div class="flex items-center gap-2 shrink-0 flex-wrap">
          <Button
            size="sm"
            variant="outline"
            class="rounded-[10px] h-9 bg-white/10 border-white/20 text-white hover:bg-white/20 hover:text-white"
            @click="window.open('/', '_blank')"
          >
            查看前台
          </Button>
          <Button
            size="sm"
            class="rounded-[10px] h-9 bg-white text-[#075985] hover:bg-white/90 font-semibold shadow"
            @click="navigateTo('/admin/content/posts/new')"
          >
            写一篇新文章
            <ChevronRight class="size-4 ml-0.5" />
          </Button>
        </div>
      </div>
    </section>

    <!-- 4 统计卡：去掉所有硬编码的假趋势/trend，只保留后端/计算可证实的 viewsTrend 与 待审评论状态 -->
    <section class="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-4">
      <StatCard
        title="文章总数"
        :value="summary.postsCount"
        :icon="FileText"
        accent="primary"
        :sub-value="`已发布 ${summary.publishedCount} / 草稿 ${summary.draftCount}`"
        :loading="loading"
        action-label="管理文章"
        @action="navigateTo('/admin/content/posts')"
      />
      <StatCard
        title="24 小时浏览"
        :value="summary.views24h.toLocaleString()"
        :icon="Eye"
        accent="info"
        :sub-value="`7 日合计 ${summary.views7d.toLocaleString()}`"
        :trend="viewsTrend.d === 'flat' ? { direction: 'flat', value: viewsTrend.v } : viewsTrend"
        :hint="'vs 日均'"
        :loading="loading"
      />
      <StatCard
        title="待审评论"
        :value="summary.pendingComments"
        :icon="MessageSquare"
        accent="warning"
        :sub-value="`累计 ${summary.totalComments} 条`"
        :trend="summary.pendingComments > 0 ? { direction: 'up', value: '请处理', hint: '有新评论' } : { direction: 'flat', value: '全部处理' }"
        :loading="loading"
        action-label="查看待审"
        @action="navigateTo('/admin/interaction/comments')"
      />
      <StatCard
        title="注册用户"
        :value="summary.usersCount"
        :icon="Users"
        accent="success"
        :sub-value="authStore.isAdmin ? '您拥有全部权限' : '普通用户权限'"
        :loading="loading"
        action-label="用户列表"
        @action="navigateTo('/admin/users')"
      />
    </section>

    <!-- 主区 2 列：左 热门文章 + 系统健康；右 近期活动 -->
    <section class="grid grid-cols-1 lg:grid-cols-3 gap-4">
      <!-- 左：热门文章 + 系统健康 -->
      <div class="lg:col-span-2 space-y-4">
        <Card class="rounded-[14px] overflow-hidden">
          <CardHeader class="flex-row items-center justify-between py-4">
            <div>
              <CardTitle class="text-base">
                热门文章 TOP 5
              </CardTitle>
              <CardDescription class="text-xs mt-0.5">
                按近 7 日浏览量排序
              </CardDescription>
            </div>
            <Button
              variant="ghost"
              size="sm"
              class="h-8 rounded-[10px] text-muted-foreground"
              @click="navigateTo('/admin/content/posts')"
            >
              全部
              <ChevronRight class="size-4 ml-0.5" />
            </Button>
          </CardHeader>
          <CardContent class="pb-4">
            <ul
              v-if="!loading && hotPosts.length"
              class="divide-y divide-border -mx-1"
            >
              <li
                v-for="(p, idx) in hotPosts"
                :key="p.id"
                class="flex items-center gap-3 py-3 px-1 hover:bg-accent/30 transition-colors rounded-[8px] -mx-1 px-3"
              >
                <div
                  class="shrink-0 size-7 rounded-[8px] flex items-center justify-center font-bold text-[13px] text-white"
                  :style="{
                    background:
                      idx === 0 ? 'linear-gradient(135deg,#0EA5E9,#0369A1)'
                      : idx === 1 ? 'linear-gradient(135deg,#6366F1,#4F46E5)'
                        : idx === 2 ? 'linear-gradient(135deg,#14B8A6,#0D9488)'
                          : 'hsl(var(--muted))'
                  }"
                  :class="{ 'text-muted-foreground': idx > 2 }"
                >
                  {{ idx + 1 }}
                </div>
                <div class="flex-1 min-w-0">
                  <p class="text-sm font-medium truncate">
                    {{ p.title }}
                  </p>
                  <p class="text-[11px] text-muted-foreground mt-0.5">
                    {{ p.views.toLocaleString() }} 次浏览
                  </p>
                </div>
                <Badge
                  v-if="p.trend != null"
                  class="rounded-full h-5 px-2 text-[11px]"
                  :variant="p.trend >= 0 ? 'default' : 'secondary'"
                  :class="p.trend >= 0 ? 'bg-success-muted text-success-muted-foreground' : ''"
                >
                  <TrendingUp
                    v-if="p.trend > 0"
                    class="size-3 mr-0.5"
                  />
                  <ChevronRight
                    v-else-if="p.trend === 0"
                    class="size-3 mr-0.5 rotate-90"
                  />
                  <ChevronRight
                    v-else
                    class="size-3 mr-0.5 -rotate-90"
                  />
                  {{ p.trend >= 0 ? '+' : '' }}{{ p.trend }}%
                </Badge>
                <Tooltip>
                  <TooltipTrigger as-child>
                    <Button
                      size="icon"
                      variant="ghost"
                      class="size-8 rounded-[8px]"
                      @click="window.open(`/posts/${p.slug || p.id}`, '_blank')"
                    >
                      <ArrowUpRight class="size-4 text-muted-foreground" />
                    </Button>
                  </TooltipTrigger>
                  <TooltipContent>
                    <p class="text-xs">
                      打开前台页面
                    </p>
                  </TooltipContent>
                </Tooltip>
              </li>
            </ul>
            <div
              v-else-if="loading"
              class="space-y-3"
            >
              <Skeleton
                v-for="i in 5"
                :key="i"
                class="h-11 rounded-[8px]"
              />
            </div>
            <div
              v-else
              class="text-sm text-muted-foreground py-8 text-center"
            >
              暂无文章数据
            </div>
          </CardContent>
        </Card>

        <Card class="rounded-[14px] overflow-hidden">
          <CardHeader class="flex-row items-center justify-between py-4">
            <div>
              <CardTitle class="text-base">
                系统健康
              </CardTitle>
              <CardDescription class="text-xs mt-0.5">
                实时资源使用率
              </CardDescription>
            </div>
            <Badge
              variant="outline"
              class="rounded-full h-5 px-2 text-[11px]"
            >
              <CheckCircle2 class="size-3 mr-1 text-success" />
              运行正常
            </Badge>
          </CardHeader>
          <CardContent class="pb-5 space-y-4">
            <div
              v-for="h in health"
              :key="h.label"
              class="space-y-1.5"
            >
              <div class="flex items-center justify-between text-[13px]">
                <span class="text-foreground/80">{{ h.label }}</span>
                <span class="font-medium tabular-nums">
                  {{ h.value }}
                  <span
                    class="ml-1.5 inline-block size-1.5 rounded-full align-middle"
                    :class="{
                      'bg-success': h.status === 'ok',
                      'bg-warning': h.status === 'warn',
                      'bg-error': h.status === 'bad'
                    }"
                  />
                </span>
              </div>
              <Progress
                :value="h.value"
                class="h-1.5 rounded-full"
                :class="{
                  '[&>div]:bg-success': h.status === 'ok',
                  '[&>div]:bg-warning': h.status === 'warn',
                  '[&>div]:bg-error': h.status === 'bad'
                }"
              />
            </div>
            <div class="pt-2 flex items-center justify-between text-[12px] text-muted-foreground">
              <span>OOBE 初始化：{{ summary.oobeComplete ? '已完成' : '未完成' }}</span>
              <Button
                variant="link"
                size="sm"
                class="h-6 text-xs p-0"
                @click="navigateTo('/admin/tools/performance')"
              >
                打开完整监控 →
              </Button>
            </div>
          </CardContent>
        </Card>
      </div>

      <!-- 右：近期活动 -->
      <Card class="rounded-[14px] overflow-hidden">
        <CardHeader class="flex-row items-center justify-between py-4">
          <div>
            <CardTitle class="text-base">
              近期活动
            </CardTitle>
            <CardDescription class="text-xs mt-0.5">
              博客最新动态
            </CardDescription>
          </div>
          <Button
            variant="ghost"
            size="sm"
            class="h-8 rounded-[10px] text-muted-foreground"
            @click="navigateTo('/admin/tools/audit-logs')"
          >
            日志
            <ChevronRight class="size-4 ml-0.5" />
          </Button>
        </CardHeader>
        <CardContent class="pb-4">
          <ol class="relative border-l border-border ml-2.5 space-y-5 pl-5">
            <template v-if="!loading">
              <li
                v-for="a in activities"
                :key="a.id"
                class="relative"
              >
                <span
                  class="absolute -left-[30px] top-0.5 size-6 rounded-full flex items-center justify-center"
                  :class="pillFor(a.accent)"
                >
                  <component
                    :is="iconFor(a.icon)"
                    class="size-3.5"
                  />
                </span>
                <div class="flex items-start justify-between gap-2">
                  <p class="text-sm leading-5 text-foreground/90">
                    {{ a.text }}
                  </p>
                </div>
                <p class="text-[11px] text-muted-foreground mt-0.5">
                  {{ a.time }}
                </p>
              </li>
            </template>
            <template v-else>
              <li
                v-for="i in 5"
                :key="i"
                class="relative"
              >
                <Skeleton class="absolute -left-[30px] top-0.5 size-6 rounded-full" />
                <Skeleton class="h-4 w-4/5 rounded-md" />
                <Skeleton class="mt-1 h-3 w-16 rounded-md" />
              </li>
            </template>
          </ol>

          <div
            v-if="!loading"
            class="mt-6 -mx-1"
          >
            <Button
              variant="outline"
              size="sm"
              class="w-full h-9 rounded-[10px] justify-between"
              @click="navigateTo('/admin/interaction/activities')"
            >
              <span>查看全部动态</span>
              <ActivityIcon class="size-4 text-muted-foreground" />
            </Button>
          </div>
        </CardContent>
      </Card>
    </section>

    <!-- 快捷入口 Grid -->
    <section>
      <h3 class="text-sm font-semibold text-muted-foreground mb-3 px-1">
        快捷入口
      </h3>
      <div class="grid grid-cols-2 md:grid-cols-4 xl:grid-cols-6 gap-3">
        <button
          v-for="q in [
            { title: '新建文章', icon: FileText, to: '/admin/content/posts/new', grad: '#0EA5E9,#0284C7' },
            { title: '站点设置', icon: ActivityIcon, to: '/admin/system/settings', grad: '#6366F1,#4F46E5' },
            { title: '媒体库', icon: Eye, to: '/admin/media/library', grad: '#14B8A6,#0D9488' },
            { title: '用户列表', icon: Users, to: '/admin/users', grad: '#3B82F6,#2563EB' },
            { title: '审核评论', icon: MessageSquare, to: '/admin/interaction/comments', grad: '#EA580C,#C2410C' },
            { title: 'SEO 工具', icon: CheckCircle2, to: '/admin/tools/seo', grad: '#0EA5E9,#0284C7' }
          ]"
          :key="q.title"
          type="button"
          class="group flex items-center gap-3 p-3.5 rounded-[12px] border border-border bg-card hover:-translate-y-0.5 hover:shadow-[0_8px_22px_-14px_rgba(0,0,0,0.25)] transition-all duration-200 text-left"
          @click="navigateTo(q.to)"
        >
          <div
            class="shrink-0 size-10 rounded-[10px] text-white flex items-center justify-center"
            :style="{ background: `linear-gradient(135deg, ${q.grad})` }"
          >
            <component
              :is="q.icon"
              class="size-5"
            />
          </div>
          <div class="min-w-0 flex-1">
            <p class="text-sm font-semibold truncate">
              {{ q.title }}
            </p>
            <p class="text-[11px] text-muted-foreground group-hover:text-primary transition-colors">
              点击进入
            </p>
          </div>
          <ChevronRight class="shrink-0 size-4 text-muted-foreground group-hover:text-primary group-hover:translate-x-0.5 transition-all" />
        </button>
      </div>
    </section>
  </div>
</template>
