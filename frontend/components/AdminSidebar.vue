<template>
  <Sidebar collapsible="icon">
    <SidebarHeader>
      <div class="flex items-center gap-2 font-display text-xl font-bold">
        <div class="flex items-center justify-center size-8 rounded-md bg-primary text-primary-foreground">
          <Home class="size-5" />
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
<<<<<<< Updated upstream
              <SidebarMenuButton as="component" :is="'NuxtLink'" to="/admin" :active="$route.path === '/admin'">
=======
              <SidebarMenuButton
                :is="'NuxtLink'"
                as="component"
                to="/admin"
                :active="$route.path === '/admin'"
              >
>>>>>>> Stashed changes
                <LayoutDashboard class="size-4" />
                <span>仪表盘</span>
              </SidebarMenuButton>
            </SidebarMenuItem>
            <SidebarMenuItem>
<<<<<<< Updated upstream
              <SidebarMenuButton as="component" :is="'NuxtLink'" to="#">
=======
              <SidebarMenuButton
                :is="'NuxtLink'"
                as="component"
                to="#"
              >
>>>>>>> Stashed changes
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
<<<<<<< Updated upstream
                  <SidebarMenuSubButton as="component" :is="'NuxtLink'" to="#">
=======
                  <SidebarMenuSubButton
                    :is="'NuxtLink'"
                    as="component"
                    to="/admin/posts"
                    :active="$route.path === '/admin/posts' || ($route.path.startsWith('/admin/posts/') && !$route.path.startsWith('/admin/posts/new'))"
                  >
>>>>>>> Stashed changes
                    <FileEdit class="size-4" />
                    <span>所有文章</span>
                  </SidebarMenuSubButton>
                </SidebarMenuSubItem>
                <SidebarMenuSubItem>
<<<<<<< Updated upstream
                  <SidebarMenuSubButton as="component" :is="'NuxtLink'" to="#">
=======
                  <SidebarMenuSubButton
                    :is="'NuxtLink'"
                    as="component"
                    to="/admin/posts/new"
                    :active="$route.path === '/admin/posts/new'"
                  >
>>>>>>> Stashed changes
                    <Plus class="size-4" />
                    <span>新建文章</span>
                  </SidebarMenuSubButton>
                </SidebarMenuSubItem>
              </SidebarMenuSub>
            </SidebarMenuItem>
            <SidebarMenuItem>
<<<<<<< Updated upstream
              <SidebarMenuButton as="component" :is="'NuxtLink'" to="#">
=======
              <SidebarMenuButton
                :is="'NuxtLink'"
                as="component"
                to="/admin/categories"
                :active="$route.path.startsWith('/admin/categories')"
              >
>>>>>>> Stashed changes
                <FolderOpen class="size-4" />
                <span>分类</span>
              </SidebarMenuButton>
            </SidebarMenuItem>
            <SidebarMenuItem>
<<<<<<< Updated upstream
              <SidebarMenuButton as="component" :is="'NuxtLink'" to="#">
=======
              <SidebarMenuButton
                :is="'NuxtLink'"
                as="component"
                to="#"
              >
>>>>>>> Stashed changes
                <Tags class="size-4" />
                <span>标签</span>
              </SidebarMenuButton>
            </SidebarMenuItem>
            <SidebarMenuItem>
<<<<<<< Updated upstream
              <SidebarMenuButton as="component" :is="'NuxtLink'" to="#">
=======
              <SidebarMenuButton
                :is="'NuxtLink'"
                as="component"
                to="/admin/comments"
                :active="$route.path.startsWith('/admin/comments')"
              >
>>>>>>> Stashed changes
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
<<<<<<< Updated upstream
              <SidebarMenuButton as="component" :is="'NuxtLink'" to="#">
=======
              <SidebarMenuButton
                :is="'NuxtLink'"
                as="component"
                to="/admin/users"
                :active="$route.path.startsWith('/admin/users')"
              >
>>>>>>> Stashed changes
                <Users class="size-4" />
                <span>用户</span>
              </SidebarMenuButton>
            </SidebarMenuItem>
            <SidebarMenuItem>
<<<<<<< Updated upstream
              <SidebarMenuButton as="component" :is="'NuxtLink'" to="#">
=======
              <SidebarMenuButton
                :is="'NuxtLink'"
                as="component"
                to="/admin/settings"
                :active="$route.path.startsWith('/admin/settings')"
              >
>>>>>>> Stashed changes
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
