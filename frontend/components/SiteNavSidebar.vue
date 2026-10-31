<!--
  侧边栏导航（lg 起，顶栏按钮 + 左侧抽屉）。

  与顶栏、移动端汉堡共用同一份导航数据：items 由 AppHeader 注入（顶栏已有
  /navigations + 兜底 + ENSURE_PRESENT 合并管线），这里不再自拉 header 档，避免两套
  菜单口径漂移。抽屉另外自拉 location=sidebar 一档，并补一节「分类」——分类在顶栏只占
  一条入口，深链只能先进 /categories 再点，侧边栏把它摊平。

  分类的 useAPI 键与 AppFooter / 分类页共用 `blog:categories:<locale>`（Nuxt 按 key
  去重，同页只发一条）。抽屉里的链接只在展开时进 DOM，爬虫的链接图仍由顶栏
  SSR 输出承担，所以这里不追求 SSR 可见性。

  但「不追求 SSR」不等于可以不取数：本组件挂在 <ClientOnly> 里，sidebar 档这条读口没有任何
  SSR 侧的同键喂数方，所以必须写 `server: false`（见下方注释），否则运营者存进 sidebar 的项
  在真实浏览器里一条都不显示。
-->
<script setup lang="ts">
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { PanelLeft } from '~~/lib/lucide-svg-icons'
import { Button } from '~~/components/ui/button'
import {
  Sheet,
  SheetTrigger,
  SheetContent,
  SheetHeader,
  SheetTitle,
  SheetClose
} from '~~/components/ui/sheet'
import { Separator } from '~~/components/ui/separator'
import DynamicIcon from '~~/components/DynamicIcon.vue'
import { flattenNavLinks, isNavActive, navRowsToLinks, withoutDuplicateTos, type NavApiRow, type NavLink } from '~~/lib/navigation'
import { pickLocalizedText } from '~~/composables/useI18nHelpers'

const props = defineProps<{ items: NavLink[] }>()

const { t, locale } = useI18n()
const route = useRoute()
const { localeHref } = useLocaleLink()

interface CategoryRow {
  id: number | string
  slug: string
  name?: string | Record<string, string>
  post_count?: number
  postsCount?: number
}

/**
 * 后台导航管理把 location 分成 header / footer / sidebar 三档，每一档都必须有消费方，
 * 否则运营者存进 sidebar 的项会静默消失（顶栏只读 header，页脚只读 footer）。
 * 这里读 sidebar 档，与注入的 items（header 档）分节显示，两者 URL 归一化共用 lib/navigation.ts。
 *
 * `server: false` 不是风格选择，是线上实测修出来的。ClientOnly 组件在 hydration 期调用带
 * `default` 的 useAPI 时，Nuxt（见 node_modules/nuxt/dist/app/composables/asyncData.js 的
 * `fetchOnServer && nuxtApp.isHydrating && asyncData.data.value !== void 0` 分支）会因为
 * `default` 已把 data 填成 `[]` 而直接把状态标成 success、handler 一次都不跑——表现是抽屉里
 * sidebar 那一节永久为空、CDP 网络面板看不见这条请求，接口本身却完全正常。
 * 分类那一节能显示只是巧合：它和 AppFooter 共用 `blog:categories:<locale>`，SSR 已把该键填好。
 */
const { data: sidebarNavRows } = useAPI<NavApiRow[]>('/navigations', {
  query: { location: 'sidebar' },
  key: `public:navigations:sidebar:${locale.value}`,
  server: false,
  default: () => []
})
const sidebarNavLinks = computed<NavLink[]>(() => {
  // 抽屉上半段渲染的是注入的 header 档；同一 URL 在两档都配置时只显示一次，
  // 否则抽屉里会出现两条一模一样的入口（两个位置各渲染一份，去重只能在这一层做）。
  // taken 要含 header 档的子项，且 sidebar 档里被摘掉的父项要把子项上提，不能整支消失。
  const taken = new Set(flattenNavLinks(props.items).map(item => item.to))
  return withoutDuplicateTos(
    navRowsToLinks(sidebarNavRows.value, row => pickLocalizedText(row.label ?? row.title ?? row.name, locale.value as string)),
    taken
  )
})

const { data: catsData } = useAPI<CategoryRow[]>('/blog/categories', {
  query: { lang: locale.value },
  key: `blog:categories:${locale.value}`,
  default: () => []
})

// 只取前 10 条：侧边栏是速览入口，完整清单仍在 /categories
const categories = computed<CategoryRow[]>(() =>
  Array.isArray(catsData.value) ? catsData.value.slice(0, 10) : []
)
const catName = (c: CategoryRow) => pickLocalizedText(c.name, locale.value as string)
const catCount = (c: CategoryRow) => c.post_count ?? c.postsCount ?? 0
</script>

<template>
  <Sheet>
    <SheetTrigger as-child>
      <Button
        variant="ghost"
        size="icon"
        :aria-label="t('nav.sidebarNav') || 'Sidebar'"
        :title="t('nav.sidebarNav') || 'Sidebar'"
      >
        <PanelLeft />
      </Button>
    </SheetTrigger>
    <SheetContent
      side="left"
      class="w-[85%] max-w-xs flex flex-col overflow-y-auto overscroll-contain"
    >
      <SheetHeader class="text-left mb-4">
        <SheetTitle class="text-base">
          {{ t('nav.sidebarNav') || 'Sidebar' }}
        </SheetTitle>
      </SheetHeader>
      <Separator class="mb-4" />

      <nav
        class="flex flex-col gap-1"
        :aria-label="t('nav.navigation') || 'Navigation'"
      >
        <SheetClose
          v-for="item in flattenNavLinks(items)"
          :key="item.to"
          as-child
        >
          <NuxtLink
            :to="localeHref(item.to)"
            :target="item.target"
            :rel="item.target === '_blank' ? 'noopener noreferrer' : undefined"
            :aria-current="isNavActive(route.path, item.to) ? 'page' : undefined"
            :class="[
              'px-3 py-2 text-sm font-medium rounded-md transition-colors hover:bg-accent hover:text-accent-foreground',
              item.depth > 0 ? 'pl-7' : '',
              isNavActive(route.path, item.to) ? 'bg-accent text-accent-foreground' : 'text-foreground/60 hover:text-foreground'
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

      <template v-if="sidebarNavLinks.length > 0">
        <Separator class="my-4" />
        <div class="px-3 mb-2 text-xs font-semibold uppercase tracking-wide text-muted-foreground">
          {{ t('nav.sidebarNav') || 'Sidebar' }}
        </div>
        <nav
          class="flex flex-col gap-1"
          :aria-label="t('nav.sidebarNav') || 'Sidebar'"
        >
          <SheetClose
            v-for="link in flattenNavLinks(sidebarNavLinks)"
            :key="`sidebar-${link.to}`"
            as-child
          >
            <NuxtLink
              :to="localeHref(link.to)"
              :target="link.target"
              :rel="link.target === '_blank' ? 'noopener noreferrer' : undefined"
              :aria-current="isNavActive(route.path, link.to) ? 'page' : undefined"
              :class="[
                'px-3 py-2 text-sm font-medium rounded-md transition-colors hover:bg-accent hover:text-accent-foreground',
                link.depth > 0 ? 'pl-7' : '',
                isNavActive(route.path, link.to) ? 'bg-accent text-accent-foreground' : 'text-foreground/60 hover:text-foreground'
              ]"
            >
              <span class="inline-flex items-center gap-1.5">
                <DynamicIcon
                  v-if="link.icon"
                  :icon="link.icon"
                  class="size-3.5 shrink-0 opacity-80"
                />
                {{ link.label }}
              </span>
            </NuxtLink>
          </SheetClose>
        </nav>
      </template>

      <template v-if="categories.length > 0">
        <Separator class="my-4" />
        <div class="px-3 mb-2 text-xs font-semibold uppercase tracking-wide text-muted-foreground">
          {{ t('nav.categories') || 'Categories' }}
        </div>
        <div class="flex flex-col gap-1">
          <SheetClose
            v-for="cat in categories"
            :key="cat.id"
            as-child
          >
            <NuxtLink
              :to="localeHref(`/categories/${cat.slug}`)"
              class="flex items-center justify-between gap-2 px-3 py-1.5 text-sm rounded-md text-foreground/60 hover:bg-accent hover:text-foreground transition-colors"
            >
              <span class="truncate">{{ catName(cat) }}</span>
              <span class="shrink-0 text-xs text-muted-foreground tabular-nums">{{ catCount(cat) }}</span>
            </NuxtLink>
          </SheetClose>
        </div>
      </template>
    </SheetContent>
  </Sheet>
</template>
