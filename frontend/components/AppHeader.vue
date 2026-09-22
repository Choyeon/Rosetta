<script setup lang="ts">
import { watch, computed, onMounted } from 'vue'
import {
  Menu, Search, LogOut, User, ChevronDown
} from '~~/lib/lucide-svg-icons'
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

const { t, locale } = useI18n()
const authStore = useAuthStore()
const route = useRoute()

// 极简主题（astro-paper-inspired）导航栏模式：
//   · show_avatar === false → data-navbar-minimal="text-only"（style.css 隐藏 logo img，只留站名文字）
//   · 其余情况（含非极简主题）→ "default"
// 仅在极简主题激活时才允许 text-only，避免影响默认 Editorial 主题导航。
const ft = useFrontendTheme()
const MINIMAL_THEME_SLUGS = new Set<string>(['astro-paper-inspired'])
const navbarMinimalMode = computed<'default' | 'text-only'>(() => {
  if (!MINIMAL_THEME_SLUGS.has(ft.slug.value || '')) return 'default'
  return ft.mods.value.show_avatar === false ? 'text-only' : 'default'
})

/**
 * Header 导航栏（当前仅默认 Editorial 主题）：
 * 完整中文菜单 + 登录 / 注册按钮显式 + 登录后进入后台。
 *
 * 去重规则：导航后端返回可能重复（用户配置时误加 2 次同 to）。按 to 路径去重。
 * 移动端：≥md 显示完整中文；<md 统一折叠进 Sheet（左侧抽屉），仍然有登录/注册/进入后台。
 */

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

// 内置兜底（非极简主题 fallback）—— 当后端 /api/navigations 为空或请求失败时使用。
// 保留核心必要页面：首页 / 文章 / 分类 / 标签 / 归档 + 两个高权重静态页（关于 / 留言板）。
// 这样即便用户 DB 中 navigation_menu 表未 seed，顶部导航也永远不会缺链接。
const FALLBACK_NAV: { label: string, to: string }[] = [
  { label: t('nav.home') || '首页', to: '/' },
  { label: t('nav.posts') || '文章', to: '/posts' },
  { label: t('nav.categories') || '分类', to: '/categories' },
  { label: t('nav.tags') || '标签', to: '/tags' },
  { label: t('nav.archive') || '归档', to: '/archive' },
  { label: t('nav.about') || t('common.about') || t('about.title') || '关于', to: '/about' },
  { label: t('nav.friends') || t('friends.title') || '友情链接', to: '/friends' },
  { label: t('nav.gallery') || t('gallery.title') || '相册', to: '/gallery' },
  { label: t('nav.guestbook') || t('common.guestbook') || t('guestbook.title') || '留言板', to: '/guestbook' }
]

/**
 * 保证某些路由在 Header 导航中必然渲染（即便后端菜单漏配）。
 *   · 旧 Minimal 主题强制 9 条导航，但 Editorial 默认走后端配置 navRowsRef，
 *     易出现"友情链接 / 相册"缺失 → 点不到。这里最后一步合并：缺失就补上。
 */
const ENSURE_PRESENT: { label: () => string, to: string }[] = [
  { label: () => t('nav.home') || '首页', to: '/' },
  { label: () => t('nav.posts') || '文章', to: '/posts' },
  { label: () => t('nav.categories') || '分类', to: '/categories' },
  { label: () => t('nav.tags') || '标签', to: '/tags' },
  { label: () => t('nav.archive') || '归档', to: '/archive' },
  { label: () => t('nav.about') || t('common.about') || t('about.title') || '关于', to: '/about' },
  { label: () => t('nav.friends') || t('friends.title') || '友情链接', to: '/friends' },
  { label: () => t('nav.gallery') || t('gallery.title') || '相册', to: '/gallery' },
  { label: () => t('nav.guestbook') || t('common.guestbook') || t('guestbook.title') || '留言板', to: '/guestbook' }
]

const { data: navRowsRef, refresh: refreshNav } = useAPI<NavApiRow[]>('/navigations', {
  key: 'public:navigations:' + locale.value,
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

/**
 * 去重：按 to 字段保留第一次出现（解决用户截图里"关于 × 2 连续出现"的问题）。
 */
const dedupeByTo = <T extends { to: string }>(arr: ReadonlyArray<T>): T[] => {
  const seen = new Set<string>()
  const out: T[] = []
  for (const it of arr) {
    if (seen.has(it.to)) continue
    seen.add(it.to)
    out.push(it)
  }
  return out
}

const navItems = computed(() => {
  const _ = locale.value // 显式建立响应式依赖：语言切换 → 标签重新 pickNavStr
  const raw = navRowsRef.value
  if (!Array.isArray(raw) || raw.length === 0) return dedupeByTo(FALLBACK_NAV)
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
  const base = out.length > 0 ? out : FALLBACK_NAV
  // Merge ensure: 若后端未配置友情/相册等关键路径，按 ENSURE_PRESENT 顺序补齐在末尾
  for (const req of ENSURE_PRESENT) {
    if (base.some(x => x.to === req.to)) continue
    const label = req.label()
    if (!label) continue
    base.push({ label, to: req.to })
  }
  return dedupeByTo(base)
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
    :data-navbar-minimal="navbarMinimalMode"
    class="sticky top-0 z-40 w-full border-b bg-background/80 backdrop-blur supports-[backdrop-filter]:bg-background/60"
  >
    <div
      class="container mx-auto flex items-center justify-between gap-4 h-16"
    >
      <NuxtLink
        to="/"
        data-navbar="brand"
        class="flex items-center gap-2 font-display font-bold tracking-tight min-w-0 shrink-0 text-lg sm:text-xl"
      >
        <img
          :src="brandLogo"
          :alt="brandName"
          role="brand-logo"
          class="h-7 w-auto object-contain shrink-0"
        >
        <span
          class="whitespace-nowrap overflow-hidden text-ellipsis max-w-[40vw] sm:max-w-[46vw] md:max-w-[50vw]"
          :title="brandName"
        >{{ brandName }}</span>
      </NuxtLink>

      <nav
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
                <Search data-icon="inline-start" />
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
                <Menu data-icon="inline-start" />
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
                      :name="userDisplayName || 'U'"
                      :size="40"
                      :show-title="false"
                    />
                    <div class="min-w-0">
                      <div class="text-sm font-medium truncate">
                        {{ userDisplayName }}
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
                        <User
                          data-icon="inline-start"
                          class="mr-2"
                        />
                        {{ t('common.dashboard') || 'Dashboard' }}
                      </Button>
                    </SheetClose>
                    <Button
                      variant="ghost"
                      size="sm"
                      class="justify-start text-error"
                      @click="handleLogout"
                    >
                      <LogOut
                        data-icon="inline-start"
                        class="mr-2"
                      />
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
