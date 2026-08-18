<script setup lang="ts">
/* eslint-disable */
/* eslint-disable @typescript-eslint/ban-ts-comment */
// @ts-nocheck
/* eslint-enable @typescript-eslint/ban-ts-comment */
import {
  ChevronLeft,
  ChevronRight,
  LayoutDashboard,
  FileText,
  FolderKanban,
  Tags,
  BookOpen,
  File,
  MessageSquare,
  MessageSquareText,
  Bell,
  Activity,
  Users,
  Award,
  Image,
  Album,
  Settings,
  Link as LinkIcon,
  Globe,
  PlugZap,
  ArrowUpDown,
  Search,
  Languages,
  Gauge,
  ClipboardList,
  Database,
  Archive
} from '@lucide/vue'
import { Button } from '~~/components/ui/button'
import { ScrollArea } from '~~/components/ui/scroll-area'
import { Tooltip, TooltipContent, TooltipTrigger } from '~~/components/ui/tooltip'
import { Badge } from '~~/components/ui/badge'

const props = defineProps<{
  collapsed?: boolean
}>()

const emit = defineEmits<{
  'update:collapsed': [value: boolean]
}>()

const collapsed = computed({
  get: () => props.collapsed ?? false,
  set: (v: boolean) => emit('update:collapsed', v)
})

const route = useRoute()

interface MenuItem {
  label: string
  path: string
  icon: unknown
  badge?: string
  badgeVariant?: 'default' | 'secondary' | 'destructive' | 'outline'
}
interface MenuGroup {
  key: string
  title: string
  icon: unknown
  items: MenuItem[]
}

const groups = reactive<MenuGroup[]>([
  {
    key: 'overview',
    title: '总览',
    icon: LayoutDashboard,
    items: [
      { label: '仪表盘', path: '/admin', icon: LayoutDashboard }
    ]
  },
  {
    key: 'content',
    title: '内容管理',
    icon: FileText,
    items: [
      { label: '文章管理', path: '/admin/content/posts', icon: FileText, badge: '热', badgeVariant: 'secondary' },
      { label: '分类管理', path: '/admin/content/categories', icon: FolderKanban },
      { label: '标签管理', path: '/admin/content/tags', icon: Tags },
      { label: '系列管理', path: '/admin/content/series', icon: BookOpen },
      { label: '独立页面', path: '/admin/content/pages', icon: File }
    ]
  },
  {
    key: 'interaction',
    title: '互动管理',
    icon: MessageSquare,
    items: [
      { label: '评论管理', path: '/admin/interaction/comments', icon: MessageSquare },
      { label: '留言板', path: '/admin/interaction/guestbook', icon: MessageSquareText },
      { label: '公告管理', path: '/admin/interaction/announcements', icon: Bell },
      { label: '动态说说', path: '/admin/interaction/activities', icon: Activity }
    ]
  },
  {
    key: 'users',
    title: '用户与权限',
    icon: Users,
    items: [
      { label: '用户列表', path: '/admin/users', icon: Users },
      { label: '头衔称号', path: '/admin/users/titles', icon: Award }
    ]
  },
  {
    key: 'media',
    title: '媒体资源',
    icon: Image,
    items: [
      { label: '媒体库', path: '/admin/media/library', icon: Image, badge: 'NEW', badgeVariant: 'outline' },
      { label: '相册管理', path: '/admin/media/gallery', icon: Album }
    ]
  },
  {
    key: 'system',
    title: '系统配置',
    icon: Settings,
    items: [
      { label: '站点设置', path: '/admin/system/settings', icon: Settings, badge: '17组', badgeVariant: 'secondary' },
      { label: '导航菜单', path: '/admin/system/navigation', icon: Globe },
      { label: '友情链接', path: '/admin/system/friendlinks', icon: LinkIcon },
      { label: 'Webhook 配置', path: '/admin/system/webhooks', icon: PlugZap }
    ]
  },
  {
    key: 'tools',
    title: '工具与运维',
    icon: ArrowUpDown,
    items: [
      { label: '导入导出', path: '/admin/tools/import-export', icon: ArrowUpDown },
      { label: 'SEO 工具', path: '/admin/tools/seo', icon: Search },
      { label: '翻译工具', path: '/admin/tools/translate', icon: Languages },
      { label: '性能监控', path: '/admin/tools/performance', icon: Gauge },
      { label: '审计日志', path: '/admin/tools/audit-logs', icon: ClipboardList },
      { label: '数据库迁移', path: '/admin/tools/migrations', icon: Database },
      { label: '缓存管理', path: '/admin/tools/cache', icon: Archive }
    ]
  }
])

const isActive = (path: string) => {
  if (path === '/admin') return route.path === '/admin' || route.path === '/admin/'
  return route.path === path || route.path.startsWith(path + '/')
}

const go = (path: string) => navigateTo(path)
</script>

<template>
  <aside
    class="admin-sidebar shrink-0 transition-all duration-300 ease-out border-r border-sidebar-border bg-sidebar flex flex-col"
    :class="collapsed ? 'w-[72px]' : 'w-[256px]'"
  >
    <!-- Logo + 标题 -->
    <div
      class="h-16 shrink-0 px-3 md:px-4 flex items-center justify-between border-b border-sidebar-border"
    >
      <NuxtLink
        to="/admin"
        class="flex items-center gap-2.5 min-w-0"
      >
        <div
          class="shrink-0 size-9 rounded-[10px] flex items-center justify-center font-bold text-white shadow-[0_6px_16px_-6px_hsl(var(--primary)/0.6)]"
          style="background: linear-gradient(135deg,#0EA5E9 0%,#0284C7 60%,#0369A1 100%);"
        >
          <span class="font-display text-lg tracking-tight">R</span>
        </div>
        <Transition
          name="fade-collapsed"
          mode="out-in"
        >
          <div
            v-if="!collapsed"
            class="flex flex-col leading-tight min-w-0"
          >
            <span class="font-display font-bold text-sidebar-foreground truncate">Rosetta Admin</span>
            <span class="text-[11px] text-muted-foreground/80 truncate">博客管理控制台</span>
          </div>
        </Transition>
      </NuxtLink>

      <Button
        v-if="!collapsed"
        variant="ghost"
        size="icon"
        class="ml-1 shrink-0 size-8 text-muted-foreground hover:text-sidebar-foreground"
        @click="collapsed = true"
      >
        <ChevronLeft class="size-4" />
      </Button>
    </div>

    <!-- Menu -->
    <ScrollArea class="flex-1 py-3 px-2">
      <nav class="flex flex-col gap-1">
        <template
          v-for="(group, gi) in groups"
          :key="group.key"
        >
          <!-- group 标题：展开态显示文字，折叠态省略 -->
          <div
            v-if="!collapsed"
            class="px-3 pt-4 pb-1.5 text-[11px] uppercase tracking-[0.12em] text-muted-foreground/70 font-semibold"
            :class="{ 'pt-2': gi === 0 }"
          >
            {{ group.title }}
          </div>
          <div
            v-else
            class="h-2"
          />

          <ul class="flex flex-col gap-0.5">
            <li
              v-for="item in group.items"
              :key="item.path"
            >
              <Tooltip :disabled="!collapsed">
                <TooltipTrigger as-child>
                  <button
                    type="button"
                    class="w-full group flex items-center gap-2.5 px-2.5 h-9 rounded-[10px] relative transition-all duration-200"
                    :class="[
                      isActive(item.path)
                        ? 'bg-gradient-to-r from-[hsl(var(--primary)/0.18)] to-[hsl(var(--primary)/0.06)] text-sidebar-foreground font-medium shadow-[inset_0_0_0_1px_hsl(var(--primary)/0.25)]'
                        : 'text-sidebar-foreground/70 hover:bg-sidebar-accent hover:text-sidebar-foreground'
                    ]"
                    @click="go(item.path)"
                  >
                    <span
                      v-if="isActive(item.path)"
                      class="absolute left-0 top-1/2 -translate-y-1/2 w-[3px] h-5 rounded-r-sm bg-primary"
                      aria-hidden="true"
                    />
                    <component
                      :is="item.icon"
                      class="shrink-0 size-[18px]"
                      :class="isActive(item.path) ? 'text-primary' : 'text-muted-foreground group-hover:text-sidebar-foreground'"
                    />
                    <span
                      v-if="!collapsed"
                      class="flex-1 min-w-0 text-sm truncate text-left"
                    >
                      {{ item.label }}
                    </span>
                    <Badge
                      v-if="!collapsed && item.badge"
                      :variant="item.badgeVariant || 'outline'"
                      class="shrink-0 text-[10px] h-4 px-1.5"
                    >
                      {{ item.badge }}
                    </Badge>
                  </button>
                </TooltipTrigger>
                <TooltipContent
                  v-if="collapsed"
                  side="right"
                  class="text-xs"
                >
                  {{ item.label }}
                </TooltipContent>
              </Tooltip>
            </li>
          </ul>
        </template>
      </nav>
    </ScrollArea>

    <!-- Footer：返回前台 + 折叠切换 -->
    <div class="shrink-0 border-t border-sidebar-border p-2 flex items-center gap-1">
      <NuxtLink
        to="/"
        target="_blank"
        class="flex-1 min-w-0 flex items-center gap-2 h-9 px-2 rounded-[10px] text-sidebar-foreground/70 hover:bg-sidebar-accent hover:text-sidebar-foreground transition-colors"
      >
        <Globe class="shrink-0 size-[18px] text-muted-foreground" />
        <span
          v-if="!collapsed"
          class="text-sm truncate"
        >返回前台</span>
      </NuxtLink>
      <Button
        v-if="collapsed"
        variant="ghost"
        size="icon"
        class="shrink-0 size-8 text-muted-foreground hover:text-sidebar-foreground"
        @click="collapsed = false"
      >
        <ChevronRight class="size-4" />
      </Button>
    </div>
  </aside>
</template>

<style scoped>
.fade-collapsed-enter-active,
.fade-collapsed-leave-active {
  transition: opacity 220ms ease, transform 220ms ease;
}
.fade-collapsed-enter-from,
.fade-collapsed-leave-to {
  opacity: 0;
  transform: translateX(-4px);
}
</style>
