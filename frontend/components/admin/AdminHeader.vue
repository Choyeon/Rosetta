<script setup lang="ts">
import {
  Search,
  Bell,
  Menu as MenuIcon,
  LogOut,
  User as UserIcon,
  Settings as SettingsIcon,
  ExternalLink,
  MessageSquare,
  CheckCheck,
  Inbox,
  ChevronRight,
  Loader2
} from '@lucide/vue'
import { Button } from '~~/components/ui/button'
import { Input } from '~~/components/ui/input'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuGroup,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger
} from '~~/components/ui/dropdown-menu'
import { Avatar, AvatarFallback, AvatarImage } from '~~/components/ui/avatar'
import { Badge } from '~~/components/ui/badge'
import { ScrollArea } from '~~/components/ui/scroll-area'
import { Skeleton } from '~~/components/ui/skeleton'
import ThemeToggle from '~~/components/ThemeToggle.vue'
import { useAuthStore } from '~~/stores/auth'
import {
  fetchNotifications,
  fetchNotificationStats,
  markNotificationRead,
  clearAllNotifications,
  type AdminNotification,
  type NotificationLevel
} from '~~/composables/useAdminManage'
import { useToast } from '~~/composables/useToast'

defineProps<{
  sidebarCollapsed: boolean
}>()

const authStore = useAuthStore()
const router = useRouter()
const route = useRoute()
const toast = useToast()

// ==================== 面包屑 ====================
const crumbMap: Record<string, string> = {
  '/admin': '仪表盘',
  '/admin/content/posts': '文章管理',
  '/admin/content/categories': '分类管理',
  '/admin/content/tags': '标签管理',
  '/admin/content/series': '系列管理',
  '/admin/content/pages': '独立页面',
  '/admin/interaction/comments': '评论管理',
  '/admin/interaction/guestbook': '留言板',
  '/admin/interaction/announcements': '公告管理',
  '/admin/interaction/activities': '动态说说',
  '/admin/users': '用户列表',
  '/admin/users/titles': '头衔称号',
  '/admin/media/library': '媒体库',
  '/admin/media/gallery': '相册管理',
  '/admin/system/settings': '站点设置',
  '/admin/system/navigation': '导航菜单',
  '/admin/system/friendlinks': '友情链接',
  '/admin/system/webhooks': 'Webhook 配置',
  '/admin/tools/import-export': '导入导出',
  '/admin/tools/seo': 'SEO 工具',
  '/admin/tools/translate': '翻译工具',
  '/admin/tools/performance': '性能监控',
  '/admin/tools/audit-logs': '审计日志',
  '/admin/tools/migrations': '数据库迁移',
  '/admin/tools/cache': '缓存管理'
}

const groupMap: Record<string, string> = {
  content: '内容管理',
  interaction: '互动管理',
  users: '用户与权限',
  media: '媒体资源',
  system: '系统配置',
  tools: '工具与运维'
}

const currentGroup = computed(() => {
  const segs = route.path.split('/')
  const seg2: string | undefined = segs[2]
  if (seg2 === undefined) return '总览'
  return groupMap[seg2] || '未命名分组'
})
const currentPage = computed(() => crumbMap[route.path] || route.path.split('/').pop() || '')

// ==================== 用户信息 ====================
const userDisplayName = computed(() => authStore.user?.username || '未登录')
const userAvatar = computed(() => authStore.user?.avatar || '')
const userFallback = computed(() => (userDisplayName.value || 'U').slice(0, 1).toUpperCase())

const logout = () => {
  authStore.clearTokens()
  navigateTo('/login', { replace: true })
}

const openFront = () => {
  if (import.meta.client) window.open('/', '_blank')
}

// ==================== 站内通知（真实 API） ====================
/** 未读数量（仅未读>0时显示 badge；接口失败时降级为 0 不误导） */
const unreadCount = ref(0)
const items = ref<AdminNotification[]>([])
const loadingList = ref(false)
const loadingBadge = ref(false)
const markingClearing = ref(false)
const dropdownOpen = ref(false)

const levelToClass: Record<NotificationLevel, string> = {
  info: 'bg-sky-500/10 text-sky-600 dark:text-sky-400 ring-1 ring-inset ring-sky-500/20',
  success: 'bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 ring-1 ring-inset ring-emerald-500/20',
  warning: 'bg-amber-500/10 text-amber-600 dark:text-amber-400 ring-1 ring-inset ring-amber-500/20',
  error: 'bg-rose-500/10 text-rose-600 dark:text-rose-400 ring-1 ring-inset ring-rose-500/20'
}
const levelLabel: Record<NotificationLevel, string> = {
  info: '通知',
  success: '成功',
  warning: '提醒',
  error: '异常'
}

/** 拉取 badge 数字（后台 header 初始化后立刻拉一次；后台操作成功后可再刷新） */
async function loadBadge(silent = false) {
  loadingBadge.value = !silent
  try {
    const s = await fetchNotificationStats()
    unreadCount.value = Number(s?.unread_count ?? 0) || 0
  } catch {
    // 接口未就绪或没权限：保持 0，不要显示假 badge
    unreadCount.value = 0
  } finally {
    loadingBadge.value = false
  }
}

/** 点开下拉时拉取最近 10 条（不缓存，保持当前最新） */
async function loadList() {
  loadingList.value = true
  try {
    const r = await fetchNotifications({ page: 1, page_size: 10 })
    items.value = r?.items ?? []
    if (typeof r?.unread_count === 'number') unreadCount.value = r.unread_count
  } catch (e) {
    items.value = []
    unreadCount.value = 0
  } finally {
    loadingList.value = false
  }
}

watch(dropdownOpen, (open) => {
  if (open) loadList()
})

async function handleOpenItem(n: AdminNotification) {
  // 先标记已读（异步不阻塞跳转），badge 立刻 -1 给即时反馈
  if (!n.is_read && unreadCount.value > 0) unreadCount.value -= 1
  const localId = n.id
  markNotificationRead(localId).catch(() => {
    // 失败则回滚 UI 状态
    if (!n.is_read) unreadCount.value += 1
    toast.warning('标记已读失败，请稍后再试')
  })
  if (n.link && typeof n.link === 'string' && n.link.trim()) {
    const target = n.link.trim()
    if (/^https?:\/\//i.test(target)) {
      window.open(target, '_blank', 'noopener')
    } else {
      await navigateTo(target)
    }
    dropdownOpen.value = false
    return
  }
  // 无 link 时，仅在本地把这一条翻为已读
  const hit = items.value.find((i) => i.id === localId)
  if (hit) hit.is_read = true
}

async function handleClearAll() {
  markingClearing.value = true
  try {
    await clearAllNotifications()
    unreadCount.value = 0
    items.value = items.value.map((i) => ({ ...i, is_read: true }))
    toast.success('已全部标记为已读')
  } catch (e) {
    toast.error(e instanceof Error ? e.message : '清空失败')
  } finally {
    markingClearing.value = false
  }
}

function fmtTime(iso: string | null): string {
  if (!iso) return ''
  const d = new Date(iso)
  if (Number.isNaN(d.getTime())) return iso
  const now = Date.now()
  const diff = Math.max(0, Math.floor((now - d.getTime()) / 1000))
  if (diff < 60) return `${diff}s 前`
  if (diff < 3600) return `${Math.floor(diff / 60)}m 前`
  if (diff < 86400) return `${Math.floor(diff / 3600)}h 前`
  if (diff < 86400 * 7) return `${Math.floor(diff / 86400)}d 前`
  return `${d.getMonth() + 1}/${String(d.getDate()).padStart(2, '0')}`
}

// 登录完成后第一次拉 badge；组件卸载时跳过
onMounted(async () => {
  if (authStore.isAuthenticated) await loadBadge(true)
})

// authStore 登录态变化时（从 login → /admin 跳转）再拉一次
watch(
  () => authStore.isAuthenticated,
  (loggedIn) => {
    if (loggedIn) loadBadge(true)
    else { unreadCount.value = 0; items.value = [] }
  },
  { immediate: false }
)
</script>

<template>
  <header class="admin-header h-16 shrink-0 border-b border-border bg-background/80 backdrop-blur-md sticky top-0 z-40 px-3 md:px-5 flex items-center gap-3">
    <!-- 移动端/窄屏：菜单折叠切换 -->
    <Button
      variant="ghost"
      size="icon"
      class="md:hidden size-9 text-muted-foreground"
    >
      <MenuIcon class="size-5" />
    </Button>

    <!-- 面包屑 -->
    <nav
      aria-label="Breadcrumb"
      class="hidden sm:flex items-center gap-2 text-sm min-w-0"
    >
      <span class="text-muted-foreground/60 shrink-0">
        {{ currentGroup }}
      </span>
      <span class="text-muted-foreground/40 shrink-0 font-light">/</span>
      <span
        class="font-medium text-foreground truncate"
        :title="currentPage"
      >
        {{ currentPage }}
      </span>
    </nav>

    <!-- 搜索框（中大屏） -->
    <div class="hidden lg:flex flex-1 max-w-md mx-auto">
      <div class="relative w-full">
        <Search class="absolute left-3 top-1/2 -translate-y-1/2 size-4 text-muted-foreground" />
        <Input
          class="pl-9 h-9 rounded-[10px] bg-muted/50 focus:bg-background"
          placeholder="搜索文章/用户/设置 (Ctrl+K)"
        />
        <kbd
          class="absolute right-2.5 top-1/2 -translate-y-1/2 inline-flex items-center gap-0.5 px-1.5 h-5 rounded-[6px] border border-border bg-background text-[10px] font-medium text-muted-foreground"
        >
          ⌘K
        </kbd>
      </div>
    </div>

    <div class="flex-1 sm:hidden lg:hidden" />

    <!-- 右区：通知 + 主题切换 + 用户菜单 -->
    <div class="flex items-center gap-1 md:gap-2">
      <!-- 通知铃铛（真实数据）：点开后显示下拉列表，badge 只在未读>0时出现 -->
      <DropdownMenu v-model:open="dropdownOpen">
        <DropdownMenuTrigger as-child>
          <Button
            variant="ghost"
            size="icon"
            class="relative size-9 text-muted-foreground hover:text-foreground transition-opacity"
            :disabled="loadingBadge"
            aria-label="通知中心"
          >
            <Bell v-if="!loadingBadge" class="size-[18px]" />
            <Loader2 v-else class="size-[18px] animate-spin opacity-60" />
            <span
              v-if="unreadCount > 0"
              class="absolute top-1.5 right-1.5 min-w-[16px] h-4 px-1 rounded-full text-[10px] font-bold flex items-center justify-center bg-error text-error-foreground shadow"
            >
              {{ unreadCount > 99 ? '99+' : unreadCount }}
            </span>
          </Button>
        </DropdownMenuTrigger>

        <DropdownMenuContent
          align="end"
          class="w-[380px] max-w-[92vw] rounded-[14px] p-1.5 shadow-2xl"
        >
          <div class="flex items-center justify-between px-2.5 py-2">
            <div class="flex items-center gap-2 min-w-0">
              <span class="text-sm font-semibold tracking-tight">
                通知中心
              </span>
              <Badge
                v-if="unreadCount > 0"
                variant="secondary"
                class="h-4 px-1.5 text-[10px] rounded-full"
              >
                未读 {{ unreadCount }}
              </Badge>
              <Badge
                v-else
                variant="outline"
                class="h-4 px-1.5 text-[10px] rounded-full opacity-70"
              >
                暂无未读
              </Badge>
            </div>
            <Button
              variant="ghost"
              size="sm"
              class="h-7 px-2 rounded-lg text-xs text-muted-foreground hover:text-foreground disabled:opacity-50"
              :disabled="markingClearing || unreadCount === 0"
              @click="handleClearAll"
            >
              <CheckCheck v-if="!markingClearing" class="size-3.5 mr-1" />
              <Loader2 v-else class="size-3.5 mr-1 animate-spin" />
              全部已读
            </Button>
          </div>
          <DropdownMenuSeparator class="my-1" />

          <div class="h-[340px] w-full">
            <ScrollArea class="h-full w-full pr-1">
              <Skeleton
                v-if="loadingList"
                class="rounded-xl h-14 mb-2 last:mb-0 mx-1.5"
              />
              <Skeleton
                v-if="loadingList"
                class="rounded-xl h-14 mb-2 last:mb-0 mx-1.5"
              />
              <Skeleton
                v-if="loadingList"
                class="rounded-xl h-14 mb-2 last:mb-0 mx-1.5"
              />

              <template v-else-if="items.length === 0">
                <div class="flex flex-col items-center justify-center gap-2 px-4 pt-10 pb-8 text-center">
                  <div class="size-12 rounded-2xl bg-muted/60 flex items-center justify-center text-muted-foreground">
                    <Inbox class="size-5" />
                  </div>
                  <p class="text-sm font-medium text-foreground/90">
                    暂时没有通知
                  </p>
                  <p class="text-xs text-muted-foreground">
                    新文章评论、系统公告、审核结果等都会在这里出现
                  </p>
                </div>
              </template>

              <template v-else>
                <DropdownMenuGroup class="p-0.5">
                  <DropdownMenuItem
                    v-for="n in items"
                    :key="n.id"
                    class="h-auto w-full p-3 my-0.5 rounded-[10px] flex items-start gap-3 cursor-pointer focus:bg-accent/60"
                    :class="{ 'bg-accent/20': !n.is_read }"
                    @click="handleOpenItem(n)"
                  >
                    <!-- level 小圆点 -->
                    <span
                      class="mt-1 shrink-0 size-2 rounded-full inline-flex items-center justify-center"
                      :class="{
                        'bg-sky-500': n.level === 'info',
                        'bg-emerald-500': n.level === 'success',
                        'bg-amber-500': n.level === 'warning',
                        'bg-rose-500': n.level === 'error' || !n.level
                      }"
                    />
                    <div class="flex-1 min-w-0">
                      <div class="flex items-start justify-between gap-2">
                        <div class="min-w-0 flex items-center gap-1.5">
                          <span
                            class="shrink-0 inline-flex items-center rounded-md px-1.5 py-0.5 text-[10px] font-semibold"
                            :class="levelToClass[n.level] || levelToClass.info"
                          >
                            {{ levelLabel[n.level] || levelLabel.info }}
                          </span>
                          <span class="text-[13px] font-semibold leading-snug truncate text-foreground">
                            {{ n.title }}
                          </span>
                        </div>
                        <span class="shrink-0 text-[10px] tabular-nums text-muted-foreground">
                          {{ fmtTime(n.created_at) }}
                        </span>
                      </div>
                      <p class="mt-0.5 text-[12px] leading-snug text-muted-foreground line-clamp-2">
                        {{ n.message || n.verb || '' }}
                      </p>
                      <div class="mt-1 flex items-center justify-between gap-2">
                        <div v-if="n.actor" class="flex items-center gap-1.5 min-w-0">
                          <Avatar class="size-4 shrink-0">
                            <AvatarImage :src="n.actor.avatar || ''" />
                            <AvatarFallback class="text-[9px]">
                              {{ (n.actor.nickname || n.actor.username || '?').slice(0, 1).toUpperCase() }}
                            </AvatarFallback>
                          </Avatar>
                          <span class="text-[11px] text-muted-foreground truncate">
                            {{ n.actor.nickname || n.actor.username }}
                          </span>
                        </div>
                        <span
                          v-if="n.link"
                          class="ml-auto inline-flex items-center text-[11px] text-primary shrink-0"
                        >
                          查看详情
                          <ChevronRight class="size-3 ml-0.5" />
                        </span>
                      </div>
                    </div>
                  </DropdownMenuItem>
                </DropdownMenuGroup>
              </template>
            </ScrollArea>
          </div>
        </DropdownMenuContent>
      </DropdownMenu>

      <!-- 主题切换（保留，无 navbar 调色板） -->
      <ThemeToggle />

      <!-- 用户菜单 -->
      <DropdownMenu>
        <DropdownMenuTrigger as-child>
          <Button
            variant="ghost"
            class="h-9 px-1.5 pl-1 pr-3 rounded-full gap-2 hover:bg-accent"
          >
            <Avatar class="size-7 ring-2 ring-border">
              <AvatarImage :src="userAvatar" />
              <AvatarFallback
                class="text-[11px] font-semibold text-[hsl(var(--primary-foreground))]"
                style="background: linear-gradient(135deg,#0EA5E9,#0369A1);"
              >
                {{ userFallback }}
              </AvatarFallback>
            </Avatar>
            <span class="hidden md:block text-sm font-medium truncate max-w-[120px]">
              {{ userDisplayName }}
            </span>
            <Badge
              v-if="authStore.isAdmin"
              variant="secondary"
              class="hidden md:flex h-5 px-1.5 text-[10px] rounded-full"
            >
              管理员
            </Badge>
          </Button>
        </DropdownMenuTrigger>
        <DropdownMenuContent
          align="end"
          class="w-64 rounded-[12px] p-1.5"
        >
          <DropdownMenuLabel class="px-2.5 py-2">
            <div class="flex items-center gap-2.5 min-w-0">
              <Avatar class="size-9 shrink-0">
                <AvatarImage :src="userAvatar" />
                <AvatarFallback
                  style="background: linear-gradient(135deg,#0EA5E9,#0369A1);"
                  class="text-[hsl(var(--primary-foreground))]"
                >
                  {{ userFallback }}
                </AvatarFallback>
              </Avatar>
              <div class="flex flex-col min-w-0">
                <span class="text-sm font-semibold truncate">{{ userDisplayName }}</span>
                <span class="text-[11px] text-muted-foreground truncate">
                  {{ authStore.user?.email || 'admin@rosetta.dev' }}
                </span>
              </div>
            </div>
          </DropdownMenuLabel>
          <DropdownMenuSeparator class="my-1" />
          <DropdownMenuGroup>
            <DropdownMenuItem
              class="h-9 rounded-[8px] cursor-pointer"
              @click="navigateTo(`/admin/users/${authStore.user?.id ?? 1}/edit`)"
            >
              <UserIcon class="size-4 mr-2 text-muted-foreground" />
              <span>个人资料</span>
            </DropdownMenuItem>
            <DropdownMenuItem
              class="h-9 rounded-[8px] cursor-pointer"
              @click="navigateTo('/admin/system/settings')"
            >
              <SettingsIcon class="size-4 mr-2 text-muted-foreground" />
              <span>站点设置</span>
            </DropdownMenuItem>
          </DropdownMenuGroup>
          <DropdownMenuSeparator class="my-1" />
          <DropdownMenuItem
            class="h-9 rounded-[8px] cursor-pointer"
            @click="openFront"
          >
            <ExternalLink class="size-4 mr-2 text-muted-foreground" />
            <span>打开前台</span>
          </DropdownMenuItem>
          <DropdownMenuSeparator class="my-1" />
          <DropdownMenuItem
            class="h-9 rounded-[8px] cursor-pointer text-error focus:text-error focus:bg-error-muted"
            @click="logout"
          >
            <LogOut class="size-4 mr-2" />
            <span>退出登录</span>
          </DropdownMenuItem>
        </DropdownMenuContent>
      </DropdownMenu>
    </div>
  </header>
</template>
