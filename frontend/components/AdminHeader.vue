<template>
  <header class="flex h-16 shrink-0 items-center justify-between gap-3 border-b px-4 md:px-6 sticky top-0 bg-background z-30">
    <div class="flex items-center gap-2">
      <SidebarTrigger />

      <Breadcrumb>
        <BreadcrumbList>
          <BreadcrumbItem
            v-for="(item, index) in (breadcrumbItems ?? [])"
            :key="index"
          >
            <template v-if="index === (breadcrumbItems ?? []).length - 1">
              <BreadcrumbPage>{{ item.label }}</BreadcrumbPage>
            </template>
            <template v-else>
              <BreadcrumbLink
                :is="'NuxtLink'"
                v-if="item.href"
                as="component"
                :to="item.href"
              >
                {{ item.label }}
              </BreadcrumbLink>
              <BreadcrumbLink v-else>
                {{ item.label }}
              </BreadcrumbLink>
              <BreadcrumbSeparator />
            </template>
          </BreadcrumbItem>
        </BreadcrumbList>
      </Breadcrumb>
    </div>

    <div class="flex items-center gap-2">
      <div class="relative w-64 hidden md:block">
        <Search class="absolute left-3 top-1/2 -translate-y-1/2 size-4 text-muted-foreground" />
        <Input
          placeholder="搜索..."
          class="pl-10"
        />
      </div>

      <Button
        variant="ghost"
        size="icon"
        class="relative"
      >
        <Bell class="size-5" />
        <span class="absolute top-2 right-2 size-2 bg-destructive rounded-full ring-2 ring-background" />
      </Button>

      <ThemePaletteSwitcher />
      <ThemeToggle />

      <DropdownMenu>
        <DropdownMenuTrigger as-child>
          <Button
            variant="ghost"
            size="icon"
            class="relative rounded-full"
          >
            <Avatar size="sm">
              <AvatarImage
                v-if="authStore.user?.avatar"
                :src="authStore.user.avatar"
                :alt="authStore.user?.name ?? authStore.user?.username ?? 'avatar'"
              />
              <AvatarFallback>{{ authStore.user?.name?.[0] ?? authStore.user?.username?.[0] ?? 'A' }}</AvatarFallback>
            </Avatar>
          </Button>
        </DropdownMenuTrigger>
        <DropdownMenuContent
          class="w-56"
          align="end"
        >
          <DropdownMenuLabel>
            <div class="flex flex-col space-y-1">
              <p class="text-sm font-medium">
                {{ authStore.user?.name || authStore.user?.nickname || authStore.user?.username || '未登录' }}
              </p>
              <p class="text-xs text-muted-foreground">
                {{ authStore.user?.email || '—' }}
              </p>
            </div>
          </DropdownMenuLabel>
          <DropdownMenuSeparator />
          <DropdownMenuGroup>
            <DropdownMenuItem @select.prevent="avatarDialogOpen = true">
              <User class="mr-2 size-4" />
              <span>个人资料 / 更换头像</span>
            </DropdownMenuItem>
            <DropdownMenuItem>
              <Settings2 class="mr-2 size-4" />
              <span>系统设置</span>
            </DropdownMenuItem>
          </DropdownMenuGroup>
          <DropdownMenuSeparator />
          <DropdownMenuItem
            class="text-destructive focus:text-destructive"
            @click="handleLogout"
          >
            <LogOut class="mr-2 size-4" />
            <span>退出登录</span>
          </DropdownMenuItem>
        </DropdownMenuContent>
      </DropdownMenu>
    </div>

    <AdminAvatarCropper v-model="avatarDialogOpen" />
  </header>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { Button } from '~~/components/ui/button'
import {
  SidebarTrigger
} from '~~/components/ui/sidebar'
import {
  Breadcrumb,
  BreadcrumbList,
  BreadcrumbItem,
  BreadcrumbLink,
  BreadcrumbPage,
  BreadcrumbSeparator
} from '~~/components/ui/breadcrumb'
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
import {
  Search,
  Bell,
  User,
  Settings2,
  LogOut
} from '@lucide/vue'
import ThemeToggle from './ThemeToggle.vue'
import ThemePaletteSwitcher from './ThemePaletteSwitcher.vue'
import AdminAvatarCropper from './AdminAvatarCropper.vue'
import { useAuthStore } from '~~/stores/auth'

interface BreadcrumbItem {
  label: string
  href?: string
}

defineProps<{
  breadcrumbItems?: BreadcrumbItem[]
}>()

const authStore = useAuthStore()
const avatarDialogOpen = ref(false)

const handleLogout = async () => {
  await authStore.logout()
  await navigateTo('/login')
}
</script>
