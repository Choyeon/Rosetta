<script setup lang="ts">
import { computed } from 'vue'
import { Menu, Search, LogOut, User, ChevronDown } from '@lucide/vue'
import { Button } from '~~/components/ui/button'
import {
  DropdownMenu,
  DropdownMenuTrigger,
  DropdownMenuContent,
  DropdownMenuLabel,
  DropdownMenuGroup,
  DropdownMenuItem,
  DropdownMenuSeparator
} from '~~/components/ui/dropdown-menu'
import {
  Sheet,
  SheetTrigger,
  SheetContent,
  SheetHeader,
  SheetTitle,
  SheetClose
} from '~~/components/ui/sheet'
import { Avatar, AvatarFallback, AvatarImage } from '~~/components/ui/avatar'
import { Separator } from '~~/components/ui/separator'
import { Tooltip, TooltipContent, TooltipTrigger } from '~~/components/ui/tooltip'
import { useAuthStore } from '~~/stores/auth'
import { useI18n } from 'vue-i18n'
import ThemeToggle from '~~/components/ThemeToggle.vue'
import LocaleSwitcher from '~~/components/LocaleSwitcher.vue'

const { t, locale } = useI18n()
const authStore = useAuthStore()
const route = useRoute()

// ===== 站点品牌：layouts/default.vue 里已经 await useSite().ensureLoaded() =====
// 所以这里 state 已填充完毕；SSR 和客户端首渲染的 brandName/brandLogo 字节级一致。
const site = useSite()
const brandName = computed(() => site.basic.value.site_name || 'Rosetta')
const brandLogo = computed(() => site.basic.value.logo || '/logo/rosetta-primary-icon.png')

interface NavApiRow {
  id?: number | string
  label?: string | Record<string, string>
  title?: string | Record<string, string>
  name?: string | Record<string, string>
  to?: string
  url?: string
  href?: string
  path?: string
  slug?: string
  link_type?: string
  is_external?: boolean
  target?: string
  sort_order?: number
}

// 内置兜底（极简、无示例数据）——当后端 /api/navigations 为空或请求失败时使用。
// 仅保留站点核心必要页面路由，不延伸任何推荐性菜单。
const FALLBACK_NAV: { label: string, to: string }[] = [
  { label: t('nav.home') || '首页', to: '/' },
  { label: t('nav.posts') || '文章', to: '/posts' },
  { label: t('nav.categories') || '分类', to: '/categories' },
  { label: t('nav.tags') || '标签', to: '/tags' },
  { label: t('nav.archive') || '归档', to: '/archive' }
]

const { data: navRowsRef } = await useAPI<NavApiRow[]>('/navigations', {
  key: 'public:navigations',
  default: () => []
})

const pickNavStr = (v: string | Record<string, string> | null | undefined, fb: string): string => {
  if (v == null) return fb
  if (typeof v === 'string') return v || fb
  const l = locale.value as string
  if (l && v[l]) return v[l] || fb
  const keys = Object.keys(v)
  const first = keys[0]
  return (first ? v[first] : '') || fb
}

const navItems = computed(() => {
  const raw = navRowsRef.value
  if (!Array.isArray(raw) || raw.length === 0) return FALLBACK_NAV
  const out: { label: string, to: string, external?: boolean }[] = []
  for (const row of raw) {
    const labelRaw = row.label ?? row.title ?? row.name ?? ''
    const label = pickNavStr(labelRaw as string | Record<string, string> | null | undefined, '')
    if (!label) continue
    const path = (row.to ?? row.url ?? row.href ?? row.path ?? row.slug ?? '') as string
    if (!path) continue
    const external = Boolean(row.is_external || row.link_type === 'external' || row.target === '_blank' || /^https?:\/\//i.test(path))
    if (external) {
      // 外链不进入 navItems（避免内部路由解析出错），前台 header 暂不渲染外链
      continue
    }
    out.push({ label, to: path })
  }
  return out.length > 0 ? out : FALLBACK_NAV
})

const isActive = (to: string) => {
  if (to === '/') return route.path === '/'
  return route.path === to || route.path.startsWith(to + '/')
}

const handleLogout = async () => {
  await authStore.logout()
  navigateTo('/')
}

const handleLogin = () => navigateTo('/login')
const handleRegister = () => navigateTo('/register')
const handleAdmin = () => navigateTo('/admin')
</script>

<template>
  <header class="sticky top-0 z-40 w-full border-b bg-background/80 backdrop-blur supports-[backdrop-filter]:bg-background/60">
    <div class="container mx-auto flex h-16 items-center justify-between gap-4">
      <NuxtLink
        to="/"
        class="flex items-center gap-2 font-display text-xl font-bold tracking-tight"
      >
        <img
          :src="brandLogo"
          :alt="brandName"
          class="h-7 w-auto object-contain"
        >
        <span>{{ brandName }}</span>
      </NuxtLink>

      <nav class="md:flex hidden items-center gap-1">
        <NuxtLink
          v-for="item in navItems"
          :key="item.to"
          :to="item.to"
          :class="[
            'px-3 py-2 text-sm font-medium rounded-md transition-colors hover:bg-accent hover:text-accent-foreground',
            isActive(item.to) ? 'bg-accent text-accent-foreground' : 'text-foreground/60 hover:text-foreground'
          ]"
        >
          {{ item.label }}
        </NuxtLink>
      </nav>

      <div class="flex items-center gap-1">
        <Tooltip>
          <TooltipTrigger as-child>
            <Button
              variant="ghost"
              size="icon"
              :aria-label="t('common.search') || '搜索'"
            >
              <Search class="h-[1.2rem] w-[1.2rem]" />
            </Button>
          </TooltipTrigger>
          <TooltipContent>
            <p>{{ t('common.search') || '搜索' }}</p>
          </TooltipContent>
        </Tooltip>

        <LocaleSwitcher />
        <ThemeToggle />

        <div
          v-if="!authStore.isAuthenticated"
          class="ml-1 flex items-center gap-2"
        >
          <Button
            variant="outline"
            size="sm"
            @click="handleLogin"
          >
            {{ t('auth.login') || '登录' }}
          </Button>
          <Button
            variant="default"
            size="sm"
            @click="handleRegister"
          >
            {{ t('auth.register') || '注册' }}
          </Button>
        </div>

        <DropdownMenu v-else>
          <DropdownMenuTrigger as-child>
            <Button
              variant="ghost"
              size="icon"
              class="relative rounded-full h-9 w-9 p-0"
            >
              <Avatar class="h-8 w-8">
                <AvatarImage
                  v-if="authStore.user?.avatar"
                  :src="authStore.user.avatar"
                  :alt="authStore.user.name || authStore.user.username || ''"
                />
                <AvatarFallback>{{ String((authStore.user as any)?.name || authStore.user?.username || '').charAt(0).toUpperCase() || 'U' }}</AvatarFallback>
              </Avatar>
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent
            align="end"
            class="w-56"
          >
            <DropdownMenuLabel class="font-normal p-3">
              <div class="flex items-center gap-3">
                <Avatar class="h-10 w-10">
                  <AvatarImage
                    v-if="authStore.user?.avatar"
                    :src="authStore.user.avatar"
                    :alt="authStore.user.name || authStore.user.username || ''"
                  />
                  <AvatarFallback>{{ String((authStore.user as any)?.name || authStore.user?.username || '').charAt(0).toUpperCase() || 'U' }}</AvatarFallback>
                </Avatar>
                <div class="space-y-0.5 min-w-0">
                  <div class="text-sm font-medium truncate">
                    {{ authStore.user?.name || authStore.user?.username }}
                  </div>
                  <div
                    v-if="authStore.user?.email"
                    class="text-xs text-muted-foreground truncate"
                  >
                    {{ authStore.user.email }}
                  </div>
                </div>
              </div>
            </DropdownMenuLabel>
            <DropdownMenuSeparator />
            <DropdownMenuGroup>
              <DropdownMenuItem @click="handleAdmin">
                <User class="mr-2 h-4 w-4" />
                <span>{{ t('common.dashboard') || 'Dashboard' }}</span>
              </DropdownMenuItem>
              <DropdownMenuItem @click="handleAdmin">
                <ChevronDown class="mr-2 h-4 w-4" />
                <span>{{ t('common.settings') || '设置' }}</span>
              </DropdownMenuItem>
            </DropdownMenuGroup>
            <DropdownMenuSeparator />
            <DropdownMenuItem
              class="text-error"
              @click="handleLogout"
            >
              <LogOut class="mr-2 h-4 w-4" />
              <span>{{ t('auth.logout') || '退出登录' }}</span>
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>

        <Sheet>
          <SheetTrigger as-child>
            <Button
              variant="ghost"
              size="icon"
              class="md:hidden"
              :aria-label="t('common.titleMenu') || 'Menu'"
            >
              <Menu class="h-[1.2rem] w-[1.2rem]" />
            </Button>
          </SheetTrigger>
          <SheetContent
            side="left"
            class="w-[85%] max-w-sm flex flex-col"
          >
            <SheetHeader class="text-left mb-4">
              <SheetTitle class="sr-only">
                {{ t('common.titleMenu') || 'Menu' }}
              </SheetTitle>
              <NuxtLink
                to="/"
                class="flex items-center gap-2 font-display text-xl font-bold tracking-tight"
              >
                <img
                  :src="brandLogo"
                  :alt="brandName"
                  class="h-7 w-auto object-contain"
                >
                <span>{{ brandName }}</span>
              </NuxtLink>
            </SheetHeader>
            <Separator class="mb-4" />
            <nav class="flex flex-col gap-1 mb-6">
              <SheetClose
                v-for="item in navItems"
                :key="item.to"
                as-child
              >
                <NuxtLink
                  :to="item.to"
                  :class="[
                    'px-3 py-2.5 text-sm font-medium rounded-md transition-colors hover:bg-accent hover:text-accent-foreground',
                    isActive(item.to) ? 'bg-accent text-accent-foreground' : 'text-foreground/60 hover:text-foreground'
                  ]"
                >
                  {{ item.label }}
                </NuxtLink>
              </SheetClose>
            </nav>
            <Separator class="mb-4" />
            <div class="mb-6">
              <template v-if="authStore.isAuthenticated">
                <div class="flex items-center gap-3 px-2 py-2 rounded-md hover:bg-accent mb-2">
                  <Avatar class="h-10 w-10">
                    <AvatarImage
                      v-if="authStore.user?.avatar"
                      :src="authStore.user.avatar"
                      :alt="authStore.user.name || authStore.user.username || ''"
                    />
                    <AvatarFallback>{{ String((authStore.user as any)?.name || authStore.user?.username || '').charAt(0).toUpperCase() || 'U' }}</AvatarFallback>
                  </Avatar>
                  <div class="min-w-0">
                    <div class="text-sm font-medium truncate">
                      {{ authStore.user?.name || authStore.user?.username }}
                    </div>
                    <div
                      v-if="authStore.user?.email"
                      class="text-xs text-muted-foreground truncate"
                    >
                      {{ authStore.user.email }}
                    </div>
                  </div>
                </div>
                <div class="flex flex-col gap-1">
                  <SheetClose as-child>
                    <Button
                      variant="ghost"
                      size="sm"
                      class="justify-start"
                      @click="handleAdmin"
                    >
                      <User class="mr-2 h-4 w-4" />
                      {{ t('common.dashboard') || 'Dashboard' }}
                    </Button>
                  </SheetClose>
                  <Button
                    variant="ghost"
                    size="sm"
                    class="justify-start text-error"
                    @click="handleLogout"
                  >
                    <LogOut class="mr-2 h-4 w-4" />
                    {{ t('auth.logout') || '退出登录' }}
                  </Button>
                </div>
              </template>
              <template v-else>
                <div class="flex flex-col gap-2">
                  <Button
                    variant="outline"
                    class="w-full"
                    @click="handleLogin"
                  >
                    {{ t('auth.login') || '登录' }}
                  </Button>
                  <Button
                    variant="default"
                    class="w-full"
                    @click="handleRegister"
                  >
                    {{ t('auth.register') || '注册' }}
                  </Button>
                </div>
              </template>
            </div>
            <Separator class="mb-4" />
            <div class="flex items-center justify-end gap-1 ml-auto">
              <LocaleSwitcher />
              <ThemeToggle />
            </div>
          </SheetContent>
        </Sheet>
      </div>
    </div>
  </header>
</template>
