<script setup lang="ts">
import { watch, computed, onMounted } from 'vue'
import {
  Menu, Search, LogOut, User, ChevronDown,
  LayoutGrid, Tags, Archive, MessageSquareText
} from '@lucide/vue'
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
import UserAvatar from '~~/components/UserAvatar.vue'
import { Separator } from '~~/components/ui/separator'
import { Tooltip, TooltipContent, TooltipTrigger } from '~~/components/ui/tooltip'
import { useAuthStore } from '~~/stores/auth'
import { useI18n } from 'vue-i18n'
import ThemeToggle from '~~/components/ThemeToggle.vue'
import LocaleSwitcher from '~~/components/LocaleSwitcher.vue'
import { useFrontendTheme } from '~~/composables/useFrontendTheme'

const { t, locale } = useI18n()
const authStore = useAuthStore()
const route = useRoute()
const ft = useFrontendTheme()

/**
 * 极简主题判定：只要 slug 属于 Minimal Paper 系列（astro-paper-inspired / minimal-brutalist），
 * 就给 <header> 挂 data-navbar-minimal 属性，让主题 style.css 里的极简 navbar 规则命中。
 * 与 pages/index.vue 的 isMinimalTheme 判断保持语义一致。
 */
const MINIMAL_THEME_SLUGS = new Set(['astro-paper-inspired', 'minimal-brutalist'])
const isMinimalTheme = computed(() => {
  const s = ft.slug.value
  return !!s && MINIMAL_THEME_SLUGS.has(s)
})
const navVariant = computed(() => (isMinimalTheme.value ? 'minimal' : 'default'))

/**
 * 极简主题桌面 nav 的"3 文字 + N 图标"分类（复刻 Astro Paper 5 项原则：3 文字 + 2 图标）。
 * 中文默认 7 项导航 → 文字保留 3 项（首页/文章/关于），其余 4 项变为 32×32 SVG 纯图标（sr-only 文字）。
 * 路径严格匹配 FALLBACK_NAV，若用户自定义了导航里不存在的路径，则全部保持文字形式。
 */
const MINIMAL_ICON_MENU_PATHS: Record<string, string> = {
  '/categories': 'categories',
  '/tags': 'tags',
  '/archive': 'archive',
  '/guestbook': 'guestbook',
  '/announcements': 'announcements'
}
// 极简主题下作为"文字链接"显示（最多 3 项以节约宽度）
const MINIMAL_TEXT_MENU_PATHS = new Set(['/', '/posts', '/about'])

const minimalTextItems = computed(() => {
  if (!isMinimalTheme.value) return navItems.value
  return navItems.value.filter(i => MINIMAL_TEXT_MENU_PATHS.has(i.to))
})
const minimalIconItems = computed(() => {
  if (!isMinimalTheme.value) return []
  return navItems.value
    .filter(i => !MINIMAL_TEXT_MENU_PATHS.has(i.to) && MINIMAL_ICON_MENU_PATHS[i.to])
    .map(i => ({
      ...i,
      iconKey: MINIMAL_ICON_MENU_PATHS[i.to]
    }))
})
// 极简模式下，如果用户自定义菜单很多（>4 项图标）且不在白名单映射中 → 保留文字但只渲染前 4 个其余进 sheet
const minimalOverflowTextItems = computed(() => {
  if (!isMinimalTheme.value) return []
  return navItems.value.filter(
    i => !MINIMAL_TEXT_MENU_PATHS.has(i.to) && !MINIMAL_ICON_MENU_PATHS[i.to]
  )
})

const resolveIcon = (iconKey: string) => {
  switch (iconKey) {
    case 'categories': return LayoutGrid
    case 'tags': return Tags
    case 'archive': return Archive
    case 'guestbook': return MessageSquareText
    case 'announcements': return Tags
    default: return LayoutGrid
  }
}

// 显示名：优先 nickname → name → username，避免出现"用户名/登录名"而非昵称
const userDisplayName = computed(() => {
  const u = authStore.user as Record<string, unknown> | null
  return String((u?.nickname ?? u?.name ?? u?.username ?? '') as string) || ''
})

// Hydration 安全守卫：SSR 时 authStore 没有 localStorage 回填，渲染纯 fallback
const userInfoReady = useState('appheader-user-info-ready', () => false)
onMounted(() => {
  // 延后一帧，避免同一微任务内切换导致的客户端立即替换
  requestAnimationFrame(() => {
    userInfoReady.value = true
  })
})

// SSR 与客户端首帧（ready=false）统一输出空值 → 两者 DOM 一致，无 mismatch
const safeDisplayName = computed(() => (userInfoReady.value ? userDisplayName.value : ''))

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
// 保留核心必要页面：首页 / 文章 / 分类 / 标签 / 归档 + 两个高权重静态页（关于 / 留言板）。
// 这样即便用户 DB 中 navigation_menu 表未 seed，顶部导航也永远不会缺链接。
const FALLBACK_NAV: { label: string, to: string }[] = [
  { label: t('nav.home') || '首页', to: '/' },
  { label: t('nav.posts') || '文章', to: '/posts' },
  { label: t('nav.categories') || '分类', to: '/categories' },
  { label: t('nav.tags') || '标签', to: '/tags' },
  { label: t('nav.archive') || '归档', to: '/archive' },
  { label: t('nav.about') || t('common.about') || t('about.title') || '关于', to: '/about' },
  { label: t('nav.guestbook') || t('common.guestbook') || t('guestbook.title') || '留言板', to: '/guestbook' }
]

const { data: navRowsRef, refresh: refreshNav } = await useAPI<NavApiRow[]>('/navigations', {
  key: computed(() => `public:navigations:${locale.value}`),
  default: () => []
})
// 语言切换时，用新的 Accept-Language 头重新拉导航（否则导航仍缓存旧语言的 label/i18n）
watch(locale, () => void refreshNav())

const pickNavStr = (v: string | Record<string, string> | null | undefined, fb: string): string => {
  if (v == null) return fb
  if (typeof v === 'string') return v || fb
  const l = locale.value as string
  if (l && v[l]) return v[l] || fb
  const keys = Object.keys(v)
  const first = keys[0]
  return (first ? v[first] : '') || fb
}

/**
 * 规范化后端导航菜单返回的内部 URL 路径。
 * — 历史兼容：旧 Astro 站点和老数据会保存 "/page/about"、"/page/guestbook"
 *   等带 "/page/" 前缀的路径。Nuxt 前端静态页位于 pages/about.vue、
 *   pages/guestbook.vue 等（不含前缀）。需要移除前缀才能命中真实路由。
 * — 独立页 slug：当 link_type==="page" 且字段含 slug 时，按 "/<slug>" 归一化。
 * — 末尾 "/"：除首页 "/" 外统一去重，避免 "/posts/" 和 "/posts" 被视为不同激活。
 */
const normalizeNavPath = (row: NavApiRow): string => {
  let raw: string = ''
  if (row.link_type === 'page' && row.slug) {
    raw = `/${String(row.slug).replace(/^\/+/, '')}`
  } else {
    raw = String(row.to ?? row.url ?? row.href ?? row.path ?? row.slug ?? '').trim()
  }
  if (!raw) return ''
  if (/^https?:\/\//i.test(raw)) return raw

  // 规范化：相对路径按内部路由处理，统一前缀 "/"
  if (!raw.startsWith('/') && !raw.startsWith('#')) {
    raw = `/${raw}`
  }
  // 兼容 "/page/<slug>" 旧前缀 → 折去 "/page"
  if (raw.startsWith('/page/')) raw = raw.slice('/page'.length) || '/'
  else if (raw === '/page') raw = '/'

  // 去重末尾斜杠（首页保留）
  if (raw.length > 1 && raw.endsWith('/')) raw = raw.slice(0, -1)
  return raw
}

const navItems = computed(() => {
  const _ = locale.value // 显式建立响应式依赖：语言切换 → 标签重新 pickNavStr
  const raw = navRowsRef.value
  if (!Array.isArray(raw) || raw.length === 0) return FALLBACK_NAV
  const out: { label: string, to: string, external?: boolean }[] = []
  for (const row of raw) {
    const labelRaw = row.label ?? row.title ?? row.name ?? ''
    const label = pickNavStr(labelRaw as string | Record<string, string> | null | undefined, '')
    if (!label) continue
    const path = normalizeNavPath(row)
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
const handleSearchClick = () => navigateTo('/search')
</script>

<template>
  <header
    id="app-header"
    data-navbar="root"
    :data-navbar-minimal="navVariant"
    :data-navbar-icon-menu="isMinimalTheme ? 'on' : null"
    class="sticky top-0 z-40 w-full border-b bg-background/80 backdrop-blur supports-[backdrop-filter]:bg-background/60"
  >
    <div
      class="container mx-auto flex items-center justify-between gap-4"
      :class="isMinimalTheme ? 'h-16 sm:h-[72px]' : 'h-16'"
    >
      <NuxtLink
        to="/"
        data-navbar="brand"
        class="flex items-center gap-2 font-display font-bold tracking-tight"
        :class="isMinimalTheme ? 'text-xl sm:text-2xl' : 'text-xl'"
      >
        <img
          v-if="!isMinimalTheme"
          :src="brandLogo"
          :alt="brandName"
          role="brand-logo"
          class="h-7 w-auto object-contain"
        >
        <!-- 极简主题 logo 图片更紧凑：h-6 24px，与 Astro Paper text-2xl logo 高度匹配 -->
        <img
          v-else
          :src="brandLogo"
          :alt="brandName"
          role="brand-logo"
          class="h-6 w-auto object-contain"
        >
        <span>{{ brandName }}</span>
      </NuxtLink>

      <nav
        v-if="!isMinimalTheme"
        data-navbar="menu"
        class="md:flex hidden items-center gap-1"
      >
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

      <!-- Minimal 主题桌面导航：复刻 Astro Paper → 3 文字 + N 图标（≥lg 展开；md 以下走 Sheet 汉堡） -->
      <nav
        v-else
        data-navbar="menu"
        data-navbar-role="minimal-desktop"
        class="lg:flex hidden items-center"
      >
        <NuxtLink
          v-for="item in minimalTextItems"
          :key="item.to"
          :to="item.to"
          :class="[
            'px-2 py-1 text-base font-medium rounded-none transition-colors whitespace-nowrap',
            isActive(item.to) ? 'bg-transparent font-bold text-foreground' : 'text-foreground/80 hover:text-foreground'
          ]"
          :aria-current="isActive(item.to) ? 'page' : undefined"
        >
          {{ item.label }}
        </NuxtLink>

        <!-- 4 个"低频/可图标化"菜单：分类 LayoutGrid / 标签 Tags / 归档 Archive / 留言板 MessageSquare -->
        <div
          v-if="minimalIconItems.length"
          data-navbar-icon-group
          class="flex items-center gap-x-4 ml-2"
        >
          <NuxtLink
            v-for="item in minimalIconItems"
            :key="'icon-' + item.to"
            :to="item.to"
            data-navbar-role="icon-only"
            class="relative inline-flex items-center justify-center w-8 h-8 rounded-none hover:text-accent transition-colors"
            :title="item.label"
            :aria-label="item.label"
            :aria-current="isActive(item.to) ? 'page' : undefined"
          >
            <component
              :is="resolveIcon(item.iconKey as string)"
              class="w-6 h-6"
              :stroke-width="isActive(item.to) ? 2.25 : 2"
              :class="isActive(item.to) ? 'stroke-accent' : ''"
            />
            <span class="sr-only" data-text>{{ item.label }}</span>
            <!-- 激活态下在图标下方显示 1.5px 细底线（与文字项视觉等价） -->
            <span
              v-if="isActive(item.to)"
              class="absolute left-1/2 -translate-x-1/2 bottom-0 w-6 h-[1.5px] bg-current rounded-full"
              aria-hidden="true"
            />
          </NuxtLink>
        </div>

        <!-- 用户自定义导航（不在映射白名单）作为少量文字保留，超过 2 个省略展示（mobile sheet 中依然完整） -->
        <div
          v-if="minimalOverflowTextItems.length"
          class="ml-2 hidden xl:flex items-center gap-3"
        >
          <NuxtLink
            v-for="item in minimalOverflowTextItems.slice(0, 2)"
            :key="'ov-' + item.to"
            :to="item.to"
            class="px-2 py-1 text-sm font-medium whitespace-nowrap text-foreground/80 hover:text-foreground"
            :aria-current="isActive(item.to) ? 'page' : undefined"
          >
            {{ item.label }}
          </NuxtLink>
        </div>
      </nav>

      <!-- 交互控件区：Tooltip/DropdownMenu/Sheet 基于 reka-ui，SSR 渲染 PrimitiveSlot 不稳定；
           且内容与用户登录态/主题偏好/语言选择强耦合，统一 ClientOnly 隔离避免 mismatch。
           Logo 与导航菜单（上方）保持 SSR，对 SEO 和首屏无影响。 -->
      <ClientOnly>
        <div
          data-navbar="actions"
          class="flex items-center gap-1"
        >
          <Tooltip>
            <TooltipTrigger as-child>
              <Button
                variant="ghost"
                size="icon"
                :aria-label="t('common.search') || '搜索'"
                @click="handleSearchClick"
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
                class="relative rounded-full h-9 w-9 p-0 overflow-hidden shrink-0"
              >
                <UserAvatar
                  :resolved-avatar-url="userInfoReady ? (authStore.user as Record<string, unknown> | null)?.resolved_avatar_url as string : ''"
                  :avatar="userInfoReady ? (authStore.user as Record<string, unknown> | null)?.avatar as string : ''"
                  :name="safeDisplayName || 'U'"
                  :size="28"
                  :show-title="false"
                />
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent
              align="end"
              class="w-56"
            >
              <DropdownMenuLabel class="font-normal p-3">
                <div class="flex items-center gap-3">
                  <UserAvatar
                    :resolved-avatar-url="userInfoReady ? (authStore.user as Record<string, unknown> | null)?.resolved_avatar_url as string : ''"
                    :avatar="userInfoReady ? (authStore.user as Record<string, unknown> | null)?.avatar as string : ''"
                    :name="safeDisplayName || 'U'"
                    :size="40"
                    :show-title="false"
                  />
                  <div class="flex flex-col gap-0.5 min-w-0">
                    <div class="text-sm font-medium truncate">
                      {{ safeDisplayName || '未登录' }}
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
                    <UserAvatar
                      :resolved-avatar-url="(authStore.user as Record<string, unknown> | null)?.resolved_avatar_url as string || ''"
                      :avatar="(authStore.user as Record<string, unknown> | null)?.avatar as string || ''"
                      :name="String((authStore.user as any)?.name || authStore.user?.username || 'U')"
                      :size="40"
                      :show-title="false"
                    />
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
        <template #fallback>
          <!-- SSR 回退占位：宽高与实际控件区一致，避免首屏布局抖动（CLS） -->
          <div
            class="flex items-center gap-1"
            aria-hidden="true"
          >
            <span class="size-10 shrink-0" />
            <span class="size-10 shrink-0" />
            <span class="size-10 shrink-0" />
            <span class="ml-1 h-9 w-16 shrink-0 rounded-md border border-transparent" />
            <span class="h-9 w-16 shrink-0 rounded-md" />
          </div>
        </template>
      </ClientOnly>
    </div>
  </header>
</template>
