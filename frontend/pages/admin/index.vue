<script setup lang="ts">
import {
  Eye,
  Users,
  MessageSquare,
  FileText,
  ChevronRight,
  Activity as ActivityIcon,
  CheckCircle2,
  TrendingUp,
  TrendingDown,
  ArrowUpRight,
  LayoutDashboard,
  PencilLine,
  Settings,
  LibraryBig,
  ShieldCheck,
  Search,
  Sparkles,
  CalendarDays,
  MessageCircleMore,
  PenTool
} from '@lucide/vue'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '~~/components/ui/card'
import { Button } from '~~/components/ui/button'
import { Avatar, AvatarFallback, AvatarImage } from '~~/components/ui/avatar'
import { Badge } from '~~/components/ui/badge'
import { Skeleton } from '~~/components/ui/skeleton'
import { Tooltip, TooltipContent, TooltipTrigger } from '~~/components/ui/tooltip'
import { Tabs, TabsList, TabsTrigger } from '~~/components/ui/tabs'
import { useAuthStore } from '~~/stores/auth'
import { useToast } from '~~/composables/useToast'
import { useTheme } from '~~/composables/useTheme'
import { resolveAvatarUrl } from '~~/composables/useResolvedAvatar'
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
})

// ============== 基础依赖 ==============
const authStore = useAuthStore()
const { error: toastError } = useToast()
const { isDark } = useTheme()

// ============== 图表调色板（亮/暗自适应） ==============
const palette = computed(() => {
  if (isDark.value) {
    return {
      bg: 'transparent',
      text: '#CBD5E1',
      textSoft: '#64748B',
      border: '#1E293B',
      gridLine: '#1E293B',
      primary: '#38BDF8', // sky-400
      primaryLight: 'rgba(56,189,248,0.25)',
      indigo: '#818CF8', // indigo-400
      indigoLight: 'rgba(129,140,248,0.22)',
      teal: '#2DD4BF', // teal-400
      tealLight: 'rgba(45,212,191,0.22)',
      amber: '#FBBF24', // amber-400
      amberLight: 'rgba(251,191,36,0.22)',
      rose: '#FB7185', // rose-400
      roseLight: 'rgba(251,113,133,0.22)',
      success: '#34D399',
      warning: '#FBBF24',
      danger: '#F87171',
      tooltipBg: '#0F172A',
      tooltipBorder: '#334155'
    }
  }
  return {
    bg: 'transparent',
    text: '#0F172A',
    textSoft: '#64748B',
    border: '#E2E8F0',
    gridLine: '#F1F5F9',
    primary: '#0284C7', // sky-600
    primaryLight: 'rgba(14,165,233,0.18)',
    indigo: '#4F46E5', // indigo-600
    indigoLight: 'rgba(99,102,241,0.15)',
    teal: '#0D9488', // teal-600
    tealLight: 'rgba(20,184,166,0.14)',
    amber: '#D97706', // amber-600
    amberLight: 'rgba(245,158,11,0.14)',
    rose: '#E11D48', // rose-600
    roseLight: 'rgba(225,29,72,0.12)',
    success: '#059669',
    warning: '#D97706',
    danger: '#DC2626',
    tooltipBg: '#FFFFFF',
    tooltipBorder: '#E2E8F0'
  }
})

// ============== 状态 ==============
const loading = ref(true)
const statsRange = ref<StatsRange>('7d')
const statsRaw = ref<DashboardStats | null>(null)

type SystemHealthShape = {
  cpu_percent?: number | null
  memory_percent?: number | null
  db_rtt_ms?: number | null
  cache_hit_percent?: number | null
  health_score?: number | null
}

type ActivityItem = {
  id: number
  icon: 'post' | 'comment' | 'user' | 'system' | 'alert'
  text: string
  time: string
  accent: 'primary' | 'success' | 'warning' | 'info' | 'error'
}
const activities = ref<ActivityItem[]>([])

// ============== 工具：相对时间 ==============
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

// ============== 通用动作 ==============
function openHomepage() {
  if (import.meta.client) {
    window.open('/', '_blank')
  }
}

// ============== 加载数据 ==============
async function loadAll() {
  loading.value = true
  try {
    statsRaw.value = await fetchDashboardStats(statsRange.value)
    const s = statsRaw.value.summary
    const pvSeries = statsRaw.value.timeseries.datasets.find(d => d.key === 'pv')?.values ?? []
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
      totalCommentsToday: s.total_comments_today ?? 0,
      oobeComplete: true
    }

    // 衍生：近 7/30 天总量与前一半环比
    rangeRingback.value = calcRingback()

    // Top articles / commenters / health 直接走原始引用
    // 活动时间线（最近文章 + 待审评论 + 动态）
    try {
      const [postsRes, commentsRes, actRes] = await Promise.allSettled([
        fetchRecentPosts(5),
        fetchAdminComments({ page: 1, page_size: 5, status: 'pending' }).catch(
          () => null as unknown as { items: AdminComment[] }
        ),
        fetchAdminActivities({ page: 1, page_size: 5 }).catch(
          () => null as unknown as { items: AdminActivity[] }
        )
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

      if (
        commentsRes.status === 'fulfilled'
        && commentsRes.value
        && Array.isArray((commentsRes.value as { items: AdminComment[] }).items)
      ) {
        for (const c of (commentsRes.value as { items: AdminComment[] }).items.slice(0, 3)) {
          merged.push({
            id: 20000 + Number(c.id),
            icon: 'comment',
            text: `新评论待审核：来自「${c.author_name}」`,
            time: timeAgo(c.created_at),
            accent: 'warning'
          })
        }
      }

      if (
        actRes.status === 'fulfilled'
        && actRes.value
        && Array.isArray((actRes.value as { items: AdminActivity[] }).items)
      ) {
        let fallbackSeq = 0
        for (const a of (actRes.value as { items: AdminActivity[] }).items.slice(0, 3)) {
          const content: string
            = (a as unknown as { content?: string }).content
              ?? (a as unknown as { text?: string }).text
              ?? (a as unknown as { message?: string }).message
              ?? '发布了新动态'
          fallbackSeq += 1
          const idN = Number((a as unknown as { id?: number | string }).id)
          merged.push({
            id: Number.isFinite(idN) && idN > 0 ? 30000 + idN : 3000000 + fallbackSeq,
            icon: 'system',
            text: content.slice(0, 60),
            time: timeAgo((a as unknown as { created_at?: string }).created_at),
            accent: 'primary'
          })
        }
      }

      merged.sort((x, y) => y.id - x.id)
      activities.value = merged.slice(0, 6)
    } catch {
      activities.value = []
    }
  } catch (e: unknown) {
    const msg
      = typeof e === 'object' && e !== null && 'message' in e ? String((e as { message: unknown }).message) : ''
    toastError(msg || '仪表盘数据加载失败')
    activities.value = []
  } finally {
    loading.value = false
  }
}

onMounted(loadAll)
watch(statsRange, loadAll)

// ============== 派生 state ==============
type DashSummary = {
  postsCount: number
  publishedCount: number
  draftCount: number
  views24h: number
  views7d: number
  usersCount: number
  pendingComments: number
  totalComments: number
  totalCommentsToday: number
  oobeComplete: boolean
}
const summary = ref<DashSummary>({
  postsCount: 0,
  publishedCount: 0,
  draftCount: 0,
  views24h: 0,
  views7d: 0,
  usersCount: 0,
  pendingComments: 0,
  totalComments: 0,
  totalCommentsToday: 0,
  oobeComplete: true
})

// 环比计算：后半段总和 vs 前半段
type Ringback = Record<string, { delta: number, pct: string, dir: 'up' | 'down' | 'flat' }>
const rangeRingback = ref<Ringback>({})
function calcRingback(): Ringback {
  const out: Ringback = {}
  if (!statsRaw.value) return out
  for (const ds of statsRaw.value.timeseries.datasets) {
    const arr = ds.values as number[]
    const n = arr.length
    if (n < 2) {
      out[ds.key] = { delta: 0, pct: '+0%', dir: 'flat' }
      continue
    }
    const mid = Math.floor(n / 2)
    const first = arr.slice(0, mid).reduce((a, b) => a + b, 0)
    const second = arr.slice(mid).reduce((a, b) => a + b, 0)
    const delta = second - first
    const pctFloat = first === 0 ? 0 : (delta / first) * 100
    const pct = `${pctFloat >= 0 ? '+' : ''}${pctFloat.toFixed(1)}%`
    out[ds.key] = {
      delta,
      pct,
      dir: Math.abs(pctFloat) < 0.5 ? 'flat' : pctFloat > 0 ? 'up' : 'down'
    }
  }
  return out
}

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
const weekday = computed(() => {
  const arr = ['周日', '周一', '周二', '周三', '周四', '周五', '周六']
  return arr[new Date().getDay()]
})

// ============== KPI 卡片定义（迷你 sparkline） ==============
type SparkSeries = 'pv' | 'uv' | 'comments' | 'posts' | 'users'
type KpiCardDef = {
  key: string
  title: string
  accent: 'primary' | 'indigo' | 'teal' | 'amber' | 'rose' | 'success'
  icon: typeof FileText
  value: () => number | string
  sub: () => string
  spark?: SparkSeries
  action?: { label: string, to: string }
  trend?: { v: string, dir: 'up' | 'down' | 'flat', hint: string }
}

const kpiCards = computed<KpiCardDef[]>(() => {
  const s = summary.value
  const rb = rangeRingback.value
  const avg7 = s.views7d / Math.max(1, statsRange.value === '30d' ? 30 : 7)
  const pvDiff = avg7 === 0 ? 0 : ((s.views24h - avg7) / avg7) * 100
  const pvPct = `${pvDiff >= 0 ? '+' : ''}${pvDiff.toFixed(1)}%`
  const pvDir: 'up' | 'down' | 'flat'
    = Math.abs(pvDiff) < 0.5 ? 'flat' : pvDiff > 0 ? 'up' : 'down'

  const cards: KpiCardDef[] = [
    {
      key: 'posts',
      title: '文章总数',
      accent: 'primary',
      icon: FileText,
      value: () => s.postsCount.toLocaleString(),
      sub: () => `已发布 ${s.publishedCount} · 草稿 ${s.draftCount}`,
      spark: 'posts',
      trend: rb.posts ? { v: rb.posts.pct, dir: rb.posts.dir, hint: '环比上期' } : undefined,
      action: { label: '管理', to: '/admin/content/posts' }
    },
    {
      key: 'views',
      title: '今日浏览 (PV)',
      accent: 'indigo',
      icon: Eye,
      value: () => s.views24h.toLocaleString(),
      sub: () => `${statsRange.value === '30d' ? '30' : '7'} 日合计 ${s.views7d.toLocaleString()}`,
      spark: 'pv',
      trend: { v: pvPct, dir: pvDir, hint: 'vs 日均' }
    },
    {
      key: 'uv',
      title: '独立访客 (UV)',
      accent: 'teal',
      icon: Users,
      value: () => {
        const uv = statsRaw.value?.timeseries.datasets.find(d => d.key === 'uv')?.values ?? []
        const last = uv.at(-1) ?? 0
        return Number(last).toLocaleString()
      },
      sub: () => {
        const uv = statsRaw.value?.timeseries.datasets.find(d => d.key === 'uv')?.values ?? []
        return `区间累计 ${uv.reduce<number>((a, b) => a + (Number(b) || 0), 0).toLocaleString()}`
      },
      spark: 'uv',
      trend: rb.uv ? { v: rb.uv.pct, dir: rb.uv.dir, hint: '环比上期' } : undefined
    },
    {
      key: 'comments',
      title: '待审评论',
      accent: 'amber',
      icon: MessageSquare,
      value: () => s.pendingComments.toLocaleString(),
      sub: () => `累计评论 ${s.totalComments} · 今日 ${s.totalCommentsToday}`,
      spark: 'comments',
      trend: {
        v: s.pendingComments > 0 ? '待处理' : '全部通过',
        dir: s.pendingComments > 0 ? 'up' : 'flat',
        hint: s.pendingComments > 0 ? '有新评论' : '状态健康'
      },
      action: { label: '审核', to: '/admin/interaction/comments' }
    },
    {
      key: 'users',
      title: '注册用户',
      accent: 'success',
      icon: Users,
      value: () => s.usersCount.toLocaleString(),
      sub: () => {
        const u = statsRaw.value?.timeseries.datasets.find(d => d.key === 'users')?.values ?? []
        const newUsers = u.reduce<number>((a, b) => a + (Number(b) || 0), 0)
        return `区间新增 ${newUsers.toLocaleString()}`
      },
      spark: 'users',
      trend: rb.users ? { v: rb.users.pct, dir: rb.users.dir, hint: '环比上期' } : undefined,
      action: { label: '用户', to: '/admin/users' }
    },
    {
      key: 'drafts',
      title: '待发布草稿',
      accent: 'rose',
      icon: PencilLine,
      value: () => s.draftCount.toLocaleString(),
      sub: () =>
        s.postsCount > 0
          ? `占比 ${((s.draftCount / s.postsCount) * 100).toFixed(1)}%`
          : '暂无文章',
      action: { label: '新建', to: '/admin/content/posts/new' }
    }
  ]
  return cards
})

// ============== 各图表 computed options ==============

// 基础 grid / tooltip 样式（根据 palette）
const _commonTextStyle = computed(() => ({
  color: palette.value.text,
  fontFamily: 'Inter, "PingFang SC", "Hiragino Sans GB", "Microsoft YaHei", system-ui, sans-serif',
  fontSize: 12
}))

function shortDateLabels(raw: string[]): string[] {
  return raw.map((d) => {
    // YYYY-MM-DD -> M/D
    const parts = d.split('-')
    if (parts.length === 3) return `${Number(parts[1])}/${Number(parts[2])}`
    return d
  })
}

// 3.1 流量总览（PV/UV 面积线 + 发帖/评论/新用户 柱）—— 用 Tabs 切换显示 mode
const trafficMode = ref<'overview' | 'content'>('overview')

const trafficOption = computed(() => {
  if (!statsRaw.value) {
    return { grid: { show: false }, xAxis: { show: false }, yAxis: { show: false }, series: [] }
  }
  const P = palette.value
  const labels = shortDateLabels(statsRaw.value.timeseries.labels)
  const pv = statsRaw.value.timeseries.datasets.find(d => d.key === 'pv')?.values ?? []
  const uv = statsRaw.value.timeseries.datasets.find(d => d.key === 'uv')?.values ?? []
  const comments = statsRaw.value.timeseries.datasets.find(d => d.key === 'comments')?.values ?? []
  const posts = statsRaw.value.timeseries.datasets.find(d => d.key === 'posts')?.values ?? []
  const users = statsRaw.value.timeseries.datasets.find(d => d.key === 'users')?.values ?? []

  if (trafficMode.value === 'overview') {
    // PV / UV 双面积折线
    return {
      animationDuration: 800,
      animationEasing: 'cubicOut',
      color: [P.primary, P.indigo],
      grid: { left: 52, right: 24, top: 44, bottom: 48 },
      legend: {
        top: 8,
        right: 12,
        itemWidth: 10,
        itemHeight: 10,
        itemGap: 18,
        textStyle: { color: P.textSoft, fontSize: 12 }
      },
      tooltip: {
        trigger: 'axis',
        backgroundColor: P.tooltipBg,
        borderColor: P.tooltipBorder,
        borderWidth: 1,
        padding: [10, 12],
        textStyle: { color: P.text, fontSize: 12 },
        axisPointer: {
          type: 'line',
          lineStyle: { color: P.primary, type: 'dashed', opacity: 0.5 }
        }
      },
      dataZoom: [
        {
          type: 'inside',
          start: 0,
          end: 100,
          zoomOnMouseWheel: false,
          moveOnMouseWheel: true,
          moveOnMouseMove: true
        }
      ],
      xAxis: {
        type: 'category',
        data: labels,
        boundaryGap: false,
        axisLine: { lineStyle: { color: P.border } },
        axisLabel: { color: P.textSoft, fontSize: 11 },
        axisTick: { show: false }
      },
      yAxis: {
        type: 'value',
        splitLine: { lineStyle: { color: P.gridLine, type: 'dashed' } },
        axisLabel: { color: P.textSoft, fontSize: 11 },
        axisLine: { show: false },
        axisTick: { show: false }
      },
      series: [
        {
          name: '浏览量 (PV)',
          type: 'line',
          smooth: 0.4,
          symbol: 'circle',
          symbolSize: 6,
          showSymbol: false,
          emphasis: { focus: 'series', scale: 1.3 },
          lineStyle: { width: 2.5, color: P.primary },
          itemStyle: { color: P.primary, borderColor: '#fff', borderWidth: 1.5 },
          areaStyle: {
            opacity: 0.9,
            color: {
              type: 'linear',
              x: 0, y: 0, x2: 0, y2: 1,
              colorStops: [
                { offset: 0, color: P.primaryLight },
                { offset: 1, color: 'rgba(14,165,233,0.02)' }
              ]
            }
          },
          data: pv
        },
        {
          name: '独立访客 (UV)',
          type: 'line',
          smooth: 0.4,
          symbol: 'circle',
          symbolSize: 5,
          showSymbol: false,
          emphasis: { focus: 'series', scale: 1.3 },
          lineStyle: { width: 2.2, color: P.indigo, type: 'solid' },
          itemStyle: { color: P.indigo, borderColor: '#fff', borderWidth: 1.5 },
          areaStyle: {
            opacity: 0.8,
            color: {
              type: 'linear',
              x: 0, y: 0, x2: 0, y2: 1,
              colorStops: [
                { offset: 0, color: P.indigoLight },
                { offset: 1, color: 'rgba(99,102,241,0.02)' }
              ]
            }
          },
          data: uv
        }
      ]
    }
  }

  // 内容互动：评论 / 发帖 / 新注册 分组柱
  return {
    animationDuration: 800,
    animationEasing: 'cubicOut',
    color: [P.teal, P.amber, P.rose],
    grid: { left: 52, right: 24, top: 44, bottom: 48 },
    legend: {
      top: 8,
      right: 12,
      itemWidth: 10,
      itemHeight: 10,
      itemGap: 18,
      textStyle: { color: P.textSoft, fontSize: 12 }
    },
    tooltip: {
      trigger: 'axis',
      backgroundColor: P.tooltipBg,
      borderColor: P.tooltipBorder,
      borderWidth: 1,
      padding: [10, 12],
      textStyle: { color: P.text, fontSize: 12 },
      axisPointer: {
        type: 'shadow',
        shadowStyle: { color: P.text, opacity: 0.04 }
      }
    },
    dataZoom: [
      { type: 'inside', start: 0, end: 100, zoomOnMouseWheel: false, moveOnMouseWheel: true, moveOnMouseMove: true }
    ],
    xAxis: {
      type: 'category',
      data: labels,
      axisLine: { lineStyle: { color: P.border } },
      axisLabel: { color: P.textSoft, fontSize: 11 },
      axisTick: { show: false }
    },
    yAxis: {
      type: 'value',
      splitLine: { lineStyle: { color: P.gridLine, type: 'dashed' } },
      axisLabel: { color: P.textSoft, fontSize: 11 },
      axisLine: { show: false },
      axisTick: { show: false }
    },
    series: [
      {
        name: '评论',
        type: 'bar',
        barWidth: 8,
        barGap: '30%',
        itemStyle: {
          borderRadius: [4, 4, 0, 0],
          color: {
            type: 'linear', x: 0, y: 0, x2: 0, y2: 1,
            colorStops: [
              { offset: 0, color: P.teal },
              { offset: 1, color: P.tealLight }
            ]
          }
        },
        emphasis: { itemStyle: { shadowBlur: 10, shadowColor: P.tealLight } },
        data: comments
      },
      {
        name: '新发文',
        type: 'bar',
        barWidth: 8,
        itemStyle: {
          borderRadius: [4, 4, 0, 0],
          color: {
            type: 'linear', x: 0, y: 0, x2: 0, y2: 1,
            colorStops: [
              { offset: 0, color: P.amber },
              { offset: 1, color: P.amberLight }
            ]
          }
        },
        data: posts
      },
      {
        name: '新注册用户',
        type: 'bar',
        barWidth: 8,
        itemStyle: {
          borderRadius: [4, 4, 0, 0],
          color: {
            type: 'linear', x: 0, y: 0, x2: 0, y2: 1,
            colorStops: [
              { offset: 0, color: P.rose },
              { offset: 1, color: P.roseLight }
            ]
          }
        },
        data: users
      }
    ]
  }
})

// 3.2 内容结构环形图（已发布 / 草稿 / 待审评论 / 今日评论 / 新用户 按"运营核心对象"归一对比）
const contentDonutOption = computed(() => {
  const s = summary.value
  const P = palette.value
  const data = [
    { value: s.publishedCount, name: '已发布文章', color: P.primary },
    { value: s.draftCount, name: '草稿', color: P.amber },
    { value: s.totalComments - s.pendingComments, name: '已放行评论', color: P.teal },
    { value: s.pendingComments, name: '待审评论', color: P.rose },
    { value: s.usersCount, name: '注册用户', color: P.indigo }
  ].filter(d => d.value > 0)

  return {
    animationDuration: 900,
    color: data.map(d => d.color),
    tooltip: {
      trigger: 'item',
      backgroundColor: P.tooltipBg,
      borderColor: P.tooltipBorder,
      borderWidth: 1,
      padding: [10, 12],
      textStyle: { color: P.text, fontSize: 12 },
      formatter: (p: { name: string, value: number, percent?: number | string }) =>
        `<div style="font-weight:600;margin-bottom:4px">${p.name}</div>`
        + `<div style="display:flex;align-items:center;gap:8px">`
        + `<span style="font-weight:700;color:${P.text};font-size:14px">${Number(p.value).toLocaleString()}</span>`
        + `<span style="color:${P.textSoft};font-size:11px">${p.percent ?? 0}%</span></div>`
    },
    legend: {
      orient: 'vertical',
      right: 4,
      top: 'center',
      itemWidth: 9,
      itemHeight: 9,
      itemGap: 12,
      textStyle: { color: P.textSoft, fontSize: 11 }
    },
    series: [
      {
        name: '运营结构',
        type: 'pie',
        radius: ['58%', '82%'],
        center: ['32%', '50%'],
        avoidLabelOverlap: true,
        itemStyle: {
          borderRadius: 6,
          borderColor: P.bg === 'transparent' ? undefined : P.bg,
          borderWidth: 2
        },
        label: { show: false },
        labelLine: { show: false },
        emphasis: {
          scale: true,
          scaleSize: 6,
          itemStyle: { shadowBlur: 20, shadowColor: P.primaryLight }
        },
        data: data.map(d => ({
          name: d.name,
          value: d.value,
          itemStyle: { color: d.color }
        }))
      },
      // 装饰：中心空心文字
      {
        name: 'center',
        type: 'gauge',
        center: ['32%', '50%'],
        radius: '40%',
        startAngle: 0,
        endAngle: 360,
        pointer: { show: false },
        progress: { show: false },
        axisLine: { show: false },
        splitLine: { show: false },
        axisTick: { show: false },
        axisLabel: { show: false },
        title: {
          offsetCenter: [0, '-12%'],
          fontSize: 11,
          color: P.textSoft,
          fontWeight: 500
        },
        detail: {
          offsetCenter: [0, '20%'],
          fontSize: 20,
          fontWeight: 700,
          color: P.text,
          valueAnimation: true,
          formatter: (v: number) => Number(v).toLocaleString()
        },
        data: [
          {
            value: s.postsCount + s.totalComments + s.usersCount,
            name: '全站内容体量'
          }
        ]
      }
    ]
  }
})

// 4.1 Top 文章水平柱
const topArticlesOption = computed(() => {
  const P = palette.value
  const arts = (statsRaw.value?.top_articles ?? []).slice(0, 6)
  const titles = arts.map((a) => {
    const t = String(a.title || 'Untitled')
    return t.length > 22 ? `${t.slice(0, 21)}…` : t
  })
  const views = arts.map(a => a.views ?? 0)
  const comments = arts.map(a => a.comments_count ?? 0)

  return {
    animationDuration: 900,
    grid: { left: 8, right: 36, top: 24, bottom: 8, containLabel: true },
    tooltip: {
      trigger: 'axis',
      axisPointer: { type: 'shadow' },
      backgroundColor: P.tooltipBg,
      borderColor: P.tooltipBorder,
      borderWidth: 1,
      padding: [10, 12],
      textStyle: { color: P.text, fontSize: 12 }
    },
    legend: {
      top: 0,
      right: 0,
      itemWidth: 10,
      itemHeight: 10,
      itemGap: 14,
      textStyle: { color: P.textSoft, fontSize: 11 }
    },
    xAxis: {
      type: 'value',
      splitLine: { lineStyle: { color: P.gridLine, type: 'dashed' } },
      axisLabel: { color: P.textSoft, fontSize: 10 },
      axisLine: { show: false },
      axisTick: { show: false }
    },
    yAxis: {
      type: 'category',
      data: titles.reverse(),
      axisLabel: { color: P.text, fontSize: 11 },
      axisLine: { show: false },
      axisTick: { show: false }
    },
    series: [
      {
        name: '浏览量',
        type: 'bar',
        barWidth: 10,
        data: views.reverse(),
        itemStyle: {
          borderRadius: [0, 6, 6, 0],
          color: {
            type: 'linear', x: 0, y: 0, x2: 1, y2: 0,
            colorStops: [
              { offset: 0, color: 'rgba(14,165,233,0.25)' },
              { offset: 1, color: P.primary }
            ]
          }
        }
      },
      {
        name: '评论',
        type: 'bar',
        barWidth: 10,
        data: comments.reverse(),
        itemStyle: {
          borderRadius: [0, 6, 6, 0],
          color: {
            type: 'linear', x: 0, y: 0, x2: 1, y2: 0,
            colorStops: [
              { offset: 0, color: 'rgba(99,102,241,0.25)' },
              { offset: 1, color: P.indigo }
            ]
          }
        }
      }
    ]
  }
})

// 4.2 健康雷达 + 4.3 健康分数仪表
type HealthRow = {
  label: string
  value: number
  reversed?: boolean
}
const healthRows = computed<HealthRow[]>(() => {
  const h = (statsRaw.value?.system_health ?? {}) as SystemHealthShape
  const rows: HealthRow[] = []
  if (h.cpu_percent != null) rows.push({ label: 'CPU', value: Math.round(Number(h.cpu_percent)) })
  if (h.memory_percent != null)
    rows.push({ label: '内存', value: Math.round(Number(h.memory_percent)) })
  if (h.db_rtt_ms != null) {
    // RTT 越小越好 → 反向：0ms=100分，500ms=0分
    const rtt = Math.min(500, Math.max(0, Number(h.db_rtt_ms)))
    rows.push({ label: '数据库', value: Math.round(100 - (rtt / 500) * 100), reversed: true })
  }
  if (h.cache_hit_percent != null)
    rows.push({ label: '缓存', value: Math.round(Number(h.cache_hit_percent)) })
  if (rows.length < 4) {
    // 补齐 4 轴显示（用已存在的 + fallback: 空占位会变形，所以重复补齐第一项）
    while (rows.length < 4) rows.push(rows[0] ?? { label: 'N/A', value: 0 })
  }
  return rows
})

const healthRadarOption = computed(() => {
  const P = palette.value
  const rows = healthRows.value
  const indicators = rows.map(r => ({ name: r.label, max: 100 }))
  const data = rows.map(r => r.value)
  return {
    animationDuration: 800,
    tooltip: {
      backgroundColor: P.tooltipBg,
      borderColor: P.tooltipBorder,
      borderWidth: 1,
      padding: [10, 12],
      textStyle: { color: P.text, fontSize: 12 }
    },
    radar: {
      center: ['50%', '54%'],
      radius: '66%',
      indicator: indicators,
      shape: 'polygon',
      splitNumber: 4,
      axisName: {
        color: P.textSoft,
        fontSize: 10
      },
      splitLine: { lineStyle: { color: P.border } },
      splitArea: { areaStyle: { color: [P.gridLine, 'transparent'] } },
      axisLine: { lineStyle: { color: P.border } }
    },
    series: [
      {
        type: 'radar',
        symbol: 'circle',
        symbolSize: 5,
        data: [
          {
            value: data,
            name: '系统负载',
            lineStyle: { width: 2, color: P.primary },
            itemStyle: { color: P.primary },
            areaStyle: {
              color: {
                type: 'radial',
                x: 0.5, y: 0.5, r: 0.5,
                colorStops: [
                  { offset: 0, color: P.primaryLight },
                  { offset: 1, color: 'rgba(14,165,233,0.05)' }
                ]
              }
            }
          }
        ]
      }
    ]
  }
})

const healthGaugeOption = computed(() => {
  const P = palette.value
  const score = Math.round(Number((statsRaw.value?.system_health as SystemHealthShape)?.health_score ?? 0))
  const statusColor = score >= 85 ? P.success : score >= 60 ? P.warning : P.danger
  return {
    animationDuration: 1100,
    series: [
      {
        type: 'gauge',
        startAngle: 210,
        endAngle: -30,
        min: 0,
        max: 100,
        splitNumber: 5,
        radius: '92%',
        center: ['50%', '58%'],
        itemStyle: {
          color: statusColor,
          shadowColor: statusColor,
          shadowBlur: 12
        },
        progress: {
          show: true,
          width: 14,
          roundCap: true
        },
        pointer: { show: false },
        axisLine: {
          lineStyle: {
            width: 14,
            color: [[1, P.gridLine]]
          }
        },
        axisTick: { show: false },
        splitLine: {
          distance: -16,
          length: 8,
          lineStyle: { color: P.border, width: 2 }
        },
        axisLabel: {
          distance: -2,
          color: P.textSoft,
          fontSize: 10
        },
        anchor: { show: false },
        title: {
          offsetCenter: [0, '20%'],
          color: P.textSoft,
          fontSize: 11,
          fontWeight: 500
        },
        detail: {
          valueAnimation: true,
          offsetCenter: [0, '-5%'],
          fontSize: 28,
          fontWeight: 800,
          color: P.text,
          formatter: '{value}'
        },
        data: [{ value: score, name: '健康分数' }]
      }
    ]
  }
})

// 4.4 活跃评论者 Leaderboard：头像 + 进度条（无图表库，直接纯 UI，性能好）
type CommenterRow = { name: string, avatar: string | null, comments_count: number }
const commenters = computed<CommenterRow[]>(
  () => (statsRaw.value?.active_commenters ?? []) as CommenterRow[]
)
const commentersMax = computed(() => Math.max(1, ...commenters.value.map(c => Number(c.comments_count) || 0)))

// ============== 活动 timeline 渲染辅助 ==============
const iconFor = (t: ActivityItem['icon']) =>
  ({
    post: FileText,
    comment: MessageSquare,
    user: Users,
    system: ActivityIcon,
    alert: CheckCircle2
  })[t]
const pillFor = (a: ActivityItem['accent']) =>
  ({
    primary: 'bg-[#E0F2FE] text-[#0369A1] dark:bg-[#075985]/40 dark:text-[#BAE6FD]',
    success: 'bg-[#ECFDF5] text-[#065F46] dark:bg-[#064E3B]/40 dark:text-[#A7F3D0]',
    warning: 'bg-[#FEF9C3] text-[#854D0E] dark:bg-[#713F12]/40 dark:text-[#FDE68A]',
    info: 'bg-[#EFF6FF] text-[#1E40AF] dark:bg-[#1E3A8A]/40 dark:text-[#BFDBFE]',
    error: 'bg-[#FEF2F2] text-[#991B1B] dark:bg-[#7F1D1D]/40 dark:text-[#FECACA]'
  })[a]
</script>

<template>
  <div class="admin-dashboard-v2 space-y-5 py-1 animate-in">
    <!-- =============== HERO =============== -->
    <section
      class="relative overflow-hidden rounded-2xl p-6 md:p-7 text-white shadow-[0_22px_45px_-18px_rgba(14,165,233,0.55)] border border-white/10"
      style="background: radial-gradient(1200px 320px at 10% 0%, rgba(125,211,252,0.35) 0%, transparent 55%), linear-gradient(135deg,#0284C7 0%,#0369A1 45%,#0F172A 100%);"
    >
      <!-- decorative orbs -->
      <svg
        aria-hidden="true"
        viewBox="0 0 600 260"
        preserveAspectRatio="none"
        class="pointer-events-none absolute inset-0 w-full h-full opacity-60 mix-blend-screen"
      >
        <defs>
          <radialGradient
            id="orb1"
            cx="50%"
            cy="50%"
            r="50%"
          >
            <stop
              offset="0%"
              stop-color="#38BDF8"
              stop-opacity="0.45"
            />
            <stop
              offset="100%"
              stop-color="#38BDF8"
              stop-opacity="0"
            />
          </radialGradient>
          <radialGradient
            id="orb2"
            cx="50%"
            cy="50%"
            r="50%"
          >
            <stop
              offset="0%"
              stop-color="#818CF8"
              stop-opacity="0.35"
            />
            <stop
              offset="100%"
              stop-color="#818CF8"
              stop-opacity="0"
            />
          </radialGradient>
        </defs>
        <circle
          cx="120"
          cy="210"
          r="150"
          fill="url(#orb1)"
        />
        <circle
          cx="520"
          cy="-40"
          r="180"
          fill="url(#orb2)"
        />
        <circle
          cx="520"
          cy="130"
          r="82"
          fill="none"
          stroke="#fff"
          stroke-opacity="0.08"
          stroke-width="1"
          stroke-dasharray="3 5"
        />
        <circle
          cx="520"
          cy="130"
          r="54"
          fill="none"
          stroke="#fff"
          stroke-opacity="0.1"
          stroke-width="1"
        />
      </svg>

      <div class="relative flex flex-col md:flex-row md:items-stretch md:justify-between gap-6">
        <div class="min-w-0 flex-1">
          <p class="text-white/75 text-sm flex items-center gap-2">
            <CalendarDays class="size-4 opacity-80" />
            {{ today }} · {{ weekday }} · {{ greeting }}，
            <span class="font-semibold">{{ authStore.user?.nickname || authStore.user?.username || '管理员' }}</span>
          </p>
          <h1 class="mt-2 font-display font-bold text-2xl md:text-[30px] tracking-tight leading-[1.2]">
            Rosetta 控制台 <span class="text-sky-300">·</span> 一切尽在掌握
          </h1>
          <p class="mt-2 text-white/80 text-sm max-w-2xl leading-relaxed">
            今日博客获
            <span class="font-semibold text-white">{{ summary.views24h.toLocaleString() }}</span>
            次浏览 ·
            <span class="font-semibold text-white">{{ summary.totalCommentsToday }}</span>
            条新评论 ·
            <span class="font-semibold text-white">{{ summary.pendingComments }}</span>
            条评论等待审核 ·
            <span class="font-semibold text-white">{{ summary.draftCount }}</span>
            篇草稿待发布。
          </p>
          <div class="mt-5 flex items-center gap-2.5 flex-wrap">
            <Button
              size="sm"
              class="h-9 rounded-xl bg-white text-[#075985] hover:bg-white/90 font-semibold shadow-lg shadow-black/10"
              @click="navigateTo('/admin/content/posts/new')"
            >
              <PencilLine class="size-4 mr-1" />
              写一篇新文章
            </Button>
            <Button
              size="sm"
              variant="outline"
              class="h-9 rounded-xl bg-white/10 border-white/20 text-white hover:bg-white/20 hover:text-white backdrop-blur"
              @click="openHomepage"
            >
              <LayoutDashboard class="size-4 mr-1" />
              查看前台
            </Button>
            <Button
              size="sm"
              variant="outline"
              class="h-9 rounded-xl bg-white/5 border-white/15 text-white/90 hover:bg-white/15 hover:text-white backdrop-blur"
              @click="navigateTo('/admin/tools/seo')"
            >
              <Search class="size-4 mr-1" />
              SEO 工作台
            </Button>
          </div>
        </div>

        <!-- Hero 右侧：环形迷你总览 -->
        <div class="relative shrink-0 grid grid-cols-3 gap-3 md:w-[380px]">
          <div
            v-for="tile in [
              {
                label: '已发布',
                value: summary.publishedCount,
                grad: 'from-sky-300/30 to-sky-500/30',
                ring: 'ring-sky-300/40'
              },
              {
                label: '今日评论',
                value: summary.totalCommentsToday,
                grad: 'from-indigo-300/30 to-indigo-500/30',
                ring: 'ring-indigo-300/40'
              },
              {
                label: '注册用户',
                value: summary.usersCount,
                grad: 'from-teal-300/30 to-teal-500/30',
                ring: 'ring-teal-300/40'
              }
            ]"
            :key="tile.label"
            class="relative rounded-xl p-3.5 bg-white/5 backdrop-blur ring-1 ring-inset border border-white/10"
            :class="tile.ring"
          >
            <div
              class="absolute inset-0 rounded-xl bg-gradient-to-br opacity-60 pointer-events-none"
              :class="tile.grad"
            />
            <p class="relative text-[11px] text-white/70">
              {{ tile.label }}
            </p>
            <p class="relative mt-1 text-2xl font-bold tabular-nums tracking-tight text-white drop-shadow-sm">
              {{ Number(tile.value).toLocaleString() }}
            </p>
          </div>
          <div
            class="col-span-3 rounded-xl p-3.5 bg-black/15 backdrop-blur border border-white/10 flex items-center justify-between"
          >
            <div class="min-w-0">
              <p class="text-[11px] text-white/70">
                健康分数
              </p>
              <p class="mt-0.5 text-3xl font-bold tabular-nums tracking-tight">
                {{ Number(statsRaw?.system_health.health_score ?? 0) }}
                <span class="text-sm font-semibold text-white/70 ml-0.5">/ 100</span>
              </p>
            </div>
            <div class="shrink-0 flex items-center gap-2">
              <Badge
                variant="outline"
                class="rounded-full border-white/30 text-white/90 bg-white/5 backdrop-blur"
              >
                <CheckCircle2 class="size-3 mr-1" />
                实时监控
              </Badge>
            </div>
          </div>
        </div>
      </div>
    </section>

    <!-- =============== 6 KPI CARDS =============== -->
    <section class="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-3 2xl:grid-cols-6 gap-4">
      <div
        v-for="card in kpiCards"
        :key="card.key"
        class="group relative rounded-2xl bg-card border border-border/70 hover:border-primary/30 hover:-translate-y-0.5 transition-all duration-200 overflow-hidden shadow-sm hover:shadow-[0_12px_30px_-16px_rgba(14,165,233,0.35)]"
      >
        <!-- subtle accent glow -->
        <div
          aria-hidden="true"
          class="pointer-events-none absolute -top-16 -right-14 size-40 rounded-full opacity-30 blur-3xl transition-opacity group-hover:opacity-60"
          :class="{
            'bg-primary/50': card.accent === 'primary',
            'bg-indigo-500/50': card.accent === 'indigo',
            'bg-teal-500/50': card.accent === 'teal',
            'bg-amber-500/50': card.accent === 'amber',
            'bg-rose-500/50': card.accent === 'rose',
            'bg-emerald-500/50': card.accent === 'success'
          }"
        />

        <div class="relative p-4 pb-3.5">
          <div class="flex items-start justify-between gap-3">
            <div
              class="shrink-0 size-10 rounded-xl flex items-center justify-center text-white shadow-sm"
              :class="{
                'bg-gradient-to-br from-sky-500 to-sky-600': card.accent === 'primary',
                'bg-gradient-to-br from-indigo-500 to-indigo-600': card.accent === 'indigo',
                'bg-gradient-to-br from-teal-500 to-teal-600': card.accent === 'teal',
                'bg-gradient-to-br from-amber-500 to-amber-600': card.accent === 'amber',
                'bg-gradient-to-br from-rose-500 to-rose-600': card.accent === 'rose',
                'bg-gradient-to-br from-emerald-500 to-emerald-600': card.accent === 'success'
              }"
            >
              <component
                :is="card.icon"
                class="size-5"
              />
            </div>
            <div
              v-if="card.trend"
              class="flex items-center gap-0.5 text-[11px] font-medium tabular-nums rounded-full px-2 py-0.5"
              :class="{
                'bg-emerald-50 text-emerald-700 dark:bg-emerald-500/10 dark:text-emerald-400':
                  card.trend.dir === 'up' && card.accent !== 'amber',
                'bg-amber-50 text-amber-700 dark:bg-amber-500/10 dark:text-amber-400':
                  card.trend.dir === 'up' && card.accent === 'amber',
                'bg-rose-50 text-rose-700 dark:bg-rose-500/10 dark:text-rose-400':
                  card.trend.dir === 'down',
                'bg-slate-50 text-slate-600 dark:bg-slate-500/10 dark:text-slate-400':
                  card.trend.dir === 'flat'
              }"
            >
              <TrendingUp
                v-if="card.trend.dir === 'up'"
                class="size-3 mr-0.5"
              />
              <TrendingDown
                v-else-if="card.trend.dir === 'down'"
                class="size-3 mr-0.5"
              />
              <span
                v-else
                class="inline-block size-3 mr-0.5 rounded-full bg-current opacity-70 align-middle"
              />
              {{ card.trend.v }}
            </div>
          </div>

          <p class="mt-3 text-[12.5px] text-muted-foreground">
            {{ card.title }}
          </p>
          <p class="mt-1 text-2xl font-bold tracking-tight tabular-nums leading-tight">
            {{ loading ? '—' : card.value() }}
          </p>
          <p class="mt-0.5 text-[11.5px] text-muted-foreground truncate">
            {{ loading ? '加载中…' : card.sub() }}
          </p>

          <!-- 迷你 sparkline -->
          <div
            v-if="card.spark && !loading"
            class="mt-3 -mx-1 h-12"
          >
            <v-chart
              autoresize
              :option="{
                grid: { left: 0, right: 0, top: 4, bottom: 0 },
                xAxis: {
                  type: 'category',
                  show: false,
                  boundaryGap: false,
                  data: (statsRaw?.timeseries.labels ?? []).map(() => '')
                },
                yAxis: { type: 'value', show: false },
                tooltip: {
                  trigger: 'axis',
                  show: true,
                  backgroundColor: palette.tooltipBg,
                  borderColor: palette.tooltipBorder,
                  textStyle: { color: palette.text, fontSize: 11 }
                },
                series: [
                  {
                    type: 'line',
                    smooth: true,
                    symbol: 'none',
                    lineStyle: {
                      width: 2,
                      color:
                        card.accent === 'primary' ? palette.primary
                        : card.accent === 'indigo' ? palette.indigo
                          : card.accent === 'teal' ? palette.teal
                            : card.accent === 'amber' ? palette.amber
                              : card.accent === 'rose' ? palette.rose
                                : palette.success
                    },
                    areaStyle: {
                      opacity: 0.9,
                      color: {
                        type: 'linear',
                        x: 0,
                        y: 0,
                        x2: 0,
                        y2: 1,
                        colorStops: [
                          {
                            offset: 0,
                            color:
                              card.accent === 'primary' ? palette.primaryLight
                              : card.accent === 'indigo' ? palette.indigoLight
                                : card.accent === 'teal' ? palette.tealLight
                                  : card.accent === 'amber' ? palette.amberLight
                                    : card.accent === 'rose' ? palette.roseLight
                                      : 'rgba(16,185,129,0.22)'
                          },
                          { offset: 1, color: 'rgba(0,0,0,0)' }
                        ]
                      }
                    },
                    data:
                      statsRaw?.timeseries.datasets.find((d) => d.key === card.spark)?.values ?? []
                  }
                ]
              }"
            />
          </div>
          <div
            v-else-if="loading"
            class="mt-3 h-12"
          >
            <Skeleton class="h-full w-full rounded-lg" />
          </div>

          <div
            v-if="card.action"
            class="mt-2 -mx-0.5 flex items-center justify-between"
          >
            <span class="text-[11px] text-muted-foreground">
              {{ card.trend?.hint || '' }}
            </span>
            <Button
              variant="ghost"
              size="sm"
              class="h-7 px-2 rounded-lg text-[11.5px] text-muted-foreground hover:text-primary group/act"
              @click="navigateTo(card.action!.to)"
            >
              {{ card.action.label }}
              <ChevronRight class="size-3.5 ml-0.5 opacity-70 group-hover/act:translate-x-0.5 transition-transform" />
            </Button>
          </div>
        </div>
      </div>
    </section>

    <!-- =============== 主图表区 Row 1 =============== -->
    <section class="grid grid-cols-1 xl:grid-cols-12 gap-4">
      <!-- Traffic Overview (col 8/12) -->
      <Card class="xl:col-span-8 rounded-2xl overflow-hidden border-border/60 shadow-sm">
        <CardHeader class="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 py-4">
          <div>
            <CardTitle class="text-[15px] flex items-center gap-2">
              <Sparkles class="size-4 text-primary" />
              流量与互动趋势
            </CardTitle>
            <CardDescription class="text-xs mt-0.5">
              {{ statsRange === '7d' ? '最近 7 天' : '最近 30 天' }} · 时间序列分析
            </CardDescription>
          </div>
          <div class="flex items-center gap-3 flex-wrap">
            <Tabs
              :model-value="trafficMode"
              class="w-auto"
              @update:model-value="(v: any) => trafficMode = String(v) as 'overview' | 'content'"
            >
              <TabsList class="h-8 rounded-lg">
                <TabsTrigger
                  value="overview"
                  class="h-7 px-3 text-xs data-[state=active]:shadow-sm"
                >
                  <Eye class="size-3.5 mr-1" />
                  流量总览
                </TabsTrigger>
                <TabsTrigger
                  value="content"
                  class="h-7 px-3 text-xs data-[state=active]:shadow-sm"
                >
                  <MessageCircleMore class="size-3.5 mr-1" />
                  互动 & 内容
                </TabsTrigger>
              </TabsList>
            </Tabs>
            <div class="inline-flex rounded-lg border border-border overflow-hidden">
              <button
                type="button"
                class="h-8 px-3 text-xs transition-colors"
                :class="
                  statsRange === '7d'
                    ? 'bg-primary text-primary-foreground font-semibold'
                    : 'hover:bg-accent text-muted-foreground'
                "
                @click="statsRange = '7d'"
              >
                7 天
              </button>
              <button
                type="button"
                class="h-8 px-3 text-xs transition-colors"
                :class="
                  statsRange === '30d'
                    ? 'bg-primary text-primary-foreground font-semibold'
                    : 'hover:bg-accent text-muted-foreground'
                "
                @click="statsRange = '30d'"
              >
                30 天
              </button>
            </div>
          </div>
        </CardHeader>
        <CardContent class="pt-0 pb-4">
          <div class="h-[360px] -mx-2">
            <Skeleton
              v-if="loading"
              class="h-full w-full rounded-xl"
            />
            <v-chart
              v-else
              autoresize
              :option="trafficOption"
              class="h-full w-full"
            />
          </div>
        </CardContent>
      </Card>

      <!-- Content Donut (col 4/12) -->
      <Card class="xl:col-span-4 rounded-2xl overflow-hidden border-border/60 shadow-sm">
        <CardHeader class="flex-row items-center justify-between py-4">
          <div>
            <CardTitle class="text-[15px]">
              内容构成
            </CardTitle>
            <CardDescription class="text-xs mt-0.5">
              核心运营对象占比总览
            </CardDescription>
          </div>
          <Badge
            variant="outline"
            class="rounded-full h-5 px-2 text-[11px]"
          >
            <ActivityIcon class="size-3 mr-1 text-primary" />
            Live
          </Badge>
        </CardHeader>
        <CardContent class="pt-0 pb-3">
          <div class="h-[360px] -mx-2">
            <Skeleton
              v-if="loading"
              class="h-full w-full rounded-xl"
            />
            <v-chart
              v-else
              autoresize
              :option="contentDonutOption"
              class="h-full w-full"
            />
          </div>
        </CardContent>
      </Card>
    </section>

    <!-- =============== 主图表区 Row 2 =============== -->
    <section class="grid grid-cols-1 xl:grid-cols-12 gap-4">
      <!-- Top Articles (col 5/12) -->
      <Card class="xl:col-span-5 rounded-2xl overflow-hidden border-border/60 shadow-sm">
        <CardHeader class="flex-row items-center justify-between py-4">
          <div>
            <CardTitle class="text-[15px]">
              热门文章 TOP
            </CardTitle>
            <CardDescription class="text-xs mt-0.5">
              浏览量 · 评论数 排名
            </CardDescription>
          </div>
          <Tooltip>
            <TooltipTrigger as-child>
              <Button
                variant="ghost"
                size="sm"
                class="h-8 rounded-lg text-muted-foreground"
                @click="navigateTo('/admin/content/posts')"
              >
                更多
                <ArrowUpRight class="size-4 ml-0.5" />
              </Button>
            </TooltipTrigger>
            <TooltipContent>
              <p class="text-xs">
                打开文章管理
              </p>
            </TooltipContent>
          </Tooltip>
        </CardHeader>
        <CardContent class="pt-0 pb-3">
          <div class="h-[320px] -mx-2">
            <Skeleton
              v-if="loading"
              class="h-full w-full rounded-xl"
            />
            <v-chart
              v-else
              autoresize
              :option="topArticlesOption"
              class="h-full w-full"
            />
          </div>
        </CardContent>
      </Card>

      <!-- System Health: Radar + Gauge (col 4/12) -->
      <Card class="xl:col-span-4 rounded-2xl overflow-hidden border-border/60 shadow-sm">
        <CardHeader class="flex-row items-center justify-between py-4">
          <div>
            <CardTitle class="text-[15px]">
              系统健康
            </CardTitle>
            <CardDescription class="text-xs mt-0.5">
              CPU / 内存 / 数据库 / 缓存
            </CardDescription>
          </div>
          <Badge
            variant="outline"
            class="rounded-full h-5 px-2 text-[11px]"
            :class="
              Number(statsRaw?.system_health.health_score ?? 0) >= 85
                ? 'text-success border-success/30 bg-success/5'
                : Number(statsRaw?.system_health.health_score ?? 0) >= 60
                  ? 'text-warning border-warning/30 bg-warning/5'
                  : 'text-destructive border-destructive/30 bg-destructive/5'
            "
          >
            <CheckCircle2 class="size-3 mr-1" />
            在线
          </Badge>
        </CardHeader>
        <CardContent class="pt-0 pb-2">
          <Skeleton
            v-if="loading"
            class="h-[320px] w-full rounded-xl"
          />
          <div
            v-else
            class="grid grid-cols-1 md:grid-cols-2 gap-1 items-center"
          >
            <div class="h-[260px] -mx-1">
              <v-chart
                autoresize
                :option="healthRadarOption"
                class="h-full w-full"
              />
            </div>
            <div class="h-[260px] -mx-1 -my-3">
              <v-chart
                autoresize
                :option="healthGaugeOption"
                class="h-full w-full"
              />
            </div>
          </div>
          <div class="mt-1 grid grid-cols-2 gap-2 text-[11.5px]">
            <div
              v-for="r in healthRows"
              :key="r.label"
              class="flex items-center justify-between rounded-lg bg-accent/40 px-2.5 py-1.5"
            >
              <span class="text-muted-foreground">{{ r.label }}</span>
              <span
                class="font-semibold tabular-nums"
                :class="
                  (!r.reversed && r.value < 70) || (r.reversed && r.value < 60)
                    ? 'text-warning'
                    : 'text-success'
                "
              >
                {{ r.label === '数据库' && statsRaw?.system_health?.db_rtt_ms != null
                  ? `${Number(statsRaw.system_health.db_rtt_ms).toFixed(1)} ms`
                  : `${r.value}%` }}
              </span>
            </div>
          </div>
        </CardContent>
      </Card>

      <!-- Active Commenters (col 3/12) -->
      <Card class="xl:col-span-3 rounded-2xl overflow-hidden border-border/60 shadow-sm">
        <CardHeader class="flex-row items-center justify-between py-4">
          <div>
            <CardTitle class="text-[15px]">
              活跃评论者
            </CardTitle>
            <CardDescription class="text-xs mt-0.5">
              核心社区贡献者
            </CardDescription>
          </div>
          <Button
            variant="ghost"
            size="sm"
            class="h-8 rounded-lg text-muted-foreground"
            @click="navigateTo('/admin/users')"
          >
            社区
            <ChevronRight class="size-4 ml-0.5" />
          </Button>
        </CardHeader>
        <CardContent class="pt-0 pb-4">
          <template v-if="loading">
            <div class="space-y-3.5">
              <Skeleton
                v-for="i in 5"
                :key="i"
                class="h-12 rounded-xl"
              />
            </div>
          </template>
          <ul
            v-else-if="commenters.length"
            class="space-y-3.5"
          >
            <li
              v-for="(c, idx) in commenters"
              :key="c.name"
              class="flex items-center gap-3"
            >
              <div
                class="shrink-0 size-6 rounded-full flex items-center justify-center text-[11px] font-bold tabular-nums"
                :class="
                  idx === 0
                    ? 'bg-amber-100 text-amber-700 dark:bg-amber-500/20 dark:text-amber-400'
                    : idx === 1
                      ? 'bg-slate-100 text-slate-600 dark:bg-slate-500/20 dark:text-slate-300'
                      : idx === 2
                        ? 'bg-orange-100 text-orange-700 dark:bg-orange-500/20 dark:text-orange-400'
                        : 'bg-muted text-muted-foreground'
                "
              >
                {{ idx + 1 }}
              </div>
              <Avatar class="size-9 shrink-0 ring-2 ring-background shadow-sm">
                <AvatarImage
                  :src="resolveAvatarUrl(c.avatar)"
                  :alt="c.name"
                />
                <AvatarFallback class="text-xs font-semibold bg-primary/10 text-primary">
                  {{ c.name.slice(0, 1).toUpperCase() }}
                </AvatarFallback>
              </Avatar>
              <div class="flex-1 min-w-0">
                <div class="flex items-center justify-between">
                  <p class="text-sm font-medium truncate">
                    {{ c.name }}
                  </p>
                  <span class="text-xs font-semibold tabular-nums text-muted-foreground ml-2 shrink-0">
                    {{ c.comments_count }}
                  </span>
                </div>
                <div class="mt-1 h-1.5 w-full rounded-full bg-muted overflow-hidden">
                  <div
                    class="h-full rounded-full transition-all duration-700 ease-out"
                    :style="{
                      width: `${(Number(c.comments_count) / commentersMax) * 100}%`,
                      background:
                        idx === 0
                          ? 'linear-gradient(90deg,#F59E0B,#FBBF24)'
                          : idx === 1
                            ? 'linear-gradient(90deg,#64748B,#94A3B8)'
                            : idx === 2
                              ? 'linear-gradient(90deg,#EA580C,#FB923C)'
                              : 'linear-gradient(90deg,#0EA5E9,#38BDF8)'
                    }"
                  />
                </div>
              </div>
            </li>
          </ul>
          <div
            v-else
            class="text-sm text-muted-foreground py-10 text-center"
          >
            暂无数据
          </div>
        </CardContent>
      </Card>
    </section>

    <!-- =============== Row 3: 近期活动 + 快捷入口 =============== -->
    <section class="grid grid-cols-1 xl:grid-cols-12 gap-4">
      <Card class="xl:col-span-8 rounded-2xl overflow-hidden border-border/60 shadow-sm">
        <CardHeader class="flex-row items-center justify-between py-4">
          <div>
            <CardTitle class="text-[15px]">
              近期活动时间线
            </CardTitle>
            <CardDescription class="text-xs mt-0.5">
              文章 · 评论 · 系统动态
            </CardDescription>
          </div>
          <Button
            variant="ghost"
            size="sm"
            class="h-8 rounded-lg text-muted-foreground"
            @click="navigateTo('/admin/tools/audit-logs')"
          >
            审计日志
            <ChevronRight class="size-4 ml-0.5" />
          </Button>
        </CardHeader>
        <CardContent class="pt-0 pb-4">
          <ol class="relative border-l border-border ml-2.5 mt-2 space-y-5 pl-6">
            <template v-if="loading">
              <li
                v-for="i in 6"
                :key="i"
                class="relative"
              >
                <Skeleton class="absolute -left-[30px] top-0.5 size-6 rounded-full" />
                <Skeleton class="h-4 w-4/5 rounded-md" />
                <Skeleton class="mt-1 h-3 w-16 rounded-md" />
              </li>
            </template>
            <template v-else-if="activities.length">
              <li
                v-for="a in activities"
                :key="a.id"
                class="relative group"
              >
                <span
                  class="absolute -left-[30px] top-0.5 size-6 rounded-full flex items-center justify-center shadow-sm transition-transform group-hover:scale-110"
                  :class="pillFor(a.accent)"
                >
                  <component
                    :is="iconFor(a.icon)"
                    class="size-3.5"
                  />
                </span>
                <div class="flex items-start justify-between gap-3">
                  <p class="text-sm leading-6 text-foreground/90">
                    {{ a.text }}
                  </p>
                  <span class="shrink-0 text-[11px] text-muted-foreground whitespace-nowrap">
                    {{ a.time }}
                  </span>
                </div>
              </li>
            </template>
            <template v-else>
              <li class="relative text-sm text-muted-foreground py-6">
                暂无活动记录
              </li>
            </template>
          </ol>
        </CardContent>
      </Card>

      <Card class="xl:col-span-4 rounded-2xl overflow-hidden border-border/60 shadow-sm">
        <CardHeader class="py-4">
          <CardTitle class="text-[15px]">
            快捷入口
          </CardTitle>
          <CardDescription class="text-xs mt-0.5">
            一键直达常用功能
          </CardDescription>
        </CardHeader>
        <CardContent class="pt-0 pb-4">
          <div class="grid grid-cols-2 gap-2.5">
            <button
              v-for="q in [
                { title: '新建文章', icon: PenTool, to: '/admin/content/posts/new', grad: '#0EA5E9,#0284C7' },
                { title: '站点设置', icon: Settings, to: '/admin/system/settings', grad: '#6366F1,#4F46E5' },
                { title: '媒体库', icon: LibraryBig, to: '/admin/media/library', grad: '#14B8A6,#0D9488' },
                { title: '权限管理', icon: ShieldCheck, to: '/admin/roles', grad: '#0EA5E9,#0E7490' },
                { title: '审核评论', icon: MessageSquare, to: '/admin/interaction/comments', grad: '#F59E0B,#D97706' },
                { title: 'SEO 工具', icon: Search, to: '/admin/tools/seo', grad: '#0369A1,#075985' }
              ]"
              :key="q.title"
              type="button"
              class="group flex items-center gap-3 p-3 rounded-xl border border-border bg-card hover:-translate-y-0.5 hover:shadow-[0_10px_22px_-14px_rgba(14,165,233,0.45)] hover:border-primary/30 transition-all duration-200 text-left"
              @click="navigateTo(q.to)"
            >
              <div
                class="shrink-0 size-9 rounded-lg text-white flex items-center justify-center shadow-sm"
                :style="{ background: `linear-gradient(135deg, ${q.grad})` }"
              >
                <component
                  :is="q.icon"
                  class="size-4.5"
                />
              </div>
              <div class="min-w-0 flex-1">
                <p class="text-[13px] font-semibold truncate leading-tight">
                  {{ q.title }}
                </p>
                <p class="text-[11px] text-muted-foreground mt-0.5 flex items-center gap-1">
                  进入
                  <ChevronRight class="size-3 opacity-70 transition-transform group-hover:translate-x-0.5" />
                </p>
              </div>
            </button>
          </div>
        </CardContent>
      </Card>
    </section>
  </div>
</template>
