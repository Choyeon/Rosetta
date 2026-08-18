<script setup lang="ts">
/* eslint-disable */
/* eslint-disable @typescript-eslint/ban-ts-comment */
// @ts-nocheck
/* eslint-enable @typescript-eslint/ban-ts-comment */
import {
  Search,
  Bell,
  Menu as MenuIcon,
  LogOut,
  User as UserIcon,
  Settings as SettingsIcon,
  ExternalLink,
  MessageSquare
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
import ThemeToggle from '~~/components/ThemeToggle.vue'
import { useAuthStore } from '~~/stores/auth'
import { Tooltip, TooltipContent, TooltipTrigger } from '~~/components/ui/tooltip'

defineProps<{
  sidebarCollapsed: boolean
}>()

const authStore = useAuthStore()
const router = useRouter()
const route = useRoute()

// 根据当前路由生成面包屑（基于 AdminSidebar 分组定义）
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
  return groupMap[segs[2]] || (segs[2] === undefined ? '总览' : '未命名分组')
})
const currentPage = computed(() => crumbMap[route.path] || route.path.split('/').pop() || '')

// 未读通知数量（假数据占位）
const unreadNotifications = ref(3)

const userDisplayName = computed(() => authStore.user?.username || '未登录')
const userAvatar = computed(() => authStore.user?.avatar || '')
const userFallback = computed(() => (userDisplayName.value || 'U').slice(0, 1).toUpperCase())

const logout = () => {
  authStore.clearTokens()
  navigateTo('/login', { replace: true })
}
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
      <!-- 通知铃铛 -->
      <Tooltip>
        <TooltipTrigger as-child>
          <Button
            variant="ghost"
            size="icon"
            class="relative size-9 text-muted-foreground hover:text-foreground"
          >
            <Bell class="size-[18px]" />
            <span
              v-if="unreadNotifications > 0"
              class="absolute top-1.5 right-1.5 min-w-[16px] h-4 px-1 rounded-full text-[10px] font-bold flex items-center justify-center bg-error text-error-foreground shadow"
            >
              {{ unreadNotifications > 9 ? '9+' : unreadNotifications }}
            </span>
          </Button>
        </TooltipTrigger>
        <TooltipContent>
          <p class="text-xs">
            未读通知 {{ unreadNotifications }} 条
          </p>
        </TooltipContent>
      </Tooltip>

      <!-- 评论快捷 -->
      <Tooltip>
        <TooltipTrigger as-child>
          <Button
            variant="ghost"
            size="icon"
            class="hidden sm:flex size-9 text-muted-foreground hover:text-foreground"
          >
            <MessageSquare class="size-[18px]" />
          </Button>
        </TooltipTrigger>
        <TooltipContent>
          <p class="text-xs">
            待审评论
          </p>
        </TooltipContent>
      </Tooltip>

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
            @click="window.open('/', '_blank')"
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
