<!--
  前台顶栏：品牌 + 主导航（GET /navigations?location=header）+ 右侧交互控件区。
  契约一：lib/navigation.ts 的 normalizeNavRowUrl 负责把历史 /page/<slug> 数据折回真实路由并去尾斜杠，
  删它会让旧菜单直接 404；外链行被有意排除在 navItems 之外。
  契约二：控件区整体 <ClientOnly>（reka-ui 弹层 SSR 输出不稳 + 登录态强耦合），fallback
  占位尺寸与实际控件对齐以防 CLS；用户名字段须等 userInfoReady 延后一帧再显示。
-->
<script setup lang="ts">
import { watch, computed, onMounted } from 'vue'
import {
  Menu, Search, LogOut, User, UserCircle2, Settings, ChevronDown, MessageSquare, Bell
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
import ThemeToggle from '~~/components/ThemeToggle.vue'
import { Separator } from '~~/components/ui/separator'
import { Tooltip, TooltipContent, TooltipTrigger } from '~~/components/ui/tooltip'
import { useAuthStore } from '~~/stores/auth'
import { useI18n } from 'vue-i18n'
import LocaleSwitcher from '~~/components/LocaleSwitcher.vue'
import DynamicIcon from '~~/components/DynamicIcon.vue'
import { MINIMAL_THEME_SLUGS } from '~~/lib/rosetta-themes'
import { flattenNavLinks, isNavActive, navRowsToLinks, dedupeByTo, type NavApiRow, type NavLink } from '~~/lib/navigation'

const { t, locale } = useI18n()
const authStore = useAuthStore()
const route = useRoute()
const { localeHref } = useLocaleLink()

/**
 * Header 导航栏：
 *  · 品牌为纯文字（logo 图片由各主题 style.css 决定是否展示）
 *  · 桌面主菜单（lg 起，版心最窄的一档实测能容纳 5 项 + 「更多」）：前 NAV_PRIMARY_MAX 项常驻，
 *    其余收进「更多」下拉；默认主题另有平铺档（见 NAV_FLAT_MAX 与 flatOverflowAtWide）。
 *    主题骨架差异走 MINIMAL_THEME_SLUGS 分支，不允许一个主题的排版约束泄漏到另一个主题。
 *  · 每个导航项都带 whitespace-nowrap + shrink-0：中文标签可以在任意字符处断行，
 *    一旦 flex 容器把项压到内容宽度以下就会竖排成"留言板"三行，把 h-16 的单行顶栏撑坏。
 *  · lg 以下一律折叠进 Sheet（与导航同一个断点，两处必须一起改，否则中间带宽屏既无导航也无汉堡）
 *  · 右侧控件：搜索 / 明暗切换 / 语言切换（文字标签）/ 登录态
 */
const ft = useFrontendTheme()
const isMinimalTheme = computed<boolean>(() => MINIMAL_THEME_SLUGS.has(ft.slug.value || ''))

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

// features 分组关掉功能时顶栏入口必须消失；navigation 分组是同一层的显示开关，两者取与。
const showSearch = computed(() => site.features.value.enable_search && site.navigation.value.show_search)
const showRegister = computed(() => site.features.value.enable_registration)
const showDarkModeToggle = computed(() => site.features.value.enable_dark_mode && site.navigation.value.show_theme_toggle)
const showLanguageSwitch = computed(() => site.navigation.value.show_language_switch)
// header_style 只有"吸顶/随页面滚走"两种；非吸顶时去掉 sticky+top-0+z-40。
const headerClass = computed(() =>
  site.navigation.value.header_style === 'sticky'
    ? 'sticky top-0 z-40 w-full border-b bg-background/80 backdrop-blur supports-[backdrop-filter]:bg-background/60'
    : 'relative w-full border-b bg-background/80 backdrop-blur supports-[backdrop-filter]:bg-background/60'
)

// 内置兜底（非极简主题 fallback）—— 当后端 /api/navigations 为空或请求失败时使用。
// 保留核心必要页面：首页 / 文章 / 分类 / 标签 / 归档 + 两个高权重静态页（关于 / 留言板）。
// 这样即便用户 DB 中 navigation_menu 表未 seed，顶部导航也永远不会缺链接。
// 必须是函数而不是常量数组：常量在 setup 期就把当前语言烘死，语言切换后 navItems
// 会重算，但标签仍是第一次渲染时的那一版（英文页显示中文导航）。
const buildFallbackNav = (): { label: string, to: string, target?: string }[] => [
  { label: t('nav.home') || '首页', to: '/' },
  { label: t('nav.posts') || '文章', to: '/posts' },
  { label: t('nav.categories') || '分类', to: '/categories' },
  { label: t('nav.tags') || '标签', to: '/tags' },
  { label: t('nav.archive') || '归档', to: '/archive' },
  { label: t('nav.about') || t('common.about') || t('about.title') || '关于', to: '/about' },
  { label: t('nav.friends') || t('friends.title') || '友情链接', to: '/friends' },
  { label: t('nav.gallery') || t('gallery.title') || '相册', to: '/gallery' },
  { label: t('nav.activity') || t('activity.title') || '动态', to: '/activity' },
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
  { label: () => t('nav.activity') || t('activity.title') || '动态', to: '/activity' },
  { label: () => t('nav.guestbook') || t('common.guestbook') || t('guestbook.title') || '留言板', to: '/guestbook' }
]

const { data: navRowsRef, refresh: refreshNav } = useAPI<NavApiRow[]>('/navigations', {
  // 只要顶栏这一档：库里 location 是 header/footer/sidebar 三档，不带筛选时
  // 页脚与侧边栏的菜单项会整批混进顶栏（同一份 URL 在三个位置各出现一次）。
  query: { location: 'header' },
  key: 'public:navigations:header:' + locale.value,
  default: () => []
})
// 语言切换时，用新的 Accept-Language 头重新拉导航（否则导航仍缓存旧语言的 label/i18n）
watch(locale, () => void refreshNav())

const pickNavStr = (v: string | Record<string, string> | null | undefined, fb: string): string =>
  pickLocalizedText(v, locale.value as string, fb)

// URL 归一化与按 to 去重都在 lib/navigation.ts：页脚与侧边栏抽屉消费的是同一批
// 历史形态（/page/<slug>、带尾斜杠、外链），两处各写一遍必然漂移。

const navItems = computed<NavLink[]>(() => {
  const _ = locale.value // 显式建立响应式依赖：语言切换 → 标签重新 pickNavStr
  const raw = navRowsRef.value
  if (!Array.isArray(raw) || raw.length === 0) return dedupeByTo(buildFallbackNav())
  // 行 → 链接（含 parent_id 两层折叠）的唯一构造点在 lib/navigation.ts。
  // includeExternal: false —— 顶栏把链接交给 <NuxtLink :to>，外链会走内部路由解析；
  // target_blank 按 WordPress 口径翻成 target="_blank"，不再把内部页踢出导航。
  const nested = navRowsToLinks(
    raw,
    row => pickNavStr(row.label ?? row.title ?? row.name ?? '', ''),
    { includeExternal: false }
  )
  const base = nested.length > 0 ? nested : dedupeByTo(buildFallbackNav())
  // 补齐关键路由。「已存在」必须按展开后的全集判：子项同样在渲染面上
  // （移动抽屉 / 侧边栏抽屉 / 页脚），只比一级会把菜单里已有的「关于」
  // 再补一条到末尾 = 同一屏两条同链接。
  const present = new Set(flattenNavLinks(base).map(item => item.to))
  const merged = [...base]
  for (const req of ENSURE_PRESENT) {
    if (present.has(req.to)) continue
    present.add(req.to)
    const label = req.label()
    if (!label) continue
    merged.push({ label, to: req.to })
  }
  return merged
})

const isActive = (to: string) => {
  // 导航项的 to 是中性路径（/posts），而 route.path 在带前缀的语言下是 /en/posts。
  // 不先剥前缀，英文/日文/繁体页面上整条导航的高亮全都不亮（首页那条还会误亮）。
  // 判定本身与侧边栏导航共用 lib/navigation.ts，两处不得各写一遍。
  return isNavActive(route.path, to)
}

// ===== 导航分组 =====
// 折叠条数按主题取：极简主题的顶栏 gap 是 1.25rem（默认主题 gap-1 的 5 倍）、品牌字号更大，
// 1024 宽下第 5 项就已放不下；写死同一个数会让极简主题在小屏笔记本上溢出
// （导航项 nowrap，溢出表现为「更多」被裁掉 = 那些页面再也进不去）。
const NAV_PRIMARY_MAX = computed(() => (isMinimalTheme.value ? 4 : 5))
// 宽屏平铺闸门：默认主题在 2xl（版心 1536）起把溢出项也平铺出来——
// 溢出项在 SSR HTML 里始终是真实 `<a>`（下拉里的只在展开时存在），平铺让桌面爬虫读到完整内链图。
// 上限 12：按实测英文标签（最宽的一档）12 项约 944px，仍小于 2xl 下扣掉品牌与控件后的 ~1053px。
const NAV_FLAT_MAX = 12
// 展开后的全集（一级 + 子项，带 depth）。子项必须是真实 `<a>` 进 SSR：
// 「更多」下拉是 ClientOnly，爬虫读不到——后台一挂 parent_id 就让那条内链从
// 链接图里消失，等于把层级支持做成了 SEO 回退。
const flatNavItems = computed(() => flattenNavLinks(navItems.value))
const flatOverflowAtWide = computed(() =>
  !isMinimalTheme.value && flatNavItems.value.length <= NAV_FLAT_MAX
)
const primaryNavItems = computed(() => navItems.value.slice(0, NAV_PRIMARY_MAX.value))
// 顶栏永远是单行：超出闸门的一级项、以及所有子项一起算作溢出——
// 宽屏按 flatNavItems 的顺序平铺，窄处整批收进「更多」下拉。
// 两处都是同一批链接换位置，没有一项因为"没地方放"而消失。
const overflowNavItems = computed(() => {
  const visible = new Set(primaryNavItems.value.map(item => item.to))
  return flatNavItems.value.filter(item => !visible.has(item.to))
})
const moreActive = computed(() => overflowNavItems.value.some(item => isActive(item.to)))

/**
 * 站内跳转统一入口：登录 / 注册 / 搜索 / 个人中心都属于 i18n 页面，必须带上当前语言
 * 前缀；否则在 /en /ja /zh_Hant 下点「登录」会跳到中文裸路径，回访又被客户端中间件
 * 改写一次，语言与地址栏来回判逆。后台 /admin 不参与语言前缀，保留裸路径。
 */
const go = (path: string) => navigateTo(localeHref(path))

const handleLogout = async () => {
  await authStore.logout()
  navigateTo(localeHref('/'))
}

const handleLogin = () => go('/login')
const handleRegister = () => go('/register')
const handleAdmin = () => navigateTo('/admin')
const handleSearchClick = () => go('/search')
</script>

<template>
  <header
    id="app-header"
    data-navbar="root"
    :class="headerClass"
  >
    <div
      class="container mx-auto flex items-center justify-between gap-4 h-16"
    >
      <NuxtLink
        :to="localeHref('/')"
        data-navbar="brand"
        class="flex items-center gap-2 font-display font-bold tracking-tight min-w-0 shrink-0 text-lg sm:text-xl"
      >
        <img
          :src="brandLogo"
          :alt="brandName"
          data-navbar="brand-logo"
          width="112"
          height="28"
          class="h-7 w-auto object-contain shrink-0"
        >
        <span
          class="whitespace-nowrap overflow-hidden text-ellipsis max-w-[40vw] sm:max-w-[46vw] md:max-w-[50vw]"
          :title="brandName"
        >{{ brandName }}</span>
      </NuxtLink>

      <!-- hidden!/lg:flex! 必须带 important：极简主题在 [data-layout-scope=frontend] 嵌套里写了
           本导航的 display:flex，编译后选择器权重高于 Tailwind 的 .hidden，
           不加 ! 的话折叠断点在极简主题下整个失效（手机上同时出现挤压的横排导航和汉堡按钮）。 -->
      <nav
        data-navbar="menu"
        class="hidden! lg:flex! items-center gap-1 min-w-0 overflow-hidden"
      >
        <NuxtLink
          v-for="item in primaryNavItems"
          :key="item.to"
          :to="localeHref(item.to)"
          :target="item.target"
          :rel="item.target === '_blank' ? 'noopener noreferrer' : undefined"
          data-navbar="link"
          :aria-current="isActive(item.to) ? 'page' : undefined"
          :class="[
            'shrink-0 whitespace-nowrap px-3 py-2 text-sm font-medium rounded-md transition-colors hover:bg-accent hover:text-accent-foreground',
            isActive(item.to) ? 'bg-accent text-accent-foreground' : 'text-foreground/60 hover:text-foreground'
          ]"
        >
          <span class="inline-flex items-center gap-1.5">
            <DynamicIcon
              v-if="item.icon"
              :icon="item.icon"
              class="size-3.5 shrink-0 opacity-80"
            />
            {{ item.label }}
          </span>
        </NuxtLink>

        <!-- 溢出导航（默认主题、总条数在平铺闸门内）：2xl 起继续平铺，窄处交给下面的「更多」下拉。
             这一段遍历的是展开后的全集（含二级项），所以后台挂上 parent_id 之后，
             爬虫在 SSR HTML 里仍读得到那条内链——下拉是 ClientOnly，不进 HTML，
             把子项只放进下拉等于用「支持层级」换掉一整条内链。 -->
        <template v-if="flatOverflowAtWide">
          <NuxtLink
            v-for="item in overflowNavItems"
            :key="`wide-${item.to}`"
            :to="localeHref(item.to)"
            :target="item.target"
            :rel="item.target === '_blank' ? 'noopener noreferrer' : undefined"
            data-navbar="link"
            :data-depth="item.depth > 0 ? 1 : undefined"
            :aria-current="isActive(item.to) ? 'page' : undefined"
            :class="[
              'hidden shrink-0 whitespace-nowrap px-3 py-2 text-sm font-medium rounded-md transition-colors hover:bg-accent hover:text-accent-foreground 2xl:inline-flex',
              item.depth > 0 ? 'pl-2 border-l border-border/60 rounded-l-none' : '',
              isActive(item.to) ? 'bg-accent text-accent-foreground' : 'text-foreground/60 hover:text-foreground'
            ]"
          >
            <span class="inline-flex items-center gap-1.5">
              <DynamicIcon
                v-if="item.icon"
                :icon="item.icon"
                class="size-3.5 shrink-0 opacity-80"
              />
              {{ item.label }}
            </span>
          </NuxtLink>
        </template>

        <!-- 溢出导航收纳口：第 6 项（极简主题第 5 项）起进下拉，保证顶栏永远是单行；
             平铺档生效时它只在 2xl 以下出现（上面已平铺）。
             与下方控件区同理必须 ClientOnly：reka-ui 的 DropdownMenu 服务端只渲染一个
             空注释占位，客户端却要渲染触发器 button，裸写进 SSR 会让整站每一页都报
             hydration node mismatch（server 是注释节点、client 是 Fragment）。
             SEO 不受影响——溢出项与二级项在平铺档里本来就是真实 `<a>`（上面那段），
             爬虫读得到完整内链图。 -->
        <ClientOnly v-if="overflowNavItems.length > 0">
          <DropdownMenu>
            <DropdownMenuTrigger as-child>
              <button
                type="button"
                data-navbar="link"
                data-navbar-more
                :data-active="moreActive || undefined"
                :class="[
                  'inline-flex shrink-0 whitespace-nowrap items-center gap-1 px-3 py-2 text-sm font-medium rounded-md transition-colors hover:bg-accent hover:text-accent-foreground cursor-pointer',
                  flatOverflowAtWide ? '2xl:hidden' : '',
                  moreActive ? 'bg-accent text-accent-foreground' : 'text-foreground/60 hover:text-foreground'
                ]"
              >
                {{ t('nav.more') }}
                <ChevronDown class="size-3.5 opacity-70" />
              </button>
            </DropdownMenuTrigger>
            <DropdownMenuContent
              align="start"
              class="w-44"
            >
              <DropdownMenuItem
                v-for="item in overflowNavItems"
                :key="item.to"
                as-child
              >
                <NuxtLink
                  :to="localeHref(item.to)"
                  :target="item.target"
                  :rel="item.target === '_blank' ? 'noopener noreferrer' : undefined"
                  :class="[
                    item.depth > 0 ? 'pl-7' : '',
                    isActive(item.to) ? 'font-semibold' : ''
                  ]"
                >
                  <!-- 与上面两处同构：DynamicIcon 的根是多分支条件节点，data-icon 之类的
                       透传属性不保证落到图标元素上，所以统一用一层 span 收住「图标 + 标签」。 -->
                  <span class="inline-flex items-center gap-1.5">
                    <DynamicIcon
                      v-if="item.icon"
                      :icon="item.icon"
                      class="size-4 shrink-0 opacity-80"
                    />
                    {{ item.label }}
                  </span>
                </NuxtLink>
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
        </ClientOnly>
      </nav>

      <!-- 交互控件区：Tooltip/DropdownMenu/Sheet 基于 reka-ui，SSR 渲染 PrimitiveSlot 不稳定；
           且内容与用户登录态/主题偏好/语言选择强耦合，统一 ClientOnly 隔离避免 mismatch。
           Logo 与导航菜单（上方）保持 SSR，对 SEO 和首屏无影响。 -->
      <ClientOnly>
        <div
          data-navbar="actions"
          class="flex shrink-0 items-center gap-1"
        >
          <!-- 侧边栏导航只在 lg 起出现：窄屏已有汉堡抽屉（同一批导航入口），
               两个抽屉并排会让 actions 区再次超宽，挤压品牌与导航。 -->
          <div class="hidden lg:flex items-center">
            <SiteNavSidebar :items="navItems" />
          </div>

          <Tooltip v-if="showSearch">
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

          <ThemeToggle v-if="showDarkModeToggle" />

          <!-- 语言切换器与登录/注册按钮在 <sm 收进汉堡抽屉（Sheet 里已有同一批入口）：
               375px 下"品牌 + 搜索 + 明暗 + 语言 + 登录 + 注册 + 汉堡"的 shrink-0 总宽
               约 500px，一定溢出——溢出时最先被裁掉的是汉堡，等于移动端没有导航。 -->
          <div
            v-if="showLanguageSwitch"
            class="hidden sm:flex items-center"
          >
            <LocaleSwitcher />
          </div>

          <div
            v-if="!authStore.isAuthenticated"
            class="ml-1 hidden sm:flex items-center gap-2"
          >
            <Button
              variant="outline"
              size="sm"
              @click="handleLogin"
            >
              {{ t('auth.login') || '登录' }}
            </Button>
            <Button
              v-if="showRegister"
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
                  :seed="userInfoReady ? ((authStore.user as Record<string, unknown> | null)?.username as string) : ''"
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
                    :seed="userInfoReady ? ((authStore.user as Record<string, unknown> | null)?.username as string) : ''"
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
                <!-- 「Dashboard」入口只对 staff 显示：/admin/** 的 admin.global 中间件会把
                     普通成员静默弹回 /，看得见却点不进去比看不见更让人困惑。 -->
                <DropdownMenuItem
                  v-if="authStore.isAdmin"
                  @click="handleAdmin"
                >
                  <User data-icon="inline-start" />
                  <span>{{ t('common.dashboard') || 'Dashboard' }}</span>
                </DropdownMenuItem>
                <!-- 个人中心：/account 是 ssr:false 私有页（routeRules），入口只在这里，
                     不进主导航——未登录访客点它会得到一次跳转，没有意义。 -->
                <DropdownMenuItem @click="go('/account')">
                  <UserCircle2 data-icon="inline-start" />
                  <span>{{ t('account.title') }}</span>
                </DropdownMenuItem>
                <!-- 私信：与 /account 同档 ssr:false 私有页，入口同样只放在登录态菜单里。 -->
                <DropdownMenuItem @click="go('/account/messages')">
                  <MessageSquare data-icon="inline-start" />
                  <span>{{ t('messages.title') }}</span>
                </DropdownMenuItem>
                <!-- 站内通知：/api/notifications 只要求登录，普通成员也会收到"评论已通过"
                     这类回执。入口与 /account 同档（ssr:false 私有页），不进主导航。 -->
                <DropdownMenuItem @click="go('/account/notifications')">
                  <Bell data-icon="inline-start" />
                  <span>{{ t('notifications.title') }}</span>
                </DropdownMenuItem>
                <DropdownMenuItem @click="go('/settings')">
                  <Settings data-icon="inline-start" />
                  <span>{{ t('common.settings') || '设置' }}</span>
                </DropdownMenuItem>
              </DropdownMenuGroup>
              <DropdownMenuSeparator />
              <DropdownMenuItem
                class="text-error"
                @click="handleLogout"
              >
                <LogOut data-icon="inline-start" />
                <span>{{ t('auth.logout') || '退出登录' }}</span>
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>

          <Sheet>
            <SheetTrigger as-child>
              <Button
                variant="ghost"
                size="icon"
                class="lg:hidden"
                :aria-label="t('common.titleMenu') || 'Menu'"
              >
                <Menu data-icon="inline-start" />
              </Button>
            </SheetTrigger>
            <SheetContent
              side="left"
              class="w-[85%] max-w-sm flex flex-col overflow-y-auto overscroll-contain"
            >
              <SheetHeader class="text-left mb-4">
                <SheetTitle class="sr-only">
                  {{ t('common.titleMenu') || 'Menu' }}
                </SheetTitle>
                <NuxtLink
                  :to="localeHref('/')"
                  class="flex items-center gap-2 font-display text-xl font-bold tracking-tight"
                >
                  <img
                    :src="brandLogo"
                    :alt="brandName"
                    width="112"
                    height="28"
                    class="h-7 w-auto object-contain"
                  >
                  <span>{{ brandName }}</span>
                </NuxtLink>
              </SheetHeader>
              <Separator class="mb-4" />
              <nav
                class="flex flex-col gap-1 mb-6"
                :aria-label="t('common.titleMenu') || 'Menu'"
              >
                <SheetClose
                  v-for="item in flattenNavLinks(navItems)"
                  :key="item.to"
                  as-child
                >
                  <NuxtLink
                    :to="localeHref(item.to)"
                    :target="item.target"
                    :rel="item.target === '_blank' ? 'noopener noreferrer' : undefined"
                    :aria-current="isActive(item.to) ? 'page' : undefined"
                    :class="[
                      'px-3 py-2.5 text-sm font-medium rounded-md transition-colors hover:bg-accent hover:text-accent-foreground',
                      item.depth > 0 ? 'pl-7' : '',
                      isActive(item.to) ? 'bg-accent text-accent-foreground' : 'text-foreground/60 hover:text-foreground'
                    ]"
                  >
                    <span class="inline-flex items-center gap-1.5">
                      <DynamicIcon
                        v-if="item.icon"
                        :icon="item.icon"
                        class="size-3.5 shrink-0 opacity-80"
                      />
                      {{ item.label }}
                    </span>
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
                      :seed="(authStore.user as Record<string, unknown> | null)?.username as string || ''"
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
                    <SheetClose
                      v-if="authStore.isAdmin"
                      as-child
                    >
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
                    <SheetClose as-child>
                      <Button
                        variant="ghost"
                        size="sm"
                        class="justify-start"
                        @click="go('/account')"
                      >
                        <UserCircle2 data-icon="inline-start" />
                        {{ t('account.title') }}
                      </Button>
                    </SheetClose>
                    <SheetClose as-child>
                      <Button
                        variant="ghost"
                        size="sm"
                        class="justify-start"
                        @click="go('/account/messages')"
                      >
                        <MessageSquare data-icon="inline-start" />
                        {{ t('messages.title') }}
                      </Button>
                    </SheetClose>
                    <SheetClose as-child>
                      <Button
                        variant="ghost"
                        size="sm"
                        class="justify-start"
                        @click="go('/account/notifications')"
                      >
                        <Bell data-icon="inline-start" />
                        {{ t('notifications.title') }}
                      </Button>
                    </SheetClose>
                    <SheetClose as-child>
                      <Button
                        variant="ghost"
                        size="sm"
                        class="justify-start"
                        @click="go('/settings')"
                      >
                        <Settings data-icon="inline-start" />
                        {{ t('common.settings') || '设置' }}
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
                      v-if="showRegister"
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
                <LocaleSwitcher v-if="showLanguageSwitch" />
              </div>
            </SheetContent>
          </Sheet>
        </div>
        <template #fallback>
          <!-- SSR 回退占位：宽高与实际控件区一致，避免首屏布局抖动（CLS）。
               三个图标位必须跟着同一批开关走——写死 4 个占位时，功能开关关掉的主题
               在 375px 下会先渲染 ~250px 的 shrink-0 空位（品牌与导航一起被压），
               hydration 换成真实控件后又突然变窄，等于把整条顶栏左右弹一次。 -->
          <div
            class="flex items-center gap-1"
            aria-hidden="true"
          >
            <span
              v-if="showSearch"
              class="size-10 shrink-0"
            />
            <span
              v-if="showDarkModeToggle"
              class="size-10 shrink-0"
            />
            <span
              v-if="showLanguageSwitch"
              class="hidden sm:flex h-9 w-16 shrink-0 rounded-md"
            />
            <span class="ml-1 hidden sm:flex h-9 w-16 shrink-0 rounded-md border border-transparent" />
            <span
              v-if="showRegister"
              class="hidden sm:flex h-9 w-16 shrink-0 rounded-md"
            />
          </div>
        </template>
      </ClientOnly>
    </div>
  </header>
</template>
