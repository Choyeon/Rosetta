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
      { label: '文章管理', path: '/admin/content/posts', icon: FileText },
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
      { label: '媒体库', path: '/admin/media/library', icon: Image },
      { label: '相册管理', path: '/admin/media/gallery', icon: Album }
    ]
  },
  {
    key: 'system',
    title: '系统配置',
    icon: Settings,
    items: [
      { label: '站点设置', path: '/admin/system/settings', icon: Settings },
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

/**
 * 判断某个菜单项是否应当高亮。
 *
 * 关键点：**不要使用 startsWith(path + '/')** —— 它会把「父项」与「同前缀兄弟子项」
 * 一起误激活。典型的反例：
 *   path = /admin/users，当前路由 = /admin/users/titles
 *   → startsWith('/admin/users/') === true → 用户列表也错误地被染成激活色
 *
 * 新规则（按优先级）：
 *   1) /admin（仪表盘）：精确匹配 /admin 或 /admin/
 *   2) 其它菜单项：
 *      - 精确匹配 path → 激活
 *      - 以「path + "/"」开头，并且紧接着的段为数字或通用 id 段
 *        （如 /admin/content/posts/42/edit、/admin/users/12/edit）→ 激活
 *      - 同前缀下出现了「其它菜单的 path 段」（如 /admin/users/titles 中
 *        「titles」是另一个真实菜单项，并非数字/id 段）→ **不** 算作激活
 */
const isActive = (path: string) => {
  const rp = route.path
  if (path === '/admin') return rp === '/admin' || rp === '/admin/'
  if (rp === path) return true
  const prefix = path + '/'
  if (!rp.startsWith(prefix)) return false

  const rest = rp.slice(prefix.length) // e.g. "titles" | "42/edit" | ""
  if (rest === '') return true

  // 取 '/' 分隔的第一段
  const firstSeg = rest.split('/')[0] ?? ''
  if (firstSeg === '') return true

  // 数字 id 段 → 认定为子资源（posts/:id、users/:id 等编辑页）
  if (/^\d+$/.test(firstSeg)) return true

  // UUID / nanoid / slug 样式（仅包含字母数字和 -）且长度足够像 id 也算
  if (/^[A-Za-z0-9_-]{8,}$/.test(firstSeg) && !/[A-Z]/.test(firstSeg.slice(1, 4))) {
    // 但要排除掉已知的菜单项 label，稳妥做法：再看该段是否恰好是
    // 同组里"其它菜单项"相对于 path 的子路径
    const isGroupSibling = groups.some(g =>
      g.items.some(it => {
        if (it.path === path) return false
        const prefixOfOther = path + '/'
        return it.path.startsWith(prefixOfOther) &&
               it.path.slice(prefixOfOther.length).split('/')[0] === firstSeg
      })
    )
    if (isGroupSibling) return false
    return true
  }

  // 如果第一段正好对应同组的兄弟菜单项 → 说明"用户点到另一个菜单去了"，当前不应激活
  const isSiblingLabel = groups.some(g =>
    g.items.some(it => it.path !== path && it.path.startsWith(prefix) &&
      it.path.slice(prefix.length).split('/')[0] === firstSeg)
  )
  if (isSiblingLabel) return false

  return true
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
                    class="sb-item w-full group flex items-center gap-2.5 px-2.5 h-[38px] rounded-[11px] relative isolate transition-all duration-300 ease-[cubic-bezier(0.22,1,0.36,1)] will-change-transform"
                    :class="[
                      isActive(item.path)
                        ? 'sb-item-active text-[hsl(var(--sidebar-active-foreground,var(--primary)))] font-semibold'
                        : 'sb-item-idle text-sidebar-foreground/75 hover:text-sidebar-foreground'
                    ]"
                    @click="go(item.path)"
                  >
                    <!-- Hover / Active 底衬：iOS26 风格的柔和胶囊 + 天青光晕 -->
                    <span
                      class="absolute inset-0 rounded-[11px] -z-10 transition-all duration-300 ease-[cubic-bezier(0.22,1,0.36,1)]"
                      :class="[
                        isActive(item.path)
                          ? 'sb-bg-active'
                          : 'opacity-0 group-hover:opacity-100 sb-bg-hover'
                      ]"
                      aria-hidden="true"
                    />
                    <component
                      :is="item.icon"
                      class="shrink-0 size-[18px] transition-colors duration-300"
                      :class="isActive(item.path) ? 'sb-icon-active' : 'text-muted-foreground group-hover:text-sidebar-foreground'"
                    />
                    <span
                      v-if="!collapsed"
                      class="flex-1 min-w-0 text-[13.5px] truncate text-left tracking-[0.01em]"
                    >
                      {{ item.label }}
                    </span>
                    <ChevronRight
                      v-if="isActive(item.path) && !collapsed"
                      class="shrink-0 size-3.5 opacity-70 sb-chevron"
                      aria-hidden="true"
                    />
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
  transition: opacity 240ms cubic-bezier(0.22, 1, 0.36, 1), transform 240ms cubic-bezier(0.22, 1, 0.36, 1);
}
.fade-collapsed-enter-from,
.fade-collapsed-leave-to {
  opacity: 0;
  transform: translateX(-6px);
}

/* ======= 侧边栏菜单：朴素低调激活态 ======= */

/* —— 激活胶囊：仅使用淡主题色底色 + 细描边，与 hover 强度接近，避免侵略性 —— */
.sb-bg-active {
  background: hsl(var(--primary) / 0.12);
  box-shadow:
    inset 0 0 0 1px hsl(var(--primary) / 0.22);
}

/* —— Hover 胶囊：与激活态观感接近，仅底色略深 + 极细描边 —— */
.sb-bg-hover {
  background: hsl(var(--sidebar-accent, var(--accent)) / 0.9);
  box-shadow:
    inset 0 0 0 1px hsl(var(--foreground) / 0.05);
}

@media (prefers-color-scheme: dark) {
  .sb-bg-active {
    background: hsl(var(--primary) / 0.18);
    box-shadow:
      inset 0 0 0 1px hsl(var(--primary) / 0.30);
  }
  .sb-bg-hover {
    background: hsl(var(--sidebar-accent) / 0.85);
    box-shadow:
      inset 0 0 0 1px hsl(var(--foreground) / 0.06);
  }
}

/* —— 微抬升动画：hover 与激活都不做激进位移 —— */
.sb-item-idle:hover {
  transform: none;
}
.sb-item-active {
  transform: none;
}

/* —— 激活图标：仅主题色填充，去掉外缘发光滤镜（避免侵略性） —— */
.sb-icon-active {
  color: hsl(var(--primary));
}

/* —— 激活项右箭头：弱化，不做滑入动画 —— */
.sb-chevron {
  color: hsl(var(--primary) / 0.7);
  opacity: 0.7;
}
</style>
