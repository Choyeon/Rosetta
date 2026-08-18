<template>
  <Sidebar collapsible="icon">
    <SidebarHeader>
      <div class="flex items-center gap-2 font-display text-xl font-bold">
        <div class="flex items-center justify-center size-8 rounded-md bg-primary/10 ring-1 ring-primary/20">
          <img
            src="/logo/rosetta-primary-icon.png"
            alt="Rosetta"
            class="size-6 object-contain"
          >
        </div>
        <span>Rosetta Admin</span>
      </div>
    </SidebarHeader>
    <SidebarSeparator />
    <SidebarContent>
      <SidebarGroup>
        <SidebarGroupLabel>概览</SidebarGroupLabel>
        <SidebarGroupContent>
          <SidebarMenu>
            <SidebarMenuItem>
              <SidebarMenuButton
                :is="'NuxtLink'"
                as="component"
                to="/admin"
                :active="$route.path === '/admin'"
              >
                <LayoutDashboard class="size-4" />
                <span>仪表盘</span>
              </SidebarMenuButton>
            </SidebarMenuItem>
            <SidebarMenuItem>
              <SidebarMenuButton
                :is="'NuxtLink'"
                as="component"
                to="#"
              >
                <LineChart class="size-4" />
                <span>数据分析</span>
              </SidebarMenuButton>
            </SidebarMenuItem>
          </SidebarMenu>
        </SidebarGroupContent>
      </SidebarGroup>

      <SidebarGroup>
        <SidebarGroupLabel>内容</SidebarGroupLabel>
        <SidebarGroupContent>
          <SidebarMenu>
            <SidebarMenuItem>
              <SidebarMenuButton>
                <FileText class="size-4" />
                <span>文章</span>
                <ChevronDown class="size-4 ml-auto transition-transform duration-200 group-data-[state=open]/menu-button:rotate-180" />
              </SidebarMenuButton>
              <SidebarMenuSub>
                <SidebarMenuSubItem>
                  <SidebarMenuSubButton
                    :is="'NuxtLink'"
                    as="component"
                    to="/admin/posts"
                    :active="$route.path === '/admin/posts' || ($route.path.startsWith('/admin/posts/') && !$route.path.startsWith('/admin/posts/new'))"
                  >
                    <FileEdit class="size-4" />
                    <span>所有文章</span>
                  </SidebarMenuSubButton>
                </SidebarMenuSubItem>
                <SidebarMenuSubItem>
                  <SidebarMenuSubButton
                    :is="'NuxtLink'"
                    as="component"
                    to="/admin/posts/new"
                    :active="$route.path === '/admin/posts/new'"
                  >
                    <Plus class="size-4" />
                    <span>新建文章</span>
                  </SidebarMenuSubButton>
                </SidebarMenuSubItem>
              </SidebarMenuSub>
            </SidebarMenuItem>
            <SidebarMenuItem>
              <SidebarMenuButton
                :is="'NuxtLink'"
                as="component"
                to="/admin/categories"
                :active="$route.path.startsWith('/admin/categories')"
              >
                <FolderOpen class="size-4" />
                <span>分类</span>
              </SidebarMenuButton>
            </SidebarMenuItem>
            <SidebarMenuItem>
              <SidebarMenuButton
                :is="'NuxtLink'"
                as="component"
                to="#"
              >
                <Tags class="size-4" />
                <span>标签</span>
              </SidebarMenuButton>
            </SidebarMenuItem>
            <SidebarMenuItem>
              <SidebarMenuButton
                :is="'NuxtLink'"
                as="component"
                to="/admin/comments"
                :active="$route.path.startsWith('/admin/comments')"
              >
                <MessageSquare class="size-4" />
                <span>评论</span>
              </SidebarMenuButton>
            </SidebarMenuItem>
          </SidebarMenu>
        </SidebarGroupContent>
      </SidebarGroup>

      <SidebarGroup>
        <SidebarGroupLabel>系统</SidebarGroupLabel>
        <SidebarGroupContent>
          <SidebarMenu>
            <SidebarMenuItem>
              <SidebarMenuButton
                :is="'NuxtLink'"
                as="component"
                to="/admin/users"
                :active="$route.path.startsWith('/admin/users')"
              >
                <Users class="size-4" />
                <span>用户</span>
              </SidebarMenuButton>
            </SidebarMenuItem>
            <SidebarMenuItem>
              <SidebarMenuButton
                :is="'NuxtLink'"
                as="component"
                to="/admin/settings"
                :active="$route.path.startsWith('/admin/settings')"
              >
                <Settings2 class="size-4" />
                <span>设置</span>
              </SidebarMenuButton>
            </SidebarMenuItem>
          </SidebarMenu>
        </SidebarGroupContent>
      </SidebarGroup>
    </SidebarContent>
    <SidebarFooter>
      <div class="flex items-center gap-3 w-full">
        <Avatar size="sm">
          <AvatarFallback>{{ authStore.user?.name?.[0] ?? authStore.user?.username?.[0] ?? 'A' }}</AvatarFallback>
        </Avatar>
        <div class="flex flex-col min-w-0 flex-1">
          <span class="font-medium text-sm truncate">
            {{ authStore.user?.name || authStore.user?.nickname || authStore.user?.username || '未登录' }}
          </span>
          <span class="text-xs text-muted-foreground truncate">
            {{ authStore.user?.email || '—' }}
          </span>
        </div>
      </div>
    </SidebarFooter>
  </Sidebar>
</template>

<script setup lang="ts">
import {
  Sidebar,
  SidebarHeader,
  SidebarSeparator,
  SidebarContent,
  SidebarGroup,
  SidebarGroupLabel,
  SidebarGroupContent,
  SidebarMenu,
  SidebarMenuItem,
  SidebarMenuButton,
  SidebarMenuSub,
  SidebarMenuSubItem,
  SidebarMenuSubButton,
  SidebarFooter
} from '~~/components/ui/sidebar'
import { Avatar, AvatarFallback } from '~~/components/ui/avatar'
import {
  LayoutDashboard,
  LineChart,
  FileText,
  FolderOpen,
  Tags,
  MessageSquare,
  Users,
  Settings2,
  Home,
  ChevronDown,
  FileEdit,
  Plus
} from '@lucide/vue'
import { useAuthStore } from '~~/stores/auth'

const authStore = useAuthStore()
</script>
